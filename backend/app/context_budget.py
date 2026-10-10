"""沿用原生历史压缩；在请求边界校验预算并记录实际配置的估算明细。"""

from deepagents.middleware.summarization import SummarizationMiddleware
from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.exceptions import ContextOverflowError
from langchain_core.messages import HumanMessage

from app.context import estimate_tokens, input_budget, request_budget


class BudgetedSummarization(SummarizationMiddleware):
    def __init__(self, *args, limit: int, output: int, emit, memory_prompt="", **kwargs):
        super().__init__(*args, **kwargs)
        self.limit, self.output, self.emit = limit, output, emit
        self.memory_prompt = memory_prompt

    @property
    def name(self):
        # Deep Agents 按名称替换默认中间件，避免同时运行两套摘要策略。
        return "SummarizationMiddleware"

    def _input_budget(self, _request):
        return input_budget(self.limit, self.output)

    async def awrap_model_call(self, request, handler):
        effective = request.override(messages=self._get_effective_messages(request))
        snapshot = request_budget(effective, self.limit, self.output, self.memory_prompt)
        self.emit("context_budget", {**snapshot, "phase": "before_compaction"})
        return await super().awrap_model_call(request, handler)

    async def _acreate_summary(self, messages):
        self.emit("stage", {"stage": "compacting"})
        self.emit("compaction", {"text": "正在压缩完整请求上下文，原始对话保留"})
        helper = self._lc_helper
        trimmed = False
        while True:
            selected = helper._trim_messages_for_summary(messages)
            prompt = helper._format_summary_prompt(selected)
            if estimate_tokens([HumanMessage(content=prompt)]) <= input_budget(
                self.limit, self.output
            ):
                break
            old = helper.trim_tokens_to_summarize
            if not old or old <= 1:
                raise ContextOverflowError("压缩提示本身超过 context token 预算，请增大上下文配置")
            # XML 包装和摘要指令也占空间；按实际生成的提示反复校验，不仅看历史正文。
            helper.trim_tokens_to_summarize = max(1, int(old * 0.75))
            trimmed = True
        if trimmed:
            self.emit(
                "compaction",
                {"text": "摘要请求已按预算缩短，完整历史仍保存在原文档案中"},
            )
        return await super()._acreate_summary(messages)


class ContextBudget(AgentMiddleware):
    def __init__(self, limit: int, output: int, memory_prompt: str, emit):
        self.limit, self.output = limit, output
        self.memory_prompt, self.emit = memory_prompt, emit

    async def awrap_model_call(self, request, handler):
        budget = {
            **request_budget(request, self.limit, self.output, self.memory_prompt),
            "phase": "model_request",
        }
        self.emit("context_budget", budget)
        self.emit("context", budget)
        if budget["tokens"] > budget["input_limit"]:
            # 外层原生摘要中间件可尝试压缩；仍超量时不向供应商发送已知过大的请求。
            raise ContextOverflowError(
                f"context token 估算 {budget['tokens']} 超过输入预算 {budget['input_limit']}；"
                "请减少选区或工具定义、调整记忆，或增大上下文配置。原始问题和选区已保留。"
            )
        return await handler(request)
