# 偏移标定与停止：实际覆盖边界

范围：从标定入口追踪普通停止、界面急停、Machine.EmergencyStop 和任务关闭判断。结论来自当前 trunk；未执行设备动作，不证明安全停机性能。

## 工作流摘要

两个标定入口提交独立 Task.Run，且不保存句柄。普通停止调用 Machine.Stop，随后界面通过生产任务清单判断是否恢复。界面“急停”直接遍历轴调用 StopMove，不调用 Machine.EmergencyStop。后者虽定义停轴、Stop 和三个 Abort 调用，但在 trunk C# 的具名检索中未找到调用或方法组注册。三条路径不能画成同一个“标定已取消”节点。

## 入口与实际动作

| 路径 | 源码和执行顺序 | 对标定任务能证明什么 |
| --- | --- | --- |
| 普通停止按钮 | [Designer绑定:716](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.designer.cs#L716)、[2816](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.designer.cs#L2816) → [BtCancel_ItemClick:758–764](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L758)：禁用界面、显示停止提示、调用Stop | 没有等待或取消标定Task的代码 |
| Machine.Stop | [347–378](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L347)：状态Stop、弹窗清理、报警状态、关闭单步、复位需晶、按配置关要料、关顶针真空、清缺陷计数 | 本方法无标定句柄、取消令牌、Join/Wait；不等于标定已结束 |
| 界面“急停” | [Designer:876–883](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.designer.cs#L876) → [1057–1067](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L1057)：取Axis列表，Parallel.ForEach调用StopMove(false,true) | 本处理方法没有Machine.Stop、Machine.EmergencyStop或任务终止调用；底层轴接口语义另行验收 |
| Machine.EmergencyStop | [383–402](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L383)：并行停轴→Stop→点胶Abort→Bond Abort→供晶Abort | 与界面处理方法不同；不包含标定Task。只证明定义内容，不把它当成已证实可达入口 |

普通Stop及三个Abort的依赖实现已有[停止清理审计](stop-cleanup-review.md)，不重复将空方法、Dispose或请求箭头标成成功终止。上述入口没有统一finally确保后续步骤：前面调用抛异常时，不能保证后面的清理或Abort一定执行。

## 界面可用性不是任务终止证明

[ChangeRunningUiState:34–85](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.UIState.cs#L34)把BtEmergencyStop.Enabled设false；[ChangeStopUiState:150–201](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.UIState.cs#L150)设true；[ChangePauseUiState:256–305](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.UIState.cs#L256)设false。这是当前源码赋值，不根据“急停”名称推断它在所有状态均可点击，也不代表实体急停按钮行为。

[ChangeUiByState:382–420](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.UIState.cs#L382)在状态Stop、界面禁用且提示文字匹配时调用IsAllowTaskClosed；返回true后恢复界面。后段按Working/Pause/Stop调用对应UI状态方法。

[IsAllowTaskClosed完整方法:201–262](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.cs#L201)每次重建清单，列入S1点胶（按配置）、供晶、Bond、胶盘、翻转、各段输送及上下料仓任务；只拒绝Status==Running。两个[标定入口](calibration-task-lifecycle-review.md)提交但未保存的Task不在此清单中。故“停止提示消失/界面恢复”不能证明这条标定任务结束；本方法也不是所有Task终态判定。

## 单步模式退出的不同路径

Stop设置IsSingleStepWork=false。下一次进入[System2Domain.WaitSingleStep:777–788](../../trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs#L777)时，若标志已false，则直接返回true，不等待事件。已经进入[Signal.WaitSingleStep:175–196](../../trunk/AKRS.Galaxy2.Machine/Models/Signal.cs#L175)的调用在循环顶部看到false时返回false；若事件已经满足，则退出循环后没有再检查标志。不要把关闭单步统一画成“所有后续动作被拒绝”。

高层安全移动对false/Abort的消费边界已有[安全移动审计与原方法检查](safe-motion-workflow-review.md)：外层拒绝可以void返回，Z包装的返回值未必被上层检查。标定[完整方法:1817–2270](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L1817)本身没有Stop/Pause/取消令牌检查。若子调用正常返回，上层按后续语句继续；若抛异常则走既有catch/结果展示路径。实际是否停止取决于具体子调用及底层设备反馈，不可仅据顶层缺少检查断言机器必然继续运动。

## 已知与未完成

- 已完成：三个软件停止路径区别、普通停止后的界面恢复条件、生产任务清单对本标定入口的覆盖缺口、单步关闭的局部分支。
- 已复用：普通Stop依赖审计、安全移动与信号替身测试；本轮新增内容为静态源码分析，不冒充新设备运行检查。
- 未完成：实体急停链、驱动StopMove实效与参数契约、停止时已在执行的取放/识别/对焦响应、真实权限和线程交叠验收。
- 没有修改生产行为，也没有据此提高模块完整验收数量。工程师应分别验证“停轴调用返回”“任务退出”“界面恢复”，不能相互替代。
