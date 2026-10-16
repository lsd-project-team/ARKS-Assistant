# 原界面离线配方重载验证

两轮各48项检查通过，共96项；每轮正常构造一个原UcMainSystem控件，执行6次真实ReLoadRecipe（4次成功、2次独占晶圆参数文件保存失败）。24项阶段绑定通过，414新增+11965=12379，461复用。整体目标未完成。

|情况|原状态|已替换单例|立即Enabled / Tip / PrInitSuccess|解锁后程序化重试|最终流程步骤|
|---|---|---|---|---|---|
|A→B成功|Stop|6|true / false / true|无需|1|
|A→A成功|Pause|6|true / false / true|无需|2|
|A→B晶圆Save失败|Stop|前4个，晶圆及流程仍原对象|false / true / false|原私有方法直接调用恢复|1|
|A→A晶圆Save失败|Pause|前4个，晶圆及流程仍原对象|false / true / false|原私有方法直接调用恢复|2|

原构造器执行InitializeComponent、Init及本地化，真实Designer/资源与16个原源程序集加载在Framework STA宿主。初始化完成时没有原生句柄或Load事件；后续真实重载引起一次Load和隐藏句柄。闭合Action委托持有正常构造的控件接收者，无未初始化对象、私有字段写入、SDK替身或生产源码修改。夹具对机器状态、离线设置、配方ID及日期只使用公开接口。

实际SDK缺失配方列表文件会返回一个未命名Recipe，测试保留该原对象并通过公开属性固定ID/日期，再经原AddRecipe添加A/B、原Save保存一次；列表共3条。原InitProgramNodes用于6次公开数据准备，执行前原IL证明其非虚、无接收者读取、六个初始化调用固定顺序。真正被验收的重载调用均经原控件闭合委托执行。

原ReLoadRecipe先置PrInitSuccess=false、禁用控件、显示提示，更新配方Caption并Clear默认空DockManager；随后在142偏移调用InitProgramNodes，而所有try/catch/finally从148或更后开始。实际文件锁使SDK抛出无InnerException的通用Exception，包含“文件保存失败”；前四个配置单例已替换，晶圆及流程保留。恢复界面状态的finally没有执行；控件禁用、提示显示及PrInitSuccess=false均由真实原对象读取。解锁后代码直接调用原私有方法可以恢复，不代表用户可从当时已禁用的按钮重试。私有重载本身没有IsWorking或IsAllowTaskClosed门禁，Stop/Pause未被改变；外部按钮事件契约仍单独待验收。

原Load注册一个“刷新UcMain界面状态”SDK调度记录；原BackgroundThread构造器IL调用一次TaskFactory.StartNew。该SDK基础工作线程不计入S1/S2/输送业务任务（本轮0），未捕获Task句柄，未证明正常终止。只读反射读取SDK内部注册表；原UnregisterGlobalHotkeys与公开RemoveTask清除当前控件登记并验证记录数0。两次Win32热键注册调用由原IL证明，返回成功与否没有观测。未Show、渲染、运行Application.Run/DoEvents或启动原Program/MainForm。

原Load调用ExportService.EnsureDirectoryExists固定D盘设备功能测试目录；该方法先Exists，缺失才CreateDirectory，并捕获异常。两次成功宿主在Load前后均观测目录已存在。更早失败候选没有记录先前存在性，不归因其创建，也没有删除该目录。

初次真实ReLoadRecipe因VM.Core所需Apps.Data1.0精确强名称身份缺失而在方法体前失败。只读原仓库托管依赖闭包列出23个精确程序集身份，其中16个来自原InterpolationMovementTest/bin/Debug补充；原172项runtime-map保持不变。补充解析按完整身份匹配，缺失身份明确返回null。实际离线入口加载5个SDK程序集。仍缺log4net1.2.15（仓库两处均2.0.14）；没有版本替换、binding redirect或在线视觉验收。原当前/Debug VM.Core字节相同。离线PrInitSuccess=true只是分支标志。

12份原程式JSON、晶圆参数及配方列表共14份文件，11份两轮原字节相同。两份BondProgram与晶圆参数逐字段比较，仅排除原构造器产生的5个精确时间路径模式（8个实际值）；每份原文件字节及SHA独立冻结，没有时间回写。Bond日期仍验证DueDate-StartDateTime=UseDateTime分钟。精确路径为Bond /SlideFluxerProgram/FluxConsumable下StartDateTime、DueDate、LastAlarmTime，以及Wafer /WaferTableDevicePara/CurrentTablet/CreateTime、/WaferTableDevicePara/CurrentStaticAdapterTablet/CreateTime。

346声明/230原源文件保留严格编码、原字节、UTF16偏移和符号记录；111个原IL方法/6程序集，16原源与资源程序集及5实际SDK/轮。所有SDK闭包、错版本文件及VM.Core对照原字节均绑定。7份失败候选、编译禁止CLR记录及2份校验器草稿保留；成功原宿主不为文字或只读来源补充而重跑。

证据：[测试台账](native-recipe-ui-reload-test.json)、[观察审计](native-recipe-ui-reload-audit.json)、[进度](native-recipe-ui-reload-progress.json)。16项目、29组、1436文件、13任务范围保持，29组仍partial，旧正式1328验证独立保持。原生产源/项目未改；整机Start/Prepare/CleanFile、物理设备、SQL消费者、在线VM、完整MSBuild及生产流程尚未验收。下一步继续实际按钮事件/初始化和原任务关闭契约。
