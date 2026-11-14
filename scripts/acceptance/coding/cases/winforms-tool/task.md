# 任务：WinForms 设备点检计时器

在工作区从零实现一个 Windows 桌面点检计时器（生成模式会自动准备 WinForms 骨架）：

1. 界面保持骨架的两页签（参数设置 / 设备功能），保留参数控件与通信日志区。
2. 参数页：点检间隔（秒）、单次时长（秒）、重复次数、机种名、模式（手动/自动）。
3. 功能区按钮：开始、暂停、复位、记录一次、导出记录、帮助；点击后更新状态与日志。
4. 计时逻辑写在 `Actions.cs`，不要重写 `MainForm.cs/UiParts.cs/Program.cs/ScreenshotTool.cs`（受保护）。
   骨架已有 6 个动作按钮，键为 `connect/test/read/set/play/info`；按这个映射绑定计时器行为
   （连接=开始、测试=暂停、读取=复位、设置=记录、执行=导出、信息=帮助），不要再读 MainForm 找布局。
   参数用骨架字段 `Channel/Mode/Pressure/Time/Vacuum/ModelName`，状态用 `SetStatus`、日志用 `WriteLog`。
5. 运行 `dotnet build` 0 错误 0 警告；用 `dotnet run --project App.csproj -- --screenshot shots/ui_tab0.png 0` 生成截图自检，再生成 tab1。
6. 写 README（操作说明与验收命令）；不要留 TODO/占位。

完成前必须调用 `verify build` 与 `check_ui`，界面截图非空白、两页签结构完整。
