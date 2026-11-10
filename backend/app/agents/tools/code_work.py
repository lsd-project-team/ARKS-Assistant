"""聊天中的代码工作工具；所有动作固定到当前对话的独立副本。"""

import asyncio
import json

from langchain_core.tools import tool

from app.agents.tools.guards import safe_source_tools
from app.core.config import dump_json

CODE_WORK_GUIDANCE = """
【独立代码副本】
本对话可使用代码工作工具修改管理员配置的原工程 Simulation 副本。
直接理解用户描述的问题和需求，无需斜杠命令、附件或预先创建副本，也不要求用户输入特定口令。
用户描述软件故障、代码缺陷或期望的新功能时，默认按修复或实现任务处理，直接完成相关代码修改及验证，不只给建议或再次询问是否开始。
仅解释原因、分析流程、讨论方案或明确暂不修改时，只回答；问题描述不足以确定预期行为时先核对相关实现，必要时询问具体缺失信息。
工艺、设备操作和经验问答按实际问题回答，不自动扩为代码修改。
聊天工具只修改副本，写回原工程须在合并面板明确确认。
用户要求实际修改时先 prepare_code_workspace，再用 read_work_file/search_work_files 核对副本。
用户指定文件、类或方法时，先核对完整声明；不能把其他类中的同名方法当成修改目标。
知道文件名时先 find_work_files 定位；修改后 inspect_work_changes 核对文件范围。
同一版本同一范围已读到的内容直接复用，不反复请求相同行段；缺少方法结尾时调整行范围，不重复原请求。
副本与 /workspace/ 原分析源码可能是不同版本；修改依据、文件版本和差异必须来自工作副本工具。
edit_work_file 替换唯一匹配的原文；write_work_file 保存完整文件或新增业务 C#，版本必须来自本轮读取。
用户只询问、讨论时不修改。实际修改需求应完成编辑及 verify_code_workspace；编译失败按日志修复后重跑。
修改业务代码时使用set_work_requirement保存与本次需求对应的C#断言测试，随后再验证。
测试代码是Run方法体，支持System/Linq/Reflection/HarmonyLib及using static CodeWork.Harness。
使用Check(条件,说明)执行真实行为断言；可用Invoke/typeof访问原类型，不能用恒真断言代替需求验证。
新一轮修订既有需求时，使用原用例id/version更新，不新建同目标用例并留下失效旧断言；保留历史报告。
需求测试应执行已编译业务类型，不依赖源码相对路径或用源码字符串包含关系代替行为验证。
int CountCalls(MethodBase method, Action action)返回action内原方法的实际调用次数，不替换业务实现。
验证宿主已初始化虚拟硬件；测试填写C#方法体，不另建Main/Run或模拟驱动来替代原业务。
宿主已导入点胶Models/Modules/Controllers，可使用System1Domain和DispenseModule等类型。
CountCalls的返回值只统计传入Action执行期间的调用；用空Action再次调用得到的是0，不是上次结果。
反例和修复使用同一预期断言：如预期一次，原代码实际两次时该断言应失败，修复后应通过。
原实现的两次调用写入失败日志，不添加修复后仍要求两次的相反断言，不为通过而削弱测试。
每轮最多验证3次，失败后根据日志修复业务代码再重验；首次验证后本轮验收测试固定，不能削弱断言。
需要原界面按钮流程时使用enable_work_desktop_flow开启固定启动、暂停、继续、生产、停止验证。
本轮验证被用户停止（cancelled）时，说明未完成并停止，不自行重新启动验证。
首次完整验证是基础回归，每项新需求仍需对应预期与验证；明确区分已验证和未覆盖的行为。
没有任意命令、写回原件或设备控制工具。不能更改仿真驱动、启动入口或工程配置。
修改副本引用在代码修改面板查看，不使用指向原目录的 source: 链接冒充修改后的文件依据。
回复说明实际改动及本版验证结果，不把已有检查通过说成视觉、力控、标定或真实设备已验收。
"""


def code_work_tools(work, thread_id, emit, *, run_id=""):
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
        return await call(work.write, path, new_text, version, old_text=old_text, run_id=run_id)

    @tool
    async def write_work_file(path: str, content: str, version: str) -> str:
        """Write business C#; version is its last read hash, or empty for a new file."""
        return await call(work.write, path, content, version, run_id=run_id)

    @tool
    async def inspect_work_changes() -> str:
        """List changed files, revision and actual compile/simulation results."""
        return await call(work.status)

    @tool
    async def set_work_requirement(
        name: str, expectation: str, code: str, test_id: str = "", version: str = ""
    ) -> str:
        """Save a C# requirement body with Check assertions before first verification.

        Use the returned id/version to update it.
        """
        return await call(
            work.set_requirement,
            {
                "id": test_id,
                "version": version,
                "name": name,
                "expectation": expectation,
                "code": code,
            },
            run_id=run_id,
        )

    @tool
    async def enable_work_desktop_flow(enabled: bool, revision: int) -> str:
        """Set original MainForm button flow in an independent Simulation process."""
        return await call(work.set_desktop_flow, enabled, revision, run_id=run_id)

    @tool
    async def verify_code_workspace() -> str:
        """Compile this revision and run fixed driver/Simulation checks, without devices."""
        nonlocal verification_cancelled
        if verification_cancelled:
            raise ValueError("本轮验证已被停止，请等待用户明确重新发起")
        await work.verify(thread_id, run_id=run_id)
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
            set_work_requirement,
            enable_work_desktop_flow,
            verify_code_workspace,
        ],
        "代码副本工具",
    )
