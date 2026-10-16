# 异步图片与数据库队列：入口、消费与温补分派缺口

更新：2026-09-29。范围为 `trunk` 内两条**进程内**队列的直接 `.Add`、已定位的包装器/委托、消费者与关机外层。对应 11 个源码文件的哈希、27 个行锚点及 5 处直接入队见[机器证据](async-persistence-ingress.json)；`node scripts/build-async-persistence-ingress.cjs --check` 复核。该扫描不等于反射、别名和第三方调用的完整生产者证明，也没有连接数据库、运行设备或执行队列。

[Archify 交互数据流图](async-persistence-dataflow.html)按“来源→进程内队列→后台消费→输出”并排展示图片与数据库路径；[图规格](async-persistence-dataflow.archify.json)与[浏览器回执](async-persistence-dataflow.visual-check.json)可复验。九项 Showcase 校验、四个桌面视口及两主题截图已通过；这仅验证静态图和页面，不是数据库或设备验收。图内 `PR 定位回调`、`图片队列`、`SaveBitmap`、`BMP 文件`分别对应下文图片链的[委托绑定](../../trunk/AKRS.ZX2200/Program.cs#L248)、[入队](../../trunk/AKRS.ZX2200/Infrastructure/Service/VisionService.cs#L244)、[消费](../../trunk/AKRS.ZX2200/Infrastructure/Service/VisionService.cs#L343)和[保存语句](../../trunk/AKRS.ZX2200/Infrastructure/Service/VisionService.cs#L351)；`状态 / 日志`、`温补结果`、`数据库队列`、`SaveEntityToDb`、`业务数据库`对应[生产入口](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.StateRelated.cs#L65)、[温补入队](../../trunk/AKRS.ZX2200/SupportFeature/Compensate/TemperatureCompensate/TpMarkCompensate.cs#L138)、[队列构造](../../trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsService.cs#L53)、[消费分派](../../trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsService.cs#L110)与[插入调用](../../trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsService.cs#L118)。红色入队分支强调下游未匹配的类型，不表示此入口未成功入队或现场已经丢数据。

## 图片：定位回调到 BMP 文件

1. [Program.Main](../../trunk/AKRS.ZX2200/Program.cs#L246) 将 `PREntity.SaveLocateImageAction` 绑定到 `VisionService.SaveVisionImage`；[PREntity](../../trunk/AKRS.Galaxy2.PR/Models/Entities/PREntity.cs#L520) 在相关定位/图像条件分支调用该委托。该回调链不同于直接 `VisionService.SaveVisionImage(...)` 的文本命中，不能因那些命中是注释就宣称没有生产者。
2. [SaveVisionImage](../../trunk/AKRS.ZX2200/Infrastructure/Service/VisionService.cs#L213) 按路径片段创建目录，把 Bitmap 原引用和文件名放入 `BitmapBlockingCollection`（244），本方法 catch 记录日志。队列在 [320–321](../../trunk/AKRS.ZX2200/Infrastructure/Service/VisionService.cs#L320) 以无容量参数构造；入队不等于文件已成功保存。
3. 主[设备监控循环](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L662) 在传感器检查后调用 `VisionService.StartSaveThread()`（690）；[启动方法](../../trunk/AKRS.ZX2200/Infrastructure/Service/VisionService.cs#L326) 在引用为空或线程不存活时启动后台线程。[SaveBitmap](../../trunk/AKRS.ZX2200/Infrastructure/Service/VisionService.cs#L343) 无限循环 `Take`，非空图片按 BMP 保存后 `Dispose`。这段消费体没有局部 catch、队列排空或成功回执；若 `Save` 抛出，随后 `Dispose` 不在 `finally`，不能保证释放。

## 两条队列的五处直接入队与数据库分派

|入口|入队对象/条件|源码|
|---|---|---|
|`Machine.SetState`|状态变化时构造 `ParameterChangeLogEntity`，更新状态后入队|[状态写入](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.StateRelated.cs#L52)|
|`PropertyChangeAop.OnPropertyChangedEvent`|通过初始化、非空、非相等和显示名等门控后，入队 `ParameterChangeLogEntity`|[属性审计](../../trunk/AKRS.ZX2200/Infrastructure/AOP/Module/PropertyChangeAop.cs#L47)|
|`StatisticsService.SaveEntity`|与上一条消息完全相同时提前返回；否则记录日志并入队 `OperateLogEntity`|[操作日志](../../trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsService.cs#L77)|
|`StatisticsDomain.SaveDataToDb(object)`|将传入的 `object` 原样入队；可见调用包括焊点、缺陷及两处温度补偿结果|[通用入口](../../trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsDomain.cs#L419) · [温补调用](../../trunk/AKRS.ZX2200/SupportFeature/Compensate/TemperatureCompensate/TpMarkCompensate.cs#L138)|
|`VisionService.SaveVisionImage`|第五处直接 `.Add`，属于图片队列而非数据库队列|[图片入口](../../trunk/AKRS.ZX2200/Infrastructure/Service/VisionService.cs#L244)|

数据库队列构造为[容量 500](../../trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsService.cs#L53)，满队列的 `Add` 可能阻塞生产线程；源码没有在此调用显式取消。设备监控循环调用[数据库线程启动](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L693)。[SaveEntityToDb](../../trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsService.cs#L110) 无限 `Take` 后仅对 `OperateLogEntity`、`DefectStatisticsEntity`、带 `SugarTable` 属性的 `ParameterChangeLogEntity`、`BondPositionLogEntity` 四种分支调用 `DBService.Insert`。没有默认分支、局部 catch、重试或写入结果反馈。

**可核对的缺口：**[TpMarkCompensate 的两处结果](../../trunk/AKRS.ZX2200/SupportFeature/Compensate/TemperatureCompensate/TpMarkCompensate.cs#L94)被声明并构造为 `TemperatureCompensationEntity`，分别在[138](../../trunk/AKRS.ZX2200/SupportFeature/Compensate/TemperatureCompensate/TpMarkCompensate.cs#L138) 和 [226](../../trunk/AKRS.ZX2200/SupportFeature/Compensate/TemperatureCompensate/TpMarkCompensate.cs#L226) 交给 `SaveDataToDb(object)`；[类型声明](../../trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/TemperatureCompensationEntity.cs#L13)未继承上述四个处理类型。按仓库所示消费者源码，若这类对象被该线程 `Take` 出队，就不会命中任何 Insert 分支。`DBService` [建表](../../trunk/AKRS.ZX2200/Infrastructure/Service/DBService.cs#L58)及 `StatisticsDomain` [查询](../../trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsDomain.cs#L351)并不能补出缺失的消费分派。**这是特定源码路径的静态结论，不是现场数据库已丢数据的实测结论。**

## 写库失败：原方法隔离检查（2026-09-29）

消费循环没有局部 catch，**不等于每次 SQL 写入异常都会终止消费线程**。[DBService.Insert](../../trunk/AKRS.ZX2200/Infrastructure/Service/DBService.cs#L84)把 `Instance.db.CopyNew()`、`Insertable(...).ExecuteCommand()` 和 using 释放放在 try 内；异常后仅调用日志函数，没有返回成功/失败状态、重抛或重入队。在日志函数正常返回的前提下，调用者继续下一轮 Take。若 catch 内的日志函数自身抛异常，则该方法没有第二层捕获，异常继续向消费者外传播；是否终止进程或怎样被全局处理，本检查不下结论。

[11 项隔离检查回执](async-db-consumer-test.json)记录了原方法全文、行号和源文件哈希。复跑命令：`node scripts/test-async-db-consumer.cjs`。

|受控场景|观察结果|
|---|---|
|写入正常 / ExecuteCommand 抛异常|前者释放复制客户端；后者也释放并记一次日志，然后返回|
|CopyNew / Dispose 抛异常|均进入 Insert 的 catch；没有写入结果回执|
|四种匹配类型|按入队顺序调用对应泛型 Insert；参数类型仍受 SugarTable 属性门控|
|温补类型后接操作日志|温补对象被取出但没有 Insert 或告警；后一个对象仍被消费|
|不带 SugarTable 的测试参数子路径|对象被跳过；此为控制场景，不声称生产类型缺少该属性|
|第一次写入失败后还有下一项|第一项不重试，第二项仍被取出并尝试写入|
|复制客户端连续失败|两项仍被取出，各记日志，不重入队|
|日志函数自身抛异常|异常离开 Insert 和消费者，后项尚未执行 Insert|

隔离环境抽取的是真实 `Insert` 和 `SaveEntityToDb` 方法；为旧编译器仅降级 using 声明、字符串插值和模式变量语法。SqlSugar、日志、单例、实体是显式测试替身；使用真实 `BlockingCollection`，但 `CompleteAdding()` 仅用于测试结束，生产代码没有因此新增排空协议。没有实际连接 SQL Server，也未测试并发、线程重启、UI、设备或生产模型映射。静态缺口与受控结果需要用现场版本和数据继续确认。

## 退出与工程师核验

[MainForm_FormClosed](../../trunk/AKRS.ZX2200/Main/Controls/MainForm.cs#L295)调用 `ExitSoftware`；[退出方法](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L706)尝试 `DataSave` 和硬件关闭后直接 `Environment.Exit(0)`，没有对两条队列显式 `CompleteAdding`、`Join` 或排空等待。需带实际配方/数据库与随附程序集版本在隔离环境核对：温补结果是否能写入、队列容量到达时生产线程的行为、消费异常后监控线程是否重新启动，以及退出时未落盘项的处理。不得以这份源码阅读替代生产设备验收。
