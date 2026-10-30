"""主流程用同一产品与芯片画前后变化，可选章节复用原有几何。"""
import re
import math
from common import *
from case_data import VALUES,display

class StoryCanvas(Canvas):
    def text(self,x,y,text,size=48,fill=INK,bold=False,anchor='mm'):
        # 正文图只保留三位小数；精确数值另附计算索引。
        text=re.sub(r'(?<![\w.])−?\d+\.\d{4,}',lambda m:format(float(m[0].replace('−','-')),'.3f').replace('-','−'),str(text))
        return super().text(x,y,text,size,fill,bold,anchor)

def heading(c,title,sub=''):
    c.text(1200,70,title,55,bold=True)
    if sub:c.text(1200,965,sub,47,GRAY)

def product(c,x,y,w=870,h=300,selected=True):
    c.rect(x,y,w,h,PALE,GREEN,5,12)
    # 两块基板，每板三个岛；只标当前A点，保持全书同一结构。
    for row in range(2):
        for col in range(3):
            left=x+28+col*(w-44)/3;top=y+23+row*(h-33)/2
            iw=(w-100)/3;ih=(h-76)/2
            c.rect(left,top,iw,ih,'white',GREEN,3)
            for j in range(2):
                px=left+iw*(.32+.38*j);py=top+ih*.52
                c.circle(px,py,9,GRAY)
                if selected and row==0 and col==1 and j==0:
                    c.circle(px,py,26,'white',BLUE,6);c.circle(px,py,10,BLUE)
    return x+28+(w-44)/3+(w-100)/3*.32,y+23+(h-76)/2*.52

def split(c,left,right):
    c.text(590,190,left,53,BLUE,True);c.text(1810,190,right,53,BLUE,True)
    c.line([(1200,160),(1200,860)],LINE,3)

def tu_journey(c):
    old_figures.route(c)
    c.text(1200,165,'实物P1向前走 同一运行记录N1随区段交接',51,BLUE,True)

def tu_new_record(c):
    heading(c,'先有实物P1 再建立本轮运行记录N1','N1从当前配方建立  每个位置保存自己的进度')
    product(c,90,300,880,300);c.text(530,720,'P1  2板 × 3岛 × A/B',51,GREEN,True)
    c.arrow(1010,460,1310,460)
    ledger(c,1400,220,'N1中的当前A点',[('地址','1 / 2 / A'),('点胶','未完成'),('固晶','未完成')],880)

def tu_local_chain(c):
    numeric_steps(c,[('A在基岛内',['(10, 5)','加基岛 (10, 5)','基板内A = (20, 10)']),('再加基板1',['基板位置 (20, 0)','TU内A = (40, 10)']),('再加TU原点',['TU原点 (100, 200)','G0 A = (140, 210)'])],
        '跟住同一个A点  主例各层角度先取0','局部位置逐层换到机器全局G0  单位mm')

def tu_offset_before_after(c):
    heading(c,'S1工位偏移让整份P1的当前位置变化','蓝圈是同一个A点  位移方向为示意  单位mm')
    split(c,'配置位置','加入S1偏移后')
    product(c,100,340);product(c,1360,300)
    c.lines(560,750,['TU (100, 200)','A (140, 210)'],52,gap=96)
    c.lines(1800,710,['TU (102, 199)','A (142, 209)'],52,gap=96)
    c.arrow(1050,480,1310,440);c.text(1200,575,'+(2, −1)',44,ORANGE,True)

def tu_height_before_after(c):
    heading(c,'基板1测高差为 +0.12毫米','高度仅作夸张示意  不表示焊头实际工作高度')
    split(c,'加测高差之前','加测高差之后')
    for x,yy,z in [(590,560,'0'),(1810,455,'0.12')]:
        c.line([(x-430,560),(x+430,560)],LINE,4,False,True)
        c.rect(x-420,yy,840,65,PALE,GREEN,5);c.circle(x,yy,20,BLUE)
        c.text(x,yy-80,'基板1上的A点',50,BLUE)
        c.text(x,800,f'G0 (142, 209, {z})',54)
    c.arrow(2260,560,2260,455,ORANGE)
    c.text(2170,655,'+0.12',45,ORANGE,True)

def tu_dispense_scene(c):
    heading(c,'本次A点点胶成功以后 只写当前A点进度','先执行本次动作  再写成功记录')
    ax,ay=product(c,80,490,1000,300);nozzle(c,ax,ay-100)
    c.line([(ax,ay-90),(ax,ay-20)],ORANGE,6,True)
    c.text(580,870,'P1  当前A点 G0 (142, 209, 0.12)',45,GREEN,True)
    c.arrow(1120,530,1340,530)
    ledger(c,1420,240,'N1中的当前A点',[('点胶','完成'),('固晶','未完成'),('其余焊点','各自记录')],850)

def tu_handover_scene(c):
    heading(c,'实物P1从S1移到S2 同一个N1交给目标','正常路径：目标接收N1 → 刷新 → 清源 → 保存 → 通知')
    for x,label in [(90,'S1点胶'),(1380,'S2固晶')]:
        c.text(x+450,170,label,55,bold=True);conveyor(c,x,620,900)
    product(c,1440,380,780,230);c.text(1820,780,'实物P1',51,GREEN,True)
    c.arrow(1030,490,1350,490);c.text(1170,350,'移送',46)
    c.box(140,245,800,150,'源入口最终清空',fill=LIGHT)
    c.text(1810,295,'目标持有原N1',49,BLUE,True)

def tu_refresh_story(c):
    heading(c,'交接刷新重建位置 保留当前A点工序','这不是新建另一棵产品树  仍是N1中的同一个A点')
    split(c,'在S1交接之前','到S2刷新之后')
    for x,position in [(590,'(142, 209, 0.12)'),(1810,'(140, 210, 0)')]:
        product(c,x-440,290,880,265)
        c.text(x,650,'A G0 '+position,52,BLUE,True)
        c.text(x,775,'点胶完成  固晶未完成',51,GREEN,True)
    c.arrow(1070,630,1320,630)

def tu_s2_bridge(c):
    heading(c,'要把C1贴到A点 需要合并两路信息','TU册先讲当前产品记录  纠偏册从这一步展开')
    product(c,75,300,900,310);c.text(520,735,'产品P1：找到当前A点',50,GREEN,True)
    nozzle(c,1830,350,True,8);camera(c,1830,640,True)
    c.text(1830,820,'芯片C1：找到真实中心',50,ORANGE,True)
    c.line([(1010,450),(1200,450),(1200,840)],GREEN,6,True)
    c.line([(1650,540),(1340,540),(1340,840)],ORANGE,6,True)
    c.text(1250,895,'形成贴装目标',50,BLUE,True)

def tu_bond_scene(c):
    heading(c,'本次C1固晶成功以后 写当前A点固晶完成','一个A点完成 不等于整份P1全部完成')
    ax,ay=product(c,80,470,1000,300);chip(c,ax,ay,110);nozzle(c,ax,ay-100)
    c.text(580,860,'C1贴在P1的当前A点',52,ORANGE,True)
    c.arrow(1120,530,1340,530)
    ledger(c,1420,240,'N1中的当前A点',[('点胶','完成'),('固晶','完成'),('其他焊点','各自继续')],850)

def tu_full_replay(c):
    heading(c,'回看P1的一轮 位置和进度分别跟踪','固晶中的产品定位和芯片补偿 继续见纠偏册')
    labels=['建立N1','A点点胶后','交接刷新后','A点固晶后']
    xs=[320,900,1480,2060]
    for x,label,d,t,pos in zip(xs,labels,['未完成','完成','完成','完成'],['未完成','未完成','未完成','完成'],['(140,210)','(142,209,0.12)','(140,210,0)','见纠偏目标']):
        c.text(x,220,label,48,BLUE,True);product(c,x-250,340,500,200)
        c.lines(x,650,[pos,'点胶 '+d,'固晶 '+t],44,gap=96)
        if x<2000:c.arrow(x+265,430,x+305,430)

def tu_divide_story(c):
    numeric_steps(c,[('第一段',['配置X100 + S1偏移2','TU X = 102']),('移段40毫米',['仍是同一个N1','TU X = 142']),('后续两种动作',['回移40：X回102','刷新：X回配置100'])],
        '分段点胶看TU整体X  不是A点X','正常移段保留工序与对象  不统一清定位和测高')

def tu_change_recipe(c):
    heading(c,'配方改变后 先判断旧树还能不能匹配','改变结构或节点关联时 仅刷新坐标不够')
    split(c,'只改位置且结构匹配','岛数 工序或节点关联改变')
    product(c,130,340);product(c,1360,340)
    c.text(560,760,'沿用当前树 刷新坐标',51,BLUE,True)
    c.text(1800,760,'重新建立匹配的运行树',51,ORANGE,True)

def tu_mapping_owners(c):
    two_lanes(c,['配方Mapping','窗口样本','后续参与规则'],['生产Mapping','区段当前P1','当前点的参与和工序'],
        '配方画面改变后续产品规则','生产画面改变当前产品记录')

def co_journey(c):
    heading(c,'从同一个A点出发 看C1怎样贴准它','本册主例：静态华夫盒 + 快速单点上视')
    product(c,70,200,850,280);c.text(490,580,'产品P1 / A点',50,GREEN,True)
    for x,title,kind in [(450,'找C1','tray'),(1150,'快速上视','chip'),(1870,'贴到A点','bond')]:
        c.text(x,650,title,49,ORANGE,True)
        if kind=='tray':
            c.rect(x-210,785,420,125,PALE,GREEN,4);chip(c,x,845,90)
        elif kind=='chip':nozzle(c,x,825,True);camera(c,x+190,865,True)
        else:
            ax,ay=product(c,x-210,785,420,125);chip(c,ax,ay,65)
    c.line([(970,330),(1870,330),(1870,595)],GREEN,6,True)
    c.text(1550,250,'产品位置这一支',49,GREEN,True)
    c.arrow(710,820,880,820,ORANGE);c.arrow(1430,820,1600,820,ORANGE)

def co_product_story(c):
    heading(c,'产品定位只改变P1这一侧 本例不增加角度','从TU册的交接基础位置 继续到本次定位结果')
    split(c,'交接刷新后','本次产品定位后')
    product(c,90,360);product(c,1360,320);camera(c,1820,265)
    c.text(560,770,'A (140, 210)',57,BLUE,True)
    c.text(1800,770,'A (140.2, 209.9)',57,BLUE,True)
    c.text(1200,880,'本例平移 +(0.2, −0.1) 毫米',49,ORANGE,True)

def co_tray_story(c):
    heading(c,'C1仍在华夫盒槽内 先由下视相机识别','相机像素 → 标定转换 → 物理参考位置  不直接拿像素移动')
    c.rect(80,460,1030,340,PALE,GREEN,5)
    for i in range(3):
        for j in range(2):chip(c,260+i*340,550+j*170,140,2 if i==1 and j==0 else 0)
    camera(c,600,275);c.circle(600,550,105,'white',BLUE,6);chip(c,600,550,140,2)
    c.text(600,865,'本次只跟中间这一颗C1',50,ORANGE,True)
    c.lines(1780,260,['转换并加头相机差后','Mark轴参考 (200,100) mm','Mark到中心 (0.5,0.2) mm','C1识别角 2°'],48,gap=150)

def co_pick_angle_story(c):
    heading(c,'本例不翻转  取片T = 5 − 2 + 30 = 33°','识别角 硬角补偿和吸嘴校准角共同形成轴角')
    chip(c,580,555,360,2);camera(c,580,270)
    c.text(580,830,'槽内C1识别角2°',53,ORANGE,True)
    nozzle(c,1810,470,True,33);c.text(1810,770,'本次取片轴T33°',53,ORANGE,True)
    c.arrow(1070,520,1330,520)
    c.text(1810,880,'本角度下偏心给(0.05,−0.02)',45,GRAY)

def co_pick_xy_story(c):
    numeric_steps(c,[('Mark换算起点',['(200, 100)','减偏心 (0.05, −0.02)']),('换到芯片中心',['加取料量 (0.01, 0.03)','减转过角的中心向量','约 (0.507, 0.182)']),('取片目标',['XY约 (199.453, 99.868)','T = 33°','Z按取片高度分支'])],
        '仍在同一静态华夫盒路线  单位毫米','中间量显示到三位小数  实际复算使用未舍入值')

def co_photo_story(c):
    heading(c,'取片之后  带着C1转到上视拍照准备角','选择快速单点  本例几何PR正常拍1次')
    split(c,'已取起C1  当前T33°','拍照准备后  当前T30°')
    nozzle(c,590,460,True,33);nozzle(c,1810,460,True,30);camera(c,1810,760,True)
    c.arrow(1040,470,1350,470)
    c.text(590,790,'C1仍在同一吸嘴上',50,ORANGE,True)
    c.text(1810,890,'准备角 = 示教0° + 校准30°',46,BLUE,True)

def co_measure_story(c):
    heading(c,'先识别C1的Mark 再换到芯片中心','图形位置和小角度作了放大  数值单位毫米')
    c.rect(100,210,1040,620,LIGHT,BLUE,5)
    c.line([(620,240),(620,800)],LINE,4,False,True);c.line([(130,520),(1110,520)],LINE,4,False,True)
    chip(c,720,500,380,8);c.circle(600,415,15,BLUE)
    c.text(340,335,'识别Mark',47,BLUE,True);c.line([(420,355),(590,410)],BLUE,4,True)
    c.text(880,675,'C1中心',47,ORANGE,True);c.line([(830,630),(730,515)],ORANGE,4,True)
    c.lines(1800,260,['标定位移 (0.12, −0.08)','参考差 (0.02, −0.01)','中心向量 (0.5, 0.2)','识别2° − 示教1° = 1°'],48,gap=155)

def co_saved_story(c):
    heading(c,'保存的是当前A点这次C1的偏移','先保存结果  贴装入口随后读取并使用')
    nozzle(c,550,420,True,30);camera(c,550,730,True)
    c.text(550,885,'当前T仍为30°',51,ORANGE,True)
    c.arrow(1000,510,1300,510)
    c.text(1840,220,'当前A点的数据',54,bold=True)
    for i,(name,value) in enumerate([('当前位置','(140.2,209.9)'),('本次芯片偏移','(−0.363,−0.281)'),('本次角度记录','2°')]):
        y=300+i*132;c.rect(1380,y,920,132)
        c.text(1422,y+66,name,43,anchor='lm')
        c.text(2055,y+66,value,43,BLUE)

def co_rotate_story(c):
    heading(c,'目标T33° − 当前T30° = 剩余3°','图中夹角夸张示意  不按比例测量')
    c.line([(650,260),(650,830)],LINE,4);c.line([(280,550),(1080,550)],LINE,4)
    c.circle(650,550,14,GRAY)
    c.arrow(650,550,330,730,BLUE);c.arrow(650,550,365,820,ORANGE)
    c.text(500,305,'同一段偏移随剩余角转向',49,BLUE,True)
    c.lines(1800,260,['保存偏移约','(−0.363, −0.281)','按剩余3°旋转','追加量约','(−0.348, −0.300)'],51,gap=115)

def co_target_story(c):
    heading(c,'A点位置 + 转过剩余角的芯片偏移','本例其他XY补偿0  轴转换恒等  轴后实时量0')
    c.box(100,200,910,230,'产品P1的A点','(140.2, 209.9) mm',PALE)
    c.box(100,555,910,230,'本次C1追加量','约(−0.348, −0.300) mm',WARM)
    c.line([(1050,315),(1250,315),(1250,510),(1390,510)],GREEN,6,True)
    c.line([(1050,670),(1250,670),(1250,540)],ORANGE,6,True)
    c.box(1430,320,870,400,'本例说明目标','XY约(139.852, 209.600)\nT = 33°\nZ另按高度分支计算',LIGHT)

def co_replay_story(c):
    heading(c,'回看C1从华夫盒到当前A点的完整一轮','产品A点定位后为(140.2,209.9)  从头到尾没有换成另一个点')
    flow(c,['取起C1','快速单点上视','计算贴装目标','贴装成功'],['XY约199.453 / 99.868','当前T30° 保存偏移','XY约139.852 / 209.600','A点固晶完成'],y=280)
    for x,text in [(330,'取片T33°'),(910,'照片准备T30°'),(1500,'目标T33°'),(2090,'点胶完成保留')]:c.text(x,760,text,47,ORANGE,True)

def co_options_story(c):old_figures.co_uplook_counts(c)
def co_normal_story(c):
    numeric_steps(c,[('普通准备',['示教0° + 产品0°','+ 硬角1° + 校准30°','当前T31°']),('拍 转 再拍',['首拍识别2°','相对转2 + 0 + 1 = 3°','转后T34° 再拍位置']),('贴装读取',['保存角度 −1°','34 − 1 + 0 + 1','目标T仍为34°'])],
        '普通单点对照 不沿用快速模式准备角','本页转后说明XY偏移 (−0.36, −0.29) 毫米')
def co_mirror_story(c):
    heading(c,'普通生产上视的镜像与非镜像分别比较','同样识别2°  A点角0°  硬角1°  准备T31°')
    ledger(c,70,175,'普通非镜像',[('准备T','31°'),('相对旋转','3°'),('转后T','34°'),('最终T','34°')])
    ledger(c,1370,175,'普通镜像',[('准备T','31°'),('相对旋转','181°'),('转后T','212°'),('最终T','212°')])
    c.text(1200,890,'两侧都保存角度记录 −1°  贴装入口不会重复补一次',47,ORANGE,True)
def co_ipt_center_story(c):
    title,items,footer=old_figures.NUMERIC_FIGURES['co_ipt_center'];numeric_steps(c,items,title,footer)
def co_table_routes(c):
    two_lanes(c,['自动收集完整轮次','逐点估计与中位数','发布XY矩阵'],['人工导入列表','行内均值平滑','编辑保存矩阵'],
        '自动路线与人工路线算法不同','都需要匹配区域起点 间距 尺寸和生产开关')

CUSTOM={name:fn for name,fn in list(globals().items()) if callable(fn) and name.startswith(('tu_','co_'))}

def generate(book):
    out=ROOT/'docs/design'/book.FOLDER/'figures';used=[]
    for p in book.PAGES:
        name=p['diagram']
        if name in used:continue
        c=StoryCanvas(name,out)
        if name in CUSTOM:CUSTOM[name](c)
        elif name in old_figures.FLOW_FIGURES:
            labels,subs=old_figures.FLOW_FIGURES[name];flow(c,labels,subs)
            if name=='co_order':
                c.text(1200,730,'记录G0 → 转运动轴 → 追加实时X',58,BLUE,True)
                c.text(1200,930,'Z高度按独立分支计算',54,ORANGE,True)
            elif name=='tu_partial_failure':
                c.line([(1140,180),(1140,850)],ORANGE,9,False,True)
                c.text(1200,960,'失败位置不同 已发生的数据修改就不同',56,ORANGE,True)
            else:c.text(1200,850,p['remember'],46,BLUE,True)
        else:old_figures.CUSTOM[name](c)
        c.save();used.append(name)
    return used
