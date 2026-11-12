"""副本依赖路径、备份重建和落盘失败的回归。"""

import io
import shutil
from zipfile import ZipFile

import pytest

from app.infrastructure.storage.backup import create_backup
from app.infrastructure.storage.files import digest
from app.modules.code_work.environment import EnvironmentWrite
from app.modules.code_work.files import PROJECT, copy_project_outputs, read_json, save_json
from tests.helpers.code_work import FILE, make_work


def test_snapshot_preserves_project_reference_output_locations(tmp_path):
    source, destination = tmp_path / "original", tmp_path / "copied"
    main = source / PROJECT
    dependency = source / "Dependency"
    main.mkdir(parents=True)
    dependency.mkdir()
    namespace = 'xmlns="http://schemas.microsoft.com/developer/msbuild/2003"'
    (main / f"{PROJECT}.csproj").write_text(
        f"<Project {namespace}><ItemGroup>"
        '<ProjectReference Include="..\\Dependency\\Dependency.csproj"/>'
        "</ItemGroup></Project>",
        encoding="utf-8",
    )
    (dependency / "Dependency.csproj").write_text(
        f"<Project {namespace}><PropertyGroup><AssemblyName>Dependency</AssemblyName>"
        "<OutputType>Library</OutputType></PropertyGroup></Project>",
        encoding="utf-8",
    )
    (main / "bin/Debug").mkdir(parents=True)
    (main / "bin/Debug/Dependency.dll").write_bytes(b"pinned-dependency")
    copy_project_outputs(source, destination, [0, 0], PROJECT)
    assert (
        destination / "Dependency/bin/Debug/Dependency.dll"
    ).read_bytes() == b"pinned-dependency"
    assert not (dependency / "bin").exists()


def test_compact_backup_preserves_changes_and_rebuilds_exact_source(services, tmp_path):
    service, thread, original = make_work(services, tmp_path)
    service.write(thread, FILE, "class Edited {}", service.read(thread, FILE)["version"])
    added = f"{PROJECT}/Main/Added.cs"
    service.write(thread, added, "class Added {}", "")
    folder = service.folder(thread)
    (folder / "checks/output/Simulation").mkdir(parents=True)
    (folder / "checks/output/Simulation/generated.exe").write_bytes(b"rebuildable")
    with ZipFile(create_backup(service.paths)) as package:
        names = package.namelist()
        prefix = "scratch/cw/" + folder.name + "/"
        assert prefix + "state.json" in names and prefix + "inputs.json" in names
        assert prefix + "source/" + FILE in names
        assert prefix + "baseline/" + FILE in names
        assert not any(name.endswith("runtime.dll") or "/checks/" in name for name in names)
        assert prefix + "ready" not in names
        # 按真实备份成员还原源树，不改动正式数据或其他测试目录。
        saved = {
            name[len(prefix) :]: package.read(name) for name in names if name.startswith(prefix)
        }
    for path in sorted((folder / "source").rglob("*"), reverse=True):
        if path.is_file():
            path.unlink()
        else:
            path.rmdir()
    (folder / "ready").unlink()
    for name, content in saved.items():
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    assert service.status(thread)["prepared"] is False
    with ZipFile(io.BytesIO(service.export(thread))) as package:
        assert package.read(FILE) == b"class Edited {}"
    service.create(thread)
    assert service.status(thread)["prepared"] is True
    assert (folder / "source" / FILE).read_bytes() == b"class Edited {}"
    assert (folder / "source" / added).read_bytes() == b"class Added {}"
    assert (
        folder / "source" / PROJECT / "bin/Debug/runtime.dll"
    ).read_bytes() == b"test-dependency"
    assert "int Value = 1;" in service.diff(thread, FILE)["before"]
    assert "int Value = 1;" in (original / "Main/Example.cs").read_text(encoding="utf-8")


def test_restored_copy_rejects_different_source_without_losing_edits(services, tmp_path):
    service, thread, original = make_work(services, tmp_path)
    service.write(thread, FILE, "class Edited {}", service.read(thread, FILE)["version"])
    folder = service.folder(thread)
    (folder / "ready").unlink()
    (original / "Main/Example.cs").write_text("class NewOriginal {}", encoding="utf-8")
    with pytest.raises(ValueError, match="版本不同"):
        service.create(thread)
    assert (folder / "source" / FILE).read_bytes() == b"class Edited {}"
    assert service.status(thread)["prepared"] is False
    assert not list(folder.glob("hydrating-*"))


def test_backup_keeps_immutable_history_reports_and_merge_recovery_but_excludes_builds(
    services, tmp_path
):
    work, thread, _ = make_work(services, tmp_path)
    work.write(thread, FILE, "class Edited {}", work.read(thread, FILE)["version"], run_id="run-a")
    folder = work.folder(thread)
    report = folder / "reports/job/verification.json"
    report.parent.mkdir(parents=True)
    report.write_text('{"status":"failed"}', encoding="utf-8")
    merge = folder / "merges/0123456789"
    merge.mkdir(parents=True)
    save_json(merge / "transaction.json", {"status": "recovered"})
    save_json(merge / "plan.json", {"id": "plan"})
    candidate = merge / "source"
    candidate.mkdir()
    (candidate / "private.cs").write_text("exclude candidate source", encoding="utf-8")
    with ZipFile(create_backup(work.paths)) as archive:
        prefix = f"scratch/cw/{folder.name}/"
        assert archive.read(prefix + "reports/job/verification.json") == report.read_bytes()
        assert prefix + "merges/0123456789/transaction.json" in archive.namelist()
        assert prefix + "merges/0123456789/plan.json" in archive.namelist()
        assert prefix + "merges/0123456789/source/private.cs" not in archive.namelist()
        assert any(name.startswith(prefix + "history/blobs/") for name in archive.namelist())
    assert work.diff(thread, FILE, "run-a")["after"] == "class Edited {}"


def test_verified_identical_source_relocation_updates_pinned_path_and_clears_old_result(
    services, tmp_path
):
    work, thread, original = make_work(services, tmp_path)
    relocated = tmp_path / "relocated"
    shutil.copytree(original.parent, relocated)
    folder = work.folder(thread)
    state = read_json(folder / "state.json")
    state["verification"] = {"id": "old", "status": "passed", "revision": state["revision"]}
    save_json(folder / "state.json", state)
    (folder / "ready").unlink()
    work.environment.save(
        EnvironmentWrite(source_root=str(relocated), version=work.environment.version())
    )
    work.create(thread)
    status = work.status(thread)
    assert status["source_path"] == str(relocated.resolve())
    assert status["verification"] is None and not status["verification_current"]


@pytest.mark.parametrize("action", ["write", "revert"])
def test_state_save_failure_preserves_file_and_revision(services, tmp_path, monkeypatch, action):
    service, thread, _ = make_work(services, tmp_path)
    service.write(thread, FILE, "class First {}", service.read(thread, FILE)["version"])
    folder = service.folder(thread)
    before = (folder / "source" / FILE).read_bytes()
    state = read_json(folder / "state.json")

    def fail(*_args):
        raise OSError("disk full")

    monkeypatch.setattr("app.modules.code_work.service.save_json", fail)
    with pytest.raises(OSError, match="disk full"):
        if action == "write":
            service.write(thread, FILE, "class Lost {}", digest(before))
        else:
            service.revert(thread, FILE, digest(before))
    assert (folder / "source" / FILE).read_bytes() == before
    assert read_json(folder / "state.json") == state
