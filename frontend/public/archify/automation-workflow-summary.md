# ZX2200 自动化流程摘要

入口：[中文流程与源码导航](index.html) · [完整分析](automation-source-analysis.md) · [信号矩阵](automation-signal-matrix.md)。

程序初始化、按配置回零并加载主窗体后，由操作员点击生产启动。Machine.Start 检查配方、硬件就绪、安全门和旧任务，再设 Working 并启动多个协作任务。源码没有表明这里由 cron 或外部云调度触发。

载具主线为：上料 → 配置的 S1 点胶/定位/测高/检测 → 信号放行到 S2 → 配方展开后的取晶、所选相机校正、固晶及配置的点胶/检测 → 放行至下料段。晶圆供料、可选翻转和胶盘任务通过信号与 S2 协作，下一颗供料可以和当前固晶交叠。实际动作顺序由配方排序及启用条件确定。

Retry 可能重做当前动作，也可能重置更早的配方消息；Ignore 不证明物理动作成功。Pause、Stop、急停和工作线程退出是不同机制。载具加工完成后工作线程继续等下一片，没有统一的“全部批次成功结束”事件。

本次增加 8 个深入章节、54 处可展开的源码证据，以及 23 项信号的 137 处活动引用。图形状态：总览、时序和 8 张详细子图均已交付 HTML 与可编辑 Archify JSON；全部通过 showcase 校验。

以下保留第一版证据索引，方便核对。

## Scope and evidence

Analysis is limited to source under `trunk`; vendor packages, generated designer code and unrelated test applications are not treated as production entry points. No application or hardware-control code was executed. References below identify local files and one-based source lines from this checkout. `trunk` was untracked at analysis time, so these are local source references, not commit-verified public links. Active machine settings and the selected production recipe were not established; configurable alternatives are explicitly labelled.

Paths in the table are relative to `trunk/AKRS.ZX2200/` unless stated otherwise.

| ID | Source evidence | What it establishes |
|---|---|---|
| E01 | `Program.cs:65–70, 99–113, 138–180, 226–256` | Single-instance entry, exception handlers, disk/licence checks, online hardware/PR initialization, optional homing, `Application.Run(MainForm)`. Hardware-init exceptions are displayed; the catch does not itself exit. |
| E02 | `Main/Controls/MainForm.cs:232–257`; `Main/Machine/MachineSupport/Machine.cs:294–358` | Form-load homing gate, load configuration repositories, connect pressure/bondhead devices, start background monitoring. |
| E03 | `Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs:68–109`; `UcMainSystem.cs:699–735` in the same directory | Two Start handlers, optional recipe confirmation, disable single-step mode, call `Machine.Start`; startup exceptions call Stop. |
| E04 | `Main/Machine/MachineSupport/Machine.Operate.cs:89–127, 185–255` | Check homing, previous tasks, initialization, safety door, safe positions, wafer/S2/S1/product/bond-position/process readiness. Failed checks return without starting workers. |
| E05 | `Main/Machine/MachineSupport/Machine.Operate.cs:261–308` | Working state and exact task launch order: transport → wafer → optional S1 → S2 action initialization → Bond → optional flux → optional flip. Compensation mode skips the other production tasks. |
| E06 | `TransportSystem/Models/TransportDomain.cs:84–140` | Transport-disabled early return; dry-cycle alternative; carrier checks, map material, optional loader/unloader bin tasks, transport workers. |
| E07 | `TransportSystem/Tasks/TransportTask.cs:115–418, 470–595, 606–770` | Concurrent loading/transfer/unloading workers; online, belt/manual and bin branches; arrival signals; existing-material restart prompts. S1-absent bypass signal is explicit in the belt-loading branch at 293–295. Do not generalize that branch to every configuration. |
| E08 | `DispenseSystem/Tasks/DispenseWorkTask.cs:63–181, 189–260`; `Main/Machine/Process/S1ActionNodeController.cs:708–733, 749–788` | Initialize action order, pre-dispense while waiting, consume arrival, inject recipe, execute first unfinished action, retry or stop, mark finished, release transfer, reset for next carrier. S1 recipe steps select dispensing or dispense inspection. |
| E09 | `TransportSystem/Controllers/TransportController.cs:1266–1291, 1531–1565`; `TransportSystem/Tasks/TransportTask.cs:525–540` | Transfer requires source material/destination capacity and the relevant release signal. Successful transfer emits `TransferToBondFinishedSignal`. |
| E10 | `BondSystem/Tasks/BondTask.cs:100–354, 361–400, 443–480` | Wait carrier, compensation checks, inject S2 steps, execute action loop, finish/reset, release to transport or request manual removal; optional local mapping save in manual mode. |
| E11 | `Main/Machine/Process/S2ActionNodeController.cs:92–174, 182–234, 715–874, 1033–1074` | Enabled recipe steps; ordering by carrier/substrate/module/bond-position and step/position priority. Component steps expand to Pick → UpLook correction → substrate-camera correction → Bond. Flip/dip settings insert flux before or after UpLook. Defect steps select post-bond check; epoxy steps select S2 dispensing. First unfinished message is returned. |
| E12 | `BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs:55–78, 318–337, 624–664`; `PickActionNode.cs:156–213` in the same directory | First-pick request names the component and signals wafer demand; nozzle preparation and pickup wait; subsequent requests can prefetch the next component. |
| E13 | `WaferSubSystem/Tasks/WaferSubSystemTask.cs:64–162, 165–252, 322–324, 375–384` | Wait demand, validate component, change carrier when needed, `Block.NextDie`, search/replacement retry branches, emit pickup-ready; caught failures display an alarm and stop. |
| E14 | `BondSystem/Models/Parameter/System2RunTimeProvider.cs:337–392`; `WaferSubSystem/Tasks/FlipTask.cs:57–101, 236–239`; `BondSystem/Tasks/SlideFluxerTask.cs:92–150, 208–210` | Direct versus flip pickup waits; flip publishes ready and waits pickup success. Flux task publishes dip permission and waits dip completion / slide-out permission. |
| E15 | `BondSystem/Tasks/BondTask.cs:224–319`; `DispenseSystem/Tasks/DispenseWorkTask.cs:149–165` | Different S1/S2 failure policies. S2 Ignore marks the action finished; this is operator-selected continuation, not evidence that the action succeeded. |
| E16 | `trunk/AKRS.Galaxy2.Machine/Models/Signal.cs:46–82, 119–170, 208–243`; `Main/Machine/MachineSupport/Machine.Operate.cs:314–401` | EventWaitHandle-based signals, cooperative pause/stop gates, Continue, Stop cleanup and emergency axis-stop calls. `Wait(int outTime)` uses `recycleTime`, not its argument. |
| E17 | `Main/Machine/MachineSupport/Machine.Operate.cs:449–488, 662–699`; `Machine.Sustain.cs:276–319` in the same directory | Background loop sleeps 100 ms between monitoring passes; door opens → Pause, encoder failure → Stop, temperature handling; ensures image/statistics workers exist. |
| E18 | `trunk/AKRS.Galaxy2.MachineSupport/Config/PathConfig.cs:40–94, 117–119`; `Infrastructure/Models/Path/ZX2200PathConfig.cs:71–105, 303–308`; `Main/Machine/Process/ProcessDomain.cs:29–51` | Settings under executable directory: hardware/device JSON, recipe-specific JSON and PR templates. ProcessDomain reads its process-program path. |
| E19 | `SupportFeature/Statistics/StatisticsService.cs:53–54, 97–137`; `Infrastructure/Service/DBService.cs:43–70, 84–99`; `Infrastructure/Service/VisionService.cs:213–244, 326–340` | Bounded in-memory statistics collection (500), background SQL writes, local SQL Server `ZX2200` using Windows authentication, queued image persistence. Database insert failure logs an error; no retry is present there. |
| E20 | `AKRS.ZX2200.csproj:12, 259–283`; `Program.cs:177–222`; `Main/Controls/MainForm.cs:251–253` | .NET 4.8; external Galaxy drive/infrastructure/hardware DLLs; motion/camera/IO hardware APIs and Modbus device connections. Driver internals are outside the inspected source boundary. |

## Execution, branches and completion

1. **Launch and prepare** (E01–E04): desktop startup and operator Start are separate. Startup may initialize hardware and home axes; production Start validates current state and recipe. Cancelling recipe confirmation or failing readiness produces no production launch.
2. **Dispatch concurrent workers** (E05–E07): `Task.Factory.StartNew(...LongRunning, TaskScheduler.Default)` is used for S1/Bond; transport uses `Task.Run`. There is no calendar scheduler in this traced production path. Background monitoring starts at form load, independently of Start.
3. **Move and dispense a carrier** (E07–E09): configured feeder/belt/bin mechanisms load material. S1 waits for `TransferToDispense1FinishedSignal`, executes its ordered actions, then sets `AllowDispenseTransferToBondSignal`. Transfers also check occupancy; they are not unconditional arrows. Existing material can be resumed through configured prompts. Offline, dry-cycle, transport-disabled and compensation modes are separate paths, not proof of production behaviour.
4. **Execute S2 recipe** (E10–E11): wait `TransferToBondFinishedSignal`, perform compensation checks and inject steps. Recipe ordering and `IsDoWork()` determine which actions execute. Inspection is a selected recipe step, not an unconditional operation after every bond. Optional preparation/vision/height actions come from the action repositories and ordering policy.
5. **Supply and pick chips** (E12–E14): the first Pick sets component demand; wafer search responds with readiness. The direct wafer-camera path waits that readiness before pickup. Bond-camera search can defer its wait until search position; flip mode routes readiness through FlipTask. Subsequent requests can overlap later bond actions.
6. **Handle action outcomes** (E15–E17): Retry normally leaves the action unfinished; S2 Alarm offers retry/ignore/abort. S2's repeated UpLook/substrate-camera action guard can throw instead of treating every retry identically (E11:1056–1060). No universal retry count/backoff is implemented by these task loops. Wafer search has local replacement/reselection branches. Exceptions are not uniformly handled: some transport catches only display errors, and Bond's task wrapper has no broad catch.
7. **Complete one carrier, continue production** (E09–E10): S2 moves safe, resets action messages, normalizes compensation and optionally saves timing; it signals permission to unload. Transport then moves through waiting/unload stages according to configuration. Without transport it can save mapping and asks the operator to remove the carrier. Workers repeat until stopped; release permission alone does not establish physical unloading success.

## Inputs, outputs and system boundaries

- **Inputs:** operator commands, selected recipe/process steps, product geometry, component/nozzle/epoxy/inspection configuration, PR templates/calibration data, carrier/die availability and hardware sensors (E03–E04, E11–E14, E18).
- **Outputs:** executed physical dispense/pick/bond/transport operations, per-carrier/action state, defects/statistics/operation records, configured vision images and optional manual-mode mapping export (E08–E10, E19).
- **External systems:** motion controllers, cameras, IO, wafer/eject/flip/flux modules, configured upstream/downstream feeder equipment, Modbus-connected instruments and local SQL Server (E07, E14, E20). No HTTP/MES/cloud orchestration was established in this traced path; SECS UI labels alone are not evidence of a live integration.
- **Coordination/storage:** `SignalPool` uses in-process events, action controllers use ordered in-memory messages, and statistics/images use in-memory work collections. These are not durable broker queues. Background persistence is not a commit barrier for production completion (E16, E19).

## Important limits

Pause is cooperative at checked boundaries, not a demonstrated instantaneous hardware halt. `EmergencyStop()` requests axis stops, but `BondTask.AbortThread()` is empty and the transport-abort call is commented out; do not claim all tasks are force-cancelled or joined. The analysis describes source behaviour, not a safety certification or a successful hardware test (E16; `BondTask.cs:382–384`).

The diagrams show the normal transport-enabled production path, with configurable branches and local source references in detail cards. The sequence illustrates the first direct wafer-camera component pickup, not an exact timing trace of all concurrent workers.


## Delivered artifacts and verification

- [Interactive workflow](automation-workflow.html) and [editable source](automation-workflow.archify.json).
- [Runtime sequence](automation-sequence.html) and [editable source](automation-sequence.archify.json).
- [Verification and SHA-256 receipts](verification.md): both diagrams passed 9/9 showcase checks and all four desktop viewport checks. Screenshot review covered both themes.
