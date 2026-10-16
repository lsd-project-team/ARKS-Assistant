# 原组件配方、完整注册节点选择与Interactive短分支

两轮隔离Framework宿主各31,655项检查通过。每轮实际选择5,888条消息，公开配方现已选择全部34种原注册节点实例，补齐上一轮26种范围中的取片、贴片、浸胶、两种校正、S1检测和分段交互。原组件仓库真实Save/Load与Interactive的五次短分支调用亦通过。34种实例选择不等于34种DoWork执行；16工程/29组/1436文件/13项整体目标未完成。

## 组件配方与浸胶顺序

原BaseCarrierConfig的反转台开关×三种浸胶枚举及未知999值生成8个真实对象，一项IsEnable=false。先通过公开BaseDsSettingList填充原仓库，再调用实际SDK Save和Load，获得8个新的原对象实例。名称、反转台标志、浸胶字段（含999）和启用状态均保持；两个宿主的原路径和文件哈希记录保存。SDK使用含$type/$values的JSON类型列表格式。本轮没有调用CarrierConfigRepository.Add的PR复制/保存工作流，配方创建与PR生命周期仍待验证。

每个组件在S2四种WorkProcess×两种WorkProcessModule下生成计划，共64份。另有检测、点胶和禁用无效步骤；真实2基板×2基岛、每基岛2焊点树参与原上下文解析。每个基板/基岛的组件动作顺序逐项核对：

|反转台开关|DipMode|原计划中的顺序|
|---|---|---|
|false|0/1/2/999|Pick → UpLookCorrection → SubstrateCameraCorrection → Bond|
|true|Off(0)|Pick → UpLookCorrection → SubstrateCameraCorrection → Bond|
|true|BeforeAccuracyMode(1)|Pick → DipFlux → UpLookCorrection → SubstrateCameraCorrection → Bond|
|true|AfterAccuracyMode(2)|Pick → UpLookCorrection → DipFlux → SubstrateCameraCorrection → Bond|
|true|未知999|Pick → DipFlux → UpLookCorrection → SubstrateCameraCorrection → Bond|

未知浸胶枚举实际进入else，行为与校正前浸胶顺序相同；没有被Init拒绝。公开仓库中的禁用组件仍被Find和GetCurrentComponent找到，并生成其动作；这是选择层行为，不表示完整启动就绪或节点执行会接受禁用组件。

组件名不是字面量Null时，组件分支优先于同一步的检测/点胶；另两个步骤分别生成PostBondInspection和S2Dispense消息。名字缺失与null均在原公开Init中抛异常，此时已生成45条前置消息；字面量Null则进入检测分支并生成57条消息，不能将null与此哨兵混用。禁用无效步骤完全不进入消息计划。

## S1分段与全部注册接收者

S1三个SubstrateProcessing枚举×八种排序共24计划。Complete和DivideWithInverted各57条；仅字面量Divide生成一个Interactive消息、共58条，在2列配置下把非首半区消息放在Interactive前，首半区放在后。DivideWithInverted本轮实际不生成Interactive，当前源码也只比较Divide。

S1带胶型的步骤优先生成S1Dispense，只有检测的步骤生成S1DispenseDefect。S2组件/检测/点胶及S1分段合并共88计划、5,888条消息/轮；全部34个注册具体类型均至少由原GetNextActionNode返回一次。来源中的39个虚候选是更宽静态集合，不能与34个原目录注册实例混计。

每条消息验证真实目录对象引用、未完成当前消息、实际步骤/树上下文及公开FinishCurrentActionNode逐条标记。共5,376次重复请求返回同一对象；512个校正消息的第二次请求会走原提示/异常守卫，因此本轮没有重复调用，specialRepeatWarningBranchExecuted=false。正常选择这些校正实例及其上下文已真实执行，校正DoWork未执行。

宿主显式用公开Finish方法推进消息；原生产Task、节点IsDoWork、其他具体节点DoWork未调用。 privateMessageDataWritten=false，私有工作消息只读观察，全部消息来自原公开Init。

## 原Interactive DoWork及事件异常

实际原目录Interactive对象共执行5次DoWork；仅此一种具体DoWork类型运行。公开IsTuInDispense1明确设false并在每次普通调用前验证，使Divide分支在移动Z、信号Set/Wait之前返回。Complete、DivideWithInverted不进入Divide块。三个正常调用均返回Success，State最终Stop；WorkStart看到之前的State，WorkStop看到Stop。

另两次使用原公开WorkStart/WorkStop回调验证异常边界。WorkStart位于State=Running及try之前，回调抛出的同一异常直接离开方法，不运行finally/WorkStop，状态保持原值。WorkStop在finally中、State=Stop之后调用；它抛出的同一异常离开finally，覆盖正常Success返回，最终状态仍Stop。测试没有替换SDK方法或消息框；没有执行原catch中的真实提示。

这五次是明确的原节点短分支运行证据，包含主流程事件语义；不能据此认定分段传料、轴运动、等待/信号或其他33种节点执行完成。WorkStart/Stop测试回调属于公开事件接口，已清除。

## 来源、重放与冻结

102个原声明来自65个原文件，完整符号、原字节SHA、严格UTF8/CP936解码和UTF16位置逐项核对；34个目录类型/DoWork符号均与静态候选对应，只有Interactive记录限定运行。准确任务目标仍为Main.Machine.Process.S1/S2ActionNodeController。完整Cecil静态IL共544方法，包含控制器/闭包、组件/仓库/泛型基础仓库和Interactive；544不是运行方法数量。

宿主2份源码、162真实引用编译exit0后运行；bound/replay分别绑定16个已冻结保真资源原源码程序集，32文件SHA/物理路径核对。两个原生过程exit0，31,655个唯一标签、顺序和全部业务结果一致，共63,310次断言放置。原硬件配置路径自然属于隔离目录，硬件仓库始终为空，未创建硬件配置。原组件仓库文件真实保存并重载，SQL没有执行。

初探针在4项通过后因“构造后文件仍缺失”的错误假设exit1；原SDK实际创建零字节文件。完整候选、编译产物/失败输出保留，改为构造前检查缺失、构造后检查空文件/list，再重编译两轮通过。初独立检查器假设保存JSON是裸数组而exit1，草稿/错误记录保留；实际$type/$values封装已按原格式验证，没有修改原JSON或原生输出。

五步原生/来源/IL与动作选择、算法选择、阅读器、虚候选父绑定核验通过。75新增冻结输入，275既有副本复用不增数，9659+75=9734；来源台账不是业务执行覆盖计数。本轮不加入正式冻结1328，也不与历史套件相加认定完整运行。

原生产C#/csproj、完整阅读器/语义图和全部历史冻结证据保持原值。保真原源码程序集未经过完整原工程LC/Fody/MSBuild/部署流程。其他节点IsDoWork/DoWork、生产Task、重复校正提示、真实PR/VM/SQL/UI/设备与完整29组业务解释仍未验收。

下一步检查全部注册节点的原IsDoWork条件与可运行的非设备分支，结合实际组件/树/步骤验证，再推进原Task的等待/Retry/Pause/异常退出；组件Add/PR复制、不同标签/VM初始化及配方完整生命周期、原构建/部署/UI/设备继续待办。整体目标未完成。

只读复验：`node --max-old-space-size=4096 scripts/verify-native-recipe-action-selection.cjs`、`node scripts/verify-native-recipe-action-selection-bindings.cjs`。冻结输出禁止覆盖，新实验另建目录。见[测试](native-recipe-action-selection-test.json)、[审计](native-recipe-action-selection-audit.json)、[进度](native-recipe-action-selection-progress.json)。
