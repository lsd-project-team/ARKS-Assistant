"""Maintain explicit reviewed claims separately from broad discovery candidates."""
from pathlib import Path
import json,hashlib,collections
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
SCOPE=(ROOT/'trunk/AKRS.ZX2200').resolve(); OUT=ROOT/'output/correction-v3.2'
OLD=ROOT/'docs/design/correction-process/v3.1'
def dump(name,obj):(OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def evidence(rel,start,end,token):
    p=(SCOPE/rel).resolve();assert p.is_relative_to(SCOPE)
    raw=p.read_bytes();ls=raw.decode('utf-8-sig').splitlines();assert 1<=start<=end<=len(ls)
    return dict(path='trunk/AKRS.ZX2200/'+rel,start=start,end=end,method_or_token=token,
                sha256=hashlib.sha256(raw).hexdigest(),start_text=ls[start-1].strip(),end_text=ls[end-1].strip())
claims=json.loads((OLD/'claim-map.json').read_text(encoding='utf-8'))['claims']
for c in claims:
    c['review_status']='沿用已核对正文；本轮重新核对原始文件哈希和范围锚点'
    for e in c['evidence']:
        p=(ROOT/e['path']).resolve();assert p.is_relative_to(SCOPE)
        assert hashlib.sha256(p.read_bytes()).hexdigest()==e['sha256']
        ls=p.read_text(encoding='utf-8-sig').splitlines()
        assert ls[e['start']-1].strip()==e['start_text'] and ls[e['end']-1].strip()==e['end_text']

MA='Main/Machine/MachineSupport/Machine.Operate.cs'
ET='Infrastructure/Utils/ETelDrive.cs'; GG='Infrastructure/Utils/GuGaoDrive.cs'
TE='TransportUnitSystem/Controls/Assistant/FrmAdjustDegree.cs'
AS='Infrastructure/Controls/Feature/EditProgram/UcEditProductProgram/UcEditProductProgramming.Assistance.cs'
TH='TransportUnitSystem/Controls/Assistant/TUAssistantHelper.cs'
AU='SupportFeature/Compensate/MotionAreaCompensate/FrmAutoCompensate.cs'
CA='SupportFeature/Compensate/MotionAreaCompensate/CompensateCalculator.cs'
DS='SupportFeature/Compensate/MotionAreaCompensate/CompensateDataService.cs'
IM='SupportFeature/Compensate/MotionAreaCompensate/FrmBondCompensate.cs'
TU='SupportFeature/Compensate/MotionAreaCompensate/TransportUnitCompensate.cs'
BP='BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.Provider.cs'
fresh=[
('9.1','轴二维表与TU应用补偿的保存对象、生效层级及开关独立。',[(MA,589,635,'CloseCompensate / OpenCompensate'),(TU,66,146,'GetBondCompensate'),(BP,498,630,'CalculateBondPos')]),
('9.2','整机回零先关闭，OneKeyHome成功后才按开关开启；无统一失败恢复。',[(MA,504,635,'AllAxisGoHome')]),
('9.2、表9-2','固高开启false只弹窗，不传播为回零false；历史AllAxisReset未在入口统一清除。',[(MA,504,635,'AllAxisGoHome / OpenCompensate')]),
('9.3','ETEL开启包装实际读取全局TextName；下载DsaException被内层吞掉后仍可继续激活。',[(ET,27,47,'DownloadMapping'),(ET,292,330,'Open2DCompensate / Close2DCompensate')]),
('9.3、式9-1、式9-2','固高间距先取整再乘10000，起点先乘再取整；AutoScale行列各扩20。',[(GG,839,1047,'Close2DCompensate / Open2DCompensate')]),
('9.4','标定UI的启停、回零次序及固高bool处理与整机路径不同。', [('CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs',415,503,'CloseStage / OpenStage')]),
('10.1','在线采点转换到传入对象上级参考系；S1/S2相机参考转换分别处理。',[(TH,463,502,'GetPosBySystem'),(TE,91,178,'InitControl')]),
('10.2','判据是X跨度<1及角度绝对值>5；用Atan斜率，Degree写弧度。',[(TE,133,173,'doneAction')]),
('10.2、10.3','离线提前OK未算RealDegree；调用方仍可能复制默认0；取消无统一回滚。',[(TE,133,173,'doneAction'),(TE,239,242,'BtCancel_Click'),(AS,683,728,'焊点角示教')]),
('10.3、表10-2','TU完整与分段均先拉角度；分段无AssistantAllRotation条件，随后编辑左右PR。',[(AS,63,153,'AssistanceTuAdjust')]),
('10.3、表10-2','基板传TU、基岛传基板、焊点传基岛；窗口与调用方写回目标不同。',[(AS,159,213,'AssistanceSubAdjust'),(AS,219,274,'AssistanceModuleAdjust'),(AS,683,728,'焊点示教')]),
('11.1','查询名固定贴片精度，按TU索引、基板索引和日期分组，组内按ModuleIndex排序。',[(DS,24,68,'GetRoundsAfterTime')]),
('11.1','焊后构造链把TU名称写Id，未赋TuIndex；采集按TuIndex而非Id分组。',[(DS,39,63,'GetRoundsAfterTime'),('SupportFeature/Statistics/DefectStatisticsEntity.cs',13,67,'统计字段'),('SupportFeature/Statistics/DefectStatisticsEntity.cs',164,186,'构造函数'),('BondSystem/Models/ActionNodes/BPActionNode/AfterBondCheckActionNode.cs',556,587,'LogDefect'),('SupportFeature/Statistics/StatisticsDomain.cs',407,422,'AddDefectResult / SaveDataToDb'),('SupportFeature/Statistics/StatisticsService.cs',110,124,'SaveEntityToDb')]),
('11.1','新组先记去重键后判点数，不重判相同键的补齐数据；未校验点号唯一性。',[(AU,173,232,'PollTimer_Tick')]),
('11.1','有效轮达标优先判断；未达标且总查询组数>=2K时停机。',[(AU,173,232,'PollTimer_Tick')]),
('11.1','关闭采集窗只停Timer，显式停止和轮询异常同时Stop设备。',[(AU,57,69,'FormClosing'),(AU,128,141,'BtnStopCollect_Click'),(AU,225,231,'catch')]),
('11.2','X/Y偏移除1000，前K轮形成[位置,轮次]矩阵；逐位置一次Huber，残差再Huber。',[(AU,237,289,'FinishCollectAndCalculate'),(CA,26,95,'Calculate / HuberEstimate')]),
('11.2','残差估计按位置，不是跨位置公共漂移；平移等变推导及浮点误差界限经独立计算复核。',[(CA,35,58,'逐位置估计与残差')]),
('11.2、图11-2','行优先还原，默认5列滑动中位数边界截断且不跨行。',[(CA,112,153,'SmoothMedianRowWise / WrapTo2D')]),
('11.3','自动窗发布只改XY矩阵，不初始化网格几何、不改生产开关；未启用保留旧表。',[(AU,91,123,'BtnStartCollect_Click'),(AU,146,161,'BtnEnable_Click'),(AU,237,289,'FinishCollectAndCalculate'),(TU,66,146,'GetBondCompensate')]),
('11.4','人工导入非空校验后先改行列元数据，再检查点数；读取首条位置和配置间距。',[(IM,48,99,'BtInput_Click')]),
('11.4、图11-3','人工导入按原始行数据做首末不变、邻3点/5点均值，与自动Huber后中位数不同。',[(IM,101,131,'BtInput_Click'),(CA,112,133,'SmoothMedianRowWise')]),
('11.4','人工清空只置内存null，无Save；手工编辑保存另行Save。',[(IM,138,142,'BtClear_Click'),(IM,190,202,'BtSave_Click')]),
('11.4','主界面通过泛型ShowForm<FrmBondCompensate>打开人工补偿界面。', [('Main/Controls/Ucmain/MainControls/UcMainSystem.cs',1929,1937,'BarBondCompensate_ItemClick')]),
('12.3','扩展区域插值用于标定扫描，IPT示教写设备位置，诊断路径与生产输出分别归属。', [('CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs',882,960,'ScanPointsWithCompensation'),('CalibSystem/GlobalCalibration/FrmGlobalCalibrationEx.cs',998,1015,'扫描移动'),('BondSystem/Controls/Manual/FrmLearnIPT.cs',90,156,'InitControl'),('BondSystem/Models/ActionNodes/BPActionNode/BondPositionVisionTest.cs',33,104,'DoWork / IsDoWork')]),
]
for i,(section,conclusion,refs) in enumerate(fresh,1):
    claims.append(dict(id=f'CN{i:02}',sections=section,conclusion=conclusion,evidence=[evidence(*r) for r in refs],
                       review_status='本轮按完整相关区段阅读并结合调用方核对'))
dump('claim-map.json',dict(scope='trunk/AKRS.ZX2200',date='2026-10-21',claims=claims))
ranges=collections.defaultdict(list)
for c in claims:
    for e in c['evidence']:ranges[e['path']].append(dict(start=e['start'],end=e['end'],claim=c['id'],token=e.get('method_or_token'),review_status=c['review_status']))
dump('source-analysis.json',dict(scope='trunk/AKRS.ZX2200',review_type='既有56文件重新验哈希及锚点，新增关键链路逐区段阅读；扫描索引不计为业务通读',reviewed_ranges=ranges))

discovery=json.loads((OUT/'scope-discovery.json').read_text(encoding='utf-8'))
old_entries=json.loads((OLD/'entry-coverage.json').read_text(encoding='utf-8'))['entries']
old_by={e['file']:e for e in old_entries}
legacy_sections=collections.defaultdict(set)
for c in claims:
    if not c['id'].startswith('CO'):continue
    for e in c['evidence']:legacy_sections[e['path'].split('trunk/AKRS.ZX2200/')[1]].add(c['sections'])
reviewed={p.split('trunk/AKRS.ZX2200/')[1] for p in ranges}
def disposition(c):
    rel=c['file'];name=Path(rel).name
    if rel in old_by:return '既有生产／手动入口归属已保留；本轮源文件哈希一致',old_by[rel].get('sections','第3至8章')
    if rel in legacy_sections:return '既有正文已核对的算法、输入或调用接口；哈希与结论锚点一致','；'.join(sorted(legacy_sections[rel]))
    if name=='FrmAutoCompensate.cs':return '辅助采集实现已纳入；工程编译存在，但未发现本目录内直接构造或泛型打开入口','11.1至11.3；入口证据边界外置'
    if name in ['FrmBondCompensate.cs','CompensateCalculator.cs','CompensateDataService.cs']:return '区域表生成或维护实现','第11章'
    if name in ['Machine.Operate.cs','ETelDrive.cs','GuGaoDrive.cs','GlobalCalibrationDomain.cs','FrmAssistant2DStage.cs']:return '设备轴二维补偿调用、数据或辅助关闭入口','第9章'
    if name=='FrmAdjustDegree.cs' or name=='UcEditProductProgramming.Assistance.cs':return '两点角度示教及其五处直接调用','第10章'
    if name=='UcMainSystem.cs':return '主界面回零、人工表维护、标定及诊断入口','第9章、第11章、12.3'
    if name=='FrmLearnIPT.cs':return '左右IPT设备位置示教输入','12.3'
    if 'BondForce/' in rel or name in ['System2Controller.cs','UcBondModuelSetting.cs']:return '力控／测高标定输入，非额外XY视觉纠偏','12.3'
    if rel.startswith('Experiment/') or name in ['BondPositionVisionTest.cs','FrmCompensateTest.cs']:return '实验或诊断实现，分别记录；不据类名计为注册生产动作','12.3'
    if rel.startswith('CalibSystem/') or name=='BilinearCompensator.cs':return '标定数据、扫描验证或区域维护；独立于生产TU查表','9.4、12.3'
    if name in ['EtelCompensate.cs','GooGolCompensate.cs']:return '空辅助类；实际启停证据来自Machine与Infrastructure/Utils，未以空类推断整机功能缺失','第9章'
    if name=='CompensationPredictor.cs':return '模型类存在；标定界面初始化代码被注释，不作为有效生产AI纠偏','12.3归属；详细边界外置'
    if rel.startswith(('SupportFeature/HeatingSettings/','TransportSystem/Controllers/')):return '加热温控通道，不属于XY纠偏','12.3'
    if rel.startswith(('SupportFeature/Statistics/','Infrastructure/Service/')) or name=='TemperatureCompensationEntity.cs':return '统计查询、展示或存储支持；不新增纠偏算法','第11章、12.3'
    if name=='FrmSystem2Calibrate.cs':return '相机标定输入','12.3'
    if name=='PostBondProgram.cs':return '焊后补偿启用配置汇总','7.3'
    if name=='UcEpoxyApplication.cs':return 'S1/S2定位领域方法的示教调用，不新增算法','第4章、12.3'
    if name=='BondPosition.cs':return '硬补偿参数访问器，不新增视觉过程','第7章'
    if name=='FrmEjectionRealtimeState.cs':return '顶针诊断数据导出方法，非XY纠偏生产更新','12.3'
    raise AssertionError('Unassigned candidate: '+rel)
entries=[]
for c in discovery['candidates']:
    d,s=disposition(c)
    entries.append(dict(**c,entry_kind=d,document_sections=s,review_depth='相关方法语义区段已读／既有证据沿用' if c['file'] in reviewed else '入口、声明、接收对象或输出归属核对；未宣称全文通读'))
dump('entry-coverage.json',dict(scope='trunk/AKRS.ZX2200',discovery='C#当前语法树、编译项、调用/赋值/构造/泛型UI入口和方法声明，人工逐类归属',known_unassigned_entries=[],entries=entries,
     unresolved_runtime_entry=[dict(file='SupportFeature/Compensate/MotionAreaCompensate/FrmAutoCompensate.cs',status='辅助实现已描述；无法在本目录证明外部或反射入口，不作为生产自动调用事实')]))
lines=['# 本轮源码核查发现','','业务源码保持只读，检索、读取、调用追踪均限制在trunk/AKRS.ZX2200。','',
       f'当前索引{len(discovery["scanned_files"])}个C#文件；{len(entries)}个候选文件逐项归属。索引不等于通读；实际已读区段和结论见source-analysis.json、claim-map.json。','',
       '旧版56个依据文件哈希及既有结论锚点全部一致；本轮保留原生产正文，重点新读设备轴、角度示教和区域表生成维护。', '',
       '## 新增与纠正','']
for c in claims:
    if c['id'].startswith('CN'):lines.append(f'- {c["id"]}（{c["sections"]}）：{c["conclusion"]}')
lines+=['','## 入口证据边界','','FrmBondCompensate可由主界面ShowForm<T>打开。FrmAutoCompensate编译项、Designer事件与内部实现存在；全目录语法调用、构造及泛型搜索未发现其他代码直接打开它。不能据此断言不可达，也不能声称已接入每轮生产。',
        'CompensationPredictor在标定界面存在调用分支，但初始化代码被注释，未作为生产AI补偿写入。GooGolCompensate／EtelCompensate空类不代表实际驱动补偿缺失，真正调用包装位于Infrastructure/Utils。','',
        '## 验证边界','','本轮使用原生Word导出并恢复原始图片流。独立纯CompensateCalculator C#类可编译复算；未加载设备程序集、运行设备或执行整套C#业务。其余数值和条件按独立模型检查。驱动SDK及外部坐标库内部不展开。','']
(OUT/'source-findings.md').write_text('\n'.join(lines),encoding='utf-8')
lines=['# 相关候选入口逐项归属','','|文件|归属|正文位置|','|---|---|---|']
for e in entries:lines.append(f'|{e["file"]}|{e["entry_kind"]}|{e["document_sections"]}|')
(OUT/'entry-coverage.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(f'{len(claims)} claims, {len(fresh)} fresh findings, {len(entries)} candidate dispositions')
