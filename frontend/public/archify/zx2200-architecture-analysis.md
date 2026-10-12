# ZX2200 软件总体架构分析

## 证据范围

本图基于 `trunk/AKRS.ZX2200/AKRS.ZX2200.csproj`、项目目录和关键入口源码建立。它描述源码可见的模块边界，不把第三方 DLL 内部实现当成已知事实。

## 分层关系

- **界面层**：`MainForm` 和 `UcMainSystem` 接收 Start、Pause、Continue、Stop 等操作。
- **生命周期层**：`Machine.Operate` 负责就绪检查、回零、设置 Working、启动任务及 Stop/EmergencyStop。
- **配方与动作层**：`ProcessDomain`、S1/S2 ActionNodeController 把配方步骤展开为动作消息。
- **生产域**：`TransportSystem` 负责载具输送；`DispenseSystem` 负责 S1；`BondSystem` 负责取晶、校正、固晶和蘸胶；`WaferSubSystem` 负责搜晶、换料和供晶。
- **协作层**：`SignalPool` / `Signal` 提供进程内等待与放行；它不是外部消息队列。
- **外部边界**：轴、IO、相机、Modbus、VisionMaster 和其他 DLL 通过引用或硬件仓库接入，其内部行为不在本仓库源码中。
- **数据层**：Settings、Recipe、统计、图片和可选 Mapping 形成配置与运行记录。

## 入口证据

- `Program.cs:65–256`：单实例、初始化、回零和 `Application.Run`。
- `MainForm.cs:232–257`：配置加载、仪器连接、后台线程。
- `Machine.Operate.cs:185–308`：就绪检查及并发任务启动。
- `TransportDomain.cs:84–140`：输送域启动。
- `DispenseWorkTask.cs:63–181`：S1 工作循环。
- `BondTask.cs:100–354`：S2 工作循环。
- `WaferSubSystemTask.cs:64–384`：供晶、搜晶及异常路径。
- `SignalPool.cs:74–186`：模块间信号声明。

对应交互图：[zx2200-architecture.html](zx2200-architecture.html)，可编辑源：[zx2200-architecture.archify.json](zx2200-architecture.archify.json)。
