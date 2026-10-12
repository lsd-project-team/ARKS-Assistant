# 编程页面 Confirm 方法体复核

本页先把20个直接声明 `IProgrammingControl` 的页面完整 `Confirm` 方法体锚定到源码，再区分直接 `.Save(`、委托方法以及条件返回/抛出。表中“未命中”仅限当前方法体，不代表页面无保存行为，也不表示调用会成功落盘。

|页面|方法体|直接Save调用|提前返回|显式抛出|可能的委托调用|
|---|---|---|---|---|---|
|UcTransportSystem|[167–180](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcTransportSystem.cs#L167)|[179](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcTransportSystem.cs#L179)|未命中|未命中|未命中|
|UcBondMaxSubSection|[41–47](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcBondMaxSubSection.cs#L41)|[46](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcBondMaxSubSection.cs#L46)|未命中|未命中|未命中|
|UcLoderSetting|[80–85](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcLoderSetting.cs#L80)|[84](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcLoderSetting.cs#L84)|未命中|未命中|未命中|
|UcInput|[36–47](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcInput.cs#L36)|[46](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcInput.cs#L46)|[40](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcInput.cs#L40)|未命中|未命中|
|UcBeltSystem1|[106–148](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcBeltSystem1.cs#L106)|[146](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcBeltSystem1.cs#L146)、[147](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcBeltSystem1.cs#L147)|[110](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcBeltSystem1.cs#L110)|未命中|未命中|
|UcBeltSystem2|[90–140](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcBeltSystem2.cs#L90)|[138](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcBeltSystem2.cs#L138)、[139](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcBeltSystem2.cs#L139)|[94](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcBeltSystem2.cs#L94)、[100](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcBeltSystem2.cs#L100)|未命中|未命中|
|UcUnloaderSetting|[81–86](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcUnloaderSetting.cs#L81)|[85](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcUnloaderSetting.cs#L85)|未命中|未命中|未命中|
|UcOutput|[35–46](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcOutput.cs#L35)|[45](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcOutput.cs#L45)|[39](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcOutput.cs#L39)|未命中|未命中|
|UcWaferHanding|[102–111](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Setting/Waferhandling/UcWaferHanding.cs#L102)|[110](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Setting/Waferhandling/UcWaferHanding.cs#L110)|未命中|未命中|未命中|
|UcMagazineGeometry|[295–298](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Setting/Waferhandling/UcMagazineGeometry.cs#L295)|未命中|未命中|未命中|[297](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Setting/Waferhandling/UcMagazineGeometry.cs#L297)|
|UcConfiguration1|[38–40](../../trunk/AKRS.ZX2200/Infrastructure/Controls/Feature/EditProgram/UcConfiguration1.cs#L38)|未命中|未命中|未命中|未命中|
|UcNozzleEdit|[95–98](../../trunk/AKRS.ZX2200/BondSystem/Controls/Setting/Nozzle/UcNozzleEdit.cs#L95)|[97](../../trunk/AKRS.ZX2200/BondSystem/Controls/Setting/Nozzle/UcNozzleEdit.cs#L97)|未命中|未命中|未命中|
|UcFlipToolEdit|[94–104](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Setting/FlipTool/UcFlipToolEdit.cs#L94)|[103](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Setting/FlipTool/UcFlipToolEdit.cs#L103)|未命中|未命中|未命中|
|UcDispenser|[182–240](../../trunk/AKRS.ZX2200/DispenseSystem/Controls/Setting/Dispenser/UcDispenser.cs#L182)|[231](../../trunk/AKRS.ZX2200/DispenseSystem/Controls/Setting/Dispenser/UcDispenser.cs#L231)、[233](../../trunk/AKRS.ZX2200/DispenseSystem/Controls/Setting/Dispenser/UcDispenser.cs#L233)|未命中|[238](../../trunk/AKRS.ZX2200/DispenseSystem/Controls/Setting/Dispenser/UcDispenser.cs#L238)|未命中|
|UcTransportUnitFrame|[49–56](../../trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Setting/UcTransportUnitFrame.cs#L49)|[51](../../trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Setting/UcTransportUnitFrame.cs#L51)、[52](../../trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Setting/UcTransportUnitFrame.cs#L52)、[53](../../trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Setting/UcTransportUnitFrame.cs#L53)、[55](../../trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Setting/UcTransportUnitFrame.cs#L55)|未命中|未命中|未命中|
|UcBondPositionEdit|[308–311](../../trunk/AKRS.ZX2200/BondSystem/Controls/Setting/BondPosition/UcBondPositionEdit.cs#L308)|[310](../../trunk/AKRS.ZX2200/BondSystem/Controls/Setting/BondPosition/UcBondPositionEdit.cs#L310)|未命中|未命中|未命中|
|UcComponentEdit|[1045–1048](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Setting/Component/UcComponentEdit.cs#L1045)|未命中|未命中|未命中|[1047](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Setting/Component/UcComponentEdit.cs#L1047)|
|UcEpoxyApplication|[483–546](../../trunk/AKRS.ZX2200/DispenseSystem/Controls/Setting/EpoxyApplication/UcEpoxyApplication.cs#L483)|[544](../../trunk/AKRS.ZX2200/DispenseSystem/Controls/Setting/EpoxyApplication/UcEpoxyApplication.cs#L544)、[545](../../trunk/AKRS.ZX2200/DispenseSystem/Controls/Setting/EpoxyApplication/UcEpoxyApplication.cs#L545)|未命中|未命中|未命中|
|UcPostBondEdit|[122–153](../../trunk/AKRS.ZX2200/BondSystem/Controls/Setting/PostBond/UcPostBondEdit.cs#L122)|[152](../../trunk/AKRS.ZX2200/BondSystem/Controls/Setting/PostBond/UcPostBondEdit.cs#L152)|未命中|未命中|未命中|
|UcProcessStep|[673–681](../../trunk/AKRS.ZX2200/Main/Machine/Process/UcProcessStep.cs#L673)|[680](../../trunk/AKRS.ZX2200/Main/Machine/Process/UcProcessStep.cs#L680)|未命中|[677](../../trunk/AKRS.ZX2200/Main/Machine/Process/UcProcessStep.cs#L677)|未命中|

## 重点分派与分支

- [UcConfiguration1.Confirm 38–40](../../trunk/AKRS.ZX2200/Infrastructure/Controls/Feature/EditProgram/UcConfiguration1.cs#L38) 的当前方法体为空；这只说明该入口无直接动作。
- [UcMagazineGeometry.Confirm 295–298](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Setting/Waferhandling/UcMagazineGeometry.cs#L295) 委托 [SaveData 124–150](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Setting/Waferhandling/UcMagazineGeometry.cs#L124)：先写几何名称并调用一次 MagazineBoxConfigRepository.Save；随后更新其他内存字段与可选几何尺寸，再顺序调用另外两次 Save。中途异常后是否已部分持久化取决于仓库实现，本审查不声称原子性。
- [UcComponentEdit.Confirm 1045–1048](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Setting/Component/UcComponentEdit.cs#L1045) 委托 [SaveAllData 896–996](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Setting/Component/UcComponentEdit.cs#L896)。后者在 [993–995行](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Setting/Component/UcComponentEdit.cs#L993) 调用 `ComponentCheck()` 后继续调用 `CarrierConfigRepository.Save()`；[ComponentCheck 1003–1040](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Setting/Component/UcComponentEdit.cs#L1003) 的提示与 `return` 只退出该检查方法，不直接取消外层 Save。其他异常仍可能中断。
- [UcProcessStep.Confirm 673–681](../../trunk/AKRS.ZX2200/Main/Machine/Process/UcProcessStep.cs#L673) 在 `CheckIsReady()` 为 false 时先抛异常，否则调用 `ProcessDomain.Save()`；[UcDispenser 230–239](../../trunk/AKRS.ZX2200/DispenseSystem/Controls/Setting/Dispenser/UcDispenser.cs#L230) 的两个 Save 在 try 内顺序调用，catch 输出异常并重抛。此处只确认语句次序，未确认任何实际磁盘写入。

## 审核边界

提取前验证主文件 SHA-256，读取完整 Confirm 方法体并为正文另存哈希和原文。方法末尾按该仓库四空格缩进样式定位，任何声明、缩进或范围异常即失败。表格只说明方法体字面调用，其他委托目标、早退可达性与文件结果仍需逐项复核。与[页面创建清单](programming-page-inventory.md)、[提交分派](programming-confirm-review.md)合用，不能把二十种页面概括为同一个保存事务。

重建：`node scripts/build-programming-confirm-bodies.cjs`；校验：同命令加 `--check`。
