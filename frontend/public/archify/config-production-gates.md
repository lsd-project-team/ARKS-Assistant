# 配置提交 → 配方重载 → 真实生产启动

日期：2026-09-28。本专题衔接已完成的页面 Confirm 复核与生产主链。范围是 trunk 中指定方法的静态执行路径；没有操作设备、修改生产代码或声称第三方 Save 已成功写盘。

## 工作流摘要

1. 编程页 Confirm 修改配置对象并按页面调用仓库/程式 Save；空实现、静默返回、异常与真实保存不是同一结果，见 [20类页面提交](programming-confirm-review.md)。
2. 选择/新建配方触发 ReLoadRecipe 的路径先置 PrInitSuccess=false、禁用页面、清理停靠窗口，再按 Product→Transport→Bond→System1→Wafer→Process 顺序调用 InitProgramNodes。这里不能把重置路径/实例当作已证明的反序列化成功；外部 Singleton/Save 仍是实现边界。
3. ReLoadRecipe 离线分支直接置 PrInitSuccess=true；在线重建视觉方案，按当前配方名称查询 PR 并初始化存在的模板。缺失 PR 只记日志，循环后仍可置 true。因此 true 不等于所有引用模板存在。InitProgramNodes 位于 try 之前，其异常不经过该方法的 catch/finally；try 内异常提示并重新抛出，finally 恢复页面。方法末尾 return 后的重启进程语句不可达，不属于实际工作步骤。
4. 实际生产入口 Machine.Start 先 PrepareMachineReadyToStart；准备失败直接返回。准备包含机台状态、初始化、安全门、安全位置及环境检查。环境检查顺序：Wafer→System2→System1→TransportUnit→BondPosition→Process，任一返回 false 即停止后续检查。
5. 准备通过后设置 Working，按补偿模式、硬件配置启动输送/供晶/S1/S2等任务。参见现有自动化主图和启动源码；这不是编程页示教 Start。

## 配置输入与启动消费矩阵

|顺序|消费方法|编辑/配置输入|结果与重要分支|
|---|---|---|---|
|前置|MachineInitSuccess|轴复位开关与状态、PrInitSuccess、磁盘空间、加热配置|必需复位未完成、PR标志 false、空间不足、需预热未完成均阻止启动；不是全部配置正确性证明|
|1|WaferSystemDomain.CheckIsReady|料盒/几何、顶针、芯片、吸嘴、翻转、搜索/相机、力控/蘸胶参数|在线且未绕过辅助检查时检查相关配置、示教和兼容性；料盒检查还受屏蔽顶针开关影响；异常提示并返回 false|
|2|System2Domain.CheckIsReady|BondProgram、动作列表、ULM/焊头/吸嘴架、力控与补偿、工具检测、预点胶|先开焊头真空；自检关闭直接 true。开启时逐项失败返回 false；工具逻辑/物理不一致可能询问并修改记忆；有料可选择抛料|
|3|System1Domain.CheckIsReady|点胶器、预点胶模式/板/胶型名称、胶材|S1未配置直接 true；预点胶开启才核对板和胶型；其他检查失败返回 false|
|4|ProductConfiguration.IsTransportUnitReady|TransportUnitConfig.IsAssistantSucceed|仅该辅助完成标志门控，不证明载具每个字段有效|
|5|BondPositionConfig.IsBpAssistanceFinish|SingleBpPositionConfigList 各项辅助状态|任一未完成返回 false；空列表循环不执行并返回 true|
|6|ProcessDomain.CheckIsReady|S2SystemProcess.ProcessSteps、翻转硬件开关、普通/异形载具、焊点列表|翻转启用限制有效芯片工步数；随后遍历所有S2工步检查名称/序号/焊点/功能选择；不是此方法核验S1所有工步|

## 不能忽略的副作用

供晶检查在配置拒绝前已设置任务模式、移焊头Z到安全位置、复位推片气缸并关闭顶针台真空；后续可能退料、保存CurrentTablet、重建料盘状态和移动晶圆台。固晶检查先开真空，也可能修改吸嘴记忆或抛料。因此这些方法不是纯读取校验；本次只在隔离替身中测试不涉及硬件的制程方法，不能直接运行生产域来“验证配置”。

## 制程检查的原方法验证

运行 `node scripts/test-process-start-gate.cjs`，14项隔离用例通过，见 [测试报告](process-start-gate-test.json)。测试抽取 ProcessDomain.CheckIsReady 原文；仅把插值提示文字改为常量以适配C#5。配置、集合、消息框使用替身，并明确提供有效工步作为测试初始数据；不是复刻真实工步默认构造或全界面行为。

确认的边界：空S2列表返回true；Index只拒绝0，不拒绝负数；异形载具的焊点存在性代码被注释；禁用工步仍进入后面的全量字段检查；功能数按是否等于字符串“Null”计算，所以真正null也计作一种功能。翻转硬件仅在开头计数时筛选IsEnable。以上是该方法的接受/拒绝行为，不等于后续动作一定成功，也不能由此声称现场一定会产生这些输入。

## 选择、准备与失败处理补充

选择配方确认后先保存RecipeID；仅旧配方不存在或ID改变才调用ReLoadRecipe。同ID选择并不必然重新加载。生产按钮不会在所读方法中自动调用ReLoadRecipe；启用提示开关时先询问当前配方，取消即返回。Machine.Start异常被按钮catch捕获后调用Stop并提示，finally恢复界面；Machine.Start的普通准备失败是void返回，不经过该异常提示。

PrepareMachineReadyToStart开头先清理过期文件、复位信号，再无条件检查AllAxisReset；后面的MachineInitSuccess虽然有复位开关，但不能覆盖前面的无条件门控。安全移动发生在CheckOperatingEnvironment之前。下层动作失败、异常传播及副作用回滚不由本专题认定已完整验证。

## 已完成与剩余工作

已完成14个上层方法，并补入14段下层检查、属性绑定及集合来源，共28段限定源码；另完成制程14项隔离测试和两层门控9项对照测试。未完成：外部Singleton、Save、JSON加载真实实现与故障语义；配方切换后所有缓存对象的身份一致性；所有下层SelfCheck/IsReady与SDK动作的完整递归调用；实际硬件联调。

优先下一步：继续追踪IsAssistantSucceed等状态的形成、缺失仓库条目的处理、S2预点胶IsAlarm，以及未解析的集合扩展和外部持久化实现。现有29组仍是部分复核；本专题证据不冒充全工程覆盖率。

## 源码证据索引

- [reload：trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs:137–212](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L137)
- [nodes：trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs:124–132](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L124)
- [environment：trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:89–128](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L89)
- [machine-init：trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:408–444](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L408)
- [wafer：trunk/AKRS.ZX2200/WaferSubSystem/Models/WaferSystemDomain.cs:159–412](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/WaferSystemDomain.cs#L159)
- [bond：trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs:594–771](../../trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs#L594)
- [dispense：trunk/AKRS.ZX2200/DispenseSystem/Models/System1Domain.cs:481–528](../../trunk/AKRS.ZX2200/DispenseSystem/Models/System1Domain.cs#L481)
- [process：trunk/AKRS.ZX2200/Main/Machine/Process/ProcessDomain.cs:179–252](../../trunk/AKRS.ZX2200/Main/Machine/Process/ProcessDomain.cs#L179)
- [tu：trunk/AKRS.ZX2200/TransportUnitSystem/ProductConfiguration.cs:89–99](../../trunk/AKRS.ZX2200/TransportUnitSystem/ProductConfiguration.cs#L89)
- [bp：trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/BondPositionConfig.cs:26–38](../../trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/BondPositionConfig.cs#L26)
- [main-recipe-select：trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs:804–839](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L804)
- [startgate-prepare：trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:185–256](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L185)
- [startgate-launch：trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:261–309](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L261)
- [production-button：trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs:68–110](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs#L68)

## 下层自检与配置来源（本轮补齐）

- DispenserProgram按DispenserName查DispenserRepository；IsReady只拒绝对象缺失和未示教。EpoxyMaterialProgram按名称查胶材仓库，IsReady只拒绝对象缺失；这里并未检查胶材寿命或耗尽。预点胶板IsReady直接返回设备参数AssistanceFinish。
- BondProgram.SelfCheck先检查吸嘴架，再遍历芯片：吸嘴名不可空；贴片、取片、中转台取片/放片在各自Force模式下必须严格大于最小值且严格小于最大值；相应纠偏相机位置不能等于新建空点；关真空延时不能大于对应放片延时。中转台放片延时检查受IsIPTConfigrated条件控制。
- 吸嘴架对象按名称查仓库；GetNozzlesOnToolBank跳过查不到的吸嘴。未示教拒绝条件排除TouchDown和BMC，但提示选择FindLast仅排除TouchDown，不能保证提示对象就是触发条件中的对象。槽位真实类型为数组；OnBondHead检查中的Find扩展尚未解析，未用List.Find或替身臆造其语义。
- System2Domain.ActionNodesService属性实际类型为S2ActionNodeController。不能把DispenseSystem/Services/System2ActionNodesService同名SelfCheck中的条件移植到这条生产链。实际控制器每次通过FindAll(IsEnable)取得当前S2有效步骤；SelfCheck拒绝空集合，普通载具检查焊点名和成员关系，异形载具跳过该循环。

## 两层工步门控必须一起阅读

[9项对照测试](process-gate-composition-test.json)提取真实ProcessDomain.CheckIsReady、S2ActionNodeController.SelfCheck及其ProcessSteps过滤属性。只将表达式属性展开为C#5 getter并替换提示插值文字；外部对象/UI为显式构造替身，两方法分别调用对照，不是假称执行完整Machine.Start。

|输入情况|动作控制器SelfCheck|后面的ProcessDomain.CheckIsReady|
|---|---|---|
|空S2工步 / 全部禁用|拒绝|可通过|
|有效启用工步 + 名称为空的禁用工步|通过，禁用项被过滤|拒绝，仍遍历禁用项|
|普通载具的焊点不存在|拒绝|拒绝|
|异形载具的非空焊点名不存在|跳过成员校验|成员校验被注释，可通过|
|异形载具的焊点名真正null|可通过该循环|拒绝|
|功能字段ComponentName真正null，其余为字符串Null|此处不校验该字段|计作一种功能，可通过|

特别限定：只有S2自检开启并执行到动作控制器时，空有效工步才被该上游检查拦截；自检关闭会跳过这一路径。因此不能用“ProcessDomain接受空列表”推出整机必然放行，也不能反向声称空列表总被拦截。底层ProcessSteps本身为null时，FindAll已抛空引用，控制器中的结果null检查不能保护该属性求值。未验证这些异常输入是否由正常界面产生。

## 本轮新增源码直达

- [dispenser-ready：trunk/AKRS.ZX2200/DispenseSystem/Models/Programs/DispenserProgram.cs:55–80](../../trunk/AKRS.ZX2200/DispenseSystem/Models/Programs/DispenserProgram.cs#L55)
- [material-ready：trunk/AKRS.ZX2200/DispenseSystem/Models/Programs/EpoxyMaterialProgram.cs:51–65](../../trunk/AKRS.ZX2200/DispenseSystem/Models/Programs/EpoxyMaterialProgram.cs#L51)
- [plate-ready：trunk/AKRS.ZX2200/DispenseSystem/Models/Programs/PreDispensePlateProgram.cs:200–203](../../trunk/AKRS.ZX2200/DispenseSystem/Models/Programs/PreDispensePlateProgram.cs#L200)
- [bond-program-check：trunk/AKRS.ZX2200/BondSystem/Models/Programs/BondProgram.cs:85–211](../../trunk/AKRS.ZX2200/BondSystem/Models/Programs/BondProgram.cs#L85)
- [nozzle-shelf-check：trunk/AKRS.ZX2200/BondSystem/Models/Programs/NozzleShelfProgram.cs:224–255](../../trunk/AKRS.ZX2200/BondSystem/Models/Programs/NozzleShelfProgram.cs#L224)
- [action-service-binding：trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs:108–113](../../trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs#L108)
- [action-controller-check：trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs:1359–1404](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L1359)
- [action-step-source：trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs:89–93](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L89)
- [dispenser-source：trunk/AKRS.ZX2200/DispenseSystem/Models/Programs/DispenserProgram.cs:27–36](../../trunk/AKRS.ZX2200/DispenseSystem/Models/Programs/DispenserProgram.cs#L27)
- [material-source：trunk/AKRS.ZX2200/DispenseSystem/Models/Programs/EpoxyMaterialProgram.cs:22–32](../../trunk/AKRS.ZX2200/DispenseSystem/Models/Programs/EpoxyMaterialProgram.cs#L22)
- [plate-source：trunk/AKRS.ZX2200/DispenseSystem/Models/Programs/PreDispensePlateProgram.cs:33–37](../../trunk/AKRS.ZX2200/DispenseSystem/Models/Programs/PreDispensePlateProgram.cs#L33)
- [shelf-source：trunk/AKRS.ZX2200/BondSystem/Models/Programs/NozzleShelfProgram.cs:63–68](../../trunk/AKRS.ZX2200/BondSystem/Models/Programs/NozzleShelfProgram.cs#L63)
- [shelf-nozzles：trunk/AKRS.ZX2200/BondSystem/Models/Repositories/NozzleShelf/NozzleShelf.cs:165–180](../../trunk/AKRS.ZX2200/BondSystem/Models/Repositories/NozzleShelf/NozzleShelf.cs#L165)
- [shelf-slot-type：trunk/AKRS.ZX2200/BondSystem/Models/Repositories/NozzleShelf/NozzleShelf.cs:30–43](../../trunk/AKRS.ZX2200/BondSystem/Models/Repositories/NozzleShelf/NozzleShelf.cs#L30)

## 示教状态 → S2预点胶检查 → 执行（2026-09-28增量）

本页现收录46段限定源码。新增19项隔离测试通过；它们验证状态聚合、Reset、S2 IsAlarm和板IsReady，不运行示教界面、仓库、硬件或完整Machine.Start。DoWork与IsDispense为静态源码复核，未包含在这19项执行测试中。

### 示教状态从哪里来

- AssistantState是类，State初始化为UnAble。点胶头聚合一个状态，吸嘴聚合高度、对中、几何三个状态。聚合方法只拒绝null和UnAble，因此ForBidden也通过；不能改写成“全部必须Able”。
- 高度、几何完成按钮先调用DoneAction，再设对应状态Able、保存仓库。对中回调设Able，但矩形吸嘴会把几何状态重置UnAble；对中完成按钮随后保存仓库。这里没有证明所有DoneAction内部都成功或持久化有事务。
- S2板保存写入坐标、行列、AssistanceFinish=true，再调用BondDevicePara.Save。
- S2点胶示教回调的实际顺序包括System1Program.Save、DispenseDevicePara.Save，再设S2点胶头状态Able、保存点胶头仓库，之后还有安全位移动和耗材提示。名称按真实源码保留，不改写成System2Program.Save。异常捕获后重新抛出，本段未见保存失败回滚。

### 启动门控不是实际执行

S2自检开启且执行到预点胶检查时，IsAlarm先看硬件是否启用；硬件关闭或模式和时机均Off时不报警。否则依次检查示教聚合结果、胶型名称是否null/空字符串、预点胶板完成标志。

名称非空不等于胶型存在：此处没有胶型仓库查找，空白字符串也可通过。点胶头或板参数缺失可能抛空引用，并非稳定返回“报警”。独立的S2DispenserProgram.IsReady仅检查点胶头对象非空，不应与这里的示教检查混为一谈。

### 实际执行顺序与结束状态

1. DoWork在try之前调用WorkStart并设Running；随后IsDispense判断是否需要运行。不运行直接返回Success，但仍经过finally。
2. IsDispense：硬件关闭不运行；手动且Timing Off不运行，其他手动运行；自动模式两项均Off不运行，否则首轮标志为真运行，或Periodic且时间差严格大于配置间隔才运行。BeforeEveryDispense枚举不能单独证明每次都会执行；首轮标志生命周期仍待追踪。
3. 按重复次数获取板上位置，位置集合为null返回Abort；然后按名称查胶型。启用打印工具时检查工具名并换工具，换工具false返回Abort。
4. 对每个位置调用InterpolationApplication；DryCycle传入不出胶参数。任一插补结果非Success返回Alarm。
5. 找到胶后检测对象才调用检测，但此DoWork没有消费检测返回值。手动模式另移动相机；成功更新LastDispenseTime并返回Success。
6. try内异常记录日志、提示并返回Exception；finally清除手动标志、设Stop、调用WorkStop。WorkStart在try外，WorkStop位于finally，回调自身抛异常不受这里catch完整保护，不能承诺所有路径都正常返回。此方法没有重试循环，上层重试不能凭此推断。

输入包括硬件开关、示教状态、预点胶模式/时机/间隔/次数、胶型与检测名称、板坐标和运行模式；输出为状态、位置动作、日志、时间戳及执行结果。运动和视觉控制器的内部完成判据仍待展开。

### 本轮验收边界

已完成：上述限定片段的源码快照与19项状态/报警隔离测试。待完成：首轮标志的全部写入点、位置生成GetEpoxy边界、插补和检测内部语义、调用者处理各返回值、全部示教委托及外部Save实现、真实设备运行验证。源码行号和哈希对应当前trunk，以下链接亦可在HTML卡片内展开原文。

- [assistant-enum：trunk/AKRS.ZX2200/Infrastructure/Models/Enums/CommonEnum.cs:74–90](../../trunk/AKRS.ZX2200/Infrastructure/Models/Enums/CommonEnum.cs#L74)
- [dispenser-assistant-state：trunk/AKRS.ZX2200/DispenseSystem/Models/Repositories/Dispenser/Dispenser.cs:104–147](../../trunk/AKRS.ZX2200/DispenseSystem/Models/Repositories/Dispenser/Dispenser.cs#L104)
- [nozzle-assistant-state：trunk/AKRS.ZX2200/BondSystem/Models/Repositories/Nozzle/Nozzle.cs:223–270](../../trunk/AKRS.ZX2200/BondSystem/Models/Repositories/Nozzle/Nozzle.cs#L223)
- [s2-predispense-alarm：trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/DispenseAction/S2PreDispenseActionNode.cs:211–260](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/DispenseAction/S2PreDispenseActionNode.cs#L211)
- [teach-height-commit：trunk/AKRS.ZX2200/BondSystem/Controls/Assistant/FrmToolHeightTeach.cs:288–296](../../trunk/AKRS.ZX2200/BondSystem/Controls/Assistant/FrmToolHeightTeach.cs#L288)
- [teach-geometry-commit：trunk/AKRS.ZX2200/BondSystem/Controls/Assistant/FrmToolGeometryTeach.cs:378–385](../../trunk/AKRS.ZX2200/BondSystem/Controls/Assistant/FrmToolGeometryTeach.cs#L378)
- [teach-s2-plate-save：trunk/AKRS.ZX2200/BondSystem/Controls/Assistant/FrmS2DispensePlateAssistant.cs.cs:256–268](../../trunk/AKRS.ZX2200/BondSystem/Controls/Assistant/FrmS2DispensePlateAssistant.cs.cs#L256)
- [assistant-state-default：trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/AssistantState.cs:14–24](../../trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/AssistantState.cs#L14)
- [teach-alignment-state：trunk/AKRS.ZX2200/BondSystem/Controls/Assistant/FrmToolAlignmentTeach.cs:213–229](../../trunk/AKRS.ZX2200/BondSystem/Controls/Assistant/FrmToolAlignmentTeach.cs#L213)
- [teach-alignment-commit：trunk/AKRS.ZX2200/BondSystem/Controls/Assistant/FrmToolAlignmentTeach.cs:347–353](../../trunk/AKRS.ZX2200/BondSystem/Controls/Assistant/FrmToolAlignmentTeach.cs#L347)
- [s2-dispenser-source：trunk/AKRS.ZX2200/BondSystem/Models/Programs/S2DispenserProgram.cs:25–34](../../trunk/AKRS.ZX2200/BondSystem/Models/Programs/S2DispenserProgram.cs#L25)
- [s2-dispenser-ready：trunk/AKRS.ZX2200/BondSystem/Models/Programs/S2DispenserProgram.cs:58–68](../../trunk/AKRS.ZX2200/BondSystem/Models/Programs/S2DispenserProgram.cs#L58)
- [s2-plate-source：trunk/AKRS.ZX2200/BondSystem/Models/Programs/S2PreDispensePlateProgram.cs:31–41](../../trunk/AKRS.ZX2200/BondSystem/Models/Programs/S2PreDispensePlateProgram.cs#L31)
- [s2-plate-ready：trunk/AKRS.ZX2200/BondSystem/Models/Programs/S2PreDispensePlateProgram.cs:191–194](../../trunk/AKRS.ZX2200/BondSystem/Models/Programs/S2PreDispensePlateProgram.cs#L191)
- [predispense-enums：trunk/AKRS.ZX2200/DispenseSystem/Models/Enums/DispenseEnum.cs:73–111](../../trunk/AKRS.ZX2200/DispenseSystem/Models/Enums/DispenseEnum.cs#L73)
- [teach-s2-dispenser-commit：trunk/AKRS.ZX2200/BondSystem/Controls/Assistant/FrmAssistantDispense.cs:368–398](../../trunk/AKRS.ZX2200/BondSystem/Controls/Assistant/FrmAssistantDispense.cs#L368)
- [s2-predispense-work：trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/DispenseAction/S2PreDispenseActionNode.cs:70–158](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/DispenseAction/S2PreDispenseActionNode.cs#L70)
- [s2-predispense-trigger：trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/DispenseAction/S2PreDispenseActionNode.cs:164–205](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/DispenseAction/S2PreDispenseActionNode.cs#L164)

## 首轮标志与点位分配（2026-09-28后续增量）

当前索引53段源码；本节补充前节待追踪的首轮标志与GetEpoxy。13项新增测试仅执行原始InitPre/GetEpoxy方法，外部坐标、配置、提示、Save为明确替身；不证明生产参数合法、真实落盘或硬件可运行。

### 首轮标志跨方法流转

1. System2RunTimeProvider.IsFirstDispense静态初始化为true；BondTask在InjectSteps返回后也设true。因此“首轮”不是仅指软件启动后的第一次。
2. Machine.Continue配置安全门且门关闭时，把S1/S2首轮标志都设true；未配置安全门分支只切Working，未在这里重置标志。门未关闭只提示。
3. S2DispenseActionNode在单步和WaitStart门控后调用预点胶DoWork；预点胶任何非Success返回统一转成Alarm，包括其Abort或Exception，不保留原返回类型。主点胶节点自身抛异常则由自身catch返回Exception。
4. 预点胶通过后再WaitStart，随后取得焊点、胶型、补偿位置和角度，必要时判断并换打印吸嘴，再执行主点胶插补。主插补非Success返回Alarm。
5. 主点胶到达尾部时，硬件启用且Timing为BeforeEveryDispense则置true，为BeforeComingFirstDispense则置false，Timing Off不改此标志。随后把预点胶节点LastDispenseTime更新为Now，再更新S2统计并返回Success；前面提前返回不执行这些尾部语句。

由此可解释BeforeEveryDispense的效果：它通过主点胶尾部留下true，影响下一次预点胶触发，并非IsDispense直接识别枚举即返回true。周期判断比较LastDispenseTime，然而正常主点胶尾部也刷新该值，所以不能把间隔描述成“距上一次预点胶”的固定周期。上述是源码路径推导，尚未运行整机或模拟完整调度。

### 位置是如何预先分配的

- InitPre按Rows×Columns建二维数组，XY从起止点等分，Z始终取起点；遍历取点时按Index/Rows定位列，先走完同一列各行，再换下一列。初始化将Index置0并调用System1Program.Save，S2代码中的名称按原文保留。
- 数组为空或长度0时先初始化；Index恰好等于容量时提示清洁，确认则重建，停止返回null。行列数变化另有清洁确认分支；仅起止坐标改变、行列不变时，本方法不会自动重建已有数组。示教或其他显式InitPre调用可另行重建，本结论仅限定此方法。
- 取点先Index++，后访问数组，再Save；越界或Save抛异常时没有本地回滚。耗尽只检查相等，Index大于容量并不触发同一清洁分支。
- GetEpoxy(count)一次预取整个列表，然后DoWork才开始硬件动作。因此分配不是动作成功后确认；批量中途停止返回null，但前面已递增的索引保留。DoWork在该null结果上返回Abort，上层主点胶将其转Alarm。
- count≤0返回空列表，不会初始化数组。DoWork只检查null；空列表的后续结果还取决于检测/手动等分支，不能写成稳定拒绝。零行参数在测试的确认路径出现数组越界；这证明局部防护边界，不证明正常界面能提交该参数。

[点位分配13项报告](s2-predispense-allocation-test.json)覆盖网格、排序、Save调用、耗尽确认/停止、批量中断、非正次数、行列变化、坐标缓存、越界和保存异常。输入显式构造，Save替身仅记录调用或抛错；不冒充外部持久化实现。

剩余重点：插补/检测内部返回语义、上层Alarm如何重试/停止以及是否重新消耗位置、所有示教委托、外部Save和设备运行验收。

- [s2-plate-init：trunk/AKRS.ZX2200/BondSystem/Models/Programs/S2PreDispensePlateProgram.cs:53–90](../../trunk/AKRS.ZX2200/BondSystem/Models/Programs/S2PreDispensePlateProgram.cs#L53)
- [s2-plate-next：trunk/AKRS.ZX2200/BondSystem/Models/Programs/S2PreDispensePlateProgram.cs:96–159](../../trunk/AKRS.ZX2200/BondSystem/Models/Programs/S2PreDispensePlateProgram.cs#L96)
- [s2-plate-batch：trunk/AKRS.ZX2200/BondSystem/Models/Programs/S2PreDispensePlateProgram.cs:167–184](../../trunk/AKRS.ZX2200/BondSystem/Models/Programs/S2PreDispensePlateProgram.cs#L167)
- [s2-first-default：trunk/AKRS.ZX2200/BondSystem/Models/Parameter/System2RunTimeProvider.cs:58–62](../../trunk/AKRS.ZX2200/BondSystem/Models/Parameter/System2RunTimeProvider.cs#L58)
- [s2-first-injection：trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs:192–196](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L192)
- [s2-first-continue：trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:323–342](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L323)
- [s2-dispense-caller：trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/DispenseAction/S2DispenseActionNode.cs:49–188](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/DispenseAction/S2DispenseActionNode.cs#L49)

## 插补、检测与报警重试（2026-09-28后续增量）

当前索引62段源码。本节为静态复核，未新增硬件或完整调度执行测试；此前13项点位测试仍仅覆盖InitPre/GetEpoxy。

### 绘图前的工作流摘要

BondTask取到动作后先检查IsDoWork，再执行主点胶DoWork。主点胶先执行预点胶；预点胶再次判断触发条件，预取整批板位置，然后逐点插补，可选胶后检测。预点胶任何非Success被主点胶统一转换为Alarm。BondTask的Alarm对话框提供终止、重试、忽略：重试goto同一节点的IsDoWork处，忽略后结束当前节点，终止Stop并抬安全Z后退出。

重试是否消耗新位置有条件：同一主点胶仍通过IsDoWork、预点胶仍通过IsDispense且进入GetEpoxy时，会从已有Index再次分配，不恢复上次预取的整批位置。失败发生在预点胶成功之前时，首轮标志和时间戳通常未在该成功尾部更新；但如果预点胶已成功而主点胶随后失败，时间戳可能已被预点胶更新，周期条件可能改变，不能笼统说每次重试都必定再次预点胶。外部状态变化也可能令资格判断失败。

两种Retry不同：Alarm框选择Retry是局部goto；动作直接返回ExcuteResult.Retry则continue外层循环，会再次调用GetNextActionNode。这一段不能单独证明后者重取哪一个节点。

### 插补控制器的实际工作步骤

InterpolationApplication先做G0到机器坐标转换，按打印工具/点胶头选偏移，调用EpoxyPretreatment，再应用预点胶或普通Z偏移。对每段图形：打印策略先蘸胶；首段或打印工具分支启动压力任务并移动，随后task.Wait；其他段移动Z/XY；再处理提前开胶、到位延时、单点或GuGao插补、两段断尾。全部完成后抬到准备高度并返回Success；异常提示后返回Fail。

需保留的源码边界：部分单步判断实际调用System1Domain；提前开胶的while循环只比较轴位置并Sleep，本段没有显式停止/超时；ETEL插补分支直接抛“没有开发”。异常路径没有finally统一关胶，SDK与设备层是否另有保护未验证。

上层DryCycle仅传isDrip=false；单点主出胶使用该值，但提前开胶、滞后开胶及GuGao分支的OpenDispensingElectric不以该参数为条件。不能把上层注释“空跑不出胶”当作所有下层路径的保证；此处只陈述源代码控制流，未执行设备试验。

### 检测结果如何影响预点胶

CheckEpoxyApplication先减焊头到相机偏移，调用BondCameraVisionDefect，然后将算法结果、null焊点和硬件交给PostBondEpoxyCheck。后者检查识别数量、面积比与XY偏差。圆形分支虽然计算并显示半径，阈值比较仍使用面积比；Y偏移源码含双减号，未按注释重写公式。

异常/不合格进入PostBondCheckHand：查PR并调用视觉报警委托，OK→Success、Ignore→Fail、Abort→Abort、Retry→Retry，PR缺失或未知选择抛异常。但是预点胶DoWork调用检测后不判断返回值，所以这些正常返回的Fail/Abort/Retry不会在此调用点变成对应动作返回；若检测方法抛异常，则被预点胶catch转Exception，再被主点胶转换Alarm。视觉报警委托是否另有全局状态副作用仍待展开，不推断其只返回值。

检测通过且启用导出时尝试写胶量检测Excel。预点胶传入的bondPosition为null，而导出代码读取其TuName等字段；如果执行到这些字段会抛错，由导出局部catch记录并提示，之后方法仍到达Success。文件创建、第三方Excel库和提示自身的行为未在真实环境验收。

本轮完成限定的插补/检测外层与Alarm局部重试；仍待展开EpoxyPretreatment、GuGao驱动、相机识别内部、视觉报警委托副作用、GetNextActionNode直接Retry语义及外部持久化。

- [s2-interpolation：trunk/AKRS.ZX2200/BondSystem/Controllers/S2DispenseController.cs:226–620](../../trunk/AKRS.ZX2200/BondSystem/Controllers/S2DispenseController.cs#L226)
- [s2-drip-io：trunk/AKRS.ZX2200/BondSystem/Controllers/S2DispenseController.cs:625–652](../../trunk/AKRS.ZX2200/BondSystem/Controllers/S2DispenseController.cs#L625)
- [s2-pressure：trunk/AKRS.ZX2200/BondSystem/Controllers/S2DispenseController.cs:673–691](../../trunk/AKRS.ZX2200/BondSystem/Controllers/S2DispenseController.cs#L673)
- [s2-print-epoxy：trunk/AKRS.ZX2200/BondSystem/Controllers/S2DispenseController.cs:809–860](../../trunk/AKRS.ZX2200/BondSystem/Controllers/S2DispenseController.cs#L809)
- [s2-pre-inspection：trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/DispenseAction/S2PreDispenseActionNode.cs:294–304](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/DispenseAction/S2PreDispenseActionNode.cs#L294)
- [epoxy-check：trunk/AKRS.ZX2200/BondSystem/Models/Repositories/PostBondInspection/PostBondInspection.cs:361–539](../../trunk/AKRS.ZX2200/BondSystem/Models/Repositories/PostBondInspection/PostBondInspection.cs#L361)
- [epoxy-check-dialog：trunk/AKRS.ZX2200/BondSystem/Models/Repositories/PostBondInspection/PostBondInspection.cs:594–627](../../trunk/AKRS.ZX2200/BondSystem/Models/Repositories/PostBondInspection/PostBondInspection.cs#L594)
- [bond-alarm-dispatch：trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs:214–326](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L214)
- [s2-dispense-eligible：trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/DispenseAction/S2DispenseActionNode.cs:194–217](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/DispenseAction/S2DispenseActionNode.cs#L194)

[打开S2预点胶与报警重试Archify时序图](s2-predispense-retry.sequence.html) · [消息与源码逐条映射](s2-predispense-retry.evidence.json)

## 节点重取、图形预处理和视觉报警副作用（2026-09-28增量）

当前索引75段源码；新增9项原方法节点选择隔离测试。测试替换动作/消息容器和InitCurrentMessage为计数替身，不执行完整BondTask、真实初始化或硬件。

### 直接Retry到底取哪个节点

BondTask收到ExcuteResult.Retry后continue外层循环，不调用FinishCurrentActionNode。GetNextActionNode重新遍历WorkMessages，选择第一个Finished=false的消息，再按名称解析动作并InitCurrentMessage。若消息列表及完成标志未被其他逻辑改变，普通未完成动作仍会被取到；不能把“GetNext”误读成总会推进一步。

例外：本次未完成消息名称与上次相同，且为UpLookCorrectionActionNode或SubstrateCameraCorrectionActionNode时，方法提示排序错误并抛异常。这与Alarm框Retry的goto不同：后者绕过GetNextActionNode，直接回到同一动作的IsDoWork。FinishCurrentActionNode仅将当前消息Finished=true。

动作名称未在仓库找到时，ChangeNameToActionNode仍调用InitCurrentMessage后返回null；外层把null当作循环结束。因此null返回不只意味着所有消息完成。ActionNodes为null时Find先抛异常，后面的显式null检查来不及保护。实际上下文初始化还包含仓库查询及焊点定位；本轮测试不证明这些外部查询成功。

### 重要补充：返回值忽略不等于没有停机副作用

前节“预点胶未判断检测返回值”仍成立，但界面按钮有独立副作用：FrmVisionAlarm的终止按钮先调用Machine.Stop，再设置DialogResult.Abort。因而不能据返回值未被使用就断言终止不生效。跳过与补胶按钮分别设置Ignore/Retry；在这个预点胶调用点，正常返回值没有驱动对应分派。

编辑PR按钮先Pause，等待/编辑、保存视觉仓库后Continue；这也可能影响首轮标志（取决于Continue安全门分支）。VisionAlarm委托在UI锁内Invoke模态窗口，之后插入报警数据库、调用ResetAlarm，再返回选择；数据库或ResetAlarm异常可能令其无法正常返回。ResetAlarm实际操作报警器RunState，并不将整机MachineState恢复Working；其null集合分支还存在索引空引用边界。没有执行真实UI或数据库来验证这些路径。

### 图形预处理与驱动结束边界

EpoxyPretreatment先调用ObjectHelper.Clone，再按所有轨迹点的XY极值中点居中，并按SizeX/SizeY缩放；两点且原策略为SingleDotOnly时将首点移至两点均值。非正速度/加减速分别置100/1000，再乘SpindleSpeedPercentage百分比。NaN坐标在旋转前归零，随后按角度旋转、平移到目标XYZ；本段未见Infinity或百分比范围校验。后续已用原Clone与原预处理方法验证受控夹具对象图的深复制；完整生产类型与实际配方仍未验收，不能据调用名或夹具测试宣称所有原对象绝不变化。

GuGao插补末尾反复调用GTN_CommandListDataEnd直到返回0，再StartCommandList并轮询execute==0；所核对循环没有显式超时、Sleep或停止检查。之后停止/解组/禁用等调用连续覆盖返回码，最后依据最后一次返回码给出bool；catch重抛通用异常。上层S2DispenseController忽略这个bool，因此false本身不能视为已走失败分支；抛异常则进入上层catch。这里只核实驱动末尾，完整命令构造、SDK行为及实际硬件停止仍未验收。

### 本轮新增证据
- [s2-next-node：trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs:1042–1075](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L1042)
- [s2-finish-node：trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs:1033–1036](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L1033)
- [s2-resolve-node：trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs:1082–1093](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L1082)
- [epoxy-pretreatment：trunk/AKRS.ZX2200/DispenseSystem/Services/DispenserMoveHelper.cs:327–446](../../trunk/AKRS.ZX2200/DispenseSystem/Services/DispenserMoveHelper.cs#L327)
- [vision-alarm-delegate：trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcmainSystem.Action.cs:273–303](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcmainSystem.Action.cs#L273)
- [vision-alarm-abort：trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/FrmVisionAlarm.cs:415–419](../../trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/FrmVisionAlarm.cs#L415)
- [vision-alarm-edit：trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/FrmVisionAlarm.cs:426–498](../../trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/FrmVisionAlarm.cs#L426)
- [vision-alarm-ignore：trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/FrmVisionAlarm.cs:505–508](../../trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/FrmVisionAlarm.cs#L505)
- [vision-alarm-retry：trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/FrmVisionAlarm.cs:565–568](../../trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/FrmVisionAlarm.cs#L565)
- [gugao-interpolation-tail：trunk/AKRS.ZX2200/Infrastructure/Utils/GuGaoDrive.cs:1494–1594](../../trunk/AKRS.ZX2200/Infrastructure/Utils/GuGaoDrive.cs#L1494)
- [vision-alarm-binding：trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcmainSystem.Action.cs:31–37](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcmainSystem.Action.cs#L31)
- [s2-message-context：trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs:930–974](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L930)
- [machine-reset-alarmer：trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.cs:166–178](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.cs#L166)

## 固高指令构造全方法复核（2026-09-28增量）

本轮完整读到GuGaoDrive.Interpolation的1098–1594行，限定为该方法静态控制流；新增11项原始指令循环隔离测试，详见[gugao-command-loop-test.json](gugao-command-loop-test.json)。SDK和指针封送均为受控替身，不执行真实驱动、整段插补或硬件。

1. **输入**：S2控制器传coreIndex=2、当前轨迹点数组及GetDispenseIndex()。驱动固定使用指令流1、组1、轴1/2。上层负责首点及Z高度动作，驱动循环只把下一点XY写入直线运动。
2. **准备**：设置/读取两轴比例，读取列表配置及关联组，再解组、禁用并重新加入轴，设置正交变换。局部commandListConfig虽然先写动态模式与容量，随后的Get覆盖它；这里没有调用SetCommandListConfig，不能把这些赋值当成已下发配置。velMax等常量附近的运动约束设置是注释，也不能据注释宣称已限制速度。
3. **规划设置**：写平滑、停止参数及前瞻；源代码顺序是前瞻调用在StopCommandList/ClearCommandListData之前。之后启用组、设规划与命令坐标系。前面的rtn反复覆盖，1414行仅检查最近GetGroupCommandPosDefine的返回，不能覆盖性证明准备调用全部成功。SDK如何处理这段队列顺序尚未验证。
4. **逐段构造**：j从0到Length-2。当前点OpenGlueFlag为真时压入LagOpen定时输出，值0；AdvanceClose非0再压入提前输出，值1。假时压入立即输出位1。随后以param[j+1]的XY为目标、param[j]的Speed/Acc/Dec为参数调用MoveLinearAbsolute。这里描述写入值，不凭源码猜现场IO极性。末点自身的IO/速度字段不会用于下一段。
5. **错误门槛**：IO和每段Move的返回都写同一个rtn，循环后才检查；受控测试已确认IO错误或前段Move错误可被后续0覆盖，最后Move非0才触发本段报警异常。空数组/单点不生成段指令而沿用进入循环前的rtn，null会抛异常。这些是方法边界行为，不代表上层必然传入无效数组。
6. **发送、等待、清理**：结束数据循环→启动列表→轮询execute→停止/解组/禁用/停止列表；没有看到本方法显式轮询超时或finally清理。尾部关IO代码被注释。正常返回后S2调用CloseDispensingElectric；驱动抛异常不会顺序执行这一句，后续停机清理保证仍需结合上层错误路径和设备验证。catch将原异常换为通用异常。

本轮11项检查包括开关顺序、当前速度/下一坐标、零提前关闭、错误覆盖、最后错误、空/单点/null以及末点标志。不测试SDK返回语义、原生指针有效期、设备动作或命令列表生命周期。

### Clone边界已进一步定位

ObjectHelper.Clone并非缺失外部实现：本地109–119行使用MemoryStream和BinaryFormatter序列化/反序列化并返回复制对象，无局部catch。前文“Clone语义未展开”是上一阶段状态，本轮已定位其机制；完整配方对象图是否都可成功序列化仍未执行验证，不把本地方法存在当作所有生产配置复制成功。

- [gugao-prepare：trunk/AKRS.ZX2200/Infrastructure/Utils/GuGaoDrive.cs:1098–1244](../../trunk/AKRS.ZX2200/Infrastructure/Utils/GuGaoDrive.cs#L1098)
- [gugao-planning：trunk/AKRS.ZX2200/Infrastructure/Utils/GuGaoDrive.cs:1246–1425](../../trunk/AKRS.ZX2200/Infrastructure/Utils/GuGaoDrive.cs#L1246)
- [gugao-command-loop：trunk/AKRS.ZX2200/Infrastructure/Utils/GuGaoDrive.cs:1427–1513](../../trunk/AKRS.ZX2200/Infrastructure/Utils/GuGaoDrive.cs#L1427)
- [object-binary-clone：trunk/AKRS.ZX2200/Infrastructure/Utils/ObjectHelper.cs:109–119](../../trunk/AKRS.ZX2200/Infrastructure/Utils/ObjectHelper.cs#L109)

## 胶后视觉识别与活动上下文（2026-09-28增量）

### 工作流摘要

预点胶检测位置减焊头到相机偏移 → BondCameraVisionDefect查PR、并行光源与运动并等待 → 检查DryCycle → 按配置次数调用VisionDefect → PREntity设置硬件/相机、抓图、FindModel → 返回算法结果列表 → PostBondEpoxyCheck进行数量/位置/面积判断 → 必要时进入视觉报警。此处继续追trunk内的AKRS.Galaxy2.PR子项目，未把子项目源码误归为不可见外部算法。ZX2200.csproj有直接ProjectReference；这不证明现场DLL与当前源码相同。

### 控制器、服务与相机层

- 控制器先Find模板并写IsDefectPR，没有先判null；缺名可能在相机运动前抛异常。VisionService也在null保护之前写属性，其后报警分支不能保护这次空引用。
- 非空位置时，SetLight在Task内执行，当前线程按isZSafe选MoveToG0Pos或坐标转换后MoveBondXY，再Task.Wait；空位置直接SetLight。DryCycle在这些步骤之后才返回null，所以不能把它解释为本入口完全不操作运动/光源。等待没有在本方法显式指定超时。
- VisionRetryTimesLimit是总尝试次数，不是初次之外再加的次数；每次先DownLookVisionDelay再取CurrentMatter并识别。非null立即返回，包括空列表；只有null进入下一次。0/负数不识别；异常向外传播。7项隔离测试仅验证这个循环，日志调用为编译兼容省略，运动/相机均未运行。
- 服务在PR实体锁内DoWork；只有Success才返回AlgResults，其余转null。本方法中的SaveVisionImage调用被注释，不代表下层完全不存图。
- PREntity.DoWork在另一把锁内设置硬件；按isSetLight设置光源、曝光、增益、Gamma，后三项返回false仅记日志。Excute抓8位灰度图；抓图null保留None。SetImage/FindModel发生在存图catch之外，异常不会被该存图catch捕获。
- 算法成功后的可选存图发生在设置Success之前；存图块异常被记录后可能留下None，服务因此返回null并触发上层再次识别。结果图再按连接状态投给缺陷/普通显示管道；没有显示接收者时会Dispose结果图。图像保存和显示消费没有本轮真实运行验收。

### 胶量算法的可见边界

EpoxyDetectAlg选择BLOB分析1或2，设置粗定位输入后运行VmProcedure，并读取对应1Blob/2Blob的X、Y、面积数组。识别和图像绘制依赖VisionMaster/Halcon调用，内部算法与现场流程文件未验证。IsOutputTotal把X/Y分别取算术平均、面积求和，不能称为面积加权质心；按X数组长度取Y/面积，源码这些位置未见长度一致性保护。成功分支生成BlobResult并共用结果位图；失败分支也可能生成带失败标志的对象，但FindModel返回false，经服务转换后上层收到null，并非该失败对象列表。异常记录后返回false。

这些输入、聚合、结果构造及失败分支已存原文；不宣称所有绘图/粗定位辅助调用都已完成语义或运行验证。

### 当前动作上下文从哪里来

TransportUnit属性实时读取输送域固晶段对象；ProcessSteps每次取S2启用工步。InitCurrentMessage先按名字Find工步，有工步才查询检测/胶型仓库，然后按消息中的Substrate/Module索引和工步焊点名匹配对象。方法开始没有统一清空旧上下文。

因此，缺工步时ProcessStep变null，但检测配置、胶型、焊点可能保留旧值；基板/基岛/焊点匹配缺失也不会在这里自动清空相应旧字段。遍历异常仅提示并吞下，而此前工步/仓库查询在try外。CurrentMatter用当前这些字段拼基板/基岛/焊点名称，故不能凭名称存在证明已匹配当前消息。这里是源码静态状态更新结论；已有9项节点选择测试仍以InitCurrentMessage计数替身运行，不能充当真实上下文测试。

### 本轮证据及剩余工作

当前专题90段。PREntity.cs为GB编码，本轮在索引中记录gb18030并按原始字节保留SHA，避免中文注释乱码；其他文件继续UTF-8。仍需核实全部视觉辅助调用、流程文件及SDK运行、真实上下文场景、复制对象图、示教和持久化。

上述EpoxyDetectAlg分支仅在所选PR.Alg实际为该类型时适用；本入口通过虚方法FindModel分派，不能在缺少实际配方时宣称每次都运行该算法。

- [s2-camera-defect：trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.Vision.cs:291–376](../../trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.Vision.cs#L291)
- [vision-defect-service：trunk/AKRS.ZX2200/Infrastructure/Service/VisionService.cs:158–204](../../trunk/AKRS.ZX2200/Infrastructure/Service/VisionService.cs#L158)
- [pr-hardware-work：trunk/AKRS.Galaxy2.PR/Models/Entities/PREntity.cs:339–433](../../trunk/AKRS.Galaxy2.PR/Models/Entities/PREntity.cs#L339)
- [pr-capture-execute：trunk/AKRS.Galaxy2.PR/Models/Entities/PREntity.cs:458–639](../../trunk/AKRS.Galaxy2.PR/Models/Entities/PREntity.cs#L458)
- [epoxy-alg-run：trunk/AKRS.Galaxy2.PR/Models/Algs/EpoxyDetectAlg.cs:63–128](../../trunk/AKRS.Galaxy2.PR/Models/Algs/EpoxyDetectAlg.cs#L63)
- [epoxy-alg-aggregate：trunk/AKRS.Galaxy2.PR/Models/Algs/EpoxyDetectAlg.cs:180–195](../../trunk/AKRS.Galaxy2.PR/Models/Algs/EpoxyDetectAlg.cs#L180)
- [epoxy-alg-results：trunk/AKRS.Galaxy2.PR/Models/Algs/EpoxyDetectAlg.cs:269–279](../../trunk/AKRS.Galaxy2.PR/Models/Algs/EpoxyDetectAlg.cs#L269)
- [epoxy-alg-failure：trunk/AKRS.Galaxy2.PR/Models/Algs/EpoxyDetectAlg.cs:394–417](../../trunk/AKRS.Galaxy2.PR/Models/Algs/EpoxyDetectAlg.cs#L394)
- [s2-context-properties：trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs:42–93](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L42)
- [s2-current-matter：trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs:1323–1353](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L1323)
- [vision-project-reference：trunk/AKRS.ZX2200/AKRS.ZX2200.csproj:4114–4118](../../trunk/AKRS.ZX2200/AKRS.ZX2200.csproj#L4114)

## 视觉辅助与默认胶量模板（2026-09-28）

本节先说明调用与配置边界，再阅读[Archify模板图](epoxy-template.workflow.html)。图来自仓库默认模板的连接声明，不代表实际配方一定运行该模板。

1. `SetLight` 按启用灯光及可选硬件绑定设置强度，再设置相机曝光、增益和Gamma；设置返回失败会抛异常，与 `DoWork` 内部只记录部分设置失败的路径不同。灯光与强度列表未做长度一致性检查。[源码101–159](config-production-gates.html#pr-set-light)
2. `SetHardware` 覆盖相机、轴和指定灯名；循环未清除旧灯光列表的多余尾项，也不重置启用状态或强度。[源码165–180](config-production-gates.html#pr-set-hardware)
3. `SetImage` 必要时获取视觉流程，向图像源赋值并生成缩略图；它捕获异常并记录日志，返回void，不能把调用返回当作图像成功加载。[源码252–286](config-production-gates.html#alg-input-image)
4. `InitVmProcedure` 在锁内优先加载当前保存目录的 `Name.prc`，只有文件不存在才选择默认 `AlgFlowTemplates` 模板；不是加载异常后自动回退。它随后获取参数、图像源和输出图像模块，异常被记录而不重新抛出。部分字段可能已更新，不能保证返回时得到全新有效流程。[源码291–319](config-production-gates.html#alg-init-procedure)
5. 保存目录按 Calibration 选择设备标定PR，否则选择所有产品PR；目录创建失败可返回null。`GetVmProcedure` 根据缓存与方案成员关系决定初始化，最后返回当前对象。[目录325–351](config-production-gates.html#alg-save-path)、[获取357–372](config-production-gates.html#alg-get-procedure)、[默认路径](config-production-gates.html#alg-template-root)
6. PR项目声明复制默认胶量模板到输出目录。[工程声明584–586](config-production-gates.html#alg-template-content)。从该模板ZIP内 `ProcFile\ProcedureInfo.xml` 原样提取结构，得到13模块、15条连接、92条数据订阅；全部保存在[结构证据](epoxy-template-structure.json)和[原始XML](epoxy-template-procedure.xml)。
7. 模板声明图像源→分支模块；一支为BLOB分析2→脚本3，另一支为初定位方式→四种匹配之一→脚本1→位置修正1→BLOB分析1→脚本2。分支模块订阅IsFirPR，初定位方式订阅FirPRType。未解析二进制脚本和分支取值规则，因此图中不标注推测的true/false条件，也不将支路末端标成整机完成。

验证：模板重新解析、原始XML及源码哈希、13模块和15连接全覆盖、图规格与HTML哈希、Archify九项检查和自动浏览器检查已接入统一验证。最终1440×900浅色及2048×1320深色截图已人工查看，未见节点文字遮挡或画布溢出。自动报告的 `visualReview: pending` 是工具原始字段，本段记录另行完成的截图审阅，不篡改自动报告。

仍未验收：生产配方实际覆盖的 `.prc`、脚本内部算法、分支条件取值、第三方SDK运行、图像/硬件行为和全工程构建。下一步继续真实上下文更新场景与复制对象图，再推进其余示教委托和外部持久化。

## S2上下文更新与胶型复制对象图（2026-09-28）

### 实际消费链

`System2Domain.ActionNodesService` 的声明类型是 `S2ActionNodeController`，[类型绑定](config-production-gates.html#s2-domain-context-binding)。点胶动作也明确通过这个类型获取当前焊点与胶型，[动作绑定](config-production-gates.html#s2-dispense-context-binding)、[消费位置与补偿](config-production-gates.html#s2-dispense-context-inputs)。仓库另有 `System2ActionNodesService` 类，但不能用其同名方法解释此主链，也不据本次搜索宣布它在全工程不可达。

主链为：节点选择 → `ChangeNameToActionNode` → `InitCurrentMessage` → 当前字段getter → 点胶动作使用焊点坐标和胶型偏移。前三者已有[节点选择证据](s2-node-selection-test.json)；本轮直接抽取 `InitCurrentMessage` 原方法执行[14项上下文隔离检查](s2-context-update-test.json)。[原方法](config-production-gates.html#s2-message-context)及[getter](config-production-gates.html#s2-context-getters)可逐行核对。

|条件|原方法可证实的结果|验证层级|
|---|---|---|
|所有名称与WorkIndex匹配|字段绑定到仓库和层级中的对象引用|原方法隔离测试|
|工步被禁用或查找无匹配|ProcessStep变null；旧检测、胶型和焊点未被统一清空|禁用场景实测；无匹配由同一Find分支静态确认|
|新消息找不到基板|旧基板、基岛、焊点可继续保留|原方法隔离测试|
|新基板找到但基岛缺失，或新基岛找到但焊点缺失|可能形成新父对象与旧子对象的混合上下文|原方法隔离测试|
|重复工步名或同一基岛内重复焊点名|前者Find取第一项；后者首次匹配后break|原方法隔离测试|
|重复基板或基岛WorkIndex|外层循环没有break，后匹配可覆盖前匹配|原方法隔离测试|
|层级遍历抛异常|显示消息后吞下异常，已赋值字段不回滚|原方法隔离测试|
|胶型仓库查询抛异常、当前消息或工步列表为空|发生在局部try之前，异常继续传播|依赖替身触发的原方法隔离测试|
|仓库返回null|字段被赋null，但不阻止后续层级更新|依赖替身触发的原方法隔离测试|

测试使用最小引用对象容器、可控仓库替身、等价启用项过滤和提示计数器；未运行真实仓库加载、完整任务调度或设备。它证明原方法的局部状态与异常边界，不证明线上配方会产生上述输入。不得把这些风险直接写成已复现的设备故障，也未擅自修改生产源码。

### 复制对象图与边界

[仓库Load/Find](config-production-gates.html#setting-repository-load-find)表明：Load调用JsonFormatHelper，返回null时回退空列表；Find按名称取首项，不筛选IsEnable或RecipeID，也不克隆。JsonFormatHelper内部读盘和异常行为仍未纳入本轮测试。[GetInstance](config-production-gates.html#epoxy-repository-singleton)复用首次构造的实例，不代表每次访问都重新读盘。

|对象层级|源码声明|本轮结论|
|---|---|---|
|EpoxyApplication|[胶型成员](config-production-gates.html#epoxy-object-members)|Serializable；包含标量、枚举、字符串及点位列表|
|DispensePatternParas|同上|List → EpoxyApplicationLocation[] → 点位对象；不是单纯复制一组坐标值|
|EpoxyApplicationLocation|[点位成员](config-production-gates.html#epoxy-location-members)|Serializable；含坐标、速度、加减速、开关胶和高度补偿等数据|
|BaseDsSetting|[基类成员](config-production-gates.html#epoxy-base-members)|Serializable；含名称、启用状态、创建时间及List<Guid>配方归属|
|PropertyChangeAop|[序列化边界](config-production-gates.html#epoxy-aop-serialization)|Serializable；PropertyChanged事件标注NonSerialized；静态初始化标志不是实例复制字段|

[EpoxyPretreatment](config-production-gates.html#epoxy-pretreatment)先调用[ObjectHelper.Clone](config-production-gates.html#object-binary-clone)，随后在返回对象上归一化、初始化速度并旋转平移。Clone使用BinaryFormatter把对象写入内存再读回，方法内没有异常捕获；这里只描述本地受控对象的现有实现，不新增反序列化外部数据的动作。

剩余验收：真实配方实例的全部运行时类型、编译后Fody织入、对象别名与订阅状态、克隆异常如何穿过完整任务外层、真实加载/保存。Serializable声明只能提供结构证据，不能代替这些运行验证。下一步继续复制与预处理的调用传播，并进入其余示教委托和外部持久化。

## 复制/预处理入口与失败传播（2026-09-28）

### 工作流摘要

预处理本身不操作硬件：接收胶型、目标XYZ和角度 → 内存序列化复制 → 按轨迹极值居中缩放 → 单点策略调整 → 速度/加减速默认值及百分比缩放 → NaN归零 → 旋转平移 → 返回副本。实际运动由调用它的控制器继续执行。数学转换、原Clone及真实点位类/胶型枚举已做[14项隔离验证](epoxy-pretreatment-test.json)；胶型根对象、坐标依赖仍为明确披露的最小替身。

### 三个直接入口与后续处理

|入口|调用后的对象使用|异常与后续分派|
|---|---|---|
|S1插补控制器|接收返回副本，继续高度补偿及点胶|方法catch提示后返回Fail；catch中未抬安全高度。[准备](config-production-gates.html#s1-interpolation-prepare)、[catch](config-production-gates.html#s1-interpolation-catch)|
|S2插补控制器|接收返回副本，继续高度补偿及点胶|catch提示后返回Fail；不是直接抛到主动作。[完整方法](config-production-gates.html#s2-interpolation)|
|图形编辑InitPatternData|先清空重建原对象点位，再调用预处理但丢弃返回副本|没有局部catch；失败会中断后续Refresh。编辑按钮外层也没有局部catch；不能把此调用当作把归一化结果写回配方。[数据转换](config-production-gates.html#epoxy-editor-transform)、[对话框](config-production-gates.html#epoxy-editor-dialog)、[Click绑定](config-production-gates.html#epoxy-editor-click-binding)|

编辑对话框OK后，还会调用EpoxyIsReasonable；失败goto重新显示编辑框。这个重试与机器任务重试不同。预处理失败并不会在本地自动进入该goto。

### 控制器的八处调用点

|调用场景|控制器非Success时的实际处理|
|---|---|
|S1自动点胶|转Alarm，不执行后面的焊点工步完成标记。[来源](config-production-gates.html#s1-dispense-result-map)|
|S1自动预点胶|逐点执行，首个非Success转Alarm。[来源](config-production-gates.html#s1-predispense-result-map)|
|S2自动点胶|转Alarm，不执行后面的焊点工步完成标记。[来源](config-production-gates.html#s2-dispense-result-map)|
|S2自动预点胶|逐点执行，首个非Success转Alarm。[来源](config-production-gates.html#s2-predispense-work)|
|普通S1试胶|直接return，不继续该分支视觉移动。[来源](config-production-gates.html#epoxy-teach-s1-return)|
|普通S2试胶|直接return，不继续该分支视觉移动。[来源](config-production-gates.html#epoxy-teach-s2-return)|
|预点胶板S1试胶|未判断返回值；正常返回Fail后仍可继续安全Z和视觉移动。[来源](config-production-gates.html#epoxy-teach-preplant)|
|预点胶板S2试胶|未判断返回值；正常返回Fail后仍可继续气缸及视觉移动。[来源](config-production-gates.html#epoxy-teach-preplant)|

试胶按钮实际绑定见[Designer源码](config-production-gates.html#epoxy-teach-click-binding)。预点胶板试胶先Confirm，不等同于纯预览；本轮未执行上述按钮或设备动作。

### 任务层差异

- S1任务：仅Retry继续取节点，其余非Success先调用MoveToSafePos，再Stop并退出；此处没有S2式的Alarm三选项。安全移动也可能抛异常，因此不据静态调用顺序保证Stop必定完成。[分派源码](config-production-gates.html#s1-task-result-dispatch)
- S2任务：Alarm显示终止/重试/忽略。重试goto同一节点的IsDoWork；忽略后会FinishCurrentActionNode，但不能等同于补写动作内部的焊点完成状态；终止调用Stop、安全Z并退出。直接Retry则continue重新取节点。[分派源码](config-production-gates.html#bond-alarm-dispatch)
- S2主动作自身的其他异常由catch转Exception，finally恢复State并触发WorkStop；这与控制器catch返回Fail→主动作Alarm的路径不同。回调若再次抛异常仍属待核对外层边界。[源码](config-production-gates.html#s2-dispense-catch-finally)

### 隔离验证结论及限制

14项检查涵盖：居中缩放/旋转/平移；受控夹具图的深复制和原点位不变；速度默认值及百分比；SingleDotOnly只改变首点而保留第二点；退化单轴和单点；空列表、null段、空首段；非有限尺寸；null根和夹具非序列化后代导致的异常传播。

已证实的局部边界：空首段会使后续正坐标极值包含初始零，得到不同于正常首段的归一化；零/负百分比会产生零/负运动参数；旋转前只清理NaN，不能保证最终坐标均有限。这些都是方法级输入场景，尚未证明真实配方能通过所有上游门控触发，更没有复现现场运动风险。

真实EpoxyApplication全类、基类、Fody织入、生产实例与克隆回调仍未纳入本次执行测试；不能从最小夹具的深复制通过推断全部配方可复制。下一步推进试胶入口的Confirm、示教委托和外部保存/加载，继续保留真实配方与完整构建验收缺口。

## 试胶前提交、胶型名称解析与持久化边界（2026-09-28）

### 工作流摘要

编程树按当前系统取得胶型程序的解析结果 → 将胶型对象放入NodeTag → 编辑页保存传入引用 → 试胶按钮先Confirm → 逐项更新该对象 → 胶型仓库Save → System1Program.Save → 再检查试胶条件并进入控制器。这里必须分别记录对象修改、保存委托和真实文件写入，不能把按钮返回当成三者全部成功。

[树数据来源](config-production-gates.html#epoxy-tree-object-source)、[选择节点](config-production-gates.html#epoxy-tree-editor-open)、[构造引用](config-production-gates.html#epoxy-editor-object-reference)、[普通试胶提交顺序](config-production-gates.html#epoxy-test-confirm-order)、[预点胶板入口](config-production-gates.html#epoxy-teach-preplant)。另有[异形编辑入口](config-production-gates.html#epoxy-alternative-editor)：先调用自己的Save，再通过S1胶型程序查对象，对话框前后切换当前系统；不是独立的胶型克隆路径。

### Confirm的状态与中断边界

[原方法](config-production-gates.html#epoxy-confirm)包含33项直接控件赋值，另处理吸嘴名称。11项[隔离测试](epoxy-confirm-test.json)核实：

|情形|已发生和未发生的步骤|
|---|---|
|正常提交|先写当前对象，再依次委托胶型仓库Save、System1Program.Save|
|胶型库Save抛异常|对象字段已经修改；第二次Save不执行；没有本地回滚|
|System1Program.Save抛异常|第一次Save调用已返回，内存修改保留；不能据替身测试保证第一份真实文件已写入|
|胶型策略EditValue为null|更早字段可已更新；策略转换失败，后续字段与两个Save尚未执行|
|整型转换溢出|更早字段保留，保存未执行；属于故障注入|
|吸嘴未选或空字符串|写入字面字符串Null；空白字符串不会被归一化|
|小数速度百分比|decimal转int截断；Confirm自身没有额外范围校验|

无论随后选择S1还是S2试胶，该Confirm方法都写明保存System1Program，没有按系统切换到BondProgram。两类试胶都是先Confirm再做后面的试胶准备检查，所以准备失败可能发生在保存委托之后。这里不扩展为“所有S2操作都会错误保存”，也不替第三方Save推断行为。

测试限制：控件、实体字段与Save目标为可控替身；原方法仅将SelectedItem空条件语法等价改写以兼容C#5。真实[速度控件范围为10–500](config-production-gates.html#epoxy-ui-speed-limits)，[断尾延迟最大5000](config-production-gates.html#epoxy-ui-delay-limit)。负百分比和decimal溢出测试只证明方法自身边界，不证明正常界面能输入这些值。属性织入与真实磁盘未运行。

### 读取名称列表并非无副作用

[EpoxyApplicationProgram](config-production-gates.html#epoxy-program-name-resolver)保存名称列表，EpoxyApplications是带JsonIgnore的计算属性，每次调用Find解析对象。Find直接使用仓库返回的对象引用；缺失名称会在正向for循环中RemoveAt(i)，删除后仍i++。原方法7项[隔离测试](epoxy-name-resolution-test.json)确认：

- 名称为“缺失、A、B”时，本次返回可能只有B；名称列表变成“A、B”，再次读取才返回A和B。
- 连续两个缺失名称可能只删掉第一个，第二个因索引移动被跳过。
- 重复名称返回同一对象的重复引用；null名称列表返回空对象列表。
- 如果先删除缺失项，随后仓库查询抛异常，之前删除不会在本方法回滚。

因此刷新编程树本身可能改变内存里的名称列表。这个方法不调用Save，不能说“刷新已把删除写入磁盘”；随后何时保存仍须沿调用链证明。测试使用仓库替身，未执行真实UI或文件读取。

### 两种路径与外部实现缺口

|数据|仓库中声明的路径/调用|证据边界|
|---|---|---|
|胶型对象库|DeviceDirPath / EpoxyApplicationRepository.json；BaseSettingRepository.Save → JsonFormatHelper.SaveGenericList|本地调用可见；外部序列化、异常、原子性和实际写入未验证|
|System1产品程式|RecipeDirPath / DispenseProgram.json；System1Program继承Singleton并设置FilePath|外部Singleton.Save实现未在trunk源码中找到；不推断其包含哪些实际序列化字段|
|胶型库加载|JsonFormatHelper.ReadGenericList；本地将null回退空列表|不能把null回退解释为任何异常都被吞下或缺文件总成功|

[路径源码](config-production-gates.html#epoxy-storage-paths)、[保存/加载委托](config-production-gates.html#epoxy-repository-save-delegate)、[System1Program继承与路径](config-production-gates.html#system1-save-owner)。外部DLL/PDB及项目引用已有[依赖边界清单](persistence-dependency-boundary.md)，本轮没有执行这些设备程序集，也没有把库文件存在等同于真实加载版本已确认。

下一步：继续试胶前置门控与其余示教委托，并核对可获得的持久化依赖类型证据；真实写盘、恢复、构建与设备验收保持未完成。

## 后续增量：板示教资格如何产生

S1/S2预点胶板示教的入口、三步委托、保存、退出和IsReady消费链已单独复核，新增33段源码及16项隔离检查。[步骤与限制](plate-teaching-workflow-review.md)、[源码阅读器](plate-teaching-source.html)。特别区分S1调用方正常退出清理、S2测高结果未检查、Save前写完成标志；仍不代表其他示教、真实保存或硬件验收完成。
