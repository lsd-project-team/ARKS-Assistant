# S1/S2 InjectSteps 与步骤模型审计

日期：2026-10-06。状态：`source-confirmed-partial`。机器结果见 [process-step-injection-audit.json](process-step-injection-audit.json)，可复跑脚本为 [register-process-step-injection-audit.cjs](../../scripts/register-process-step-injection-audit.cjs)。

本轮固定了两个动作控制器的 `InjectSteps(TransportUnit)` 原始实现。S1 和 S2 都只读取各自启用的 `ProcessSteps`，遍历载具的基板、基岛和焊点；当步骤的 `BondPositionName` 等于当前焊点名称，且对应的 `S1RemainingSteps` 或 `S2RemainingSteps` 没有该步骤键时，才加入值为 `false` 的键。已有键和值不会被清空或覆盖，因此重复注入会保留已经写入的完成状态。

调用链也已固定：`TransportUnit` 构造时同时注入 S1/S2；`TuService` 的两个 Mapping 读取入口各自同时注入；`DispenseWorkTask` 在来料准备后、进入动作循环前注入 S1；`BondTask` 在来料、温漂/参考点处理和移动安全位之后、进入动作循环前注入 S2。`BondTask` 的补偿模式会先替换为测试载具，再沿相同位置注入。

该结果是原始源码控制流和哈希证据，不是生产运行验收。它没有执行真实载具、Mapping 文件、完整任务、UI、SQL、VM 或设备，也没有修改生产源、工程文件或配置。仍需在匹配配方和安全宿主中验证步骤列表、焊点字典以及重复载具/配方切换时保留旧键的实际影响。
