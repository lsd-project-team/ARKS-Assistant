# 主界面后台刷新：注册、调度与错误边界

更新：2026-09-29。证据为 `trunk` 调用源码与随仓库 `AKRS.Galaxy2.BackgroundWorkThread.dll` 的[静态 IL 快照](background-task-binary-evidence.json)，DLL SHA-256 为 `620cafdd6b50a6dccd42886307aa0c34e6e779e731c233f68dabc2331db19b77`。未加载 DLL、运行 UI、设备或现场进程；现场实际程序集版本未核对。

[交互时序图](background-task-sequence.html)将注册、循环扫描、间隔门控与 UI 排队放在同一条可追踪链路；各箭头以本页的源码行与 IL 快照为依据。

## 从主界面 Load 到刷新委托

1. [UcMainSystem_Load:251–313](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L251) 在 try 中注册名为“刷新UcMain界面状态”的 `BackgroundThreadService` 任务；传入随机 Guid、优先级 1、间隔 1000 ms、`SingleExecuteState=false`，省略的 timeout 形参元数据默认 1000。随后调用 `ActivateSingleTaskExecute()`、注册热键、确保测试目录存在。Load 的 catch 只显示错误提示。项目[声明本地 DLL 引用](../../trunk/AKRS.ZX2200/AKRS.ZX2200.csproj#L245)。
2. 注册的 Action 只调用 `BeginInvoke` 排入 UI 委托。**真正 UI 工作在 UI 委托中**：[改变设备状态显示、按配置刷新、自动登出、构造授权/配方/用户/工作模式文本](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L275)。因此调度 Action 返回不等于 UI 已刷新；其异常捕获范围也不自动包住随后 UI 线程执行的委托。
3. [新建配方](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L355)、[载入配方](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L834)、[管理窗口关闭](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L930)各调用一次 `ActivateSingleTaskExecute()`；它们的注释写“触发一次界面刷新”，但实际效果需按以下 DLL 分支判断。注册不等于设备生产启动。

## 随附 DLL 的调度次序

|步骤|IL 证据与限定结论|
|---|---|
|首次获取服务|`BackgroundThread.GetInstance` 无本地 lock 的空值检查和构造（`threadGetInstance IL_0001–002b`）；构造先建空列表，对已有列表执行 StartTime（当时是空列表），再 `Task.Factory.StartNew(Action, TaskCreationOptions.LongRunning)` 并对返回 Task 调用 `ConfigureAwait(false)`、丢弃结果（`threadConstructor IL_0000–005c`）。不能据此当作已 await 或受托管的错误监控。|
|登记|`RegisterTask` 先以**名称**做 `Exists` 检查（`register IL_000e–002e`），成功才新建任务，在锁内 Add、StartTime、按 Priority 降序排列并替换 TaskList（`IL_0034–00b6`）。已存在同名则记录“注册任务失败”（`IL_00c7–00e6`）；随机 Guid 在此方法体没有被读取。名称检查在锁外，不证明并发注册互斥。|
|循环|后台线程在 [RuntimeProvider.ThreadFlag](../../trunk/AKRS.Galaxy2.MachineSupport/RuntimeProvider.cs#L43) 为 true 时运行，锁内读 `IsExecuteSingleTask` 并立即复位，然后逐项检查 `SingleExecuteState`：若为 true，仅本轮激活标志为 true 才调用 Execute；若为 false，**每轮都调用 Execute**（`threadLoop IL_0019–0068`）。解锁后 `Thread.Sleep(20)`（`IL_00b5–00d9`）。这是扫描周期，不是每 20 ms 刷新 UI。|
|时间门控|`BackgroundTask.Execute` 只有在 Stopwatch 已经过 `interval` 且未 Pause 时才调用 Action，随后 Restart；调用异常被 catch、Restart 后记录日志并返回（`taskExecute IL_0001–0088`）。`timeout` 被构造器保存，但在该 Execute 方法体中未读取，不能声称已执行超时取消/重试。|
|激活与移除|`ActivateSingleTaskExecute` 仅将布尔标志置 true（`activate IL_0001–000d`），不直接调用 UI Action。`RemoveTask` 按名称 RemoveAll，方法体无 Monitor lock（`remove IL_000e–002a`）。未验证并发修改时的现场结果。|

**对本页面的重要推论：**该任务登记为 `SingleExecuteState=false`，因此上述三处激活调用不会绕过 1000 ms 的 Stopwatch 门控，也不会使它立即执行；只要后台循环运行且任务仍在列表中，刷新 Action 才会在间隔满足的循环中排队。多个激活调用会折叠为一个布尔状态，且该状态在每轮扫描时复位。真实刷新时序还取决于 UI 消息泵、委托排队、ThreadFlag 及实际加载版本。

## 错误和交接边界

- `BackgroundTask.Execute` 的 catch 处理同步 Action 异常并记日志；`BackgroundThread` 另在单项 Execute 周围 catch 记日志（`threadLoop IL_003b–0096`）。取列表、锁获取、Sleep 等部分不在该单项 catch 内；服务构造的后台 Task 无等待/观察逻辑。不能据此宣称全局任务不会停止或故障必被发现。
- `BeginInvoke` 之前的调用异常可能落入 `BackgroundTask.Execute` 的 catch；排队后执行的 `ChangeUiByState` 等 UI 委托不在这个同步 Action catch 中。应结合 [Program 的 UI 全局异常处理](async-notification-exception-review.md)另外核对；该处理仅弹窗，不能代替 UI 状态成功验收。
- [ThreadFlag 初值为 true](../../trunk/AKRS.Galaxy2.MachineSupport/RuntimeProvider.cs#L43)；随附 DLL 和设备监控线程都读取它作循环条件。[BaseMachine.ExitApp](../../trunk/AKRS.Galaxy2.Machine/BaseMachine.cs#L160) 会将其置 false，但 `trunk` 的 C# 直接调用搜索只找到方法定义。[主窗体 FormClosed](../../trunk/AKRS.ZX2200/Main/Controls/MainForm.cs#L295) 实际调用 [ExitSoftware](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L706)，先尝试保存和关闭硬件，最后直接 `Environment.Exit(0)`；其方法体没有设置 ThreadFlag、移除刷新任务或等待后台任务。因此**不能把正常窗口退出画成先发停止信号再 Join 的有序回收**，也不能据静态源码断言现场必然发生并发交错。更完整的外层关闭链见[后台监控/退出复核](authorization-background-source-review.md)。并发注册、移除、日志配置、DLL 版本及 UI 线程异常效果仍需隔离/现场核对。

复核：`node scripts/verify-background-task-contract.cjs` 重新从随附 DLL 提取 14 个方法、核对哈希、调用顺序、异常表与源码行；这是静态证据复核，不是任务运行测试。
