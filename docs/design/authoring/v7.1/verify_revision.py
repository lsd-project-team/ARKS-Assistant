"""Compare source guard expressions with document contracts, plus independent examples.
This interprets pure condition expressions; it never loads or executes the C# program.
"""
from pathlib import Path
import itertools,json,math,sys
from syntax_inventory import BASE,SCOPE,parse,walk,text,region
actions=['S1CarrierVisionActionNode','S1SubstrateVisionActionNode','S1ModuleVisionActionNode','S1DispenseCorrectionActionNode','S2CarrierVisionActionNode','S2SubstrateVisionActionNode','S2ModuleVisionActionNode','BondPositionVisionActionNode']
checks=[]
def value(n,data,e):
    if n.type=='binary_expression':
        a=n.child_by_field_name('left');b=n.child_by_field_name('right')
        op=data[a.end_byte:b.start_byte].decode().strip()
        av=value(a,data,e)
        if op=='||':return av or value(b,data,e)
        if op=='&&':return av and value(b,data,e)
        bv=value(b,data,e)
        return av==bv if op=='==' else av!=bv if op=='!=' else (_ for _ in ()).throw(ValueError(op))
    if n.type=='parenthesized_expression':return value(n.named_children[0],data,e)
    s=text(n,data)
    if s=='null':return None
    if s in ('true','false'):return s=='true'
    if '.' not in s:return None if e['null'] else 'object'
    if s.startswith('MatterProductState.'):return s.split('.')[-1]
    if s.startswith('AdjustTypeEnum.'):return s.split('.')[-1]
    if s.startswith('EntityState.'):return s.split('.')[-1]
    if e['null']:raise AttributeError('null target')
    if s.endswith('.MatterProductState'):return e['scope']
    if s.endswith('.AdjustType'):return 'None' if e['none'] else 'One'
    if s.endswith('.IsVisioned'):return e['visioned']
    if s.endswith('.EntityState'):return 'Process' if e['process'] else 'Fail'
    if re_finished(s):return e['finished']
    raise ValueError(s)
def re_finished(s):return 'Finished' in s or 'FinishInSystem2' in s
for i,name in enumerate(actions):
    p=next(SCOPE.rglob(name+'.cs'));data,tree=parse(p)
    m=next(n for n in walk(tree.root_node) if n.type=='method_declaration' and text(n.child_by_field_name('name'),data)=='IsDoWork')
    guards=[n for n in m.child_by_field_name('body').named_children if n.type=='if_statement']
    cases=0
    for null,none,visioned,finished,process,scope in itertools.product([False,True],[False,True],[False,True],[False,True],[False,True],['Enable','Disable','EnableInSystem1','EnableInSystem2']):
        env=dict(null=null,none=none,visioned=visioned,finished=finished,process=process,scope=scope)
        excluded=scope in (['Disable','EnableInSystem2'] if i<4 else ['Disable','EnableInSystem1'])
        expected='error' if null else not(excluded or visioned or (none and i!=0) or (finished and i!=7) or (not process and i==5))
        try:
            actual=True
            for g in guards:
                if value(g.child_by_field_name('condition'),data,env):
                    body=text(g.child_by_field_name('consequence'),data)
                    actual='error' if 'throw ' in body else False
                    break
        except AttributeError:actual='error'
        assert actual==expected,(name,env,actual,expected)
        cases+=1
    checks.append({'action':name,'source':region(name+'.cs','IsDoWork'),'cases':cases,'passed':True})

numeric=[]
def record(id,inputs,result,expected):
    def close(a,b):
        if isinstance(a,(list,tuple)):return len(a)==len(b) and all(close(x,y) for x,y in zip(a,b))
        return abs(a-b)<1e-10 if isinstance(a,(float,int)) else a==b
    assert close(result,expected),(id,result,expected)
    numeric.append(dict(id=id,inputs=inputs,result=result,expected=expected,passed=True))
record('R01',{'config_x':100,'s1_offset':2,'divide_distance':40},[100+2,100+2+40,100+2+40-40,100],[102,142,102,100])
record('R02',{'substrates':2,'modules':[2,3],'one_bp_per_module':True},1+2+sum([2,3])+sum([2,3]),13)
record('R03',{'tu':[100,200],'sub':[20,0],'module':[10,5],'bp':[2,1]},[100+20+10+2,200+0+5+1],[132,206])
record('R04',{'sub_location_delta_x':.1},[132+.1,206],[132.1,206])
record('R05',{'origin':[100,200],'offset':[.1,-.2],'rotation':0},[[100+.1+.1,200-.2-.2],[100+.1,200-.2]],[[100.2,199.6],[100.1,199.8]])
for mirror in [False,True]:
    a,b,h,pr,n=2,5,1,3,20
    prep=pr+n+b+h;rel=a+b+(180-h if mirror else h);now=prep+rel;save=-(b+h);goal=now+save+b+h
    record('R06M' if mirror else 'R06N',{'a':a,'b':b,'h':h,'pr':pr,'align':n,'mirror':mirror},[prep,rel,now,save,goal],[29,186,215,-6,215] if mirror else [29,8,37,-6,37])
record('R07',{'post_rotation_machine_minus_glass':[.02,-.01],'pixel_distance':[.12,-.08],'taught_vector':[.5,.2]},[.02+.12-.5,-.01-.08-.2],[-.36,-.29])
# Two-axis selection and odd-column segmentation are independent design boundaries.
record('R08',{'column_count':5,'row_indices':[[1,2,3,4,5]]},list(range(1,5//2+1)),[1,2])
record('R09',{'irregular_substrate_x':[-10,0,15,-2]},[i+1 for i,x in enumerate([-10,0,15,-2]) if x<0],[1,4])

report={'method':'直接解释本目录IsDoWork纯条件表达式，并与文档逐入口契约比较；数值独立复算；不执行C#业务或设备','scope':'trunk/AKRS.ZX2200','guard_cases':sum(c['cases'] for c in checks),'guards':checks,'numeric_examples':numeric,'tolerance':1e-10}
(BASE/'revision-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Source guard contracts:',report['guard_cases'],'cases; numeric examples:',len(numeric))
