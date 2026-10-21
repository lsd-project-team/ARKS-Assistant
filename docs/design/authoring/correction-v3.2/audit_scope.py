"""Discover compiled correction candidates, including generic UI entry calls.

The discovery output is an index, not a declaration that every file was read.
All source access is asserted against the user-approved directory.
"""
from pathlib import Path
import sys,json,hashlib,re,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
SCOPE=(ROOT/'trunk/AKRS.ZX2200').resolve(); OUT=ROOT/'output/correction-v3.2'
sys.path.insert(0,str(ROOT/'output/design-publication-v7.1/vendor'))
import tree_sitter_c_sharp
from tree_sitter import Language,Parser
parser=Parser(Language(tree_sitter_c_sharp.language()))
ns={'m':'http://schemas.microsoft.com/developer/msbuild/2003'}
compiled={e.attrib['Include'].replace('\\','/') for e in ET.parse(SCOPE/'AKRS.ZX2200.csproj').findall('.//m:Compile',ns)}
names=set('System1MatterVision System2ObjectVision System2MatterVision CalculatePickPos CalculateBondPos UplookVisionAction ToRequiredAccuracy MoveDieToPickCenter GetPostBondCompensation GetBpSeparateOffset GetCompensatePoint3D GetBondCompensate PickUpCompensationVision System2TemperatureCompensation GetTemperatureCompensation GetPickCompensation Open2DCompensate Close2DCompensate OpenCompensate CloseCompensate OpenStage CloseStage HuberEstimate FinishCollectAndCalculate GetRoundsAfterTime'.split())
extra=re.compile(r'Correction|Compensat|AdjustDegree|Calibrat|VisionTest')
def walk(n):
    yield n
    for c in n.children:yield from walk(c)
def txt(n,b):return b[n.start_byte:n.end_byte].decode('utf-8-sig') if n else ''
candidates=[]; scanned=[]
for p in sorted(SCOPE.rglob('*.cs')):
    assert p.resolve().is_relative_to(SCOPE)
    rel=p.relative_to(SCOPE).as_posix()
    raw=p.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    scanned.append(dict(file=rel,sha256=digest,compiled=rel in compiled))
    if p.name.endswith('.Designer.cs'):continue
    tree=parser.parse(raw); hits=[]
    for n in walk(tree.root_node):
        if n.type=='method_declaration':
            name=txt(n.child_by_field_name('name'),raw)
            if extra.search(name):hits.append(dict(line=n.start_point.row+1,kind='declaration',expression=name))
        elif n.type=='invocation_expression':
            f=n.child_by_field_name('function');name=txt(f.child_by_field_name('name') if f else None,raw)
            expression=txt(f,raw)
            if name in names or ('ShowForm<' in expression and extra.search(expression)):
                hits.append(dict(line=n.start_point.row+1,kind='call',expression=expression))
        elif n.type=='object_creation_expression':
            t=txt(n.child_by_field_name('type'),raw)
            if extra.search(t):hits.append(dict(line=n.start_point.row+1,kind='new',expression=t))
        elif n.type=='assignment_expression':
            left=txt(n.child_by_field_name('left'),raw)
            if re.search(r'(Component(?:Angle)?OffSet|IPT(?:Vision|Pick)Pos|TransportUnitCompensate[XY])$',left):
                hits.append(dict(line=n.start_point.row+1,kind='write',expression=left))
    if not hits and not extra.search(p.stem):continue
    candidates.append(dict(file=rel,compiled=rel in compiled,sha256=digest,parse_error=tree.root_node.has_error,hits=hits))
out=dict(scope='trunk/AKRS.ZX2200',date='2026-10-21',method='当前C#语法树调用、泛型UI入口、构造与关键字段赋值；Compile为工程显式项，非整机编译或精确类型绑定',
         project_sha256=hashlib.sha256((SCOPE/'AKRS.ZX2200.csproj').read_bytes()).hexdigest(),
         scanned_files=scanned,candidates=candidates)
(OUT/'scope-discovery.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
old=json.loads((ROOT/'docs/design/correction-process/v3.1/source-baseline.json').read_text(encoding='utf-8'))
old_paths={f['path'].split('trunk/AKRS.ZX2200/')[1]:f['sha256'] for f in old['files']}
changed=[rel for rel,h in old_paths.items() if hashlib.sha256((SCOPE/rel).read_bytes()).hexdigest()!=h]
assert not changed,changed
print(f'{len(scanned)} C# files indexed; {len(candidates)} candidates; {len(old_paths)} retained source files unchanged')
for c in candidates:
    if c['file'] not in old_paths:print(('IN ' if c['compiled'] else 'OUT ')+c['file']+' : '+', '.join(str(h['line'])+':'+h['expression'] for h in c['hits'][:5]))
