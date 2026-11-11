"""通用工作区：读写、补丁、快照还原、路径边界与命令审批。"""

import sys
import threading
import time
from pathlib import Path

import pytest

from app.core.config import Paths
from app.modules.workspace_work import commands
from app.modules.workspace_work.environment import WorkspaceSettings
from app.modules.workspace_work.service import WorkspaceWork


class Catalog:
    def get(self, thread_id, include_deleted=False):
        if thread_id != "thread-1":
            raise FileNotFoundError("对话不存在")
        return {"id": thread_id}


class Repository:
    project_id = "project-1"
    catalog = Catalog()


@pytest.fixture()
def area(tmp_path):
    paths = Paths(data_dir=tmp_path / "data")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "src").mkdir()
    (workspace / "src" / "a.cs").write_text("class A { int Value = 1; }\n", encoding="utf-8")
    work = WorkspaceWork(paths, Repository())
    work.environment.save(
        "project-1",
        WorkspaceSettings(root=str(workspace), auto_approve=True, version=""),
        paths.data,
    )
    return work, workspace


def test_read_write_diff_and_version_lock(area):
    work, workspace = area
    read = work.read("thread-1", "src/a.cs")
    assert read["content"].startswith("1: class A")
    assert read["line_count"] == 1

    written = work.write("thread-1", "src/a.cs", "class A { int Value = 2; }\n", read["version"])
    assert written["changed"] and written["revision"] == 1
    assert (workspace / "src" / "a.cs").read_text(encoding="utf-8").startswith("class A { int")

    diff = work.diff("thread-1", "src/a.cs")
    assert diff["additions"] == 1 and diff["deletions"] == 1
    assert "-class A { int Value = 1; }" in diff["diff"]

    with pytest.raises(ValueError, match="重新读取"):
        work.write("thread-1", "src/a.cs", "class A { int Value = 3; }\n", read["version"])

    status = work.status("thread-1")
    assert status["exists"] and status["file_count"] == 1
    assert status["additions"] == 1


def test_edit_requires_unique_match(area):
    work, workspace = area
    version = work.read("thread-1", "src/a.cs")["version"]
    with pytest.raises(ValueError, match="唯一匹配"):
        work.edit("thread-1", "src/a.cs", "missing", "x", version)
    result = work.edit("thread-1", "src/a.cs", "Value = 1", "Value = 9", version)
    assert result["changed"]
    assert "Value = 9" in (workspace / "src" / "a.cs").read_text(encoding="utf-8")


def test_new_file_and_restore_deletes_it(area):
    work, workspace = area
    created = work.write("thread-1", "src/new.cs", "class New { }\n", "")
    assert created["changed"]
    target = workspace / "src" / "new.cs"
    assert target.is_file()
    assert work.status("thread-1")["files"][0]["kind"] == "added"

    work.restore("thread-1", "src/new.cs")
    assert not target.exists()
    assert work.status("thread-1")["file_count"] == 0


def test_patch_is_atomic_and_rejects_stale_version(area):
    work, workspace = area
    first = work.read("thread-1", "src/a.cs")["version"]
    created = work.write("thread-1", "src/b.cs", "class B { }\n", "")
    edits = [
        {
            "path": "src/a.cs",
            "version": first,
            "old_text": "Value = 1",
            "new_text": "Value = 4",
        },
        {
            "path": "src/b.cs",
            "version": "stale",
            "old_text": "class B",
            "new_text": "class C",
        },
    ]
    with pytest.raises(ValueError, match="重新读取"):
        work.apply_patch("thread-1", edits)
    assert "Value = 1" in (workspace / "src" / "a.cs").read_text(encoding="utf-8")

    edits[1]["version"] = created["version"]
    result = work.apply_patch("thread-1", edits)
    assert [row["changed"] for row in result["files"]] == [True, True]
    assert "class C" in (workspace / "src" / "b.cs").read_text(encoding="utf-8")


def test_restore_all_returns_original_content(area):
    work, workspace = area
    version = work.read("thread-1", "src/a.cs")["version"]
    work.write("thread-1", "src/a.cs", "class A { int Value = 7; }\n", version)
    work.write("thread-1", "src/b.cs", "class B { }\n", "")
    status = work.restore("thread-1")
    assert status["file_count"] == 0
    assert (
        (workspace / "src" / "a.cs")
        .read_text(encoding="utf-8")
        .startswith("class A { int Value = 1")
    )
    assert not (workspace / "src" / "b.cs").exists()


def test_paths_outside_workspace_and_ignored_directories_are_rejected(area):
    work, _ = area
    for path in ("../outside.txt", "C:/Windows/win.ini", "node_modules/x.js", ".git/config"):
        with pytest.raises(ValueError):
            work.read("thread-1", path)
    with pytest.raises(ValueError):
        work.write("thread-1", "../escape.txt", "x", "")


def test_search_reports_line_numbers(area):
    work, _ = area
    result = work.search("thread-1", "value")
    assert result["matches"][0] == {
        "path": "src/a.cs",
        "line": 1,
        "text": "class A { int Value = 1; }",
    }


def test_command_whitelist_denies_unknown_and_runs_allowed(area):
    work, workspace = area
    with pytest.raises(commands.CommandDenied):
        work.run_command("thread-1", ["definitely-not-a-tool"])

    name = Path(sys.executable).name
    work.environment.save(
        "project-1",
        WorkspaceSettings(
            root=str(workspace),
            auto_approve=True,
            version=work.environment.version(),
            commands=[[name]],
        ),
        work.paths.data,
    )
    result = work.run_command("thread-1", [sys.executable, "-c", "print('ok')"])
    assert result["status"] == "passed" and "ok" in result["output"]
    assert work.status("thread-1")["commands"][-1]["status"] == "passed"


def test_command_requires_approval_and_records_decision(area):
    work, workspace = area
    name = Path(sys.executable).name
    work.environment.save(
        "project-1",
        WorkspaceSettings(
            root=str(workspace),
            auto_approve=False,
            approval_timeout_seconds=30,
            version=work.environment.version(),
            commands=[[name]],
        ),
        work.paths.data,
    )
    outcome = {}

    def run():
        outcome.update(work.run_command("thread-1", [sys.executable, "-c", "print('approved')"]))

    thread = threading.Thread(target=run)
    thread.start()
    for _ in range(100):
        pending = work.status("thread-1").get("approvals", [])
        if pending:
            break
        time.sleep(0.05)
    assert pending, "等待审批请求"
    work.decide_approval("thread-1", pending[0]["id"], "approve", {"id": "u1", "name": "admin"})
    thread.join(timeout=30)
    assert outcome["status"] == "passed" and "approved" in outcome["output"]


def test_command_denied_by_approval_does_not_run(area):
    work, workspace = area
    name = Path(sys.executable).name
    work.environment.save(
        "project-1",
        WorkspaceSettings(
            root=str(workspace),
            auto_approve=False,
            approval_timeout_seconds=30,
            version=work.environment.version(),
            commands=[[name]],
        ),
        work.paths.data,
    )
    outcome = {}

    def run():
        outcome.update(work.run_command("thread-1", [sys.executable, "-c", "print('nope')"]))

    thread = threading.Thread(target=run)
    thread.start()
    pending = []
    for _ in range(100):
        pending = work.status("thread-1").get("approvals", [])
        if pending:
            break
        time.sleep(0.05)
    work.decide_approval("thread-1", pending[0]["id"], "deny", {"id": "u1", "name": "admin"})
    thread.join(timeout=30)
    assert outcome["status"] == "denied" and "nope" not in outcome["output"]


def test_command_timeout_kills_process(area):
    work, workspace = area
    name = Path(sys.executable).name
    work.environment.save(
        "project-1",
        WorkspaceSettings(
            root=str(workspace),
            auto_approve=True,
            command_timeout_seconds=10,
            version=work.environment.version(),
            commands=[[name]],
        ),
        work.paths.data,
    )
    result = work.run_command(
        "thread-1", [sys.executable, "-c", "import time; time.sleep(5)"], timeout=1
    )
    assert result["status"] == "timeout" and result["timed_out"]
