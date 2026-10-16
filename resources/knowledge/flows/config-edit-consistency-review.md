# ZX2200 配置编辑、阵列一致性与焊点重命名

更新：2026-09-28。范围为trunk源码与隔离原方法实验；未执行示教、运动、PR文件操作或真实配置保存。

## 工作流摘要

1. 基板/基岛示教完成后调用各自Save：非手动输入间距模式先更新行列和间距；矩阵模式将Count设为行×列，并按双循环重建坐标；离散模式以采集点数生成Count和坐标。最后设置示教状态Able，再调用产品配置Save。数量/坐标同步确实存在，但不能据此证明所有编辑/加载入口或异常时都一致。
2. 焊点列表双击改名：校验所选项、空名、原名、非法文件名字符、长度>15和同名项。通过后依次执行OtherConfig.ChangeBpName → ProcessDomain.ChangeBpName（内含Save）→ ChangePrName；若存在载具则调用InitializeTS，随后修改当前焊点配置Name → 产品Save → RefreshControl。
3. 这不是自动生产循环，而是影响后续自动生产对象和恢复状态的配置准备链路。制程保存早于最终产品保存，已读调用段没有统一事务或回滚。

## 已确认的分支与缺口

- 基板行列输入小于1会提示并重试；基岛输入先TryParse，失败重试，再取绝对值，0或1时将间距设为0。两处验证规则不同，不能统一表述为“均保证正数”。
- 手动矩阵对话框确定按钮直接写入行列/间距，调用方未检查ShowDialog返回值即Save。Designer设置无边框，不能据此声称有可点击取消按钮；第三方控件最小值、其他退出方式待实际UI验证。
- OtherConfig.ChangeBpName确实更新BpSingleSeparates的匹配名称；但普通状态改名只写入局部list，后续RemoveAll/AddRange仍作用于局部list，没有回写MatterProductInfo，也没有触碰MatterProductInfoMax。
- ProcessDomain.ChangeBpName更新S1/S2步骤的BondPositionName后Save。隔离Save抛错实验确认已改内存仍保留，异常向外传播；不等于真实文件保存失败已复现。
- ChangePrName对Mark1至Mark4逐个调用CopyPREntity再DeletePREntity；该调用段没有事务或返回检查。这里只证明调用顺序，未验证内部磁盘失败契约。
- InitializeTS返回void：工作/暂停时直接返回；用户选No则不清空。Yes分支有安全位置/气缸调用，并将五个输送段状态置NoMaterial、TU置null、保存、提示人工取走。它不是自动重建载具。改名调用方不检查清理结果；是否能在特定运行状态从UI进入该路径仍待验证。

## 原方法验证与更正

`node scripts/test-config-rename.cjs`：6项断言通过，覆盖偏移改名、两类状态列表保留旧名、双工位步骤改名、未匹配项保留及保存异常后的内存状态。见[报告](config-rename-test.json)。生产状态结构体、偏移类、枚举来自源码；两个结构体构造器仅为C#5补 : this()；制程容器和Save为替身，未运行UI/硬件/磁盘。

上一版状态测试误把结构体模拟成类，现撤回“缺名触发catch并清理”。更正后14项状态断言通过：大数量状态Find缺名返回默认结构体，状态为Enable，不进入catch/Save；真正的数组越界才用于验证部分写入保留。见[更正说明](mapping-constructor-config-review.md)。

## 下一验收条件

- 用已认证配方复核改名前后两类状态、偏移、制程、视觉键及现存TU的一致性。
- 隔离验证拒绝清空、运行/暂停返回、PR复制失败和分段保存失败的UI行为；不直接在设备上试错。
- 继续展开配置加载/其余编辑入口、动作字典与运行中切换限制。所有模块仍保持部分复核，本轮不修改生产源码。

## 精确源码入口

- [config-sub-save：FrmSubstratePositionTeach.cs:511–558](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=config-sub-save)
- [config-sub-input：FrmSubstratePositionTeach.cs:302–348](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=config-sub-input)
- [config-sub-rows：FrmSubstratePositionTeach.cs:399–422](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=config-sub-rows)
- [config-module-save：FrmModulePositionTeach.cs:535–590](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=config-module-save)
- [config-module-input：FrmModulePositionTeach.cs:305–353](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=config-module-input)
- [config-module-rows：FrmModulePositionTeach.cs:400–424](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=config-module-rows)
- [config-matrix-input：FrmInputMatrixInfo.cs:16–51](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=config-matrix-input)
- [config-matrix-border：FrmInputMatrixInfo.Designer.cs:292–303](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=config-matrix-border)
- [config-rename-offset-state：OtherConfig.cs:62–89](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=config-rename-offset-state)
- [config-state-types：OtherConfig.cs:157–294](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=config-state-types)
- [config-state-enum：TuEnum.cs:278–302](module-source-explorer.html#module=AKRS.ZX2200%2FTransportUnitSystem&evidence=config-state-enum)
- [config-rename-ui：UcAddBondPosition.cs:331–395](module-source-explorer.html#module=AKRS.ZX2200%2FBondSystem&evidence=config-rename-ui)
- [config-rename-pr：UcAddBondPosition.cs:313–324](module-source-explorer.html#module=AKRS.ZX2200%2FBondSystem&evidence=config-rename-pr)
- [config-rename-event：UcAddBondPosition.Designer.cs:94–100](module-source-explorer.html#module=AKRS.ZX2200%2FBondSystem&evidence=config-rename-event)
- [config-rename-process：ProcessDomain.cs:259–278](module-source-explorer.html#module=AKRS.ZX2200%2FMain&evidence=config-rename-process)
- [config-rename-clear：TransportController.cs:150–224](module-source-explorer.html#module=AKRS.ZX2200%2FTransportSystem&evidence=config-rename-clear)
