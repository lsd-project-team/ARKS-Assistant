"""原地编码工作区：文件、快照与命令的回归。"""

import base64
import codecs
import time
from threading import Thread
from types import SimpleNamespace

import pytest

from app.core.config import Paths
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

    blocked = work.run_command("Remove-Item important.txt", wait=False)
    assert blocked["approval_required"]
    assert work.list_approvals()

    safe = work.run_command("dotnet --version")
    assert safe["exit_code"] == 0


def test_unknown_command_can_be_approved_and_executed(tmp_path):
    work, _ = make_workspace(tmp_path, mode="allowlist")
    request = work.request_approval("Get-Location")
    assert [row["id"] for row in work.list_approvals()] == [request["id"]]

    done = work.decide_approval(request["id"], True)

    assert done["status"] == "approved"
    assert done["result"]["exit_code"] == 0
    assert work.list_approvals() == []


def test_rejected_approval_does_not_run_command(tmp_path):
    work, _ = make_workspace(tmp_path, mode="allowlist")
    request = work.request_approval("Get-Location")

    rejected = work.decide_approval(request["id"], False)

    assert rejected["status"] == "rejected"
    assert rejected["result"]["ok"] is False


def test_waiting_command_continues_after_approval(tmp_path):
    work, _ = make_workspace(tmp_path, mode="allowlist")
    events, result = [], {}

    def execute():
        result["value"] = work.run_command(
            "Get-Location",
            wait=True,
            emit=lambda kind, payload: events.append((kind, payload)),
        )

    worker = Thread(target=execute, daemon=True)
    worker.start()
    for _ in range(100):
        pending = work.list_approvals()
        if pending:
            break
        time.sleep(0.05)
    assert pending
    approval = pending[0]
    work.decide_approval(approval["id"], True)
    worker.join(20)

    assert not worker.is_alive()
    assert result["value"]["exit_code"] == 0
    assert any(
        kind == "coding_approval" and payload["status"] == "approved" for kind, payload in events
    )


def test_rejected_waiting_command_reports_status(tmp_path):
    work, _ = make_workspace(tmp_path, mode="allowlist")
    result = {}

    def execute():
        result["value"] = work.run_command("Get-Location", wait=True)

    worker = Thread(target=execute, daemon=True)
    worker.start()
    for _ in range(100):
        pending = work.list_approvals()
        if pending:
            break
        time.sleep(0.05)
    work.decide_approval(pending[0]["id"], False)
    worker.join(20)

    assert result["value"]["approval_status"] == "rejected"
    assert result["value"]["approved"] is False


def test_command_output_streams_to_events(tmp_path):
    work, _ = make_workspace(tmp_path)
    events = []
    work.run_command(
        "Write-Output streamed-line",
        emit=lambda kind, payload: events.append((kind, payload)),
    )

    outputs = [payload for kind, payload in events if kind == "coding_output"]
    assert outputs and "streamed-line" in "".join(row["chunk"] for row in outputs)


def test_edit_file_keeps_original_encoding_and_newlines(tmp_path):
    work, root = make_workspace(tmp_path)
    target = root / "legacy.txt"
    target.write_bytes("中文说明\r\n第二行\r\n".encode("gb18030"))

    read = work.read_file("legacy.txt")
    work.edit_file(
        "legacy.txt",
        [{"old": "第二行", "new": "新的第二行"}],
        read["version"],
    )

    data = target.read_bytes()
    assert not data.startswith(codecs.BOM_UTF8)
    assert b"\r\n" in data
    assert data.decode("gb18030") == "中文说明\r\n新的第二行\r\n"


def test_edit_file_preserves_utf8_bom(tmp_path):
    work, root = make_workspace(tmp_path)
    target = root / "bom.txt"
    target.write_bytes(codecs.BOM_UTF8 + "第一行\r\n第二行\r\n".encode())

    read = work.read_file("bom.txt")
    work.edit_file("bom.txt", [{"old": "第二行", "new": "改后"}], read["version"])

    data = target.read_bytes()
    assert data.startswith(codecs.BOM_UTF8)
    assert b"\r\n" in data
    assert data.decode("utf-8-sig") == "第一行\r\n改后\r\n"


def test_edit_requires_hash_and_unique_match(tmp_path):
    work, root = make_workspace(tmp_path)
    work.write_file("notes.txt", "alpha\nbeta\nalpha\n")
    read = work.read_file("notes.txt")

    with pytest.raises(ValueError, match="必须带上"):
        work.edit_file("notes.txt", [{"old": "alpha", "new": "gamma"}])
    with pytest.raises(ValueError, match="匹配到"):
        work.edit_file("notes.txt", [{"old": "alpha", "new": "gamma"}], read["version"])

    work.edit_file(
        "notes.txt",
        [{"old": "alpha", "new": "gamma", "replace_all": True}],
        read["version"],
    )
    assert (root / "notes.txt").read_text(encoding="utf-8") == "gamma\nbeta\ngamma\n"


def test_write_binary_creates_asset(tmp_path):
    work, root = make_workspace(tmp_path)
    payload = base64.b64encode(b"\x89PNG\r\n\x1a\n").decode()

    created = work.write_binary("assets/icon.png", payload)

    assert created["created"]
    assert (root / "assets/icon.png").read_bytes() == b"\x89PNG\r\n\x1a\n"


def test_search_and_find_files(tmp_path):
    work, root = make_workspace(tmp_path)
    work.write_file("src/app.py", "def handler():\n    return 'needle'\n")
    work.write_file("src/helper.py", "needle\nneedle\n")
    work.write_file("docs/readme.md", "no match here\n")

    found = work.search_files("needle")
    paths = {row["path"] for row in found["results"]}
    assert {"src/app.py", "src/helper.py"} <= paths
    assert sum(1 for row in found["results"] if row["path"] == "src/helper.py") == 2

    files = work.find_files("*.py")
    assert {"src/app.py", "src/helper.py"} <= set(files["entries"])
    assert "docs/readme.md" not in files["entries"]


def test_command_classification_separates_outside_project_writes(tmp_path):
    work, root = make_workspace(tmp_path)
    outside = str(tmp_path / "outside")
    assert work.executor.classify(f"Remove-Item {outside} -Recurse -Force") == "dangerous"
    assert work.executor.classify("Remove-Item %TEMP% -Recurse") == "dangerous"
    assert work.executor.classify("Remove-Item src -Recurse") == "unknown"
    assert work.executor.classify("dotnet build") == "safe"


def test_destructive_command_is_snapshotted_before_execution(tmp_path):
    work, root = make_workspace(tmp_path)
    work.snapshots.ensure()
    work.write_file("keep.txt", "v1")
    assert work.snapshots.has_changes()

    work.run_command("Remove-Item keep.txt")
    assert not (root / "keep.txt").exists()

    points = work.checkpoints()["checkpoints"]
    before = next(row["commit"] for row in points if row["label"] == "before-command")
    work.restore(before)
    assert (root / "keep.txt").read_text(encoding="utf-8") == "v1"


def test_detects_project_commands_and_respects_overrides(tmp_path):
    work, root = make_workspace(tmp_path)
    (root / "Demo.sln").write_text("", encoding="utf-8")

    environment = work.environment()
    assert environment["language"] == ".NET"
    assert environment["build_command"] == "dotnet build"
    assert environment["test_command"] == "dotnet test"

    work.save_settings({"build_command": "dotnet build Demo.sln"})
    assert work.environment()["build_command"] == "dotnet build Demo.sln"


def test_without_git_files_still_work_and_snapshots_degrade(tmp_path, monkeypatch):
    work, root = make_workspace(tmp_path)
    monkeypatch.setattr("app.modules.coding.snapshots.shutil.which", lambda name: None)

    created = work.write_file("note.txt", "still editable")
    assert created["created"]
    assert (root / "note.txt").read_text(encoding="utf-8") == "still editable"
    assert work.snapshots.available() is False
    assert work.begin_run("run-no-git") in (None, "")


def test_readonly_project_blocks_restore_and_snapshot_creation(tmp_path, monkeypatch):
    work, root = make_workspace(tmp_path)
    work.snapshots.ensure()
    commit = work.snapshots.checkpoint("baseline")
    monkeypatch.setattr("app.modules.coding.service.READONLY_ROOT", root.resolve())

    with pytest.raises(ValueError, match="只读"):
        work.restore(commit)
    with pytest.raises(ValueError, match="只读"):
        work.checkpoint("manual")
    assert work.checkpoints()["readonly"] is True


def test_default_analysis_root_stays_read_only_until_enabled(tmp_path, monkeypatch):
    work, root = make_workspace(tmp_path)
    monkeypatch.setattr("app.modules.coding.service.READONLY_ROOT", root.resolve())

    with pytest.raises(ValueError, match="只读"):
        work.write_file("new.txt", "content")

    work.save_settings({"enabled": True})
    assert work.write_file("new.txt", "content")["created"]


def test_background_process_can_be_read_and_stopped(tmp_path):
    work, _ = make_workspace(tmp_path)

    job = work.start_process("Start-Sleep -Seconds 30")
    assert job["job_id"]
    running = work.read_process(job["job_id"])
    assert running["running"] is True

    work.stop_process(job["job_id"])
    with pytest.raises(FileNotFoundError):
        work.read_process(job["job_id"])
    rows = work.list_jobs()["jobs"]
    assert any(row["job_id"] == job["job_id"] and row["status"] == "stopped" for row in rows)

    restored = CodingWorkspace(
        Paths(work.data, work.root),
        SimpleNamespace(project_id=work.project_id, workspace_id=work.project_id),
    )
    assert any(
        row["job_id"] == job["job_id"] and row["status"] == "stopped"
        for row in restored.list_jobs()["jobs"]
    )
    restored.executor.stop_all()


def test_read_image_validates_bytes_path_and_limits(tmp_path):
    from tests.helpers.chat_attachments import image_bytes

    work, root = make_workspace(tmp_path)
    shots = root / "shots"
    shots.mkdir()
    png = image_bytes((120, 80))
    (shots / "app.png").write_bytes(png)
    result = work.read_image("shots/app.png")
    assert result["format"] == "PNG"
    assert (result["width"], result["height"]) == (120, 80)
    assert result["data"] == png
    with pytest.raises(FileNotFoundError):
        work.read_image("shots/missing.png")
    (shots / "note.txt").write_bytes(b"not an image")
    with pytest.raises(ValueError):
        work.read_image("shots/note.txt")
    with pytest.raises(ValueError):
        work.read_image("../outside.png")
