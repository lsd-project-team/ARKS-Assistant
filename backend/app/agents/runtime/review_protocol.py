"""复核协议边界：区分处理失败和资料不足，供应商异常原文不外露。"""

import json
from time import monotonic

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.context.tokens import estimate_tokens
from app.agents.runtime.privacy import redact_messages
from app.core.config import dump_json
from app.infrastructure.providers.usage import reported_usage


class ReviewUnavailable(ValueError):
    pass


class ReviewCalls:
    def __init__(self, model, emit, input_limit):
        self.model, self.emit, self.input_limit = model, emit, input_limit

    async def ask(self, prompt, payload, purpose, validate):
        # 结构无效只重试一次；服务异常和输入超限不能解释为没有资料。
        hint = ""
        for attempt in range(2):
            messages = redact_messages(
                [
                    SystemMessage(content=prompt),
                    HumanMessage(content=dump_json({**payload, "protocol_hint": hint})),
                ]
            )
            if estimate_tokens(messages) > self.input_limit:
                raise ReviewUnavailable("input_budget")
            started = monotonic()
            try:
                checked = await self.model.ainvoke(
                    messages, config={"metadata": {"lc_source": purpose}}
                )
            except Exception:
                raise ReviewUnavailable("provider_error") from None
            self.emit(
                "provider_usage",
                {
                    **reported_usage(checked),
                    "purpose": purpose,
                    "duration_ms": round((monotonic() - started) * 1000),
                },
            )
            text = checked.text.strip()
            if text.startswith("```") and "\n" in text:
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            code = "empty_output" if not text else "invalid_structure"
            try:
                result = json.loads(text)
                if not isinstance(result, dict):
                    raise ValueError("object required")
                return validate(result)
            except (ValueError, KeyError, TypeError, AttributeError):
                self.emit(
                    "knowledge_stage_error",
                    {"stage": purpose, "code": code, "attempt": attempt + 1},
                )
                hint = "上次输出无法解析或字段无效。只返回要求的JSON对象，不附解释或代码围栏。"
        raise ReviewUnavailable(code)
