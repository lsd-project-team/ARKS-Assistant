# 原 S2 自检门与 UI/设备边界复核

复核日期：2026-10-06。状态：`source-confirmed-partial`。机器可复核证据见 [s2-self-check-audit.json](s2-self-check-audit.json)。本轮只读取源码，没有调用生产自检、DevExpress 对话框、轴/真空/吸嘴架、SQL、VM 或设备。

`System2Domain.CheckIsReady()` 从 `System2Domain.cs:594` 开始，先在第 597 行调用 `OpenBondHeadVaccum()`，然后才读取 `IsActiveSelfCheck`。开关关闭时直接返回 true；开启时按顺序执行 `BondProgram.SelfCheck()`、`ActionNodesService.SelfCheck()`、ULM 点位、BondHead 点位、吸嘴架点位、力控标定、温漂/取片补偿点位、七槽吸嘴架传感器检查、可选吸嘴检测、焊头余料处理和 S2 预点胶报警检查。吸嘴检测使用逻辑记忆与物理传感器比较；不一致时会进入 Yes/No 对话框，焊头有料时会进入 OK/Cancel 对话框，并可能调用 `ThrowAction()`。

`System2ActionNodesService.SelfCheck()`（第 818 行）有 7 类失败门：没有 ProcessStep、步骤没有 BondPosition、BondPosition 不在当前配方、步骤没有 Component、组件仓库找不到组件，以及上视/下视点位为空。每条失败路径都先调用 `XtraMessageBox.Show` 再返回 false。`BondProgram.SelfCheck()`（第 85 行）先调用吸嘴架程序自检，再逐个载具检查吸嘴、四类力控范围、上/下视示教点位、关真空延时与固晶延时，以及 IPT 条件下的吸嘴关真空延时；失败路径使用 `AKRSXtraMessageBox`。

`NozzleShelfProgram.SelfCheck()`（第 224 行）允许 TouchDown/BMC 例外，检查其他吸嘴是否完成示教，并拒绝焊头上超过一个吸嘴。`NozzleShelfController.CheckToolBankConfiguration()`（第 73 行）在吸嘴架启用时依次读取 1–7 号槽传感器；空槽且传感器有料会进入报警对话框。源码配置中 `IsActiveSelfCheck` 和 `IsActiveToolDetection` 默认均为 true。

结论是：S2 启动就绪自检的源级顺序、配置门、UI 失败反馈和硬件读取边界已经固定；完整入口仍不能在当前无生产 UI/设备环境中安全执行。已有的原始 System2Domain 二进制探针在进入 UI 绑定的 SelfCheck 前停止，因此不能把此前的相对重做/Init 通过记录当成自检运行验收。

## 可点击证据

- [System2Domain.cs:594](../../trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs#L594)
- [System2ActionNodesService.cs:818](../../trunk/AKRS.ZX2200/DispenseSystem/Services/System2ActionNodesService.cs#L818)
- [BondProgram.cs:85](../../trunk/AKRS.ZX2200/BondSystem/Models/Programs/BondProgram.cs#L85)
- [NozzleShelfProgram.cs:224](../../trunk/AKRS.ZX2200/BondSystem/Models/Programs/NozzleShelfProgram.cs#L224)
- [NozzleShelfController.cs:73](../../trunk/AKRS.ZX2200/BondSystem/Controllers/NozzleShelfController.cs#L73)
- [System2Configuration.cs:30](../../trunk/AKRS.ZX2200/BondSystem/Models/Parameter/System2Configuration.cs#L30)
- [original-system2-domain-native-audit.json](original-system2-domain-native-audit.json)
