# 原S1 Working任务循环、暂停与节点异常

两轮独立Framework CLR各126项检查通过，标签、顺序和全部结果一致。每轮原Start创建13个实际LongRunning任务，11个正常完成、2个Faulted；实际节点DoWork尝试317次，覆盖9种具体节点。原S1 Working循环已在限定非设备配置下运行，不能等同真实点胶/检测/完整生产验收。16工程、29组、1436文件、13项整体目标未完成。

## 条件到动作与完整循环

原公开构造生成2基板×每板2基岛×每岛2焊点真实树，两个步骤仅指定不同焊点，组件/检测/胶型保持字面量Null，即明确无业务动作的步骤。原配置为OffLineWork、LocateConfig.AdjustType=None、空测高点、测高启用、身份识别Manual，产品IsProduct=true。没有替换节点、控制器、SDK、硬件或私有上下文；每次Start运行完整原Init/InjectSteps/GetNext/IsDoWork/DoWork/Finish。

四种WorkProcess×两种WorkProcessModule共8计划，各45条消息，31次原DoWork，14条条件跳过。原目录对象跨多层实体复用，WorkStart第一次见Idle、后续见Stop；WorkStop见Stop。实际事件次序与先行公开选择、条件列表一致。通过最后一个原节点WorkStop公开设MachineState=Stop同步结束；回调时44条前置消息已完成，当前尚未Finish。原循环仍提交当前Finish，再执行产品Finish，把45条Finished全清false并清当前指针，Stop阻止向流道发信号。

每计划执行9种原节点：载具视觉、四层测高、四层身份。定位None使载具视觉在原System1MatterVision内直接设置IsVisioned；其他三层定位条件false。空点让原MatterHeightMeasurePoints早返回；载具、基板、基岛测高在离线设置的是IsVisioned，IsMeasureHeight仍false，而焊点测高设置IsMeasureHeight=true。四层身份在原节点离线分支设IsIdentity并返回。焊点视觉与两个无业务步骤仍未完成，不能将任务完成或发传料信号解释为业务步骤完成。

另一个真实任务完成第一整轮，原GetNext返回null、设置AllowDispenseTransferToBondSignal，再原Finish重置消息；第二轮已定位载具的视觉被跳过，第一项实际动作仍为载具测高，WorkStart公开设Stop，最终正常退出。第一轮传料信号保持Set；原离线绕过输入，预先Set的来料信号也未消费。此任务32次动作，证实空选择及正常周期后传料路径，而非仅最后节点处Stop的循环。

## 实际任务Pause、Start与Abort

首个原载具视觉WorkStop公开设Pause。当前Finish已提交，实际任务阻塞于节点间WaitStart，没有新的节点回调。此时Start返回true且保留同一Task，其Status=Running；AbortThread直接Dispose活跃Task抛InvalidOperationException，任务继续存活。

公开恢复Working后完成31次节点调用，最后回调设Stop，正常清理。另一组Pause恢复为Stop却仍再执行一个原载具测高节点，共2次调用，再退出并产品Finish。原Signal.WaitStart在暂停睡眠后未重新检查Stop即返回true，实际Task证明这一窗口会让节点循环多前进一次。普通任务初始Stop与Pause后的Stop不是相同路径；没有据150ms等待推断永久阻塞。

## 原节点公开事件异常

对第二个实际动作、原载具测高的WorkStart及WorkStop分别抛出同一显式InvalidOperationException。真实Start创建的Task均Faulted，Task.Exception.InnerException就是回调异常对象。机器状态仍Working，第一条载具视觉消息Finished=true，当前测高消息未完成；没有进入原Task停止或产品Finish。公开GetNext仍返回同一未完成测高对象。

WorkStart在节点State=Running及try之前，异常跳出后状态Idle、WorkStop未运行。WorkStop在finally及State=Stop之后，异常跳出后状态Stop。两组各尝试2个原动作，合计4次。原S1/S2 Task DoWork均无自身catch/finally；这与返回ExcuteResult.Exception后原任务主动Stop是不同机制。测试回调在每组后清除，没有运行真实异常提示框。

## 重试路径只做静态验收

原S1的Retry不Finish，而continue回WaitStart，再GetNext；S2的ExcuteResult.Retry也回WaitStart/GetNext。S2报警对话框选择Retry则goto RetryCommand，保留本地接收者，直接重新IsDoWork，绕过循环头WaitStart/GetNext。本轮完整原方法及52份Cecil静态方法/分支偏移逐项核验这些边；Retry返回、报警窗口和在线动作没有运行，不以既有重复GetNext或配置Success代替重试运行证据。

## 来源、重放与冻结

151个完整原声明来自74个文件，严格UTF8/CP936文本、原字节SHA、符号与UTF16位置匹配。原S1/S2任务、所执行9种节点、控制器离线安全位、域定位/测高守卫和统计方法的52份静态IL绑定实际Main程序集。52不是317次调用的计数。

两份宿主源码、162真实引用编译成功，两个新隔离进程各绑定16个保真资源原程序集，32物理文件SHA核对。8×31+32+33+4=317次动作尝试/轮，工作配置/公开事件回调为明确夹具。旧122项成功候选顺序子序列原样保留，新增4项正常周期检查。两个编译失败、7项后错误事件状态预期失败、101项后第二轮已跳过前项的错误预期失败，以及已通过122项的完整候选均保存；仅宿主修正，没有改原生产源码。

七步原生/来源/IL与节点条件、配方、动作、算法、阅读器、虚分派父绑定通过。170新增冻结输入，288父输入复用不增数，9836+170=10006；正式冻结1328及历史报告不变，来源台账不是覆盖率。未经过完整原工程LC/Fody/MSBuild/部署，物理点胶/检测、S2完整Working、Retry/Pause其他分支、UI/SQL/VM/设备与完整29组业务解释继续待验收。

下一步核对S1真实业务步骤与离线状态提交、可执行的Retry返回路径，以及S2入口/准备对设备的依赖；继续上下文清理、任务失败后的上层监控/停止、配方生命周期、原构建与UI/设备验收。整体目标未完成。

只读复验：node --max-old-space-size=4096 scripts/verify-native-s1-task-loop.cjs，node scripts/verify-native-s1-task-loop-bindings.cjs。禁止覆盖冻结运行目录，新实验另建目录。
