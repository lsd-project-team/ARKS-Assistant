# 源码运动耗时的已知条件

核对日期：2026-10-22。用户已确认没有 `Hardware.json` 所在目录，按现有源码继续计算可算部分，并明确标记缺参运动段。分析保持只读，不运行设备或加载目标程序集。

## 轴与参数来源

业务模块通过 `GetHardware<Axis>(名称)` 查找轴，当前可恢复32个不同名称。硬件仓库读取 `Application.StartupPath/Settings/Hardwares/Hardware.json`，按轴的 `CardNum` 匹配卡的 `AxisCardNum`，再由 `AxisCardType` 选择 GT、ACS、LeadShine 或 ETEL 驱动。整个提供的 trunk 没有这份文件；文件不存在时仓库不会自动按业务轴名生成默认轴。因此业务声明为 Axis、源码中出现 GT/ETEL 转换，都不能证明每条轴当前使用哪个驱动。

四类参数分别保留来源：

| 来源 | 例子 | 可得结论 |
| --- | --- | --- |
| 源码字面值 | 压力测高请求 V=1、A=D=10、J=0.02、目标=currentZ−5 | 可恢复请求，不能代替反馈停止后的完整动作时间 |
| 库构造默认 | AxisMovePara 的速度/加减速为10、J=0 | 可描述默认场景，不能替代每轴保存配置；脉冲当量没有可用默认值 |
| 保存配置 | 轴类型、脉冲当量、有效速度、限速、点位、坐标标定和倍率 | 未提供的值保持未定，不补零起点 |
| 运行读值 | GetRealPosition、GetVel、GetAcc、GetDec及压力反馈 | 不能一律替换为声明初值或上次请求目标 |

初始化命令速度还会经过 `(min(AbsoluteMoveSpeed, MaxSpeedLimit) − 0.1) × PulseEquivalent`，不能把 GetVel 简化为保存的 AbsoluteMoveSpeed。不同 MoveAxisZ 重载对速度、加减速和倍率的处理不同；MoveBondXY 的 X 轴 J 实际来自 Y 轴配置，分析保留原表达式。

## 驱动与时间公式

精确包指纹：LogicHardware 为 `5d88c570a5823b35cd347f008357a6dd3b6a81b3b079dd93a7bab2f20b04b250`，Drive 为 `110c57d1dc48f94ee6c32ef223f48e78bc03ef3ad4aeb9986c76306f0d41ae79`。已核对包内调用、重载和单位变换，未执行 DLL。

GT 封装的 P/Invoke 指向 gxn.dll；相邻候选文件 SHA-256 为 `3686b3e228cf476a1410e7268f9ce1d8499107a7fad7147d2580b1122df84f18`，固定资源版本为2025.9.29.0。其导出和 TTrapPrm 字段与封装声明相容，但尚未证明运行时实际装载路径，也没有匹配的 SDK 发布清单。

已证明的软件转换包括速度除以1000、加减速除以1,000,000，以及目标位置向 Int32 脉冲取整。[固高 GEN 基本功能手册](https://www.googoltech.com.cn/Uploads/file/20240611/20240611111501_26829.pdf)将对应 Trap 参数定义为 pulse/ms、pulse/ms² 和毫秒，但尚未将该手册绑定到上述精确 SDK 构建，不能外推为全部驱动的统一单位。ACS 官方资料正文当前不可读；ETEL 与 LeadShine 的曲线参数另有语义。

只有已知有效配置、规划起点、量化目标、V/A/D、正确单位、零起终速且无平滑时，普通梯形/三角速度公式才适用。GT 的 GetCurrentPosition 实际读编码器位置，不能自动当作规划器起点。相对命令也经过读编码器位置后转绝对目标的路径。

普通 Axis 的绝对运动在发令后有20 ms等待，该等待与已启动的运动重叠；CamAxis、到位模式和多轴完成边界分别处理。不能将完整运动理论时间再加20 ms，也不能把每根轴的时间逐项相加。

## 当前交付口径

固定延时及可跟踪的分支、循环和等待组成直接给出数值；不确定的运动、反馈、初始化或 SDK 调用保留条件与源码位置。目前没有找到由已提供配置完全绑定、又不依赖未知反馈/入口状态的完整物理运动动作，不能编造总毫秒数。

用户主表显示“耗时未定”或“已知停留，运动/等待耗时未定”，不把缺失文件变成采集、导入或补参数的操作流程。原表达式、包契约和条件公式保留在详情。已跳过和源码抛异常的动作继续分别显示。

本地完整证据在 `output/action-timing-trunk/axis-binding-next.*` 和 `gtn-unit-contract-next.*`。25个重点 LogicHardware 方法及92个 Drive 方法体的原 IL 字节哈希已核对；这些局部证据不代表完整原生 SDK 算法已恢复。整体进度和未验收范围见[全 trunk 开发记录](action-timing-trunk.md)。
