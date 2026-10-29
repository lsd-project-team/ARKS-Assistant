"""旧修改档案只保留备份兼容，不能因移除执行功能而丢失历史数据。"""

from alembic import command
from alembic.config import Config
from sqlalchemy import select

from app.core.config import PROJECT_ROOT, Paths
from app.infrastructure.database.legacy_code_work import LegacyCodeChange
from app.infrastructure.database.session import Database
from app.infrastructure.storage.backup import create_backup
from app.infrastructure.storage.restore import restore_backup
from app.modules.settings.model_ledger import ModelLedger


def test_backup_restore_preserves_legacy_archive_and_current_model_ledger(services, tmp_path):
    paths, database, *_ = services
    config = Config(str(PROJECT_ROOT / "backend/alembic.ini"))
    config.attributes["connection"] = database.engine
    command.upgrade(config, "head")
    with database.session.begin() as session:
        session.add(
            LegacyCodeChange(
                id="legacy",
                project_id="old-project",
                title="旧修改",
                goal="历史记录",
                source_root=str(paths.workspace),
            )
        )
    ledger = ModelLedger(database, "old-project")
    ledger.save({"token_limit": 5000})
    ledger.settle(ledger.reserve(800), 120)
    previous = ledger.tokens()
    archive = paths.scratch / "code-changes/old-project/archive.txt"
    archive.parent.mkdir(parents=True)
    archive.write_bytes(b"legacy archive")
    backup = create_backup(paths)
    restored = Paths(tmp_path / "restored", paths.workspace)
    assert restore_backup(backup, restored.data)["restored"] is True
    restored_db = Database(restored.data / "app.sqlite3")
    try:
        with restored_db.session() as session:
            row = session.scalar(select(LegacyCodeChange))
            assert row.id == "legacy" and row.goal == "历史记录"
        assert ModelLedger(restored_db, "old-project").tokens() == previous
        assert (
            restored.scratch / "code-changes/old-project/archive.txt"
        ).read_bytes() == b"legacy archive"
    finally:
        restored_db.close()
