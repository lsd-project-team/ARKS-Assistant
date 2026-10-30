# ZX2200 Mapping恢复链路验收清单
更新：2026-09-28

本页区分已读源码、隔离测试和待验收场景。14项均未完成端到端运行验收；测试PASS包括命中预期缺陷，不表示设备恢复安全。

## 配置一致性边界

先选择实际配方并核对配置，再导入Mapping。文件RecipeName只是写入载具信息，不能据此认定软件切换了配方。ReLoadRecipe的InitProgramNodes位于PR加载try之前，该调用抛错时不能借用后面的finally承诺界面恢复。外部单例、视觉库和真实配置加载尚需运行证据。

## 场景清单

### R01 配方选择与配置重载

- 当前状态：源码已核对；端到端运行未验收。
- 已确认：不同RecipeID触发重载；ProductConfiguration重新指定当前配方目录并清空instance。重载先初始化节点，再进入PR加载try。
- 待验收：记录实际RecipeID、配置文件哈希、阵列尺寸及步骤名称；验证实际单例加载和PR失败路径，不能由instance=null推出已成功读盘。
- 隔离测试：本场景无对应执行报告。

- [main-recipe-select](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=main-recipe-select) — `trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs:804–839`
- [main-program-nodes](module-source-explorer.html#module=AKRS.ZX2200%2FInfrastructure&evidence=main-program-nodes) — `trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs:124–132`
- [main-recipe-reload](module-source-explorer.html#module=AKRS.Galaxy2.PR&evidence=main-recipe-reload) — `trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs:137–203`
- [recipe-product-init](module-source-explorer.html#module=AKRS.ZX2200%2FInfrastructure&evidence=recipe-product-init) — `trunk/AKRS.ZX2200/TransportUnitSystem/ProductConfiguration.cs:68–83`
- [recipe-root-path](module-source-explorer.html#module=AKRS.ZX2200%2FInfrastructure&evidence=recipe-root-path) — `trunk/AKRS.Galaxy2.MachineSupport/Config/PathConfig.cs:35–94`

### R02 文件头与当前配置一致性

- 当前状态：源码已核对；端到端运行未验收。
- 已确认：先按当前配置构造并注入，再将文件配方名写入TU信息；网格循环使用当前配置。
- 待验收：用不同实际配方、同名不同尺寸、不同步骤定义的历史文件检查对象、键和位置；明确不一致时应拒绝还是转换。
- 隔离测试：[mapping-codec-test.json](mapping-codec-test.json)；仅限报告范围。

- [codemap-read](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=codemap-read) — `trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs:1953–2079`
- [tu-construct-init](module-source-explorer.html#module=AKRS.ZX2200%2FBondSystem&evidence=tu-construct-init) — `trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/TransportUnit.cs:65–143`

### R13 构造阶段的配置修改和异常清理

- 当前状态：源码已核对；端到端运行未验收。
- 已确认：构造按当前配置创建实体并可能修改阵列配置；ModifyMatter异常时清状态配置并调用Save，不回滚此前实体状态。清理或Save再抛错会向外传播。 大数量状态缺名返回默认结构体Enable，不触发catch或Save；已撤回旧类替身的相反结论。
- 待验收：用已认证配方核对Count/行列/坐标/名称一致性，记录导入前后配置哈希和实体状态；验证真实保存失败行为。14项原方法测试未执行完整构造或磁盘保存。
- 隔离测试：[mapping-constructor-state-test.json](mapping-constructor-state-test.json)；仅限报告范围。

- [tu-construct-init](module-source-explorer.html#module=AKRS.ZX2200%2FBondSystem&evidence=tu-construct-init) — `trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/TransportUnit.cs:65–143`
- [tu-coordinate-create](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=tu-coordinate-create) — `trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/TransportUnit.cs:261–357`
- [tu-modify-matter](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=tu-modify-matter) — `trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs:887–957`
- [tu-clear-config](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=tu-clear-config) — `trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/OtherConfig.cs:20–55`
- [restorebuild-sub-mod](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=restorebuild-sub-mod) — `trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/Substrate.cs:104–175`
- [restorebuild-module](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=restorebuild-module) — `trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/Module.cs:54–141`
- [restorebuild-bp](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=restorebuild-bp) — `trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/BondPosition.cs:40–82`
- [restorebuild-config](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=restorebuild-config) — `trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/BaseMatter.cs:111–140`
- [restorebuild-array](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=restorebuild-array) — `trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/ArrayConfig.cs:18–68`
- [config-state-types](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=config-state-types) — `trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/OtherConfig.cs:157–294`
- [config-state-enum](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=config-state-enum) — `trunk/AKRS.ZX2200/TransportUnitSystem/Model/TuEnum.cs:278–302`

### R03 窗口目标与导入对象

- 当前状态：源码已核对；端到端运行未验收。
- 已确认：文件按钮固定写S2；扫码按钮写窗口绑定对象。
- 待验收：分别在S1和S2窗口记录导入前后对象标识、显示对象与实际执行对象；确认产品设计。
- 隔离测试：本场景无对应执行报告。

- [restorestart-ui-binding](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=restorestart-ui-binding) — `trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Mapping/FrmTransportUnitMapping.cs:32–71`
- [restorestart-ui-targets](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=restorestart-ui-targets) — `trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.DataAdministrator.cs:81–113`
- [codemap-ui-read](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=codemap-ui-read) — `trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Mapping/FrmTransportUnitMapping.cs:107–125`
- [codemap-ui-save-id](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=codemap-ui-save-id) — `trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Mapping/FrmTransportUnitMapping.cs:175–213`

### R04 启动时对象重建

- 当前状态：源码已核对；端到端运行未验收。
- 已确认：IsProduct默认false；S1/S2有不同条件的new对象分支。
- 待验收：覆盖S1/S2、输送配置、Enable、补偿模式，逐时点记录对象身份和恢复字典；确认何时保留恢复数据。
- 隔离测试：本场景无对应执行报告。

- [restorestart-product-default](module-source-explorer.html#module=AKRS.ZX2200%2FBondSystem&evidence=restorestart-product-default) — `trunk/AKRS.ZX2200/TransportUnitSystem/Module/Information/TransportUnitInfo.cs:25–29`
- [restorestart-bond-replace](module-source-explorer.html#module=AKRS.ZX2200%2FBondSystem&evidence=restorestart-bond-replace) — `trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs:187–226`
- [restorestart-s1-loop](module-source-explorer.html#module=AKRS.ZX2200%2FDispenseSystem&evidence=restorestart-s1-loop) — `trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs:93–166`

### R05 物料搜索与人工确认

- 当前状态：源码已核对；端到端运行未验收。
- 已确认：已有对象可能早退、刷新、保留或清空；真空无料分支可人工Retry。
- 待验收：覆盖搜索结果、反向搜索、自动模式、已有对象及人工选项，记录重试和退出；不得以提示框出现代替物料确认。
- 隔离测试：本场景无对应执行报告。

- [restoretransfer-s1-belt](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=restoretransfer-s1-belt) — `trunk/AKRS.ZX2200/TransportSystem/Controllers/DispenseSubSectionController.cs:437–523`
- [restoretransfer-s2-belt](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=restoretransfer-s2-belt) — `trunk/AKRS.ZX2200/TransportSystem/Controllers/BondSubSectionController.cs:429–510`
- [restoretransfer-s2-vacuum](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=restoretransfer-s2-vacuum) — `trunk/AKRS.ZX2200/TransportSystem/Controllers/BondSubSectionController.cs:511–605`

### R06 Refresh与工位交接

- 当前状态：源码已核对；端到端运行未验收。
- 已确认：交接是引用赋值；Refresh更新坐标与定位测高信息；几处空值处理不同。
- 待验收：验证交接前后对象及步骤字典、坐标上下级，模拟Refresh异常；运动和外部坐标实现仍需独立验证。
- 隔离测试：本场景无对应执行报告。

- [restorestart-tu-refresh](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=restorestart-tu-refresh) — `trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/TransportUnit.cs:135–143`
- [restoretransfer-clear](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=restoretransfer-clear) — `trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/TransportUnit.cs:623–642`
- [restoretransfer-s1-s2](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=restoretransfer-s1-s2) — `trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs:1475–1501`
- [restoretransfer-s2-wait](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=restoretransfer-s2-wait) — `trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs:1763–1779`
- [restoretransfer-wait-out](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=restoretransfer-wait-out) — `trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs:2011–2026`

### R07 码值格式和信息损失

- 当前状态：源码已核对；端到端运行未验收。
- 已确认：受控样本确认1/X状态冲突、空格错位、空码恢复完成及首焊点码复制。
- 待验收：确认合法字符、空值和逐焊点保存需求；使用脱敏真实样本对比每个位置，不能将格式缺陷的预期命中当验收通过。
- 隔离测试：[mapping-codec-test.json](mapping-codec-test.json)；仅限报告范围。

- [codemap-export-grid](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=codemap-export-grid) — `trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs:1578–1739`
- [codemap-read](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=codemap-read) — `trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs:1953–2079`

### R08 步骤注入与完成标记

- 当前状态：源码已核对；端到端运行未验收。
- 已确认：完成方法标记现有字典；空S2字典也可报告完成。重复注入的隔离行为已有测试。
- 待验收：按实际生产步骤名称核对键集合、重名/改名/缺键和目标焊点名称，不能只比较最终完成布尔值。
- 隔离测试：[mapping-step-semantics-test.json](mapping-step-semantics-test.json)；仅限报告范围。

- [tu-construct-init](module-source-explorer.html#module=AKRS.ZX2200%2FBondSystem&evidence=tu-construct-init) — `trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/TransportUnit.cs:65–143`
- [restorestep-finish1](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=restorestep-finish1) — `trunk/AKRS.ZX2200/TransportUnitSystem/Module/Information/BondPositionInfo.cs:166–178`
- [restorestep-finish2](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=restorestep-finish2) — `trunk/AKRS.ZX2200/TransportUnitSystem/Module/Information/BondPositionInfo.cs:200–212`
- [restorestep-isfinished2](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=restorestep-isfinished2) — `trunk/AKRS.ZX2200/TransportUnitSystem/Module/Information/BondPositionInfo.cs:145–161`

### R09 动作门控与队列完成

- 当前状态：源码已核对；端到端运行未验收。
- 已确认：七类门控有隔离测试；字典缺键会抛出，返回false仍可完成队列消息。
- 待验收：验证剩余动作类型和真实Init队列；记录每步IsDoWork、DoWork是否调用、队列Finished及载具状态。
- 隔离测试：[mapping-action-gates-test.json](mapping-action-gates-test.json)；仅限报告范围。

- [restorestart-gate-0](module-source-explorer.html#module=AKRS.ZX2200%2FBondSystem&evidence=restorestart-gate-0) — `trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/BondPosition.cs:187–200`
- [restorestart-gate-1](module-source-explorer.html#module=AKRS.ZX2200%2FBondSystem&evidence=restorestart-gate-1) — `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs:521–540`
- [restorestart-gate-2](module-source-explorer.html#module=AKRS.ZX2200%2FBondSystem&evidence=restorestart-gate-2) — `trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.cs:383–408`
- [restorestart-gate-7](module-source-explorer.html#module=AKRS.ZX2200%2FDispenseSystem&evidence=restorestart-gate-7) — `trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/DispenseBPAction/S1DispenseActionNode.cs:177–203`
- [restorestart-bond-finish](module-source-explorer.html#module=AKRS.ZX2200%2FBondSystem&evidence=restorestart-bond-finish) — `trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs:316–319`
- [restorestart-s1-loop](module-source-explorer.html#module=AKRS.ZX2200%2FDispenseSystem&evidence=restorestart-s1-loop) — `trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs:93–166`
- [restoreconsume-s2-filter](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=restoreconsume-s2-filter) — `trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs:1554–1628`

### R10 文件错误及保存结果

- 当前状态：源码已核对；端到端运行未验收。
- 已确认：缺文件返回null，损坏头异常外传；保存异常只提示，上层不能仅据无异常确认成功。
- 待验收：覆盖缺失/截断/权限/重复ID/中途写入失败，并检查UI提示、调用返回、日志和落盘内容是否一致。
- 隔离测试：[mapping-codec-test.json](mapping-codec-test.json)；仅限报告范围。

- [codemap-write](module-source-explorer.html#module=AKRS.ZX2200%2FBondSystem&evidence=codemap-write) — `trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs:1741–1762`
- [codemap-read](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=codemap-read) — `trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs:1953–2079`
- [codemap-send](module-source-explorer.html#module=AKRS.ZX2200%2FBondSystem&evidence=codemap-send) — `trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs:443–489`

### R11 恢复后停止与再次启动

- 当前状态：源码已核对；端到端运行未验收。
- 已确认：启动包含多个任务及对象条件分支；局部方法测试没有执行这些任务。
- 待验收：在获批运行环境记录导入、启动、暂停、停止、重启、任务结束和对象替换时间线；验证不会重复或遗漏加工。
- 隔离测试：本场景无对应执行报告。

- [restorestart-start](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=restorestart-start) — `trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:261–290`
- [restorestart-transport-start](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=restorestart-transport-start) — `trunk/AKRS.ZX2200/TransportSystem/Models/TransportDomain.cs:84–141`
- [restorestart-bond-replace](module-source-explorer.html#module=AKRS.ZX2200%2FBondSystem&evidence=restorestart-bond-replace) — `trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs:187–226`
- [restorestart-s1-loop](module-source-explorer.html#module=AKRS.ZX2200%2FDispenseSystem&evidence=restorestart-s1-loop) — `trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs:93–166`

### R12 端到端交接验收

- 当前状态：源码已核对；端到端运行未验收。
- 已确认：已具备局部源码链与独立测试，尚无同一次运行的完整恢复记录。
- 待验收：提交版本/配置/原文件哈希、位置期望表、全过程事件记录、实际输出逐位置对照、异常处理及工程师签认；没有这些材料不得标记完成。
- 隔离测试：本场景无对应执行报告。

- [codemap-read](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=codemap-read) — `trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs:1953–2079`
- [restorestart-start](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=restorestart-start) — `trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:261–290`
- [restoretransfer-s1-s2](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=restoretransfer-s1-s2) — `trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs:1475–1501`
- [restoretransfer-s2-wait](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=restoretransfer-s2-wait) — `trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs:1763–1779`
- [restoretransfer-wait-out](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=restoretransfer-wait-out) — `trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs:2011–2026`
- [codemap-send](module-source-explorer.html#module=AKRS.ZX2200%2FBondSystem&evidence=codemap-send) — `trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs:443–489`

### R14 配置改名与恢复状态名称一致性

- 当前状态：源码已核对；端到端运行未验收。
- 已确认：偏移与双工位步骤改名，普通状态列表和大数量状态数组保留旧名；制程Save早于产品Save；InitializeTS为void且可不清理直接返回。
- 待验收：认证配方下验证状态、PR、现存TU和动作键一致性，覆盖拒绝清空及分段保存失败。6项隔离原方法断言不替代完整改名和恢复验收。
- 隔离测试：[config-rename-test.json](config-rename-test.json)；仅限报告范围。

- [config-rename-ui](module-source-explorer.html#module=AKRS.ZX2200%2FBondSystem&evidence=config-rename-ui) — `trunk/AKRS.ZX2200/BondSystem/Controls/Setting/BondPosition/UcAddBondPosition.cs:331–395`
- [config-rename-offset-state](module-source-explorer.html#module=AKRS.ZX2200%2FBondSystem&evidence=config-rename-offset-state) — `trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/OtherConfig.cs:62–89`
- [config-rename-process](module-source-explorer.html#module=AKRS.ZX2200%2FBondSystem&evidence=config-rename-process) — `trunk/AKRS.ZX2200/Main/Machine/Process/ProcessDomain.cs:259–278`
- [config-rename-pr](module-source-explorer.html#module=AKRS.ZX2200%2FBondSystem&evidence=config-rename-pr) — `trunk/AKRS.ZX2200/BondSystem/Controls/Setting/BondPosition/UcAddBondPosition.cs:313–324`
- [config-rename-clear](module-source-explorer.html#module=AKRS.ZX2200%2FBondSystem&evidence=config-rename-clear) — `trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs:150–224`

## 交接材料

保留源码版本/哈希、实际配方及配置哈希、输入文件、逐位置预期、运行事件顺序、对象标识、实际输出、异常处置及复核人。材料缺失则保持未验收。

[项目入口](index.html) · [项目进度](project-plan-status.md) · [恢复流程图](mapping-restore-workflow.html)