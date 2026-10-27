# ZX2200 功能图谱清单

以 `trunk/AKRS.ZX2200` 为主程序，整理为 **45 个功能专题、241 条候选阅读内容**。这些条目用于覆盖功能和分支，制图时可以合并为关系图、流程图或时序图，不要求每条单独生成一张图。已有生产主流程和局部图继续复用。

G0 坐标、产品坐标、公共视觉、测高和安全移动先独立讲清，再由点胶、取晶、固晶等专题引用，公共过程只解释一次。

## 查找范围

核对日期：2026-10-27。主程序路径：`D:/agent_project/code_agent/trunk/AKRS.ZX2200`。工作区版本：`2a1fb1cf29bb08fb9356580e421c05066fbe5b43`；trunk 文件另以 SHA-256 清单固定。

- 排除 `bin`、`obj`、`.vs` 缓存，扫描 1,157 个 C# 文件，包含 341 个 Designer 文件。
- 与主工程逐项比较：1,137 个 Compile 文件均存在，其中 802 个非 Designer 文件、335 个 Designer 文件；另有 20 个 C# 文件未列入该工程。
- Roslyn 语法目录覆盖全部 1,157 个文件，无语法错误；主工程编译项包含 6,188 个方法声明，含界面生成方法。没有按方法数量推定功能数量。
- 从主窗体 Designer 提取 146 组文字与事件绑定，对应 140 个处理方法，均定位到源码；全部窗体共提取 1,440 组文字与事件绑定。该提取覆盖可匹配的显式文字和事件，不等于所有动态入口。
- 清单绑定 144 个源码文件、323 个方法位置，包含重载。G0 沿工程引用补查坐标库。
- 10 个直接 ProjectReference 中 9 个路径存在；Parameters 工程路径缺失，见依赖边界。

上述范围核对用于功能目录完整性；单条流程的全部条件、回调和跨库行为在制图时继续沿源码展开，不代表整机运行或全部分支已验收。

## 专题总览

| 类别 | 专题数 | 阅读条目 | 专题 |
| --- | ---: | ---: | --- |
| 基础功能 | 6 | 35 | 01 整机架构与启动；02 硬件配置与设备自检；03 G0 与设备坐标系统；04 产品层级与产品坐标；05 视觉模板与公共视觉流程；43 参数仓库与示教系统 |
| 标定与运动 | 5 | 28 | 06 相机与机械坐标标定；07 吸嘴顶针与三点一线校准；08 全局标定与扫描采集；09 光源控制与亮度标定；10 安全运动与连续轨迹 |
| 生产组织 | 3 | 16 | 11 配方与配置生命周期；12 工艺步骤与 S1 S2 调度；13 物料地图与加工状态 |
| 生产流程 | 2 | 11 | 14 轨道输送与工位交接；15 上下料仓与换层 |
| 供晶与取片 | 5 | 26 | 16 芯片载具与料片配置；17 机械换片与扩晶；18 搜晶与 WaferMap；19 顶针动作与顶针库；20 翻转供晶 |
| 加工动作 | 8 | 41 | 21 取晶动作与漏晶恢复；22 上视校正与芯片检测；23 IPT 中转台与下视校正；24 固晶动作与留晶处理；25 S1 点胶与胶量返工；26 S2 点胶与打印工具；27 蘸胶与刮胶盘；28 焊后检测与 BLT |
| 标定与检测 | 2 | 12 | 29 测高与测量工具；30 力控标定与反馈 |
| 维护功能 | 4 | 18 | 31 工具库与吸嘴更换；32 清嘴排胶与手动维护；37 耗材寿命与提醒；38 手动点动与状态面板 |
| 补偿与温控 | 4 | 21 | 33 焊后反馈与产品补偿；34 运动区域与实时位置补偿；35 温漂与取片位置补偿；36 加热预热与温度监控 |
| 运行与数据 | 4 | 22 | 39 报警互锁与运行监控；40 暂停停止与物料恢复；41 后台任务与保存退出；42 生产统计与日志查询 |
| 管理功能 | 1 | 5 | 44 用户权限与界面配置 |
| 实验诊断 | 1 | 6 | 45 精度实验与设备诊断 |

## 功能与流程目录

每条编号表示一项阅读任务，流程先后关系以该条对应源码为准；并列模式和互斥分支分开说明。

### 基础功能

#### 01 整机架构与启动

- 01.01 主程序与各 Domain、Controller、Module 的职责关系。
- 01.02 单实例、磁盘、数据迁移提示与软件授权检查。
- 01.03 PR、硬件、参数加载及主窗体启动。
- 01.04 在线、离线与 DryCycle 运行模式入口。

源码入口：[Program.Main](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Program.cs:63)；[MainForm.MainForm_Load](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Controls/MainForm.cs:232)；[Machine.Operate.StartBackGroundThread](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:662)。


#### 02 硬件配置与设备自检

- 02.01 硬件名称与设备模块配置对应。
- 02.02 按配置检查轴、相机、气缸和传感器。
- 02.03 整机自检项目、结果汇总与失败返回。
- 02.04 回零执行、回零标记与初始化就绪判断。

源码入口：[Machine.SelfCheck.SelfCheck](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.SelfCheck.cs:48)；[Machine.Operate.AllAxisGoHome](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:504)；[FrmMachineHardWareConfig.BtSave_Click](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Machine/Control/FrmMachineHardWareConfig.cs:44)。


#### 03 G0 与设备坐标系统

- 03.01 G0、普通坐标与从属坐标的关系。
- 03.02 坐标 JSON 加载、父级绑定、创建、查找、刷新和保存。
- 03.03 本地坐标逐级转换为 G0。
- 03.04 G0 逆序转换为本地坐标。
- 03.05 像素坐标结合拍照时轴位置转换为 G0。
- 03.06 平移、旋转、Z 偏移与角度累积。
- 03.07 General、VM 和其他标定类型的转换分支。
- 03.08 标定文件和转换工具的载入与缓存。
- 03.09 父级缺失、首次创建 G0、删除接口和未实现逆变换的边界。
- 03.10 点胶、焊头、晶圆模块消费 G0 的入口。

源码入口：[MachineCoordinateSystem.Load](D:/agent_project/code_agent/trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/MachineCoordinateSystem.cs:49)、[MachineCoordinateSystem.CreateCoordinateSystem](D:/agent_project/code_agent/trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/MachineCoordinateSystem.cs:104)；[GeneralCoordinateSystem.SelfPosToG0](D:/agent_project/code_agent/trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/GeneralCoordinateSystem.cs:44)、[GeneralCoordinateSystem.G0PosToSelf](D:/agent_project/code_agent/trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/GeneralCoordinateSystem.cs:76)；[DependentCoordinateSystem.SelfPosToG0](D:/agent_project/code_agent/trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/DependentCoordinateSystem.cs:43)；[DispenseController.ConvertVisionResultInG0](D:/agent_project/code_agent/trunk/AKRS.ZX2200/DispenseSystem/Controllers/DispenseController.cs:791)；[BondModuleController.ConvertPixelToG0Pos](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/BondModuleController.cs:221)；[BaseCoordinateSystem.ForwardConvertCoordinate](D:/agent_project/code_agent/trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/BaseCoordinateSystem.cs:84)、[BaseCoordinateSystem.BackConvertCoordinate](D:/agent_project/code_agent/trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/BaseCoordinateSystem.cs:140)、[BaseCoordinateSystem.UpdateCoordinateSystem](D:/agent_project/code_agent/trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/BaseCoordinateSystem.cs:204)；[TransformTool.LoadVmProcedure](D:/agent_project/code_agent/trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/TransformTool.cs:122)、[TransformTool.GetCCalibTransTool](D:/agent_project/code_agent/trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/TransformTool.cs:168)、[TransformTool.GetPoint3D](D:/agent_project/code_agent/trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/TransformTool.cs:182)。

实现边界：核心实现需沿 ProjectReference 阅读坐标工程。普通坐标的逐级变换与从属坐标两层组合分开绘制；从属 G0PosToSelf 当前仅返回新建点。 DeleteCoordinateSystem 当前只调用保存并返回 false，没有执行删除。


#### 04 产品层级与产品坐标

- 04.01 载具、基板、模块、焊点的对象和坐标继承关系。
- 04.02 矩阵、蛇形顺序、异形结构的实例展开。
- 04.03 定位点使用规则及新旧位置、角度计算。
- 04.04 定位结果更新父子坐标与后续目标点。
- 04.05 S1、S2 偏移和焊点位置、旋转补偿的来源。

源码入口：[TransportUnit.InitTransportUnitCoordinateSystem](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/TransportUnit.cs:261)、[TransportUnit.InitSubstrateCoordinateSystem](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/TransportUnit.cs:285)；[TuService.CalculateNewPoint](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs:617)、[TuService.CreateMatterCoordinate](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs:872)、[TuService.ModifyMatter](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs:887)；[BondPosition.GetPositionCompensate](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/BondPosition.cs:265)。


#### 05 视觉模板与公共视觉流程

- 05.01 配方视觉名称收集、方案载入与初始化结果。
- 05.02 相机、曝光、灯光设置与图像采集。
- 05.03 定位与缺陷检测结果分流、距离校验。
- 05.04 载具、基板、模块、焊点的视觉调用关系。
- 05.05 身份识别与墨点节点的门控、状态写入和实际实现边界。
- 05.06 视觉失败的报警对话、重试、跳过与修改模板。

源码入口：[VisionService.Vision](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Service/VisionService.cs:78)、[VisionService.VisionDefect](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Service/VisionService.cs:158)、[VisionService.DistanceCheck](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Service/VisionService.cs:257)；[System2Controller.Vision.AdjustAction](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.Vision.cs:58)、[System2Controller.Vision.BacksideCrackDetect](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.Vision.cs:737)；[FrmVisionAlarm.BtOK_Click](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/FrmVisionAlarm.cs:339)、[FrmVisionAlarm.BtSkip_Click](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/FrmVisionAlarm.cs:505)；[System1Domain.MatterIdentity](D:/agent_project/code_agent/trunk/AKRS.ZX2200/DispenseSystem/Models/System1Domain.cs:553)。

实现边界：CheckInkDotActionNode.DoWork 当前直接返回 Success；不能据此声称完成墨点识别。身份识别和供晶 Nine 中的墨点方法分别沿实际调用绘制。


#### 43 参数仓库与示教系统

- 43.01 设备参数、配方参数、数据集和仓库的归属。
- 43.02 参数反射、分组树、搜索与编辑器选择。
- 43.03 参数修改事件、单位、保存与取消。
- 43.04 示教步骤状态、前进后退、跳过和完成。
- 43.05 共享数据集筛选、添加、删除与配方关联。
- 43.06 参数迁移提示和设备信息重置。

源码入口：[ParamService.GetAllParamMappings](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Parameters/Service/ParamService.cs:43)、[ParamService.Search](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Parameters/Service/ParamService.cs:272)、[ParamService.LoadCurrentEditors](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Parameters/Service/ParamService.cs:429)；[FrmParamManager.EditorValueChanged](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Parameters/FrmParamManager.cs:380)、[FrmParamManager.ChoseEditor](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Parameters/FrmParamManager.cs:496)；[BaseSettingRepository.GetDataSourceByCurrentRecipe](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Models/BaseModels/BaseSettingRepository.cs:124)；[ObjectHelper.SaveAll](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Utils/ObjectHelper.cs:863)、[ObjectHelper.Cancel](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Utils/ObjectHelper.cs:901)；[Machine.SelfCheck.JudgeDataMigrated](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.SelfCheck.cs:563)、[Machine.SelfCheck.ReSetMachineInfo](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.SelfCheck.cs:535)。


### 标定与运动

#### 06 相机与机械坐标标定

- 06.01 系统自动标定各子任务的调度顺序。
- 06.02 点胶与 Bond 相机采点、比例和坐标建立。
- 06.03 上视相机坐标及机械拍照位置标定。
- 06.04 晶圆相机、晶圆台与 N 点标定。
- 06.05 焊头到相机偏移和旋转中心标定。
- 06.06 标定成功、参数更新、文件保存与最后复核的先后顺序。
- 06.07 自动对焦、对中和目标像素移动的公共调用。

源码入口：[CalibrateTask.StartAutoCalib](D:/agent_project/code_agent/trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs:2275)、[CalibrateTask.StartDispenseCalibTask](D:/agent_project/code_agent/trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs:170)、[CalibrateTask.StartBondCalibTask](D:/agent_project/code_agent/trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs:291)、[CalibrateTask.StartUpLookCalibTask](D:/agent_project/code_agent/trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs:486)、[CalibrateTask.StartWaferNPointCalibTask](D:/agent_project/code_agent/trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs:794)、[CalibrateTask.StartBondToCamCalibTask1](D:/agent_project/code_agent/trunk/AKRS.ZX2200/CalibSystem/Models/CalibrateTask.cs:1834)；[CalibController.AutoFocus](D:/agent_project/code_agent/trunk/AKRS.ZX2200/CalibSystem/Services/CalibController.cs:273)、[CalibController.LocateAndMoveToTargetPixel](D:/agent_project/code_agent/trunk/AKRS.ZX2200/CalibSystem/Services/CalibController.cs:161)。


#### 07 吸嘴顶针与三点一线校准

- 07.01 吸嘴中心与高度示教、自动校准。
- 07.02 单顶针及全部顶针配置校准。
- 07.03 取片偏移校准与准备门控。
- 07.04 系统 2 三点一线校准的组合顺序。
- 07.05 校准取消、工具更换与结果保存。

源码入口：[FrmSystem2Calibrate.BtnCaliNozzle_Click](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Calibrate/FrmSystem2Calibrate.cs:130)、[FrmSystem2Calibrate.BtnCaliEjection_Click](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Calibrate/FrmSystem2Calibrate.cs:286)、[FrmSystem2Calibrate.BtnCaliPickOffset_Click](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Calibrate/FrmSystem2Calibrate.cs:362)、[FrmSystem2Calibrate.BtnCaliAll_Click](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Calibrate/FrmSystem2Calibrate.cs:462)；[System2Controller.AutoCali.NozzleCaliAssistance](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.AutoCali.cs:389)、[System2Controller.AutoCali.AllEjectionsCaliAssistance](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.AutoCali.cs:592)。


#### 08 全局标定与扫描采集

- 08.01 扫描范围、预定义点及补偿区域建立。
- 08.02 X、Y 比例与二维平台采集。
- 08.03 普通扫描、温漂采集、带补偿扫描及暂停停止。
- 08.04 点序与区域排序、扫描清单导入导出。
- 08.05 标定数据生成、ETEL 或固高补偿开关及下载。
- 08.06 Bond 偏移标定、校验与 BC 偏移关系计算。

源码入口：[FrmGlobalCalibration.GlobalCalibration](D:/agent_project/code_agent/trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs:168)、[FrmGlobalCalibration.Mapping2DCalibration](D:/agent_project/code_agent/trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs:581)、[FrmGlobalCalibration.SaveData](D:/agent_project/code_agent/trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs:1264)；[FrmGlobalCalibrationEx.ScanPoints](D:/agent_project/code_agent/trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs:659)、[FrmGlobalCalibrationEx.ScanPointsWithCompensation](D:/agent_project/code_agent/trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs:882)；[FrmBondCompensateCalibration.StartBondCompensateCalibration](D:/agent_project/code_agent/trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmBondCompensateCalibration.cs:217)；[BCOffsetRelationModel.GetΔXY](D:/agent_project/code_agent/trunk/AKRS.ZX2200/CalibSystem/GlobalCalibrationEnd/BCOffsetRelationCalib/BCOffsetRelationModel.cs:66)。


#### 09 光源控制与亮度标定

- 09.01 各相机红绿蓝环光、点光的硬件对应。
- 09.02 灯光亮度手动调整与同步。
- 09.03 点胶和 Bond 亮度映射采集、补全与保存。
- 09.04 正反向亮度映射在视觉流程中的应用。

源码入口：[FrmLightnessCalibTeach.InitControl](D:/agent_project/code_agent/trunk/AKRS.ZX2200/CalibSystem/Controls/Assistant/FrmLightnessCalibTeach.cs:239)；[LightCalibrationPara.ApplyLightMapping](D:/agent_project/code_agent/trunk/AKRS.ZX2200/CalibSystem/Models/LightCalibrationPara.cs:364)、[LightCalibrationPara.ApplyLightMappingReverse](D:/agent_project/code_agent/trunk/AKRS.ZX2200/CalibSystem/Models/LightCalibrationPara.cs:409)；[UcLight.ChangeIntensity](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/UcLight.cs:311)。


#### 10 安全运动与连续轨迹

- 10.01 机械目标与 G0 目标的转换及软限位检查。
- 10.02 二维、三维、四维安全位与高度动作顺序。
- 10.03 取片、固晶、上视、IPT 和换嘴区域间的运动。
- 10.04 碰撞圆、运动区域及路径交点计算。
- 10.05 插补组、连续轨迹与驱动分支选择。
- 10.06 发指令、等待到位、异常和停止的不同完成边界。

源码入口：[BondModuleController.MovementRelated.MoveSafeBondXYZ](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/BondModuleController.MovementRelated.cs:49)、[BondModuleController.MovementRelated.MoveSafeBondXYZT](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/BondModuleController.MovementRelated.cs:186)、[BondModuleController.MovementRelated.MoveToPickupPos](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/BondModuleController.MovementRelated.cs:773)；[MotionPlanDomain.GetMoveParaByDistance](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/MotionPlan/MotionPlanDomain.cs:100)、[MotionPlanDomain.GetMoveLine](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/MotionPlan/MotionPlanDomain.cs:265)；[GuGaoDrive.ContinueInterpolationMove](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Utils/GuGaoDrive.cs:46)、[GuGaoDrive.PickContinueInterpolationMove](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Utils/GuGaoDrive.cs:1600)；[WaferTableController.IsInCollisionCircle](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferTableController.cs:1710)。


### 生产组织

#### 11 配方与配置生命周期

- 11.01 程式创建、复制、加载、编辑与删除的主程序入口。
- 11.02 当前配方身份、共享数据集和仓库对象的绑定。
- 11.03 集中保存、切换与重载时的对象更新。
- 11.04 运行任务上下文与新配方的重新绑定关系。
- 11.05 示教完成状态、步骤重置、跳过与生产可用性检查。

源码入口：[UcMainSystem.BtNewProduct_ItemClick](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs:320)、[UcMainSystem.BarBtLoad_ItemClick](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs:804)、[UcMainSystem.BarBtRecipeManage_ItemClick](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs:930)、[UcMainSystem.BtSave_ItemClick](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs:632)；[UcMainSystem.Production.ReLoadRecipe](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs:137)；[UcEditProductProgramming.Start](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Controls/Feature/EditProgram/UcEditProductProgram/UcEditProductProgramming.cs:1138)、[UcEditProductProgramming.BtReset_Click](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Controls/Feature/EditProgram/UcEditProductProgram/UcEditProductProgramming.cs:936)。

实现边界：配方管理窗体和部分文件机制来自引用库；先画本工程入口、对象绑定及结果消费，库内部另列待展开。


#### 12 工艺步骤与 S1 S2 调度

- 12.01 工艺编辑、自动生成与生产准备检查。
- 12.02 八种排序配置与动作消息的展开。
- 12.03 视觉、测高、识别、点胶和固晶节点的映射与互斥。
- 12.04 相对贴片排序、禁用步骤过滤及步骤注入。
- 12.05 消息完成、焊点步骤完成和载具放行的关系。
- 12.06 单步、循环次数、仅点胶或仅固晶模式的门控。

源码入口：[ProcessDomain.AutoGenerateProcessStep](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Machine/Process/ProcessDomain.cs:283)、[ProcessDomain.CheckIsReady](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Machine/Process/ProcessDomain.cs:179)；[S1ActionNodeController.Init](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Machine/Process/S1ActionNodeController.cs:168)、[S1ActionNodeController.InjectSteps](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Machine/Process/S1ActionNodeController.cs:859)、[S1ActionNodeController.Finish](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Machine/Process/S1ActionNodeController.cs:749)；[S2ActionNodeController.SortRelativeBond](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs:1440)、[S2ActionNodeController.RemoveDisableActionNode](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs:1554)、[S2ActionNodeController.InitCurrentMessage](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs:930)；[ActionNodesSortService.SortBondPositionActionNode](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Service/ActionNodesSortService.cs:25)。


#### 13 物料地图与加工状态

- 13.01 载具、基板、模块、焊点的启用、禁用及仅加工状态。
- 13.02 S1 S2 步骤完成和剩余步骤的传播。
- 13.03 地图读取、保存及芯片映射恢复。
- 13.04 人工框选、状态修改与重新加工入口。
- 13.05 载具标识、加工数据导出与当前物料清理。

源码入口：[TuService.SaveMappingToLocal](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs:1385)、[TuService.ReadTransportMapping](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs:1800)、[TuService.ReadTransportMappingByComponent](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs:1953)；[BondPosition.S1FinishedStep](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/BondPosition.cs:168)、[BondPosition.S2FinishedStep](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/BondPosition.cs:177)、[BondPosition.SetMatterDisable](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/BondPosition.cs:205)；[MappingDraw.ChangeMatterProduct](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Mapping/MappingDraw.cs:314)；[FrmTransportUnitMapping.BtImportMapping_Click](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Mapping/FrmTransportUnitMapping.cs:88)。


### 生产流程

#### 14 轨道输送与工位交接

- 14.01 输送启动、段内物料映射与清空轨道。
- 14.02 自动上料机或皮带进入 S1。
- 14.03 S1 段间移动与 S1 到 S2 交接。
- 14.04 S2 到等待区、出料皮带及自动收板。
- 14.05 夹紧、阻挡、升降、真空与到位检测。
- 14.06 普通生产和 DryRun 的分支、握手与超时恢复。

源码入口：[TransportController.InitializeTS](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs:159)、[TransportController.TransferLoadBeltToDispense](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs:558)、[TransportController.TransferDispenseToBond](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs:1266)、[TransportController.TransferBondToWaitingUnload](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs:1531)、[TransportController.TransferUnloadBeltToAutoUnloader](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs:2292)；[TransportTask.Start](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:115)、[TransportTask.StartDryRun](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs:775)；[BondSubSectionController.Clamp](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportSystem/Controllers/BondSubSectionController.cs:136)、[BondSubSectionController.OpenVacuumAndCheck](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportSystem/Controllers/BondSubSectionController.cs:725)。


#### 15 上下料仓与换层

- 15.01 料仓几何、层高和推料位置示教。
- 15.02 A B 仓选择、当前层初始化与换仓。
- 15.03 上料仓推板到 S1 的许可和状态推进。
- 15.04 等待区向下料仓收板与层号推进。
- 15.05 空仓、满仓、推杆安全及人工指定层操作。

源码入口：[LoaderBinController.MoveToCurrentPlaceLayer](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportSystem/Controllers/LoaderBinController.cs:449)、[LoaderBinController.MoveToNextPlaceLayer](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportSystem/Controllers/LoaderBinController.cs:542)、[LoaderBinController.IsPushRodSafe](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportSystem/Controllers/LoaderBinController.cs:397)；[UnLoaderBinController.MoveToNextPlaceLayer](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportSystem/Controllers/UnLoaderBinController.cs:494)、[UnLoaderBinController.IsUnloaderFull](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportSystem/Controllers/UnLoaderBinController.cs:328)；[LoaderTask.Start](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportSystem/Tasks/LoaderTask.cs:49)；[UnloaderTask.Start](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportSystem/Tasks/UnloaderTask.cs:41)。


### 供晶与取片

#### 16 芯片载具与料片配置

- 16.01 芯片类型、Wafer Waffle 载体和几何参数配置。
- 16.02 料盒层、适配器、槽位和静态 Waffle 的对应。
- 16.03 载体上料、槽扫描、槽状态与供料选择。
- 16.04 芯片尺寸、步距、边界、墨点和搜索信息示教。
- 16.05 当前需求芯片与当前料片切换、选择一致性。

源码入口：[MagazineAllocationsProgram.GetCarriers](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Models/Programs/MagazineAllocationsProgram.cs:38)、[MagazineAllocationsProgram.GetAdapterConfig](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Models/Programs/MagazineAllocationsProgram.cs:71)；[StaticAdapterProgram.GetCarriers](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Models/Programs/StaticAdapterProgram.cs:39)；[MagazineController.SlotScan](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Controllers/MagazineController.cs:280)；[FrmChooseWafer.InitControl](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Controls/Assistant/ComponentsTeach/FrmChooseWafer.cs:57)。


#### 17 机械换片与扩晶

- 17.01 手动换片、自动换片及重试入口。
- 17.02 料盒、夹爪、重夹持位置及晶圆台的安全运动许可。
- 17.03 料片从槽位取出、放回及在台检测。
- 17.04 扩晶升降、压紧、真空与热风动作。
- 17.05 换片后的地图初始化、后处理与供晶放行。

源码入口：[WaferSubSystemTask.ChangeTabletManual](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs:1000)、[WaferSubSystemTask.ChangeTabletAuto](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs:1105)、[WaferSubSystemTask.ChangeSucceedOperation](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs:488)；[WaferTableController.ActionWaferClampPlaceWaferInSlot](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferTableController.cs:642)、[WaferTableController.ActionWaferClampRemoveWaferFromSlot](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferTableController.cs:723)、[WaferTableController.MoveExpandToUpPosition](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferTableController.cs:372)、[WaferTableController.ActionHotBlowerOfLoad](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferTableController.cs:595)；[MagazineController.CheckWaferPushCylinderAllowMagazineLiftAction](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Controllers/MagazineController.cs:481)。

实现边界：ChangeSucceedOperation 的 ManualAtStart 分支当前显式抛异常，不列为已实现的自动换片后启动方式。


#### 18 搜晶与 WaferMap

- 18.01 Single 搜索边界、方向、换行与跳步。
- 18.02 Nine 邻点缓存、备用点及空白计数。
- 18.03 WaferMap 参考点、预取、寻路与地图推进。
- 18.04 Box 和静态 Waffle 槽位蛇形选择。
- 18.05 墨点、视觉失败、换料标记和停止出口。
- 18.06 芯片视觉中心、取片补偿及实际取片后的地图提交。

源码入口：[Block.SearchSingle.SearchSingle](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.SearchSingle.cs:35)；[Block.SearchNine.SearchNine](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.SearchNine.cs:39)、[Block.SearchNine.DetectInkDot](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.SearchNine.cs:504)；[Block.SearchMapping.SearchMapping](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.SearchMapping.cs:46)、[Block.SearchMapping.RemeberPickedDieInfo](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.SearchMapping.cs:510)；[Block.SearchDieBox.SearchDieBox](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.SearchDieBox.cs:48)；[Block.MoveDieToPickCenter](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.cs:1045)。

实现边界：WaferMap 双点、MultipleSearch 和关闭位置搜索等分支存在显式抛异常；支持的搜索模式须按当前分支分别标注。


#### 19 顶针动作与顶针库

- 19.01 顶针配置、工作槽及寿命计数。
- 19.02 顶针、顶针台和晶圆相机高度关系。
- 19.03 就绪、顶起、安全返回与同步 Z 运动。
- 19.04 顶针更换、归还、锁紧、真空及吹气。
- 19.05 顶针架 T 轴、碰撞与安全位置检查。

源码入口：[EjectController.ChangeEjection](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Controllers/EjectController.cs:452)、[EjectController.ReturnEjection](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Controllers/EjectController.cs:605)、[EjectController.MoveEjectToLiftPosition](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Controllers/EjectController.cs:227)、[EjectController.MoveEjectionAxisZToG0Pos](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Controllers/EjectController.cs:774)；[BondHeadController.SynchronousEjection](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs:1091)；[EjectionBankProgram.GetEjectFrequencyList](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Models/Programs/EjectionBankProgram.cs:57)。


#### 20 翻转供晶

- 20.01 翻转工具几何与翻转到晶圆位置示教。
- 20.02 从晶圆台取晶、翻转与转交焊头。
- 20.03 真空检测、漏晶重测、重取及下一颗处理。
- 20.04 吹气、抛料、安全返回及 DryRun 分支。
- 20.05 翻转任务与焊头的需求和可取料信号。

源码入口：[WaferSubController.FlipChipAction](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferSubController.cs:229)、[WaferSubController.FlipFromWaferTable](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferSubController.cs:509)；[FlipTask.DoWork](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Tasks/FlipTask.cs:57)；[FlipTableController.Throw](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Controllers/FlipTableController.cs:237)、[FlipTableController.MoveFlipToTransferPos](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Controllers/FlipTableController.cs:126)。


### 加工动作

#### 21 取晶动作与漏晶恢复

- 21.01 晶圆台、翻转台、静态 Waffle 三种取晶入口。
- 21.02 取晶位置、角度、温漂偏移及运动参数形成。
- 21.03 慢下、接触、吸真空、顶针配合和慢上。
- 21.04 漏晶判断、重新检测、重取、抛料、跳过与停止。
- 21.05 可用计数、后台通知、供晶信号和步骤提交顺序。

源码入口：[PickActionNode.DoWork](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs:156)、[PickActionNode.Pick](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs:587)；[PickActionNode.Provider.PrepareBeforePickAction](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs:55)、[PickActionNode.Provider.EjectionLift](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs:715)、[PickActionNode.Provider.SendSignalToWaferTable](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs:633)；[BondHeadController.PickAction](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs:97)、[BondHeadController.ComponentCheckAfterPickup](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs:576)。


#### 22 上视校正与芯片检测

- 22.01 按来源选择上视位置和安全运动。
- 22.02 单点、双点或代码视觉校正分支。
- 22.03 识别角度、旋转中心和贴片偏移的组合。
- 22.04 尺寸、背崩、胶印等检测与结果消费。
- 22.05 温漂补偿调用、失败重试和校正状态写入。

源码入口：[UpLookCorrectionActionNode.DoWork](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs:131)、[UpLookCorrectionActionNode.UpLookVision](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs:1375)、[UpLookCorrectionActionNode.UpLookVisionByCode](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs:1617)；[System2Controller.Vision.UpLookCameraVision](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.Vision.cs:506)、[System2Controller.Vision.BacksideCrackDetect](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.Vision.cs:737)；[System2Controller.Assistant.UplookVisionAction](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.Assistant.cs:950)。


#### 23 IPT 中转台与下视校正

- 23.01 中转台位置、真空、吹气及旋转示教。
- 23.02 取晶后移动到 IPT 并放置芯片。
- 23.03 下视拍照、位置计算与再次取晶。
- 23.04 放置与取片前的焊头清零及力控。
- 23.05 IPT 供料通知、DryRun 与失败返回。

源码入口：[SubstrateCameraCorrectionActionNode.DoWork](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.cs:136)、[SubstrateCameraCorrectionActionNode.DownLookVision](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.cs:546)、[SubstrateCameraCorrectionActionNode.Place](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.cs:709)、[SubstrateCameraCorrectionActionNode.Pick](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.cs:779)；[SubstrateCameraCorrectionActionNode.MoveHelper.MoveToIPT](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.MoveHelper.cs:51)、[SubstrateCameraCorrectionActionNode.MoveHelper.JumpToPickIPTPos](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.MoveHelper.cs:572)；[IPTController.IPTRotary](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/IPTController.cs:73)、[IPTController.OpenIPTVacuum](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/IPTController.cs:22)。


#### 24 固晶动作与留晶处理

- 24.01 焊点 G0 目标、上视修正及各类补偿汇合。
- 24.02 预贴片、安全跳转、旋转和下降运动。
- 24.03 距离模式或力控模式的放片、吹气与抬升。
- 24.04 固晶后持晶检查、留晶重做与停止。
- 24.05 次数记录、力曲线、焊点提交和后台动作顺序。

源码入口：[BondActionNode.DoWork](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.cs:118)、[BondActionNode.Bond](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.cs:467)；[BondActionNode.Provider.CalculateBondPos](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.Provider.cs:498)、[BondActionNode.Provider.CheckBondedNumber](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.Provider.cs:310)、[BondActionNode.Provider.BlowAsyn](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.Provider.cs:338)；[BondHeadController.BondAction](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs:397)、[BondHeadController.ComponentCheckAfterBonding](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs:600)。


#### 25 S1 点胶与胶量返工

- 25.01 S1 来料、动作循环、分段交互与任务退出。
- 25.02 预点胶触发、排胶、试胶板索引及胶板用尽处理。
- 25.03 胶型点位、缩放旋转、点胶偏移和高度生成。
- 25.04 单点、线段与不同驱动的插补出胶。
- 25.05 胶压、电磁阀与打印工具控制。
- 25.06 胶量检查、确认、重新点胶、步骤提交与放行。

源码入口：[DispenseWorkTask.DoWork](D:/agent_project/code_agent/trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs:63)；[PredispenseAction.DoWork](D:/agent_project/code_agent/trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/OtherAction/PredispenseAction.cs:74)、[PredispenseAction.EpoxySqueeze](D:/agent_project/code_agent/trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/OtherAction/PredispenseAction.cs:258)；[DispenseController.InterpolationApplication](D:/agent_project/code_agent/trunk/AKRS.ZX2200/DispenseSystem/Controllers/DispenseController.cs:300)；[DispenserMoveHelper.EpoxyPretreatment](D:/agent_project/code_agent/trunk/AKRS.ZX2200/DispenseSystem/Services/DispenserMoveHelper.cs:327)；[S1DispenseDefectActionNode.ReDispense](D:/agent_project/code_agent/trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/DispenseBPAction/S1DispenseDefectActionNode.cs:190)。


#### 26 S2 点胶与打印工具

- 26.01 S2 点胶与固晶工艺的调用关系。
- 26.02 随焊头移动的点胶、视觉与测高位置转换。
- 26.03 S2 预点胶、试胶板索引与重试。
- 26.04 S2 插补出胶、胶压和测高气缸控制。
- 26.05 打印工具连续运动、停止及手动操作。

源码入口：[S2DispenseController.InterpolationApplication](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/S2DispenseController.cs:226)、[S2DispenseController.PrintEpoxy](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/S2DispenseController.cs:809)、[S2DispenseController.PrintToolContinueMove](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/S2DispenseController.cs:867)；[S2DispenseActionNode.DoWork](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/DispenseAction/S2DispenseActionNode.cs:49)；[S2PreDispenseActionNode.DoWork](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/DispenseAction/S2PreDispenseActionNode.cs:70)、[S2PreDispenseActionNode.EpoxySqueeze](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/DispenseAction/S2PreDispenseActionNode.cs:265)；[UcS2DispenseManual.BtPreDispense_Click](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controls/Manual/UcS2DispenseManual.cs:161)。

实现边界：S2EpoxyDefectActionNode 为空派生类，继承公共 ActionNode 的默认成功返回；实际胶检需从预点胶或焊后检测等调用链分别展开。


#### 27 蘸胶与刮胶盘

- 27.01 胶盘工作位置、蘸胶高度与参数示教。
- 27.02 刮胶盘伸出、归位、刮胶与后台任务握手。
- 27.03 取晶后移动、蘸胶与后续上视固晶的衔接。
- 27.04 蘸胶后的胶印检查和返回结果消费。
- 27.05 手动自动刮胶与 DryRun 边界。

源码入口：[SlideFluxerController.SlideFlux](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/SlideFluxerController.cs:140)；[SlideFluxerTask.DoWork](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Tasks/SlideFluxerTask.cs:92)；[System2Controller.DipFlux](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.cs:1278)；[DipFluxActionNode.DoWork](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/DipFluxActionNode.cs:105)、[DipFluxActionNode.DipFluxActionDryRun](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/DipFluxActionNode.cs:704)。

实现边界：DipFluxActionDryRun 第一条有效语句直接抛出待验证异常，后面的动作不可作为正常空跑流程绘制。


#### 28 焊后检测与 BLT

- 28.01 检测频率和配方开关的门控。
- 28.02 胶量、焊后位置、背崩等不同检测路径。
- 28.03 BLT 测量、阈值与人工选择。
- 28.04 检测失败、重新点胶、拾回与重做。
- 28.05 检测结果缓存、统计记录与补偿输入。

源码入口：[AfterBondCheckActionNode.DoWork](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/AfterBondCheckActionNode.cs:112)、[AfterBondCheckActionNode.BLTCheck](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/AfterBondCheckActionNode.cs:776)、[AfterBondCheckActionNode.ReDispense](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/AfterBondCheckActionNode.cs:592)、[AfterBondCheckActionNode.PickUpDie](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/AfterBondCheckActionNode.cs:677)、[AfterBondCheckActionNode.PostBondDefect](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/AfterBondCheckActionNode.cs:711)；[FrmAssistantBLT.InitControl](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controls/Assistant/FrmAssistantBLT.cs:120)；[FrmPostBondData.InitControl](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controls/Setting/PostBond/FrmPostBondData.cs:51)。


### 标定与检测

#### 29 测高与测量工具

- 29.01 S1 探针气缸测高与结果回写。
- 29.02 S2 激光、力控测高及在途测高。
- 29.03 载具、基板、模块、焊点多点测高与平面插值。
- 29.04 固晶水平、S1 S2 平面度的示教、测量与复测。
- 29.05 距离、焊头标准量块及多高度测量工具。
- 29.06 测量结果展示、范围统计和导出。

源码入口：[DispenseMeasureHeightController.DispenserHeightMeasurementG0](D:/agent_project/code_agent/trunk/AKRS.ZX2200/DispenseSystem/Controllers/DispenseMeasureHeightController.cs:175)；[BondHeadController.MeasureHeight](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs:640)；[S2DispenseController.LaserMeasureHeightInGo](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/S2DispenseController.cs:155)；[UcMeasuringTool.BtMultipleHeightMeasurement_Click](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Controls/Feature/MeasuringTool/UcMeasuringTool.cs:48)、[UcMeasuringTool.BtDistanceMeasurement_Click](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Controls/Feature/MeasuringTool/UcMeasuringTool.cs:73)；[FrmBondLevel.Measure](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/LevelMeasurementSystem/Controls/BondLevelMeasure/FrmBondLevel.cs:75)。


#### 30 力控标定与反馈

- 30.01 压力计和焊头 Modbus 连接、清零与采集。
- 30.02 闭环与音圈电机的不同标定入口。
- 30.03 ETEL 固高、大小力区间及角度对应标定。
- 30.04 输入力、实际力、增量和初始值转换。
- 30.05 取放力控设定、复位和焊头清零。
- 30.06 力 LVDT 实时曲线、检测结果与导出。

源码入口：[ClosedLoopCalibrationController.GTDoWork](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/BondForce/Controllers/ClosedLoopCalibrationController.cs:111)、[ClosedLoopCalibrationController.EtelDoWork](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/BondForce/Controllers/ClosedLoopCalibrationController.cs:252)、[ClosedLoopCalibrationController.RecordForceInitialValWithAngle](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/BondForce/Controllers/ClosedLoopCalibrationController.cs:614)；[VoiceCoilMotorCalibrationController.DoWork](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/BondForce/Controllers/VoiceCoilMotorCalibrationController.cs:118)；[ForceCalibrationService.ActualForceToInputForce](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/BondForce/Services/ForceCalibrationService.cs:35)；[BondHeadController.ForceRelated.ForceControlSet](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.ForceRelated.cs:119)、[BondHeadController.ForceRelated.ForceControlReset](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.ForceRelated.cs:851)、[BondHeadController.ForceRelated.ZeroBondhead](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.ForceRelated.cs:1072)；[ModbusService.ConnectManometer](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/BondForce/Modbus/ModbusService.cs:57)、[ModbusService.ReadBondForce](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/BondForce/Modbus/ModbusService.cs:190)。


### 维护功能

#### 31 工具库与吸嘴更换

- 31.01 吸嘴、工具槽、TouchDown BMC 工具及当前工具的对应。
- 31.02 工具几何、高度、对中与工具库位置示教。
- 31.03 取嘴、还嘴、自动判断换嘴及参数更新。
- 31.04 工具在位、工具库回零、真空与安全高度检查。
- 31.05 工具重复动作测试与人工操作入口。

源码入口：[System2Controller.TakeNozzle](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.cs:157)、[System2Controller.PutbackNozzle](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.cs:579)、[System2Controller.ChangeNozzle](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.cs:898)、[System2Controller.JudgeAndChangeNozzle](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.cs:1008)；[NozzleShelfController.CheckToolBankConfiguration](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/NozzleShelfController.cs:73)、[NozzleShelfController.IsSlotHaveNozzle](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/NozzleShelfController.cs:253)；[System2Controller.Assistant.ChangeNozzleAssistance](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.Assistant.cs:1827)。


#### 32 清嘴排胶与手动维护

- 32.01 清嘴触发、清嘴区域索引与清洁动作。
- 32.02 吹气盒、抛料位置和持晶清理。
- 32.03 S1 手动试胶、板上试胶与换胶入口。
- 32.04 工具和设备参数示教的准备、取消与保存。

源码入口：[System2Controller.InitCleanTable](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.cs:1136)、[System2Controller.CleanNozzle](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.cs:1176)；[BondModuleController.MovementRelated.ThrowAction](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/BondModuleController.MovementRelated.cs:806)；[UcDispenseManual.BtPreDispense_Click](D:/agent_project/code_agent/trunk/AKRS.ZX2200/DispenseSystem/Controls/Manual/UcDispenseManual.cs:163)；[FrmBlowOffBoxAssistant.InitControl](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controls/Manual/FrmBlowOffBoxAssistant.cs:61)。


#### 37 耗材寿命与提醒

- 37.01 胶水、吸嘴、翻转工具、顶针耗材汇集。
- 37.02 次数寿命与时间寿命的计算。
- 37.03 后台扫描、到期和提前提醒门控。
- 37.04 寿命参数编辑、清零与更换后复位。

源码入口：[ConsumablesProgram.BackgroundConsumable](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Consumables/ConsumablesProgram.cs:64)、[ConsumablesProgram.ScanConsumables](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Consumables/ConsumablesProgram.cs:72)；[FrequencyConsumables.IsExpired](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Consumables/FrequencyConsumables.cs:48)、[FrequencyConsumables.IsRemind](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Consumables/FrequencyConsumables.cs:69)；[TimeConsumable.IsExpired](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Consumables/TimeConsumable.cs:56)、[TimeConsumable.IsRemind](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Consumables/TimeConsumable.cs:75)；[UcMainSystem.DataAdministrator.BtConsumables_ItemClick](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.DataAdministrator.cs:120)。


#### 38 手动点动与状态面板

- 38.01 方向盘和摇杆的轴绑定、速度模式与停止。
- 38.02 模块相机切换、曝光、增益及实时图像。
- 38.03 真空、吹气、气缸和料仓的手动控制。
- 38.04 轨道物料、槽位、顶针和力 LVDT 实时状态。
- 38.05 快捷键扫描、上一颗点胶或贴片查看及人工位置偏移。

源码入口：[UcGuideMove.Joystick.MoveAxisByJoystick](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/UcGuideMove.Joystick.cs:407)、[UcGuideMove.Joystick.StopCurAxis](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/UcGuideMove.Joystick.cs:631)；[UcGuideMove.SetCameraParematerByModule](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/UcGuideMove.cs:539)；[UcVacuum.RefreshControl](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controls/Manual/UcVacuum.cs:66)；[FrmSetionState.TimerState_Tick](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportSystem/Controls/Feature/FrmSetionState.cs:28)；[FrmEntityOffsetChange.FrmEntityOffsetChange_Load](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Controls/Common/FrmEntityOffsetChange.cs:78)。


### 补偿与温控

#### 33 焊后反馈与产品补偿

- 33.01 焊后样本进入缓存的路径和筛选门槛。
- 33.02 按检测名称取样、比例换算与补偿计算。
- 33.03 按载具归一化和按焊点独立偏移。
- 33.04 Bond 与载具补偿数据的读入和人工清除。
- 33.05 自动采集多轮、过滤、计算及保存的窗体实现。

源码入口：[DefectCompensate.GetPostCompensation](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Compensate/DefectCompensate/DefectCompensate.cs:57)、[DefectCompensate.NormalizationOffset](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Compensate/DefectCompensate/DefectCompensate.cs:90)、[DefectCompensate.GetBpSeparateOffset](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Compensate/DefectCompensate/DefectCompensate.cs:235)；[FrmAutoCompensate.BtnStartCollect_Click](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Compensate/MotionAreaCompensate/FrmAutoCompensate.cs:91)、[FrmAutoCompensate.FinishCollectAndCalculate](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Compensate/MotionAreaCompensate/FrmAutoCompensate.cs:237)、[FrmAutoCompensate.BtnEnable_Click](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Compensate/MotionAreaCompensate/FrmAutoCompensate.cs:146)；[TransportUnitCompensate.GetBondCompensate](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Compensate/MotionAreaCompensate/TransportUnitCompensate.cs:66)。

实现边界：FrmAutoCompensate 有已编译实现，本轮未定位到生产菜单或其他业务文件中的直接创建引用；作为独立窗体流程，入口可达性待核实。


#### 34 运动区域与实时位置补偿

- 34.01 全局标定数据在加工目标处的查表和插值。
- 34.02 多区域双线性插值、区域选择与边界。
- 34.03 标定尺基准点示教、首轮扫描和周期扫描。
- 34.04 实时基准点偏差作用到目标位置。
- 34.05 软件偏移、驱动二维补偿和工具偏移的调用顺序。

源码入口：[GlobalCalibrationDomain.GetAxisCompensate](D:/agent_project/code_agent/trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/GlobalCalibrationDomain.cs:94)、[GlobalCalibrationDomain.GetBondHandCompensate](D:/agent_project/code_agent/trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/GlobalCalibrationDomain.cs:160)；[BilinearCompensator.TryInterpolate](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/BilinearCompensator.cs:98)、[BilinearCompensator.Interpolate](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/BilinearCompensator.cs:294)；[RealTimeCorrection.ScanReferencePoints](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Compensate/MotionAreaCompensate/RealTimeCorrection.cs:271)、[RealTimeCorrection.GetCompensatePoint3D](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Compensate/MotionAreaCompensate/RealTimeCorrection.cs:149)；[BondActionNode.Provider.CalculateBondPos](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.Provider.cs:498)。


#### 35 温漂与取片位置补偿

- 35.01 温漂 Mark、取片 Mark 的示教和校准。
- 35.02 首载具与周期补偿的触发门控。
- 35.03 上视温漂偏移计算与阈值处理。
- 35.04 取片偏移计算和取晶位置应用。
- 35.05 温度曲线、补偿记录及预测功能的当前边界。

源码入口：[TpMarkCompensate.TemperatureCompensation](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Compensate/TemperatureCompensate/TpMarkCompensate.cs:64)、[TpMarkCompensate.PickUpCompensationVision](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Compensate/TemperatureCompensate/TpMarkCompensate.cs:153)、[TpMarkCompensate.GetTemperatureCompensation](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Compensate/TemperatureCompensate/TpMarkCompensate.cs:240)、[TpMarkCompensate.GetPickCompensation](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Compensate/TemperatureCompensate/TpMarkCompensate.cs:261)；[System2Controller.Vision.System2TemperatureCompensation](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.Vision.cs:897)；[CompensationPredictor.Predict](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/CompensationPredictor.cs:81)。

实现边界：ONNX 预测器的 Predict 当前直接 return null，界面载入预测模型代码被注释；不能画成已生效的生产预测补偿。


#### 36 加热预热与温度监控

- 36.01 工位加热开启、设定温度与关闭。
- 36.02 报警温度、补偿值、温度斜率及预热时长保存。
- 36.03 温度到达、预热计时和生产启动门控。
- 36.04 后台超温检测、停机与提示。
- 36.05 轴温度与热电偶曲线、采集和保存。
- 36.06 风冷 PID 计算框架及当前输入输出边界。

源码入口：[FrmHeatingSettings.BtHeatingSet_Click](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/HeatingSettings/FrmHeatingSettings.cs:41)、[FrmHeatingSettings.TsIsOpenHeater_Toggled](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/HeatingSettings/FrmHeatingSettings.cs:92)；[Machine.Operate.MachineInitSuccess](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:408)、[Machine.Operate.BackgroundTemperatureAlarm](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:449)；[FrmTemperatureMonitoring.GetTemperatureData](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/TemperatureMonitoring/FrmTemperatureMonitoring.cs:121)、[FrmTemperatureMonitoring.SaveData](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/TemperatureMonitoring/FrmTemperatureMonitoring.cs:197)；[AirCooledController.Start](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Compensate/TemperatureCompensate/AirCooledController.cs:119)。

实现边界：AirCooledController.Start 使用本地 feedback 累加输出，真实传感器读取和模拟量输出仅有注释；只列框架，不作为完整风冷闭环。


### 运行与数据

#### 39 报警互锁与运行监控

- 39.01 报警等级、状态灯、弹窗与操作结果回传。
- 39.02 安全门检查及继续生产门控。
- 39.03 供气、负压和工位真空监测。
- 39.04 激光编码器预热、状态检测与运动就绪。
- 39.05 报警历史查询、强制解除与清理。

源码入口：[AKRSMessageBoxExt.SetAlarmState](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/AKRSMessageBoxExt.cs:60)、[AKRSMessageBoxExt.Alarm](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/AKRSMessageBoxExt.cs:163)；[Machine.Sustain.StartCheckSafeDoorTask](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Sustain.cs:276)、[Machine.Sustain.LaserEncoderCheck](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Sustain.cs:326)；[NeedScanSensorPool.ScanSensor](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/SensorCheckScan/NeedScanSensorPool.cs:54)；[UcAlarmHistory.BtQuery_Click](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Controls/Common/UcAlarmHistory.cs:84)。

实现边界：传感器扫描池中总气压等三个传感器的报警弹窗当前被注释；工位负压不足分支仍有实际停机和报警，须分别画出。


#### 40 暂停停止与物料恢复

- 40.01 工作、暂停、停止与单步状态迁移。
- 40.02 Pause Continue 对任务、信号与安全门的处理。
- 40.03 Stop 与急停入口的实际调用差异。
- 40.04 线程存活、任务退出许可及再次启动。
- 40.05 物料地图恢复、重做和已完成步骤保留。
- 40.06 异常后的软件清理与实际机械状态边界。

源码入口：[Machine.Operate.Pause](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:314)、[Machine.Operate.Continue](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:323)、[Machine.Operate.Stop](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:347)、[Machine.Operate.EmergencyStop](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:383)；[Machine.IsAllowTaskClosed](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.cs:201)；[BondTask.AbortThread](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs:382)；[WaferSubSystemTask.AbortWaferSubThread](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs:1431)；[TuService.ReadTransportMapping](D:/agent_project/code_agent/trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs:1800)。


#### 41 后台任务与保存退出

- 41.01 主窗体与整机后台任务创建和退出条件。
- 41.02 图像保存队列、消费者和实际写文件。
- 41.03 统计记录队列与数据库写入。
- 41.04 参数、仓库、地图和生产信息保存。
- 41.05 磁盘容量、定期文件清理及日志保留。
- 41.06 退出确认、任务结束许可与软件关闭。

源码入口：[Machine.Operate.StartBackGroundThread](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:662)、[Machine.Operate.ExitSoftware](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs:706)；[VisionService.StartSaveThread](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Service/VisionService.cs:326)、[VisionService.SaveBitmap](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Service/VisionService.cs:343)；[StatisticsService.StartSaveThread](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsService.cs:97)、[StatisticsService.SaveEntityToDb](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsService.cs:110)；[Machine.Sustain.CleanFile](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Sustain.cs:215)；[MainForm.MainForm_FormClosing](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Controls/MainForm.cs:280)。


#### 42 生产统计与日志查询

- 42.01 点胶固晶计数、节拍和生产用时记录。
- 42.02 产能、良率、缺陷与报警时长统计。
- 42.03 焊点日志、操作日志、参数修改日志。
- 42.04 力 LVDT、测高及补偿记录展示。
- 42.05 时间范围查询、数据导入导出和人工清零。

源码入口：[StatisticsDomain.CalculateDispenseCycle](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsDomain.cs:250)、[StatisticsDomain.CalculateBondCycle](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsDomain.cs:279)、[StatisticsDomain.QueryCapacity](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsDomain.cs:313)、[StatisticsDomain.QueryDefect](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsDomain.cs:325)、[StatisticsDomain.QueryParameterChangeLog](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsDomain.cs:396)；[StatisticsService.GetMaxMTBA](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsService.cs:142)；[FrmStatistics.QueryData](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Statistics/FrmStatistics.cs:174)；[DBService.CleanInfo](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Service/DBService.cs:161)。


### 管理功能

#### 44 用户权限与界面配置

- 44.01 登录身份、角色和可操作功能的对应。
- 44.02 工作状态、硬件配置决定菜单显示和启用。
- 44.03 实验入口解锁与锁屏入口。
- 44.04 多语言缓存、控件翻译和语言切换。
- 44.05 版本说明、软件信息与授权到期提示。

源码入口：[Machine.GetCurrentRoleLevel](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.cs:118)；[UcMainSystem.UIState.ChangeUiByState](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.UIState.cs:382)、[UcMainSystem.UIState.InitByConfiguration](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.UIState.cs:489)；[LocalizationManager.Initialize](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Localization/LocalizationManager.cs:22)、[LocalizationManager.ChangeLanguage](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Localization/LocalizationManager.cs:53)；[LocalizationCache.LoadFormTranslation](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Localization/LocalizationCache.cs:268)；[VersionUpdateAnnouncement.CheckVersionUpdate](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/VisionControl/VersionUpdateAnnouncement.cs:33)。

实现边界：角色及用户管理、加密狗等部分实现来自引用库；图谱展示主程序调用边界。实验入口不与生产步骤混排。


### 实验诊断

#### 45 精度实验与设备诊断

- 45.01 静态视觉、像素比例、回差和重复定位实验。
- 45.02 旋转中心、温漂、Bond 上视关系与 CMK 实验。
- 45.03 取片、放片、角度校正和模拟贴片实验。
- 45.04 力控、测高、焊头稳定性与振动实验。
- 45.05 整机功能检查、换嘴换针换片耐久测试。
- 45.06 实验参数、停止条件、结果统计和数据导出。

源码入口：[FrmRepeatPositionAccuracy.TestRepeatPositionAccuracy](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Experiment/RepeatPositionAccuracy/FrmRepeatPositionAccuracy.cs:220)；[FrmBMCTest.BMCTest](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Experiment/Test/FrmBMCTest.cs:311)；[FrmPickupRepeatTest.PickTest](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Experiment/BondAccuracyExperiment/FrmPickupRepeatTest.cs:195)；[FrmPlacementTest.PlacementTest](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Experiment/BondAccuracyExperiment/FrmPlacementTest.cs:157)；[FrmMachineFunctionTest.PPToolsTestRun](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Experiment/Test/FrmMachineFunctionTest.cs:386)、[FrmMachineFunctionTest.ForceControlTest](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Experiment/Test/FrmMachineFunctionTest.cs:1286)。

实现边界：Experiment 中 64 个 C# 文件列入编译；部分主菜单实验处理为空，窗体实现与菜单可达性必须分开记录。


## G0 专题的优先顺序

先做设备坐标关系、普通坐标正反变换和相机从属坐标，再连接产品坐标、视觉定位与机械移动。G0 定义与转换在 03，载具到焊点的坐标继承在 04，相机标定在 06，轴执行在 10。

- `MachineCoordinateSystem` 管理加载、父级绑定、创建、查找和保存。首次缺少 G0 时，CreateCoordinateSystem 创建 G0 后直接返回，本次不继续创建请求的子坐标。
- `GeneralCoordinateSystem` 沿父引用收集链路，正向逐层变换，反向逆序变换；停止依据是父引用为空。
- `DependentCoordinateSystem.SelfPosToG0` 将像素变换结果与传入的上层位置组合，再做直接父级变换；它与普通坐标的逐级遍历分别绘制。
- `BaseCoordinateSystem` 的 General 计算直接使用 Sin 和 Cos；角度和长度单位跟随参数来源核对。VM 三维逆变换显式抛异常；从属坐标的 G0PosToSelf 仅返回新建点。
- `TransportUnit` 以 TransportCoordinateSystem 创建载具坐标，再展开基板、模块和焊点；定位更新与加工目标生成分别跟踪。

这些内容对应 03、04、05、06、10 的源码入口，公共转换只在坐标专题展开。

## 必须区分的实现状态

| 位置或入口 | 当前源码行为 | 图谱处理 |
| --- | --- | --- |
| [CompensationPredictor.Predict](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/CompensationPredictor.cs:81) | 直接返回 null，预测执行代码被注释 | 列为未实现边界，不能画成已启用的预测补偿 |
| [AirCooledController.Start](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/Compensate/TemperatureCompensate/AirCooledController.cs:119) | 本地 feedback 累加，真实输入输出仅留注释 | 仅记录 PID 框架 |
| [CheckInkDotActionNode.DoWork](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/AdjustActionNode/CheckInkDotActionNode.cs:32) | 直接返回 Success | 不将该节点画成实际执行墨点识别 |
| S2EpoxyDefectActionNode | 空派生类，继承 ActionNode 默认行为 | 实际胶检沿预点胶、焊后等调用链展开 |
| [DipFluxActionNode.DipFluxActionDryRun](D:/agent_project/code_agent/trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/DipFluxActionNode.cs:704) | 先抛出待验证异常 | 画异常出口，不沿后续代码画正常空跑 |
| [Block.SearchMapping.SearchMapping](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.SearchMapping.cs:46) | 双点、MultipleSearch 等分支显式抛异常 | 搜索模式按实际支持情况分别列出 |
| [WaferSubSystemTask.ChangeSucceedOperation](D:/agent_project/code_agent/trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs:488) | ManualAtStart 分支显式抛异常 | 不列为已完成的换料后自动启动方式 |
| [NeedScanSensorPool.ScanSensor](D:/agent_project/code_agent/trunk/AKRS.ZX2200/SupportFeature/SensorCheckScan/NeedScanSensorPool.cs:54) | 三个气压传感器的弹窗被注释，工位真空不足另有实际停机路径 | 监测与报警分支分别处理 |
| FrmAutoCompensate | 有编译实现，未在本工程定位到直接创建引用 | 记录窗体流程，入口可达性待确认 |
| 部分输送 SearchBelt、MapBelt 和 HasMaterialInModule | 直接抛 NotImplementedException | 保留异常出口，不依据方法名推定已实现 |
| 主菜单部分处理函数 | 存在空方法；同名功能可能另有有效入口 | 区分具体绑定，不因单一空方法否定整个功能 |

三点一线的 `barBtnSystem2Cali_ItemClick` 为空，`barBtnThreePointOneLineCali_ItemClick` 则实际打开 FrmSystem2Calibrate；主界面“加载程式”也有不同处理入口。

主菜单中定位到的空处理如下。

| 界面文字 | 方法 |
| --- | --- |
| Machine Statistics | [UcMainSystem.BarBtMachineStatistics_ItemClick](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs:1084) |
| Production Statistics | [UcMainSystem.BarBtProductionStatistics_ItemClick](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs:1093) |
| Visual Static Test | [UcMainSystem.BarBtnVisualStatic_ItemClick](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs:1253) |
| Test | [UcMainSystem.BarBtTest_ItemClick](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs:1467) |
| 标定精度实验 | [UcMainSystem.BarBtCalibAccuracyTest_ItemClick](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs:1644) |
| 放片实验 | [UcMainSystem.BarBtPlaceAccuracyTest_ItemClick](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs:1657) |
| 三点一线校准 | [UcMainSystem.barBtnSystem2Cali_ItemClick](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs:2088) |
| 加载程式 | [UcMainSystem.BtLoadProduct_ItemClick](D:/agent_project/code_agent/trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs:1244) |

## 文件覆盖核对

下表为主目录 C# 文件数量；方法声明按 Roslyn 语法节点统计，包含重载、接口和界面生成方法，partial 类型不按声明数量统计为独立功能。

| 目录 | C# 文件 | 主工程编译项 | Designer 文件 | 方法声明 |
| --- | ---: | ---: | ---: | ---: |
| BondSystem | 227 | 222 | 60 | 1438 |
| CalibSystem | 65 | 65 | 24 | 432 |
| 根目录 | 2 | 1 | 0 | 7 |
| DispenseSystem | 75 | 74 | 13 | 290 |
| Experiment | 68 | 64 | 34 | 397 |
| Infrastructure | 126 | 123 | 30 | 582 |
| Localization | 4 | 4 | 0 | 40 |
| Main | 76 | 72 | 22 | 508 |
| Properties | 3 | 3 | 2 | 0 |
| SupportFeature | 160 | 160 | 55 | 515 |
| TransportSystem | 73 | 73 | 14 | 381 |
| TransportUnitSystem | 104 | 104 | 36 | 586 |
| WaferSubSystem | 174 | 172 | 51 | 1100 |

### 未列入主工程的文件

这些文件仍保留在扫描目录中，不能直接归入当前构建的生产功能。

- `BondSystem/Controls/Setting/ProcessStep/FrmCreateProcessStep.cs`
- `BondSystem/Controls/Setting/ProcessStep/FrmCreateProcessStep.Designer.cs`
- `BondSystem/Controls/Setting/ProcessStep/UcProcessStepEdit.cs`
- `BondSystem/Controls/Setting/ProcessStep/UcProcessStepEdit.Designer.cs`
- `BondSystem/Services/System1ActionNodesService.cs`
- `Common.cs`
- `DispenseSystem/Services/System2ActionNodesService.cs`
- `Experiment/RepeatPositionAccuracy/FrmChooseCamera.cs`
- `Experiment/RepeatPositionAccuracy/FrmChooseCamera.Designer.cs`
- `Experiment/RepeatPositionAccuracy/FrmRotateCenterAccuracy.cs`
- `Experiment/RepeatPositionAccuracy/FrmRotateCenterAccuracy.Designer.cs`
- `Infrastructure/Models/CommonModels/InterpolationParamConfig.cs`
- `Infrastructure/Models/CommonModels/NLogTraceWriter.cs`
- `Infrastructure/Models/CommonModels/SingleInterpolationParam.cs`
- `Main/Machine/Control/FrmChipFrictionSetting.cs`
- `Main/Machine/Control/FrmChipFrictionSetting.Designer.cs`
- `Main/Machine/Product/ProcessStep/ProcessStep.cs`
- `Main/Machine/Product/ProcessStep/ProcessStepProgram.cs`
- `WaferSubSystem/Controls/Assistant/ComponentsTeach/FrmComponentLocateUseInfo.cs`
- `WaferSubSystem/Controls/Assistant/ComponentsTeach/FrmComponentLocateUseInfo.Designer.cs`

### 依赖边界

主工程直接引用 Calibration、SoftKey、AutoFocusing、AxisCompensate、CoordinateSystems、Dispense、MachineSupport、Machine、Parameters、PR 共 10 个源码工程。`../AKRS.Galaxy2.Parameters/AKRS.Galaxy2.Parameters.csproj` 当前不存在，其余 9 个引用路径存在。

硬件与驱动、Recipe、UserManager、WaferMap、视觉 SDK、测高等还有 DLL 引用。作图先明确主程序的参数、调用、等待和结果处理；库内部行为只在取得对应源码或明确的接口证据后展开。当前清单不依靠旧报告推定外部算法已实现。

## 制作顺序与阅读约定

1. 先做 G0、产品坐标、公共视觉、标定与安全移动，形成后续动作的公共基础。
2. 串起配方、工艺调度、输送、供晶、取晶、校正、点胶和固晶主流程。
3. 展开测高力控、换嘴换针、维护、补偿、温控与恢复。
4. 补齐后台、统计、参数、权限和实验诊断入口。

每个专题先用一张关系或主流程图交代整体，再按需要展开实际调用、条件、状态写入和失败出口。调用、异步通知、等待完成与实际动作完成分别标注；公共内容以链接引用。

现有页面有 10 个阅读专题和 65 个阅读目录项，其中含辅助条目。新清单按源码功能重新细分，不能直接用清单数量减现有图数计算“还差多少张”。本轮仅形成清单，不改正式页面和业务源码。

## 本地检索索引

- [逐文件覆盖与 SHA-256](D:/agent_project/code_agent/output/zx2200-functional-inventory-20261027/source-coverage.csv)：1,157 行文件记录。
- [完整类型和方法语法目录](D:/agent_project/code_agent/output/zx2200-functional-inventory-20261027/syntax-inventory.json)：可按方法名检索。
- [主菜单到处理方法](D:/agent_project/code_agent/output/zx2200-functional-inventory-20261027/main-menu-traces.json)：含空处理、直接创建及泛型窗体入口。
- [其他界面文字与事件绑定](D:/agent_project/code_agent/output/zx2200-functional-inventory-20261027/ui-entries.json)：按界面文件检索。
- [专题与方法位置](D:/agent_project/code_agent/output/zx2200-functional-inventory-20261027/functional-topics.json)：45 个专题的候选内容和入口位置。
