# 原始任务退出与配方初始化核验

100项原生CLR4.0.30319.42000检查及独立重放通过。新增54份冻结绑定父3322份，共3376份。业务程序集使用原Main1137份Compile源码及资源产物，16个源码/资源程序集的实际加载位置与SHA核对通过；原C#、SDK单例、机器状态类型、路径和构造器没有替换。测试宿主是独立新代码。整体16工程/29组/1436文件/13项仍未完成。

## Pause到Stop的返回边界

[原Signal.WaitStart](../../trunk/AKRS.Galaxy2.Machine/Models/Signal.cs#L202)进入时遇到Stop返回false；Pause时每轮睡眠20ms。Stop判断在while体内，while条件只判断Pause。如果在睡眠期间变为Stop，下次while条件不成立，直接落到末尾return true。两次直接门控线程分别在Pause等待期间释放到Stop和Working，本次原生运行及重放均返回true。线程只调用原Signal，不运行业务任务或硬件；这证明一个可复现的路径，不断言所有调度下Pause→Stop都必然返回true。源码还存在Pause条件与循环体Stop检查之间的窄窗口，可能返回false。

直接测试Working、Operate、Teaching、Preparing及未定义999状态均返回true，说明该门控没有限定仅Working。由于这个Stop边界，撤下原计划的整段暂停任务释放测试：S1/S2外层while一旦得到true，会先调用安全位置/焊头动作。没有把“设置Stop”当作进入设备前的可靠隔离。原业务任务Pause/Working循环、正在运行任务的Abort行为仍未原生核验。

## 两个原任务在Stop时的真实行为

- [S1 DoWork](../../trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs#L63)先调用完整ActionNodeController.Init，然后检查Signal。原任务在Stop也会重建排程并清掉已完成消息。ProcessSteps=null时，原getter.FindAll抛NullReferenceException，WorkMessages已清空。通过原Start建立的真实Task呈Faulted，Wait抛AggregateException，恢复真实工序集合后再次Start会创建新Task并恢复排程。
- [S2 DoWork](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L100)先ResetInformation，十个原运行字段确实恢复默认值，然后检查Signal；已建排程对象及完成标记保持，没有像S1一样在此入口重建。
- 两个原Start在Enable=false、MachineState=Stop时仍返回true并创建LongRunning Task。六个实际创建任务中五个正常结束，一个以上述初始化异常Faulted；重复Start在已完成或已故障之后更换Task引用。未测试WaitingToRun或Running时重复Start的竞争。
- S1 AbortThread在尚无Task时空引用；对本次已完成原Task调用Dispose成功。S2 AbortThread为空方法，两种场景都无动作。选定IL记录S1仅Task.Dispose、S2无调用，两段Start均使用CancellationToken.None。没有把Dispose或空方法认定为运行中取消成功。

独立门控线程2个，业务暂停任务0个。业务任务始终在Stop启动；成功运行末态Stop、所选Task均结束、实际SDK硬件仓库为空且硬件/限位配置文件仍缺失。这里的硬件边界来自原路径和入口检查，未使用替身设备。

## 执行真实配方初始化辅助方法

[UcMainSystem.InitProgramNodes](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L124)编译IL为非虚实例方法，不读参数/this/实例字段，按Product→Transport→Bond→System1→Wafer→Process调用六个原初始化入口。只读Cecil核验后，用open Action<UcMainSystem> delegate、null receiver执行这个完整原方法。没有构造UcMainSystem，没有未初始化对象，没有复制它的源码作为替身，也没有反射写私有单例。成功3次、独占晶圆参数文件锁失败1次。

固定A/B/C三个隔离配方目录均无这六个保存的配方文件；本轮核验缺失文件时的真实构造/切换合同，未覆盖既有复杂配方反序列化。从A切B及B内部重复初始化后，六个原单例均换为新实例，FilePath均指向当前RecipeID；两个系统域、输送域和输送控制器自身不换实例，其程序getter读取新单例。

五个既有输送子控制器的基类SubSectionProgram仍引用A的旧载台。固晶控制器派生bondSubSectionProgram getter读取新B，而基类引用保持旧A。原A载台UpdateTransportUnit生成的真实树仍在旧对象中，新域TransportUnit为空；S2公开GetNext选出的真实焊点缓存和原消息对象仍旧。前一阶段只执行SDK Load，本阶段在生产页面真正调用的初始化辅助方法中复现同一引用分离。但没有构造生产页面或执行整个ReLoadRecipe，仍需检查其他入口是否重建控制器、如何使用这些引用，不能推断所有派生设备动作都读旧基类引用。

## 晶圆清理、保存与部分提交

[WaferSystemProgram.InitWaferSystemProgram](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/WaferSystemProgram.cs#L70)在清除单例前调用ClearWaferSubMemory。真实设备参数构造在OffLineWork取原相机坐标零值，清理替换当前Tablet为NullTablet、Magazine层号归0、标记Magazine需重建，并通过原SingletonJson/SDK JsonFormatHelper真实Save写入宿主参数文件。IsClearStaticAdapter=false不置位静态盒重建；true会在第二次Save前置位。两条路径都保留CurrentStaticAdapterTablet对象，不能把“清理静态盒”描述为此处立即重建对象。

FileShare.None独占既有WaferSubDevicePara.json后，辅助方法在第五个Wafer入口失败：前四组单例的清空与路径切到C已经提交；Wafer尚未执行自身路径/instance清空，Process入口尚未执行，二者保留B。清理的内存Tablet/层号/Magazine标记已改变，第一次Save异常使后续静态盒标记步骤跳过；磁盘原字节仍保留。Wafer catch以new Exception(e.Message)丢失InnerException，SDK Save也有消息包装，open delegate另外包装TargetInvocationException。释放锁后再次调用原辅助方法，六个单例与路径均归C，真实保存恢复。

只读IL确认[ReLoadRecipe](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L137)的辅助方法调用offset142，而catch/finally保护从offset148才开始。由此推断初始化异常不经过后面的Enabled恢复finally；生产页面此前已禁用并显示提示，这是源码/IL路径判断，未执行实际控件来验证最终界面状态。完整UI、VM/PR重载及后续启动仍未通过。

## 重放与失败记录

宿主EXE、38个选定Main/Machine/SDK方法（含两个Start lambda）的IL与运行断言/物理程序集绑定重放一致。实际晶圆JSON两份原始快照都冻结；两个原构造器DateTime.Now字段（/WaferTableDevicePara/CurrentTablet/CreateTime、/WaferTableDevicePara/CurrentStaticAdapterTablet/CreateTime）不同，因此不声称文件字节一致。去除且仅去除这两个命名字段后，其余整个解析对象一致。运行结果只在比较时排除该文件SHA/字节长度摘要。时钟命名的备份由原CopyFile实际产生，原始主轮备份/捕获元数据保留，活动输出目录不纳入不可变冻结清单；未宣称备份数量/名称或字节重放一致。

早期错误与中断均保存：v1在11项之后因错误预期Pause→Stop为false失败；v2/v3隔离宿主出现原消息窗口并未返回，精确核对进程路径后终止，两个终端会话最终-1，不计通过。v3逐项日志定位到未有TU时的S2 GetNext，源码InitCurrentMessage在空引用catch中显示原消息框；未读取弹窗文字或自动关闭。补上原UpdateTransportUnit调用才继续。v4在85项之后仅因宿主用无空格字符串判断漂亮格式JSON而失败，改为解析实际字段；v5为95项，95条断言名称/顺序保留为最终100子序列。一次IL检查扩展的PowerShell逻辑分组错误被receiver guard拒绝、actualexit1，修正宿主检查脚本括号，原程序集未改。

见[测试](native-recipe-task-lifecycle-test.json)、[审计](native-recipe-task-lifecycle-audit.json)、[进度](native-recipe-task-lifecycle-progress.json)。本100与原生180/251/58、正式1328、旧受控278/目录119以及98/124分开，不相加认定覆盖。原LC5/Fody2/VM5失败、388资源1498条与40专题3817快照保持。下一步推进任务暂停/退出及真实配方入口的重建调用、其他等待与异常传播、在线节点/下层算法、PR/校准/测量/就绪负分支、IO稳定性和匹配构建/部署/UI/设备验证。
