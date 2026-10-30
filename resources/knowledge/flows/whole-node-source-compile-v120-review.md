# Whole-node source combination v120

v120 在 v119 候选上补入真实的 `BondSystem/BondForce/Models/VoiceCoilModels/ForceTorque.cs`、`WaferSubSystem/Models/Entities/SearchChip/PickRefEnd.cs` 和 `BondSystem/BondForce/Modbus/RtuConnectConfig.cs`，使用 177 个源码输入、70 个程序集引用。Roslyn 诊断 902 条，其中错误 448 条、非错误诊断 454 条，退出码为 1，DLL 未验收。

v120 比 v119 的 455 个错误减少 7 个，比 v8 的 642 个错误减少 194 个。加入完整 `ForceCalibrationService.cs` 或四文件 EjectionBank 组后均回升到 452，故不纳入 v120。剩余未解析类型仍集中在 BondHead/BondModule/System2Controller 等控制器、BondForce.Services、BondSystem.Controls、EjectionBank、Consumables、Product 和主窗体命名空间。

正式 whole-node 基线文件仍保持 642 个错误；本候选是隔离源码组合，没有执行原工程构建、Fody、部署、UI、硬件或生产 Task，且未修改 `trunk`。
