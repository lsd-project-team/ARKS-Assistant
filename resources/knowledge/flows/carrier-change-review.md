# 自动换片：源码控制流复核

更新：2026-09-28。范围：`WaferSubSystemTask.ChangeTabletAuto`、手动换片窗口的构造/初始化入口、`ChangeSucceedOperation` 完整外层分支，以及部分 Block 状态方法。被调用的视觉、运动和地图方法未全部展开。此文是静态源码分析，不是硬件运行验证。

## 流程摘要

供晶任务发现需要换片后调用 `ChangeTabletAuto`。该方法按 DryCycle、是否使用料库升降机构、载具类型、当前料片及所需晶粒选择复用当前载具、料库换片或人工换片。随后调用 `ChangeSucceedOperation` 初始化当前载具；不同分支初始化失败的重试位置不同。“自动换片”方法包含人工确认，不能等同于全程无人值守。

入口：[WaferSubSystemTask.cs:134–149](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L134)；换片主体：[1105–1366](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1105)。

## 实际分支与顺序

|条件|源码中的动作与返回|证据|
|---|---|---|
|DryCycle|若当前为 WaferTablet，置 Good 并 InitTabletInfo；调用 ChangeSucceedOperation 后返回 true，未检查该调用的 bool 返回值；异常仍可能向上传播|[1107](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1107)|
|所需 CarrierType 为 Wafer|调用的实际接口名是 CloseWaffleVacuum；不按接口名字推测物理意义|[1120](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1120)|
|使用料库，StaticWaffle，当前静态适配器无所需晶粒槽位|打开 FrmChangeStaticAdapterTeach；Abort 返回 false；其他非 OK 结果重开；OK 后初始化失败也重开|[1126](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1126)|
|使用料库，非 StaticWaffle|已有层号时 PlaceWaferInfo，随后按所需晶粒查层号；找不到时允许放回载具、料库移到标记位、人工换料库后重查；取消则抛异常|[1169](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1169)|
|目标是当前适配器/当前料层|符合条件则直接进入初始化；当前层首次判断时，传感器无料会清空 CurrentTablet、层号并保存后重查；有料则夹紧，Wafer 时执行扩膜上移|[1202](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1202)|
|目标在另一料层|依次 PlaceWaferInSlot、RemoveWaferFromSlot(layerIndex)，再初始化|[1236](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1236)|
|料库分支公共初始化|ChangeSucceedOperation 返回 false 则跳回 Operation 再初始化；成功返回 true|[1243](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1243)|
|无料库，当前载具可复用|静态适配器有目标槽位直接初始化；普通 Wafer 要配置存在、名称匹配及 Good，普通适配器要有匹配槽位；后两类还检查有料传感器，无料则进入人工换片|[1252](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1252)|
|无料库，需人工换片|StaticWaffle 使用静态适配器向导，其余构造 FrmChangeTabletTeach；Abort 返回 false，其他非 OK 结果重试；OK 后进入初始化|[1312](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1312)|
|无料库，初始化失败|ChangeSucceedOperation 返回 false 会跳回 ChangeMap，再执行人工换片流程|[1357](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1357)|

## 手动换片窗口确实会显示

调用处仅 `new FrmChangeTabletTeach()`，但构造函数会调用 `InitControl`，而 `InitControl` 内部调用 `this.ShowDialog()`。不能因调用点没有显式 ShowDialog 就判断窗口未打开。

1. [构造函数112–128](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.cs#L112)：料库配置启用时提示并关闭；否则复制当前载具、绑定数据并 InitControl。
2. [InitControl134–180](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.cs#L134)：打开报警，提示操作；取消返回 Abort。随后顶针回位、扩膜下降、按配置处理夹紧气缸、夹具到安全位置、料台到手动换片位。
3. [182–218](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.cs#L182)：按配置关闭真空，提示取旧料；清空并保存 CurrentTablet；提示放新料，确认但无料时重复提示，取消返回 Abort。
4. [221–222](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeTabletTeach.cs#L221)：提示完成向导，再显示模态窗口。

这些是调用顺序；上述设备动作方法内部的互锁、超时和具体轴运动尚未在本专题完成复核。

## 换片后初始化：已确认的边界

- [488–509](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L488)：先 Block.StartInit；静态适配器找到所需且 Good 的槽位后，设置当前载具、槽位状态，重置换片信号，返回 true。
- [518–529](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L518)：普通 Wafer 检查载具配置及匹配/Good，移动相机、设置当前载具、更换顶针；随后进入下面的模式分支。
- [950–983](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L950)：普通适配器检查配置和槽位，符合条件后移动相机、设置载具/槽位状态并重置换片信号。
- [990–993](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L990)：未找到适用载具时提示并返回 false。

## 普通晶圆初始化：模式对照

这里的 Automatic/Manual 是 `AutoRunWithDieMode`，Single/Nine/WaferMap 是另一维度的 `SearchMode`。不能把两个枚举合并成同一“自动/手动”开关。

|运行模式 × 搜索模式|实际执行顺序与退出条件|源码|
|---|---|---|
|Automatic × WaferMap，未准备好|LoadMap(name, true) → 移到参考位置 → MatchResult；匹配成功保存 ReferencePosition，SetReferencePoint1 → FindReferencePoint → MoveToStartPoint → StartAsyncSeekingPath → InitMapInfo → 复位换片信号；可选人工确认起点，Abort 抛异常|[531–578](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L531)|
|Automatic × WaferMap，已准备好|直接复位换片信号，IsNewTablet=false，保存设备参数；不再次执行上述地图初始化链|[660–665](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L660)|
|Automatic × Single|当前位置越界时 InitTabletInfo 并保存；移动到当前位置。DryCycle 直接复位信号；否则只有新料片才打开定位向导，旧料片直接复位信号。此分支的预匹配调用是注释，不是实际步骤|[709–760](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L709)|
|Automatic × Nine|位置越界时重置并保存，移动后实际调用 MatchResult；新料片或匹配失败打开定位向导，否则直接复位信号。此分支没有与 Single 相同的 DryCycle 快捷判断|[762–805](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L762)|
|Manual × WaferMap|位置检查/必要时重置保存 → 移动；地图未准备好则打开 FrmChangeWaferMapTeach；已准备好则复位信号，标记非新料并保存|[812–852](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L812)|
|Manual × Single|位置检查/必要时重置保存 → 移动 → 始终通过 ControlService 打开定位向导|[854–892](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L854)|
|Manual × Nine|位置检查/必要时重置保存 → 移动 → 始终通过 SendUiAction 构造并显示定位向导|[894–929](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L894)|
|其他搜索模式 / ManualAtStart / 其他运行模式|本方法直接抛异常，不能因为枚举存在或 NextDie 可分派，就认定普通晶圆初始化支持它；Box 也没有本表对应分支|[807](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L807)、[931–942](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L931)|

**定位向导返回不等于初始化完成。** Single/Nine 及手动地图分支先检查 `this.IsNeedChange`：判断为 true 且返回 Abort 才抛异常；为 true 但其他结果则重复向导；判断为 false 才标记 IsNewTablet=false 并保存。不能只按 DialogResult.OK 画完成出口。尤其 WaferMap 的判断还涉及参考晶粒列表，不能简化为只检查单个标志，见下文。

**自动地图匹配失败的局部探测：** 启用 IsAroundLocate 时，在原中心失败后依次探测中心的 Y−、Y+、X−、X+ 偏移位置；仍失败则回中心打开定位向导，并重置本轮计数。OK 使用当前 G0 坐标作为新中心，Abort 抛异常，其余结果继续 Retry。未启用环绕定位时，每次失败直接打开定位向导并重试。四个方向不是整个初始化过程的四次总重试上限。[582–656](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L582)

### 已追踪的 Block 状态契约

- [StartInit1193–1203](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.cs#L1193)：先设置首次搜晶、清空空晶计数及提前换片标志，再调用 WaferMap、WaffleMap、Single、Nine 各自的 StartInit。
- [四个子方法1551–1605](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.cs#L1551)：地图对象为空时创建并 Show/Hide；Single 初始化体为空；Nine 重置方向、行号和若干晶粒存在标志，然后 ResetNineDiesData。创建界面不等于加载并准备好地图。
- [ReSetChangeCarrierSignal1292–1296](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.cs#L1292)：同时清除换载具和换载具地图两个标志。
- [SetCurrentCarrier1302–1305](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.cs#L1302)：仅赋值当前载具配置引用，没有在该方法内复制或保存。
- [SetCurrentWafflePlateSlotState1311–1319](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.cs#L1311)：赋值当前槽位并调用 FrmWaffleMap.LoadCarrierMapping；注释中的异步方案不算实际调用。
- [GetCheckPreparedResult1633–1643](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.cs#L1633)：必须同时满足 WaferMapII.CheckPrepared 返回 OK、未置换地图标志。地图文件存在并不等同于这里的准备完成。
- [任务 IsNeedChange1506](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L1506) 调用 [Block.IsNeedChangeCarrier1161–1188](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.cs#L1161)：内部标志为 false 时返回 false；为 true 时，Single/Nine/Box 返回 true，但 WaferMap 只有 pickingRefDieInfo 为 null 或空才返回 true。内部标志仍为 true 且参考晶粒列表非空时，本方法也返回 false。参考晶粒列表的生产与消费尚需另行追踪。

### 人工向导的完成动作

- **定位向导**：[Load296–300](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ComponentsTeach/FrmChangePositionTeach.cs#L296) 调用 InitControl；其 [doneAction99–110](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ComponentsTeach/FrmChangePositionTeach.cs#L99) 检查当前 G0 位置在搜索范围内才复位换片标志并设置 DialogResult.OK，越界仅提示。[DoneOperation180–184](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ComponentsTeach/FrmChangePositionTeach.cs#L180) 在回调正常返回后仍调用 Close，包括越界提示返回的情况；外层可据 IsNeedChange 再次打开向导。这不是“越界就一直留在原窗口”。[按钮244–262](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ComponentsTeach/FrmChangePositionTeach.cs#L244) 捕获并提示异常，finally 恢复按钮。
- **地图向导**：[InitControl113–203](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeWaferMapTeach.cs#L113) 定义四步：提示更换晶圆图（该步 NextAction 为空）→ SetReferencePoint1 → FindReferencePoint → 完成时 MoveToStartPoint、StartAsyncSeekingPath、InitMapInfo、复位信号。不能把第一步提示文字当成自动加载地图调用；[显示地图按钮414–417](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeWaferMapTeach.cs#L414) 调用 ShowMapping，地图内部选择/加载操作仍待追踪。
- 地图向导 [DoneOperation276–280](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeWaferMapTeach.cs#L276) 执行当前步 DoneAction 后关闭；该完成回调没有显式设置 DialogResult.OK。外层依靠 IsNeedChange 判断符合源码。[完成按钮342–360](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ChangeMapTeach/FrmChangeWaferMapTeach.cs#L342) 捕获并提示异常，未在这里直接 Machine.Stop。

## 重试、取消和失败传播

- `ChangeTabletAuto` 的 goto 重试未在该方法内设置统一次数上限、退避延迟或统一 Stop 检查；底层方法是否有这些控制需要分别核实。
- 料库公共 Operation 失败重复初始化；无料库失败回 ChangeMap；料库静态适配器向导分支失败重开向导。三者不能画成同一种重试。
- 调用者对返回 false 写入报警并抛异常：[140–149](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L140)。供晶循环外层捕获异常、提示并调用 Machine.Stop：[375–384](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L375)。
- DryCycle 未检查初始化 bool，不能用返回 true 证明实际换片成功。

## 尚未完成的复核

- PlaceWaferInfo、料层/适配器槽位选择、放旧料/取新料、夹片传感器重试及料库升降允许条件已补充至 [料库换片动作复核](magazine-transfer-review.md)。该文指出 SlotScan(index) 提前返回及无料检查的配置分支，不能把调用名称当作检测完成。
- 气缸有/无反馈重载、热吹输出与定时保持已在料库复核第6–7节展开；扩膜/顶针/相机移动、Sensor及运动驱动内部、停机兜底关闭和现场行为仍待核实。
- 普通 Wafer 初始化外层已读完；LoadMap、参考点定位、异步寻路调用、InitMapInfo 与参考晶粒列表生命周期已补充至 [地图运行复核](wafer-map-runtime-review.md)。地图库内部、ResetNineDiesData、设备底层仍待展开。
- 地图界面内部选择/解析流程仍停在库边界；外层向导完成回调、标志复位和调用方保存已核实。
- [MainForm50–71](../../trunk/AKRS.ZX2200/Main/Controls/MainForm.cs#L50) 已确认 SendUiAction 在构造函数绑定 PostAction，后者直接 this.Invoke(action)，不是异步 Task.Run；运行生命周期和异常表现仍待验证。
- 把上述已确认控制流同步至 Archify 图和逐边语义台账，完成浏览器验收。

## 证据与验收

本专题快照见 [carrier-change-evidence.json](carrier-change-evidence.json)。快照包含文件 SHA-256、行范围和带行号源文；校验只证明源文匹配，不证明运行行为，也不意味着整个初始化函数已完成语义复核。
