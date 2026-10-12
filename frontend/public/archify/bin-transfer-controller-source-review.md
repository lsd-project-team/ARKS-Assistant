# 料仓输送控制器：传感器、推杆、皮带和异常出口

2026-09-28。源码静态复核；接续[料仓任务与信号交接](loader-unloader-handshake-source-review.md)。本报告说明软件执行分支，不证明物理物料成功传输。

## 上料仓 → 点胶载台

1. 点胶段记忆HasMaterial时睡眠500ms并返回NoStart。否则挡料气缸1升起、UnClamp；RePush处再次升起挡料气缸，然后MovePushRodHome，紧接PushTabletToDispenseNoWait。前一个返回值被后一个覆盖，未单独检查缩回成功。
2. 推出返回非Success，弹窗：Retry清错、等待50ms、上使能、等待50ms并回RePush；Ignore继续；下一片返回None；终止返回Abort；不再上料把ContinuousFeeding=false并返回NoStart。
3. while(true)轮询点胶入口传感器；检测有料才break。若推杆已到位仍无料，先缩回再出现同样五选项。此处Ignore的break只退出switch，不退出while；不能画成忽略后直接进入皮带接料。此循环自身没有Sleep、Stop/Pause判断或总超时；下层异常/阻塞能力另算。
4. 检测有料后创建后台缩回Task：轮询推杆到位，到位时缩回并break；否则计时超过10000ms后break。没有Sleep，缩回返回值未检查。10秒是该轮询退出门槛，不是全流程超时，也不能保证执行中的硬件调用可在10秒内结束。
5. 点胶传料状态设Transfering，调用MoveBeltWaitArrive，再睡眠200ms并复查入口。入口仍有料时置NoMaterial/Alarm并报警：Retry回RePush；Abort退出；不再上料关ContinuousFeeding并返回NoStart；Ignore跳出switch后直接到方法尾返回Success。
6. 只有入口无料的else分支执行Clamp(true)、按需创建System1 TransportUnit并Save、Refresh、点胶HasMaterial、清上料段TU及记忆、两段Ready、IsTuInDispense1=true，并等待后台缩回Task结束。外层catch日志/弹窗后返回Exception，没有本地统一finally收尾。

证据：[入口与首次推料](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L873)、[传感器轮询](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L953)、[后台缩回](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L1047)、[最终报警与提交](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L1078)。

## 等待区 → 下料仓

1. 物理传感器无料、等待区记忆NoMaterial或皮带仍运动，各自睡眠500ms后返回NoStart。Online/OnlineWithAutoUnloader另检查下料段记忆有料。
2. retry处把等待区传料状态设Transfering，启动皮带相对运动且不等待到位，睡眠200ms。循环仅在IsMoving为true时读取有料传感器；读到false就退出，读到true则每300ms继续。该循环自身无Stop/Pause判断或总超时。
3. 若循环保存的hasMaterialInWaitingUnload为true，置Alarm并提示：Retry回retry；Abort直接返回；Ignore退出switch。注意推杆段位于该if的else内，所以这次Ignore会跳过该推杆段，进入后续收尾与状态提交。变量初始false；若从未进入IsMoving循环，则没有本轮循环内传感器采样，也会走else推杆段。
4. else分支RePush：先MovePushRodHome，后PushTabletToUnloader，前一个返回值同样被覆盖。推出非Success时Retry只回RePush、Ignore继续、Abort返回。
5. 再次HasMaterialInModule检查等待区有料；若仍有料，把等待/下料两段传料状态置Alarm并提示。Retry先缩回后回retry（会重启皮带）；Abort返回；Ignore继续收尾。源码注释称传感器F，但实际调用是等待区HasMaterialInModule，不能据注释改画成另一个独立出料传感器。
6. 公共收尾：缩回推杆（返回值未检查）、停止等待区皮带、清等待区TU、等待区NoMaterial/下料区HasMaterial、两段Ready、AddCurPlaceLayer、Save、返回Success。异常只显式恢复等待区SubSectionState到stateTemp，日志/弹窗后返回Exception，不是完整回滚。

证据：[前置与皮带启动](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L2063)、[传感器与第一处卡料](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L2113)、[推杆与二次检测](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L2162)、[收尾及异常](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs#L2240)。

## 下层实现与边界

- 上料缩回目标传参为2，下料为4；均检查模块返回值，非Success在包装层转Exception。调用者覆盖或忽略该结果的事实不能被包装层检查掩盖。参数单位和实际安全位置仍需硬件配置确认。
- 上料推出是SendAbsoluteMoveCommand，上料缩回和下料推杆是AbsoluteMove；本报告不为这些外部Axis方法臆造超时/中断契约。上料IsPushRodInPosition异常被catch后返回false，可能使上层继续等待；未实机复现。
- 模块IsReady主要检查轴对象非null，不能称伺服就绪或安全互锁完备。OffLineWork下上料动作返回None、上料到位判断true；下料动作返回Success，二者离线语义不一致。
- 点胶皮带使用ForwardTransportDistance与ForwardVelRate，模块调用Axis.RelativeMove；等待区皮带调用SendRelativeMoveCommand。公共模块将速度设为AbsoluteMoveSpeed*velRate；这两层包装是void且没有显式检查调用结果，未读SDK不能称已经确认运动成功。
- IsMoving读取Axis.GetAxisState().Moving；StopMove在轴非null时调用StopMove(false,true)。等待区轴由名称“固晶出料等待区X”查找，传感器为“出料等待区有料检测1”，读取CheckStateForNums(true,1,0)。配置及SDK读取契约未验证。

证据：[上料包装](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/LoaderBinController.cs#L92)、[下料包装](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/UnLoaderBinController.cs#L87)、[上料模块](../../trunk/AKRS.ZX2200/TransportSystem/Modules/LoaderBinModule.cs#L110)、[下料模块](../../trunk/AKRS.ZX2200/TransportSystem/Modules/UnloaderBinModule.cs#L116)、[皮带基类](../../trunk/AKRS.ZX2200/TransportSystem/Modules/BaseSubSectionModule.cs#L46)、[等待区映射](../../trunk/AKRS.ZX2200/TransportSystem/Modules/WaitingUnloadSubSectionModule.cs#L39)、[点胶皮带参数](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/DispenseSubSectionController.cs#L547)、[等待区皮带参数](../../trunk/AKRS.ZX2200/TransportSystem/Controllers/WaitingUnloadSubSectionController.cs#L112)。

## 风险与后续验收

|关注点|源码已证明|尚不能证明 / 验收方法|
|---|---|---|
|成功不等于物理成功|两处Ignore可绕过正常动作/状态初始化段后Success|人工忽略的业务意图与后续任务是否可承受；隔离场景回放|
|缩回失败继续推|调用处覆盖缩回返回值|实际轴是否继续运动、硬件互锁是否阻止；核对SDK及配置|
|等待与停止|上料入口while和下料IsMoving循环无本地Stop/Pause检查|全局Stop是否足以终止这些循环；联查Machine.Stop与轴状态反馈|
|并发缩回Task|非正常出口没有统一等待/取消；只有正常else等待|重试时旧Task是否与新推料重叠；用可控假轴做时序测试|
|状态持久化|上料只在新TU创建处显式Save；下料多项修改后Save|其他Save消费者、内存/磁盘一致性和保存失败恢复|

下一步优先联查Machine.Stop/Pause/Continue与这些循环、后台缩回任务及轴停止之间的真实联系；再展开层位移动和配置持久化。暂不修改设备代码，不把静态风险宣称为已复现故障。
