# 固晶动作与回带恢复：源码复核

更新：2026-09-28。范围：BondActionNode 主流程、Bond 执行包装、回带处理和胶印检测外层；驱动与设备运行另行验收。

## 实际工作步骤摘要

1. 调度先查 IsDoWork：焊点 EntityState 必须为 Process，且不能为 Disable/EnableInSystem1，当前 S2 步骤必须仍需要执行。WorkStart 事件在 DoWork 的 try 之前触发；不能说所有入口异常都由该 catch/finally 包住。
2. PrepareBeforeBondAction 获取当前组件、吸嘴、焊点和 Z 速度。OffLine 直接标当前 S2 步骤完成后 Success；DryCycle 转独立模拟动作。两者均位于 try 内，与取晶的 OffLine 提前返回位置不同。
3. 普通路径 CalculateBondPos→按慢速下压配置构造预固晶高度→MoveToPreBondPos；非 Success 提前返回。随后通知胶盘并记录当前 RealBondPos。
4. ReBond 标签从启动力曲线、力模式清零开始。IsDipOnTU 且 WatchFluxCount 对 DipOnTUAfterBondingNum 取模为0时执行 DipFluxOnTU，否则 BondOnTU。重贴不重新计算位置、不重做预固晶移动或胶盘通知。
5. Bond 包装：取动作参数→慢下→延时 max(PlacementDelay−VacuumOffDelay,0)→普通贴片关真空、提交异步弱吹并延时 VacuumOffDelay→记录实际压力→关闭界面压力读取→条件慢升。DipFluxOnTU 跳过关真空/弱吹段。内部异常日志/弹窗后返回 Exception，无统一硬件 finally。
6. Bond Success 后 ExportForceData。普通贴片仅在启用芯片检测且启用慢速离开时检查回带；关闭当前吹气，取 ComponentCheckAfterBonding 的反值为 hasMaterial，并异步关真空。
7. 回带四选项：Retry 回 ReBond；Abort 失败计数加一并返回 Abort；Ignore 失败计数加一、抛料但继续收尾；Cancel 抛料、计失败及芯片 Reject，重置 Pick、配置对应的校正动作和 Bond 消息，置 IsRepickComponent 并返回 Retry。
8. 命中 TU 胶印周期时做胶印视觉；之后 WatchFluxCount++、VisionPreviousBondPosition、清持料标记、S2FinishedStep、统计、吸嘴次数、检查贴装上限和刷新UI，最后 Success。进入收尾不证明贴片或检测合格。
9. 同步 try 内异常转 Exception；finally 只置动作 State=Stop 并发 WorkStop。异步弱吹/关真空没有被该同步 catch 等待或统一接管。

## 局部重贴与重新取贴

Retry 返回标签 ReBond，在同一位置重新执行力曲线、清零和 Bond，不重新执行上游定位。Cancel 则调用 SetActionNodeReWork：Pick 必选，AccuracyMode非Off时按 AdjustCamera选 UpLookCorrection 或 SubstrateCameraCorrection，最后加入 Bond；没有在此处自动重置所有可能出现的 DipFlux/其他视觉消息。动作表找不到对应消息时会抛异常；重新取贴不是固定回退一个数组索引。

## 胶印视觉的实际结果转换

DipFluxOnBondPositionVision 先校验胶盘硬件与视觉位置，再拍照并 DipOnTUEpoxyCheck。检查成功时移动回焊点，再调用一次 BondOnTU；检查 Fail 时 SetMatterDisable，**返回 Success**；Abort 直接设置机器状态 Stop并返回Abort；其他异常转Exception。

DipOnTUEpoxyCheck 检查结果列表非空、数量和坐标偏移阈值；人工 OK 取新 AlgResults 并回 Recheck，Ignore 返回 Fail，Abort返回Abort，未知返回抛异常。这里没有统一人工重检次数上限。外层主方法对 Fail 的分支不能代替实际包装语义：当前包装已把检查Fail转换为Success，所以“忽略胶印失败”仍会继续外层步骤处理。

CheckBondedNumber 条件为 AllBondedNumber **大于** BondWarningLimit，而非大于等于。命中时抬Z、Pause、提示；OK只将统计数量清零，该方法没有显式 Resume。

## 源码入口

- [BondActionNode.cs 118–407](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.cs#L118)：主路径、回带、收尾和IsDoWork。
- [452–565](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.cs#L452)：清零、Bond包装、压力记录。
- [Provider 57–143](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.Provider.cs#L57)：准备、胶印视觉与结果转换。
- [Provider 219–360](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.Provider.cs#L219)：阈值检查、贴装上限、异步吹气。
- [S2重做消息](../../trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs#L1099)：按模块、基板、步骤定位并将消息Finished=false。

## 继续核实的范围

已追加下列包装与状态复核。仍未验收：AbsMoveToBondPos/JumpToBondPos完整轨迹、各补偿服务内部算法、统计服务全链路、驱动SDK、实体设备的成功/安全退出和质量结果。


## 补充输入、输出与边界

- CalculateBondPos组合焊点坐标、位置/角度补偿、PostBond与独立焊点偏移；按AccuracyMode与AdjustCamera处理吸嘴/相机补偿，再加TransportUnit补偿、可选参考点及高度。此次核实组合调用，不声称所有补偿算法已验收。[Provider 498–629](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.Provider.cs#L498)。
- MoveToPreBondPos按AbsoluteMove/InterpolationMove分派；距离模式按开关慢下/慢升，力模式调用ForceControlSet/Reset。DryRun实际高度表达式加Z=5，注释写3mm不作为行为依据；移动、延时、抬安全Z、标步骤、刷新后Success。[MoveHelper 151–216](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.MoveHelper.cs#L151)、[367–444](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.MoveHelper.cs#L367)。
- 力曲线读取时机为Pick则Start方法提前返回；否则设置初始力、限定线并启用界面读取。ExportForceData按配置及TransportUnit是否存在决定是否输出；机器日期目录/芯片取贴片受力表/载具名/芯片名+日期+贴片过程力值数据.xlsx，记录时间、芯片、实际取片力和贴片力。[Provider 364–491](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.Provider.cs#L364)。
- 保存xlsx的try内异常提示Retry/Cancel；Retry递归调用ExportForceData，没有此方法内的次数上限；Cancel不保存后返回void，外层继续。目录准备在这个局部try之前，不能说所有导出错误都只提示后忽略。没有证明文件持久化成功才算动作Success。
- SendSignalToSlideFluxer在首次预移动成功后、ReBond之前发出；两点调整仅AllowSlideOut，其余浸胶路径先BondDipFluxFinish再AllowSlideOut；随后更新下一组件IsNeedDip。这是提前交接，不是最终贴片完成信号。[Provider 665–700](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.Provider.cs#L665)。
- VisionPreviousBondPosition是可选人工观察等待，不是配方AfterBondCheck。MachineState.Stop仅清标志并退出该等待，调用者随后仍可执行步骤收尾。[Provider 635–660](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.Provider.cs#L635)。
- S2FinishedStep只把指定步骤字典值置true，SetMatterDisable只修改MatterProductState，均不能单独证明质量合格或整片完成。[BondPosition 177–221](../../trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/BondPosition.cs#L177)。

## 主图关系逐条验收

|关系|类型与成立条件|源码|
|---|---|---|
|prepare→move|条件控制流：普通路径；OffLine/DryCycle走独立返回|DoWork 128–165|
|move→bond|条件控制流：预移动Success后通知/记录再进ReBond|DoWork 165–203|
|bond→check|条件控制流：Bond Success后导出，再判断回带检测条件|DoWork 203–234|
|check→finish|条件控制流：无回带处理或检测条件未开启；不等于检测通过|DoWork 218–310|
|finish→return|顺序控制流：胶印及收尾未提前返回/抛异常才到Success|DoWork 304–364|
|check→choice|条件控制流：启用检测且hasMaterial为true|DoWork 220–243|
|choice→bond|人工操作：Retry跳ReBond，不重新定位|DoWork 245–247|
|choice→repick|人工操作：Cancel重置指定消息并返回Retry|DoWork 263–292|
|choice→throw|人工操作：Ignore计失败并抛料|DoWork 256–260|
|throw→finish|顺序控制流：Ignore分支break后继续胶印与收尾|DoWork 256–364|
|choice→stop|人工操作：Abort计失败返回Abort|DoWork 250–253|

图中的无箭头展开部分由节点详情和此文明确记录：OffLine/DryCycle、预移动/Bond提前返回、胶印检测人工重试和异常、异步弱吹/关真空。图保持主路径可读，不将10节点11关系当作所有方法覆盖。

## 静态风险与后续验收

- 胶印Fail被包装转换为Success、人工观察Stop仍可能继续标步骤，应结合调度及质量记录在测试环境验证业务预期；目前是源码控制流事实，不是已复现事故。
- 文件保存Retry使用递归，应验证持续失败下栈增长和现场文件占用处理；尚无压力测试。
- 完成标记、统计和硬件安全状态需分别验收。禁止用该主图通过代替编译、设备、全部业务覆盖。

## 本轮交付核验

Archify validate/deliver：9项检查通过、0错误0警告。Edge visual-check通过，已目视1440×900浅色截图，节点、标签、恢复关系及卡片无可见遮挡。交付哈希见 bond-action-workflow.delivery.json；自动浏览器凭据见 bond-action-workflow.browser-check.json。自动检查中的visualReview=pending是工具未替人执行审阅的原始字段，保留不改写。统一门户完整交互导航仍未验收。
