# 上视双点、读码与空跑的自动工作步骤

更新：2026-09-28。静态复核 UpLookCorrectionActionNode；不代表视觉算法、坐标精度或实际设备已经验收。

## 流程摘要

DoWork记录下一芯片类型。纠偏关闭、使用BondCamera或离线时提前Success；DryCycle进入独立空跑方法。正常分支先移动到P1上视位置，再执行单点或双点定位。定位完成后，按IsRecognizeQRCode执行读码并保存码值，随后异步关灯、异步条件请求下一芯片，再做温漂补偿。补偿失败可Abort，不能据此撤销已启动的后台通知。

## 实际定位次数

|配置|调用顺序|失败传播与输出|
|---|---|---|
|单点、快速定位|P1一次UpLookVision|非Success直接返回；计算角度和位置偏移|
|单点、非快速|P1 → T轴旋转 → P1再次定位|每次结果非Success直接返回；第二次结果参与偏移计算|
|双点、快速|P1 → 移XY到P2 → P2|每次非Success直接返回；两次结果及实际拍照位置参与偏移计算|
|双点、非快速|P1 → P2 → T轴旋转 → P1 → P2|实际调用四次UpLookVision，后两次结果参与偏移计算；不是仅拍两次|

这只是源码调用顺序；移动函数、图像采集和坐标算法的内部正确性须单独验收。

## 读码条件、失败及输出

DoWork:433–443在定位后调用UpLookVisionByCode(CodeVisionPRPos, CodeVisionPRName, false)。非Success原样返回；Success后写BondPositionInfo.ComponentCode，CodeValue为null时写字符串"0"。此处没有先保护matchResult对象本身为null；异常由DoWork外层catch记录/提示并返回Exception，finally恢复动作状态并触发WorkStop。

UpLookVisionByCode:1617–1843实际步骤：

1. 按名称查PR；不存在提示并返回Exception。
2. SetHardware(name, UpLookCamera) → AdjustVisionDelay → pREntity.DoWork(null,false)。本方法体没有使用传入visionPoint3D做运动，也没有显式移动到CodeVisionPRPos。不能把参数名画成必然存在的读码位移动步骤；SetHardware等被调方法内部行为另核。
3. PR执行非Success或AlgResult.IsSuccess为false时，先考虑自动抛料重取。次数非零且计数未到上限才进入；重读nextComponentName。下一类型为空或不同，条件缩回翻转晶圆顶针、刷新Map、请求当前类型。然后SetLight、ThrowAction、拒收计数增加、将Pick/UpLook及按蘸胶模式选择的Dip节点置为重做，置IsRepickComponent、等待20ms、自动计数增加，返回Retry。
4. 自动重取未进入则计数清零，调用VisionAlarmFunc。Abort返回Abort；Retry执行人工抛料重取并返回Retry；OK将报警返回结果转换为CodeResult并返回Success。人工Retry在配置助焊且定位前蘸胶时补信号：双点只Set BondDipFluxFinish，单点额外Set AllowSlideOut。
5. switch没有default或Ignore分支；若收到其他结果，函数落到尾部，返回Success和强转后的pREntity.AlgResult。这是源码控制流，不代表任何异常结果一定会放行：类型转换、空对象、报警窗口实际返回均有条件。

自动重取发送的是当前类型，正常定位后的后台换型请求发送的是nextComponentName，不能混画。重做节点的调度消费见既有visionroute-rework和bondflow-work证据。

## 报警到界面的连接

InitAction以+=注册VisionAlarmFunc。VisionAlarm锁UiLock，通过Invoke打开FrmVisionAlarm，读取其BaseAlgResult和DialogResult，Dispose窗口，写入AlarmLogEntity数据库记录，ResetAlarm，再返回结果。这段没有本地catch；任一操作抛出时由调用链上层处理。

FrmVisionAlarm.BtSkip_Click写DialogResult.Ignore，证明窗口存在该返回路径；本轮尚未验证它在每一种读码报警配置下的按钮可见性、可用性及事件绑定，因此不宣称读码失败必然可以点击跳过。此项保留为精确缺口。

## 空跑与后台通知

UplookActionDryRun:1979–2042仍会调用移动P1、延时；双点还移动XY到P2并延时。随后Task.Run：下一类型非空且不同、并且不用翻转台时，刷新Map、写下一芯片名、Set需料信号、清两种跳过计数，方法不等待该Task就返回Success。这个路径没有调用UpLookVisionByCode，也没有正常分支后面的温漂补偿。空跑不等于本地无运动模拟。

正常分支的CloseLight也由单独Task.Run启动；它与供晶通知之间只存在启动调用先后，没有等待关系保证执行完成先后。动态component和nextComponentName的共享上下文边界仍见[异步通知专题](async-notification-exception-review.md)。

## 精确源码入口

在[源码阅读器](module-source-explorer.html)搜索uplookextra前缀。以下主体文件均为trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs。

|ID|行号与范围|
|---|---|
|uplookextra-entry|131–162：前置放行和空跑入口|
|uplookextra-single|207–294：单点与快速定位|
|uplookextra-two|295–431：双点与四次定位路径|
|uplookextra-code-call|433–452：读码调用、码值及异步关灯|
|uplookextra-code-auto|1617–1728：读码硬件设置、算法执行、自动重取|
|uplookextra-code-manual|1730–1843：人工报警分支和尾部返回|
|uplookextra-end|484–513：补偿、最终返回及异常/finally|
|uplookextra-dry|1979–2042：空跑及后台请求|
|uplookextra-alarm-register|Main/Controls/Ucmain/MainControls/UcmainSystem.Action.cs:31–38|
|uplookextra-alarm|同上:234–263，UI调用和报警记录|
|uplookextra-skip|Infrastructure/Controls/Currency/FrmVisionAlarm.cs:500–508|
|uplookextra-code-field|TransportUnitSystem/Module/Information/BondPositionInfo.cs:80–83|

## 未完成项

- [ ] 读码PR类型、空结果与类型转换的隔离测试；报警按钮静态门控已在[后续专题](vision-alarm-hardware-review.md)核实，上视相机分支隐藏跳过，现场配置仍待对应。
- [ ] SetHardware名称绑定与CloseLight条件已在后续专题展开；外部硬件效果和并发运行验证仍待完成。
- [ ] ComponentCode在TuService导入/导出的格式、覆盖与持久化全链路。
- [ ] 双点坐标公式及实际运动验证；不得用静态图代替精度验收。
- [ ] 其他视觉节点及通知路径仍未全量覆盖；29模块状态不因此改为完成。
