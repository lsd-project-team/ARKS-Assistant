# 完整原输送Start生产器接入UI与真实供晶Task

2026-09-30：870项受控断言通过。完整656行TransportTask.Start、九个原任务字段及原上料配置枚举，接入原UI按钮、准备帮助方法、Machine.Start、TransportDomain.StartTask、供晶Start/搜索/消费者和完整Stop。组合编译含81原方法、31属性、4枚举、13字段，共129原片段，58份测试/依赖来源及23种真实信号契约。编译范围不表示所有依赖方法和分支均执行。

生产源码未修改。Task.Run、循环、TaskStatus检查、返回码分派和Signal等待均直接运行原代码。线程命名边界、九条控制器传输方法、TransportProvider日志/程式生命周期、警告/UI、配置/视觉/持久化/域/SDK为显式替身；Provider两个标志属性、区段状态属性和枚举也直接编译原声明；其程序对象生命周期与日志仍为替身。完整传输控制器与原生UI、设备验收继续保留。

## 配置与真实任务

| 上料配置 | 实际分配任务数 | 入口/出口分支 |
| --- | ---: | --- |
| None | 3 | 三条中部任务，无进出料任务 |
| Belt | 5 | 入料皮带、三条中部、等待区到出料皮带 |
| LoaderBin | 5 | 上料仓、三条中部、等待区到下料仓 |
| Online | 7 | 送板机、入料皮带、三条中部、等待区到出料、收板机 |
| OnlineWithAutoLoader | 6 | 同Online，但无收板机任务 |
| OnlineWithAutoUnloader | 6 | 同Online，但无送板机任务 |

两个原UI按钮各走全部六种配置，九个原字段与实际Task身份逐项比对。命名替身处的入口屏障使线程调度明确：UI已返回、输送任务均Running且尚未进入原循环，供晶LongRunning Task仍能接收新需料并发允许取料。重复直接调用生产器Start保留同一批Running句柄。

完整Stop在这些屏障处返回时，输送Task仍未完成、原IsAllowTaskClosed仍拒绝关闭。测试随后放行并逐个等待Task退出；供晶工作线程单独Join。Task.Run使用线程池，测试不Join复用的池线程。原Stop本身没有这些等待操作。测试把线程池最小工作线程数临时提高至至少64以避免屏障饥饿，最后恢复，不能当作原项目线程池配置。

九个字段各覆盖运行时八种真实TaskStatus。仅Running保留；Created、WaitingToRun、WaitingForActivation、WaitingForChildrenToComplete及三个终态均被替换。旧任务样本句柄保留到显式完成与释放；没有把覆盖字段解释为旧任务已经退出。此矩阵直接调用生产器，完整Machine.Start的准备步骤会先按原关闭谓词拒绝Running；[既有准备验证](readiness-helpers-review.md)仍保留这一调用边界。

输送禁用、DryCycle、补偿模式不会执行本完整Start；DryCycle仍使用既有StartDryRun替身。禁用S1不会删除三条中部输送任务。S1、Loader/Unloader、Bond、翻转等其他生产器仍是替身。

## 初始有料与停止被重写

None配置同步提示点胶台已有料，Yes发真实TransferToDispense1FinishedSignal，No调用完整Stop。No分支未退出Start：三条中部Task仍被分配，然后在出料段前返回。后续原供晶Start重写Working并创建真实消费者；两种原UI入口均不进入catch，新需料仍可得到取料许可。

这里以入口屏障控制全部输送Task在警告与后续供晶启动完成后才继续。原生产环境可能在Stop或Working不同时间启动循环；本轮明确验证所控制的调度，不声称唯一调度顺序。

皮带进料、仓式进料、点胶到Bond三条任务，各覆盖IsReStartWarn、有无初始物料、Yes/No。不提示时首次进入可直接发完成事件并继续调用传输；提示模式首次迭代无论有没有物料均continue，后续才调用传输。有料且No执行Stop，任务结束且不调用控制器；其他任务和真实供晶的退出由实际停止门控与显式收尾验证。

PrepareFeeding=false阻止送板机传输；ContinuousFeeding=false阻止皮带/仓式进料。按目标Task身份观察原状态读取，证明该线程已重复进入等待循环，然后恢复标志，实际控制器边界被到达。其余任务的状态读取不作为目标任务已到达的证据。

## 返回码与真实信号

九条任务各跑显式SDK替身的13个ExcuteResult值。Abort在九条中均执行Stop；Exception只在上料仓、Bond到等待区、等待区到出料皮带、等待区到下料仓执行Stop，其他五条没有对应Stop分支。NoStart的sleep、continue和底部延迟保持原文。本轮只检查行为次序与阶段，不把测量耗时当作设备时序验收。

Success只有入料皮带/仓到点胶1、点胶1到点胶2、点胶到Bond四条发各自完成事件；送板机和两条进料任务清PrepareFeeding。其他任务不由这个外层switch发布这四种完成事件。实际控制器内部仍可能有自己的信号与状态行为，待后续原控制器接入。

仓式两条任务的NoStart经continue保留手动推料事件且不发移动许可；Abort/Exception停止并return，也不复位推料。Success、None及其他未处理返回值会继续执行原尾部：复位推料并发送AllowLoaderMoveSignal或AllowUnloaderMoveSignal。测试检查实际EventWaitHandle而非用并发公开State推断事件消费。

## 暂停、停止与异步失败

九条任务在入口放行后先进入Pause，按目标Task的状态读取确认原WaitStart暂停循环，控制器未调用；改Working后进入实际控制器边界。

九条任务在控制器替身内阻塞时，完整Stop仍立即返回。随后控制器返回Success，原switch仍执行：完成事件、PrepareFeeding修改及仓式复位/移动许可可以在Stop之后发生。直到下一次循环门控才结束Task。此处证明原外层没有返回后再次检查Stop；不会把控制器替身里的挂起当作已验证设备运动。

九条控制器各注入抛错，原delegate catch显示提示，Task以RanToCompletion结束而不自动Stop，其他任务及供晶仍活动；UI调用已返回，UI catch不接收该异步异常。在线程命名边界注入异常时，该调用位于delegate try之外，真实Task变Faulted，无delegate提示或UI错误提示，Working仍保留。测试显式观察Task.Exception并结束其余所有任务。

## 复现与剩余项

`node scripts/test-transport-producer.cjs`执行870项唯一断言；`node scripts/build-transport-producer-audit.cjs --check`核验58来源、129原片段、23信号契约及30段专题快照。统一回归与阅读器页面检查另存集成回执。

下一步把已单独验证的原TransferBondToWaitingUnload及轴/解夹/信号链接入本完整生产器，再接其他八条原传输方法及真实载具检查、MapMaterial、Provider/区段/池/域/SDK。现场DLL和配置、原项目构建、原生UI事件/控件生命周期与设备验收仍未完成。29个源组保持partial，不提高总体覆盖比例。
