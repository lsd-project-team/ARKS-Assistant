"""聊天中的原地编码工具；直接读写项目目录，用快照回滚。"""

import asyncio

from langchain_core.tools import tool

from app.core.config import dump_json

CODING_GUIDANCE = """
【项目编码】
当前项目目录就是工作区，所有路径都使用项目内相对路径。
读取和修改项目文件用 read_project_file / list_files / search_files / find_files / write_file / edit_file；
带 /workspace/ 前缀的只读工具用于引用当前源码，不要用它们判断项目工作区的可写状态。
工艺、设备操作、故障与经验类问题不要当作编码任务：先调用 search_debug_issues 检索本地问题与经验，
再结合检索结果回答；只有用户明确要求修改代码、创建工程或运行命令时才使用文件与命令工具。
用户明确要求实现或修改时，先 list_files / read_project_file / search_files / find_files 了解现状，
再建目录、写文件、跑构建或测试。
新建项目可以是空目录，从零创建工程结构也可以。
修改已有文件优先用 edit_file：按原文精确替换，需要先读取并带上 version；大范围重写才用 write_file。
覆盖已有文件必须带上一次读取得到的 hash；新建文件 hash 留空。
图片、图标等二进制资源用 write_binary_file，内容为 base64。
删除、移动前系统会自动建快照；每轮结束系统会自动记录检查点，用户可从检查点回滚。
run_command 用于构建、测试和一次性命令；start_process 用于常驻服务，
返回 job_id 后可用 read_process/stop_process 查看和停止。
命令不在自动放行范围时会在本轮内等待用户确认；确认后自动继续。被拒绝或超时不要反复重试。
命令输出会实时推送，结束后返回末尾摘要；需要更多时用 read_process 或读取日志。
不要编造执行结果；失败时读取日志、修复后重试。用户只询问、讨论时不修改任何文件。
同一命令或同一文件读取不要连续重复；连续重复会被拦截。了解基本情况后直接开始创建工程、写代码和构建。
"""


def coding_tools(work, thread_id, emit, *, run_id=""):
    def call(name, function, *args, **kwargs):
        try:
            result = function(*args, **kwargs)
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
    async def find_files(pattern: str, path: str = ".", limit: int = 100) -> str:
        """Find files by name pattern, for example *.csproj or **/test_*.py."""
        return await run("find_files", work.find_files, pattern, path, limit)

    @tool
    async def write_file(path: str, content: str, expected_hash: str = "") -> str:
        """Create or overwrite a text file; expected_hash must match for existing files."""
        return await run("write_file", work.write_file, path, content, expected_hash)

    @tool
    async def edit_file(
        path: str,
        old_string: str,
        new_string: str,
        expected_hash: str,
        replace_all: bool = False,
    ) -> str:
        """Replace exact text in a file; requires the version from read_project_file."""
        return await run(
            "edit_file",
            work.edit_file,
            path,
            [
                {
                    "old": old_string,
                    "new": new_string,
                    "replace_all": replace_all,
                }
            ],
            expected_hash,
        )

    @tool
    async def multi_edit(path: str, edits: list[dict], expected_hash: str) -> str:
        """Apply several exact replacements to one file in a single write.

        Each edit is {"old": "...", "new": "...", "replace_all": false}.
        """
        return await run("multi_edit", work.edit_file, path, edits, expected_hash)

    @tool
    async def write_binary_file(path: str, content_base64: str, expected_hash: str = "") -> str:
        """Create or overwrite an image or other binary file from base64 content."""
        return await run(
            "write_binary_file", work.write_binary, path, content_base64, expected_hash
        )

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
        return await run(
            "run_command",
            work.run_command,
            command,
            cwd,
            timeout_seconds,
            False,
            wait=True,
            emit=emit,
            run_id=run_id,
            thread_id=thread_id,
        )

    @tool
    async def start_process(command: str, cwd: str = ".") -> str:
        """Start a long-running background process; returns a job id."""
        return await run(
            "start_process",
            work.start_process,
            command,
            cwd,
            False,
            wait=True,
            emit=emit,
            run_id=run_id,
            thread_id=thread_id,
        )

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
        find_files,
        write_file,
        edit_file,
        multi_edit,
        write_binary_file,
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
