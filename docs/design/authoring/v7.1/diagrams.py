from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import math,html,shutil,json
OUT=Path(__file__).resolve().parents[4]/'output/design-publication-v7.1/figures'
OUT.mkdir(exist_ok=True)
C={'ink':'#162e43','muted':'#4d6070','line':'#a5b5c1','tu':'#edf0f3','sub':'#eaf4ed','mod':'#eaf1f9','bp':'#fff0df','blue':'#245b87','green':'#356d4a','orange':'#b65f17'}
class Canvas:
    def __init__(self,name,h):
        self.name=name;self.w=2400;self.h=h
        self.im=Image.new('RGB',(self.w,h),'white');self.d=ImageDraw.Draw(self.im)
        self.svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="2400" height="{h}" viewBox="0 0 2400 {h}"><rect width="100%" height="100%" fill="white"/>']
    def text(self,x,y,s,size=48,color=None,bold=False,anchor='mm'):
        f=ImageFont.truetype('C:/Windows/Fonts/msyhbd.ttc' if bold else 'C:/Windows/Fonts/msyh.ttc',size)
        bounds=self.d.textbbox((x,y),s,font=f,anchor=anchor)
        assert bounds[0]>=0 and bounds[1]>=0 and bounds[2]<self.w and bounds[3]<self.h,(self.name,s,bounds)
        self.d.text((x,y),s,font=f,fill=color or C['ink'],anchor=anchor)
        self.svg.append(f'<text x="{x}" y="{y}" fill="{color or C["ink"]}" font-family="Microsoft YaHei" font-size="{size}" font-weight="{700 if bold else 400}" text-anchor="{"middle" if anchor=="mm" else "start"}" dominant-baseline="central">{html.escape(s)}</text>')
    def rect(self,x,y,w,h,fill='white',stroke=None,width=3):
        self.d.rectangle((x,y,x+w,y+h),fill=fill,outline=stroke or C['line'],width=width)
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke or C["line"]}" stroke-width="{width}"/>')
    def line(self,pts,color=None,width=4,arrow=False,dash=False):
        color=color or C['muted']
        if dash:
            for (x1,y1),(x2,y2) in zip(pts,pts[1:]):
                length=math.hypot(x2-x1,y2-y1)
                for a in range(0,int(length),24):
                    b=min(a+12,length)
                    self.d.line([(x1+(x2-x1)*a/length,y1+(y2-y1)*a/length),(x1+(x2-x1)*b/length,y1+(y2-y1)*b/length)],fill=color,width=width)
        else:self.d.line(pts,fill=color,width=width)
        self.svg.append('<polyline points="'+' '.join(f'{x},{y}' for x,y in pts)+f'" fill="none" stroke="{color}" stroke-width="{width}"'+(' stroke-dasharray="12 12"' if dash else '')+'/>')
        if arrow:
            (x1,y1),(x,y)=pts[-2:];a=math.atan2(y-y1,x-x1);sz=23
            poly=[(x,y),(x-sz*math.cos(a-.45),y-sz*math.sin(a-.45)),(x-sz*math.cos(a+.45),y-sz*math.sin(a+.45))]
            self.d.polygon(poly,fill=color);self.svg.append('<polygon points="'+' '.join(f'{u},{v}' for u,v in poly)+f'" fill="{color}"/>')
    def dot(self,x,y,r=12,color=None):
        col=color or C['orange'];self.d.ellipse((x-r,y-r,x+r,y+r),fill=col);self.svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}"/>')
    def box(self,x,y,w,h,title,sub='',fill=None):
        self.rect(x,y,w,h,fill or C['mod'])
        self.text(x+w/2,y+h/2-(30 if sub else 0),title,52,bold=True)
        if sub:self.text(x+w/2,y+h/2+38,sub,44,color=C['muted'])
    def save(self):
        self.im.save(OUT/(self.name+'.png'),dpi=(360,360));(OUT/(self.name+'.svg')).write_text('\n'.join(self.svg)+'</svg>',encoding='utf-8')

def render():
    d=Canvas('p02-responsibility',1110)
    # Three horizontal responsibility bands, with product hierarchy as the centre.
    for y,label,col in [(30,'配方',C['sub']),(380,'运行',C['mod']),(750,'执行',C['bp'])]:
        d.rect(25,y,2350,285,col);d.text(130,y+142,label,55,bold=True)
    d.box(310,80,820,175,'产品配置','结构 · 示教坐标 · 工艺参与',C['sub'])
    d.box(1320,80,950,175,'工序定义','启用工序 · 工序名 · 焊点名',C['sub'])
    d.box(310,435,820,175,'TU → 基板 → 基岛 → 焊点','每层坐标与Info；焊点保存步骤',C['mod'])
    d.box(1320,435,950,175,'区段程式持有当前TU','来料 · 引用交接 · 几何刷新',C['mod'])
    d.box(310,805,820,175,'动作控制器','展开工作消息 · 解析当前对象',C['bp'])
    d.box(1320,805,950,175,'具体动作与任务','条件判断 · 执行 · 结果写回',C['bp'])
    d.line([(700,255),(700,435)],arrow=True);d.text(1030,345,'配置展开',44)
    d.line([(1795,255),(1795,340),(1200,340),(1200,720),(700,720),(700,805)],arrow=True)
    d.text(1820,340,'工序编排',44)
    d.line([(1320,520),(1130,520)],arrow=True)
    d.line([(720,805),(720,610)],arrow=True);d.text(1045,680,'查询／注入',42)
    d.line([(1130,895),(1320,895)],arrow=True)
    d.line([(2270,895),(2330,895),(2330,680),(1130,680),(1130,610)],arrow=True)
    d.text(1920,690,'读取位置／写回结果',44)
    d.text(1200,1060,'TuService辅助结构展开、索引换算、坐标建立与状态映射',46,color=C['muted'])
    d.save()

    d=Canvas('p04-work-order',1030)
    d.text(1200,55,'LeftDownToRight + Snake',56,bold=True)
    for y,items in [(180,[(4,6),(5,5),(6,4)]),(560,[(1,1),(2,2),(3,3)])]:
        for i,(idx,work) in enumerate(items):
            x=150+i*800;d.box(x,y,490,215,f'Index {idx}',f'WorkIndex {work}',C['sub'])
    d.line([(400,845),(2330,845),(2330,470),(400,470)],C['blue'],7,True)
    d.line([(890,845),(920,845)],C['blue'],7,True);d.line([(1710,845),(1740,845)],C['blue'],7,True)
    d.line([(1580,470),(1550,470)],C['blue'],7,True)
    d.text(1200,955,'工作路径：对象 1 → 2 → 3 → 6 → 5 → 4',52,bold=True)
    d.save()

    d=Canvas('p05-coordinate-chain',1080)
    steps=[(40,150,'焊点局部','(0, 0)'),(835,150,'基岛中','(10, 5)'),(1630,150,'基板中','(20, 10)'),(1630,650,'TU中','(40, 10)'),(835,650,'G0中','(90, 240)')]
    for x,y,t,v in steps:d.box(x,y,710,220,t,v,C['bp'] if t=='G0中' else C['mod'])
    d.line([(750,260),(835,260)],arrow=True);d.text(795,90,'A点平移',46)
    d.line([(1545,260),(1630,260)],arrow=True);d.text(1590,90,'岛2平移',46)
    d.line([(1985,370),(1985,650)],arrow=True);d.text(1985,515,'基板1平移 (20, 0)',46)
    d.line([(1630,760),(1545,760)],C['orange'],5,True)
    d.text(1200,565,'TU：旋转90°，再平移(100, 200)',49,bold=True)
    d.text(400,760,'长度单位 mm',46,color=C['muted'])
    d.text(1200,1000,'Transport到G0在本例中为零平移、零角度；各下层角度为0',47,color=C['muted'])
    d.save()

    d=Canvas('p06-coordinate-geometry',1500)
    # A true-to-scale G0 window: 80<=X<=120, 190<=Y<=250.
    def pt(x,y):return (320+(x-80)*17,1260-(y-190)*17)
    for x in range(80,121,10):
        a,b=pt(x,190),pt(x,250);d.line([a,b],C['line'],2);d.text(a[0],1320,str(x),43)
    for y in range(190,251,10):
        a,b=pt(80,y),pt(120,y);d.line([a,b],C['line'],2);d.text(240,a[1],str(y),43)
    d.line([pt(80,190),pt(123,190)],C['ink'],5,True);d.text(1160,1260,'G0 X',47)
    d.line([pt(80,190),pt(80,256)],C['ink'],5,True);d.text(320,80,'G0 Y',47)
    o=pt(100,200);a=pt(90,240);b=pt(92,239)
    d.line([o,pt(100,247)],C['blue'],6,True);d.text(820,210,'TU +X',48,C['blue'],True)
    d.line([o,pt(82,200)],C['blue'],6,True);d.text(460,1020,'TU +Y',48,C['blue'],True)
    d.line([o,pt(100,240),a],C['orange'],5,dash=True)
    d.dot(*o,14,C['blue']);d.dot(*a,15);d.dot(*b,13,C['green'])
    d.line([a,(1500,360)],C['orange'],3);d.text(1880,350,'A点 (90,240)',52,bold=True)
    d.line([b,(1500,530)],C['green'],3);d.text(1890,525,'加S1偏移后',49,C['green'],True);d.text(1890,595,'(92,239)',49,C['green'])
    d.line([o,(1490,900)],C['blue'],3);d.text(1880,880,'TU原点',49,C['blue'],True);d.text(1880,950,'(100,200)',49,C['blue'])
    d.text(1900,710,'局部点 (40,10)',48);d.text(1890,780,'旋转后 (−10,40)',48)
    d.text(1200,1440,'G0局部视窗；X、Y同比例，图中长度单位为mm',46,color=C['muted'])
    d.save()

    d=Canvas('p07-build-sequence',1130)
    d.box(40,60,590,175,'新建TU运行信息','建立新的根Info',C['tu'])
    d.box(900,60,590,175,'建立TU根坐标','连接机器父坐标',C['tu'])
    d.line([(630,148),(900,148)],arrow=True)
    d.line([(1490,148),(2010,148),(2010,350)],arrow=True)
    d.box(1280,350,1050,180,'常规：按模板与数量展开','坐标表 + 阵列与工作方向',C['sub'])
    d.box(70,350,1050,180,'异形：按节点树展开','节点位置 + 配置名称关联',C['mod'])
    d.line([(1195,235),(1195,290),(595,290),(595,350)],arrow=True)
    d.text(1200,425,'或',48)
    d.line([(595,530),(595,610),(1200,610)])
    d.line([(1800,530),(1800,610),(1200,610)],arrow=True)
    d.box(70,700,680,180,'映射工艺参与状态','ModifyMatter',C['bp'])
    d.box(860,700,680,180,'注入S2，再注入S1','只补缺失工序键',C['bp'])
    d.box(1650,700,680,180,'名称与工位偏移','系统参数构造再加偏移',C['bp'])
    # Connect the merge to the first operation, avoiding a false order.
    d.line([(1200,610),(410,610),(410,700)],arrow=True)
    d.line([(750,790),(860,790)],arrow=True);d.line([(1540,790),(1650,790)],arrow=True)
    d.text(1200,1020,'输出：对象树 + 当前坐标 + 独立运行信息 + 已注入的工序字典',49,bold=True)
    d.save()

    d=Canvas('p08-lifetimes',1230)
    xs=[650,1090,1560,2080]
    for x,t in zip(xs,['S1入口','S1完成','交接刷新','S2完成']):
        d.text(x,75,t,49,bold=True);d.line([(x,145),(x,1100)],C['line'],2,dash=True)
    for y,t in [(290,'运行对象'),(540,'当前几何'),(825,'焊点进度')]:d.text(190,y,t,52,bold=True)
    d.line([(460,290),(650,290)],C['muted'],16);d.text(520,215,'N0',44)
    d.line([(650,290),(2300,290)],C['blue'],20);d.dot(650,290,19,C['blue']);d.text(1430,220,'N1：S1创建后跨工位保留',49,C['blue'],True)
    d.rect(650,430,910,200,C['sub']);d.text(1100,490,'S1几何',49,bold=True);d.text(1100,565,'工位偏移 + 本阶段定位／测高',43)
    d.rect(1560,430,740,200,C['mod']);d.text(1920,490,'刷新后的新坐标',48,bold=True);d.text(1920,565,'原定位／测高标记清除',43)
    d.line([(650,790),(1090,790)],C['orange'],10);d.line([(1090,790),(2300,790)],C['green'],14)
    d.text(850,730,'D_A=false',44);d.text(1660,730,'D_A=true，交接保留',46,C['green'],True)
    d.line([(650,975),(2080,975)],C['orange'],10);d.line([(2080,975),(2300,975)],C['green'],14)
    d.text(1350,915,'T_A=false',44);d.text(2190,1050,'true',44,C['green'],True)
    d.text(1200,1170,'Refresh不清IsProduct，也不清S1／S2工序字典',48,bold=True)
    d.save()

    d=Canvas('p09-handover',1220)
    xs=[290,920,1540,2140]
    for x,t in zip(xs,['S1任务','输送任务／控制器','区段TU引用','S2任务']):
        d.text(x,65,t,47,bold=True);d.line([(x,125),(x,1125)],C['line'],3)
    d.line([(290,190),(920,190)],C['blue'],5,True);d.text(590,145,'允许向固晶段移送',47)
    d.rect(70,260,440,130,C['sub']);d.text(290,300,'Finish复位消息',47);d.text(290,360,'无需等移送结束',47)
    d.rect(640,260,560,130,C['tu']);d.text(920,300,'确认源有料、目标无料',47);d.text(920,360,'机械移送与检测完成',47)
    d.line([(920,465),(1540,465)],C['blue'],5,True);d.text(1230,420,'目标TU = 源TU',47)
    d.rect(1290,500,500,110,C['mod']);d.text(1540,555,'目标TU.Refresh',47,bold=True)
    d.line([(920,680),(1540,680)],C['blue'],5,True);d.text(1230,635,'源TU清空；更新状态',47)
    d.text(920,745,'保存；返回Success',47)
    d.line([(920,850),(2140,850)],C['green'],5,True);d.text(1510,805,'输送任务发送固晶来料完成信号',47)
    d.rect(1875,930,495,170,C['bp']);d.text(2120,970,'补充S2键',47);d.text(2120,1020,'IsProduct=true',47);d.text(2120,1070,'保留原TU',47)
    d.text(1200,1180,'时间向下；机械完成后才交接引用，随后通知S2进入产品处理',46,color=C['muted'])
    d.save()

    d=Canvas('p10-progress',820)
    d.text(590,55,'两侧动作控制器',55,bold=True);d.text(1810,55,'当前TU中的焊点A',55,bold=True)
    for x in [50,1280]:d.rect(x,130,1060,520,'white',C['line'])
    for y,t in [(200,'S1工作消息：D_A'),(355,'S2工作消息：T_A')]:
        d.rect(110,y,940,100,C['mod']);d.text(580,y+50,t,49,bold=True)
    d.text(580,525,'Finish → Finished=false',47,C['blue']);d.text(580,595,'为下一轮编排复位',45)
    d.rect(1340,200,940,100,C['sub']);d.text(1810,250,'S1步骤  { D_A : true }',49,bold=True)
    d.rect(1340,355,940,100,C['sub']);d.text(1810,405,'S2步骤  { T_A : true }',49,bold=True)
    d.text(1810,525,'Finish不修改这两条记录',47,C['green']);d.text(1810,595,'其他焊点有自己的字典',45)
    d.line([(1110,250),(1280,250)],C['orange'],5,True);d.text(1200,740,'动作写回焊点步骤；任务标记当前消息完成',49,bold=True)
    d.save()

def render_layout_models():
    d=Canvas('p11-layout-models',1110)
    d.text(600,60,'常规产品',60,bold=True);d.text(1800,60,'异形产品',60,bold=True)
    d.text(600,135,'同一模板重复展开',48);d.text(1800,135,'每个分支读取自己的节点',48)
    d.line([(1200,30),(1200,1030)],C['line'],3)
    def island(x,y,index):
        d.rect(x,y,240,170,C['mod']);d.text(x+120,y+40,'岛 '+str(index),48,bold=True)
        for dx,label in [(65,'A'),(175,'B')]:
            d.dot(x+dx,y+115,34,C['orange']);d.text(x+dx,y+115,label,44,bold=True)
    for side in range(2):
        x=40+side*1200
        for row,y in enumerate([220,610]):
            d.rect(x,y,1120,330,C['sub']);d.text(x+560,y+50,'基板 '+str(row+1),52,bold=True)
            positions=[x+90,x+440,x+790] if side==0 or row==1 else [x+160,x+720]
            for i,pos in enumerate(positions,1):island(pos,y+110,i)
    d.text(600,1015,'两块基板各3岛，共12个焊点',46,bold=True)
    d.text(1800,1015,'两块基板分别2岛和3岛，共10个焊点',46,bold=True)
    d.save()

if __name__=='__main__':
    render()
    render_layout_models()
    existing=Path('D:/agent_project/code_agent/docs/design/transport-unit/figures')
    shutil.copyfile(existing/'p01-product-map.png',OUT/'p01-product-map.png')
    shutil.copyfile(existing/'p03-config-instance.png',OUT/'p03-config-instance.png')
    print('11 illustration plates ready')
