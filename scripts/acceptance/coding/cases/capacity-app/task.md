# 任务：真实 WinForms 应用支持 --title-suffix

工作区是真实产能统计应用 `CapacityStatistics`（.NET Framework 4.8，WinForms，老式 csproj，MSBuild 构建）。

要求（不得破坏现有功能）：

1. `Program.Main` 解析命令行参数 `--title-suffix <text>`（未知参数忽略，允许与其他参数共存）；
2. 启动时，主窗口标题追加 ` - <text>`；**没有该参数时标题保持原样**；
3. 不改数据库/统计逻辑与配置文件；
4. README 说明新参数；不要留 TODO/占位；
5. 构建必须 0 错误 0 警告（`verify build` 会自动走 MSBuild）。

隐藏验收会启动 `CapacityStatistics.exe`：默认启动检查标题仍是“产能统计 …”，带 `--title-suffix TEST123` 启动检查标题包含 `TEST123`。
