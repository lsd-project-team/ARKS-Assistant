"""Independent numeric examples for the book, not device or C# workflow tests."""
from evidence import dump
import math,cmath
checks=[]
def check(name,actual,expected,tol=1e-9):
    if isinstance(actual,complex):assert abs(actual-complex(*expected))<tol,(name,actual,expected)
    else:assert abs(actual-expected)<tol,(name,actual,expected)
    checks.append(dict(name=name,actual=[actual.real,actual.imag] if isinstance(actual,complex) else actual,expected=expected,tolerance=tol))
# Independent rigid-transform evaluation, with explicitly declared inputs.
local=complex(20,0)+complex(10,5)+complex(10,5)
global_point=complex(100,200)+local*cmath.exp(1j*math.pi/2)
check('普通四层点 G0 mm',global_point,(90,240))
check('S1偏移后的点 mm',global_point+complex(2,-1),(92,239))
check('G0逆变换回TU局部 mm',(global_point-complex(100,200))*cmath.exp(-1j*math.pi/2),(40,10))
check('刷新恢复配置的Z mm',0,0)
check('分段前移 X mm',102+40,142);check('分段回移 X mm',142-40,102)
check('异形例对象总数',1+2+5+5,13);check('异形例焊点 mm',complex(100,200)+complex(20,0)+complex(10,5)+complex(2,1),(132,206))
angle=math.atan2(1,20)
check('两点示教角 rad',angle,0.04995839572194276)
check('两点示教角 deg',math.degrees(angle),2.862405226111748)
assert 20>=1 and abs(math.degrees(angle))<=5
# Copy-spacing reading: six locations include original; five additional nodes.
points=[(10+20*c,5+10*r) for c in range(3) for r in range(2)]
assert points==[(10,5),(10,15),(30,5),(30,15),(50,5),(50,15)]
check('两行三列复制新增节点数',len(points)-1,5)
check('边缘距离转中心间距 mm',12+8,20)
dump('arithmetic-verification.json',dict(method='独立Python复数/atan2复算解释模型；不执行C#业务、设备或外部坐标实现',checks=checks,copy_example=points,all_passed=True))
print('Independent numeric checks:',len(checks))
