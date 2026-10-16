# ZX2200 自动化源码分析

## 阅读范围与结论

只分析 `trunk` 的生产控制源码。没有启动机器程序、移动硬件或选择一个假定的现场配方。下述流程是源码中的条件流程；当前现场启用了哪些模块，需要由运行时配置确定。主要工程是 .NET Framework 4.8 Windows Forms，入口为 `AKRS.ZX2200/Program.cs::Main`。

整机采用多任务生产管线：输送任务搬运载具，S1 执行点胶配方，S2 执行固晶配方，晶圆任务响应芯片需求；翻转和蘸胶任务按硬件配置参与。它们靠共享状态和 `SignalPool` 交接，不是依次等待上一个线程结束。一个载具的结束也不是整个自动生产任务结束。

交互入口为 [index.html](index.html)。每个流程章节的“源码依据”提供方法、行号和原始代码片段。来源路径均位于当前工作区，没有伪造公开仓库或提交链接。

## 1. 启动、回零与生产启动

调用链：`Program.Main → MainForm_Load → 操作员 Start → Machine.Start → PrepareMachineReadyToStart → SetState(Working) → 各工作任务 Start`。

- `Program.cs:65–256`：单实例检查、异常处理、磁盘检查、可选软件授权检查；非 OffLineWork 执行 PR/硬件初始化和轴相关设置。硬件初始化的 catch 会记录/弹窗，但没有直接 return，不能画成“任何初始化异常都会退出进程”。按 `IsAxisResetBeforeWork` 调用回零，再进入主窗体。
- `Machine.Operate.cs::AllAxisGoHome:504–583`：人员确认；按配置收回气缸、关闭补偿、复位顶针/料仓相关机构、收回胶盘；`HardwareRepositoryService.OneKeyHome()` 成功后开启补偿并设 `AllAxisReset=true`。取消或失败返回 false。底层各轴的严格回零时序在外部驱动边界内，不能自行补画。
- `MainForm.cs::MainForm_Load:232–257`：在线且未完成回零时禁用主界面并返回；随后加载各配置仓库、连接 Modbus 仪器、启动后台监控。
- `UcMainSystem.Production.cs::BarItemStart_ItemClick:68–109` 和 `UcMainSystem.cs::BtStart_ItemClick:699–735`：可选配方确认、关闭手动面板、退出单步、调用 Start。取消不启动；捕获启动异常会 Stop。
- `Machine.Operate.cs::PrepareMachineReadyToStart:185–255`：清理文件、复位信号、确认回零、确认旧任务不在 Running、清检测计数、检查 PR/磁盘/预热、门状态和设备状态、移安全位、检查各域/产品/制程。失败返回，不启动生产。
- `MachineInitSuccess:408–443` 的预热条件只在对应加热配置及加热已开启时适用。`CheckOperatingEnvironment:89–127` 依次检查晶圆、S2、S1、产品、焊点辅助和制程。
- `Start:261–308`：先设 Working；非补偿模式启动输送、晶圆、配置的 S1；初始化 S2 动作序列并启动 Bond；按配置启动胶盘、翻转任务。启动顺序不等于动作的运行顺序。

## 2. 输送与上下料

调用链：`TransportDomain.StartTask → TransportTask.Start → 各段 Task.Run → TransportController.Transfer* → 工位控制器/轴/气缸/传感器`。

`TransportDomain.cs:84–140`：没有输送配置直接返回；DryCycle 使用 `StartDryRun`；正常路径检查载具、映射现有物料，再按料仓配置启动 Loader/Unloader，最后启动分段输送任务。

| 环节 | 条件、动作与交接 | 源码 |
|---|---|---|
| 在线上料 | 入料段空才发上游要料 IO；等入口感应，移动皮带后关闭要料；5 秒未到弹出重试/终止/退出连续上料 | `TransportController.TransferAutoLoaderToLoading:439–548` |
| 皮带或料仓到 S1 | 检查目的段和物料状态，执行转移；成功发 `TransferToDispense1FinishedSignal`。已有物料可根据配置提示继续。皮带路径在未配 S1 时直接发放行信号 | `TransportTask.cs:180–418` |
| 料仓握手 | Loader 首次移当前层并发 `LoaderAllowPushSignal`；搬运任务推料后复位该信号，发 `AllowLoaderMoveSignal`；Loader 移下一层再允许推料 | `LoaderTask.cs:74–119`; `TransportTask.cs:375–415` |
| S1 分段 | 配方排序插入 `InteractiveAction`；抬 Z 后发允许点胶1→点胶2信号，并等传输完成 | `S1ActionNodeController.cs:244–285`; `InteractiveAction.cs:29–64`; `TransportController.cs:1186–1208` |
| S1→S2 | S2 无料、S1 有料，且取得 `AllowDispenseTransferToBondSignal` 才传输；成功发 S2 来料完成信号 | `TransportController.cs:1266–1291`; `TransportTask.cs:525–540` |
| S2→等待下料 | S2 有料、等待区无料，且取得 `AllowBondTransferToWaitingUnloadSignal` 才传输 | `TransportController.cs:1531–1565` |
| 等待区→出口/料仓 | 根据上/下料配置分支；检查传感器和占用。料仓等待允许推料，推料后复位并发允许料仓移动 | `TransportTask.cs:606–770`; `TransportController.cs:1816–1861`; `UnloaderTask.cs:66–117` |
| 在线出料 | 下游要料 IO 为真且出料段有料才运行；检查出口传感器经过/离开；异常可重试、终止、忽略；结束清载具、置 NoMaterial/Ready 并 Save | `TransportController.TransferUnloadBeltToAutoUnloader:2292–2428` |

`NoStart` 通常表示条件还不满足，任务继续轮询，不等于失败重试。`Abort` 会在对应调用方触发 Stop。部分 catch 只弹窗，不能把所有 Exception 都画成统一停机。Ignore 后软件状态可能继续推进，并不能据此断言物理转移成功。

无输送时 S2 的 `GetIncomingSignal` 走人工放料/MapBelt，`SendAway` 可以保存 Mapping、清载具、提示人工拿走（`BondTask.cs:390–480`）。不要把这条路径与在线自动下料合并。

## 3. 配方如何变成动作序列

核心是 `ProcessDomain.S1SystemProcess/S2SystemProcess.ProcessSteps → ActionNodeController.Init → WorkMessages → GetNextActionNode → IsDoWork → DoWork → FinishCurrentActionNode`。

1. 取启用的制程步骤，按 `WorkProcess`（载具/基板/基岛/焊点优先）和 `WorkProcessModule`（步骤/位置优先）构造消息序列。不是按 C# 文件顺序执行。
2. 在载具、基板、基岛、焊点层插入定位、测高、识别等准备动作。是否真正执行，仍由具体动作条件决定。
3. S1 将 Epoxy 步骤映射为点胶，Defect 步骤映射为胶量检测。Divide 模式按 `GetFirstMatrixIndex` 把序列分成两组，在中间插入输送交互动作。代码先加入 `lastActionNodeMessages`，再 Interactive，再 `firstActionNodeMessages`；不能只凭变量名推断物理前后半片。
4. S2 的 Component 步骤生成 Pick、UpLook、SubstrateCameraCorrection、Bond；翻转/蘸胶配置决定 DipFlux 插入位置。Defect 生成 AfterBondCheck；Epoxy 生成 S2Dispense。S2 还执行 RemoveOtherStep、RemoveDisableActionNode、SortRelativeBond。
5. **生成两个校正节点不代表两台相机都拍照**：UpLook 在精度模式 Off 或选择 BondCamera 时直接返回 Success；SubstrateCameraCorrection 在 Off 或选择 UpLookCamera 时直接返回。见两个类的 `DoWork:131–154 / 136–152`。
6. `InjectSteps` 为载具中的焊点补充尚不存在的步骤状态，不是每次无条件清除历史状态。`GetNextActionNode` 找第一个 `Finished=false` 的消息；`FinishCurrentActionNode` 改消息状态。焊点自身还有 `S1RemainingSteps/S2RemainingSteps`，两层状态不同。
7. `SetActionNodeReWork` 根据动作名、基板、基岛、制程名找到消息并置 false；查不到会抛出 `ActionNode Sort Error`。调用方发出 Retry 并不保证重做一定成功。

依据：`S1ActionNodeController.cs:168–285,708–815,859–880`；`S2ActionNodeController.cs:92–234,715–874,1033–1115,1410–1435`；`DispenseActionNodes.cs:192–234`。

## 4. S1 点胶执行

`DispenseWorkTask.DoWork:63–181` 初始化排序，然后在 `Signal.WaitStart()` 循环内回安全位、等来料、注入步骤并执行动作。

- 等料的 `GetInputSignal:221–260` 每轮休眠 10ms，暂停时等待；调用预点胶；预点胶非 Success 返回 false；Stop 返回 false；收到来料后直接把信号的公开 `State` 改为 ReSet。它没有调用该事件的 `Wait()`，因此不能把这个实现称作标准 AutoResetEvent 消费。
- `PreDispenseAction.DoWork:74–169` 先调用 `IsDispense`。触发包括人工请求、入料后首次点胶条件、Periodic 间隔；Mode 和 Timing 都 Off 时跳过（177–209）。预点胶按预点胶板位置和胶图案执行插补，可配置胶后检测。检测调用的返回值未在 134 行传播，不能把预点胶函数 Success 解释为该检测已通过。
- `S1DispenseActionNode.DoWork:46–170`：等单步/运行状态、预点胶、取胶图案和焊点坐标、加入位置/旋转补偿、`DispenseController.InterpolationApplication`，成功标记焊点步骤完成、刷新统计。DryCycle 设置 `isDrip=false`。`IsDoWork:177–202` 根据产品启用范围和剩余步骤跳过。
- `S1DispenseMeasureActionNode` 调用 `MatterHeightMeasurePoints`，条件见 91–123；并非每个产品必测。定位/测高/识别节点按层级插入。
- 胶量检测 `S1DispenseDefectActionNode.EpoxyApplicationDefect:218–246`：Success 标步骤；Fail 禁用焊点后返回 Success；Abort Stop；Retry 通过 `ReDispense:190–209` 重置点胶/检测消息及步骤状态。**检测不合格可以是“已处理”，而非整机异常。**
- 任务层 Retry 不完成当前消息；其他非 Success 回安全位并 Stop。跳过或成功才完成消息。全部动作结束且未 Stop 才发 `AllowDispenseTransferToBondSignal`，随后 `Finish()` 重置消息，等待下一个载具。
- 等料阶段预点胶失败会使 S1 返回，但该分支本身没有调用 Stop（`DispenseWorkTask.cs:79–85,234–238`），需与动作层失败停机区分。

## 5. 晶圆供料、搜晶和翻转

`PickActionNode.PrepareBeforePickAction:55–78` 在首次取晶时设置芯片名、发 `IsBondNeedChipSignal`。晶圆线程 `WaferSubSystemTask.Dowork:64–324` 等该信号，查配方中的 Carrier；不存在则抛异常。当前无料片或芯片型号变化时置换料标志。

`ChangeTabletAuto:1105–1364` 名字虽有 Auto，也包含人工介入：DryCycle 初始化模拟料片；启用 MagazineLift 时查目标层、必要时归还当前料片并取目标层；缺型号可提示换 Magazine 再查；静态华夫盒和未使用升降料仓的路径可以弹出换料向导。换完还需 `ChangeSucceedOperation`；部分失败回到局部标签重试。

`Block.NextDie:335–355` 按 SearchMode 分派到 `SearchSingle / SearchNine / SearchMapping / SearchDieBox`，不是四者依次运行。搜晶失败若需要换片，走换片/重新选点路径；某些选点必须重新检查范围；未能恢复则异常，由任务 catch 弹窗并 Stop（`WaferSubSystemTask.cs:162–252,375–384`）。

找到芯片后按 CarrierType 控制真空，清需求信号，发 `IsWaferAllowPickSignal`。直接取晶和翻转取晶是互斥的接收路径：

- 普通 WaferCamera 或 StaticWaffle：S2 等晶圆允许取料。
- BondCamera 搜晶：S2 先到搜索位置，再等晶圆允许取料（`PickActionNode.Provider.cs:318–337`）。
- 使用 FlipTable：FlipTask 等晶圆允许，完成自己的取料/翻转流程，发 `IsFlipTableAllowPickSignal` 给 S2，再等 `IsBondPickSucceedSignal`。见 `FlipTask.cs:57–239`、`System2RunTimeProvider.cs:337–392`。

取晶结束可以提前请求下一颗。相同芯片在 Pick 侧刷新 Map 并发需求；不同芯片与精度校正模式有关，不能画成无条件提前换片（`PickActionNode.Provider.cs:633–664`）。

## 6. S2 从取晶到固晶完成

`BondTask.DoWork:100–354`：安全位/可选提前换嘴 → 等载具 → 取片温漂、系统温漂及参考点补偿检查 → 注入制程 → 取未完成动作执行。补偿检查的 false 分支直接 return，不能统一画成其本身调用 Stop。

**取晶动作**（`PickActionNode.cs:156–500`）：准备当前/下一芯片、换嘴/清嘴、模式分支、温漂补偿；等待可取信号；按相机/华夫盒获取角度并计算取晶位；配置真空、移动预取晶位、取片前检查；按 Wafer/Waffle/FlipTable 调用 Pick。成功后可做真空漏晶检测：重新检测、终止、忽略、重取同颗、抛料换下一颗是不同出口。结束设置 `IsMaterialOnBondhead`，预开校正灯光并异步通知下一供料/翻转交接。

**校正与蘸胶**：按 AccuracyMode/AdjustCamera 选择实际校正动作；翻转组件的 DipMode 决定蘸胶在精度校正前还是后，Off 不插入蘸胶节点。SlideFluxerTask 在需求条件下准备胶盘并发 `IsAllowDipFluxSignal`，等待 `BondDipFluxFinishSignal` 和后续 `AllowSlideOutSignal`，不是一个无条件随 Bond 串行执行的线程。

**固晶动作**（`BondActionNode.cs:118–370`）：准备参数 → 计算固晶位/预固晶位 → 移动 → 通知胶盘 → 清零与力控 → 选择正常贴装或配置的 TU 胶印动作 → Bond → 力数据输出 → 配置的焊后回带检测 → 统计/步骤完成。回带检测可以局部重新 Bond，也可以抛料并把 Pick、对应校正、Bond 置为未完成后返回 Retry。后者会回退到较早动作，不是只重做 Bond。

**检测与载具结束**：AfterBondCheck 是制程选择，不能宣称每次固晶必定检测。胶量检测分支也可禁用焊点后返回 Success，或触发重做（`AfterBondCheckActionNode.cs:638–670`）。动作列表无剩余时，BondTask 安全移动、Finish、归一化补偿、可选保存顶针时间，再 SendAway。自动路径发下料许可；人工路径提示拿走。外层循环继续运行。

## 7. 暂停、重试、停止与恢复的实际边界

| 情况 | 真实控制流 | 不能声称 |
|---|---|---|
| S1 Retry | 不标消息完成，再取未完成消息；动作可能已经重置更早消息 | 一定只重试当前机械动作 |
| S2 Retry | 继续循环；S2 获取消息还有重复校正节点保护，可能抛异常 | 所有 Retry 都保证成功回到原节点 |
| S2 Alarm | 弹窗 Abort / Retry / Ignore；Retry 直接跳回当前 DoWork；Ignore 继续并完成消息 | Ignore 代表检测或机械动作成功 |
| S2 Abort/Exception | Stop、抬 BondZ、按配置收胶盘、退出 | 任意返回码都进入这个分支；switch 没有覆盖所有枚举 |
| 开安全门 | 配置安全门且 Working 时设 Pause | 关闭门会自动恢复；恢复代码在该监控中被注释 |
| Continue | 检查门状态后设 Working，特定路径重置首次点胶标志 | 自动重建已经退出的所有工作线程 |
| Stop | 改状态、清弹窗/单步、复位要芯片、关闭在线要料与顶针真空等 | 自动 Join/取消所有任务 |
| EmergencyStop | 并行请求轴停止，再 Stop，再调 Abort 方法 | BondTask 的空 AbortThread 真正终止线程 |
| 持久化失败 | DBService.Insert catch 记录错误 | 数据库写失败自动重试或回滚物理动作 |

依据：`BondTask.cs:224–319,382–384`；`Machine.Operate.cs:314–401`；`Machine.Sustain.cs:276–319`；`DBService.cs:84–99`。

`Signal.WaitStart` 在 Pause 等待、Stop 返回 false。普通 `Wait()` 先过状态门，再轮询事件，循环检查 Stop；开始等信号后并没有每轮重新做 Pause 判断。`Wait(int outTime)` 实际使用 `recycleTime` 而不是参数（`Signal.cs:119–170,208–243`）。Loader/Unloader 的外层是 `while(IsWorking())`，与 WaitStart 不同：在循环边界遇到 Pause 可能退出；Continue 只改状态，不重启任务。这个时序差异必须保留。

## 8. 输入、输出与依赖

输入包含操作员指令、Settings 下硬件/设备 JSON、按 RecipeID 选择的配方 JSON、ProcessDomain 步骤、PR 模板、标定/补偿、芯片/吸嘴/胶配置、物料与传感器状态。路径见 `PathConfig.cs:40–94,117–119` 和 `ZX2200PathConfig.cs`。

输出包含物理贴装/点胶/转移、载具与焊点状态、产能/缺陷/参数/操作记录、配置的图片和力曲线、可选 Mapping。`StatisticsService` 使用容量 500 的 `BlockingCollection` 后台写本地 SQL Server；VisionService 使用图片集合后台存图；不是外部持久消息队列，也不是载具完成的提交屏障。

外部边界为 Galaxy 驱动/逻辑硬件 DLL、运动控制器、相机与 IO、配置的上下游设备、Modbus 仪器和 SQL Server。当前生产调用链没有建立 HTTP/MES/云调度证据。外部 DLL 的内部动作、线程安全和真实设备响应不在本次可证明范围内。

## 9. 与第一版总览的差异

现在分别分析启动、输送、点胶、供晶、S2 调度、取晶内部动作、固晶内部动作和故障恢复；增加实际调用的源码片段、信号表和方法索引。保留正常路径，也标出条件跳过、人工恢复、局部重做、线程返回及全机 Stop 的区别。完整指覆盖上述生产控制范围，不代表枚举全部实验窗体、全部配方排列或驱动内部实现。

图形交付状态：总览、时序和 8 张细分图均已交付且通过 showcase 校验。详细节点和分支可在导航页展开源码依据。
