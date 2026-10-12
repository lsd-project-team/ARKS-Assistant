# 送板机传入料段：原超时、前端传感器与实际第一任务验证

原 `TransferAutoLoaderToLoading`、入料前端物料的控制器/模组方法与仓库 getter，现接入完整生产器、两条 UI、准备链、真实供晶 Task、原 Stop 和既有六阶段下游链。238项受控检查通过：159个完整方法、95个属性、10个枚举、15个字段、23条原信号初始化契约，共279段原代码、123个来源文件；本专题180段链路快照。

本轮使用原 Stopwatch、5000ms条件和全部原Thread.Sleep，没有加速时间或替换等待逻辑。前端 Sensor/SDK、硬件与参数仓库、对话框/日志/Save、域和程式生命周期为明确替身；坐标 SDK、子实体、TuService/行列/动作服务、配置及类型适配继承上一专题边界。整个原项目构建、部署配置/DLL、原生 UI与设备尚未验收；最后一条料仓到点胶传输仍待集成，29源码组保持partial。

## 第一任务与七阶段连续链

Online和OnlineWithAutoLoader分别在两条UI下分配实际第一父任务；其余四种配置不分配。直接手动方法可在六种配置执行，不依赖父任务分配。isManual只出现在原签名，方法内未使用，成功及超时分支均分别验证。

原初始化只有Online设置上游需料false，OnlineWithAutoLoader没有这次初始化输出。原传输再写true，感应到前端物料后写Transfering、异步运动、200ms、需料false、500ms和StopMove(false,true)。成功将Loading状态写HasMaterial，再构造Unit(System2)并Save，原方法没有将Transfering改回Ready。源速度80×倍率0.625=50，距离41。

实际第一父任务Success只清除PrepareFeeding，没有点胶完成事件。已存在物料时原方法关闭需料并返回NoStart，不创建载具或Save。父任务只检查PrepareFeeding；ContinuousFeeding=false不阻止它执行。PrepareFeeding=false时原父任务继续活跃但不进入控制器，恢复true后实际运行。

两条UI的七阶段链依次执行送板机入料、入料到点胶1、点胶1到2、点胶到Bond、Bond到待出料、待出料到出料、出料到收板机。Unit在同一身份下构造一次、原Refresh四次、Save五次。系统2偏移先使受控坐标X=14；入料到点胶的原Refresh重建坐标为10并清除该偏移标志；点胶分段偏移后，下游Refresh再次重建。最终数值限于明确坐标/服务替身，未执行坐标SDK。

## 真实超时、重试和忽略后的再次要料

前端无料时循环通过原GetInputValue和Thread.Sleep(1)采样。原Stopwatch超过5000ms才写Alarm、关闭需料、显示超时对话框；外部计时只观察耗时，不替换原计时器。两种manual参数下Retry/Abort/Ignore均实际等待至少5秒。另一次Retry后继续无料的检查等待两个完整5秒，证明goto Retry重新启动计时器。

Retry重新请求料片，感应成功后提交HasMaterial/Unit/Save但仍Transfering。Abort返回Abort，直接调用不自带Stop；实际第一父任务则调用原Stop并退出，真实供晶一并结束。Ignore关闭ContinuousFeeding并返回NoStart，保留Alarm，不清除PrepareFeeding，父任务和供晶仍Working。

两条UI另观察Ignore之后的真实第二次需料true：父任务不检查ContinuousFeeding，PrepareFeeding仍true，因此500ms NoStart延时及500ms循环延时后重新进入传输。此处不能把“不再上料”按钮映射为实际第一父任务已经停止请求。

## Stop/Pause、异常返回与部分提交

前端等待期间改变机器为Stop或Pause，原内层循环没有机器状态检查；随后传感器true仍可完成运动、StopMove、Unit/Save，父任务清除PrepareFeeding，机器状态保留Stop/Pause。进入父任务前的Stop阻止控制器；进入前的Pause阻止动作，恢复Working后执行。这些检查不证明实际设备停止。

所有13个受控SDK返回码由原异步void运动包装忽略。需料、前端读值、参数、运动、关闭需料、SDK停止、坐标/子实体/行列/动作服务、偏移getter和Save抛错分别执行原catch，记录并显示错误后返回Exception，没有Stop或回滚。

前端/请求输出失败还未写Transfering；运动和停止失败保留NoMaterial/Transfering，参数错误还能留下需料true。原代码先HasMaterial后构造，故构造失败留下HasMaterial且Unit=null；构造成功后Save失败留下已有Unit。真实第一父任务忽略Exception，随后HasMaterial分支返回NoStart，继续活跃而不重新创建，PrepareFeeding仍true。此部分状态可能阻止重新接料，不能把状态HasMaterial视为实体已成功生成。

catch中的日志或错误对话框再抛错，实际父任务外层catch显示错误后正常结束，机器和真实供晶仍Working；外层对话框也抛错则实际Task Faulted，异常被检查观察。正常Task结束与成功物料提交分开记录。

前端读值观察门在旧程式NoMaterial检查之后持有。替换全局程式并令新段已经HasMaterial，原getter随后仍对新段写Transfering、构造/赋Unit并Save；旧段仍NoMaterial/Ready、无Unit。该受控域/程式替换证明读取和写入的时间边界，不证明实际生命周期会发生这种替换。

## 来源、SDK边界和接续

前端使用原名称“入料区入料检测（左）”，调用GetInputValue()，不使用CheckStateForNums。沿用[Sensor静态契约](transport-auto-unloader-sdk-evidence.json)的GetInputValue及编织执行体，两方法返回bool、无参数；[Electric输出契约](transport-loading-output-sdk-evidence.json)两方法返回void、必需bool value。均为仓库DLL元数据/IL检查，未执行SDK，未证明部署版本或设备状态。

专项：`node scripts/test-transport-auto-loader-integration.cjs`；审计：`node scripts/build-transport-auto-loader-integration-audit.cjs --check`。审计绑定全部来源、片段偏移/行号/哈希、信号初始化和报告；确认原方法使用真实Stopwatch阈值、manual参数未使用、没有Task.Run/WaitAll或Refresh、HasMaterial在构造和Save之前且没有Ready重置。统一回归与四宽度阅读器由收尾回执登记。

首轮夹具修正OnlineWithAutoLoader没有启动false输出的断言，20项通过；232项扩展通过后，Ignore再请求的观察窗口原设6秒，恰好覆盖5秒超时加两次500ms延时，扩展到8秒。未修改生产代码或加速原等待；失败与通过日志保留在`.archify-work/auto-loader-integration-*.log`，失败诊断改为锁内最后160条追踪。清理释放观察门、恢复注入故障并等待原任务，不计作生产恢复/停止证明。

下一项最后一条原料仓→点胶传输、推杆/入料口/仓库参数、第三父任务及真实10秒子任务，见[接续源码](transport-loader-bin-next-evidence.json)。随后继续载具检查/MapMaterial、实际Unit子实体/TuService/动作/产品/程式/池/域/SDK生命周期和原构建/部署配置/DLL/原生UI/设备验收。
