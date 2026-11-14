# 编码模块多案例验收

在隔离数据目录中跑真实 Agent 编码任务，并用独立脚本复核；用于持续测试编码模块、发现回归。

## 用例

| 用例 | 类型 | 验收 |
| --- | --- | --- |
| `python-cli` | 从零生成（Python CLI + pytest） | compileall 通过、pytest 通过 ≥5、文件齐全、无 TODO |
| `dotnet-console` | 从零生成（.NET 8 控制台 + 自测工程） | build 0/0、自测 PASS ≥6、文件齐全、无 TODO |
| `bugfix-python` | 现有项目修复 | pytest 通过、测试文件未被修改、无 TODO |
| `bugfix-multi` | 跨文件 bug 修复（shop 包） | pytest 通过、测试文件未被修改、README、无 TODO |
| `feature-python` | 现有待办服务增加截止日期/逾期 | 现有测试通过、隐藏验收验证 due/overdue、测试文件未被修改 |
| `project-large` | 图书馆服务（5 模块 + 15 测试）加搜索分页/热门榜 | 现有 15 测试通过、隐藏验收验证分页/热门榜、测试文件未被修改 |
| `refactor-python` | 现有项目重构 | pytest 通过、测试文件未被修改、README 更新、无 TODO |
| `web-static` | 从零生成原生 JS 单页应用 | `node --check` 通过、`node --test` ≥6、界面三文件齐全、无 TODO |
| `winforms-tool` | 从零生成 WinForms 点检计时器 | build 0/0、两页截图非空白、布局断言、无 TODO |

## 运行

```powershell
backend\.venv\Scripts\python.exe scripts\acceptance\coding\run.py --case bugfix-python
backend\.venv\Scripts\python.exe scripts\acceptance\coding\batch.py
```

每次运行写入 `output/acceptance/coding-<case>-<时间>/`：`project/`、`answer.md`、`grade.json`、`grade.md`、`server.log`。

## CI 入口

```powershell
# 全部用例跑 1 轮
backend\.venv\Scripts\python.exe scripts\acceptance\coding\ci.py --rounds 1
# 指定用例跑 2 轮
backend\.venv\Scripts\python.exe scripts\acceptance\coding\ci.py --cases python-cli,web-static --rounds 2
```

输出 `output/acceptance/coding-ci-<时间>/report.md` 与 `report.json`；任一轮/用例失败则退出码非 0，适合接 CI。

## GitHub Actions

`.github/workflows/coding-acceptance.yml` 提供手动触发（workflow_dispatch）：

- 需要仓库 secret `ARKS_API_KEY`；可选 variables `ARKS_BASE_URL`、`ARKS_MODEL`。
- 自动安装 Python/Node/.NET，写入 `data/settings.private.json`，运行 `ci.py` 并上传报告 artifact。
- 默认 8 个用例 1 轮；可在触发时指定 cases/rounds。

## 判定

只有 `run` 状态为 `completed` 且 `grade.json` 全绿才算通过。评分分两层：

- **独立验收（acceptance，必需）**：`cases/*/acceptance/` 下的脚本直接跑 CLI/纯函数/可执行文件，不依赖 Agent 自写的测试；bugfix/refactor 用受保护的种子测试。
- **Agent 自测（selftest，告警）**：仍会执行并记录，但不再决定整体通过与否，避免自测断言写错误伤正确实现。
