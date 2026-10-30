# 料库换片动作与失败处理：源码复核

日期：2026-09-28。范围：trunk 中 WaferSubSystemTask、MagazineController 和 WaferTableController 的料库选层、放回旧料、取出新料及局部传感器处理。本文不修改控制源码，不声称现场安全验证通过。

## 工作步骤摘要

保存当前载具记忆 → 从配置中选择所需晶粒所在层 → 必要时放回旧料 → 顶针归还并准备换片位置 → 移到目标料层 → 按载具配置执行人工或夹片机构取料 → 夹紧载具、更新当前料层与载具记忆 → 料库退安全位、热吹/扩晶、料台到准备位 → 返回换片后的搜晶初始化。外层入口见 [自动换片控制流](carrier-change-review.md)。

## 1. 选层是配置检索，不是传感器扫描

- [PlaceWaferInfo1460–1468](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1460) 在 CurrentLayerNo>0 时，把 CurrentTablet 写回 TabletArray[层号−1] 并保存配置。没有实际放片动作。
- [JudgeNeedChipAtLayerIndex172–210](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/MagazineController.cs#L172) 按索引递增检查 MaxUseLayerCount 范围内配置。仅 Good 料层参与：普通晶圆要求配置存在且名称匹配；适配器要求适配器配置存在，内部某槽位的载具配置存在、名称匹配且槽位 Good。返回首个匹配索引，无匹配返回 −1；不是按物理距离或实时有料状态排序。
- [JudgeNeedChipAtAdapterSlotIndex217–275](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/MagazineController.cs#L217) 先检查所需载具在当前程序列表中；不存在则抛异常。StaticWaffle 使用 CurrentStaticAdapterTablet，其余使用 CurrentTablet；遍历适配器槽位，配置存在、名称匹配且 Good 则返回首个索引，否则 −1。
- [IsManualChangeTabletMode1728–1752](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferTableController.cs#L1728)：Wafer 按自身 TabletChangeType 判断；适配器中任一非空名称的槽位配置为 ManualChange 就返回 true，并非只看本次所需晶粒的那个槽位。

## 2. 放回旧料：PlaceWaferInSlot

[964–1052](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferTableController.cs#L964)：

1. 离线模式仅在层号>0时更新料层记忆、保存、清空当前载具和层号并保存，直接返回。
2. 非离线且当前层号>0：Wafer+热吹配置走“归还顶针 → 扩晶下降 → 夹持气缸落下 → 卸料热吹 → 自动换料位 → SlotScan”；其他配置走 PreChangeTablet，等待料台到位，适配器另落夹持气缸，SlotScan 后等待扩晶下降完成。
3. 手动换片：提示人工塞回槽位；OK 调 JudgeTabletOnWaferTable(false)，Cancel 抛异常。自动换片：料库 Z 按 MagazineLiftDistanceWithClamp 偏移，再 ActionWaferClampPlaceWaferInSlot。
4. 动作路径正常返回后，将 CurrentTablet 写回原层配置并保存，然后 CurrentTablet=NullTablet、CurrentLayerNo=0，再保存设备参数。当前层号为0时本方法不执行以上放料路径。

**准备动作的并行边界：** [PreChangeTablet616–637](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferTableController.cs#L616) 先归还顶针，再分别 BeginInvoke 料台去换料位、扩晶下降（Wafer 时随后落夹持气缸）。调用方通过各自 EndInvoke 汇合；不能画成所有动作严格串行，也不能把发起动作画成已到位。

**夹片放回动作：** [642–718](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferTableController.cs#L642) 在料库未配置时直接返回。其余路径依次松夹、靠近料台、到料台位置；正常工作模式检查夹片传感器有料，失败 Retry 只重复检查，Cancel 抛异常。随后夹紧、移向料库、松夹、再移动，检查夹片传感器不应仍有料；该后置检查没有同样的 IsNormalWork 外层条件。结束时到料库位置、等待取料位并松夹。

## 3. 取新料：RemoveWaferFromSlot

[1059–1192](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferTableController.cs#L1059)：

|条件/阶段|实际行为|
|---|---|
|未配置料库|立即返回，不更新目标载具|
|离线|设置目标层号并保存，再深拷贝配置中的目标载具到 CurrentTablet 并保存；不执行物理抽片|
|当前层号已等于目标层号|立即返回；本方法不再验证当前载具或台面传感器|
|切换料层|先 PlaceWaferInSlot，再 PreChangeTablet，并等待料台和扩晶两个准备动作|
|选择人工/自动|人工时料夹到安全位，否则到等待取料位；随后 SlotScan(targetIndex)|
|人工取片|提示人工把料片移入料台；OK 检查有料，Cancel 抛异常；发起料库退安全位|
|自动取片|若 Push 配置启用，ActionPushCyc；然后 ActionWaferClampRemoveWaferFromSlot|
|更新记忆|抬起夹持气缸；设置目标层号并保存，深拷贝目标载具并再次保存|
|普通晶圆收尾|热吹开启：等待料库退安全位 → 料台到准备位 → 上料热吹 → 扩晶；否则异步扩晶，与料库退安全位汇合后料台到准备位，再等扩晶完成|
|其他载具收尾|等待料库退安全位后料台到准备位|

注意：目标层号和 CurrentTablet 在后续热吹/扩晶收尾之前已保存。若后续动作抛异常，不能把数据库/配置状态解释为整个换片已经成功；本方法没有覆盖整个过程的事务回滚。参数 isOnlyAction 在已读取的整个方法体中未使用，不能据参数名推断跳过数据保存。

## 4. 自动抽片传感器与重试

[ActionWaferClampRemoveWaferFromSlot723–873](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferTableController.cs#L723)：

- 到等待位并松夹，按 IsNeedSlowTravel 选择接近速度和位置。慢速路径始终调用夹片传感器 WaitSignal；非慢速路径只在 IsNormalWork 时调用。参数使用 DelayClampCheckSensor 和 ref isCancelWait。
- 传感器未等到时 StopMove(false)，提示 Retry/Cancel。Retry 回到 WaitSignal 标签，**不重新执行标签之前的移动命令**；Cancel 抛异常。不能把 Retry 画成完整抽片动作重新开始。
- IsNeedRegrip 时按 FirstPullDistance/RegripDistance 二次夹持，否则按料库 Offset 移动；夹紧，必要时慢速退出。
- 正常工作模式向料台接近并发移动指令，再 WaitSignal 等台面有料，使用 DelayWaferTableSensor；失败同样停轴、提示重查或抛异常。其他工作模式直接移动到料台位置。
- 最后 BeginInvoke 料库退安全位，松夹并把料夹移至安全位；外层 RemoveWaferFromSlot 后续 EndInvoke 等待。

上述是调用方传入的超时参数；WaitSignal 和 CheckStateForNums 内部时间单位、取消返回及采样实现尚未在本专题验证。各 Retry 标签没有统一重试次数上限。

## 5. 不能按名称推断的检查与边界

### SlotScan(index) 的后半段不可达

[MagazineController333–395](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/MagazineController.cs#L333) 实际先 MoveMagazineToSlotPosition(index)，接着在357行直接 return。CheckMagazine 调用被注释，本地函数没有在这里被执行；359行后的 SlotScanSensor 判断不可达。因此本调用不能描述为“扫描确认料层有料”。无参 SlotScan 是另一个方法，本结论不扩展到它。

### 人工确认“无料”存在配置相关路径

[JudgeTabletOnWaferTable888–950](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferTableController.cs#L888)：离线直接返回；期望有料时检测不到会反复提示重查或抛异常。期望无料但实际仍有料时，先归还顶针、扩晶下降；**IsUseWaferTableWaffleVacuum=true 分支只有注释，随后可直接返回**。false 分支才落夹持气缸并提示 Retry/Cancel。因此不能声称该方法所有配置下都强制确认无料。此为静态控制流发现，尚未现场复现。

### 料库升降与推料入口

[ActionPushCyc400–405](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/MagazineController.cs#L400) 仅调用推料气缸置位、Sleep(DelayPushHold)、复位；气缸函数内部检测另待核实。[MoveMagazineAxisZToG0Pos420–436](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/MagazineController.cs#L420) 在离线或未配置料库时返回，否则 SingleStep 后检查料台、料夹与推料气缸的升降允许条件。不能由入口有 Check 方法就推断全部安全互锁已验证。

已展开的三个检查为：

- [CheckWaferTableAllowMagazineAction2021–2036](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferTableController.cs#L2021)：料台 Y+range 小于 AutoChangePosition.Y 则提示；OK 调去自动换料位并返回，Abort 抛异常。不是全轴安全区域判断。
- [CheckWaferClampAllowMagazineAction2084–2099](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferTableController.cs#L2084)：料夹 Y+range 小于等待取料位 Y 则提示；OK 调去等待位并返回，Abort 抛异常。
- [CheckWaferPushCylinderAllowMagazineLiftAction481–496](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/MagazineController.cs#L481)：缩回限位传感器检查失败则提示；OK 调气缸复位并返回，Abort 抛异常。

三个 Check 方法本体在恢复动作返回后都没有第二次显式条件检查；恢复动作内部是否等待到位需单独核实。随后 [437–450](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/MagazineController.cs#L437) 根据轴参数、软件速度倍率及坐标转换构造 MovePara，调用 AbsoluteMove；结果不为 Success 则抛异常。AbsoluteMove 参数和完成语义属于下一层，不把返回 Success 直接解释为现场安全验收。

## 6. 气缸完成条件：有传感器与无传感器必须分开

[WaferSubController76–185](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferSubController.cs#L76) 提供两组重载，不能统一画成“驱动气缸并确认到位”：

|重载|执行顺序|返回/失败含义|
|---|---|---|
|SetCyc/ResetCyc(Electric,Sensor,...)|离线返回；SingleStep → delayBefore → 输出 true/false → sensor.WaitSignal(true,timeOut,ref isCancelWait) → delayAfter|等待返回 false 即抛“气缸置位/复位操作超时”异常；无本地 Retry，也无输出回滚；调用方默认 timeOut 数值5000|
|SetCyc/ResetCyc(Electric,...)|离线返回；SingleStep → delayBefore → 输出 true/false → delayAfter|不检查到位传感器，返回只说明这段输出/延时逻辑已返回|

这些是实际调用点对应的重载：

- [夹片气缸 Set418–436](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferTableController.cs#L418)：未配置料库直接返回；正常工作使用 WaferClampPLimitSensor，其余工作模式使用无反馈重载。
- [松夹 Reset441–449](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferTableController.cs#L441)：未配置料库直接返回；否则无反馈重载，仅输出与 DelayClampCycActionAfter。
- [载具夹持气缸454–465](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferTableController.cs#L454)：抬起无反馈；落下使用 BlockCylinderNLimitSensor。
- [推料气缸111–141](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/MagazineController.cs#L111)：IsShieldEjectModule 时直接返回；否则置位使用正限位，复位使用负限位，均走有反馈重载。这里的旁路判断实际是顶针模块屏蔽标志，不能按方法名改写成“推料模块屏蔽”。

无反馈 SetCyc 使用 `electric?.SetOutputValue(true)`；对应 ResetCyc 使用 `electric.SetOutputValue(false)`，空对象处理并不对称。本文记录源码行为，不据此断言现场存在空对象故障。

### 等待参数与单步门控

- Sensor 重载的 `isCancelWait` 是按值传入方法的 bool，再以 ref 传给 WaitSignal。当前气缸调用点未显式传入取消参数，使用默认 false；不能声称它天然绑定整机 Stop。WaferTableController 的另一字段 [isCancelWait57](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferTableController.cs#L57) 用于夹片/台面传感器等待，本轮该文件完整标识符检索仅见声明和三处 ref 传入，未见显式外部停止赋值；WaitSignal 内部可能读写该 ref，尚无源码可确认。
- [SingleStep141–151](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/WaferSystemDomain.cs#L141) 仅当 IsSingleStepWork 为 true 时等待 System2SingleStepSignal.WaitSingleStep；返回 false 抛异常。其他模式直接返回，这不是覆盖后续整个动作的暂停/停止监控。
- Thread.Sleep(delayBefore/delayAfter) 的位置已明确，但 Sensor.WaitSignal 的时间单位、取消行为、轮询间隔不能仅凭默认数值推断。trunk 的 C# 定义检索未找到该方法及 CheckStateForNums 的实现；项目引用了 [LogicHardware程序集281–284](../../trunk/AKRS.ZX2200/AKRS.ZX2200.csproj#L281)，WaferTableModule 将传感器声明为 Sensor 并通过硬件仓库获取：[97](../../trunk/AKRS.ZX2200/WaferSubSystem/Modules/WaferTableModule.cs#L97)、[121](../../trunk/AKRS.ZX2200/WaferSubSystem/Modules/WaferTableModule.cs#L121)。本次停在库调用边界，不编造库内部算法。

## 7. 热吹是输出与定时保持，不是温控闭环证明

[Open/CloseHotBlower579–590](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferTableController.cs#L579) 调用无 Sensor 参数的 SetCyc/ResetCyc。

- [上料595–600](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferTableController.cs#L595)：OpenHotBlower → Sleep(DelayHotBlowerHold) → CloseHotBlower。
- [下料605–611](../../trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferTableController.cs#L605)：同上，关闭后再 Sleep(DelayHotBlowerAfterClose)。

这段链路没有温度达标判断、温度反馈等待或局部重试，也没有 try/finally 保证后续 Close 总会执行。如果 Open 之后到 Close 之前抛异常，该方法没有本地补偿关闭；其他停机路径是否兜底关闭需另查，不能直接判定最终硬件保持开启。上料/下料热吹方法自身无离线提前返回，底层输出重载离线时返回后，外层配置的 Sleep 仍可执行。

[参数声明311–323](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/DeviceParams/WaferTableDevicePara.cs#L311) 默认不开启热吹，保持时间2000、关闭后延时1000；两项界面元数据明确标为 ms，范围0–20000。这些是代码默认值，不是已读取的现场配方值。本轮在 ZX2200 非 Designer C# 中检索 HotBlower，CloseHotBlower 的直接调用仅见上述上下料两处；通用硬件输出清理可能按集合或名称处理，不能以该名称检索替代整个停机链审计。

## 后续验收与源码证据

- 已完成上述方法体外层控制流、配置分支、局部重试、气缸重载及热吹顺序的静态阅读；[停止清理复核](stop-cleanup-review.md) 已补充普通 Stop、EmergencyStop 与退出软件差异，未发现这些入口显式关闭热吹。实际轴运动、运动驱动和 Sensor 库内部、外围停机清理及现场行为仍待验证。
- 异常是否导致整机停止需看调用者；自动生产外层 ChangeTabletAuto 的异常进入供晶 Dowork catch 后 Stop，手动界面调用不能未经追踪套用相同结论。
- 源码快照纳入 [carrier-change-evidence.json](carrier-change-evidence.json)，由统一脚本检查内容和行号；尚未同步该专题图，不宣称动态运行验收完成。
