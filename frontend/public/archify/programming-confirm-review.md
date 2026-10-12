# 编程页面 Confirm 提交链路复核

日期：2026-09-28。范围：32 种已盘点页面中的 20 种直接声明 IProgrammingControl 的主类；完成这 20 个 Confirm 方法与指定保存委托的静态复核，不表示全工程、所有事件或设备运行已验收。

## 逐页执行链

|页面|实际执行顺序|分支 / 边界|源码|
|---|---|---|---|
|UcTransportSystem|输送配置名称 → TransportProgram.Save|直接读取 EditValue.ToString；本方法没有空值保护或本地 catch。|[167–180](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcTransportSystem.cs#L167)|
|UcBondMaxSubSection|尺寸枚举 → TransportProgram.Save|尺寸类型强制转换可能抛出。|[41–47](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcBondMaxSubSection.cs#L41)|
|UcLoderSetting|上料器名称 → TransportProgram.Save|来自当前组合框 Text。|[80–85](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcLoderSetting.cs#L80)|
|UcInput|配置检查 → 入口带速度 → InOutPutBeltSettingRepository.Save|检查 true 时静默 return；返回语义见下方重点。|[36–47](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcInput.cs#L36)|
|UcBeltSystem1|配置检查 → S1 带/插入参数 → 带仓库 Save → 插入仓库 Save|两次 Save 顺序执行；没有本地回滚。|[106–148](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcBeltSystem1.cs#L106)|
|UcBeltSystem2|配置检查 → 额外 Dispense 带空值检查 → Bond/WaitingUnload 参数 → 两个仓库 Save|额外 guard 检查 Dispense，后续写 Bond/WaitingUnload；不能视为全部目标空值保护。|[90–140](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcBeltSystem2.cs#L90)|
|UcUnloaderSetting|下料器名称 → TransportProgram.Save|来自当前组合框 Text。|[81–86](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcUnloaderSetting.cs#L81)|
|UcOutput|配置检查 → 出口带速度 → InOutPutBeltSettingRepository.Save|检查 true 时静默 return。|[35–46](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcOutput.cs#L35)|
|UcWaferHanding|MagazineProgram.Name → WaferSystemProgram.Save|EditValue 为空分支只有注释，随后可赋 null 并调用 Save。|[102–111](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Setting/Waferhandling/UcWaferHanding.cs#L102)|
|UcMagazineGeometry|SaveData → MagazineBoxConfigRepository.Save → 修改几何配置 → 再 Save → MagazineBoxGeoConfigRepository.Save|第一次保存发生在 Push、Direction、Offset 赋值前；不是单次事务。|[295–298](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Setting/Waferhandling/UcMagazineGeometry.cs#L295)|
|UcConfiguration1|空 Confirm|本方法无赋值、无 Save；不等于整个界面或 Designer 永远无副作用。|[38–40](../../trunk/AKRS.ZX2200/Infrastructure/Controls/Feature/EditProgram/UcConfiguration1.cs#L38)|
|UcNozzleEdit|Save → 吸嘴参数 → NozzleRepository.Save|Save 同时从 RgZDeterminationMethod.SelectedIndex 读取 Z 与 XY 方法；是否符合设计待确认。|[95–98](../../trunk/AKRS.ZX2200/BondSystem/Controls/Setting/Nozzle/UcNozzleEdit.cs#L95)|
|UcFlipToolEdit|翻晶工具参数 → FlipToolRepository.Save|本地未捕获转换或保存异常。|[94–104](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Setting/FlipTool/UcFlipToolEdit.cs#L94)|
|UcDispenser|点胶器参数 → DispenserRepository.Save → System1Program.Save|catch 写 Console 后 rethrow；EpoxyMaterial 非空才修改耗材；设备参数也被修改但本方法未调用其 Save。|[182–240](../../trunk/AKRS.ZX2200/DispenseSystem/Controls/Setting/Dispenser/UcDispenser.cs#L182)|
|UcTransportUnitFrame|载具 Save → 基板 Save → 模块 Save → ProductConfiguration.Save|前三个委托修改内存；任意异常中断剩余调用，详见已有提交专项。|[49–56](../../trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Setting/UcTransportUnitFrame.cs#L49)|
|UcBondPositionEdit|Save → 焊点参数 → ProductConfiguration.Save|AdjustType.None 将辅助状态设为 ForBidden。|[308–311](../../trunk/AKRS.ZX2200/BondSystem/Controls/Setting/BondPosition/UcBondPositionEdit.cs#L308)|
|UcComponentEdit|SaveAllData → 参数及辅助状态 → ComponentCheck → CarrierConfigRepository.Save|ComponentCheck 为 void；消息后 return 仅退出该检查，调用方仍继续 Save。|[1045–1048](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Setting/Component/UcComponentEdit.cs#L1045)|
|UcEpoxyApplication|点胶参数 → EpoxyApplicationRepository.Save → System1Program.Save|吸嘴未选写字符串 Null；本方法明确保存 System1Program，不据此推断所有 S2 路径行为。|[483–546](../../trunk/AKRS.ZX2200/DispenseSystem/Controls/Setting/EpoxyApplication/UcEpoxyApplication.cs#L483)|
|UcPostBondEdit|检测参数 → PostBondInspectionRepository.Save|Confirm 的 IsCircle 行是模型写回 UI；实际 UI 写模型在 CheckedChanged，不能单凭 Confirm 判断漏存。|[122–153](../../trunk/AKRS.ZX2200/BondSystem/Controls/Setting/PostBond/UcPostBondEdit.cs#L122)|
|UcProcessStep|ProcessDomain.CheckIsReady → 失败 throw / 成功 ProcessDomain.Save|校验失败抛“步骤保存失败”；与静默 return 不同。|[673–681](../../trunk/AKRS.ZX2200/Main/Machine/Process/UcProcessStep.cs#L673)|

## 输送配置校验：名称不能代替返回语义

[TransportProgram.IsSettingNull:146–179](../../trunk/AKRS.ZX2200/TransportSystem/Models/TransportProgram.cs#L146) 依次调用 Loading、Dispense、Bond、WaitingUnload、Unloading：任一子段返回 true，聚合立即返回 false；只有五段全返回 false 才最终返回 true。子段实现是配置存在返回 true、缺失提示并返回 false。因此聚合不能当作“所有配置是否有效”的校验。

[UcInput.Confirm:36–47](../../trunk/AKRS.ZX2200/TransportSystem/Controls/Setting/UcInput.cs#L36) 在聚合 true 时 return，否则直接访问入口配置并 Save。原方法隔离测试覆盖五个子段整体有效性的全部32种组合：
- 16种 Loading 有效组合：更新速度并调用 Save，包括其他段缺失的情况。
- 15种 Loading 缺失、至少另一段有效组合：继续访问空配置，抛 NullReferenceException。
- 1种五段均缺失组合：静默跳过更新和 Save。

[测试报告](transport-config-guard-test.json) 记录7个原方法所在文件的 SHA-256；[可重复测试脚本](../../scripts/test-transport-config-guard.cjs) 使用配置对象、UI 和 Save 替身。结论限定为这些源方法和组合；未执行真实仓库存取、真实界面、设备或生产启动，也未覆盖每个段内部部分字段缺失。测试 PASS 指成功复现当前行为，不代表行为正确。

## 对自动工作的影响边界

页面 Confirm 属于配方编辑准备链，不是自动生产循环。统一保存按钮 optional Confirm 返回后显示成功；空 Confirm 和静默 return 并不保证执行 Save。[统一提交专项](config-submit-reload-review.md) 已区分编辑/示教 Start 与 Machine.Start。生产就绪还需要继续追踪实际加载、引用绑定和生产启动校验，不能从按钮文案推出生产可运行。

## 保存委托与事件依据

- [Magazine.SaveData:124–150](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Setting/Waferhandling/UcMagazineGeometry.cs#L124)：配置仓库先保存一次，修改参数后再次保存，再保存几何仓库。
- [Nozzle.Save:75–90](../../trunk/AKRS.ZX2200/BondSystem/Controls/Setting/Nozzle/UcNozzleEdit.cs#L75)：参数赋值及吸嘴仓库保存。
- [BondPosition.Save:265–303](../../trunk/AKRS.ZX2200/BondSystem/Controls/Setting/BondPosition/UcBondPositionEdit.cs#L265)：焊点参数、辅助状态和产品配置保存。
- [Component.SaveAllData:896–996](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Setting/Component/UcComponentEdit.cs#L896)：调用 ComponentCheck 后继续 Save；[ComponentCheck:1003–1040](../../trunk/AKRS.ZX2200/WaferSubSystem/Controls/Setting/Component/UcComponentEdit.cs#L1003) 中缺吸嘴、未配置吸嘴架、未配置中转台均是提示后局部 return，不抛出或向调用者返回失败值。未配置吸嘴架时还先清空 NozzleName。这里仅证明保存调用继续，不证明实际写盘成功或后续生产允许启动。
- [PostBond.CheckedChanged:383–386](../../trunk/AKRS.ZX2200/BondSystem/Controls/Setting/PostBond/UcPostBondEdit.cs#L383)：IsCircle 的 UI→模型赋值；事件绑定和真实 UI 时序仍需单独验收。

## 完成与待办

已完成：20个 Confirm 主体的逐页静态阅读；上述保存委托追踪；原输送校验方法32种组合验证；明确空实现、静默返回、抛出异常的区别。所有20个 Confirm 的完整源码、行号和文件摘要保存在 [结构化清单](programming-confirm-review.json)。

未完成：仓库 Save 的真实落盘与重新加载闭环；全部字段/事件覆盖；上述异常条件的现场可达性；配方编辑结果进入 Machine.Start 的完整约束关系；硬件与 SDK 联调。没有修改 trunk，也没有把本专题计为模块完整验收。下一步优先将这些配置保存结果追踪到真实生产加载/启动门槛，而不是继续增加无验收标准的图表数量。


2026-09-28后续验证：UcEpoxyApplication.Confirm新增[11项原方法隔离检查](epoxy-confirm-test.json)，胶型名称解析新增[7项检查](epoxy-name-resolution-test.json)。两次保存的失败边界、控件范围和读取属性修改名称列表的副作用，详见[整合说明](config-production-gates.md)。不是实际写盘或全工程运行验收。
