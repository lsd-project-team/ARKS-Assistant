# 原始操作日志生产者与AOP异常记录核验

60项原生CLR4.0.30319.42000检查通过；宿主EXE、完整运行JSON、进程结果、34个选定原方法IL独立重放一致。完整原Main1137编译项/资源与16个源码/资源程序集实际加载位置、SHA保持父证据一致。新增30份冻结绑定+3461父绑定=3491。生产C#/工程、原类、构造器、单例、队列、SDK广播和私有状态未改写。16工程/29组/1436文件/13项整体仍未完成。

## 只按上一条成功入队的消息文本去重

完整执行[StatisticsService.SaveEntity](../../trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsService.cs#L77)，队列由原静态初始化创建，容量500，数据库保存thread保持null。lastMessage只读观察，LastOperaDateTime也没有测试赋值。方法先比较message==lastMessage；不同时调用原SDK LogHelper.Post，再构造真实[OperateLogEntity](../../trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/OperateLogEntity.cs#L15)，Add成功后才更新lastMessage和LastOperaDateTime。原IL没有锁/Interlocked、规范化、catch或失败回退。

- 初始lastMessage=null，所以首次null消息直接被抑制，活动时间保持default。成功记录其他消息后再次null则产生真实null Message/Technician实体；连续null又去重。
- 连续相同文本即使Technician不同也被抑制，活动时间和SDK最新日志对象均不变；不同string对象但相同字符也去重。不是按操作者、对象地址或异常对象去重。
- alpha→beta→alpha三次中后两次都能入队；只比较上一条已成功入队文本，没有全局历史去重。空字符串接受一次；大小写和首尾空白保留，并分别入队。
- 真实模型ID仍0，DateTime在调用前后时间窗口内，LastOperaDateTime不早于构造时间且不晚于返回。这里只比较运行时关系，不把实际DateTime.Now序列化进重放JSON，避免把时间值相同误作可重放依据。模型对象不是替身。

## SDK原日志路径在数据库分支之前返回

原主程序集调用实际trunk/libs/AKRS.Galaxy2.Log.dll，传Trace、Global=8、ViewType.InFile=0。SDK LogHelper.Post创建真实LogDataEntity，向原LogsManager.LogDataBroadcastBlock发布，然后调用原LogDataInDB。SDK原IL只在ViewType.InDB=2或All=4继续get_DB/Insert，0直接返回。用只读反射检查SDK dbInitializationAttempted=false、dbInstances=null，并检查主工程DBService原Lazy.IsValueCreated=false；所有成功、阻塞、并发和异常输入后仍成立。没有调用SDK DB/get_DB或主工程Instance/Insert，没有SQL连接/建表/清理，也没有更换数据库配置以制造通过。

宿主使用自己的实际Application.StartupPath与AppDomain.BaseDirectory；Log4Net.config和Probe.exe.config自然不存在，原SDK从这个目录Configure并创建自己的BroadcastBlock/文件ActionBlock及LinkTo。测试仅对原BroadcastBlock调用公开TryReceive观察最新消息，没有换广播、加观察目标或修改私有状态。SDK广播克隆函数返回同一个LogDataEntity；实际当前对象引用可以证明重复消息未再Post，失败重试则有新日志对象。广播只保留最新值，不据此声明每条Trace均被文件写入器消费；原SDK内部Dataflow调度没有计为业务任务数量。宿主stdout诊断和stderr均为空，没有生成日志/可执行配置文件；实际文件日志写入与UI日志订阅未验收。

## 满队列：日志已发布，消息提交和活动时间尚未发生

真实原队列用500个普通object填满，普通测试调用线程执行完整SaveEntity(新消息)。原SDK新日志对象已可观察、ThreadName等于实际调用线程名；100ms内调用未返回，队列500，lastMessage与活动时间仍旧值。公开TryTake取走一项后，原调用返回，最后一项是真实OperateLogEntity，499个普通输入在前；消息和活动时间随后提交。

队列再次满但消息等于上次成功消息时，另一完整原调用直接返回，不Add也不Post，即使操作者不同。该调用不能用于证明消费者恢复；本轮原数据库消费者从未启动，容量释放明确来自测试的公开TryTake。

## 同一消息的两个实际调用能在背压窗口都入队

再次填满原集合；线程1调用racing same message，观察其真实SDK日志与未返回状态，lastMessage仍blocked producer。在线程1未提交时线程2调用同样文本，观察到另一个新SDK日志对象及线程2名字，两个调用都已通过旧消息门控且队列仍500。释放两个槽后两个完整调用返回，真实队列含498个普通object和2个相同Message、不同Technician的真实OperateLogEntity。最终lastMessage是该相同文本。

这是原队列/方法在明确输入下的可重现并发去重缺口，没有人工写lastMessage、人工Task、替换Queue或替换SDK Post；4个普通fixture Threads中2个是并发输入，其余用于满队列和重复消息。两实体先后顺序随调度而变，检查比较操作者集合而不是强制某个顺序。它证明这个窗口允许重复，不估计常规生产的发生率，也不声称已观察现场事件。

## 关闭队列：重复成功文本可绕过，失败新文本仍会反复Post

排空原队列后CompleteAdding仅作为显式隔离故障输入；原源码未发现该集合的生产CompleteAdding调用。当前已成功消息再SaveEntity，因去重提前返回，即使集合已关闭也没有错误。新文本则先发布SDK Trace，再在原Add抛InvalidOperationException；栈包含完整SaveEntity，原lastMessage、活动时间和空集合保持旧值。重试相同失败文本仍发布一个新的SDK日志并再次Add失败，因为前一次没有提交去重状态。

因此“没有统计实体入队”和“没有SDK Trace副作用”不是同一个结论；SaveEntity本方法的源/IL顺序及真实失败边界分别验证。此处没有启动保存线程，未触发前一阶段已证明的空完成队列消费者异常终止宿主。

## 原AOP方法手动调用，自动拦截仍未证明

[MethodAopAttribute.OnEntry](../../trunk/AKRS.ZX2200/Infrastructure/AOP/Module/MethodAopAttribute.cs#L27)的0参数和不匹配控件类型的2参数输入直接返回，没有生产者副作用；OnEntry(null)在读取Arguments时NullReference，未到SaveEntity。OnExit为空方法，null参数返回。未构造WinForms/DevExpress控件、Machine单例或执行权限/按钮视觉路径。

手动调用完整原OnException，实际CurrentLoginUser自然为null，日志实体只有“界面操作异常发生”和null Technician，不含MethodExecutionArgs.Exception的原消息。原IL没有读取Exception属性。紧接着OnException(null)仍能返回，但相同通用文本去重、无第二条记录和活动更新；不同异常详情不会改变这个门控。

在上一成功文本已改为并发测试文本、真实队列完成时，再手动调用原OnException：原SaveEntity先发布通用SDK日志，然后Add失败，InvalidOperationException栈同时含原SaveEntity与MethodAopAttribute.OnException；异常记录方法本身可再抛异常，旧已提交消息/活动时间保留。没有执行真实UI异常或Fody织入，因此不声称这次覆盖了自动OnException回调、异常替换方式或织入后方法返回行为。既有5次LC和2次Fody原目标失败仍保持，不能用这项手动调用把Fody验收改成通过。

## 证据和剩余范围

本轮编译43789完成exit0、原生运行/IL流水线dace91 exit0、冻结前核验b93714 exit0、独立重放ca7c90 exit0；最终绑定核验58517完成exit0。本60项未出现宿主编译/运行或核验失败，父证据中的路径、stderr、许可证/织入/VM等失败不变。24项冻结先于重放，追加6项重放文件成为30，宿主源码与案例没有在冻结后修改。

见[测试](native-statistics-producer-test.json)、[审计](native-statistics-producer-audit.json)、[进度](native-statistics-producer-progress.json)。原生60与数据库消费者30正常/12故障、机器70、任务100、输送180、动作251、程序58、正式1328、受控278/目录119、98/124及40专题3817分别登记，不相加作全工程覆盖。剩余继续图片队列/消费者和其他等待/异常退出链、真实已识别日志数据库持久化与SQL故障、生产配方重建、在线节点下层、就绪负分支、PR/校准/测量/IO、匹配完整构建/部署和真实UI/设备。
