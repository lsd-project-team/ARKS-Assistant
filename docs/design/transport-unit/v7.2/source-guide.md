# Transport Unit源码阅读索引

完整路径、主题与行号锚点。文件哈希以source-baseline.json为准。

## [1] 运行对象与状态

对象层级、查询、刷新、镜像标记及参与范围

- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/TransportUnit.cs：void Init()，L107；void Refresh()，L135；BondPosition GetBondPosition(int substrateIndex, int moduleIndex, string bondPositionName)，L195
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/BaseMatter.cs：BaseConfig GetConfigByType(EntityTypeEnum type)，L111；abstract void SetMatterDisable();，L89
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/Substrate.cs：void Refresh(int index, GeneralCoordinateSystem upperCoordinateSystem)，L182
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/Module.cs：void Refresh(int index, GeneralCoordinateSystem upperCoordinateSystem)，L148
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Matter/BondPosition.cs：void Refresh(GeneralCoordinateSystem upperCoordinateSystem)，L88
- trunk/AKRS.ZX2200/TransportUnitSystem/Model/TuEnum.cs：字段定义，L1

## [2] 配置与展开

常规、异形节点、阵列和状态配置

- trunk/AKRS.ZX2200/TransportUnitSystem/ProductConfiguration.cs：void InitProductConfiguration()，L71；void ClearProductConfigurationInstance()，L80；bool IsTransportUnitReady()，L89
- trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs：static void CreateMatterCoordinate(BaseMatter baseMatter, GeneralCoordinateSystem upperCoordinateSystem, ElementCoordinate elementCoordinate)，L872；static void UpdateEntity(BaseMatter baseEntity, AdjustTypeEnum type)，L528；static TransportUnit ReadTransportMapping()，L1800
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/TransportUnitConfig.cs：TransportUnitConfig()，L158；bool GetAssistantResult()，L255；List<AssistantState> GetAssistantStates()，L280
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/OppositeSex.cs：OppositeSexConfig GetConfig()，L128；static string GetDefaultName(string name)，L147；static bool IsExistName(string name)，L170
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/OppositeSexConfiguration.cs：void InitOppositeSexConfigIndex()，L64；void RemoveOppositeSexConfig(OppositeSex oppositeSexConfig)，L236
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/ArrayConfig.cs：字段定义，L1
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/SubstrateConfig.cs：List<int> GetFrontSubstrateIndex()，L71；List<int> GetBackSubstrateIndex()，L116；List<int> GetSubstrateIndex()，L155
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/ModuleConfig.cs：字段定义，L1
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/BaseConfig.cs：void RefreshMeasureHeightPoint()，L65
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/OtherConfig.cs：void SaveInformation(TransportUnit transportUnit)，L95；void ClearInformation()，L38
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/SingleBondPositionConfig.cs：SingleBondPositionConfig()，L144；bool GetAssistantResult()，L184；List<AssistantState> GetAssistantStates()，L208

## [3] 动作控制与步骤

消息解析、步骤注入、相对固晶重排

- trunk/AKRS.ZX2200/Main/Machine/Process/S1ActionNodeController.cs：void Init()，L168；void InjectSteps(TransportUnit transportUnit)，L859
- trunk/AKRS.ZX2200/Main/Machine/Process/S2ActionNodeController.cs：void Init()，L155；void InjectSteps(TransportUnit transportUnit)，L1410
- trunk/AKRS.ZX2200/Main/Machine/Process/SingleProcessStep.cs：SingleProcessStep()，L20
- trunk/AKRS.ZX2200/Infrastructure/Models/CommonModels/ActionNodeMessage.cs：ActionNodeMessage(string actionNodeName, int substrate, int module, string processStepName)，L21
- trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/OtherAction/InteractiveAction.cs：override ExcuteResult DoWork()，L29

## [4] 运行信息

Info、定位结果、身份与完成记录

- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Information/BaseInformation.cs：字段定义，L1
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Information/TransportUnitInfo.cs：字段定义，L1
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Information/SubstrateInfo.cs：字段定义，L1
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Information/ModuleInfo.cs：字段定义，L1
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Information/BondPositionInfo.cs：bool IsFinishedInSystem1()，L118；bool IsFinishedInSystem2()，L145；void SetFinishedInSystem1()，L166
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Information/LocateResultInfo.cs：字段定义，L1
- trunk/AKRS.ZX2200/TransportUnitSystem/Model/VisionResult.cs：void SaveInfo(MatchResult matchResult, AKRSPoint3D resultPoint3D, AKRSPoint3D resultPoint3DInG0, AKRSPoint3D visionPoint3DInG0)，L60

## [5] 坐标调用接口

本目录中的坐标建立、转换调用和参数归属

- trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs：static void CreateMatterCoordinate(BaseMatter baseMatter, GeneralCoordinateSystem upperCoordinateSystem, ElementCoordinate elementCoordinate)，L872；static void UpdateEntity(BaseMatter baseEntity, AdjustTypeEnum type)，L528；static TransportUnit ReadTransportMapping()，L1800
- trunk/AKRS.ZX2200/BondSystem/Controllers/BondModuleController.cs：AKRSPoint3D ConvertG0ToMachinePos(AKRSPoint3D pos)，L173
- trunk/AKRS.ZX2200/DispenseSystem/Controllers/DispenseController.cs：void MoveToSafePos()，L103；void MoveToG0Pos3D(AKRSPoint3D point3D, bool isMeasureOpen = false)，L129；void MoveToG0Pos3DWithoutSafe(AKRSPoint3D point3D)，L191

## [6] 点胶生产入口

S1创建、执行、放行和写回

- trunk/AKRS.ZX2200/DispenseSystem/Tasks/DispenseWorkTask.cs：void DoWork()，L63
- trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/DispenseBPAction/S1DispenseActionNode.cs：override ExcuteResult DoWork()，L46

## [7] 固晶生产入口

S2创建、动作处理和产品发送

- trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs：void DoWork()，L100
- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.cs：override ExcuteResult DoWork()，L118

## [8] 输送与搜索

交接、物料搜索、人工补料和完成信号

- trunk/AKRS.ZX2200/TransportSystem/Models/TransportProgram.cs：void InitTransportSystemProgram()，L71；void RefreshTransportUnit()，L90；List<BaseSubSectionProgram> GetSubSectionPrograms()，L112
- trunk/AKRS.ZX2200/TransportSystem/Models/Programs/BaseSubSectionProgram.cs：void UpdateTransportUnit()，L62；void RefreshTransportUnit()，L71
- trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs：ExcuteResult TransferDispenseToBond(bool isManual = false)，L1266
- trunk/AKRS.ZX2200/TransportSystem/Controllers/DispenseSubSectionController.cs：override void MapBelt(bool AutoWork)，L437
- trunk/AKRS.ZX2200/TransportSystem/Controllers/BondSubSectionController.cs：override void MapBelt(bool autoWork)，L429
- trunk/AKRS.ZX2200/TransportSystem/Controllers/WaitingUnloadSubSectionController.cs：override void MapBelt(bool AutoWork)，L71
- trunk/AKRS.ZX2200/TransportSystem/Controllers/UnloadingSubSectionController.cs：override void MapBelt(bool AutoWork)，L71
- trunk/AKRS.ZX2200/TransportSystem/Models/TransportDomain.cs：void StartTask()，L84
- trunk/AKRS.ZX2200/TransportSystem/Tasks/TransportTask.cs：void Start()，L115；void StartDryRun()，L775；bool IsAlive()，L897
- trunk/AKRS.ZX2200/TransportSystem/Models/Programs/DispenseSubSectionProgram.cs：bool IsSettingNull()，L73
- trunk/AKRS.ZX2200/TransportSystem/Controls/Manual/UcTransportSystemManual.cs：UcTransportSystemManual()，L32；void ChkEmptyIndexOn_CheckedChanged(object sender, EventArgs e)，L47；void BtTransportUnitIndex_Click(object sender, EventArgs e)，L57

## [9] 示教与界面入口

示教重建、扫描、Mapping显示和状态编辑

- trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Assistant/TUAssistantHelper.cs：static TransportUnit JudgeTuExist()，L392
- trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.ShortcutKeys.cs：void UcMainSystem_KeyDown(object sender, KeyEventArgs e)，L45
- trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs：void Init()，L203
- trunk/AKRS.ZX2200/DispenseSystem/Controls/Setting/EpoxyApplication/UcEpoxyApplication.cs：void Init()，L123
- trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Mapping/UcTransportShow.cs：UcTransportShow(TransportUnit transportUnit, CurrentMachineSystemEnum system)，L44；static extern bool GetCursorPos(out System.Drawing.Point lpPoint);，L82；void PaintFramework()，L192
- trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Mapping/FrmTuMapping.cs：void FrmTuMapping_FormClosed(object sender, FormClosedEventArgs e)，L390；void TsmEnable_Click(object sender, EventArgs e)，L620
- trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Mapping/FrmTuMappingNew.cs：void FrmTuMappingNew_FormClosed(object sender, FormClosedEventArgs e)，L180；void BtClearAll_Click(object sender, EventArgs e)，L112
- trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Mapping/FrmTransportUnitMapping.cs：FrmTransportUnitMapping(BaseSubSectionProgram baseSubSectionProgram)，L32；void FrmTransportUnitMapping_Load(object sender, EventArgs e)，L58；void ReFreshUi()，L78
- trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Mapping/FrmAddTuInfo.cs：FrmAddTuInfo(TransportUnit transportUnit)，L26；void BtSure_Click(object sender, EventArgs e)，L42；void FrmAddTuInfo_Load(object sender, EventArgs e)，L63
- trunk/AKRS.ZX2200/BondSystem/Controls/Assistant/FrmTeachBondingPosition.cs：void Save()，L390
- trunk/AKRS.ZX2200/BondSystem/Controls/Assistant/FrmRelativeBondTeach.cs：void Save()，L185
- trunk/AKRS.ZX2200/Main/Controls/UcShortcutMenu.cs：void BtInitializeTS_Click(object sender, EventArgs e)，L228；void BtClearDispense_Click(object sender, EventArgs e)，L242

## [10] 存储边界

区段忽略序列化及独立TU存储接口

- trunk/AKRS.ZX2200/TransportUnitSystem/Model/TransportUnitStorage.cs：static void Save(TransportUnit transportUnit, string path)，L35；static TransportUnit Read(string path)，L62
- trunk/AKRS.ZX2200/TransportSystem/Models/Programs/BaseSubSectionProgram.cs：void UpdateTransportUnit()，L62；void RefreshTransportUnit()，L71

## [11] 定位与测高写回

领域采集、坐标和结果的写入

- trunk/AKRS.ZX2200/DispenseSystem/Models/System1Domain.cs：bool System1MatterVision(BaseMatter baseEntity, bool byMapping = true)，L96
- trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs：bool System2MatterVision(BaseMatter baseEntity, bool byMapping = true)，L279
- trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/DispenseBPAction/S1DispenseActionNode.cs：override ExcuteResult DoWork()，L46
- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.cs：override ExcuteResult DoWork()，L118
- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs：override ExcuteResult DoWork()，L131

## [12] 启动调度

准备、任务启动和物料搜索

- trunk/AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs：bool CheckOperatingEnvironment()，L89；void ResetMachineSignal()，L133；void ReadyToLog()，L168
- trunk/AKRS.ZX2200/TransportSystem/Models/TransportDomain.cs：void StartTask()，L84

## [13] 身份记录

读码、离线和跳过条件

- trunk/AKRS.ZX2200/DispenseSystem/Models/System1Domain.cs：bool System1MatterVision(BaseMatter baseEntity, bool byMapping = true)，L96
- trunk/AKRS.ZX2200/BondSystem/Models/System2Domain.cs：bool System2MatterVision(BaseMatter baseEntity, bool byMapping = true)，L279
- trunk/AKRS.ZX2200/DispenseSystem/Models/DispenseAction/IdentityActionNode/S1SubstrateIdentityActionNode.cs：override ExcuteResult DoWork()，L40
- trunk/AKRS.ZX2200/BondSystem/Models/ActionNodes/IdentityActionNode/S2SubstrateIdentityActionNode.cs：override ExcuteResult DoWork()，L40

## [14] Mapping导入

按当前配方创建树、恢复部分记录并替换引用

- trunk/AKRS.ZX2200/TransportUnitSystem/Service/TuService.cs：static TransportUnit ReadTransportMapping()，L1800；static TransportUnit ReadTransportMappingByComponent(string transportId)，L1953
- trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Mapping/FrmTransportUnitMapping.cs：FrmTransportUnitMapping(BaseSubSectionProgram baseSubSectionProgram)，L32；void FrmTransportUnitMapping_Load(object sender, EventArgs e)，L58；void ReFreshUi()，L78

## [15] 异形配置编辑与节点匹配

配置树编辑、重排ID和运行节点关联

- trunk/AKRS.ZX2200/TransportUnitSystem/Controls/TransportUnitEdit/FrmTransportUnitEdit.cs：void BtAdd_Click(object sender, EventArgs e)，L114；void BtDelete_Click(object sender, EventArgs e)，L142；void BtCopy_Click(object sender, EventArgs e)，L179
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/OppositeSexConfiguration.cs：void InitOppositeSexConfigIndex()，L64；void RemoveOppositeSexConfig(OppositeSex oppositeSexConfig)，L236
- trunk/AKRS.ZX2200/TransportUnitSystem/Controls/TransportUnitEdit/FrmAddObject.cs：FrmAddObject()，L25；void BtSure_Click(object sender, EventArgs e)，L65；void BtCancel_Click(object sender, EventArgs e)，L141
- trunk/AKRS.ZX2200/TransportUnitSystem/Controls/TransportUnitEdit/FrmObjectCopy.cs：FrmObjectCopy(OppositeSex oppositeSexConfig)，L30；void BtCancel_Click(object sender, EventArgs e)，L53；void BtSure_Click(object sender, EventArgs e)，L63
- trunk/AKRS.ZX2200/TransportUnitSystem/Controls/TransportUnitEdit/UcTransportUnitView.cs：void Init()，L245
- trunk/AKRS.ZX2200/TransportUnitSystem/Controls/TransportUnitEdit/UcObjectFunctionEdit.cs：void Init(OppositeSex oppositeSexConfig)，L93；void Save()，L790
- trunk/AKRS.ZX2200/Infrastructure/Controls/Feature/EditProgram/UcEditProductProgram/UcEditProductProgramming.cs：UcEditProductProgramming()，L97；void RefreshNode()，L119；TreeListNode GetInputNode()，L390

## [16] 配方与生产Mapping

样本对象、参与状态保存和关闭后的清空确认

- trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Mapping/FrmTuMappingNew.cs：void FrmTuMappingNew_FormClosed(object sender, FormClosedEventArgs e)，L180；void BtClearAll_Click(object sender, EventArgs e)，L112
- trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Mapping/FrmTuMapping.cs：void FrmTuMapping_FormClosed(object sender, FormClosedEventArgs e)，L390；void TsmEnable_Click(object sender, EventArgs e)，L620
- trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Mapping/UcTransportShow.cs：UcTransportShow(TransportUnit transportUnit, CurrentMachineSystemEnum system)，L44；static extern bool GetCursorPos(out System.Drawing.Point lpPoint);，L82；void PaintFramework()，L192
- trunk/AKRS.ZX2200/TransportUnitSystem/Module/Config/OtherConfig.cs：void SaveInformation(TransportUnit transportUnit)，L95；void ClearInformation()，L38
- trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Mapping/MappingDraw.cs：MappingDraw(List<MatterProductInformation> matterProductStateList)，L61；void DrawingFrame(Graphics g, PanelControl panelControl)，L95；void DrawBaseEntityFrame(Graphics g, BaseMatter baseEntity, Pen pen)，L161
- trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs：void Init()，L203

## [17] 主动清空载具

整线与局部引用清除及界面进入条件

- trunk/AKRS.ZX2200/TransportSystem/Controllers/TransportController.cs：void InitializeTS()，L159；void InitializeTSInDispense()，L229；void InitializeTSInBond()，L282
- trunk/AKRS.ZX2200/Main/Controls/UcShortcutMenu.cs：void BtInitializeTS_Click(object sender, EventArgs e)，L228；void BtClearDispense_Click(object sender, EventArgs e)，L242
- trunk/AKRS.ZX2200/TransportSystem/Controls/Manual/UcTransportSystemManual.cs：UcTransportSystemManual()，L32；void ChkEmptyIndexOn_CheckedChanged(object sender, EventArgs e)，L47；void BtTransportUnitIndex_Click(object sender, EventArgs e)，L57

## [18] 辅助对象与补偿模式

窗口对象、局部测试与区段替换

- trunk/AKRS.ZX2200/BondSystem/Tasks/BondTask.cs：void DoWork()，L100
- trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Assistant/TUAssistantHelper.cs：static TransportUnit JudgeTuExist()，L392
- trunk/AKRS.ZX2200/BondSystem/Controls/Assistant/FrmMoveToBondingPosition.cs：void Init()，L97；void Save()，L248
- trunk/AKRS.ZX2200/DispenseSystem/Controls/Setting/EpoxyApplication/UcEpoxyApplication.cs：void Init()，L123
- trunk/AKRS.ZX2200/Experiment/TestFunction/FrmTest.cs：FrmTest()，L53；static void ShowUi()，L61；void SimpleButton1_Click(object sender, EventArgs e)，L70

## [19] 位置辅助接口

固晶区段读取、配置点和返回参考系

- trunk/AKRS.ZX2200/BondSystem/Services/System2TUService.cs：static AKRSPoint3D GetSubstratePos(int index)，L21；static AKRSPoint3D GetModulePos(int substrateIndex, int moduleIndex)，L51
- trunk/AKRS.ZX2200/BondSystem/Controls/Assistant/FrmMoveToBondingPosition.cs：void Init()，L97；void Save()，L248
- trunk/AKRS.ZX2200/BondSystem/Controls/Setting/BondPosition/UcBondPositionEdit.cs：void Save()，L265

## [20] 角度示教写回

窗口对象、调用方目标及分阶段保存

- trunk/AKRS.ZX2200/Infrastructure/Controls/Feature/EditProgram/UcEditProductProgram/UcEditProductProgramming.Assistance.cs：void AssistanceTuAdjust()，L63；void AssistanceSubAdjust()，L159
- trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Assistant/FrmAdjustDegree.cs：void InitControl()，L91
- trunk/AKRS.ZX2200/TransportUnitSystem/Controls/Assistant/TUAssistantHelper.cs：static TransportUnit JudgeTuExist()，L392
