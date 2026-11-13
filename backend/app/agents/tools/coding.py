"""聊天中的原地编码工具；直接读写项目目录，用快照回滚。"""

import asyncio

from langchain_core.tools import tool

from app.core.config import dump_json

CODING_GUIDANCE = """
【项目编码】
当前项目目录就是工作区，所有路径都使用项目内相对路径。
读取和修改项目文件用 read_project_file / list_files / search_files /
find_files / write_file / edit_file；
带 /workspace/ 前缀的只读工具用于引用当前源码，不要用它们判断项目工作区的可写状态。
工艺、设备操作、故障与经验类问题不要当作编码任务：先调用 search_debug_issues 检索本地问题与经验，
再结合检索结果回答；只有用户明确要求修改代码、创建工程或运行命令时才使用文件与命令工具。
用户明确要求实现或修改时，先 list_files / read_project_file / search_files / find_files 了解现状，
再建目录、写文件、跑构建或测试。
新建项目可以是空目录，从零创建工程结构也可以。
修改已有文件优先用 edit_file：按原文精确替换，需要先读取并带上 version；大范围重写才用 write_file。
覆盖已有文件必须带上一次读取得到的 hash；新建文件 hash 留空。
图片、图标等二进制资源用 write_binary_file，内容为 base64。
需要看界面、报错截图或设计图时，用 view_image 打开项目内的图片（PNG/JPG/GIF/WebP）；
运行程序后先截图保存到项目内，再用 view_image 查看，不要凭猜测描述界面。
删除、移动前系统会自动建快照；每轮结束系统会自动记录检查点，用户可从检查点回滚。
run_command 用于构建、测试和一次性命令；start_process 用于常驻服务，
返回 job_id 后可用 read_process/stop_process 查看和停止。
命令不在自动放行范围时会在本轮内等待用户确认；确认后自动继续。被拒绝或超时不要反复重试。
当前权限决定是否可以写文件和是否需要确认：仅可查看时写入与写命令会被直接拒绝，需要时请让用户切换权限。
命令输出会实时推送，结束后返回末尾摘要；需要更多时用 read_process 或读取日志。
构建或测试用 verify：返回 file:line:code 结构化诊断，不要只从日志尾部猜错误。
界面用 check_ui：自动跑 --screenshot、校验布局并生成截图，再用 view_image 看截图。
不要编造执行结果；失败时读取日志、修复后重试。用户只询问、讨论时不修改任何文件。
同一命令或同一文件读取不要连续重复；连续重复会被拦截。了解基本情况后直接开始创建工程、写代码和构建。
"""

GENERATION_GUIDANCE = """
【从零生成】
本轮项目目录为空，目标是一次交付可运行、可验收的完整系统。
1. 先读需求/任务书，调用 update_plan 建立 4-7 步计划
   （协议层 → 回放测试 → 构建 → 界面骨架 → 业务功能 → 截图自检 → 验收）。
2. 先实现协议层与离线回放测试，verify test 通过后再做界面；
   自测覆盖需求要求的用例即可，不要额外加编码页/区域设置等设备未要求的测试；
   自己新增的用例反复失败时先删除或修正，不要卡在同一个用例上；
   若目录里已有 App.csproj / Program.cs / MainForm.cs / UiParts.cs / ScreenshotTool.cs
   （生成模式会自动准备 WinForms 骨架），不要重复 scaffold，直接在骨架上实现页面与业务逻辑；
   否则先 scaffold_winforms。每完成一步更新计划状态。
3. 完成前必须调用 verify build、verify test 与 check_ui；对生成的截图调用 view_image 核对；任何一项失败先修复，
   不得带着错误或空白界面宣称完成。check_ui 失败时先看返回的 issues 与 log_tail：
   启动异常（尤其是 TabPage/Panel 结构错误）必须先修，修完重新 check_ui。
4. 截图契约固定为 `--screenshot <png路径> <标签页索引>`（scaffold_winforms 已内置），
   不要改成“输出目录”；控件 bounds 要递归打印全部层级（不限深度），
   check_ui 依赖它校验参数表单、按钮与日志区。
5. 最终回答按验收清单逐项给出证据（构建退出码、自测数量、截图路径），未满足项明确列出。
"""


def coding_tools(work, thread_id, emit, *, run_id="", checks=None):
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
    async def view_image(path: str) -> str:
        """Look at an image file in the project directly (screenshot, design, icon).

        The image is attached to this turn's model context automatically.
        """
        try:
            result = await asyncio.to_thread(work.read_image, path)
        except Exception as error:  # 失败原因让模型看到，由它修正路径或说明无法查看
            emit("coding", {"tool": "view_image", "ok": False})
            return dump_json({"ok": False, "error": str(error)})
        emit("coding", {"tool": "view_image", "ok": True})
        return dump_json(
            {
                "ok": True,
                "path": result["path"],
                "format": result["format"],
                "width": result["width"],
                "height": result["height"],
                "note": "图片已附在本轮消息，可直接查看并回答。",
            }
        )

    @tool
    async def verify(kind: str = "build") -> str:
        """Build or test the project; returns file:line:code diagnostics and a summary.

        For test, runs the configured test command, or the first tests/*.csproj
        self-test console project, or `dotnet test` when neither exists.
        """
        try:
            result = await asyncio.to_thread(work.verify, kind)
        except Exception as error:
            result = {"ok": False, "kind": kind, "error": str(error)}
        if checks is not None:
            checks.record_verify(result)
        emit(
            "verify",
            {
                "ok": bool(result.get("ok")),
                "kind": kind,
                "summary": result.get("summary") or result.get("error", ""),
                "errors": result.get("errors", [])[:10],
            },
        )
        return dump_json(result)

    @tool
    async def check_ui(tabs: int = 2) -> str:
        """Render screenshots, validate layout, and return shot paths for view_image.

        The app must support `--screenshot <png-path> <tab-index>` (scaffold_winforms
        provides it) and print every control's bounds recursively, without a depth
        limit. It must not treat the argument as an output directory.
        """
        try:
            result = await asyncio.to_thread(work.check_ui, tabs)
        except Exception as error:
            result = {"ok": False, "error": str(error)}
        if checks is not None:
            checks.record_ui(result)
        emit(
            "ui_check",
            {
                "ok": bool(result.get("ok")),
                "issues": (result.get("issues") or [])[:10],
                "shots": result.get("shots", []),
                "notes": result.get("notes", []),
            },
        )
        return dump_json(result)

    @tool
    async def scaffold_winforms(product: str = "SP900 点胶机上位机") -> str:
        """Create the verified WinForms skeleton (layout + screenshot entry) in an empty project.

        The generated Program.cs already supports `--screenshot <png-path> <tab-index>`.
        Keep that contract; do not replace it with an output-directory argument.
        """
        try:
            result = await asyncio.to_thread(
                work.scaffold, "winforms", {"__PRODUCT__": product}
            )
        except Exception as error:
            result = {"ok": False, "error": str(error)}
        if checks is not None:
            checks.record_scaffold(result)
        emit("coding", {"tool": "scaffold_winforms", "ok": bool(result.get("ok"))})
        return dump_json(result)

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
        view_image,
        verify,
        check_ui,
        scaffold_winforms,
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
