# 任务：从零生成 WinForms 产能统计看板

工作区是空的，自动骨架已经准备好（WinForms，两页签、功能区、日志区）。

要求（在 `Actions.cs` 的 `OnReady()` 中实现，不要重写布局）：

1. 读取 `data/capacity.csv`（列：`date,count`，日期形如 `2026-01-01`）；
2. 统计 `2026-03-10` 所在周（周一至周日）的总产能，调用 `SetStatus($"WEEK {total}", UiTheme.Blue)`；
3. 统计 `2026-03` 自然月的总产能，调用 `WriteLog($"MONTH {total}", UiTheme.Grey)`；
4. 把主窗口标题改为 `产能统计`；
5. 保持骨架的两页签、功能区与日志区，支持 `--screenshot <png> <tab>`；
6. 写 README（构建/运行/验收命令）；不要留 TODO/占位。

完成前运行 `dotnet build`（0 错误 0 警告）与 `check_ui`。隐藏验收会启动应用截图，并从控件树核对 `WEEK <数字>`、`MONTH <数字>` 与标题。
