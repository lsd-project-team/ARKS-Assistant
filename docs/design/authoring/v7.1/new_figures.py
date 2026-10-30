from pathlib import Path
import math
import diagrams
from diagrams import Canvas,C
BASE=Path(__file__).resolve().parents[4]/'output/design-publication-v7.1'
def target(book):diagrams.OUT=BASE/book/'figures'
def block(d,x,y,w,t,s,col=None):d.box(x,y,w,180,t,s,col)

target('transport-unit')
d=Canvas('p19-divide-lifecycle',1120)
d.text(1200,65,'分段保持同一TU 机械移段与几何刷新分别生效',53,bold=True)
for x,t,s in [(60,'第一组消息','N1  D.X = 102'),(860,'移段并通知','N1  D.X = 142'),(1660,'第二组消息','N1  步骤继续累积')]:block(d,x,220,680,t,s,C['sub'])
d.line([(740,310),(860,310)],arrow=True);d.line([(1540,310),(1660,310)],arrow=True)
d.text(400,470,'集合外消息',43);d.text(1200,470,'InteractiveAction + 输送',43);d.text(2000,470,'集合内消息',43)
d.text(1200,570,'位置标记 true → false   增量 +40mm   不执行Refresh',47,bold=True)
block(d,160,760,930,'搜索确认回第一段','D.X减40 → 102  定位标记保留',C['mod'])
block(d,1300,760,930,'Refresh重建几何','配置X = 100  几何标记清除',C['bp'])
d.line([(2340,400),(2355,400),(2355,675),(625,675),(625,760)],arrow=True,dash=True)
d.line([(1765,675),(1765,760)],arrow=True,dash=True)
d.text(1200,1030,'单位mm  示例配置X=100  S1偏移=2  DistanceToRight=40',44,color=C['muted']);d.save()

d=Canvas('p20-irregular-address',1000)
d.text(1200,65,'实际节点树决定数量 配置名称决定工艺关联',53,bold=True)
d.box(80,160,920,150,'TU N1','下层两块基板  总计13个对象')
d.box(80,360,430,150,'基板1','2个岛 / 2个A点',C['sub']);d.box(570,360,430,150,'基板2','3个岛 / 3个A点',C['sub'])
d.line([(540,310),(540,335),(295,335),(295,360)],arrow=True);d.line([(540,335),(785,335),(785,360)],arrow=True)
d.rect(80,650,920,160,C['bp']);d.text(540,700,'各A点可引用同一个ConfigName',43,bold=True);d.text(540,765,'Info与工序记录仍归各自运行节点',40)
d.line([(295,510),(295,650)],arrow=True,dash=True);d.line([(785,510),(785,650)],arrow=True,dash=True)
d.text(1725,200,'基板1 / 基岛2 / A',52,bold=True)
for y,s in [(335,'TU (100,200) + 基板1 (20,0)'),(445,'+ 岛2 (10,5) + A (2,1)'),(560,'G0 = (132,206) mm'),(710,'基板定位 +0.1X → (132.1,206)'),(840,'Refresh → (132,206)')]:d.text(1700,y,s,43,color=C['blue'] if y==560 else None,bold=y==560)
d.text(1200,930,'树图和坐标为说明模型  不按实物比例绘制',43,color=C['muted']);d.save()

target('correction-process')
d=Canvas('c21-candidate-validity',1260)
d.text(1200,65,'候选存在 允许取料 已取走分属不同阶段',53,bold=True)
for y,label,vals in [(230,'Nine',[('缓存或新识别','选取候选'),('移到Mark中心','再运行PR刷新邻片'),('移动取料位','本次搜索成功')]),(690,'WaferMap',[('Map提供候选','本目录外的寻路接口'),('标准单点定位','跳板 / isSkip则继续选取'),('有效候选','本次搜索成功')])]:
    d.text(145,y+90,label,43,bold=True)
    for j,(t,s) in enumerate(vals):block(d,340+j*690,y,620,t,s,C['sub'] if j==2 else C['mod'])
    for x in [960,1650]:d.line([(x,y+90),(x+70,y+90)],arrow=True)
d.line([(1310,870),(1310,950),(600,950),(600,870)],arrow=True,color=C['orange'])
d.text(680,1000,'跳过当前候选 重走选择',42,color=C['orange'])
d.text(1200,1130,'成功后由供料任务发允许取料信号  取后RefreshMap另行记忆与更新',43,bold=True);d.save()

d=Canvas('c22-mirror-angle',1160)
d.text(1200,65,'普通上视先完成实际旋转 后续目标使用新的当前T',53,bold=True)
labels=['普通拍照准备','首次识别后相对转动','旋转后当前T','保存角度','贴装目标T']
for x,t in [(900,'非镜像'),(1820,'镜像')]:d.text(x,190,t,50,bold=True)
for i,(a,b) in enumerate([('29°','29°'),('2+5+1 = 8°','2+5+180−1 = 186°'),('37°','215°'),('−(5+1) = −6°','−(5+1) = −6°'),('37−6+5+1 = 37°','215−6+5+1 = 215°')]):
    y=310+i*145;d.text(270,y,labels[i],40,bold=True)
    for x,s in [(900,a),(1820,b)]:d.text(x,y,s,46,C['blue'] if i in [2,4] else None,bold=i in [2,4])
    if i<4:
        for x in [900,1820]:d.line([(x,y+38),(x,y+98)],arrow=True)
d.text(1200,1100,'说明输入 PR=3°  Align=20°  b=5°  h=1°  a=2°  不自行折算轴角范围',41,color=C['muted']);d.save()

d=Canvas('c23-manual-target',1070)
d.text(1200,65,'同一芯片偏移在两条贴片入口中具有不同使用表达式',51,bold=True)
for x,t,col in [(620,'手动PlacementTest',C['bp']),(1810,'生产上视贴装',C['sub'])]:
    d.rect(x-525,180,1050,710,col);d.text(x,255,t,52,bold=True)
for x,lines in [(620,['q = (o.X, o.Y, 0)','SelfPosToG0(q) + o','局部转换和全局追加均使用o','例：原点(100,200)，o=(0.1,−0.2)','输出 (100.2,199.6) mm']),(1810,['产品硬补偿 → G0目标','按剩余角旋转o后追加','配置硬补偿与芯片偏移分别产生','例：剩余角=0，其余补偿=0','输出 (100.1,199.8) mm'])]:
    for i,line in enumerate(lines):d.text(x,370+i*105,line,41 if i in [2,3] else 46,bold=i==4)
d.text(1200,990,'本例父链角为0且轴转换取恒等输入  Z另由高度流程计算',44,color=C['muted']);d.save()
print('Five source-backed engineering plates rendered as SVG and PNG')
