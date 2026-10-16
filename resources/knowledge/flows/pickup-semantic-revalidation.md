# 取晶动作与漏晶恢复：源码复核

更新：2026-09-28。本轮从 PickActionNode 主入口、Pick 执行包装和 Provider 辅助方法追踪真实控制流；底层运动、视觉 SDK 与现场运行不由本记录证明。

## 实际工作步骤摘要

1. Bond 调度先检查 IsDoWork：焊点 Disable、EnableInSystem1 或无需当前 S2 步骤时跳过。DoWork 的 OffLineWork 在 try 之前直接 Success，既不取料，也不经过该方法的 finally。
2. PrepareBeforePickAction 获取焊点、下一组件名、吸嘴、初始 Z 速度，清跳过标志；首次启动先写芯片名再发需求。翻转的新产品另有刷新地图/发需求分支；DipMode 非 Off 置 IsNeedDip。
3. 判断并换嘴，失败返回 Abort；当前吸嘴为空抛异常。按清嘴配置/累计次数清洁。DryCycle 随后转入 PickActionDryRun，不执行普通漏晶主流程。
4. 普通流程检查取片补偿，false 返回 Abort；取得补偿坐标。NextDie 标签在此之后：重取下一颗不会重做前述换嘴、清嘴和补偿获取。
5. 非补偿工作调用 WaitAllowBondPickSignal。StaticWaffle 调 StaticWaffleVision；Retry 回 NextDie。其余组件若使用 BondCamera，再移动到搜索位置并等待晶圆信号，然后取晶圆角度。
6. 保存芯片角度，CalculatePickPos，PrepareBeforePick，叠加 XY 补偿及按配置抬高预取 Z；取得安全高度并 MoveToPrePickPos。非 Success 返回原结果。然后启动曲线/压力采集，再 CheckBeforePick。
7. 按翻转优先，否则 Wafer 配置类型/其他配置选择 PickType。Repick 标签紧邻 Pick 调用，因此漏晶“重取”复用当前坐标与类型，跳过前面的等待、定位、移动、采集启动和取前检查。
8. Pick 正常返回后计可用次数，再按配置检测漏晶。成功、未启用检测或人工 Ignore 都可进入 IsMaterialOnBondhead=true；此软件标志不能证明实际有料。
9. 异步设置精度相机灯光，WaitStart=false 返回 Abort；否则另起任务通知晶圆预取或翻转取片完成，主方法不 await，随后返回 Success。同步 try 内异常经日志/弹窗转 Exception；finally 仅 State=Stop 并调用 WorkStop 事件，不是统一硬件安全清理。

## 五种漏晶处理

|按钮 / DialogResult|实际动作与跳转|
|---|---|
|重新检测 / Retry|goto ReCheckVacuum；重新判断真空，不重做取料|
|退出 / Abort|返回 Abort，由 BondTask 的显式返回值处理执行 Stop/局部回退|
|忽略 / Ignore|离开处理框继续持料标记及通知，不保证真有芯片|
|重取 / Cancel|goto Repick，仅再次执行 Pick，复用取料位置|
|下一颗 / Yes|ThrowAction 后：直取刷新地图、写当前芯片名并发需求；翻转仅 nextComponentName 为 null 时补发晶圆需求，但总会发 IsBondPickSucceedSignal；置 IsRepickComponent 再 goto NextDie|

未见这些人工重试统一的次数上限。Usable 计数在检测前增加，重取又会经过此处；不能把该计数解释为检测通过的独立芯片数。

## Pick 执行包装

Pick 在补偿工作时直接 Success。普通路径：取得 PickActionParameter → SlowDownToPickLevel → 开吸嘴真空 → 关参数指定的平台真空 → 可选翻转工具吹气 → 记录压力 → Wafer 类型 EjectionLift → 拾取延时 → 关闭界面压力读取 → 非同步顶针条件下 SlowUpToLiftLevel → Success。

Pick 自身当前实现没有正常返回 Abort/Exception 的分支：捕获 NullReferenceException 或其他异常后弹窗并 **throw**，由外层 catch 返回 Exception。因此外层 switch 的 pickRes==Exception 所写顶针准备/吹气不能当作所有 Pick 异常必经路径。外层 switch 没有 default，其他枚举值也可能继续到检测，但本轮已读 Pick 实现的正常返回只有 Success。

## 通知条件与异常边界

SendSignalToWaferTable：下一组件名非空且等于当前名则刷新地图并发当前需求；否则仅 AccuracyMode=Off 时写 nextComponentName 并发需求，这一路没有额外排除 null。其他情况不在此方法发需求。

SendSignalToFlipTable：等待焊头离开翻转台区域才 Set IsBondPickSucceedSignal。Pause 重置计时并 Sleep；超过10秒提示，Ignore 重置计时继续，Abort Stop/return。区域内 Thread.Yield 继续；此 while(true) 未见普通 Stop 状态退出检查，不能声称 Stop 会立即结束该通知任务。

灯光、晶圆通知、翻转通知是未 await 的 Task.Run，异步委托异常不由主方法的同步 try/catch 自动接住。主方法 Success 不证明通知已执行完。

CheckBeforePick：翻转交接位检查、关闭已有吹气、力模式清零，以及请求芯片名与当前芯片名一致性检查；失败可能直接 throw。它位于 Repick 标签之前。

## 源码入口

- [PickActionNode.cs 156–539](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs#L156)：主流程、漏晶选择、同步异常/finally、IsDoWork。
- [PickActionNode.cs 587–727](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs#L587)：Pick 与压力记录。
- [Provider 55–173](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs#L55)：准备、换嘴、清嘴。
- [Provider 571–695](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs#L571)：翻转通知、晶圆预取、设置灯光。
- [Provider 775–806](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs#L775)：取前检查。
- [供晶与等待分支复核](wafer-supply-semantic-revalidation.md)：直取/翻转的条件等待及晶圆生产者。

## 已补齐的辅助分支

StaticWaffleVision 根据 IsMatchWithVacuum 开关真空，移动到由 Block 坐标转换的视觉位置。定位返回 null 时：未达到非零 BlankDieAutoSkipMaxTimes 则刷新地图、请求当前芯片、计跳过并 Retry；超限后计数清零再人工处理，OK 接受结果，Ignore 请求下一颗并 Retry，Abort/其他返回 Abort。源码不能证明“连续空晶计数在每次成功时归零”，成功路径未见该清零。证据：[Provider 180–310](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs#L180)。

BondCamera 延后等待包装先移动至搜索位，成功后置 IsBondArriveSearchPos=true，再等 IsWaferAllowPickSignal；Wait=false 返回 Abort。[318–338](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs#L318)。

MoveToPrePickPos 对非 StaticWaffle 且配置翻转模块的情况检查交接位/回零位；IsRepickComponent=true 用安全 XYZT 移动后清标志；否则按 AbsoluteMove/InterpolationMove 分派。switch 无 default，未知枚举保持初始 Success，不能视为已做运动。插补包装入口检查单步许可与软限位，具体轨迹计算仍待逐行验收。[MoveHelper 61–146](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.MoveHelper.cs#L61)。

DryRun 仍等待允许取晶，并按载具移动模拟位置、回 Z 安全位及 WaitStart；它不调用普通 Pick 或漏晶检测。异步直取请求在“同名非空或 AccuracyMode=Off”条件下均写 **当前 component.Name**，不同于普通路径在精度关闭时写 nextComponentName。翻转通知复制了离区等待/10秒人工续等逻辑。[788–958](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.MoveHelper.cs#L788)。

EjectionLift 同步顶针直接调用 SynchronousEjection；非同步路径可另起 LVDT 采集，再起顶针 Task，按配置提前退出力控，最后 Wait 顶针任务。它等待顶针，不等待 LVDT 文件完成。SlowUpToLiftLevel 根据 Distance/Force、慢速抬升和提前退力控设置分别移动或退出力控，不保证每条分支都有一次显式抬升调用。[Provider 697–769](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs#L697)、[MoveHelper 965–1009](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.MoveHelper.cs#L965)。

## 数据输出与待验证风险

启用 IsActiveSavePickupForce 且非 ETEL、Force 模式时，采集 Task 置 isReadPickupForce=true，再循环读取力值，退出后导出机器日期目录/载具名下的 xlsx。LVDT 由另一个配置启用，使用同一标志循环，在 `D:\顶针顶起过程LVDT值\` 下按配方、日期、载具保存 xlsx，再按阈值提示。两个循环都未见内部 Sleep 或直接机器 Stop 条件。

**静态风险 P1（未复现）：采集生命周期缺少已确认的正常停止链。** 主方法353行的 StopSetBondForceRealTimeCurve 调用被注释；trunk 搜索未找到其活动调用。该方法的异步委托会清标志，但当前没有证据它被正常取晶调用。MoveHelper 328/334 的清标志仅在此前 Jump 运动异常 catch 中，而正常采集在 MoveToPrePickPos 返回后启动。可能出现持续采集、内存增长、文件迟迟不导出或后续任务共享标志干扰，均需受控运行验证；不能宣称故障必然发生。现阶段只登记，不修改控制源码。

证据：[Provider 343–565](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs#L343)、[主方法353](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs#L353)、[Jump catch 326–336](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.MoveHelper.cs#L326)。后续工程师应在非生产环境确认两个保存开关、Force/ETEL分支、正常/异常结束后的任务状态、采样内存与输出文件。

## 十三条图关系的源码依据

|关系|类型与限定|
|---|---|
|prepare-ready|顺序控制流：普通在线路径167–209；OffLine/DryCycle及准备失败已提前分流|
|ready-position|条件控制流：209–266等待成功后定位；StaticWaffle Retry可回NextDie，BondCamera另有延后等待|
|position-pick|条件控制流：266–334，移动/取前检查通过后执行；异常走同步catch|
|pick-check|顺序控制流：334–371；当前Pick正常返回Success，异常重抛而非保证通过switch的Exception回退|
|check-handoff|条件控制流：368–460检测通过或未启用；不能等同物理持料已验证|
|handoff-result|条件控制流：460–502；WaitStart必须通过，Task.Run只提交工作，不等待通知完成|
|check-operator|条件控制流：371–385检测返回false才提示五选项|
|operator-check|人工操作：389–390 Retry回ReCheckVacuum|
|operator-pick|人工操作：398–399 Cancel回Repick，跳过定位和取前检查|
|operator-nextdie|人工操作：402–452 Yes先ThrowAction，再按翻转/直取通知分支处理|
|nextdie-ready|条件控制流：452 goto NextDie；再次等待仍受补偿/相机条件影响|
|operator-handoff|人工操作：395–396 Ignore继续标记持料和通知|
|operator-abort|人工操作：392–393返回Abort，BondTask外层处理；不是这里直接Stop|

## 尚未完成

上述包装与分支已静态复核；轨迹插补计算、CalculatePickPos、PickActionService、视觉/驱动内部和所有硬件响应未全量验收。力值采集风险、线程竞态和配置组合未运行验证。当前图聚合普通在线主路径，OffLine、DryRun、早退及异常范围由节点说明和图卡标明，不宣称覆盖所有下层实现。

## 本轮交付验收

正式规格及HTML哈希已核验，门户节点标签与13条边一致；本记录的本地路径及源码行号已检查。Archify deliver 的9项检查通过（0错误/0警告），Edge visual-check为pass。已实际查看1440×900浅色截图，主路径、五种处理和风险卡未见遮挡；此截图检查不代表所有交互均已测试。

verify-all的13项任务通过，包含证据快照、复核绑定、台账及负例保护。当前登记67/89节点、77/100关系，新增10段证据。完整构建、硬件运行、线程风险复现与门户本轮实际导航仍未验收。
