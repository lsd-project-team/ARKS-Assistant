"""完成前验收门禁：从零生成必须计划完成、构建通过、界面自检通过。"""

import asyncio

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import HumanMessage

from app.agents.runtime.answer_completion import final_message


class RunChecks:
    def __init__(self, generation=False):
        self.generation = generation
        self.verify = None
        self.test = None
        self.ui = None
        self.scaffolded = None

    def record_verify(self, result):
        if result.get("kind") == "test":
            self.test = result
        else:
            self.verify = result

    def record_ui(self, result):
        self.ui = result

    def record_scaffold(self, result):
        self.scaffolded = result

    def technical_complete(self):
        """构建（0 错误 0 警告）与界面自检通过；自测由独立评分强制复核。"""
        build = self.verify and self.verify.get("ok") and not self.verify.get("warning_count")
        failed_test = self.test is not None and not self.test.get("ok")
        return bool(build and not failed_test and self.ui and self.ui.get("ok"))

    def missing(self, plan_complete, include_plan=True):
        missing = []
        if include_plan and not plan_complete:
            missing.append("计划清单未全部完成（用 update_plan 标记 done 或 blocked）")
        if not (self.verify and self.verify.get("ok")):
            missing.append("未通过 verify build（构建 0 错误，最好 0 警告）")
        elif self.verify.get("warning_count"):
            missing.append(f"构建有 {self.verify['warning_count']} 个警告，需要清零")
        if self.test is not None and not self.test.get("ok"):
            missing.append("verify test 未通过（回放自测失败）")
        if not (self.ui and self.ui.get("ok")):
            missing.append("未通过 check_ui（界面截图与布局自检）")
        return missing


class AcceptanceGate(AgentMiddleware):
    """从零生成的最终回答前检查验收项；不满足则要求继续，最多重试两次。"""

    def __init__(self, checks, plan, emit, generation=False, max_retries=3, recover=None):
        self.checks, self.plan, self.emit = checks, plan, emit
        self.generation, self.max_retries = generation, max_retries
        self.recover = recover
        self.recovered = False
        self.attempts = 0

    async def awrap_model_call(self, request, handler):
        await self.recover_ui_if_needed()
        technical = self.generation and self.checks.technical_complete()
        if technical:
            # 技术项已全部通过：禁止继续调用工具，让模型直接收尾，避免通过后空转。
            choice = (
                {"type": "none"}
                if "anthropic" in getattr(request.model, "_llm_type", "")
                else "none"
            )
            response = await handler(request.override(tool_choice=choice))
        else:
            response = await handler(request)
        if not self.generation:
            return response
        answer = final_message(response)
        if answer is None or answer.tool_calls:
            return response
        missing = self.checks.missing(
            self.plan.complete(), include_plan=not technical
        )
        if not missing:
            self.emit(
                "acceptance",
                {
                    "ok": True,
                    "missing": [],
                    "attempt": self.attempts,
                    "plan_incomplete": not self.plan.complete(),
                },
            )
            return response
        if self.attempts >= self.max_retries:
            self.emit("acceptance", {"ok": False, "missing": missing, "final": True})
            return response
        self.attempts += 1
        self.emit(
            "acceptance", {"ok": False, "missing": missing, "attempt": self.attempts}
        )
        nudge = HumanMessage(
            content=(
                "系统验收检查未通过，不能结束：\n- "
                + "\n- ".join(missing)
                + self.details()
                + "\n请先完成这些步骤并用 update_plan 更新状态，再给出最终回答；"
                "不得把未验证的内容说成已完成。"
            ),
            id=f"acceptance-gate-{self.attempts}",
        )
        return await handler(
            request.override(messages=[*request.messages, answer, nudge])
        )

    async def recover_ui_if_needed(self):
        """界面被改坏时回退到最近一次通过状态，避免带着布局回退收尾。"""
        if not self.generation or self.recovered or not self.recover:
            return
        ui = self.checks.ui
        if not ui or ui.get("ok"):
            return
        if not (self.checks.verify and self.checks.verify.get("ok")):
            return
        if self.checks.test is not None and not self.checks.test.get("ok"):
            return
        self.recovered = True
        try:
            result = await asyncio.to_thread(self.recover)
        except Exception as error:
            result = {"ok": False, "error": str(error)}
        if result.get("ok"):
            self.checks.record_ui(result)
            self.emit(
                "acceptance",
                {
                    "ok": True,
                    "recovered": True,
                    "checkpoint": result.get("recovered_from", ""),
                },
            )
        else:
            self.emit(
                "acceptance",
                {"ok": False, "recover_error": result.get("error", "回退失败")},
            )

    def details(self):
        lines = []
        if self.checks.verify and self.checks.verify.get("errors"):
            errors = self.checks.verify["errors"][:3]
            lines.append(
                "构建错误：" + "；".join(
                    f"{row.get('file', '')}:{row.get('line', 0)} {row.get('code', '')}"
                    for row in errors
                )
            )
        if self.checks.test and self.checks.test.get("failed"):
            lines.append(f"自测失败 {self.checks.test['failed']} 项")
        if self.checks.ui and self.checks.ui.get("issues"):
            lines.append("界面问题：" + "；".join(self.checks.ui["issues"][:5]))
        return ("\n" + "\n".join(lines)) if lines else ""
