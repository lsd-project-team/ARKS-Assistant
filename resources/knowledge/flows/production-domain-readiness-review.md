# 启动各域就绪检查：顺序、放行和副作用

更新：2026-09-28。范围：Machine.CheckOperatingEnvironment调用的域级方法；下层SelfCheck、IsReady与运动控制器单列待展开。只做源码分析，没有执行设备操作。

## 总体顺序

Machine.CheckOperatingEnvironment 按晶圆 → S2 → S1 → TU示教 → BP示教 → Process顺序短路，任一false返回。域检查可能已经修改状态或调用硬件包装；false不代表此前无副作用，也不代表自动回滚。调用锚点：startgate-environment；启动外层：startgate-prepare、startgate-launch。

## 晶圆域

证据：ready-wafer-config、ready-wafer-exchange、ready-wafer-state。Machine以默认参数调用，四个bool参数默认为false。

- 进入try后先覆盖任务IsAloneDryCycle/IsRecordSearchData/IsSearchOne，再调用BondZ安全位、Magazine推杆复位、关闭顶针台真空。它们位于!IsOffLineWork判断之前；下层是否屏蔽动作另查。
- 非离线且未屏蔽顶针模组：检查MagazineBoxConfig非空、MagazineBoxGeo非空、料盒示教完成；任一失败提示false。屏蔽顶针只绕过这一组检查，不等于绕过全部晶圆检查。
- 非离线且!isNoJudgeAssistant：遍历独立顶针配置和芯片示教状态；CarrierWithWaferConfig还检查Mapping参考点范围、限位半径、同步顶与力控冲突、Bond搜晶与翻转冲突、纠偏相机只能Bond/UpLook。半径过大弹窗OK继续、Abort拒绝，不是无条件拒绝。
- 同一芯片遍历还检查提前退出力控与Distance模式冲突、与取片后慢升冲突、吸嘴在NozzleList中、蘸胶所需硬件配置、吸嘴架配置；最后已配置翻转但示教未完成返回false。
- 随后IsUseMagazineLift分支在离线判断之外：自动换片模式遇手动片时调用退顶针/扩晶下移/阻挡复位，再询问移除；OK设置CurrentTablet为NullTablet并Save，否则false。无记忆片且层号<=0则JudgeTabletOnWaferTable(false)。
- 手动模式但CurrentLayerNo>0：PlaceWaferInSlot及两项安全位移动；否则无记忆片时判断实际片状态。两种模式都有前后安全位置检查调用。这里仅确认调用，不把方法名当作安全效果证明。
- 按重建标志重建静态华夫盘/料盒/当前片状态、设Good并复位标志；静态华夫盘条件使用单个&，两边都会求值。最终若当前G0位置不在碰撞圆内，调用退顶针和晶圆台准备位，然后true。
- 本方法catch显示异常后返回false；无统一回滚。提示本身异常不包含在这一返回保证内。

## 固晶S2域

证据：ready-s2-checks、ready-s2-tool。

- 先OpenBondHeadVaccum，再检查IsActiveSelfCheck；关闭自检直接true，跳过本方法余下检查和处理。不能解读为“关闭自检时没有输出调用”。
- 启用自检依次委托BondProgram.SelfCheck、ActionNodesService.SelfCheck；再检查ULM点位、焊头点位、启用吸嘴架时的点位。
- 力控配置为空时，仅在遍历到使用力控的芯片时拒绝；温漂/取片补偿各自启用时检查对应定位点；随后CheckToolBankConfiguration为false拒绝。
- 启用吸嘴检测时：物理有而逻辑无直接false；物理无而逻辑有时询问，Yes清空当前吸嘴名，否则false。代码中的ret相等比较不是独立返回条件。
- 记忆焊头有料时用OKCancel弹窗，OK调用ThrowAction；其他返回值没有在此分支返回false。提示文字写No但实际按钮为Cancel，按代码按钮记录。最后S2PreDispenseActionNode.IsAlarm为true拒绝，否则true。
- 本域方法无本地try/catch；异常与正常false应区分，不能套用晶圆catch行为。

## 点胶S1、TU/BP、制程

|检查|拒绝或放行条件|证据|
|---|---|---|
|S1|未配置S1直接true；否则DispenserProgram.IsReady；预点胶非Off时还检查板IsReady、胶型名称非null、胶型在列表存在；最后EpoxyMaterialProgram.IsReady|ready-s1|
|TU|TransportUnitConfig.IsAssistantSucceed为false拒绝；不等于全产品校验|startgate-tu|
|BP|遍历SingleBpPositionConfigList，任一示教未完成拒绝；空列表自然true，未见最少数量检查|ready-bp|
|Process|翻转硬件配置时统计ComponentName不等于字面Null且启用的步骤，超过1拒绝；统计的是步骤数，不是Distinct芯片数|ready-process|
|Process逐步|遍历全部S2步骤，不按IsEnable过滤；名称等于空字符串、Index等于0、焊点名为字面Null或null均拒绝|ready-process|
|Process焊点存在|普通TU要求焊点列表存在；IsOppositeSex分支的存在性检查被注释，不能当作已执行|ready-process|
|Process功能数|ComponentName/DefectName/EpoxyApplicationName分别与字面Null比较，要求恰好一项；不是全面的null/空白有效性检查|ready-process|

本次不把S1委托IsReady、S2 SelfCheck的函数名解释为具体下层检查范围；这些依赖将在后续展开。各域真空、运动和保存行为的结果及回滚仍需控制器与测试环境证据。

## 后续验收

- [ ] 展开S1三个IsReady、S2两个SelfCheck、CheckToolBankConfiguration及预点胶IsAlarm。
- [ ] 建立就绪失败后状态/输出保留矩阵，关联已有Stop与启动重入路径。
- [ ] 结合异常后信号发送/等待，核实并行任务结束条件。
- [ ] 设备或仿真运行验证；静态文档不替代该验收。

## 源码快照

- [ready-wafer-config 159–310](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/WaferSystemDomain.cs#L159) · [阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=ready-wafer-config)
- [ready-wafer-exchange 313–369](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/WaferSystemDomain.cs#L313) · [阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=ready-wafer-exchange)
- [ready-wafer-state 371–412](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/WaferSystemDomain.cs#L371) · [阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=ready-wafer-state)
- [ready-s1 481–528](../../trunk/AKRS.ZX2200/DispenseSystem/Models/System1Domain.cs#L481) · [阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=ready-s1)
- [ready-s2-checks 594–709](../../trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs#L594) · [阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=ready-s2-checks)
- [ready-s2-tool 711–771](../../trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs#L711) · [阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=ready-s2-tool)
- [ready-process 179–252](../../trunk/AKRS.ZX2200/Main/Machine/Process/ProcessDomain.cs#L179) · [阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=ready-process)
- [ready-bp 26–38](../../trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/BondPositionConfig.cs#L26) · [阅读器](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=ready-bp)

## 下层复核更新

[S1/S2委托检查专题](production-readiness-delegates-review.md)已展开上述三个S1 IsReady、BondProgram与动作列表SelfCheck、吸嘴架七槽位检查及S2预点胶IsAlarm。数组Find扩展、S2板实现及运行影响仍明确保留待办。
