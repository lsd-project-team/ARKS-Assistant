# Mapping恢复后：状态如何影响调度

更新：2026-09-28。范围限定为源码静态调用与条件判断；未运行主程序、设备或完整Mapping文件往返。

## 工作流摘要

码值文件存在时读取文本，按当前配置构造载具（构造内已执行S2/S1注入），再次注入，然后赋文件头和逐格状态。X禁用位置；1不覆盖构造后的状态；其他字符串把对应模块全部焊点的两套步骤键置true，并赋相同码值。三种阵列分支决定遍历；均非阵列时不处理网格。本方法解析异常没有有效catch或自动重试。

[Archify恢复流程](mapping-restore-workflow.html)展示读取方法范围。分支节点说明每格副作用；“全部处理后”表示遍历完成才返回，不表示并行执行。构造/注入细节见[mapping-restore-step-review.md](mapping-restore-step-review.md)。

## 已核实的下游消费者

1. BondPosition.IsFinishedInSystem1在EnableInSystem2或Disable时直接true，否则调用步骤字典判定；IsFinishedInSystem2对EnableInSystem1或Disable直接true。因此禁用与步骤全true是不同写入，但这些属性都可能返回true。证据restoreconsume-properties。
2. S1/S2焊点身份识别IsDoWork在禁用、仅另一系统启用、已识别或相应IsFinished为true时返回false。S2字段名substrate实际类型是BondPosition，不能按字段名称推断层级。此处仅证明身份识别动作条件，不宣称全部步骤共用门控。证据restoreconsume-s1-identity、restoreconsume-s2-identity。
3. S2ActionNodeController.Init清空WorkMessages，排序生成动作后调用RemoveOtherStep→RemoveDisableActionNode→SortRelativeBond。禁用过滤仅在LagerNumber为true且BondSubSectionProgram.TransportUnit非null时执行。按WorkIndex排序后，用消息1基索引定位基板/模块，按分支检查基板、焊点或模块Disable并删除消息；Substrate==0消息不在此过滤。不能推广成所有配置均删除禁用动作。证据restoreconsume-s2-init、restoreconsume-s2-filter。
4. GetNextActionNode取WorkMessages第一个Finished==false的消息；FinishCurrentActionNode将当前消息Finished=true。这是动作队列标志，并非直接读取BondPositionInfo步骤字典。连续同名UpLookCorrection/SubstrateCameraCorrection动作会被拒绝。导入步骤字典全true不等价于在此将所有消息标为完成。证据restoreconsume-s2-next。

## 源码导航

在[源码阅读器](module-source-explorer.html)搜索restoreconsume。路径相对trunk/AKRS.ZX2200。

|证据|文件|行号|
|---|---|---|
|restoreconsume-properties|TransportUnitSystem/Module/Matter/BondPosition.cs|125–139|
|restoreconsume-s1-identity|DispenseSystem/Models/DispenseAction/IdentityActionNode/S1BondPositionIdentityActionNode.cs|74–108|
|restoreconsume-s2-identity|BondSystem/Models/ActionNodes/IdentityActionNode/S2BondPositionIdentityActionNode.cs|23–108|
|restoreconsume-s2-init|Main/Machine/Process/S2ActionNodeController.cs|155–175|
|restoreconsume-s2-filter|同上|1554–1628|
|restoreconsume-s2-next|同上|1033–1075|

## 缺失项

- 已核实身份识别门控和S2队列过滤/选择；取片、固晶、点胶等具体动作的全部跳过条件仍需逐项追踪。
- 导入UI与实际启动Init的先后、载具对象身份一致性、非LagerNumber配置的恢复状态消费仍待核实。
- 配方一致性、阵列尺寸、空/含空格码值等完整编解码样本验证未完成。
- 图表收据证明渲染质量，不证明恢复后可在实机正确续跑。
