# Transport Unit源码阅读索引

完整路径、主题与行号锚点。文件哈希以source-baseline.json为准。

## [1] 产品运行对象与状态

对象层级、查询、刷新、偏移与参与范围

- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/TransportUnit.cs：TransportUnit(string reason)，L73；void Init()，L107
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/BaseMatter.cs：abstract class BaseMatter，L22；BaseConfig GetConfigByType，L111
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/Substrate.cs：Substrate(int index，L51；void Refresh(int index，L182
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/Module.cs：Module(int index，L54；void CreateBondPosition()，L107
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/BondPosition.cs：BondPosition(string name，L40；bool IsFinishedInSystem1，L129
- trunk/AKRS.ZX2200/TransportUnitSystem/Model/TuEnum.cs：enum MatterProductState，L278；enum EntityState，L256

## [2] 产品配置与展开服务

常规／异形结构、阵列、状态映射及Mapping输出

- trunk/AKRS.ZX2200/TransportUnitSystem/ProductConfiguration.cs：class ProductConfiguration，L22；void InitProductConfiguration()，L71
- trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs：static void CreateMatterCoordinate，L872；static void ModifyMatter，L887
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/TransportUnitConfig.cs：class TransportUnitConfig，L24
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/OtherConfig.cs：void ClearInformation()，L38
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/OppositeSex.cs：OppositeSexConfig Config，L121
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/ArrayConfig.cs：class ArrayConfig，L18
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/BaseConfig.cs：class BaseConfig，L22
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/SubstrateConfig.cs：GetFrontSubstrateIndex，L71
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/ModuleConfig.cs：class ModuleConfig，L13
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/SingleBondPositionConfig.cs：class SingleBondPositionConfig，L24

## [3] 动作控制与步骤定义

当前对象解析、消息复位与缺失步骤键注入

- trunk/AKRS.ZX2200/Main/Machine/Process/S1ActionNodeController.cs：void InjectSteps(TransportUnit transportUnit)，L859；ActionNode GetNextActionNode()，L776
- trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs：void InjectSteps(TransportUnit transportUnit)，L1410；ActionNode GetNextActionNode()，L1042
- trunk/AKRS.ZX2200/Main/Machine/Process/SingleProcessStep.cs：class SingleProcessStep，L15
- trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/ActionNodeMessage.cs：class ActionNodeMessage，L12

## [4] 运行信息与定位结果

独立Info、IsProduct、步骤完成条件及定位数据

- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Information/BaseInformation.cs：abstract class BaseInformation，L12
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Information/TransportUnitInfo.cs：class TransportUnitInfo，L12
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Information/BondPositionInfo.cs：class BondPositionInfo，L18；bool IsFinishedInSystem1()，L118
- trunk/AKRS.ZX2200/TransportUnitSystem/Model/VisionResult.cs：SaveInfo，L60
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Information/LocateResultInfo.cs：class LocateResultInfo，L13

## [5] 父坐标与几何转换

普通正逆变换、父链合成与坐标更新

- trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/BaseCoordinateSystem.cs：AKRSPoint3D ForwardConvertCoordinate，L84；void Init(ElementCoordinate，L281
- trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/GeneralCoordinateSystem.cs：AKRSPoint3D SelfPosToG0，L44；double DegreeInG0()，L107
- trunk/AKRS.Galaxy2.CoordinateSystems/CoordinateSystems/ElementCoordinate.cs：class ElementCoordinate，L11
- trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs：static void CreateMatterCoordinate，L872；static void ModifyMatter，L887

## [6] 点胶生产入口

IsProduct重建、放行顺序和点胶工序写回

- trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs：if (this.Enable)，L93；TransportUnitInfo.IsProduct =，L99
- trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/DispenseBPAction/S1DispenseActionNode.cs：override ExcuteResult DoWork()，L46；override bool IsDoWork()，L177

## [7] 固晶生产入口

有条件重建、步骤执行、结束与产品发送

- trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs：new TransportUnit(CurrentMachineSystemEnum.System2)，L204；ExcuteResult ret = actionNode.DoWork()，L232
- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.cs：override ExcuteResult DoWork()，L118；override bool IsDoWork()，L383

## [8] 输送与区段产品引用

自动交接、Refresh、源清空、完成信号与物料搜索

- trunk/AKRS.ZX2200/TransportSystem/Models/TransportProgram.cs：class TransportProgram，L20；void RefreshTransportUnit()，L90
- trunk/AKRS.ZX2200/TransportSystem/Models/Programs/BaseSubSectionProgram.cs：abstract class BaseSubSectionProgram，L36；void UpdateTransportUnit()，L62
- trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs：ExcuteResult TransferAutoLoaderToLoading，L439；ExcuteResult TransferDispenseToBond，L1266
- trunk/AKRS.ZX2200/TransportSystem/Models/TransportDomain.cs：void StartTask()，L84；TransportProgram.RefreshTransportUnit();，L117
- trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs：ExcuteResult ret = this.transportController.TransferDispenseToBond();，L525；TransferToBondFinishedSignal.Set();，L540
- trunk/AKRS.ZX2200/TransportSystem/Controllers/DispenseSubSectionController.cs：this.dispenseSubSectionProgram.TransportUnit.Refresh();，L482；this.dispenseSubSectionProgram.TransportUnit.System1BackMoveDistance();，L504

## [9] 示教与人工状态修改

示教重建、工位偏移、Mapping与信息编辑

- trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Assistant/TUAssistantHelper.cs：static TransportUnit JudgeTuExist()，L392
- trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.ShortcutKeys.cs：void VisionScan()，L126
- trunk/AKRS.ZX2200/DispenseSystem/Controls/Setting/EpoxyApplication/UcEpoxyApplication.cs：transportUnit.SetSystem1OffSet();，L813；transportUnit.System1MoveDistance();，L843
- trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Mapping/UcTransportShow.cs：TransportUnitInfo.IsProduct = true;，L56；void BtNormal_ItemClick，L938
- trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Mapping/FrmTransportUnitMapping.cs：TransportUnitInfo.IsProduct = true;，L62
- trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Mapping/FrmAddTuInfo.cs：void BtSure_Click，L42

## [10] 存储与配置关联

独立TU存储及当前配方关联的边界

- trunk/AKRS.ZX2200/TransportUnitSystem/Model/TransportUnitStorage.cs：static void Save(TransportUnit transportUnit，L35；static TransportUnit Read，L62
- trunk/AKRS.ZX2200/TransportUnitSystem/ProductConfiguration.cs：class ProductConfiguration，L22；void InitProductConfiguration()，L71
- trunk/AKRS.ZX2200/TransportSystem/Models/Programs/BaseSubSectionProgram.cs：abstract class BaseSubSectionProgram，L36；void UpdateTransportUnit()，L62

## [11] 具体动作中的位置与记录

定位和测高写回、点胶与固晶执行条件

- trunk/AKRS.ZX2200/DispenseSystem/Models/System1Domain.cs：bool System1MatterVision，L96；baseEntity.BaseInfo.MeasureHeightResult = addHieght;，L460
- trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs：bool System2MatterVision，L279；baseEntity.BaseInfo.MeasureHeightResult = addHeight;，L995
- trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs：static void CreateMatterCoordinate，L872；static void ModifyMatter，L887
- trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/DispenseBPAction/S1DispenseActionNode.cs：override ExcuteResult DoWork()，L46；override bool IsDoWork()，L177
- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.cs：override ExcuteResult DoWork()，L118；override bool IsDoWork()，L383

## [12] 机器启动调度

准备、任务启动与S2动作控制器初始化

- trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs：void Start(，L261

## [13] 身份识别记录的有效期

识别结果保存、离线标记及重复识别条件

- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Information/BaseInformation.cs：abstract class BaseInformation，L12
- trunk/AKRS.ZX2200/DispenseSystem/Models/System1Domain.cs：baseEntity.BaseInfo.IsIdentity = true;，L624；baseEntity.BaseInfo.IdentityCode = codeResult.CodeValue;，L625
- trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs：baseEntity.BaseInfo.IsIdentity = true;，L1088；baseEntity.BaseInfo.IdentityCode = codeResult.CodeValue;，L1089
- trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/IdentityActionNode/S1SubstrateIdentityActionNode.cs：override ExcuteResult DoWork()，L40；if (this.substrate.BaseInfo.IsIdentity)，L102
- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/IdentityActionNode/S2SubstrateIdentityActionNode.cs：override ExcuteResult DoWork()，L40；if (this.substrate.BaseInfo.IsIdentity)，L102
