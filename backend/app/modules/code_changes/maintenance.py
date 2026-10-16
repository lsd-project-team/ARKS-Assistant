"""显式清理到期临时文件，保留数据库审计及尚未交付的修改。"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.modules.code_changes.files import remove_copy
from app.modules.code_changes.models import CodeChangeRecord, VerificationRecord


def cleanup(service, dry_run=True, *, now=None):
    now = now or datetime.now(UTC)
    cutoff = (now - timedelta(days=service.policy.get().retention_days)).isoformat()
    result = {"eligible": 0, "removed": 0, "bytes": 0, "skipped": 0}
    with service.lock, service.database.session.begin() as session:
        rows = session.scalars(
            select(CodeChangeRecord).where(CodeChangeRecord.project_id == service.project_id)
        )
        for row in rows:
            # 丢弃或交付明确发生后才开始保留期；仅创建时间久不构成删除授权。
            completed_at = row.delivered_at or (row.updated_at if row.status == "discarded" else "")
            active = session.scalar(
                select(VerificationRecord.id).where(
                    VerificationRecord.change_id == row.id, VerificationRecord.status == "running"
                )
            )
            if row.status == "verifying" or active or not completed_at or completed_at >= cutoff:
                result["skipped"] += 1
                continue
            if row.status != "discarded":
                # 已交付后被外部程序改过的副本仍是未交付工作，不能按旧交付时间删除。
                try:
                    service._refresh(row)
                except (OSError, ValueError):
                    result["skipped"] += 1
                    continue
                if not row.delivered_at:
                    result["skipped"] += 1
                    continue
            folder = service._folder(row)
            if not folder.exists():
                continue
            usage = service.policy.storage(folder)
            result["eligible"] += 1
            result["bytes"] += usage["storage_bytes"]
            if not dry_run:
                if row.status != "discarded":
                    # 完整空间统计可能耗时；删除前再核对，避免统计期间外部保存的新工作被清理。
                    try:
                        service._refresh(row)
                    except (OSError, ValueError):
                        result["eligible"] -= 1
                        result["bytes"] -= usage["storage_bytes"]
                        result["skipped"] += 1
                        continue
                    if not row.delivered_at:
                        result["eligible"] -= 1
                        result["bytes"] -= usage["storage_bytes"]
                        result["skipped"] += 1
                        continue
                remove_copy(service._scope(row.project_id), folder)
                row.status = "discarded"
                row.error = "临时文件已按保留规则清理；需求、审核与验证记录仍保留"
                result["removed"] += 1
    return result
