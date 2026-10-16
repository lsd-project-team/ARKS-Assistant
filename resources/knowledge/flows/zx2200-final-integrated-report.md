# ZX2200 源码理解与自动化流程整合报告

> 分析范围：`trunk` 当前源码树。本文将源码证据、自动化流程、框架语义、业务分支、数据生命周期和 Archify 成果统一到一个入口。

## 1. 一页结论

ZX2200 是一个 WinForms 设备控制应用。`Program.Main` 完成单实例、初始化和主窗体启动；`MainForm` 加载配置、连接仪器并启动后台监控；`Machine` 执行回零、就绪检查、状态切换和生产任务调度。生产过程由输送、S1 点胶、S2 固晶、晶圆供料/取晶及可选翻转、蘸胶和检测任务并发协作。

载具主线是：上料 → S1 配方动作 → 放行至 S2 → 按配方取晶/视觉校正/固晶/检测 → 下料。任务之间通过进程内 `SignalPool`/`Signal` 等待和放行；这不是外部消息队列。配方、设备配置、统计记录、图片和 Mapping 文件构成运行数据面。

## 2. 从启动到完成

1. **启动与回零**：`Program.cs` 初始化 PR、硬件和环境；按配置执行回零，加载 `MainForm`。
2. **生产放行**：操作员点击启动；`Machine.Operate` 复位信号并检查回零、旧任务、PR、门、产品和配方。
3. **任务调度**：检查通过后置为 `Working`，按配置启动 Transport、S1、S2、供晶、翻转和胶盘任务。
4. **载具输送**：根据上料/下料配置选择在线、皮带或料仓路径，并通过状态和信号交接。
5. **S1**：从配方展开动作，执行预点胶、定位、测高、点胶和检测；Retry 保留动作，其他失败由任务决定停止或放行。
6. **供晶与取晶**：根据 Wafer/Waffle/FlipTable 和 Single/Nine/WaferMap/Box 等模式搜晶、换料、翻转并预取下一颗。
7. **S2**：根据 Component/Defect/Epoxy 生成动作，执行取晶、上视/基板校正、固晶、蘸胶和可选检测。
8. **完成与持久化**：载具完成后放行下料；统计进入有界队列并写入数据库，视觉图片进入队列并保存为 BMP，设备状态和 Mapping 写入配置/文件。
9. **异常与恢复**：Pause 使协作边界的 `Signal.Wait` 阻塞；Continue 检查门状态后恢复 `Working`；Retry/Ignore/Abort 按 S1、S2 和具体动作分别处理。

## 3. 成果地图

### 主流程与自动化子流程

- [主自动化流程](automation-workflow.html)
- [模块交互时序](automation-sequence.html)
- [启动/回零](startup-workflow.html)
- [输送与上下料](transport-workflow.html)
- [S1 点胶](dispense-workflow.html)
- [晶圆供料/换料/翻转](wafer-supply-workflow.html)
- [S2 调度与载具完成](bonding-workflow.html)
- [取晶与漏晶恢复](pickup-workflow.html)
- [固晶与回带恢复](bond-action-workflow.html)
- [暂停、重试、停止与线程边界](failure-recovery-workflow.html)

### 架构、框架和专题

- [软件总体架构](zx2200-architecture.html)
- [框架运行时语义](framework-runtime-architecture.html)
- [配置与配方生命周期](recipe-lifecycle-workflow.html)
- [视觉、运动与补偿](vision-motion-workflow.html)
- [标定任务细化](calibration-task-workflow.html)
- [运行数据与持久化](runtime-dataflow.html)
- [手动维护、报警与标定](maintenance-calibration-workflow.html)

### 源码证据与验收

- [完整自动化源码分析](automation-source-analysis.md)
- [流程摘要](automation-workflow-summary.md)
- [业务分支覆盖清单](business-branch-coverage.md)
- [源码覆盖审计](source-coverage-audit.md)
- [信号矩阵](automation-signal-matrix.md)
- [源码证据索引](source-evidence.json)
- [验收记录](verification.md)
- [最终文件清单与 SHA-256](artifact-manifest.json)

## 4. 已确认的源码边界

- `Signal.Wait` 的 Pause/Stop/AutoReset/SingleStep 语义已由 `Signal.cs` 直接证明。
- `RuntimeProvider.ThreadFlag` 是全局退出标志，但各线程是否读取必须逐线程核实。
- `MachineConfigContext` 从 `MachineConfig.json` 读取单例并通过 `RecipeID` 解析当前配方。
- `MachineService.cs` 当前为空类，不能虚构其职责。
- 外部 PR、轴、IO、相机、力控、VisionMaster、Modbus 和第三方 DLL 内部实现不在 `trunk` 中，图中保持外部边界。
- 测试/示例项目不混入生产主链。

## 5. 验收状态

当前共 17 个 Archify 图规格，全部通过 showcase 的 9/9 检查，0 errors、0 warnings；HTML、Archify JSON、源码说明、证据索引和导航页均已生成。自动浏览器 visual-check 受当前环境没有 Chrome/Chromium 影响而跳过，未将其伪称为通过。
