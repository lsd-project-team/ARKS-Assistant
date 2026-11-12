"""聊天中的原地编码工具；直接读写项目目录，用快照回滚。"""

import asyncio

from langchain_core.tools import tool

from app.core.config import dump_json
from app.modules.coding.executor import ApprovalRequired

CODING_GUIDANCE = """
【项目编码】
当前项目目录就是工作区，所有路径都使用项目内相对路径。
用户描述需求后直接完成：先 list_files / read_project_file / search_files 了解现状，
再建目录、写文件、跑构建或测试。
新建项目可以是空目录，从零创建工程结构也可以。
覆盖已有文件必须带上一次读取得到的 hash；新建文件 hash 留空。
删除、移动前系统会自动建快照；每轮结束调用 checkpoint 记录本轮结果，用户可从检查点回滚。
run_command 用于构建、测试和一次性命令；start_process 用于常驻服务，
返回 job_id 后可用 read_process/stop_process 查看和停止。
命令不在自动放行范围时会返回需要确认的提示，此时向用户说明要执行的命令并等待确认，不要反复重试。
不要编造执行结果；失败时读取日志、修复后重试。用户只询问、讨论时不修改任何文件。
"""


def coding_tools(work, thread_id, emit, *, run_id=""):
    def call(name, function, *args, **kwargs):
        try:
            result = function(*args, **kwargs)
        except ApprovalRequired as error:
            payload = {
                "ok": False,
                "approval_required": True,
                "approval": work.request_approval(error.command, error.cwd, error.timeout),
                "message": "命令需要用户在界面上确认，批准后会由后台执行；不要反复重试。",
            }
        except Exception as error:  # 工具失败要让模型看到原因，而不是中断整轮
            payload = {"ok": False, "error": str(error)}
        else:
            payload = {"ok": True, **(result if isinstance(result, dict) else {"result": result})}
        emit("coding", {"tool": name, "ok": payload["ok"]})
        return dump_json(payload)

    async def run(name, function, *args, **kwargs):
        return await asyncio.to_thread(call, name, function, *args, **kwargs)

    @tool
    async def list_files(path: str = ".", depth: int = 2) -> str:
        """List project files under a relative path, depth 1-5."""
        return await run("list_files", work.list_files, path, depth)

    @tool
    async def read_project_file(path: str, start_line: int = 1, end_line: int = 400) -> str:
        """Read a text file with line numbers and its hash."""
        return await run("read_project_file", work.read_file, path, start_line, end_line)

    @tool
    async def search_files(query: str, path: str = ".", glob: str = "") -> str:
        """Search text content in the project."""
        return await run("search_files", work.search_files, query, path, glob)

    @tool
    async def write_file(path: str, content: str, expected_hash: str = "") -> str:
        """Create or overwrite a text file; expected_hash must match for existing files."""
        return await run("write_file", work.write_file, path, content, expected_hash)

    @tool
    async def create_directory(path: str) -> str:
        """Create a directory (parents included)."""
        return await run("create_directory", work.create_directory, path)

    @tool
    async def move_path(path: str, destination: str) -> str:
        """Move or rename a file or directory inside the project."""
        return await run("move_path", work.move_path, path, destination)

    @tool
    async def delete_path(path: str, recursive: bool = False) -> str:
        """Delete a file, or a directory when recursive is true."""
        return await run("delete_path", work.delete_path, path, recursive)

    @tool
    async def run_command(command: str, cwd: str = ".", timeout_seconds: int = 120) -> str:
        """Run a one-shot shell command in the project directory."""
        result = await asyncio.to_thread(
            call, "run_command", work.run_command, command, cwd, timeout_seconds
        )
        work.checkpoint(f"run-{run_id or 'manual'}")
        return result

    @tool
    async def start_process(command: str, cwd: str = ".") -> str:
        """Start a long-running background process; returns a job id."""
        return await run("start_process", work.start_process, command, cwd)

    @tool
    async def read_process(job_id: str, lines: int = 80) -> str:
        """Read recent output of a background process."""
        return await run("read_process", work.read_process, job_id, lines)

    @tool
    async def stop_process(job_id: str) -> str:
        """Stop a background process and its child processes."""
        return await run("stop_process", work.stop_process, job_id)

    @tool
    async def checkpoint(label: str = "") -> str:
        """Commit the current project state as a rollback checkpoint."""
        return await run("checkpoint", work.checkpoint, label)

    @tool
    async def list_checkpoints(limit: int = 20) -> str:
        """List recent checkpoints and pending changes."""
        return await run("list_checkpoints", work.checkpoints, limit)

    @tool
    async def diff_checkpoint(base: str = "", head: str = "", path: str = "") -> str:
        """Show diff between checkpoints or the working tree."""
        paths = [path] if path else None
        return await run("diff_checkpoint", work.diff, base, head, paths)

    @tool
    async def restore_checkpoint(commit: str, paths: list[str] | None = None) -> str:
        """Restore the project (or selected paths) to a checkpoint."""
        return await run("restore_checkpoint", work.restore, commit, paths)

    return [
        list_files,
        read_project_file,
        search_files,
        write_file,
        create_directory,
        move_path,
        delete_path,
        run_command,
        start_process,
        read_process,
        stop_process,
        checkpoint,
        list_checkpoints,
        diff_checkpoint,
        restore_checkpoint,
    ]
