# 焊后结果：数据库入队、实时曲线与生产补偿

更新：2026-09-29。仅分析 `trunk` 中这条反馈链及其任务失败边界。对应[31 段源码快照及 6 处回调引用](postbond-feedback-evidence.json)，复核命令为 `node scripts/build-postbond-feedback-evidence.cjs --check`。此处没有执行设备、数据库或 WinForms。

## 工作步骤摘要

图表状态：[焊后反馈与补偿失败路径图](postbond-feedback-workflow.html)已交付，Showcase 9/9 与四视口浏览器检查通过；浅色/深色最终截图已目视复核。[交付回执](postbond-feedback-diagram-status.json)提供规格和 HTML 哈希、11 条关系对应的源码证据 ID。图中依赖箭头不表示数据库落库完成或硬件实际到位；完整条件与边界见下文。

焊后结果进入 `AddDefectResult` → 先调用 `SaveDataToDb` 入队 → 同步调用 `RePostBondInspection` → 默认委托更新按检测名分组的内存列表 → 已注册窗体回调安排 `Task.Run` → 工作任务调用 `Invoke(ReFreshData)` → UI 读取当前选中检测名的共享列表并刷新表格/曲线。后续生产坐标计算也读取这一共享数据所形成的焊后补偿；它不是等待数据库写入完成后再读取的反馈链。

## 顺序与模块调用

1. **发布顺序。** [StatisticsDomain.cs:407–422](../../trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsDomain.cs#L407)先执行阻塞队列的 Add，再直接调用委托，没有 Task 包装、空值检查或此处的 catch。队列 Add 尚未返回时不会通知曲线；若委托随后失败，代码没有撤回此前入队的对象。入队完成不表示 SQL 写入成功，见[保存链路](async-persistence-ingress-review.md)。
2. **默认内存更新。** [DefectCompensate.cs:29–50](../../trunk/AKRS.ZX2200/SupportFeature/Compensate/DefectCompensate/DefectCompensate.cs#L29)的委托是可设置的 Action 属性，不是 event；默认实现按 `DefectName` 建列表、在索引 0 插入最新对象，数量超过 2000 时删除索引 2000。这是默认处理器，不能假定运行期从未替换它；本次词法盘点在 trunk 找到其定义、一次调用和两对订阅/退订，未覆盖反射或外部程序集替换。
3. **实时曲线窗体。** [FrmPostBondResCurve.cs:28–33](../../trunk/AKRS.ZX2200/BondSystem/Controls/Manual/FrmPostBondResCurve.cs#L28)在构造完成初始化后订阅；[64–87](../../trunk/AKRS.ZX2200/BondSystem/Controls/Manual/FrmPostBondResCurve.cs#L64)每次回调创建一个 Task，检查 `Created` / `Disposing` 后同步 Invoke 到 UI。返回的 Task 没有被保存或等待；此任务体没有 catch。不得因此直接断言进程会崩溃。
4. **数据窗体的不同边界。** [FrmPostBondData.cs:325–340](../../trunk/AKRS.ZX2200/BondSystem/Controls/Setting/PostBond/FrmPostBondData.cs#L325)在 Load 时订阅；[71–100](../../trunk/AKRS.ZX2200/BondSystem/Controls/Setting/PostBond/FrmPostBondData.cs#L71)同样创建 Task，但额外检查 `IsDisposed` / `IsHandleCreated`，并以空 catch 吞掉 Invoke 区域异常。它还调用 `RefreshIndicator`，曲线窗体只调用 `RefreshLine`。两种实现不可混为同一刷新契约。
5. **显示数据来源。** 两者的 AddDefectData 参数没有参与筛选；真正刷新时读取当时选中的检测名。两份 [GetDataSource](../../trunk/AKRS.ZX2200/BondSystem/Controls/Manual/FrmPostBondResCurve.cs#L134) / [GetDataSource](../../trunk/AKRS.ZX2200/BondSystem/Controls/Setting/PostBond/FrmPostBondData.cs#L106)返回字典中原 List 引用，没有查询数据库或制作快照。当前回调和读列表局部代码没有锁；是否产生现场并发问题还需运行证据。不能保证每个事件对应一个不同的画面样本。
6. **关闭退订。** [曲线窗体:224](../../trunk/AKRS.ZX2200/BondSystem/Controls/Manual/FrmPostBondResCurve.cs#L224)与[数据窗体:337](../../trunk/AKRS.ZX2200/BondSystem/Controls/Setting/PostBond/FrmPostBondData.cs#L337)在 FormClosed 退订；Designer 中分别有[事件绑定](../../trunk/AKRS.ZX2200/BondSystem/Controls/Manual/FrmPostBondResCurve.Designer.cs#L313)及[Load/Closed 绑定](../../trunk/AKRS.ZX2200/BondSystem/Controls/Setting/PostBond/FrmPostBondData.Designer.cs#L962)。退订不能等同于取消先前已安排的 Task，这些关闭方法没有等待它们。

## 返回自动生产的路径

生产动作在 [BondActionNode.cs:150](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.cs#L150)调用 `CalculateBondPos`；该方法在 [Provider.cs:521–527](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.Provider.cs#L521)取 `GetPostBondCompensation`，并加到 `realBondPositionInG0`。这里证明坐标计算依赖，不表示设备已经执行了该位置。

[GetPostBondCompensation:187–228](../../trunk/AKRS.ZX2200/SupportFeature/Compensate/DefectCompensate/DefectCompensate.cs#L187)先检查按基板补偿模式，启用则返回默认点；否则按焊点名查 S2 检测步骤，对启用焊后补偿的检测调用 [GetPostCompensation:57–84](../../trunk/AKRS.ZX2200/SupportFeature/Compensate/DefectCompensate/DefectCompensate.cs#L57)。后者从同一字典复制列表，检查数量、取最近 N 项、分别筛选绝对偏差小于 50 的 X/Y 样本，再求均值、除 1000 并乘比例。数量不足或检测名不存在时返回默认点；筛选后空集合的 Average 没有局部保护，不能保证该路径始终返回数值。此处不推断异常能否在更外层恢复。

## UI 清空的业务影响及未证实入口

- 两个清空处理器均在用户选择 OK 后执行整个 `DefectDataS.Clear()`，再刷新当前窗体；不是只清当前检测名。见[曲线窗体:208–217](../../trunk/AKRS.ZX2200/BondSystem/Controls/Manual/FrmPostBondResCurve.cs#L208)与[数据窗体:276–285](../../trunk/AKRS.ZX2200/BondSystem/Controls/Setting/PostBond/FrmPostBondData.cs#L276)。它们未调用数据库删除，也未撤回排队记录；清空的是后续上述补偿取样所依赖的内存数据。
- [BarBtPostBondRes_ItemClick:195–205](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.DataAdministrator.cs#L195)包含曲线窗体创建/Show 代码，另一数据窗体 Show 调用是注释。当前 trunk C# 按处理器全名搜索只定位到方法定义，未发现显式事件绑定或调用。故这里只登记处理器体，不把它画成已证实可点击的现场入口；动态绑定、其他入口及部署版本仍须核对。

## 后续验收

### 入口与外层失败处理：已补齐的静态调用链

此前未定位显式绑定的是旧 `BarBtPostBondRes_ItemClick`，不能扩大为所有焊后窗口都没有入口。当前源码另有完整的新入口：[Designer:1691–1695](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Designer.cs#L1691)将“实时焊后曲线”的 `BtPostBondDataNew.ItemClick` 绑定到处理器，[2035](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Designer.cs#L2035)将按钮加入 ribbon 分组；[UcMainSystem.cs:1964–1967](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L1964)调用 `ShowForm<FrmPostBondData>()`。该辅助方法在[ControlHelper.cs:78–98](../../trunk/AKRS.ZX2200/Infrastructure/Utils/ControlHelper.cs#L78)先找未释放的同类型打开窗体，无实例则反射构造并 Show。随后接入前文已核对的 Load 订阅。这里只证明源码接线，不证明现场权限、可见性或部署版本。旧曲线窗体处理器仍未找到显式绑定。

补偿空集合异常的生产传播路径现已追到任务层：

1. `GetPostCompensation` → `GetPostBondCompensation` → `CalculateBondPos`，由[BondActionNode.DoWork:125–150](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.cs#L125)的 try 区域调用；离线和空跑分别在此调用之前返回，因此不能把此补偿路径应用到所有工作模式。
2. [DoWork:366–376](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.cs#L366)捕获 Exception，先写错误日志，再弹消息，返回 `ExcuteResult.Exception`；finally 设置节点 State=Stop 并调用 WorkStop。此分支没有重算或用默认补偿继续；日志、消息框或 WorkStop 若再抛异常，不能保证正常返回该枚举。WorkStart/初始日志在 try 之前，也不属于这个捕获范围。
3. [BondTask:214–234](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L214)取得动作节点，经 IsDoWork 判断后调用 DoWork 并分派返回值；[Exception 分支:260–275](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L260)记录结果、调用 Machine.Stop、MoveBondZToSafePos，并在配置胶盘时调用 SlideFluxerHomeWaitArrive，随后 return。该分支不是 Retry，也不进入 Alarm 的“终止/重试/忽略”选择。

这证明了代码中的失败处理顺序，不证明停止成功、安全位实际到达或现场弹窗行为；如果上述调用本身失败，后续语句可能不执行。相关入口与失败处理原文、文件哈希已加入[可再生证据](postbond-feedback-evidence.json)。外层失败处理的静态链已完成，运行验证仍未完成。

### 二次异常、任务退出与重启门控

核对[BondTask.DoWork 全方法:100–355](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L100)及[Start 包装:361–377](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L361)，两层均没有 try/catch/finally。Start 以 `Task.Factory.StartNew`、`LongRunning`、`CancellationToken.None` 创建任务，任务体先设置线程名再执行 DoWork；Start 的 true 返回值不等待生产成功。紧邻的[AbortThread:382–384](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L382)为空实现。

| 实际分支 | 源码中会继续执行什么 | 不能据此承诺什么 |
| --- | --- | --- |
| 补偿失败，节点日志/弹窗/finally 均正常 | 返回 Exception，BondTask 调用 Stop 和安全位指令后 return | 返回任务方法不等于产品成功完成 |
| 节点 catch 的日志或弹窗再次抛异常 | 仍进入节点 finally；异常越过 DoWork 返回值分派 | 不能保证执行 BondTask 的 Exception 分支或 Machine.Stop |
| 节点 finally 的 WorkStop 抛异常 | 未正常返回 Exception；BondTask 外层没有兜底 | 节点 State 已置 Stop 不等于机器也已停止 |
| BondTask Exception 分支的日志、Stop 或回位调用抛异常 | 该调用之后的本地语句不再正常顺序执行；没有外围 finally 清理 | 不能保证后续安全位/胶盘指令被执行 |

[Machine.Stop:347–378](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L347)也没有本地捕获：依次置设备 Stop、清弹窗、设置报警器、关闭单步、复位需料信号、按配置关闭在线需料输出、关闭顶针真空并清检测计数。因置状态在前，后续调用失败时可能已经显示 Stop，却未走完本次停止处理。这里不把控制调用等同于硬件反馈。

再次启动的局部门控也不能证明故障已恢复：[IsAllowTaskClosed:201–214](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.cs#L201)把 BondWorkTask 放入列表，[253–262](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.cs#L253)只对 Running 返回 false，其他状态不会在此阻止；BondTask.Start 同样只排除 Running。因此 Faulted 并不是这两处的显式拒绝条件，但是否真正再次启动还取决于其他机器启动检查。相关完整停止/重启上下文见[停止清理复核](stop-cleanup-review.md)与[启动链复核](startup-call-review.md)。

[Program:99–105](../../trunk/AKRS.ZX2200/Program.cs#L99)注册的是 WinForms ThreadException 和 AppDomain UnhandledException，[281–296](../../trunk/AKRS.ZX2200/Program.cs#L281)处理体仅显示异常信息，未在这两个处理体调用 Stop。不能把这两项注册当作 Bond Task 自动观察和停止机制。已有[全 trunk 词法审计](task-exception-audit.json)覆盖 1436 个 C# 文件，未找到 UnobservedTaskException、OnlyOnFaulted、TaskStatus.Faulted 或 IsFaulted 的具名引用；这不排除外部程序集、反射或其他表达方式，详见[异步异常审计](async-notification-exception-review.md)。

**待验证边界：**尚未注入日志/弹窗/WorkStop/停止指令故障，也未观察生产 Task 的故障状态、全局处理器触发、现场设备停止或故障后重启。本节新增的是源码传播和门控证据，不将静态无 catch 检查冒充整机故障测试。

### 已完成：补偿原方法的受控输入验证

[测试脚本](../../scripts/test-postbond-compensation.cjs)直接提取并编译上述 `GetPostCompensation:57–84`，未改写方法体；使用真实 LINQ，点、检测配置、统计实体和字典容器由最小测试替身提供。配置字段类型按[配置源码:227–238](../../trunk/AKRS.ZX2200/BondSystem/Models/Repositories/PostBondInspection/PostBondInspection.cs#L227)核对：参考次数为 double，比例为 int。[测试回执](postbond-compensation-test.json)保存两处源码文件哈希、原文片段及 18 项通过结果，可用统一验证入口重跑。

| 场景 | 原方法实际结果 | 对交接的意义 |
| --- | --- | --- |
| 检测名不存在或样本总数不足 | 返回默认点 | 与筛选后无有效样本不同 |
| 前 N 项样本、独立 X/Y 筛选 | 各轴分别求均值，再除 1000、乘比例/100 | 两轴可能来自不同子集；原列表不被改变 |
| 偏差恰为正负 50 | 被严格小于条件排除 | 阈值边界不可画成包含 50 |
| X 或 Y 筛选结果为空 | InvalidOperationException | 本方法没有默认值回退；外层恢复尚待核对 |
| 已存在检测名且次数为 0 或负数 | Take 后为空，Average 抛异常 | 测试人为输入，不表示 UI 或部署配方允许该值 |
| 次数为 2.5 | 两项样本不足；三项样本时取前两项 | 数量比较在整数转换之前 |
| 比例为 0 且筛选为空 | 仍然抛异常 | 乘零不跳过前面的均值计算 |
| 负比例、非有限样本 | 负比例直接参与计算；NaN/Infinity 不通过筛选 | 只验证方法局部，不推断生产数据可达性 |
| 字典清空后，逐步重新提供样本 | 缺名/不足返回默认点，达到次数后恢复计算 | 模拟字典状态，未运行生产回调或 UI 清空处理器 |

尚未测试真实 `AKRSPoint3D` 默认构造、UI 参数验证、生产回调并发、窗口关闭、设备动作或外层异常恢复；因此这 18 项通过不能计作模块完整验收。以下现场事项仍保留。

优先核对现场实际入口、配方中的检测名和补偿开关；在隔离 UI 环境验证关闭期间回调、高频事件下任务积压、共享 List 读取和清空。验证数据库写入失败时界面仍有数据的条件，避免把曲线显示误当作落库成功。补偿筛选无有效样本及清空后重新累积的原方法检查已完成，仍需生产类型、真实配置与现场行为验收。本报告不扩大现有模块完整验收范围。
