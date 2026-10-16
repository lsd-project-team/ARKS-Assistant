# 生产任务启动顺序与部分启动失败边界

后续组合验证（2026-09-30）：[完整正常启动与真实供晶Task](normal-start-integration-review.md)通过175项检查，将完整准备包装、输送StartTask、供晶Start/消费者及Stop接入。准备帮助方法、输送/其他生产器和原生UI仍为替身或未执行；本文30项隔离测试的自身范围不扩大。


范围：Machine.Start 调度方法及三个具名调用点；原方法隔离执行，不是任务线程、SDK或设备验收。

## 实际执行步骤

[Machine.Start 261–309](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L261)：PrepareMachineReadyToStart 返回false则直接返回；否则先SetState(Working)。非补偿模式调用输送StartTask、供晶Start；配置S1且非补偿模式再调用点胶Start。之后无论是否补偿模式，均执行ActionNodesService.Init和BondTask.Start。滑动助焊、翻转分别受其配置及非补偿模式限制。最后依次调用两种华夫盘真空检查开启包装。

这是同步调用顺序，不是各线程动作完成顺序。固晶Start通过Task.Factory.StartNew使用CancellationToken.None和LongRunning启动工作，末尾return true，没有等待工作结束：[BondTask.Start 361–377](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L361)。其他任务入口与循环前动作参见[既有任务门控报告](production-task-start-gates-review.md)。

## 中途失败与正常返回

|触发情况|本调度方法后续行为|不能据此声称|
|---|---|---|
|准备检查false|正常返回，不设置Working、不发起后续调用|所有调用方能够识别失败；Start返回void|
|准备检查抛异常|向调用方传播|准备阶段没有副作用|
|设置Working或后续任一步同步调用抛异常|当前调用截断，其后的启动及真空调用不执行；方法无本地catch/finally补救|此前已启动的任务自动停止或资源自动回滚|
|输送StartTask内部Stop后正常返回|Machine.Start继续调用供晶及后续步骤，没有立即检查状态|设备必定保持Stop，或必定继续机械运动|
|任务Start正常返回|继续下一步，调用方未消费bool返回值|返回true等于线程执行成功或所有子任务已就绪|

输送真实Abort分支调用Stop后return；内部try异常被日志和弹窗catch处理，若catch自身正常返回则不重抛：[TransportDomain.StartTask 84–141](../../trunk/AKRS.ZX2200/TransportSystem/Models/TransportDomain.cs#L84)。调度测试中的“返回false”只是检查调用方未读取结果的防护用例；不表示当前BondTask实际存在返回false分支。

## 不同入口的恢复边界

- [BarItemStart_ItemClick 68–110](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L68)捕获同步启动异常，先调用Machine.Stop，再提示启动失败，finally恢复Enabled。若Stop自身抛异常，后续失败提示不会执行，finally仍尝试恢复Enabled。这是静态控制流结论，本轮未隔离执行界面处理器。
- [BtStart_ItemClick 699–736](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L699)也具有上述catch/finally。这里只说明具名方法，不据此认定该入口在所有版本界面均已绑定。
- [补偿采集按钮 91–123](../../trunk/AKRS.ZX2200/SupportFeature/Compensate/MotionAreaCompensate/FrmAutoCompensate.cs#L91)先清采集数据并将采集状态改为Collecting，再调用Machine.Start，随后启动轮询定时器；此方法没有本地catch/finally。Start正常返回（包括准备检查false）仍到达轮询启动；若Start同步抛异常则不会到达轮询启动，也未在本方法恢复采集状态。外层全局处理和实际UI运行未验证。此入口未在所示方法设置IsCompensateWork，不能仅凭窗体名称推断其模式。
- [Machine.Stop 347–378](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L347)设置Stop，清弹窗、报警及单步模式、重置需料信号、按Online关闭要料输出、关闭顶针真空、清焊后计数。此方法未等待、Join或取消所有Task；它不是已证明的完整启动事务回滚。各任务如何观察Stop需结合既有门控报告及后续并发验证。

## 30项隔离检查

运行 node scripts/test-production-start-launch.cjs。脚本从当前源文件精确提取261–309行的原Start方法，编译到临时.NET程序；配置、域、任务、准备检查和真空控制全部为记录调用的替身，无设备操作。

- 16项：8种S1/助焊/翻转配置组合，分别在普通与补偿模式核对顺序。
- 2项：准备检查false与抛异常。
- 10项：设置Working及其后每个同步调用点注入异常，核对调用前缀与异常向外传播。
- 2项：任务false返回值不被消费；输送写Stop后正常返回仍继续后续调用。最后一种替身不模拟真实供晶Start再次写Working，其真实行为见既有报告。

检查不执行实际工作线程、不证明任务已终止或机械安全状态、不覆盖模式及配置并发修改、队列异常、真实真空输出。所有参数保持稳定，未覆盖各个配置Getter自身抛异常。

## 证据及未完成项

机器可读快照见[源码证据](production-start-launch-evidence.json)，统一阅读入口见[模块源码阅读器](module-source-explorer.html)。报告及源文件均有哈希绑定。

- 尚需追踪供晶Block.StartInit失败后的状态与资源残留。
- 尚需验证Stop与Start并发、WaitingToRun重复启动、任务内部故障通知的完整链路。
- 真正完成状态必须结合工作线程退出、队列和设备反馈，不能用Start返回代替。
