# 补偿结果是否用于生产：三套对象的实际边界

更新：2026-09-28。源码限定复核；没有启用补偿、修改参数或运行设备。

[统一入口](index.html) · [全局标定](global-calibration-source-review.md) · [邦定模块](bond-system-module-review.md)

## 关键结论与流程摘要

不能把“全局标定得到BondCompensate数组”直接连成“贴装应用该数组”。[BondCompensate.GetBondCompensate：74–86](../../trunk/AKRS.ZX2200/SupportFeature/Compensate/MotionAreaCompensate/BondCompensate.cs#L74)入口立即return new AKRSPoint3D()，后续开关、数组检查和插值全部不可达。即使IsBondCompensate开启，此方法也不会读数组计算修正。本轮不修改这个提前返回。

生产CalculateBondPos实际调用另一类TransportUnitCompensate。其数据来自补偿窗口读取统计列表、按产品网格排列、缩放和平滑后保存；生产按开关和数组存在性决定是否插值，再从G0贴装位置减去返回值，转换为机械目标并用于预贴装移动。

| 对象 | 输入/保存 | 本次确认的消费 |
|---|---|---|
| GlobalCalibrationDomain | 二维台面映射、起点/网格，GlobalCalibrationDomain.json | 全局窗口SaveData按驱动写映射；不能替代载具补偿 |
| BondCompensate | 全局Z-XY扫描累加double数组，BondCompensate.json | 全局窗口调用GetBondCompensate，但它立即返回新点，插值不执行 |
| TransportUnitCompensate | 统计列表导入生成数组，TransportUnitCompensate.json | CalculateBondPos调用GetBondCompensate，在满足条件时执行插值 |

路径见[ZX2200PathConfig344–369](../../trunk/AKRS.ZX2200/Infrastructure/Models/Path/ZX2200PathConfig.cs#L344)，三者均组合DeviceDirPath和不同文件名。绑定分别见[Global域22–25](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/GlobalCalibrationDomain.cs#L22)、[Bond对象23–26](../../trunk/AKRS.ZX2200/SupportFeature/Compensate/MotionAreaCompensate/BondCompensate.cs#L23)、[TU对象20–23](../../trunk/AKRS.ZX2200/SupportFeature/Compensate/MotionAreaCompensate/TransportUnitCompensate.cs#L20)。Singleton实际加载/原子保存契约仍未得到实现证明。

## 统计列表到载具补偿表

1. [主界面1934–1937](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L1934)通过ShowForm打开FrmBondCompensate。
2. [FrmInputData43–77](../../trunk/AKRS.ZX2200/SupportFeature/Compensate/MotionAreaCompensate/FrmInputData.cs#L43)加载UcDefectStatistics，关闭时取其DefectStatisticsEntities；导入按钮设DialogResult.OK，取消设Cancel。这不是直接读取Excel文件的代码。
3. [统计刷新64–80](../../trunk/AKRS.ZX2200/SupportFeature/Statistics/UcDefectStatistics.cs#L64)按选中检测名称和起止时间调用QueryDefect，并把返回列表绑定到界面和属性。[QueryDefect325–328](../../trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsDomain.cs#L325)按时间闭区间和DefectName筛选DBService.Query，没有显式网格排序。数据库内部默认顺序尚未核实。
4. [补偿导入48–99](../../trunk/AKRS.ZX2200/SupportFeature/Compensate/MotionAreaCompensate/FrmBondCompensate.cs#L48)检查OK、非空、数量等于产品行×列；从产品配置读取网格尺寸和间距，以list[0]的BondPositionX/Y作为起点。注意行列数赋值发生在数量校验前，失败不是完全无内存副作用。
5. 使用list[j+i*ColumnCount]排列网格，OffsetX/Y除1000；没有在此按行列/坐标重新排序或验证每点坐标。数量匹配不证明空间顺序正确。
6. [101–130](../../trunk/AKRS.ZX2200/SupportFeature/Compensate/MotionAreaCompensate/FrmBondCompensate.cs#L101)只沿列方向平滑：首尾保持，次首/次尾取3点均值，其余取5点均值；赋值到TU数组、Save、刷新界面。不是二维邻域滤波。
7. [清除138–142](../../trunk/AKRS.ZX2200/SupportFeature/Compensate/MotionAreaCompensate/FrmBondCompensate.cs#L138)只将两个数组设null，该处理器没有Save或刷新调用；不能声称已永久清除配置文件。

## 载具补偿计算和边界

[TransportUnitCompensate.GetBondCompensate66–145](../../trunk/AKRS.ZX2200/SupportFeature/Compensate/MotionAreaCompensate/TransportUnitCompensate.cs#L66)：IsBondCompensate为false或任一数组null则返回新点。开关声明默认false，见[MachineSoftwareConfiguration123–127](../../trunk/AKRS.ZX2200/Main/Machine/MachineSupport/MachineSoftwareConfiguration.cs#L123)；这不是现场已加载配置值的证明。

启用且数组存在时，目标减起点，除间距强转int得到索引，取余数作为格内距离；索引下界夹到0，上边界夹到末索引并将邻接增量设0；取四角后按列、行依次线性插值，返回XYZ=(插值X,插值Y,0)。任一插值绝对值>1抛异常。此方法没有/1000，缩放发生在导入阶段。

不能将此描述成完整安全的边界钳制：索引改变后余数没有重算；负小偏移的强转int与数学floor不同。方法没有显式验证间距非零、数组非空且维度一致、输入有限。负向越界、单行/单列、空数组、NaN及不同维度需要验证；不能凭>1检查推断所有坏值已被拦截。

## 生产坐标在哪里使用

[CalculateBondPos498–527](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.Provider.cs#L498)先组合焊点坐标转换、硬补偿、焊后补偿和单点补偿；[555–593](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.Provider.cs#L555)可继续处理吸嘴/上视偏移，然后调用TU补偿并以减号应用到realBondPositionInG0，接着可加IPT参考点，记录RealBondPoint3D，ConvertG0ToMachinePos后再加point3D。这里仅追TU补偿插入点，其余算法不能视为已完整验收。

[BondActionNode126–169](../../trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.cs#L126)：离线先返回Success，DryCycle走独立BondActionDryRun；其后正常路径才CalculateBondPos，构造预贴装位置并MoveToPreBondPos，非Success返回该结果。因此不能用离线通过证明真实补偿计算或移动完成。

## 全局域中的插值辅助函数

[GlobalCalibrationDomain.GetAxisCompensate94–149](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/GlobalCalibrationDomain.cs#L94)对int映射四角插值，再除10000；GetBondHandCompensate在[160–169](../../trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/GlobalCalibrationDomain.cs#L160)取相机位置与减去相机/邦头偏移位置的差。trunk C#调用文本检索仅找到后者调用前者，未找到其他直接调用点；这不能排除反射/外部调用，亦不能画成已连接到贴装主链。硬件台面映射写入是另一条已发现路径，参见全局标定说明。

该辅助插值允许的上界为Start+Spacing*Count，却仍读取index+1四角，没有末格特判；有效边界及数组尺寸需要单独验证。它与TU补偿的边界处理不同，不应混合解释。

## 交接缺口

需确认BondCompensate无条件返回是否为有意停用、统计列表顺序能否对应产品网格、补偿开关及配置加载值、数组/间距有效性、清除后持久化策略，以及驱动映射与软件补偿叠加的实际效果。保留Singleton、DBService、点类默认值和运动SDK契约缺口；本文只证明已读调用链，不证明精度、稳定性或全部补偿业务完成。
