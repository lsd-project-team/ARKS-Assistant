"""交付后清理的并发反例；外部写入使用真实临时文件，删除逻辑保持真实。"""

import sys
from datetime import UTC, datetime, timedelta

from app.modules.code_changes import CodeChanges
from app.modules.code_changes.delivery import delivery_package, review_change
from app.modules.code_changes.maintenance import cleanup
from app.modules.code_changes.models import CodeChangeRecord


async def test_cleanup_keeps_work_saved_externally_while_counting_expired_copy(
    services, monkeypatch
):
    paths, database, workspace, *_ = services
    service = CodeChanges(paths, database, workspace, "cleanup-race")
    service.policy.save({"min_free_mb": 0, "require_sandbox_delivery": False})
    try:
        change = service.create("已交付工作", "保留后续工作", acceptance_criteria=["命令验证通过"])
        source = service.read_file(change["id"], "Program.cs")
        service.edit_file(change["id"], "Program.cs", "Main", "Start", source["version"])
        profile = service.save_profile(
            "真实临时 Python",
            [sys.executable, "-c", "print('passed')"],
            5,
            executor={"kind": "trusted_host"},
            baseline_required=False,
        )
        service.verify(change["id"], profile["id"])
        passed = await service.wait(change["id"], 10)
        assert passed["status"] == "passed"
        review_change(service, change["id"], passed["change_version"], "核对", "reviewer")
        delivery_package(service, change["id"])
        now = datetime(2030, 1, 31, tzinfo=UTC)
        with database.session.begin() as session:
            row = session.get(CodeChangeRecord, change["id"])
            row.delivered_at = (now - timedelta(days=31)).isoformat()
            folder = service._folder(row)
        fresh_file = folder / "work" / "Program.cs"
        fresh_content = b"class FreshUnreviewedWork {}\n"
        real_storage = service.policy.storage

        def external_save_during_storage(scope):
            usage = real_storage(scope)
            # 模拟外部编辑器在清理检查完成后、遍历统计期间保存了新的工作。
            fresh_file.write_bytes(fresh_content)
            return usage

        monkeypatch.setattr(service.policy, "storage", external_save_during_storage)
        result = cleanup(service, False, now=now)
        assert result["removed"] == 0, "统计期间保存的新工作不能按旧交付版本删除"
        assert fresh_file.read_bytes() == fresh_content
    finally:
        await service.shutdown()
