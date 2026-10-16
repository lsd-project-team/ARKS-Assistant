# 点胶与邦定相机标定：采样、拟合和保存

更新：2026-09-28。接续[标定主流程](calibration-module-review.md)，本轮只核查StartDispenseCalibTask和StartBondCalibTask及其网格、变换、文件导出调用。生产源码未修改，未运行标定。

## 执行摘要

- 点胶：收回测高气缸 → 移到标记中心 → 生成3×3网格 → 逐点移动、等待、模板定位 → 建立并保存VM相机坐标 → 计算Halcon仿射矩阵 → 移动探针并伸出气缸测高 → 更新高度/移安全Z → 保存运行参数 → 收回气缸 → 记录结果、返回true。
- 邦定：移到BMC测高位 → Touchdown测高并保存BMC设备参数 → 更新Z偏移、关闭工具真空 → 定位并居中BMC → 生成6行5列网格 → 逐点移动和定位 → 保存VM相机坐标 → 计算Halcon矩阵 → 再居中并更新位置 → 记录结果、返回true。此子任务末尾没有calibratePara.Save；总流程另有末尾保存。

## 采样、输入和决策

- [StartDispenseCalibTask samples and transform 170–248](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L170)：点胶固定模板名“点胶标定模板”，使用DispenseMarkVisionMachinePos与DispenseCalibDistance生成9点；配置DispensePRName调用在注释中，不能作为本路径实际模板来源。每点Sleep200后DoWork，非Success立刻false；缺少实体或类型异常进入外层catch。
- [StartBondCalibTask height and preparation 291–337](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L291)：先WithTDSensor测高，成功立即写BMCDevicePara.MeasureHeightResult并Save；失败弹窗false。由标定Z与测高差生成Z偏移，再LocatePosition/MoveToCamCenter/LocateAndMoveToTargetPixel更新中心。
- [GeneratePointList overloads 87–145](../../trunk/AKRS.ZX2200/CalibSystem/Services/CalibService.cs#L87)：外层行、内层列，X随列、Y随行递增，非蛇形。点胶为3×3=9点；邦定传distanceX=0.1、distanceY=0.05、numRows=6、numColumns=5，故30点。坐标单位遵循轴配置，未自行标成毫米。
- [StartBondCalibTask samples transform and finish 339–424](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L339)：邦定按BmcPRName逐点取PR、移动、等待并DoWork；任一点非Success即false。注释“调用9点标定”不是实际点数依据。
- 两路径world点使用计划网格位置减中心，而不是每点重新采集实际XY轴反馈；image点来自MatchResult.CenterX/Y。需验证跟随误差与采样时序，不能认定计划位置就是实测真值。

## 两套变换及保存顺序

- 相机坐标依赖分别为DispenseCameraCoordinateSystem→DispenseCoordinateSystem、BondCameraCoordinateSystem→BondCoordinateSystem；类型Vm。任务以Init(realPoints,imgPoints)初始化，再MachineCoordinateSystem.Save/Refresh。证据：[StartDispenseCalibTask samples and transform 170–248](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L170)、[StartBondCalibTask samples transform and finish 339–424](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L339)。
- [Init point lists 299–304](../../trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/BaseCoordinateSystem.cs#L299)：Init不仅更新内存点集，还直接调用TransformTool.Save。[Save calibration file 296–327](../../trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/TransformTool.cs#L296)：把virtually映射到图像坐标、reality映射到世界坐标，调用VisionDesigner CNPointCalibTool.Run并ExportCalibFile(name+.iwcal)。结果HomoMatrix被读入局部变量，未据此检查拟合残差或阈值。
- [NPointTrans 202–225](../../trunk/AKRS.ZX2200/CalibSystem/Services/CalibService.cs#L202)：将original与transformed各自拼接为HTuple，调用Halcon VectorToHomMat2d；任务传imagePoints→physicalPoints，故该矩阵是图像点到相对计划物理点。随后HomMat2dToAffinePar提取比例/角度/斜切/平移并生成展示值。VM文件与Halcon矩阵是两条计算输出，不能假定完全一致。
- 网格生成、NPointTrans和文件Save包装中未见点数一致性、退化几何、重投影误差的本地校验；SDK可能抛异常，其详细有效性规则仍待SDK契约核实。
- [CalibrateRunPara static constructor 15–23](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateRunPara.cs#L15)、[CalibratePara path 232–240](../../trunk/AKRS.ZX2200/Infrastructure/Models/Path/ZX2200PathConfig.cs#L232)：CalibrateRunPara继承外部Singleton并将FilePath设为DeviceDirPath/CalibratePara.json。trunk当前C#检索没有找到该Singleton基类实现，因此不能声明其Save为原子写、带备份或可恢复。不要把另一个SingletonJson类的实现当作它。

## 失败路径与完成边界

- [StartDispenseCalibTask height and save 250–284](../../trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs#L250)：气缸Open后测高失败直接false，跳过本方法后面的安全Z、Save和Close气缸；catch也只记日志/弹窗/false，无finally归位。测高下层是否自行清理尚待继续追踪，不能断言现场气缸一定保持伸出。
- 点胶VM坐标/.iwcal保存发生在测高之前，参数保存发生在成功测高之后；后续失败可以留下部分新文件/旧参数。邦定BMC设备参数更早就保存。没有跨这些调用的事务或回滚代码。
- 两个任务正常返回true意味着代码走到末尾，不代表满足误差规范、实机标定通过或配置全部原子提交。返回false也不表示没有改变任何参数。
- 成功路径向共享结果列表追加展示项；任务本身没有在入口清空列表，也没有显式互斥。应结合具体上层入口判断是否清空与防并发，不能从Singleton身份推断线程安全。

## 未完成项

- 上视、同标记、晶圆及多点子任务，居中迭代、测高下层恢复和轴同步契约。
- Singleton/JSON序列化、目录创建、旧文件覆盖行为、Halcon HTuple持久化及SDK异常/资源生命周期。
- 真实模板/配方/单位、采样质量与拟合残差验收；误差注入、失败恢复与实机测试。
- Archify专题图与主图同步；本次仅先完成可追溯的源码分析。
