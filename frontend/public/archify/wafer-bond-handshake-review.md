# 供晶、取晶与翻转台握手复核

2026-09-28；静态源码复核，不代表现场线程时序或运动验证。以下为主握手范围，未把所有取晶动作、换片算法视为已完成。

## 流程摘要

PickActionNode 首次准备时先写入需要的芯片名，再发需料信号。供晶任务消费请求，按芯片名找配置，必要时换片并调用 NextDie；成功路径复位需料信号、发布允许取料。直取由 Bond 侧按相机/载体配置等待该信号；翻转路径由 FlipTask 先消费晶圆就绪，完成翻转后向 Bond 发布翻转台就绪，并等待 Bond 取走确认。后续需料可异步提前发出，不能把每颗芯片画成完全串行的全机流程。

## 调用和信号证据

|步骤|实际条件和行为|源码|
|---|---|---|
|取晶入口|OffLineWork 直接 Success；否则调用准备方法；DryCycle 转空跑取晶；正常路径非补偿模式调用 WaitAllowBondPickSignal|[PickActionNode:156](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs#L156)|
|首次需料|IsBondTaskFirstStart 时 SetCurrentNeedChipName(component.Name)，Set IsBondNeedChipSignal，再清首次/新产品标志；后续翻转且新产品分支也会请求|[PrepareBeforePickAction:55](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs#L55)|
|供晶接收|while WaitStart 内 Wait IsBondNeedChipSignal；失败跳回循环之前，重新检查状态；独立空跑可自己发需料|[WaferSubSystemTask:64](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L64)|
|芯片配置与换片|所需芯片不在 GetCarriers 中则抛异常；NullTablet 或芯片名变化置换片信号；IsNeedChange 时 ChangeTabletAuto，失败写报警并抛异常|[WaferSubSystemTask:115](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L115)|
|搜晶|调用 Block.NextDie；失败后依换片标志、WaferMap、空跑及人工选点结果跳转；不满足处理路径则抛搜晶失败|[WaferSubSystemTask:161](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L161)|
|晶圆就绪|真空配置分支处理后 ReSet 需料，再 Set IsWaferAllowPickSignal；该循环中没有等待 IsBondPickSucceedSignal|[WaferSubSystemTask:258](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L258)|
|直取等待|非翻转：静态华夫盒避让配置走 Wait(100) 循环，必要时移避让位并 Pause；否则 WaferCamera 或 StaticWaffle 等晶圆就绪；BondCamera 的普通载体在搜晶位另等该信号|[WaitAllowBondPickSignal:337](../../trunk/AKRS.ZX2200/BondSystem/Models/Parameter/System2RunTimeProvider.cs#L337)、[搜晶位等待:318](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs#L318)、[调用:249](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs#L249)|
|翻转取片|当前 component 为 null 时循环等候；IsUseFlipTable 且翻转吸嘴无片时等晶圆就绪，再调用 FlipChipAction / FlipChipActionDryRun|[FlipTask:62](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/FlipTask.cs#L62)|
|提前需料|传给翻转动作的 notifyWafer 回调会另起任务，角度超过 SearchComponentAvoidancePos 且存在下一颗时刷新 Map，写 component.Name 并请求；这里不是写 nextComponentName|[FlipTask:107](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/FlipTask.cs#L107)|
|翻转交接|成功置 IsComponentOnFlipTool=true；发布 IsFlipTableAllowPickSignal，然后 Wait IsBondPickSucceedSignal；Bond 等待方法的翻转分支消费前者|[FlipTask:202](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/FlipTask.cs#L202)、[Bond 等待:386](../../trunk/AKRS.ZX2200/BondSystem/Models/Parameter/System2RunTimeProvider.cs#L386)|
|取晶后分支|WaitStart 通过后，非翻转异步调用 SendSignalToWaferTable（非补偿）；翻转异步调用 SendSignalToFlipTable；DoWork 可在异步信号实际发出之前返回 Success|[PickActionNode:470](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs#L470)|
|直取下一颗|同名且下一颗非 null：RefreshMap、写当前名、发需料；否则 AccuracyMode.Off 分支写下一颗名并发需料；其他精度模式换芯片请求仍需追上视/中转逻辑|[SendSignalToWaferTable:633](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs#L633)|
|翻转取走确认|SendSignalToFlipTable 等待 Bond 离开翻转台范围后 Set IsBondPickSucceedSignal；10 秒提示可忽略重置计时或终止 Stop|[SendSignalToFlipTable:571](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs#L571)|

## 失败、重试和停止的边界

- 供晶 Dowork 外层 catch 显示错误并调用 Machine.Stop；IsSearchOne 在发送就绪后也调用 Stop。[375](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L375)、[369](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L369)。
- FlipTask 的 FlipChipAction 返回 Exception/Abort 时，Wafer 类型先缩回顶针，然后直接 return；这些分支未显式调用 Stop。NoStart 跳回 NextDie 再等晶圆就绪。不能把“设备停止”注释当成实际 Stop。[202](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/FlipTask.cs#L202)。
- FlipTask 正常退出 while 后才调用 FlipTableGoHome；内部提前 return 不经过这句。[239](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/FlipTask.cs#L239)。是否有底层复位不能由本方法判断。
- 翻转提前需料的异步循环超过 10 秒提示：Ignore 重启计时，Abort 调 Stop；循环也检查停止。不是固定重试次数，也不是 10 秒必然终止。[151](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/FlipTask.cs#L151)。
- PickActionNode 的同步 catch 返回 Exception；不能据此断言其 Task.Run 回调异常也会被该 catch 捕获。[504](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs#L504)。
- IsBondNeedChipSignal 为 ManualReset；晶圆就绪、翻转就绪、取走确认是 AutoReset。[SignalPool:136](../../trunk/AKRS.Galaxy2.Machine/Models/SignalPool.cs#L136)。因此需料保持到显式复位，不能当作每次请求都有独立排队记录。
- Wait(100) 的 outTime 参数未用于底层等待，实际使用 recycleTime；已有框架复核结论仍适用，不能根据实参直接声称准确的 100 ms 超时契约。[Signal:153](../../trunk/AKRS.Galaxy2.Machine/Models/Signal.cs#L153)。

## 仍需追踪

Block.NextDie / ChangeTabletAuto 内部；FlipChipAction 何时调用 notifyWafer；其他发需料位置的分支（上视、重取、手动和标定）；IsComponentOnFlipTool 清除时机；全部载体/相机组合的互斥条件。当前记录支持主握手分支，不证明所有配置组合可达且正确。

## 搜晶入口与单颗搜索展开（2026-09-28）

`Block.NextDie()` 按 **SearchMode** 分派，而不是直接按 CarrierType 分派：Single→SearchSingle、Nine→SearchNine、WaferMap→SearchMapping、Box→SearchDieBox；其他值抛异常。载体配置如何赋给 SearchMode 仍需追踪，不能按类型名称猜映射。[Block.cs:335](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.cs#L335)。

本次已展开 Single 分支：[SearchSingle:35](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.SearchSingle.cs#L35)。

1. 调 GetNextPosition(isOffset)，随后将局部 isOffset 设为 false。
2. 若位置为 null 或提前换片标志置位，清提前换片标志、置 isNeedChangeCarrier、将当前槽位标为 Bad、调用异步保存，并返回 false（48–56）。因此 false 可以表达“需要换料”，不等于单一的视觉故障。
3. 只有 IsPositionSearch 且 PositionSearchMode==StandardSearch 进入已实现定位分支；MultipleSearch、其他模式或关闭 IsPositionSearch 均抛异常（59–149），不能把枚举存在当成模式已实现。
4. 两点定位依次移动并 AnalyseDie；未跳过时合成角度并移动到两点中心，跳过时回当前芯片位置；单点则移动后 AnalyseDie（63–135）。视觉底层成功判定尚未展开。
5. 调 StopSearch 后，isSkip 为 true 则再次循环取位置；该方法未声明次数上限。循环结束调用 MoveDieToPickCenter，随后返回 true（152–162）。StopSearch 的具体停止检查待追踪，不能按名字断言取消机制。

结果回到 WaferSubSystemTask.Dowork 的 NextDie 判断：false 且需要换片时进入已记录的换片/人工选点分支；不能处理则抛搜晶失败，外层 catch 调 Stop。true 后继续真空配置与发布晶圆就绪。[调用方:161](../../trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs#L161)。

待补：GetNextPosition、AnalyseDie、StopSearch、MoveDieToPickCenter；Nine/Mapping/Box 的完整方法体与配置赋值；ChangeTabletAuto 内部分支。本节只确认分派和 Single 外层控制流。

## 单颗搜索的位置生成与停止语义

已读取 GetNextPosition 全方法（174–389）。首次搜索直接使用晶圆台当前 G0 位置，并按配置行列间距及跳行/跳列数计算步距，按搜索方向调整符号；此首次返回分支没有调用 IsInSearchRange。后续从当前位置（按 isOffset 决定是否减取片偏移）沿行/列推进，越界时换行/列并探测或反向找有效点，成功后改变方向，失败返回 null。[位置生成:174](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.SearchSingle.cs#L174)。

探测和反向寻找的各个 for 循环受 retryTimes 限制，字段初值为 50；这约束几何候选点探测，不是“视觉失败最多重试 50 次”，也不是整个 SearchSingle 的循环上限。[字段:499](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.SearchSingle.cs#L499)。返回 null 后，SearchSingle 会标记需要换料并返回 false，接入上层换片分支。

StopSearch 并不发起 Machine.Stop：它检查是否已经处于 Stop。若已停止且 isNeedEjectZero=true，则开顶针台吹气、延时、关吹气、移动顶针到安全位，之后抛出“搜晶过程中设备已停止”异常；未停止直接返回。该方法没有 Pause 等待。[StopSearch:1495](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.cs#L1495)。此异常可沿 SearchSingle→NextDie→供晶 Dowork 到达其外层 catch；不能将其画为独立的后台取消线程。

MoveDieToPickCenter 会清空空晶计数，记录 matchResult.Angle，取两点中心或视觉 Mark 中心。对于 Single 所在的非 Box 路径，它设置当前位置记忆，并调用 MoveWaferTableToG0PosWithSearch(中心+取片偏移)。Nine 另有中心对准及 CalculateDiesPosition；Box 的 StaticWaffle 分支不执行该段晶圆台移动。[方法:1045](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.cs#L1045)。具体坐标变换和运动完成判定尚未展开。

SearchMode 与 PositionSearchMode 属性直接读取 currentCarrierConfig，对应配置对象的初始化/切换仍待核实。[配置读取:1706](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.cs#L1706)。此前“GetNextPosition、StopSearch、MoveDieToPickCenter 待展开”现已推进至上述方法体范围；视觉 AnalyseDie、其他搜索模式和自动换片仍未完成。

## 视觉判定 AnalyseDie 的实际分支

已读取 [AnalyseDie:78–317](../../trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.cs#L78)。该方法同时返回 MatchResult 和 out isSkip，不能仅凭返回对象非空判断可取晶。

|条件|动作与返回|源码位置|
|---|---|---|
|基础定位|MatchResult(template)；启用框架定位时另调 MatchFrameResult，两者成功才通过，并计算 FrameOffset；未启用则清零偏移|87–111|
|定位成功、有墨点、非跳板晶片|自动跳过，或人工 OK 保留 / Ignore 跳过 / Abort 抛异常；跳过会增加墨点及总数计数、清空空晶计数，返回 CameraCenterPixel 且 isSkip=true|118–155|
|启用多次定位、非跳板晶片|ToRequiredAccuracy 失败后人工 Retry 回到多次定位标签；Ignore 标记跳过；返回此次定位结果。不是直接重启整个供晶任务|191–214|
|定位失败、允许自动跳过且未到阈值|空晶计数加一、isSkip=true，返回 CameraCenterPixel|221、308–315|
|达到报警条件且启用提前到末端、Single 模式|未到三倍阈值时继续跳过；恰到第一阈值先 AheadReachEnd，再回 RetryAnalyseDie 重新定位|227–245|
|定位失败、进入人工处理|OK 检查选点范围（非 Box）后重新定位；Cancel 也重新定位；Abort 抛异常；Retry 设置提前换片标志及 isSkip；Ignore 清空空晶计数并跳过|249–298|
|定位失败且是跳板晶片|清空空晶计数，isSkip=true，返回 CameraCenterPixel|300–305|

尤其要注意：这里 **DialogResult.Retry 表示提前换片，Cancel 表示重新定位**，不能按按钮结果名推断执行含义。提前换片标志会在 SearchSingle 下一轮被处理为换片返回 false；人工 Ignore 和自动跳过则经 isSkip 进入下一轮位置搜索。

这些人工 Retry/Cancel 回跳在此方法中没有总次数上限。底层 MatchResult、MatchFrameResult、BlobResult、ToRequiredAccuracy 及 VisionAlarmFunc 的算法/界面契约仍需独立展开。本节验证了调用后分支，不声称视觉算法或全部配置已验收。
