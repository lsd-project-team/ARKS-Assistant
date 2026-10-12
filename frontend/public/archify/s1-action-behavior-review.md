# S1 定位、测高与识别动作复核

更新：2026-09-28。范围：15 个注册动作的包装层和独立预点胶入口中，本轮补完其余 11 个动作包装及 System1Domain 共用方法；不是全部硬件驱动、视觉 SDK 和配方持久化验收。前一轮排序与调度见 [S1 主链复核](dispense-semantic-revalidation.md)。

## 对自动工作的影响

配方消息先由 GetNextActionNode 找动作，IsDoWork 判定是否执行。门控 false 仅标消息完成；门控抛异常不会自动进入动作 DoWork 的 catch。动作返回 Success 会标消息完成，但可能代表跳过、禁用物料或未检查的定位结果，不能等同加工合格。

|动作组|实际调用|返回与关键门控|
|---|---|
|载具定位|System1MatterVision(TransportUnit)|Divide 直接 Success；非分段时忽略 bool 结果再返回 Success。门控含禁用、仅 S2、已定位及 S1 已完成；不含显式 AdjustType.None 检查。|
|基板/模块定位|System1MatterVision(CurrentSubstrate/Module)|包装层也忽略 bool；门控额外检查 AdjustType.None。|
|焊点定位修正|System1MatterVision(CurrentBondPosition)|非异形且 RelativeBondPosition 时直接 Success；其余忽略 bool。门控含 AdjustType.None、物料状态、已定位和完成。|
|载具测高|MatterHeightMeasurePoints(TransportUnit)|总配置未启用直接 Success；否则透传结果。门控含已测高、物料状态及 S1 完成。|
|基板测高|MatterHeightMeasurePoints(Substrate)|门控还要求 EntityState.Process、当前对象配置启用；DoWork 在总基板配置关闭且非异形时跳过。|
|模块测高|MatterHeightMeasurePoints(Module)|门控含当前对象测高配置；DoWork 再检查同一配置，结果透传。|
|四层身份识别|MatterIdentity(当前层级对象)|门控要求 EntityState.Process、识别开启、未识别、非禁用/仅 S2、S1 未完成；离线标记识别后真正 return Success，普通路径透传结果。|

包装层 catch 把其 try 内异常转换为 Exception；WorkStart 在 try 前、WorkStop 在 finally，不能声称所有回调异常都被转换。载具/基板/模块测高的离线分支实际设置 IsVisioned，不是 IsMeasureHeight，且没有立即 return；该表述按代码原样记录，未修改生产源码。

## 共用定位链

[System1MatterVision 96–196](../../trunk/AKRS.ZX2200/DispenseSystem/Models/System1Domain.cs#L96)：AdjustType.None 置 IsVisioned=true 返回；Disable 且 byMapping 时直接 true。其余依序执行 P1/P2/P3/P4，在对应配置点数且 EntityState 非 Fail 时调用 TuService.UpdateEntity 并返回；取点 false 则返回 false。

两点模式额外执行 DistanceCheck：Abort 调 Stop 返回 false；Retry 设置 visionAlarm=true 后回到 P1，后续重试轮不再进行同一距离检查；None 直接赋 MatterProductState.Disable，随后仍 UpdateEntity。直接属性赋值不等同 SetMatterDisable 递归方法。

[System1VisionByPos 205–360](../../trunk/AKRS.ZX2200/DispenseSystem/Models/System1Domain.cs#L205)：单步等待不通过或 EntityState.Fail 返回 false；计算坐标后调用 DispenseVision。开启 AroundLocate 且未匹配则按 +X、-X、+Y、-Y 最多四次搜索，任一非空即结束。仍无结果则移动到原视觉位并调用 VisionAlarmLockFunc：OK 采用人工结果，Ignore 调 SetMatterDisable 返回 false，Abort Stop 后 false，其余 false。成功转换坐标并 SaveInfo；这些包装不能证明视觉 SDK 内部实际采集流程。

四个定位动作都没有消费 System1MatterVision 的 bool 返回。因此共用方法返回 false 后包装仍可能 Success，外层标消息完成；若内部已 Stop，外层后续 WaitStart 会退出。不能把所有 false 解释成自动全机停止，也不能把 Success 解释成定位成功。

[TuService.UpdateEntity 553–609](../../trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs#L553) 清四个 Bitmap、计算新旧点和角度，按配置可走两点角度或三点圆心分支，调用 UpdateCoordinateSystem 并置 IsVisioned=true。底层坐标类及角度公式的物理正确性未验收。

## 共用测高链与重试边界

[MatterHeightMeasurePoints 371–474](../../trunk/AKRS.ZX2200/DispenseSystem/Models/System1Domain.cs#L371)：零测高点或对象配置未启用直接 Success。逐点单步等待，转换坐标，按激光配置决定 Z 附加距离；调用 DispenserHeightMeasurementG0(HeightSensor, ..., closeCy)。

返回高度先转换并 Add 到 resultList，之后才判断返回值、偏差和 NaN。Retry 跳回当前测量标签，不删除已加入的读数；因此最终 Average 的集合可能包括失败或越界尝试，而非每个测点只保留最后一次成功值。这是源码可见的数据路径，不是已经复现的设备故障。

Ignore 调 SetMatterDisable 后返回 Success；Abort 返回 Exception。正常末段平均读数减配置高度平均值，先写 MeasureHeightResult；NaN 会抛异常，否则给坐标 Z 加偏移，置 IsMeasureHeight=true。底层传感器读取、气缸反馈和实际量测精度仍待验收。焊点测高包装还会把共用方法所有非 Success 返回转换为 Abort，其他三层包装透传。

## 共用身份识别链

[MatterIdentity 553–626](../../trunk/AKRS.ZX2200/DispenseSystem/Models/System1Domain.cs#L553)：Off 直接 Success；读取相对视觉位和 PR 名，转换到 G0 后调用 DispenseVision 并转成 CodeResult。空结果通过 VisionAlarmLockFunc 处理：OK 采用返回结果，Ignore 递归禁用后 Success，Abort 调 Stop 后 Abort，其他结果 Abort。最后置 IsIdentity=true 并写 IdentityCode；此处未看到数据库或外部服务调用，不能把代码保存到内存属性表述为上传或持久化。人工 OK 后仍可能为空或类型不符，由包装 catch 处理相应异常。

## 禁用传播

[载具 556–562](../../trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/TransportUnit.cs#L556) 遍历基板；[基板 323–329](../../trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/Substrate.cs#L323) 遍历模块；[模块 329–335](../../trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/Module.cs#L329) 遍历焊点；[焊点 205–208](../../trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/BondPosition.cs#L205) 置 MatterProductState.Disable。因此上层 Ignore 可以影响其下多个焊点后续门控；父对象聚合状态计算及空子集行为不在本节验收范围。

## 源码包装层入口

- [S1CarrierVisionActionNode](../../trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/DispenseUpAction/S1CarrierVisionActionNode.cs)
- [S1SubstrateVisionActionNode](../../trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/DispenseUpAction/S1SubstrateVisionActionNode.cs)
- [S1ModuleVisionActionNode](../../trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/DispenseUpAction/S1ModuleVisionActionNode.cs)
- [S1CarrierMeasureHeightActionNode](../../trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/HeightMeasurementActionNode/S1CarrierMeasureHeightActionNode.cs)
- [S1SubstrateMeasureHeightActionNode](../../trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/HeightMeasurementActionNode/S1SubstrateMeasureHeightActionNode.cs)
- [S1ModuleMeasureHeightActionNode](../../trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/HeightMeasurementActionNode/S1ModuleMeasureHeightActionNode.cs)
- [S1TransportIdentityActionNode](../../trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/IdentityActionNode/S1TransportIdentityActionNode.cs)
- [S1SubstrateIdentityActionNode](../../trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/IdentityActionNode/S1SubstrateIdentityActionNode.cs)
- [S1ModuleIdentityActionNode](../../trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/IdentityActionNode/S1ModuleIdentityActionNode.cs)
- [S1BondPositionIdentityActionNode](../../trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/IdentityActionNode/S1BondPositionIdentityActionNode.cs)
- [S1DispenseCorrectionActionNode](../../trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/DispenseBPAction/S1DispenseCorrectionActionNode.cs)

## 当前完成与缺失

已读：全部注册动作包装、独立预点胶包装、调度排序、共用定位/测高/身份识别外层。未完成：所有下层控制器/SDK、配置读写、配方实例数据、硬件运行、整合门户浏览器导航验收。源码快照收录于 [S1 证据文件](dispense-review-evidence.json)，哈希检查不是运行验证。
