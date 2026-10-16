# 原始 S2 清零 / Retry IL 边界

本轮对 `trunk/AKRS.ZX2200/bin/Debug/AKRS.ZX2200.exe` 做只读 Mono.Cecil 检查，程序集 SHA-256 为 `ea7c14767e29420d54f00c2070bb66f833980147156123a77a7925946b0f4ad8`。没有启动生产程序，也没有触发 UI、SDK、数据库、VM、Modbus、轴或设备。

| 原始类型/方法 | IL 指令数 | 关键边界 |
| --- | ---: | --- |
| `BondTask.DoWork` | 435 | 无本地异常处理器；调用 `BondHeadController.ResetBondhead()` 后紧接 `pop` 丢弃返回值，随后继续 `GetFirstComponent()`；`GetIncomingSignal()` 成功后依次执行 `PickUpCompensationVision`、`System2TemperatureCompensation`、`ScanReferencePoints`，每个失败都早退到返回点，再进入 `InjectSteps`、设置 `IsFirstDispense`，按 `Enable` 门检查载具产品标志和输送配置，必要时创建 System2 `TransportUnit`、设置 `IsProduct` 并标记 `IsNewProduct`；动作循环按 `WaitStart` → `GetNextActionNode`（空值退出）→ `ActionNode.IsDoWork` → `CloseDispenseCylinder` → `ActionNode.DoWork` → `FinishCurrentActionNode` → 再次 `WaitStart` 排序，动作节点的 `Abort`/`Exception`/报警终止路径调用 `Machine.Stop()` 和安全位移动，`Retry` 回到 `WaitStart` 循环，成功路径执行产品 `Finish`、补偿归一化、可选顶针耗时保存，再到 `SendAway()` 和 UI 刷新。 |
| `BondHeadController.ResetBondhead` | 102 | 包含一个 `Catch` 处理器，按 `ForceZeroMode` 选择 Modbus 或 IO（含 30ms 等待），失败时显示 Retry/Ignore/Abort 对话框；Retry 递归调用自身，Abort 调用 `Machine.Stop()`，默认返回 false。 |
| `ModbusService.ResetBondhead` | 34 | 包含一个 `Catch` 处理器，调用 `WriteMultipleRegisters(Int32, Int32[])` 和 `Thread.Sleep(Int32)`；当前 IL 快照显示寄存器 94 写入、异常捕获后等待 50 ms 再次写入。 |

校验入口为 `scripts/verify-original-s2-reset-il.cjs`，会校验程序集指纹、DoWork 无本地异常处理器、两个清零方法的 Catch 处理器、三个方法、清零返回值被丢弃的 `pop` 邻接关系、三项补偿门的顺序与失败早退、`InjectSteps`/`IsFirstDispense`/Enable/载具重建/`IsNewProduct` 顺序、WaitStart/空节点退出/动作循环回环、首组件查询、动作门/气缸关闭/节点执行顺序、四种动作结果标签、报警对话框、Retry 回跳、Abort/Exception/报警终止的 Stop 计数、产品完成、补偿归一化、顶针耗时保存、`SendAway` 后刷新，以及清零模式、IO 延迟、Retry/Ignore/Abort 标签和 Modbus/Stop 调用绑定。机器结果见 [original-s2-reset-il.json](original-s2-reset-il.json)。

这项证据仍不代表真实清零成功、Retry 全链、生产任务完成、UI 状态更新、Modbus/轴执行、数据库写入或现场设备验收。
