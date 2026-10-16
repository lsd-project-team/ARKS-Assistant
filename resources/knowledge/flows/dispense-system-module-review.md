# ZX2200/DispenseSystem：准备检查、预点胶与生产循环

2026-09-28。部分复核。与既有[点胶主流程专题](dispense-semantic-revalidation.md)共同阅读；本轮补模块入口和直接准备检查，不声称已覆盖所有胶路、胶型、视觉和运动实现。

## 真实执行顺序

1. System1Domain.CheckIsReady在未配置System1时直接true；否则检查点胶头。启用预点胶才检查预点胶板、胶型名非null及胶型列表命中，最后检查胶材。[481–528](../../trunk/AKRS.ZX2200/DispenseSystem/Models/System1Domain.cs#L481)。
2. DispenseWorkTask.DoWork先Init动作控制器，再WaitStart；回安全位，非离线模式调用GetInputSignal。后者先处理Pause，再执行PreDispenseAction；非Success返回false；之后才检查Stop/Pause和来料信号，并将Set直接改为ReSet后返回true。因此不能把预点胶描述为来料后才执行。[63–89](../../trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs#L63)；[221–263](../../trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs#L221)。
3. Enable时若TU不是IsProduct就重新构造System1载具并置IsProduct，注入步骤，开始循环。动作IsDoWork=false也会走FinishCurrentActionNode；Retry重取动作；其他非Success先回安全位、Stop并return。没有包住DoWork全过程的try/finally。[91–166](../../trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs#L91)。
4. 正常离开内循环或Enable=false后回安全位，仅非Stop时发AllowDispenseTransferToBondSignal，随后Finish。发信号不证明物理搬运完成。[169–182](../../trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs#L169)。

Start创建LongRunning任务后直接true；AbortThread只是调用DispenseTask.Dispose，没有该方法内的取消令牌、null保护或设备停止调用。不把方法名等同于已经终止工作。[189–215](../../trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs#L189)。

## 尚未完成

- BeforeEveryDispense时机的实际效果、底层IO/设备驱动和挤胶异常后的硬件状态仍待验证；本轮已补坐标分配、检测返回及控制器/模块包装。
- 胶型/胶材实际存储、视觉与测高、下层运动轨迹、断胶和胶量控制及硬件验证。

## 准备检查的实际范围

### 已补深：预点胶板索引和检测返回

InitPre按Rows×Columns创建点阵，X沿列、Y沿行从起止点计算间距，Z统一使用起点Z；Index清零并Save。GetEpoxy按列优先取点（column=Index/Rows、row=Index-column×Rows），先Index++再取数组项并Save，返回的点尚未执行点胶。GetEpoxy(count)先循环分配整批位置；之后的运动或检测失败没有该方法内的索引回滚。因此“预留位置/索引已保存”不能当作“该位置已成功点胶”。[PreDispensePlateProgram55–193](../../trunk/AKRS.ZX2200/DispenseSystem/Models/Programs/PreDispensePlateProgram.cs#L55)。

板满判断使用Index==EpoxyArea.Length：DryCycle重建，其他模式要求人工确认清洁，否则抛异常；行列改变也要求确认。代码未在这里校验行列正值或Index超过Length的情形，也未见本地失败回滚。零维或损坏索引的运行结果需配置测试，不能从AssistanceFinish推断其安全性。[98–168](../../trunk/AKRS.ZX2200/DispenseSystem/Models/Programs/PreDispensePlateProgram.cs#L98)。

CheckEpoxyApplication转换相机位置，调用DispenseVisionDefect，再将返回列表和null焊点传给PostBondEpoxyCheck并返回ExcuteResult；但上层PreDispenseAction.DoWork调用它时未保存或判断这个返回值，随后可更新时间并返回Success。抛出的异常仍进入DoWork的catch。这里必须区分“返回失败码未传播”与“抛异常”。[检测287–297](../../trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/OtherAction/PredispenseAction.cs#L287)；[调用132–162](../../trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/OtherAction/PredispenseAction.cs#L132)。

DispenserProgram.IsReady按名称查仓库，要求对象存在且IsAssistantSucceed；EpoxyMaterialProgram.IsReady只要求仓库对象非null，没有在该方法检查保质期、剩余量或压力。PreDispensePlateProgram.IsReady直接返回设备参数AssistanceFinish。[点胶头25–80](../../trunk/AKRS.ZX2200/DispenseSystem/Models/Programs/DispenserProgram.cs#L25)；[胶材20–65](../../trunk/AKRS.ZX2200/DispenseSystem/Models/Programs/EpoxyMaterialProgram.cs#L20)；[预点胶板200–203](../../trunk/AKRS.ZX2200/DispenseSystem/Models/Programs/PreDispensePlateProgram.cs#L200)。这些条件不等于完整胶路可用性验证。

## 预点胶不是独立定时任务

除GetInputSignal轮询调用外，S1DispenseActionNode也在生产点胶前调用PreDispenseAction，非Success转换为Alarm，再通过WaitStart检查是否继续。[生产入口75–85](../../trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/DispenseBPAction/S1DispenseActionNode.cs#L75)。

IsDispense依次判断：手动=true；模式与时机同时Off=false；IsFirstDispense且当前动作是S1DispenseActionNode且时机BeforeComingFirstDispense=true；或Periodic且距离动作私有LastDispenseTime超过毫秒间隔=true；否则false。它由调用驱动，不能画成独立后台定时器。生产动作结束时BeforeEveryDispense会将IsFirstDispense设true，但当前IsDispense首次点胶条件要求另一个枚举BeforeComingFirstDispense，因此不能仅凭标记名保证“每次前都预点胶”。[触发177–210](../../trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/OtherAction/PredispenseAction.cs#L177)；[标记144–153](../../trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/DispenseBPAction/S1DispenseActionNode.cs#L144)。

DoWork先WorkStart/Running，再进入try：无需执行就Success；报警返回Abort；按开关挤胶、取坐标、取胶型并逐点InterpolationApplication，非Success返回Alarm；之后可选胶后检测/手动移动，完成才更新LastDispenseTime。catch日志弹窗并返回Exception；finally复位IsManual/State并WorkStop。WorkStart在try外，finally也不统一关闭胶阀或回安全位。[74–170](../../trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/OtherAction/PredispenseAction.cs#L74)。

IsAlarm检查点胶头存在且示教、胶型名非空和板已示教；EpoxySqueeze按配置设置压力→移动挤胶位→开阀等待→关阀→移动擦胶位，该方法没有本地finally。逐点插补传入isDrip=false可对应DryCycle，但此前挤胶分支未在此方法判断DryCycle，下述控制器/模块包装同样未检查DryCycle；是否实际出胶仍需IO驱动和设备验证，不能声称空跑所有路径都不出胶。[216–279](../../trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/OtherAction/PredispenseAction.cs#L216)。

## 本轮补充：检测和硬件调用的边界

DispenseVisionDefect先启动照明任务、移动到相机位置并等待照明，再判断DryCycle；空跑返回空结果列表，否则延时并调用VisionService.VisionDefect。因此空跑分支不等于不运动或不开灯。[195–246](../../trunk/AKRS.ZX2200/DispenseSystem/Controllers/DispenseVisionController.cs#L195)。

PostBondEpoxyCheck复用System2的相机坐标系和相机比例；结果数不符或检测超限时调用PostBondCheckHand。人工OK/Ignore/Abort/Retry分别返回Success/Fail/Abort/Retry；找不到PR或未知选择会抛异常。预点胶上层没有判断这些返回码，不可把Retry画成已实现的检测重试环。[361–446](../../trunk/AKRS.ZX2200/BondSystem/Models/Repositories/PostBondInspection/PostBondInspection.cs#L361)；[594–625](../../trunk/AKRS.ZX2200/BondSystem/Models/Repositories/PostBondInspection/PostBondInspection.cs#L594)。

启用胶量检测导出时，PostBondEpoxyCheck读取bondPosition.TuName等字段；预点胶传入null。该导出块的异常被本地catch记录并弹窗，之后仍可返回Success；这不是成功写入数据的证明。导出目标为设备功能测试目录下的Excel文件；开关、文件权限及真实运行尚待验证。[447–538](../../trunk/AKRS.ZX2200/BondSystem/Models/Repositories/PostBondInspection/PostBondInspection.cs#L447)。

胶阀控制器直接转发开关调用；模块检查DripElectric非null后读写输出，关闭写false、开启在原值为false时写true。这两层没有DryCycle/Offline判断，也没有统一的异常关阀finally。结论只到输出API调用，未证明物理阀动作。[控制器827–847](../../trunk/AKRS.ZX2200/DispenseSystem/Controllers/DispenseController.cs#L827)；[模块500–537](../../trunk/AKRS.ZX2200/DispenseSystem/Modules/DispenseModule.cs#L500)。

设置压力在IsLinkDispenser=false时返回；否则叠加补偿，先限制最大值，再限制最低30，交给模块写Pressure/Vacuum/Time=10并调用SetPressureVacuumTime。两层catch均替换为通用异常；当前包装没有保留原异常作为inner exception。配置最大值是否始终大于等于30及驱动协议仍待核实。[控制器854–892](../../trunk/AKRS.ZX2200/DispenseSystem/Controllers/DispenseController.cs#L854)；[模块475–494](../../trunk/AKRS.ZX2200/DispenseSystem/Modules/DispenseModule.cs#L475)。

## 机械目标到运动调用

已补移动分支、轴包装和普通停止/急停差异，见[点胶运动与驱动边界](dispense-motion-source-review.md)。已追到外部LogicHardware/Drive API；不能宣称到位等待、超时和设备安全已验证。
