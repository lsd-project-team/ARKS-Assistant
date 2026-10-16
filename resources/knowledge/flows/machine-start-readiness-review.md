# Machine.Start 与启动就绪链复核

复核日期：2026-10-06。状态：`source-confirmed-partial`。机器可复跑证据见 [machine-start-readiness-audit.json](machine-start-readiness-audit.json)。本轮只读取源码，没有调用 `Machine.Start`、`PrepareMachineReadyToStart`、`SelfCheck`、`CleanFile`、运动、真空、信号、VM 或硬件接口。

## 启动前准备顺序

`Machine.Operate.cs:185–255` 的 `PrepareMachineReadyToStart` 依次执行清理、信号复位、总复位门、任务关闭门、`MachineInitSuccess`、安全门门控、工作态检查、安全位置动作和 `CheckOperatingEnvironment`。其中清理、复位、安全位置与顶针轴动作在真实调用时都有设备或状态副作用；本轮只登记顺序。

`MachineInitSuccess`（`:408–444`）检查配置启用时的总复位、`PrInitSuccess`、磁盘容量和已配置加热器的预热完成；激光编码器检查整段仍为注释。`CheckOperatingEnvironment`（`:89–128`）按晶圆域、System2、System1、产品载具、焊点示教、制程的顺序调用六个门，任一返回 false 即立即返回。

## Machine.Start 顺序

`Machine.Start`（`Machine.Operate.cs:261–309`）先调用准备方法，失败直接返回；成功后在 `:272` 设置 `Working`，再启动 Transport、Wafer、可配置的 System1 点胶、System2 动作排序初始化、Bond、刮胶盘和翻转台任务，最后检查两个晶圆台真空。点胶、Bond、刮胶盘和翻转台的 `Start()` 返回 `bool`，当前调用者没有消费这些返回值。`ActionNodesService.Init()` 位于 Transport/Wafer 启动之后、Bond 启动之前，启动方法本身没有统一的 `try/finally`。

## 域级就绪检查

- System2 `CheckIsReady`（`System2Domain.cs:594–770`）先打开焊头真空；关闭 `IsActiveSelfCheck` 时立即返回 true。开启时检查 Bond 程式、动作节点、ULM/BondHead/吸嘴架参数、力控标定、温漂/取片点位、吸嘴架与工具一致性、焊头物料和预点胶报警。
- System1 `CheckIsReady`（`System1Domain.cs:481–528`）在未配置 System1 时直接返回 true；配置后检查点胶头、预点胶板/胶型和胶料。
- Wafer `CheckIsReady`（`WaferSystemDomain.cs:159` 起）包含料盒、示教状态、载具约束、力控/翻转/相机组合和料片安全条件。
- Process `CheckIsReady`（`ProcessDomain.cs:179` 起）检查步骤数量、名称、序号、焊点引用和制程参数范围。

## 失败传播边界

`TransportDomain.StartTask`（`:84–141`）捕获异常并弹窗；载具预检失败时先调用 `Machine.Stop()`，随后返回，不向 `Machine.Start` 重新抛出。`WaferSubSystemTask.Start`（`:1373–1425`）也捕获异常并弹窗。由于 `Machine.Start` 在 Transport 返回后继续调用 Wafer Start，而 Wafer Start 的源代码会设置 `Working`，当前顺序存在“Transport 失败停止后，后续 Wafer 启动再次写入 Working”的源级风险。这是静态可达序列，不是现场复现结论。

## 范围与后续

- 当前证据证明的是调用顺序、返回值是否被消费和异常边界，不证明任何真实配方满足这些门，也不证明任务线程健康运行。
- 后续应继续核对 `ActionNodesService.Init` 失败后的状态回收、各任务 `Start()` 内部异常观察、Stop/Abort 与 Working 状态的并发交错，以及 System2/晶圆/制程自检的真实配置矩阵。

## 可点击源码证据

- [Machine.Operate.cs:89–128](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L89)
- [Machine.Operate.cs:185–255](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L185)
- [Machine.Operate.cs:261–309](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L261)
- [Machine.Operate.cs:408–444](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L408)
- [System2Domain.cs:594–770](../../trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs#L594)
- [System1Domain.cs:481–528](../../trunk/AKRS.ZX2200/DispenseSystem/Models/System1Domain.cs#L481)
- [WaferSystemDomain.cs:159–211](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/WaferSystemDomain.cs#L159)
- [ProcessDomain.cs:179–230](../../trunk/AKRS.ZX2200/Main/Machine/Process/ProcessDomain.cs#L179)
- [TransportDomain.cs:84–141](../../trunk/AKRS.ZX2200/TransportSystem/Models/TransportDomain.cs#L84)
- [WaferSubSystemTask.cs:1373–1425](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1373)
