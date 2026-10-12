# 原始在线监控安全门故障传播核验

隔离 CLR 4.0.30319.42000 子进程执行原始 `Machine.StartBackGroundThread`。机器设为 `NormalWork`/`Working`，安全门配置打开，但硬件仓库保持为空，因此没有门控 `Sensor`。子进程预期失败并实际以非零码 `3221225477` 结束；原始 `AppDomain.UnhandledException` 回调记录到终止事件。

记录内容确认：

- 异常类型为 `System.NullReferenceException`。
- 异常栈包含原始 `StartCheckSafeDoorTask`。
- `UnhandledExceptionEventArgs.IsTerminating=true`，说明后台监控线程异常没有被外层监控循环捕获。
- 事件中记录到 16 个 bound 源/资源程序集，路径与冻结运行时映射一致。
- 未执行 SQL、硬件动作、UI 报警或生产任务。

标准错误只显示 CLR 的“由于 Exception.ToString() 失败，因此无法打印异常字符串”提示；完整异常类型、消息和终止标志以事件文件为准。该子进程的非零退出是预期故障证据，不是成功运行。

这项证据只覆盖安全门已配置但传感器缺失的原始故障传播，不代表真实门控报警对话框、硬件安全门或设备运行安全已验收。测试输出见 [进度](native-online-monitor-fault-progress.json)、[审计](native-online-monitor-fault-audit.json)；独立核验命令为 `node .archify-work/verify-native-online-monitor-fault.cjs`。
