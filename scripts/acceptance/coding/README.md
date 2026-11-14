# 编码模块多案例验收

在隔离数据目录中跑真实 Agent 编码任务，并用独立脚本复核；用于持续测试编码模块、发现回归。

## 用例

| 用例 | 类型 | 验收 |
| --- | --- | --- |
| `python-cli` | 从零生成（Python CLI + pytest） | compileall 通过、pytest 通过 ≥5、文件齐全、无 TODO |
| `dotnet-console` | 从零生成（.NET 8 控制台 + 自测工程） | build 0/0、自测 PASS ≥6、文件齐全、无 TODO |
| `bugfix-python` | 现有项目修复 | pytest 通过、测试文件未被修改、无 TODO |
| `bugfix-multi` | 跨文件 bug 修复（shop 包） | pytest 通过、测试文件未被修改、README、无 TODO |
| `refactor-python` | 现有项目重构 | pytest 通过、测试文件未被修改、README 更新、无 TODO |
| `web-static` | 从零生成原生 JS 单页应用 | `node --check` 通过、`node --test` ≥6、界面三文件齐全、无 TODO |

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

## 判定

只有 `run` 状态为 `completed` 且 `grade.json` 全绿才算通过。评分分两层：

- **独立验收（acceptance，必需）**：`cases/*/acceptance/` 下的脚本直接跑 CLI/纯函数/可执行文件，不依赖 Agent 自写的测试；bugfix/refactor 用受保护的种子测试。
- **Agent 自测（selftest，告警）**：仍会执行并记录，但不再决定整体通过与否，避免自测断言写错误伤正确实现。
