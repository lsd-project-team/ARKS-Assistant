# 输送—固晶交接：失败传播、重试与收尾边界

日期：2026-09-28。范围为实际 BondTask、TransportTask、TransportController 与 System2Domain 所绑定的 S2ActionNodeController。静态源码复核，未运行设备；不代表全部业务或异常链路完成。

## 工作顺序摘要

1. 点胶传入固晶任务循环调用 TransferDispenseToBond，Success 才发送 TransferToBondFinishedSignal。启动时固晶台已有料，还可通过无提示恢复或提示选择 Yes 发送同一信号；不能把每次信号都解释成刚发生了输送运动。
2. BondTask.GetIncomingSignal 在配置输送且非补偿模式时等待该信号。补偿模式直接放行；未配置输送走载具存在检查与人工提示。
3. 来料后进行补偿、注入步骤，逐项 GetNextActionNode → IsDoWork → DoWork → FinishCurrentActionNode。节点返回值、人工报警选择和抛异常是不同路径。
4. 离开动作循环后，依次安全位、ActionNodesService.Finish、偏移归一化、可选耗时保存、SendAway。配置输送且检查时非 Stop，才发送 AllowBondTransferToWaitingUnloadSignal。发送不等于已收到下游运动完成确认。
5. 下游控制器先要求固晶段 HasMaterial、等待段 NoMaterial；非手动模式才等待允许送走信号。Wait 返回 false 转为 Abort；任务收到 Abort/Exception 调用 Stop。

## 关键失败分支

|位置|实际处理|边界|
|---|---|---|
|点胶传入固晶任务 ret=Abort|Stop，退出 switch，Sleep(50)，再判断 WaitStart|不是立即 return；Exception 枚举没有显式 case，不能宣称在此一定停止|
|同任务 try 中抛异常|catch 仅提示，然后委托结束|本地 catch 没有 Stop；后续是否停止取决于其他来源|
|固晶来料后三个补偿检查返回 false|直接 return|这些调用点不显式 Stop；被调用方法的内部副作用需另查|
|动作 ret=Abort/Exception，或 Alarm 对话框选 Abort|Stop → BondZ 安全位 → 可选助焊归位 → return|归位调用仍可能失败；不能保证所有恢复动作完成|
|动作 ret=Retry|continue 到内层 while 的 WaitStart，再 GetNextActionNode；不标记当前完成|与对话框 Retry 不同；重新选首个未完成记录|
|Alarm 对话框选 Retry|goto RetryCommand，重跑当前 actionNode 的 IsDoWork/DoWork|该 goto 不经过循环顶端 WaitStart；本层无次数上限|
|Alarm 选 Ignore，或 IsDoWork=false|到 FinishCurrentActionNode，标记当前记录完成|标记完成不证明该动作成功执行|
|BondTask.DoWork 抛异常|DoWork 与 Start 委托没有本地 catch|异常可离开工作委托；未证明全局观察者/监督器会 Stop|
|下游控制器 try 中抛异常|记录、提示并返回 Exception；外层任务据此 Stop|若异常处理自身再抛出，外层 catch 仅记录和提示，不能合并为同一路径|

## 两个容易误读的收尾条件

- 内层 while(Signal.WaitStart()) 因 Stop 返回 false 结束时，没有额外 return，仍可进入循环后的安全位、Finish、归一化与保存；SendAway 才单独检查 Stop 抑制发送。因此“整件做完”日志并不足以证明所有动作完成。以上仅描述前序调用正常返回时的可达路径。
- 实际服务绑定为 System2Domain.ActionNodesService: S2ActionNodeController（不是目录中旧 System2ActionNodesService）。Finish 将 WorkMessages 的 Finished 全设为 false，并把当前记录指向第一个；它是复位，不是逐项成功验收。仅检查 null，没有在此检查空列表。
- GetNextActionNode 取首个未完成记录；若与上次同名且名称为 UpLookCorrectionActionNode 或 SubstrateCameraCorrectionActionNode，会提示并抛异常。因此不能笼统声称 ret=Retry 总能无限重做同一动作。ChangeNameToActionNode 的对象匹配、消息重排和各节点内部重试仍需细化。

## 信号与恢复限制

这两个交接信号定义为 AutoReset、初值 false、100ms 单次轮询。无参 Wait 无整体超时；若发送者提前退出、没有其他 Set，且消费者已等待、设备未停止，则可持续等待。启动复位、Stop/Continue 与 Pause 的非原子窗口沿用[四信号专题中的公共 Wait 与状态证据](bin-failure-handshake-recovery-review.md)。不能由本专题推断实机死锁或确认恢复安全。

本轮只闭合正常生产的上述调用点；干跑另有发送/消费路径，未混入本正常生产结论。

## 源码证据索引

下表 ID 已登记到 [模块源码阅读器](module-source-explorer.html)；快照保存精确行号、原文和源文件 SHA256。

|证据 ID|源码（相对仓库根）与行号|
|---|---|
|bondflow-infeed|trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:470–552|
|bondflow-work|trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs:100–355|
|bondflow-start-incoming|trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs:361–438|
|bondflow-send|trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs:443–459|
|bondflow-domain|trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs:108–114|
|bondflow-cursor|trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs:1033–1093|
|bondflow-finish|trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs:911–925|
|bondflow-out-gate|trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs:1531–1566|
|bondflow-out-catch|trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs:1790–1809|
|bondflow-out-task|trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:555–599|
|bondflow-signals|trunk/AKRS.Galaxy2.Machine/Models/SignalPool.cs:89–114|

## 尚未完成与下一步

- 追踪供晶—取片—顶针的失败信号传播，再合并跨域异常图；本轮不把尚未分析的支路画成确定流程。
- 补三个补偿 false 返回的实际 Stop/报警副作用，以及全局任务异常观察者。
- 区分实际节点执行成功、消息 Finished 标记、Finish 复位、发送允许移走和下游物理完成；需要故障注入与设备日志验证这些时序。
- 验证 Stop→Working 竞争、信号残留、手动/干跑路径，以及动作服务空集合和名称匹配的真实配置可达性。
