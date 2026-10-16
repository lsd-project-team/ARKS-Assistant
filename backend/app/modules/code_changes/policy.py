"""项目额度与保留规则；余额在数据库中原子预留，服务重启不能重置预算。"""

import json
import os
import shutil
import stat
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import update
from sqlalchemy.dialects.sqlite import insert

from app.core.identifiers import new_id, now_iso
from app.modules.code_changes.files import is_link
from app.modules.code_changes.models import (
    CodeWorkPolicyRecord,
    CodeWorkReservation,
    CodeWorkUsageRecord,
)
from app.modules.code_changes.schemas import CodeWorkPolicy

MEBIBYTE = 1024 * 1024


class WorkPolicy:
    def __init__(self, paths, database, project_id):
        self.paths, self.database, self.project = paths, database, project_id

    @property
    def project_id(self):
        return str(self.project() if callable(self.project) else self.project)

    def get(self):
        with self.database.session() as session:
            row = session.get(CodeWorkPolicyRecord, self.project_id)
            return CodeWorkPolicy.model_validate_json(row.payload_json) if row else CodeWorkPolicy()

    def save(self, payload):
        policy = CodeWorkPolicy.model_validate(payload)
        with self.database.session.begin() as session:
            row = session.get(CodeWorkPolicyRecord, self.project_id)
            if row is None:
                row = CodeWorkPolicyRecord(project_id=self.project_id)
                session.add(row)
            row.payload_json, row.updated_at = policy.model_dump_json(), now_iso()
        return policy.model_dump()

    @staticmethod
    def day():
        # 项目日额度统一按UTC结算，前端说明口径，避免迁移服务器后时区改变重置边界。
        return datetime.now(UTC).date().isoformat()

    def tokens(self):
        day, project = self.day(), self.project_id
        with self.database.session() as session:
            row = session.get(CodeWorkUsageRecord, (project, day))
            return {
                "day": day,
                "reserved_tokens": row.reserved_tokens if row else 0,
                "actual_tokens": row.actual_tokens if row else 0,
                "calls": row.calls if row else 0,
            }

    def reserve(self, maximum):
        if type(maximum) is not int or maximum <= 0:
            raise ValueError("模型额度预留必须是正整数")
        limit, day, identifier = self.get().reading_token_limit, self.day(), new_id()
        project = self.project_id
        with self.database.session.begin() as session:
            session.execute(
                insert(CodeWorkUsageRecord)
                .values(project_id=project, day=day, reserved_tokens=0, actual_tokens=0, calls=0)
                .on_conflict_do_nothing()
            )
            claimed = session.execute(
                update(CodeWorkUsageRecord)
                .where(
                    CodeWorkUsageRecord.project_id == project,
                    CodeWorkUsageRecord.day == day,
                    CodeWorkUsageRecord.reserved_tokens + maximum <= limit,
                )
                .values(
                    reserved_tokens=CodeWorkUsageRecord.reserved_tokens + maximum,
                    calls=CodeWorkUsageRecord.calls + 1,
                )
            )
            if claimed.rowcount != 1:
                raise ValueError("本项目当日模型Token预算不足；进度已保留，请提高额度或次日继续")
            session.add(
                CodeWorkReservation(
                    id=identifier, project_id=project, day=day, reserved_tokens=maximum
                )
            )
        return {"id": identifier, "day": day, "maximum": maximum, "project_id": project}

    def settle(self, reservation, actual_tokens):
        if actual_tokens is None:
            return  # 供应商未给用量或调用异常时保留预留，不能把未知费用当成零。
        if type(actual_tokens) is not int or actual_tokens < 0:
            raise ValueError("供应商用量必须是非负整数")
        project = self.project_id
        with self.database.session.begin() as session:
            receipt = session.get(CodeWorkReservation, reservation["id"])
            if receipt is None or receipt.project_id != project:
                raise ValueError("模型额度预留不属于当前项目")
            claimed = session.execute(
                update(CodeWorkReservation)
                .where(
                    CodeWorkReservation.id == receipt.id,
                    CodeWorkReservation.actual_tokens.is_(None),
                )
                .values(actual_tokens=actual_tokens)
            )
            if claimed.rowcount != 1:
                return  # 重复回调只结算一次，不能重复退款绕过日额度。
            session.execute(
                update(CodeWorkUsageRecord)
                .where(
                    CodeWorkUsageRecord.project_id == project,
                    CodeWorkUsageRecord.day == receipt.day,
                )
                .values(
                    reserved_tokens=CodeWorkUsageRecord.reserved_tokens
                    - receipt.reserved_tokens
                    + actual_tokens,
                    actual_tokens=CodeWorkUsageRecord.actual_tokens + actual_tokens,
                )
            )

    def limits(self, scope=None):
        policy = self.get()
        output = min(policy.max_storage_mb * MEBIBYTE, 1_000_000_000)
        if scope is not None:
            used = self.storage(scope)["storage_bytes"]
            available = min(
                policy.max_storage_mb * MEBIBYTE - used,
                shutil.disk_usage(self.paths.scratch).free - policy.min_free_mb * MEBIBYTE,
            )
            # 同时容纳传入归档、回传归档和交换目录，另为日志/tar头预留空间。
            spare = (
                available // policy.max_active_verifications - (policy.max_log_mb + 64) * MEBIBYTE
            )
            output = min(output, spare // 3)
            if output <= 0:
                raise ValueError("项目临时空间不足以安全传输并回传副本，请先清理或提高额度")
        return {
            "cpus": 2,
            "memory_mb": 2048,
            "pids": 128,
            "max_log_bytes": policy.max_log_mb * MEBIBYTE,
            "max_output_bytes": output,
            "windows_scratch_mb": policy.windows_scratch_mb,
        }

    def _storage_scope(self, scope):
        scratch = Path(os.path.abspath(self.paths.scratch))
        scope = Path(os.path.abspath(scope))
        if not scope.is_relative_to(scratch):
            raise ValueError("只能统计项目临时目录内的空间")
        for path in (scope, *scope.parents):
            if path.exists() or path.is_symlink() or path.is_junction():
                if is_link(path):
                    raise ValueError("项目临时目录包含链接，不能统计或清理")
                if not path.is_dir():
                    raise ValueError("项目临时路径必须是目录")
            if path == scratch:
                break
        return scope

    def storage(self, scope):
        scope = self._storage_scope(scope)
        total = logs = 0
        if not scope.exists():
            return {"storage_bytes": 0, "logs_bytes": 0}
        for folder, directories, files in os.walk(
            scope, followlinks=False, onerror=self._walk_error
        ):
            for name in (*directories, *files):
                path = Path(folder) / name
                info = path.lstat()
                if is_link(path):
                    raise ValueError("项目临时目录包含链接，不能统计或清理")
                if stat.S_ISREG(info.st_mode):
                    if info.st_nlink > 1:
                        raise ValueError("项目临时目录包含硬链接，不能统计或清理")
                    total += info.st_size
                    logs += info.st_size if path.suffix.casefold() == ".log" else 0
                elif not stat.S_ISDIR(info.st_mode):
                    raise ValueError("项目临时目录只允许普通文件和目录")
        self._storage_scope(scope)
        return {"storage_bytes": total, "logs_bytes": logs}

    @staticmethod
    def _walk_error(error):
        raise ValueError("无法完整统计项目临时目录，未开始新操作") from error

    def check_space(self, scope, required=0):
        if type(required) is not int or required < 0:
            raise ValueError("新增临时空间必须是非负整数")
        policy, usage = self.get(), self.storage(scope)
        if usage["storage_bytes"] + required > policy.max_storage_mb * MEBIBYTE:
            raise ValueError("项目临时空间额度不足，请导出所需修改并清理已交付或已丢弃副本")
        if shutil.disk_usage(self.paths.scratch).free - required < policy.min_free_mb * MEBIBYTE:
            raise ValueError("服务器剩余磁盘空间不足，未开始新建副本或验证")
        return usage


def profile_version(profile):
    from app.modules.code_changes.files import digest

    fields = {
        key: profile.get(key)
        for key in ("argv", "executor", "timeout_seconds", "category", "baseline_required")
    }
    return digest(json.dumps(fields, sort_keys=True, separators=(",", ":")).encode())
