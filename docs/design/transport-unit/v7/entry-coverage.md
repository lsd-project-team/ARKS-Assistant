# 限定目录入口核查与归属

本轮源码解析限定在trunk/AKRS.ZX2200。发现清单与关键方法核查分别记录，文件数和搜索命中不代表全项目通读。

| 文件 | 归属 | 文档位置 | 核查结论 |
|---|---|---|---|
| System2Controller.Assistant.cs | 手动辅助与公共计算 | 纠偏 3.3、8.5 | 手动贴片定位后只支持独立上视；CalculatePickPos也是生产使用的公共取片计算。 |
| FrmMoveToBondingPosition.cs | 手动辅助 | TU 6.6 | 界面创建自身使用的TU，不是生产区段引用交接。 |
| FrmLearnIPT.cs | 示教输入 | 纠偏 2.1、6.1 | IPTVisionPos命中是设备参数写入，不是运行焊点Info或生产纠偏调用。 |
| UcBondPositionEdit.cs | 示教入口 | TU 6.6 | 命中只是当前TU空检查，不增加独立生产流程。 |
| BondPositionVisionActionNode.cs | 生产定位动作 | 纠偏 4.2 | 八入口之一；IsDoWork与DoWork独立核对，领域bool不直接决定动作Success。 |
| S2CarrierVisionActionNode.cs | 生产定位动作 | 纠偏 4.2 | 八入口之一；IsDoWork与DoWork独立核对，领域bool不直接决定动作Success。 |
| S2ModuleVisionActionNode.cs | 生产定位动作 | 纠偏 4.2 | 八入口之一；IsDoWork与DoWork独立核对，领域bool不直接决定动作Success。 |
| S2SubstrateVisionActionNode.cs | 生产定位动作 | 纠偏 4.2 | 八入口之一；IsDoWork与DoWork独立核对，领域bool不直接决定动作Success。 |
| BondActionNode.cs | 生产 | TU 6.4、纠偏 7.4 | 固晶动作的进入、完成写回；贴装位置另由Provider计算。 |
| BondActionNode.Provider.cs | 生产 | 纠偏 7.1—7.4 | 计算G0目标、保存中间结果、转轴及追加实时量，返回运动目标。 |
| PickActionNode.cs | 生产 | 纠偏 3.3、3.4 | 先取片漂移，按载具识别并计算取片XYZT，保存供料角。 |
| PickActionNode.Provider.cs | 生产 | 纠偏 3.2、3.4 | 静态华夫盒PR及人工OK/Ignore/Abort；失败不可当作正常取料许可。 |
| SubstrateCameraCorrectionActionNode.cs | 生产 | 纠偏 6、8.4 | 放片、目标记录、拍照、重取和检测；Retry位置按具体标签。 |
| UpLookCorrectionActionNode.cs | 生产 | 纠偏 5、8.4 | 按快速/普通及单/双点计算焊点偏移，后续二维码和温漂仍可能失败。 |
| System2Domain.cs | 公共领域 | 纠偏 4、TU 3.4 | 按配置采点、保存结果并更新本层；bool由不同包装分别处理。 |
| BondTask.cs | 生产调度 | TU 6.4、纠偏 7.3 | 注入工序、按条件重建TU；产品结束触发自动补偿及发送。 |
| FrmGlobalCalibration.cs | 标定输入 | 纠偏 1.2 | 调用标定补偿，操作流程不展开为生产纠偏。 |
| UcEpoxyApplication.cs | 点胶示教 | TU 6.6 | 辅助测试可按工位创建TU，不当作正常交接。 |
| S1DispenseCorrectionActionNode.cs | 生产定位动作 | 纠偏 4.2 | 八入口之一；IsDoWork与DoWork独立核对，领域bool不直接决定动作Success。 |
| S1CarrierVisionActionNode.cs | 生产定位动作 | 纠偏 4.2 | 八入口之一；IsDoWork与DoWork独立核对，领域bool不直接决定动作Success。 |
| S1ModuleVisionActionNode.cs | 生产定位动作 | 纠偏 4.2 | 八入口之一；IsDoWork与DoWork独立核对，领域bool不直接决定动作Success。 |
| S1SubstrateVisionActionNode.cs | 生产定位动作 | 纠偏 4.2 | 八入口之一；IsDoWork与DoWork独立核对，领域bool不直接决定动作Success。 |
| System1Domain.cs | 公共领域 | 纠偏 4、TU 3.4 | S1坐标与异常处理有本侧分支，不能直接套用S2。 |
| System2ActionNodesService.cs | 旧代码 | 配套资料 | 不在当前工程显式Compile项中，不作为现行生产行为依据。 |
| DispenseWorkTask.cs | 生产调度 | TU 6.2、6.3 | IsProduct条件创建、执行并放行，Finish只复位消息。 |
| FrmTest.cs | 实验入口 | 配套资料 | 实验界面单独归属，不以测试入口推断生产路径。 |
| UcEditProductProgramming.Assistance.cs | 示教配置 | 纠偏 8.5 | TU空检查及示教/调整对话框，配置作为运行输入。 |
| UcMainSystem.cs | 界面入口 | TU 8.3 | 按UseNewMappingUi选择两种Mapping界面，两者均有配置入口。 |
| UcMainSystem.ShortcutKeys.cs | 快捷辅助 | TU 6.6；纠偏 8.5 | 可按选择重建及调用层级定位，需区分扫描与生产动作条件。 |
| DefectCompensate.cs | 运行补偿 | 纠偏 7.3 | 样本筛选、自动补偿配置写回及单点补偿分别生效。 |
| BondCompensate.cs | 标定输入 | 纠偏 1.2 | 本次调用清单中的GetBondCompensate用于全局标定界面，不与生产TU网格补偿混同。 |
| RealTimeCorrection.cs | 运行补偿 | 纠偏 7.2 | 实际参数顺序保留，单点插值异常与最终超限置零不同。 |
| TransportUnitCompensate.cs | 运行补偿 | 纠偏 7.3 | 生产使用的TU网格双线性补偿，在G0目标处相减。 |
| TpMarkCompensate.cs | 运行补偿 | 纠偏 3.4、5.4 | 取片与上视分别保存与取用漂移；符号和超限出口不同。 |
| BondSubSectionController.cs | 物料搜索 | TU 6.6 | 检测、缓存与人工选择决定保留/Refresh/新建/清空，输送配置分支不同。 |
| DispenseSubSectionController.cs | 物料搜索 | TU 6.6 | S1独立物料检测与补建，不把S2条件推广为共同实现。 |
| TransportController.cs | 生产与手动交接 | TU 6.3、8.2 | 按区段条件移送，引用先交后Refresh，Ignore/Abort/Retry分别影响路径。 |
| UnloadingSubSectionController.cs | 物料搜索 | TU 6.6 | 人工有料/TU空分支没有补建；无料确认可清引用。 |
| WaitingUnloadSubSectionController.cs | 物料搜索 | TU 6.6 | 人工有料/TU空分支没有补建；无料确认可清引用。 |
| BaseSubSectionProgram.cs | 区段与示教 | TU 6.6、8.4 | TU和运行状态不随普通配置序列化；示教更新可替换树。 |
| TransportTask.cs | 生产与空跑 | TU 6.3、6.6 | 成功返回才发来料信号；DryCycle使用分别创建的工位对象。 |
| TUAssistantHelper.cs | 示教辅助 | TU 6.6；纠偏 8.5 | 必要时新建/刷新TU，定位可直接调用公共领域能力。 |
| FrmTransportUnitMapping.cs | 手动导入 | TU 8.5 | 载入返回的新TU替换目标区段；不恢复旧对象身份。 |
| FrmTuMapping.cs | 手动界面 | TU 8.3 | 旧样式仍由配置选择可达；不直接标为不可达旧代码。 |
| FrmTuMappingNew.cs | 手动界面 | TU 8.3 | UseNewMappingUi配置可选择该界面；编入工程且有启用路径。 |
| UcObjectFunctionEdit.cs | 示教辅助 | 纠偏 8.5 | 示教定位可绕过生产IsDoWork，明确byMapping条件。 |
| TuService.cs | 公共计算与导入 | TU 4、8.5；纠偏 4 | 按当前配方重建Mapping；产品选点与更新调用另按领域链使用。 |
| Block.cs | 供料生产 | 纠偏 3.1—3.3 | 四模式调度、多次阈值与取料中心更新，XY移动受运行条件控制。 |
| Block.SearchDieBox.cs | 供料生产 | 纠偏 3.2 | 槽位供料；静态华夫盒标准单点先提供拍照目标。 |
| Block.SearchMapping.cs | 供料生产 | 纠偏 3.2 | Map候选与本次识别有效性分别检查。 |
| Block.SearchNine.cs | 供料生产 | 纠偏 3.2 | 九宫格候选与邻片几何更新，不保证每次完整重拍。 |
| Block.SearchSingle.cs | 供料生产 | 纠偏 3.2 | 单/双特征识别形成候选、角度和中心，外层决定跳片。 |
