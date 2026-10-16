"""项目阅读与隔离开发工具；模型只能选用管理员配置的验证命令。"""

import asyncio
import logging
import re

from langchain_core.tools import tool

from app.agents.context.tokens import fit_text
from app.agents.tools.guards import safe_source_tools
from app.core.config import dump_json

CHANGE_TOOLS = {
    "list_code_changes",
    "create_code_change",
    "read_change_file",
    "edit_change_file",
    "get_change_diff",
    "list_verification_profiles",
    "verify_code_change",
}
_EDIT_ACTION = r"(?:修改|改一下|修复|实现|编写|写代码|生成补丁|尝试开发|继续开发)"
EDIT_REQUEST = re.compile(
    r"(?:^|[。！\n；;])\s*"
    + _EDIT_ACTION
    + r"|(?:请(?:你)?|帮我|给我|尝试|开始|继续|直接|现在|需要|我要|我想)"
    r"(?:来|去|帮我)?\s*"
    + _EDIT_ACTION
    + r"|(?:^|[。！\n；;])\s*(?:按照|按|把|将).{1,30}"
    + _EDIT_ACTION
)
READ_REQUEST = re.compile(
    r"^(?:(?:请(?:你)?|帮我|麻烦(?:你)?|现在|立即|直接|先)\s*)*"
    r"(?:(?:把|将).{1,40})?"
    r"(?:通读(?!功能|能力|需求|原理|方案|机制)|全量阅读|完整阅读|从头阅读"
    r"|阅读(?:整个|全部|所有|本|这个)?项目|阅读全部"
    r"|(?:开始|启动|继续|恢复|重新(?:开始)?)\s*(?:进行\s*)?"
    r"(?:项目阅读|(?:全量|完整|从头)?阅读|通读))"
)
READ_INQUIRY = re.compile(
    r"如何|怎样|怎么|为什么|为何|是否|能否|可否|什么|有何|多少|多久|何时|有没有|是不是"
    r"|吗|么|能不能|可不可以|会不会|并不|并非|不代表|不意味着|[?？]"
)
READ_CONTINUATION = re.compile(
    r"(?:好的[，, ]*)?(?:继续|接着|continue)[吧。.!！ ]*\n此前已授权的请求：(.+)", re.I | re.S
)
DISCUSSION_ONLY = re.compile(
    r"先讨论|先回答|先(?:给|提供|看).{0,20}方案|只(?:要|做|需|是)?.{0,8}(?:分析|解释|方案)"
    r"|(?:不要|不需要|不用|暂不|先不|别).{0,10}(?:修改|实现|编写|修复|通读|阅读|开始|动代码)"
)
VERIFICATION_CANCEL_TIMEOUT = 30
_verification_cleanups = set()
_logger = logging.getLogger(__name__)


def _explicit_read_request(request_text):
    inherited = READ_CONTINUATION.fullmatch(request_text.strip())
    text = inherited.group(1) if inherited else request_text
    # 在动作分句内识别命令；“如何开始通读”不能因命中名词或动词子串触发付费任务。
    clauses = re.split(
        r"[，,。！!\n；;]|并(?:且)?(?=总结|分析|说明|解释|告诉|给出|列出|梳理|开始|继续|通读)"
        r"|然后|接着|后(?=分析|说明|解释|总结|告诉)",
        text,
    )
    return any(
        READ_REQUEST.match(clause.strip()) and not READ_INQUIRY.search(clause) for clause in clauses
    )


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


def engineering_tools(runtime, request_text="", emit=None, *, use_knowledge=True):
    if not runtime.repository.project_id:
        return []
    changes, reading = runtime.code_changes, runtime.project_reading
    discussion = bool(DISCUSSION_ONLY.search(request_text))
    can_edit = bool(EDIT_REQUEST.search(request_text)) and not discussion
    attempts = 0

    async def mutate(operation, *arguments):
        async with runtime.project_lock:
            await asyncio.to_thread(runtime.repository.creation_guard)
            return await asyncio.to_thread(operation, *arguments)

    @tool
    async def project_reading_status(job_id: str = "") -> str:
        """Inspect persistent project reading coverage; read/analyzed/reviewed are distinct."""
        return dump_json(
            await asyncio.to_thread(
                reading.get if job_id else reading.list, *([job_id] if job_id else [])
            )
        )

    @tool
    async def search_project_reading(query: str) -> str:
        """Find current versioned reading summaries. Re-read current code before conclusions."""
        context, documents = await asyncio.to_thread(reading.prompt, query, 2000)
        return dump_json({"context": context, "documents": documents})

    @tool
    async def start_project_reading(job_id: str = "", title: str = "项目阅读") -> str:
        """Start/resume a persistent whole-project analysis only when the user requested it."""
        if not _explicit_read_request(request_text) or discussion:
            raise ValueError("本轮用户没有要求启动全项目阅读，可先查看阅读状态")
        async with runtime.project_lock:
            await asyncio.to_thread(runtime.repository.creation_guard)
            job = await asyncio.to_thread(reading.get, job_id) if job_id else None
            if job is None and "继续" in request_text:
                job = (await asyncio.to_thread(reading.list))["latest"]
            if job is None:
                job = await asyncio.to_thread(reading.create, title)
            return dump_json(await reading.start(job["id"]))

    @tool
    async def list_code_changes() -> str:
        """List this project's isolated changes and latest verification states."""
        return dump_json(await asyncio.to_thread(changes.list))

    @tool
    async def create_code_change(title: str, goal: str) -> str:
        """Create an isolated copy for requested implementation. Original stays read-only."""
        if not can_edit:
            raise ValueError("本轮用户只要求分析，尚未要求修改或实现代码")
        return dump_json(await mutate(changes.create, title, goal))

    @tool
    async def read_change_file(
        change_id: str, path: str, start_line: int = 1, end_line: int = 200
    ) -> str:
        """Read at most 500 isolated file lines and current hash. Large content is bounded."""
        if start_line < 1 or end_line < start_line or end_line - start_line >= 500:
            raise ValueError("请读取1–500行范围，行号从1开始")
        result = await asyncio.to_thread(changes.read_file, change_id, path)
        lines = result["content"].splitlines(keepends=True)
        selected = "".join(lines[start_line - 1 : end_line])
        bounded = fit_text(selected, 6000)
        return dump_json(
            {
                **result,
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
        return dump_json(await mutate(changes.edit_file, change_id, path, before, after, version))

    @tool
    async def get_change_diff(change_id: str) -> str:
        """Inspect patch and base conflicts. A patch is not a passing test or device acceptance."""
        result = await asyncio.to_thread(changes.diff, change_id)
        bounded = fit_text(result["diff"], 6000)
        return dump_json({**result, "diff": bounded, "truncated": bounded != result["diff"]})

    @tool
    async def list_verification_profiles() -> str:
        """List administrator-configured argv commands; cannot create or change them."""
        return dump_json(await asyncio.to_thread(changes.profiles))

    @tool
    async def verify_code_change(change_id: str, profile_id: str) -> str:
        """Run configured verification and await result/log for repairs. Max 3 attempts."""
        nonlocal attempts
        if not can_edit:
            raise ValueError("本轮用户没有要求实施修改，请在代码工作页主动验证")
        if attempts >= 3:
            raise ValueError("本轮已验证3次，请保留失败日志、当前差异和剩余项后结束")
        attempts += 1
        # 保留启动任务：取消 to_thread 的等待不能停止其线程，必须等登记完成再取消进程。
        launch = asyncio.create_task(mutate(changes.verify, change_id, profile_id))
        try:
            await asyncio.shield(launch)
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
            project_reading_status,
            *([search_project_reading] if use_knowledge else []),
            start_project_reading,
            list_code_changes,
            create_code_change,
            read_change_file,
            edit_change_file,
            get_change_diff,
            list_verification_profiles,
            verify_code_change,
        ],
        "代码工作工具",
    )
