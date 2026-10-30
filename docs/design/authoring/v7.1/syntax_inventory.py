"""Parse only approved C# sources. Syntax edges are not semantic binding."""
from pathlib import Path
import sys,json,hashlib,xml.etree.ElementTree as ET
BASE=Path(__file__).resolve().parents[4]/'output/design-publication-v7.1'
sys.path.insert(0,str(BASE/'vendor'))
import tree_sitter_c_sharp
from tree_sitter import Language,Parser
ROOT=Path(__file__).resolve().parents[4];SCOPE=(ROOT/'trunk/AKRS.ZX2200').resolve()
PARSER=Parser(Language(tree_sitter_c_sharp.language()))
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def walk(n):
    yield n
    for c in n.children:yield from walk(c)
def text(n,data):return data[n.start_byte:n.end_byte].decode('utf-8') if n else ''
def parse(p):
    assert p.resolve().is_relative_to(SCOPE)
    data=p.read_bytes();return data,PARSER.parse(data)
def methods(p):
    data,tree=parse(p);out=[]
    for n in walk(tree.root_node):
        if n.type not in ('method_declaration','constructor_declaration'):continue
        owner=n.parent
        while owner and owner.type not in ('class_declaration','struct_declaration'):owner=owner.parent
        name=text(n.child_by_field_name('name'),data)
        cname=text(owner.child_by_field_name('name'),data) if owner else ''
        calls=[];guards=[];writes=[]
        for c in walk(n):
            if c.type=='invocation_expression':
                f=c.child_by_field_name('function');name_node=f.child_by_field_name('name') if f else None
                calls.append({'line':c.start_point.row+1,'callee':text(name_node or f,data),'expression':text(f,data)})
            elif c.type=='if_statement':guards.append({'line':c.start_point.row+1,'condition':text(c.child_by_field_name('condition'),data)})
            elif c.type=='assignment_expression':writes.append({'line':c.start_point.row+1,'target':text(c.child_by_field_name('left'),data),'expression':text(c,data)})
        out.append({'path':'trunk/AKRS.ZX2200/'+p.relative_to(SCOPE).as_posix(),'class':cname,'method':name,'start':n.start_point.row+1,'end':n.end_point.row+1,'parse_error':n.has_error,'sha256':sha(p),'calls':calls,'conditions':guards,'writes':writes})
    return out,tree.root_node.has_error
def region(filename,method):
    hits=list(SCOPE.rglob(filename));assert len(hits)==1,(filename,hits)
    found=[m for m in methods(hits[0])[0] if m['method']==method];assert found,(filename,method)
    return found[0]
if __name__=='__main__':
    project=SCOPE/'AKRS.ZX2200.csproj';ns={'m':'http://schemas.microsoft.com/developer/msbuild/2003'}
    compiled={n.attrib['Include'].replace('\\','/') for n in ET.parse(project).findall('.//m:Compile',ns)}
    entries=[];files=[]
    for p in sorted(SCOPE.rglob('*.cs')):
        rel=p.relative_to(SCOPE).as_posix();print('Parsing',rel,flush=True);ms,error=methods(p)
        for m in ms:m['compiled']=rel in compiled
        entries.extend(ms);files.append({'path':'trunk/AKRS.ZX2200/'+rel,'compiled':rel in compiled,'parse_error':error,'sha256':sha(p),'methods':len(ms)})
    dump(BASE/'syntax-index.json',{'scope':'trunk/AKRS.ZX2200','project_sha256':sha(project),'parser':'tree-sitter-c-sharp','method':'语法解析排除注释和字符串伪调用；名称级调用需结合接收对象人工核对，不作Roslyn类型绑定声明','files':files,'methods':entries})
    nodes=['S1CarrierVisionActionNode','S1SubstrateVisionActionNode','S1ModuleVisionActionNode','S1DispenseCorrectionActionNode','S2CarrierVisionActionNode','S2SubstrateVisionActionNode','S2ModuleVisionActionNode','BondPositionVisionActionNode']
    with (BASE/'eight-actions.txt').open('w',encoding='utf-8') as o:
        for name in nodes:
            for m in [m for m in entries if m['class']==name and m['method'] in ('DoWork','IsDoWork')]:
                assert not m['parse_error'],(name,m['method'])
                p=ROOT/m['path'];ls=p.read_text(encoding='utf-8-sig').splitlines()
                o.write(f"\n{name}.{m['method']} L{m['start']}-{m['end']}\n")
                for n in range(m['start']-1,m['end']):
                    line=ls[n].strip()
                    if line and not line.startswith('//'):o.write(f'{n+1}: {line}\n')
    print({'files':len(files),'compiled':sum(f['compiled'] for f in files),'methods':len(entries),'parse_error_files':sum(f['parse_error'] for f in files)})
