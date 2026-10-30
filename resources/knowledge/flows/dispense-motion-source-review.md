# 点胶运动：机械目标、到位等待与停止边界

2026-09-28。源码限定复核；未调用硬件，不把到位API名称当成实测保证。

## 调用顺序与分支

MoveToG0Pos3D先G0PosToSelf得到机械目标。条件以代码为准：非Working或TU为null，执行Z到配置安全高度→XY目标→Z目标；Working且有TU、测高打开且未配置激光测高时，执行Z到目标+跨越高度→XY→Z目标，三个调用传accuracy=false；其余情况按TU位置和产品SafeHeight计算安全高度并做点胶头/机械坐标转换，然后调用MoveToMachinePoint。[129–182](../../trunk/AKRS.ZX2200/DispenseSystem/Controllers/DispenseController.cs#L129)。

MoveToMachinePoint的point3D已经是机械目标，方法中只是赋给targetPos，没有再次做G0转换。其实际判断如下：[208–254](../../trunk/AKRS.ZX2200/DispenseSystem/Controllers/DispenseController.cs#L208)。

|条件|执行顺序|
|---|---|
|当前Z>=安全Z 且目标Z>=安全Z|XYZ命令与到位等待|
|当前Z>安全Z 且目标Z<安全Z|XY后Z|
|当前Z<安全Z 且目标Z>安全Z|Z后XY|
|当前Z<安全Z 且目标Z<=安全Z|Z到安全高度、XY、Z到目标|
|其他|日志后抛点胶移动异常|

因此当前Z==安全Z且目标Z<安全Z落入异常分支；不能概括为全部低位目标都会自动抬Z。坐标的物理方向和实际配置仍需验证。MoveToG0Pos3DWithoutSafe是另一入口，转换后直接调用XYZ包装，不执行上述安全高度分支。[191–200](../../trunk/AKRS.ZX2200/DispenseSystem/Controllers/DispenseController.cs#L191)。

## 模块到硬件API

轴通过HardwareRepositoryService按点胶X/Y/Z名称获取；速度取轴AbsoluteMoveSpeed乘MachineMoveSpeedPercentage，Acc/Dec/Jerk仍来自各轴配置。局部未验证倍率范围。[34–78](../../trunk/AKRS.ZX2200/DispenseSystem/Modules/DispenseModule.cs#L34)。

Z包装先检查轴非null，accuracy=true调用Axis.AbsoluteMove(movePara)，false调用AbsoluteMove(movePara,false,HighSpeed)。不根据外部API第二个bool猜测等待或安全语义。模块另提供独立SendAbsoluteMoveCommand和WaitForArrival包装。[249–342](../../trunk/AKRS.ZX2200/DispenseSystem/Modules/DispenseModule.cs#L249)。

XY高精度分支先分别SendAbsoluteMoveCommand，再MotionService.WaitAxesArrival；低精度分支虽先构造MovePara，实际调用MoveAxesToTargetPosition只传轴、false、目标、HighSpeed，未传入刚构造的MovePara。该分支最终速度/加速度须看外部实现，不能照搬高精度分支结论。[352–402](../../trunk/AKRS.ZX2200/DispenseSystem/Modules/DispenseModule.cs#L352)。

XYZ逐个发送X/Y/Z命令，随后调用WaitAxesArrival，均使用HighAccuracy。发送是三次顺序调用，不证明硬件插补同步起动。在已读包装内没有移动失败后的本地重试、统一停轴catch/finally或显式超时值；底层是否有超时不可推断。[408–467](../../trunk/AKRS.ZX2200/DispenseSystem/Modules/DispenseModule.cs#L408)。

## 停止不是同一层行为

Machine.Stop在所读方法内改Stop状态、报警状态及若干信号/业务状态，没有逐轴StopMove。EmergencyStop先取Axis列表并Parallel.ForEach调用StopMove(false,true)，再Machine.Stop和各任务Abort。若前面的停轴调用抛异常，此方法没有本地catch保证后续步骤继续。[347–402](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L347)。

DispenseWorkTask.AbortThread代码只Dispose任务；不能当作已验证的取消/中断机制，也不能证明等待到位已解除。[212–215](../../trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs#L212)。普通停止和完整任务恢复还应参照既有主流程专题，不将这里的急停等同于整机安全认证。

## 外部实现与交接缺口

模块using引用AKRS.Galaxy2.LogicHardware.Services。trunk内C#类声明检索仅找到空的MotionService2，未找到实际MotionService或Axis实现；它不是这条调用链的实现。项目引用libs中的LogicHardware和Drive程序集。[using1–6](../../trunk/AKRS.ZX2200/DispenseSystem/Modules/DispenseModule.cs#L1)；[空类9–13](../../trunk/AKRS.ZX2200/Infrastructure/Service/MotionService2.cs#L9)；[引用257–284](../../trunk/AKRS.ZX2200/AKRS.ZX2200.csproj#L257)。

当前文件SHA256仅标识本地依赖，不证明运行时实际加载版本：
- AKRS.Galaxy2.LogicHardware.dll：5d88c570a5823b35cd347f008357a6dd3b6a81b3b079dd93a7bab2f20b04b250
- AKRS.Galaxy2.Drive.dll：110c57d1dc48f94ee6c32ef223f48e78bc03ef3ad4aeb9986c76306f0d41ae79

待取得或定位对应版本的运动库实现/API契约，核实WaitAxesArrival超时、到位判定、限位/急停解除等待、bool参数、异常类型及低精度参数默认值。还需覆盖其他系统运动、插补/力控和真实硬件测试。本轮不修改生产代码。
