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
- **审计**：命令记录写入 `data/coding/audit/<project>.jsonl`。
- **只读保护**：默认分析目录（`trunk`）保持只读，除非项目显式 `enabled=true`，避免问答引用的原代码被就地改写。
- **工具接入**：聊天工具改为 `list_files / read_file / search_files / write_file / create_directory / move_path / delete_path / run_command / start_process / read_process / stop_process / checkpoint / list_checkpoints / diff_checkpoint / restore_checkpoint`，旧的副本工具不再挂载。
- **API**：项目级 `/api/p/{project}/coding/*`，覆盖设置、目录树、文件、搜索、检查点、差异、回滚、命令和后台任务。

## 验证

- `tests/unit/coding/test_workspace.py`：新建/读取/覆盖保护/移动/删除、路径越界拒绝、检查点与单文件回滚、整项目回滚删除新增文件、前台命令、白名单确认、后台进程起停，7 项通过。
- `tests/integration/coding/test_api.py`：项目级 API 建项目→写文件→读目录→执行命令→列检查点，1 项通过。
- 聊天管线回归：`tests/integration/chat/test_api.py`、`test_autonomous_answer.py` 5 项通过。
- `ruff check` 与 `ruff format` 通过。

## 尚未完成

- 前端：项目创建选目录、变更/差异面板、命令审批弹窗、后台任务面板尚未接入。
- 旧副本流程（`code_work` 的合并、验证、需求断言、桌面流程、环境页）仍保留在代码中，只是不再挂到聊天工具；按计划在切换阶段删除。
- 普通用户创建项目时选择任意源码目录仍受管理员权限限制，需要按“用户自选目录”调整。
- 真正的端到端验收（由聊天 Agent 从空目录完成点胶机开发任务书）尚未执行。
