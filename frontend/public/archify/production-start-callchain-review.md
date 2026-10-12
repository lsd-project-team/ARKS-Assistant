# 自动生产启动调用链复核（2026-09-28）

> 进度说明（2026-09-28）：本文保留分批分析过程。启动图 12 个节点及 10 条关系的最新限定范围验收，以 [启动章节语义复核](startup-semantic-revalidation.md) 和当前台账为准；旧文中的阶段性待办不代表最新计数。

范围：读取当前方法体后的静态控制流复核。以下是调用顺序，不是线程运行顺序。未展开的被调方法不算已验收。

|调用方及位置|调用/条件|被调入口或待查内容|
|---|---|---|
|[BarItemStart_ItemClick:74–85](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L74)|配方提示配置启用时弹窗；Cancel 直接返回|finally 仍恢复 Enabled|
|[BarItemStart_ItemClick:99](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L99)|调用 Machine.Start；同步异常在 101–104 调 Stop 并提示|[Machine.Start:261](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L261)|
|[Machine.Start:266–272](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L266)|PrepareMachineReadyToStart 为 false 则 return；否则 SetState(Working)|准备检查及 SetState 内部需独立复核|
|[Machine.Start:274–277](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L274)|非补偿模式：Transport.StartTask，随后 WaferSubSystemTask.Start|[Transport.StartTask:84](../../trunk/AKRS.ZX2200/TransportSystem/Models/TransportDomain.cs#L84)；Wafer.Start:1373 尚待展开|
|[Machine.Start:280–284](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L280)|已配 S1 且非补偿模式：DispenseWorkTask.Start|Start 继承/实现与工作循环待查|
|[Machine.Start:289–290](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L289)|ActionNodesService.Init 后 BondTask.Start；这里没有补偿模式条件|排序及任务入口待查|
|[Machine.Start:291–303](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L291)|胶盘/翻转分别按硬件配置且非补偿模式启动|两个任务的启动实现与信号待查|
|[Machine.Start:307–308](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L307)|最后调用两种 Waffle 真空检查开启方法|配置和硬件实现待查|

## 输送模块入口的具体分支

[TransportDomain.cs:84–140](../../trunk/AKRS.ZX2200/TransportSystem/Models/TransportDomain.cs#L84)：

- 未配置输送时直接返回；已配置时先 TransportModule.Init。
- DryCycle 调 StartDryRun，跳过正常生产分支。
- 正常分支 CheckCarrierBeforeLoaderMove 返回 false：调用 Machine.Stop，然后返回。
- 在线上料配置先关闭要料信号；反向搜索配置下刷新 TransportUnit；随后 MapMaterial。
- LoaderBin 配置下依次启动 LoaderTask 和 UnloaderTask；随后启动 transportTask。
- catch 记录日志并显示错误，没有重新 throw。

## 不可省略的控制流差异

Machine.Start 在调用 void StartTask 后，没有读取启动成功值，也没有立即检查 Stop 状态。因此 StartTask 内检查失败、调用 Stop 后正常返回时，调用方仍执行后续 Wafer.Start 等语句。StartTask 内被 catch 捕获的异常同样不会直接进入按钮的 catch。后续任务是否依据 Stop 状态退出，尚需追踪任务实现；不能推断设备继续运动或一定停住。

## 当前进度与下一步

已复核：按钮方法、Machine.Start 方法、TransportDomain.StartTask 方法中的上述分支。
未完成：任务基类 Start、Wafer.Start、各工作循环、SetState 的副作用、配置加载来源、图关系与本记录的逐条绑定。
该记录不将现有 103 条流程箭头自动升级为已验证调用关系。

## 任务启动与状态门控（2026-09-28 追加）

|模块|已读实现及结论|仍待验证|
|---|---|---|
|WaferSubSystem|[Start:1373–1399](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1373)：任务为空或 Status 不为 Running 时先 StartInit，再将状态置 Working，随后 StartNew(Dowork)；否则也置 Working|StartInit 内部、初始化失败与并发时序|
|BondSystem|[Start:361–377](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L361)：任务为空或不为 Running 才 StartNew(DoWork)，方法正常返回 true；[AbortThread:382–384](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L382) 为空方法|不能把 true 当作加工完成，也不能把 AbortThread 当作取消成功|
|DispenseSystem|[Start:189–207](../../trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs#L189)：相同任务状态判断后 StartNew(DoWork)，正常返回 true；[AbortThread:212–215](../../trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs#L212) 调用 Dispose|Dispose 与任务生命周期、异常传播需单独分析，不等于已证明强制终止|
|Main|[SetState:52–68](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.StateRelated.cs#L52)：状态变化时赋值并将日志实体加入统计队列，没有在该方法体里遍历取消任务|日志队列消费者和其他状态订阅者|
|Galaxy2.Machine|[Signal.WaitStart:202–228](../../trunk/AKRS.Galaxy2.Machine/Models/Signal.cs#L202)：入口 Stop 返回 false；Pause 循环检查 Stop 并每轮 sleep 20ms；离开循环返回 true|暂停到停止的并发读取窗口及信号其他重载|

三个任务的循环分别在 BondTask.cs:109、DispenseWorkTask.cs:69、WaferSubSystemTask.cs:69 调用 Signal.WaitStart。它们有各自启动方法，不能假定来自共同任务基类。

### 上一轮疑点的进一步结论

Transport.StartTask 内 Stop 后返回，外层继续调用 Wafer.Start；当该方法正常执行到 SetState 时，会再次置 Working。源码中确有这条可达调用路径。是否发生于现场、哪些轴已经动作、任务是否完成不能由此断言。图中应表达“局部失败返回与外层继续启动”，不能归纳为全局 fail-fast。

### 状态等待的具体边界

WaitStart 并不是“只在 Working 返回 true”：其他非 Stop、非 Pause 状态也可返回 true。Pause 循环退出后没有再次检查 Stop；并发状态在循环条件读取前改变时存在需要运行验证的窗口。这里仅记录代码控制流，不声称已经复现故障。

## 信号等待与退出实现（2026-09-28 追加）

源码：[Signal.cs:116–195](../../trunk/AKRS.Galaxy2.Machine/Models/Signal.cs#L116)。

|入口|实际执行|限制及待查|
|---|---|---|
|Wait()|先 WaitStart；false 立即返回；循环检查 Stop、sleep 5ms，再 WaitOne(recycleTime)，收到事件后结束循环；AutoReset 时更新 State=ReSet|入口之后进入 Pause 不会在该循环重新调用 WaitStart；收到事件后的状态再次变化未检查|
|Wait(int outTime)|先 WaitStart，再检查 Stop，最后只调用一次 WaitOne(recycleTime)|outTime 没有被使用；没有无参版的循环和 State 更新。不能按形参声称等待指定时长|
|WaitSingleStep()|循环检查 IsSingleStepWork；false 返回 false；sleep 5ms 后 WaitOne(recycleTime)；AutoReset 时更新 State|没有直接读取 Stop/Pause；Machine.Stop 会清除单步标志，但实际退出时机取决于下一次读取|

### 中止方法不等于已中止线程

[WaferSubSystemTask.cs:1431–1437](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1431) 的 AbortWaferSubThread 只有被注释的旧线程实现，没有执行语句。结合 Bond 空 AbortThread 和点胶 Dispose，不能把 EmergencyStop 中三个方法调用画成三个已完成的线程取消动作。

下一步：寻找各等待重载的实际调用者，检查 false 是按超时、停止还是动作失败处理；随后将已确认关系和修正后的说明同步到图规格、HTML 与台账。以上是当前源码控制流事实，未验证设备运行行为。

## 实际等待调用方（2026-09-28）

- [BondTask.GetIncomingSignal:390–438](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L390)：补偿模式直接 true；配置输送则返回 TransferToBondFinishedSignal.Wait() 的结果；无输送且无载具时提示人工放料，映射仍为空或选择停止会调用 Stop 并 false。不能概括为所有模式都等待来料信号。
- [BondTask.DoWork:151–157](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L151)：GetIncomingSignal false 后直接 return；该分支本身不再调用 Stop，也不是 Retry。
- [WaferSubSystemTask.Dowork:68–83](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L68)：需求 Wait false 后 goto WaitBondNeed，重新经过 while(Signal.WaitStart())。退出还是继续取决于重新读取的设备状态，不能画成无条件重新供料。
- [System2Domain.WaitSingleStep:777–788](../../trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs#L777) 与 [System1Domain.WaitSingleStep:534–545](../../trunk/AKRS.ZX2200/DispenseSystem/Models/System1Domain.cs#L534)：非单步模式直接 true；单步模式才调用底层等待。底层 Signal.WaitSingleStep 在非单步时 false，包装方法却在非单步时 true，分析必须区分调用层次。
- [BondTask.SendAway:447–459](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L447)：配置输送且 IsStop 为 false 才 Set AllowBondTransferToWaitingUnloadSignal；停止分支只记录日志，不发放行信号。

尚未建立 Wait(int) 的实际生产调用证据；不能仅凭重载存在就把超时参数问题归入所有生产路径。SignalPool 实际位置是 trunk/AKRS.Galaxy2.Machine/Models/SignalPool.cs，旧审计中 Main/Machine/SignalPool.cs 路径应纠正。
