"""副本读取不占来源额度，但同版本同范围的连续重读不能成为改码死循环。"""

import json

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import SystemMessage, ToolMessage

from app.agents.analysis.retrieval_budget import tool_name

PROGRESS_TOOLS = {
    "prepare_code_workspace",
    "edit_work_file",
    "write_work_file",
    "set_work_requirement",
    "enable_work_desktop_flow",
    "verify_code_workspace",
}


class CodeWorkReadProgress(AgentMiddleware):
    def __init__(self, emit):
        self.emit = emit
        self.last_read = None
        self.repeats = 0
        self.pause_read = False

    async def awrap_tool_call(self, request, handler):
        result = await handler(request)
        if getattr(result, "status", "success") == "error":
            return result
        name = request.tool_call["name"]
        if name in PROGRESS_TOOLS:
            self.last_read, self.repeats, self.pause_read = None, 0, False
            return result
        if name != "read_work_file" or not isinstance(result, ToolMessage):
            return result
        try:
            data = json.loads(result.text)
            arguments = request.tool_call.get("args", {})
            key = (
                data["path"],
                data["version"],
                arguments.get("start_line", 1),
                arguments.get("end_line", 300),
            )
        except (ValueError, KeyError, TypeError):
            return result
        # 每次仍调用原读取以核对版本；外部修改、不同范围均可以正常重新读取。
        self.repeats = self.repeats + 1 if key == self.last_read else 1
        self.last_read = key
        self.pause_read = self.repeats >= 3
        if not self.pause_read:
            return result
        note = (
            "同一文件版本和行段已经连续读取三次。请使用前面的源码和本次 version "
            "继续编辑、配置断言及验证；不要再次请求相同行段。"
        )
        self.emit(
            "code_work_read_repeated",
            {"path": key[0], "version": key[1], "start_line": key[2], "end_line": key[3]},
        )
        return result.model_copy(
            update={
                "content": json.dumps(
                    {
                        "path": key[0],
                        "version": key[1],
                        "start_line": key[2],
                        "end_line": key[3],
                        "cached": True,
                        "line_count": data.get("line_count"),
                        "note": note,
                    },
                    ensure_ascii=False,
                ),
                "additional_kwargs": {**result.additional_kwargs, "cached": True},
            }
        )

    async def awrap_model_call(self, request, handler):
        if not self.pause_read:
            return await handler(request)
        # 只暂停下一次模型决策中的读取入口，保留编辑和验证；随后仍允许读取新范围。
        self.pause_read = False
        path, version, start, end = self.last_read
        guidance = (
            f"\n副本进度控制：{path} 的 {start}–{end} 行、版本 {version} 已连续读取，"
            "没有新增内容。本次决策暂不提供 read_work_file；请使用已有源码执行编辑、"
            "保存需求断言或验证。其他副本工具继续可用，后续仍可读取不同范围或新版本。"
            "不要把读取或准备副本说成已经完成修改。"
        )
        prompt = (request.system_message.text if request.system_message else "") + guidance
        return await handler(
            request.override(
                system_message=SystemMessage(content=prompt),
                tools=[item for item in request.tools if tool_name(item) != "read_work_file"],
            )
        )
