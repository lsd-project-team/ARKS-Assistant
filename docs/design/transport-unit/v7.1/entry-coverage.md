# 已发现相关入口的逐项归属

范围：trunk/AKRS.ZX2200。1158个C#文件完成语法扫描，1137个显式Compile项。扫描不等于逐文件业务通读；关键已读范围另见source-analysis.json。

| 文件 | 编译 | 归属 | 文档位置 | 核查结论 |
|---|---|---|---|---|
| BondSystem/Controllers/System2Controller.Assistant.cs | True | 手动辅助与公共计算 | 纠偏 3.3、8.5 | 手动贴片定位后只支持独立上视；CalculatePickPos也是生产使用的公共取片计算。 |
| BondSystem/Controls/Assistant/FrmMoveToBondingPosition.cs | True | 手动辅助 | TU 6.6 | 界面创建自身使用的TU，不是生产区段引用交接。 |
| BondSystem/Controls/Assistant/FrmRelativeBondTeach.cs | True | 示教保存 | TU 5.3、6.5 | Save中的UpdateTransportUnit重建当前运行树；不纳入生产定位动作 |
| BondSystem/Controls/Assistant/FrmTeachBondingPosition.cs | True | 示教保存 | TU 5.3、6.5 | 保存后重建；不沿用旧对象及旧几何 |
| BondSystem/Controls/Manual/FrmLearnIPT.cs | True | 示教输入 | 纠偏 2.1、6.1 | IPTVisionPos命中是设备参数写入，不是运行焊点Info或生产纠偏调用。 |
| BondSystem/Controls/Setting/BondPosition/UcBondPositionEdit.cs | True | 示教入口 | TU 6.6 | 命中只是当前TU空检查，不增加独立生产流程。 |
| BondSystem/Models/ActionNodes/AdjustActionNode/BondPositionVisionActionNode.cs | True | 生产定位动作 | 纠偏 4.2 | 八入口之一；IsDoWork与DoWork独立核对，领域bool不直接决定动作Success。 |
| BondSystem/Models/ActionNodes/AdjustActionNode/S2CarrierVisionActionNode.cs | True | 生产定位动作 | 纠偏 4.2 | 八入口之一；IsDoWork与DoWork独立核对，领域bool不直接决定动作Success。 |
| BondSystem/Models/ActionNodes/AdjustActionNode/S2ModuleVisionActionNode.cs | True | 生产定位动作 | 纠偏 4.2 | 八入口之一；IsDoWork与DoWork独立核对，领域bool不直接决定动作Success。 |
| BondSystem/Models/ActionNodes/AdjustActionNode/S2SubstrateVisionActionNode.cs | True | 生产定位动作 | 纠偏 4.2 | 八入口之一；IsDoWork与DoWork独立核对，领域bool不直接决定动作Success。 |
| BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.Provider.cs | True | 生产 | 纠偏 7.1—7.4 | 计算G0目标、保存中间结果、转轴及追加实时量，返回运动目标。 |
| BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.cs | True | 生产 | TU 6.4、纠偏 7.4 | 固晶动作的进入、完成写回；贴装位置另由Provider计算。 |
| BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.MoveHelper.cs | True | 空跑辅助 | 纠偏 3.5、6.5 | PickActionDryRun的RefreshMap不作为真实取片结果 |
| BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs | True | 生产 | 纠偏 3.2、3.4 | 静态华夫盒PR及人工OK/Ignore/Abort；失败不可当作正常取料许可。 |
| BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs | True | 生产 | 纠偏 3.3、3.4 | 先取片漂移，按载具识别并计算取片XYZT，保存供料角。 |
| BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.Provider.cs | True | 生产供料协作 | 纠偏 3.5、6.4 | SendSignalToWaferTable负责取后更新与后续要料，不等同于本次纠偏几何 |
| BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.cs | True | 生产 | 纠偏 6、8.4 | 放片、目标记录、拍照、重取和检测；Retry位置按具体标签。 |
| BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs | True | 生产 | 纠偏 5、8.4 | 按快速/普通及单/双点计算焊点偏移，后续二维码和温漂仍可能失败。 |
| BondSystem/Models/System2Domain.cs | True | 公共领域 | 纠偏 4、TU 3.4 | 按配置采点、保存结果并更新本层；bool由不同包装分别处理。 |
| BondSystem/Tasks/BondTask.cs | True | 生产调度 | TU 6.4、纠偏 7.3 | 注入工序、按条件重建TU；产品结束触发自动补偿及发送。 |
| CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs | True | 标定输入 | 纠偏 1.2 | 调用标定补偿，操作流程不展开为生产纠偏。 |
| DispenseSystem/Controls/Setting/EpoxyApplication/UcEpoxyApplication.cs | True | 点胶示教 | TU 6.6 | 辅助测试可按工位创建TU，不当作正常交接。 |
| DispenseSystem/Models/DispenseAction/DispenseBPAction/S1DispenseCorrectionActionNode.cs | True | 生产定位动作 | 纠偏 4.2 | 八入口之一；IsDoWork与DoWork独立核对，领域bool不直接决定动作Success。 |
| DispenseSystem/Models/DispenseAction/DispenseUpAction/S1CarrierVisionActionNode.cs | True | 生产定位动作 | 纠偏 4.2 | 八入口之一；IsDoWork与DoWork独立核对，领域bool不直接决定动作Success。 |
| DispenseSystem/Models/DispenseAction/DispenseUpAction/S1ModuleVisionActionNode.cs | True | 生产定位动作 | 纠偏 4.2 | 八入口之一；IsDoWork与DoWork独立核对，领域bool不直接决定动作Success。 |
| DispenseSystem/Models/DispenseAction/DispenseUpAction/S1SubstrateVisionActionNode.cs | True | 生产定位动作 | 纠偏 4.2 | 八入口之一；IsDoWork与DoWork独立核对，领域bool不直接决定动作Success。 |
| DispenseSystem/Models/System1Domain.cs | True | 公共领域 | 纠偏 4、TU 3.4 | S1坐标与异常处理有本侧分支，不能直接套用S2。 |
| DispenseSystem/Services/System2ActionNodesService.cs | False | 旧代码 | 配套资料 | 不在当前工程显式Compile项中，不作为现行生产行为依据。 |
| DispenseSystem/Tasks/DispenseWorkTask.cs | True | 生产调度 | TU 6.2、6.3 | IsProduct条件创建、执行并放行，Finish只复位消息。 |
| Experiment/Test/FrmMachineFunctionTest.cs | True | 实验按钮 | 纠偏 1.2 | BtnCaliPickOffset_Click为实验/标定辅助，不据此扩展生产纠偏类型 |
| Experiment/TestFunction/FrmTest.cs | True | 实验入口 | 配套资料 | 实验界面单独归属，不以测试入口推断生产路径。 |
| Infrastructure/Controls/Feature/EditProgram/UcEditProductProgram/UcEditProductProgramming.Assistance.cs | True | 示教配置 | 纠偏 8.5 | TU空检查及示教/调整对话框，配置作为运行输入。 |
| Main/Controls/UcShortcutMenu.cs | True | 手动搜索入口 | TU 6.7 | 两个搜索按钮调用MapBelt(false)，不满足自动免反搜条件 |
| Main/Controls/Ucmain/MainControls/UcMainSystem.ShortcutKeys.cs | True | 快捷辅助 | TU 6.6；纠偏 8.5 | 可按选择重建及调用层级定位，需区分扫描与生产动作条件。 |
| Main/Controls/Ucmain/MainControls/UcMainSystem.cs | True | 界面入口 | TU 8.3 | 按UseNewMappingUi选择两种Mapping界面，两者均有配置入口。 |
| Main/Machine/Process/S2ActionNodeController.cs | True | 生产编排 | TU 7.3；纠偏 4.2 | Init中SortRelativeBond重排定位到对应Pick前 |
| SupportFeature/Compensate/DefectCompensate/DefectCompensate.cs | True | 运行补偿 | 纠偏 7.3 | 样本筛选、自动补偿配置写回及单点补偿分别生效。 |
| SupportFeature/Compensate/MotionAreaCompensate/BondCompensate.cs | True | 标定输入 | 纠偏 1.2 | 本次调用清单中的GetBondCompensate用于全局标定界面，不与生产TU网格补偿混同。 |
| SupportFeature/Compensate/MotionAreaCompensate/RealTimeCorrection.cs | True | 运行补偿 | 纠偏 7.2 | 实际参数顺序保留，单点插值异常与最终超限置零不同。 |
| SupportFeature/Compensate/MotionAreaCompensate/TransportUnitCompensate.cs | True | 运行补偿 | 纠偏 7.3 | 生产使用的TU网格双线性补偿，在G0目标处相减。 |
| SupportFeature/Compensate/TemperatureCompensate/TpMarkCompensate.cs | True | 运行补偿 | 纠偏 3.4、5.4 | 取片与上视分别保存与取用漂移；符号和超限出口不同。 |
| TransportSystem/Controllers/BondSubSectionController.cs | True | 物料搜索 | TU 6.6 | 检测、缓存与人工选择决定保留/Refresh/新建/清空，输送配置分支不同。 |
| TransportSystem/Controllers/DispenseSubSectionController.cs | True | 物料搜索 | TU 6.6 | S1独立物料检测与补建，不把S2条件推广为共同实现。 |
| TransportSystem/Controllers/TransportController.cs | True | 生产与手动交接 | TU 6.3、8.2 | 按区段条件移送，引用先交后Refresh，Ignore/Abort/Retry分别影响路径。 |
| TransportSystem/Controllers/UnloadingSubSectionController.cs | True | 物料搜索 | TU 6.6 | 人工有料/TU空分支没有补建；无料确认可清引用。 |
| TransportSystem/Controllers/WaitingUnloadSubSectionController.cs | True | 物料搜索 | TU 6.6 | 人工有料/TU空分支没有补建；无料确认可清引用。 |
| TransportSystem/Controls/Manual/UcTransportSystemManual.cs | True | 手动搜索入口 | TU 6.7 | 手动页两个按钮调用各侧MapBelt(false)，对象变化由控制器分支决定 |
| TransportSystem/Models/Programs/BaseSubSectionProgram.cs | True | 区段与示教 | TU 6.6、8.4 | TU和运行状态不随普通配置序列化；示教更新可替换树。 |
| TransportSystem/Models/TransportDomain.cs | True | 生产启动 | TU 6.2、6.5 | StartTask中的全区段Refresh只刷新已有TU，后续物料搜索另行处理 |
| TransportSystem/Models/TransportProgram.cs | True | 生产刷新入口 | TU 6.2、7.1 | RefreshTransportUnit遍历各区段已有对象，与物料搜索和新建分离 |
| TransportSystem/Tasks/TransportTask.cs | True | 生产与空跑 | TU 6.3、6.6 | 成功返回才发来料信号；DryCycle使用分别创建的工位对象。 |
| TransportUnitSystem/Controls/Assistant/TUAssistantHelper.cs | True | 示教辅助 | TU 6.6；纠偏 8.5 | 必要时新建/刷新TU，定位可直接调用公共领域能力。 |
| TransportUnitSystem/Controls/Mapping/FrmTransportUnitMapping.cs | True | 手动导入 | TU 8.5 | 载入返回的新TU替换目标区段；不恢复旧对象身份。 |
| TransportUnitSystem/Controls/Mapping/FrmTuMapping.cs | True | 手动界面 | TU 8.3 | 旧样式仍由配置选择可达；不直接标为不可达旧代码。 |
| TransportUnitSystem/Controls/Mapping/FrmTuMappingNew.cs | True | 手动界面 | TU 8.3 | UseNewMappingUi配置可选择该界面；编入工程且有启用路径。 |
| TransportUnitSystem/Controls/TransportUnitEdit/UcObjectFunctionEdit.cs | True | 示教辅助 | 纠偏 8.5 | 示教定位可绕过生产IsDoWork，明确byMapping条件。 |
| TransportUnitSystem/Service/TuService.cs | True | 公共计算与导入 | TU 4、8.5；纠偏 4 | 按当前配方重建Mapping；产品选点与更新调用另按领域链使用。 |
| WaferSubSystem/Controllers/WaferSubController.cs | True | 翻转取片辅助 | 纠偏 3.5 | FlipFromWaferTable调用RefreshMap(true)，输入载具与实际取片阶段由辅助入口负责 |
| WaferSubSystem/Models/Entities/SearchChip/Block.SearchDieBox.cs | True | 供料生产 | 纠偏 3.2 | 槽位供料；静态华夫盒标准单点先提供拍照目标。 |
| WaferSubSystem/Models/Entities/SearchChip/Block.SearchMapping.cs | True | 供料生产 | 纠偏 3.2 | Map候选与本次识别有效性分别检查。 |
| WaferSubSystem/Models/Entities/SearchChip/Block.SearchNine.cs | True | 供料生产 | 纠偏 3.2 | Nine复用候选存在标记；MoveDieToPickCenter仍再次CalculateDiesPosition。取片角先保存，后次PR不重写角且void失败不直接使本次搜索返回false。 |
| WaferSubSystem/Models/Entities/SearchChip/Block.SearchSingle.cs | True | 供料生产 | 纠偏 3.2 | 单/双特征识别形成候选、角度和中心，外层决定跳片。 |
| WaferSubSystem/Models/Entities/SearchChip/Block.cs | True | 供料生产 | 纠偏 3.1—3.3 | 四模式调度、多次阈值与取料中心更新，XY移动受运行条件控制。 |
| WaferSubSystem/Tasks/FlipTask.cs | True | 生产翻转协作 | 纠偏 3.5 | 翻转达到避让角后更新Map并请求后续芯片，属于供料结果交接 |
| WaferSubSystem/Tasks/WaferSubSystemTask.cs | True | 生产供料任务 | 纠偏 3.1、3.5 | NextDie成功后复位要料并发允许取料；失败走换片/报警出口 |
