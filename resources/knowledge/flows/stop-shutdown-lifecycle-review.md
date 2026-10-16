# 停止、急停与软件退出的实际边界

更新：2026-09-28。只核对 trunk 中的静态调用和控制流，不运行设备、不修改生产程序。

## 工作流摘要

生产停止与进程退出不是同一完成状态。普通 Stop 首先改设备状态，然后清弹窗、设置停止报警、退出单步、复位需料信号，按配置关闭要料输出，关闭顶针真空并清焊后缺陷计数。此函数没有等待生产任务或后台通知完成。

急停先 Parallel.ForEach 调用轴 StopMove(false,true)，随后调用普通 Stop，再依次调用点胶、固晶、供晶 Abort 方法。固晶方法为空，供晶方法只有注释；点胶方法仅调用 DispenseTask.Dispose()。不能用 Abort 的名称证明取消或等待完成。急停函数没有为这些步骤各自包异常处理；前一步抛异常时，后续调用不保证执行。轴与 Task API 的运行表现未在本轮验证。

## 四条路径

|入口|真实执行顺序及条件|最终状态能证明什么|
|---|---|---|
|Machine.Stop|SetState(Stop) → 清弹窗/报警/单步 → 需料ReSet → 条件关闭要料 → 关顶针真空 → 清缺陷计数|已发起停止状态及这些操作；不证明工作任务或异步通知结束|
|Machine.EmergencyStop|各轴StopMove → Stop → Dispense.AbortThread → Bond.AbortThread → Wafer.AbortWaferSubThread|调用顺序已确认；没有建立全任务Join闭环|
|关闭主窗口|FormClosing 若非IsStop则取消；允许关闭后 FormClosed → ExitSoftware|关闭许可只看此处IsStop；没有在该事件调用IsAllowTaskClosed|
|关机/重启弹窗|关机先Kill当前进程；重启先Process.Start同目录exe再Kill；后面还写有Application.Exit/Environment.Exit|不能把Kill之后的语句或主窗口保存流程视为可靠完成保证；没有操作系统关机命令|

主窗口 FormClosing/FormClosed 在 Designer 中明确绑定。关机按钮处理器打开 FrmShutDown 模态窗口；停止UI分支启用该按钮，暂停分支禁用。其他权限及UI刷新时序沿用既有门控专题，不能声称运行中任意时刻按钮都可用。

## ExitSoftware 的保存与硬件关闭

Machine.Operate.cs:706–739：显示保存提示 → DataSave → 显示关闭硬件提示 → 配置加热时CLoseHeater → 非离线时CloseAllHardware → 关闭启动提示窗 → Environment.Exit(0)。

- CloseAllHardware 有内层空catch；外层也有空catch，之后仍走Environment.Exit(0)。
- 若DataSave或加热关闭抛异常，直接进入外层catch，后面的硬件关闭与提示窗关闭可能被跳过。不能将退出码0当作保存/硬件清理成功证明。
- 方法体没有先调用Stop、等待生产Task、回收通知Task或显式取消后台服务；硬件库内部实现及DataSave内部完整语义不在此断言范围。
- Machine.Sustain 的三个激光干涉尺状态报警分支，在用户选择Abort时直接调用ExitSoftware。因此退出来源不只有主窗口关闭事件；不能把FormClosing的IsStop门控推广到每个调用方。相关检测何时被调度仍需继续追踪。

## “任务已关闭”检查到底检查了什么

Machine.cs:201–262 重新构造WorkTasks：按配置加入点胶，再加入供晶、固晶、助焊、翻转，以及多个输送和料仓任务。foreach仅当 task?.Status == TaskStatus.Running 返回false，其余情况返回true。没有等待，没有检查每个任务IsCompleted，也不保存本轮三类Task.Run通知的句柄。该谓词不是所有任务成功结束的证明。

UIState.cs:382–398 仅在Stop且控件被禁用且提示文字为“设备正在停止，请稍后”时，用该谓词决定恢复控件/隐藏提示，未通过则return。关闭主窗口的事件没有复用这套条件。重启生产时的既有检查仍见启动门控专题。

## 源码证据

在[模块源码阅读器](module-source-explorer.html)搜索以下ID，可查看精确行号与原文，快照绑定文件哈希。路径以trunk/AKRS.ZX2200为根。

|证据ID|位置|
|---|---|
|motion-stop-boundary|Main/Machine/MachineSupport/Machine.Operate.cs:347–402|
|data-window-exit|Main/Controls/MainForm.cs:278–298|
|auth-exit|Main/Machine/MachineSupport/Machine.Operate.cs:706–739|
|dispense-task-start-input|DispenseSystem/Tasks/DispenseWorkTask.cs:189–263|
|bond-task-start|BondSystem/Tasks/BondTask.cs:361–384|
|binwait-taskclosed|Main/Machine/MachineSupport/Machine.cs:201–262|
|shutdown-wafer-abort|WaferSubSystem/Tasks/WaferSubSystemTask.cs:1429–1437|
|shutdown-events|Main/Controls/MainForm.designer.cs:308–309|
|shutdown-process|Main/Controls/FrmShutDown.cs:20–45|
|shutdown-dialog|Main/Controls/Ucmain/MainControls/UcMainSystem.cs:1164–1173|
|shutdown-ui-stop|同目录 UcMainSystem.UIState.cs:147–175|
|shutdown-ui-pause|同上:253–280|
|shutdown-ui-wait|同上:379–398|
|shutdown-sensor-exit|Main/Machine/MachineSupport/Machine.Sustain.cs:358–407|

## 工程师接手与未完成项

- [ ] 展开激光状态检测的调用方、后台循环及停止条件。
- [ ] 补齐其他视觉、双点、读码通知分支及全部共享字段写入者。
- [ ] 确认外部CloseAllHardware与线程服务实现、版本和退出契约；未知实现明确保留缺口。
- [ ] 在隔离测试中验证任务各状态、异常中断、保存失败、退出与并发通知交错；不在生产设备上执行Kill/急停实验。
- [ ] 若授权改造，再设计通知句柄、取消、等待超时、清理失败记录与退出策略。本次只完善源码理解和证据。

本专题不宣称停止必然失效，也不宣称所有资源都已释放。静态事实、潜在后果和运行验证应分别交付。
