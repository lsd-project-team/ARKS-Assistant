# Machine 任务生命周期与异常回收复核

复核日期：2026-10-06。状态：`source-confirmed-partial`。审计证据见 [machine-task-lifecycle-audit.json](machine-task-lifecycle-audit.json)。本轮只读取源码，没有启动任何后台任务、调用停止/急停、VM、硬件或设备接口。

## ActionNodes 初始化

`S2ActionNodeController.Init`（`S2ActionNodeController.cs:155–175`）先清空 `WorkMessages`，无流程步骤时直接返回，否则执行按模组排序、删除其他步骤、删除禁用节点和相对焊点排序。该方法没有本地 `catch`、返回值或失败状态。

`Machine.Start` 在 Transport 和 Wafer 任务启动后，于 `Machine.Operate.cs:289` 调用这个 `Init`，再启动 Bond 任务。因而如果初始化抛出异常，源码中没有显示出已启动任务的统一回收路径；具体调用者是否捕获取决于外层入口。

## Worker Task 和异常观察

Bond、点胶、刮胶盘、翻转台的启动方法分别用 `Task.Factory.StartNew` 保存 Task 句柄，Transport 代表分支用 `Task.Run`。本轮解析的四个 `DoWork` 方法没有顶层 `catch`；源码没有在这些启动方法中 `await`、读取 `Exception` 或转换为统一结果。Transport 的多个分支各自有 catch 和弹窗，但这不等于所有 Worker 都有共同异常监督。

`Machine.IsAllowTaskClosed`（`Machine.cs:201–262`）收集 16 个任务句柄，只在 `task?.Status == TaskStatus.Running` 时返回 false。`Faulted`、`Canceled`、`RanToCompletion` 和 null 在这个检查里都不会阻止下一次启动，因此故障句柄本身不能作为“仍在运行”状态被识别。

## Stop 与 EmergencyStop

`EmergencyStop`（`Machine.Operate.cs:383–401`）先调用 `Stop`，随后依次调用点胶、Bond、Wafer 的 Abort 方法。点胶 `AbortThread` 在 `DispenseWorkTask.cs:212–215` 直接 Dispose Task，不等待；Bond `AbortThread`（`BondTask.cs:382–384`）为空；Wafer `AbortWaferSubThread`（`WaferSubSystemTask.cs:1431–1437`）只有注释掉的旧线程中止代码。源码因此不能证明急停会取消或 Join 这三个 Task。

## 结论与边界

- 已把启动顺序中“ActionNodes 初始化失败”和“Worker 任务故障/回收”从一般风险细化为具体方法、句柄和状态谓词。
- 当前结论是源码边界，不是 Task 运行时故障复现；没有据此声称现场一定留下 Faulted 任务或一定发生并发重启。
- 后续应在隔离托管任务夹具中验证异常 Task 的状态、`IsAllowTaskClosed` 的重启行为、Stop/Abort 后线程是否仍存活，以及外层事件处理器的捕获范围。

## 可点击源码证据

- [S2ActionNodeController.cs:155–175](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L155)
- [Machine.Operate.cs:261–309](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L261)
- [Machine.cs:201–262](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.cs#L201)
- [Machine.Operate.cs:383–401](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L383)
- [BondTask.cs:361–384](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L361)
- [DispenseWorkTask.cs:189–215](../../trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs#L189)
- [SlideFluxerTask.cs:227–250](../../trunk/AKRS.ZX2200/BondSystem/Tasks/SlideFluxerTask.cs#L227)
- [FlipTask.cs:260–277](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/FlipTask.cs#L260)
- [WaferSubSystemTask.cs:1373–1437](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1373)
