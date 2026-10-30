# ZX2200 全工程源码基准清单

文件系统清单，排除 bin/obj/.git；含 Designer 等生成源码；不等于 csproj 编译项或业务覆盖率。

|源码分组|C# 文件数|主流程证据文件数|状态|
|---|---:|---:|---|
|AKRS.Calibration|12|0|部分复核：定义与代表调用已核实，未完成模块闭环|
|Akrs.ChangeJson|12|0|部分复核：定义与代表调用已核实，未完成模块闭环|
|AKRS.Galaxy.SoftKey|6|0|部分复核：定义与代表调用已核实，未完成模块闭环|
|AKRS.Galaxy2.AutoFocusing|4|0|部分复核：定义与代表调用已核实，未完成模块闭环|
|AKRS.Galaxy2.AxisCompensate|7|0|部分复核：定义与代表调用已核实，未完成模块闭环|
|AKRS.Galaxy2.Component.TestDemo|6|0|部分复核：定义与代表调用已核实，未完成模块闭环|
|AKRS.Galaxy2.CoordinateSystems|13|0|部分复核：定义与代表调用已核实，未完成模块闭环|
|AKRS.Galaxy2.Dispense|82|0|部分复核：定义与代表调用已核实，未完成模块闭环|
|AKRS.Galaxy2.LogTest|6|0|部分复核：定义与代表调用已核实，未完成模块闭环|
|AKRS.Galaxy2.Machine|7|2|部分复核：定义与代表调用已核实，未完成模块闭环|
|AKRS.Galaxy2.MachineSupport|4|1|部分复核：定义与代表调用已核实，未完成模块闭环|
|AKRS.Galaxy2.PR|87|0|部分复核：定义与代表调用已核实，未完成模块闭环|
|AKRS.Galaxy2.PR.Test|6|0|部分复核：定义与代表调用已核实，未完成模块闭环|
|AKRS.Galaxy2.TeachTest|17|0|部分复核：定义与代表调用已核实，未完成模块闭环|
|AKRS.ZX2200/BondSystem|227|13|部分复核：定义与代表调用已核实，未完成模块闭环|
|AKRS.ZX2200/CalibSystem|65|0|部分复核：定义与代表调用已核实，未完成模块闭环|
|AKRS.ZX2200/Common.cs|1|0|部分复核：定义与代表调用已核实，未完成模块闭环|
|AKRS.ZX2200/DispenseSystem|75|19|部分复核：定义与代表调用已核实，未完成模块闭环|
|AKRS.ZX2200/Experiment|68|0|部分复核：定义与代表调用已核实，未完成模块闭环|
|AKRS.ZX2200/Infrastructure|126|0|部分复核：定义与代表调用已核实，未完成模块闭环|
|AKRS.ZX2200/Localization|4|0|部分复核：定义与代表调用已核实，未完成模块闭环|
|AKRS.ZX2200/Main|76|9|部分复核：定义与代表调用已核实，未完成模块闭环|
|AKRS.ZX2200/Program.cs|1|1|部分复核：定义与代表调用已核实，未完成模块闭环|
|AKRS.ZX2200/Properties|3|0|部分复核：定义与代表调用已核实，未完成模块闭环|
|AKRS.ZX2200/SupportFeature|160|1|部分复核：定义与代表调用已核实，未完成模块闭环|
|AKRS.ZX2200/TransportSystem|73|6|部分复核：定义与代表调用已核实，未完成模块闭环|
|AKRS.ZX2200/TransportUnitSystem|104|5|部分复核：定义与代表调用已核实，未完成模块闭环|
|AKRS.ZX2200/WaferSubSystem|174|8|部分复核：定义与代表调用已核实，未完成模块闭环|
|InterpolationMovementTest|10|0|部分复核：定义与代表调用已核实，未完成模块闭环|

完整文件列表见 source-module-inventory.json。模块定义、代表调用、证据与剩余项见 [模块复核进度](module-review-status.md)，主流程证据文件数不包含独立模块证据快照。下一步为每组补充职责、实际入口、调用证据、业务链路、成果入口和缺失项；当前不按文件数量计算项目完成率。
