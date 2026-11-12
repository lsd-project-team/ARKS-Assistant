"""按目录结构识别主工程、按项目保存执行环境的回归。"""

import json

import pytest

from app.modules.code_work.environment import (
    CodeEnvironment,
    EnvironmentWrite,
    migrate_legacy,
)
from app.modules.code_work.files import main_project
from app.modules.code_work.service import CodeWork


def make_project(root, name, *, simulation=True):
    app = root / name
    (app / "Main").mkdir(parents=True)
    (app / "Infrastructure/Simulation").mkdir(parents=True)
    (app / "bin/Debug").mkdir(parents=True)
    (app / f"{name}.csproj").write_text("<Project />", encoding="utf-8")
    (app / "App.config").write_text("<configuration />", encoding="utf-8")
    (app / "Program.cs").write_text("class Program {}", encoding="utf-8")
    (app / "Main/Example.cs").write_text("class Example {}", encoding="utf-8")
    if simulation:
        (app / "Infrastructure/Simulation/OriginalSimulation.cs").write_text(
            "class OriginalSimulation {}", encoding="utf-8"
        )
    return app


def test_main_project_is_detected_by_layout_not_by_name(tmp_path):
    make_project(tmp_path, "SampleApp")
    make_project(tmp_path, "Unrelated", simulation=False)

    assert main_project(tmp_path) == "SampleApp"


def test_main_project_reports_missing_or_multiple_candidates(tmp_path):
    make_project(tmp_path, "First")
    make_project(tmp_path, "Second")

    with pytest.raises(ValueError, match="多个主工程"):
        main_project(tmp_path)

    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ValueError, match="需包含主工程"):
        main_project(empty)


def test_environment_is_saved_per_project_without_shared_state(tmp_path):
    first = make_project(tmp_path / "one", "Alpha")
    second = make_project(tmp_path / "two", "Beta")
    alpha = CodeEnvironment(tmp_path / "data", "project-a")
    beta = CodeEnvironment(tmp_path / "data", "project-b")

    alpha.save(EnvironmentWrite(source_root=str(first.parent), version=alpha.version()))
    beta.save(EnvironmentWrite(source_root=str(second.parent), version=beta.version()))

    assert alpha.load().source_root == str(first.parent.resolve())
    assert alpha.load().project == "Alpha"
    assert beta.load().source_root == str(second.parent.resolve())
    assert beta.load().project == "Beta"
    assert CodeEnvironment(tmp_path / "data", "project-c").load().source_root == ""


def test_saving_requires_a_layout_with_main_project(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    environment = CodeEnvironment(tmp_path / "data", "project-a")
    with pytest.raises(ValueError, match="需包含主工程"):
        environment.save(EnvironmentWrite(source_root=str(empty), version=environment.version()))
    assert environment.load().source_root == ""


def test_legacy_global_environment_is_migrated_to_default_project(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    source = make_project(tmp_path / "source", "SampleApp")
    (data / "code-work.local.json").write_text(
        json.dumps({"source_root": str(source.parent), "timeout_seconds": 120}),
        encoding="utf-8",
    )

    migrate_legacy(data, "default-project")

    default = CodeEnvironment(data, "default-project").load()
    assert default.source_root == str(source.parent)
    assert default.timeout_seconds == 120
    assert default.project == "SampleApp"
    assert CodeEnvironment(data, "another-project").load().source_root == ""


def test_copy_and_edit_use_detected_project_name(services, tmp_path):
    paths, _, _, repository, *_ = services
    source = tmp_path / "generic-source"
    make_project(source, "SampleApp")
    service = CodeWork(paths, repository)
    service.environment.save(
        EnvironmentWrite(source_root=str(source), version=service.environment.version())
    )
    thread = repository.create_thread("通用项目")["id"]

    status = service.create(thread, desktop_flow=False)

    assert status["source_pinned"]
    folder = service.folder(thread) / "source"
    assert (folder / "SampleApp/SampleApp.csproj").is_file()
    assert "class Example {}" in service.read(thread, "SampleApp/Main/Example.cs")["content"]
    with pytest.raises(ValueError, match="只能修改主工程"):
        service.write(thread, "SampleApp/Program.cs", "changed", "")
