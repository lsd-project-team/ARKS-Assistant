"""跨会话 Markdown 记忆，带来源、源码版本和乐观并发检查。"""

from __future__ import annotations

import json
from pathlib import Path
from threading import RLock

from app.config import Paths, dump_json
from app.context import fit_text, text_tokens
from app.database import Database
from app.memory_history import MemoryHistory
from app.memory_matching import rank_memories, related_memories
from app.models import MemoryRecord, Thread, now_iso
from app.schemas import MemoryRestore, MemoryWrite
from app.workspace import Workspace, content_version


class MemoryService:
    def __init__(self, paths: Paths, database: Database, workspace: Workspace):
        self.paths = paths
        self.database = database
        self.workspace = workspace
        self.lock = RLock()
        self.history = MemoryHistory(database, workspace.id)

    def folder(self, scope: str) -> Path:
        folder = self.paths.memories / (self.workspace.id if scope == "project" else "user")
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def memory_id(self, scope: str, name: str) -> str:
        return f"{self.workspace.id if scope == 'project' else 'user'}:{name}"

    def list(self, include_deleted: bool = False) -> list[dict]:
        with self.lock:
            return self._list(include_deleted)

    def _list(self, include_deleted: bool) -> list[dict]:
        result = []
        for scope in ("project", "user"):
            for target in self.folder(scope).glob("*.md"):
                result.append(self.read(scope, target.name))
        if include_deleted:
            present = {(row["scope"], row["name"]) for row in result}
            result.extend(
                {**row, "content": "", "version": None, "deleted": True, "updated_at": 0}
                for row in self.history.deleted()
                if (row["scope"], row["name"]) not in present
            )
        return result

    def read(self, scope: str, name: str) -> dict:
        with self.lock:
            return self._read(scope, name)

    def _read(self, scope: str, name: str) -> dict:
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
        return self._write(request)

    def review(self, request: MemoryWrite) -> list[dict]:
        with self.lock:
            return related_memories(self.list(), request)

    def _write(self, request: MemoryWrite, *, sources_override=None, action=None) -> dict:
        if not request.content.strip():
            raise ValueError("记忆内容不能为空")
        target = self.folder(request.scope) / request.name
        with self.lock:
            previous_bytes = target.read_bytes() if target.exists() else None
            current_version = (
                content_version(previous_bytes) if previous_bytes is not None else None
            )
            if current_version != request.version:
                raise ValueError("记忆已被更新，请重新打开后编辑")
            matches = self.review(request)
            duplicates = [row["name"] for row in matches if row["kind"] == "duplicate"]
            if duplicates:
                raise ValueError(f"内容已保存在 {', '.join(duplicates)}，请编辑已有记忆")
            conflicts = [row["name"] for row in matches if row["kind"] == "conflict"]
            if conflicts and not request.confirm_conflicts:
                raise ValueError(f"同一字段与 {', '.join(conflicts)} 的值不同，请核对后确认保存")
            if any(
                request.reviewed_versions.get(row["name"]) != row["version"]
                for row in matches
                if row["kind"] == "conflict"
            ):
                raise ValueError("相关记忆已更新，请重新检查冲突后保存")
            sources = (
                sources_override
                if sources_override is not None
                else [
                    {"path": path, "version": self.workspace.read(path)["version"]}
                    for path in dict.fromkeys(request.source_paths)
                ]
            )
            previous = self.read(request.scope, request.name) if target.exists() else None
            temporary = target.with_suffix(".tmp")
            # 字节写入保留 CRLF / LF；历史恢复不能经过 Windows 文本换行转换。
            temporary.write_bytes(request.content.encode("utf-8"))
            try:
                with self.database.session.begin() as session:
                    if previous:
                        self.history.preserve_legacy(session, previous)
                    self.history.snapshot(
                        session,
                        {**request.model_dump(), "sources": sources},
                        action or ("updated" if previous else "created"),
                    )
                    self._metadata(session, request, sources)
                    temporary.replace(target)
            except Exception:
                if previous_bytes is None:
                    target.unlink(missing_ok=True)
                else:
                    temporary.write_bytes(previous_bytes)
                    temporary.replace(target)
                raise
            finally:
                temporary.unlink(missing_ok=True)
        return self.read(request.scope, request.name)

    def _metadata(self, session, request, sources):
        key = self.memory_id(request.scope, request.name)
        row = session.get(MemoryRecord, key)
        if not row:
            row = MemoryRecord(
                id=key, workspace_id=self.workspace.id, name=request.name, scope=request.scope
            )
            session.add(row)
        row.source_thread_id = request.source_thread_id
        row.source_paths_json = dump_json(sources)
        row.updated_at = now_iso()

    def delete(self, scope: str, name: str, version: str):
        with self.lock:
            current = self.read(scope, name)
            if current["version"] != version:
                raise ValueError("记忆已被更新，请刷新后再删除")
            target = self.folder(scope) / name
            original = target.read_bytes()
            try:
                with self.database.session.begin() as session:
                    self.history.preserve_legacy(session, current)
                    self.history.snapshot(session, current, "deleted")
                    row = session.get(MemoryRecord, self.memory_id(scope, name))
                    if row:
                        session.delete(row)
                    target.unlink()
            except Exception:
                target.write_bytes(original)
                raise

    def restore(self, scope: str, name: str, request: MemoryRestore):
        MemoryWrite(name=name, scope=scope, content="")
        with self.lock:
            revision = self.history.get(scope, name, request.revision_id)
            return self._write(
                MemoryWrite(
                    name=name,
                    scope=scope,
                    content=revision["content"],
                    version=request.version,
                    source_thread_id=revision["source_thread_id"],
                    confirm_conflicts=request.confirm_conflicts,
                    reviewed_versions=request.reviewed_versions,
                ),
                sources_override=revision["sources"],
                action="restored",
            )

    def prompt_snapshot(
        self, query: str | None = None, *, max_tokens: int = 8000
    ) -> tuple[str, list[dict]]:
        rows = list(rank_memories(self.list(), query))
        chunks = [
            f"[{row['scope']}/{row['name']}]\n源码来源：{dump_json(row['sources'])}\n"
            + (
                f"记忆核对：相关条目包括 {', '.join(row['conflicts'][:5])}，"
                f"共 {len(row['conflicts'])} 条同字段不同值，回答前需核对。\n"
                if row["conflicts"]
                else ""
            )
            + row["content"]
            for row in rows
        ]
        included = []
        accepted = []
        for row, chunk in zip(rows, chunks, strict=True):
            remaining = max_tokens - text_tokens("\n\n".join(accepted)) - (1 if accepted else 0)
            if remaining <= 0:
                break
            header = chunk[: len(chunk) - len(row["content"])]
            if text_tokens(header) >= remaining:
                continue
            chosen = fit_text(chunk, remaining)
            accepted.append(chosen)
            included.append(
                {**row, "partial": len(chosen) < len(chunk), "injected_text": chosen}
            )
        return "\n\n".join(accepted), included

    def prompt(self) -> str:
        return self.prompt_snapshot()[0]
