# 相对贴片动作排序审计

日期：2026-10-06。状态：`source-confirmed-partial`。机器结果见 [relative-bond-order-audit.json](relative-bond-order-audit.json)，可复跑脚本为 [register-relative-bond-order-audit.cjs](../../scripts/register-relative-bond-order-audit.cjs)。

`S2ActionNodeController.Init()` 在动作排序、异形载具过滤和禁用动作移除之后调用 `SortRelativeBond()`。该方法选出 `RelativeBondPosition=true` 的焊点配置，为每个配置查找启用步骤；随后删除该步骤原有的 `BondPositionVisionActionNode` 消息，并在对应 `PickActionNode` 前插入新的视觉消息。这个顺序与相对贴片必须先完成前一焊点固晶再定位的源码意图一致。

源码还留下两个需要匹配配方验证的边界：找不到启用步骤时，查找结果仍会加入列表，后续读取 `ProcessStepName` 没有空值保护；找不到对应 `PickActionNode` 时，原视觉消息已经删除，但没有备用插入路径。两条都是方法体可达条件的静态结论，不等于现场已经发生故障。

本轮没有执行动作控制器、配方、载具、UI、VM、SQL 或设备，也没有修改生产源、工程文件或配置。
