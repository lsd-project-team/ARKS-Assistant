"""Scoped source evidence. A scan record is deliberately not a reading claim."""
from pathlib import Path
import json,hashlib,re,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[5];SCOPE=(ROOT/'trunk/AKRS.ZX2200').resolve()
TMP=ROOT/'output/design-publication-v7.2/transport-unit';TMP.mkdir(parents=True,exist_ok=True)
OLD=ROOT/'docs/design/transport-unit/v7.1'
def read(p):
    try:return p.read_text(encoding='utf-8-sig')
    except UnicodeDecodeError:return p.read_text(encoding='gb18030')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(n,v):(TMP/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
oldbase=json.loads((OLD/'source-baseline.json').read_text(encoding='utf-8'))
GROUPS=[(g['number'],g['title'],g['purpose'],g['source_ids']) for g in oldbase['reference_groups']]
GROUPS.extend([
 (15,'异形配置编辑与节点匹配','配置树编辑、重排ID和运行节点关联',[
 'TransportUnitSystem/Controls/TransportUnitEdit/FrmTransportUnitEdit.cs','TransportUnitSystem/Module/Config/OppositeSexConfiguration.cs','TransportUnitSystem/Controls/TransportUnitEdit/FrmAddObject.cs','TransportUnitSystem/Controls/TransportUnitEdit/FrmObjectCopy.cs','TransportUnitSystem/Controls/TransportUnitEdit/UcTransportUnitView.cs','TransportUnitSystem/Controls/TransportUnitEdit/UcObjectFunctionEdit.cs','Infrastructure/Controls/Feature/EditProgram/UcEditProductProgram/UcEditProductProgramming.cs']),
 (16,'配方与生产Mapping','样本对象、参与状态保存和关闭后的清空确认',[
 'TransportUnitSystem/Controls/Mapping/FrmTuMappingNew.cs','TransportUnitSystem/Controls/Mapping/FrmTuMapping.cs','TransportUnitSystem/Controls/Mapping/UcTransportShow.cs','TransportUnitSystem/Module/Config/OtherConfig.cs','TransportUnitSystem/Controls/Mapping/MappingDraw.cs','Main/Controls/Ucmain/MainControls/UcMainSystem.cs']),
 (17,'主动清空载具','整线与局部引用清除及界面进入条件',[
 'TransportSystem/Controllers/TransportController.cs','Main/Controls/UcShortcutMenu.cs','TransportSystem/Controls/Manual/UcTransportSystemManual.cs']),
 (18,'辅助对象与补偿模式','窗口对象、局部测试与区段替换',[
 'BondSystem/Tasks/BondTask.cs','TransportUnitSystem/Controls/Assistant/TUAssistantHelper.cs','BondSystem/Controls/Assistant/FrmMoveToBondingPosition.cs','DispenseSystem/Controls/Setting/EpoxyApplication/UcEpoxyApplication.cs','Experiment/TestFunction/FrmTest.cs']),
 (19,'位置辅助接口','固晶区段读取、配置点和返回参考系',[
 'BondSystem/Services/System2TUService.cs','BondSystem/Controls/Assistant/FrmMoveToBondingPosition.cs','BondSystem/Controls/Setting/BondPosition/UcBondPositionEdit.cs']),
 (20,'角度示教写回','窗口对象、调用方目标及分阶段保存',[
 'Infrastructure/Controls/Feature/EditProgram/UcEditProductProgram/UcEditProductProgramming.Assistance.cs','TransportUnitSystem/Controls/Assistant/FrmAdjustDegree.cs','TransportUnitSystem/Controls/Assistant/TUAssistantHelper.cs'])])
NEW=[
 ('TU25','6.10','整线和两种局部清空解除对应区段引用并置NoMaterial；入口受工作/暂停及确认限制，不统一回滚或复位全部消息。', [('TransportSystem/Controllers/TransportController.cs',159,328),('Main/Controls/UcShortcutMenu.cs',228,263),('TransportSystem/Controls/Manual/UcTransportSystemManual.cs',57,71),('TransportSystem/Controls/Manual/UcTransportSystemManual.cs',138,154)]),
 ('TU26','5.6','新配方Mapping使用样本TU，改变后的参与状态在关闭时写OtherConfig；生产Mapping持有真实TU，修改不等于配方进度保存。',[('TransportUnitSystem/Controls/Mapping/FrmTuMappingNew.cs',18,187),('TransportUnitSystem/Controls/Mapping/UcTransportShow.cs',44,79),('TransportUnitSystem/Controls/Mapping/UcTransportShow.cs',901,1005),('TransportUnitSystem/Module/Config/OtherConfig.cs',95,149)]),
 ('TU27','5.6','主界面关闭两种配方Mapping后，IsExistTu为真才进入InitializeTS，其状态检查和确认仍会影响是否清空。',[('Main/Controls/Ucmain/MainControls/UcMainSystem.cs',1025,1050),('TransportSystem/Controllers/TransportController.cs',140,224)]),
 ('TU28','5.5','异形编辑从编程页面可达，修改配置树并重排配置ID，不直接重建当前区段TU。',[('Infrastructure/Controls/Feature/EditProgram/UcEditProductProgram/UcEditProductProgramming.cs',711,734),('TransportUnitSystem/Controls/TransportUnitEdit/FrmTransportUnitEdit.cs',55,87),('TransportUnitSystem/Controls/TransportUnitEdit/FrmTransportUnitEdit.cs',114,212),('TransportUnitSystem/Controls/TransportUnitEdit/FrmTransportUnitEdit.cs',286,293)]),
 ('TU29','5.5','复制按行列跳过原位，调用方增加平移并改显示名；没有为复制节点独立重命名ConfigName。',[('TransportUnitSystem/Controls/TransportUnitEdit/FrmObjectCopy.cs',63,96),('TransportUnitSystem/Controls/TransportUnitEdit/FrmTransportUnitEdit.cs',179,212),('TransportUnitSystem/Controls/TransportUnitEdit/UcTransportUnitView.cs',339,371)]),
 ('TU30','5.5','异形删除用引用移除节点；配置名无剩余引用时清该名称公共配置及四个Mark PR。',[('TransportUnitSystem/Module/Config/OppositeSexConfiguration.cs',236,279),('TransportUnitSystem/Module/Config/OppositeSexConfiguration.cs',64,108),('TransportUnitSystem/Controls/TransportUnitEdit/FrmAddObject.cs',82,133)]),
 ('TU31','6.11','在线JudgeTuExist不补建空区段；非空时可重建，生产标记存在先确认；离线仅返回新辅助TU。',[('TransportUnitSystem/Controls/Assistant/TUAssistantHelper.cs',392,455)]),
 ('TU32','6.11','窗口和点胶测试创建局部TU，与区段当前对象分开；S1二次偏移调用受构造时标记保护。',[('BondSystem/Controls/Assistant/FrmMoveToBondingPosition.cs',97,114),('DispenseSystem/Controls/Setting/EpoxyApplication/UcEpoxyApplication.cs',640,646),('DispenseSystem/Controls/Setting/EpoxyApplication/UcEpoxyApplication.cs',805,813),('TransportUnitSystem/Module/Matter/TransportUnit.cs',526,550)]),
 ('TU33','6.11','补偿工作模式先替换为字符串构造TU，再在Enable且输送配置条件下按S2再次创建。',[('BondSystem/Tasks/BondTask.cs',181,209),('TransportUnitSystem/Module/Matter/TransportUnit.cs',73,101)]),
 ('TU34','7.6','异形节点反查使用对象引用比较，包括根；未命中抛异常；示教父对象与目标对象均使用该接口。',[('TransportUnitSystem/Module/Matter/TransportUnit.cs',649,680),('TransportUnitSystem/Controls/TransportUnitEdit/UcObjectFunctionEdit.cs',335,369)]),
 ('TU35','7.6','位置辅助从固晶区段取TU，返回阶段并不统一；焊点示教取基岛父链与配置点。',[('BondSystem/Services/System2TUService.cs',21,159),('BondSystem/Controls/Assistant/FrmMoveToBondingPosition.cs',180,229)]),
 ('TU36','8.7','两点窗口在线成功先改传入运行坐标并Save；离线OK不计算新角；跨度不足及超角不成功写入。',[('TransportUnitSystem/Controls/Assistant/FrmAdjustDegree.cs',91,173),('TransportUnitSystem/Controls/Assistant/FrmAdjustDegree.cs',239,242)]),
 ('TU37','8.7','TU、基板、基岛和焊点示教的窗口对象与后续目标不同；窗口Save先于部分后续赋值，后续取消无统一回滚。',[('Infrastructure/Controls/Feature/EditProgram/UcEditProductProgram/UcEditProductProgramming.Assistance.cs',63,153),('Infrastructure/Controls/Feature/EditProgram/UcEditProductProgram/UcEditProductProgramming.Assistance.cs',159,274),('Infrastructure/Controls/Feature/EditProgram/UcEditProductProgram/UcEditProductProgramming.Assistance.cs',687,728)]),
 ('TU38','附录C','GetAllBondPositionConfigs最内层加入基岛节点；本目录只有注释中的调用，不能外推已发生生产故障。',[('TransportUnitSystem/Module/Config/OppositeSexConfiguration.cs',215,229),('Main/Machine/Process/ProcessDomain.cs',208,225)]),
]
def build():
    paths=list(dict.fromkeys(x for _,_,_,xs in GROUPS for x in xs));files=[]
    for rel in paths:
        p=(SCOPE/rel).resolve();assert p.is_relative_to(SCOPE);ls=read(p).splitlines()
        anchors=[{'line':i,'symbol':t.strip()} for i,t in enumerate(ls,1) if re.search(r'^\s*(?:public|private|protected|internal).*(?:\(| class | enum )',t)]
        files.append({'id':rel,'path':'trunk/AKRS.ZX2200/'+rel,'sha256':sha(p),'line_count':len(ls),'anchors':anchors or [{'line':1,'symbol':ls[0]}],'anchor_method':'文本定位；不作为整文件业务理解证明'})
    base={'date':'2026-10-21','revision':'7.2','scope':'trunk/AKRS.ZX2200','external_dependencies':'仅核对本目录调用及前提，不解析外部实现','files':files,'reference_groups':[dict(number=n,title=t,purpose=u,source_ids=xs) for n,t,u,xs in GROUPS]};dump('source-baseline.json',base)
    claims=json.loads((OLD/'claim-map.json').read_text(encoding='utf-8'))['claims']
    for c in claims:
        for e in c['evidence']:
            p=ROOT/e['path'];assert sha(p)==e['sha256'];ls=read(p).splitlines();assert ls[e['start']-1].strip()==e['start_text'] and ls[e['end']-1].strip()==e['end_text']
        c['review_origin']='保留第7.1版语义核查；本轮重新核验源码哈希和原锚点，重点路径另列新增范围'
    for cid,sec,conclusion,ranges in NEW:
        ev=[]
        for rel,a,b in ranges:
            p=SCOPE/rel;ls=read(p).splitlines();assert 1<=a<=b<=len(ls)
            ev.append(dict(path='trunk/AKRS.ZX2200/'+rel,start=a,end=b,start_text=ls[a-1].strip(),end_text=ls[b-1].strip(),sha256=sha(p),locator='本轮实际核读区段及调用上下文'))
        claims.append(dict(id=cid,sections=sec,conclusion=conclusion,evidence=ev,basis='本目录当前源码静态路径；不声称设备或整套C#运行验证'))
    extra=[('TU39','附录C','异形GetModuleCount返回每板最大基岛数，空基板集合上的Max会抛异常。','TransportUnitSystem/Module/Config/OppositeSexConfiguration.cs',300,312),('TU40','5.6','新Mapping关闭写回只改内存；SaveInformation无Save且异常仅弹窗；旧Mapping关闭调用保存回调。','TransportUnitSystem/Module/Config/OtherConfig.cs',95,150)]
    for cid,sec,conclusion,rel,a,b in extra:
        p=SCOPE/rel;ls=read(p).splitlines();ev=[dict(path='trunk/AKRS.ZX2200/'+rel,start=a,end=b,start_text=ls[a-1].strip(),end_text=ls[b-1].strip(),sha256=sha(p),locator='本轮实际核读区段')]
        if cid=='TU40':
            for rel,a,b in [('TransportUnitSystem/Controls/Mapping/FrmTuMappingNew.cs',180,187),('TransportUnitSystem/Controls/Mapping/FrmTuMapping.cs',390,393),('TransportUnitSystem/Controls/Mapping/MappingDraw.cs',314,352)]:
                p=SCOPE/rel;ls=read(p).splitlines();ev.append(dict(path='trunk/AKRS.ZX2200/'+rel,start=a,end=b,start_text=ls[a-1].strip(),end_text=ls[b-1].strip(),sha256=sha(p),locator='本轮实际核读区段'))
        claims.append(dict(id=cid,sections=sec,conclusion=conclusion,evidence=ev,basis='本目录静态实现及集合接口契约；不外推实机故障'))
    dump('claim-map.json',dict(scope='trunk/AKRS.ZX2200',claims=claims))
    oldreads=json.loads((OLD/'source-analysis.json').read_text(encoding='utf-8'))
    reviewed=oldreads['reviewed_ranges']
    for c in claims[24:]:
        for e in c['evidence']:reviewed.setdefault(e['path'],[]).append(dict(start=e['start'],end=e['end'],claim=c['id'],review_round='7.2'))
    dump('source-analysis.json',dict(scope='trunk/AKRS.ZX2200',review_type='旧语义核查保留且验当前哈希；新增范围实际核读；扫描不等于全文件阅读',reviewed_ranges=reviewed))
    return base
if __name__=='__main__':print('source basis',len(build()['files']))
