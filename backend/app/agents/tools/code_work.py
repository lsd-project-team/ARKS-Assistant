"""聊天中的代码工作工具；所有动作固定到当前对话的独立副本。"""

import asyncio
import json

from langchain_core.tools import tool

from app.agents.tools.guards import safe_source_tools
from app.core.config import dump_json

CODE_WORK_GUIDANCE = """
【独立代码副本】
本对话可使用代码工作工具修改管理员配置的原工程 Simulation 副本；原业务文件始终只读。
用户要求实际修改时先 prepare_code_workspace，再用 read_work_file/search_work_files 核对副本。
用户指定文件、类或方法时，先核对完整声明；不能把其他类中的同名方法当成修改目标。
知道文件名时先 find_work_files 定位；修改后 inspect_work_changes 核对文件范围。
副本与 /workspace/ 原分析源码可能是不同版本；修改依据、文件版本和差异必须来自工作副本工具。
edit_work_file 替换唯一匹配的原文；write_work_file 保存完整文件或新增业务 C#，版本必须来自本轮读取。
用户只询问、讨论时不修改。实际修改需求应完成编辑及 verify_code_workspace；编译失败按日志修复后重跑。
本轮验证被用户停止（cancelled）时，说明未完成并停止，不自行重新启动验证。
首次完整验证是基础回归，每项新需求仍需对应预期与验证；明确区分已验证和未覆盖的行为。
没有任意命令、写回原件或设备控制工具。不能更改仿真驱动、启动入口或工程配置。
修改副本引用在代码修改面板查看，不使用指向原目录的 source: 链接冒充修改后的文件依据。
回复说明实际改动及本版验证结果，不把已有检查通过说成视觉、力控、标定或真实设备已验收。
"""


def code_work_tools(work, thread_id, emit):
    verification_cancelled = False

    async def call(function, *args, **kwargs):
        result = await asyncio.to_thread(function, thread_id, *args, **kwargs)
        if result.get("verification"):
            # 完整编译日志留在页面；模型只接收状态、检查数和定位失败所需的片段。
            verification = result["verification"]
            steps = []
            for step in verification["steps"]:
                row = {key: value for key, value in step.items() if key != "log"}
                if step["status"] == "failed":
                    log = step.get("log", "")
                    errors = [line for line in log.splitlines() if "error" in line.lower()]
                    row["log"] = "\n".join(errors[:15]) + "\n" + log[-2500:]
                steps.append(row)
            result = {**result, "verification": {**verification, "steps": steps}}
        emit("code_work", {"thread_id": thread_id})
        return dump_json(result)

    @tool
    async def prepare_code_workspace() -> str:
        """Create or reuse this conversation's independent original-project Simulation copy."""
        return await call(work.create)

    @tool
    async def find_work_files(query: str) -> str:
        """Find file paths by name in the fixed working copy, e.g. DispenseController.cs."""
        return await call(work.find, query)

    @tool
    async def read_work_file(path: str, start_line: int = 1, end_line: int = 300) -> str:
        """Read up to 500 numbered C# lines and version. Use a path from working-copy tools."""
        return await call(work.read, path, start_line, end_line)

    @tool
    async def search_work_files(query: str) -> str:
        """Search current C# code in the independent copy before editing."""
        return await call(work.search, query)

    @tool
    async def edit_work_file(path: str, old_text: str, new_text: str, version: str) -> str:
        """Replace a unique text block in business C# using the last read version."""
        return await call(work.write, path, new_text, version, old_text=old_text)

    @tool
    async def write_work_file(path: str, content: str, version: str) -> str:
        """Write business C#; version is its last read hash, or empty for a new file."""
        return await call(work.write, path, content, version)

    @tool
    async def inspect_work_changes() -> str:
        """List changed files, revision and actual compile/simulation results."""
        return await call(work.status)

    @tool
    async def verify_code_workspace() -> str:
        """Compile this revision and run fixed driver/Simulation checks, without devices."""
        nonlocal verification_cancelled
        if verification_cancelled:
            raise ValueError("本轮验证已被停止，请等待用户明确重新发起")
        await work.verify(thread_id)
        task = work.tasks[thread_id]
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            work.cancel(thread_id)
            raise
        result = await call(work.status)
        verification_cancelled = (
            json.loads(result).get("verification", {}).get("status") == "cancelled"
        )
        return result

    return safe_source_tools(
        [
            prepare_code_workspace,
            find_work_files,
            read_work_file,
            search_work_files,
            edit_work_file,
            write_work_file,
            inspect_work_changes,
            verify_code_workspace,
        ],
        "代码副本工具",
    )
