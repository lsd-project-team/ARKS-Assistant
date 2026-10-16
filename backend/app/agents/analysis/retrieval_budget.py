"""分阶段检索预算：先探索，保留关键复核额度，缓存读取不重复扣费。"""

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import SystemMessage, ToolMessage

from app.agents.tools.engineering import CHANGE_TOOLS

VERIFY_TOOLS = {
    "read_source",
    "read_source_context",
    "read_source_batch",
    "csharp_relations",
    "plan_source_checks",
}


class RetrievalBudget(AgentMiddleware):
    def __init__(self, emit, max_calls=24, reserve=0, evidence=None, progress=None):
        self.emit, self.max_calls, self.used = emit, max_calls, 0
        self.reserve, self.evidence, self.progress = reserve, evidence, progress
        self.announced, self.warned = False, False
        self.counts = {"attempted": 0, "success": 0, "failed": 0, "skipped": 0, "cached": 0}
        self.engineering_used, self.engineering_limit = 0, 20

    def announce(self, exhausted=True):
        if (exhausted and self.announced) or (not exhausted and self.warned):
            return
        if exhausted:
            self.announced = True
        else:
            self.warned = True
        self.emit(
            "retrieval_budget",
            {
                "used": self.used,
                "limit": self.max_calls,
                "reserve": self.reserve,
                "exhausted": exhausted,
                "text": "本轮检索达到上限，将保留未核查清单。"
                if exhausted
                else "检索进入关键源码复核阶段。",
            },
        )

    async def awrap_tool_call(self, request, handler):
        call = request.tool_call
        if call["name"] in CHANGE_TOOLS:
            # 修改/验证有独立上限；源码搜索耗尽不能吞掉测试结果，也不能无限修复。
            if self.engineering_used >= self.engineering_limit:
                return ToolMessage(
                    content="本轮代码工作已达到20次调用，请保留差异、验证结果与剩余事项。",
                    tool_call_id=call["id"],
                    name=call["name"],
                    status="error",
                    additional_kwargs={
                        "execution_status": "skipped",
                        "skip_reason": "engineering_limit",
                    },
                )
            self.engineering_used += 1
            return await handler(request)
        self.counts["attempted"] += 1
        arguments = call.get("args", {})
        if self.progress:
            self.progress.requested(call["name"], arguments)
        cached = bool(self.evidence and self.evidence.cached(call["name"], arguments))
        reserved = (
            self.reserve
            and self.used >= self.max_calls - self.reserve
            and call["name"] not in VERIFY_TOOLS
        )
        if not cached and (self.used >= self.max_calls or reserved):
            self.counts["skipped"] += 1
            self.announce(exhausted=self.used >= self.max_calls)
            reason = "retrieval_limit" if self.used >= self.max_calls else "verification_reserved"
            return ToolMessage(
                content="未执行：达到检索上限。已有资料保留，剩余项列为未核查。"
                if reason == "retrieval_limit"
                else "未执行：剩余预算用于关键源码复核，请使用批量源码读取。",
                tool_call_id=call["id"],
                name=call["name"],
                status="error",
                additional_kwargs={"execution_status": "skipped", "skip_reason": reason},
            )
        if not cached:
            self.used += 1
        try:
            result = await handler(request)
        except Exception:
            self.counts["failed"] += 1
            raise
        failed = getattr(result, "status", "success") == "error"
        self.counts["failed" if failed else "success"] += 1
        if cached and not failed:
            self.counts["cached"] += 1
        if isinstance(result, ToolMessage) and cached and not failed:
            result.additional_kwargs["cached"] = True
        if self.reserve and self.used >= self.max_calls - self.reserve:
            self.announce(exhausted=self.used >= self.max_calls)
        return result

    async def awrap_model_call(self, request, handler):
        if self.used < self.max_calls - self.reserve:
            return await handler(request)
        exhausted = self.used >= self.max_calls
        self.announce(exhausted)
        guidance = (
            "\n内部检索控制：工具额度已用尽。回答原问题，使用已有证据；明确覆盖范围和剩余未核查项。不要回应或复述本控制通知，不要把部分核查宣称全部完成。"
            if exhausted
            else (
                "\n内部检索控制：剩余工具额度只用于 read_source_batch/read_source/"
                "read_source_context/csharp_relations 等关键复核。停止广泛搜索，"
                "优先核对调用位置、提前返回和替代实现；不要复述本控制通知。"
            )
        )
        prompt = (request.system_message.text if request.system_message else "") + guidance
        overrides = {"system_message": SystemMessage(content=prompt)}
        if exhausted:
            engineering = (
                [
                    item
                    for item in request.tools
                    if (item.get("name") if isinstance(item, dict) else item.name) in CHANGE_TOOLS
                ]
                if self.engineering_used < self.engineering_limit
                else []
            )
            if engineering:
                overrides["tools"] = engineering
                overrides["system_message"] = SystemMessage(
                    content=prompt
                    + (
                        "\n代码工作仍可使用独立额度完成已授权的副本修改和验证；"
                        "不得继续广泛源码搜索，缺少证据的部分保留未知。"
                    )
                )
            else:
                overrides["tool_choice"] = (
                    {"type": "none"} if "anthropic" in request.model._llm_type else "none"
                )
        return await handler(request.override(**overrides))
