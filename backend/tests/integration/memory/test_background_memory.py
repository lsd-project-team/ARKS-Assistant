"""真实数据库、文件和后台流程，仅替换模型网络调用。"""

import asyncio
import json
import time
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from sqlalchemy import select

from app.agents.runtime.engine import AgentRuntime
from app.bootstrap import create_app
from app.core.config import AppSettings, ModelSettings
from app.modules.auth.context import request_identity
from app.modules.chat.models import Message, Thread
from app.modules.knowledge.search import catalog
from app.modules.memory.background import BackgroundMemories
from app.modules.memory.generated_store import archive_legacy_memories
from app.modules.memory.generation_protocol import (
    ExtractionResponse,
    parse_response,
    validate_facts,
)
from app.modules.memory.models import MemoryBundle, MemoryExtraction


@pytest.fixture
def worker(services, monkeypatch):
    paths, database, workspace, repository, memories, settings = services
    settings.save(
        AppSettings(
            model=ModelSettings(
                model="test-model",
                base_url="https://example.invalid",
                api_key="test-only-key",
            )
        )
    )
    calls = []
    monkeypatch.setattr(catalog(database).retrieval, "scores", lambda *_: {})

    class Model:
        callbacks = []

        async def ainvoke(self, messages):
            payload = json.loads(messages[-1].content)
            if "提取少量" in messages[0].content:
                calls.append("extract")
                row = next(row for row in payload if row["role"] == "user")
                content = {
                    "memories": [
                        {
                            "title": "回答偏好",
                            "kind": "preference",
                            "content": "用户希望回答先说明结果，再说明依据。",
                            "evidence": [{"message_id": row["id"], "quote": row["content"][:24]}],
                        }
                    ]
                }
            elif "你负责比较长期记忆" in messages[0].content:
                calls.append("reconcile")
                content = {
                    "decisions": [
                        {"pair_id": pair["id"], "relation": "duplicate"} for pair in payload
                    ]
                }
            else:
                calls.append("consolidate")
                content = {
                    "groups": [{"title": "回答偏好", "memory_ids": [row["id"] for row in payload]}]
                }
            return AIMessage(content=json.dumps(content, ensure_ascii=False))

    monkeypatch.setattr("app.modules.memory.background.create_model", lambda *_: Model())
    background = BackgroundMemories(
        SimpleNamespace(
            paths=paths,
            database=database,
            settings=settings,
            memories=memories,
            runtime=AgentRuntime(paths, settings, workspace, repository, memories),
        )
    )
    return background, calls


def make_chat(services, *, idle=7, remember=True, owner=None):
    _, database, _, repository, _, _ = services
    token = request_identity.set({"user": {"id": owner, "role": "user"}} if owner else None)
    try:
        thread_id = None
        for _ in range(2):
            run = repository.create_run(
                thread_id,
                "请记住我的回答偏好：先说明结果，再说明依据，并保留事实适用条件。" * 3,
                [],
                source_options={"use_memory": remember},
            )
            thread_id = run["thread_id"]
            repository.finish(run["id"], "收到。回答将围绕你提出的目标、证据和条件展开。" * 3)
        with database.session.begin() as session:
            session.get(Thread, thread_id).updated_at = (
                datetime.now(UTC) - timedelta(hours=idle)
            ).isoformat()
        return thread_id
    finally:
        request_identity.reset(token)


async def test_extract_consolidate_publish_and_next_session_inject(services, worker):
    background, calls = worker
    thread_id = make_chat(services)
    assert not services[4].list()
    await background.run_once()
    assert calls == ["extract", "consolidate"]
    prompt, rows = services[4].prompt_snapshot("回答偏好")
    assert "用户希望回答先说明结果" in prompt
    assert rows[0]["generated"] and rows[0]["source_thread_ids"] == [thread_id]
    files = list((services[0].memories / "automatic").rglob("MEMORY.md"))
    assert len(files) == 1 and "先说明结果" in files[0].read_text(encoding="utf-8")
    with services[1].session() as session:
        assert session.get(MemoryExtraction, thread_id).state == "completed"
        assert session.scalar(select(MemoryBundle)).revision == 1
    await background.run_once()
    assert calls == ["extract", "consolidate"]  # 重启/重复扫描不重复付费。


@pytest.mark.parametrize("idle,remember", [(0, True), (7, False), (24 * 31, True)])
async def test_ineligible_chats_do_not_call_model(services, worker, idle, remember):
    make_chat(services, idle=idle, remember=remember)
    await worker[0].run_once()
    assert worker[1] == [] and not services[4].list()


async def test_active_chat_and_short_chat_are_skipped(services, worker):
    thread_id = make_chat(services)
    run = services[3].create_run(thread_id, "继续", [])
    with services[1].session.begin() as session:
        session.get(Thread, thread_id).updated_at = (
            datetime.now(UTC) - timedelta(hours=7)
        ).isoformat()
    await worker[0].run_once()
    assert worker[1] == []
    services[3].finish(run["id"], "完成")
    with services[1].session.begin() as session:
        for message in session.scalars(select(Message).where(Message.thread_id == thread_id)):
            message.content = "短"
        session.get(Thread, thread_id).updated_at = (
            datetime.now(UTC) - timedelta(hours=7)
        ).isoformat()
    await worker[0].run_once()
    assert worker[1] == []


async def test_failed_consolidation_reuses_durable_extraction_after_restart(
    services, worker, monkeypatch
):
    background, calls = worker
    thread_id = make_chat(services)
    original = background.invoke

    async def failing(*args, **kwargs):
        if kwargs.get("consolidate"):
            raise RuntimeError("provider failed with secret data")
        return await original(*args, **kwargs)

    monkeypatch.setattr(background, "invoke", failing)
    await background.run_once()
    with services[1].session.begin() as session:
        job = session.get(MemoryExtraction, thread_id)
        assert job.state == "failed" and job.raw_json and job.error_code == "RuntimeError"
        job.retry_after = 0
    assert not services[4].list()
    restarted = BackgroundMemories(background.services)
    await restarted.run_once()
    assert calls == ["extract", "consolidate"]
    assert services[4].list()


async def test_changed_or_deleted_source_is_not_injected(services, worker):
    thread_id = make_chat(services)
    await worker[0].run_once()
    assert services[4].list()
    with services[1].session.begin() as session:
        message = session.scalar(select(Message).where(Message.thread_id == thread_id))
        message.content = "用户已撤回原来的偏好。"
    assert not services[4].list()
    with services[1].session.begin() as session:
        session.get(Thread, thread_id).state = "deleted"
    assert not services[4].prompt_snapshot("回答偏好")[0]


async def test_durable_memory_outlives_candidate_window_and_survives_next_consolidation(
    services, worker, monkeypatch
):
    old_thread = make_chat(services)
    await worker[0].run_once()
    with services[1].session.begin() as session:
        session.get(Thread, old_thread).updated_at = (
            datetime.now(UTC) - timedelta(days=40)
        ).isoformat()
    assert old_thread in services[4].list()[0]["source_thread_ids"]
    new_thread = make_chat(services)
    original_inputs = worker[0].store.inputs
    monkeypatch.setattr(worker[0].store, "inputs", lambda *args: original_inputs(*args)[:1])
    await worker[0].run_once()
    assert worker[1] == ["extract", "consolidate", "extract", "reconcile", "consolidate"]
    assert set(services[4].list()[0]["source_thread_ids"]) == {old_thread, new_thread}


async def test_wrong_evidence_is_rejected_and_previous_bundle_survives(
    services, worker, monkeypatch
):
    make_chat(services)
    await worker[0].run_once()
    before = services[4].list()[0]["content"]
    make_chat(services)

    async def hallucinated(*_args, **_kwargs):
        return json.dumps(
            {
                "memories": [
                    {
                        "title": "虚构",
                        "kind": "project",
                        "content": "假事实",
                        "evidence": [{"message_id": "invented", "quote": "不存在的原文"}],
                    }
                ]
            }
        )

    monkeypatch.setattr(worker[0], "invoke", hallucinated)
    await worker[0].run_once()
    assert services[4].list()[0]["content"] == before
    with services[1].session() as session:
        assert any(
            row.error_code == "memory_evidence_mismatch"
            for row in session.scalars(select(MemoryExtraction))
        )


async def test_low_budget_and_disabled_generation_do_not_claim_jobs(services, worker):
    make_chat(services)
    config = services[5].load()
    services[5].save(config.model_copy(update={"auto_memory": False}))
    await worker[0].run_once()
    assert not worker[1]
    services[5].save(config)
    ledger = worker[0].ledger(services[2].id)
    ledger.reserve(490000)
    await worker[0].run_once()
    assert not worker[1]
    with services[1].session() as session:
        assert session.scalar(select(MemoryExtraction)) is None


async def test_lease_prevents_duplicate_processing_and_expired_lease_recovers(services, worker):
    thread_id = make_chat(services)
    snapshot = worker[0].snapshot(thread_id, services[5].load())
    first = worker[0].claim(snapshot, time.time())
    assert first and worker[0].claim(snapshot, time.time()) is None
    with services[1].session.begin() as session:
        session.get(MemoryExtraction, thread_id).lease_until = 0
    await worker[0].run_once()
    assert worker[1] == ["extract", "consolidate"]


def test_legacy_memory_archived_once_without_becoming_new_input(services):
    legacy = services[0].memories / "user" / "旧记忆.md"
    legacy.parent.mkdir()
    legacy.write_text("旧的即时记忆", encoding="utf-8")
    result = archive_legacy_memories(services[0])
    assert result and not legacy.exists()
    archived = services[0].memories / result / "user" / "旧记忆.md"
    assert archived.read_text(encoding="utf-8") == "旧的即时记忆"
    assert archive_legacy_memories(services[0]) is None
    assert services[4].prompt_snapshot("回答偏好") == ("", [])


def test_memory_api_is_read_only(services):
    app = create_app(services[0])
    with TestClient(app) as client:
        assert app.state.background_memories.task is not None
        assert not app.state.background_memories.task.done()
        project_id = services[2].id
        prefix = f"/api/p/{project_id}"
        response = client.get(prefix + "/memories/status")
        assert response.status_code == 200 and response.json()["idle_hours"] == 6
        assert client.get(prefix + "/memories").json() == []
        assert client.put(prefix + "/memories", json={"content": "不能即时写入"}).status_code == 405
        assert client.post(prefix + "/memories/review", json={}).status_code == 404
    assert app.state.background_memories.task is None


async def test_shutdown_cancels_background_work_without_affecting_chat(
    services, worker, monkeypatch
):
    entered = asyncio.Event()

    async def running():
        entered.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(worker[0], "run_once", running)
    worker[0].start()
    await asyncio.wait_for(entered.wait(), 1)
    await worker[0].shutdown()
    assert worker[0].task is None


async def test_cancel_after_source_job_deleted_still_propagates_cancellation(
    services, worker, monkeypatch
):
    thread_id = make_chat(services)
    entered = asyncio.Event()

    async def blocked(*_args):
        entered.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(worker[0], "extract", blocked)
    task = asyncio.create_task(worker[0].run_once())
    await asyncio.wait_for(entered.wait(), 1)
    with services[1].session.begin() as session:
        session.delete(session.get(MemoryExtraction, thread_id))
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, 1)


def test_secret_values_never_enter_snapshot(services, worker):
    thread_id = make_chat(services)
    with services[1].session.begin() as session:
        row = session.scalar(select(Message).where(Message.thread_id == thread_id))
        row.content += ' api_key="test-only-key" Bearer private-credential-value'
    snapshot = worker[0].snapshot(thread_id, services[5].load())
    text = json.dumps(snapshot)
    assert "test-only-key" not in text and "private-credential-value" not in text
    assert "敏感值已隐藏" in json.dumps(snapshot, ensure_ascii=False)


async def test_disable_during_extraction_does_not_publish(services, worker, monkeypatch):
    make_chat(services)
    original = worker[0].extract

    async def switched(*args):
        facts = await original(*args)
        services[5].save(services[5].load().model_copy(update={"auto_memory": False}))
        return facts

    monkeypatch.setattr(worker[0], "extract", switched)
    await worker[0].run_once()
    assert not services[4].list()
    with services[1].session() as session:
        job = session.scalar(select(MemoryExtraction))
        assert job.error_code == "memory_generation_disabled"


async def test_input_changed_while_model_worked_does_not_publish(services, worker, monkeypatch):
    thread_id = make_chat(services)
    original = worker[0].invoke

    async def changed(*args, **kwargs):
        response = await original(*args, **kwargs)
        if kwargs.get("consolidate"):
            with services[1].session.begin() as session:
                row = session.scalar(select(Message).where(Message.thread_id == thread_id))
                row.content = "原始问题已编辑，不能再发布旧问题的记忆。"
        return response

    monkeypatch.setattr(worker[0], "invoke", changed)
    await worker[0].run_once()
    assert not services[4].list()
    with services[1].session() as session:
        assert session.get(MemoryExtraction, thread_id).error_code == "memory_source_changed"


def test_assistant_statement_cannot_be_saved_as_personal_preference(services, worker):
    thread_id = make_chat(services)
    snapshot = worker[0].snapshot(thread_id, services[5].load())
    assistant = next(row for row in snapshot["messages"] if row["role"] == "assistant")
    response = parse_response(
        json.dumps(
            {
                "memories": [
                    {
                        "title": "伪偏好",
                        "content": "助手猜测的偏好",
                        "kind": "preference",
                        "evidence": [
                            {"message_id": assistant["id"], "quote": assistant["content"][:10]}
                        ],
                    }
                ]
            }
        ),
        ExtractionResponse,
    )
    with pytest.raises(ValueError, match="memory_preference_requires_user"):
        validate_facts(response, snapshot["messages"], snapshot)


async def test_lost_lease_does_not_publish_stale_results(services, worker, monkeypatch):
    thread_id = make_chat(services)
    original = worker[0].invoke

    async def lost(*args, **kwargs):
        response = await original(*args, **kwargs)
        if kwargs.get("consolidate"):
            with services[1].session.begin() as session:
                session.get(MemoryExtraction, thread_id).lease_until = 0
        return response

    monkeypatch.setattr(worker[0], "invoke", lost)
    await worker[0].run_once()
    assert not services[4].list()
    with services[1].session() as session:
        assert session.get(MemoryExtraction, thread_id).error_code == "memory_lease_lost"


async def test_generated_memory_database_and_files_survive_backup_restore(
    services, worker, tmp_path
):
    from app.core.config import Paths
    from app.infrastructure.database.session import Database
    from app.infrastructure.storage.backup import create_backup
    from app.infrastructure.storage.restore import restore_backup
    from app.modules.memory.service import MemoryService

    make_chat(services)
    await worker[0].run_once()
    before = services[4].list()
    backup = create_backup(services[0])
    target = Paths(tmp_path / "restored", services[0].workspace)
    restore_backup(backup, target.data)
    database = Database(target.data / "app.sqlite3")
    try:
        restored = MemoryService(target, database, services[2])
        assert restored.list() == before
        files = list(target.memories.rglob("MEMORY.md"))
        assert len(files) == 1 and "用户希望回答" in files[0].read_text(encoding="utf-8")
        with database.session() as session:
            assert session.scalar(select(MemoryExtraction)).state == "completed"
    finally:
        database.close()
