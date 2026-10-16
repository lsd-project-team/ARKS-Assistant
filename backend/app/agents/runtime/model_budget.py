"""LangChain供应商调用的项目日预算；实际用量未知时保留保守预留。"""

import asyncio

from langchain_core.callbacks import AsyncCallbackHandler

from app.agents.context.tokens import estimate_tokens
from app.infrastructure.providers.usage import reported_usage


def usage_tokens(result):
    totals, unknown = [], False
    for generations in getattr(result, "generations", []):
        for generation in generations:
            total = reported_usage(getattr(generation, "message", None))["total_tokens"]
            if total is None:
                unknown = True
            else:
                totals.append(total)
    output = getattr(result, "llm_output", None) or {}
    usage = output.get("token_usage") or output.get("usage") or {}
    aggregate = usage.get("total_tokens")
    if type(aggregate) is int and aggregate >= 0:
        # 有些供应商在每个候选上重复总数；宁可保守多记，也不能只记首个生成结果。
        return max(aggregate, sum(totals))
    return sum(totals) if totals and not unknown else None


class ProjectModelBudget(AsyncCallbackHandler):
    raise_error = True
    run_inline = True

    def __init__(self, ledger, maximum, *, output_tokens=None):
        if type(maximum) is not int or maximum <= 0:
            raise ValueError("模型上下文额度必须是正整数")
        if output_tokens is not None and (
            type(output_tokens) is not int or not 0 < output_tokens < maximum
        ):
            raise ValueError("模型输出额度必须是小于上下文额度的正整数")
        self.ledger, self.maximum = ledger, maximum
        self.output_tokens = output_tokens
        self.reservations = {}
        self.owners = {}
        self.lock = asyncio.Lock()

    def reservation_size(self, messages, **kwargs):
        if self.output_tokens is None:
            return self.maximum
        parameters = kwargs.get("invocation_params") or {}
        tools = parameters.get("tools") or parameters.get("functions")
        total = 0
        for batch in messages:
            estimated = estimate_tokens(batch, tools=tools)
            # 这是调度预留而非供应商实报；额外余量覆盖协议包装与 tokenizer 差异。
            total += min(self.maximum, estimated + self.output_tokens + max(128, estimated // 10))
        return total or self.output_tokens

    async def on_chat_model_start(self, serialized, messages, *, run_id, **kwargs):
        async with self.lock:
            if run_id not in self.reservations:
                self.reservations[run_id] = await asyncio.to_thread(
                    self.ledger.reserve, self.reservation_size(messages, **kwargs)
                )
                if task := asyncio.current_task():
                    # LangChain 的外层取消不保证触发 on_llm_error；只清内存，不退未知费用。
                    def cleanup(owner):
                        if owner.cancelled() or owner.exception() is not None:
                            self._forget(run_id)

                    self.owners[run_id] = (task, cleanup)
                    task.add_done_callback(cleanup)

    def _forget(self, run_id):
        owner = self.owners.pop(run_id, None)
        if owner:
            owner[0].remove_done_callback(owner[1])
        return self.reservations.pop(run_id, None)

    async def on_llm_end(self, response, *, run_id, **kwargs):
        reservation = self._forget(run_id)
        if reservation:
            await asyncio.to_thread(self.ledger.settle, reservation, usage_tokens(response))

    async def on_llm_error(self, error, *, run_id, **kwargs):
        self._forget(run_id)
