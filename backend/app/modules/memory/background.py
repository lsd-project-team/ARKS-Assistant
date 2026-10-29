"""聊天提取与整理分阶段持久化，不在回答里即时写记忆。"""

import asyncio
import json
import logging
import time
from contextlib import suppress

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import update
from sqlalchemy.dialects.sqlite import insert

from app.agents.context.tokens import estimate_tokens, input_budget
from app.agents.runtime.model_budget import ProjectModelBudget
from app.core.config import dump_json
from app.core.identifiers import new_id, now_iso
from app.infrastructure.providers.models import close_models, create_model
from app.modules.auth.context import request_identity
from app.modules.memory.candidates import candidate_threads, snapshot_thread
from app.modules.memory.generated_store import GeneratedMemoryStore, archive_legacy_memories
from app.modules.memory.generation_protocol import (
    CONSOLIDATE_PROMPT,
    EXTRACT_PROMPT,
    ConsolidationResponse,
    ExtractionResponse,
    grouped_document,
    parse_response,
    sanitized,
    validate_facts,
)
from app.modules.memory.models import MemoryExtraction
from app.modules.settings.model_preferences import ModelPreferences

logger = logging.getLogger(__name__)


class BackgroundMemories:
    def __init__(self, services, *, runtime_for=None):
        self.services = services
        self.store = GeneratedMemoryStore(services.paths, services.database)
        self.task = None
        self.lock = asyncio.Lock()
        self.runtime_for = runtime_for or (lambda _scope: services.runtime)

    def ledger(self, scope):
        return self.runtime_for(scope).model_ledger

    def start(self):
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self._loop(), name="background-memory")

    async def shutdown(self):
        if self.task:
            self.task.cancel()
            with suppress(asyncio.CancelledError):
                await self.task
            self.task = None

    async def _loop(self):
        token = request_identity.set(None)
        try:
            while True:
                try:
                    await self.run_once()
                except Exception as error:
                    logger.warning("后台记忆调度失败：%s", type(error).__name__)
                await asyncio.sleep(self.services.settings.load().memory_generation.poll_seconds)
        finally:
            request_identity.reset(token)

    def snapshot(self, identifier, config, *, require_idle=True):
        return snapshot_thread(
            self.services.database,
            identifier,
            config.memory_generation,
            require_idle=require_idle,
            secrets=[profile.config.api_key for profile in config.model_profiles],
        )

    def claim(self, snapshot, now):
        token = new_id()
        with self.services.database.session.begin() as session:
            session.execute(
                insert(MemoryExtraction)
                .values(
                    thread_id=snapshot["thread_id"],
                    owner_id=snapshot["owner_id"],
                    workspace_id=snapshot["workspace_id"],
                    fingerprint=snapshot["fingerprint"],
                    state="pending",
                    raw_json="",
                    attempts=0,
                    lease_token="",
                    lease_until=0,
                    retry_after=0,
                    error_code="",
                )
                .on_conflict_do_nothing()
            )
            row = session.get(MemoryExtraction, snapshot["thread_id"])
            if row.lease_until > now:
                return None
            same = row.fingerprint == snapshot["fingerprint"]
            if same and (row.state == "completed" or row.retry_after > now):
                return None
            raw = row.raw_json if same else ""
            claimed = session.execute(
                update(MemoryExtraction)
                .where(
                    MemoryExtraction.thread_id == snapshot["thread_id"],
                    MemoryExtraction.lease_until <= now,
                )
                .values(
                    owner_id=snapshot["owner_id"],
                    workspace_id=snapshot["workspace_id"],
                    fingerprint=snapshot["fingerprint"],
                    state="running",
                    raw_json=raw,
                    attempts=row.attempts + 1 if same else 1,
                    lease_token=token,
                    lease_until=now + 3600,
                    error_code="",
                    updated_at=now_iso(),
                )
            )
            return (token, json.loads(raw) if raw else None) if claimed.rowcount == 1 else None

    def update_job(self, snapshot, token, **values):
        with self.services.database.session.begin() as session:
            result = session.execute(
                update(MemoryExtraction)
                .where(
                    MemoryExtraction.thread_id == snapshot["thread_id"],
                    MemoryExtraction.fingerprint == snapshot["fingerprint"],
                    MemoryExtraction.lease_token == token,
                )
                .values(**values, updated_at=now_iso())
            )
            if result.rowcount != 1:
                raise ValueError("memory_lease_lost")

    def has_budget(self, ledger, config):
        limit = ledger.get().token_limit
        used = ledger.tokens()["reserved_tokens"]
        return limit is None or (limit - used) * 100 >= (
            limit * config.memory_generation.min_remaining_percent
        )

    async def invoke(self, config, ledger, prompt, payload, *, consolidate=False):
        policy = config.memory_generation
        model_name = policy.consolidation_model if consolidate else policy.extract_model
        settings = config.model.model_copy(
            update={
                "model": model_name or config.model.summary_model or config.model.model,
                "output_tokens": min(config.model.output_tokens, 4096),
            }
        )
        messages = [SystemMessage(content=prompt), HumanMessage(content=dump_json(payload))]
        if estimate_tokens(messages) > input_budget(
            settings.context_tokens, settings.output_tokens
        ):
            raise ValueError("memory_input_too_large")
        if not self.has_budget(ledger, config):
            raise ValueError("memory_budget_deferred")
        model = create_model(settings)
        model.callbacks = [
            *(getattr(model, "callbacks", None) or []),
            ProjectModelBudget(
                ledger,
                settings.context_tokens,
                output_tokens=settings.output_tokens,
            ),
        ]
        try:
            response = await asyncio.wait_for(
                model.ainvoke(messages),
                timeout=settings.timeout_seconds + 5,
            )
            return sanitized(
                response.text, [profile.config.api_key for profile in config.model_profiles]
            )
        finally:
            await close_models([model])

    def chunks(self, snapshot, config):
        limit = input_budget(config.model.context_tokens, config.model.output_tokens) // 2
        batches, current = [], []
        for message in snapshot["messages"]:
            text = message["content"]
            width = max(128, limit // 2)
            for offset in range(0, len(text), width):
                part = {**message, "content": text[offset : offset + width]}
                if (
                    current
                    and estimate_tokens([HumanMessage(content=dump_json([*current, part]))]) > limit
                ):
                    batches.append(current)
                    current = []
                current.append(part)
        return [*batches, *([current] if current else [])]

    async def extract(self, snapshot, config, ledger):
        indexed = {}
        for chunk in self.chunks(snapshot, config):
            response = parse_response(
                await self.invoke(config, ledger, EXTRACT_PROMPT, chunk), ExtractionResponse
            )
            for fact in validate_facts(response, chunk, snapshot):
                indexed[fact["id"]] = fact
        return list(indexed.values())

    def current_facts(self, snapshot, config):
        facts, snapshots = [], {}
        rows = self.store.inputs(snapshot["owner_id"], snapshot["workspace_id"])
        previous = self.store.bundle(snapshot["owner_id"], snapshot["workspace_id"])
        if previous:
            # 整理新输入时也保留既有长期成果，不能因原始输入窗口轮换丢失稳定认识。
            rows += [
                {
                    "thread_id": fact["thread_id"],
                    "fingerprint": fact["fingerprint"],
                    "facts": [fact],
                }
                for group in previous["document"]["groups"]
                for fact in group["memories"]
            ]
        for row in rows:
            identifier = row["thread_id"]
            if identifier not in snapshots:
                snapshots[identifier] = self.snapshot(identifier, config, require_idle=False)
            current = snapshots[identifier]
            if current and current["fingerprint"] == row["fingerprint"]:
                facts.extend(row["facts"])
        return list({row["id"]: row for row in facts}.values())

    async def process(self, snapshot, config, ledger, claim):
        token, facts = claim
        try:
            if facts is None:
                facts = await self.extract(snapshot, config, ledger)
                self.update_job(snapshot, token, raw_json=dump_json(facts), state="extracted")
            previous = self.store.bundle(snapshot["owner_id"], snapshot["workspace_id"])
            revision = previous["revision"] if previous else 0
            all_facts = self.current_facts(snapshot, config)
            groups = []
            for chunk in self.fact_chunks(all_facts, config):
                response = parse_response(
                    await self.invoke(
                        config,
                        ledger,
                        CONSOLIDATE_PROMPT,
                        chunk,
                        consolidate=True,
                    ),
                    ConsolidationResponse,
                )
                groups.extend(grouped_document(response, chunk)["groups"])
            current = self.snapshot(snapshot["thread_id"], self.services.settings.load())
            if not current or current["fingerprint"] != snapshot["fingerprint"]:
                raise ValueError("memory_source_changed")
            if not self.services.settings.load().auto_memory:
                raise ValueError("memory_generation_disabled")
            with self.services.memories.lock:
                self.store.publish(
                    snapshot, {"groups": groups}, lease_token=token, expected_revision=revision
                )
        except asyncio.CancelledError:
            self.update_job(snapshot, token, state="pending", lease_until=0)
            raise
        except Exception as error:
            code = str(error) if str(error).startswith("memory_") else type(error).__name__
            self.update_job(
                snapshot,
                token,
                state="failed",
                lease_until=0,
                retry_after=time.time() + 300,
                error_code=code[:64],
            )

    def fact_chunks(self, facts, config):
        limit = input_budget(config.model.context_tokens, config.model.output_tokens) // 2
        chunks, current = [], []
        for fact in facts:
            if (
                current
                and estimate_tokens([HumanMessage(content=dump_json([*current, fact]))]) > limit
            ):
                chunks.append(current)
                current = []
            current.append(fact)
        return [*chunks, *([current] if current else [])]

    async def run_once(self):
        if self.lock.locked():
            return
        async with self.lock:
            config = self.services.settings.load()
            if not config.auto_memory:
                return
            identifiers = await asyncio.to_thread(
                candidate_threads, self.services.database, config.memory_generation
            )
            processed = 0
            for identifier in identifiers:
                if processed >= config.memory_generation.max_chats_per_pass:
                    break
                snapshot = await asyncio.to_thread(self.snapshot, identifier, config)
                if not snapshot:
                    continue
                config = ModelPreferences(
                    self.services.database, self.services.settings
                ).configuration(snapshot["owner_id"] if snapshot["owner_id"] != "local" else None)
                if not config.auto_memory or not config.model.api_key or not config.model.model:
                    continue
                ledger = self.ledger(snapshot["workspace_id"])
                if not await asyncio.to_thread(self.has_budget, ledger, config):
                    continue
                claim = await asyncio.to_thread(self.claim, snapshot, time.time())
                if claim:
                    processed += 1
                    await self.process(snapshot, config, ledger, claim)

    def initialize(self):
        return archive_legacy_memories(self.services.paths)
