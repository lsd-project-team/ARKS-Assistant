# 编码模块多案例验收

在隔离数据目录中跑真实 Agent 编码任务，并用独立脚本复核；用于持续测试编码模块、发现回归。

## 用例

| 用例 | 类型 | 验收 |
| --- | --- | --- |
| `python-cli` | 从零生成（Python CLI + pytest） | compileall 通过、pytest 通过 ≥5、文件齐全、无 TODO |
| `dotnet-console` | 从零生成（.NET 8 控制台 + 自测工程） | build 0/0、自测 PASS ≥6、文件齐全、无 TODO |
| `bugfix-python` | 现有项目修复 | pytest 通过、测试文件未被修改、无 TODO |

## 运行

```powershell
backend\.venv\Scripts\python.exe scripts\acceptance\coding\run.py --case bugfix-python
backend\.venv\Scripts\python.exe scripts\acceptance\coding\batch.py
```

每次运行写入 `output/acceptance/coding-<case>-<时间>/`：`project/`、`answer.md`、`grade.json`、`grade.md`、`server.log`。

## 判定

只有 `run` 状态为 `completed` 且 `grade.json` 全绿才算通过；失败会保留现场，便于定位是 Agent 行为、提示词、工具还是评分问题。
