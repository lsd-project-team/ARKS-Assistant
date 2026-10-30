"""Independent arithmetic for the added diagrams and algorithm contracts."""
from pathlib import Path
import math,statistics,json
H=Path(__file__).resolve().parent;ROOT=H.parents[3];OUT=ROOT/'output/correction-v3.2'
checks=[]
def close(a,b):
    if isinstance(a,(list,tuple)):return len(a)==len(b) and all(close(x,y) for x,y in zip(a,b))
    if isinstance(a,bool):return a is b
    return abs(a-b)<1e-10
def check(name,inputs,actual,expected):
    assert close(actual,expected),(name,actual,expected)
    checks.append(dict(name=name,inputs=inputs,result=actual,expected=expected,passed=True))
check('图10-1两点角',dict(p1=[0,0],p2=[20,1]),math.degrees(math.atan((-1)/(-20))),2.862405226111748)
check('X跨度边界包含1',dict(dx=1),abs(1)<1,False)
check('按X跨度而非欧氏距离',dict(p1=[0,0],p2=[.9,10]),abs(.9)<1,True)
check('角度上限包含5',dict(angle=5),abs(5)>5,False)
check('角度超限',dict(angle=-5.001),abs(-5.001)>5,True)
check('固高间距先取整',dict(spacing=.8,pulse_ratio=10000),math.trunc(.8)*10000,0)
check('固高间距与起点不同次序',dict(value=1.25,pulse_ratio=10000),[math.trunc(1.25)*10000,math.trunc(1.25*10000)],[10000,12500])
row=[0.,1.,100.,3.,4.]
def imported(a):
    out=[]
    for i in range(len(a)):
        if i in (0,len(a)-1):out.append(a[i])
        elif i in (1,len(a)-2):out.append(statistics.mean(a[i-1:i+2]))
        else:out.append(statistics.mean(a[i-2:i+3]))
    return out
check('图11-3人工均值',[row],imported(row),[0,101/3,108/5,107/3,4])
check('图11-3自动中位数',[row],[statistics.median(row[max(0,i-2):min(len(row),i+3)]) for i in range(5)],[1,2,3,3.5,4])
check('两列人工导入边界',[1,10],imported([1,10]),[1,10])
check('三列人工导入边界',[1,10,100],imported([1,10,100]),[1,37,100])
check('TU插值超限边界',dict(value=1),abs(1)>1,False)
check('TU插值超限',dict(value=-1.000001),abs(-1.000001)>1,True)

def huber(a):
    if not a:return 0.
    if len(a)==1:return a[0]
    m=statistics.median(a);mad=statistics.median([abs(v-m) for v in a]);scale=1.4826*mad
    if scale==0:return m
    weights=[1. if abs(v-m)/scale<=1.345 else 1.345/(abs(v-m)/scale) for v in a]
    return sum(v*w for v,w in zip(a,weights))/sum(weights)
sample=[.01,.011,.012,.4];center=huber(sample)
check('Huber残差平移等变',dict(sample=sample),huber([v-center for v in sample]),0.)
(OUT/'calculator-reference.json').write_text(json.dumps(dict(sample=sample,center=center,method='独立Python中位数与单次权重计算；供原始C#类交叉验证'),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'new-arithmetic-verification.json').write_text(json.dumps(dict(method='独立公式与边界复算；实际原始C#数值类另见calculator-csharp.json',checks=checks),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'{len(checks)} new diagram and boundary checks passed; weighted Huber reference={center:.14f}')
