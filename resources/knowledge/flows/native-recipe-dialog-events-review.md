# 原配方模态对话框及Designer事件验证

两轮各89项检查通过，共178项。每轮11次实际加载选择器、1次实际新建取消选择器、1次原SDK名称校验提示；26项阶段绑定通过。382新增+12534=12916，482复用。独立控件缺MainForm.MF时原SDK刷新回调每轮实际抛出一次NullReferenceException，作为明确故障保留。整体目标未完成。

|原交互入口与条件|真实观察|边界|
|---|---|---|
|初始A，取消或确认同一A|配置和程序保持A；标题仍为Designer的Name|同ID不执行重载，也不更新该标题|
|A→B或聚焦网格A确认|6个程序单例替换，标题及步数更新|实际原SDK查名/网格选择与原Designer事件|
|同B且晶圆文件独占锁|确认成功，无重载/保存异常|同ID跳过晶圆初始化|
|B→A且晶圆Save锁|磁盘与内存RecipeID已A，前4程序A，后2仍B；标题A，界面禁用/Pr=false|原通用保存异常无InnerException，传播至PerformClick调用者|
|解锁后再选同A|磁盘A，但原B流程仍在，界面仍禁用|同ID跳过重载，公开程序化触发不证明鼠标能点击|
|A→B且MachineConfig Save锁|内存B，磁盘A不变，全部程序A，标题A|失败发生在ReLoadRecipe之前，未禁用界面|
|解锁后再选同B|磁盘变B，但程序和标题仍A|原比较用内存CurrentRecipe，继续同ID跳过|
|不存在的名称|真实Xtra提示后选择器仍打开、Recipe=null，再实际取消|2次SDK按钮激活；提示通过公开DialogResult关闭|
|新建取消|原SDK对话框取消，原调用者Dispose并再次Save相同3条列表|没有执行新建、拷贝或目录删除|
|取消与两次保存异常|5个加载对话框原调用者未Dispose|先测IsDisposed，再由公开夹具Dispose清理|

两轮均正常构造原UcMainSystem，原Designer绑定BarBtLoad和BtNewProduct通过公开PerformClick执行，进入原FrmLoadRecipe/FrmAddRecipe.ShowDialog。SDK窗体没有替换，私有字段只读获取控件引用，Text、FocusedRowHandle与SimpleButton.PerformClick是公开夹具操作。12个原窗体均Visible/Modal/HandleCreated。主控件有隐藏句柄，未显示原MainForm；没有物理鼠标点击。原SDK选择器真实消息泵运行，首次原Load执行一次。

每轮11次加载尝试中9次到达追加的公开ItemClick观察订阅；两次原保存异常阻止后续订阅，因此不能把9误报为11。原MachineConfig事件保存8次尝试/7成功/1失败；另一次公开初始Save为独立夹具。实际UI重载5次（4成功/1晶圆失败），其中2次是明确程序化私有重试，只有这些重试才修复六程序路径与流程步数；不能宣称原同配方确认自动恢复。初始化辅助调用3次、配方列表种子Save1次和新建取消Save1次分开计数。

每轮私有Windows桌面在任何原控件创建前分配给独立STA线程，没有SwitchDesktop。实际输入桌面前后Default，主线程桌面保持Default，工作桌面ArchifyRecipeDialog进程号与输入不同；工作线程结束，CloseDesktop返回true。原始桌面名与过程JSON分别冻结，结果不抹去PID。接口语义查验：[CreateDesktopW](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-createdesktopw)、[SetThreadDesktop](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setthreaddesktop)、[CloseDesktop](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-closedesktop)。

原SDK登记刷新回调经BeginInvoke实际运行ChangeUiByState、ChangeUiByConfiguration与AutoLogOut，然后访问MainForm.MF.HtmlText。独立宿主没有原MainForm，MF=null，每轮记录一次原NullReferenceException，原回调没有异常处理器。公开Application.ThreadException订阅只捕获原异常、阻止Framework错误弹窗呈现，不替换/取消SDK回调。此前失败候选误把Framework异常弹窗当名称提示；该原始失败截图与日志保留，成功候选真实名称提示另有截图。此结果不是完整主窗体或无故障UI验收。

原Load登记1个SDK刷新记录，结束时原热键注销及公开RemoveTask删除记录。原基础线程StartNew由IL确认，未捕获其Task句柄和正常终止证据。业务Task、状态日志、主窗体Xtra派发和硬件数量均0，没有启动SQL消费者。固定D盘测试目录在成功宿主前后都已存在，未执行整机Start/Prepare/CleanFile。

27份实际JSON中24份两轮字节一致；两份Bond和晶圆设备参数仅对原构造器5个精确时间路径模式/8个实际值进行语义比较，原字节独立绑定。12个配置快照逐行绑定，最终MachineConfig为A。RecipeList保留原未命名默认记录及A/B三条，公开固定ID/日期/User夹具使其字节可复验。每轮3张原生DrawToBitmap PNG（875×534加载、412×147名称提示、461×266新建取消），6张均已视觉查看并分别冻结。

![原加载选择器](C:/Users/akrs/Documents/ChatGPT/archify/.archify-work/native-recipe-dialog-events/bound/dialog-row-2.png)

![原名称校验提示](C:/Users/akrs/Documents/ChatGPT/archify/.archify-work/native-recipe-dialog-events/bound/sdk-validation-row-10.png)

![原新建取消对话框](C:/Users/akrs/Documents/ChatGPT/archify/.archify-work/native-recipe-dialog-events/bound/dialog-row-11.png)

源码证据346声明/230文件，142原IL方法/7程序集，严格编码/UTF16位置/符号记录对应原源。实际16原源资源程序集及5SDK身份逐一核SHA；父172项runtime-map未改，23精确SDK身份/16补充/1缺失log4net1.2.15保持，不替代SDK版本或执行在线VM。

保留4个失败候选：编译错误未进入CLR；主桌面重复赋值Win32失败0检查；原SDK刷新Framework弹窗导致校验超时70检查；11尝试/9订阅计数 guard错误83检查。另2个只读验证草稿错误（PNG宽度及Recipe/FrmLoadRecipe符号尾缀边界）有真实失败回执，修复预期与匹配而未改原运行或截图。成功宿主未为文档重跑，无生产C#/csproj编辑。

证据：[测试台账](native-recipe-dialog-events-test.json)、[观察审计](native-recipe-dialog-events-audit.json)、[进度](native-recipe-dialog-events-progress.json)。16项目、29组、1436文件、13项任务范围保持，29组仍partial，旧正式1328独立。下一步继续原新建/拷贝的实际确认流程和完整MainForm上下文初始化；动态生产、设备/视觉、SQL与完整MSBuild/LC/Fody部署链仍待验收。整体目标未完成。
