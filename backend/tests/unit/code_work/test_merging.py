"""合并事务使用独立工程，验证冲突、并行修改、故障恢复与回退保护。"""

import pytest

from app.infrastructure.storage.files import digest
from app.modules.code_work.files import PROJECT, code_manifest, read_json, save_json
from app.modules.code_work.merge_text import include_files, merge
from app.modules.code_work.transactions import recover
from tests.helpers.code_work import FILE, make_work


def verified_plan(work, thread, **options):
    """此层只测试应用事务，构建边界由runner及真实Windows验收覆盖。"""
    plan = work.merge_preview(thread, **options)
    directory = work.folder(thread) / "merges" / plan["id"][:10]
    state = read_json(directory / "state.json")
    manifest = code_manifest(directory / "source")
    state["verification"] = {
        "id": "unit",
        "status": "passed",
        "steps": [],
        "revision": plan["revision"],
        "code_version": digest(str(sorted(manifest.items())).encode()),
    }
    save_json(directory / "state.json", state)
    return plan


@pytest.mark.parametrize(
    "base,source,workspace,expected",
    [
        (b"a\nb\nc\n", b"A\nb\nc\n", b"a\nb\nC\n", b"A\nb\nC\n"),
        (b"a\n", b"a\n", b"b\n", b"b\n"),
        (None, None, b"new\n", b"new\n"),
        (None, b"same", b"same", b"same"),
        (b"a\r\nb\r\nc\r\n", b"A\r\nb\r\nc\r\n", b"a\r\nb\r\nC\r\n", b"A\r\nb\r\nC\r\n"),
    ],
)
def test_three_way_preserves_non_overlapping_changes_and_encoding(
    base, source, workspace, expected
):
    assert merge(base, source, workspace) == expected


@pytest.mark.parametrize(
    "base,source,workspace",
    [
        (b"a\n", b"A\n", b"B\n"),
        (None, b"a", b"b"),
        (b"a", None, b"b"),
        (b"a\n", b"x\na\n", b"y\na\n"),
    ],
)
def test_three_way_rejects_overlap_and_add_delete_collisions(base, source, workspace):
    with pytest.raises(ValueError):
        merge(base, source, workspace)


def test_preview_verify_apply_rebase_and_rollback_preserve_both_editors(services, tmp_path):
    work, thread, original = make_work(services, tmp_path)
    initial = (original / "Main/Example.cs").read_bytes()
    work.write(
        thread,
        FILE,
        "int Value = 2;",
        work.read(thread, FILE)["version"],
        old_text="int Value = 1;",
        run_id="round-1",
    )
    snapshot = work.summary(thread, "round-1")
    (original / "Main/Example.cs").write_bytes(initial + b"// human change\r\n")
    plan = verified_plan(work, thread)
    assert plan["source_changed"] and plan["conflicts"] == []
    difference = work.merge_diff(thread, plan["id"], FILE)
    assert "human change" in difference["after"] and "Value = 2" in difference["after"]
    applied = work.merge_apply(thread, plan["id"], {"id": "operator"})
    assert applied["files"] == [] and applied["verification"] is None
    merged = (original / "Main/Example.cs").read_bytes()
    assert b"human change" in merged and b"Value = 2" in merged
    assert (work.folder(thread) / "source" / FILE).read_bytes() == merged
    assert work.summary(thread, "round-1") == snapshot
    reverted = work.merge_rollback(thread, plan["id"], {"id": "operator"})
    assert b"Value = 1" in (original / "Main/Example.cs").read_bytes()
    assert b"human change" in (original / "Main/Example.cs").read_bytes()
    assert len(reverted["files"]) == 1
    assert b"Value = 2" in (work.folder(thread) / "source" / FILE).read_bytes()
    assert reverted["applied"][-1]["status"] == "rolled_back"


def test_conflict_requires_explicit_resolution_and_reverification(services, tmp_path):
    work, thread, original = make_work(services, tmp_path)
    work.write(thread, FILE, "class Copy {}", work.read(thread, FILE)["version"])
    (original / "Main/Example.cs").write_text("class Human {}", encoding="utf-8")
    conflict = work.merge_preview(thread)
    assert conflict["conflicts"] == [FILE] and not conflict["can_apply"]
    with pytest.raises(ValueError, match="验证"):
        work.merge_apply(thread, conflict["id"], {})
    resolved = verified_plan(
        work, thread, resolutions={FILE: {"choice": "manual", "content": "class Combined {}"}}
    )
    work.merge_apply(thread, resolved["id"], {})
    assert (original / "Main/Example.cs").read_text() == "class Combined {}"


@pytest.mark.parametrize("changed", ["original", "copy", "unselected-original"])
def test_preview_is_stale_after_any_relevant_version_changes(services, tmp_path, changed):
    work, thread, original = make_work(services, tmp_path)
    work.write(thread, FILE, "class Changed {}", work.read(thread, FILE)["version"])
    plan = verified_plan(work, thread)
    if changed == "original":
        (original / "Main/Example.cs").write_text("class Human {}")
    elif changed == "copy":
        work.write(thread, FILE, "class Later {}", work.read(thread, FILE)["version"])
    else:
        (original / "Main/Other.cs").write_text("class Human {}")
    with pytest.raises(ValueError, match="变化|更新"):
        work.merge_apply(thread, plan["id"], {})


def test_partial_selection_keeps_other_copy_changes_pending(services, tmp_path):
    work, thread, original = make_work(services, tmp_path)
    work.write(thread, FILE, "class Changed {}", work.read(thread, FILE)["version"])
    added = "AKRS.ZX2200/Main/Added.cs"
    work.write(thread, added, "class Added {}", "")
    plan = verified_plan(work, thread, selected=[FILE])
    status = work.merge_apply(thread, plan["id"], {})
    assert [item["path"] for item in status["files"]] == [added]
    assert not (original / "Main/Added.cs").exists()
    assert work.diff(thread, added)["after"] == "class Added {}"


def test_new_file_is_in_project_and_rollback_restores_project(services, tmp_path):
    work, thread, original = make_work(services, tmp_path)
    added = "AKRS.ZX2200/Main/Added.cs"
    project = original / f"{PROJECT}.csproj"
    before = project.read_bytes()
    work.write(thread, added, "class Added {}", "")
    plan = verified_plan(work, thread)
    assert any(item["kind"] == "project" for item in plan["files"])
    work.merge_apply(thread, plan["id"], {})
    assert b"Main\\Added.cs" in project.read_bytes()
    assert include_files(project.read_bytes(), [added], PROJECT) == project.read_bytes()
    work.merge_rollback(thread, plan["id"], {})
    assert project.read_bytes() == before and not (original / "Main/Added.cs").exists()
    assert work.status(thread)["files"][0]["path"] == added


@pytest.mark.parametrize("failure", ["second-write", "state-save"])
def test_application_failure_restores_original_copy_and_state(
    services, tmp_path, monkeypatch, failure
):
    work, thread, original = make_work(services, tmp_path)
    before = (original / "Main/Example.cs").read_bytes()
    work.write(thread, FILE, "class Changed {}", work.read(thread, FILE)["version"])
    work.write(thread, "AKRS.ZX2200/Main/New.cs", "class New {}", "")
    plan = verified_plan(work, thread)
    original_status = work.status(thread)
    folder = work.folder(thread)
    if failure == "second-write":
        from app.modules.code_work import transactions

        real = transactions.atomic_bytes
        calls = 0

        def failing(path, data):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected write failure")
            real(path, data)

        monkeypatch.setattr(transactions, "atomic_bytes", failing)
    else:
        from app.modules.code_work import merging

        real = merging.save_json

        def failing(path, data):
            if path == folder / "state.json":
                raise OSError("injected state failure")
            real(path, data)

        monkeypatch.setattr(merging, "save_json", failing)
    with pytest.raises(OSError, match="injected"):
        work.merge_apply(thread, plan["id"], {})
    assert (original / "Main/Example.cs").read_bytes() == before
    assert not (original / "Main/New.cs").exists()
    assert work.status(thread)["revision"] == original_status["revision"]
    assert work.status(thread)["files"] == original_status["files"]
    assert work.diff(thread, FILE)["after"] == "class Changed {}"
    recover(folder)


def test_rollback_never_overwrites_later_original_edits(services, tmp_path):
    work, thread, original = make_work(services, tmp_path)
    work.write(thread, FILE, "class Changed {}", work.read(thread, FILE)["version"])
    plan = verified_plan(work, thread)
    work.merge_apply(thread, plan["id"], {})
    (original / "Main/Example.cs").write_text("class LaterHuman {}")
    with pytest.raises(ValueError, match="后续修改"):
        work.merge_rollback(thread, plan["id"], {})
    assert (original / "Main/Example.cs").read_text() == "class LaterHuman {}"


@pytest.mark.parametrize("restart", [False, True])
def test_interrupted_write_preserves_external_edit_and_requires_versioned_acknowledgement(
    services, tmp_path, monkeypatch, restart
):
    from app.modules.code_work import transactions
    from app.modules.code_work.service import CodeWork

    work, thread, original = make_work(services, tmp_path)
    work.write(thread, FILE, "class Copy {}", work.read(thread, FILE)["version"])
    added = f"{PROJECT}/Main/New.cs"
    work.write(thread, added, "class New {}", "")
    plan = verified_plan(work, thread)
    original_write = transactions.write

    def interrupted(folder, directory, journal):
        original_write(folder, directory, journal)
        (original / "Main/Example.cs").write_text("class Human {}", encoding="utf-8")
        if restart:
            raise SystemExit("simulate terminated process")
        raise OSError("injected interrupted write")

    monkeypatch.setattr(transactions, "write", interrupted)
    with pytest.raises((SystemExit, OSError)):
        work.merge_apply(thread, plan["id"], {})
    # 新实例只按持久化记录恢复；不依赖旧进程或内存。
    work = CodeWork(work.paths, work.repository)
    status = work.status(thread)
    assert (original / "Main/Example.cs").read_text() == "class Human {}"
    assert not (original / "Main/New.cs").exists()
    assert work.diff(thread, FILE)["after"] == "class Copy {}"
    record = status["recovery"][0]
    assert [item["path"] for item in record["files"]] == [FILE]
    difference = work.recovery_diff(thread, record["id"], FILE)
    assert difference["after"] == "class Human {}"
    assert "Value = 1" in difference["before"]
    with pytest.raises(ValueError, match="恢复"):
        work.write(thread, FILE, "class Wrong {}", work.read(thread, FILE)["version"])
    with pytest.raises(ValueError, match="恢复"):
        work.merge_preview(thread)
    versions = {FILE: difference["version"]}
    (original / "Main/Example.cs").write_text("class LaterHuman {}", encoding="utf-8")
    with pytest.raises(ValueError, match="变化"):
        work.recovery_resolve(thread, record["id"], record["target"], versions, {})
    current = work.recovery_diff(thread, record["id"], FILE)
    status = work.recovery_resolve(
        thread, record["id"], record["target"], {FILE: current["version"]}, {"name": "reviewer"}
    )
    assert not status["recovery"]
    assert (original / "Main/Example.cs").read_text() == "class LaterHuman {}"
    assert work.merge_preview(thread)["conflicts"] == [FILE]


def test_project_compile_item_escapes_xml_filename():
    project = include_files(b"<Project />", [f"{PROJECT}/Main/A&B.cs"], PROJECT)
    assert b"A&amp;B.cs" in project
