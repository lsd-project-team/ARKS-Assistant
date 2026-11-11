"""把当前轮次的真实验证失败送回工具循环，最多三次验证且尊重停止。"""

import asyncio
import json

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import HumanMessage

from app.agents.runtime.answer_completion import final_message


class CodeWorkRepair(AgentMiddleware):
    def __init__(self, work, thread_id, run_id, emit):
        self.work, self.thread_id, self.run_id, self.emit = work, thread_id, run_id, emit
        self.nudges = {}

    async def awrap_model_call(self, request, handler):
        response = await handler(request)
        answer = final_message(response)
        if answer is None or answer.tool_calls:
            return response
        status = await asyncio.to_thread(self.work.status, self.thread_id)
        job = status.get("verification") or {}
        failed_here = job.get("run_id") == self.run_id and job.get("status") == "failed"
        pending = False
        if not failed_here and any(
            item.get("run_id") == self.run_id for item in status.get("history", [])
        ):
            changes = await asyncio.to_thread(self.work.summary, self.thread_id, self.run_id)
            pending = bool(changes["files"]) and not (
                job.get("run_id") == self.run_id
                and job.get("status") == "passed"
                and status.get("verification_current")
            )
        if (
            not failed_here
            and not pending
            or job.get("run_id") == self.run_id
            and job.get("status") == "cancelled"
        ):
            return response
        key = job.get("id", "pending:" + str(status.get("revision")))
        if (
            job.get("run_id") == self.run_id
            and job.get("attempt", 1) >= 3
            or self.nudges.get(key, 0) >= 1
            or sum(self.nudges.values()) >= 3
        ):
            self.emit("notice", {"text": "本轮自动修复已达到边界，剩余错误保留在代码修改面板。"})
            return response
        self.nudges[key] = 1
        failures = [
            {"name": item["name"], "log": item.get("log", "")[-6000:]}
            for item in job.get("steps", [])
            if item["status"] == "failed"
        ]
        self.emit(
            "stage",
            {
                "stage": "thinking",
                "detail": f"根据实际验证状态继续处理（已验证{job.get('attempt', 0)}/3次）",
            },
        )
        correction = HumanMessage(
            content=(
                "代码副本本轮验证实际失败"
                if failed_here
                else "本轮已实际修改副本，但尚未完成当前版本验证"
            )
            + "，请继续处理已授权修改：未配置需求测试时先用set_work_requirement"
            "添加对应原业务行为的Check断言；根据下列真实结果读取并修复业务代码，"
            "再调用verify_code_workspace；保留已固定的验收断言。"
            "不要把失败或未验证报告为已完成或通过。若无法修复，明确说明具体障碍。\n"
            + json.dumps(
                {
                    "revision": status.get("revision"),
                    "error": job.get("error"),
                    "failures": failures,
                },
                ensure_ascii=False,
            )
        )
        return await handler(request.override(messages=[*request.messages, answer, correction]))
