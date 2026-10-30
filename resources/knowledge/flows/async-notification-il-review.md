# 异步通知 Task.Run 的原始 IL 复核

使用 Mono.Cecil 只读检查当前保留的绑定 ZX2200 程序集：
`AKRS.ZX2200.exe` SHA-256 为 `99351b5fde6a8b400bcac8d5f71c5b39ac45ecc5c25facf5fc43e05ad96d5a9f`。

在 `PickActionNode`、`SubstrateCameraCorrectionActionNode`、`UpLookCorrectionActionNode` 三个原始动作节点类型中，共发现 24 个 `Task.Run` 调用点，其中 12 个紧随调用出现 `pop`，12 个紧随调用保存到局部变量。`DoWork` 与两个 DryRun 方法中承载通知的调用点均为 `pop`：Pick 的 3 个 `DoWork` 调用、Substrate 的 1 个 `DoWork` 调用、UpLook 的 2 个 `DoWork` 调用，以及相应 DryRun 分支均未把任务交给后续等待链。

这与当前源码的 8 个通知 Task 块核对相互印证：源码没有在启动处保存返回 Task，绑定 IL 也显示对应调用结果被立即丢弃。IL 只证明程序集中的调用结果处理方式；它不证明委托一定执行、一定抛异常或一定造成芯片/信号交错，也不替代运行时任务、Stop、UI、外部 DLL 和设备验收。

机器结果见 [async-notification-il-audit.json](async-notification-il-audit.json)，可复现命令为 `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/inspect-async-notification-il.ps1`。

