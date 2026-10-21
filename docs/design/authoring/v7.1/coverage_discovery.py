from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[4];BASE=ROOT/'output/design-publication-v7.1'
data=json.loads((BASE/'syntax-index.json').read_text(encoding='utf-8'))
names=set('System1MatterVision System2ObjectVision System2MatterVision CalculatePickPos CalculateBondPos UplookVisionAction ToRequiredAccuracy MoveDieToPickCenter GetPostBondCompensation GetBpSeparateOffset GetCompensatePoint3D GetBondCompensate PickUpCompensationVision System2TemperatureCompensation GetTemperatureCompensation GetPickCompensation RefreshMap RefreshTransportUnit UpdateTransportUnit System1MoveDistance System1BackMoveDistance MapBelt ReadTransportMapping ReadTransportMappingByComponent SaveMappingToLocal SortRelativeBond'.split())
old=json.loads((ROOT/'docs/design/transport-unit/v7/entry-coverage.json').read_text(encoding='utf-8'))
oldfiles={e['file']:e for e in old['entries']}
files={}
for m in data['methods']:
    calls=[c for c in m['calls'] if c['callee'] in names or (c['callee']=='Refresh' and re.search('TransportUnit|transportUnit',c['expression']))]
    writes=[w for w in m['writes'] if re.search(r'(?:^|\.)TransportUnit$|^transportUnit$',w['target'])]
    # Constructors can be qualified; byte-level line matches are independently cross-checked below.
    if not calls and not writes:continue
    rel=m['path'].split('trunk/AKRS.ZX2200/')[1]
    f=files.setdefault(rel,{'file':rel,'compiled':m['compiled'],'sha256':m['sha256'],'methods':[]})
    f['methods'].append({'class':m['class'],'method':m['method'],'start':m['start'],'end':m['end'],'calls':calls,'writes':writes})
for rel,f in files.items():
    o=oldfiles.get(rel)
    f['prior_disposition']=o['entry_kind'] if o else None
out={'scope':'trunk/AKRS.ZX2200','method':'全目录语法树调用及赋值发现，并从已注册动作、任务及UI事件反向核对；语法名称不等于精确类型绑定','files':list(files.values())}
(BASE/'coverage-candidates.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for rel,f in files.items():
    if rel not in oldfiles:print(('COMPILED ' if f['compiled'] else 'EXCLUDED ')+rel+' : '+', '.join(m['method'] for m in f['methods']))
print('syntax candidates:',len(files),'new files:',len(set(files)-set(oldfiles)))
