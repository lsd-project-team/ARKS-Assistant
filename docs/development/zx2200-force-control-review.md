# ZX2200 力控标定与反馈源码复核

日期：2026-10-27。对应功能图谱清单 30.01–30.06。本记录用于后续阅读页和 Archify 图的来源；它记录当前源码行为，不代表设备动作、压力精度或驱动 SDK 已验收。

主源码根为 `trunk/AKRS.ZX2200/`，以下路径均相对于该根。源码保持只读；原始文件不在 Git 中，后续图引用本记录的固定提交，文件指纹和读取范围另存本地审计结果。

## 01 入口与通讯

- 主界面 `Main/Controls/Ucmain/MainControls/UcMainSystem.Manual.cs:214–223` 打开 `UcBondForceMeasurement`。面板构造时打开焊头真空；四个按钮分别进入标定、平台压力实时图、力值检验、角度初值刷新。`BondSystem/BondForce/Forms/UcBondForceMeasurement.Designer.cs:64–99` 确认按钮与定时器真实绑定，定时器仅按 S1/S2 禁用或启用标定按钮。
- 标定和检验先调用 `ChangeTouchDownAssistance`，取消即返回。标定可先重新示教，再确认开始；拒绝开始时放回吸嘴。`UcBondForceMeasurement.cs:24–95,132–160`。公共工具准备和测高语义复用测高专题，不把逻辑工具名写入当作物理换装完成。
- 示教下一步先到测高位置；确定时用 TD 测高，成功后把当前机械 XY 与测得 Z 转为 G0，写 `BMCDevicePara.ForceCalibratePos` 并保存设备参数，返回 OK。测高失败仅退出该回调，外层 Done 仍递增步骤。`BondSystem/BondForce/Forms/Assistant/FrmCalibrateTeach.cs:70–140,174–214`。
- `ModbusService.ConnectManometer:57–102` 与 `ConnectBondhead:108–155` 离线直接返回 true；在线先保存 RTU 配置，再建立或更新客户端的端口、波特率、校验、站号、停止位和超时后 Connect。串口未授权异常把当前客户端指向另一客户端并返回 true，未再次确认该客户端非空且已连通；其他异常提示并返回 false。
- `BondSystem/BondForce/Modbus/RtuConnectConfig.cs:24–90` 定义配置默认值：平台 COM13、焊头 COM14、站号各 1、9600 波特、None/One、超时 3000、起始地址 33、数量 1。它们是源码默认值，不能作为现场配置结论。
- 两路 Read 在同一个静态锁内设置各自站号，再读取配置指定的保持寄存器，返回原始 int 数组；未在此处转为力值。两路 Reset 设置站号、向地址 94 写入 `[1]`，异常后等待 50ms 重写一次；Reset 没有使用读取所用的锁。Disconnect 直接调用当前客户端。`ModbusService.cs:160–252`。
- 高层读数不全经过 Modbus：`BondSystem/Controllers/System2Controller.cs:1230–1269` 以轴卡 1 的控制器是否为 GTController 分流。GT 焊头为 `Round(ADC/32767*BondheadMaxPress,6)*1000`；平台为 `Round(ADC*CalibrateTableMaxPress,6)*100`。其他驱动取相应寄存器首项 `/10.0`。不能把两种 ADC 公式统一替换成同一比例。

## 02 标定启动与驱动分派

- `FrmCalibrationRelationship.cs:77–113,143–180` 启动前先写入 UI 参数并保存 ForceConfig，检查所选大小力参数表非空；选“仅大力”会清空小力关系表。SavePara 在启动 try 之前，不能把后续 catch 当作它的统一异常处理。界面禁用两个启动按钮，在后台执行闭环标定，正常返回后提示完成，finally 恢复按钮。
- `ClosedLoopCalibrationController.DoWork:95–106`：焊头 Z 轴驱动为 ETELAxis 则 EtelDoWork，其余进入 GTDoWork。这个 else 本身没有证明实际轴一定是 GTAxis。
- 同目录 `VoiceCoilMotorCalibrationController.cs:61–113,118–198` 的 TurnOn 只调用一个仅含注释的转矩方法；TurnOff、DoWork、TorqueMotion 无有效标定动作。`ForceCalibration.cs:19–30` 只是注入控制器后 TurnOn、转调 DoWork 的包装。主程序直接构造/调用名称检索未发现音圈控制器或该包装的实际 new 调用；不能画成当前面板的可执行并列分支。
- `ClosedLoopCalibrationController.PrepareBeforeCali:435–474` 调用两路 Connect 但不检查 bool；Z 先回安全位、XY 到标定 G0 点、再把标定点换成机械坐标。预压高度为 Z+0.2，抬起高度为 Z+8；清除所选范围的旧关系表，最后设置 IsStop=false。
- 停止按钮只设置静态 IsStop=true。窗口关闭清自动检验标志、释放检验窗、放回吸嘴，未在该关闭处理里等待标定任务或设置 IsStop。`FrmCalibrationRelationship.cs:187–203`。

## 03 固高大小力与角度标定

- `GTDoWork:111–206` 先准备、再刷新角度初值。单角模式转到 0°，依所选范围先小力后大力；多角模式分别按大小力角距从 −180° 遍历至 180°，每角采样前检查停止。停止返回和异常都会进入 finally，异常记录后重抛。
- `GTDoWork:218–246` 在 finally 把所选范围的本批局部列表写回关系表，记录耗时，然后 Save，再把 Z 移到安全位。因而停止或异常可能写入部分或空数据；Save 抛错也会使其后的回安全位不执行。这里没有“整批完整才提交”的事务门控。
- `RecordForceInitialValWithAngle:614–659` 每次清空字典，在 −180° 至 180° 每 5° 旋转、等待 500ms、采集 73 个初值。存在值小于 −4 时转到最低值对应角度，清零、再等待 500ms 并重采；最多四轮，第四轮仍不合格则抛错。循环不检查 IsStop。
- 上述采集虽传 `GetBondForceCurrentVal(false)`，GT 实现实际使用静态 channel/maxPress，并不按 bool 即时切换通道；单独刷新或前一阶段留下的通道状态会影响读数口径。刷新按钮仅回模组安全位后调用该方法并提示成功，未在该处理里 Save。`UcBondForceMeasurement.cs:150–160`、`BondHeadController.ForceRelated.cs:65–87,955–964`。
- `CaliForceAtSingleAngle:482–521` 先切通道/配置压力参数，再选对应的起始增量、上界、标定间距和保持延时，按当前 T 角逐点遍历。停止时返回已收集的局部列表。
- 每点先读平台基线，绝对值大于 3 才清零重读；读当前焊头初值 A，同时从角度表选初值 B，以 `B+循环增量` 得输入值。小力输入超过 LVDTMaxInputForce 就退出本角循环。到预压位后以 isUseActualInitial=true 调用 GTForceControlSet，保持后采集。`CaliForceAtSingleAngle:524–583`。
- 样本字段为：InputForce=输入值；CaliTableForce=平台当前值−平台基线；BondHeadForce=大力时的应变片读数，小力填 0；InitialValue=A；ForceIncrement=输入值−A；ZAxisPos=当前机械 Z。ForceIncrement 因而不必等于循环增量。随后以速度 100 设置 Z，再 GTForceControlReset 到抬起位，等待 500ms。`CaliForceAtSingleAngle:586–608`、`Models/ClosedLoopModels/ForceRelateAngleItem.cs:28–58`。

## 04 ETEL 路径与保存条件

- `EtelDoWork:252–349` 仍用共用准备，但未调用角度初值刷新；不按 ForceRange 分开标小力，而是用 LargeForceConfigItemList 和 LargeForceCaliAngleDistance。GetCaliData 按大力最小/最大输入生成列表，输入达到 100 后后续步距减半。`GetCaliData:387–430`。
- 每点清平台、读平台基线和焊头初值；初值小于 0 时清焊头，但不刷新这个已读变量。移动到预压位后直接给 ETEL 输入值/100，目标为 bondLevel−0.01，保持后写平台净力、焊头读数、旧初值及输入−初值，再复位抬起。停止在每个样点开头检查。`EtelDoWork:284–331`。
- 单角分支把角度改为 0，完成本角后先 break，后面的 LargeForceRelationList.Add 未执行；多角才追加本角列表。finally 记录耗时、Save、回安全位，不在这里将 IsStop 改回 true。不能把单角正常返回提示写成已经保存了一套新的 ETEL 单角关系表。`EtelDoWork:334–380`。
- `ClosedLoopCalibrationController.Save:664–751`：有小力/大力表时分别用“各角首点实测力的最大值”作下界、“各角末点实测力的最小值”作上界。两表都有时用小力上界作分界，设备最小力取小力下界、最大力取大力上界；只有大力时分界为 0。两表均空则直接返回。
- 仅小力分支先对空的大力列表执行 Max，再计算小力上下限，这个源路径可能在最后的持久化之前异常；各角存在空采样表时 First/Last 也会先异常。只有到达尾部才写完成时间并依次保存 ForceCalibrationData、BondDevicePara、ForceConfig。
- 路径由 `Infrastructure/Models/Path/ZX2200PathConfig.cs:143–153` 定义：设备目录下 `ForceConfig.json`、`RtuConnectConfig.json`、`ForceCalibrationDataFilePath/ForceCalibrationData.json`。ForceCalibrationData 包含大小力角度表、角度初值字典、耗时和完成时间。`Models/ClosedLoopModels/ForceCalibrationData.cs:18–55`。这些保存不是同一原子操作。

## 05 目标力、输入和反馈换算

- `ForceCalibrationService.JudgeIsSmallForce:380–393`：负值抛错，严格小于 ForceBoundary 为小力，等于分界进入大力。`GetInitialValByAngle:400–406` 选绝对角度差最小项，同距保留先遇项，不作角度插值或环绕距离转换；空字典 Aggregate 会异常。
- `ActualForceToInputForce:35–132`：小力使用传入初值，大力先改用角度字典初值。选对应大小力关系表中最近角度，再以采样列表首尾的 CaliTableForce 作范围检查；未在此处排序。集合 Aggregate 和首尾索引早于“标定未完成”显式检查，空表不保证得到那条提示。
- 目标落在相邻实测力区间时，对 ForceIncrement 作线性插值，输出 `(插值增量+初值)/100`。下一样本的增量为 0 时抛错；只有一条样本时直接返回该样本实测力/100，不加初值。小力还检查结果是否超过小力配置最后一项的 ForceUpperLimit。
- `ForceIncrementToActualForce:207–302` 逆向选择最近角度。空采样列表返回 0，单样本直接返回该样本实测力；多点情况下增量小于 2 返回 0。低于最小增量按首点比例外推，高于最大增量按末两点外推，区间内线性插值。异常记录日志后返回 999，调用者不能把这个返回值当成已验证的有效力。
- `ForceConfig.GetLargeForceConfigItem/GetSmallForceConfigItem:196–259` 先按下界排序，用包含两端的区间选 PID/运动参数；低于全表取首项，高于全表取末项，内部空洞返回 null。`GetForceModelChange:359–372` 以 `输入−(下界−切换下界)` 计算切环阈值再除以 1000。另一个分三段的 GetSmallForceModelChange 有定义，但当前 GT 下压的有效代码使用前者。

## 06 力控设定、退回与清零

- `BondHeadController.ForceRelated.cs:119–158` 的共用设定先查 Z 软限位，再等单步；单步拒绝则 void 返回。ETEL 读取初值、换算后调用 EtelForceControlSet；其余驱动先切通道和参数，再换算×100进入 GTForceControlSet。上层不能仅凭该 void 正常返回断言已经执行了下压。
- `ChangeChannelAndSetForceControlPara:1027–1036` 仅 GTAxis 真正切换；小力选 LVDT.SensorIO/LVDTMaxPress，大力选 ReadBondheadForce.SensorIO/BondheadMaxPress，并写 ADC、压力反馈配置。`GetBondForceCurrentVal:65–87` 的 GT 读数为当前静态通道的 ADC 归一化×量程×1000；`GetLVDTVal:94–108` 独立读 LVDT 通道。`ReadLVDT:946–949` 则是 Sensor.ReadTxPDO，不是同一个读数接口。
- `GTForceControlSet:169–200,610–634` 要求输入值>0、B到C距离>0、慢行距离≥0。默认从角度表取初值，标定专用 true 才取当前值；按输入−初值选择参数项，运动下限为 pos−慢行距离−B到C距离。
- 该方法停止并清理旧指令组，配置 ADC、PID、压力目标与力/转矩限位，启用自动切环，以配置低速下移并等待压力环/压力规划条件。目标压力按输入×32.767/maxPress转换；切环阈值为负会异常。多数 SDK 返回码仅赋给局部变量，不能据此声称每步驱动执行已确认。`GTForceControlSet:222–537`。
- 压入指令流的循环在超过 20 秒的 if 内没有有效退出；运行结束等待超时则停/清指令流，尝试复位到安全位后抛错，catch 再关闭自动切环并重抛。不能把两段等待都概括为可靠的 20 秒上界。`GTForceControlSet:539–601`。
- 共用复位先等单步、再查限位，ETEL 用配置 ForceResetMode 调其接口；其余走 GT 位置环切换、必要时 20ms 后重试、移动及指令/到位等待，再检查实际目标差是否大于 3。GT 复位 catch 只记录而不重抛，finally 关闭自动切环；不能把调用正常返回写成确认成功。`ForceControlReset:851–877`、`GTForceControlReset:641–843`。
- `ResetBondhead:883–940` 按配置选择 Modbus 清零或电信号 true→等待30ms→false。异常后可重试、忽略、终止；递归重试的 bool 未透传，忽略也返回 true，终止调用 Machine.Stop 并返回 false。
- `ZeroBondhead:1072–1134` 先受 IsZeroBondForceBeforeDown 开关控制；ETEL 分支只有注释。其他驱动仅大力且当前读数<−3时尝试清零，持续小于−3最多连续六次，然后提示重试、忽略或抛错终止。它不等于每次取放都对全部通道清零。

## 07 生产取放、末次力值与过程文件

- 普通取片、IPT 取片分别取 PickupForce/Mode 与 IPTPickupForce/Mode；固晶/蘸胶/BMC 与 IPT 放片也各取对应配置。`Models/ActionNodes/Commons/PickActionService.cs:40–112,156–198`、`BondActionService.cs:24–105`。
- 当前 BP 动作节点通过 PickActionService.SlowDownToPickLevel 和 BondActionNode.MoveHelper.SlowDownToBondLevel 调共用 ForceControlSet，目标为当前机械 Z−0.01；带入力值、速度、超时和慢行距离。抬起分支用当前位置+慢抬距离，或原地退力控。`PickActionNode.cs:600–609`、`PickActionService.cs:170–198`、`BondActionNode.MoveHelper.cs:367–443`、`PickActionNode.MoveHelper.cs:965–1008`。BondHeadController.PickAction/BondAction 另有完整动作实现，不能和当前节点实现混写成同一条调用链。
- 取片先 StartSetBondForceRealTimeCurve，再开始可选后台过程采集，随后 CheckBeforePick 中执行清零；固晶也先开启曲线基线再清零。开始曲线时除被另一动作的采集时机过滤外，写当前焊头初值到 System2RunTimeProvider.BondHeadInitialVal，并更新参考线/静态采集开关。该基线早于后续清零。`PickActionNode.cs:304–313`、`PickActionNode.Provider.cs:343–358,775–794`、`BondActionNode.cs:182–203`、`BondActionNode.Provider.cs:364–379`。
- 末次取力记录发生在开吸嘴真空后、顶针顶起和 PickDelay 之前；末次固晶力记录发生在关真空/弱吹相关延时后、退力控抬起之前。仅力模式且非 ETEL 时，把当前值−运行时初值经过逆换算写入 BondPositionInfo.ActualPickForce/ActualBondForce。不是整个过程峰值或稳定段统计。`PickActionNode.cs:616–651,702–725`、`BondActionNode.cs:480–517,541–563`。
- 生产完成的可选汇总导出由 IsExportComponentForceData 与当前 TransportUnit 非空控制，向设备日期目录“芯片取贴片受力表/载具名”下当日芯片工作簿首表追加时间、芯片、末次取力、末次贴力。`BondActionNode.cs:203–212`、`BondActionNode.Provider.cs:403–475`。ETEL 或距离模式跳过本次末次力写入时，导出方法未额外把字段改成新测量结果。
- 另一个 IsActiveSavePickupForce 开关发起非 ETEL、力模式的取片过程后台任务；while中无显式采样延时，直接把当前原始通道值传给 ForceIncrementToActualForce，没有像末次力那样先减基线。其停止依赖 isReadPickupForce；标准节点的 StopSetBondForceRealTimeCurve 调用被注释，其他显式置 false 位于运动异常处理，启动返回的 Task 也未在该节点等待。不能写成正常尾部已可靠停止并完成过程文件。`PickActionNode.Provider.cs:364–472`、`PickActionNode.cs:304–355`、`PickActionNode.MoveHelper.cs:326–336`。

## 08 实时曲线与检测导出

- 主界面分别打开焊头力曲线和 LVDT 曲线；委托将采集开关/参考力转给力曲线静态成员，开关本身不创建窗口。`UcMainSystem.DataAdministrator.cs:145–188`、`UcmainSystem.Action.cs:39–50`。
- 平台实时窗 ConnectManometer 返回 false 即停止初始化；后台读高层平台力、BeginInvoke 显示，循环等待20ms。暂停后重新开始会清当前图点并重置计时；关闭设置 isClose 并等任务结束。`FrmCalibrateTableForceRealtimeLine.cs:72–128,190–220`。
- 力曲线 TestOnCaliTable 模式绘焊头原始通道值、平台当前值及 Z；其他模式先减运行时基线，再按大小力和当前角度逆换算，另绘 Z。可见列表各保留200点。后台循环等待1ms并通过 BeginInvoke 采样，不能称确定的1kHz硬实时采样。`Controls/Manual/FrmForceRealTimeCurve.cs:186–240,247–355`。
- 力曲线导出缓存保存 DateTime 与 force 字段，超过5000条时先快照并清缓存，再异步写 `D:\力控实时曲线yyyy-MM-dd.xlsx`；手动保存写按日号命名的文件。TestOnCaliTable 分支未更新 force 字段，不能把导出列说成两路原始曲线的完整样本；BeginInvoke采样与后台缓存写入也未逐样本同步。清图只清三路可见列表、不清导出缓存；关闭取消任务但不自动导出剩余缓存。`FrmForceRealTimeCurve.cs:289–325,416–506`。
- LVDT 曲线用 GetLVDTVal，显示最多200点，后台等待1ms并异步入图；超过5000条自动快照写当日 LVDT 实时文件，手动写 `D:\LVDT曲线日号.xlsx`。清图、导出缓存和关闭取消同样各自独立。`Controls/Experiment/FrmLVDTRealTimeCurve.cs:93–221,250–323`。
- 曲线共用 `Infrastructure/Service/ExportService.cs:29–104`：打开指定工作簿，加带秒级时间后缀的新表，写字段和行后 Save。写入区异常提示重试/取消，取消后不抛出明确失败；建立工作簿和新表位于该 try 之前。不能把发起异步导出当作文件已成功落盘。
- “力值检验”窗口为给定力和次数反复下压：清平台、读基线、设置测试采集时机、共用设定/保持后取平台净力、记录列表、退力控抬起，再检查停止。正常尾部显示列表极差，没有在此加入与容差比较的合格判定；次数为0会在空列表极差处异常。运行中关闭被取消；异常分支回安全位，但没有统一 finally 停采集。`FrmInspectForceRes.cs:126–170,257–386,483–498`。
- 该窗口手动导出 Number/Input force(g)/Actual force(g) 三列；标定参数窗口的导出则是“小力/大力”两表，写角度、输入、初值、增量、焊头力和平台力。UI扩展名筛选为xls，而实现均使用 ExcelPackage。`FrmInspectForceRes.cs:394–477`、`FrmCalibrationRelationship.cs:210–242`、`ForceCalibrationService.cs:412–550`。

## 09 诊断补充与尚未进入正式专题的工作

- 主界面诊断以及“标定并检验”可打开 FrmBondheadTest；组合按钮后台先标定，再 BeginInvoke 打开自动启动检验窗，UI线程同步 task.Wait，不能把它描述成已等待检验窗完成。`UcMainSystem.Diagnosis.cs:199–203`、`FrmCalibrationRelationship.cs:250–329`。
- FrmBondheadTest 的主 Start 遍历目标力和 −180°至180°角度，记录保持前/后平台净力、焊头值、Z、输入和退回后读数；超500条、停止或总小时数到达时追加写 `D:\焊头力控稳定性测试数据.xlsx`。计时器在设定下压后、保持延时前就停止，虽然列标题写“下压到抬起”，该列不能按标题解释为完整周期。`FrmBondheadTest.cs:177–258,263–488,1000–1102`。
- 另外三个已绑按钮分别是定角定力循环、定角变力循环、−360°至360°每5°读数/计时循环。定角变力旋转使用 SpAngle3 而保存角度使用 SpAngle；定角定力部分 Modbus 读数用整数 `/10`；第四种计时里的 ResetBondhead 调用被注释，所记 resetTime 不是清零耗时。`FrmBondheadTest.cs:494–794,1239–1365` 及 Designer 的四个 Click 绑定。
- 主界面的 GT 调试窗另有直接 GTForceControlSet 循环，并开启力与 LVDT 曲线，输入是模拟量而非共用换算后的目标g力。`Controls/Experiment/FrmGTForceTest.cs:471–568`。`FrmForceControlInspection` 还有同窗力/LVDT读取实现，但未检出主程序直接 new 调用，不把它并为标准检验入口。`FrmForceControlInspection.cs:177–220`。
- 本轮先固定源事实与边界。后续仍须制作完整专题、读数/保存对照、实际 Archify 图、逐项绑定及浏览器验收，完成前不将30.01–30.06改为已复核；原45专题、241条范围继续有效。

本轮读取范围涉及37个主程序文件，全部列入当前工程1,137个Compile项；对照原基线复算1,157个C#文件，指纹全部一致。读取范围、文件指纹、编译归属以及入口/动作检索结果保存在 `output/functional-atlas/force-control-source-audit.json` 和同前缀检索文件。本轮属于静态源码复核，尚未新增正式专题，也未执行设备程序、SDK动作或精度验收。
