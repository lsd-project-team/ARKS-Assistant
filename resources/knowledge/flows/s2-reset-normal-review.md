# 原 S2 清零正常路径与返回值边界复核

复核日期：2026-10-06。状态：`source-confirmed-partial`。机器可复核证据见 [s2-reset-normal-audit.json](s2-reset-normal-audit.json)。本轮只读取源码，没有执行压力传感器、Modbus、IO、轴、UI、SQL 或设备动作。

`BondTask.DoWork()` 在 `BondTask.cs:114` 先调用 `bondHeadController.ResetBondhead()`，随后继续取得首个组件，再进入来料等待和动作流程。调用表达式没有接收或判断返回值，因此 `ResetBondhead()` 返回 false 时，源码没有在该调用点停止任务。这个顺序早于 `GetIncomingSignal()`，也早于可选换吸嘴分支。

`BondHeadController.ResetBondhead()` 根据 `ForceZeroMode` 选择 Modbus 或 IO。IO 分支依次置位焊头压力清零输出、等待 30 ms、复位输出；Modbus 分支调用 `ModbusService.ResetBondhead()`。异常统一进入报警对话框：Retry 递归重试，Ignore 返回 true，Abort 调用 `Machine.Stop()` 后返回 false，默认分支也返回 false。源码没有为 Retry 递归设置次数上限；递归调用的返回值也被丢弃，随后外层仍返回 true。

`ModbusService.ResetBondhead()` 向寄存器 94 写入清零值；第一次异常后等待 50 ms 再写一次，第二次异常会从辅助方法中逸出。既有 [S2 清零故障证据](native-s2-reset-propagation-review.md) 已在无硬件环境中覆盖 null 客户端、UI 分派故障、Task Faulted 和 Stop 退出，但没有证明真实 Modbus/IO 成功或完整生产循环。

结论是：清零正常返回路径已经明确到源码级，但当前调用方忽略 bool 返回、Retry 无界递归、Modbus 只重试一次，这些都需要在受控硬件/SDK环境中单独验收或修复评审。当前不能把已有故障路径记录升级为正常清零验收。

## 可点击证据

- [BondTask.cs:114](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L114)
- [BondHeadController.ForceRelated.cs:883](../../trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.ForceRelated.cs#L883)
- [ModbusService.cs:236](../../trunk/AKRS.ZX2200/BondSystem/BondForce/Modbus/ModbusService.cs#L236)
- [既有 S2 清零故障说明](native-s2-reset-propagation-review.md)
- [s2-reset-normal-audit.json](s2-reset-normal-audit.json)

