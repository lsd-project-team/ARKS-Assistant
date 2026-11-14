# 编码模块多案例验收（2026-11-14）

## 目的

用与 SP900 不同的任务类型持续测试编码模块，覆盖：从零生成（非 UI）、从零生成（.NET 控制台）、现有项目修复。每次运行都在隔离数据目录、空/种子工作区里跑真实 Agent，并由独立评分脚本复核。

## 用例与判定

| 用例 | 类型 | 判定 |
| --- | --- | --- |
| `python-cli` | 从零生成 Python CSV→JSON 命令行工具 | `compileall` 通过、`pytest` ≥5 全过、文件齐全、无 TODO |
| `dotnet-console` | 从零生成 .NET 8 日志分析器 + 控制台自测 | `dotnet build` 0/0、自测 ≥6 全过、README、无 TODO |
| `bugfix-python` | 修复现有库存模块（测试文件受保护） | `pytest` 全过、测试文件哈希未变、README、无 TODO |

只有 run 状态为 `completed` 且评分全绿才算通过。

## 结果

`scripts/acceptance/coding/batch.py` 连续 3 个用例全部通过：

| 用例 | 运行状态 | 构建 | 测试 | 文件 | 测试未改 | 规范 |
| --- | --- | --- | --- | --- | --- | --- |
| python-cli | completed | 通过 | 7/7 | 齐全 | — | 无占位 |
| dotnet-console | completed | 0/0 | 9/9 | 齐全 | — | 无占位 |
| bugfix-python | completed | 通过 | 4/4 | 齐全 | 未改动 | 无占位 |

运行目录：`output/acceptance/coding-<case>-20261114-*`；批次汇总在 `output/acceptance/coding-batch-*/batch.json`。

## 本轮暴露并修复的问题

1. generation 模式对所有任务强制 `check_ui`，Python/控制台项目会被卡死：改为按 `ui_required` 判断，WinForms 才要求界面自检。
2. `verify build` 对 Python/Node 项目回退成 `dotnet build`：新增按项目文件探测构建命令（Python compileall、npm build、dotnet build）。
3. `verify test` 不识别 Python：新增 pytest 探测与 `python -m pytest` 的允许清单。
4. `run_command` 执行的 `python -m pytest` 不计入验收：扩展识别 Python/Node 构建与测试，技术项全过即可强制收尾。
5. 自测失败输出 `[FAIL]`、`7 PASS, 1 FAIL` 不被统计，门禁误判通过：补充 `[FAIL]` 行与 `N PASS/N FAIL` 解析。
6. 质量扫描把《任务书.md》中的“TODO/占位”误判为代码占位：扫描时排除任务书。
7. .NET 用例漏写 README：生成提示改为“先写 README 与全部交付物，再实现代码”，并把 README 纳入评分。

## 后续

- 增加 Web/前端、较大现有项目重构、跨文件 bug 修复用例。
- 每个用例连续跑 3 次，统计通过率与工具调用数，形成回归基线。
- 把批次报告接入 CI（可手动触发），失败时保留现场。
