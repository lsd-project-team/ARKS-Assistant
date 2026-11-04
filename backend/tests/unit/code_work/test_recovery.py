"""副本依赖路径、备份重建和落盘失败的回归。"""

import io
from zipfile import ZipFile

import pytest

from app.infrastructure.storage.backup import create_backup
from app.infrastructure.storage.files import digest
from app.modules.code_work.files import PROJECT, copy_project_outputs, read_json
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
    copy_project_outputs(source, destination, [0, 0])
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
