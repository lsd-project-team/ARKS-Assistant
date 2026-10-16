# 生产任务重复启动与停止状态交错验证

后续集成（2026-09-30）：[原范围、完整初始化与真实供晶启动](wafer-range-init-review.md)的105项检查已将原Start、原初始化/位置/消费者和原Stop串联，验证失败后再启动及同步串行UI替身下的双Start竞争。实际MainForm/上层生产入口、SDK和设备仍未验收。本文原9项或47项隔离测试范围不扩大。


范围：五种原始Start方法，真实.NET Task与受控前置状态，业务循环、初始化、UI及Machine状态服务使用替身。47项通过，不是生产程序并发、完整Stop清理或设备安全验收。

## 五类启动门控

|原入口|Running旧任务|其余TaskStatus或null|状态写入|
|---|---|---|---|
|[供晶Start](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1373)|不创建|初始化后创建并替换引用|两个分支均写Working|
|[固晶Start](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L361)|不创建|创建并替换引用|此方法不写状态|
|[点胶Start](../../trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs#L189)|不创建|创建并替换引用|此方法不写状态|
|[滑动助焊Start](../../trunk/AKRS.ZX2200/BondSystem/Tasks/SlideFluxerTask.cs#L227)|不创建|创建并替换引用|此方法不写状态；先检查配置|
|[翻转Start](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/FlipTask.cs#L260)|不创建|创建并替换引用|仅创建分支写Working|

本轮每类测试null以及全部8种TaskStatus：Created、WaitingForActivation、WaitingToRun、Running、WaitingForChildrenToComplete、RanToCompletion、Canceled、Faulted，共45项。状态来自真实Task而不是枚举替身。滑动助焊配置保持已启用，不涵盖配置并发变化。

WaitingToRun样本使用受控TaskScheduler暂存旧任务；把它作为旧引用交给未改写的Start方法，新Task仍按原方法使用Default和LongRunning创建。验证旧引用被替换后旧任务依然WaitingToRun，随后释放旧调度器仍执行成功。此实验精确证明该门控面对该状态的行为，不证明生产Default调度器的排队窗口长度或现场重现频率。WaitingForChildrenToComplete由真实附属子任务形成，同样被放行；本测试没有认定生产业务实际创建了此类附属任务。

## 两个供晶交错场景

第46项：两个真实调用任务同时进入同一供晶对象Start。Block.StartInit替身内放置Barrier，让两方均越过原null检查，随后继续原方法。观察到两个真实工作Task进入替身业务循环，而对象字段最终只保留其中一个任务引用。测试退出时释放并确认两个业务替身都结束。这里没有修改原Start方法，也没有用重复调用次数推断线程数量；线程进入计数来自两个真实Task执行。

第47项：初始化回调把状态写为Stop，之后原Start再次写Working并启动工作Task。这是确定顺序的状态交错测试，不是完整Machine.Stop执行，也没有证明硬件清理与启动互斥。

## Stop与状态日志边界

[Machine.Stop](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L347)先SetState(Stop)，再处理弹窗、报警、单步、信号、输出、真空与计数；该方法没有Join全部工作线程。以上第47项仅模拟Stop的状态写入这一影响，未执行后续清理。

[SetState](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.StateRelated.cs#L52)先构造日志，再赋值MachineState，再向队列Add；赋值之后Add失败不意味着状态回滚。当前47项测试用简单状态服务替身，不验证真实日志构造、队列阻塞或Add失败。不能据此关闭原清单中的队列异常缺口。

## 可复现验证与剩余任务

命令：`node scripts/test-task-start-concurrency.cjs`。测试提取五个原Start方法编译执行，打印47条检查及源文件/片段哈希。包含超时及线程释放，未加载生产SDK或下发设备命令。源码快照见[证据](task-start-concurrency-evidence.json)。

- 已完成：五类入口全部TaskStatus的受控门控检查、旧排队任务引用替换后的可执行性、供晶双调用竞争的确定重现。
- 部分完成：Stop/Start状态交错；完整Stop副作用和真实任务退出仍待验证。
- 未完成：生产UI/定时器实际并发可达性、默认调度器现场时间窗口、业务循环共享状态的实际后果。
- 未完成：状态日志队列Add失败/阻塞、停止和硬件命令之间的全部检查点、真实SDK与配置验收。
- 后续：继续换片失败传播及状态日志队列边界，再回填模块旧缺口；29组仍部分复核、0组完整验收。
