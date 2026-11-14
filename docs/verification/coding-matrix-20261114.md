# 编码模块多案例验收（2026-11-14）

## 目的

用不同任务类型持续测试编码模块，覆盖：从零生成（Python / .NET 控制台 / 原生 Web）、现有项目修复。每次运行都在隔离数据目录与空/种子工作区里跑真实 Agent，并由独立评分脚本复核。

## 用例与判定

| 用例 | 类型 | 判定 |
| --- | --- | --- |
| `python-cli` | 从零生成 Python CSV→JSON 命令行工具 | compileall 通过、pytest ≥5 全过、文件齐全、无 TODO |
| `dotnet-console` | 从零生成 .NET 8 日志分析器 + 控制台自测 | build 0/0、自测 ≥6 全过、README、无 TODO |
| `bugfix-python` | 修复现有库存模块（测试文件受保护） | pytest 全过、测试文件哈希未变、README、无 TODO |
| `bugfix-multi` | 修复 shop 包跨文件折扣 bug（测试受保护） | pytest 全过、测试文件哈希未变、README、无 TODO |
| `feature-python` | 现有待办服务增加截止日期/逾期 | 现有 10 测试通过、隐藏验收 due/overdue、测试文件未被修改 |
| `refactor-python` | 重构现有订单统计模块（测试受保护） | pytest 全过、测试文件哈希未变、README、无 TODO |
| `web-static` | 从零生成原生 JS 单页任务看板 | `node --check` 通过、`node --test` ≥6、界面三文件齐全、无 TODO |
| `winforms-tool` | 从零生成 WinForms 点检计时器 | build 0/0、两页截图非空白、布局断言（2 页签/6 按钮/5 输入/日志 ≥120px） |

只有 run 状态为 `completed` 且评分全绿才算通过。

## 评分口径（2026-11-14 起）

- **独立验收（acceptance）为必需项**：直接运行 CLI、纯函数或构建产物验证行为，不依赖 Agent 自写的测试；避免“自测写错误伤正确实现”。
- **Agent 自测（selftest）降为交付质量告警**：仍会执行并在报告中标注，但不由它决定整体通过与否。
- 构建、必需文件、受保护测试文件、TODO/FIXME 仍是硬性项。

## CI 入口

```powershell
backend\.venv\Scripts\python.exe scripts\acceptance\coding\ci.py --rounds 1
```

输出 `output/acceptance/coding-ci-<时间>/report.md` 与 `report.json`；任一轮/用例失败退出码非 0，可直接接 CI。

## 稳定性结果

最近 3 轮完整批次（`scripts/acceptance/coding/batch.py`，每轮 5 个用例，按独立验收判定）：

| 批次 | python-cli | dotnet-console | bugfix | refactor | web-static | 通过 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | PASS | PASS | PASS | PASS | PASS | 5/5 |
| 2 | PASS（自测告警） | PASS | PASS | PASS | PASS | 5/5 |
| 3 | PASS（自测告警） | PASS（修正选工程后复评） | PASS | PASS | PASS | 5/5 |

合计 15/15。python-cli 有两次 Agent 自测断言写错（selftest 告警），但独立验收直接跑 CLI 均通过——说明“自测降为告警、独立验收为准”的口径按预期工作。

### 6 用例 CI 回归（含跨文件 bugfix）

| 轮次 | 用例数 | 通过 | 单例耗时 |
| --- | --- | --- | --- |
| 1 | 6 | **6/6** | 37–109s |
| 2 | 6 | **6/6** | 37–74s |

合计 **12/12**；报告在 `output/acceptance/coding-ci-20261114-203906/report.md`。dotnet-console 在早前偶发 794s 的长尾本轮未复现（74–92s），仍需继续观察。

### 8 用例 CI 回归（加入 feature-python）

| 轮次 | 用例数 | 通过 | 单例耗时 |
| --- | --- | --- | --- |
| 1 | 8 | **8/8** | 39–102s |
| 2 | 8 | 7/8 | 37–134s（dotnet 超时 947s） |

合计 **15/16**。第二轮 dotnet-console 在 15 分钟内未收尾（仍在修构建，计划/构建未完成），被超时终止；说明该用例存在长尾。已把 CI 默认超时提到 20 分钟，并把超时状态明确标记为 `timeout`（不再显示 `running`）。报告：`output/acceptance/coding-ci-20261114-214453/report.md`。

运行目录：`output/acceptance/coding-<case>-<时间>/`；批次汇总：`output/acceptance/coding-batch-*/batch.json`。

## 本轮新增

- 独立验收脚本：`cases/python-cli/acceptance/check.py`（直接跑 CLI：引号逗号、空文件、indent、缺文件退出码）、`cases/web-static/acceptance/check.mjs`（直接 import `logic.mjs` 验证纯函数）、`cases/dotnet-console/acceptance/check.py`（直接运行可执行工程，覆盖坏行/非法等级/等级过滤/缺文件）。
- 评分器：`selftest` 只做告警，`acceptance` 必需；兼容 UTF-8 BOM 的 case 配置。
- .NET 验收自动挑选 `OutputType=Exe` 的可运行工程（避免误选 Library）。

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

- 继续压 dotnet-console 的真实行为缺陷（独立验收已能区分自测误报与实现错误）。
- 增加“较大现有项目重构”“跨文件 bug 修复”用例；每轮 5 用例 × 3 次作为回归基线，把批次报告接入可手动触发的 CI。
