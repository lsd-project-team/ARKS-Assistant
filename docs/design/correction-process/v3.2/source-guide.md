# 纠偏过程源码阅读索引

完整路径、主题与行号锚点。文件哈希以source-baseline.json为准。

## [1] 纠偏对象与配置

产品定位与芯片定位的独立配置

- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/LocateConfig.cs：List<string> GetPrNames()，L159；void VisionPosOffSet(AKRSPoint3D offset)，L185；bool IsUseCircleAngel()，L197
- trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/AdjustConfig.cs：字段定义，L1
- trunk/AKRS.ZX2200/WaferSubSystem/Models/Repositories/Carrier/BaseCarrierConfig.cs：void AddCountOfPositionError()，L1000；void AddCountOfInkDot()，L1008；void AddCountOfVacuumError()，L1016
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Information/BondPositionInfo.cs：bool IsFinishedInSystem1()，L118；bool IsFinishedInSystem2()，L145；void SetFinishedInSystem1()，L166

## [2] 产品定位计算

采集、分轴选点、角度和坐标更新调用

- trunk/AKRS.ZX2200/DispenseSystem/Models/System1Domain.cs：bool System1MatterVision(BaseMatter baseEntity, bool byMapping = true)，L96
- trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs：bool System2MatterVision(BaseMatter baseEntity, bool byMapping = true)，L279
- trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs：static void CreateMatterCoordinate(BaseMatter baseMatter, GeneralCoordinateSystem upperCoordinateSystem, ElementCoordinate elementCoordinate)，L872；static void UpdateEntity(BaseMatter baseEntity, AdjustTypeEnum type)，L528；static TransportUnit ReadTransportMapping()，L1800
- trunk/AKRS.ZX2200/TransportUnitSystem/Model/VisionResult.cs：void SaveInfo(MatchResult matchResult, AKRSPoint3D resultPoint3D, AKRSPoint3D resultPoint3DInG0, AKRSPoint3D visionPoint3DInG0)，L60
- trunk/AKRS.ZX2200/Infrastructure/Utils/MathHelper.cs：static AKRSPoint3D RotateCenter(AKRSPoint3D distanceToCenter,double degree)，L34；static AKRSPoint3D OnePointAdjust(double angleDifference, double radius, AKRSPoint3D resultPos, double NewDegree,double rotateDistance)，L100；static AKRSPoint3D UpLookAdjust(AKRSPoint3D upLookCenter, DependentCoordinateSystem coordinateSystem, AKRSPoint3D visionPos, double degree, MatchResult matchResult)，L128

## [3] 坐标及标定接口

相机结果转换和吸嘴校准角度

- trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.Vision.cs：AKRSPoint3D GetBondVisionResultPos(MatchResult result, AKRSPoint3D visionPos = null)，L652
- trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs：AKRSPoint2D GetNozzleOffset(string nozzleName, double angle)，L970；Nozzle GetCurrentNozzle()，L932
- trunk/AKRS.ZX2200/BondSystem/Controllers/BondModuleController.cs：AKRSPoint3D ConvertG0ToMachinePos(AKRSPoint3D pos)，L173
- trunk/AKRS.ZX2200/BondSystem/Models/Repositories/Nozzle/Nozzle.cs：Nozzle(string name)，L30；string GetNozzlePRName()，L138；override string ToString()，L186
- trunk/AKRS.ZX2200/DispenseSystem/Controllers/DispenseController.cs：void MoveToSafePos()，L103；void MoveToG0Pos3D(AKRSPoint3D point3D, bool isMeasureOpen = false)，L129；void MoveToG0Pos3DWithoutSafe(AKRSPoint3D point3D)，L191
- trunk/AKRS.ZX2200/Infrastructure/Utils/MathHelper.cs：static AKRSPoint3D RotateCenter(AKRSPoint3D distanceToCenter,double degree)，L34；static AKRSPoint3D OnePointAdjust(double angleDifference, double radius, AKRSPoint3D resultPos, double NewDegree,double rotateDistance)，L100；static AKRSPoint3D UpLookAdjust(AKRSPoint3D upLookCenter, DependentCoordinateSystem coordinateSystem, AKRSPoint3D visionPos, double degree, MatchResult matchResult)，L128

## [4] 生产上视纠偏

快速、普通、镜像和温漂调用

- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs：override ExcuteResult DoWork()，L131
- trunk/AKRS.ZX2200/BondSystem/Models/Parameter/System2RunTimeProvider.cs：static void RecordTime(string item, string subItem, bool isAsync = false)，L227
- trunk/AKRS.ZX2200/SupportFeature/Compensate/TemperatureCompensate/TpMarkCompensate.cs：static AKRSPoint3D GetPickCompensation()，L261

## [5] 生产中转台纠偏

放片、拍照、重取及重试

- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.cs：override ExcuteResult DoWork()，L136
- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.Provider.cs：void PrepareBeforeAction()，L33
- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.MoveHelper.cs：ExcuteResult MoveToIPTVisionPos(AKRSPoint3D targetPos)，L423；ExcuteResult MoveToIPTPickPos(AKRSPoint4D targetPos)，L543

## [6] 贴装目标

补偿次序、位置记录与运动轴目标

- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.Provider.cs：AKRSPoint4D CalculateBondPos()，L498
- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.cs：override ExcuteResult DoWork()，L118
- trunk/AKRS.ZX2200/SupportFeature/Compensate/MotionAreaCompensate/RealTimeCorrection.cs：AKRSPoint3D RealTimeVision(AKRSPoint3D point3D)，L61；AKRSPoint3D GetCompensatePoint3D(AKRSPoint3D iptPickPos, AKRSPoint3D iptVisionPos, AKRSPoint3D bondPos, AKRSPoint3D bondVisonPos)，L149；AKRSPoint3D GetCompensatePosByPoint(AKRSPoint3D point3D)，L208

## [7] 报警与人工确认

PR重跑和距离检查

- trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcmainSystem.Action.cs：void InitAction()，L31
- trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/FrmVisionAlarm.cs：FrmVisionAlarm(PREntity pREntity, string message, string caption,PRHardware pRHardware = null)，L43；void TimerVision_Tick(object sender, EventArgs e)，L104；void BackgroundWorkerDoWork()，L135
- trunk/AKRS.ZX2200/Infrastructure/Service/VisionService.cs：static BaseAlgResult Vision(string pRName, PRHardware prHardware, string systemName = "Other", string bitmapName = "", bool setLight = true)，L78；static List<BaseAlgResult> VisionDefect(string pRName, PRHardware prHardware, string systemName = "Other", string bitmapName = "", bool setLight = true)，L158；static void SaveVisionImage(Bitmap bitmap, List<string> filePath,string bitmapName)，L213

## [8] 定位动作与编排

八个层级定位入口及相对固晶时机

- trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/DispenseUpAction/S1CarrierVisionActionNode.cs：override ExcuteResult DoWork()，L44
- trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/DispenseUpAction/S1SubstrateVisionActionNode.cs：override ExcuteResult DoWork()，L34
- trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/DispenseUpAction/S1ModuleVisionActionNode.cs：override ExcuteResult DoWork()，L36
- trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/DispenseBPAction/S1DispenseCorrectionActionNode.cs：override ExcuteResult DoWork()，L48
- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/AdjustActionNode/S2CarrierVisionActionNode.cs：override ExcuteResult DoWork()，L36
- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/AdjustActionNode/S2SubstrateVisionActionNode.cs：override ExcuteResult DoWork()，L55
- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/AdjustActionNode/S2ModuleVisionActionNode.cs：override ExcuteResult DoWork()，L55
- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/AdjustActionNode/BondPositionVisionActionNode.cs：override ExcuteResult DoWork()，L58
- trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/DispenseActionNodes.cs：void Init()，L192
- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BondActionNodeRepository.cs：void Init()，L255
- trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs：void Init()，L155；void InjectSteps(TransportUnit transportUnit)，L1410
- trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs：void DoWork()，L100

## [9] 供料端定位及取片

搜晶分支、多次校正、静态华夫盒和取片位

- trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.cs：bool NextDie()，L335；(bool isSucceed, MatchResult matchResult) ToRequiredAccuracy()，L1394
- trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.SearchSingle.cs：bool SearchSingle(bool isOffset = true)，L35
- trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.SearchNine.cs：bool SearchNine()，L39；bool AnalyseDies()，L294；void CalculateDiesPosition()，L391
- trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.SearchMapping.cs：bool SearchMapping()，L46；void StartAsyncSeekingPath()，L204；void StopAsyncSeekingPath()，L216
- trunk/AKRS.ZX2200/WaferSubSystem/Models/Entities/SearchChip/Block.SearchDieBox.cs：bool SearchDieBox()，L48；AcupointEntity GetWaffleNextPositionInfo()，L151；void AsyncSaveWaferSubDevicePara()，L175
- trunk/AKRS.ZX2200/WaferSubSystem/Tasks/WaferSubSystemTask.cs：void Dowork()，L64；bool ChangeSucceedOperation()，L488；bool ChangeTabletManual()，L1000
- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs：override ExcuteResult DoWork()，L156
- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs：void PrepareBeforePickAction()，L55；ExcuteResult JudgeAndChangeNozzle()，L120；void JudgeAndCleanNozzle()，L146
- trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.Assistant.cs：ExcuteResult PlacementTest(，L659；(ExcuteResult, AKRSPoint4D) UplookVisionAction(BondPosition bondPosition, BaseCarrierConfig component)，L950；AKRSPoint4D CalculatePickPos(BaseCarrierConfig component, double componentAngle, MatchResult matchResult)，L1457
- trunk/AKRS.ZX2200/WaferSubSystem/Controllers/WaferSubController.cs：void ResetCyc(Electric electric, Sensor sensor, int delayBefore = 0, int delayAfter = 0, int timeOut = 5000, bool isCancelWait = false)，L76；void SetCyc(Electric electric, Sensor sensor, int delayBefore = 0, int delayAfter = 0, int timeOut = 5000, bool isCancelWait = false)，L111；void SetUIControl(TileBar tileBar, TileBarGroup tileBarGroup, List<AssistantConfig> list, int stepIndex, SimpleButton bt1, SimpleButton bt2, SimpleButton bt3, LabelControl lc1)，L198
- trunk/AKRS.ZX2200/WaferSubSystem/Tasks/FlipTask.cs：void DoWork()，L57

## [10] 手动辅助入口

贴片测试、示教定位与独立上视实现

- trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.Assistant.cs：ExcuteResult PlacementTest(，L659；(ExcuteResult, AKRSPoint4D) UplookVisionAction(BondPosition bondPosition, BaseCarrierConfig component)，L950；AKRSPoint4D CalculatePickPos(BaseCarrierConfig component, double componentAngle, MatchResult matchResult)，L1457
- trunk/AKRS.ZX2200/BondSystem/Controls/Assistant/FrmComponentPlacement.cs：void PlacementTest(BondTypeEnum bondType)，L433
- trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Assistant/TUAssistantHelper.cs：static TransportUnit JudgeTuExist()，L392
- trunk/AKRS.ZX2200/TransportUnitSystem/Controls/TransportUnitEdit/UcObjectFunctionEdit.cs：void Init(OppositeSex oppositeSexConfig)，L93；void Save()，L790
- trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.ShortcutKeys.cs：void UcMainSystem_KeyDown(object sender, KeyEventArgs e)，L45

## [11] 中转台运动分支

绝对运动、插补运动与空跑

- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.MoveHelper.cs：ExcuteResult MoveToIPTVisionPos(AKRSPoint3D targetPos)，L423；ExcuteResult MoveToIPTPickPos(AKRSPoint4D targetPos)，L543
- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.cs：override ExcuteResult DoWork()，L136

## [12] 相关运行补偿

取片温漂、焊后、单点、TU区域与实时补偿

- trunk/AKRS.ZX2200/SupportFeature/Compensate/TemperatureCompensate/TpMarkCompensate.cs：static AKRSPoint3D GetPickCompensation()，L261
- trunk/AKRS.ZX2200/SupportFeature/Compensate/DefectCompensate/DefectCompensate.cs：static AKRSPoint3D GetPostBondCompensation(string bpName)，L187；static void NormalizationOffset(string tuId)，L90
- trunk/AKRS.ZX2200/SupportFeature/Compensate/MotionAreaCompensate/TransportUnitCompensate.cs：AKRSPoint3D GetBondCompensate(double x, double y)，L66
- trunk/AKRS.ZX2200/SupportFeature/Compensate/MotionAreaCompensate/RealTimeCorrection.cs：AKRSPoint3D RealTimeVision(AKRSPoint3D point3D)，L61；AKRSPoint3D GetCompensatePoint3D(AKRSPoint3D iptPickPos, AKRSPoint3D iptVisionPos, AKRSPoint3D bondPos, AKRSPoint3D bondVisonPos)，L149；AKRSPoint3D GetCompensatePosByPoint(AKRSPoint3D point3D)，L208
- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/AfterBondCheckActionNode.cs：override ExcuteResult DoWork()，L112
- trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs：void DoWork()，L100

## [13] 设备轴二维补偿

回零、标定界面和驱动补偿的启停契约

- trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs：bool AllAxisGoHome()，L504；void OpenCompensate()，L609；void CloseCompensate()，L589
- trunk/AKRS.ZX2200/Infrastructure/Utils/ETelDrive.cs：static void Open2DCompensate(Axis axisX, Axis axisY, string fileName)，L292；static void DownloadMapping(Axis axisX, Axis axisY, string fileName)，L27
- trunk/AKRS.ZX2200/Infrastructure/Utils/GuGaoDrive.cs：static bool Open2DCompensate(GTCalib2DParam paramObj, int[,] dataX, int[,] dataY)，L897；static void Close2DCompensate()，L839
- trunk/AKRS.ZX2200/Main/Machine/MachineSupport/MachineSoftwareConfiguration.cs：protected virtual void OnPropertyChanged(string propertyName, object before, object after)，L182；bool SaveLoacteImage()，L191
- trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs：void Save()，L355
- trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/GlobalCalibrationDomain.cs：(double, double) GetAxisCompensate(double x, double y)，L94；AKRSPoint3D GetBondHandCompensate(double x, double y, AKRSPoint3D offset)，L160
- trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmAssistant2DStage.cs：void Save()，L280

## [14] 两点角度示教

采点参考系、角度边界、调用方写回和取消语义

- trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Assistant/FrmAdjustDegree.cs：void InitControl()，L91；void BtDone_Click(object sender, EventArgs e)，L227
- trunk/AKRS.ZX2200/Infrastructure/Controls/Feature/EditProgram/UcEditProductProgram/UcEditProductProgramming.Assistance.cs：void AssistanceTuAdjust()，L63；void AssistanceSubAdjust()，L159；void AssistanceModuleAdjust()，L219
- trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Assistant/TUAssistantHelper.cs：static TransportUnit JudgeTuExist()，L392

## [15] 自动生成区域补偿表

统计分组、轮次筛选、矩阵计算及保存

- trunk/AKRS.ZX2200/SupportFeature/Compensate/MotionAreaCompensate/FrmAutoCompensate.cs：void PollTimer_Tick(object sender, EventArgs e)，L173；void FinishCollectAndCalculate()，L237
- trunk/AKRS.ZX2200/SupportFeature/Compensate/MotionAreaCompensate/CompensateCalculator.cs：static double[,] Calculate(double[,] rawOffsets, int rows, int cols,，L26；static double HuberEstimate(double[] data, double c = DefaultC)，L72
- trunk/AKRS.ZX2200/SupportFeature/Compensate/MotionAreaCompensate/CompensateDataService.cs：CompensateDataService()，L30；List<RoundGroup> GetRoundsAfterTime(DateTime startTime)，L39；int GetPointPerRound() => _pointPerRound;，L68
- trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsDomain.cs：void StatisticsBondPositionInfo(BondPosition bondPosition, BaseCarrierConfig component)，L165；void RefreshS2DispenseStatistics()，L217；void RefreshDispenseStatistics()，L232
- trunk/AKRS.ZX2200/SupportFeature/Statistics/DefectStatisticsEntity.cs：DefectStatisticsEntity(DateTime dateTime, string defectName, string id, int subIndex, int moduleIndex, string bondPositionName, double offsetX, double offsetY, double offsetAngle, double area, double tpOffsetX, double tpOffsetY, double upLookOffsetX, double upLookOffsetY, double bondPositionX, double bondPositionY, double bpOffsetX, double bpOffsetY,double substrateCameraCompensateX,double substrateCameraCompensateY)，L164

- trunk/AKRS.ZX2200/SupportFeature/Statistics/StatisticsService.cs：SaveEntityToDb，L110-124

## [16] 人工维护区域补偿表

统计导入、行平滑、编辑、清空和生产使用

- trunk/AKRS.ZX2200/SupportFeature/Compensate/MotionAreaCompensate/FrmBondCompensate.cs：void BtInput_Click(object sender, EventArgs e)，L48；void BtSave_Click(object sender, EventArgs e)，L190
- trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs：void Init()，L203
- trunk/AKRS.ZX2200/SupportFeature/Compensate/MotionAreaCompensate/TransportUnitCompensate.cs：AKRSPoint3D GetBondCompensate(double x, double y)，L66
- trunk/AKRS.ZX2200/SupportFeature/Compensate/MotionAreaCompensate/FrmInputData.cs：FrmInputData()，L23；void FrmInputData_Load(object sender, EventArgs e)，L43；void FrmInputData_FormClosed(object sender, FormClosedEventArgs e)，L54

## [17] 标定与诊断输入

IPT示教、标定验证和诊断入口与生产流程的归属

- trunk/AKRS.ZX2200/BondSystem/Controls/Manual/FrmLearnIPT.cs：FrmLearnIPT(IPTTypeEnum iptType)，L35；void InitControl()，L90；void SetUIControl(int stepIndex)，L220
- trunk/AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs：void Save()，L290
- trunk/AKRS.ZX2200/SupportFeature/Compensate/MotionAreaCompensate/FrmCompensateTest.cs：FrmCompensateTest()，L23；void simpleButton1_Click(object sender, EventArgs e)，L28
- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondPositionVisionTest.cs：override ExcuteResult DoWork()，L33
- trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/BilinearCompensator.cs：BilinearCompensationRegion()，L33；bool FindInterpolationCell(Coords2D pt, out KeyValuePair<Coords2D, Coords2D>[] cellCorners)，L62；bool TryInterpolate(double x, double y, out AKRSPoint2D result)，L98
- trunk/AKRS.ZX2200/BondSystem/BondForce/Services/ForceCalibrationService.cs：static double ActualForceToInputForce(double force, double initialValue, double angle)，L35；static double ForceIncrementToActualForce(double forceIncrement, bool isSmallForce, double angle)，L207；static double GetSmallForceModelChange(double inputValue, double initialValue)，L310
