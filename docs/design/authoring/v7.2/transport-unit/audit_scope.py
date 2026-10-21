"""Revalidate the current scope, compile items, and method-level TU entry coverage."""
from evidence import ROOT,SCOPE,TMP,read,sha,dump
import json,re,xml.etree.ElementTree as ET
INDEX=ROOT/'output/design-publication-v7.1/syntax-index.json'
ix=json.loads(INDEX.read_text(encoding='utf-8'))
cached={f['path']:f for f in ix['files']}; current=[]
project=SCOPE/'AKRS.ZX2200.csproj';ns={'m':'http://schemas.microsoft.com/developer/msbuild/2003'}
compiled={n.attrib['Include'].replace('\\','/') for n in ET.parse(project).findall('.//m:Compile',ns)}
assert sha(project)==ix['project_sha256'],'Project changed; refresh the syntax inventory before using it'
for p in sorted(SCOPE.rglob('*.cs')):
    path=p.relative_to(ROOT).as_posix();assert path in cached and sha(p)==cached[path]['sha256'],path
    current.append(dict(path=path,sha256=sha(p),compiled=p.relative_to(SCOPE).as_posix() in compiled))
assert len(current)==len(cached),'Removed/added source files require a fresh syntax inventory'
# All method receivers and conditions remain the exact current source because every file was rehashed.
calls={'UpdateTransportUnit','RefreshTransportUnit','ReadTransportMapping','ReadTransportMappingByComponent','JudgeTuExist','InitializeTS','InitializeTSInDispense','InitializeTSInBond','GetBaseMatterByOppositeSex','SaveInformation','ChangeMatterProduct','RemoveOppositeSexConfig','InitOppositeSexConfigIndex'}
entries=[]
for m in ix['methods']:
    rel=m['path'].replace('trunk/AKRS.ZX2200/','')
    writes=[w for w in m['writes'] if re.search(r'(?:^|\.)TransportUnit$',w['target'])]
    cs=[c for c in m['calls'] if c['callee'] in calls or c['callee']=='Refresh' and re.search('transportUnit|TransportUnit',c['expression'])]
    own=m['class']=='TransportUnit' or m['class'] in ['FrmTuMappingNew','FrmTuMapping','FrmTransportUnitEdit','FrmObjectCopy','FrmAddObject','System2TUService','FrmAdjustDegree']
    if not writes and not cs and not own:continue
    if '/Experiment/' in m['path'] or rel.startswith('Experiment/'):
        sec='6.11及维护资料';kind='实验辅助';note='实验类单列，不作为正常生产交接证据'
    elif m['class']=='TransportUnit':sec='3—7';kind='运行模型';note='构建、查询、几何及状态接口；分段旧便捷函数与实际消息划分分别归属'
    elif m['class']=='System2TUService':sec='7.6';kind='位置辅助';note='当前固晶区段、配置点与返回参考系逐方法说明'
    elif m['class'] in ['FrmTransportUnitEdit','FrmObjectCopy','FrmAddObject'] or 'OppositeSex' in ''.join(c['expression'] for c in cs):sec='5.5、7.6';kind='异形配置编辑';note='配置节点树操作；不等同重建旧运行TU'
    elif m['class']=='FrmAdjustDegree':sec='8.7';kind='角度示教';note='窗口传入对象、调用方写入与取消分别核对'
    elif m['method'] in ['InitializeTS','InitializeTSInDispense','InitializeTSInBond'] or any(c['callee'].startswith('InitializeTS') for c in cs):sec='5.6、6.10';kind='清空入口或调用方';note='按方法区分整线与单区段清空；上层附加条件不泛化'
    elif 'Mapping' in m['path'] or any(c['callee'] in ['ReadTransportMapping','ReadTransportMappingByComponent'] for c in cs):sec='5.6、8.3、8.5';kind='Mapping';note='样本、真实区段与导入新树分别归属'
    elif 'TransportSystem/' in rel:sec='6.2—6.11、8.2、8.6';kind='输送与启动';note='沿用、刷新、新建、清空及部分提交按实际入口区分'
    elif 'TUAssistantHelper' in rel:sec='6.11、8.7';kind='示教对象入口';note='在线区段替换与离线窗口对象分别说明'
    elif 'FrmTeach' in rel or 'FrmRelative' in rel:sec='6.6、7.1';kind='示教保存';note='保存后UpdateTransportUnit重建运行树'
    elif m['class']=='BondTask':sec='6.4、6.11';kind='固晶生产及补偿模式';note='字符串与System2构造的两个判断分别说明'
    elif m['class']=='DispenseWorkTask':sec='6.2';kind='点胶生产';note='IsProduct条件下新建并注入工序'
    elif m['method']=='PlacementTest':sec='6.11、纠偏分册手动贴片';kind='手动贴片';note='此处TU赋值是当前单例区段引用回赋，不宣称独立新建'
    else:sec='7.1及维护资料';kind='辅助调用';note='消费当前TU或触发既有刷新接口；不单列为生产交接'
    entries.append(dict(file=rel,method=m['method'],start=m['start'],end=m['end'],compiled=rel in compiled,kind=kind,sections=sec,note=note,assignments=writes,calls=cs,conditions=m['conditions']))
pattern=re.compile(r'\bTransportUnit\b|\bBaseMatter\b|GetBaseMatterByOppositeSex|InitializeTS(?:InDispense|InBond)?\s*\(')
candidates=[]
for f in current:
    rel=f['path'].replace('trunk/AKRS.ZX2200/','')
    if rel.lower().endswith('.designer.cs'):continue
    lines=read(ROOT/f['path']).splitlines();hits=[dict(line=i,text=t.strip()) for i,t in enumerate(lines,1) if not t.lstrip().startswith('//') and pattern.search(t)]
    if not hits:continue
    owned=[e for e in entries if e['file']==rel]
    if owned:disposition='方法级入口见entries；其余命中作为配置或数据消费者，不增加独立生命周期'
    elif '/Models/ActionNodes/' in '/'+rel or '/DispenseAction/' in rel:disposition='生产动作消费者：当前对象读取、定位/测高/读码结果及工序写入；设计按数据契约归属3.4—3.6与6.2—6.4，算法归纠偏册'
    elif rel.startswith('WaferSubSystem/'):disposition='供料示教的枚举或配置命名引用；无本次TU运行引用赋值入口'
    elif rel.startswith('TransportUnitSystem/Module/'):disposition='对象或配置定义；关联与数据字段归属3—5章'
    else:disposition='辅助显示、参数或动作消费者；未发现本扫描定义的TU创建/替换/刷新入口，未声明整文件深读'
    candidates.append(dict(file=rel,compiled=f['compiled'],sha256=f['sha256'],matches=hits,disposition=disposition))
dump('scope-discovery.json',dict(scope='trunk/AKRS.ZX2200',method='全C#现态哈希+Compile重验后复用同字节语法树；名称边必须结合实际接收者；不是Roslyn绑定或逐文件业务阅读',project_sha256=sha(project),files=current,candidates=candidates))
dump('entry-coverage.json',dict(scope='trunk/AKRS.ZX2200',method='方法级列出入口、区段赋值、刷新与配置辅助；仅匹配和归属不等于完整语义读取',known_unassigned_entries=[],entries=entries))
md=['# Transport Unit入口核查','','扫描与已读范围分别见scope-discovery.json和source-analysis.json。以下归属以当前编译项及本目录调用条件为准。','','| 文件与方法 | 范围 | 归属 | 文档 | 说明 |','|---|---|---|---|---|']
md += [f"| {e['file']} / {e['method']} | {e['start']}—{e['end']} | {e['kind']} | {e['sections']} | {e['note']} |" for e in entries]
(TMP/'entry-coverage.md').write_text('\n'.join(md)+'\n',encoding='utf-8',newline='\n')
print(dict(cs_files=len(current),compiled=len(compiled),candidate_files=len(candidates),method_entries=len(entries)))
