# ZX2200 自动化信号矩阵

声明来自 `trunk/AKRS.Galaxy2.Machine/Models/SignalPool.cs`。下列引用自动扫描 `trunk/AKRS.ZX2200` 的非 Designer C# 文件，去除行注释和块注释；包含生产、手动和调试调用，实际适用范围以文件及条件为准。这是源码引用清单，不是运行时调用次数。

`AutoReset` 是事件声明模式；S1 来料的公开 State 轮询例外需单独理解。`ManualReset` 必须显式复位。公共等待的 Stop/Pause 和超时参数边界见 `Signal.cs:119–170,208–243`。没有发现通用、持久化、断点续跑的消息队列。

| 信号 | 事件模式 | 已确认语义 |
|---|---|---|
| `System2SingleStepSignal` | AutoReset | UI 按钮/快捷键放行；System2Domain 和晶圆域在单步边界等待。 |
| `System1SingleStepSignal` | AutoReset | UI 按钮/快捷键放行；System1Domain 在单步边界等待。 |
| `AllowLoaderMoveSignal` | AutoReset | 输送完成推料后允许上料仓移层。 |
| `LoaderAllowPushSignal` | ManualReset | 上料仓就绪后置位；输送推料后显式复位。 |
| `AllowDispense1TransferToDispense2Signal` | AutoReset | S1 InteractiveAction 请求移至第二点胶段。 |
| `AllowDispenseTransferToBondSignal` | AutoReset | S1 完成放行；无 S1 的特定皮带分支也会发送。 |
| `AllowBondTransferToWaitingUnloadSignal` | AutoReset | S2 完成后允许输送到等待下料区。 |
| `AllowWaitingUnloadTransferToOutloadSignal` | AutoReset | 此应用源码仅见复位，未找到活动的 Set/Wait；不能依据名字画出握手。 |
| `TransferToDispense1FinishedSignal` | AutoReset | S1 来料完成；DispenseWorkTask 轮询公开 State 并赋 ReSet，不调用 Wait。 |
| `TransferToDispense2FinishedSignal` | AutoReset | 分段传输完成，InteractiveAction 等待；该调用未检查 Wait 返回值。 |
| `TransferToBondFinishedSignal` | AutoReset | 输送到 S2 完成，BondTask 等待。 |
| `AllowUnloaderMoveSignal` | AutoReset | 输送交接后允许下料仓移动。 |
| `UnloaderAllowPushSignal` | ManualReset | 下料仓准备好后置位；输送使用后显式复位。 |
| `IsBondPickSucceedSignal` | AutoReset | S2 离开翻转区域后通知 FlipTask；不是所有路径共用的产品合格事件。 |
| `IsWaferAllowPickSignal` | AutoReset | 晶圆找到芯片后发送；由 S2 或 FlipTask 按模式消费。 |
| `IsBondNeedChipSignal` | ManualReset | S2 发芯片需求，晶圆处理后清需求并发允许取晶；Stop 也复位。 |
| `IsBondNeedEjectionSignal` | AutoReset | 未找到此应用中的活动引用；不据此推断独立顶针线程。 |
| `IsEjectionComplete` | AutoReset | 未找到此应用中的活动引用。 |
| `IsLoadWaferMap` | AutoReset | 此应用中相关调用被注释；不纳入活动流程。 |
| `IsFlipTableAllowPickSignal` | AutoReset | FlipTask 完成翻转后允许 S2 取晶。 |
| `IsAllowDipFluxSignal` | AutoReset | SlideFluxerTask 胶盘就绪；DipFluxActionNode 等待。 |
| `BondDipFluxFinishSignal` | AutoReset | Bond/UpLook 的配置分支通知胶盘；不能把注释掉的 DipFlux Set 当作活动调用。 |
| `AllowSlideOutSignal` | AutoReset | Bond/UpLook 的配置分支允许胶盘伸出，SlideFluxerTask 等待。 |

## 逐信号源码引用

每项列出调用操作、文件行号及原始代码。公共初始化复位同样保留，避免误认为没有复位。完整机器可读数据见 [signal-inventory.json](signal-inventory.json)。

### System2SingleStepSignal

声明：`SignalPool.cs:60`；UI 按钮/快捷键放行；System2Domain 和晶圆域在单步边界等待。

- **WaitSingleStep** — [System2Domain.cs:781](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs:781)：`if (!SignalPool.GetInstance().System2SingleStepSignal.WaitSingleStep())`
- **Set** — [UcMainSystem.cs:992](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs:992)：`SignalPool.GetInstance().System2SingleStepSignal.Set();`
- **Set** — [UcMainSystem.cs:1010](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs:1010)：`SignalPool.GetInstance().System2SingleStepSignal.Set();`
- **Set** — [UcMainSystem.HotKeyManage.cs:109](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.HotKeyManage.cs:109)：`SignalPool.GetInstance().System2SingleStepSignal.Set();`
- **Set** — [UcMainSystem.ShortcutKeys.cs:54](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.ShortcutKeys.cs:54)：`SignalPool.GetInstance().System2SingleStepSignal.Set();`
- **WaitSingleStep** — [WaferSystemDomain.cs:145](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/WaferSubSystem/Models/WaferSystemDomain.cs:145)：`if (!SignalPool.GetInstance().System2SingleStepSignal.WaitSingleStep())`

### System1SingleStepSignal

声明：`SignalPool.cs:65`；UI 按钮/快捷键放行；System1Domain 在单步边界等待。

- **WaitSingleStep** — [System1Domain.cs:538](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/DispenseSystem/Models/System1Domain.cs:538)：`if (!SignalPool.GetInstance().System1SingleStepSignal.WaitSingleStep())`
- **Set** — [UcMainSystem.cs:1015](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs:1015)：`SignalPool.GetInstance().System1SingleStepSignal.Set();`
- **Set** — [UcMainSystem.ShortcutKeys.cs:59](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.ShortcutKeys.cs:59)：`SignalPool.GetInstance().System1SingleStepSignal.Set();`

### AllowLoaderMoveSignal

声明：`SignalPool.cs:74`；输送完成推料后允许上料仓移层。

- **ReSet** — [Machine.Operate.cs:150](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:150)：`SignalPool.GetInstance().AllowLoaderMoveSignal.ReSet();`
- **Wait** — [LoaderTask.cs:99](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/LoaderTask.cs:99)：`if (!SignalPool.GetInstance().AllowLoaderMoveSignal.Wait())`
- **Set** — [TransportTask.cs:415](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:415)：`SignalPool.GetInstance().AllowLoaderMoveSignal.Set();`

### LoaderAllowPushSignal

声明：`SignalPool.cs:79`；上料仓就绪后置位；输送推料后显式复位。

- **ReSet** — [Machine.Operate.cs:151](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:151)：`SignalPool.GetInstance().LoaderAllowPushSignal.ReSet();`
- **Set** — [LoaderTask.cs:93](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/LoaderTask.cs:93)：`SignalPool.GetInstance().LoaderAllowPushSignal.Set();`
- **Set** — [LoaderTask.cs:119](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/LoaderTask.cs:119)：`SignalPool.GetInstance().LoaderAllowPushSignal.Set();`
- **Wait** — [TransportTask.cs:375](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:375)：`if (!SignalPool.GetInstance().LoaderAllowPushSignal.Wait())`
- **ReSet** — [TransportTask.cs:412](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:412)：`SignalPool.GetInstance().LoaderAllowPushSignal.ReSet();`

### AllowDispense1TransferToDispense2Signal

声明：`SignalPool.cs:84`；S1 InteractiveAction 请求移至第二点胶段。

- **Set** — [InteractiveAction.cs:53](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/OtherAction/InteractiveAction.cs:53)：`SignalPool.GetInstance().AllowDispense1TransferToDispense2Signal.Set();`
- **ReSet** — [Machine.Operate.cs:140](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:140)：`SignalPool.GetInstance().AllowDispense1TransferToDispense2Signal.ReSet();`
- **Wait** — [TransportController.cs:1200](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs:1200)：`bool rt = SignalPool.GetInstance().AllowDispense1TransferToDispense2Signal.Wait();`

### AllowDispenseTransferToBondSignal

声明：`SignalPool.cs:89`；S1 完成放行；无 S1 的特定皮带分支也会发送。

- **Set** — [DispenseWorkTask.cs:175](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs:175)：`SignalPool.GetInstance().AllowDispenseTransferToBondSignal.Set();`
- **ReSet** — [Machine.Operate.cs:141](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:141)：`SignalPool.GetInstance().AllowDispenseTransferToBondSignal.ReSet();`
- **Wait** — [TransportController.cs:1286](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs:1286)：`bool rt = SignalPool.GetInstance().AllowDispenseTransferToBondSignal.Wait();`
- **Set** — [TransportTask.cs:295](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:295)：`SignalPool.GetInstance().AllowDispenseTransferToBondSignal.Set();`
- **Wait** — [TransportTask.cs:818](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:818)：`bool rt = SignalPool.GetInstance().AllowDispenseTransferToBondSignal.Wait();`

### AllowBondTransferToWaitingUnloadSignal

声明：`SignalPool.cs:94`；S2 完成后允许输送到等待下料区。

- **Set** — [BondTask.cs:453](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs:453)：`SignalPool.GetInstance().AllowBondTransferToWaitingUnloadSignal.Set();`
- **ReSet** — [Machine.Operate.cs:142](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:142)：`SignalPool.GetInstance().AllowBondTransferToWaitingUnloadSignal.ReSet();`
- **Wait** — [TransportController.cs:1557](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs:1557)：`bool rt = SignalPool.GetInstance().AllowBondTransferToWaitingUnloadSignal.Wait();`
- **Wait** — [TransportTask.cs:863](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:863)：`bool rt = SignalPool.GetInstance().AllowBondTransferToWaitingUnloadSignal.Wait();`

### AllowWaitingUnloadTransferToOutloadSignal

声明：`SignalPool.cs:99`；此应用源码仅见复位，未找到活动的 Set/Wait；不能依据名字画出握手。

- **ReSet** — [Machine.Operate.cs:143](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:143)：`SignalPool.GetInstance().AllowWaitingUnloadTransferToOutloadSignal.ReSet();`

### TransferToDispense1FinishedSignal

声明：`SignalPool.cs:104`；S1 来料完成；DispenseWorkTask 轮询公开 State 并赋 ReSet，不调用 Wait。

- **State / 属性** — [DispenseWorkTask.cs:249](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs:249)：`else if (SignalPool.GetInstance().TransferToDispense1FinishedSignal.State == SignalStateEnum.Set)`
- **State / 属性** — [DispenseWorkTask.cs:251](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs:251)：`SignalPool.GetInstance().TransferToDispense1FinishedSignal.State = SignalStateEnum.ReSet;`
- **State / 属性** — [DispenseWorkTask.cs:254](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs:254)：`else if (SignalPool.GetInstance().TransferToDispense1FinishedSignal.State == SignalStateEnum.ReSet)`
- **ReSet** — [Machine.Operate.cs:144](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:144)：`SignalPool.GetInstance().TransferToDispense1FinishedSignal.ReSet();`
- **Set** — [TransportTask.cs:198](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:198)：`SignalPool.GetInstance().TransferToDispense1FinishedSignal.Set();`
- **Set** — [TransportTask.cs:230](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:230)：`SignalPool.GetInstance().TransferToDispense1FinishedSignal.Set();`
- **Set** — [TransportTask.cs:253](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:253)：`SignalPool.GetInstance().TransferToDispense1FinishedSignal.Set();`
- **Set** — [TransportTask.cs:286](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:286)：`SignalPool.GetInstance().TransferToDispense1FinishedSignal.Set();`
- **Set** — [TransportTask.cs:333](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:333)：`SignalPool.GetInstance().TransferToDispense1FinishedSignal.Set();`
- **Set** — [TransportTask.cs:355](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:355)：`SignalPool.GetInstance().TransferToDispense1FinishedSignal.Set();`
- **Set** — [TransportTask.cs:396](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:396)：`SignalPool.GetInstance().TransferToDispense1FinishedSignal.Set();`
- **Set** — [TransportTask.cs:784](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:784)：`SignalPool.GetInstance().TransferToDispense1FinishedSignal.Set();`
- **Set** — [TransportTask.cs:830](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:830)：`SignalPool.GetInstance().TransferToDispense1FinishedSignal.Set();`

### TransferToDispense2FinishedSignal

声明：`SignalPool.cs:109`；分段传输完成，InteractiveAction 等待；该调用未检查 Wait 返回值。

- **Wait** — [InteractiveAction.cs:56](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/OtherAction/InteractiveAction.cs:56)：`SignalPool.GetInstance().TransferToDispense2FinishedSignal.Wait();`
- **ReSet** — [Machine.Operate.cs:145](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:145)：`SignalPool.GetInstance().TransferToDispense2FinishedSignal.ReSet();`
- **Set** — [TransportTask.cs:456](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:456)：`SignalPool.GetInstance().TransferToDispense2FinishedSignal.Set();`

### TransferToBondFinishedSignal

声明：`SignalPool.cs:114`；输送到 S2 完成，BondTask 等待。

- **Wait** — [BondTask.cs:400](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs:400)：`return SignalPool.GetInstance().TransferToBondFinishedSignal.Wait();`
- **ReSet** — [Machine.Operate.cs:146](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:146)：`SignalPool.GetInstance().TransferToBondFinishedSignal.ReSet();`
- **ReSet** — [Machine.Operate.cs:157](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:157)：`SignalPool.GetInstance().TransferToBondFinishedSignal.ReSet();`
- **Set** — [TransportTask.cs:489](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:489)：`SignalPool.GetInstance().TransferToBondFinishedSignal.Set();`
- **Set** — [TransportTask.cs:512](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:512)：`SignalPool.GetInstance().TransferToBondFinishedSignal.Set();`
- **Set** — [TransportTask.cs:540](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:540)：`SignalPool.GetInstance().TransferToBondFinishedSignal.Set();`
- **Set** — [TransportTask.cs:794](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:794)：`SignalPool.GetInstance().TransferToBondFinishedSignal.Set();`
- **Set** — [TransportTask.cs:875](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:875)：`SignalPool.GetInstance().TransferToBondFinishedSignal.Set();`

### AllowUnloaderMoveSignal

声明：`SignalPool.cs:119`；输送交接后允许下料仓移动。

- **ReSet** — [Machine.Operate.cs:149](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:149)：`SignalPool.GetInstance().AllowUnloaderMoveSignal.ReSet();`
- **Set** — [TransportTask.cs:709](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:709)：`SignalPool.GetInstance().AllowUnloaderMoveSignal.Set();`
- **Wait** — [UnloaderTask.cs:97](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/UnloaderTask.cs:97)：`if (!SignalPool.GetInstance().AllowUnloaderMoveSignal.Wait())`

### UnloaderAllowPushSignal

声明：`SignalPool.cs:124`；下料仓准备好后置位；输送使用后显式复位。

- **ReSet** — [Machine.Operate.cs:152](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:152)：`SignalPool.GetInstance().UnloaderAllowPushSignal.ReSet();`
- **Wait** — [TransportTask.cs:677](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:677)：`if (!SignalPool.GetInstance().UnloaderAllowPushSignal.Wait())`
- **ReSet** — [TransportTask.cs:706](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:706)：`SignalPool.GetInstance().UnloaderAllowPushSignal.ReSet();`
- **Set** — [UnloaderTask.cs:92](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/UnloaderTask.cs:92)：`SignalPool.GetInstance().UnloaderAllowPushSignal.Set();`
- **Set** — [UnloaderTask.cs:117](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/TransportSystem/Tasks/UnloaderTask.cs:117)：`SignalPool.GetInstance().UnloaderAllowPushSignal.Set();`

### IsBondPickSucceedSignal

声明：`SignalPool.cs:136`；S2 离开翻转区域后通知 FlipTask；不是所有路径共用的产品合格事件。

- **Set** — [PickActionNode.cs:434](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs:434)：`SignalPool.GetInstance().IsBondPickSucceedSignal.Set();`
- **Set** — [PickActionNode.MoveHelper.cs:950](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.MoveHelper.cs:950)：`SignalPool.GetInstance().IsBondPickSucceedSignal.Set();`
- **Set** — [PickActionNode.Provider.cs:624](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs:624)：`SignalPool.GetInstance().IsBondPickSucceedSignal.Set();`
- **ReSet** — [Machine.Operate.cs:158](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:158)：`SignalPool.GetInstance().IsBondPickSucceedSignal.ReSet();`
- **Wait** — [FlipTask.cs:239](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/WaferSubSystem/Tasks/FlipTask.cs:239)：`if (!SignalPool.GetInstance().IsBondPickSucceedSignal.Wait())`

### IsWaferAllowPickSignal

声明：`SignalPool.cs:142`；晶圆找到芯片后发送；由 S2 或 FlipTask 按模式消费。

- **Wait** — [System2Controller.Assistant.cs:123](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.Assistant.cs:123)：`if (!SignalPool.GetInstance().IsWaferAllowPickSignal.Wait())`
- **Wait** — [System2Controller.Assistant.cs:389](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.Assistant.cs:389)：`if (!SignalPool.GetInstance().IsWaferAllowPickSignal.Wait())`
- **Wait** — [System2Controller.Assistant.cs:451](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.Assistant.cs:451)：`if (!SignalPool.GetInstance().IsWaferAllowPickSignal.Wait())`
- **Wait** — [PickActionNode.Provider.cs:332](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs:332)：`if (!SignalPool.GetInstance().IsWaferAllowPickSignal.Wait())`
- **Wait** — [System2RunTimeProvider.cs:348](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/Parameter/System2RunTimeProvider.cs:348)：`while (!SignalPool.GetInstance().IsWaferAllowPickSignal.Wait(100))`
- **Wait** — [System2RunTimeProvider.cs:379](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/Parameter/System2RunTimeProvider.cs:379)：`if (!SignalPool.GetInstance().IsWaferAllowPickSignal.Wait())`
- **ReSet** — [Machine.Operate.cs:137](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:137)：`SignalPool.GetInstance().IsWaferAllowPickSignal.ReSet();`
- **ReSet** — [Machine.Operate.cs:156](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:156)：`SignalPool.GetInstance().IsWaferAllowPickSignal.ReSet();`
- **Wait** — [WaferSubController.cs:560](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferSubController.cs:560)：`if (!SignalPool.GetInstance().IsWaferAllowPickSignal.Wait())`
- **Wait** — [FlipTask.cs:101](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/WaferSubSystem/Tasks/FlipTask.cs:101)：`if (!SignalPool.GetInstance().IsWaferAllowPickSignal.Wait())`
- **Set** — [WaferSubSystemTask.cs:324](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs:324)：`SignalPool.GetInstance().IsWaferAllowPickSignal.Set();`

### IsBondNeedChipSignal

声明：`SignalPool.cs:147`；S2 发芯片需求，晶圆处理后清需求并发允许取晶；Stop 也复位。

- **Set** — [System2Controller.Assistant.cs:208](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.Assistant.cs:208)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [System2Controller.Assistant.cs:353](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.Assistant.cs:353)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [System2Controller.Assistant.cs:1323](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.Assistant.cs:1323)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [System2Controller.AutoCali.cs:378](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.AutoCali.cs:378)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [FrmComponentAccuracyMode.cs:1476](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Controls/Assistant/FrmComponentAccuracyMode.cs:1476)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [FrmComponentPickup.cs:590](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Controls/Assistant/FrmComponentPickup.cs:590)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [FrmComponentPlacement.cs:704](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Controls/Assistant/FrmComponentPlacement.cs:704)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [PickActionNode.cs:429](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs:429)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [PickActionNode.cs:445](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs:445)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [PickActionNode.MoveHelper.cs:888](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.MoveHelper.cs:888)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [PickActionNode.Provider.cs:75](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs:75)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [PickActionNode.Provider.cs:101](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs:101)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [PickActionNode.Provider.cs:255](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs:255)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [PickActionNode.Provider.cs:290](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs:290)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [PickActionNode.Provider.cs:646](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs:646)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [PickActionNode.Provider.cs:664](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs:664)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [SubstrateCameraCorrectionActionNode.cs:470](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.cs:470)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [SubstrateCameraCorrectionActionNode.cs:661](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.cs:661)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [SubstrateCameraCorrectionActionNode.Provider.cs:65](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.Provider.cs:65)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [UpLookCorrectionActionNode.cs:472](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs:472)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [UpLookCorrectionActionNode.cs:1439](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs:1439)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [UpLookCorrectionActionNode.cs:1525](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs:1525)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [UpLookCorrectionActionNode.cs:1681](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs:1681)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [UpLookCorrectionActionNode.cs:1767](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs:1767)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [UpLookCorrectionActionNode.cs:2029](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs:2029)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [FrmBaseTest.cs:621](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Experiment/Test/FrmBaseTest.cs:621)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [FrmMachineFunctionTest.cs:1718](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Experiment/Test/FrmMachineFunctionTest.cs:1718)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [FrmMachineFunctionTest.cs:1802](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Experiment/Test/FrmMachineFunctionTest.cs:1802)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [UcShortcutMenu.cs:1069](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Controls/UcShortcutMenu.cs:1069)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [UcShortcutMenu.cs:1361](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Controls/UcShortcutMenu.cs:1361)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **ReSet** — [Machine.Operate.cs:136](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:136)：`SignalPool.GetInstance().IsBondNeedChipSignal.ReSet();`
- **ReSet** — [Machine.Operate.cs:155](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:155)：`SignalPool.GetInstance().IsBondNeedChipSignal.ReSet();`
- **ReSet** — [Machine.Operate.cs:362](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:362)：`SignalPool.GetInstance().IsBondNeedChipSignal.ReSet();`
- **Set** — [FrmDebug.cs:109](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/WaferSubSystem/Controls/FrmDebug.cs:109)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [FlipTask.cs:143](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/WaferSubSystem/Tasks/FlipTask.cs:143)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Set** — [WaferSubSystemTask.cs:75](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs:75)：`SignalPool.GetInstance().IsBondNeedChipSignal.Set();`
- **Wait** — [WaferSubSystemTask.cs:80](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs:80)：`if (!SignalPool.GetInstance().IsBondNeedChipSignal.Wait())`
- **ReSet** — [WaferSubSystemTask.cs:322](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs:322)：`SignalPool.GetInstance().IsBondNeedChipSignal.ReSet();`

### IsBondNeedEjectionSignal

声明：`SignalPool.cs:152`；未找到此应用中的活动引用；不据此推断独立顶针线程。

在扫描范围内没有活动引用。

### IsEjectionComplete

声明：`SignalPool.cs:157`；未找到此应用中的活动引用。

在扫描范围内没有活动引用。

### IsLoadWaferMap

声明：`SignalPool.cs:162`；此应用中相关调用被注释；不纳入活动流程。

在扫描范围内没有活动引用。

### IsFlipTableAllowPickSignal

声明：`SignalPool.cs:167`；FlipTask 完成翻转后允许 S2 取晶。

- **Wait** — [System2RunTimeProvider.cs:389](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/Parameter/System2RunTimeProvider.cs:389)：`if (!SignalPool.GetInstance().IsFlipTableAllowPickSignal.Wait())`
- **ReSet** — [Machine.Operate.cs:159](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:159)：`SignalPool.GetInstance().IsFlipTableAllowPickSignal.ReSet();`
- **Set** — [FlipTask.cs:236](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/WaferSubSystem/Tasks/FlipTask.cs:236)：`SignalPool.GetInstance().IsFlipTableAllowPickSignal.Set();`

### IsAllowDipFluxSignal

声明：`SignalPool.cs:176`；SlideFluxerTask 胶盘就绪；DipFluxActionNode 等待。

- **Wait** — [DipFluxActionNode.cs:136](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/DipFluxActionNode.cs:136)：`if (!SignalPool.GetInstance().IsAllowDipFluxSignal.Wait())`
- **Wait** — [DipFluxActionNode.cs:709](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/DipFluxActionNode.cs:709)：`if (!SignalPool.GetInstance().IsAllowDipFluxSignal.Wait())`
- **Set** — [SlideFluxerTask.cs:147](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Tasks/SlideFluxerTask.cs:147)：`SignalPool.GetInstance().IsAllowDipFluxSignal.Set();`
- **ReSet** — [Machine.Operate.cs:160](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:160)：`SignalPool.GetInstance().IsAllowDipFluxSignal.ReSet();`

### BondDipFluxFinishSignal

声明：`SignalPool.cs:181`；Bond/UpLook 的配置分支通知胶盘；不能把注释掉的 DipFlux Set 当作活动调用。

- **Set** — [BondActionNode.Provider.cs:680](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.Provider.cs:680)：`SignalPool.GetInstance().BondDipFluxFinishSignal.Set();`
- **Set** — [UpLookCorrectionActionNode.cs:717](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs:717)：`SignalPool.GetInstance().BondDipFluxFinishSignal.Set();`
- **Set** — [UpLookCorrectionActionNode.cs:1550](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs:1550)：`SignalPool.GetInstance().BondDipFluxFinishSignal.Set();`
- **Set** — [UpLookCorrectionActionNode.cs:1555](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs:1555)：`SignalPool.GetInstance().BondDipFluxFinishSignal.Set();`
- **Set** — [UpLookCorrectionActionNode.cs:1792](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs:1792)：`SignalPool.GetInstance().BondDipFluxFinishSignal.Set();`
- **Set** — [UpLookCorrectionActionNode.cs:1797](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs:1797)：`SignalPool.GetInstance().BondDipFluxFinishSignal.Set();`
- **Wait** — [SlideFluxerTask.cs:150](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Tasks/SlideFluxerTask.cs:150)：`if (!SignalPool.GetInstance().BondDipFluxFinishSignal.Wait())`
- **ReSet** — [Machine.Operate.cs:161](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:161)：`SignalPool.GetInstance().BondDipFluxFinishSignal.ReSet();`

### AllowSlideOutSignal

声明：`SignalPool.cs:186`；Bond/UpLook 的配置分支允许胶盘伸出，SlideFluxerTask 等待。

- **Set** — [BondActionNode.Provider.cs:675](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.Provider.cs:675)：`SignalPool.GetInstance().AllowSlideOutSignal.Set();`
- **Set** — [BondActionNode.Provider.cs:683](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.Provider.cs:683)：`SignalPool.GetInstance().AllowSlideOutSignal.Set();`
- **Set** — [UpLookCorrectionActionNode.cs:1558](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs:1558)：`SignalPool.GetInstance().AllowSlideOutSignal.Set();`
- **Set** — [UpLookCorrectionActionNode.cs:1800](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs:1800)：`SignalPool.GetInstance().AllowSlideOutSignal.Set();`
- **Wait** — [SlideFluxerTask.cs:208](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/BondSystem/Tasks/SlideFluxerTask.cs:208)：`if (!SignalPool.GetInstance().AllowSlideOutSignal.Wait())`
- **ReSet** — [Machine.Operate.cs:162](C:/Users/akrs/Documents/ChatGPT/archify/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:162)：`SignalPool.GetInstance().AllowSlideOutSignal.ReSet();`
