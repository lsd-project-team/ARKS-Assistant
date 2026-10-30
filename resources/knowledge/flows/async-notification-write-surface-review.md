# 动作节点异步通知写入面审计

记录时间：2026-10-07T08:26:59.571Z。扫描 37 个 ActionNodes C# 文件，登记 54 个匹配点。

本审计覆盖晶圆要料、翻转台取料成功、刮胶盘完成/允许伸出，以及对应 helper 和名称写入。`nearbyAsyncLaunch` 只表示同一文件中前 80 行内出现 Task.Run/Task.Factory.StartNew，不把词法邻近误读为委托闭包或任务已被等待。

| 家族 | 文件 | 行 | 写入面 | 附近异步启动 |
| --- | --- | ---: | --- | --- |
| slide-fluxer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.Provider.cs` | 675 | slide-allow | none |
| slide-fluxer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.Provider.cs` | 680 | slide-finish | none |
| slide-fluxer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.Provider.cs` | 683 | slide-allow | none |
| slide-fluxer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/DipFluxActionNode.cs` | 273 | slide-finish | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.MoveHelper.cs` | 885 | wafer-name | line 870 |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.MoveHelper.cs` | 888 | wafer-signal | line 870 |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs` | 72 | wafer-name | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs` | 75 | wafer-signal | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs` | 98 | wafer-name | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs` | 101 | wafer-signal | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs` | 252 | wafer-name | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs` | 255 | wafer-signal | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs` | 287 | wafer-name | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs` | 290 | wafer-signal | none |
| flip | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs` | 571 | flip-helper | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs` | 633 | wafer-helper | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs` | 643 | wafer-name | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs` | 646 | wafer-signal | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs` | 661 | wafer-name | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs` | 664 | wafer-signal | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs` | 426 | wafer-name | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs` | 429 | wafer-signal | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs` | 442 | wafer-name | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs` | 445 | wafer-signal | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs` | 486 | wafer-helper | line 479 |
| flip | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs` | 497 | flip-helper | line 492 |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.MoveHelper.cs` | 954 | wafer-helper | line 949 |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.Provider.cs` | 52 | wafer-helper | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.Provider.cs` | 62 | wafer-name | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.Provider.cs` | 65 | wafer-signal | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.cs` | 467 | wafer-name | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.cs` | 470 | wafer-signal | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.cs` | 495 | wafer-helper | line 490 |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.cs` | 658 | wafer-name | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.cs` | 661 | wafer-signal | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs` | 469 | wafer-name | line 454 |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs` | 472 | wafer-signal | line 454 |
| slide-fluxer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs` | 717 | slide-finish | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs` | 1436 | wafer-name | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs` | 1439 | wafer-signal | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs` | 1522 | wafer-name | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs` | 1525 | wafer-signal | none |
| slide-fluxer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs` | 1550 | slide-finish | none |
| slide-fluxer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs` | 1555 | slide-finish | none |
| slide-fluxer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs` | 1558 | slide-allow | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs` | 1678 | wafer-name | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs` | 1681 | wafer-signal | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs` | 1764 | wafer-name | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs` | 1767 | wafer-signal | none |
| slide-fluxer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs` | 1792 | slide-finish | none |
| slide-fluxer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs` | 1797 | slide-finish | none |
| slide-fluxer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs` | 1800 | slide-allow | none |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs` | 2026 | wafer-name | line 2011 |
| wafer | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs` | 2029 | wafer-signal | line 2011 |

家族计数：{"slide-fluxer":11,"wafer":41,"flip":2}。完整机器结果见 [async-notification-write-surface-audit.json](async-notification-write-surface-audit.json)。

这一步闭合了源码写入点盘点，但没有闭合运行时交错、任务异常监督、停止回收、真实配方或设备验收。下一步需要对这些写入点逐个确认调用者是否保存/等待 Task，并在受控无设备夹具中记录创建、执行和完成顺序。
