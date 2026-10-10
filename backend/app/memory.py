"""跨会话 Markdown 记忆，带来源、源码版本和乐观并发检查。"""

from __future__ import annotations

import json
from pathlib import Path
from threading import RLock

from app.config import Paths, dump_json
from app.database import Database
from app.models import MemoryRecord, Thread, now_iso
from app.schemas import MemoryWrite
from app.workspace import Workspace, content_version


class MemoryService:
    def __init__(self, paths: Paths, database: Database, workspace: Workspace):
        self.paths = paths
        self.database = database
        self.workspace = workspace
        self.lock = RLock()

    def folder(self, scope: str) -> Path:
        folder = self.paths.memories / (self.workspace.id if scope == "project" else "user")
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def memory_id(self, scope: str, name: str) -> str:
        return f"{self.workspace.id if scope == 'project' else 'user'}:{name}"

    def list(self) -> list[dict]:
        result = []
        for scope in ("project", "user"):
            for target in self.folder(scope).glob("*.md"):
                result.append(self.read(scope, target.name))
        return result

    def read(self, scope: str, name: str) -> dict:
        MemoryWrite(name=name, scope=scope, content="")
        target = self.folder(scope) / name
        if not target.exists():
            raise FileNotFoundError("记忆不存在")
        data = target.read_bytes()
        with self.database.session() as session:
            row = session.get(MemoryRecord, self.memory_id(scope, name))
            sources = json.loads(row.source_paths_json) if row else []
            source_thread = row.source_thread_id if row else None
            source = session.get(Thread, source_thread) if source_thread else None
            source_status = source.state if source else "deleted" if source_thread else None
        checked = []
        for source in sources:
            try:
                current = self.workspace.read(source["path"])
                stale = current["version"] != source["version"]
            except (ValueError, OSError):
                stale = True
            checked.append({**source, "stale": stale})
        return {
            "name": name,
            "scope": scope,
            "content": data.decode("utf-8"),
            "version": content_version(data),
            "source_thread_id": source_thread,
            "source_thread_status": source_status,
            "sources": checked,
            "updated_at": target.stat().st_mtime,
        }

    def save(self, request: MemoryWrite) -> dict:
        target = self.folder(request.scope) / request.name
        with self.lock:
            current_version = content_version(target.read_bytes()) if target.exists() else None
            if current_version != request.version:
                raise ValueError("记忆已被更新，请重新打开后编辑")
            sources = [
                {"path": path, "version": self.workspace.read(path)["version"]}
                for path in dict.fromkeys(request.source_paths)
            ]
            temporary = target.with_suffix(".tmp")
            temporary.write_text(request.content, encoding="utf-8")
            temporary.replace(target)
            with self.database.session.begin() as session:
                key = self.memory_id(request.scope, request.name)
                row = session.get(MemoryRecord, key)
                if not row:
                    row = MemoryRecord(
                        id=key,
                        workspace_id=self.workspace.id,
                        name=request.name,
                        scope=request.scope,
                    )
                    session.add(row)
                row.source_thread_id = request.source_thread_id
                row.source_paths_json = dump_json(sources)
                row.updated_at = now_iso()
        return self.read(request.scope, request.name)

    def delete(self, scope: str, name: str, version: str):
        with self.lock:
            current = self.read(scope, name)
            if current["version"] != version:
                raise ValueError("记忆已被更新，请刷新后再删除")
            (self.folder(scope) / name).unlink()
            with self.database.session.begin() as session:
                row = session.get(MemoryRecord, self.memory_id(scope, name))
                if row:
                    session.delete(row)

    def prompt_snapshot(self) -> tuple[str, list[dict]]:
        rows = self.list()
        chunks = [
            f"[{row['scope']}/{row['name']}]\n{row['content']}\n"
            f"源码来源：{dump_json(row['sources'])}"
            for row in rows
        ]
        remaining = 24000
        included = []
        accepted = []
        for row, chunk in zip(rows, chunks, strict=True):
            if remaining <= 0:
                break
            accepted.append(chunk[:remaining])
            included.append(
                {**row, "partial": len(chunk) > remaining, "injected_text": chunk[:remaining]}
            )
            remaining -= len(chunk) + 2
        return "\n\n".join(accepted)[:24000], included

    def prompt(self) -> str:
        return self.prompt_snapshot()[0]
