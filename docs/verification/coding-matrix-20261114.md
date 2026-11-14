# 编码模块多案例验收（2026-11-14）

## 目的

用不同任务类型持续测试编码模块，覆盖：从零生成（Python / .NET 控制台 / 原生 Web）、现有项目修复。每次运行都在隔离数据目录与空/种子工作区里跑真实 Agent，并由独立评分脚本复核。

## 用例与判定

| 用例 | 类型 | 判定 |
| --- | --- | --- |
| `python-cli` | 从零生成 Python CSV→JSON 命令行工具 | compileall 通过、pytest ≥5 全过、文件齐全、无 TODO |
| `dotnet-console` | 从零生成 .NET 8 日志分析器 + 控制台自测 | build 0/0、自测 ≥6 全过、README、无 TODO |
| `bugfix-python` | 修复现有库存模块（测试文件受保护） | pytest 全过、测试文件哈希未变、README、无 TODO |
| `web-static` | 从零生成原生 JS 单页任务看板 | `node --check` 通过、`node --test` ≥6、界面三文件齐全、无 TODO |

只有 run 状态为 `completed` 且评分全绿才算通过。

## 稳定性结果

最近 3 轮完整批次（`scripts/acceptance/coding/batch.py`，每轮 4 个用例）：

| 批次 | python-cli | dotnet-console | bugfix-python | web-static | 通过 |
| --- | --- | --- | --- | --- | --- |
| 1 | PASS | PASS | PASS | PASS | 4/4 |
| 2 | PASS | FAIL（自测 1 项失败） | PASS | PASS | 3/4 |
| 3 | PASS | PASS | PASS | PASS | 4/4 |

合计 11/12。唯一失败是 .NET 用例自测“坏行不计入统计”真实实现缺陷，Agent 在重试后仍未修正；这是应当由矩阵暴露的质量问题。

运行目录：`output/acceptance/coding-<case>-<时间>/`；批次汇总：`output/acceptance/coding-batch-*/batch.json`。

## 本轮暴露并修复的问题

1. 非 UI 生成被强制要求 `check_ui`：改为 `ui_required`，仅 WinForms 强制。
2. `verify build/test` 对 Python/Node 项目回退成 dotnet：按项目文件探测（compileall、pytest、npm、node）。
3. `run_command` 跑的 `python -m pytest`、`node --check`、`node --test` 不计入验收：扩展识别；此前失败的构建命令还会被误判为通过，现要求退出码为 0 且输出无 `Cannot find module/SyntaxError`。
4. `[FAIL]`、`7 PASS, 1 FAIL`、Node TAP/`ℹ pass` 汇总不被统计：解析补齐，门禁不再误放行。
5. 质量扫描误报：把《任务书.md》、“时间占位文本”“todos 变量”当成占位；改为只认大写 `TODO/FIXME` 整词，并排除任务书。
6. 构建/测试先过就强制收尾，导致 Web 界面文件未创建：收尾条件改为“技术项 + 任务书列出的文件 + README 都齐”，缺文件继续做。
7. 自测失败后模型看不到失败细节：验收提示追加自测输出尾部；重试次数从 3 提到 5。
8. `node --test tests/` 在 Node 24 把目录当模块：用例改成显式 `tests/logic.test.mjs`。

## 后续

- 继续压 dotnet-console 的稳定性（失败集中在自测逻辑错误）。
- 增加“较大现有项目重构”“跨文件 bug 修复”用例。
- 每轮 4 用例 × 3 次作为回归基线；把批次报告接入可手动触发的 CI。
