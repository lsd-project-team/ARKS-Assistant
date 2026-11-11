"""通用工作区工具：直接读写已配置目录，命令受白名单与审批约束。"""

import asyncio
import json

from langchain_core.tools import tool

from app.agents.tools.guards import safe_source_tools
from app.core.config import dump_json

WORKSPACE_WORK_GUIDANCE = """
【代码工作区】
本对话可直接读写管理员为本项目配置的工作目录，不再创建独立副本，也没有合并或写回确认步骤。
用户描述软件故障、代码缺陷或新功能时，按 Codex 方式直接完成修改并运行构建/测试验证。
用户只解释、分析、讨论或明确暂不修改时，只回答，不修改文件。
先 open_workspace 查看工作目录与当前改动，再用 list_workspace / search_workspace /
read_workspace_file 定位代码。
修改前必须读取当前文件拿到 version；write_workspace_file 保存完整内容，
edit_workspace_file 替换唯一匹配的原文。
多个文件一起改使用 apply_workspace_patch，一次提交全部修改；版本不一致时整批拒绝。
修改后运行 run_workspace_command 执行构建或测试；命令必须在白名单内，可能等待用户批准。
命令被拒绝、超时或失败时读取真实输出再修复，不重复提交同一条被拒命令，不把未运行的结果说成通过。
运行结果、退出码和差异都来自本轮真实执行；未执行的验证必须明确说明。
restore_workspace_changes 可把本对话的修改还原到第一次改动前的状态；还原前先说明影响范围。
不要编造文件内容、命令输出或测试结果；无法确定时先读取或运行确认。
"""


def workspace_work_tools(work, thread_id, emit):
    async def call(function, *args, **kwargs):
        result = await asyncio.to_thread(function, thread_id, *args, **kwargs)
        if isinstance(result, dict) and isinstance(result.get("output"), str):
            output = result["output"]
            if len(output) > 12_000:
                result = {**result, "output": output[-12_000:], "output_truncated": True}
        emit("workspace_work", {"thread_id": thread_id})
        return dump_json(result)

    @tool
    async def open_workspace() -> str:
        """Show the configured workspace root, changed files and pending approvals."""
        return await call(work.status)

    @tool
    async def list_workspace(path: str = "") -> str:
        """List files and directories under the workspace (relative path)."""
        return await call(work.list, path)

    @tool
    async def read_workspace_file(path: str, start_line: int = 1, end_line: int = 400) -> str:
        """Read numbered lines and the current version of a workspace text file."""
        return await call(work.read, path, start_line, end_line)

    @tool
    async def search_workspace(query: str, limit: int = 60) -> str:
        """Search text across the workspace and return matching paths and line numbers."""
        return await call(work.search, query, limit)

    @tool
    async def write_workspace_file(path: str, content: str, version: str = "") -> str:
        """Create or replace a whole file; version must be the last read version, empty for new."""
        return await call(work.write, path, content, version)

    @tool
    async def edit_workspace_file(path: str, old_text: str, new_text: str, version: str) -> str:
        """Replace one unique block in a file using the version from the last read."""
        return await call(work.edit, path, old_text, new_text, version)

    @tool
    async def apply_workspace_patch(edits: str) -> str:
        """Apply several file edits atomically. edits is a JSON array of
        {path, old_text, new_text, version}; old_text empty means full content."""
        try:
            rows = json.loads(edits)
        except ValueError as error:
            raise ValueError("edits 必须是 JSON 数组") from error
        if not isinstance(rows, list):
            raise ValueError("edits 必须是 JSON 数组")
        return await call(work.apply_patch, rows)

    @tool
    async def run_workspace_command(
        argv: list[str], cwd: str = "", timeout_seconds: int = 0
    ) -> str:
        """Run one allowlisted command in the workspace, e.g. ["dotnet","build"]."""
        return await call(work.run_command, argv, cwd, timeout_seconds or None)

    @tool
    async def inspect_workspace_changes() -> str:
        """Show changed files, line counts, recent commands and pending approvals."""
        return await call(work.status)

    @tool
    async def restore_workspace_changes(path: str = "") -> str:
        """Restore this conversation's edits to the pre-edit content; empty path restores all."""
        return await call(work.restore, path)

    return safe_source_tools(
        [
            open_workspace,
            list_workspace,
            read_workspace_file,
            search_workspace,
            write_workspace_file,
            edit_workspace_file,
            apply_workspace_patch,
            run_workspace_command,
            inspect_workspace_changes,
            restore_workspace_changes,
        ],
        "代码工作区工具",
    )
