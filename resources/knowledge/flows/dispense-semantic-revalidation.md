# S1 配方与动作执行源码复核

更新：2026-09-28。范围：DispenseWorkTask 外层执行与 S1ActionNodeController 消息调度；本轮已读取外层调度、八种排序及代表动作；不代表全部动作内部和硬件已验收。

## 已确认主链

1. Start 只检查任务为空或 Status != Running，然后 StartNew(LongRunning, CancellationToken.None) 调用 DoWork；返回 true 不证明动作启动成功。
2. DoWork 先 Init 清空、重排 WorkMessages，再以 Signal.WaitStart 控制外层循环。非 OffLineWork 进入 GetInputSignal；每轮暂停检查后先调用预点胶，再检查停止/来料。
3. 来料 State=Set 时直接赋值 ReSet 后返回。预点胶非 Success 返回 false，调用者移安全位后 return；此路径没有显式 Machine.Stop。未知信号状态 throw，DoWork/StartNew 委托没有统一 catch。
4. Enable=true 才创建/注入产品对象并执行动作；Enable=false 仍可进入安全位、非 Stop 放行及 Finish。
5. GetNextActionNode 找第一条未 Finished 消息，再按 ActionNodeName 查注册动作。未注册也返回 null，与全部完成共用 break 路径；这只是静态分支风险，未证明现场配置触发。
6. IsDoWork=false 直接 FinishCurrentActionNode；否则非四类测高动作且非离线时先收回测高气缸，再 DoWork。该收回调用的结果未被外层检查。
7. Retry 不标记完成而重新取首条未完成消息，未必重做同一动作。其他非 Success 先安全位、Machine.Stop，再 return；未捕获异常不走此返回值分支。
8. 普通收尾移安全位；仅 IsStop=false 才 Set AllowDispenseTransferToBondSignal。Finish 复位 WorkMessages.Finished 和 CurrentActionNodeMessage，不是清空产品对象全部状态。

## 排序与分段

- ProcessSteps 来源是 S1SystemProcess.ProcessSteps 中 IsEnable 项。Init 根据 WorkProcess 与 WorkProcessModule 在四种层级优先×两种排序策略间分派；具体消息顺序见后表。
- Divide 模式按 GetFirstMatrixIndex 分组，实际拼接顺序为 lastActionNodeMessages → InteractiveAction → firstActionNodeMessages；不能按变量名假设 first 组先执行。
- RemoveOtherStep 按异形配置剔除不存在的基板/模块/焊点步骤；本方法不证明所有配置均有效。
- InteractiveAction 在 Divide 且 IsTuInDispense1 时抬 Z、发送移段许可、调用 TransferToDispense2FinishedSignal.Wait；代码没有检查 Wait 返回值，随后设置 IsFirstDispense 并返回 Success。因此不能表述为必定收到到位确认。

## 源码入口

- [任务循环、启动及来料检查](../../trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs#L63)：63–263。
- [排序入口](../../trunk/AKRS.ZX2200/Main/Machine/Process/S1ActionNodeController.cs#L168)：168–287。
- [消息完成与选择](../../trunk/AKRS.ZX2200/Main/Machine/Process/S1ActionNodeController.cs#L749)：749–815。
- [步骤注入及异形过滤](../../trunk/AKRS.ZX2200/Main/Machine/Process/S1ActionNodeController.cs#L859)：859–937。
- [分段交接](../../trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/OtherAction/InteractiveAction.cs#L29)：29–75。
- [预点胶与触发条件](../../trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/OtherAction/PredispenseAction.cs#L74)：74–209。

## 待补齐

剩余：配置持久化、底层控制器/SDK与实际构建及设备验证。定位/识别动作包装及共用方法补充见文末专题。

## 八种排序与映射

所有策略先加入载具前置动作。前置消息不等于动作一定执行，仍受 IsDoWork 门控。

|策略|源码实际顺序|
|---|---|
|TransportFirst + StepFirst（294–350）|全体基板/模块/去重焊点前置完成后，步骤→基板→模块加入工艺动作。|
|TransportFirst + PositionFirst（357–413）|相同前置批次；工艺按基板→模块→步骤。|
|SubstrateFirst + StepFirst（420–466）|每基板先基板及模块前置；焊点前置按动作→去重焊点→模块；工艺按步骤→模块。|
|SubstrateFirst + PositionFirst（473–514）|每基板先基板及模块前置；焊点前置按动作→模块→去重焊点；工艺按模块→步骤。|
|ModuleFirst + StepFirst（521–562）|基板→模块；每模块先模块前置、焊点前置动作→去重焊点，随后全部步骤。|
|ModuleFirst + PositionFirst（568–604）|本源码的消息排列与上一项相同，不按名称推断不同执行顺序。|
|BondPositionFirst + StepFirst（610–651）|本源码的消息排列与 ModuleFirst 两种策略相同。|
|BondPositionFirst + PositionFirst（657–696）|基板→模块→步骤；在各焊点首个步骤前插入其焊点前置，再加入该工艺步骤。|

GetWorkBondPosition（740–743）按 BondPositionName 分组取首项。GetActionNodeMessageByProcess（708–733）先判断 EpoxyNameApplicationName != 字符串 Null 添加点胶；只有 else if DefectName != 字符串 Null 才添加检测。同一配置项不会由此同时生成二者；不是 C# null 判断。

DispenseActionNodes 构造（24–27）调用 Init；System1Domain 属性（66）创建集合。Init（192–235）清空总 ActionNodes 后注册实例，但四个层级集合只 Add 没有 Clear；重复调用是静态风险，未证明现场触发。

## 代表动作与结果

- 点胶（S1DispenseActionNode:46–202）：检查焊点禁用、仅 S2 使用和剩余步骤。离线分支只提前标记步骤，无 return；仍继续单步等待、预点胶、WaitStart、坐标/旋转补偿及 InterpolationApplication。DryCycle 传 isDrip=false，不证明底层全部硬件不动作。成功标记步骤、更新统计，观察模式仍可等待。
- 测高（S1DispenseMeasureActionNode:41–124）：已测高、S1已完成、配置未启用等可跳过。MatterHeightMeasurePoints 返回 Success 才保留成功，其余返回值映射 Abort；异常映射 Exception。离线设 IsMeasureHeight 后仍继续调用测高。
- 检测（S1DispenseDefectActionNode:98–246）：只有 WithoutReferenceSearch 分支执行视觉与判定；其他枚举落到 Success，不能声称所有模式均实现。离线标记步骤后仍继续。
- PostBondEpoxyCheck 返回 Success 时标记步骤；Fail 将焊点 Disable 后返回 Success；Abort 先 Stop；Retry 调用 ReDispense。外层 Success 不是产品合格的同义词。
- ReDispense（190–209）将当前焊点 S1RemainingSteps 所有键置 false，要求点胶和检测消息重做。SetActionNodeReWork（795–815）按动作名、当前基板/模块/步骤 Find 第一条匹配消息置未完成，找不到抛异常。循环下标未用于定位，不能据此声称所有历史消息都重置。
- 所读代表动作 WorkStart 在 try 前，WorkStop/UI 刷新在 finally；这些回调异常不保证转换成返回值。IsDoWork 抛错也不在动作 DoWork 的 catch 内。

## 输入输出与系统边界

输入为启用的配方步骤、排序配置、层级/异形/分段配置、来料信号、模式和产品状态。通过仓库按名称取 EpoxyApplication/PostBondInspection；不是据此推断外部 API。输出为消息完成标志、焊点步骤/禁用状态、统计调用、分段/出料许可、日志和消息框。插补、视觉算法、测高硬件及统计持久化仍需向下追踪。

## 交付状态

新版主图以简短标签重新组织后已通过 Archify showcase 9 项检查（0 错误、0 警告）及 Edge 自动浏览器检查。已查看 1440×900 浅色截图，主线及说明卡未见遮挡；整合页浏览器导航未重做。10 个节点和 12 条关系已完成本文限定外层范围复核并绑定源码，生产源码未修改。

## 补充源码入口

- [八种排序和动作映射](../../trunk/AKRS.ZX2200/Main/Machine/Process/S1ActionNodeController.cs#L294)
- [动作注册](../../trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/DispenseActionNodes.cs#L192)
- [点胶动作](../../trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/DispenseBPAction/S1DispenseActionNode.cs#L46)
- [测高动作](../../trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/DispenseBPAction/S1DispenseMeasureActionNode.cs#L41)
- [检测与重做](../../trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/DispenseBPAction/S1DispenseDefectActionNode.cs#L98)
- [Signal.Wait 停止可返回 false](../../trunk/AKRS.Galaxy2.Machine/Models/Signal.cs#L116)

本章逐行快照与文件 SHA-256 见 [S1 源码证据](dispense-review-evidence.json)。快照验证仅证明源码未漂移，不替代语义和设备验收。

后续复核已补齐其余 11 个动作包装与共用业务方法，见 [定位、测高与识别动作复核](s1-action-behavior-review.md)。此范围不是底层 SDK/设备验收。

## 本章关系验收

图为 Enable=true 的主执行关系，离线跳过等料、Enable=false 绕过动作、未捕获异常等在节点说明与本文列出，不把主图声明为全部代码路径。

|关系|条件与源码位置|
|---|---|
|sort→wait|DoWork 先 Init，再 WaitStart；非 OffLineWork 才 GetInputSignal。任务63–87。|
|wait→inject|GetInputSignal=true 且 Enable；离线绕过等料。任务76–107。|
|inject→next|InjectSteps 后记录统计并进入 WaitStart 动作循环。任务105–119。|
|next→gate|GetNextActionNode 非 null 才 IsDoWork。任务119–127。|
|next→release|返回 null 则 break，可能消息耗尽也可能注册名未匹配；再安全位/条件放行。控制器776–788，任务122–181。|
|gate→work|IsDoWork=true；非测高且非离线先收回气缸，再 DoWork。任务127–149。|
|gate→finish|IsDoWork=false goto Finish，标记消息，不执行动作。任务127–130、164–165。|
|work→result|DoWork 正常返回才能进入结果判断；抛错不是该边。任务149–155。|
|result→finish|返回 Success 落到 Finish；不等同产品合格。任务151–165及检测218–246。|
|finish→next|标记完成后下一轮 WaitStart 通过才重新选择；Stop 可以结束循环。任务117–166。|
|result→next|Retry continue，不先 Finish；检测可重置先前消息。任务151–153、控制器795–815、检测190–209。|
|result→stop|非 Retry 且非 Success，安全位→Stop→return；此前抛异常不保证这条清理链。任务155–161。|

交付回执见 [delivery](dispense-workflow.delivery.json)，浏览器回执见 [visual-check](dispense-workflow.visual-check.json)。二者必须对应同一 HTML 哈希；视觉截图检查不替代所有交互功能验收。
