"""模型协议适配与连通性验证；供应商异常在边界脱敏。"""

import inspect
import logging
from functools import cached_property

import anthropic
import httpx
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.config import ModelSettings


class StateInspectionModel(BaseChatModel):
    """只装配图的状态通道；读取历史不依赖供应商配置，也不允许生成回复。"""

    @property
    def _llm_type(self):
        return "state-inspection"

    def bind_tools(self, _tools, **_kwargs):
        return self

    def _generate(self, *_args, **_kwargs):
        raise RuntimeError("状态检查不能调用模型")


class OwnedChatAnthropic(ChatAnthropic):
    """供应商连接随一次运行释放，避免关闭 LangChain 缓存的共享连接池。"""

    @cached_property
    def _client(self):
        return anthropic.Client(**self._client_params)

    @cached_property
    def _async_client(self):
        return anthropic.AsyncClient(**self._client_params)


def create_model(settings: ModelSettings, *, summary: bool = False):
    if not settings.base_url or not settings.model or not settings.api_key:
        raise ValueError("请先配置接口地址、模型和密钥")
    common = {
        "model": settings.summary_model if summary and settings.summary_model else settings.model,
        "api_key": settings.api_key,
        "base_url": settings.base_url,
        "temperature": settings.temperature,
        "max_tokens": settings.output_tokens,
        "timeout": settings.timeout_seconds,
        "max_retries": 1,
        "profile": {
            "max_input_tokens": settings.context_tokens,
            "max_output_tokens": settings.output_tokens,
            "tool_calling": True,
        },
    }
    if settings.protocol == "anthropic":
        return OwnedChatAnthropic(**common)
    return ChatOpenAI(
        **common,
        use_responses_api=False,
        stream_usage=True,
        http_client=httpx.Client(),
        http_async_client=httpx.AsyncClient(),
    )


def safe_error(error: BaseException, settings: ModelSettings) -> str:
    text = str(error)
    if settings.api_key:
        text = text.replace(settings.api_key, "[密钥已隐藏]")
    return text[:1000] or type(error).__name__


async def probe_model(settings: ModelSettings) -> dict:
    model = create_model(settings)
    try:
        reply = await model.ainvoke("请仅回复：连接成功")
        return {
            "ok": True,
            "model": settings.model,
            "protocol": settings.protocol,
            "reply": reply.text[:200],
        }
    finally:
        await close_models([model])


async def close_models(models):
    for model in models:
        # Anthropic 客户端是惰性属性，读取缓存避免为了关闭而新建客户端。
        for name in ("root_async_client", "root_client", "_async_client", "_client"):
            client = model.__dict__.get(name)
            if not client:
                continue
            try:
                result = client.close()
                if inspect.isawaitable(result):
                    await result
            except Exception:
                logging.getLogger(__name__).warning("模型连接关闭失败：%s", type(client).__name__)
