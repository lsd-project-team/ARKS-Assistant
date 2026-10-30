# 全原工程符号与静态操作关系核验

16个原工程、1410个原Compile文件完成两轮独立Roslyn语义提取，32个提取进程均退出0、无语义错误。原始1436文件严格保真解码；未列入原Compile的26文件另行语法解析无错误，仍明确不作工程语义绑定。工程编译项、DEBUG/TRACE等定义、平台、unsafe选项及357个实际元数据引用文件沿用冻结的保真资源编译输入，并核对字节SHA。原生产源码与项目未修改。

结果为29764处声明、32112个当前源编译符号、384201条静态操作边、4581条类型/成员声明关联。384201不是业务断言或方法覆盖数，其中构造引用37250、调用65401、属性143674、字段130113、事件2658、方法引用2719、用户定义运算符1082、转换1304；3252条属于属性元数据，单独标为declaration-attribute-metadata，不能读作运行中的构造调用。5187条操作目标的完整程序集身份与另一原工程源符号精确对应。

所有边和声明均核对符号存在、原字节/解码文本SHA、UTF16偏移、长度及行号；源符号索引和图谱对应。类的继承、接口、成员覆盖和接口实现由真实Roslyn符号得到，包含继承成员实现接口的编译模型映射；它们不等于新的业务模块依赖或运行时派发证明。旧552关系、所有历史阅读器和正式1328测试均保持冻结。

## 重放与真实边界

bound/replay使用各自冻结资源编译引用。6份工程图原始JSON字节一致，另外10份的编译器诊断排列不同；仅排序完整诊断记录后，16份图全部逐值/逐数组顺序一致。没有删除警告、改变消息、规范化源码/符号/操作/关系或抹掉引用身份。主工程原4810条诊断及其顺序都保留；全部工程警告合计6058条，原依赖与部署风险继续成立。

17518条虚调用只绑定其声明目标，546条委托调用保留DelegateInvoke及未解析的运行时目标。原编译配置下本提取范围没有dynamic操作，合成校验fixture则确实验证dynamic未解析分类。反射、配置驱动、事件/委托连接、Fody织入、SDK内部派发、不同预处理配置、全业务解释和实际制程仍需要后续证据。方法引用是引用；属性/字段/事件边是访问或引用，不能统一当作直接函数调用。代码中未执行/不可达分支仍可出现静态边。

本图收录遍历可见IOperation中的上述目标，没有做完整IL降级补全。foreach的GetEnumerator/MoveNext/Dispose、using隐式Dispose、await/async状态机及其他编译器生成调用不能据此图断言已完整列出；属性引用也没有自动扩展成全部访问器调用路径。静态图定位和已执行原生报告是不同证据范围。

合成语义fixture核对重载、泛型原定义、属性get/set、读写、字段初始化、lambda/局部函数归属、接口/virtual目标、用户运算符、隐式转换、delegate/dynamic未解析分类与覆盖/接口关系。此fixture仅测试分析器，不是原生产执行或新增业务覆盖。

## 工程师可用的查询入口

执行下面命令可取回带原行号的完整声明正文及精确符号边，默认最多30条、可设--limit200；--references同时包含属性/字段/事件访问。--assembly同时限定源符号及读取的工程图，省略时搜索全部16工程。

```powershell
node --max-old-space-size=4096 scripts/explore-original-semantic-graph.cjs --symbol .DispenseSystem.Controllers.DispenseController.InterpolationApplication --assembly AKRS.ZX2200 --limit 200
node --max-old-space-size=4096 scripts/explore-original-semantic-graph.cjs --symbol .Infrastructure.Utils.ObjectHelper.Clone --limit 200
node --max-old-space-size=4096 scripts/explore-original-semantic-graph.cjs --symbol .Dispense.Point2D.op_Equality --assembly AKRS.Galaxy2.Dispense --limit 200
```

三条真实查询均退出0并核对原源码文本。真正控制器完整InterpolationApplication为300行起/15837个UTF16字符、98条匹配边；泛型Clone绑定原定义Clone``1(``0)，Point2D相等运算符绑定其精确签名。控制器直接调用EpoxyPretreatment，Clone属于下一级，查询没有把传递调用伪装成直接边；lambda和局部函数分别有自己的词法归属。查询截断明示，完整JSON图可进一步遍历。

只读复验：`node --max-old-space-size=4096 scripts/verify-original-semantic-graph.cjs`、`node scripts/verify-original-semantic-fixture.cjs --check`、`node scripts/verify-original-semantic-query.cjs`及`node scripts/verify-original-semantic-graph-bindings.cjs`。已有结果目录保留，禁止覆盖式重新提取；新提取应另建证据目录。索引位于.archify-work/original-semantic-graph/source-symbol-index.json，各工程原始图、比较、来源与日志位于同一目录。

## 29组范围

Common.cs等被原工程排除的文件没有语义覆盖。以下按清单原29组列出，数量是解析结果，不是模块业务完成率；29组人工业务状态仍为partial。

|组|清单文件|原Compile|排除文件|声明位置|操作边|
|---|---:|---:|---:|---:|---:|
|AKRS.Calibration|12|12|0|144|1546|
|Akrs.ChangeJson|12|12|0|110|742|
|AKRS.Galaxy.SoftKey|6|6|0|74|463|
|AKRS.Galaxy2.AutoFocusing|4|4|0|28|276|
|AKRS.Galaxy2.AxisCompensate|7|7|0|45|123|
|AKRS.Galaxy2.Component.TestDemo|6|6|0|24|136|
|AKRS.Galaxy2.CoordinateSystems|13|13|0|155|1027|
|AKRS.Galaxy2.Dispense|82|81|1|1341|8872|
|AKRS.Galaxy2.LogTest|6|6|0|27|283|
|AKRS.Galaxy2.Machine|7|6|1|187|294|
|AKRS.Galaxy2.MachineSupport|4|4|0|39|92|
|AKRS.Galaxy2.PR|87|85|2|1291|25188|
|AKRS.Galaxy2.PR.Test|6|6|0|29|97|
|AKRS.Galaxy2.TeachTest|17|17|0|307|4294|
|AKRS.ZX2200/BondSystem|227|222|5|5691|79609|
|AKRS.ZX2200/CalibSystem|65|65|0|1893|29161|
|AKRS.ZX2200/Common.cs|1|0|1|0|0|
|AKRS.ZX2200/DispenseSystem|75|74|1|1372|15242|
|AKRS.ZX2200/Experiment|68|64|4|1485|31179|
|AKRS.ZX2200/Infrastructure|126|123|3|1932|22467|
|AKRS.ZX2200/Localization|4|4|0|78|390|
|AKRS.ZX2200/Main|76|72|4|1724|22282|
|AKRS.ZX2200/Program.cs|1|1|0|12|174|
|AKRS.ZX2200/Properties|3|3|0|235|367|
|AKRS.ZX2200/SupportFeature|160|160|0|2752|32905|
|AKRS.ZX2200/TransportSystem|73|73|0|1220|14533|
|AKRS.ZX2200/TransportUnitSystem|104|104|0|2640|32037|
|AKRS.ZX2200/WaferSubSystem|174|172|2|4778|56546|
|InterpolationMovementTest|10|8|2|151|3876|

26个排除文件只有明确DEBUG/TRACE配置下的语法证据：

- trunk/AKRS.Galaxy2.Dispense/Properties/Resources.Designer.cs
- trunk/AKRS.Galaxy2.Machine/Services/MachineService.cs
- trunk/AKRS.Galaxy2.PR/Models/TemplateConfigs/BaseTemplateConfig.cs
- trunk/AKRS.Galaxy2.PR/Models/TemplateConfigs/PRTemplateConfig.cs
- trunk/AKRS.ZX2200/BondSystem/Controls/Setting/ProcessStep/FrmCreateProcessStep.cs
- trunk/AKRS.ZX2200/BondSystem/Controls/Setting/ProcessStep/FrmCreateProcessStep.Designer.cs
- trunk/AKRS.ZX2200/BondSystem/Controls/Setting/ProcessStep/UcProcessStepEdit.cs
- trunk/AKRS.ZX2200/BondSystem/Controls/Setting/ProcessStep/UcProcessStepEdit.Designer.cs
- trunk/AKRS.ZX2200/BondSystem/Services/System1ActionNodesService.cs
- trunk/AKRS.ZX2200/Common.cs
- trunk/AKRS.ZX2200/DispenseSystem/Services/System2ActionNodesService.cs
- trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmChooseCamera.cs
- trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmChooseCamera.Designer.cs
- trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmRotateCenterAccuracy.cs
- trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmRotateCenterAccuracy.Designer.cs
- trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/InterpolationParamConfig.cs
- trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/NLogTraceWriter.cs
- trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/SingleInterpolationParam.cs
- trunk/AKRS.ZX2200/Main/Machine/Control/FrmChipFrictionSetting.cs
- trunk/AKRS.ZX2200/Main/Machine/Control/FrmChipFrictionSetting.Designer.cs
- trunk/AKRS.ZX2200/Main/Machine/Product/ProcessStep/ProcessStep.cs
- trunk/AKRS.ZX2200/Main/Machine/Product/ProcessStep/ProcessStepProgram.cs
- trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ComponentsTeach/FrmComponentLocateUseInfo.cs
- trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ComponentsTeach/FrmComponentLocateUseInfo.Designer.cs
- trunk/InterpolationMovementTest/FrmTest.cs
- trunk/InterpolationMovementTest/FrmTest.Designer.cs

## 保留的候选与审计

首个81文件pilot通过，但未采用其属性归属分类；大工程初候选因重复创建语义模型过慢及属性元数据分类问题主动停止，未产生主图。输入、空日志、4294967295提取退出和原脚本保持在interrupted-v1。修正后32次提取均成功，但外层原始字节相等守卫失败；完整原图和原守卫保留，诊断排序比较bb3b69通过。第一份查询检查器错误预期控制器直接Clone，实际EpoxyPretreatment已核；833dd8失败检查器保留、e9cbce通过，图/源未改变。初摘要/索引亦保留，后增加分类计数并复验通过。

完整范围/索引/位置、合成fixture、三查询、原控制器与保真资源父绑定五项流水线2867/4f2da4通过；冻结27074/1456d1、只读绑定9e2aad通过。1982新增输入绑定包括1436原源文件、357元数据引用及本轮输入/图谱/脚本/历史候选与日志，父6653+1982=8635。该计数是证据绑定数，没有与原生业务检查相加。

本轮未加载原生产程序集执行、未进行完整MSBuild/LC/Fody/部署、真实窗口/OS输入/SQL/设备或成功制程。现有点胶阅读器仍52专题5257快照，尚未接入这份精确语义索引或最新策略/控制器报告。下一步将可追溯符号关系接入派生交接视图，再推进业务解释与真实依赖/完整构建验收。16工程/29组/1436文件/13项整体目标未完成。

见[测试](original-semantic-graph-test.json)、[审计](original-semantic-graph-audit.json)、[进度](original-semantic-graph-progress.json)。
