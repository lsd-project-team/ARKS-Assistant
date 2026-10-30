# 运行中原任务的程式重载验证

两轮各93项检查通过（186项），每轮12次原帮助方法调用：10次成功、2次实际独占文件锁导致保存失败。每轮启动28个原任务（20个输送、8个S1/S2），26个正常完成、2个由公开UI调度夹具抛出的同一异常对象故意置为Faulted；全部已结束。23项阶段绑定通过，166新增+11799=11965，436复用。整体目标未完成。

|情况|重载时原输送Task|已替换单例|流程步骤立即/恢复后|原下料任务结果|
|---|---|---|---|---|
|A→B成功|5个Running并等待许可|6|1/1|原缺失传感器捕获，原离线Stop，正常完成|
|A→A成功|5个Running并等待许可|6|2/2|同上|
|A→B晶圆Save失败|5个Running并等待许可|前4个，晶圆/流程保持原对象|2/1|控制器与任务外层调度两次抛出夹具异常，Faulted，Stop前仍Working|
|A→A晶圆Save失败|5个Running并等待许可|前4个，晶圆/流程保持原对象|2/2|同上|

首次构造域之前，先用实际原Save保存A（二贴装位置/二流程步骤）及B（一位置/一步骤）的六类程式JSON，再加载A。之后域、控制器、任务拥有者全程保留。四行均使用同一套域；仅第0行的五个缓存在重载前与当前程式对齐，后续行的缓存已指向首次A。每次帮助方法均替换单例，即使同一RecipeID也不保留原对象。

五个原基础控制器的SubSectionProgram缓存仍指向首次A，派生Bond getter及域程式getter则返回新单例。原任务的私有输送控制器与域公开控制器是两个对象；五个缓存断言针对域公开控制器，私有控制器不反射读取。新单例的运行TransportUnit不从JSON恢复，S2消息表与当前贴装位置却仍引用旧A实体。帮助方法没有替换、停止或重建五个正在等待的原输送Task句柄。

新点胶段公开HasMaterial夹具下，直接原TransferLoadBinToDispense返回NoStart，而域基础缓存仍NoMaterial。这四次直接调用与运行中的上料Task分别计数：ContinuousFeeding=false让原上料Task等待，不声称它执行了该帮助调用。下料Task在公开UnloaderAllowPushSignal.Set后实际进入原帮助方法；第一传感器缺失，捕获后保留新等待段HasMaterial，旧域缓存仍NoMaterial，push保持Set、move保持ReSet，没有TU提交或成功信号。两成功行由原Exception分支调用原离线Machine.Stop并生成2份原状态日志；两调度抛出行在Stop前Faulted，通过公开Stop状态夹具释放另4个任务。6次Xtra调度跳过真实UI；两Faulted任务是夹具结果。

独占实际晶圆参数文件使原SDK Save失败。DynamicInvoke外层TargetInvocationException包裹原通用Exception，包含“文件保存失败”，原异常没有InnerException；磁盘字节保持。前四个重载已提交，晶圆FilePath/单例与Process FilePath/单例仍旧，没有回滚。释放锁后原帮助方法重试使六个单例一致。停止状态下，原S1 Start先Init再WaitStart，重建消息表；原S2 Start先重置运行信息再WaitStart，保留旧消息表及旧贴装位置。此处未执行节点DoWork。

13份JSON中，10份原字节两轮相同；两份BondProgram及晶圆设备参数逐字段比较，仅排除以下原构造器时间路径（5个模式、8个实际值）。每份原文件字节与SHA均独立冻结，不回写时间，不扩大规范化范围：

- BondProgram：/SlideFluxerProgram/FluxConsumable/StartDateTime、DueDate、LastAlarmTime。原TimeConsumable/BaseConsumable使用DateTime.Now，DueDate由StartDateTime+UseDateTime计算，原1440分钟关系也检查。
- WaferSubDevicePara：/WaferTableDevicePara/CurrentTablet/CreateTime、/WaferTableDevicePara/CurrentStaticAdapterTablet/CreateTime。

320声明/207原源文件严格保留UTF8及CP936字节、UTF16切片偏移、行号和SHA；69个原IL方法/3程序集，16个实际原源与资源程序集/轮。执行null接收者open Action<UcMainSystem>前，57方法IL预检已确认InitProgramNodes非虚、无接收者读取，且六调用顺序固定。真实ReLoadRecipe静态IL显示帮助方法位于其try/finally之前；它依赖原UI对象，本轮没有运行它，不能把帮助方法结果推广为真实UI入口已验收。

已保留一次编译缺少Services导入的失败（未进入CLR）、一次只读IL扩展脚本失败、三份验证器草稿。两轮成功原宿主未重跑；后续仅扩充原Start lambda与耗材日期的只读来源/IL证据。

证据：[测试台账](native-recipe-live-reload-test.json)、[观察审计](native-recipe-live-reload-audit.json)、[进度](native-recipe-live-reload-progress.json)。原生产源/项目文件未修改，未调用整机Start/Prepare/CleanFile、物理转料、SQL消费者、真实UI/在线算法或完整MSBuild。16项目、29组、1436文件、13项任务范围保持，29组仍partial，旧正式1328验证保持独立。下一步继续其余实际重载入口/初始化范围、运行任务关闭契约和完整生产链验收。
