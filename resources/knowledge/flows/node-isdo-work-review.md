# 动作节点 IsDoWork 条件清单

日期：2026-10-06。状态：`source-confirmed-partial`。机器结果见 [node-isdo-work-audit.json](node-isdo-work-audit.json)，可复跑脚本为 [register-node-isdo-work-audit.cjs](../../scripts/register-node-isdo-work-audit.cjs)。

本轮扫描原始 `AKRS.ZX2200` 动作节点的 `IsDoWork()`，为每个方法记录源码位置、文件哈希、方法体摘要以及离线、空跑、MatterProductState、步骤、视觉完成和测高完成等公开条件。共解析 35 个动作节点方法，覆盖 S1/S2 身份、视觉、测高、点胶、取片、固晶、上视纠偏、基板相机纠偏及焊后检查等类别。

条件并不统一：部分节点明确拒绝离线模式，部分节点只检查实体状态、步骤是否需要执行或视觉/测高完成标志。35 个节点中有 30 个在 `IsDoWork()` 与 `DoWork()` 中呈现不同的离线模式门存在性；这说明动作是否被调度与执行时是否早退是两个需要分别验证的契约。动作名称本身不能推出 `IsDoWork()` 会放行，也不能推出随后的 `DoWork()` 不触碰运动或视觉依赖。已有非设备 `DoWork` 夹具只覆盖选定早退分支，本清单不把其扩大成全部节点运行覆盖。

该项是原始源码条件地图，没有调用任何 `IsDoWork()`，没有创建配方或载具，也没有触碰 UI、SQL、VM、运动、视觉或设备。正生产条件、辅助方法副作用和完整任务 Retry/Pause/异常传播仍需匹配环境验证。
