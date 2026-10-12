# 料仓上下料：实际执行步骤与信号闭环

2026-09-28。限定源码复核；未启动设备、未修改生产源码。

## 执行摘要

流道已配置且非DryCycle，启动前检查通过并完成MapMaterial后，LoaderBin模式先调用LoaderTask.Start和UnloaderTask.Start，再调用transportTask.Start。这些Start创建并行Task，不表示先完成上料再开始下料。Enable=false或DryCycle使各料仓任务直接返回；仅以Task为null或Status不等于Running作为创建条件，不构成严格并发单例保障。

|阶段|上料仓|下料仓|
|---|---|---|
|首次定位|MoveToCurrentPlaceLayer，定位当前层|MoveToCurrentPlaceLayer，定位当前层|
|允许推料|Set LoaderAllowPushSignal|Set UnloaderAllowPushSignal|
|输送任务消费|Wait后TransferLoadBinToDispense|Wait后TransferWaitingUnloadToUnloadBin|
|成功更新|发TransferToDispense1FinishedSignal；PrepareFeeding=false|控制器清等待区TU、改两段状态；AddCurPlaceLayer后Save|
|交接移动权|ReSet允许推料；Set AllowLoaderMoveSignal|等待200ms；ReSet允许推料；Set AllowUnloaderMoveSignal|
|料仓继续|Wait移动信号；MoveToNextPlaceLayer，层号加1后Save|Wait移动信号；再次MoveToCurrentPlaceLayer，使用控制器已加1的层号|
|下一轮|再次Set允许推料|再次Set允许推料|

上料输送并非只在Success时交接：None也走复位/允许移动路径，但不发该Success分支中的点胶来料信号。NoStart睡眠500ms并continue，保留允许推料；Abort和Exception调用Stop后return。下料输送NoStart、Abort、Exception处理相同，Success进入交接；未匹配的枚举也会落到交接语句，不能称穷尽处理。上料还有ContinuousFeeding=false的1000ms等待，以及首次已有料的分支，见完整任务快照。

## 重试与料盒边界

- 当前层定位：有盒且未越界时定位料盒/层位；A盒耗尽或满层切换下一盒、重置层位再Reload；另一盒耗尽/满层提示人工换仓或停止。换仓重置后Reload；Abort返回Abort。
- 未感应料盒：Retry回Reload；Ignore切盒并重置后Reload；Abort返回Abort。已读这些方法没有重试次数上限；并不代表底层动作无超时。
- 上料下一层通常定位CurPlaceLayer+1、递增并Save；A盒越界设置B盒及层号0再Reload；另一盒用尽选择换仓后ResetLoader并定位当前层，直接Success。它与首次定位的Reload处理并不完全相同。
- 层位控制器已读方法显式返回Success或Abort。任务switch虽只列这两项，不应将其他返回值实际可达当成已经证实的缺陷。底层抛异常则由任务catch弹窗结束。

## 等待、暂停和失败边界

- 允许推料信号是ManualReset；允许料仓移动信号是AutoReset，初始化均false、recycleTime为100。100是每轮WaitOne等待参数，不是整条握手总超时。
- 无参数Wait先调用WaitStart；进入事件循环后检查Stop并Sleep(5)、WaitOne(recycleTime)，无总超时；AutoReset成功时将显示State改ReSet。WaitStart在Pause时等待，不能据此声称整个事件等待期持续拦截暂停：后续循环只检查Stop。
- 料仓任务外层是while(IsWorking())，IsWorking严格等于Working。若在循环边界观察到Pause，任务会退出；若已在WaitStart可能等恢复；若暂停发生于事件等待期间，可能继续消费事件。具体时序需验证，不能宣称已复现。
- 下料任务另有IsPause/Sleep(1000)/continue，但位于IsWorking循环体内；不能把它解释成稳定的全程暂停保障。
- Wait返回false时任务直接return；层位返回Abort时调用Machine.Stop并return。四个任务catch均只弹窗，在所读catch内没有Stop或重试；不是全项目异常统一停止。
- 下料控制器成功路径先改TU引用和多个状态、增加层号再Save。异常catch只显式恢复等待区SubSectionState、记录/弹窗并返回Exception；不能将此描述为所有内存与设备动作的完整回滚。

## 待验证及下一步

- 输送控制器前半段的传感器等待、推杆/皮带内部安全条件和所有人工选择分支。
- MoveToCurrentBin、MoveToTabletLevel及ResetLoader/ResetUnloader的下层运动、存储和失败恢复契约。
- 启动时信号重置与Stop/Pause恢复的完整跨线程时序，重复Start竞争及任务收集/退出。
- 在隔离环境验证暂停发生于循环边界、WaitStart、WaitOne三个时刻，以及保存失败后的层号与TU状态；本轮没有运行复现。

## 精确源码依据

- [StartTask — trunk/AKRS.ZX2200/TransportSystem/Models/TransportDomain.cs:84](../../trunk/AKRS.ZX2200/TransportSystem/Models/TransportDomain.cs#L84)
- [LoaderTask.Start — trunk/AKRS.ZX2200/TransportSystem/Tasks/LoaderTask.cs:49](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/LoaderTask.cs#L49)
- [UnloaderTask.Start — trunk/AKRS.ZX2200/TransportSystem/Tasks/UnloaderTask.cs:41](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/UnloaderTask.cs#L41)
- [料仓到点胶任务 — trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:314](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L314)
- [等待区到下料仓任务 — trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:664](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L664)
- [MoveToCurrentPlaceLayer — trunk/AKRS.ZX2200/TransportSystem/Controllers/LoaderBinController.cs:449](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/LoaderBinController.cs#L449)
- [MoveToNextPlaceLayer — trunk/AKRS.ZX2200/TransportSystem/Controllers/LoaderBinController.cs:542](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/LoaderBinController.cs#L542)
- [MoveToCurrentPlaceLayer — trunk/AKRS.ZX2200/TransportSystem/Controllers/UnLoaderBinController.cs:402](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/UnLoaderBinController.cs#L402)
- [层号修改 — trunk/AKRS.ZX2200/TransportSystem/Controllers/UnLoaderBinController.cs:145](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/UnLoaderBinController.cs#L145)
- [下料完成和异常出口 — trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs:2240](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L2240)
- [IsWorking and IsPause — trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.StateRelated.cs:25](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.StateRelated.cs#L25)
- [Signal.Wait — trunk/AKRS.Galaxy2.Machine/Models/Signal.cs:116](../../trunk/AKRS.Galaxy2.Machine/Models/Signal.cs#L116)
- [Signal.WaitStart — trunk/AKRS.Galaxy2.Machine/Models/Signal.cs:202](../../trunk/AKRS.Galaxy2.Machine/Models/Signal.cs#L202)
- [上料信号类型 — trunk/AKRS.Galaxy2.Machine/Models/SignalPool.cs:69](../../trunk/AKRS.Galaxy2.Machine/Models/SignalPool.cs#L69)
- [下料信号类型 — trunk/AKRS.Galaxy2.Machine/Models/SignalPool.cs:114](../../trunk/AKRS.Galaxy2.Machine/Models/SignalPool.cs#L114)
