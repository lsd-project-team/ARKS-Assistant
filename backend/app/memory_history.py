"""记忆版本保存在业务数据库中，覆盖或删除 Markdown 后仍可找回原内容。"""

import json

from sqlalchemy import func, select

from app.config import dump_json
from app.models import MemoryRevision
from app.workspace import content_version


class MemoryHistory:
    def __init__(self, database, workspace_id):
        self.database, self.workspace_id = database, workspace_id

    def key(self, scope, name):
        return f"{self.workspace_id if scope == 'project' else 'user'}:{name}"

    def snapshot(self, session, memory, action):
        session.add(
            MemoryRevision(
                memory_id=self.key(memory["scope"], memory["name"]),
                workspace_id=self.workspace_id,
                name=memory["name"],
                scope=memory["scope"],
                content=memory["content"],
                version=content_version(memory["content"].encode()),
                source_thread_id=memory.get("source_thread_id"),
                source_paths_json=dump_json(memory.get("sources", [])),
                action=action,
                lifecycle=memory.get("lifecycle", "valid"),
            )
        )

    def preserve_legacy(self, session, memory):
        exists = session.scalar(
            select(MemoryRevision.id)
            .where(
                MemoryRevision.memory_id == self.key(memory["scope"], memory["name"]),
                MemoryRevision.version == memory["version"],
            )
            .limit(1)
        )
        if exists is None:
            self.snapshot(session, memory, "imported")

    @staticmethod
    def public(row):
        return {
            "id": row.id,
            "name": row.name,
            "scope": row.scope,
            "content": row.content,
            "version": row.version,
            "sources": json.loads(row.source_paths_json),
            "source_thread_id": row.source_thread_id,
            "action": row.action,
            "lifecycle": row.lifecycle,
            "created_at": row.created_at,
        }

    def list(self, scope, name):
        with self.database.session() as session:
            rows = session.scalars(
                select(MemoryRevision)
                .where(MemoryRevision.memory_id == self.key(scope, name))
                .order_by(MemoryRevision.id.desc())
            ).all()
            return [self.public(row) for row in rows]

    def get(self, scope, name, revision_id):
        with self.database.session() as session:
            row = session.get(MemoryRevision, revision_id)
            if not row or row.memory_id != self.key(scope, name):
                raise FileNotFoundError("记忆版本不存在")
            return self.public(row)

    def deleted(self):
        with self.database.session() as session:
            latest = select(func.max(MemoryRevision.id)).group_by(MemoryRevision.memory_id)
            rows = session.scalars(
                select(MemoryRevision).where(
                    MemoryRevision.id.in_(latest),
                    MemoryRevision.action == "deleted",
                    (MemoryRevision.memory_id.startswith(self.workspace_id + ":"))
                    | (MemoryRevision.scope == "user"),
                )
            ).all()
            return [self.public(row) for row in rows]
