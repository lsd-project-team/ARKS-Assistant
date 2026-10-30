# S2 / Bond 调度源码复核

更新：2026-09-28。范围：BondTask 外层调度、S2 动作消息生成/选择/完成和 SlideFluxer 辅助任务。取晶、贴片及视觉动作内部另章验收；本记录不是设备运行证明。

## 工作流程摘要

1. 启动流程先调用动作服务 Init，再启动 BondTask。Init 清消息，按 WorkProcess 与 StepFirst/PositionFirst 分派八种排序方法，再过滤其他步骤、禁用动作、处理相对贴片。InjectSteps 只向焊点 S2RemainingSteps 注入缺失键，不是在每次循环重建 WorkMessages。
2. BondTask.Start 仅在任务为空或非 Running 时创建 LongRunning Task；AbortThread 是空方法。DoWork 重置运行信息，在 WaitStart 循环内回安全位、复位焊头，并可提前换嘴；换嘴失败 Stop 后返回。
3. GetIncomingSignal：补偿工作直接 true；配置流道则等待 TransferToBondFinishedSignal；无流道则检查本地载具，必要时提示放料并 MapBelt，仍无载具或取消就 Stop/false。
4. 来料后依次检查 TpMark 取片补偿、系统2温度补偿、参考点扫描；任一 false 直接 return，本方法这些分支没有显式 Stop。补偿模式创建测试载具，然后 InjectSteps。
5. Enable=true 才执行动作循环。GetNextActionNode 选择第一个 Finished=false 的消息并按名字找动作；null 时 break。IsDoWork=false 跳过执行但仍 FinishCurrentActionNode。执行前调用 CloseDispenseCylinder。
6. 返回 Retry：continue，重新 WaitStart 并重新取第一个未完成消息。返回 Alarm：人工 Retry 用 goto RetryCommand 重试同一个动作对象，不经过该循环顶部的 WaitStart；Ignore 继续标完成；Abort Stop、抬 Z、按配置收胶盘后 return。返回 Abort/Exception 同样局部收尾后 return。
7. switch 未单列的结果会落到 FinishCurrentActionNode；不能把标记完成统一解释为实际动作 Success。DoWork 无统一 try/catch/finally，抛出的异常不保证执行局部 Stop/回退。
8. 内层正常耗尽、Enable=false，甚至内层 WaitStart=false 退出后，代码都可继续执行安全位→Finish→补偿归一化→可选顶针耗时保存→SendAway。Finish 把消息 Finished 全部置 false，并取 WorkMessages[0]；空列表没有保护。
9. SendAway 只有非 Stop 时放行：自动模式发允许传到等待下料信号；人工模式可保存 Mapping，清载具/置 NoMaterial，提示拿走再 Stop。信号发出不等于物理下料已完成。

## 配方编排不是每次执行时重新生成

GetActionNodeMessageByProcess 的判定有优先级：ComponentName != 字符串 `Null`，否则 DefectName，否则 EpoxyNameApplicationName。组件找不到抛异常；三个字段均为 `Null` 返回空列表。它不是三个独立同时触发的分支。

|组件配置|生成的动作消息顺序|
|---|---|
|翻转且 DipMode=AfterAccuracyMode|Pick → UpLookCorrection → DipFlux → SubstrateCameraCorrection → Bond|
|翻转且 DipMode=Off|Pick → UpLookCorrection → SubstrateCameraCorrection → Bond|
|翻转且其他 DipMode|Pick → DipFlux → UpLookCorrection → SubstrateCameraCorrection → Bond|
|非翻转|Pick → UpLookCorrection → SubstrateCameraCorrection → Bond；这里不插入独立 DipFlux 消息，不能据此断言取晶内部没有蘸胶|
|无组件且有 Defect|AfterBondCheck|
|无组件/Defect 且有 Epoxy|S2Dispense|

图的“当前动作类别”表示已经取出的动作所属类别，不是运行到那里才重新生成配方。相机动作可能依据自己的 IsDoWork/DoWork 条件跳过，不能据消息名称承诺每颗芯片都拍上下视。

## 消息选择与退出风险

- GetNextActionNode 对连续相同名称的 UpLookCorrection/SubstrateCameraCorrection 抛异常。因此动作返回 Retry 后也不保证无条件重做成功。
- ChangeNameToActionNode 的 Find 返回值未做空判断；检查的是 ActionNodes 集合本身，且检查晚于 Find。名字没有匹配时会返回 null，外层与“无剩余动作”共用 break。
- InitCurrentMessage 绑定当前步骤、模块、焊点等；部分绑定异常只弹窗，未统一清空旧上下文。完整业务影响仍需结合具体动作复核。
- SetActionNodeReWork 两个重载按当前基板/模块及步骤找到消息，把 Finished 置 false；不存在则抛异常。它影响下一次“首个未完成”的选择，而不是固定回退一个索引。
- Finish 不等于逐消息成功统计，也不等于焊点 S2RemainingSteps 已正确完成；这两类状态须分别溯源。

## 并发胶盘任务

SlideFluxerTask 由启动入口按配置独立启动，不由配方类别节点启动。DoWork 先收胶盘；WaitStart 后在 IsNeedDip 循环中等待焊头离开胶盘区域，再伸出→Set IsAllowDipFluxSignal→等 BondDipFluxFinishSignal→收回→等 AllowSlideOutSignal。

区域等待超过15秒弹窗：Abort Stop/return；其他返回重启计时。Pause 分支重启计时并 continue，跳过本次末尾 Sleep。该区域 while(true) 未见独立 Stop 检查；不能假设所有内层等待都立即响应 Stop。蘸胶完成 Wait=false 会先收盘再 return；AllowSlideOut Wait=false 直接 return。自然退出最外层循环还会收盘；无统一 finally。

## 主要源码入口

- [BondTask 100–354](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L100)：主循环、结果处理与收尾。
- [BondTask 361–490](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L361)：启动、空 Abort、来料与送走。
- [S2ActionNodeController 155–234](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L155)：编排入口与八种分派。
- [715–874](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L715)：组件、检测、点胶展开。
- [911–974](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L911)：Finish 与上下文绑定。
- [1033–1139](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L1033)：选择、完成与重做。
- [1410–1433](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L1410)：焊点步骤注入。
- [SlideFluxerTask 92–250](../../trunk/AKRS.ZX2200/BondSystem/Tasks/SlideFluxerTask.cs#L92)：胶盘并发循环与启动。

## 编排后处理与执行前动作

RemoveOtherStep 仅在 IsOppositeSex 配置下按基板/模块索引和焊点存在性删除不适用消息，0索引和找不到步骤的消息部分直接保留。RemoveDisableActionNode 仅在 LagerNumber 配置为真且运行载具存在时执行，先排序基板/模块，再按消息所在层检查 Disable；不是无条件递归过滤所有父层状态。两个方法都依赖列表索引及对应配置，不能从名字推断提供完整空值防护。

SortRelativeBond 找相对贴片焊点的第一个匹配制程，先删除该制程的 BondPositionVisionActionNode，再在其每个 PickActionNode 前插入视觉消息；Find 结果未逐项判空，不能宣称找不到制程也安全跳过。证据：[1440–1630](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L1440)。

CloseDispenseCylinder 的条件是 **!actionNode.IsCloseCylinder** 才调用 CloseDispenseHeightMeasurementCylinder，与单看属性名可能产生的理解相反；只确认该条件，不推断物理气缸到位。证据：[BondTask 495–500](../../trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs#L495)。

## 十五条图关系的限定

|关系|类型与源码依据|
|---|---|
|wait-prepare|顺序控制流：GetIncomingSignal true 后，159–193执行补偿与注入；false 已返回|
|prepare-next|条件控制流：198–216只有 Enable=true 且 WaitStart 允许才取动作|
|next-type|条件控制流：216–226非 null 才处理当前对象；类别为阅读分组，非运行时重新编排|
|type-component|条件分组：715–854生成组件消息；232逐个调用实际对象 DoWork，非一次调用整串组件动作|
|type-inspect|条件分组：855–873生成检测或点胶消息；运行时同样逐个处理|
|component-outcome|顺序控制流：232–234每个动作返回后 switch；抛异常不进入此返回处理|
|inspect-outcome|顺序控制流：同上；不表示检测必然成功|
|outcome-next|条件控制流：Retry在258 continue；其他正常落到319标完成；再次循环才重新取未完成|
|outcome-operator|条件控制流：277–289仅 Alarm 显示该处理框|
|operator-next|人工操作：Ignore 在310–314退出 switch，319标完成，再重新选取|
|operator-stop|人工操作：293–305选择 Abort 才 Stop、局部回退并返回|
|outcome-stop|条件控制流：236–275显式 Abort/Exception 返回值；不包含所有抛出的异常|
|next-complete|条件返回：219–221 null 才走此边；未匹配动作名也可能 null，不等于完整成功判定|
|complete-release|顺序控制流：330–347；中途任一调用抛异常会中断，SendAway仍按Stop状态决定是否发信号|
|operator-type|人工操作：307–308 goto RetryCommand，重试当前对象及 IsDoWork，不重新生成配方，也不经过顶部 WaitStart|

图只绘制主路径；Enable=false 或内层 WaitStart=false 也可进入收尾，已在图卡明确标注。独立胶盘节点不是主线同步调用。

## 尚未完成

八种排序方法的每层循环、具体动作内部以及过滤依赖的对象完整性仍需展开；三个后处理方法与执行前气缸调用已核实外层分支，未进行运行测试。图表同步和限定范围复核登记完成后更新进度，不因已有图而默认整个 Bond 子系统完成。

## 本轮验收记录

正式 HTML 与规格交付哈希已复核；Archify deliver 9项检查通过且0错误/0警告。Edge visual-check 的回执为 pass；已实际查看1440×900浅色截图，主链、回退、独立胶盘区和提示卡未见遮挡。图像审查只覆盖该截图，不代表全部交互或设备行为已验收。

源码/片段/复核绑定/台账等 verify-all 13项任务通过；新增8段证据，门户共129段。当前限定范围登记57/89节点和64/100关系。整合门户实际导航、完整构建和硬件运行仍未验证。
