# 原始在线监控与报警未配置分支核验

隔离 CLR 4.0.30319.42000 宿主对原始 `Machine` 直接执行 17 项检查，两次独立运行均通过；16 个源/资源程序集均从冻结的 `encoding-preserving-resources/builds/bound` 路径加载且位置匹配。生产 C#、工程和运行时程序集未修改。

## 实际执行边界

宿主把 `MachineStateModel.MachineWorkMode` 设为原始 `NormalWork`（在线工作模式语义），把机器状态设为 `Stop`，保持 `HardwareRepositoryService.Hardwares` 为空。原始 `MachineHardwareConfiguration` 的安全门、激光干涉尺和输送加热配置均为 `false`；软件自动登出为 `false`，当前登录用户为空。

随后直接调用原始方法：

- `StartCheckSafeDoorTask` 在安全门未配置时返回，停止状态不变；配置打开但“门控”硬件缺失时，原始方法传播 `System.NullReferenceException`，且工作状态保持不变。
- `LaserEncoderCheck` 在激光未配置且无硬件时正常返回；即使配置打开但硬件仍缺失，原始 null 保护仍返回正常；两次 `StartLaserEncoderCheckTask` 都不触发原始 `Stop`。
- `AutoLogOut` 在自动登出关闭且无登录用户时不改变登录状态。
- `BackgroundTemperatureAlarm` 在输送加热未配置时返回，不执行报警 UI 或停止动作；配置打开但加热模块缺失时，原始方法传播 `System.NullReferenceException`，停止状态保持不变。

调用完成后硬件仓库仍为空，统计保存线程未创建，`DBService` 的 Lazy 未创建，SQL 写入、UI 调度、VM、生产任务和硬件动作均为零。`RuntimeProvider.ThreadFlag` 仍为 `true`。

## 证据限制

本轮验证的是在线模式下各监控方法的“未配置/无硬件”门控分支，不启动完整 `StartBackGroundThread` 循环，也不构造在线硬件、报警对话框、VM、数据库或设备连接。因此不能把它写成在线故障报警、真实硬件成功或完整监控周期已验收。已识别的环境传感器、算法状态、光强异常和通讯异常 UI 分支仍需匹配设备配置后单独验证。

测试输出见 [进度](native-online-monitor-boundary-progress.json)、[审计](native-online-monitor-boundary-audit.json)；独立核验命令为 `node .archify-work/verify-native-online-monitor-boundary.cjs`。


