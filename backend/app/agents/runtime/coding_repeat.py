"""编码工具重复调用保护：同样的检查或命令连续执行三次就拦截，避免空转。"""

import json

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import SystemMessage, ToolMessage

GUARDED = {
    "list_files",
    "read_project_file",
    "search_files",
    "find_files",
    "run_command",
    "read_process",
    "list_checkpoints",
    "diff_checkpoint",
}
PROGRESS = {
    "write_file",
    "edit_file",
    "multi_edit",
    "write_binary_file",
    "create_directory",
    "move_path",
    "delete_path",
    "checkpoint",
    "restore_checkpoint",
    "start_process",
    "stop_process",
}
LOOP_LIMIT = 12


class CodingRepeatGuard(AgentMiddleware):
    def __init__(self, emit, limit=3, total_limit=150):
        self.emit = emit
        self.limit = limit
        self.total_limit = total_limit
        self.total = 0
        self.counts = {}
        self.cached = {}
        self.blocked_streak = 0

    async def awrap_model_call(self, request, handler):
        repeated = [
            (key[0], key[1], count)
            for key, count in self.counts.items()
            if count > 10
        ]
        if self.blocked_streak < 2 and not repeated:
            return await handler(request)
        if repeated:
            tool, args, count = repeated[0]
            guidance = (
                f"\n【重复读取限制】{tool} 的同一参数已被请求 {count} 次（{args[:120]}）。"
                "不要再读取同一内容：基于已有信息直接写文件/Actions.cs，或调用 update_plan "
                "标记完成并结束；继续重复读取不会得到新信息。"
            )
        else:
            guidance = (
                "\n【重复调用保护】同一工具调用已被拦截多次，不要再读同一段内容。"
                "直接修改或删除失败的自测、换一个命令/路径，或者结束本轮并说明未完成项。"
            )
        system = request.system_message
        blocks = list(system.content_blocks) if system else []
        blocks.append({"type": "text", "text": guidance})
        prompt = (
            system.model_copy(update={"content": blocks})
            if system
            else SystemMessage(content=blocks)
        )
        return await handler(request.override(system_message=prompt))

    async def awrap_tool_call(self, request, handler):
        name = request.tool_call["name"]
        if name in GUARDED or name in PROGRESS:
            self.total += 1
            if self.total > self.total_limit:
                self.blocked_streak += 1
                self.emit("coding_budget_blocked", {"total": self.total})
                return _blocked(
                    request,
                    name,
                    {
                        "ok": False,
                        "budget_exhausted": True,
                        "note": (
                            "本轮编码工具调用已达上限。请停止继续探查，"
                            "基于已有结果总结完成情况、未完成项和下一步建议。"
                        ),
                    },
                )
        if name in PROGRESS:
            self.counts.clear()
            self.cached.clear()
            self.blocked_streak = 0
            return await handler(request)
        if name not in GUARDED:
            return await handler(request)
        arguments = json.dumps(
            request.tool_call.get("args", {}), sort_keys=True, ensure_ascii=False
        )
        key = (name, arguments)
        count = self.counts.get(key, 0) + 1
        self.counts[key] = count
        if count < self.limit:
            result = await handler(request)
            if not _failed(result):
                self.cached[key] = _reusable(result)
            return result
        if key in self.cached:
            # 重复读取直接返回上次内容，但必须换成当前调用的 tool_call_id，
            # 否则会出现“tool_result 找不到对应 tool_use”的 400。
            self.emit("coding_repeat_cached", {"tool": name, "count": count})
            self.blocked_streak = 0
            cached = self.cached[key]
            return cached.model_copy(update={"tool_call_id": request.tool_call["id"]})
        result = await handler(request)
        if not _failed(result):
            self.cached[key] = _reusable(result)
        return result


def _failed(result):
    return getattr(result, "status", "success") == "error"


def _reusable(result):
    try:
        return result.model_copy(
            update={
                "content": result.text
                or "（同一调用已执行过，返回上次相同结果；请基于该结果继续，不要重复读取。）",
                "additional_kwargs": {**getattr(result, "additional_kwargs", {}), "cached": True},
            }
        )
    except AttributeError:
        return result


def _blocked(request, name, payload):
    return ToolMessage(
        content=json.dumps(payload, ensure_ascii=False),
        tool_call_id=request.tool_call["id"],
        name=name,
        status="error",
    )
