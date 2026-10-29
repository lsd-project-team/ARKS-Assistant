"""隔离开发工具；模型只能选用管理员配置的验证命令。"""

import asyncio
import logging
from functools import partial

from langchain_core.tools import tool

from app.agents.context.tokens import fit_text
from app.agents.tools.engineering_evidence import code_work_evidence
from app.agents.tools.engineering_intent import (
    explicit_edit_request,
    requested_requirement_fields,
)
from app.agents.tools.guards import safe_source_tools
from app.core.config import dump_json
from app.modules.code_changes.request_binding import RequestOrigin

CHANGE_TOOLS = {
    "list_code_changes",
    "create_code_change",
    "read_change_file",
    "edit_change_file",
    "update_code_change_requirements",
    "get_change_diff",
    "list_verification_profiles",
    "verify_code_change",
}
VERIFICATION_CANCEL_TIMEOUT = 30
_verification_cleanups = set()
_logger = logging.getLogger(__name__)


def _retain_verification_cleanup(task):
    """超时只结束前台等待；保留清理任务，不能让稍后启动的命令脱离取消。"""
    _verification_cleanups.add(task)

    def finished(current):
        _verification_cleanups.discard(current)
        if not current.cancelled() and (error := current.exception()) is not None:
            _logger.error("验证取消清理失败", exc_info=(type(error), error, error.__traceback__))

    task.add_done_callback(finished)


async def _finish_cancellation(cleanup):
    deadline = asyncio.get_running_loop().time() + VERIFICATION_CANCEL_TIMEOUT
    while True:
        if cleanup.done():
            return cleanup.result()
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            raise TimeoutError("验证仍在启动，后台取消清理尚未完成，请查看验证状态")
        try:
            return await asyncio.wait_for(asyncio.shield(cleanup), remaining)
        except TimeoutError as error:
            raise TimeoutError("验证仍在启动，后台取消清理尚未完成，请查看验证状态") from error
        except asyncio.CancelledError:
            # 同一聊天可连续收到取消或关闭请求，不能因此中断不可取消线程的善后。
            if cleanup.cancelled():
                raise


async def _cancel_launched_verification(launch, changes, change_id):
    started = await asyncio.shield(launch)
    verification_id = (started.get("latest_verification") or {}).get("id")
    if not verification_id:
        raise ValueError("验证启动没有返回验证记录，无法确认取消对象")

    def cancel_current():
        with changes.lock:
            current = changes.get(change_id)
            latest = current.get("latest_verification") or {}
            if current["status"] == "verifying" and latest.get("id") == verification_id:
                changes.cancel(change_id)

    await asyncio.to_thread(cancel_current)


def engineering_tools(runtime, request_text="", emit=None, *, evidence=None):
    if not runtime.repository.project_id:
        return []
    changes = runtime.code_changes
    if evidence is not None:
        evidence.code_work_reader = partial(code_work_evidence, changes)
        evidence.user_request = request_text
    can_edit = explicit_edit_request(request_text)
    requirement_fields = requested_requirement_fields(request_text)
    origin = RequestOrigin(
        "chat", request_text, **(evidence.request_identity if evidence is not None else {})
    )
    seen_contracts = {}
    created_identifier = None
    attempts = 0

    def remember_contract(current):
        identifier = current["id"]
        if evidence is not None:
            evidence.observe_code_change(identifier)
        result = {
            key: current[key]
            for key in (
                "id",
                "title",
                "goal",
                "acceptance_criteria",
                "constraints",
                "allowed_paths",
                "request_binding",
            )
        }
        seen_contracts[identifier] = current["requirements_version"]
        return {
            **result,
            "change_version": current["change_version"],
            "requirements_version": current["requirements_version"],
        }

    async def contract(identifier):
        return remember_contract(await asyncio.to_thread(changes.get, identifier))

    async def mutate(operation, *arguments, **options):
        async with runtime.project_lock:
            await asyncio.to_thread(runtime.repository.creation_guard)
            return await asyncio.to_thread(operation, *arguments, **options)

    @tool
    async def list_code_changes() -> str:
        """List this project's isolated changes and latest verification states."""
        return dump_json(await asyncio.to_thread(changes.list))

    @tool
    async def create_code_change(
        title: str,
        goal: str,
        acceptance_criteria: list[str] | None = None,
        constraints: str = "",
        allowed_paths: list[str] | None = None,
    ) -> str:
        """Create one isolated change per user request; retries reuse its current contract/work."""
        if not can_edit:
            raise ValueError("本轮用户只要求分析，尚未要求修改或实现代码")

        def create_or_reuse():
            nonlocal created_identifier
            # 直接构建工具时可能没有消息身份；同一工具实例仍须在项目锁内防止重复创建。
            if created_identifier is not None:
                return changes.reuse(created_identifier)
            current = changes.create(
                title,
                goal,
                acceptance_criteria=acceptance_criteria or [],
                constraints=constraints,
                allowed_paths=allowed_paths or [],
                request_origin=origin,
            )
            created_identifier = current["id"]
            return current

        result = await mutate(create_or_reuse)
        remember_contract(result)
        return dump_json(result)

    @tool
    async def read_change_file(
        change_id: str, path: str, start_line: int = 1, end_line: int = 200
    ) -> str:
        """Read at most 500 isolated file lines and current hash. Large content is bounded."""
        if start_line < 1 or end_line < start_line or end_line - start_line >= 500:
            raise ValueError("请读取1–500行范围，行号从1开始")
        result = await asyncio.to_thread(changes.read_file, change_id, path)
        requirements = await contract(change_id)
        lines = result["content"].splitlines(keepends=True)
        selected = "".join(lines[start_line - 1 : end_line])
        bounded = fit_text(selected, 6000)
        return dump_json(
            {
                **result,
                "contract": requirements,
                "content": bounded,
                "start_line": start_line,
                "end_line": min(end_line, len(lines)),
                "line_count": len(lines),
                "truncated": bounded != selected,
                "complete": (start_line == 1 and end_line >= len(lines) and bounded == selected),
            }
        )

    @tool
    async def edit_change_file(
        change_id: str, path: str, before: str, after: str, version: str
    ) -> str:
        """Replace exact old context in an isolated file using its current hash; conflicts fail."""
        if not can_edit:
            raise ValueError("本轮用户没有要求修改代码")
        expected = seen_contracts.get(change_id)
        if expected is None:
            raise ValueError("请先读取副本文件或差异，核对本次需求、验收标准与修改范围")
        return dump_json(
            await mutate(
                changes.edit_file,
                change_id,
                path,
                before,
                after,
                version,
                expected_requirements=expected,
            )
        )

    @tool
    async def update_code_change_requirements(
        change_id: str,
        change_version: str,
        requirements_version: str,
        title: str,
        goal: str,
        acceptance_criteria: list[str],
        constraints: str,
        allowed_paths: list[str],
    ) -> str:
        """Update requested requirements after reading contract; invalidates tests and review."""
        if not requirement_fields:
            raise ValueError("本轮用户没有明确要求修改需求约定")
        if change_id not in seen_contracts:
            raise ValueError("请先读取副本文件或差异，核对当前需求约定")
        if requirements_version != seen_contracts[change_id]:
            raise ValueError("需求约定与本轮已读取版本不符，请重新读取")
        return dump_json(
            await mutate(
                changes.update_requirements,
                change_id,
                change_version,
                requirements_version,
                title=title,
                goal=goal,
                acceptance_criteria=acceptance_criteria,
                constraints=constraints,
                allowed_paths=allowed_paths,
                request_origin=origin,
                authorized_fields=requirement_fields,
            )
        )

    @tool
    async def get_change_diff(change_id: str) -> str:
        """Inspect patch and base conflicts. A patch is not a passing test or device acceptance."""
        result = await asyncio.to_thread(changes.diff, change_id)
        requirements = await contract(change_id)
        bounded = fit_text(result["diff"], 6000)
        return dump_json(
            {
                **result,
                "contract": requirements,
                "diff": bounded,
                "truncated": bounded != result["diff"],
            }
        )

    @tool
    async def list_verification_profiles() -> str:
        """List administrator-configured argv commands; cannot create or change them."""
        return dump_json(await asyncio.to_thread(changes.profiles))

    @tool
    async def verify_code_change(change_id: str, profile_id: str, purpose: str = "change") -> str:
        """Run baseline for environment diagnosis or change verification. Max 3 attempts."""
        nonlocal attempts
        if not can_edit:
            raise ValueError("本轮用户没有要求实施修改，请在代码工作页主动验证")
        if attempts >= 3:
            raise ValueError("本轮已验证3次，请保留失败日志、当前差异和剩余项后结束")
        attempts += 1
        # 保留启动任务：取消 to_thread 的等待不能停止其线程，必须等登记完成再取消进程。
        launch = asyncio.create_task(mutate(changes.verify, change_id, profile_id, purpose))
        try:
            await asyncio.shield(launch)
            if evidence is not None:
                evidence.observe_code_change(change_id)
            if emit:
                emit("stage", {"stage": "thinking", "detail": "正在验证隔离副本中的修改"})
            result = await changes.wait(change_id, timeout_seconds=650)
        except asyncio.CancelledError:
            cleanup = asyncio.create_task(_cancel_launched_verification(launch, changes, change_id))
            _retain_verification_cleanup(cleanup)
            await _finish_cancellation(cleanup)
            raise
        return dump_json(result)

    return safe_source_tools(
        [
            list_code_changes,
            create_code_change,
            read_change_file,
            edit_change_file,
            update_code_change_requirements,
            get_change_diff,
            list_verification_profiles,
            verify_code_change,
        ],
        "代码工作工具",
    )
