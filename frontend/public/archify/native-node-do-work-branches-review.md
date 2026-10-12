# 原动作节点非设备 DoWork 分支

日期：2026-10-06。状态：`original-runtime-selected-non-device-dowork-passed`。机器可读结果：[native-node-do-work-branches-progress.json](native-node-do-work-branches-progress.json)。

本轮复用原节点前置条件的公开完整树、步骤、控制器和 16 个保真程序集。两轮每轮 604 项检查均通过；两个原始公开 S1/S2 控制器各选出 34 个注册接收者，并在每轮执行 544 次原始 `IsDoWork()` 调用（15 个条件场景及脱离传输对象观察）。DoWork 的限定非设备分支覆盖八个身份、三个 S1 测高、五个 S1/S2 视觉、一个 S1 相对固晶焊点定位、一个 S2 上视纠偏、一个 S2 预点胶禁用硬件门和继承的 Pick 离线早退。八个身份分支返回 `Success` 并设置对应身份标记，三个测高分支在离线状态更新后通过禁用测高门返回 `Success`，五个视觉分支返回 `Success` 并设置视觉标记，相对固晶焊点定位在视觉硬件前返回 `Success`，上视纠偏在运动和视觉前返回 `Success`，预点胶分支通过系统2点胶硬件门返回 `Success`；这些限定分支的回调和状态断言均通过。两轮结果对象一致，实际硬件仓库保持空。

这是真实原程序集上的隔离公开夹具运行，未写私有状态，未启动生产 Task、PR、视觉、测量、VM、UI、SQL、运动或设备 I/O。`IsDoWork()` 条件矩阵不代表所有配方和辅助方法路径；其它具体 DoWork、在线分支、完整等待/Retry/Pause/异常链、原工程构建、Fody/LC、部署和现场验收仍未完成；生产源码和项目文件未修改。
