# 邦头安全高度、轴包装与单步信号

更新：2026-09-28。限定静态复核，无生产源码修改或设备执行。

[统一入口](index.html) · [标定测高与移动](calibration-height-motion-source-review.md) · [邦定模块](bond-system-module-review.md)

## 执行摘要

标定调用MoveSafeBondXYZ：取当前位置 → 计算三维目标对应安全高度 → 检查目标软限位 → 单步闸门 → 按当前/目标高度安排XY与Z。XY包装先检查离线模式与轴引用，发X、Y命令后等待到位；Z包装再次检查单步、检查软限位，再调用AxisZ.AbsoluteMove并返回执行码。上层MoveSafeBondXYZ没有消费Z返回码。

单步模式下，System2Domain等待System2SingleStepSignal；非单步模式直接放行。信号循环发现单步标志变false则返回false，收到事件则返回true。UI下一步按钮发送事件；Stop将单步标志清为false。不能把普通Stop、单步闸门和底层停轴视作同一件事。

## 安全高度按什么计算

仅分析[GetBondheadSafeLevel(AKRSPoint3D)：337–405](../../trunk/AKRS.ZX2200/BondSystem/Controllers/BondModuleController.cs#L337)，不扩展到同名2D/4D/无参重载。

1. 取得BondSubSection的TransportUnit及当前位置，把配置AxisSafePos通过BondCoordinateSystem.SelfPosToG0转换，取Z作为初始高度。
2. 有TU时，若配置System2点胶、测高气缸打开且Dispenser非null，高度为TU原点G0.Z + 产品SafeHeight − 邦头与点胶头Z距离；否则为TU原点G0.Z + 产品SafeHeight + 当前吸嘴MeasureHeightOffset（无吸嘴为0）。
3. 将高度ConvertG0ToMachinePos。无TU时也把初始G0高度转换回来。
4. Machine.IsWorking()==false时，覆盖为配置AxisSafePos.Z。注意前面的TU访问和转换已经执行，不能描述为非工作状态跳过所有TU逻辑。
5. 配置静态华夫盒时，转换BondAvoidStaticWafflePos；目标Y或当前Y达到该位置Y时，取现有安全高度与avoidPos.Z+吸嘴偏移的较大值。此步骤在非工作覆盖之后。
6. 最终安全高度超出BondZ AxisSetPara正负软限位则抛异常，否则返回。上述加减号和比较方向来自源码；物理坐标方向与参数有效性未实测。

[MoveSafeBondXYZ：123–178](../../trunk/AKRS.ZX2200/BondSystem/Controllers/BondModuleController.MovementRelated.cs#L123)按这个高度执行：当前Z>=安全Z时XY后目标Z；当前低而目标>=安全时目标Z后XY；两者低时安全Z、XY、目标Z。非有限数等异常输入未由本次复核验证。

## XY/Z包装与返回值

| 项目 | 源码实际行为 | 不能据此推断的内容 |
|---|---|---|
| [MoveBondXY：449–498](../../trunk/AKRS.ZX2200/BondSystem/Modules/BondModule.cs#L449) | OffLineWork直接return；IsReady false也return；随后检查软限位，分别SendAbsoluteMoveCommand(X,Y)，最后MotionService.WaitAxesArrival，HighAccuracy | void返回不表示已运动；两次命令不证明硬件同步插补；等待超时和失败停轴属于外部契约 |
| [IsReady：893–901](../../trunk/AKRS.ZX2200/BondSystem/Modules/BondModule.cs#L893) | 只检查X、Y和BondHead.AxisZ是否为null | 不证明回零、伺服使能、驱动无报警或设备已准备好 |
| [MoveZAxis：219–233](../../trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.MovementRelated.cs#L219) | 单步false返回Abort；检查Z软限位；取配置速度乘MachineMoveSpeedPercentage，调用AbsoluteMove(pos,true,vel)，原样返回结果 | bool参数true的驱动含义、超时与取消机制未经外部实现核验 |

XY速度、加速度、减速度均乘MachineMoveSpeedPercentage；X与Y的MovePara.Jerk都取BondAxisY.AxisMovePara.Jerk，不能写成X取自己的Jerk。需工程师确认是否有意共用；本轮未修改。包装未做倍率范围检查。

Z速度来源见[267–270](../../trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.MovementRelated.cs#L267)，Z越界抛异常见[411–421](../../trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.MovementRelated.cs#L411)。

上层安全移动不检查MoveZAxis的ExcuteResult。因此若Z包装返回Abort而不抛异常，调用者仍执行该分支之后的语句。例如两者低于安全高度分支中，首次安全Z返回Abort后仍会调用XY。这个条件性结论不证明设备已发生碰撞或该场景可在真实配置中复现。

## 单步从哪里放行或退出

- [System2Domain.WaitSingleStep：777–788](../../trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs#L777)：单步标志为true才调用信号等待，否则直接true。这意味着“非单步进入”与“等待过程中退出单步”不是同一个返回路径。
- [信号配置：60](../../trunk/AKRS.Galaxy2.Machine/Models/SignalPool.cs#L60)：System2使用recycleTime=100、AutoReset、初始false。底层EventWaitHandle构造与Set见[75–95](../../trunk/AKRS.Galaxy2.Machine/Models/Signal.cs#L75)。
- [Signal.WaitSingleStep：175–196](../../trunk/AKRS.Galaxy2.Machine/Models/Signal.cs#L175)：每轮先检查IsSingleStepWork，false直接返回false；Sleep(5)后WaitOne(recycleTime)，等待不到则继续。收到事件后更新State=ReSet并返回true，没有再次检查单步标志。100ms是每轮等待参数，不是整体超时；该方法没有调用WaitStart或直接检查MachineState.Stop。
- [UI单步开关和下一步：982–1016](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L982)：开关开启设true；关闭先Set系统2信号再设false。下一步按当前System2/其他选择信号，且要求单步标志true。关闭开关与等待线程之间存在时序差异：等待者可能先消费事件返回true，也可能先观察false返回false，不能声称关闭一定Abort。
- [Machine.Stop：347–359](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs#L347)：先改Stop状态、清弹窗、设置报警状态，再清除单步标志。如果执行到该赋值，单步等待者可在后续检查时返回false；若同时收到事件，也不能排除该次等待返回true。未对线程内存可见性、延迟或竞争做运行保证。

MoveSafeBondXYZ自身和每次MoveZAxis都有闸门，因此一次高层移动在单步模式可能需要多个事件。信号是自动复位事件，不是持久任务队列；本轮未模拟多等待线程争用或验证UI是否限制并发。

## 交接缺口

已收窄“单步false来源未知”的缺口：有源码路径可解释它，但标定界面状态、并发操作与现场可达性仍待验证。不得把单步返回false当成自动取消整个标定任务。

后续需继续独立/全局标定入口、2D/4D安全高度与其他运动路径；取得外部Axis/MotionService契约核验到位、停止、取消和异常清理。离线不运动、轴缺失、不同TU/吸嘴/华夫盒配置、Z返回Abort、单步退出与停止竞争均需隔离测试。本文不作整机安全或运行质量验收。
