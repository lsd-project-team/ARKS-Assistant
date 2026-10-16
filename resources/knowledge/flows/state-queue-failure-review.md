# 状态日志队列、停止清理与供晶故障传播

本轮18项受控检查补齐状态日志失败和换片外层失败处理的限定缺口。SetState、Stop两个原方法未改写；另提取供晶catch及空跑分支原文执行。测试使用真实容量500的BlockingCollection，UI、日志实体和硬件服务是替身；PowerShell内置.NET编译运行，不等于现场.NET Framework版本、完整业务线程或设备验收。

## Stop状态不等于清理完成

[SetState](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.StateRelated.cs#L52)只有状态不同才构造日志、写入状态、Add日志。用户信息读取或日志构造异常发生在赋值之前；Add失败发生在赋值之后。[Stop](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L347)先调用SetState，再清弹窗、报警、单步、需料信号、在线输出、顶针真空和焊后计数。

|隔离条件|状态结果|后续清理|
|---|---|---|
|正常有容量队列|Stop，新增一条日志|按顺序执行，单步关闭、计数归零|
|队列CompleteAdding / Dispose / null|先变Stop，再分别抛InvalidOperationException / ObjectDisposedException / NullReferenceException|本次Stop后续清理均跳过|
|登录信息读取或日志构造抛异常|仍为原Working|后续清理均跳过|
|原状态已经Stop，队列已CompleteAdding|SetState跳过日志入队|后续清理仍可完成；不保证其他清理依赖成功|
|容量500已满，无消费者释放位置|已为Stop，Add阻塞|清理尚未开始，单步仍保留|
|上述阻塞时取走一项|入队恢复，Stop返回|清理继续完成|
|上述阻塞时CompleteAdding|入队抛异常，状态仍Stop|清理仍未执行|

队列容量来自[StatisticsService声明](../../trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsService.cs#L53)。[消费者启动与分派](../../trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsService.cs#L97)为独立后台Thread，循环Take；本测试故意不启动真实数据库消费者以确定性构造满队列。没有声称现场一定满队列，也未证明现场使用CompleteAdding/Dispose；后两者是受控失败条件。既有[数据库消费者检查](async-persistence-ingress-review.md)保留数据库写入及日志二次异常边界。

## 换片失败如何到达停止

[Dowork换片调用](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L132)在ChangeTabletAuto返回false时先写报警再抛异常；子调用直接抛异常则跳过此返回false分支，进入循环外层catch。不能将两者当作都已写入同一报警记录。

[外层catch](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L375)先显示错误弹窗，再Machine.Stop，无本地finally或第二层catch。三项真实Task包装的片段检查确认：弹窗与Stop都成功时原业务异常被消费，包装Task为RanToCompletion；弹窗抛异常则根本未调用Stop、状态保持Working；Stop的队列异常则Task为Faulted、状态已Stop但清理未开始。这里验证的是提取catch控制块与原Stop的组合，不是完整Dowork，也不将包装Task状态冒充现场供晶任务状态。

因此，错误弹窗阻塞期间尚未到达本catch的Stop；任务正常完成也不能单独代表供料成功；Task Faulted同样不能单独说明是否已经设置Stop。没有通过本测试证明全部硬件输出都关闭。

## 换片初始化返回与重试位置

[ChangeSucceedOperation入口](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L488)第一步StartInit；它抛异常时不会返回false，各调用点的goto分支也不会执行。初始化前缀残留见[已完成专题](wafer-start-init-review.md)。

|调用分支|返回false|抛异常|
|---|---|---|
|[空跑分支](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1107)|不读取结果，仍return true|向外传播|
|[料库静态向导](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1157)|回RetryChangeStaticAdapter，再开向导|越过本地重试，向外传播|
|[料库公共Operation](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1243)|直接再次执行初始化；本标签循环无显式延迟、次数上限或Stop检查|越过本地重试，向外传播|
|[无料库Operation](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1357)|回ChangeMap重新处理换料|越过本地重试，向外传播|

空跑原分支的6项检查覆盖有/无WaferTablet时子调用返回true/false，以及InitTabletInfo和ChangeSucceedOperation抛异常。存在WaferTablet时先写SlotState=Good再InitTabletInfo，即使后续抛异常，此赋值仍保留。没有模拟整套换片机械动作。

已完成的初始化也可能留下失败前修改：[自动地图定位尾段](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L550)在可选人工确认之前已更新参考点、保存、启动寻路并复位换片信号；随后人工Abort会抛异常。不能把任意异常都描述成换片标志必然仍为true；此分支本轮为静态复核，异步寻路和外部图库未执行。

## 验证与未完成项

运行 `node scripts/test-state-queue-failure.cjs`，18项通过：7项状态/队列条件、2项真实阻塞与释放、3项catch组合、6项空跑分支。所有原文范围和哈希随测试输出记录；[证据快照](state-queue-failure-evidence.json)绑定报告。失败注入不代表对应条件在现场已经发生。

- 已补齐：日志队列失败/满队列对原Stop的影响，供晶catch二次异常和空跑忽略返回值的受控验证。
- 仍待完成：真实数据库吞吐与后台线程存活、实际.NET Framework行为复核、现场调用入口和异常可达条件。
- 仍待完成：完整换片动作及所有重试路径的Stop观察点、输出安全状态、SDK与真实配置验收。
- 复用既有[换片业务分支报告](carrier-change-review.md)及[料库动作报告](magazine-transfer-review.md)，未把局部片段验证升级为完整换片或模块验收。
