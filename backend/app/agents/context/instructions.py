"""全局文件作为用户指令进入每次主模型请求，不写进聊天检查点或长期记忆。"""

from contextlib import contextmanager
from contextvars import ContextVar

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import HumanMessage

from app.modules.memory.identity import user_memory_owner
from app.modules.settings.agent_instructions import AgentInstructionsStore

_current = ContextVar("run_agent_instructions", default=None)
INSTRUCTION_MESSAGE_ID = "global-agent-instructions"


@contextmanager
def bind_agent_instructions(snapshot):
    token = _current.set(snapshot)
    try:
        yield
    finally:
        _current.reset(token)


def instruction_snapshot(paths):
    owner = user_memory_owner()
    if (snapshot := _current.get()) is not None:
        if snapshot["owner_id"] != owner:
            raise ValueError("全局指令不属于当前执行账号")
        return snapshot
    return AgentInstructionsStore(paths.data).read(owner)


def instruction_messages(snapshot):
    if not snapshot or not snapshot["content"].strip():
        return []
    return [
        HumanMessage(
            id=INSTRUCTION_MESSAGE_ID,
            content="# 全局 agent.md 指令\n"
            "以下为当前账号预设的长期用户指令，适用于该账号的所有项目和独立对话。"
            "当前问题中的明确要求优先；这些指令不能改变系统权限、工具边界或事实核查要求。\n\n"
            + snapshot["content"],
        )
    ]


class GlobalAgentInstructions(AgentMiddleware):
    def __init__(self, snapshot):
        self.snapshot = snapshot

    async def awrap_model_call(self, request, handler):
        messages = instruction_messages(self.snapshot)
        if not messages:
            return await handler(request)
        # 在摘要完成后补入，避免压缩或恢复时丢失；当前用户问题始终在它后面。
        history = [row for row in request.messages if row.id != INSTRUCTION_MESSAGE_ID]
        return await handler(request.override(messages=[*messages, *history]))
