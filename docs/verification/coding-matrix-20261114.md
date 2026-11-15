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
| `project-large` | 图书馆服务（8 模块 + 24 测试）加搜索分页/热门榜 | 现有 24 测试通过、隐藏验收分页/热门榜 + auth/导出/通知回归 |
| `project-large-csharp` | 多工程 .NET 8 解决方案（Core + Api + CLI + 18 项自测）加补货 | build 0/0、自测 18 项、隐藏验收跑 CLI 验证补货/低库存/总值/错误码 |
| `capacity-db` | 真实 .NET Framework 4.8 数据库层（AKRS.Capacity.DB）加名称规范化 | MSBuild 构建 0/0、隐藏检查程序直接调用 `NormalizeName` 验证边界 |
| `capacity-app` | 真实 WinForms 应用（产能统计）加 `--title-suffix` | MSBuild 构建 0/0、`check_app` 验证默认/带参/含空格窗口标题 |
| `capacity-zero-cli` | **从空目录**生成产能统计查询 CLI（.NET Framework 4.8） | MSBuild 构建 0/0、隐藏验收对比 SQLite 周/月汇总与错误码 |
| `capacity-zero-ui` | **从空目录**生成 WinForms 产能统计看板 | build 0/0、截图/布局、标题 `产能统计`、WEEK/MONTH 文本与 CSV 独立计算一致 |
| `capacity-zero-app` | **从空目录**生成完整 WinForms 桌面应用（无骨架） | build 0/0、5 导航 + 7 天柱状图 + 标题/WEEK/MONTH + 截图 |
| `capacity-zero-pages` | **从空目录**生成多页面应用（导航切换 + 导出） | build 0/0、5 页截图 + PAGE 标题 + WEEK/MONTH + CSV 导出数据一致 |
| `capacity-zero-dbapp` | **从空目录**生成直连 SQLite 的 .NET Framework WinForms 应用 | MSBuild 0/0、5 页截图、WEEK/MONTH 与 SQL 计算一致、导出数据一致 |
| `cross-language` | Python service + Node client 跨语言仓库 | pytest 与 node:test 通过、隐藏验收同时验证 full_name/initials |
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

### dotnet 长尾与真实缺陷（本轮定位）

- 失败构建/测试命令原先**不记录**，门禁只能给泛泛的“未通过 verify build”，模型看不到编译错误。已改为失败也记录 `errors/warnings/tail`，并把错误详情带回门禁提示；改进后 dotnet 单跑 75s 通过（`coding-dotnet-console-20261114-221945`）。
- 评测脚本原先在项目根目录跑 `dotnet build`；当工程放在 `src/`、`tests/` 子目录时直接 MSB1003 误判失败。已改为自动发现 `*.sln` / 可运行 `*.csproj` 再构建；此前一次“构建失败”的 dotnet 运行复评后为 PASS。
- 最终确认轮 8 用例 7/8：dotnet 一次真实实现 bug（时间戳解析把所有行判坏行，自测 5 项失败）；重跑 2 分钟通过（`coding-dotnet-console-20261114-224400`）。
- `feature-python` 曾因 `overdue(today)` 契约不清（`date` vs ISO 字符串）失败；任务书已明确“接受 date 或 YYYY-MM-DD”，重跑通过。

### 最终 8 用例 CI

| 轮次 | 用例数 | 通过 | 单例耗时 |
| --- | --- | --- | --- |
| 1 | 8 | **8/8** | 41–133s |
| 2 | 8 | **8/8** | 36–146s |

合计 **16/16**；报告：`output/acceptance/coding-ci-20261114-234709/report.md`。加入“禁止安装浏览器依赖 + 单命令 180s 上限”后，之前 668s 的长尾未再复现；CI 报告新增每用例平均/最大耗时统计。

### 9 用例 CI（加入 project-large）

| 轮次 | 用例数 | 通过 | 单例耗时 |
| --- | --- | --- | --- |
| 1 | 9 | **9/9** | 41–126s |
| 2 | 9 | **9/9** | 46–256s |

合计 **18/18**；报告：`output/acceptance/coding-ci-20261115-002025/report.md`。`project-large` 为 5 模块 + 15 测试的图书馆服务，要求新增搜索分页与热门榜；现有测试受保护，隐藏验收直接调用服务验证分页、大小写、非法参数与热门排序。两轮耗时 91s / 256s。

工作流 `.github/workflows/coding-acceptance.yml` 已通过 YAML 解析校验（Windows runner，secret `ARKS_API_KEY`，手动触发并上传报告 artifact）。

### 10 用例 CI（加入 cross-language 与扩大后的 project-large）

| 轮次 | 用例数 | 通过 | 单例耗时 |
| --- | --- | --- | --- |
| 1 | 10 | **10/10** | 46–210s |
| 2 | 10 | **10/10** | 38–177s |

合计 **20/20**；报告：`output/acceptance/coding-ci-20261115-052808/report.md`。

- `cross-language`：Python `service/` + Node ESM `client/`，隐藏验收同时跑 pytest 与 node:test，验证 `full_name`/`initials` 与旧行为回退。
- `project-large` 扩为 **8 模块 / 24 测试**（新增 auth、CSV 导出、逾期通知），隐藏验收同时做搜索分页/热门榜与旧模块回归；两轮 176s / 148s。

### 11 用例 CI（加入多工程 C# 解决方案）

| 轮次 | 用例数 | 通过 | 单例耗时 |
| --- | --- | --- | --- |
| 1 | 11 | **11/11** | 48–166s |
| 2 | 11 | **11/11** | 45–232s |

合计 **22/22**；报告：`output/acceptance/coding-ci-20261115-122134/report.md`。本轮包含自动 repo map、编辑后语法诊断、verify 自动 checkpoint、命令编码回退；winforms 两轮 99s / 80s。

### 12 用例 CI（加入真实 .NET Framework 项目）

| 轮次 | 用例数 | 通过 | 单例耗时 |
| --- | --- | --- | --- |
| 1 | 12 | 11/12 | 50–271s |

报告：`output/acceptance/coding-ci-20261115-194811/report.md`。唯一失败是 python-cli 一次真实 indent 实现错误（隐藏验收直接跑 CLI 抓到），单独重跑通过（`coding-python-cli-20261115-201316`）。`capacity-db` 首次即过（102s）。

- `capacity-db`：从真实 `AKRS.Capacity.DB` 裁剪 20 个 `.cs`，老式 .NET Framework 4.8 csproj + SQLite 引用；MSBuild 构建 0/0，隐藏验收编译独立检查程序直接调用 `NormalizeName`。
- repo_map 改为子进程执行：tree-sitter 在真实 DB 代码上发生 native 访问冲突（0xC0000005），此前会拖死服务并卡在 `connecting_model`；隔离后主服务返回“地图生成失败，已隔离”继续任务。

- `project-large-csharp`：Core + Api + CLI + **18 项自测 / 4 工程** 的 .NET 8 解决方案，隐藏验收直接跑 CLI 验证补货/低库存/总值/错误码；两轮 88s / 109s。
- 修复 **任务书二次编码乱码**：之前用 PowerShell 替换中文时把 UTF-8 写成二次编码，模型看到乱码后反复“修编码”；已重写为正确 UTF-8，并作为编码类问题的根因记录。
- 修复 **Windows 命令输出编码**：固定 UTF-8 解码改为失败回退 GB18030。

同时提供手动触发的 GitHub Actions 工作流 `.github/workflows/coding-acceptance.yml`（Windows runner，secret `ARKS_API_KEY`，上传报告 artifact）。

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
