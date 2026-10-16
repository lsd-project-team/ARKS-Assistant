"""仅依据供应商结束原因续写；缺失原因的疑似截断不能冒充完整回答。"""

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import AIMessage, HumanMessage

from app.infrastructure.providers.usage import reported_usage


def termination(message, limit):
    metadata = getattr(message, "response_metadata", {})
    reason = metadata.get("stop_reason") or metadata.get("finish_reason")
    if reason in {"max_tokens", "length", "MAX_TOKENS"}:
        state = "incomplete"
    elif not reason and (reported_usage(message).get("output_tokens") or 0) >= limit:
        state = "suspected_truncated"
    elif reason and reason not in {"stop", "end_turn", "stop_sequence", "tool_calls", "tool_use"}:
        state = "incomplete"
    else:
        state = "complete"
    return {"output": state, "finish_reason": reason, "output_limit": limit}


def merge_continuation(previous, following):
    if following.startswith(previous):
        return following
    # 模型可能重复末尾的一段；只去掉边界处的明确重复，不改写正文。
    for size in range(min(len(previous), len(following), 4000), 3, -1):
        candidate = following[:size]
        sufficient = size >= 12 or sum("\u4e00" <= char <= "\u9fff" for char in candidate) >= 4
        if sufficient and previous[-size:] == candidate:
            return previous + following[size:]
    return previous + following


def final_message(response):
    return next((item for item in reversed(response.result) if isinstance(item, AIMessage)), None)


class AnswerCompletion(AgentMiddleware):
    def __init__(self, emit, output_limit, max_continuations=2):
        self.emit, self.output_limit = emit, output_limit
        self.max_continuations, self.used = max_continuations, 0

    async def awrap_model_call(self, request, handler):
        response = await handler(request)
        answer = final_message(response)
        if answer is None or answer.tool_calls:
            return response
        state = termination(answer, self.output_limit)
        merged = answer.text
        while (
            state["output"] == "incomplete"
            and state["finish_reason"] in {"max_tokens", "length", "MAX_TOKENS"}
            and self.used < self.max_continuations
        ):
            self.used += 1
            self.emit(
                "stage",
                {
                    "stage": "continuing_answer",
                    "detail": f"自动续写 {self.used}/{self.max_continuations}",
                },
            )
            self.emit(
                "answer_completion", {**state, "continuations": self.used, "continuing": True}
            )
            choice = {"type": "none"} if "anthropic" in request.model._llm_type else "none"
            response = await handler(
                request.override(
                    tool_choice=choice,
                    messages=[
                        *request.messages,
                        answer.model_copy(update={"content": merged}),
                        HumanMessage(
                            content="系统输出恢复：上一段因输出长度上限停止。只从断点接着写完原问题的回答，不重述开头，不重复已写内容，不新增检索或猜测。"
                        ),
                    ],
                )
            )
            answer = final_message(response)
            if answer is None or answer.tool_calls:
                state = {**state, "output": "incomplete"}
                break
            merged = merge_continuation(merged, answer.text)
            state = termination(answer, self.output_limit)
        if answer is not None:
            answer.content = merged
            answer.additional_kwargs["answer_completion"] = {**state, "continuations": self.used}
        self.emit("answer_completion", {**state, "continuations": self.used, "continuing": False})
        self.emit("answer_replace", {"text": merged})
        return response
