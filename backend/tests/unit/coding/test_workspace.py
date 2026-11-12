"""原地编码工作区：文件、快照与命令的回归。"""

from types import SimpleNamespace

import pytest

from app.core.config import Paths
from app.modules.coding.executor import ApprovalRequired
from app.modules.coding.service import CodingWorkspace


def make_workspace(tmp_path, mode="full"):
    root = tmp_path / "project"
    root.mkdir()
    paths = Paths(tmp_path / "data", root)
    repository = SimpleNamespace(project_id="test-project", workspace_id="test-project")
    work = CodingWorkspace(paths, repository)
    work.save_settings({"approval_mode": mode})
    return work, root


def test_create_edit_move_and_delete_files(tmp_path):
    work, root = make_workspace(tmp_path)

    work.create_directory("src/pages")
    created = work.write_file("src/pages/index.html", "<h1>通信协议</h1>\n")
    assert created["created"] and (root / "src/pages/index.html").is_file()

    read = work.read_file("src/pages/index.html")
    assert "通信协议" in read["content"] and read["version"] == created["version"]

    with pytest.raises(ValueError, match="必须带上"):
        work.write_file("src/pages/index.html", "overwrite without hash")

    work.write_file("src/pages/index.html", "<h1>协议配置</h1>\n", read["version"])
    work.move_path("src/pages/index.html", "src/config.html")
    assert not (root / "src/pages/index.html").exists()
    assert (root / "src/config.html").is_file()

    work.delete_path("src", recursive=True)
    assert not (root / "src").exists()


def test_paths_cannot_escape_project_root(tmp_path):
    work, _ = make_workspace(tmp_path)
    for path in ("../outside.txt", "C:/Windows/win.ini"):
        with pytest.raises(ValueError):
            work.write_file(path, "x")


def test_checkpoint_and_restore_file(tmp_path):
    work, root = make_workspace(tmp_path)
    target = root / "Program.cs"
    target.write_text("class A {}", encoding="utf-8")

    baseline = work.checkpoint("baseline")["commit"]
    version = work.read_file("Program.cs")["version"]
    work.write_file("Program.cs", "class B {}", version)
    assert "class B" in target.read_text(encoding="utf-8")

    work.restore(baseline, ["Program.cs"])
    assert "class A" in target.read_text(encoding="utf-8")


def test_restore_removes_files_added_after_checkpoint(tmp_path):
    work, root = make_workspace(tmp_path)
    (root / "keep.txt").write_text("keep", encoding="utf-8")
    commit = work.checkpoint("base")["commit"]

    (root / "added.txt").write_text("added", encoding="utf-8")
    (root / "keep.txt").write_text("changed", encoding="utf-8")

    work.restore(commit)

    assert not (root / "added.txt").exists()
    assert (root / "keep.txt").read_text(encoding="utf-8") == "keep"


def test_command_runs_in_project_and_reports_output(tmp_path):
    work, root = make_workspace(tmp_path)
    work.write_file("hello.txt", "hello")

    result = work.run_command("Get-Content hello.txt")

    assert result["exit_code"] == 0
    assert "hello" in result["output"]
    assert (root / "hello.txt").is_file()


def test_allowlist_requires_confirmation_for_unknown_command(tmp_path):
    work, _ = make_workspace(tmp_path, mode="allowlist")

    with pytest.raises(ApprovalRequired):
        work.run_command("Remove-Item important.txt")

    safe = work.run_command("dotnet --version")
    assert safe["exit_code"] == 0


def test_background_process_can_be_read_and_stopped(tmp_path):
    work, _ = make_workspace(tmp_path)

    job = work.start_process("Start-Sleep -Seconds 30")
    assert job["job_id"]
    running = work.read_process(job["job_id"])
    assert running["running"] is True

    work.stop_process(job["job_id"])
    with pytest.raises(FileNotFoundError):
        work.read_process(job["job_id"])
