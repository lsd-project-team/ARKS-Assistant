# 动作耗时源码复核（2026-10-24）

本轮结论：当前动作目录、计算覆盖及详情显示仍有缺口，不能宣称“全部动作已找齐、源码可算耗时全部显示”。主表已有正数汇总没有发现被隐藏，但详情漏掉运动契约中的20 ms固定等待；另有目录识别、回调入口和展开能力问题。

本轮核实保持只读，未修改应用分析器、前端或trunk，未替换正式报告。以下是复核发现，尚未修复。

## 复核范围与方法

重新读取当前工程Compile/ProjectReference、生成文件类型声明，生成目录，与正式v33报告逐ID比较；另做直接SDK调用、向导回调、源码延时和显示函数扫描。没有用“分类器自己报告遗漏为0”代替独立检查。

- 当前10个工程，977个非生成编译文件；378个生成文件只补类型声明。业务方法12,730个、依赖方法1,475个。当前编译业务文件语法扫描未发现解析错误。
- 39个ActionNode继承类、16个服务工作循环均有去向，主要表47项。语法直接找到19个Tasks顶层循环：另外3个是GetInputSignal内部轮询、DryCycle启动前返回的Loader/Unloader循环，不应新增3个生产单轮。
- 新目录仍2,737项，与当前报告没有缺ID或过期ID；这证明当前目录与当前生成规则一致，不能证明规则找到了所有动作。

## 确认的问题

| 问题 | 源码事实 | 当前表现与处理口径 |
| --- | --- | --- |
| 直接SDK动作漏目录 | FrmGTForceTest1.BtnStartMove_Click向2个核各12个轴发GTN_Stop，再各发StopCommandList；ETelDrive.DownloadMapping有单轴、双轴两个重载 | 三个入口均是no_recognized_timing_path且无动作行。应列辅助动作，硬件完成时间标未定，不能填0 ms |
| SDK辅助调用覆盖不全 | 新扫出27个方法声明、68处硬件形态调用；逐项分出22个读写/配置/监视辅助入口，5个对象获取或已有动作包装 | 22个是待补辅助接口，含上述3个；不表示22个独立生产工序。完整分类见下表 |
| UIActionAsync漏展 | FrmGlobalCalibrationEx的BarBtnMoveTo_ItemClick和BtnMoveToCamCenter_Click，在ChkSimRun.Checked时各有Sleep(1000) | 行存在，但包装重载/扩展调用未接上，两个1,000 ms阶段不在详情。需恢复条件后台阶段，不能直接把按钮同步总时长改成1秒 |
| 向导操作缺独立入口 | FrmWaferCameraCalibTeach.InitControl保存的doneAction，正常10轮各Sleep(100)；FrmAssistantDispense保存的doneAction在非离线成功路径Sleep(500) | 回调不在初始化时执行，因此不能把它们相加给InitControl。应按用户点击的向导步骤列入口，分别展示至少1,000 ms、条件500 ms及其他未知组成 |
| 展开保护与未知值没有完全消除 | 750行truncated，包含18个主表动作；另有重载未绑定、旧式Thread、共享状态失效等原因 | 不是用户缺少Hardware.json就能全部解决。需继续改分析器；4096调用/迭代/跳转额度及单块512轮上限不是设备实际次数 |
| 详情漏显已知组成 | motion_model.source_fixed_wait_ms已有20 ms，涉及61个源码位置、589条报告行 | SourceTimingDetail只渲染目标/速度/公式/条件，未显示该字段。应显示“包内固定等待20 ms，与运动重叠”；保留初始化条件，不直接加到总运动时长 |

具体位置：`trunk/AKRS.ZX2200/BondSystem/Controls/Experiment/FrmGTForceTest.cs:601`；`trunk/AKRS.ZX2200/Infrastructure/Utils/ETelDrive.cs:27`、第54行；`trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs:1228`、第1248行；`trunk/AKRS.ZX2200/CalibSystem/Controls/Assistant/FrmWaferCameraCalibTeach.cs:220`；`trunk/AKRS.ZX2200/BondSystem/Controls/Assistant/FrmAssistantDispense.cs:276`。

向导全量语法清点：80个文件、317组AssistantConfig，backAction/nextAction/doneAction共951个具名回调；226个含动作/耗时名称调用。这是候选数，不是226个已确认新增独立动作；有些动作主体已作为控制器方法列出。源码与构造位置逐项保存在wizard-callbacks.json，后续要绑定用户步骤和已有子方法，避免重复计时。

## 已算出的数值有没有被页面隐藏

对正式报告全部2,737行执行了前端实际actionPresentation、filterActions和actionTableCsv函数：226行有正数已知边界，另2行有每路光源至少2,000 ms；228行均有数值呈现。主/辅列表分别47/2,690行且分区无丢行，导出与呈现一致，没有把未定总时长显示成0 ms。

这项检查只证明主表汇总字段的数值能显示，不能覆盖详情的每个结构化字段。进一步代码检查发现运动契约中的source_fixed_wait_ms没有被详情组件引用，61个源码位置的20 ms固定等待没有明确数值展示，涉及589条父/子入口行；不能说它们是589次设备运动，也不能把61×20 ms加为节拍。证据在detail-field-review.json。

同样不能据此证明“源码里能算出的值都进入报告”；上面的UI包装和向导步骤就是反例。本轮未重新登录浏览器做视觉验收，检查的是实际数据及显示/筛选/导出代码。

源码直接Sleep/Delay/Wait等调用643处，134处没有对应独立阶段（阶段按源码位置去重）。其中351处为直接数值Sleep/Delay，307处有delay记录且数值全部一致，44处没有独立delay记录。44处逐项列于后文，包含合法跳过、不可达、缺运行条件与分析器漏展，不能把44全部当成遗漏，也不能全归因为缺硬件配置。

## 未定具体缺什么

| 类别 | 具体缺项 | 能否只靠现有源码补齐 |
| --- | --- | --- |
| 物理运动 | 每轴实际驱动、CardNum/AxisNum映射、PulseEquivalent、有效V/ACC/DEC/J、限速与倍率、规划起点/目标、起末速度、平滑/插补、到位稳定及精确SDK单位 | 当前未提供Hardware.json，部分点位/运动配置和运行反馈也缺失；不能给完整物理毫秒数。详情应保留具体轴与原参数表达式 |
| 配方/载具/界面值 | 当前carrier/component/nozzle、点胶图案及点集、循环次数、测试间隔；如OpenWaferTableVacuumBeforePickDelay、TableBlowDelay、placementDelay、AfterPickupVacuumCheckDelay及Sp...Value/EditValue | 声明初值不等于当前值。117个源码延时位置当前值未定，逐点列表在后文；有些是形参，有些有初值但被未知写入失效 |
| 信号/反馈/人工条件 | 真空/气缸限位、轴到位、允许取片/来料信号、暂停/继续、人工对话框、取消/重试、锁和UI队列释放时间 | 源码能显示判断、轮询间隔和保护上限，无法静态知道何时满足。超时不能当必耗时 |
| SDK/外部操作 | 某些具体硬件重载内部等待、通讯、视觉处理、补偿文件下载及实际驱动曲线 | 一部分是尚未核实的包契约，一部分依赖外部数据；应分别说明，不能统称缺一个配置文件 |
| 分析器能力 | UIActionAsync/扩展重载、保存后执行的向导/Thread回调、未知返回/共享写入、条件循环和展开额度 | 属于程序待补齐；先恢复可证明的等待/每轮组成，再保留确实无法求解的部分 |

例如晶圆单轮275行读取currentNeedCarrierConfig.OpenWaferTableVacuumBeforePickDelay，当前载具对象在未知调用后失效，不能拿BaseCarrierConfig声明0当当前值；这与“整个trunk没有Hardware.json”是两种原因。

只有缺少次数时，也应尽量显示每轮组成。例如FrmTestAccuary.BtnStart_Click在每个点的每次完整循环直接Sleep(30)三次，单算这三处就是90 ms×点数×次数；点集和界面次数未知会阻止总数求值，不会使这三处源码等待不存在。当前报告没有展开这些组成，是待完善项。

各段不能笼统说速度/加速度全部缺失：例如S2DispenseController.cs第182行相关请求在报告中已能恢复V=1、A=D=10、J=0.02；但规划起点、驱动/单位、初始化及压力反馈完成边界仍未定。部分相对请求也已有位移。应逐字段区分“已知请求值”和“缺少的有效运行参数”，不能要求用户重新提供已有的源码数值。

### 主表47项当前显示及未定组成

下表按当前真实表格数据生成。通用“未解析调用”不等于每个调用都会造成实际设备等待；它表示当前分析未能证明完整边界。每项的原条件、表达式、来源和参数快照保存在primary-details.json。

| 工位 | 动作 | 当前显示 | 未定的组成 |
| --- | --- | --- | --- |
| S1 | 焊点定位 | 耗时未定 | 循环次数/退出条件；参数/回调/调用尚未绑定 |
| S1 | 点胶 | 耗时未定 | 轴起点/目标、速度曲线、配置/SDK完成边界；循环次数/退出条件；参数/回调/调用尚未绑定 |
| S2 | 取片 | 至少 5 ms | 轴起点/目标、速度曲线、配置/SDK完成边界；信号何时满足；循环次数/退出条件；参数/回调/调用尚未绑定 |
| S2 | 上视纠偏 | 20–40 ms | 轴起点/目标、速度曲线、配置/SDK完成边界；循环次数/退出条件；参数/回调/调用尚未绑定；分析展开触及保护边界 |
| S2 | 固晶 | 至少 20 ms | 轴起点/目标、速度曲线、配置/SDK完成边界；循环次数/退出条件；参数/回调/调用尚未绑定 |
| S1 | 流道交互 | 耗时未定 | 信号何时满足；循环次数/退出条件；参数/回调/调用尚未绑定；分析展开触及保护边界 |
| S1 | 预点胶动作 | 耗时未定 | 循环次数/退出条件；参数/回调/调用尚未绑定 |
| S1 | 焊点身份识别 | 耗时未定 | 轴起点/目标、速度曲线、配置/SDK完成边界；信号何时满足；循环次数/退出条件；参数/回调/调用尚未绑定；分析展开触及保护边界 |
| S1 | 载具测高 | 耗时未定 | 循环次数/退出条件；参数/回调/调用尚未绑定 |
| S1 | 载具定位 | 耗时未定 | 循环次数/退出条件；参数/回调/调用尚未绑定 |
| S1 | 胶型检测 | 耗时未定 | 轴起点/目标、速度曲线、配置/SDK完成边界；循环次数/退出条件；参数/回调/调用尚未绑定；分析展开触及保护边界 |
| S1 | 点胶测高动作 | 耗时未定 | 循环次数/退出条件；参数/回调/调用尚未绑定 |
| S1 | 基岛身份识别 | 耗时未定 | 轴起点/目标、速度曲线、配置/SDK完成边界；信号何时满足；循环次数/退出条件；参数/回调/调用尚未绑定；分析展开触及保护边界 |
| S1 | 基岛测高 | 耗时未定 | 循环次数/退出条件；参数/回调/调用尚未绑定 |
| S1 | 基岛定位 | 耗时未定 | 循环次数/退出条件；参数/回调/调用尚未绑定 |
| S1 | 基板身份识别 | 耗时未定 | 轴起点/目标、速度曲线、配置/SDK完成边界；信号何时满足；循环次数/退出条件；参数/回调/调用尚未绑定；分析展开触及保护边界 |
| S1 | 基板测高 | 耗时未定 | 循环次数/退出条件；参数/回调/调用尚未绑定 |
| S1 | 基板定位 | 耗时未定 | 循环次数/退出条件；参数/回调/调用尚未绑定 |
| S1 | 载具身份识别 | 耗时未定 | 轴起点/目标、速度曲线、配置/SDK完成边界；信号何时满足；循环次数/退出条件；参数/回调/调用尚未绑定；分析展开触及保护边界 |
| S2 | 焊后检测流程 | 500 ms | 轴起点/目标、速度曲线、配置/SDK完成边界；循环次数/退出条件；参数/回调/调用尚未绑定；分析展开触及保护边界 |
| S2 | 焊点定位流程 | 耗时未定 | 循环次数/退出条件；参数/回调/调用尚未绑定 |
| S2 | 焊点定位精度测试 | 耗时未定 | 轴起点/目标、速度曲线、配置/SDK完成边界；循环次数/退出条件；参数/回调/调用尚未绑定；分析展开触及保护边界 |
| S2 | 墨点检测 | 无固定停留 | 源码无固定停留；不等于设备实际0毫秒 |
| S2 | 蘸胶动作节点 | 空跑不可执行 | 空跑专用主体抛异常；异常后动作不计 |
| S2 | 焊点身份识别 | 耗时未定 | 轴起点/目标、速度曲线、配置/SDK完成边界；信号何时满足；循环次数/退出条件；参数/回调/调用尚未绑定；分析展开触及保护边界 |
| S2 | 焊点测高 | 耗时未定 | 循环次数/退出条件；参数/回调/调用尚未绑定 |
| S2 | 载具测高 | 耗时未定 | 循环次数/退出条件；参数/回调/调用尚未绑定 |
| S2 | 载具定位 | 耗时未定 | 循环次数/退出条件；参数/回调/调用尚未绑定 |
| S2 | 系统2点胶动作 | 耗时未定 | 轴起点/目标、速度曲线、配置/SDK完成边界；循环次数/退出条件；参数/回调/调用尚未绑定 |
| S2 | 基岛身份识别 | 耗时未定 | 轴起点/目标、速度曲线、配置/SDK完成边界；信号何时满足；循环次数/退出条件；参数/回调/调用尚未绑定；分析展开触及保护边界 |
| S2 | 基岛测高 | 耗时未定 | 循环次数/退出条件；参数/回调/调用尚未绑定 |
| S2 | 基岛定位 | 耗时未定 | 循环次数/退出条件；参数/回调/调用尚未绑定 |
| S2 | 系统2预点胶 | 耗时未定 | 循环次数/退出条件；参数/回调/调用尚未绑定 |
| S2 | 基板身份识别 | 耗时未定 | 轴起点/目标、速度曲线、配置/SDK完成边界；信号何时满足；循环次数/退出条件；参数/回调/调用尚未绑定；分析展开触及保护边界 |
| S2 | 基板测高 | 耗时未定 | 循环次数/退出条件；参数/回调/调用尚未绑定 |
| S2 | 基板定位 | 耗时未定 | 循环次数/退出条件；参数/回调/调用尚未绑定 |
| S2 | 载具身份识别 | 耗时未定 | 轴起点/目标、速度曲线、配置/SDK完成边界；信号何时满足；循环次数/退出条件；参数/回调/调用尚未绑定；分析展开触及保护边界 |
| S2 | 基板相机矫正 | 至少 80 ms | 轴起点/目标、速度曲线、配置/SDK完成边界；循环次数/退出条件；参数/回调/调用尚未绑定；分析展开触及保护边界 |
| S1 | 点胶单轮流程 | 至少 10 ms | 轴起点/目标、速度曲线、配置/SDK完成边界；信号何时满足；循环次数/退出条件；参数/回调/调用尚未绑定；分析展开触及保护边界 |
| S2 | 固晶单轮流程 | 至少 5 ms | 轴起点/目标、速度曲线、配置/SDK完成边界；信号何时满足；后台任务完成边界；循环次数/退出条件；参数/回调/调用尚未绑定；分析展开触及保护边界 |
| S2 | 刮胶单轮流程 | 至少 20 ms | 信号何时满足；循环次数/退出条件；参数/回调/调用尚未绑定；分析展开触及保护边界 |
| 晶圆与翻转 | 翻转单轮流程 | 0–100 ms | 循环次数/退出条件；参数/回调/调用尚未绑定 |
| 晶圆与翻转 | 晶圆单轮流程 | 至少 5 ms | 轴起点/目标、速度曲线、配置/SDK完成边界；当前载具延时参数值；信号何时满足；循环次数/退出条件；参数/回调/调用尚未绑定；分析展开触及保护边界 |
| 输送与上下料 | 上料任务 | 空跑不动作 | DryCycle启动前返回；不是需要补时间 |
| 输送与上下料 | 点胶传入Bond（单轮） | 至少 505 ms | 信号何时满足；循环次数/退出条件；参数/回调/调用尚未绑定 |
| 输送与上下料 | Bond传入等待区（单轮） | 至少 505 ms | 信号何时满足；循环次数/退出条件；参数/回调/调用尚未绑定 |
| 输送与上下料 | 下料任务 | 空跑不动作 | DryCycle启动前返回；不是需要补时间 |

## SDK候选逐项复核

“应补”表示辅助目录及证据的覆盖缺口；没有源码固定等待时，时间仍应未定。不能为凑齐数值填零。

| 方法/重载 | 源码 | 复核结论 |
| --- | --- | --- |
| BondHeadController.GetZZIpolGroup | `trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs:1144` | 获取驱动/插补组对象；不作为新增独立设备动作 |
| BondHeadController.GetBondForceCurrentVal | `trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.ForceRelated.cs:65` | 应补SDK读取/采样/校准辅助入口；读取反馈或更新界面不是已知零毫秒设备操作 |
| BondHeadController.GetLVDTVal | `trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.ForceRelated.cs:94` | 应补SDK读取/采样/校准辅助入口；读取反馈或更新界面不是已知零毫秒设备操作 |
| BondHeadController.SetForceControlPara | `trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.ForceRelated.cs:969` | 应补辅助配置子方法；父入口ChangeChannelAndSetForceControlPara已收录，不能重复相加 |
| BondModuleController.GetXYIpolGroup | `trunk/AKRS.ZX2200/BondSystem/Controllers/BondModuleController.MovementRelated.cs:619` | 获取驱动/插补组对象；不作为新增独立设备动作 |
| BondModuleController.GetXYZIpolGroup | `trunk/AKRS.ZX2200/BondSystem/Controllers/BondModuleController.MovementRelated.cs:652` | 获取驱动/插补组对象；不作为新增独立设备动作 |
| BondModuleController.GetXYZTIpolGroup | `trunk/AKRS.ZX2200/BondSystem/Controllers/BondModuleController.MovementRelated.cs:686` | 获取驱动/插补组对象；不作为新增独立设备动作 |
| System2Controller.GetBondheadForceValue | `trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.cs:1230` | 应补SDK读取/采样/校准辅助入口；读取反馈或更新界面不是已知零毫秒设备操作 |
| System2Controller.GetCalibrateTableForceValue | `trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.cs:1253` | 应补SDK读取/采样/校准辅助入口；读取反馈或更新界面不是已知零毫秒设备操作 |
| FrmGTForceTest1.timer3_Tick | `trunk/AKRS.ZX2200/BondSystem/Controls/Experiment/FrmGTForceTest.cs:167` | 应补SDK读取/采样/校准辅助入口；读取反馈或更新界面不是已知零毫秒设备操作 |
| FrmGTForceTest1.simpleButton2_Click | `trunk/AKRS.ZX2200/BondSystem/Controls/Experiment/FrmGTForceTest.cs:225` | 应补测试监视配置/停止/导出辅助入口；SDK及文件操作没有源码固定总毫秒数 |
| FrmGTForceTest1.simpleButton1_Click_1 | `trunk/AKRS.ZX2200/BondSystem/Controls/Experiment/FrmGTForceTest.cs:262` | 应补测试监视配置/停止/导出辅助入口；SDK及文件操作没有源码固定总毫秒数 |
| FrmGTForceTest1.BtnStartMove_Click | `trunk/AKRS.ZX2200/BondSystem/Controls/Experiment/FrmGTForceTest.cs:601` | 确认遗漏：轴停止；24条GTN_Stop和2条StopCommandList，调用用时及实际停止完成时间未定 |
| UcBondModuelSetting.simpleButton6_Click | `trunk/AKRS.ZX2200/BondSystem/Controls/Experiment/UcBondModuelSetting.cs:1927` | 应补测试监视配置/停止/导出辅助入口；SDK及文件操作没有源码固定总毫秒数 |
| UcBondModuelSetting.simpleButton5_Click | `trunk/AKRS.ZX2200/BondSystem/Controls/Experiment/UcBondModuelSetting.cs:1950` | 应补测试监视配置/停止/导出辅助入口；SDK及文件操作没有源码固定总毫秒数 |
| UcGuideMove.RefreshJoystick | `trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/UcGuideMove.Joystick.cs:127` | 应补SDK读取/采样/校准辅助入口；读取反馈或更新界面不是已知零毫秒设备操作 |
| UcGuideMove.GetSpeedFromJoystick | `trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/UcGuideMove.Joystick.cs:164` | 应补SDK读取/采样/校准辅助入口；读取反馈或更新界面不是已知零毫秒设备操作 |
| ETelDrive.DownloadMapping | `trunk/AKRS.ZX2200/Infrastructure/Utils/ETelDrive.cs:27` | 确认遗漏：补偿数据下载到驱动；单/双轴分别为独立重载，文件及设备通讯/SDK完成时间未定 |
| ETelDrive.DownloadMapping | `trunk/AKRS.ZX2200/Infrastructure/Utils/ETelDrive.cs:54` | 确认遗漏：补偿数据下载到驱动；单/双轴分别为独立重载，文件及设备通讯/SDK完成时间未定 |
| FrmTeachJoystick.BtnSetXInitialVal_Click | `trunk/AKRS.ZX2200/Main/Controls/FrmTeachJoystick.cs:60` | 应补SDK读取/采样/校准辅助入口；读取反馈或更新界面不是已知零毫秒设备操作 |
| FrmTeachJoystick.BtnSetYInitialVal_Click | `trunk/AKRS.ZX2200/Main/Controls/FrmTeachJoystick.cs:77` | 应补SDK读取/采样/校准辅助入口；读取反馈或更新界面不是已知零毫秒设备操作 |
| FrmTeachJoystick.BtnSetTInitialVal_Click | `trunk/AKRS.ZX2200/Main/Controls/FrmTeachJoystick.cs:94` | 应补SDK读取/采样/校准辅助入口；读取反馈或更新界面不是已知零毫秒设备操作 |
| FrmTeachJoystick.BtnSetXMaxVal_Click | `trunk/AKRS.ZX2200/Main/Controls/FrmTeachJoystick.cs:111` | 应补SDK读取/采样/校准辅助入口；读取反馈或更新界面不是已知零毫秒设备操作 |
| FrmTeachJoystick.BtnSetYMaxVal_Click | `trunk/AKRS.ZX2200/Main/Controls/FrmTeachJoystick.cs:128` | 应补SDK读取/采样/校准辅助入口；读取反馈或更新界面不是已知零毫秒设备操作 |
| FrmTeachJoystick.BtnSetTMaxVal_Click | `trunk/AKRS.ZX2200/Main/Controls/FrmTeachJoystick.cs:145` | 应补SDK读取/采样/校准辅助入口；读取反馈或更新界面不是已知零毫秒设备操作 |
| FrmTeachJoystick.timer1_Tick | `trunk/AKRS.ZX2200/Main/Controls/FrmTeachJoystick.cs:184` | 应补SDK读取/采样/校准辅助入口；读取反馈或更新界面不是已知零毫秒设备操作 |
| Machine.OpenCompensate | `trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:609` | 包装入口；实际ETelDrive/GuGaoDrive.Open2DCompensate已收录，不另计独立工序 |

## 44处直接数值等待未独立显示的原因

此表基于AST而不是注释/文本搜索；不把正常DryCycle未走、暂停、while(false)或初始化保存回调混成必耗时。

| 所属方法 | 行/等待 | 核实口径 |
| --- | --- | --- |
| BondModuleController.WaitLaserEncoderWarmupAsync | `trunk/AKRS.ZX2200/BondSystem/Controllers/BondModuleController.cs:881`，1000 ms | IsLaserEncoderConfigured显式初值false时提前返回；配置开启且未预热才按每轮1,000 ms等待。当前默认跳过正确。 |
| S2DispenseController.InterpolationApplication | `trunk/AKRS.ZX2200/BondSystem/Controllers/S2DispenseController.cs:417`，1 ms | 依赖配方集合、就绪结果、工作/停止状态、限位反馈或后台条件；当前未走到此点，不等于源码没有延时。原条件见wait-site-contexts.json。 |
| System2Controller.CleanNozzle | `trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.cs:1222`，50 ms | IsNozzleCleanTableConfigured默认未配置时在前面抛异常，当前入口标空跑不可执行；50 ms不应作为已执行等待。 |
| FrmAssistantDispense.InitControl | `trunk/AKRS.ZX2200/BondSystem/Controls/Assistant/FrmAssistantDispense.cs:316`，500 ms | 向导doneAction保存后待用户触发；非OffLine成功步骤包含500 ms。初始化不应累加，但应独立展示步骤。 |
| BondActionNode.VisionPreviousBondPosition | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.Provider.cs:655`，100 ms | 等待查看上颗焊点图像的开关/轮询分支，依赖IsVisionPreviousBondPosition状态；不是每次必经100 ms。 |
| PickActionNode.PickActionDryRun | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.MoveHelper.cs:915`，20 ms | 暂停分支的20 ms轮询；本模型MachineState=Working，不计入正常工作固定等待。 |
| PickActionNode.SendSignalToFlipTable | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs:589`，20 ms | 暂停分支的20 ms轮询；本模型MachineState=Working，不计入正常工作固定等待。 |
| UpLookCorrectionActionNode.MoveToUplookPos | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs:732`，5 ms | 依赖配方集合、就绪结果、工作/停止状态、限位反馈或后台条件；当前未走到此点，不等于源码没有延时。原条件见wait-site-contexts.json。 |
| UpLookCorrectionActionNode.UpLookVision | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs:1477`，20 ms | 视觉失败且允许自动跳过的恢复分支；需失败结果及UpLookAutoSkipTimes/Count，不是正常成功路径的固定等待。 |
| UpLookCorrectionActionNode.UpLookVisionByCode | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs:1719`，20 ms | 视觉失败且允许自动跳过的恢复分支；需失败结果及UpLookAutoSkipTimes/Count，不是正常成功路径的固定等待。 |
| S2DispenseActionNode.DoWork | `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/DispenseAction/S2DispenseActionNode.cs:151`，100 ms | 等待查看上颗焊点图像的开关/轮询分支，依赖IsVisionPreviousBondPosition状态；不是每次必经100 ms。 |
| System2RunTimeProvider.RecordTime | `trunk/AKRS.ZX2200/BondSystem/Models/Parameter/System2RunTimeProvider.cs:251`，100 ms | DeBugWork专用暂停轮询；当前DryCycle不走该分支。 |
| FrmWaferCameraCalibTeach.InitControl | `trunk/AKRS.ZX2200/CalibSystem/Controls/Assistant/FrmWaferCameraCalibTeach.cs:274`，100 ms | 向导doneAction保存后待用户触发；正常完成10次×100 ms=1,000 ms。初始化不应累加，但应有独立步骤入口。 |
| FrmTestAccuary.BtnStart_Click | `trunk/AKRS.ZX2200/CalibSystem/FrmTestAccuary.cs:216`，30 ms | 依赖用户添加的pointAList及界面次数；当前默认点集为空。总时长缺数据，但可补每点/每轮组成，不能只留泛化未定。 |
| FrmTestAccuary.BtnStart_Click | `trunk/AKRS.ZX2200/CalibSystem/FrmTestAccuary.cs:224`，30 ms | 依赖用户添加的pointAList及界面次数；当前默认点集为空。总时长缺数据，但可补每点/每轮组成，不能只留泛化未定。 |
| FrmTestAccuary.BtnStart_Click | `trunk/AKRS.ZX2200/CalibSystem/FrmTestAccuary.cs:231`，30 ms | 依赖用户添加的pointAList及界面次数；当前默认点集为空。总时长缺数据，但可补每点/每轮组成，不能只留泛化未定。 |
| FrmTestAccuary.simpleButton4_Click | `trunk/AKRS.ZX2200/CalibSystem/FrmTestAccuary.cs:841`，20 ms | 依赖用户添加的pointAList及界面次数；当前默认点集为空。总时长缺数据，但可补每点/每轮组成，不能只留泛化未定。 |
| FrmTestAccuary.simpleButton15_Click | `trunk/AKRS.ZX2200/CalibSystem/FrmTestAccuary.cs:2053`，1000 ms | 依赖用户添加的pointAList及界面次数；当前默认点集为空。总时长缺数据，但可补每点/每轮组成，不能只留泛化未定。 |
| FrmTestAccuary.simpleButton16_Click | `trunk/AKRS.ZX2200/CalibSystem/FrmTestAccuary.cs:2251`，1000 ms | 源码不可达：while(false)，或for起点120但条件i<=0；不应计入。 |
| FrmGlobalCalibrationEx.BarBtnMoveTo_ItemClick | `trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs:1232`，1000 ms | 确认漏展：UIActionAsync回调未接上。勾选模拟运行且回调实际执行时有1,000 ms；不能直接当按钮同步总时长。 |
| FrmGlobalCalibrationEx.BtnMoveToCamCenter_Click | `trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs:1252`，1000 ms | 确认漏展：UIActionAsync回调未接上。勾选模拟运行且回调实际执行时有1,000 ms；不能直接当按钮同步总时长。 |
| DispenseController.InterpolationApplication | `trunk/AKRS.ZX2200/DispenseSystem/Controllers/DispenseController.cs:436`，1 ms | 依赖配方集合、就绪结果、工作/停止状态、限位反馈或后台条件；当前未走到此点，不等于源码没有延时。原条件见wait-site-contexts.json。 |
| S1DispenseActionNode.DoWork | `trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/DispenseBPAction/S1DispenseActionNode.cs:138`，100 ms | 等待查看上颗焊点图像的开关/轮询分支，依赖IsVisionPreviousBondPosition状态；不是每次必经100 ms。 |
| FrmBaseTest.BtnSearchOne_Click | `trunk/AKRS.ZX2200/Experiment/Test/FrmBaseTest.cs:620`，100 ms | 依赖配方集合、就绪结果、工作/停止状态、限位反馈或后台条件；当前未走到此点，不等于源码没有延时。原条件见wait-site-contexts.json。 |
| FrmBaseTest.BondGoHomeWithZMethod | `trunk/AKRS.ZX2200/Experiment/Test/FrmBaseTest.cs:983`，100 ms | 依赖用户测试次数/当前任务与标定状态；需单列每轮组成，不把未知次数当固定总时长。 |
| FrmBaseTest.BondGoHomeWithZMethod | `trunk/AKRS.ZX2200/Experiment/Test/FrmBaseTest.cs:997`，100 ms | 依赖用户测试次数/当前任务与标定状态；需单列每轮组成，不把未知次数当固定总时长。 |
| FrmBaseTest.BondGoHomeWithZMethod | `trunk/AKRS.ZX2200/Experiment/Test/FrmBaseTest.cs:1010`，100 ms | 依赖用户测试次数/当前任务与标定状态；需单列每轮组成，不把未知次数当固定总时长。 |
| FrmBaseTest.BondGoHomeWithZMethod | `trunk/AKRS.ZX2200/Experiment/Test/FrmBaseTest.cs:1024`，100 ms | 依赖用户测试次数/当前任务与标定状态；需单列每轮组成，不把未知次数当固定总时长。 |
| FrmMachineFunctionTest.BtnCaliNozzle_Click | `trunk/AKRS.ZX2200/Experiment/Test/FrmMachineFunctionTest.cs:963`，100 ms | 依赖用户测试次数/当前任务与标定状态；需单列每轮组成，不把未知次数当固定总时长。 |
| FrmTest2.simpleButton18_Click | `trunk/AKRS.ZX2200/Experiment/TestFunction/FrmTest2.cs:532`，200 ms | 源码不可达：while(false)，或for起点120但条件i<=0；不应计入。 |
| FrmTest2.simpleButton18_Click | `trunk/AKRS.ZX2200/Experiment/TestFunction/FrmTest2.cs:547`，200 ms | 源码不可达：while(false)，或for起点120但条件i<=0；不应计入。 |
| FrmVisionAlarm.BtOK_Click | `trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/FrmVisionAlarm.cs:346`，100 ms | 依赖配方集合、就绪结果、工作/停止状态、限位反馈或后台条件；当前未走到此点，不等于源码没有延时。原条件见wait-site-contexts.json。 |
| FrmVisionAlarm.BtEditProgram_Click | `trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/FrmVisionAlarm.cs:433`，100 ms | 依赖配方集合、就绪结果、工作/停止状态、限位反馈或后台条件；当前未走到此点，不等于源码没有延时。原条件见wait-site-contexts.json。 |
| Machine.StartBackGroundThread | `trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:695`，100 ms | new Thread保存的后台监控体；当前未独立展开其100 ms每轮停留，属于Thread/后台分析边界。 |
| FrmLogRecord.Dowork | `trunk/AKRS.ZX2200/SupportFeature/Logs/FrmLogRecord.cs:98`，100 ms | 依赖配方集合、就绪结果、工作/停止状态、限位反馈或后台条件；当前未走到此点，不等于源码没有延时。原条件见wait-site-contexts.json。 |
| FrmTemperatureMonitoring.GetTemperatureData | `trunk/AKRS.ZX2200/SupportFeature/TemperatureMonitoring/FrmTemperatureMonitoring.cs:148`，100 ms | 依赖配方集合、就绪结果、工作/停止状态、限位反馈或后台条件；当前未走到此点，不等于源码没有延时。原条件见wait-site-contexts.json。 |
| TransportController.TransferLoadBeltToDispense | `trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs:577`，50 ms | 依赖在线上下料配置及载具状态的特定分支；缺少配置/状态不能作为默认空跑必经等待。 |
| TransportController.TransferWaitingUnloadToUnloadBin | `trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs:2098`，500 ms | 依赖在线上下料配置及载具状态的特定分支；缺少配置/状态不能作为默认空跑必经等待。 |
| TransportTask.Start | `trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:140`，1000 ms | 正常生产启动体，DryCycle已改走StartDryRun或启动前返回；不应混入空跑单轮。 |
| TransportTask.Start | `trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:268`，1000 ms | 正常生产启动体，DryCycle已改走StartDryRun或启动前返回；不应混入空跑单轮。 |
| TransportTask.Start | `trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:370`，1000 ms | 正常生产启动体，DryCycle已改走StartDryRun或启动前返回；不应混入空跑单轮。 |
| UnloaderTask.Start | `trunk/AKRS.ZX2200/TransportSystem/Tasks/UnloaderTask.cs:71`，1000 ms | 正常生产启动体，DryCycle已改走StartDryRun或启动前返回；不应混入空跑单轮。 |
| Block.MatchResult | `trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.cs:562`，10 ms | 依赖配方集合、就绪结果、工作/停止状态、限位反馈或后台条件；当前未走到此点，不等于源码没有延时。原条件见wait-site-contexts.json。 |
| FlipTask.DoWork | `trunk/AKRS.ZX2200/WaferSubSystem/Tasks/FlipTask.cs:181`，10 ms | 依赖配方集合、就绪结果、工作/停止状态、限位反馈或后台条件；当前未走到此点，不等于源码没有延时。原条件见wait-site-contexts.json。 |

## 117处当前延时值未定的源码位置

同一源码位置在不同入口/分支的表现可能不同：这里列的是出现过未定值的位置，不表示该位置在所有入口都未定。原条件和受影响行ID在unknown-sites.json中。

| 源码 | 延时表达式 | 缺少的当前输入 |
| --- | --- | --- |
| `trunk/AKRS.ZX2200/BondSystem/BondForce/Controllers/ClosedLoopCalibrationController.cs:312` | `Thread.Sleep(delay)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/BondSystem/BondForce/Controllers/ClosedLoopCalibrationController.cs:568` | `Thread.Sleep(delay)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/BondSystem/BondForce/Forms/FrmInspectForceRes.cs:311` | `Thread.Sleep(this.delay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs:204` | `Thread.Sleep(pickActionParameter.TableBlowDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs:282` | `DelayHelper.Delay(pickActionParameter.PickDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs:473` | `DelayHelper.Delay(placementDelay)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs:493` | `DelayHelper.Delay(bondActionParameter.BlowingDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs:501` | `DelayHelper.Delay(bondActionParameter.VacuumOffDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs:585` | `Thread.Sleep(nozzle.AfterPickupVacuumCheckDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs:608` | `Thread.Sleep(nozzle.AfterBondingVacuumCheckDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/BondSystem/Controllers/BondModuleController.MovementRelated.cs:815` | `Thread.Sleep(this.bondDevicePara.BondHeadParam.ThrowBlowDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/BondSystem/Controllers/BondModuleController.MovementRelated.cs:830` | `Thread.Sleep(this.bondDevicePara.BondHeadParam.ThrowBlowDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/BondSystem/Controllers/SlideFluxerController.cs:149` | `Thread.Sleep(delay)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.Assistant.cs:594` | `Thread.Sleep(component.OpenWaferTableVacuumBeforePickDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.Vision.cs:242` | `DelayHelper.Delay((int)this.system2Configuration.DownLookVisionDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.Vision.cs:454` | `DelayHelper.Delay((int)this.system2Configuration.DownLookVisionDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.Vision.cs:613` | `DelayHelper.Delay((int)this.system2Configuration.DownLookVisionDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.cs:470` | `Thread.Sleep(this.bondDevicePara.BondHeadParam.ChangeToolBlowDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/BondSystem/Controls/Experiment/FrmBondheadTest.cs:409` | `Thread.Sleep(this.delay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/BondSystem/Controls/Experiment/FrmBondheadTest.cs:552` | `Thread.Sleep(this.delay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/BondSystem/Controls/Experiment/FrmBondheadTest.cs:668` | `Thread.Sleep(delay)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/BondSystem/Controls/Experiment/FrmGTForceTest.cs:531` | `Thread.Sleep(delay)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.Provider.cs:353` | `DelayHelper.Delay(bondActionParameter.BlowingDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.cs:489` | `DelayHelper.Delay(placementDelay)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.Provider.cs:92` | `DelayHelper.Delay(bondActionParameter.BlowingDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.cs:735` | `DelayHelper.Delay(placementDelay)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.cs:820` | `Thread.Sleep(pickActionParameter.TableBlowDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs:250` | `DelayHelper.Delay(System2Domain.GetInstance().System2Configuration.DownLookVisionDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmBondCompensateCalibration.cs:447` | `Thread.Sleep(this.BondCompensateCalibration.PrDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs:606` | `Thread.Sleep(this.GlobalCalibrationDomain.Delay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs:699` | `Thread.Sleep(this.GlobalCalibrationDomain.Delay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs:771` | `Thread.Sleep(this.GlobalCalibrationDomain.Delay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs:887` | `Thread.Sleep(this.GlobalCalibrationDomain.Delay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs:968` | `Thread.Sleep(this.GlobalCalibrationDomain.Delay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs:1084` | `Thread.Sleep(this.GlobalCalibrationDomain.Delay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs:1161` | `Thread.Sleep(this.GlobalCalibrationDomain.Delay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs:1448` | `Thread.Sleep(this.GlobalCalibrationDomain.Delay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs:1557` | `Thread.Sleep(this.GlobalCalibrationDomain.Delay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/CalibSystem/Test/TestAlg.cs:152` | `Thread.Sleep(interval)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/CalibSystem/Test/TestAlg.cs:254` | `Thread.Sleep(interval)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/CalibSystem/Test/TestAlg.cs:338` | `Thread.Sleep(interval)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/CalibSystem/Test/TestAlg.cs:1046` | `Thread.Sleep(sleepTime)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/CalibSystem/Test/TestAlg.cs:1071` | `Thread.Sleep(sleepTime)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/CalibSystem/TestControls/FrmCalibTest.cs:114` | `Thread.Sleep(prInterval)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/CalibSystem/TestControls/FrmCalibTest.cs:147` | `Thread.Sleep(prInterval)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/CalibSystem/TestControls/FrmCalibTest.cs:366` | `Thread.Sleep(prInterval)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/CalibSystem/TestControls/FrmMoveLocateTest.cs:96` | `Thread.Sleep(prInterval)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/CalibSystem/TestControls/FrmMoveLocateTest.cs:116` | `Thread.Sleep(prInterval)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/Experiment/AccuracyExperiment/FrmAccuracyExperiment.cs:271` | `Thread.Sleep((int)this.SpBondCameraDelay.Value)` | 界面控件当前值/类型转换结果 |
| `trunk/AKRS.ZX2200/Experiment/AccuracyExperiment/FrmAccuracyExperiment.cs:302` | `Thread.Sleep((int)this.SpUpLookCameraDelay.EditValue)` | 界面控件当前值/类型转换结果 |
| `trunk/AKRS.ZX2200/Experiment/AccuracyExperiment/FrmAccuracyExperiment.cs:346` | `Thread.Sleep((int)this.SpBondCameraDelay.Value)` | 界面控件当前值/类型转换结果 |
| `trunk/AKRS.ZX2200/Experiment/AccuracyExperiment/FrmAccuracyExperiment.cs:391` | `Thread.Sleep((int)this.SpBondCameraDelay.Value)` | 界面控件当前值/类型转换结果 |
| `trunk/AKRS.ZX2200/Experiment/AccuracyExperiment/FrmAccuracyExperiment.cs:444` | `Thread.Sleep((int)this.SpUpLookCameraDelay.EditValue)` | 界面控件当前值/类型转换结果 |
| `trunk/AKRS.ZX2200/Experiment/AccuracyExperiment/FrmAccuracyExperiment.cs:488` | `Thread.Sleep((int)this.SpUpLookCameraDelay.Value)` | 界面控件当前值/类型转换结果 |
| `trunk/AKRS.ZX2200/Experiment/AccuracyExperiment/FrmAccuracyExperiment.cs:532` | `Thread.Sleep((int)this.SpUpLookCameraDelay.Value)` | 界面控件当前值/类型转换结果 |
| `trunk/AKRS.ZX2200/Experiment/AccuracyExperiment/FrmAccuracyExperiment.cs:585` | `Thread.Sleep((int)this.SpUpLookCameraDelay.EditValue)` | 界面控件当前值/类型转换结果 |
| `trunk/AKRS.ZX2200/Experiment/AccuracyExperiment/FrmAccuracyExperiment.cs:620` | `Thread.Sleep((int)this.SpBondCameraDelay.EditValue)` | 界面控件当前值/类型转换结果 |
| `trunk/AKRS.ZX2200/Experiment/AccuracyExperiment/FrmAccuracyExperiment.cs:628` | `Thread.Sleep((int)this.SpBondCameraDelay.EditValue)` | 界面控件当前值/类型转换结果 |
| `trunk/AKRS.ZX2200/Experiment/AccuracyExperiment/FrmAccuracyExperiment.cs:669` | `Thread.Sleep((int)this.SpUpLookCameraDelay.EditValue)` | 界面控件当前值/类型转换结果 |
| `trunk/AKRS.ZX2200/Experiment/AccuracyExperiment/FrmAccuracyExperiment.cs:678` | `Thread.Sleep((int)this.SpBondCameraDelay.EditValue)` | 界面控件当前值/类型转换结果 |
| `trunk/AKRS.ZX2200/Experiment/AccuracyExperiment/FrmAccuracyExperiment.cs:719` | `Thread.Sleep((int)this.SpUpLookCameraDelay.EditValue)` | 界面控件当前值/类型转换结果 |
| `trunk/AKRS.ZX2200/Experiment/AccuracyExperiment/FrmAccuracyExperiment.cs:727` | `Thread.Sleep((int)this.SpUpLookCameraDelay.EditValue)` | 界面控件当前值/类型转换结果 |
| `trunk/AKRS.ZX2200/Experiment/AccuracyExperiment/FrmAccuracyExperiment.cs:764` | `Thread.Sleep((int)this.SpBondCameraDelay.EditValue)` | 界面控件当前值/类型转换结果 |
| `trunk/AKRS.ZX2200/Experiment/AccuracyExperiment/FrmAccuracyExperiment.cs:837` | `Thread.Sleep((int)this.SpUpLookCameraDelay.Value)` | 界面控件当前值/类型转换结果 |
| `trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmRepeatPositionAccuracy.cs:282` | `Thread.Sleep(delay)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmRepeatPositionAccuracy.cs:307` | `Thread.Sleep(delay)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmRepeatPositionAccuracy.cs:330` | `Thread.Sleep(delay)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmRepeatPositionAccuracy.cs:512` | `Thread.Sleep(delay)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmRepeatPositionAccuracy.cs:721` | `Thread.Sleep(delay)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmRepeatPositionAccuracy.cs:901` | `Thread.Sleep(delay)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmRepeatPositionAccuracy.cs:1085` | `Thread.Sleep(delay)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmRepeatPositionAccuracy.cs:1251` | `Thread.Sleep(delay)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmRepeatPositionAccuracy.cs:1484` | `Thread.Sleep(delay)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmRepeatPositionAccuracy.cs:1510` | `Thread.Sleep(delay)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmRepeatPositionAccuracy.cs:1532` | `Thread.Sleep(delay)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmUpLookMarkTest.cs:132` | `Thread.Sleep(this.visionDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/Experiment/Test/FrmBMCTest.cs:548` | `Thread.Sleep(this.visionDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/Experiment/Test/FrmBMCTest.cs:598` | `Thread.Sleep(this.visionDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/Experiment/Test/FrmBMCTest.cs:698` | `Thread.Sleep(this.visionDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/Experiment/Test/FrmBMCTest.cs:719` | `Thread.Sleep(this.visionDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/Experiment/Test/FrmBaseTest.cs:211` | `Thread.Sleep(delayPhoto)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/Experiment/Test/FrmBaseTest.cs:407` | `Thread.Sleep(angleDelayPhoto)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/Experiment/Test/FrmVibrationTest.cs:298` | `Thread.Sleep(Convert.ToInt32(SpDelay.EditValue))` | 界面控件当前值/类型转换结果 |
| `trunk/AKRS.ZX2200/SupportFeature/TemperatureMonitoring/FrmTemperatureMonitoring.cs:125` | `Thread.Sleep((int)this.SpTimes.Value)` | 界面控件当前值/类型转换结果 |
| `trunk/AKRS.ZX2200/TransportSystem/Controllers/BondSubSectionController.cs:91` | `Thread.Sleep(afterDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/TransportSystem/Controllers/BondSubSectionController.cs:103` | `Thread.Sleep(afterDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/TransportSystem/Controllers/BondSubSectionController.cs:115` | `Thread.Sleep(afterDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/TransportSystem/Controllers/BondSubSectionController.cs:127` | `Thread.Sleep(afterDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/TransportSystem/Controllers/BondSubSectionController.cs:174` | `Thread.Sleep(this.bondSubSectionProgram.BondinsertSetting.BeforeClampingDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/TransportSystem/Controllers/BondSubSectionController.cs:177` | `Thread.Sleep(this.bondSubSectionProgram.BondinsertSetting.AfterClampingDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/TransportSystem/Controllers/BondSubSectionController.cs:256` | `Thread.Sleep(this.bondSubSectionProgram.BondinsertSetting.BeforeUnClampingDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/TransportSystem/Controllers/BondSubSectionController.cs:258` | `Thread.Sleep(this.bondSubSectionProgram.BondinsertSetting.AfterUnClampingDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/TransportSystem/Controllers/DispenseSubSectionController.cs:67` | `Thread.Sleep(afterDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/TransportSystem/Controllers/DispenseSubSectionController.cs:83` | `Thread.Sleep(afterDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/TransportSystem/Controllers/DispenseSubSectionController.cs:93` | `Thread.Sleep(afterDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/TransportSystem/Controllers/DispenseSubSectionController.cs:109` | `Thread.Sleep(afterDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/TransportSystem/Controllers/DispenseSubSectionController.cs:119` | `Thread.Sleep(afterDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/TransportSystem/Controllers/DispenseSubSectionController.cs:129` | `Thread.Sleep(afterDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/TransportSystem/Controllers/DispenseSubSectionController.cs:188` | `Thread.Sleep(this.dispenseSubSectionProgram.BondinsertSetting.BeforeClampingDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/TransportSystem/Controllers/DispenseSubSectionController.cs:195` | `Thread.Sleep(this.dispenseSubSectionProgram.BondinsertSetting.AfterClampingDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/TransportSystem/Controllers/DispenseSubSectionController.cs:280` | `Thread.Sleep(this.dispenseSubSectionProgram.BondinsertSetting.BeforeUnClampingDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/TransportSystem/Controllers/DispenseSubSectionController.cs:289` | `Thread.Sleep(this.dispenseSubSectionProgram.BondinsertSetting.AfterUnClampingDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/WaferSubSystem/Controllers/EjectController.cs:431` | `Thread.Sleep(EjectDevicePara.DelayEjectBlowHold)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/WaferSubSystem/Controllers/FlipTableController.cs:169` | `Thread.Sleep(this.flipModuleProgram.CurrentFlipTool.ComponentCheckDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/WaferSubSystem/Controllers/FlipTableController.cs:229` | `Thread.Sleep(delay)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/WaferSubSystem/Controllers/MagazineController.cs:403` | `Thread.Sleep(MagazineBoxDevicePara.DelayPushHold)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferSubController.cs:99` | `Thread.Sleep(delayAfter)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferSubController.cs:134` | `Thread.Sleep(delayAfter)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferSubController.cs:159` | `Thread.Sleep(delayAfter)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferSubController.cs:184` | `Thread.Sleep(delayAfter)` | 调用方实参或其本次更新后的值 |
| `trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferSubController.cs:269` | `Thread.Sleep(pickupDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferTableController.cs:598` | `Thread.Sleep(WaferTableDevicePara.DelayHotBlowerHold)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferTableController.cs:608` | `Thread.Sleep(WaferTableDevicePara.DelayHotBlowerHold)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferTableController.cs:610` | `Thread.Sleep(WaferTableDevicePara.DelayHotBlowerAfterClose)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.cs:500` | `Thread.Sleep(this.DelayPhoto)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs:74` | `Thread.Sleep(WaferSubDevicePara.GetInstance().WaferTableDevicePara.DelaySearchDieContinue)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |
| `trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs:275` | `Thread.Sleep(currentNeedCarrierConfig.OpenWaferTableVacuumBeforePickDelay)` | 配方/载具/成员当前值；不能无条件沿用声明初值 |

## 范围外源码及复核验证

81个排除文件也做了延时/运动形态扫描：57个属于未引用的示例/测试工程，24个没有进入当前Compile。其中3个文件有6处相关调用，分别是未编译的FrmRotateCenterAccuracy.cs，以及未引用的InterpolationMovementTest/FrmTest.cs与Helper/Movements.cs。它们不属于当前ZX2200可执行目录，排除原因与位置保存在excluded-timing-candidates.json；不能默默混入当前运行耗时。

本轮实际执行：前端动作表2文件13项测试、后端源码接口/缓存2文件9项测试通过（2项耗时很长的真实源码回归本轮未重跑）；全2,737行真实显示/筛选/导出函数检查无丢失；新编译目录逐ID一致；307处已显示的直接字面量等待无数值差异。未采集覆盖率，未运行目标设备、未新增浏览器视觉验收。质量判断为中：显示/接口证据充分，全面性检查已找出反例，计算引擎不能据此判全功能通过。

正式服务PID46604健康，缓存仍为已发布v33。trunk 6,281个文件集合及SHA256再次一致。测试使用现有隔离fixture；未向正式库采集或导入数据。报告源码版本为d0a554dbe7a48e1306b36f1acd963bf37b0a51d9c87c97f59cef330b801eee0c，当前压缩缓存SHA256为55ad60232c99c27281530a13d8a424cafe8bf712fdfbbd4226cd6e6c7f67de0a。

审计原始数据与可重跑脚本位于output/action-timing-recheck-20261024/。这些是本地核实资料，Git提交保存本报告及项目状态说明。此前1,174项回归是v33发布时的既有检查，未发现这批遗漏；本轮没有把历史通过数冒充新执行结果。
