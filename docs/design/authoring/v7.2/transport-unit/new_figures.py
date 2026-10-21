"""Precise ownership and lifecycle diagrams; raster plus editable SVG."""
from diagrams import Canvas,C
from PIL import ImageFont
def box(d,x,y,w,h,lines,fill=None):
    d.rect(x,y,w,h,fill or C['mod'])
    for i,s in enumerate(lines):
        size=51 if i==0 else 46
        f=ImageFont.truetype('C:/Windows/Fonts/msyhbd.ttc' if i==0 else 'C:/Windows/Fonts/msyh.ttc',size)
        assert d.d.textbbox((0,0),s,font=f)[2] < w-35,(d.name,s,w)
        d.text(x+w/2,y+h/2+(i-(len(lines)-1)/2)*68,s,size,bold=i==0)
def arr(d,pts,color=None,dash=False):d.line(pts,color,5,True,dash)

d=Canvas('p21-clear-scope',1040)
titles=['整线清空','只清点胶段','只清固晶段']
xs=[820,1440,2060]
for x,t in zip(xs,titles):d.text(x,80,t,58,bold=True)
regions=['上料段','点胶段','固晶段','待下料段','下料段']
for j,t in enumerate(regions):
    y=230+j*135;d.text(240,y,t,54,bold=True)
    for i,x in enumerate(xs):
        changed=i==0 or i==1 and j==1 or i==2 and j==2
        if changed:d.dot(x,y,25,C['orange']);d.text(x+90,y,'清空',46,anchor='lm')
        else:d.rect(x-23,y-23,46,46,'white');d.text(x+90,y,'保留',46,anchor='lm')
    d.line([(80,y+65),(2330,y+65)],C['line'],2)
d.text(1200,960,'清空 = TU 设 null ＋ 有料状态设 NoMaterial',52,bold=True)
d.save()

d=Canvas('p22-mapping-ownership',1240)
d.text(1200,65,'配方参与范围与本产品进度分别维护',58,bold=True)
box(d,70,190,660,210,['新配方 Mapping','窗口样本TU'],C['tu'])
box(d,875,190,660,210,['OtherConfig','内存参与状态'],C['sub'])
box(d,1680,190,650,210,['后续新建TU','ModifyMatter读取'],C['mod'])
arr(d,[(730,295),(875,295)]);arr(d,[(1535,295),(1680,295)])
d.text(1200,490,'关闭且 IsChange → SaveInformation',48)
box(d,70,690,660,210,['生产 Mapping','区段当前TU'],C['mod'])
box(d,875,690,660,210,['本产品参与状态','焊点完成字典'],C['bp'])
box(d,1680,690,650,210,['后续生产判断','读取当前记录'],C['sub'])
arr(d,[(730,795),(875,795)]);arr(d,[(1535,795),(1680,795)])
d.text(1200,1015,'配方界面关闭且任一区段有TU时，可进入清空确认',48)
d.text(1200,1120,'确认、机器状态与保存结果分别影响实际出口',49,bold=True)
d.save()

d=Canvas('p23-teach-writes',1290)
cols=[315,1080,1940]
for x,t in zip(cols,['示教层级','窗口先改运行坐标','调用方继续写入']):d.text(x,65,t,53,bold=True)
rows=[('TU','TU','TU配置角'),('基板','TU','所选基板角／全板配置角'),('基岛','所选基板','所选基岛角／全岛配置角'),('焊点','所选基岛','单焊点配置角')]
for j,(a,b,c) in enumerate(rows):
    y=180+j*210
    box(d,70,y,490,140,[a],C['tu']);box(d,725,y,710,140,[b],C['mod']);box(d,1600,y,730,140,[c],C['sub'])
    arr(d,[(560,y+70),(725,y+70)]);arr(d,[(1435,y+70),(1600,y+70)])
d.text(1200,1080,'在线通过后，窗口 Save 先于调用方后续复制',50,bold=True)
d.text(1200,1190,'后续PR取消不提供跨对象与配置的统一回滚',49,color=C['orange'])
d.save()

d=Canvas('p24-irregular-edit',1120)
box(d,80,80,660,210,['配置节点编辑','新增／删除／复制'],C['tu'])
box(d,880,80,660,210,['编辑控件 Init','重排ID并刷新视图'],C['sub'])
box(d,1680,80,640,210,['配方保存','节点树与公共配置'],C['sub'])
arr(d,[(740,185),(880,185)]);arr(d,[(1540,185),(1680,185)])
box(d,80,640,940,220,['旧运行TU','保留既有后代与关联节点'],C['bp'])
box(d,1380,640,940,220,['下一次新建TU','沿当前 DownConfigs 展开'],C['mod'])
arr(d,[(2000,290),(2000,640)])
d.text(470,455,'编辑界面重画',48,bold=True)
d.text(470,530,'不自动改写旧运行树',48,color=C['orange'])
d.text(1200,1000,'配置节点 ID、运行 Index 与节点对象引用承担不同职责',50,bold=True)
d.save()

d=Canvas('p25-compensate-lifecycle',1350)
box(d,70,60,1010,190,['补偿模式取得来料','创建字符串参数 Ntest'],C['tu'])
box(d,70,380,1010,180,['向 Ntest 注入S2步骤'])
arr(d,[(575,250),(575,380)])
box(d,70,720,1010,210,['Enable 且配置输送','IsProduct仍为false'],C['bp'])
arr(d,[(575,560),(575,720)])
box(d,70,1080,1010,200,['再创建 System2 参数 Ns2','置 IsProduct = true'],C['sub'])
arr(d,[(575,930),(575,1080)])
box(d,1370,650,960,230,['Enable但未配置输送','继续使用 Ntest','不自动加S2构造偏移'],C['mod'])
arr(d,[(1080,465),(1200,465),(1200,765),(1370,765)])
box(d,1370,1040,960,230,['Enable = false','不进入后续生产创建分支'],C['tu'])
arr(d,[(1200,765),(1200,1155),(1370,1155)])
d.text(1845,150,'Ntest 与 Ns2 是两份对象',49,bold=True)
d.text(1845,255,'新Info不复制旧产品记录',47)
d.text(1845,360,'每次新建均重新建立步骤',47)
d.save()

d=Canvas('p26-node-reference',930)
box(d,70,80,970,220,['原配置节点 N','创建时关联运行对象 B'],C['sub'])
box(d,1360,80,970,220,['另一份配置节点 N′','相同名称／ID／ConfigName'],C['tu'])
box(d,70,540,970,220,['用 N 反查','返回关联的 B'],C['mod'])
box(d,1360,540,970,220,['用 N′ 反查','未命中则抛异常'],C['bp'])
arr(d,[(555,300),(555,540)]);arr(d,[(1845,300),(1845,540)],C['orange'])
d.text(1200,425,'接口比较节点对象引用',57,bold=True)
d.text(1200,850,'名字与ID相同，不意味着是同一节点对象',50,bold=True)
d.save()
