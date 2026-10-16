# 原始数据库保存线程与停止调用边界

原生CLR4.0.30319.42000宿主30项检查通过；另一个隔离完成队列进程在终止前通过12项检查，两进程共享8个标签，共34个不同断言。完整原Main1137编译项/资源及16个源码/资源程序集实际加载路径、SHA保持父证据一致。宿主EXE、完整正常运行JSON、异常事件JSON、子进程退出记录和19个选定原方法IL独立重放一致。43份新增冻结绑定加3418父绑定共3461份。生产C#、工程、单例、队列、任务和私有状态未改写。16工程/29组/1436文件/13项整体仍未完成。

## 原始消费线程确实运行，数据库连接保持未创建

[StatisticsService.StartSaveThread](../../trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsService.cs#L97)在私有thread为空或不存活时创建原Thread(SaveEntityToDb)，名称“数据库存储线程”，IsBackground=true。用只读反射观察thread与[DBService原Lazy](../../trunk/AKRS.ZX2200/Infrastructure/Service/DBService.cs#L27)，从不访问Instance.Value。宿主只添加不属于四种数据库模型的object/string/int/数组/List，避免原SQL连接、建表和CleanInfo的实际副作用。Lazy.IsValueCreated在所有检查和异常事件中均为false；不调用实际DBService.Instance/Insert，也不替换它们。

先用真实队列Add填500个普通object，再让一个普通测试生产者在真实Add等待。100ms观察窗口内生产者未返回；原StartSaveThread启动后它返回，原消费者取走501项。接着4种其他未知对象以及2个flag测试字符串，共507项被取走。未知对象通过全部is分派后直接回到Take，没有保存或回队分支；这验证未知输入被移除，不证明真实日志入库。20次顺序StartSaveThread复用同一个实际存活消费者；原方法没有锁，未测试并发Start竞态或故障后重启。

[RuntimeProvider.ThreadFlag](../../trunk/AKRS.Galaxy2.MachineSupport/RuntimeProvider.cs#L43)是原公开volatile字段。它为false时原保存线程仍能启动、消费并在空队列等待；true再false后仍消费同一线程。原consumer IL没有读取这个字段，也没有Sleep/cancel/CompleteAdding处理。false时Join的100ms观察窗口未结束，正常宿主返回时保存线程仍存活且为后台线程；进程返回exit0由后台线程属性允许，不是保存线程的优雅停机。没有把测试生产者当作原消费者。

## 完成空队列会使原始消费者的异常终止宿主

隔离原生子进程先启动原消费者、确认空队列等待和Lazy未创建，再用真实原集合CompleteAdding制造明确的故障输入。原Take抛System.InvalidOperationException，原SaveEntityToDb没有catch。AppDomain.UnhandledException只记录事件，不抑制异常，不主动退出。事件记录isTerminating=true、当前线程就是原私有thread、IsBackground=true、集合已完成，异常栈含BlockingCollection.Take和原SaveEntityToDb；16个源码/资源程序集加载路径仍匹配。Windows Node观察退出码3762504530，即有符号-532462766/CLR异常0xE0434352。子进程实际失败，外层记录器exit0仅表示成功记录并核对预期失败。

CLR最后打印的stderr没有原栈，只提示Exception.ToString失败；原异常完整栈已在UnhandledException事件中保存。此格式化失败原因未定位，不能把它写成数据库错误。正常与完成子进程各有独立日志；原源码检索没有该队列CompleteAdding生产调用，所以不推断生产现场正在关闭队列，也不推断原程序常规退出一定触发此路径。

## 已识别日志与SQL错误只完成原方法静态核验

[SaveEntityToDb](../../trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsService.cs#L110)对OperateLogEntity、DefectStatisticsEntity、BondPositionLogEntity直接调用Insert；ParameterChangeLogEntity还要求运行类型存在SugarTable属性。这四个调用在原IL中保持，均未运行。取出之后没有队列确认、回队或重试；[DBService.Insert](../../trunk/AKRS.ZX2200/Infrastructure/Service/DBService.cs#L84)在try里访问Instance/CopyNew/Insertable.ExecuteCommand，catch(Exception)记录日志后返回。正常catch完成的路径会吞掉SQL错误；若日志记录本身抛异常，它位于catch体且没有下一层保护，这是源码/IL推断，尚未连接SQL或运行日志故障。

原DBService构造器硬编码localhost/ZX2200/Trusted_Connection=True，创建SqlSugarClient后依次尝试八类表，再CleanInfo调用八类清理方法。原Lazy静态初始化仅构造Lazy；真实数据库权限、架构、保留条件执行效果、吞吐、断连/锁等待及重试持久性仍待验收。[SaveEntity](../../trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsService.cs#L77)重复消息门控先于日志创建，Add成功才更新lastMessage与LastOperaDateTime；本轮没有执行这个已识别生产者。

## 停止按钮及退出方法的异常传播属于静态证据

[后台监控](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L659)原lambda检查ThreadFlag，然后依次安全门、激光尺、自动登出、温度、耗材、扫描信号、存图、数据库StartSaveThread、Sleep100。原IL无catch；此前调用抛出可能阻止本轮到达数据库启动，这是调用顺序推断，完整监控线程未执行。

[取消按钮](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L758)先Enabled=false、设置停止提示，再Machine.Stop；本方法没有catch/finally或本地重新启用界面的步骤。因此前70项原Stop所验证的日志背压或设备/队列异常，在这个调用体没有本地恢复保护。未构造UI，其他事件或刷新是否随后恢复界面未核验，不能说界面永远禁用。BtPause也是直接原Pause调用，无catch。

BtStart与Production的BarItemStart两个原按钮都在catch中调用Machine.Stop，然后显示启动失败；IL确认Stop在catch体内，而Enabled=true的finally涵盖这个catch。若Stop抛出，错误对话框无法到达，但仍进入该finally尝试重新启用控件；如果Stop阻塞，则finally尚未到达。这是两种独立的源码/IL分支，不是运行过真实UI的结论。

[ExitSoftware](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L706)执行保存/关闭硬件/启动画面操作，catch后Environment.Exit(0)。原方法没有关闭统计队列、Join保存线程或设置ThreadFlag；从方法体看没有等待日志排空协议，但未执行退出UI/硬件，不能据此估计实际丢失量。正常宿主的后台线程结束语义与该原退出方法静态证据分别登记。

## 保留失败及剩余验收

首次宿主编译成功，但检查0时因测试路径末尾分隔符比较失败，实际exit1；修正测试路径规范化，保留失败运行JSON与原Cases。首次核验误要求CLR stderr含原栈，第二次误要求stderr为空，两次exit1与失败核验脚本都保存；冻结前修正为观察到的Exception.ToString提示，原业务方法不改。一次修复命令被PowerShell引号解析拒绝，未执行Node或新宿主，记录保留。当前核验68939实际exit0；主原生流水线1d0823和重放f08ffa实际exit0，完成子进程错误码保持。

见[测试](native-db-saver-test.json)、[审计](native-db-saver-audit.json)、[进度](native-db-saver-progress.json)。此前70/100/180/251/58、正式1328、受控278/目录119、98/124和40专题3817计数独立，LC5/Fody2/VM5失败不改写。接下来继续实际已识别日志的持久化与SQL错误、原SaveEntity去重/背压边界、其他队列/等待/异常退出链、生产配方重建、在线动作下层、就绪负分支、PR/校准/测量、IO及完整构建/部署/UI/设备。
