# 任务：为产能统计应用增加设置持久化

工作区已有通过逐页验收的 .NET 9 WinForms 应用（`CapacityStats/`）。

要求：

1. 支持命令行：
   - `CapacityStats.exe --set-setting <key> <value>`：把键值保存到应用目录下 `settings.json`，成功退出码 0；
   - `CapacityStats.exe --get-setting <key>`：读取并输出该键的值（仅值本身），不存在时退出码 2；
2. `settings.json` 为 UTF-8 JSON 对象，键值均为字符串；多次设置要合并而不是覆盖其他键；
3. 应用启动时读取 `settings.json`；`PAGE 设置` 页面显示已保存的键值（至少显示 `shift.day` 的值）；
4. 保留现有 7 个页面、`--screenshot`、`--export` 行为；
5. 构建 0 错误；README 补充用法；不要留 TODO/占位。

隐藏验收会执行 set/get、检查 `settings.json` 内容、重启后再次 get，并截图设置页。
