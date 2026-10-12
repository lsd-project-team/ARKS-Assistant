# 其余节点非设备早退边界

日期：2026-10-06。状态：`source-confirmed-boundary`。机器结果见 [remaining-node-early-boundary-audit.json](remaining-node-early-boundary-audit.json)，可复跑脚本为 [register-remaining-node-early-boundary-audit.cjs](../../scripts/register-remaining-node-early-boundary-audit.cjs)。

S1 `S1DispenseDefectActionNode` 的离线分支先调用 `S1FinishedStep`，但没有返回；随后仍读取 `PostBondInspection` 并进入 `DispenseVisionController.DispenseVisionDefect` 路径，因此不能把它当作无视觉依赖的离线成功分支。

S2 `AfterBondCheckActionNode` 的离线门位于当前基板、基岛、焊点、检测对象和 `IsNeedDefect()` 准备之后；它会标记当前 S2 步骤，但 `finally` 仍调用 `UcMainSystem.ReFreshSystem2TuAction()`。隔离探针为此分支编译通过，但运行阶段退出码为 `3762504530`，没有得到可序列化的结果；该候选没有进入成功夹具。

本轮只登记源码顺序和失败边界，没有修改生产源或项目文件，也没有把失败探针当作生产故障或成功运行证据。后续若要验证焊后检查，需要提供匹配的检测仓库、当前消息上下文和可控 UI 刷新宿主。
