# 启动调用链复核（第一批）

> 进度说明（2026-09-28）：本文保留分批分析过程。启动图 12 个节点及 10 条关系的最新限定范围验收，以 [启动章节语义复核](startup-semantic-revalidation.md) 和当前台账为准；旧文中的阶段性待办不代表最新计数。

## 域就绪检查末段补充

S2 CheckIsReady 的末段（System2Domain.cs:744–771）还处理记忆中的焊头持料：弹窗实际按钮类型为 OKCancel，仅 OK 调用 ThrowAction，其他结果继续向下检查，并非取消就阻止启动。随后 S2PreDispenseActionNode.IsAlarm 返回 true 才返回 false；否则 true。不能从弹窗文案中的“No”推断真实按钮类型。

晶圆域 CheckIsReady 的末段（WaferSystemDomain.cs:294–410）检查吸嘴架对应关系和按配置的翻转示教。自动料仓与手动换料模式随后分别处理已有料片：可能请求回顶针、放松扩张/气缸、归还料片或移动安全位，也可能经人工确认修改 CurrentTablet 并 Save。上述模式分支位于 !IsOffLineWork 检查块之后，不可把整个函数视为离线时无动作。

接下来按标志重建静态华夫盒或料仓状态，并清重建标志；若当前位置不在碰撞圆内，会请求顶针返回和晶圆台移到准备位。正常返回 true；catch 弹窗并返回 false，未见统一回滚之前的状态写入或动作请求。

现已阅读 S1/S2/晶圆域就绪检查的函数主体。内部 SelfCheck、IsReady、控制器到位行为仍未全部展开，因此 checks 节点仍保留待审核。证据键 s2-ready-tail、wafer-ready-tail 对应本次末段原文。

## 域就绪检查：已阅读范围与边界

- System1Domain.cs:481–528：未配置 S1 直接返回 true，解释了调用方无条件调用 S1.CheckIsReady 的原因。配置 S1 时先调用点胶头 IsReady；启用预点胶时检查预点胶板、胶型名称非 null 和胶型存在；最后调用胶料 IsReady。子对象 IsReady 内部尚待展开。
- System2Domain.cs:594–743（部分方法）：先调用 OpenBondHeadVaccum，再判断 IsActiveSelfCheck；关闭自检会返回 true，但前面的真空调用已经发生。开启后检查 BondProgram、ActionNodesService、ULM/焊头点位、按配置的吸嘴架、使用力控的芯片标定、温漂/取片偏移点位及工具检测。当前只审核方法前段，不代表已覆盖末尾条件。
- WaferSystemDomain.cs:159–293（部分方法）：先写入任务模式标志，调用 BondZ 安全位、推片气缸复位和关闭顶针台真空，再进入 !IsOffLineWork 分支。因此离线模式在此并没有跳过之前的控制器调用；控制器内部是否屏蔽硬件仍需核实。在线路径按顶针屏蔽及 isNoJudgeAssistant 控制料盒、示教与芯片配置检查。
- 晶圆域中明确拒绝“翻转台 + BondCamera 搜晶”组合，以及力控与同步顶等冲突；不能把模式枚举任意组合为有效生产路径。

新增证据键：s1-ready-body、s2-ready-prefix、wafer-ready-prefix。后两项明确只覆盖方法前段，不据此把启动检查标记为全部完成。

## 就绪检查补充：任务状态与初始化

`Machine.cs:201–262` 的 IsAllowTaskClosed 收集 S1（按配置）、晶圆、Bond、胶盘、翻转及输送相关 Task，仅对 `task?.Status == TaskStatus.Running` 返回 false。因此“允许启动”不能等价解释成“所有旧任务均 Completed”，其他 TaskStatus 没有在此判定中显式拒绝。

`Machine.Operate.cs:408–442` 的 MachineInitSuccess 检查配置要求的回零、PrInitSuccess、磁盘容量以及配置了输送加热且加热已开启时的预热完成状态。激光编码器检查块已注释。

`Machine.Operate.cs:89–127` 的 CheckOperatingEnvironment 按晶圆域、S2、S1、产品载具、焊点示教、制程的顺序检查，各 false 立即返回；本函数调用 S1.CheckIsReady 没有外层 IsSystem1Configrated 条件，S1 内部如何绕过仍应继续检查。

这些补充尚未将 checks 节点整体改为已审核，因为各域 CheckIsReady 的内部条件尚未完整联查。校验工具另以四项内存故障注入确认失效哈希、未知节点、空证据和缺失审核文档均被拒绝；这些测试不启动设备，也不修改源码。

状态：以下调用点已经阅读源码核对；尚未运行设备，不代表整个启动章节审核完成。

## 操作员请求与就绪检查

`UcMainSystem.Production.cs` 的 `BarItemStart_ItemClick`（68–109）先禁用控件；配置要求确认配方时，Cancel 在 84 行直接返回。通过后关闭手动移动面板、退出单步，在 99 行直接调用 `Machine.GetInstance().Start()`。异常在 103 行调用 Stop；finally 在 108 行恢复控件。

文件：[UcMainSystem.Production.cs](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L68)。

`Machine.Start` 在 266 行直接调用 `PrepareMachineReadyToStart`；返回 false 时在 269 行退出。检查函数并非只读检查：187 行清理文件，190 行复位信号；随后检查总复位、旧任务、初始化、安全门和 Working 状态；236、240、245 行还会请求安全位/顶针轴移动，最后在 249 行检查工作环境。

因此不能把“检查失败”解释成“此前没有发生任何副作用”，也不能把界面启动失败处理解释成所有后台任务异常都能由界面捕获。

文件：[Machine.Operate.cs](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L185)。

## 启动调用顺序与条件

| 调用点（Machine.Operate.cs） | 行号 | 条件 / 关系 |
|---|---:|---|
| SetState(Working) | 272 | 就绪检查返回 true 后直接调用 |
| TransportDomain.StartTask | 276 | 非 IsCompensateWork；域内部条件另查 |
| WaferSubSystemTask.Start | 277 | 非 IsCompensateWork |
| DispenseWorkTask.Start | 284 | IsSystem1Configrated 且非 IsCompensateWork |
| ActionNodesService.Init | 289 | 上述流程未异常退出时直接调用 |
| BondTask.Start | 290 | 不受上述补偿模式条件包围 |
| SlideFluxerTask.Start | 295 | IsSlideFluxerConfigured 且非 IsCompensateWork |
| FlipTask.Start | 303 | IsFlipModuleConfigrated 且非 IsCompensateWork |
| CheckAndOpenWaffleVacuum / CheckAndOpenStaticWaffleVacuum | 307–308 | 最后调用；内部开关条件另查 |

这是发起调用的顺序，不是机械动作完成的顺序。Start 中没有等待以上所有任务完成的统一 Join。

## 已查明的异步边界

- [DispenseWorkTask.cs](../../trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs#L189)：Start 在 195 行调用 Task.Factory.StartNew，回调在 199 行调用 DoWork。
- [BondTask.cs](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L361)：Start 在 365 行调用 Task.Factory.StartNew，回调在 369 行调用 DoWork。
- [WaferSubSystemTask.cs](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1373)：Start 在任务为空或 Status 非 Running 时执行初始化，再创建 LongRunning Task 调用 Dowork；否则仅设置 Working。catch 弹窗，不能据外层 Start 调用返回断言晶圆任务已成功运行。

## 下一批待核实

TransportDomain 内部分发、胶盘和翻转 Start 的异常处理、各生产任务的首个等待/放行点。当前台账保留 pending-review，待对应节点与关系逐项建立结构化审核记录后再更新状态。

## 第二批复核：输送、翻转与胶盘

以下补充覆盖上一节的部分待核实项。结构化原文定位见 [startup-call-sites.json](startup-call-sites.json)，执行 `node scripts/verify-startup-calls.cjs` 可重新检查 13 处调用行是否变化。

- TransportDomain.StartTask（84–140）：无输送配置直接返回；DryCycle 在 97 行调用 StartDryRun。普通路径检查载具，失败则 Stop 并返回；随后按配置清在线要料信号、刷新记录、映射物料。LoaderBin 分支同时启动 LoaderTask 和 UnloaderTask，最后启动 transportTask。catch 记录日志并弹窗，未重新抛出异常。
- 上述 Stop/return 只退出 StartTask；其调用者 Machine.Start 在 276 行之后没有检查返回结果。因此不能断言“输送检查失败就阻止所有后续 Start 调用”。后续任务是否重新设置 Working、如何退出还需联查。
- FlipTask.Start（260–276）：任务为空或状态不是 Running 时创建 LongRunning Task，回调调用 DoWork；返回 true 不证明翻转动作完成。流程内可见等待 IsWaferAllowPickSignal（101）、发送 IsFlipTableAllowPickSignal（236）、等待 IsBondPickSucceedSignal（239）。这些是信号消费/发送点，生产方和配置绕行条件仍需配对核实。
- SlideFluxerTask.Start（227–249）：未配置胶盘会直接抛异常；其余满足任务状态条件时创建 LongRunning Task。流程内先发送 IsAllowDipFluxSignal（147），等待 BondDipFluxFinishSignal（150），之后还等待 AllowSlideOutSignal（208）。不能把两次等待合并为一个“蘸胶结束”事件。

当前通过的是调用行一致性、证据一致性和台账一致性测试。异步故障传播、完整握手及设备运行尚未验收；不修改整个章节的 pending-review 状态。

## 第三批复核：就绪检查的实际子检查

本批把 `System1Domain.CheckIsReady` 与 `System2Domain.CheckIsReady` 调用的关键子检查展开到源码实现：

- `DispenserProgram.IsReady`（[DispenserProgram.cs](../../trunk/AKRS.ZX2200/DispenseSystem/Models/Programs/DispenserProgram.cs#L55-L80)）要求点胶针对象存在且 `IsAssistantSucceed` 为真；任一失败弹窗并返回 `false`。
- `EpoxyMaterialProgram.IsReady`（[EpoxyMaterialProgram.cs](../../trunk/AKRS.ZX2200/DispenseSystem/Models/Programs/EpoxyMaterialProgram.cs#L51-L65)）只检查胶水对象是否存在。`PreDispensePlateProgram.IsReady`（[PreDispensePlateProgram.cs](../../trunk/AKRS.ZX2200/DispenseSystem/Models/Programs/PreDispensePlateProgram.cs#L200-L203)）直接返回 `AssistanceFinish`，没有额外硬件检查。
- `BondProgram.SelfCheck`（[BondProgram.cs](../../trunk/AKRS.ZX2200/BondSystem/Models/Programs/BondProgram.cs#L85-L155)）先委托吸嘴架自检，再遍历载具检查吸嘴名称和多类力控参数范围；失败路径弹窗并返回 `false`。
- `S2ActionNodeController.SelfCheck`（[S2ActionNodeController.cs](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L1359-L1404)）拒绝空步骤；非异性输送配置时还检查每个步骤的焊点名称及其是否仍存在；异性输送配置会跳过这段焊点遍历。
- `NozzleShelfController.CheckToolBankConfiguration`（[NozzleShelfController.cs](../../trunk/AKRS.ZX2200/BondSystem/Controllers/NozzleShelfController.cs#L73-L147)）在启用换吸嘴架时读取槽位传感器；检测到“槽位无配置但传感器有吸嘴”会报警并返回 `false`，未启用时直接返回 `true`。

因此“系统2就绪”不是单一布尔开关，而是配置、载具参数、步骤引用和部分传感器状态的串联检查。当前仍未把所有被委托的 `ActionNodesService.SelfCheck`、吸嘴架完整槽位范围及晶圆域子检查全部展开；这些继续标记为待复核。

## 第四批复核：系统 2 动作步骤自检

`System2ActionNodesService.SelfCheck`（[System2ActionNodesService.cs](../../trunk/AKRS.ZX2200/DispenseSystem/Services/System2ActionNodesService.cs#L818-L923)）由 `System2Domain.CheckIsReady` 调用。其实际顺序是：

1. 要求系统 2 工艺步骤列表非空。
2. 对每个步骤要求焊点名非空，并在当前配方的焊点列表中存在。
3. 要求步骤组件名非空，并能从 `CarrierConfigRepository` 找到组件。
4. 对上视组件要求 `UpLookAdjustConfig.P1VisionPos` 非空；对下视组件要求 `DownLookAdjustConfig.P1VisionPos` 非空。
5. 任一条件失败都会弹窗并立即返回 `false`；全部通过才返回 `true`。

这说明系统 2 的启动自检不仅检查流程表，还校验流程步骤到焊点、组件和视觉示教位置的引用闭环。该函数本身没有启动动作或异步任务，只执行内存中的配方/仓储检查。

## 第五批复核：全局工艺步骤检查

`Machine.CheckOperatingEnvironment` 最后调用 `ProcessDomain.CheckIsReady`（[ProcessDomain.cs](../../trunk/AKRS.ZX2200/Main/Machine/Process/ProcessDomain.cs#L179-L252)）。源码显示：启用翻转模块时，启用且组件名非 `Null` 的系统 2 步骤数量必须不超过 1；随后逐步检查步骤名非空、序号非 0、焊点非空。非异性输送配置还要求焊点存在于当前焊点列表；异性输送配置的同等存在性检查被注释掉。每个步骤必须且只能选择一个功能：组件、缺陷或点胶应用名三者计数为 1。任一失败弹窗并返回 `false`，全部通过才返回 `true`。

该检查与系统 2 动作步骤自检存在重叠，但约束不同：`ProcessDomain` 检查步骤结构和功能互斥，`System2ActionNodesService` 进一步检查组件仓储及视觉示教位置。

## 第六批复核：晶圆域检查的副作用边界

对 `WaferSystemDomain.CheckIsReady`（[WaferSystemDomain.cs](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/WaferSystemDomain.cs#L159-L410)）逐调用点复核后，确认它不是纯配置谓词：函数开头会移动键合头到安全位、复位顶针气缸并关闭晶圆台真空（168–171 行）；根据料盒/晶圆台状态还会执行回顶针、扩张台下降、复位挡块、放片入槽、移动夹具/料盒安全位和判断晶圆台有无晶圆等动作（322–368 行）。

在线模式下，它检查料盒配置/硬件/示教、顶针示教、载具示教、映射参考点范围、晶圆半径、同步顶针与力控组合、翻转与搜晶相机冲突、纠偏相机类型、吸嘴存在性、蘸胶盘配置及吸嘴架配置；离线模式会跳过其中一段料盒/载具配置校验，但后续安全位和状态处理仍在函数体内执行。状态重建分支还会把静态适配器、料盒槽位和当前晶圆状态写回对象并保存/重置标志（372–395 行）。异常只弹窗并返回 `false`，没有看到事务回滚。

## 第七批复核：后台任务进入 DoWork 的首段

- 点胶线程 `DispenseWorkTask.DoWork`（[DispenseWorkTask.cs](../../trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs#L63-L119)）先初始化系统 1 动作控制器，再循环等待启动信号；每轮先移动到安全位，在线模式等待输送来料信号。来料失败会再次回安全位并退出线程；成功后可能重建产品对象、注入工艺步骤、计算周期并进入动作节点循环。
- 固晶线程 `BondTask.DoWork`（[BondTask.cs](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L100-L155)）先重置运行信息，再循环等待启动信号；每轮先把吸嘴架、固晶模组和固晶头置安全/复位位。启用提前换吸嘴且存在首个组件时先尝试换吸嘴，失败直接停止机器并退出；随后才等待输送来料。
- 翻转线程首个业务分支（[FlipTask.cs](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/FlipTask.cs#L92-L104)）在翻转吸嘴无芯片时等待 `IsWaferAllowPickSignal`，等待失败直接返回；因此该信号是翻转取片分支的进入闸门。

这些首段说明 `Start()` 返回成功只代表后台任务已提交，真实工作要等线程内部的 `WaitStart`、来料信号和设备动作完成；本轮未把任务完成等同于线程启动。

## 第八批复核：点胶/固晶动作循环与失败分支

- 点胶动作循环（[DispenseWorkTask.cs](../../trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs#L117-L181)）逐次取下一个动作节点；没有节点则结束本轮。动作返回 `Retry` 时继续当前循环；其他非 `Success` 会移动到安全位、停止机器并退出线程。成功完成整轮后，若机器未停止才发送 `AllowDispenseTransferToBondSignal`，随后重置产品动作状态。
- 固晶动作循环（[BondTask.cs](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L211-L315)）同样按节点执行，但先做取片温漂补偿、系统温度补偿和参考点扫描；任一失败直接返回。动作返回 `Abort` 或 `Exception` 时停止机器、抬升固晶头，配置胶盘时等待胶盘回原位，然后退出。`Retry` 使用 `goto RetryCommand` 重做当前节点；`Alarm` 弹出“终止/重试/忽略”，分别停止退出、重做当前节点或继续后续流程。

因此点胶和固晶的重试语义不同：点胶只对 `ExcuteResult.Retry` 继续循环，固晶对动作报警还提供人工重试/忽略分支；两者都没有在本段源码中提供自动重试次数上限。

## 第九批复核：固晶完成后的送出链路

固晶动作节点全部完成后，`BondTask.DoWork` 会先将固晶模组移到安全位、结束动作服务、归一化焊后补偿，并按配置保存顶针耗时数据（[BondTask.cs](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L330-L351)）。随后调用 `SendAway`：

- 已配置输送且机器未停止：设置 `AllowBondTransferToWaitingUnloadSignal`，允许输送移走产品。
- 已配置输送但机器已停止：只记录日志，不发允许传输信号。
- 未配置输送且机器未停止：可按配置保存 Mapping，清空当前载具对象、置为 `NoMaterial`，弹窗等待人工取走，然后停止机器。
- 未配置输送且机器已停止：只记录日志。

因此“固晶动作完成”与“载具已送走”是两个不同阶段；输送模式通过信号交接，非输送模式通过本地状态清理和人工确认结束。

## 第十批复核：固晶完成信号的输送消费端

`TransportTask` 的 Bond→等待下料区线程（[TransportTask.cs](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L846-L890)）在 `Signal.WaitStart()` 循环中先检查机器停止状态，再等待 `AllowBondTransferToWaitingUnloadSignal`。等待返回 `false` 时退出线程；成功后将 Bond 分段状态设为 `HasMaterial`，发送 `TransferToBondFinishedSignal`，并创建系统 2 载具对象，之后休眠 500ms 进入下一轮。异常只记录并弹窗。

这补齐了上一批的双向交接：固晶线程发送允许传输信号，输送线程消费后标记等待区有料并反向发送“传输到 Bond 完成”信号；下一轮固晶线程的 `GetIncomingSignal` 才能在输送配置启用时解除等待。

## 第十一批复核：等待区到出料区的分支

`TransportTask` 的后续输送分两种配置（[TransportTask.cs](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L602-L705)）：

- `LoadConfiguration == None`：不创建等待区到出料区的自动任务，直接返回。
- 非 `LoaderBin` 配置：创建“等待区传入出料区”任务，循环调用 `TransferWaitingUnloadToUnloadBelt()`。返回 `NoStart` 仅继续；`Success` 记录日志；`Abort` 或 `Exception` 停止机器；循环间隔 100ms。
- `LoaderBin` 配置：创建“等待区传入下料仓”任务，先等待 `UnloaderAllowPushSignal`，再调用 `TransferWaitingUnloadToUnloadBin()`。`NoStart` 等待 500ms 重试；`Abort`/`Exception` 停止并退出；成功后继续后续下料仓处理。

当前源码中该段没有直接消费 `AllowWaitingUnloadTransferToOutloadSignal`；实际放行由控制器调用结果或 `UnloaderAllowPushSignal` 驱动，不能把信号池中存在同名信号推断为此处必经条件。

## 第十二批复核：自动下料仓与联机收板

自动下料仓分支在 `TransferWaitingUnloadToUnloadBin()` 返回后，会等待 200ms，手动复位 `UnloaderAllowPushSignal`，再发送 `AllowUnloaderMoveSignal`（[TransportTask.cs](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L670-L710)）。`NoStart` 会延迟 500ms 重试；`Abort`/`Exception` 停机并退出；等待推料信号失败也直接退出。

当配置为 `Online` 或 `OnlineWithAutoUnloader` 时，另起“出料段到收板机”任务，循环调用 `TransferUnloadBeltToAutoUnloader()`：`NoStart` 延迟 100ms，`Abort` 停机，`Success` 继续下一轮；异常弹窗。该段源码没有显式发送新的完成信号，实际完成判断封装在控制器返回值中。

同一 `TransportTask.Start` 还提供 DryRun：夹紧点胶/固晶载台、将两段标记为有料、发送两段“传输完成”信号并创建测试载具，然后启动输送子任务（[TransportTask.cs](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L775-L800)）。

## 第十三批复核：输送任务的并发启动层

`TransportTask.Start` 会独立创建多个 `Task.Run` 输送线程，并以各自的 `TaskStatus.Running` 防止重复创建（[TransportTask.cs](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L430-L600)）：

- 点胶 1→点胶 2：循环调用控制器；成功后发送 `TransferToDispense2FinishedSignal`；`NoStart` 延迟 500ms，`Abort` 停机。
- 点胶→Bond：首次启动可根据 Bond 段已有料状态直接发送完成信号；若 Bond 台有料会弹窗询问继续或停止；正常路径循环调用传送控制器，成功后发送 `TransferToBondFinishedSignal`，每轮休眠 50ms。
- Bond→等待下料：循环调用控制器，`Abort`/`Exception` 停机，每轮休眠 100ms。

这些任务是并发提交的，`Start` 本身没有等待它们完成；各线程通过信号池和分段状态异步交接。首次启动的“已有料”分支可能直接解除 Bond 等待，属于实际源码中的恢复路径。

## 第十四批复核：输送控制器的启动条件

对三个控制器方法的入口条件进行了源码核对：

- `TransferBondToWaitingUnload` 只有 Bond 段状态为 `HasMaterial` 且等待区为 `NoMaterial` 才进入传送；自动模式还必须先收到 `AllowBondTransferToWaitingUnloadSignal`，停止时返回 `Abort`。随后并行执行松夹和挡料气缸动作，再启动 Bond 段皮带（[TransportController.cs](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L1531-L1599)）。
- `TransferWaitingUnloadToUnloadBelt` 首先要求等待区传感器有料；在线配置时还要求出料区传感器无料，并检查等待区状态不是 `NoMaterial`，Online 模式还会避让正在传输/已有料的出料段（[TransportController.cs](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L1816-L1860)）。
- `TransferWaitingUnloadToUnloadBin` 要求等待区传感器有料、状态为有料、皮带已停止；联机时下料区不能已有料，否则均返回 `NoStart`。满足条件后才将等待区传输状态置为 `Transfering` 并启动皮带（[TransportController.cs](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L2063-L2111)）。

这些条件解释了前面任务循环中大量 `NoStart`：它表示当前状态不满足传输前置条件，并不等价于故障。

## 第十五批复核：Bond→等待区传送的传感器闭环

`TransferBondToWaitingUnload` 启动 Bond 皮带后持续读取出料传感器 E（[TransportController.cs](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L1598-L1659)）。皮带停止前检测到有料才进入等待区皮带阶段；若皮带结束仍未检测到料，将传输状态置为 `Alarm` 并弹出“重试/终止/忽略”：重试回到 Bond 皮带传送，终止返回 `Abort`，忽略继续流程。

检测到 Bond 出料后，等待区皮带启动并继续检查 Bond 出料传感器 E 与等待区入口传感器 F；源码注释明确指出不能在等待区皮带尚未停止前提前写回分段状态。由此可见，控制器返回成功不只是发出皮带启动命令，而是经过传感器检测和人工报警分支后的结果。

## 第十六批复核：传送完成的状态提交点

当等待区入口传感器 F 命中时，控制器同时停止 Bond 皮带和等待区皮带（[TransportController.cs](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L1696-L1715)）。随后再次检查 Bond 出料传感器 E 与 F；若 E 仍有料或 F 从未命中，则把等待区传输状态置为 `Alarm`，弹出重试/终止/忽略，重试只重新转等待区皮带。

通过检查后才提交状态：把载具对象从 Bond 段转移到等待下料段，等待段置为 `HasMaterial`，刷新载具；Bond 段置为 `NoMaterial` 并清空载具；两段传输状态均置为 `Ready`，保存输送程序，返回 `Success`（1777–1790 行）。异常记录日志、弹窗并返回 `Exception`。因此 `Success` 对应的是传感器确认后的状态迁移和持久化，而非单纯电机动作完成。

## 第十七批复核：等待区→出料区的传感器提交

`TransferWaitingUnloadToUnloadBelt` 先用传感器 G 确认物料进入出料段；皮带结束仍未命中时把等待区传输状态置为 `Alarm`，提供重试/终止/忽略。命中后将出料段状态置为 `Transfering`，启动出料皮带；当入口传感器失去物料时，按 `IsUnloadingSubSectionContinueMove` 配置决定是否停止出料皮带，同时停止等待区皮带（[TransportController.cs](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L1863-L1953)）。这表明该阶段的 `Success` 仍依赖后续传感器和状态写回，不能仅由 `MoveBeltNoWaitArrive()` 推断。

## 第十八批复核：等待区→出料区的状态提交与回滚范围

传感器确认后，控制器还会检查出料区入口/模块传感器与等待区模块传感器；发现残留物料时同时把等待区和出料区传输状态置为 `Alarm`，提供重试/终止/忽略。通过后才把载具对象转移到出料段、刷新载具，清空等待区对象，并将等待区置为 `NoMaterial`、出料区置为 `HasMaterial`，两段传输状态置为 `Ready`，保存程序并返回 `Success`（[TransportController.cs](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L1956-L2034)）。异常处理会恢复等待区原状态 `stateTemp`，记录日志、弹窗并返回 `Exception`；源码没有对出料区状态做同等回滚。

## 第十九批复核：等待区→下料仓的推料与重试

`TransferWaitingUnloadToUnloadBin` 启动等待区皮带后，持续检查等待区物料传感器；皮带结束仍有料则置为 `Alarm`，支持重新传送、终止或忽略。确认物料已离开等待区后，先收回推杆，再调用 `PushTabletToUnloader()` 推料；推料失败提供“重试/忽略/终止”，重试回到推料动作，终止返回 `Abort`（[TransportController.cs](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L2103-L2200)）。

## 第二十批复核：推料成功后的仓位状态提交

自动下料仓推料后，若等待区传感器仍检测到物料，会同时把等待区和下料区传输状态置为 `Alarm`；重试先收回推杆再回到传送入口，终止返回 `Abort`。通过后收回推杆、停止等待区皮带，清空等待区载具，将等待区置为 `NoMaterial`、下料区置为 `HasMaterial`，两段传输状态置为 `Ready`，递增当前下料仓层位并保存程序，返回 `Success`（[TransportController.cs](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L2200-L2263)）。异常仅恢复等待区原状态 `stateTemp`，记录并弹窗后返回 `Exception`。

## 第二十一批复核：出料段→收板机状态提交

`TransferUnloadBeltToAutoUnloader` 只有出料段有料、当前不在传输中且收板机要料信号为真时才启动。出料传感器未命中会报警并支持重试/终止/忽略；命中后继续等待物料离开出料口，若仍有料同样报警。确认离开后清空出料段载具，将出料段置为 `NoMaterial`、传输状态置为 `Ready`，保存程序并返回 `Success`（[TransportController.cs](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L2292-L2447)）。异常记录并弹窗返回 `Exception`，未见状态回滚。

## 第二十二批复核：料仓移动前的载具阻断

`CheckCarrierBeforeLoaderMove` 先检查出料口和入料口传感器。启用 `LoaderBin` 或 `OnlineWithAutoUnloader` 时，出料口有载具会弹窗阻止下料仓移动；启用 `LoaderBin` 或 `OnlineWithAutoLoader` 时，入料口有载具会弹窗阻止上料仓移动。两种阻断都支持重新检测或终止返回 `false`；没有检测到阻断才返回 `true`（[TransportController.cs](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L2450-L2526)）。

## 阶段覆盖清单（当前）

已用源码逐段核实：启动入口与 `Machine.Start` 调用顺序；启动前就绪检查及其设备副作用；系统 1 点胶线程首段与动作循环；系统 2 固晶线程首段、动作循环和送出信号；翻转取片首个信号闸门；输送任务并发启动；点胶→Bond、Bond→等待区、等待区→出料区、等待区→下料仓、出料段→收板机的控制器前置条件、传感器确认、状态提交、重试/终止/忽略及异常返回。

尚未声称完成：晶圆线程 `DoWork` 的完整动作循环；翻转线程完整动作循环；系统 1/系统 2 各动作节点内部业务；所有控制器的硬件实现细节；真实设备运行验证。台账中的 86 个节点和 99 条关系仍表示文档化流程骨架，不能替代这些未完成的源码复核。

## 第二十三批复核：晶圆线程的取料请求与换料入口

`WaferSubSystemTask.Dowork`（[WaferSubSystemTask.cs](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L64-L180)）以 `Signal.WaitStart()` 为外层循环，先等待 `IsBondNeedChipSignal`；等待失败回到等待标签。单独空跑模式会按配置延时后主动发送该要料信号。收到请求后按 `CurrentNeedChipName` 查找载具配置，名称不存在直接抛异常。

当前晶圆台为空或需求芯片名不同会设置换料信号；若 `IsNeedChange` 为真则调用 `ChangeTabletAuto()`，失败写入更换料片告警并抛异常，成功也写入告警记录。随后调用 `Block.NextDie()` 搜索下一颗芯片；搜索失败且仍需换料时，晶圆图模式回到换料入口继续尝试。该段明确把“Bond 要料→查找载具→必要时换料→搜晶”串成顺序链路。

## 第二十四批复核：晶圆搜晶失败与取料前真空分支

`NextDie()` 失败时，晶圆图模式会回到换料入口；非晶圆图模式在干循环下直接换料，正常模式通过视觉报警提供 OK/Retry：Retry 会校验重新选择的位置是否在搜晶范围内，必要时重新选点，然后把当前料片标记为 `Good` 并异步保存参数，回到换料入口；无法恢复时抛出“搜晶失败”异常。

`NextDie()` 成功后记录上一次芯片名称，并按载具类型和配置打开/关闭晶圆台或顶针真空，打开时按配置延时。随后进入发送“允许取料”信号的分支；不同载具类型和空跑/离线模式会改变后续信号与真空行为（[WaferSubSystemTask.cs](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L159-L310)）。

## 第二十五批复核：晶圆允许取料信号与线程收尾

搜晶和取料前处理完成后，晶圆线程会复位 `IsBondNeedChipSignal`，设置 `IsWaferAllowPickSignal`，记录日志。静态适配器空跑模式还会把搜晶结果转换为固晶头/模组位置并执行移动；空跑模式可刷新晶圆图并递增计数。启用 `IsRecordSearchData` 且为空跑时，会把匹配结果写入 `D:\连续搜索实验.xlsx`；启用 `IsSearchOne` 时立即停止机器（[WaferSubSystemTask.cs](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L293-L373)）。

线程级异常会弹窗、调用 `Machine.Stop()` 并结束 `Dowork`；本段没有向 Bond 发送“取料完成”信号，允许取料信号本身是该线程对 Bond/翻转侧的交接点。

## 第二十六批复核：翻转线程主循环入口

`FlipTask.DoWork` 启动先调用 `FlipTableGoHome()`，随后在 `Signal.WaitStart()` 循环中从 `ActionNodesService.GetCurrentComponent()` 获取当前组件。组件为空时每 100ms 重试，源码中的超时报警逻辑被注释。只有当前组件启用 `IsUseFlipTable` 且翻转吸嘴上没有芯片时，才进入 `IsWaferAllowPickSignal` 等待；等待失败直接退出线程（[FlipTask.cs](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/FlipTask.cs#L57-L104)）。

## 第二十七批复核：翻转线程向晶圆请求下一颗芯片

翻转线程收到晶圆允许取料后，异步监视翻转台实际角度；超过 `SearchComponentAvoidancePos` 才刷新 Map、设置当前需求芯片并发送 `IsBondNeedChipSignal`。若没有下一颗组件则不发要料信号。等待超过 10 秒弹出“忽略/终止”：忽略重置计时，终止停止机器；机器停止也会退出等待（[FlipTask.cs](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/FlipTask.cs#L106-L183)）。

随后按 DryCycle 或正常模式调用不同翻转动作。动作 `Success` 将 `IsComponentOnFlipTool` 设为真；`Exception`/`Abort` 对晶圆载具先收回顶针并退出；`NoStart` 进入后续取下一颗分支（源码后段继续处理）。

## 第二十八批复核：翻转取片完成到 Bond 取片交接

翻转动作返回 `NoStart` 时回到 `NextDie` 重新等待晶圆取料；`Exception`/`Abort` 收回晶圆顶针后退出。动作完成后发送 `IsFlipTableAllowPickSignal`，再等待 `IsBondPickSucceedSignal`；等待失败直接退出，成功才记录取片完成日志。主循环结束后翻转台回原位（[FlipTask.cs](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/FlipTask.cs#L219-L254)）。`Start()` 创建 LongRunning 任务并先把机器状态设为 `Working`，返回值仍只代表任务提交成功。

## 第二十九批复核：Bond 取片成功信号的生产条件

`IsBondPickSucceedSignal` 的主要生产点在 `PickActionNode.Provider`：Bond 取片动作完成后，如果翻转台碰撞区域判断仍未满足，则持续等待；超过 10 秒弹出“忽略/退出”，退出会停止机器。只有离开碰撞区域后才设置 `IsBondPickSucceedSignal`（[PickActionNode.Provider.cs](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs#L590-L626)）。另一个取片分支在处理最后一颗或普通路径时也直接设置该信号（[PickActionNode.cs](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs#L410-L445)）。因此翻转线程等待到的不是单纯“动作函数返回”，而是 Bond 取片动作进入相应的空间安全/分支完成点后发出的 AutoReset 信号。

## 第三十批复核：启动前信号复位

`Machine.ResetMachineSignal` 在启动准备阶段被调用，会复位晶圆、输送、上下料、Bond/翻转和蘸胶相关信号，包括 `IsBondNeedChipSignal`、`IsWaferAllowPickSignal`、`AllowBondTransferToWaitingUnloadSignal`、`TransferToBondFinishedSignal`、`IsBondPickSucceedSignal`、`IsFlipTableAllowPickSignal`、`IsAllowDipFluxSignal`、`BondDipFluxFinishSignal` 和 `AllowSlideOutSignal`（[Machine.Operate.cs](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L130-L163)）。因此源码明确尝试在每次启动前清理上一轮信号；这仍不等同于已验证所有后台任务都已停止。

## 第三十一批复核：Bond PickAction 消费晶圆允许取料

`PickActionNode` 在计算取料位前记录并调用 `System2RunTimeProvider.WaitAllowBondPickSignal(component)`；非补偿模式下等待失败返回 `ExcuteResult.Abort`，成功后才增加组件累计数量并继续视觉定位（[PickActionNode.cs](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs#L194-L224)）。另一个移动到晶圆搜晶位置的辅助路径也直接等待 `IsWaferAllowPickSignal`，失败返回 `Abort`（[PickActionNode.Provider.cs](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs#L320-L337)）。这与晶圆线程设置该信号形成明确消费关系，且信号为 AutoReset，成功消费后自动复位。


## 第三十二批复核：Bond 取片的视觉与位置准备

消费晶圆允许取料信号后，`PickActionNode` 按载具类型分支：静态华夫执行 `StaticWaffleVision`，`Abort` 退出、`Retry` 回到下一颗、`Success` 保存匹配角度；其他类型若使用 Bond 相机则移动到搜晶位并等待信号，再从晶圆域取得旋转角度。随后写入组件角度，计算最终取晶位，执行取片前真空准备、计算预取位置和安全高度并移动到预取位；任一步失败直接返回。最后启动力控曲线/取片力采集并执行取片前检查（[PickActionNode.cs](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs#L217-L314)）。

## 第三十三批复核：Bond 实际取片与漏晶处理

`PickActionNode` 根据组件选择取片类型：翻转台、晶圆载具或华夫载具，然后调用 `Pick`。成功后清除 `IsComponentOnFlipTool`；`Abort`直接返回，`Exception`收回顶针并返回异常。成功取片会增加组件和顶针可用计数。非 DryCycle 且启用组件检测时，会检查取片后真空；漏晶报警提供重新检测、退出、忽略、重取、下一颗：重新检测回到真空检查，重取回到 `Pick`，下一颗先执行抛料并进入下一颗信号分支（[PickActionNode.cs](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs#L316-L430)）。

## 第三十四批复核：取片后的下一颗交接与动作完成

漏晶选择“下一颗”时，动作节点会刷新 Map；在翻转台组件的最后一颗/普通分支分别设置下一次需求芯片并发送 `IsBondNeedChipSignal`，设置 `IsRepickComponent` 后回到 `NextDie`。成功取片后标记 `IsMaterialOnBondhead`，异步设置视觉灯光；若暂停/停止信号无效则返回 `Abort`。非翻转组件异步调用 `SendSignalToWaferTable`，翻转组件异步调用 `SendSignalToFlipTable`，随后动作节点返回 `Success`（[PickActionNode.cs](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs#L425-L514)）。异常记录并弹窗返回 `Exception`，finally 将节点状态置为 `Stop`。

## 第三十五批复核：取片完成后的晶圆/翻转通知策略

`SendSignalToWaferTable` 不是无条件发信号：当下一组件名与当前组件相同且非空时，刷新 Map、继续请求同类芯片；当当前组件纠偏模式为 `Off` 时，改为把下一组件名传给晶圆台并请求下一类芯片；其他纠偏模式分支不在此处发信号（[PickActionNode.Provider.cs](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs#L633-L672)）。

`SendSignalToFlipTable` 会先把翻转台边界转换到机器坐标，在暂停时持续等待；后续循环在翻转台离开 Bond 碰撞区域后才设置 `IsBondPickSucceedSignal`（同文件 571–626 行）。因此取片完成后的异步通知还受纠偏模式、下一组件关系、暂停状态和空间安全边界共同约束。

## 第三十六批复核：取片节点的业务门槛

`PickActionNode.IsDoWork` 只有当前焊点工艺状态不是 `Disable`/`EnableInSystem1` 且当前步骤仍需要系统 2 执行时才返回 `true`；否则动作循环会跳过该节点。`IsAlarm` 会检查当前基岛和当前芯片对象：找不到基岛会把机器状态设为 `Stop` 并报警；当前芯片获取失败会报警并返回 `false`（[PickActionNode.cs](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs#L517-L579)）。

## 第三十七批复核：Pick 硬件动作顺序

私有 `Pick()` 在补偿模式直接返回 `Success`；正常模式依次取得取片参数、移动到取片高度、打开吸嘴真空、关闭平台真空，翻转台取片时按配置吹气并记录取片力；晶圆载具执行顶针动作，随后等待取片延时、停止力控采集，并按同步顶针配置决定是否低速抬头（[PickActionNode.cs](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs#L587-L697)）。空引用和其他异常都会记录、弹窗并重新抛出，由外层动作捕获为 `Exception`。

## 第三十八批复核：取片前保护条件

`CheckBeforePick` 在真正 `Pick` 前检查：启用翻转台时必须位于交接位，否则抛异常；若吸嘴吹气仍开则先关闭；力控取片模式执行焊头清零；最后校验晶圆线程当前需求芯片名必须与当前组件名一致，否则抛出动作排序异常。全部通过才返回 `Success`（[PickActionNode.Provider.cs](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs#L775-L805)）。

## 第三十九批复核：预取位移动安全分支

`MoveToPrePickPos` 在非静态华夫且启用翻转模块时，要求翻转台处于交接位（翻转组件）或原位（普通组件），否则抛出碰撞风险异常。重取组件使用安全绝对运动并清除 `IsRepickComponent`；普通路径按轴运动模式选择绝对移动或插补移动，绝对移动失败会报警并返回失败结果（[PickActionNode.MoveHelper.cs](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.MoveHelper.cs#L61-L125)）。

## 第四十批复核：插补到预取位的保护条件

`JumpToPickupPos` 先等待单步许可，失败返回 `Abort`；软限位检查失败返回 `Exception`。随后读取安全高度和当前位置；若启用 T 轴单独运动，会在静态华夫/Bond 相机模式直接旋转，否则等待 Z 轴达到安全高度或相对起始位置变化至少 1，再旋转 T 轴，超过 10 秒抛出超时异常（[PickActionNode.MoveHelper.cs](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.MoveHelper.cs#L128-L220)）。

## 第四十一批复核：插补段的分段轨迹与安全高度

插补运动根据载具/搜晶相机选择轨迹：静态华夫要求当前 Z 不低于 TU 安全高度，否则停机、报警并返回 `Exception`；Bond 相机分三段先升安全高度、再移动 XY/T、最后下到取片位；普通载具在当前 Z 低于抬升安全高度时先升高并移到轨道外延，再到取片位，否则直接两段移动。每段使用统一速度、加减速和前瞻参数，之后提交连续插补运动（[PickActionNode.MoveHelper.cs](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.MoveHelper.cs#L220-L315)）。

## 第四十二批复核：插补运动的完成与异常出口

连续插补提交后，若启用 T 轴单独运动会等待其任务完成；随后记录结束并返回 `Success`。Dsa 运动异常和其他异常都会关闭取片力读取标志、记录错误并重新抛出，由上层处理（[PickActionNode.MoveHelper.cs](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.MoveHelper.cs#L307-L337)）。

## 第四十三批复核：固晶动作入口与焊后回带检测

`BondActionNode` 在记录实际固晶位置后，先发送胶盘相关信号、设置力控曲线并清零焊头；当组件启用蘸胶且达到设定周期时选择 `DipFluxOnTU`，否则选择 `BondOnTU`，调用 `Bond()`，失败直接返回；成功后导出力控数据。非 DryCycle、非蘸胶且启用“固晶后慢速抬升+组件检测”时，会检查吸嘴上是否仍有芯片并关闭吸嘴真空；检测到残留时提供重贴、终止、忽略、重新取贴，重贴回到 `ReBond`（[BondActionNode.cs](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.cs#L170-L250)）。

## 第四十四批复核：焊后残留和胶印检查分支

焊后检测发现吸嘴残留时：重贴回到 `ReBond`；终止增加 Bond 失败计数并返回 `Abort`；忽略增加失败计数、抛料后继续；重新取贴增加失败计数、抛料、增加拒料计数，按纠偏相机把 Pick/上视纠偏或 Bond 相机纠偏/Bond 节点组成重做列表，设置 `IsRepickComponent` 并返回 `Retry`。随后按蘸胶周期执行胶印视觉检查：成功继续，失败只增加 Bond 失败计数，终止返回 `Abort`，异常增加失败计数、报警并返回 `Exception`（[BondActionNode.cs](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.cs#L230-L334)）。

## 第四十五批复核：Bond 节点完成提交

胶印检查后递增蘸胶观察计数并执行历史焊点视觉查看；随后清除 `IsMaterialOnBondhead`，将当前步骤写入焊点完成状态，统计固晶周期，递增吸嘴耗材使用次数，检查贴片数量上限，刷新界面并返回 `Success`。异常记录/弹窗后返回 `Exception`，finally 将节点状态设为 `Stop`。`IsDoWork` 还要求焊点实体状态为 `Process`、工艺不是禁用/仅系统 1 且当前步骤需要系统 2，否则跳过（[BondActionNode.cs](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.cs#L334-L407)）。

## 第四十六批复核：Bond 私有动作顺序

`Bond()` 先取得固晶参数并低速移动到固晶高度，再计算并执行固晶延时。非蘸胶固晶会关闭吸嘴真空、异步弱吹并等待关真空延时；蘸胶固晶跳过这段。随后记录最终固晶力、停止力控读取、低速抬头并返回 `Success`。任意异常记录/弹窗后返回 `Exception`（[BondActionNode.cs](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.cs#L467-L535)）。

## 第四十七批复核：固晶节点报警前置条件

`BondActionNode.IsAlarm` 会检查当前组件、当前焊点和当前基岛：组件获取失败弹窗并返回 `false`；焊点或基岛为空也返回 `false`。全部对象有效才返回 `true`（[BondActionNode.cs](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.cs#L410-L447)）。

## 第四十八批复核：焊后检测节点入口分支

`AfterBondCheckActionNode.DoWork` 在自动模式先装载当前基板、基岛、焊点、焊后检测配置和组件；若配置不需要缺陷检测，则直接把当前步骤标记完成并返回 `Success`。离线模式同样只标记完成；DryCycle 进入专用空跑检测。在线正常模式按应用系统分为胶量检测和焊后检测：胶量检测先计算视觉位置并调用 Bond 相机拍照；焊后检测再按是否有参考点、测量点数和背崩配置进入对应视觉分支（[AfterBondCheckActionNode.cs](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/AfterBondCheckActionNode.cs#L112-L189)）。

## 第四十九批复核：焊后检测视觉分支与返回语义

焊后检测在线分支按配置选择：无参考点一点/两点定位；有参考点一点/两点定位；背崩检测会在定位成功后调用背崩算法，`Retry` 回到检测；两点定位点位为空返回当前缺陷结果。`BLTMeasure` 则分别测量芯片周围和表面高度，再调用 `BLTCheck`。所有分支由结果处理函数返回 `Success/Fail/Retry/Abort/Exception`；外层异常记录、弹窗并返回 `Exception`（[AfterBondCheckActionNode.cs](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/AfterBondCheckActionNode.cs#L180-L340)）。

## 第五十批复核：焊后结果处理语义

无参考点结果处理在定位点为空时返回 `Fail`；否则将角度叠加基板角度、记录缺陷并交给 `PostBondDefect`。背崩检测命中时：Abort 增加焊后失败计数、停机并返回 `Abort`；Ignore 增加失败计数、禁用当前焊点并返回 `Success`；OK 返回 `Retry`。有参考点处理会计算两点相对 X/Y/角度偏差、记录缺陷并交给 `PostBondDefect`（[AfterBondCheckActionNode.cs](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/AfterBondCheckActionNode.cs#L472-L550)）。

## 第五十一批复核：焊后缺陷处理和补偿取回

胶量检测结果：`Success` 标记步骤完成并结束缺陷记录；`Fail` 将焊点设为禁用但返回 `Success`；`Abort` 停机并返回 `Abort`；`Retry` 调用 `ReDispense()` 并返回 `Retry`。未知结果抛异常。普通焊后检测同样将 `Success` 标记完成、`Fail` 禁用焊点、`Abort` 停机；补偿模式下检测前会执行 `PickUpDie()` 将芯片重新取起（[AfterBondCheckActionNode.cs](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/AfterBondCheckActionNode.cs#L638-L745)）。

## 第五十二批复核：BLT 厚度检测结果与报警分支

`BLTCheck` 逐点计算 `height2 - height1` 并保留 3 位小数，随后计算平均厚度和极差。当平均厚度偏离 `BLTStandard` 超过 `MaxBLTOffset`，或极差超过 `MaxSurfaceSlope` 时生成报警信息；无报警则完成当前步骤、结束缺陷记录并返回 `Success`。有报警时相机会移动到测量位置并关闭测量气缸：用户选择 `Abort` 会增加焊后失败计数、停机并返回 `Abort`；选择 `Ignore` 会增加失败计数、禁用当前焊点并返回 `Success`；选择 `OK` 会将步骤标记完成并返回 `Success`；其他结果按终止处理（[AfterBondCheckActionNode.cs](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/AfterBondCheckActionNode.cs#L776-L844)）。

## 第五十三批复核：主窗体加载到生产启动事件

`Program.Main` 构造 `MainForm` 后进入 `Application.Run`；`MainForm` 构造函数只初始化 WinForms 组件、取得平台提供者并注册 UI 委托（[MainForm.cs](../../trunk/AKRS.ZX2200/Main/Controls/MainForm.cs#L53-L62)）。窗体 `Load` 事件先检查非离线模式下是否已经完成全部轴复位；未复位时禁用主系统 Tile 并直接返回。通过后才加载设备数据、修正并保存载具配置、初始化参数、连接两个压力表、选择灯光、启动后台线程并创建导出目录（[MainForm.cs](../../trunk/AKRS.ZX2200/Main/Controls/MainForm.cs#L227-L270)）。

生产启动按钮由设计器绑定到 `BarItemStart_ItemClick`（[UcMainSystem.designer.cs](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.designer.cs#L702-L706)）。事件处理器先禁用当前控件；若启用配方确认则读取 `MachineConfigContext.RecipeName`，取消直接返回；之后关闭方向盘面板、退出单步模式并调用 `Machine.Start`。调用异常时执行 `Machine.Stop` 并弹出“启动失败”，无论结果如何 finally 重新启用控件（[UcMainSystem.Production.cs](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L68-L110)）。因此从界面到生产调度的确认调用链为：`Program.Main → MainForm → MainForm.Load 前置初始化 → BarBtStart.ItemClick → BarItemStart_ItemClick → Machine.Start`；`MainForm.Load` 的轴复位门禁和启动按钮的配方确认是两个不同层级的分支。

## 第五十四批复核：后台监控线程与生产任务并行关系

`MainForm.Load` 在完成数据、压力表、灯光等初始化后调用 `Machine.StartBackGroundThread`。该方法只有在线程对象为空或已结束时才创建线程；线程命名为“后台监控线程”、设置为后台线程，并在 `RuntimeProvider.ThreadFlag` 为真时循环。每轮依次执行安全门检查、激光干涉尺检查、高权限自动登出、温度报警、耗材检查、信号扫描、视觉图片保存和统计数据保存，最后休眠 100ms（[Machine.Operate.cs](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L660-L701)）。因此它是窗体加载后常驻的并行监控/持久化线程，不是 `Machine.Start` 内部按步骤等待的生产任务。

退出路径由 `BaseMachine.ExitApp` 设置机器状态为 `Stop`、将 `RuntimeProvider.ThreadFlag` 置为 `false` 并标记 `IsExitApp`（[BaseMachine.cs](../../trunk/AKRS.Galaxy2.Machine/BaseMachine.cs#L151-L165)）。`Machine.ExitSoftware` 另外负责保存数据、关闭输送加热器和硬件，但其关闭硬件异常被吞掉；源码没有显示等待后台线程结束的 `Join` 或超时确认（[Machine.Operate.cs](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L703-L736)）。

## 第五十五批复核：后台安全、激光、温度、耗材与真空分支

安全门配置启用且设备处于 `Working`、门未关闭时，后台检查直接调用 `Machine.Pause()`；重新关门后的自动恢复代码目前被注释，没有源码证据表明它会自动恢复到 `Working`（[Machine.Sustain.cs](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Sustain.cs#L272-L305)）。激光干涉尺未配置时检查通过；配置后环境传感器或算法状态失败会弹窗，`Abort` 调用 `ExitSoftware`，函数返回 `false`，外层 `StartLaserEncoderCheckTask` 随后调用 `Machine.Stop()`（[Machine.Sustain.cs](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Sustain.cs#L307-L320)、[Machine.Sustain.cs](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Sustain.cs#L323-L390)）。

输送加热配置启用、设备正在工作、加热器开启且温度报警时，`BackgroundTemperatureAlarm` 直接停机并弹出超温报警；加热成功后只更新 `HeatingComplete`、`HeatingCompleteTime` 和预热完成状态（[Machine.Operate.cs](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L449-L487)）。耗材扫描在过期且允许报警时弹窗：忽略保持工作并等待后续提醒，终止调用 `Machine.Stop()` 并清理耗材；即将到期只标记已提醒（[ConsumablesProgram.cs](../../trunk/AKRS.ZX2200/SupportFeature/Consumables/ConsumablesProgram.cs#L64-L114)）。

传感器扫描在离线模式直接返回；在线模式初始化并读取传感器。单个传感器无输入目前只有注释掉的报警代码，不会改变状态；但在设备工作、未配置输送、存在输送单元且真空检查失败时，会停机并弹出负压报警（[NeedScanSensorPool.cs](../../trunk/AKRS.ZX2200/SupportFeature/SensorCheckScan/NeedScanSensorPool.cs#L46-L92)）。

## 第五十六批复核：设备状态迁移与任务响应

`SetState` 只在新旧状态不同的时候更新单例 `MachineStateModel.MachineState`，并向 `StatisticsService.DbEntityBlockingCollection` 写入状态变更日志；它本身不停止线程、不释放信号，也不执行硬件动作（[Machine.StateRelated.cs](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.StateRelated.cs#L48-L68)）。初始状态模型默认是 `Stop`，状态模型同时保存工作模式、离线/空跑/补偿/单步等派生标志（[MachineStateModel.cs](../../trunk/AKRS.Galaxy2.Machine/Models/MachineStateModel.cs#L25-L93)）。

`Pause()` 只设置 `Pause` 状态；`Continue()` 在未配置安全门时直接恢复 `Working`，配置安全门时必须先确认门已关闭，并在恢复前把 S1/S2 的首次点胶标志置为真。`Stop()` 除设置 `Stop` 外，还清理报警框、设置报警器停止状态、退出单步模式、复位 Bond 需料信号、在线模式关闭上料需料信号、关闭顶针真空，并将焊后检测缺陷计数清零（[Machine.Operate.cs](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L311-L378)）。

`EmergencyStop()` 比普通停止多做并行轴停止，并显式调用 Dispense、Bond、Wafer 三个任务的中止接口；源码注释明确说明 Transport 线程没有对应结束处理，因此不能把急停描述成所有任务均已确认退出（[Machine.Operate.cs](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L380-L402)）。

任务响应并不完全一致：`Signal.WaitStart()` 遇到 `Stop` 立即返回 `false`，遇到 `Pause` 每 20ms 轮询阻塞，恢复到工作状态后返回 `true`（[Signal.cs](../../trunk/AKRS.Galaxy2.Machine/Models/Signal.cs#L198-L228)）。Bond、点胶、Transport 等主循环使用这一等待语义；但 Unloader 还通过 `IsWorking()` 作为外层循环条件、在 Pause 时每秒休眠，SlideFluxer 在特定防撞循环中自行检查 Pause。因此状态改变是全局共享的，具体停顿时机取决于每个任务当前所在的等待点（[UnloaderTask.cs](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/UnloaderTask.cs#L56-L73)、[SlideFluxerTask.cs](../../trunk/AKRS.ZX2200/BondSystem/Tasks/SlideFluxerTask.cs#L92-L119)）。

## 第五十七批复核：急停后的任务中止实现边界

三个急停调用的任务接口并不等价于“确认线程已结束”。点胶任务的 `AbortThread()` 直接对 `DispenseTask` 调用 `Dispose()`，没有取消令牌、等待完成或信号复位；如果任务引用为空，源码也没有空值保护（[DispenseWorkTask.cs](../../trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs#L189-L215)）。固晶任务的 `AbortThread()` 方法体为空，因此 `EmergencyStop()` 对 Bond 的这次调用没有源码可见的实际动作（[BondTask.cs](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L361-L384)）。

晶圆任务的 `AbortWaferSubThread()` 也只有被注释掉的旧线程 `Abort` 代码，没有对当前 `waferSubTask` 执行取消、Dispose 或等待（[WaferSubSystemTask.cs](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1373-L1437)）。Transport 没有对应的中止方法；`EmergencyStop()` 中只保留了注释，说明该线程结束方式尚未解决（[Machine.Operate.cs](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L383-L402)）。因此当前源码只能证明急停会停止轴并切换全局状态，不能证明所有生产 Task 均已终止或完成资源清理。

## 第五十八批复核：任务自然退出和异常清理

点胶任务在外层和动作循环都依赖 `Signal.WaitStart()`；来料信号失败时移动到安全位后直接返回，动作返回非 `Success/Retry` 时移动到安全位、调用 `Machine.Stop()` 后返回。该方法没有 `try/finally`，因此异常或外部中止时没有统一的收尾块（[DispenseWorkTask.cs](../../trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs#L63-L161)）。固晶任务同样以 `Signal.WaitStart()` 驱动循环，换吸嘴失败会 `Stop` 后返回，来料/补偿失败多处直接返回；当前 `DoWork` 片段没有统一 finally 资源清理（[BondTask.cs](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L98-L176)）。

晶圆任务的 `Dowork` 有外层 `try/catch`，异常时弹出“晶圆线程开启失败”，但该 catch 没有调用 `Machine.Stop()`、没有关闭真空或等待其他任务；正常停止主要依赖 `WaitStart()` 返回 `false`（[WaferSubSystemTask.cs](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L64-L83)、[WaferSubSystemTask.cs](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1421-L1425)）。翻转任务在等待晶圆允许取料信号返回 `false` 时直接退出，入口和循环也没有 finally（[FlipTask.cs](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/FlipTask.cs#L55-L104)）。

Transport 的各段任务通常在自己的 `try/catch` 中记录异常并返回，停止状态通过 `Signal.WaitStart()` 使循环结束；Loader/Unloader 则以 `IsWorking()` 作为外层条件，异常 catch 记录后退出。当前证据没有显示统一的 Transport 任务汇合、取消令牌或结束等待，因此“状态变为 Stop”与“所有搬运 Task 已完成清理”仍是两个不同结论（[TransportTask.cs](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L117-L170)、[LoaderTask.cs](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/LoaderTask.cs#L64-L124)、[UnloaderTask.cs](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/UnloaderTask.cs#L56-L125)）。

## 第五十九批复核：下一次启动前的状态复位边界

`PrepareMachineReadyToStart` 在每次启动前调用 `ResetMachineSignal`。该复位覆盖 Bond 需料、晶圆允许取料、各段搬运完成/允许移动、取料成功、翻转取料、蘸胶允许/完成等进程内信号；但它不是任务取消，也不等待旧 Task 退出（[Machine.Operate.cs](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L185-L190)、[Machine.Operate.cs](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L130-L163)）。

`Stop()` 额外关闭顶针真空、关闭在线上料需料输出并清零焊后缺陷计数，但没有统一关闭吸嘴真空、清空所有 `TransportUnit` 或把所有流道段状态恢复为 `NoMaterial`。相反，正常流程在 TransportTask 中会创建新的 S1/S2 `TransportUnit` 并设置段状态为 `HasMaterial`；Bond 完成后的特定手动移除分支才会显式将 Bond `TransportUnit` 置空并设置 `NoMaterial`（[Machine.Operate.cs](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L347-L377)、[TransportTask.cs](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L781-L796)、[BondTask.cs](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L466-L481)）。因此下一次启动的确定性来源主要是信号复位和就绪检查；物料对象、流道状态、线程生命周期需要由各模块后续逻辑分别处理，不能统一假设已经清空。

## 第六十批复核：就绪检查对残留状态的处理范围

`CheckOperatingEnvironment` 的顺序是：Wafer 就绪 → S2 自检 → S1 就绪 → 产品/TransportUnit 就绪 → 焊点辅助完成 → 制程就绪；任何一步返回 `false` 都直接拒绝启动，成功才返回 `true`（[Machine.Operate.cs](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L89-L128)）。这是一条门禁链，不是统一清理链。

对残留载具，TransportTask 在启动时会按配置和首次启动标志检查各段 `SubSectionState == HasMaterial`：部分分支弹窗询问是否继续，选择停止会调用 `Machine.Stop()`；配置允许重启或用户确认继续时则设置完成信号让对应工位继续处理（[TransportTask.cs](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L178-L250)、[TransportTask.cs](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L480-L511)）。源码因此证明“残留物料可被识别并走人工决策”，但没有证明就绪检查会自动把物料搬走或清空。

部分域的就绪检查会执行物理动作，例如 Wafer 检查中移动 Bond Z 到安全位、复位顶针气缸并关闭真空；这属于检查前准备，失败时由异常处理返回 `false`，没有通用事务回滚（[WaferSystemDomain.cs](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/WaferSystemDomain.cs#L159-L410)）。因此启动门禁同时包含读状态、提示和有限的物理准备，但不等价于完整的停机清场。

## 第六十一批复核：S1、S2、Wafer 就绪检查分支

S1 未配置时直接返回 `true`；已配置时依次检查点胶头、预点胶板/预点胶胶型（仅在预点胶模式开启时）和点胶材料。预点胶示教未完成、胶型为空或找不到都会弹窗并返回 `false`，材料检查失败则直接返回 `false`（[System1Domain.cs](../../trunk/AKRS.ZX2200/DispenseSystem/Models/System1Domain.cs#L481-L528)）。这里没有物理复位动作。

S2 检查一开始会打开焊头真空；若关闭自检开关则立即返回 `true`。开启自检时依次执行 Bond 程序和动作节点自检，再检查 ULM、焊头、吸嘴架、力控、温漂/取片补偿点位及工具架配置等参数，失败均以弹窗或子检查结果返回 `false`。因此“关闭自检”会跳过这些参数门禁，但不会跳过打开焊头真空这一前置动作（[System2Domain.cs](../../trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs#L594-L709)）。

Wafer 检查在任何配置判断前先设置运行标志、移动 Bond Z 到安全位、复位顶针气缸并关闭顶针真空。在线模式下再检查料盒配置/示教、顶针和芯片示教、搜晶范围、晶圆半径、力控与同步顶针组合、翻转台与 Bond 相机冲突、纠偏相机类型等；半径异常允许用户选择继续或终止，其余冲突大多直接弹窗返回 `false`（[WaferSystemDomain.cs](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/WaferSystemDomain.cs#L159-L278)）。这说明 Wafer 就绪检查既有硬件动作，也有会改变用户决策路径的交互分支。

## 第六十二批复核：S2 工具状态与工艺步骤门禁

工具检测开启时，S2 同时读取焊头逻辑记忆和物理检测结果：物理有吸嘴但逻辑无吸嘴直接报警失败；物理无吸嘴但逻辑有吸嘴时，用户可确认清空当前吸嘴名称，或选择终止。若运行时记忆显示焊头有料，弹窗允许抛料（调用 `ThrowAction`）或忽略；随后还要通过预点胶动作节点的 `IsAlarm` 检查（[System2Domain.cs](../../trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs#L711-L770)）。这些分支会修改焊头记忆或执行抛料，不能视为纯配置读取。

`ProcessDomain.CheckIsReady` 在翻转模组启用时限制启用的非空组件步骤数量最多为 1；随后逐步骤检查名称非空、序号非 0、焊点非空且存在于焊点列表（异性载具分支的焊点存在性校验被注释），并要求组件、缺陷、胶量功能三者恰好选择一个。任一约束失败弹窗并返回 `false`，通过后才允许进入产品和域级就绪链（[ProcessDomain.cs](../../trunk/AKRS.ZX2200/Main/Machine/Process/ProcessDomain.cs#L179-L252)）。

## 第六十三批复核：产品、焊点与动作节点三层依赖

产品层 `IsTransportUnitReady` 只检查 TransportUnit 配置是否完成示教；未完成时弹窗并返回 `false`，没有硬件动作。焊点层 `IsBpAssistanceFinish` 遍历所有焊点，只要有一个未完成示教就弹窗并返回 `false`（[ProductConfiguration.cs](../../trunk/AKRS.ZX2200/TransportUnitSystem/ProductConfiguration.cs#L89-L99)、[BondPositionConfig.cs](../../trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/BondPositionConfig.cs#L26-L38)）。

S2 动作节点服务的自检要求：至少存在一个 S2 步骤；每一步必须关联焊点，焊点必须存在于当前配方，组件名称不能为空且必须能从载具配置找到；若组件使用上视相机则上视拍照位不能为空，使用 Bond 相机则下视拍照位不能为空。任一失败弹窗并返回 `false`，该自检本身不执行运动或物料动作（[System2ActionNodesService.cs](../../trunk/AKRS.ZX2200/DispenseSystem/Services/System2ActionNodesService.cs#L818-L923)）。

`S2ActionNodeController.SelfCheck` 是另一层较窄的步骤/焊点检查：没有步骤直接失败；普通载具逐步验证焊点非空且仍存在，异性载具跳过这一段焊点存在性判断。通过后只返回 `true`，步骤注入在后续 `InjectSteps` 中才把步骤写入 TransportUnit 内各焊点的剩余步骤表（[S2ActionNodeController.cs](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L1359-L1432)）。

## 第六十四批复核：Machine.Start 的调用顺序与首个工作动作

`Machine.Start` 先执行 `PrepareMachineReadyToStart`；成功后同步把全局状态设为 `Working`，然后按固定调用顺序创建任务：Transport、Wafer、按配置启用的 S1 Dispense、动作节点 `Init`、Bond、按配置启用的 SlideFluxer、按配置启用的 Flip，最后检查并打开 Waffle/StaticWaffle 真空（补偿模式跳过 Transport、Wafer、S1、SlideFluxer、Flip，但仍初始化并启动 Bond）（[Machine.Operate.cs](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L259-L309)）。这些 `Start` 多数只创建后台 Task，因此调用顺序不等于实际动作顺序。

首个工作动作也不一致：Wafer `Start` 在创建 Task 前先执行 `Block.StartInit`、清空上一颗芯片名并设置 `Working`；Wafer Task 进入后先等待 `Signal.WaitStart` 和 Bond 需料信号。Dispense、Bond、SlideFluxer、Flip 的 `DoWork` 入口先分别初始化动作/运行信息、回安全位或回零，再进入 `WaitStart`；Transport `Start` 会按上下料配置创建多个独立 Task。由此可确认：状态切换和 Task 创建发生在 `Machine.Start` 中，而具体硬件首动作由各 Task 调度器并发决定（[WaferSubSystemTask.cs](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1373-L1394)、[DispenseWorkTask.cs](../../trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs#L63-L72)、[BondTask.cs](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L100-L114)、[SlideFluxerTask.cs](../../trunk/AKRS.ZX2200/BondSystem/Tasks/SlideFluxerTask.cs#L92-L99)、[FlipTask.cs](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/FlipTask.cs#L57-L63)）。

## 第六十五批复核：第一片产品的信号握手路径

Transport 配置启用时，Bond 首先在 `GetIncomingSignal` 等待 `TransferToBondFinishedSignal`；该信号由 Transport 在产品完成进入 Bond 段后设置。若未配置 Transport，Bond 改为检查/等待本地 Bond `TransportUnit`，必要时弹窗要求放入产品（[BondTask.cs](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L390-L446)）。

有 S1 时，Transport 把产品送入点胶段并设置 `TransferToDispense1FinishedSignal`；点胶动作完成后设置 `AllowDispenseTransferToBondSignal`，Transport 收到后继续把产品送往 Bond，并最终设置 `TransferToBondFinishedSignal`。无 S1 配置时，Transport 在前段完成后直接设置 `AllowDispenseTransferToBondSignal`（[TransportTask.cs](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L281-L299)、[TransportTask.cs](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L817-L833)、[DispenseWorkTask.cs](../../trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs#L169-L180)）。

Bond/取晶握手随后由当前组件决定：翻转流程会把下一组件名称写入 Wafer 任务并设置 `IsBondNeedChipSignal`；Wafer 收到后搜晶/换片，完成后复位需料信号并设置 `IsWaferAllowPickSignal`，翻转任务再继续取料。非翻转路径同样由取料节点等待 `WaitAllowBondPickSignal`，成功取料后再通过 `IsBondPickSucceedSignal` 等信号让后续固晶继续（[FlipTask.cs](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/FlipTask.cs#L98-L145)、[WaferSubSystemTask.cs](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L78-L85)、[WaferSubSystemTask.cs](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L319-L328)）。

固晶完成后仅在设备不是 `Stop` 时设置 `AllowBondTransferToWaitingUnloadSignal`，Transport 收到后才把 Bond 段转入等待下料；因此第一片产品的关键链路是“Transport 入段 →（可选 S1）→ Bond 入段 → Wafer 需料/允许取料 → 取料成功 → Bond → 允许下料”，每一步由信号而非 `Start` 调用返回值推进（[BondTask.cs](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L448-L458)、[TransportTask.cs](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L858-L878)）。

## 第六十六批复核：Bond 到下料的分支链

`transferBondToWaitingUnloadTask` 循环调用 `TransferBondToWaitingUnload`；控制器先要求 Bond 段为 `HasMaterial`、等待段为 `NoMaterial`，非手动模式再等待 Bond 完成信号。成功时执行夹紧、Bond/等待段皮带传送和传感器确认，最后把 TransportUnit/段状态转移到等待区；`NoStart` 会回到下一轮，`Abort`/异常结束该线程（[TransportTask.cs](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L555-L599)、[TransportController.cs](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L1531-L1562)）。

等待区下料分支按 `LoadConfiguration` 选择：`None` 直接不创建后续下料任务；非 `LoaderBin` 创建等待区到出料皮带任务；`LoaderBin` 创建等待区到下料仓任务。下料仓分支先等待 `UnloaderAllowPushSignal`，调用 `TransferWaitingUnloadToUnloadBin` 后复位该信号，再设置 `AllowUnloaderMoveSignal`；`NoStart` 延时重试，`Abort` 退出（[TransportTask.cs](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L602-L719)）。

非 `LoaderBin` 路径调用 `TransferWaitingUnloadToUnloadBelt`，其结果按 `NoStart/Success/Abort/Exception` 分支处理；若配置在线自动下料，还会继续运行 `TransferUnloadBeltToAutoUnloader` 任务，将出料皮带交给送板机。各段任务独立 `Task.Run`，没有统一等待或汇合（[TransportTask.cs](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L609-L661)、[TransportTask.cs](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L721-L760)）。

## 第六十七批复核：下料控制器的状态迁移与回滚

Bond→WaitingUnload 成功时把 WaitingUnload 的 `TransportUnit` 接收为当前产品，Bond 段状态改为 `NoMaterial`、Bond `TransportUnit` 置空，两段传输状态均置为 `Ready` 并保存；传感器未确认时把相应传输状态置为 `Alarm`，用户可 `Retry/Abort/Ignore`，异常返回 `Exception`（[TransportController.cs](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L1531-L1815)）。

WaitingUnload→UnloadBelt 先检查等待区和卸料区传感器/状态，传送卡料时两段状态置 `Alarm`，支持重试、终止或忽略。成功后把 `TransportUnit` 从 WaitingUnload 转移到 Unloading，等待段改为 `NoMaterial`、卸料段改为 `HasMaterial`，两段状态恢复 `Ready` 并保存；异常路径只把等待段状态恢复为进入前的临时值，没有统一恢复所有段或回滚硬件动作（[TransportController.cs](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L1816-L2065)）。

WaitingUnload→UnloadBin 还包含皮带传送、推杆缩回和推料动作。等待区物料未离开、推杆动作失败或传感器仍有料时进入报警；重试回到标签为 `retry` 的位置，忽略可继续部分流程，终止返回 `Abort`。成功后清空 WaitingUnload `TransportUnit`、设置等待段 `NoMaterial`、卸料段 `HasMaterial`、传输状态 `Ready` 并保存；异常同样只恢复等待段原状态（[TransportController.cs](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L2066-L2295)）。

## 第六十八批复核：自动送板与上料载具检查

`TransferUnloadBeltToAutoUnloader` 只在 Unloading 段为 `HasMaterial`、传输状态不是 `Transfering` 且自动送板机需要物料时启动。它检查出料皮带物料传感器和自动送板机状态，传送期间遇到传感器异常会报警并按 `Retry/Abort/Ignore` 分支处理；成功后清空 Unloading `TransportUnit`，设置 Unloading 为 `NoMaterial`、传输状态为 `Ready` 并保存。该方法异常返回 `Exception`，没有显示完整的失败回滚（[TransportController.cs](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L2292-L2453)）。

`CheckCarrierBeforeLoaderMove` 根据上下料配置检查入口/出口传感器和载具状态；检测到传感器不符合预期时进入报警对话，支持重试或终止，终止分支返回 `false`，通过才允许 Loader 移动。它是上料动作前置门禁，不负责创建或清空完整 `TransportUnit`（[TransportController.cs](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L2454-L2525)）。

因此自动下料链的最终状态是“Unloading 清空并保存”，而上料检查的输出只是布尔门禁；上下料两端之间没有统一事务或队列确认，仍由各自 Task 和传感器循环推进。
