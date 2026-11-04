"""验证副本隔离、编码、版本冲突、差异和验证失效，不改正式源码。"""

import asyncio
import codecs
import io
import json
import zipfile
from pathlib import Path
from threading import Event

import pytest

from app.infrastructure.storage.files import digest
from app.modules.code_work.files import PROJECT, read_json, save_json
from app.modules.code_work.service import CodeWork
from tests.helpers.code_work import FILE, make_work


@pytest.fixture
def work(services, tmp_path):
    return make_work(services, tmp_path)


def test_edit_diff_export_revert_preserves_original_and_runtime_settings(work):
    service, thread, original = work
    before = (original / "Main/Example.cs").read_bytes()
    read = service.read(thread, FILE)
    result = service.write(
        thread, FILE, "int Value = 2;", read["version"], old_text="int Value = 1;"
    )
    assert result["revision"] == 1
    difference = service.diff(thread, FILE)
    assert "- int Value = 1;" in difference["diff"]
    assert "+ int Value = 2;" in difference["diff"]
    changed = service.folder(thread) / "source" / FILE
    assert b"\r\n" in changed.read_bytes()
    with zipfile.ZipFile(io.BytesIO(service.export(thread))) as package:
        assert package.read(FILE) == changed.read_bytes()
        assert json.loads(package.read("verification.json"))["revision"] == 1
        assert "changes.diff" in package.namelist()
        assert not any("private.json" in path for path in package.namelist())
    assert not (service.folder(thread) / "source" / PROJECT / "bin/Debug/Settings").exists()
    service.revert(thread, FILE, result["version"])
    assert changed.read_bytes() == before
    assert service.status(thread)["files"] == []
    assert (original / "Main/Example.cs").read_bytes() == before


def test_new_file_and_later_edits_share_baseline_and_stale_versions_are_rejected(work):
    service, thread, _ = work
    version = service.read(thread, FILE)["version"]
    first = service.write(thread, FILE, "class Example { int Value = 3; }", version)
    with pytest.raises(ValueError, match="已更新"):
        service.write(thread, FILE, "lost edit", version)
    service.write(thread, FILE, "class Example { int Value = 4; }", first["version"])
    assert "int Value = 1;" in service.diff(thread, FILE)["before"]
    added = f"{PROJECT}/Main/New.cs"
    result = service.write(thread, added, "class Added {}", "")
    assert service.status(thread)["files"][1]["kind"] == "added"
    assert service.diff(thread, added)["before"] == ""
    service.revert(thread, added, result["version"])
    assert not (service.folder(thread) / "source" / added).exists()


@pytest.mark.parametrize(
    "path",
    [
        "../outside.cs",
        "/outside.cs",
        "C:/outside.cs",
        "Other/Thing.cs",
        f"{PROJECT}/Program.cs",
        f"{PROJECT}/Infrastructure/Simulation/OriginalSimulation.cs",
        f"{PROJECT}/Properties/AssemblyInfo.cs",
        f"{PROJECT}/Main/CON.cs",
        f"{PROJECT}/bin/New.cs",
        f"{PROJECT}/Main/Test.cs:stream",
        f"{PROJECT}/{PROJECT}.csproj",
    ],
)
def test_unsafe_or_harness_paths_are_rejected(work, path):
    service, thread, _ = work
    with pytest.raises((ValueError, FileNotFoundError)):
        service.write(thread, path, "class Escape {}", "")
    assert service.status(thread)["revision"] == 0


@pytest.mark.parametrize(
    ("raw", "encoding"),
    [
        (codecs.BOM_UTF8 + "// 测试\r\nclass Example {}".encode(), "utf-8"),
        (codecs.BOM_UTF16_LE + "// 测试\r\nclass Example {}".encode("utf-16-le"), "utf-16-le"),
        (codecs.BOM_UTF16_BE + "// 测试\r\nclass Example {}".encode("utf-16-be"), "utf-16-be"),
        ("// 测试\r\nclass Example {}".encode("gb18030"), "gb18030"),
    ],
)
def test_edits_preserve_original_encoding_and_line_endings(work, raw, encoding):
    service, thread, original = work
    path = f"{PROJECT}/Main/Encoded.cs"
    (original / "Main/Encoded.cs").write_bytes(raw)
    # 创建后新增的外部来源文件不会自动进入固定副本。
    result = service.write(thread, path, "class Example {}", "")
    file = service.folder(thread) / "source" / path
    file.write_bytes(raw)
    state = read_json(service.folder(thread) / "state.json")
    state["changes"][path]["version"] = digest(raw)
    save_json(service.folder(thread) / "state.json", state)
    result = service.write(
        thread, path, "class Example { }", digest(raw), old_text="class Example {}"
    )
    assert result["changed"]
    assert file.read_bytes() == raw.replace(
        "class Example {}".encode(encoding),
        "class Example { }".encode(encoding),
    )


def test_ambiguous_replace_and_links_cannot_modify_copy_or_original(work, tmp_path):
    service, thread, _ = work
    version = service.read(thread, FILE)["version"]
    with pytest.raises(ValueError, match="唯一匹配"):
        service.write(thread, FILE, "x", version, old_text="missing")
    outside = tmp_path / "outside.cs"
    outside.write_text("do not change")
    link = service.folder(thread) / "source" / PROJECT / "Main/Link.cs"
    try:
        link.hardlink_to(outside)
    except OSError:
        pytest.skip("当前文件系统不能创建硬链接")
    with pytest.raises(ValueError, match="硬链接"):
        service.write(thread, f"{PROJECT}/Main/Link.cs", "changed", "")
    assert outside.read_text() == "do not change"


def test_working_copy_file_lookup_and_locked_code_are_readable_without_editing(work):
    service, thread, _ = work
    assert service.find(thread, "Example.cs")["files"] == [{"path": FILE, "name": "Example.cs"}]
    program = service.read(thread, f"{PROJECT}/Program.cs")
    assert "class Program" in program["content"]
    with pytest.raises(ValueError):
        service.write(thread, f"{PROJECT}/Program.cs", "changed", program["version"])
    with pytest.raises(ValueError, match="C#"):
        service.read(thread, f"{PROJECT}/App.config")
    assert service.status(thread)["revision"] == 0


def test_short_folder_identifier_cannot_alias_another_conversation(work, monkeypatch):
    service, thread, _ = work
    other = service.repository.create_thread("另一个对话")["id"]
    original_digest = digest
    monkeypatch.setattr(
        "app.modules.code_work.service.digest",
        lambda data: (
            original_digest(thread.encode()) if data == other.encode() else original_digest(data)
        ),
    )
    with pytest.raises(ValueError, match="标识冲突"):
        service.status(other)
    with pytest.raises(ValueError, match="标识冲突"):
        service.create(other)
    assert service.status(thread)["revision"] == 0


@pytest.mark.asyncio
async def test_verification_results_bind_to_revision_and_code_edit_invalidates_pass(
    work, monkeypatch
):
    service, thread, _ = work
    monkeypatch.setattr(service.environment, "compiler", lambda: "fake-msbuild.exe")

    def execute(args, cwd, log, stop, deadline):
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("build ok", encoding="utf-8")
        if str(args[0]).endswith("VirtualMotionDrivers.Tests.exe"):
            log.write_text("PASS: 16 virtual driver checks", encoding="utf-8")
        if "/p:Configuration=Simulation" in args:
            output = next(
                item.split("=", 1)[1] for item in args if item.startswith("/p:OutputPath=")
            )
            target = Path(output)
            target.mkdir(parents=True, exist_ok=True)
            (target / f"{PROJECT}.exe").write_bytes(b"new-executable")
        if "--simulation-self-test" in args:
            Path(args[0]).with_name("original-simulation-checks.txt").write_text(
                "PASS: 69 original-project integration checks.", encoding="utf-8"
            )
        return 0

    monkeypatch.setattr("app.modules.code_work.runner.execute", execute)
    await service.verify(thread)
    await service.tasks[thread]
    state = service.status(thread)
    assert state["verification"]["status"] == "passed"
    assert [step.get("checks") for step in state["verification"]["steps"]] == [None, 16, None, 69]
    assert state["verification_current"] is True
    file = service.folder(thread) / "source" / FILE
    before = file.read_bytes()
    file.write_bytes(b"class ExternalChange {}")
    assert service.status(thread)["verification_current"] is False
    file.write_bytes(before)
    version = service.read(thread, FILE)["version"]
    service.write(thread, FILE, "class Changed {}", version)
    assert service.status(thread)["verification_current"] is False
    assert service.status(thread)["verification"]["revision"] == 0


@pytest.mark.asyncio
async def test_cancellation_and_restart_never_mark_incomplete_run_passed(work, monkeypatch):
    service, thread, _ = work
    monkeypatch.setattr(service.environment, "compiler", lambda: "fake-msbuild.exe")
    started = Event()

    def execute(args, cwd, log, stop, deadline):
        started.set()
        stop.wait(5)
        raise InterruptedError("验证已停止")

    monkeypatch.setattr("app.modules.code_work.runner.execute", execute)
    await service.verify(thread)
    await asyncio.to_thread(started.wait, 3)
    with pytest.raises(ValueError, match="正在验证"):
        service.write(thread, FILE, "cannot edit", service.read(thread, FILE)["version"])
    service.cancel(thread)
    await service.tasks[thread]
    assert service.status(thread)["verification"]["status"] == "cancelled"
    state_path = service.folder(thread) / "state.json"
    state = read_json(state_path)
    state["verification"]["status"] = "building"
    save_json(state_path, state)
    fresh = CodeWork(service.paths, service.repository)
    assert fresh.status(thread)["verification"]["status"] == "interrupted"
