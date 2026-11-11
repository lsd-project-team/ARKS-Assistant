# 通用代码工作区验收（2026-11-11）

## 范围

按用户要求移除原 `code_work` 隔离副本流程，改为 Codex 式就地工作区：直接读写管理员配置的本地目录、批量修改、受控命令执行与逐条审批、右侧差异与命令输出面板、写前快照与还原。

## 变更

- 移除：`backend/app/modules/code_work/`、`agents/tools/code_work.py`、`code_work_repair.py`、`code_work_reads.py`、`/code-work` 与 `/settings/code-work` 接口、管理员“代码修改”配置、前端 `features/chat/code_work/`、相关测试与验收脚本（提交 `f12b6c92`）。
- 新增：`backend/app/modules/workspace_work/`（配置、路径与编码、命令执行、快照日志、服务、接口）、`agents/tools/workspace_work.py`、前端 `features/chat/workspace_work/`、导航入口与管理员配置（提交 `3d5a2ae4`）。
- 保留：`data/scratch/cw/` 历史副本与报告不删除、不读取；`legacy_code_work.py` 因额度记账和备份恢复继续保留。

## 验证

- 后端完整回归：`1262 passed, 2 skipped`。13 个失败全部为 `httpx` 读取本机代理环境变量时抛 `InvalidURL: Invalid port: ':1]'`，集中在 `test_model_probe`、`test_provider_lifecycle` 和 1 个协议参数用例，均为未改动测试，与本功能无关。
- 新增后端测试 13 项：读写与版本锁、唯一匹配、批量补丁原子性、路径越界与忽略目录、搜索行号、还原（单文件/整轮）、白名单拒绝、审批同意、审批拒绝、命令超时、API 往返与数据目录拒绝。
- Ruff：`app` 与本次新增/修改测试文件通过。
- 前端：`tsc -b` 通过，`npm test` 452 项通过，生产构建成功（约 1 分 19 秒）。
- 数据：测试只写临时目录；`trunk/` 和正式 `data/` 未被写入。

## 已知边界

- 工作区不提供操作系统级沙箱，权限等同当前用户；命令审批默认开启，管理员可对白名单命令开启自动执行。
- 命令为一次性进程，没有交互式终端或后台常驻任务；超过单条超时会终止进程树。
- 快照按哈希保存每个被修改文件的版本，不复制整个工作目录；未实现快照容量上限和自动清理。
- 不自动 git commit/stash；未实现远程执行、容器或并行任务。
- 未在真实浏览器中逐项点检审批与还原流程；本轮以 API 集成测试、组件渲染测试和构建为证据。

## 后续

- 补充浏览器级端到端验证（审批弹窗、还原确认、命令输出展开）。
- 评估快照清理策略、命令输出归档和失败重试保护。
- 需要“生成独立可运行工程”时，在工作区内新建工程并加入白名单命令（`dotnet`/`MSBuild`）；本机已确认 .NET 9 SDK、VS2022 MSBuild 与 .NET Framework 4.8 参考程序集可用。
