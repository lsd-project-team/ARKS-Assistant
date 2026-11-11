"""分阶段检索预算：先探索，保留关键复核额度，缓存读取不重复扣费。"""

import json

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import SystemMessage, ToolMessage

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
        self.workflow_tools = frozenset()
        self.cached_reads, self.stalled = {}, False
        self.counts = {"attempted": 0, "success": 0, "failed": 0, "skipped": 0, "cached": 0}

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
                "stalled": self.stalled,
                "text": "已停止连续重复读取同版本源码，请使用已有内容继续当前任务。"
                if self.stalled
                else "本轮检索达到上限，将保留未核查清单。"
                if exhausted
                else "检索进入关键源码复核阶段。",
            },
        )

    async def awrap_tool_call(self, request, handler):
        call = request.tool_call
        # 编辑、断言配置和仿真执行有各自的版本/次数边界，不能被检索额度挡住。
        if call["name"] in self.workflow_tools:
            self.cached_reads.clear()
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
        if self.stalled or (not cached and (self.used >= self.max_calls or reserved)):
            self.counts["skipped"] += 1
            self.announce(exhausted=self.stalled or self.used >= self.max_calls)
            reason = (
                "repeated_read"
                if self.stalled
                else "retrieval_limit"
                if self.used >= self.max_calls
                else "verification_reserved"
            )
            return ToolMessage(
                content="未执行：已连续重复读取同版本源码，没有新增依据。使用已有内容继续副本编辑、验证或回答。"
                if self.stalled
                else "未执行：达到检索上限。已有资料保留，剩余项列为未核查。"
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
            key = (call["name"], json.dumps(read_arguments(arguments), sort_keys=True))
            self.cached_reads[key] = self.cached_reads.get(key, 0) + 1
            if self.cached_reads[key] >= 3:
                # 缓存仍免费；同一读取重复三次且没有新读取时退出，理由措辞不影响判定。
                self.stalled = True
                self.announce()
        elif not failed:
            self.cached_reads.clear()
        if isinstance(result, ToolMessage) and cached and not failed:
            result.additional_kwargs["cached"] = True
        if self.reserve and self.used >= self.max_calls - self.reserve:
            self.announce(exhausted=self.used >= self.max_calls)
        return result

    async def awrap_model_call(self, request, handler):
        if not self.stalled and self.used < self.max_calls - self.reserve:
            return await handler(request)
        exhausted = self.stalled or self.used >= self.max_calls
        self.announce(exhausted)
        guidance = (
            "\n内部检索控制：同版本源码连续重复读取，没有新增依据，停止重复检索。"
            "使用已读内容继续当前任务，仍无法推进时说明具体障碍。"
            if self.stalled
            else (
                "\n内部检索控制：工具额度已用尽。回答原问题，使用已有证据；"
                "明确覆盖范围和剩余未核查项。不要回应或复述本控制通知，"
                "不要把部分核查宣称全部完成。"
            )
            if exhausted
            else (
                "\n内部检索控制：剩余工具额度只用于 read_source_batch/read_source/"
                "read_source_context/csharp_relations 等关键复核。停止广泛搜索，"
                "优先核对调用位置、提前返回和替代实现；不要复述本控制通知。"
            )
        )
        allowed = (
            [
                item
                for item in request.tools
                if tool_name(item) in self.workflow_tools
                or not exhausted
                and tool_name(item) in VERIFY_TOOLS
            ]
            if self.workflow_tools
            else []
        )
        if self.workflow_tools:
            guidance += (
                "\n检索额度只约束来源查阅，副本工具仍可用。"
                "实际修改请求应继续用副本工具读取当前版本、编辑、保存需求断言和仿真验证；"
                "不要转去反复读取原源码，不把准备或读取说成已完成修改。"
            )
        prompt = (request.system_message.text if request.system_message else "") + guidance
        overrides = {"system_message": SystemMessage(content=prompt)}
        if allowed:
            overrides["tools"] = allowed
        elif exhausted:
            overrides["tool_choice"] = (
                {"type": "none"} if "anthropic" in request.model._llm_type else "none"
            )
        return await handler(request.override(**overrides))


def tool_name(value):
    if isinstance(value, dict):
        return value.get("name") or value.get("function", {}).get("name", "")
    return getattr(value, "name", "")


def read_arguments(value):
    if isinstance(value, dict):
        return {key: read_arguments(item) for key, item in value.items() if key != "reason"}
    if isinstance(value, list):
        return [read_arguments(item) for item in value]
    return value
