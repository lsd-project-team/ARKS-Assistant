# S2固晶任务、真实事件与门控暂停

日期：2026-09-29。37项受控检查通过，执行17个原方法片段，另直接编译完整原Signal.cs和MachineEnum.cs。使用真实Thread运行原BondTask.DoWork、GetIncomingSignal、SendAway、CloseDispenseCylinder、S2点胶节点及原机器状态/Stop方法。前置见[S2任务集成](s2-task-integration-review.md)与[S1门控循环](door-task-pause-review.md)。

## 五个阶段的暂停恢复

- ResetInformation返回前开门：外层WaitStart阻塞，尚未调用吸嘴架回原点。
- 来料后的取片补偿调用中开门：返回后仍调用温补、参考点扫描并注入动作，再到内层WaitStart阻塞，尚未执行节点预点胶。
- 节点WorkStart中开门：S2节点在预点胶前已有WaitStart，所以预点胶尚未调用。这与S1先预点胶再检查的顺序不同。
- 节点预点胶中开门：预点胶返回后，第二次WaitStart阻止插补。
- 插补中开门：如果插补随后返回Success，原节点仍提交焊点完成，任务推进动作；到内层下一次WaitStart才暂停。

五组均观察至少四次状态读取，确认等待线程活跃且未放行产品。显式恢复Working后各完成一轮，预点胶和插补各一次。

## 来料事件在暂停期间被消费

先让完整任务进入真实TransferToBondFinishedSignal.Wait，且事件未置位；确认仍在内部轮询，再触发门控Pause并置位真实事件。原Wait仅在入口调用WaitStart，内部循环只检查Stop，故实际消费来料事件；Wait在返回前写入公开State=ReSet，但Set先唤醒事件再写State=Set，两个线程的元数据写入可竞争，不能把公开状态等同于事件句柄。任务继续调用补偿并注入动作，随后内层WaitStart阻止节点与放行；恢复后完成一轮。

此处不是把信号等待替换为true。事件句柄与原Wait类真实执行，但补偿、状态存储和硬件动作仍是替身。

## 收尾阶段的Pause与Stop不同

在任务已Finish、进入NormalizationOffset替身调用时触发门控。释放屏障后，原SendAway只判断IsStop，不判断Pause：

- 保持Pause时，真实放行事件被Set。记录放行调用前状态仍为Pause；任务并未在收尾阶段新增暂停门控。
- 同一点调用完整原Stop后，没有发送放行事件。

放行包装器在记录调用并Set真实事件之后设置Stop，只为限制测试外层循环；不能据此声称生产放行本身会改变机器状态，也不能推断实体载具已经移动。

## 单步与停止补充

单步模式下在节点入口开门，真实单步事件到达会被消费，但S2紧随其后的第一个WaitStart仍阻止预点胶。恢复后正常完成一轮；这一点与S1单步事件可先放行预点胶不同。

另在初始化、节点预点胶和插补三个屏障处调用原Stop，全部阻止放行。节点预点胶后WaitStart发现Stop返回Fail，而原BondTask的switch没有Fail分支，仍推进当前动作；插补成功返回时仍提交焊点完成。成功状态提交与设备停止不可混为一谈。

## 范围与后续

门输入、驱动、补偿、预点胶和插补、动作服务、日志/UI、状态存储等为替身。线程屏障和volatile状态仅用于测试观测；不用这些结果证明生产竞态、真实机械暂停或现场事件消费频率。普通场景关闭单步，另有一组单步场景；没有覆盖固晶所有节点、所有报警选择或全部配置。未运行产品.NET Framework宿主。

原源码、片段和全部测试依赖哈希见回执。生产源码及设备配置未修改。下一步继续输送与供晶暂停/停止集成，并核对收尾放行信号的下游消费者；29组保持部分复核。

运行：`node scripts/test-s2-door-pause.cjs`；审计：`node scripts/build-s2-door-pause-audit.cjs --check`。

观测修正（2026-09-30）：统一回归发现原来料断言依赖通用状态读计数和公开State，不能可靠证明来料处理阶段已经完成。现在显式等待动作注入，并检查真实事件句柄未置位；单步消费也检查真实句柄。保留37项断言、17原方法和全部原等待代码，专项连续三次通过；生产代码未修改。失败日志保留于`.archify-work/verify-ui-start-mode-failed-s2-door.log`。
