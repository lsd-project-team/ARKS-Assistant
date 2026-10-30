# 输送—S1—S2 生产交接复核

> 最新进度：上下料任务、出口交接及图文重新核实结果见 [输送章节语义复核](transport-semantic-revalidation.md)。本文保留先前的分批分析和当时待办，不作为当前完成计数。

2026-09-28；范围为当前源码方法体的静态控制流。控制器内部硬件封装未全部展开，不能视为设备运行验收。以下链接指向源码；行号快照另存于 transport-production-evidence.json。

## 流程摘要

TransportTask.Start 按上下料配置创建多个并发任务。正常生产中，上料成功发布 S1 来料状态；S1 获取状态后执行动作列表，未停止时发布允许转送信号。输送控制器同时满足 S1 有料、S2 无料后等待该信号，再传料、迁移 TransportUnit、保存状态。传输成功后发布 S2 来料信号，BondTask 消费该信号；固晶侧 SendAway 在配置输送且未停止时放行。下游控制器在 Bond 有料、等待区无料时等待放行，再转送并更新载具状态。各段完成一片后回到工作循环，不是全机任务结束。

## 任务、条件与交接

|环节|源码确认的行为|来源|
|---|---|---|
|在线上料|Online / OnlineWithAutoLoader 创建送板机→入料段任务；PrepareFeeding 为 false 时睡眠后再检查；成功清除 PrepareFeeding|[TransportTask:120](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L120)|
|人工/皮带/料仓分支|None 仅处理 S1 已有料确认；非 LoaderBin 创建皮带任务；LoaderBin 创建推料任务，先等 LoaderAllowPushSignal|[TransportTask:180](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L180)|
|S1 来料|皮带/料仓传输 Success 后 Set TransferToDispense1FinishedSignal；已有料也可能直接发信号，不应画成必经重新上料|[皮带:284](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L284)、[料仓:393](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L393)|
|S1 消费|非 OffLineWork 调 GetInputSignal；循环预点胶，检查停止/暂停，读取 State==Set 后直接赋 State=ReSet；不是调用 Wait 或 ReSet 方法|[DispenseWorkTask:76](../../trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs#L76)、[GetInputSignal:221](../../trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs#L221)|
|S1 动作|Enable 时注入产品步骤，取动作；IsDoWork=false 跳到完成登记；Retry 回到取动作；其他非 Success 移安全位、Stop、return；正常结束且未停止才放行|[DispenseWorkTask:93](../../trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs#L93)|
|S1 分段移动|任务确实调用 TransferDispense1ToDispense2，虽旁有“先不用”注释；控制器自动分支等待 AllowDispense1TransferToDispense2Signal，成功后任务发送 TransferToDispense2FinishedSignal|[任务:430](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L430)、[控制器:1186](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L1186)|
|S1→S2|S2 必须无料且 S1 有料；自动模式 Wait AllowDispenseTransferToBondSignal，false 返回 Abort；成功迁移载具、刷新、清空 S1、更新两段状态、Save|[控制器:1266](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L1266)、[迁移:1478](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L1478)|
|S2 接料|传输 Success 后 Set TransferToBondFinishedSignal；补偿模式直接通过 GetIncomingSignal，否则已配置输送时 Wait 该信号|[任务:525](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L525)、[BondTask:390](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L390)|
|S2→等待区|SendAway 在已配置输送且未停止时 Set；控制器在 Bond 有料且等待区无料时 Wait；成功迁移载具、清空 Bond、更新状态并 Save|[SendAway:443](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L443)、[控制器:1531](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L1531)、[状态:1763](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L1763)|
|下料任务|None 在创建 Bond→等待区任务之后 return；非 LoaderBin 调等待区→皮带；LoaderBin 等 UnloaderAllowPushSignal 后传送，复位允许推料并发 AllowUnloaderMoveSignal；联机收板机另起任务|[TransportTask:602](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L602)|

## 不能合并成一种“重试/失败”的路径

- **未满足条件**：控制器返回 NoStart，外层工作循环下一轮再调用；不是报警重试，也不能保证下一次成功。
- **S1 动作 Retry**：不调用 FinishCurrentActionNode，回到 GetNextActionNode；后者选择 WorkMessages 中第一个未完成项。若动作没有改变列表或完成状态，会再次选中该项；不能无条件断言总重做同一动作。[选择与完成实现:767](../../trunk/AKRS.ZX2200/Main/Machine/Process/S1ActionNodeController.cs#L767)。匹配动作对象失败同样可返回 null；工作循环把 null 当成退出条件，不足以证明所有动作均执行成功。
- **S1→S2 卡料**：两处人工 Retry 都跳到 retry:1304，位于放行等待之后；不会重新消费放行信号。Abort 返回；Ignore 继续后续状态迁移。第一处 Ignore 会跳过 else 中的 Bond 皮带动作，不能当作“重新检测通过”。[报警:1380](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L1380)。
- **S2→等待区卡料**：Bond 出料检测失败的 Retry 跳 retry1:1568；等待区卡料的 Retry 跳 retry2:1652，仅重入等待段传送部分；两者均在放行等待之后。Ignore 继续到状态更新。[第一处:1620](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L1620)、[第二处:1724](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L1724)。方法内未见重试次数上限。
- **控制器异常结果不一致**：S1→S2 catch 返回 Exception，但任务 switch 只有 NoStart/Abort/Success，没有 Exception 分支，随后睡眠再循环；S2→等待区 catch 也返回 Exception，但其任务显式调用 Stop。不能写成“任何传输异常统一停机”。[前者 catch:1506](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L1506)、[前者 switch:527](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L527)、[后者 switch:568](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L568)。
- **任务自身抛异常**：上述任务外层 catch 多为显示错误后结束 lambda，没有统一 Stop；控制器内部返回结果与异常冒出任务是不同路径。[任务 catch:547](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L547)。

## 状态、配置和验证边界

Signal.State 是普通自动属性；Set 同时置事件和 State，ReSet 同时复位二者。S1 直接改 State 没有调用事件 Reset，不能把 S1 的属性轮询画成与 S2 完全相同的事件消费。[Signal:26](../../trunk/AKRS.Galaxy2.Machine/Models/Signal.cs#L26)、[Set/ReSet:87](../../trunk/AKRS.Galaxy2.Machine/Models/Signal.cs#L87)。

未配置 S1 时，皮带上料循环在结果 switch 之后发 AllowDispenseTransferToBondSignal，并非只在 Success 分支发。料仓路径未见对应发信号语句；该配置组合的实际支持情况需继续追踪，不能自行补出旁路。[TransportTask:293](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L293)。

DryRun 另走 StartDryRun：构造载具并置两段有料，循环消费各自放行信号后再次构造载具/发布来料；不是正常物理上/下料路径。[TransportTask:775](../../trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs#L775)。

尚待展开：上下料控制器和料仓任务内部、S1 分段信号生产者、Bond 主动作与供晶握手、Save 实际文件位置、硬件调用及现场配置。本文确认信号收发位置和局部分支，不将全部图边标为已验证，也不声称现场运行已复现上述差异。
