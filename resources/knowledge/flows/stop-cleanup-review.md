# 停止、急停与退出软件：源码清理链复核

日期：2026-09-28。目标：明确自动生产遇到停止时实际调用了什么，避免把设备状态、线程退出、轴停止和输出关闭混为一谈。范围是下列方法体及直接调用；没有进行设备运行或安全认证测试。

[对应交互图](stop-cleanup-workflow.html) · [可编辑图规范](stop-cleanup-workflow.archify.json)

## 工作步骤摘要

普通 Stop 先改变状态，再发起弹窗清理、设置停止报警、关闭单步模式、复位需晶信号、按条件关闭上料要料信号、关闭顶针吹气/真空，最后清零焊后缺陷计数。EmergencyStop 先遍历轴调用 StopMove，再调用普通 Stop，随后调用若干 Abort 方法。ExitSoftware 则属于退出应用的保存和硬件关闭路径，不能用它替代生产 Stop 的行为证据。

## 1. 普通 Stop 的实际顺序

[Machine.Operate.cs347–378](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L347)：

|顺序|调用/条件|已确认含义|
|---|---|---|
|1|SetState(Stop)|更改状态并记录状态变更，不等于等待任务退出|
|2|AKRSMessageBoxExt.ClearMessageBox|对登记的弹窗 BeginInvoke 隐藏、设 Abort、Dispose；清空登记表。此处没有等待所有 UI 回调完成|
|3|SetStopStateAlarm|非离线时查找 Alarmer 并调用 SetStopState；不是关闭全部电气输出|
|4|IsSingleStepWork=false|退出单步模式|
|5|IsBondNeedChipSignal.ReSet|复位需晶信号；没有在这里复位所有信号|
|6|仅 LoadConfiguration==Online|SetLoadingTableNeedTabletSignal(false)；此处条件不包含 OnlineWithAutoLoader|
|7|CloseEjectionTableVacuum|实际分别 ResetCyc 顶针台吹气、顶针台真空输出|
|8|遍历 PostBondInspections|CurrentDefectNumber=0|

Stop 方法体没有统一 try/finally 或逐项 catch；若前面的调用抛异常，不能声称后续所有清理必然执行。没有直接出现 HotBlower 关闭、轴遍历停止、Task.Wait/Join 或取消令牌操作。状态模型属性已核实为自动属性，外围监控仍需独立追踪，因此这里只能确认**该方法的显式调用范围**，不能推出硬件最终状态。

### 状态与清窗的具体实现

- [SetState52–68](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.StateRelated.cs#L52)：仅当新旧状态不同，创建变更记录，赋 MachineStateModel.MachineState，再把记录放入 StatisticsService.DbEntityBlockingCollection。[MachineStateModel87](../../trunk/AKRS.Galaxy2.Machine/Models/MachineStateModel.cs#L87) 是 get/set 自动属性，没有 setter 内隐藏的硬件清理回调；ZX2200 引用该源码项目：[csproj4106](../../trunk/AKRS.ZX2200/AKRS.ZX2200.csproj#L4106)。外围线程可能观察状态，但不能假定已全部完成清理。
- [ClearMessageBox42–55](../../trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/AKRSMessageBoxExt.cs#L42)：遍历 msgBoxDict，逐窗 BeginInvoke 清理，然后清空字典。只针对该字典内登记的弹窗；不能泛化为关闭全部向导、所有窗口，亦不能把投递成功当作回调执行完毕。
- [SetStopStateAlarm183–195](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.cs#L183)：离线返回；非离线按查询结果调用首个报警器。源码判断为 `hardwaresByType == null || hardwaresByType.Any()`，随后访问 `[0]`；若查询实际返回 null，存在访问失败路径。未验证硬件仓库是否会返回 null，不能当作已复现故障。
- [CloseEjectionTableVacuum340–344](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/EjectController.cs#L340) 两个调用都是无 Sensor 的 ResetCyc，完成边界见 [料库复核第6节](magazine-transfer-review.md)。它关闭的是顶针吹气/真空，不是热吹。

## 2. EmergencyStop 不等于所有任务已退出

[Machine.Operate.cs383–402](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L383) 依次：

1. 获取全部 Axis，以 Parallel.ForEach 调用 axis.StopMove(false,true)。底层停止语义与驱动实现尚未验证。
2. 调用 Machine.Stop。
3. 调用 DispenseWorkTask.AbortThread、BondTask.AbortThread、WaferSubSystemTask.AbortWaferSubThread。调用方没有读取退出确认，也没有统一等待退出；轴停止或 Stop 异常时，后续语句未必执行。

[AbortWaferSubThread1431–1437](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1431) 方法体只有旧 Thread.Abort 的注释，当前没有实际终止操作。[BondTask.AbortThread382–384](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L382) 也是空方法。[DispenseWorkTask.AbortThread212–215](../../trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs#L212) 仅调用 DispenseTask.Dispose，没有取消令牌、等待退出或显式中断逻辑。不能把这些调用箭头标成“任务已强制结束”。Dispose 的运行前提及异常需结合运行时验证；本次未执行生产任务。

## 3. 供晶任务的生命周期边界

[WaferSubSystemTask.Start1373–1426](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1373)：任务为空或 Status!=Running 时，StartInit、清 PreviousNeedChipName、SetState(Working)，再 Task.Factory.StartNew(Dowork,CancellationToken.None,LongRunning,Default)。已有 Running 任务时只 SetState(Working)。该判断不是“所有非终态均复用”；本轮不做并发重入实测。

Start 的 catch 仅提示错误，没有 rethrow，也没有在这里恢复 Stop。供晶循环中各个 WaitStart、信号 Wait、StopSearch 负责自己的退出/抛错逻辑；已进入的气缸等待、文件操作、UI 向导或热吹 Sleep 不能单凭外层检查证明立刻退出。参见 [供晶握手复核](wafer-bond-handshake-review.md) 与 [换片动作复核](magazine-transfer-review.md)。

## 4. 重启门控与退出软件：ExitSoftware 是独立硬件关闭路径

### 停止后允许重启的检查范围

[IsAllowTaskClosed201–262](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.cs#L201) 重建任务列表：按配置加 S1 点胶，再加供晶、Bond、胶盘、翻转、多段输送及上下料仓任务。只要其中 `task?.Status == TaskStatus.Running` 则返回 false，其余情况返回 true。它没有检查每个任务均为终态，也没有 Wait/Join，因此不能等价为“全部完成退出”。未枚举的内部异步工作也不由该列表证明已完成。

[启动准备207–211](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L207) 据此决定是否提示“部分模组仍在工作”并拒绝启动；[ChangeUiByState382–398](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.UIState.cs#L382) 在 Stop、界面禁用且正在停止提示存在时，也据此恢复界面。用户界面恢复不应当被图示为硬件输出和所有内部任务都验收完成。

### 退出软件的硬件处理

[Machine.Operate.cs706–730](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L706) 的已读部分：DataSave → 若配置流道加热则 CLoseHeater → 非离线时 HardwareRepositoryService.CloseAllHardware，后者局部 catch 吞掉异常。此为退出软件路径，不是普通 Stop 的直接调用。CloseAllHardware 的库实现尚未读取，不能断言一定将热吹或所有输出置为 false。后续退出过程不在本次已读范围内。

## 热吹问题目前能得出的结论

已确认上下料热吹方法正常路径会调用 CloseHotBlower，局部没有 finally；本次读到的普通 Stop、EmergencyStop、SetState 方法未显式调用热吹关闭，MachineState setter 也没有清理逻辑。退出软件有通用 CloseAllHardware，但不等同于生产停止且存在库边界。**尚不能证明所有异常或停止条件下热吹必定关闭，也不能反向断言现场必定保持开启。** 下一步应查通用硬件清理与外围监控，并结合现场或模拟验证。

## 验收状态

- 已读上述停止入口、直接清理函数、供晶 Start、三个急停调用的 Abort 实现及任务退出判定；库实现、外围监控及生产任务各内部等待的退出响应仍需继续复核。
- 图表同步时需区分“设置 Stop”“投递清窗”“停止轴调用”“请求终止”“已确认任务退出”，不可合并为一个保证完成的结束节点。
- 源码快照加入 [carrier-change-evidence.json](carrier-change-evidence.json)；静态校验只验证原文、行号及哈希，不代表任务时序或硬件安全验证。
