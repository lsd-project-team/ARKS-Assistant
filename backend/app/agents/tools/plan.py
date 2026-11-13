"""计划工具：模型自己维护步骤与状态，运行详情可回看。"""

from langchain_core.tools import tool

from app.core.config import dump_json


def plan_tools(store, emit):
    @tool
    async def update_plan(items: list[dict]) -> str:
        """Replace the task plan with the given ordered items.

        Each item: {title, status: todo/doing/done/blocked, note?}. Update after each step.
        """
        try:
            plan = store.update(items)
        except ValueError as error:
            emit("plan", {"ok": False, "error": str(error)})
            return dump_json({"ok": False, "error": str(error)})
        emit("plan", {"ok": True, "items": plan})
        return dump_json({"ok": True, "items": plan})

    return [update_plan]
