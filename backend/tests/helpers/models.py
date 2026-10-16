"""可确定复现的测试模型，不发起真实供应商请求。"""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class DeterministicModel(BaseChatModel):
    """仅用于框架回归，不作为供应商连通性验证。"""

    @property
    def _llm_type(self):
        return "deterministic-test"

    def bind_tools(self, _tools, **_kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        summary_request = "Context Extraction" in str(messages[0].content)
        content = (
            "目标：保持中文回答；已讨论入口；待办：继续读取源码。"
            if summary_request
            else "测试回复"
        )
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])
