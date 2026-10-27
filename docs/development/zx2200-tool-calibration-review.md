# 吸嘴、顶针与三点一线校准：源码复核

覆盖清单 07.01–07.05。核对主页面、示教窗体、System2Controller.AutoCali、取片与上视辅助方法及配置状态。原业务源码保持只读，不执行工具更换或轴运动。本文供 Archify 固定已提交事实，原始文件与行号另由 source-evidence.json 校验。

## 当前入口与组合状态

主页面的三点一线菜单打开 FrmSystem2Calibrate。窗口加载时清 IsWaferCheckSucceed，独立提供吸嘴、单顶针和取片偏移按钮；InitControl 明确将 BtnCaliAll 隐藏并禁用。BtnCaliAll_Click 的处理体全部是注释，历史顺序“顶针→吸嘴→准备取片→取片偏移”不能表示为当前可执行组合。独立入口没有被这个注释块串起来。

依据：UcMainSystem.cs 2098–2103；FrmSystem2Calibrate.cs 74–123、130–183、286–355、362–454、462–579、613–616。

## 吸嘴中心与高度示教

FrmToolAlignmentTeach 两步读取机械 XY，第一步同时记录 NozzleToUplookCenterPos、AlignAngle 并旋转正/负 180 度；第二步圆嘴写 NozzleOffset=(P2-P1)/2，矩形嘴写 RectangleNozzleCornerOffset。两点均值连同当前 Z 转为 RotateCenterPos，设置 ToolAlignment.Able；矩形重置 ToolGeometryAssistant.UnAble。辅助搜索使用圆/矩形模板，定位失败可重试，转为机械目标后 XY 任一差值超过 3mm 拒绝移动。DoneAction 返回后外层 Save 并设 OK，取消没有对象快照回滚。

FrmToolHeightTeach 非离线先 ChangeNozzleAssistance，成功后到 BMC 搜索机械位置上方 8mm；界面文字写约 5mm，执行值按 8mm。手动模式写当前 Z 减 BMC 参考；TD 或真空模式调用 MeasureHeight，只有 Success 更新 MeasureHeightOffset。MeasureHeight 每次先停留 1 秒，参数超时 10 秒，失败可 Retry，取消后保留非成功结果返回；SDK 测高实体契约在引用库边界。外层 BtnDone 无条件设置 ToolHeight.Able、Save 和 OK，因此离线早退、手动轴缺失取消或自动测量失败也不能只凭 OK 认定高度已更新。

Nozzle.IsAssistantSucceed 检查 ToolHeight、ToolAlignment、ToolGeometryAssistant 三个非空状态均非 UnAble；它是配置状态检查，不是本轮传感器结果。FrmNozzleCaliTeach 是重新制作中心 PR 的一步窗口，会更换吸嘴、到原上视位置并按 AlignAngle 转 T，成功定位更新 NozzleToUplookCenterPos；点完成后外层仍调用 Save，即使 DoneAction 因缺模板/定位失败而返回。

依据：FrmToolAlignmentTeach.cs 101–245、251–272、334–371、379–466；FrmToolHeightTeach.cs 101–153、159–234、255–315；Nozzle.cs 223–269；FrmNozzleCaliTeach.cs 100–134、164–208、266–289、323–327；BondHeadController.cs 640–864。

## 吸嘴自动校准

准备检查所选吸嘴存在、示教状态、PR、上视中心位置；重做 PR 时才进入会 ChangeNozzle 的窗口，准备方法没有无条件把当前工具换成所选吸嘴。取消重教直接 false，重教后拒绝开始会去安全位。实际 NozzleCaliAssistance 中自动测高区全部注释，仅执行中心 XY 校准：按 AlignAngle 定位第一次，成功即写 NozzleToUplookCenterPos；按当前角度正负旋转 180 度，用既有旋转偏移修正 XY，再定位第二次，计算两次 G0 结果半差写 NozzleOffset。成功后去安全位并 Save；第二次失败时第一次的对象写入不自动回滚，也没有这条成功尾部保存。第一次提供拍照位置，第二次传 null；第二次虽传 isZSafe=true，但位置为 null 时不进入该参数控制的移动分支。

依据：System2Controller.AutoCali.cs 69–129、389–495；FrmSystem2Calibrate.cs 130–183。

## 单顶针与全部顶针

单顶针准备先排除“翻转硬件配 Bond 相机示教”，检查槽配置、示教、PR 和校准位置；归还吸嘴失败返回 false，随后关顶针台真空、归还顶针、晶圆台到准备位置、检查料片并将顶针台移工作位。重做模板走 FrmEjectionCaliTeach 后直接返回；选择不重教才执行自动方法。准备没有在此处显式 ChangeEjection 到所选槽。

晶圆相机自动路径先 Bond 安全位，再到顶针校准 Z 和相机校准 Z，用 Block 匹配并取 MatchResultToWorld 的首点写偏差。Bond 相机路径另归还吸嘴，用共同视觉结果与机械 (0,0) 通过 CalibService 转换，写 XY、Z=0。两者不混成同一种转换。方法捕获异常转 Exception；finally 先去安全位再 Save，即使 try 返回 Fail/Exception 也进入，若安全移动自身抛出则后续 Save 并非保证执行。

顶针重教 IsShowDialog 当前只返回 true，实际动作在 Load：关真空，按相机选择 Bond 安全位或归还吸嘴/到中心位置，再归还顶针、晶圆台准备、料片检查、ChangeEjection(Index,true)。完成时晶圆分支取世界结果，Bond 分支取像素转 G0 减当前 G0；保存相机 Z/拍照位置、顶针 Z、PRTeach.Able，并归还顶针。外层点完成仍调用 Save，关闭再次归还顶针并到安全位。下拉框显示 EjectionConfig.Name，手动换针却按槽 Name 查找，不把选择文本一致性当成已保证。

GetDistinctEjectionBankSlotConfig 按当前针库及配置存在性收集槽，经 Filter/Distinct 返回。PrepareBeforeAllEjectionsCali 按 EjectionConfig.Name 与列表项 Name 再查找，没有统一空结果保护。AllEjectionsCaliAssistance 标记 Obsolete，当前主工程直接调用检索仅找到声明；先取列表 [0]，每轮校准后访问 [i+1]，最后一轮越界被 catch 转 Exception；空表也在 [0] 失败。旧方法的 finally/Save 全部注释，不宣称全部校准有正常收尾与统一保存。另一个 PrepareBeforeCaliAllEjection 按针库非空槽检查状态，属于实验入口准备，不等同于当前页面的一键功能。

依据：System2Controller.AutoCali.cs 134–338、502–691；FrmSystem2Calibrate.cs 286–355；FrmEjectionCaliTeach.cs 108–143、148–338、385–408、498–535；WaferSystemProgram.cs 272–291；FrmMachineFunctionTest.cs 705–735。

## 取片偏移与工具边界

取片偏移页面先检查物料与绑定吸嘴，可选重教上视模板；准备方法检查 P1 PR、更换吸嘴。CheckIsReady(true) 为 false 时准备方法只 void return，调用者仍继续 Task.Run 校准；成功才缓存 IsWaferCheckSucceed、复位信号、设置需求物料/要料信号并 StartInit。窗口 Load 会清缓存；关闭调用 Machine.Stop，不等同于取消并等待所有任务。

校准按 IsUseFlipTable 选择晶圆或翻转取片，返回 false 则 Fail。普通取片等待供片、计算目标并执行取片和漏晶处理；翻转辅助中的 PickAction 返回值没有在同一位置门控，不能把两条 bool 的成功依据概括成完全一样。上视按 PRVisionAngle+AlignAngle 转 T，并把吸嘴测高偏移加到实际移动位置。单点成功得到 P1，Retry 去安全位后重新取片，其他结果原样返回；辅助上视 Retry 还会刷新图、要料、抛料和置重取标志，非简单原图重拍。

两点分支并未先执行同样的 P1 采样：p1Pos 保持初始化值，移动按 P2 位置计算，却把 P1VisionPos/P1PRName 传给定位辅助，最后 (p1Pos+p2Pos)/2。图谱保留此现实现，不替源码补出缺失采点。成功路径累加 PickupOffset += 吸嘴上视中心-本轮物料中心，再抛料、去安全位、CarrierConfigRepository.Save；后续抛料或移动异常不统一撤销已经累加的对象值。界面 finally 恢复按钮，只有 ret==Success 弹完成提示。

ChangeNozzleAssistance 在工具不同且针架启用/已配置时调用自动更换，否则提示人工确认；Cancel 返回 false，OK 写当前工具名并开真空。PutbackNozzleAssitance 的两个手工分支只在 OK 内做检测/清工具名，但 Cancel 后仍可能更新槽状态并返回 true；不能把 true 当作已验证工具实际归位。具体自动换嘴工艺继续由维护专题展开。

依据：FrmSystem2Calibrate.cs 362–454、586–616；System2Controller.AutoCali.cs 344–382、698–833；System2Controller.Assistant.cs 69–402、410–568、1244–1373、1706–1864。
