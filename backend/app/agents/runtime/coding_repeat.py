"""编码工具重复调用保护：同样的检查或命令连续执行三次就拦截，避免空转。"""

import json

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import ToolMessage

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


class CodingRepeatGuard(AgentMiddleware):
    def __init__(self, emit, limit=3, total_limit=150):
        self.emit = emit
        self.limit = limit
        self.total_limit = total_limit
        self.total = 0
        self.counts = {}

    async def awrap_tool_call(self, request, handler):
        name = request.tool_call["name"]
        if name in GUARDED or name in PROGRESS:
            self.total += 1
            if self.total > self.total_limit:
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
            return await handler(request)
        self.emit("coding_repeat_blocked", {"tool": name, "count": count})
        return _blocked(
            request,
            name,
            {
                "ok": False,
                "repeated": True,
                "note": (
                    "相同的工具调用已经连续执行三次，本次已拦截。"
                    "请改用已有结果，直接写文件、创建工程或运行构建；"
                    "需要不同信息时改变路径、范围或命令。"
                ),
            },
        )


def _blocked(request, name, payload):
    return ToolMessage(
        content=json.dumps(payload, ensure_ascii=False),
        tool_call_id=request.tool_call["id"],
        name=name,
    )
