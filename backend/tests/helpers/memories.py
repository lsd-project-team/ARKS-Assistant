"""测试数据通过真实生成快照装配；不恢复已移除的聊天写入API。"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.config import dump_json
from app.modules.auth.context import request_identity
from app.modules.auth.models import Account
from app.modules.chat.models import Thread
from app.modules.chat.repository import Repository
from app.modules.memory.generated_store import collection_id
from app.modules.memory.models import MemoryBundle, MemoryExtraction, MemoryRecord, MemoryRevision


@dataclass
class MemorySeed:
    name: str
    content: str
    scope: str = "project"
    source_paths: list[str] = field(default_factory=list)
    source_thread_id: str | None = None
    version: str | None = None


def seed_memory(memory, request):
    identity = request_identity.get()
    owner = identity["user"]["id"] if identity else None
    if owner:
        with memory.database.session.begin() as session:
            if not session.get(Account, owner):
                session.add(
                    Account(
                        id=owner,
                        username=owner,
                        display_name=owner,
                        role="user",
                        password_hash="test-only",
                    )
                )
    repository = Repository(memory.database, memory.workspace.id)
    thread_id = None
    for _ in range(2):
        run = repository.create_run(thread_id, request.content, [])
        thread_id = run["thread_id"]
        repository.finish(
            run["id"], "历史对话的补充背景，仅用于构造有足够上下文的记忆测试输入。" * 3
        )
    with memory.database.session.begin() as session:
        session.get(Thread, thread_id).updated_at = (
            datetime.now(UTC) - timedelta(hours=7)
        ).isoformat()
    snapshot = memory.live_snapshot(thread_id)
    assert snapshot, "测试记忆必须来自符合资格的真实聊天"
    sources = [
        {"path": path, "version": memory.workspace.read(path)["version"]}
        for path in request.source_paths
    ]
    fact = {
        "id": thread_id,
        "thread_id": thread_id,
        "fingerprint": snapshot["fingerprint"],
        "title": request.name,
        "content": request.content,
        "kind": "preference" if request.scope == "user" else "project",
        "sources": sources,
        "evidence": [{"message_id": snapshot["messages"][0]["id"], "quote": request.content[:32]}],
    }
    with memory.database.session.begin() as session:
        session.add(
            MemoryExtraction(
                thread_id=thread_id,
                owner_id=owner or "local",
                workspace_id=memory.workspace.id,
                fingerprint=snapshot["fingerprint"],
                state="completed",
                raw_json=dump_json([fact]),
            )
        )
    bundle = memory.generated.bundle(owner or "local", memory.workspace.id)
    groups = (
        [group for group in bundle["document"]["groups"] if group["title"] != request.name]
        if bundle
        else []
    )
    memory.generated.publish(
        snapshot, {"groups": [*groups, {"title": request.name, "memories": [fact]}]}
    )
    return memory.list()[0]


def seed_legacy_memory(memory, request):
    """历史备份必须仍能保全旧文件与版本，但旧文件不能进入新的回答。"""
    folder = memory.paths.memories / "legacy-fixture"
    folder.mkdir(exist_ok=True)
    target = folder / request.name
    target.write_text(request.content, encoding="utf-8")
    with memory.database.session.begin() as session:
        session.add(
            MemoryRecord(
                id=request.name,
                workspace_id=memory.workspace.id,
                name=request.name,
                scope=request.scope,
                source_thread_id=request.source_thread_id,
            )
        )
        session.add(
            MemoryRevision(
                memory_id=request.name,
                workspace_id=memory.workspace.id,
                name=request.name,
                scope=request.scope,
                content=request.content,
                version="0" * 64,
                action="created",
            )
        )
    return target


def clear_generated(memory):
    owner = request_identity.get()
    owner_id = owner["user"]["id"] if owner else "local"
    with memory.database.session.begin() as session:
        bundle = session.get(MemoryBundle, collection_id(owner_id, memory.workspace.id))
        if bundle:
            session.delete(bundle)
        for row in session.scalars(
            select(MemoryExtraction).where(
                MemoryExtraction.owner_id == owner_id,
                MemoryExtraction.workspace_id == memory.workspace.id,
            )
        ):
            session.delete(row)
