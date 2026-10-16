# ZX2200 业务分支覆盖清单

本清单按 `trunk/AKRS.ZX2200` 中的枚举和 `switch` 分支核对现有流程图。它记录的是源码中确实出现的分支，不代表每种配置都在现场启用。

| 领域 | 源码确认的分支 | 已覆盖位置 | 证据 |
|---|---|---|---|
| 输送上料 | None、在线/皮带、LoaderBin | 输送与上下料图 | `TransportTask.cs`、`LoaderTask.cs`、`TransportDomain.cs` |
| 输送下料 | 出口皮带/在线交接、Unloader | 输送与上下料图 | `TransportTask.cs`、`UnloaderTask.cs` |
| S1 动作 | 配方排序、Divide 分段、预点胶、测高/点胶/检测、Retry/Stop | S1 点胶图 | `DispenseWorkTask.cs`、S1 ActionNodeController |
| S2 动作类型 | Component、Defect、Epoxy；可选蘸胶、检测 | S2 调度图、固晶图 | `BondTask.cs`、`System2Domain.cs`、`BondActionService.cs` |
| 取晶类型 | Wafer、Waffle、FlipTable；漏晶重检/重取/忽略/退出 | 取晶图、供晶图 | `PickActionService.cs`、`PickActionNode.cs`、`FlipTask.cs` |
| 搜晶方式 | Single、Nine、WaferMap、Box；换片或人工选点 | 供晶图 | `EnumWaferSubSystem.cs`、`WaferSubSystemTask.cs`、`SearchChip/Block.cs` |
| 载具类型 | Wafer、Waffle、StaticWaffle（部分代码分支被注释） | 供晶图；注释分支标为未启用 | `WaferSubController.cs`、`System2Controller.Assistant.cs` |
| 视觉模式 | 上视/基板相机、PR 成功/失败、角度/中心补偿 | 视觉运动图 | `VisionService.cs`、`UpLookCorrectionActionNode.cs`、`SubstrateCameraCorrectionActionNode.cs` |
| 失败结果 | Success、Retry、Ignore、Abort/Exception、人工 Alarm 对话框 | 恢复图及各子图 | `BondTask.cs`、`TransportTask.cs`、`UnloaderTask.cs`、`WaferSubSystemTask.cs` |
| 设备状态 | Working、Pause、Stop、EmergencyStop、单步等待 | 恢复图、框架运行时图 | `Signal.cs`、`Machine.Operate.cs`、`MachineStateModel.cs` |

## 当前仍需人工确认的边界

- `switch` 中被注释掉的枚举分支不能当作运行路径；图中只保留了注释说明。
- 外部 PR、轴、IO、力控和相机驱动只提供接口/结果，仓库内没有足够实现证明其内部重试策略。
- 大量 WinForms Assistant/Teach/Test 页面是配置或维护入口，不属于每个生产载具必经路径；它们已在维护/标定边界中单独列出。

## 验收结论

主要生产分支、动作结果和状态控制已有对应图或源码说明；新增分支应先在本清单登记源码证据，再进入 Archify 图，避免把目录结构误当成执行流程。
