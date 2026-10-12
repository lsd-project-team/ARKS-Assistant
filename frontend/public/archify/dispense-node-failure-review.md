# 点胶动作失败传播、回调与安全位置复核

2026-09-29。六个完整原方法的68项隔离检查通过：S1/S2DispenseActionNode.DoWork、DispenseController.MoveToSafePos、BondHeadController.MoveBondZToSafePos，以及System1Domain/System2Domain.WaitSingleStep。生产任务分派和Machine.Stop另作静态回链，未运行完整生产任务。

## 动作结果与完成状态（54项）

- 两套节点均把预点胶或控制器返回的Fail、Alarm、Abort、Exception、Retry转换为Alarm，跳过完成标记和统计。只对这五种命名非成功样本做了枚举测试，不声称穷尽外部结果枚举。
- 控制器直接抛异常时，节点catch记日志、弹窗并返回Exception，然后执行finally。节点finally只重置节点State、调用WorkStop；S1还刷新载具动作UI。所测节点没有直接关胶或调用Machine.Stop。
- S1仅在预点胶后等待Start；S2预点胶前后各等待一次。首个Start门控失败，S1已执行预点胶而S2尚未执行；S2第二次等待失败则发生于预点胶之后。
- 单步门控false返回Abort；直接调用S1离线DoWork会先标记步骤完成，再可能因单步失败返回Abort。这不是正常调度一定执行离线节点的证明；IsDoWork没有纳入本次执行。
- WorkStart在try之前，回调抛异常会跳过整个try/finally。WorkStop在finally内，抛异常会覆盖原返回值并阻止S1后续UI刷新。S1刷新本身异常也会覆盖Success。catch中的日志/弹窗二次异常会向上传播，但finally仍执行。
- 统计发生在完成标记之后：注入统计异常时步骤已经标记完成，节点最终返回Exception，没有回滚。仅验证节点调用顺序；焊点状态内部实现为替身。
- 坐标转换替身返回输入的情况下，S1加焊点补偿及设备偏移，S2仅加焊点补偿；DryCycle传isDrip=false。坐标变换算法及物理单位不在本套测试范围。
- S2打印策略的吸嘴缺失、未示教分别进入Exception；换吸嘴返回false则Abort，均不调用插补。S2其他预点胶时机保留FirstDispense，S1对应分支将其清false；S2正常尾部更新LastDispenseTime及第二项统计。
- 两套观看点胶效果循环观察到IsStop后退出观看，但节点仍可返回Success。测试IsStop立即为true，没有持续等待或硬件执行。

## 安全位置方法与门控（14项）

- S1原MoveToSafePos顺序为收回测高气缸、Z移动、XY移动；不在方法中显式关闭点胶阀。任一动作抛异常会停止后续调用并向上抛，无本地恢复；离线直接返回。
- S2先检查离线，再经过原域WaitSingleStep门控；门控false可直接返回而不移动Z。正常仅当当前Z小于安全高度才发MoveAxisZ。
- 静态华夫盒区域边界采用当前Y>=避让位置Y；在区域内安全高度改为避让Z加吸嘴测高偏移，区域外保留普通安全高度。测试使用明确坐标替身，不推断现场轴方向。
- 两个原域WaitSingleStep只有IsSingleStepWork为true时才等待信号，关闭单步则直接true。新增测试证明S2关闭单步后即使测试信号设为false，安全Z仍正常提交。因此不能推断“停止状态必然阻止安全Z移动”。

## 接回生产调度（静态，非本次运行覆盖）

- S1 DispenseWorkTask对直接Retry执行continue；其他非Success先MoveToSafePos再Machine.Stop然后return。点胶节点把内部Retry转Alarm，因而进入后一路径。若安全移动抛异常，后面的Stop无法从这段顺序保证；不能将此静态可能性描述为已运行完整任务复现。
- S2 BondTask对Alarm显示Abort/Retry/Ignore选择：Abort先Stop再安全Z（按配置再退胶盘），Retry跳回RetryCommand，Ignore继续到FinishCurrentActionNode。对直接Abort/Exception也先Stop再安全Z。选择Ignore可能推进动作索引而本节点未执行完成标记，后续状态由实际调度器决定。
- S2该switch没有Fail分支；单步/Start产生的Fail与Alarm不能混为一谈。缺省落到后面的FinishCurrentActionNode，这是所见代码结构，不是完整运行测试。
- Machine.Stop清状态/弹窗/报警/单步/需料及顶针真空等；它会把IsSingleStepWork设false，但没有显式调用点胶阀关闭。不能把停止报警、关顶针真空、收测高气缸或安全Z当作关点胶阀。
- 此处没有证明各间接服务、轴库或外部回调都不关胶，也没有确定物理阀最终状态。EmergencyStop和硬件保护仍沿用既有停止报告的边界，完整系统退出未验收。

## 复现与限制

运行`node scripts/test-dispense-node.cjs`和`node scripts/build-dispense-node-audit.cjs --check`。回执绑定六个原方法、行号、全文件/片段及测试文件哈希；审计另保存任务分派片段和普通Stop方法原文。

控制器插补、预点胶、信号内部、配置、坐标转换、通知、UI和统计全部为惰性替身；这些替身只记录当前测试中的调用与状态。没有编译完整ActionNode类或验证Fody通知；没有把此测试与上一轮真实克隆/完整GuGao方法拼成已运行的端到端链路。无硬件连接，不修改生产源码，29组仍部分复核。
