"""按本轮任务和实际源码工具调用追加规则，不增加模型分类请求。"""

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import SystemMessage

from app.agents.analysis.policy import REPORT_GUIDANCE
from app.agents.prompts.system import SOURCE_GUIDANCE
from app.modules.source_analysis.evidence import requires_source_evidence


class TaskGuidance(AgentMiddleware):
    def __init__(self, question, source_tools, evidence=None, *, deep=False):
        self.source_tools = frozenset(source_tools)
        self.evidence, self.deep = evidence, deep
        self.source_active = deep or requires_source_evidence(question)

    async def awrap_tool_call(self, request, handler):
        call = request.tool_call
        workspace_read = call["name"] in {"read_file", "ls", "glob", "grep"} and any(
            isinstance(value, str) and (value == "/workspace" or value.startswith("/workspace/"))
            for value in call.get("args", {}).values()
        )
        # 即使首次问法未命中源码意图，选用源码工具后也在下一次模型请求前补齐规则。
        if call["name"] in self.source_tools or workspace_read:
            self.source_active = True
        return await handler(request)

    async def awrap_model_call(self, request, handler):
        needs_source = self.source_active or bool(
            self.evidence and (self.evidence.required or self.evidence.reads)
        )
        if not needs_source:
            return await handler(request)
        sections = [SOURCE_GUIDANCE]
        if self.deep:
            sections.append(REPORT_GUIDANCE)
        # 请求级追加，不把专项规则写入聊天历史；每轮运行独立，不污染后续普通问答。
        system = request.system_message
        content = list(system.content_blocks) if system else []
        content.append({"type": "text", "text": "\n" + "\n".join(sections)})
        prompt = (
            system.model_copy(update={"content": content})
            if system
            else SystemMessage(content=content)
        )
        return await handler(request.override(system_message=prompt))
