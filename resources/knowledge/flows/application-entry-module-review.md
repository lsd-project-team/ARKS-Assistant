# Program：应用启动、门禁与主窗口衔接

复核日期：2026-09-28。分组：`AKRS.ZX2200/Program.cs`。状态：部分复核。目标是说明自动生产启动之前的应用前提，而不是把启动窗口等同设备就绪。生产源码未修改、未启动设备程序。

## 主流程摘要

Main(STA) → 以 Application.ProductName 创建互斥体 → 注册UI/非UI异常处理 → 检查C/D盘空间 → 检查设备数据迁移并按需提示 → 创建日志与辅助线程 → 按配置检查授权 → 本地版本公告 → 非离线模式启动PR加载、初始化硬件/限位 → 安装控件创建日志钩子 → 注册PR图片保存委托 → 按配置回零 → 构造MainForm并进入消息循环 → 主窗口Load检查回零/离线状态后加载数据、连接压力设备、启动后台线程。

下面的 Program 行号来自 `trunk/AKRS.ZX2200/Program.cs`，其他源码另标。每个步骤的代表调用在模块台账中登记。

## 启动门禁和顺序

- Program 64–105、260–269：创建命名互斥体，只有 createNew 分支进入初始化；重复打开弹窗、等待100ms、Environment.Exit(1)。正常消息循环退出后 ReleaseMutex。互斥范围/系统会话语义未作跨进程运行验证。args 参数未在此启动体消费。
- 109–121：磁盘检查false直接返回；迁移判断true时显示 FrmParaChangeTipAfterDataMigrate，但这里不根据窗口结果退出。不能把提示窗口等同强制迁移成功。
- Machine.Sustain.cs:186–208：检查的是 TotalFreeSpace，C盘至少10 GiB、D盘至少200 GiB；不是内存/RAM。DriveInfo读取异常在此没有catch。
- Machine.SelfCheck.cs:563–573：MachineName为空时记录当前MAC/机器名并Save，返回false；否则比较保存机器名和当前机器名。该方法未比较MAC，不是完整的数据迁移校验。
- Program125–135：创建“重复标定实验”JSON日志并配置相对路径，启动后台辅助线程，启用Warn/Info日志；SuspendAllRecord只是注释。日志目录/缓冲契约另待核实。
- 138–165：IsDetectingEncryption启用时调用CheckYtSoftKey，false释放互斥并return；true再初始化授权、读取到期信息。IsPromptEncryption启用且剩余天数<7则提示，并写入显示用授权ID/日期。具体授权有效性规则在SoftkeyManager，尚不由这些调用证明。
- VersionUpdateAnnouncement.cs:33–59：比较内置VersionInfos、程序集版本和本地配置版本；不匹配提示并仅退出这个方法。需要展示公告时保存版本号/更新时间再显示窗口。没有在该方法下载软件或访问远程更新服务，不能称为自动升级器。

## 非离线初始化与异步边界

Program173–237只在MachineWorkMode不是OffLineWork时执行此块：

1. 调用Machine.InitPR（177），**没有await、Wait或读取返回Task**。Machine.Sustain.cs:116–179实际Task.Run关闭旧VM方案、创建新方案，获取配方PR列表，必要时复制备份模板配置，逐项初始化算法，再加载点胶PR，最后置PrInitSuccess=true。未找到某个PR只记录日志继续；异常弹窗/日志后重抛到Task。因此此true不能直接解释成所有模板都已找到。
2. 显示启动窗口→InitAllHardware→关闭启动窗口→SetStopStateAlarm，读取轴卡1/2。这里没有等待前面的PR任务完成。硬件初始化库的内部顺序/恢复仍待外部实现核对。
3. 轴卡1为GTController时：BondZ伺服关闭→设置平滑参数→ChangeMode配置→伺服开启→轴卡2软限位。否则按IsBondAxisTSingleMove决定是否把“焊头T”偏移设0并AbsoluteMove(0)。最后轴卡1软限位。
4. 任意本块异常进入catch记录并弹框，但catch没有return/throw/退出；之后会继续到控件钩子及主窗体路径。启动窗口CloseForm不在finally；BondZ恢复伺服也不在finally。因此“进入主窗体”不是硬件初始化成功的证明，具体状态需现场核对。

没有从非离线块跳过推导整个离线运行完全不触硬件：后面的可选AllAxisGoHome位于这个块外，MainForm.Load也有自己的状态分支。

## 主窗体与自动生产的分界

Program239–256：Harmony反射取得WinForms内部MarshalingControl构造并安装前置日志方法；未见空值检查或本段catch。注册PREntity图片保存委托，若IsAxisResetBeforeWork则调用AllAxisGoHome，返回bool未消费；随后new MainForm、Application.Run。没有在Main直接调用生产Machine.Start。

MainForm.cs:55–70：构造初始化控件、读取PlatformProvider.Current，并给SendUiAction追加PostAction；后者以Invoke执行委托。Program在构造MainForm之前已调用多个可能写UI日志的路径，其早期UI委托可用性不能只由该构造订阅推出。

MainForm.cs:232–270：若未AllAxisReset且非离线，禁用主系统入口并立即return，跳过本次Load后续的数据加载/压力连接/后台线程。其余路径依次DataLoad→ChangeData→参数界面初始化委托→ConnectBondhead/ConnectManometer→ChoseAllLight→StartBackGroundThread→创建测试目录→登记主窗体实例→关闭启动窗口。此处不等于自动开始生产；实际启动按钮/任务循环沿已有主图继续追踪。

## 异常处理与辅助线程

- Program281–295的两个全局异常处理器仅显示消息和堆栈，没有直接Stop/EmergencyStop、回滚或重试。非UI异常处理器存在不代表进程必定继续，也不覆盖所有未观察Task异常。
- Program308–317的后台辅助线程轮询特定第三方窗口并发送关闭消息；它不是生产调度器。未将这段当成产品授权检查的一部分，也未执行它。
- Program330–350的Harmony前置方法只对线程ID非1记录控件创建线程；报警代码是注释。日志不等同禁止跨线程创建，更不证明线程ID1在所有运行场景的身份。

## 输入、输出、依赖与缺口

输入：软件配置、机器参数、当前配方/PR库、工作模式、轴卡/驱动、设备磁盘及授权设备。输出：配置/日志、可选回零和硬件初始化调用、主窗体、压力设备连接及后台线程。涉及WinForms/DevExpress/Harmony、VM视觉库、硬件仓库、授权库和Windows窗口API。

已限定复核Program顺序及直接的磁盘/迁移/PR/版本/Load衔接。待复核：SoftkeyManager授权与持续监控、HardwareRepositoryService.InitAllHardware下层、Harmony跨版本兼容性、迁移提示内部、后台线程全生命周期及进程关闭清理。未声明所有依赖就绪，未进行构建或设备运行验收。

## 可点击源码证据

- [app-entry：Program.cs:64–108](../../trunk/AKRS.ZX2200/Program.cs#L64)
- [app-precheck：Program.cs:109–171](../../trunk/AKRS.ZX2200/Program.cs#L109)
- [app-hardware：Program.cs:173–237](../../trunk/AKRS.ZX2200/Program.cs#L173)
- [app-ui：Program.cs:239–272](../../trunk/AKRS.ZX2200/Program.cs#L239)
- [app-errors：Program.cs:281–295](../../trunk/AKRS.ZX2200/Program.cs#L281)
- [app-aux：Program.cs:300–350](../../trunk/AKRS.ZX2200/Program.cs#L300)
- [app-disk：Machine.Sustain.cs:186–208](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Sustain.cs#L186)
- [app-migration：Machine.SelfCheck.cs:563–573](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.SelfCheck.cs#L563)
- [app-pr：Machine.Sustain.cs:116–179](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Sustain.cs#L116)
- [app-version：VersionUpdateAnnouncement.cs:33–59](../../trunk/AKRS.ZX2200/Main/VisionControl/VersionUpdateAnnouncement.cs#L33)
- [app-form-constructor：MainForm.cs:55–70](../../trunk/AKRS.ZX2200/Main/Controls/MainForm.cs#L55)
- [app-form-load：MainForm.cs:232–270](../../trunk/AKRS.ZX2200/Main/Controls/MainForm.cs#L232)
