# 相机等待分支、视觉重取与下一芯片请求

日期：2026-09-28。静态源码复核；不运行设备，不将源码可达路径当成实机执行结果。承接[供晶握手专题](wafer-pick-ejection-handshake-review.md)。

## 本轮工作步骤摘要

- 非翻转且非静态华夫的 BondCamera 工艺，在通用等待方法不消费供晶许可；PickActionNode 随后调用 MoveToSearchPosAndWaitSignal：移动到搜晶位置成功 → IsBondArriveSearchPos=true → 等 IsWaferAllowPickSignal。
- Block.MatchResult 在启用位置检查且非 WaferCamera 时，先 StopSearch，再等上述标记；标记为 true 后还核对实际 G0 位置，不符则抛异常，符合才进入 PR 执行。该逻辑受离线/空跑直接返回、模板存在及 isCheckBondPos 参数约束。
- StaticWaffle 独立走 StaticWaffleVision：移动、定位；自动跳过或人工 Ignore 会刷新 Map、请求当前类型下一颗，并返回 Retry，让 PickActionNode 回到 NextDie 再等待许可。
- UpLookVision 重取失败片时，请求当前芯片类型并重置 Pick/可选 Dip/UpLook 节点的 Finished 标记；正常上视/中转完成的异步通知，才在下一类型不同且非 null 等条件下请求下一类型。

## 相机等待顺序矩阵

|条件|已核实的当前调用路径|证据|
|---|---|---|
|非翻转 WaferCamera|通用 WaitAllowBondPickSignal 等供晶许可；Block 另检查焊头避让条件|既有 waferflow-wait-policy；visionroute-block-gate|
|非翻转 StaticWaffle|通用等待（含可选换盒避让）→ StaticWaffleVision；静态载体分支优先于后面的 BondCamera 分支|waferflow-wait-policy；visionroute-pick-camera/static|
|非翻转、非 StaticWaffle、BondCamera|通用方法不在此消费许可；后续移动搜晶位，成功才置到位标记、等待许可|visionroute-pick-camera/search-wait|
|非 WaferCamera 的 Block.MatchResult 位置检查|StopSearch → 等标记 → 核实当前位置 → PR执行；循环 Sleep(10)，本层无整体期限|visionroute-block-entry/block-gate/stop-search|
|翻转、补偿或其他枚举组合|通用等待有不同条件；不能套用上面单一路径|见供晶握手专题；其他组合仍需配方可达性核对|

WaferCamera 避让循环超过8秒只记录错误并重启计时；原交互处理被注释，不是8秒自动退出。StopSearch 在 Stop 时先执行可选顶针吹气、延时和回安全位，再抛异常；此方法没有 Pause 分支，也不保证恢复动作不会先失败。

IsBondArriveSearchPos 是静态 bool；本轮具名引用扫描看到定义、ResetInformation 置 false、Pick/Assistant 置 true、Assistant 另一位置置 false。Pick 当前等待函数没有每次调用前清零，Block 消费点也没有清零。只能说明这些代码本身不是每次消费即复位的事件协议，不能据此断言实机必然误放行或遗漏其他并发同步。

## 静态华夫：跳过不是重拍当前片

StaticWaffleVision 定位结果为 null 时：

1. 配置跳过上限非0且计数未达上限：RefreshMap → 设置当前芯片名 → Set需料 → isSkipComponent=true → 计数+1 → Retry。
2. 否则先将跳过计数清零，再调用 VisionAlarmFunc。OK采用返回的 MatchResult；Ignore刷新Map并再次请求当前类型，返回 Retry；Abort及其他返回 Abort。OK没有在本函数再次验证 matchResult 非null。
3. PickActionNode 收到此 Retry 是 goto NextDie：重新执行等待与定位；不经过 BondTask 的动作级 Retry 分支。NextDie 后 AddCountOfTotal 也会再次执行，因此不能将这个计数直接视为成功取片数。
4. isSkipComponent=false 时走 MoveToStaticWaffleVisionPos；为true时按当前Z与目标差是否小于0.01，选择直接XY或安全XYZT移动。自动跳过上限只约束该自动分支，人工重复跳过没有在这里的统一次数上限。

证据：visionroute-static、visionroute-pick-camera。视觉算法和真实Map更新语义仍需下层验证。

## 上视：失败重取当前类型与正常切换必须分开

|情形|请求条件和顺序|后续|
|---|---|---|
|UpLookVision 自动重取|算法返回非Success或AlgResult.IsSuccess=false；计数低于配置且配置非0。重新取nextComponentName；若下一类型为null或不同，必要时翻转Wafer顶针缩回，然后RefreshMap、请求 component.Name|设置灯光、抛料、拒收计数；重置动作节点；IsRepickComponent=true；Sleep(20)；计数+1；返回Retry|
|UpLookVision 人工 Retry|使用已保存nextComponentName做相同 null/不同判断，请求当前类型；这里排除翻转的条件是注释，不能当成有效门控|抛料、按工艺处理蘸胶信号、重置动作节点、标记重取并返回Retry；人工分支不在此递增自动重取计数|
|上视正常路径末段|Task.Run 内：下一类型不同、非null、且非翻转，才刷新Map并请求nextComponentName；复位自动重取/静态跳过计数|启动Task之后还执行温漂补偿；补偿false返回Abort。因此下一类型请求可能已发生，而本节点随后Abort|
|中转台正常路径末段|Task.Run 调用 SendSignalToWaferTable；其条件是下一类型不同且非null，函数本身没有排除翻转条件|发请求后复位两种计数；节点启动Task后直接返回Success，不等待通知完成|

自动/人工重取是否发送请求不只看“定位失败”：若下一类型同当前类型，上述分支不重新Set。不能因此认定漏请求；此前取片通知可能已经请求，需结合整条时序。

正常上视请求先于后续补偿结束的语句顺序已经确认；具体后台任务何时运行、是否完成仍由调度决定，不保证先后。其他视觉辅助/读码/干跑/双点路径不在本表中宣称完全等价。

## 动作重新执行的真实机制

SetActionNodeReWork(List<ActionNode>) 逐项查找同 ActionNodeName、Module、Substrate、ProcessStepName 的记录，找到则 Finished=false，缺失则抛 ActionNode Sort Error。它不是从头重建整个产品流程；若前几项成功、后项查找失败，本方法没有回滚已更改标记。

上视自动重取列表：Pick+UpLook；DipMode=BeforeAccuracyMode 时加入 DipFlux。已核对一点定位调用将非Success结果原样返回 DoWork；结合既有 BondTask 枚举Retry的 continue 和 GetNextActionNode 首个未完成记录选择，形成“重置相关记录→重选节点”的链路。不是简单重拍当前视觉节点。

## 源码证据索引

全部ID为 visionroute- 加表内后缀，已登记[模块源码阅读器](module-source-explorer.html)。路径相对 trunk/AKRS.ZX2200。

|后缀|源码及行号|
|---|---|
|pick-camera|BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs:180–266|
|search-wait|BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs:318–338|
|static|同上 Provider.cs:180–310|
|block-entry|WaferSubSystem/Models/Entities/SearchChip/Block.cs:442–452|
|block-gate|同上 Block.cs:504–574|
|stop-search|同上 Block.cs:1495–1510|
|flag-reset|BondSystem/Models/Parameter/System2RunTimeProvider.cs:190–219|
|up-call|BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs:207–219|
|up-auto|同上 UpLookCorrectionActionNode.cs:1404–1482|
|up-manual|同上 UpLookCorrectionActionNode.cs:1485–1593|
|up-next|同上 UpLookCorrectionActionNode.cs:454–488|
|sub-next|BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.Provider.cs:52–75|
|sub-call|BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.cs:490–514|
|rework|Main/Machine/Process/S2ActionNodeController.cs:1099–1116|

## 尚未闭合

- IsBondArriveSearchPos 辅助流程写入和生产线程的生命周期/竞争；实际配置是否允许所有相机与翻转组合。
- 两点上视、读码视觉、人工辅助和干跑的全部重取分支，仍需分别复核。
- 异步委托读取的 component/nextComponentName 是否在执行前变化；全局未观察任务异常是否触发停止。
- 名称匹配、Map推进、运动到位的下层契约和设备故障注入验证。

补充辅助标记证据：visionroute-assistant-set 对应 System2Controller.Assistant.cs:376–394；visionroute-assistant-reset 对应同文件601–613。
