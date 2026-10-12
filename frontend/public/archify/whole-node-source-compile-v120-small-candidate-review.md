# Whole-node v120 小型候选隔离编译

记录时间：2026-10-07T08:17:43.470Z。基线 v120 为 177 个源码输入、70 个引用、902 条诊断，其中 448 个错误，退出码 1。

本轮将 10 个尚未纳入或已存在的真实源文件逐个追加到 v120 输入，在独立 DLL 和日志路径编译；所有候选产物均未接受为整节点构建。

| 候选 | 错误数 | 诊断数 | 决定 |
| --- | ---: | ---: | --- |
| `trunk/AKRS.ZX2200/BondSystem/Controllers/UpLookController.cs` | 449 | 904 | rejected-error-increase |
| `trunk/AKRS.ZX2200/BondSystem/Controllers/IPTController.cs` | 448 | 902 | rejected-no-error-reduction |
| `trunk/AKRS.ZX2200/BondSystem/Modules/System2Module.cs` | 459 | 914 | rejected-error-increase |
| `trunk/AKRS.ZX2200/BondSystem/Modules/BondHead.cs` | 461 | 915 | rejected-error-increase |
| `trunk/AKRS.ZX2200/DispenseSystem/Models/Programs/EpoxyMaterialProgram.cs` | 448 | 902 | rejected-no-error-reduction |
| `trunk/AKRS.ZX2200/DispenseSystem/Models/Programs/EpoxyApplicationProgram.cs` | 448 | 902 | already-present-in-v120 |
| `trunk/AKRS.ZX2200/BondSystem/Models/Programs/S2DispenserProgram.cs` | 451 | 905 | rejected-error-increase |
| `trunk/AKRS.ZX2200/BondSystem/Models/DeviceParams/BondHeadParam.cs` | 448 | 902 | already-present-in-v120 |
| `trunk/AKRS.ZX2200/BondSystem/Controllers/NozzleShelfController.cs` | 455 | 911 | rejected-error-increase |
| `trunk/AKRS.ZX2200/DispenseSystem/Models/Programs/System1OtherProgram.cs` | 448 | 902 | already-present-in-v120 |

没有候选将错误数降到 448 以下；`IPTController` 与 `EpoxyMaterialProgram` 保持 448 个错误，其余新增候选增加错误。v120 仍是当前实验最佳。

正式整节点基线仍保持 122 个原始文件、123 个源码输入、53 个引用、642 个错误；本证据不覆盖正式基线，也不宣称整体目标完成。

机器可读结果：[whole-node-source-compile-v120-small-candidate-progress.json](whole-node-source-compile-v120-small-candidate-progress.json)。

绑定校验：`node .archify-work/verify-v120-small-candidate-evidence.cjs` 通过，复核 10 个候选源码哈希及每份编译日志的错误/诊断计数。
