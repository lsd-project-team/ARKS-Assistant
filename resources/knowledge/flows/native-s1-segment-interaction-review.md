# 原启用 S1 分段交互与任务暂停、停止边界

六个模式分别在两轮全新 Framework CLR 宿主执行，12个宿主全部 exit0。每轮121次断言执行、42个不同标签；检查数按 direct/stop/pause-stop/complete/complete-while-paused/callback-stop 为15/19/20/23/25/19。每轮实际启动5个原 S1 LongRunning 任务，4个 RanToCompletion、1个预期 Faulted；direct 模式没有启动任务。24个原方法 IL 与14个原源码文件哈希冻结。宿主 exit0 表示预期观察通过，不表示全部原任务成功或物理生产完成。

## 真实输入与明确的测试条件

完整原 S1Domain、TransportDomain、SDK 构造器和注册动作原样使用。公开配置 Divide、IsOppositeSex=false、LagerNumber=false：Substrate 两个（Row=1/Col=2），Module 单个（Row=1/Col=1），一个 bp 和一个启用 step，应用/胶水/缺陷名为 Null。原 UpdateTransportUnit 建立 carrier1/substrate2/module2/bp2 共7个真实实体，EntityState=Process、IsProduct=true，原任务不会替换这棵对象树。没有私有写入、替换动作、任务、Signal、单例或硬件对象。

原 InitDivide 生成22条消息，真实 GetFirstMatrixIndex 得到 [1]；后组（sub2及transport3）12条→Interaction（零基索引12）→前组（sub1）9条。WorkMessages 仅反射读取，原 Init/GetNext/Finish 自行推进调度。真实 Machine Working/OffLineWork，空硬件、safeDoor=false、Belt；原 MoveZToSafePos 在 OffLineWork 分支直接返回，未驱动轴。

视觉和测高完成标记通过公开属性预置为 true，身份动作配置 OnForSearch。完成信号 done.Set 是明确的测试生产者，没有启动原输送任务或物理转移。公开 WorkStart/WorkStop 回调记录状态、精确 Pause、注入异常或在第二轮 Stop；这些是测试同步条件，不是自然现场故障。每个 bp 的 RemainingS1Steps[step] 始终 false，身份与握手成功不代表点胶步骤完成。未执行原 Program.Main、UI、S2、SQL、在线 S1、物理视觉/测高/点胶/输送、完整原 MSBuild 或部署。

## 已执行结果

|模式|原实现观察|任务与边界|
|---|---|---|
|direct|Complete 枚举值0、Divide 且 IsTU1InDispense1=false 均 Success；Divide/TU1=true/Stop 时原 Wait 返回 false 仍 Success，AllowSet、doneReset、IsFirstDispense=true|3次原交互直接调用，含原 finally/nodeStop；原 TransferDispense1ToDispense2 在 Stop 返回 Abort，转移字段保持原值|
|stop|进入交互前12条完成、4个真实身份动作；待完成信号100ms后仍阻塞。原 Stop 释放 Wait，返回值被忽略，firstDispense 提交 true|原任务正常结束，最终 Finish 重置22条及当前选择；前组3个身份未执行、无 BondRelease|
|pause-stop|已进入 Wait 后 Pause 仍阻塞，随后 Stop 与上述相同|不是暂停前初始 WaitStart 的用例；原任务 RanToCompletion|
|complete|消费测试完成事件并重置 done；首个 WorkStop 回调调用原 Pause，外层把交互消息标完成，下一层暂停门阻塞|Continue 保持同一任务并完成剩余3个身份，首轮 BondRelease Set；第二轮 WorkStart 测试回调 Stop，将运行限制为两次交互|
|complete-while-paused|进入 Wait 后才 Pause；此时 Set 仍被消费，WorkStop 观察设备 Pause。外层下一层暂停门随后阻塞|Continue、首轮释放及第二轮 Stop 同上；证明 pending Wait 内没有重新检查 Pause|
|callback-stop|完成事件被消费、firstDispense=true、节点 Stop 后，原 finally 的 WorkStop 抛出同一注入异常实例|原 Task Faulted，观察时设备仍 Working、当前交互未完成、前12条完成，无首组/无 BondRelease；观察后测试清理调用原 Stop|

Stop 用例的 WorkStop 在外层 FinishCurrent 之前观察交互标记 false，最终 Finish 又重置全部标记，因此没有声称直接观察到 Stop 用例的中间 Finished=true。原动作 Success、IL 中丢弃 Wait 返回值、正常任务退出与最后 Finish 共同建立该路径。完成用例在下一层 Pause 阻塞时实际观察到外层交互标记 true。

每轮 whole-task 交互7次、真实身份 DoWork 26次（4+4+7+7+4）；每轮 direct 交互3次。完成模式的两轮交互由第二轮公开 Stop 回调限定；实际输送未改变 IsTU1 标记，不能称为自然单个生产周期。

## 静态证据与执行边界

InteractiveAction.cs:56 的 Signal.Wait 调用在原 IL 是 IL_00a3 callvirt Wait → IL_00a8 pop，随后写 IsFirstDispense。其 catch 位于 try，WorkStop 在 finally 中，所注入异常向外传播。DispenseWorkTask.cs 的原 DoWork 没有外层 catch；Success 后 FinishCurrent，正常退出后 Finish。Signal.Wait 在入口 WaitStart 后，pending 循环检查 Stop 而不检查 Pause，实际结果与 IL 一致。

原 TransportController.TransferDispense1ToDispense2:1186 在非手动路径检查 AllowWait，false 返回 Abort。本轮只实际执行 HasMaterial/Stop 守卫；后续夹具、挡板、皮带和转移字段提交仅静态核验。原 TransportTask:431–466 调用该控制器，Success 后 done.Set、Abort 后 Machine.Stop；原输送任务及这个真实生产者未执行。

~~~mermaid
flowchart TD
  A[原启用 S1 / Divide / 22条原调度] --> B[后组12条 / 4个离线身份]
  B --> C[原 Interactive / Allow.Set / done.Wait]
  C -->|Stop / Wait false 被丢弃| D[原动作 Success / firstDispense true]
  D --> E[原任务正常退出 / Finish重置调度]
  C -->|测试 done.Set / 暂停中也可消费| F[原动作 Success / 外层交互Finished]
  F --> G[下一层 Pause门阻塞]
  G -->|原Continue| H[前组3身份 / 首轮BondRelease]
  H --> I[第二轮公开回调Stop / 有界退出]
  C -->|完成后WorkStop注入异常| J[原Task Faulted / 观察时Machine Working]
  K[原输送控制器Stop守卫] --> L[检查Wait false / Abort]
  M[原输送任务Success后done.Set] -.静态未执行.-> C
~~~

该补充图用于说明本轮范围，主阅读器的8章节/89节点/101边、正式1328检查及旧40专题3817片段保持冻结，不声称主阅读器已更新或完整业务流程验收。

## 可复核记录与剩余范围

每个宿主实际加载16个 bound/replay 保真资源程序集，runtime-map 172项。162编译引用中10个直接原源码程序集引用。两次成功编译 Probe SHA 相同，两轮 result 与标签严格一致；日志含实际路径、程序集信息和时间，不声称完整 stdout JSON 字节相同。两次宿主编译因遗漏真实命名空间失败，输入和诊断均保留；随后成功编译与12个全新宿主通过。父输入门/Working/资源验证在有退出守卫的同一流水线76893/105ee1中通过，未给各子命令虚构独立工具 session。

父5272冻结绑定通过，新增111，累计5383；绑定数不是业务覆盖率。测试、审计、报告、进度均有独立基线和哈希。本轮确认停止时交互仍走 Success、pending Wait 暂停后仍消费完成事件，以及公开回调异常使实际任务 Faulted；这些为已验证原行为，没有修改生产代码。

继续原 Retry/返回失败与预点胶真实下层、S2安全/清零/补偿/UI前提、实际输送握手和生产循环退出；相机 VM、在线 IO/轴、SQL、LC/Fody、完整原 MSBuild/部署仍待验收。16工程/29组/1436文件/13项整体目标未完成。

见[测试](native-s1-segment-interaction-test.json)、[审计](native-s1-segment-interaction-audit.json)、[进度](native-s1-segment-interaction-progress.json)。
