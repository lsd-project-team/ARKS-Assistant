"""经验资料先独立筛选，只有程序取回的选定原文进入回答上下文。"""

import asyncio

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.context.tokens import estimate_tokens
from app.agents.runtime.knowledge_scope import (
    SELECTION_GUIDANCE,
    selection_input,
    selection_result,
)
from app.agents.runtime.review_protocol import ReviewCalls, ReviewUnavailable
from app.core.config import dump_json
from app.modules.knowledge.corpora.debug_issues import ANSWER_GUIDANCE, debug_issue_tools
from app.modules.knowledge.feedback import references


class KnowledgeSelection:
    def __init__(self, model, question, emit, input_limit):
        self.question, self.emit = question, emit
        self.calls = ReviewCalls(model, emit, input_limit)

    def payload(self, records):
        return {"question": self.question, "records": selection_input(records)}

    def batches(self, records):
        batches, current = [], []
        for record in records:
            candidate = [*current, record]
            messages = [
                SystemMessage(content=SELECTION_GUIDANCE),
                HumanMessage(content=dump_json(self.payload(candidate))),
            ]
            # 为协议修复提示留出余量；单条超限由 ReviewCalls 明确报告处理失败。
            if current and estimate_tokens(messages) + 128 > self.calls.input_limit:
                batches.append(current)
                current = []
            current.append(record)
        return [*batches, *([current] if current else [])]

    async def select(self, records):
        self.emit("stage", {"stage": "checking_sources", "detail": "选择符合本题的资料片段"})
        selected, scopes = [], []
        for batch in self.batches(records):
            scope, rows = await self.calls.ask(
                SELECTION_GUIDANCE,
                self.payload(batch),
                "knowledge_selection",
                lambda result, batch=batch: selection_result(result, batch),
            )
            scopes.append(scope)
            selected.extend(rows)
        scope = "records" if "records" in scopes else "general"
        self.emit(
            "knowledge_selection",
            {"scope": scope, "references": [row["reference"] for row in selected]},
        )
        return scope, selected


class KnowledgeRetrieval:
    """每轮共用固定快照、筛选缓存和已公开范围，检索及按编号读取均经过此边界。"""

    def __init__(self, lookup, model, question, emit, input_limit, *, timeout=30):
        self.lookup, self.emit, self.timeout = lookup, emit, timeout
        self.selector = KnowledgeSelection(model, question, emit, input_limit)
        self._choices, self._contexts, self._scopes = {}, {}, {}
        self._scope = "general"
        self._lock = asyncio.Lock()

    def selected(self):
        rows = [row for row in self._choices.values() if row is not None]
        return ("records" if rows else self._scope), rows

    def review_records(self):
        return list(self._contexts.values())

    async def _select(self, records):
        # 并行工具不能重复筛选同版本，也不能公开尚未通过整次筛选的部分结果。
        async with self._lock:
            if not records:
                self._scope = "records"
                return [], "none"
            fresh = [row for row in records if row["reference"] not in self._choices]
            if fresh:
                try:
                    async with asyncio.timeout(self.timeout):
                        scope, chosen = await self.selector.select(fresh)
                except (ReviewUnavailable, TimeoutError) as error:
                    code = str(error) if isinstance(error, ReviewUnavailable) else "timeout"
                    self.emit(
                        "knowledge_stage_error", {"stage": "knowledge_selection", "code": code}
                    )
                    self._scope = "unavailable"
                    return [], "unavailable"
                allowed = {row["reference"]: row for row in chosen}
                for row in fresh:
                    selected = allowed.get(row["reference"])
                    self._choices[row["reference"]] = selected
                    self._scopes[row["reference"]] = scope
                    if selected is not None:
                        self._contexts[row["reference"]] = row
                        references(self.emit, "debug_issue", [selected])
            chosen = [
                self._choices[row["reference"]]
                for row in records
                if self._choices.get(row["reference"]) is not None
            ]
            self._scope = (
                "records"
                if any(self._scopes[row["reference"]] == "records" for row in records)
                else "general"
            )
            return chosen, "selected" if chosen else "none"

    @staticmethod
    def report(rows, status):
        return {
            "kind": "debug_issue",
            "matched": len(rows),
            "selection_status": status,
            "matches": rows,
            "notice": (
                "资料筛选暂未完成，未经筛选的候选未提供；这是处理失败，不代表资料库没有相关记录。"
                if status == "unavailable"
                else "仅返回本题选定的原文片段；未选中不代表资料库没有其他历史记录。"
            ),
            **({"display_hint": ANSWER_GUIDANCE} if rows else {}),
        }

    async def search_report(self, query, limit=6, **conditions):
        report = await asyncio.to_thread(
            self.lookup.search_report, query, limit, track=False, **conditions
        )
        identifiers = [row["id"] for row in [*report["matches"], *report["excluded_records"]]]
        records = await asyncio.to_thread(self.lookup.snapshot_records, identifiers)
        rows, status = await self._select(records)
        return self.report(rows, status)

    async def read(self, record_id, offset=0):
        if offset < 0:
            raise ValueError("原文偏移不能小于零")
        records = await asyncio.to_thread(self.lookup.snapshot_records, [record_id])
        if not records:
            raise ValueError("该调试记录不在本轮可用问题库中")
        rows, status = await self._select(records)
        if not rows:
            return {**self.report([], status), "content": "", "next_offset": None}
        row = rows[0]
        content = dump_json(row["content"])
        return {
            **{key: value for key, value in row.items() if key != "content"},
            "selection_status": status,
            "content": content[offset : offset + 8000],
            "next_offset": offset + 8000 if offset + 8000 < len(content) else None,
            "display_hint": ANSWER_GUIDANCE,
        }

    async def resolve_references(self, requested):
        versions = {}
        for value in requested:
            identifier, version = value.removeprefix("debug-issue:").rsplit("/", 1)
            versions[identifier] = int(version)
        records = await asyncio.to_thread(self.lookup.snapshot_records, versions)
        records = [row for row in records if row["version"] == versions[row["id"]]]
        if not records:
            self._scope = "unavailable"
            return []
        rows, _ = await self._select(records)
        return rows

    def tools(self):
        return debug_issue_tools(self.lookup, search=self.search_report, read=self.read)
