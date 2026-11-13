# SP900 一次性生成验收基准

目标：在**空白目录**里，一次 Agent 运行产出完整 SP900 点胶上位机，并用独立评分验证。

## 目录

| 路径 | 作用 |
| --- | --- |
| `task/开发任务书.md` | 输入需求（复制到被测项目根目录） |
| `reference/good-main.png` 等 | 参考界面（来自已验收的 v1.3 版本） |
| `reference/failure-1552.png` | 反例：空页签 + 浮动滚动框，绝不能出现 |
| `run.py` | 启动隔离服务、建空项目、跑一次真实生成 |
| `grade.py` | 独立评分：构建、回放自测、界面截图与结构断言、代码规范 |

## 使用

```powershell
backend\.venv\Scripts\python.exe scripts\acceptance\sp900\run.py
```

可选：`--port 8790`、`--timeout 1800`、`--keep`、`--no-grade`。

每次运行生成 `output/acceptance/sp900-<时间>/`：

- `project/`：空目录 + 任务书 + `input/` 参考图
- `answer.md`：Agent 最终回答
- `grade.json` / `grade.md`：独立评分结果
- `server.log`：服务日志

## 评分口径

硬性项全部通过才算 PASS：

1. `dotnet build` 0 错误（同时记录警告数）
2. `tests/` 下的回放自测工程全部通过，且通过数 ≥ 8
3. 两张页面截图生成、非空白；标签页高 ≥300、功能区大按钮 ≥6、输入控件 ≥6、日志区 ≥150、无 0 尺寸控件
4. 代码规范：显式 `<Compile>`、`Nullable`、README、无 TODO/占位/未实现

参考图只用于人工/模型视觉核对，不做像素级门槛；结构断言见 `app/modules/coding/ui_checks.py`。
