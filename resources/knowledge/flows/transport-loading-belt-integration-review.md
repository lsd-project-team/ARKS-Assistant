# 入料皮带传入点胶1：原控制器与单元生命周期验证

原 `TransferLoadBeltToDispense`、入料和点胶轴/物料 getter、入料参数仓库 getter、两层需料输出，以及 Unit 三种构造、Init、Refresh、坐标/基板初始化、偏移和视觉/测高清除方法，现接入完整生产器、两条 UI 入口、准备链、真实供晶 Task、原 Stop 与下游控制器。252 项受控检查通过：156 个完整方法、94 个属性、10 个枚举、15 个字段、23 条原信号初始化契约；共275段原代码、118个来源文件，本专题176段快照。

原方法体、真实 Signal、Task.Run/WaitAll 和原延时保持不变。坐标 SDK、BaseInformation 类型、基板/基岛/焊点实体、TuService、行列服务、动作注入、配置/仓库/全局程式/域生命周期、I/O、日志/对话框与 Save 是明确替身。BaseMatter.Config 以类型适配 getter 提供受控配置；TransportUnitConfig 类型用别名适配，源码表达式未改。原命名空间 Unit 由类型适配类委托原 string 构造，不证明整个原类型继承体系。真实构建、部署配置/DLL、原生 UI、设备与其他两条入料仍待完成，29 个源码组保持 partial。

## 实际入料父任务和六阶段链

两条 UI 覆盖已有/新建载具与全部六种装卸配置。None 和 LoaderBin 不分配第二个入料皮带任务，其余四种配置分配；直接手动方法不依赖任务分配。Online 单独检查入料段 NoMaterial，点胶段 HasMaterial 则所有模式提前返回 NoStart。真实第二父线程无需入料许可事件，Success 发布 TransferToDispense1FinishedSignal 后清除 PrepareFeeding。这两步独立执行，观察夹具在事件后另等标志，避免把事件发布误作后续写入已经完成。

连续链由实际入料、点胶1→2、点胶→Bond、Bond→待出料、待出料→出料、出料→收板机父任务完成。已有载具只构造一次，四次原 Refresh、四次 Save，点胶异步两次、同步一次。相同 Unit 经过各段；Divide 的 X 从10加到23，下游原 Refresh 调用坐标服务替身重建为10，同时清除两个系统偏移标志，保留 IsNeedPreDispense。此结果限定于所列坐标服务/SDK替身，替代上一专题在 Refresh 替身下的坐标保留假设，不证明实际坐标 SDK 的最终数值。

## 两种卡料忽略、参数和物料分支

参数不存在时 Transfering 已写：Retry 重新读取参数再执行，Abort 保留 Transfering 返回 Abort；Ignore 进入运动包装后再次读取空参数，抛错并由原控制器返回 Exception。错误仓库对象触发原显式 cast；仓库返回 null 则走报警。参数名称、轴对象可动态替换，原 getter 读取当前仓库对象；负距离和超出一倍的倍率原样传递。null 名称的 ArgumentNullException 是本轮字典仓库替身的契约，不外推实际仓库。

入料 A 未感应：手动返回 None，不报警；非手动 Retry/Cancel/Abort 分别重试、关闭 ContinuousFeeding并返回 NoStart、返回 Abort。一般返回并不自动停止皮带或恢复 Transfering。测试用 SDK Moving 队列结束搜索，不用伪造原控制器结果。

首次点胶 C 检测不到物料，原方法设置两段 Alarm：Retry 重试，Abort 返回 Abort，Ignore 返回 Success，但不调用 StopMove、不转移 Unit、不设置目标 HasMaterial/第一段标志。两条 UI 的真实父任务仍发布完成并清除 PrepareFeeding，原载具留在入料段；不能把父任务 Success 当作物料已提交。

第二次 C 仍有物料的卡料检查：Ignore 继续 Stop/Clamp(true)/Unit assignment/Refresh 和状态提交。Retry/Abort 仍分开验证。既有载具成功分支没有 Save；新建载具在入料感应后、点胶运动之前 Save一次，构造或保存异常的位置因而与最终物料提交分开。

## 真实父任务、Stop 与异常部分状态

原控制器 catch 日志、显示错误后返回 Exception，没有回滚或 Stop；实际第二父任务 switch 忽略 Exception，继续循环，机器和真实供晶保持 Working。初始目标无料的本次 Success 才触发完成事件；原父任务另外有已有物料启动发布分支，不能从本轮本次传输检查推导其不存在。系统1未配置时，真实父任务在 NoStart 等非成功返回后也可发布到 Bond 的许可。

13种异步 SDK 返回码均被原 void 包装忽略。气缸子任务、轴、A/C输入、SDK停止、构造服务、动作注入、保存、Refresh 抛错均经原 catch执行。Refresh 前目标 Unit 已赋值，故坐标/子实体刷新/信息缺失或 cast 失败可让两段同时引用同一对象，目标仍 NoMaterial，第一段标志未设置。原代码没有事务或回滚。

Save 后再次读取 Unit 为null，会调用原 Stop再抛错：新建对象/Save已有尝试，点胶运动尚未开始。原 Stop 的 SMEMA getter/output 类型错误也会抛错，机器状态此前已写 Stop；清理时恢复夹具输出对象，不能计作生产恢复或设备停止证明。

入料物料采样后注入 Stop/Pause，原方法无内部状态检查，仍可完成物料提交，真实父线程发布完成；原状态保留 Stop/Pause。控制器 catch 内日志再抛错时异常进入实际父任务外层 catch，对话框正常返回则父 Task 正常结束；不将正常结束误作成功。

## 原 Unit 生命周期和配置副作用

原无参构造为空：BaseInfo/Name 未初始化，Substrates 只有属性的空列表默认值。原 string 构造创建信息、Init、时间戳名；系统构造再施加偏移，System1 以外的枚举值进入 System2 分支。Init 依次取异形配置、创建坐标、初始化基板、ModifyMatter、系统2/1动作注入，服务抛错直接传播，后续步骤跳过。

普通单基板配置会被原 Init 改写 Count/RowCount/ColumnCount=1并重建 ElementCoordinates。多基板的 Matrix/Configurable 与手工间距开关分别验证：原双重循环构造 X/Y格点，保留首点 Z、Degree=0；Matrix 的行列映射由明确受控服务返回7/9，未声称行列服务实现被验证。异形路径使用 OppositeSex 坐标和 DownConfigs，绕过普通阵列改写，但仍执行服务和动作注入。

SetSystem1OffSet/SetSystem2OffSet 各自凭标志只加一次；Refresh重建坐标、逐个刷新基板、ClearVision、ClearMeasureHeight后才清除偏移标志，不清除 IsNeedPreDispense。GetAllBaseMatter不包含Unit本身，按基板/基岛/焊点顺序返回；清除方法另先清除自身信息。缺失末端BaseInfo时，前面的写入保留。空序列化对象 Refresh 可先创建坐标，然后在信息清除失败。

## SDK静态契约与验证

[Electric输出静态契约](transport-loading-output-sdk-evidence.json)从一个仓库DLL读取两个方法/IL，验证SetOutputValue和编织执行体返回void，只有一个必需bool value参数，无可选值。不运行SDK或证明部署版本。两层原包装传递需料bool；原启动初始化false后，直接true/false序列被检查。

专项：`node scripts/test-transport-loading-belt-integration.cjs`；审计：`node scripts/build-transport-loading-belt-integration-audit.cjs --check`。审计绑定所有来源、原片段偏移/行号/哈希、信号初始化、报告和数量；原入料控制器包含Task.Run/WaitAll，字符串构造和刷新顺序亦检查。统一回归与四宽度阅读器结果由收尾回执登记。

基线24项通过，扩展先修正夹具中的原枚举成员名、启动SMEMA false基线、GetAllBaseMatter不含自身的断言，以及真实完成信号先于PrepareFeeding写入的观察竞争；没有修改生产源码。230项通过后补查真实忽略发布、非成功Bond许可、晚期null/cast、Stop输出和动态仓库。失败日志与通过日志保留在`.archify-work/loading-belt-integration-*.log`。

下一项原自动送板机→入料段、前端物料 getter、真实5秒超时和第一父任务，见[接续源码](transport-auto-loader-next-evidence.json)。随后原料仓→点胶、载具检查/MapMaterial、实际产品/程式/池/域/服务/SDK生命周期，以及原构建、配置/DLL和原生UI/设备验收继续推进。
