# 入料仓传入点胶：真实推杆子任务、异常与完整料仓链验证

原 `TransferLoadBinToDispense`、推杆控制器/模组、入料检测、硬件/参数 getter 已接完整生产器、两条 UI、准备链、真实供晶 Task、原 Stop 和既有下游控制器。288项受控检查覆盖173个完整方法、103个属性、10个枚举、16个字段及23条原信号初始化契约，共302段原代码；132个文件有显式依赖绑定，另29个源码文件按片段单独绑定，合计161个唯一文件。本专题203段链路快照。九条输送方法均已在这一受控组合中编译，料仓分支执行五阶段连续链。

原 Task.Run、Task.Wait、Stopwatch、10000ms条件、忙循环和所有 Thread.Sleep 均未改写。SDK、硬件与参数仓库、对话框/日志/Save、域/程式生命周期及坐标/子实体/TuService/行列/动作服务保留明确替身。原整个项目构建、部署配置/DLL、原生UI和设备尚未验收；启动载具检查/MapMaterial/计时日志仍待原实现集成，29源码组保持partial。

## 实际第三任务与五阶段连续链

六种配置分别经过两条UI，只有LoaderBin创建实际第三父任务。直接调用原传输方法不依赖该父任务分配；isManual只出现在签名，两个参数值分别验证。点胶HasMaterial提前等待原500ms然后NoStart，没有推杆、入料采样或子任务动作。

成功先升挡料、解夹，再缩回推杆到2、异步推出到参数PushPos=67，默认速度-1；原AbsoluteMove默认不检查到位、accuracy=0。入料用原“点胶区入料检测1”和CheckStateForNums(true,1,0)，两次采样分别接受上料和确认转入后入口已清空。点胶同步皮带按明确参数替身记录距离19、速度30。

实际第三父任务等ManualReset推料许可；Success发布点胶1完成事件，清PrepareFeeding，再ReSet推料许可、Set允许料仓移动。None不发布完成、不清PrepareFeeding，仍复位许可并允许移动。NoStart在复位前continue；选择“不再上料”清ContinuousFeeding但保留许可Set。恢复ContinuousFeeding=true后，原父任务不需要新Set便再次推料并成功。Abort及Exception在复位前Stop/return，同样保留原推料许可。这里原Stop只复位供晶需料，没有重置全部输送信号。

两条UI执行料仓→点胶1、点胶1→2、点胶→Bond、Bond→待出料、待出料→下料仓的五阶段连续链。载具构造一次、坐标创建四次、原Refresh三次、Save四次；最终移出轨道，原预点胶标志保留，偏移标志经Refresh清除，受控坐标X=10。坐标与服务结果限于替身，不证明真实坐标SDK。

## 原返回值覆盖、离线和操作员选择

原代码把MovePushRodHome结果立即用PushTabletToDispenseNoWait结果覆盖。全部13个受控SDK回原位返回码验证：非Success被原helper记日志并转Exception，但随后成功推出仍提交；子任务也忽略回原位返回值。父/子回原位SDK抛错由原helper转Exception，成功路径仍可结束。异步推出helper则保留全部13个SDK返回码，仅抛错才记日志并转Exception。

Y/Z/推杆八种缺失组合，在NormalWork、DryCycle和OffLineWork分别经过原IsReady。未就绪返回Exception，位置false；就绪离线移动None、位置true，没有SDK运动。Home控制器把离线None当失败并转Exception，推出None触发原报警。缺失硬件与错误类型分别区分正常空值检查和仓库强转抛错；缺失程式/参数在原推出catch阻止SDK调用。ResetError/ServoOn原helper没有catch，SDK或空轴故障直接上抛。

推出失败的Retry清错、50ms、上使能、50ms并重新缩回/推出；Ignore继续入料检测；Yes返回None；Abort返回Abort；No清ContinuousFeeding并NoStart。位置已到但入口无料的同一报警，Ignore仅退出switch，仍留在入料while循环；Retry重新进入推出阶段。直接调用的Abort不自带机器Stop，由实际父任务处理。

## 忙循环、10秒计时及未等待的子任务

接受入口物料之前的while(true)没有延时、超时或Stop/Pause判断。观察门持有第二次SDK采样，改变机器Stop或Pause，父线程仍未结束；随后入口true，原传输仍执行提交和父事件。许可Wait之前的Stop则返回false、没有传输动作。原控制器位置异常转false，可能延长忙循环；受控验证一次异常false及下一次恢复true，不宣称穷尽无限循环。

入口接受后创建真实子Task：位置true便缩回；否则原Stopwatch超过10000ms仅break，不报错。两条UI分别持有子任务第一次位置SDK调用10.2秒，再返回false，原计时器真实超时；子任务正常完成而没有缩回动作，父线程仍发布成功。此用例证明长SDK调用后原阈值生效，没有替换时钟；没有把它描述为持续空转采样十秒的设备测试。

正常分支在等待子任务之前构造Unit(System1)、Save、Refresh、HasMaterial、Ready及点胶1标志已提交。新载具先Save后Refresh；已存在载具不重新构造或Save，仍Refresh。延迟子任务期间观察到HasMaterial和载具，但实际父线程尚未发布完成。

转入后入口仍有料写NoMaterial/Alarm。Ignore从switch退出后直接Success，无载具提交、不等待子任务；实际第三父任务仍发布完成并允许料仓移动。Abort/No也可留下正在运行的真实子任务。Retry重新缩回/推出并创建第二子Task，未先等待第一子任务。受控检查记录真实Task对象，清理时释放所有观察门、恢复硬件响应、停止并等待父任务，最后等待每个子任务并观察故障，清理不算生产停止或恢复证明。

## 部分提交与嵌套异常

SDK推出抛错由原helper转Exception，再经过报警默认Abort，实际第三父任务Stop；原Home抛错被覆盖，仍成功。同步点胶运动、入口SDK、载具构造、Save、Refresh抛错进入原传输catch，日志/错误对话框后Exception，父任务Stop且正常结束。构造失败无载具；Save/Refresh失败保留已赋载具，没有回滚或本次完成信号。

子位置SDK抛错后catch日志也抛错，真实子Task Faulted。正常分支已经提交HasMaterial/Ready/点胶1标志；Task.Wait的AggregateException进入原传输catch，实际父任务Stop但不发布完成。子回原位SDK抛错而日志正常则helper返回Exception被忽略，子任务正常完成，父任务成功。

传输catch日志或错误对话框再次抛错时，实际父任务外层catch显示“入料仓传入点胶1线程异常”并正常结束，机器与真实供晶仍Working；外层对话框也抛错则父Task Faulted，异常被观察。这与原Exception返回导致Stop分开记录。

## 来源、SDK契约与接续

推杆SDK静态证据见[9方法/2仓库DLL契约](transport-loader-bin-sdk-evidence.json)：异步AbsoluteMove的double position与可选vel=-1、返回ExcuteResult；无参bool位置查询；无参void ResetError/ServoOn及编织执行体。仓库Axis→HardwareBase→Drive.BaseOrderDriveEntity继承链经元数据核对，未执行SDK，没有部署版本或设备响应证明。输入沿用既有Sensor静态契约。

真实子Task观察通过当前受控.NET运行时Task私有t_currentTask字段取得对象并核对Task.CurrentId；这是测试运行时适配边界。为避免原忙循环造成追踪记录无限增长，每个Task/硬件名只记录首次查找，每个位置路径只记录首次事件，另外保存完整查询计数。业务源码不含这些观察代码。控制器外层字段/域/程序由组合适配器提供；只将实际提取的成员计入来源审计。

专项：`node scripts/test-transport-loader-bin-integration.cjs`；审计：`node scripts/build-transport-loader-bin-integration-audit.cjs --check`。审计绑定全部来源、片段偏移/行号/哈希、信号初始化及报告，确认原子Task与10秒阈值、manual未使用、Save/Refresh/提交/Wait先后及Home结果覆盖。统一回归和四宽度阅读器由收尾回执登记。

初轮20项通过，扩展219项通过后补齐到288项。夹具先修正Signal枚举名、NoStart/Abort提前返回保留Manual许可的断言及四参卡料对话框路由；原代码未修改。失败与通过日志保留在`.archify-work/loader-bin-integration-*.log`，不把失败运行记为通过。

下一项启动载具检查、MapMaterial、Bond/点胶MapBelt/SearchBelt及Provider计时日志，见[22段接续证据](transport-carrier-map-next-evidence.json)。随后继续实际Unit子实体/TuService/动作/产品/程式/池/域/SDK生命周期及原构建、部署配置/DLL、原生UI和设备验收。
