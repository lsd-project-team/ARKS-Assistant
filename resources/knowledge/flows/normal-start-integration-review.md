# 完整Machine启动与输送包装接入真实供晶Task

后续调用者组合（2026-09-30）：[原UI启动与模式处理](ui-start-mode-review.md)通过262项检查，将原按钮处理方法、Dock/单步和枚举派生属性接入实际供晶Task及完整Stop。同步异常现在由原UI catch停止，内部正常返回失败仍绕过catch。控件/事件派发为明确替身，原生UI未验收；本文件自身测试范围不扩大。


后续组合验证（2026-09-30）：[原准备帮助方法与实际供晶Task](readiness-helpers-review.md)通过303项检查，将原信号复位、关闭、日志、初始化、环境和容量包装接入完整启动。原Running关闭拒绝前已清除需料/取料事件，现有实际供晶Task随后等待新请求。本文件原测试的隔离/依赖替身范围不扩大。


2026-09-30：175项受控断言通过。完整原`Machine.Start`、`PrepareMachineReadyToStart`、`TransportDomain.StartTask`与`IsWorking`接入上一轮原供晶Start、完整搜索初始化、位置/搜索/消费者及完整Stop。编译包含67个原方法、19属性、2枚举、3字段，共91个源码片段；这是编译范围，不能解释为全部方法、分支均在本轮执行。44份测试/依赖文件及三信号初始化均校验SHA-256。

## 本轮结论

输送载具检查返回false时，原StartTask调用完整原Stop并返回。外层Machine.Start没有状态复查，随后调用原供晶Start；它重新写入Working并创建真实LongRunning Task。本轮等待实际消费者进入运行态，再发送真实需料Signal；任务执行原搜索/消费者，最终发出真实允许取料Signal。输送MapMaterial与transportTask.Start没有被调用，点胶、Bond、翻转等后续启动调用仍发生。后续任务生产器是记录替身，不能据此声称这些实际设备任务已运行。

输送Init、载具检查、在线信号设置、反向刷新、映射、上下料Start或输送Start抛错时，原包装catch记录并显示错误后正常返回；真实供晶Task及外层后续调用仍启动，没有隐式Stop。若catch自己的日志或对话框抛错，则异常穿透到Machine.Start调用者，供晶未启动，但之前写入的Working保留。对日志/对话框的故障为明确注入的依赖行为。

供晶地图CreateForm抛错被原供晶Start捕获后，transportTask.Start已被调用，供晶任务没有创建；外层仍继续调用Bond等并保留Working。供晶错误提示自己抛错时，异常穿透，后续Bond调用被截断，先前输送调用仍保留。

点胶Start、排序Init、BondStart、助焊Start、翻转Start或两种真空包装调用抛错时，Machine.Start没有catch或回滚。真实供晶Task仍在Working中等待；清除注入故障并发需料信号后，它继续执行原消费者并发许可。测试最后显式执行完整原Stop并Join实际供晶工作线程。并未用替身任务的异常代替真实供晶线程结果。

## 门控及顺序

16种配置/补偿组合验证原顺序。补偿模式仍执行准备阶段的点胶/Bond安全位置调用、未屏蔽顶针的轴调用及计数初始化，随后跳过输送、供晶、点胶、助焊、翻转启动；排序、Bond启动及两种真空检查调用保持执行。3种上下料配置×反向开关验证在线信号、反向刷新及LoaderBin上下料分支。DryCycle调用输送StartDryRun替身并跳过正常载具/映射检查，仍创建真实供晶Task。未配置输送也仍创建供晶Task。

总复位标志、任务关闭检查、机器初始化、安全门、已有Working及环境检查拒绝时，准备包装依原顺序提前返回；在拒绝之前已经调用的清理/信号复位/缺陷初始化不会撤销。11处准备依赖抛错均在启动任何任务之前穿透。门配置关闭时，门未关闭不阻止启动；顶针屏蔽时不查询/移动该轴。轴移动替身明确返回Fail，原包装忽略其返回值后继续。这只证明调用点没有消费返回值，尚未验证实际Axis返回契约。

在任务关闭替身返回true的本轮场景中，再次调用已经Working的Machine.Start仍先调用准备清理、信号复位与缺陷初始化，然后由原IsWorking阻止再次启动；原供晶Task保持同一引用。ResetMachineSignal在本轮为记录替身，此断言不证明真实需料信号会被清除；原复位内容待下一轮接入。原IsAllowTaskClosed的静态代码会在IsWorking之前拒绝Running任务，此场景须接入原关闭检查后重新验证。

## 执行范围与复现

`node scripts/test-normal-start-integration.cjs`运行真实.NET Signal以及原67方法的组合。`node scripts/build-normal-start-integration-audit.cjs --check`验证175个唯一断言、44份来源、91片段的文件/偏移/行号/内容哈希与专题证据。上述两项纳入统一回归。

准备帮助方法（含CleanFile、ResetMachineSignal、IsAllowTaskClosed、MachineInitSuccess、CheckOperatingEnvironment）、安全移动、其他任务生产器、TransportTask.Start/StartDryRun均是显式记录替身；没有删除磁盘文件或调用硬件。配置对象、地图/串行UI派发、线程命名、点运算、视觉/标定、驱动和持久化沿用受控替身。原生UI两个启动入口仅静态快照，尚未执行它们catch中的Stop。实际生产Task及现场UI并发的可达性仍需继续验证。

本轮扩大了[原启动隔离分析](production-start-launch-review.md)与[原范围/供晶启动](wafer-range-init-review.md)的组合执行范围。完整TransportTask.Start生产器、真实准备帮助方法及实际UI启动/模式入口是后续项；原DLL/配置、原项目构建、SDK与设备验收尚未完成。全部29源组仍为partial，本专题不增加项目覆盖比例。
