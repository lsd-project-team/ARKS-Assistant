"""权限三档：迁移、只读命令、会话放行与审批范围。"""

import json
from types import SimpleNamespace

import pytest

from app.core.config import Paths
from app.modules.coding import service as coding_service
from app.modules.coding.service import CodingWorkspace


def make_workspace(tmp_path, **settings):
    root = tmp_path / "project"
    root.mkdir(parents=True, exist_ok=True)
    paths = Paths(tmp_path / "data", root)
    repository = SimpleNamespace(project_id="perm-project", workspace_id="perm-project")
    work = CodingWorkspace(paths, repository)
    if settings:
        work.save_settings(settings)
    return work, root


def write_legacy_settings(work, value):
    work.settings_path.parent.mkdir(parents=True, exist_ok=True)
    work.settings_path.write_text(json.dumps(value), encoding="utf-8")


def test_default_permission_is_workspace_write(tmp_path):
    work, _ = make_workspace(tmp_path)

    assert work.permission() == "workspace-write"
    assert work.settings()["approval_mode"] == "allowlist"
    assert work.settings()["permission"] == "workspace-write"


def test_legacy_settings_migrate_without_losing_behaviour(tmp_path):
    work, _ = make_workspace(tmp_path)
    write_legacy_settings(work, {"approval_mode": "full"})
    assert work.permission() == "full-access"

    write_legacy_settings(work, {"approval_mode": "allowlist"})
    assert work.permission() == "workspace-write"


def test_legacy_readonly_root_migrates_to_read_only(tmp_path, monkeypatch):
    work, root = make_workspace(tmp_path)
    monkeypatch.setattr(coding_service, "READONLY_ROOT", root.resolve())
    write_legacy_settings(work, {"approval_mode": "allowlist", "enabled": False})
    assert work.permission() == "read-only"

    write_legacy_settings(work, {"approval_mode": "allowlist", "enabled": True})
    assert work.permission() == "workspace-write"


def test_enabling_readonly_root_restores_workspace_write(tmp_path, monkeypatch):
    work, root = make_workspace(tmp_path)
    monkeypatch.setattr(coding_service, "READONLY_ROOT", root.resolve())
    write_legacy_settings(work, {"approval_mode": "allowlist", "enabled": False})
    assert work.permission() == "read-only"

    work.save_settings({"enabled": True})
    assert work.permission() == "workspace-write"
    assert work.writable()


def test_read_only_rejects_writes_and_write_commands(tmp_path):
    work, _ = make_workspace(tmp_path, permission="read-only")

    with pytest.raises(ValueError, match="仅可查看"):
        work.write_file("note.txt", "content")
    with pytest.raises(ValueError, match="仅可查看"):
        work.run_command("node -e 1")
    with pytest.raises(ValueError, match="仅可查看"):
        work.start_process("Start-Sleep -Seconds 5")
    # 只读档不能把命令转成审批，否则会变成绕过权限的入口。
    assert work.list_approvals() == []


def test_read_only_still_runs_lookups_and_blocks_chaining(tmp_path):
    work, _ = make_workspace(tmp_path, permission="read-only")

    assert work.executor.readonly_allowed("git status")
    assert not work.executor.readonly_allowed("git status; Remove-Item note.txt")
    assert not work.executor.readonly_allowed("node -e 1")
    # 目录不是 git 仓库时 git 自己会失败，但命令本身允许执行。
    assert work.run_command("git status")["exit_code"] in (0, 1, 128)


def test_dangerous_command_is_rejected_in_every_permission(tmp_path):
    for permission in ("read-only", "workspace-write", "full-access"):
        work, _ = make_workspace(tmp_path / permission, permission=permission)
        with pytest.raises(ValueError, match="危险命令"):
            work.run_command("rm -rf .")
        assert work.list_approvals() == []


def test_workspace_write_asks_for_unknown_and_full_access_does_not(tmp_path):
    limited, _ = make_workspace(tmp_path / "limited", permission="workspace-write")
    blocked = limited.run_command("Get-Location", wait=False)
    assert blocked["approval_required"]
    assert limited.list_approvals()

    opened, _ = make_workspace(tmp_path / "opened", permission="full-access")
    result = opened.run_command("Get-Location")
    assert result["exit_code"] == 0
    assert opened.list_approvals() == []


def test_session_scope_allows_the_same_command_again(tmp_path):
    work, _ = make_workspace(tmp_path, permission="workspace-write")
    pending = work.run_command("Get-Location", wait=False, thread_id="thread-1")

    decided = work.decide_approval(pending["approval"]["id"], True, "session")
    assert decided["status"] == "approved"
    assert decided["scope"] == "session"

    again = work.run_command("Get-Location", thread_id="thread-1")
    assert again["exit_code"] == 0
    assert not again.get("approval_required")
    assert work.list_approvals() == []

    # 不同命令、其他对话、切换权限后都要重新确认。
    assert work.run_command("Get-Date", wait=False, thread_id="thread-1")["approval_required"]
    assert work.run_command("Get-Location", wait=False, thread_id="thread-2")["approval_required"]

    work.save_settings({"permission": "full-access"})
    work.save_settings({"permission": "workspace-write"})
    assert work.run_command("Get-Location", wait=False, thread_id="thread-1")["approval_required"]


def test_switching_permission_cancels_pending_approvals(tmp_path):
    work, _ = make_workspace(tmp_path, permission="workspace-write")
    pending = work.run_command("Get-Location", wait=False)

    work.save_settings({"permission": "full-access"})

    assert work.list_approvals() == []
    assert work.approval(pending["approval"]["id"])["status"] == "cancelled"


def test_permission_switch_is_audited(tmp_path):
    work, _ = make_workspace(tmp_path)
    work.save_settings({"permission": "read-only"})

    rows = [row for row in work.list_audit() if row["action"] == "permission"]
    assert rows
    assert rows[0]["permission"] == "read-only"
    assert "workspace-write -> read-only" in rows[0]["command"]


def test_approval_scope_must_be_known(tmp_path):
    work, _ = make_workspace(tmp_path, permission="workspace-write")
    pending = work.run_command("Get-Location", wait=False)

    with pytest.raises(ValueError, match="once"):
        work.decide_approval(pending["approval"]["id"], True, "always")


def test_read_only_blocks_file_tools_but_hides_checkpoints(tmp_path):
    work, _ = make_workspace(tmp_path, permission="read-only")

    with pytest.raises(ValueError, match="仅可查看"):
        work.restore("deadbeef")
    assert work.checkpoints()["readonly"] is True
