"""真实在线备份与异地恢复保留代码工作身份、预算及隔离副本。"""

import asyncio
import io
import json
import os
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select, text

from app.core.config import PROJECT_ROOT, Paths
from app.infrastructure.database.session import Database
from app.infrastructure.storage.backup import create_backup
from app.infrastructure.storage.paths import io_path
from app.infrastructure.storage.restore import restore_backup
from app.infrastructure.storage.validation import checked_backup
from app.modules.code_changes import CodeChanges
from app.modules.code_changes.delivery import delivery_package, review_change
from app.modules.code_changes.models import (
    CodeChangeRecord,
    CodeWorkPolicyRecord,
    CodeWorkReservation,
    CodeWorkUsageRecord,
    VerificationProfileRecord,
    VerificationRecord,
)
from app.modules.code_changes.policy import WorkPolicy
from app.modules.code_changes.request_binding import RequestOrigin
from app.modules.source_analysis.workspace import Workspace


def work_records(database):
    models = (
        CodeChangeRecord,
        VerificationProfileRecord,
        VerificationRecord,
        CodeWorkPolicyRecord,
        CodeWorkUsageRecord,
        CodeWorkReservation,
    )
    with database.session() as session:
        return {
            model.__tablename__: [
                dict(row)
                for row in session.execute(
                    select(model.__table__).order_by(*model.__table__.primary_key.columns)
                ).mappings()
            ]
            for model in models
        }


def scratch_contents(paths):
    root = io_path(paths.scratch)
    return {
        file.relative_to(root).as_posix(): file.read_bytes()
        for file in root.rglob("*")
        if file.is_file()
    }


async def run_verification(service, identifier, profile, purpose):
    service.verify(identifier, profile["id"], purpose)
    result = await service.wait(identifier, timeout_seconds=10)
    latest = result["latest_verification"]
    assert latest["status"] == "passed", latest
    assert latest["purpose"] == purpose and latest["executor"]["kind"] == "trusted_host"
    return result


async def test_restore_keeps_code_work(tmp_path, monkeypatch):
    monkeypatch.setattr(WorkPolicy, "day", staticmethod(lambda: "2030-06-30"))
    source = tmp_path / "source"
    source.mkdir()
    original = b"class Program { static void Main() {} }\n"
    (source / "Program.cs").write_bytes(original)
    paths = Paths(tmp_path / "data", source)
    database = Database(paths.data / "app.sqlite3")
    changes = CodeChanges(paths, database, Workspace(source), "backup-project")
    try:
        # 明确注入临时数据库引擎；迁移环境不能回落到正式默认 data。
        migration = Config(str(PROJECT_ROOT / "backend/alembic.ini"))
        migration.attributes["connection"] = database.engine
        command.upgrade(migration, "0020")
        policy = changes.policy.save(
            {
                **changes.policy.get().model_dump(),
                "min_free_mb": 0,
                "require_sandbox_delivery": False,
                "retention_days": 7,
                "reading_token_limit": 5000,
            }
        )
        settled = changes.policy.reserve(600)
        changes.policy.settle(settled, 120)
        pending = changes.policy.reserve(400)
        usage = changes.policy.tokens()
        assert usage == {
            "day": "2030-06-30",
            "reserved_tokens": 520,
            "actual_tokens": 120,
            "calls": 2,
        }
        change = changes.create(
            "备份修改",
            "重启后保留需求、审核与可继续核对的工作",
            acceptance_criteria=["入口改为 Start", "原件保持不变"],
            constraints="只修改入口名称",
            allowed_paths=["Program.cs"],
            request_origin=RequestOrigin("manual_form", "只改入口名称", actor_id="test-actor"),
        )
        original_request = change["request_binding"]["original"]
        change = changes.update_requirements(
            change["id"],
            change["change_version"],
            change["requirements_version"],
            title=change["title"],
            goal=change["goal"],
            acceptance_criteria=change["acceptance_criteria"],
            allowed_paths=change["allowed_paths"],
            constraints="只修改入口名称；不得联网",
            request_origin=RequestOrigin("manual_form", "增加离线约束", actor_id="test-actor"),
            authorized_fields={"constraints"},
        )
        assert change["request_binding"]["original"] == original_request
        assert len(change["request_binding"]["revisions"]) == 1
        file = changes.read_file(change["id"], "Program.cs")
        changes.edit_file(change["id"], "Program.cs", "Main", "Start", file["version"])
        profile = changes.save_profile(
            "可信临时 Python（非沙箱）",
            [sys.executable, "-c", "print('backup-verification')"],
            5,
            executor={"kind": "trusted_host"},
            baseline_required=True,
            category="test",
            environment_label="本机临时测试，不代表沙箱验收",
        )
        await run_verification(changes, change["id"], profile, "baseline")
        passed = await run_verification(changes, change["id"], profile, "change")
        review_change(
            changes,
            change["id"],
            passed["change_version"],
            passed["requirements_version"],
            "核对当前补丁",
            "test-reviewer",
        )
        package = delivery_package(changes, change["id"])
        with ZipFile(io.BytesIO(package)) as zipped:
            assert (
                json.loads(zipped.read("manifest.json"))["request_binding"]
                == change["request_binding"]
            )
        (paths.scratch / "delivery.zip").write_bytes(package)
        patch = changes.export(change["id"])
        (paths.scratch / "delivery.patch").write_text(patch, encoding="utf-8", newline="")
        expected = changes.get(change["id"])
        history = changes.verification_history(change["id"])
        records = work_records(database)
        scratch = scratch_contents(paths)
        # 数据库保持在线并可包含 WAL；实际备份负责生成一致 SQLite 快照。
        backup = await asyncio.to_thread(create_backup, paths)
        with ZipFile(backup) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            assert manifest["database_revision"] == "0020"
            assert {
                name.removeprefix("scratch/")
                for name in archive.namelist()
                if name.startswith("scratch/")
            } == set(scratch)
        # 校验后不恢复的分支也必须清除仍含长路径日志的暂存树。
        with checked_backup(backup, temporary_parent=tmp_path) as (report, staged):
            assert report["valid"] is True
            assert {
                file.relative_to(staged / "scratch").as_posix(): file.read_bytes()
                for file in (staged / "scratch").rglob("*")
                if file.is_file()
            } == scratch
        assert not await asyncio.to_thread(staged.exists)
    finally:
        await changes.shutdown()
        database.close()

    target = Paths(tmp_path / "restore", source)
    result = await asyncio.to_thread(restore_backup, backup, target.data)
    assert result["restored"] is True and result["database_revision"] == "0020"
    restored_database = Database(target.data / "app.sqlite3")
    restored = CodeChanges(target, restored_database, Workspace(source), "backup-project")
    try:
        assert work_records(restored_database) == records
        assert restored.get(change["id"]) == expected
        assert restored.log_path(change["id"], expected["latest_verification"]["id"]).read_text(
            encoding="utf-8"
        ) == expected["latest_verification"]["output"].replace("\r\n", "\n")
        assert restored.profiles() == [profile]
        assert restored.policy.get().model_dump() == policy
        assert restored.policy.tokens() == usage
        assert restored.verification_history(change["id"]) == history
        assert scratch_contents(target) == scratch
        assert restored.export(change["id"]) == patch
        assert "Start" in restored.read_file(change["id"], "Program.cs")["content"]
        assert (target.scratch / "delivery.zip").read_bytes() == package
        assert (target.scratch / "delivery.patch").read_bytes() == patch.encode("utf-8")
        with ZipFile(io.BytesIO(package)) as archive:
            delivery = json.loads(archive.read("manifest.json"))
        assert delivery["review"] == expected["review"]
        assert delivery["verification"]["purpose"] == "change"
        assert delivery["baseline"]["purpose"] == "baseline"
        assert delivery["acceptance_criteria"] == expected["acceptance_criteria"]
        with restored_database.session() as session:
            receipts = {
                row.id: row.actual_tokens for row in session.scalars(select(CodeWorkReservation))
            }
            assert receipts == {settled["id"]: 120, pending["id"]: None}
            assert session.scalar(text("SELECT version_num FROM alembic_version")) == "0020"
        assert (source / "Program.cs").read_bytes() == original
    finally:
        await restored.shutdown()
        restored_database.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows 本地扩展路径边界")
@pytest.mark.parametrize(
    "parent",
    [r"\\server\share\stage", r"\\?\UNC\server\share\stage", r"\\.\C:\stage"],
)
def test_backup_staging_rejects_unc_and_device_parent_before_io(tmp_path, monkeypatch, parent):
    archive = tmp_path / "empty.zip"
    with ZipFile(archive, "w"):
        pass

    def unexpected_resolve(_path, *args, **kwargs):
        raise AssertionError("拒绝网络或设备身份前不能解析目标路径")

    # 明确证明拒绝发生在父目录解析前，不能因恶意UNC输入访问外部节点。
    monkeypatch.setattr(Path, "resolve", unexpected_resolve)
    with pytest.raises(ValueError, match="本地绝对路径"):
        with checked_backup(archive, temporary_parent=Path(parent)):
            pytest.fail("不应创建网络或设备暂存目录")
