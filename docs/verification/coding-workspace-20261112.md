# 原地编码工作区 第一阶段验收

日期：2026-11-12。对应设计：[原地编码 Agent 方案](../features/in-place-coding-agent.md)。

## 已实现

- **项目即目录**：`CodingWorkspace` 直接以项目 `source_root` 为工作区，不再复制代码、不再走合并。
- **通用文件工具**：列目录、带行号读文本、内容搜索、新建/覆盖写（带版本哈希）、建目录、移动、删除（目录需 recursive）；路径限制在项目根内。
- **编码保持**：读取返回编码与哈希；写入保留原 UTF-8/UTF-16/GB18030 编码、BOM 和换行，原子替换。
- **Git 快照**：仓库在 `data/coding/snapshots/<project>/repo`，用 `--git-dir`/`--work-tree` 指向项目，项目里不出现 `.git`；构建产物通过 `info/exclude` 排除。
- **检查点与回滚**：手动检查点、单文件回滚、整项目回到检查点（会删除该检查点之后新增的文件），回滚本身也留检查点。
- **命令执行**：项目内 `cwd`、可配超时、超时结束进程树、输出截断并写日志；审批三档（allowlist / confirm / full），危险模式（格式化、删盘、改系统配置、管道执行）即使 full 也拒绝。
- **后台常驻**：启动返回 job id，可读尾部日志、可停止，项目关闭时统一结束。
- **用户自选目录**：新建/编辑项目可自行填写本机源码目录，不再要求管理员；仍拒绝指向助手数据目录（403）。
- **命令审批**：非白名单命令会生成待审批请求（`/coding/approvals`），批准后由服务端执行并回填结果，拒绝则不执行；工具不会反复重试。
- **审计**：命令记录写入 `data/coding/audit/<project>.jsonl`。
- **只读保护**：默认分析目录（`trunk`）保持只读，除非项目显式 `enabled=true`，避免问答引用的原代码被就地改写。
- **工具接入**：聊天工具改为 `list_files / read_file / search_files / write_file / create_directory / move_path / delete_path / run_command / start_process / read_process / stop_process / checkpoint / list_checkpoints / diff_checkpoint / restore_checkpoint`，旧的副本工具不再挂载。
- **API**：项目级 `/api/p/{project}/coding/*`，覆盖设置、目录树、文件、搜索、检查点、差异、回滚、命令和后台任务。

## 验证

- `tests/unit/coding/test_workspace.py`：新建/读取/覆盖保护/移动/删除、路径越界拒绝、检查点与单文件回滚、整项目回滚删除新增文件、前台命令、白名单确认、后台进程起停，7 项通过。
- `tests/integration/coding/test_api.py`：项目级 API 建项目→写文件→读目录→执行命令→列检查点，1 项通过。
- 聊天管线回归：`tests/integration/chat/test_api.py`、`test_autonomous_answer.py` 5 项通过。
- 全量后端：1241 项通过、2 项跳过、13 项失败；失败全部是本机 `NO_PROXY` 含 `[::1]` 导致的代理地址解析错误，与本次改动无关。
- 前端：`tsc -b` 通过，`npm test` 445 项通过，生产构建成功。
- `ruff check` 与 `ruff format --check` 通过。

## 端到端

- 聊天工具链回归 `tests/integration/coding/test_agent_loop.py`：脚本化模型在空目录里先 `write_file` 建文件，再 `run_command` 执行 `dotnet --version`，最后给出回答；断言文件内容、命令调用顺序、检查点已生成和 `coding` 事件已推送。1 项通过。
- 真实工程执行：把点胶机工程作为项目目录，通过编码执行器运行 `dotnet build Sp900SerialClient.csproj` 和 `dotnet run --project Sp900SelfTest`，构建成功、9 项协议自测全部通过，并生成检查点。说明普通命令（构建、测试）在白名单档位下可以直接完成。
- 空目录建工程：在空项目里用文件工具创建 `src/App.csproj` 和 `src/Program.cs`，再通过执行器运行 `dotnet build` 与 `dotnet run`，退出码均为 0，输出 `scaffold-ok 通信协议`，并生成检查点。
- 执行器补齐 `APPDATA`/`LOCALAPPDATA`/`ProgramData` 等环境变量，避免 `dotnet`/NuGet 在精简环境下报 `Value cannot be null (path1)`。

## 真实模型实跑开发任务书

- 环境：`deepseek-flash`，空目录 `C:\Users\w\Desktop\点胶机-agent`，项目级审批设为 `full`。
- 过程：模型先用 `run_command` 检查 .NET/NuGet 环境，再连续 `write_file` 创建工程、协议层、串口适配器、界面、图标和自测工程，运行 `dotnet build`、自测、`dotnet publish`，全程 40 次工具调用、约 4.5 分钟，未触发重复拦截。
- 产物：`Sp900SerialClient.cs`（约 43 KB）、`MainForm.cs`（约 56 KB）、`UiParts.cs`、`Icons.cs`、`SerialPortConnection.cs`、`SelfTest/` 两个文件，以及 `publish/win-x64/Sp900SerialClient.exe`（65,940,246 字节）。
- 独立复核（不只信模型自述）：`dotnet build` 两个工程均退出 0；直接运行 `SelfTest` 得到 **35 项通过、0 失败、退出码 0**；启动生成的 WinForms 程序，窗口标题为“SP900 点胶机通信工具”，界面截图见 `output/agent-run-ui.png`。
- 第一次实跑在检查 NuGet 缓存时反复执行近似命令，触发 116 步递归上限；随后新增 `CodingRepeatGuard`（同一工具+参数连续三次即拦截）并在编码提示中要求“了解基本情况后直接写代码”，第二次实跑未再出现空转。

## 尚未完成

- 真机连接、读取参数、设置参数仍需要接 SP900 设备验证；本次只验证了离线协议、构建、自测和界面启动。
- 文件级撤销与多会话冲突提示可以继续细化。

## 旧流程移除

原副本、合并、候选验证、需求断言、桌面流程、固定 C# 宿主和“编译与仿真环境”页已删除；`/threads/{id}/code-work/*` 与 `/api/settings/code-work` 接口不再注册（测试断言 404），旧前端面板一并移除。旧副本目录保留在磁盘，可手动清理。


