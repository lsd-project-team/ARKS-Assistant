"""SQLite 使用 WAL 和短事务；运行事件同时支持断线重放。"""

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker


class Database:
    def __init__(self, path: Path):
        self.engine = create_engine(
            f"sqlite:///{path.as_posix()}",
            connect_args={"check_same_thread": False, "timeout": 15},
        )
        event.listen(self.engine, "connect", self._configure_connection)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)
        self.session = self.sessions

    @staticmethod
    def _configure_connection(connection, _record) -> None:
        cursor = connection.cursor()
        for statement in ("PRAGMA foreign_keys=ON", "PRAGMA journal_mode=WAL"):
            cursor.execute(statement)
        cursor.close()

    def close(self) -> None:
        self.engine.dispose()
