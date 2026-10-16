# 异步通知 Task 生命周期源码核对

记录时间：2026-10-07T08:34:45.216Z。从当前源码提取 8 个通知 Task.Run 块，全部来自上一轮写入面审计登记的晶圆/翻转台路径。

| 入口 | 文件 | Task.Run 行段 | sink | 启动时保存返回值 | 后续近邻观察 |
| --- | --- | ---: | --- | --- | --- |
| pick-action-wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs` | 479–488 | SendSignalToWaferTable | 否 | 无 |
| pick-action-flip | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs` | 492–498 | SendSignalToFlipTable | 否 | 无 |
| pick-move-wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.MoveHelper.cs` | 870–890 | IsBondNeedChipSignal.Set | 否 | 无 |
| pick-move-flip | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.MoveHelper.cs` | 894–954 | IsBondPickSucceedSignal.Set | 否 | 无 |
| substrate-correction-wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.cs` | 490–496 | SendSignalToWaferTable | 否 | 无 |
| substrate-move-wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.MoveHelper.cs` | 949–955 | SendSignalToWaferTable | 否 | 无 |
| uplook-wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs` | 454–482 | IsBondNeedChipSignal.Set | 否 | 无 |
| uplook-repeat-wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs` | 2011–2039 | IsBondNeedChipSignal.Set | 否 | 无 |

结果：8/8 个块在启动处没有保存返回 Task；近邻 20 行未发现可归属于该块的 await/Wait 观察：8 个。

这些是当前源码的词法事实，不能替代运行时任务生命周期、异常监督、停止回收或设备行为验证。源码块锚点和哈希见 [机器审计](async-notification-task-lifecycle-audit.json)。
