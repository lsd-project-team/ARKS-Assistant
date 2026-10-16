"""临时 SQLite、真实子进程与 Git 验证需求到交付及保留期的业务边界。"""

import asyncio
import io
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zipfile import ZipFile

import pytest
from sqlalchemy import func, select

from app.modules.code_changes import CodeChanges
from app.modules.code_changes.delivery import delivery_package, review_change
from app.modules.code_changes.maintenance import cleanup
from app.modules.code_changes.models import CodeChangeRecord, VerificationRecord


@pytest.fixture
def delivery_changes(services):
    paths, database, workspace, *_ = services
    service = CodeChanges(paths, database, workspace, "delivery-project")
    set_policy(service, min_free_mb=0)
    yield service
    for task in list(service._tasks.values()):
        task.cancel.set()
    for task in list(service._tasks.values()):
        if task.thread:
            task.thread.join(timeout=12)
            assert not task.thread.is_alive(), "测试验证进程未清理"


def set_policy(service, **overrides):
    return service.policy.save({**service.policy.get().model_dump(), **overrides})


def create_change(service, **details):
    return service.create(
        "修改入口",
        "隔离修改后提供可核对的交付包",
        **{"acceptance_criteria": ["原件保持不变", "入口名称为 Start"], **details},
    )


def edit_entry(service, change, before="Main", after="Start"):
    source = service.read_file(change["id"], "Program.cs")
    return service.edit_file(change["id"], "Program.cs", before, after, source["version"])


def copy_directory(service, identifier):
    # 只用于模拟外部副本变更和核对原版快照，不伪造验证状态或审核结果。
    with service.database.session() as session:
        row = session.get(CodeChangeRecord, identifier)
        return service._folder(row)


def host_profile(service, program="print('verified-copy')", *, baseline_required=False):
    return service.save_profile(
        "明确可信的测试 Python",
        [sys.executable, "-c", program],
        5,
        executor={"kind": "trusted_host"},
        baseline_required=baseline_required,
        category="test",
        environment_label="临时测试宿主；非沙箱",
    )


async def verify_complete(service, change, profile, purpose="change"):
    service.verify(change["id"], profile["id"], purpose)
    result = await service.wait(change["id"], timeout_seconds=10)
    verification = result["latest_verification"]
    assert verification["status"] != "running"
    assert verification["purpose"] == purpose
    assert verification["executor"]["kind"] == "trusted_host"
    return result


async def approved_host_change(service, **details):
    set_policy(service, require_sandbox_delivery=False)
    change = edit_entry(service, create_change(service, **details))
    result = await verify_complete(service, change, host_profile(service))
    assert result["status"] == "passed"
    reviewed = review_change(service, change["id"], result["change_version"], "核对差异", "tester")
    assert reviewed["review"]["change_version"] == result["change_version"]
    return reviewed


def test_requirements_round_trip_and_scope_rejection_preserve_original(delivery_changes):
    service = delivery_changes
    original = (service.workspace.root / "Program.cs").read_bytes()
    change = create_change(
        service,
        acceptance_criteria=["  入口名称为 Start  ", "入口名称为 Start", " "],
        constraints="保留编码和换行",
        allowed_paths=["Program.cs", r"src\**\*.cs"],
    )
    reopened = CodeChanges(service.paths, service.database, service.workspace, service.project_id)
    result = reopened.get(change["id"])
    assert result["acceptance_criteria"] == ["入口名称为 Start"]
    assert result["constraints"] == "保留编码和换行"
    assert result["allowed_paths"] == ["Program.cs", "src/**/*.cs"]
    edited = edit_entry(service, change)
    with pytest.raises(ValueError, match="修改范围"):
        service.edit_file(change["id"], "outside.txt", "", "not allowed", "")
    assert not (copy_directory(service, change["id"]) / "work" / "outside.txt").exists()
    assert service.diff(change["id"])["scope_conflicts"] == []
    assert edited["change_version"] != change["change_version"]
    assert (service.workspace.root / "Program.cs").read_bytes() == original


@pytest.mark.parametrize(
    "scope", ["../outside.cs", "/outside.cs", "C:/outside.cs", "a/../x", "x\x00"]
)
def test_invalid_requirement_scope_is_rejected_before_copy(delivery_changes, scope):
    service = delivery_changes
    with pytest.raises(ValueError):
        create_change(service, allowed_paths=[scope])
    assert service.list() == []
    assert not service.storage.exists()


async def test_missing_acceptance_blocks_review_but_keeps_draft_export(delivery_changes):
    service = delivery_changes
    set_policy(service, require_sandbox_delivery=False)
    change = edit_entry(service, create_change(service, acceptance_criteria=[]))
    result = await verify_complete(service, change, host_profile(service))
    assert result["status"] == "passed"
    with pytest.raises(ValueError, match="验收标准"):
        review_change(service, change["id"], result["change_version"], "", "tester")
    assert service.get(change["id"])["review"] is None
    assert "+ static void Start()" in service.export(change["id"])
    with pytest.raises(ValueError, match="验收标准"):
        delivery_package(service, change["id"])


async def test_out_of_scope_external_edit_never_launches_verification(delivery_changes, tmp_path):
    service = delivery_changes
    change = create_change(service, allowed_paths=["Program.cs"])
    work = copy_directory(service, change["id"]) / "work"
    (work / "outside.txt").write_text("unapproved", encoding="utf-8")
    marker = tmp_path / "must-not-run.txt"
    profile = host_profile(
        service, f"from pathlib import Path; Path({str(marker)!r}).write_text('ran')"
    )
    assert service.diff(change["id"])["scope_conflicts"] == ["outside.txt"]
    with pytest.raises(ValueError, match="范围"):
        service.verify(change["id"], profile["id"])
    assert not marker.exists()
    assert service.get(change["id"])["latest_verification"] is None


async def test_baseline_reads_original_in_disposable_clone_and_keeps_work_edit(delivery_changes):
    service = delivery_changes
    change = edit_entry(service, create_change(service))
    folder = copy_directory(service, change["id"])
    original = (service.workspace.root / "Program.cs").read_bytes()
    edited = (folder / "work" / "Program.cs").read_bytes()
    profile = host_profile(
        service,
        "from pathlib import Path; p=Path('Program.cs'); "
        "assert 'Main' in p.read_text(); print('original-only'); "
        "print('BASELINE_DIR:' + str(Path.cwd()))",
        baseline_required=True,
    )
    result = await verify_complete(service, change, profile, "baseline")
    assert result["status"] == "editing"
    assert result["latest_verification"]["status"] == "passed", result["latest_verification"]
    assert "original-only" in result["latest_verification"]["output"]
    assert result["latest_verification"]["stale"] is False
    assert (folder / "base" / "Program.cs").read_bytes() == original
    assert (service.workspace.root / "Program.cs").read_bytes() == original
    assert (folder / "work" / "Program.cs").read_bytes() == edited
    temporary = Path(
        result["latest_verification"]["output"].split("BASELINE_DIR:")[1].splitlines()[0]
    )
    assert temporary.parent == folder and temporary.name not in {"base", "work", "logs"}
    assert not await asyncio.to_thread(temporary.exists)
    with pytest.raises(ValueError, match="尚未验证通过"):
        review_change(service, change["id"], result["change_version"], "", "tester")


async def test_baseline_command_modifying_source_fails_without_touching_base(delivery_changes):
    service = delivery_changes
    change = create_change(service)
    original = (service.workspace.root / "Program.cs").read_bytes()
    folder = copy_directory(service, change["id"])
    profile = host_profile(
        service, "from pathlib import Path; Path('Program.cs').write_text('bad')"
    )
    result = await verify_complete(service, change, profile, "baseline")
    assert result["status"] == "ready"
    assert result["latest_verification"]["status"] == "failed"
    assert result["latest_verification"]["exit_code"] == 0
    assert "基线命令修改" in result["latest_verification"]["error"]
    assert result["latest_verification"]["error_category"] == "environment_or_baseline"
    assert (folder / "base" / "Program.cs").read_bytes() == original
    assert (folder / "work" / "Program.cs").read_bytes() == original
    assert (service.workspace.root / "Program.cs").read_bytes() == original
    assert not (folder / "baseline").exists()


async def test_required_baseline_is_independent_of_changed_work_version(delivery_changes):
    service = delivery_changes
    set_policy(service, require_sandbox_delivery=False)
    change = edit_entry(service, create_change(service))
    profile = host_profile(service, baseline_required=True)
    passed = await verify_complete(service, change, profile)
    with pytest.raises(ValueError, match="基线"):
        review_change(service, change["id"], passed["change_version"], "", "tester")
    baseline = await verify_complete(service, change, profile, "baseline")
    baseline_id = baseline["latest_verification"]["id"]
    change = edit_entry(service, change, "Start", "StartAgain")
    passed = await verify_complete(service, change, profile)
    review = review_change(
        service, change["id"], passed["change_version"], "已有原版验证", "tester"
    )
    assert review["review"]["verification_id"] == passed["latest_verification"]["id"]
    history = service.verification_history(change["id"])["verifications"]
    original_proof = next(item for item in history if item["id"] == baseline_id)
    assert original_proof["purpose"] == "baseline" and original_proof["stale"] is False
    assert original_proof["change_version"] != review["change_version"]
    with ZipFile(io.BytesIO(delivery_package(service, change["id"]))) as archive:
        manifest = json.loads(archive.read("manifest.json"))
    assert manifest["baseline"]["id"] == baseline_id
    assert manifest["baseline"]["status"] == "passed"
    assert manifest["baseline"]["purpose"] == "baseline"
    assert manifest["baseline"]["source_version"] == manifest["source_version"]
    assert manifest["verification"]["id"] == passed["latest_verification"]["id"]


async def test_profile_command_change_invalidates_old_baseline(delivery_changes):
    service = delivery_changes
    set_policy(service, require_sandbox_delivery=False)
    change = edit_entry(service, create_change(service))
    profile = host_profile(service, baseline_required=True)
    baseline = await verify_complete(service, change, profile, "baseline")
    assert baseline["latest_verification"]["status"] == "passed", baseline["latest_verification"]
    profile = service.save_profile(
        profile["name"],
        [sys.executable, "-c", "print('new environment')"],
        5,
        identifier=profile["id"],
        executor={"kind": "trusted_host"},
        baseline_required=True,
        category="test",
    )
    passed = await verify_complete(service, change, profile)
    with pytest.raises(ValueError, match="基线"):
        review_change(service, change["id"], passed["change_version"], "", "tester")
    assert service.get(change["id"])["review"] is None
    history = service.verification_history(change["id"])["verifications"]
    assert next(item for item in history if item["id"] == baseline["latest_verification"]["id"])[
        "stale"
    ]


async def test_sandbox_delivery_default_rejects_real_trusted_host_result(delivery_changes):
    service = delivery_changes
    assert service.policy.get().require_sandbox_delivery is True
    change = edit_entry(service, create_change(service))
    passed = await verify_complete(service, change, host_profile(service))
    assert passed["status"] == "passed" and passed["latest_verification"]["exit_code"] == 0
    with pytest.raises(ValueError, match="沙箱"):
        review_change(service, change["id"], passed["change_version"], "", "tester")
    set_policy(service, require_sandbox_delivery=False)
    review_change(service, change["id"], passed["change_version"], "显式接受可信宿主", "tester")
    assert delivery_package(service, change["id"]).startswith(b"PK")
    set_policy(service, require_sandbox_delivery=True)
    with pytest.raises(ValueError, match="沙箱"):
        delivery_package(service, change["id"])


async def test_new_edit_and_revalidation_cannot_reuse_old_review(delivery_changes):
    service = delivery_changes
    reviewed = await approved_host_change(service)
    old_version = reviewed["change_version"]
    change = edit_entry(service, reviewed, "Start", "StartAgain")
    assert change["review"] is None and change["delivered_at"] is None
    assert change["change_version"] != old_version
    passed = await verify_complete(service, change, host_profile(service))
    with pytest.raises(ValueError, match="版本已变化"):
        review_change(service, change["id"], old_version, "旧界面仍打开", "tester")
    with pytest.raises(ValueError, match="尚未审核"):
        delivery_package(service, change["id"])
    assert service.get(change["id"])["review"] is None
    reviewed = review_change(
        service, change["id"], passed["change_version"], "核对新差异", "tester"
    )
    assert reviewed["review"]["change_version"] != old_version
    assert delivery_package(service, change["id"]).startswith(b"PK")


async def test_changed_profile_or_original_blocks_existing_review_delivery(delivery_changes):
    service = delivery_changes
    reviewed = await approved_host_change(service)
    profile = service.profiles()[0]
    service.save_profile(
        profile["name"],
        [sys.executable, "-c", "print('changed check')"],
        5,
        identifier=profile["id"],
        executor={"kind": "trusted_host"},
        category="test",
    )
    refreshed = service.get(reviewed["id"])
    assert refreshed["latest_verification"]["stale"] is True
    assert refreshed["review"] is None
    with pytest.raises(ValueError, match="环境或命令已变化"):
        delivery_package(service, reviewed["id"])
    original = service.workspace.root / "Program.cs"
    original.write_text("external update", encoding="utf-8")
    with pytest.raises(ValueError, match="原件已变化"):
        delivery_package(service, reviewed["id"])
    assert original.read_text(encoding="utf-8") == "external update"


async def test_review_delivery_and_policy_are_isolated_by_project(delivery_changes):
    service = delivery_changes
    reviewed = await approved_host_change(service)
    other = CodeChanges(service.paths, service.database, service.workspace, "other-project")
    assert service.policy.get().require_sandbox_delivery is False
    assert other.policy.get().require_sandbox_delivery is True
    with pytest.raises(FileNotFoundError):
        review_change(other, reviewed["id"], reviewed["change_version"], "越权审核", "tester")
    with pytest.raises(FileNotFoundError):
        delivery_package(other, reviewed["id"])
    assert other.list() == [] and other.profiles() == []
    assert service.get(reviewed["id"])["review"] == reviewed["review"]


async def test_delivery_zip_patch_really_applies_and_reverses(delivery_changes, tmp_path):
    service = delivery_changes
    git = shutil.which("git")
    if not git:
        pytest.skip("真实补丁应用与反向回退需要 Git")
    (service.workspace.root / "remove.txt").write_bytes(b"remove me\n")
    (service.workspace.root / "binary.dat").write_bytes(b"\x00before\xff")
    original = {path.name: path.read_bytes() for path in service.workspace.root.iterdir()}
    set_policy(service, require_sandbox_delivery=False)
    change = edit_entry(service, create_change(service, constraints="不修改原目录"))
    service.edit_file(change["id"], "new.txt", "", "new text\n", "")
    work = copy_directory(service, change["id"]) / "work"
    (work / "remove.txt").unlink()
    (work / "binary.dat").write_bytes(b"\x00after\xfe")
    passed = await verify_complete(service, change, host_profile(service))
    with pytest.raises(ValueError, match="尚未审核"):
        delivery_package(service, change["id"])
    review_change(service, change["id"], passed["change_version"], "人工核对", "tester")
    with ZipFile(io.BytesIO(delivery_package(service, change["id"]))) as archive:
        assert set(archive.namelist()) == {"changes.patch", "manifest.json", "README.md"}
        manifest = json.loads(archive.read("manifest.json"))
        patch = archive.read("changes.patch")
        assert "git apply --reverse" in archive.read("README.md").decode()
    assert manifest["project_id"] == service.project_id
    assert manifest["change_id"] == change["id"]
    assert (
        manifest["change_version"]
        == manifest["review"]["change_version"]
        == passed["change_version"]
    )
    assert manifest["verification_id"] == passed["latest_verification"]["id"]
    assert manifest["source_version"] == passed["latest_verification"]["source_version"]
    assert manifest["acceptance_criteria"] == change["acceptance_criteria"]
    assert manifest["constraints"] == "不修改原目录"
    assert manifest["profile"]["executor"]["kind"] == "trusted_host"
    assert manifest["baseline"] is None
    safe_metadata = {
        "id",
        "status",
        "exit_code",
        "purpose",
        "change_version",
        "source_version",
        "profile_version",
        "executor",
        "started_at",
        "ended_at",
    }
    assert manifest["verification"] == {
        key: passed["latest_verification"][key] for key in safe_metadata
    }
    target = tmp_path / "apply-target"
    shutil.copytree(service.workspace.root, target)
    expected = {path.name: path.read_bytes() for path in work.iterdir()}
    for options in (["--check"], [], ["--reverse", "--check"], ["--reverse"]):
        result = await asyncio.to_thread(
            subprocess.run,
            [git, "-c", "core.autocrlf=false", "apply", *options, "-"],
            input=patch,
            cwd=target,
            capture_output=True,
            check=False,
            timeout=10,
        )
        assert result.returncode == 0, result.stderr.decode(errors="replace")
        if not options:
            assert {path.name: path.read_bytes() for path in target.iterdir()} == expected
    assert {path.name: path.read_bytes() for path in target.iterdir()} == original
    assert {path.name: path.read_bytes() for path in service.workspace.root.iterdir()} == original
    assert service.get(change["id"])["delivered_at"] is not None


def set_completed_at(service, identifier, instant, *, delivered=False):
    with service.database.session.begin() as session:
        row = session.get(CodeChangeRecord, identifier)
        row.updated_at = instant.isoformat()
        if delivered:
            row.delivered_at = instant.isoformat()


async def test_retention_preview_and_cleanup_only_expired_completed_project_files(delivery_changes):
    service = delivery_changes
    now = datetime(2030, 6, 30, 12, tzinfo=UTC)
    expired = now - timedelta(days=31)
    set_policy(service, retention_days=30)
    delivered = await approved_host_change(service)
    delivery_package(service, delivered["id"])
    set_completed_at(service, delivered["id"], expired, delivered=True)
    discarded = create_change(service)
    service.discard(discarded["id"])
    set_completed_at(service, discarded["id"], expired)
    pending = edit_entry(service, create_change(service))
    set_completed_at(service, pending["id"], expired)
    recent = create_change(service)
    service.discard(recent["id"])
    set_completed_at(service, recent["id"], now - timedelta(days=29))
    other = CodeChanges(service.paths, service.database, service.workspace, "other-project")
    set_policy(other, min_free_mb=0)
    foreign = create_change(other)
    other.discard(foreign["id"])
    set_completed_at(other, foreign["id"], expired)
    folders = {
        item["id"]: copy_directory(service, item["id"])
        for item in (delivered, discarded, pending, recent)
    }
    foreign_folder = copy_directory(other, foreign["id"])
    with service.database.session() as session:
        record_count = session.scalar(select(func.count()).select_from(CodeChangeRecord))
        verification_count = session.scalar(select(func.count()).select_from(VerificationRecord))
    preview = cleanup(service, True, now=now)
    assert preview["eligible"] == 2 and preview["removed"] == 0 and preview["skipped"] == 2
    assert preview["bytes"] > 0
    assert all(folder.exists() for folder in folders.values()) and foreign_folder.exists()
    result = cleanup(service, False, now=now)
    assert result == {**preview, "removed": 2}
    assert not folders[delivered["id"]].exists() and not folders[discarded["id"]].exists()
    assert (
        folders[pending["id"]].exists()
        and folders[recent["id"]].exists()
        and foreign_folder.exists()
    )
    saved = service.get(delivered["id"])
    assert saved["status"] == "discarded" and saved["review"] == delivered["review"]
    assert saved["acceptance_criteria"] == delivered["acceptance_criteria"]
    assert service.verification_history(delivered["id"])["verifications"][0]["status"] == "passed"
    with service.database.session() as session:
        assert session.scalar(select(func.count()).select_from(CodeChangeRecord)) == record_count
        assert (
            session.scalar(select(func.count()).select_from(VerificationRecord))
            == verification_count
        )
    assert cleanup(service, False, now=now)["removed"] == 0


async def test_retention_preserves_external_edit_after_old_delivery(delivery_changes):
    service = delivery_changes
    now = datetime(2030, 6, 30, 12, tzinfo=UTC)
    reviewed = await approved_host_change(service)
    delivery_package(service, reviewed["id"])
    set_completed_at(service, reviewed["id"], now - timedelta(days=31), delivered=True)
    work = copy_directory(service, reviewed["id"]) / "work"
    changed = b"new work after delivered version\n"
    (work / "Program.cs").write_bytes(changed)
    result = cleanup(service, False, now=now)
    assert result["removed"] == 0
    assert (work / "Program.cs").read_bytes() == changed
    current = service.get(reviewed["id"])
    assert current["change_version"] != reviewed["change_version"]
    assert current["review"] is None and current["delivered_at"] is None


async def test_retention_keeps_active_verification_even_with_expired_delivery(delivery_changes):
    service = delivery_changes
    now = datetime(2030, 6, 30, 12, tzinfo=UTC)
    reviewed = await approved_host_change(service)
    delivery_package(service, reviewed["id"])
    profile = host_profile(service, "import time; print('active', flush=True); time.sleep(30)")
    service.verify(reviewed["id"], profile["id"])
    set_completed_at(service, reviewed["id"], now - timedelta(days=31), delivered=True)
    folder = copy_directory(service, reviewed["id"])
    try:
        result = cleanup(service, False, now=now)
        assert result == {"eligible": 0, "removed": 0, "bytes": 0, "skipped": 1}
        assert folder.exists()
        assert service.get(reviewed["id"])["status"] == "verifying"
    finally:
        service.cancel(reviewed["id"])
        cancelled = await service.wait(reviewed["id"], timeout_seconds=10)
    assert cancelled["latest_verification"]["status"] == "cancelled"
    assert folder.exists()


@pytest.mark.parametrize("days", [29, 30, 31])
def test_retention_boundary_uses_completion_time_not_creation(delivery_changes, days):
    service = delivery_changes
    now = datetime(2030, 6, 30, 12, tzinfo=UTC)
    change = create_change(service)
    service.discard(change["id"])
    set_completed_at(service, change["id"], now - timedelta(days=days))
    folder = copy_directory(service, change["id"])
    result = cleanup(service, True, now=now)
    assert result["eligible"] == int(days > 30)
    assert result["removed"] == 0 and folder.exists()
