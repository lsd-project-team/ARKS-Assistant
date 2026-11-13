"""运行级任务计划：从零生成或长任务时保持步骤可追踪。"""

import threading

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import SystemMessage

STATUSES = {"todo", "doing", "done", "blocked"}


class PlanStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._items = []

    def update(self, items):
        normalized = []
        for index, item in enumerate(items or [], 1):
            if not isinstance(item, dict):
                raise ValueError("计划项必须是对象")
            title = str(item.get("title") or "").strip()
            if not title:
                raise ValueError("计划项标题不能为空")
            status = str(item.get("status") or "todo")
            if status not in STATUSES:
                raise ValueError("计划状态只能是 todo/doing/done/blocked")
            normalized.append(
                {
                    "id": str(item.get("id") or index)[:40],
                    "title": title[:200],
                    "status": status,
                    "note": str(item.get("note") or "")[:300],
                }
            )
        if not normalized:
            raise ValueError("计划不能为空")
        with self._lock:
            self._items = normalized
        return self.snapshot()

    def snapshot(self):
        with self._lock:
            return [dict(item) for item in self._items]

    def complete(self):
        items = self.snapshot()
        return bool(items) and all(item["status"] in {"done", "blocked"} for item in items)

    def text(self):
        items = self.snapshot()
        if not items:
            return ""
        lines = ["【当前任务计划】"]
        for item in items:
            mark = {"todo": "待办", "doing": "进行中", "done": "完成", "blocked": "受阻"}[
                item["status"]
            ]
            note = f"（{item['note']}）" if item["note"] else ""
            lines.append(f"- [{mark}] {item['title']}{note}")
        pending = [item["title"] for item in items if item["status"] not in {"done", "blocked"}]
        if pending:
            lines.append(
                "未完成：" + "；".join(pending) + "。完成一步后调用 update_plan 更新状态。"
            )
        return "\n".join(lines)


class PlanGuidance(AgentMiddleware):
    """把当前计划附在系统提示里；从零生成时要求先建计划。"""

    def __init__(self, store, generation=False):
        self.store, self.generation = store, generation

    async def awrap_model_call(self, request, handler):
        text = self.store.text()
        if not text and self.generation:
            text = (
                "【任务计划】本轮是从零生成，先调用 update_plan 建立 4-7 步计划，"
                "再按计划推进；每完成一步更新状态。"
            )
        if not text:
            return await handler(request)
        system = request.system_message
        blocks = list(system.content_blocks) if system else []
        blocks.append({"type": "text", "text": "\n" + text})
        prompt = (
            system.model_copy(update={"content": blocks})
            if system
            else SystemMessage(content=blocks)
        )
        return await handler(request.override(system_message=prompt))
