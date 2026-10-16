# 原主窗体加载、上下文及 SDK 刷新验证

两轮各40项通过，共80项；28项阶段绑定通过。554新增+13651=14205，490复用。原MainForm正常构造与Load、SDK主模块激活及实际标题刷新已经执行，整体目标未完成。

|原流程|实际结果|本轮范围|
|---|---|---|
|NormalWork且AllAxisReset=false|原Load禁用主系统Tile，直接返回|MF仍null，未创建机器后台线程，也未构造主系统文档|
|OffLineWork且AllAxisReset=false|原Load执行DataLoad、ChangeData、参数委托赋值、两个Modbus入口、ChoseAllLight、后台线程创建、MF赋值和Splash关闭|离线分支不创建串口客户端、不操作灯；Tile.Enabled保留SDK默认null|
|原MF建立|通过实际Application.OpenForms[0]正常设置私有setter|没有反射调用setter或写私有字段；构造器原PostAction委托通过真实句柄执行一次公开Action|
|SDK ActivateDocument|原QueryControl通过原Activator构造UcMainSystem，绑定Tag/Control、InitModule及StartGroup|每轮查询一次，有真实控件句柄；不是直接填充文档Control|
|原主模块Load与SDK刷新|注册原刷新任务，实际更新MainForm.HtmlText中的配方名MainFormContext及离线模式|每轮公开ThreadException记录0；此前独立主控件的MF空引用故障未在该正常主窗体上下文出现|
|原后台监控线程|正常创建，公开ThreadFlag=false使其在循环前退出，Join确认Stopped|监控循环0次，SQL与存图消费者线程字段均null；不声称后台服务验收|
|真实数据文件|每轮28个Settings文件：10可解析JSON、17零字节原仓库文件、1原晶圆时间备份|10共同JSON语义一致、8份字节一致；17空文件逐字节冻结且不解析为JSON|
|原关闭生命周期|原FormClosed指向ExitSoftware，后者调用Environment.Exit(0)|本轮明确公开Dispose清理两个窗体，FormClosed观察0；生产关闭/保存/硬件关闭链未执行|

关键依赖已经在原IL中确认：机器监控线程和原SDK BackgroundThread worker均读取同一个RuntimeProvider.ThreadFlag。夹具先公开设false，让原MainForm_Load创建的机器线程退出并Join；然后在SDK文档激活前公开设true，使原SDK worker能够刷新；原热键注销与RemoveTask后再公开设false。没有恢复、替换或重新启动已退出的机器线程，没有替换SDK回调。SDK内部Task句柄没有保存于可观察字段，本轮仍没有该worker的句柄及正常终止回执；共享退出标志和原循环分支证据与实际终止验证分别记录。

每轮使用公开固定ID/日期的原默认Recipe种子，RecipeID=eeeeeeee-1111-2222-3333-444444444444、名称MainFormContext、日期2020-01-01；一次明确程序化私有InitProgramNodes辅助初始化和原程序Save生成6份种子程序。随后实际运行原窗体加载。不是从完整Program.Main或设备初始化入口启动，未执行授权/SoftKey、InitPR、硬件初始化或本机在线VM流程；PrInitSuccess保持原false，未设置为成功夹具。

原DataLoad正常返回并设置PropertyChangeAop.InitSuccess=true；原ChangeData对空载具仓库仍执行真实Save，生成CarrierRepository.json。其他17份缺失仓库由原读取路径创建零字节文件，后续对象使用原默认空集合。本轮并未给它们构造虚假JSON内容。晶圆及Bond程序仅在既有5个精确构造日期路径比较语义，原文件字节不改；每轮1份晶圆按秒命名备份独立绑定，名称实际不同。

![原主系统控件的单独原生渲染](C:/Users/akrs/Documents/ChatGPT/archify/.archify-work/native-mainform-context/bound/offline-main-control.png)

每轮4张原DrawToBitmap截图，共8张已查看并冻结。单独原UcMainSystem图为1920×999，真实菜单、按钮和4幅设备资源已显示；1552×832整MainForm图显示真实标题，但SDK文档区域仍为灰色。保留整窗体截图和原控件尺寸，不把单独控件完整图当作实际整窗体布局验收，也没有拼图或修改截图。整SDK文档区域的屏幕呈现、缩放及物理点击仍待验证。

两轮原Windows私有STA桌面在控件构造前分配，工作线程正常结束、CloseDesktop成功，输入及主线程桌面均保持Default。公开Show、DoEvents、SDK ActivateDocument驱动原流程，没有SwitchDesktop、物理点击或本地生产C#/csproj变更。

354原声明/236源码文件、225原IL方法/8程序集在接受运行前绑定；16原源资源程序集按身份、路径与SHA校验，172条原runtime-map及23条精确SDK闭包/16补充/缺失log4net1.2.15保持。SDK映射和IL不是正常视觉过程/VM本机依赖成功证明。

6个失败候选完整保留：首编译可空bool与AOP命名空间错误且运行守卫阻止CLR；前置辅助未设离线而失败；可空Tile默认预期错误；已结束线程IsBackground读取异常；共用ThreadFlag导致SDK刷新未执行；运行39项通过但结果包装重复键失败。两轮39项的成功初稿为整窗体截图不足而补充子控件图，作为独立初稿保留；最终两轮40项不是靠删除失败行或重复运行直到原调度次数相同获得。3个只读断言草稿（截图高度、静态字段误作setter、StartGroup字段误作setter）和空仓库JSON分析失败均列明，未再次执行已接受宿主来修改文档措辞。

证据：[台账](native-mainform-context-test.json)、[审计](native-mainform-context-audit.json)、[进度](native-mainform-context-progress.json)。16项目、29组、1436个C#文件、13项任务范围保持，29组仍partial，旧正式1328独立。下一步继续原PR/VM初始化依赖、整窗体呈现与关闭保存链；实际监控循环、设备/视觉、SQL/存图消费者、整机Start/Prepare、完整MSBuild/LC/Fody及部署仍待验收。整体目标未完成。
