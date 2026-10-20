# 纠偏过程源码阅读索引

完整路径、主题与行号锚点。文件哈希以source-baseline.json为准。

## [1] 纠偏对象与配置

产品定位和芯片纠偏的配置入口及字段归属

- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/LocateConfig.cs：class LocateConfig，L20；string P1PRName => MachineConfigContext.GetInstance().RecipeName + this.Name + "Mark1";，L43
- trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/AdjustConfig.cs：class AdjustConfig，L32；AKRSPoint3D P1VisionPos { get; set; } = new AKRSPoint3D();，L42
- trunk/AKRS.ZX2200/WaferSubSystem/Models/Repositories/Carrier/BaseCarrierConfig.cs：AdjustConfig UpLookAdjustConfig { get; set; } = new AdjustConfig();，L482；AdjustConfig DownLookAdjustConfig { get; set; } = new AdjustConfig();，L490
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Information/BondPositionInfo.cs：class BondPositionInfo : BaseInformation，L18；MatchResult UpLookMatchResult1 { get; set; } = new MatchResult();，L23

## [2] 产品层级定位

采集、选点、几何更新与两侧距离检查

- trunk/AKRS.ZX2200/DispenseSystem/Models/System1Domain.cs：bool System1MatterVision(BaseMatter baseEntity, bool byMapping = true)，L96；bool System1VisionByPos(BaseMatter baseEntity, TuService.NormalVisionType type,bool alarm = false)，L205
- trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs：bool System2ObjectVision(BaseMatter baseEntity, bool byMapping = true)，L267；bool System2MatterVision(BaseMatter baseEntity, bool byMapping = true)，L279
- trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs：enum NormalVisionType，L443；static (AKRSPoint3D point3D, string pRName,bool Autofocus) GetVisionInfo(BaseMatter baseEntity, NormalVisionType type)，L472
- trunk/AKRS.ZX2200/TransportUnitSystem/Model/VisionResult.cs：class VisionResult，L11；void SaveInfo(MatchResult matchResult, AKRSPoint3D resultPoint3D, AKRSPoint3D resultPoint3DInG0, AKRSPoint3D visionPoint3DInG0)，L60
- trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/BaseCoordinateSystem.cs：AKRSPoint3D ForwardConvertCoordinate(AKRSPoint3D value)，L84；void UpdateCoordinateSystem(AKRSPoint3D oldPoint3D, AKRSPoint3D newPoint3D, double degree)，L204
- trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/GeneralCoordinateSystem.cs：double DegreeInG0()，L107

## [3] 坐标转换与标定输入

相机像素到物理位置、吸嘴偏心及旋转帮助方法

- trunk/AKRS.ZX2200/BondSystem/Modules/UpLookModule.cs：class UpLookModule，L19；AKRSCamera UpLookCamera => HardwareRepositoryService.GetHardware<AKRSCamera>("上视相机");，L25
- trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.Vision.cs：BaseAlgResult BondCameraVision(AKRSPoint3D visionPosition, string pRName, bool isZSafe = false, bool isDefect = false, bool autofocus = false)，L159；AKRSPoint3D GetBondVisionResultPos(MatchResult result, AKRSPoint3D visionPos = null)，L652
- trunk/AKRS.ZX2200/DispenseSystem/Controllers/DispenseController.cs：AKRSPoint3D GetG0VisionPos(AKRSPoint3D point3D)，L262；AKRSPoint3D GetG0PosFromVision(AKRSPoint3D point3D)，L273
- trunk/AKRS.ZX2200/BondSystem/Controllers/BondHeadController.cs：AKRSPoint2D GetNozzleOffset(string nozzleName, double angle)，L970；AKRSPoint2D GetNozzleOffset(AKRSPoint2D offset, double angle)，L987
- trunk/AKRS.ZX2200/Infrastructure/Utils/MathHelper.cs：static class MathHelper，L26；static AKRSPoint3D RotateCenter(AKRSPoint3D distanceToCenter,double degree)，L34

## [4] 上视纠偏与温漂

入口模式、采集次序、偏移计算与温漂调用链

- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs：override ExcuteResult DoWork()，L131；override bool IsDoWork()，L520
- trunk/AKRS.ZX2200/BondSystem/Models/Parameter/System2RunTimeProvider.cs：static MatchResult GetMatchResultByConfig(MatchResult matchResult,LocateUseConfig locateUseConfig)，L415
- trunk/AKRS.ZX2200/SupportFeature/Compensate/TemperatureCompensate/TpMarkCompensate.cs：static bool TemperatureCompensation(bool firstTu)，L64；static AKRSPoint3D GetTemperatureCompensation()，L240
- trunk/AKRS.ZX2200/BondSystem/Controllers/System2Controller.Vision.cs：BaseAlgResult BondCameraVision(AKRSPoint3D visionPosition, string pRName, bool isZSafe = false, bool isDefect = false, bool autofocus = false)，L159；AKRSPoint3D GetBondVisionResultPos(MatchResult result, AKRSPoint3D visionPos = null)，L652

## [5] 中转台纠偏

放片、定位、修正取片位与重取分支

- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.cs：override ExcuteResult DoWork()，L136；override bool IsDoWork()，L520
- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.Provider.cs：partial class SubstrateCameraCorrectionActionNode，L28；void PrepareBeforeAction()，L33

## [6] 贴装输出使用

角度与XY使用、补偿次序和统计数据边界

- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.Provider.cs：AKRSPoint4D CalculateBondPos()，L498
- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.cs：override ExcuteResult DoWork()，L118
- trunk/AKRS.ZX2200/SupportFeature/Compensate/MotionAreaCompensate/RealTimeCorrection.cs：AKRSPoint3D GetCompensatePoint3D(AKRSPoint3D iptPickPos, AKRSPoint3D iptVisionPos, AKRSPoint3D bondPos, AKRSPoint3D bondVisonPos)，L149
- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/AfterBondCheckActionNode.cs：double distanceY = Math.Round(point4D.Y - this.PostBondInspection.PostBondDistanceY, 5);，L560

## [7] 报警与人工确认

报警返回、PR重跑与距离检查选项

- trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcmainSystem.Action.cs：(DialogResult, BaseAlgResult) VisionAlarm(PREntity pREntity, string message, string caption)，L234；(DialogResult, BaseAlgResult) VisionAlarm(PREntity pREntity, string message, string caption, PRHardware pRHardware = null)，L273
- trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/FrmVisionAlarm.cs：void BtOK_Click(object sender, EventArgs e)，L339；void BtSkip_Click(object sender, EventArgs e)，L505
- trunk/AKRS.ZX2200/Infrastructure/Service/VisionService.cs：static BaseAlgResult Vision(string pRName, PRHardware prHardware, string systemName = "Other", string bitmapName = "", bool setLight = true)，L78；static DialogResult DistanceCheck(BaseMatter baseMatter)，L257

## [8] 动作编排与完成记录

重做动作的选择、Retry及消息完成处理

- trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs：List<ActionNodeMessage> GetActionNodeMessageByProcess(SingleProcessStep singleProcess, int substrateIndex, int moduleIndex)，L715；void SetActionNodeReWork(List<ActionNode> actionNodes)，L1099
- trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs：ExcuteResult ret = actionNode.DoWork();，L232
- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/AdjustActionNode/S2SubstrateVisionActionNode.cs：class S2SubstrateVisionActionNode : ActionNode，L29；System2Domain system2Domain => System2Domain.GetInstance();，L34
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Information/BondPositionInfo.cs：class BondPositionInfo : BaseInformation，L18；MatchResult UpLookMatchResult1 { get; set; } = new MatchResult();，L23
