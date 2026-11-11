# 独立代码副本（已移除）

移除日期：2026-11-11。

按用户要求，基于 `AKRS.ZX2200` 固定工程、隔离副本、固定编译仿真与管理员合并确认的代码修改功能已整体移除，并按 Codex 式就地工作方式重建。本文件保留为历史入口，避免旧链接失效。

## 已移除的内容

- `backend/app/modules/code_work/`：环境、文件、服务、逐轮历史、差异、验证执行器、三方合并、事务写回与恢复。
- `backend/app/agents/tools/code_work.py`、`agents/runtime/code_work_repair.py`、`agents/runtime/code_work_reads.py`：聊天工具、验证失败回灌与读取进度保护。
- `/api/settings/code-work` 与 `/api/threads/{thread}/code-work` 全部接口；管理员“系统配置 → 代码修改”。
- 前端 `features/chat/code_work/`：变更摘要、右侧变更面板、需求断言、合并、验证报告与恢复。
- 相关测试与验收脚本：`tests/unit/code_work/`、`tests/integration/chat/test_code_work*.py`、`scripts/verification/code_work*.py`、`scripts/verification/wafer_vendor*.py`。
- 原有提示词中的 `prepare_code_workspace`、`edit_work_file`、`verify_code_workspace` 等工具说明。

## 保留的内容

- 本机历史副本与验证报告：`data/scratch/cw/` 原样保留，不再由应用读写，不会随功能移除被删除。
- 数据库兼容层 `infrastructure/database/legacy_code_work.py`：仍被模型额度记账和历史备份恢复引用，不能删除。
- 历史验收记录：`docs/verification/code-work-*.md` 等按日期保留，作为当时的证据，不代表当前功能。
- 只读源码分析与代码建议：`read_source`、`search_source`、`csharp_relations` 等不受影响。

## 替代方案

新的通用代码工作区已接入，见[通用代码工作区](workspace-work.md)：直接在管理员配置的本地工作目录读写文件、执行白名单命令、展示差异与命令输出，并保留逐次快照与还原；不再要求固定工程副本、需求断言宿主或管理员合并确认。设计与分期见[通用代码工作与就地模式改造方案](../architecture/general-code-work.md)。
