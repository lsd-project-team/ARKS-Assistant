# 产品层级与产品坐标：源码复核

核对主程序 `trunk/AKRS.ZX2200` 与坐标库；trunk 保持只读。此文是已读代码的追溯记录，供 Archify 引用已提交事实；并未把未入 Git 的设备代码冒充仓库提交。原文件指纹、逐行范围与正文保存在 `frontend/scripts/knowledge/source-evidence.json`。

## 对象与父级

`TransportUnit.Init` 先建载具坐标，再按普通或异形结构创建基板，随后执行 ModifyMatter 并向 S2、S1 注入步骤。载具父级是查找得到的 TransportCoordinateSystem；基板、模块和焊点逐级传入父坐标对象。CreateMatterCoordinate 新建 GeneralCoordinateSystem 并 Init。父级引用用于之后的转换，不是把子级一次性复制成 G0 点。

依据：TransportUnit.cs 86–125、261–355；Substrate.cs 51–174；Module.cs 54–140；BondPosition.cs 40–81；TuService.cs 872–879。

## 展开与顺序

普通基板和模块在 IsMultiple=false 时把数量与行列设为 1，清空原坐标并补默认元素。按间距输入时，以首点加列间距和行间距，保留首点 Z、把新元素角度设为 0；实际对象数量仍取 Count。矩阵行列由 RowAndColumn 求值。WorkIndex 另由 GetIndex 使用八种起始方向及 Normal/Snake 分支计算；不能把加工序号当作物理坐标重排。

异形结构递归消费 DownConfigs，各层使用自己的 ElementCoordinate；焊点使用普通焊点配置列表或异形子列表。RowAndColumn 的两个蛇形奇偶分支化简后列值相同；RightDownToUp 的 GetIndex 蛇形奇偶分支也相同，图文按代码写，不补推测中的反转。ModifyMatter 写加工屏蔽状态，捕获异常时清空 OtherConfig 信息并保存 ProductConfiguration，没有把失败重新抛出。

依据：TransportUnit.cs 285–355；Substrate.cs 104–174；Module.cs 107–140；TuService.cs 49–86、98–260、887–956。

## 定位参考点与角度

CalculateOldPoint 与 CalculateNewPoint 分别读取示教点和结果点；X、Y 各自按 UseX/UseY 及 AdjustType 可用点数累加平均，没有启用分量时该值为 0，返回 Z=0。CalculateUpdateAngle 按 UseAngle 平均匹配角，转为弧度；第四点实际仍由 LocateUseConfig3.UseAngle 门控。

UpdateEntity 先清空四张结果图片，求新旧点，将匹配角取负并扣除父级 DegreeInG0。启用两点角度时，实际公式为 atan(atan2(newΔY,newΔX)−atan2(oldΔY,oldΔX))−父级角度，不能简写成标准两点角差。三/四点模式且启用拟圆时，改用前三点圆心作为新旧点，第四点不参与拟圆。

依据：TuService.cs 553–608、617–713、721–818、827–863。

## 更新、失败与后续使用

UpdateEntity 调用当前对象 CoordinateSystem.UpdateCoordinateSystem(oldPoint,newPoint,updateDegree)。该方法将新旧点分别经过当前坐标的一层 ForwardConvertCoordinate，得到差值；任一 XYZ 差值绝对值大于 10，或角度绝对值大于 0.2，先抛异常。这里是源码数值阈值，长度单位不从名称推定，角度用于 Sin/Cos。

检查通过后更新当前坐标 Distance.X/Y、Degree 和 Distance.Z。返回到 UpdateEntity 后才置 IsVisioned=true；异常时不会执行该末尾写入，但四张图片此前已清空，旧标志也没有在入口统一复位。子级仍持有此父坐标引用，后续 SelfPosToG0 沿链读取新值；更新不等于轴运动完成，也没有在这里保存配方。

TransportUnit.Refresh 则重建载具和现有子对象的坐标，清视觉和测高状态，复位 S1/S2 偏移标志；它与定位时更新当前坐标不同。S1 定位按点数调用 UpdateEntity；双点距离对话返回 None 时先屏蔽物料仍继续更新，Retry 回到首点，Abort 停机返回。

依据：TuService.cs 553–608；BaseCoordinateSystem.cs 204–236；GeneralCoordinateSystem.cs 44–68；TransportUnit.cs 135–142、362–367；Substrate.cs 182–208；Module.cs 148–173；System1Domain.cs 96–196。

## 工位偏移与焊点补偿

带工位参数的载具构造先 Init，再选择 SetSystem1OffSet 或 SetSystem2OffSet；各自有独立标志，已设置则返回，否则给载具 Distance 加工位偏移再置标志。两个标志不互相清除，也不能把 S2 设置理解为撤销 S1。分段正反移动按 Divide 配置给载具 X 加减 DistanceToRight。

焊点位置、角度与点胶位置、角度分别取普通 SingleBondPositionConfig 的 BondPosOffset/RotaryPosition、DispensePosOffset/DispenseRotaryPosition；普通配置为 null 时改取异形 Config 对应补偿。生产节点怎样叠加设备偏移、工具偏移和焊后补偿，引用 G0 专题已有生产应用，不在此重写机械运动算法。

依据：TransportUnit.cs 86–100、373–390、526–550；BondPosition.cs 254–291；G0 复核范围 g0-s1、g0-s2。

## 制作范围

对应清单 04.01–04.05。关系图复用真实 Archify 产品父链，另生成“定位结果更新产品坐标”图；整体关系、分支细节和异常写入分别阅读。尚未运行设备、实际视觉和机械运动，不能以静态图谱代替设备验收。
