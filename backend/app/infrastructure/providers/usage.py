"""仅记录供应商实际返回的用量；没有数据时明确未知，不拿估算冒充。"""

from time import monotonic

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage


def reported_usage(message):
    usage = getattr(message, "usage_metadata", None)
    if not usage:
        metadata = getattr(message, "response_metadata", {})
        usage = metadata.get("usage") or metadata.get("token_usage") or {}
    result = {}
    fields = {
        "input_tokens": ("input_tokens", "prompt_tokens"),
        "output_tokens": ("output_tokens", "completion_tokens"),
        "total_tokens": ("total_tokens",),
    }
    for name, aliases in fields.items():
        value = next((usage[key] for key in aliases if key in usage), None)
        result[name] = (
            value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None
        )
    result["reported"] = result["input_tokens"] is not None and result["output_tokens"] is not None
    if result["reported"] and result["total_tokens"] is None:
        result["total_tokens"] = result["input_tokens"] + result["output_tokens"]
    details = usage.get("input_token_details") or {}
    result["cache_read_tokens"] = details.get("cache_read", usage.get("cache_read_input_tokens"))
    return result


def failed_usage(purpose, started):
    return {
        "purpose": purpose,
        "status": "failed",
        "reported": False,
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
        "duration_ms": round((monotonic() - started) * 1000),
    }


class ProviderUsage(AgentMiddleware):
    def __init__(self, emit):
        self.emit = emit
        self.request_number = 0

    async def awrap_model_call(self, request, handler):
        started = monotonic()
        self.request_number += 1
        number = self.request_number
        try:
            response = await handler(request)
        except Exception:
            self.emit("provider_usage", failed_usage("answer", started))
            raise
        message = next((item for item in response.result if isinstance(item, AIMessage)), None)
        if message:
            self.emit(
                "provider_usage",
                {
                    **reported_usage(message),
                    "request": number,
                    "purpose": "answer",
                    "duration_ms": round((monotonic() - started) * 1000),
                    "finish_reason": message.response_metadata.get("finish_reason"),
                    "stop_reason": message.response_metadata.get("stop_reason"),
                },
            )
        return response


class SummaryUsage(BaseCallbackHandler):
    """原生摘要走独立模型调用，通过模型回调保存实报用量。"""

    def __init__(self, emit):
        self.emit = emit
        self.started = {}

    def on_chat_model_start(self, _serialized, _messages, *, run_id, **_kwargs):
        self.started[run_id] = monotonic()

    def on_llm_end(self, response, *, run_id, **_kwargs):
        started = self.started.pop(run_id, monotonic())
        message = next(
            (getattr(item, "message", None) for row in response.generations for item in row), None
        )
        if message:
            self.emit(
                "provider_usage",
                {
                    **reported_usage(message),
                    "purpose": "summary",
                    "request_id": str(run_id),
                    "duration_ms": round((monotonic() - started) * 1000),
                },
            )

    def on_llm_error(self, _error, *, run_id, **_kwargs):
        started = self.started.pop(run_id, None)
        if started is not None:
            self.emit("provider_usage", failed_usage("summary", started))
