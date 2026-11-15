# 编码 Harness 调研与改造路线（2026-11-15）

目标：对照市面成熟编码 Agent/Harness 的实现，优化 ARKS 编码模块，使其能独立开发并维护大型 C# 代码库。

## 调研对象与关键做法

| 项目 | 关键实现 | 对我们的启示 |
| --- | --- | --- |
| **Aider** | 用 tree-sitter 构建全仓 **repo map**：列出关键类/函数签名，按引用关系用图排序，默认约 1k token 预算；模型先看地图再按需读文件（[repo map 文档](https://aider.chat/docs/repomap.html)） | 大仓库不能靠遍历；需要符号级地图 + token 预算 + 引用热度排序 |
| **SWE-agent** | 提出 ACI（Agent-Computer Interface）：简单紧凑的动作、带行号的窗口化文件查看、摘要式搜索、编辑后 lint 反馈、上下文折叠；Ablation 显示“编辑+lint”和“摘要搜索”显著提升解决率（[论文](https://arxiv.org/abs/2405.15793)） | 工具要少而稳；编辑后立即给结构化诊断；搜索/读取要有上限与摘要 |
| **OpenHands** | Docker 沙箱 runtime，client-server 执行动作，强调隔离、一致性、可复现（[runtime 文档](https://docs.openhands.dev/openhands/usage/architecture/runtime)） | 验收必须隔离数据目录/进程；命令执行要有边界与可复现环境 |
| **Cline** | 每次工具调用后在 shadow git 仓库打 checkpoint，可对比 diff、恢复文件或任务（[checkpoints](https://docs.cline.bot/core-workflows/checkpoints)） | 每步可回滚；失败可恢复到最近通过状态 |
| **Claude Code** | hooks 生命周期、subagents、skills、上下文压缩；Hooks 可在工具前后注入检查（[hooks](https://code.claude.com/docs/en/hooks)） | 用中间件在工具/模型边界做门禁、压缩、验收注入 |
| **Codex CLI** | 沙箱化命令执行 + 审批策略 + patch 式编辑（[仓库](https://github.com/openai/codex)） | 写操作与命令分级审批；diff 审核；命令沙箱 |

## 我们已有的能力

- `verify` 结构化构建/测试诊断；`check_ui` 截图与布局断言；`update_plan`；`AcceptanceGate`。
- 独立验收（CLI/纯函数/可执行文件/WinForms 截图）+ 自测告警；`ci.py` 多轮报告与耗时统计。
- 快照/检查点、`restore_checkpoint`、`ui-pass` 自动回退；重复读取限制；单命令 180s 上限。
- 10 用例矩阵（含 8 模块 Python 大仓库、Python+Node 跨语言、WinForms）。

## 差距（面向大型 C#）

1. **仓库地图缺失**：大解决方案只能逐个读文件，上下文与工具预算浪费严重。
2. **解决方案级构建/测试选择**：已能自动发现 sln/csproj，但还没有“按改动选择项目/测试”的增量策略。
3. **编辑后无即时诊断**：C# 编辑后要等下一次 `verify`，缺少 SWE-agent 式“编辑 + lint”反馈。
4. **检查点未与验收步骤绑定**：有快照但未在每次 `verify`/`check_ui` 成功后自动打“已通过”标记。
5. **大型 C# 用例缺失**：现有 .NET 用例是单工程/小工程，未覆盖多项目解决方案与较大代码量。
6. **无云端执行验证**：GitHub Actions 工作流仅 YAML 校验。

## 本轮已落地（P0/P1）

- `repo_map` 工具：tree-sitter 解析 C#，提取类/接口/方法/属性签名，按跨文件引用热度排序，按 token 预算裁剪（默认 1500 tokens）；大型 C# 项目先看地图再读文件。
- **自动注入**：C# 文件数 ≥8 时，构建期把仓库地图直接放进系统提示，不依赖模型主动调用。
- 单元测试覆盖：符号提取、预算裁剪、空仓、注入/跳过/失败。
- 生成/编码提示补充“大项目先 repo_map”。
- 运行时间预算 900s：到时强制收尾，由独立评分判定交付，避免无限跑。
- 命令输出编码：UTF-8 解码失败自动回退 GB18030，修复 Windows 中文命令输出乱码导致模型反复“修编码”的问题。
- **编辑后 C# 语法诊断**：write/edit/multi_edit 后立即用 tree-sitter 检查 `.cs` 语法，把 `syntax_errors`（行号 + 缺失/错误片段）附在工具结果里，模型不必等到下一次 `verify` 才发现。
- **验收通过自动 checkpoint**：`verify build/test` 成功后自动打 `verify-*` 检查点（Cline 式），失败可回滚到最近通过状态。
- 大型 C# 用例 `project-large-csharp`：Core + Api + CLI + 18 项自测（4 工程 / 10 个 .cs 文件）的 .NET 8 解决方案，隐藏验收跑 CLI 验证补货/低库存/总值/错误码；已加入 11 用例矩阵。

## 真实项目对照（2026-11-15）

用 `D:\zx2200\产能统计\产能统计.sln` 做验收标尺：18 个工程、376 个 `.cs`、.NET Framework 4.8（老式 csproj）+ WinForms。

- 原工程外部引用失效（`..\..\写胶图形编辑器\...AKRS.Base.dll`、`C:\SQLite\...`、Spire 安装路径），`LogTableRecordsDeleter`/`SQLite_SQL` 仍是 v3.5；
- 在副本中把引用修到本地 `refs/`、补 `DevComponents.DotNetBar2`、把 v2.0/v3.5 重定向到 v4.8 后，**MSBuild 全解决方案构建 0 错误 0 警告**；
- 编码模块新增 **legacy .NET Framework 检测**：识别非 SDK 风格 csproj 后自动走 MSBuild（vswhere/常见 VS 路径/PATH），命令用 PowerShell `&` 调用；`verify build` 在该真实解决方案上通过（增量约 1.2s）；
- 老式工程没有统一测试命令，`test_command` 需显式配置，避免误跑 `dotnet test`；
- 已知运行问题：`CapacityStatistics.exe` 启动时 `AKRS.Capacity.DB.Data..ctor` 抛 `DllNotFoundException`，是 SQLite 原生 interop 未随输出复制，不是源码编译问题。

## 后续优先级

- **P1**：按解决方案选择构建目标（只构建改动项目）；`repo_map` 结果进一步参与上下文选择。
- **P2**：更大规模 C# 解决方案（8+ 工程、30+ 自测）与“跨工程重构”任务；GitHub Actions 实跑与云端矩阵；命令沙箱/审批策略对齐 Codex。

## 参考

- Aider Repository map: <https://aider.chat/docs/repomap.html>
- SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering: <https://arxiv.org/abs/2405.15793>
- OpenHands Runtime Architecture: <https://docs.openhands.dev/openhands/usage/architecture/runtime>
- Cline Checkpoints: <https://docs.cline.bot/core-workflows/checkpoints>
- Claude Code Hooks: <https://code.claude.com/docs/en/hooks>
- OpenAI Codex CLI: <https://github.com/openai/codex>
