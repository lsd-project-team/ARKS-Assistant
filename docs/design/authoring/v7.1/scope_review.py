"""Scope-limited source inventory; text discovery is kept separate from reviewed claims."""
from pathlib import Path
import hashlib,json,re,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[4]
SCOPE=ROOT/'trunk/AKRS.ZX2200'
BASE=Path(__file__).resolve().parents[4]/'output/design-publication-v7.1'
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def source(p):
 p=(SCOPE/p).resolve();assert p.is_relative_to(SCOPE.resolve());return p

GROUPS_TU=[
 (1,'运行对象与状态','对象层级、查询、刷新、镜像标记及参与范围',['TransportUnitSystem/Module/Matter/'+n+'.cs' for n in ['TransportUnit','BaseMatter','Substrate','Module','BondPosition']]+['TransportUnitSystem/Model/TuEnum.cs']),
 (2,'配置与展开','常规、异形节点、阵列和状态配置',['TransportUnitSystem/'+p for p in ['ProductConfiguration.cs','Service/TuService.cs','Module/Config/TransportUnitConfig.cs','Module/Config/OppositeSex.cs','Module/Config/OppositeSexConfiguration.cs','Module/Config/ArrayConfig.cs','Module/Config/SubstrateConfig.cs','Module/Config/ModuleConfig.cs','Module/Config/BaseConfig.cs','Module/Config/OtherConfig.cs','Module/Config/SingleBondPositionConfig.cs']]),
 (3,'动作控制与步骤','消息解析、步骤注入、相对固晶重排',['Main/Machine/Process/'+p+'.cs' for p in ['S1ActionNodeController','S2ActionNodeController','SingleProcessStep']]+['Infrastructure/Models/CommonModels/ActionNodeMessage.cs']),
 (4,'运行信息','Info、定位结果、身份与完成记录',['TransportUnitSystem/Module/Information/'+p+'.cs' for p in ['BaseInformation','TransportUnitInfo','SubstrateInfo','ModuleInfo','BondPositionInfo','LocateResultInfo']]+['TransportUnitSystem/Model/VisionResult.cs']),
 (5,'坐标调用接口','本目录中的坐标建立、转换调用和参数归属',['TransportUnitSystem/Service/TuService.cs','BondSystem/Controllers/BondModuleController.cs','DispenseSystem/Controllers/DispenseController.cs']),
 (6,'点胶生产入口','S1创建、执行、放行和写回',['DispenseSystem/Tasks/DispenseWorkTask.cs','DispenseSystem/Models/DispenseAction/DispenseBPAction/S1DispenseActionNode.cs']),
 (7,'固晶生产入口','S2创建、动作处理和产品发送',['BondSystem/Tasks/BondTask.cs','BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.cs']),
 (8,'输送与搜索','交接、物料搜索、人工补料和完成信号',['TransportSystem/'+p+'.cs' for p in ['Models/TransportProgram','Models/Programs/BaseSubSectionProgram','Controllers/TransportController','Controllers/DispenseSubSectionController','Controllers/BondSubSectionController','Controllers/WaitingUnloadSubSectionController','Controllers/UnloadingSubSectionController','Models/TransportDomain','Tasks/TransportTask']]),
 (9,'示教与界面入口','示教重建、扫描、Mapping显示和状态编辑',['TransportUnitSystem/Controls/Assistant/TUAssistantHelper.cs','Main/Controls/Ucmain/MainControls/UcMainSystem.ShortcutKeys.cs','Main/Controls/Ucmain/MainControls/UcMainSystem.cs','DispenseSystem/Controls/Setting/EpoxyApplication/UcEpoxyApplication.cs','TransportUnitSystem/Controls/Mapping/UcTransportShow.cs','TransportUnitSystem/Controls/Mapping/FrmTuMapping.cs','TransportUnitSystem/Controls/Mapping/FrmTuMappingNew.cs','TransportUnitSystem/Controls/Mapping/FrmTransportUnitMapping.cs','TransportUnitSystem/Controls/Mapping/FrmAddTuInfo.cs','BondSystem/Controls/Assistant/FrmTeachBondingPosition.cs','BondSystem/Controls/Assistant/FrmRelativeBondTeach.cs']),
 (10,'存储边界','区段忽略序列化及独立TU存储接口',['TransportUnitSystem/Model/TransportUnitStorage.cs','TransportSystem/Models/Programs/BaseSubSectionProgram.cs']),
 (11,'定位与测高写回','领域采集、坐标和结果的写入',['DispenseSystem/Models/System1Domain.cs','BondSystem/Models/System2Domain.cs','DispenseSystem/Models/DispenseAction/DispenseBPAction/S1DispenseActionNode.cs','BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.cs','BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs']),
 (12,'启动调度','准备、任务启动和物料搜索',['Main/Machine/MachineSupport/Machine.Operate.cs','TransportSystem/Models/TransportDomain.cs']),
 (13,'身份记录','读码、离线和跳过条件',['DispenseSystem/Models/System1Domain.cs','BondSystem/Models/System2Domain.cs','DispenseSystem/Models/DispenseAction/IdentityActionNode/S1SubstrateIdentityActionNode.cs','BondSystem/Models/ActionNodes/IdentityActionNode/S2SubstrateIdentityActionNode.cs']),
 (14,'Mapping导入','按当前配方创建树、恢复部分记录并替换引用',['TransportUnitSystem/Service/TuService.cs','TransportUnitSystem/Controls/Mapping/FrmTransportUnitMapping.cs'])]
GROUPS_COR=[
 (1,'纠偏对象与配置','产品定位与芯片定位的独立配置',['TransportUnitSystem/Module/Config/LocateConfig.cs','Infrastructure/Models/CommonModels/AdjustConfig.cs','WaferSubSystem/Models/Repositories/Carrier/BaseCarrierConfig.cs','TransportUnitSystem/Module/Information/BondPositionInfo.cs']),
 (2,'产品定位计算','采集、分轴选点、角度和坐标更新调用',['DispenseSystem/Models/System1Domain.cs','BondSystem/Models/System2Domain.cs','TransportUnitSystem/Service/TuService.cs','TransportUnitSystem/Model/VisionResult.cs','Infrastructure/Utils/MathHelper.cs']),
 (3,'坐标及标定接口','相机结果转换和吸嘴校准角度',['BondSystem/Controllers/System2Controller.Vision.cs','BondSystem/Controllers/BondHeadController.cs','BondSystem/Controllers/BondModuleController.cs','BondSystem/Models/Repositories/Nozzle/Nozzle.cs','DispenseSystem/Controllers/DispenseController.cs','Infrastructure/Utils/MathHelper.cs']),
 (4,'生产上视纠偏','快速、普通、镜像和温漂调用',['BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs','BondSystem/Models/Parameter/System2RunTimeProvider.cs','SupportFeature/Compensate/TemperatureCompensate/TpMarkCompensate.cs']),
 (5,'生产中转台纠偏','放片、拍照、重取及重试',['BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode'+p+'.cs' for p in ['', '.Provider','.MoveHelper']]),
 (6,'贴装目标','补偿次序、位置记录与运动轴目标',['BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.Provider.cs','BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.cs','SupportFeature/Compensate/MotionAreaCompensate/RealTimeCorrection.cs']),
 (7,'报警与人工确认','PR重跑和距离检查',['Main/Controls/Ucmain/MainControls/UcmainSystem.Action.cs','Infrastructure/Controls/Currency/FrmVisionAlarm.cs','Infrastructure/Service/VisionService.cs']),
 (8,'定位动作与编排','八个层级定位入口及相对固晶时机',['DispenseSystem/Models/DispenseAction/DispenseUpAction/'+n+'.cs' for n in ['S1CarrierVisionActionNode','S1SubstrateVisionActionNode','S1ModuleVisionActionNode']]+['DispenseSystem/Models/DispenseAction/DispenseBPAction/S1DispenseCorrectionActionNode.cs']+['BondSystem/Models/ActionNodes/AdjustActionNode/'+n+'.cs' for n in ['S2CarrierVisionActionNode','S2SubstrateVisionActionNode','S2ModuleVisionActionNode','BondPositionVisionActionNode']]+['DispenseSystem/Models/DispenseAction/DispenseActionNodes.cs','BondSystem/Models/ActionNodes/BondActionNodeRepository.cs','Main/Machine/Process/S2ActionNodeController.cs','BondSystem/Tasks/BondTask.cs']),
 (9,'供料端定位及取片','搜晶分支、多次校正、静态华夫盒和取片位',['WaferSubSystem/Models/Entities/SearchChip/Block'+p+'.cs' for p in ['', '.SearchSingle','.SearchNine','.SearchMapping','.SearchDieBox']]+['WaferSubSystem/Tasks/WaferSubSystemTask.cs','BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs','BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.Provider.cs','BondSystem/Controllers/System2Controller.Assistant.cs']),
 (10,'手动辅助入口','贴片测试、示教定位与独立上视实现',['BondSystem/Controllers/System2Controller.Assistant.cs','BondSystem/Controls/Assistant/FrmComponentPlacement.cs','TransportUnitSystem/Controls/Assistant/TUAssistantHelper.cs','TransportUnitSystem/Controls/TransportUnitEdit/UcObjectFunctionEdit.cs','Main/Controls/Ucmain/MainControls/UcMainSystem.ShortcutKeys.cs']),
 (11,'中转台运动分支','绝对运动、插补运动与空跑',['BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.MoveHelper.cs','BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.cs']),
 (12,'相关运行补偿','取片温漂、焊后、单点、TU区域与实时补偿',['SupportFeature/Compensate/TemperatureCompensate/TpMarkCompensate.cs','SupportFeature/Compensate/DefectCompensate/DefectCompensate.cs','SupportFeature/Compensate/MotionAreaCompensate/TransportUnitCompensate.cs','SupportFeature/Compensate/MotionAreaCompensate/RealTimeCorrection.cs','BondSystem/Models/ActionNodes/BPActionNode/AfterBondCheckActionNode.cs','BondSystem/Tasks/BondTask.cs'])]

# Additional reviewed callers and state owners, within the same source root.
def extend_group(groups,number,paths):
 for n,title,purpose,ids in groups:
  if n==number:
   ids.extend(p for p in paths if p not in ids)
extend_group(GROUPS_TU,8,['TransportSystem/Models/Programs/DispenseSubSectionProgram.cs','TransportSystem/Controls/Manual/UcTransportSystemManual.cs'])
extend_group(GROUPS_TU,3,['DispenseSystem/Models/DispenseAction/OtherAction/InteractiveAction.cs'])
extend_group(GROUPS_TU,9,['Main/Controls/UcShortcutMenu.cs'])
extend_group(GROUPS_COR,9,['WaferSubSystem/Controllers/WaferSubController.cs','WaferSubSystem/Tasks/FlipTask.cs'])

def build_book(folder,groups,revision):
 p=BASE/folder;p.mkdir(parents=True,exist_ok=True);files=[]
 paths=list(dict.fromkeys(x for _,_,_,xs in groups for x in xs))
 for rel in paths:
  f=source(rel);lines=f.read_text(encoding='utf-8-sig').splitlines()
  anchors=[{'line':i,'symbol':t.strip()} for i,t in enumerate(lines,1) if re.search(r'^\s*(?:public|private|protected|internal).*(?:\(| class | enum )',t)]
  if not anchors:anchors=[{'line':1,'symbol':lines[0]}]
  files.append({'id':rel,'path':'trunk/AKRS.ZX2200/'+rel,'sha256':sha(f),'line_count':len(lines),'anchors':anchors,'anchor_method':'文本定位；不等同于全文件业务理解'})
 data={'date':'2026-10-21','revision':revision,'scope':'trunk/AKRS.ZX2200','external_dependencies':'只说明本目录内的接口调用及前提；不读取目录外实现','files':files,'reference_groups':[{'number':n,'title':t,'purpose':u,'source_ids':xs} for n,t,u,xs in groups]}
 dump(p/'source-baseline.json',data)
 return data

if __name__=='__main__':
 ns={'m':'http://schemas.microsoft.com/developer/msbuild/2003'}
 project=source('AKRS.ZX2200.csproj');tree=ET.parse(project)
 compiled={e.attrib['Include'].replace('\\','/') for e in tree.findall('.//m:Compile',ns)}
 pattern=re.compile(r'new\s+TransportUnit\s*\(|\.TransportUnit\s*=|(?:System1MatterVision|System2ObjectVision|System2MatterVision|CalculatePickPos|CalculateBondPos|UplookVisionAction|ToRequiredAccuracy|MoveDieToPickCenter|GetPostBondCompensation|GetBpSeparateOffset|GetCompensatePoint3D|GetBondCompensate|PickUpCompensationVision)\s*\(|Component(?:Angle)?OffSet\s*=|IPT(?:Vision|Pick)Pos\s*=')
 hits=[]
 for f in sorted(SCOPE.rglob('*.cs')):
  if f.name.endswith('.Designer.cs'):continue
  rel=f.relative_to(SCOPE).as_posix();lines=f.read_text(encoding='utf-8-sig',errors='replace').splitlines()
  matches=[{'line':i,'text':s.strip()} for i,s in enumerate(lines,1) if not s.lstrip().startswith('//') and pattern.search(s)]
  if not matches:continue
  if rel not in compiled:topic='未编入当前工程；不据此描述生产行为'
  elif rel.startswith('Experiment/'):topic='实验入口；与生产行为区分'
  elif rel.startswith('CalibSystem/'):topic='标定输入；本轮不展开标定操作'
  elif rel.startswith('TransportSystem/'):topic='TU区段、交接、物料搜索及人工补料'
  elif rel.startswith('TransportUnitSystem/'):topic='TU模型、配置、Mapping及示教定位'
  elif rel.startswith('WaferSubSystem/'):topic='供料定位、校正和取片结果'
  elif rel.startswith('SupportFeature/Compensate/'):topic='相关运行补偿'
  elif rel.startswith('DispenseSystem/'):topic='S1产品定位及产品动作'
  elif rel.startswith('BondSystem/'):topic='S2定位、芯片纠偏、取片或手动辅助'
  elif rel.startswith('Main/'):topic='动作编排、启动或界面入口'
  else:topic='配置与辅助入口；核查记录列明，不扩展为独立纠偏类型'
  hits.append({'file':rel,'compiled':rel in compiled,'topic':topic,'matches':matches})
 inventory={'scope':str(SCOPE),'project_sha256':sha(project),'method':'工程显式Compile项与文本调用入口交叉发现；人工核对关键链路，非Roslyn绑定或整机运行','compiled_cs_files':len(compiled),'files_with_matching_entries':len(hits),'files':hits}
 dump(BASE/'source-inventory.json',inventory)
 for folder,g,r in [('transport-unit',GROUPS_TU,'7.1'),('correction-process',GROUPS_COR,'3.1')]:
  d=build_book(folder,g,r)
  print(folder,len(d['files']),'scoped source files')
 print('Discovery inventory:',len(hits),'files; all have a topic or explicit boundary')
