# 原 S2 翻转台与刮胶盘任务启动边界复核

复核日期：2026-10-06。状态：`source-confirmed-partial`。机器可复核证据见 [s2-flip-slide-start-audit.json](s2-flip-slide-start-audit.json)。本轮只读取源码，没有启动任务、调用轴/传感器/真空、等待生产信号或执行设备动作。

`SlideFluxerTask.Start()`（`SlideFluxerTask.cs:227`）先检查 `IsSlideFluxerConfigured`；未配置时直接抛出异常。通过后仅在 `SlideFluxTask` 为空或状态不是 Running 时创建 LongRunning Task，并返回 true。其工作体先回刮胶盘零位，再等待 `IsNeedDip`；等待焊头离开区域时会处理 Pause，超过 15 秒进入 Ignore/Abort 对话框，然后发出允许蘸胶信号，等待蘸胶完成和刮胶盘伸出许可，最后回零。异常和信号退出会改变任务生命周期，但没有本地顶层 catch。

`FlipTask.Start()`（`FlipTask.cs:260`）没有自己的 `IsFlipModuleConfigrated` 检查；它在创建 Task 前直接把机器状态设为 Working。完整 `Machine.Start()` 只在 `IsFlipModuleConfigrated` 为 true 时调用它，因此直接调用与整机入口的门控强度不同。翻转任务先回零，取当前组件；组件为空时循环等待。启用翻转台后依次等待晶圆允许取料、启动一个未保存句柄的 `Task.Run` 通知晶圆线程、执行 `FlipChipAction`/`FlipChipActionDryRun`，按 Success/Exception/Abort/NoStart 分支更新翻转台状态或退出，再发出允许 Bond 取料信号并等待 Bond 成功。

结论是：两类任务的启动条件、Running 防重复、机器状态写入、信号等待和硬件动作顺序已固定；翻转台的配置门只在 `Machine.Start()` 外层存在，直接入口可绕过该门；通知晶圆的后台 `Task.Run` 没有保存为可关闭句柄。当前没有执行完整 S2 任务或设备动作，不能把源码顺序升级为翻转/刮胶成功验收。

## 可点击证据

- [SlideFluxerTask.cs:227](../../trunk/AKRS.ZX2200/BondSystem/Tasks/SlideFluxerTask.cs#L227)
- [FlipTask.cs:260](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/FlipTask.cs#L260)
- [Machine.Operate.cs](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs)
- [native-s2-task-entry-audit.json](native-s2-task-entry-audit.json)
- [s2-flip-slide-start-audit.json](s2-flip-slide-start-audit.json)
