# 标定下层：测高、重测与位置移动

更新：2026-09-28。限定静态复核，不修改生产源码、不操作设备。

[统一入口](index.html) · [标定执行图](calibration-execution-workflow.html) · [标定主调度](calibration-module-review.md)

## 工作步骤摘要

邦定相机标定先调用MoveSafeBondXYZ到BMC测高搜索位置，再用邦头当前实际Z作为搜索起点，配置WithTDSensor测高实体并执行DoWork。失败弹出Retry/Cancel，Retry在同一个实体上再次执行，Cancel返回失败结果。只有Success才写入BMC高度并立即保存设备参数，然后继续相机标定。

点胶相机标定在坐标变换更新后移动到探测位置、打开测高气缸，调用HeightMeasurement。该函数根据配置走激光读数或探针搜索。失败返回false；成功写入测高位置、移动Z到0、保存参数、关闭气缸。它不是邦头的人工重试循环。

## 邦头测高：参数、执行与重试

- [标定调用：291–321](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L291)：liftLevel取BondHeadParam.AxisSafePos.Z。Success后保存BMCDevicePara.MeasureHeightResult；否则提示并返回false。
- [入口重载：640–654](../../trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs#L640)：默认searchDistance=10、searchVel=1，searchPosition读取AxisZ.GetRealPosition，然后调用五参数重载。
- [实体构造：665–729](../../trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs#L665)：WithTDSensor设置AxisName=BondZ、负向搜索、LiftPosition=liftLevel、IsWaitStopArrive=false、TimeOutMillSeconds=10000。判定条件实际设置IsUseLVDTJudgeState=true、LvdtName=焊头LVDT、LvdtLimit来自参数、TriggeIoValue=true；不能按“默认不使用LVDT”的注释反推行为，也不能仅凭枚举名称判定底层接触传感器逻辑。该分支未显式设置MeasureType和MeasureHeightAxis，默认值/按名称解析属于外部实体契约。
- [执行和重试：817–864](../../trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs#L817)：每次先Sleep(1000)，再entity.DoWork。TimeOut和其他非Success分别提示，两者Retry均goto ReMeasureHeight。没有本地次数上限；这是操作员选择的重试，不是自动定时重试。Cancel保留并返回原失败tuple。
- 同一实体被重用，搜索起点和条件没有在goto后重新构造。DoWork内部是否复位、如何抬升/停轴、超时如何实现均未证实。10000是传入的单次配置，不能宣称整个标定最多10秒。此包装无统一catch/finally；异常不会进入针对返回码的Retry判断。WithVacuumSensor关闭真空仅位于正常返回路径。

## 点胶测高：激光、探针与普通IO

[完整分发：279–423](../../trunk/AKRS.ZX2200/DispenseSystem/Controllers/DispenseMeasureHeightController.cs#L279)。未传searchPosition时读点胶Z实际位置；未传searchSpeed时取MeasureHeightSpeed。传入传感器HardwareName与DispenseAltimemetrySensor一致时，再检查IsSystem1ConfigLaserMh。

| 路径 | 执行及输出 | 局部失败处理 |
|---|---|---|
| 匹配测高传感器且配置激光 | Sleep(LaserMhDelayTime) → LaserMeasureHeight.GetValue → 实际Z减读数 | 只对原始读数IsNaN判Abort；本方法未做Infinity或范围校验，无本地重试/抬升 |
| 匹配测高传感器且非激光 | 先读输入；再构造Probe实体，负向搜索距离为MeasureHeightDownDistance+MeasureHeightDistance，LiftPosition为搜索起点 | 输入已触发则提示并返回Abort/0，否则直接返回DoWork结果 |
| 其他传感器 | 先读输入；构造IOMeasureHeight实体，负向搜索距离3，LiftPosition为搜索起点 | 输入已触发返回Abort/0，否则直接返回DoWork结果 |

探针和IO实体均配置TimeOutMillSeconds=10000、IsWaitStopArrive=false。探针另设置ProbeAddress=4、ProbeOpenValue=4532、ProbeValueAddress=5。这里只证实传值，不证明硬件寄存器协议或实际超时语义。

[标定消费结果：250–284](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L250)：失败直接return false，跳过本方法后续Z安全移动、参数保存和关闭气缸；catch日志/弹窗后也返回false，没有finally执行这些收尾。不能由此断言机器一定保持某种物理状态，因为外部DoWork和其他监控可能有动作，但本层没有保证。激光读数成功也仍经过上层打开/关闭气缸调用，不能从本层画出“激光完全不动气缸”。

## 进入测高前的移动与单步闸门

[点胶标定移动：47–95](../../trunk/AKRS.ZX2200/CalibSystem/Services/CalibController.cs#L47)：3D依次AxisZAbsoluteMove(0) → AxisXYAbsoluteMove(X,Y) → AxisZAbsoluteMove(Z)。2D重载先读取当前Z，再复用3D；MoveDispenseZToSafePos也传0。轴包装、等待和外部MotionService边界见[点胶运动说明](dispense-motion-source-review.md)。

[邦头安全移动：123–178](../../trunk/AKRS.ZX2200/BondSystem/Controllers/BondModuleController.MovementRelated.cs#L123)：先计算GetBondheadSafeLevel，CheckSoftLimit，再WaitSingleStep。闸门false时void方法直接return，没有向调用者返回失败码。

| 当前Z / 目标Z相对安全高度 | 本方法调用顺序 |
|---|---|
| 当前>=安全（目标高或低） | XY → 目标Z |
| 当前<安全，目标>=安全 | 目标Z → XY |
| 当前<安全，目标<安全 | 安全Z → XY → 目标Z |

[CheckSoftLimit三维重载：941–965](../../trunk/AKRS.ZX2200/BondSystem/Modules/BondModule.cs#L941)以AxisSetPara上下限检查XYZ并在越界时抛异常，正常返回true。不能仅因调用者未接bool就说限位无效。

[WaitSingleStep：777–788](../../trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs#L777)仅在IsSingleStepWork为true时等待System2SingleStepSignal并传播false。结合标定调用者，可作条件性结论：若该闸门返回false且没有抛异常，MoveSafeBondXYZ提前结束后，StartBondCalibTask仍继续进入测高调用。未证明该条件在实际标定UI配置中可达；不能报告成已复现故障。

补充复核已展开三维安全高度、Bond XY/Z包装及信号false来源，见[安全移动与单步信号](bond-motion-single-step-source-review.md)。外部轴实现、完整恢复和现场时序仍待验证。本表是代码调用顺序，不等于轴已物理到位，也不是设备安全认证。

## 外部实现与交接缺口

本次在trunk的C#类声明检索未发现MeasureHeightEntity、IOJudgeCondition实现；控制器using指向AKRS.Galaxy2.MeasureHeight及其IOMeasureHeight命名空间。[项目引用70–72](../../trunk/AKRS.ZX2200/AKRS.ZX2200.csproj#L70)指向libs/AKRS.Galaxy2.MeasureHeight.dll。

本地该DLL SHA256：`0b5b4d5d7436d8fd116e5265007b9f3f07cd624bfb405ba81e5e257c3077574c`。它只标识现有依赖，不证明运行时实际加载版本；本轮没有反编译或执行DLL。

工程师后续需取得匹配实现/API契约，核实DoWork触发、超时、抬升、停止、取消、重试复位与异常清理；核实LVDT判定、激光有效范围、探针寄存器和标定配置。继续补齐其他入口后，才可讨论全量标定覆盖；运行验收另行记录。
