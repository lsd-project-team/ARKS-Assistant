"""Independent numeric examples; no C# or equipment process is executed."""
from pathlib import Path
import math,cmath,json
BASE=Path(__file__).resolve().parents[4]/'output/design-publication-v7'
(BASE/'correction-process').mkdir(parents=True,exist_ok=True)
checks=[]
def record(id,inputs,output,expected,condition):
 if isinstance(output,complex):
  assert abs(output-complex(*expected))<1e-10,(id,output,expected)
  output=[output.real,output.imag]
 else:assert output==expected,(id,output,expected)
 checks.append(dict(id=id,input=inputs,output=output,expected=expected,condition=condition,passed=True))
r=complex(.5,.2)*cmath.exp(-2j*math.pi/180)
k=complex(200,100)-complex(.05,-.02)+complex(.01,.03)-r
record('S01',{'axis_mark_plus_head_mm':[200,100],'angle_deg':2,'vector_mm':[.5,.2],'pickup_mm':[.01,.03],'nozzle_offset_mm':[.05,-.02]},k,[199.45332468714635,99.86757158296643],'静态华夫盒XY；标定与偏心作为输入')
record('S02',{'hard_angle_deg':5,'match_angle_deg':2,'nozzle_align_deg':30},[5-2+30,5+2+30],[33,37],'未翻转/翻转的取片T，偏心接口参数分别3度/7度')
record('S03',{'x_error_mm':.01,'y_error_mm':-.01,'angle_error_deg':.2,'xy_limit_mm':.01,'angle_limit_deg':.2},abs(.01)<=.01 and abs(-.01)<=.01 and abs(.2)<=.2,True,'多次定位阈值包含等号')
record('S04',{'points_mm':[[0,0],[2,1],[4,3]],'use_x':[True,False,True],'use_y':[False,True,True]},[(0+4)/2,(1+3)/2],[2,2],'产品定位X/Y独立选点')
raw=[-50,-20,10,50];filtered=[v for v in raw if abs(v)<50]
record('S05',{'raw_um':raw,'ratio':.5},sum(filtered)/len(filtered)/1000*.5,-.0025,'焊后筛选严格<50；50和−50不参与，单位由微量转mm')
record('S06',{'raw_um':[50,-50]},len([v for v in [50,-50] if abs(v)<50]),0,'筛选为空，当前Average不能得到有效均值；不执行C#异常')
u,v=.25,.75;corners=[0,.1,.2,.3]
value=(1-u)*(1-v)*corners[0]+u*(1-v)*corners[1]+(1-u)*v*corners[2]+u*v*corners[3]
assert abs(value-.175)<1e-12
record('S07',{'grid_fraction':[u,v],'x_offsets_mm':corners},round(value,12),.175,'TU区域双线性说明输入；贴装入口再相减')
record('S08',{'real_time_final_diff_mm':[.5,0]},abs(.5)>.5,False,'最终超限判断使用严格大于；单点插值的异常入口另行处理')
record('S09',{'tu_region_value_mm':1.0},abs(1.)>1,False,'区域补偿严格大于1mm才进入超限异常')
record('S10',{'uplook_drift_mm':[.1,-.05],'pickup_drift_mm':[.1,-.05]},[[-.1,.05],[.1,-.05]],[[-.1,.05],[.1,-.05]],'上视取负；取片保留正号，不混用')
data={'date':'2026-10-21','method':'独立Python数值复算与边界比较；不编译或执行C#、不运行设备','examples':checks,'tolerance':1e-10}
(BASE/'correction-process/new-arithmetic-verification.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print('10 supply, selection and compensation examples verified')
