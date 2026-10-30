"""设备动作示意。图上只留部件、动作与状态标签。"""
import math
from shared import *

HEIGHT=1360

def label(c,x,y,text,color=INK,size=62):c.text(x,y,text,size,color,True)
def pair(c,left,right):
    label(c,600,110,left);label(c,1800,110,right)
    c.line([(1200,190),(1200,1220)],LINE,3)

def product(c,x,y,w=960,h=330,selected=True,populated=False):
    c.rect(x,y,w,h,PALE,GREEN,6,16)
    iw=(w-100)/3;ih=(h-76)/2;chosen=None
    for row in range(2):
        for col in range(3):
            left=x+28+col*(w-44)/3;top=y+23+row*(h-33)/2
            c.rect(left,top,iw,ih,'white',GREEN,3)
            for j in range(2):
                px=left+iw*(.32+.38*j);py=top+ih*.52
                if populated:chip(c,px,py,min(100,w*.10))
                else:c.circle(px,py,13,GRAY)
                if row==0 and col==1 and j==0:
                    chosen=(px,py)
                    if selected:c.circle(px,py,34,'white',BLUE,7);c.circle(px,py,13,BLUE)
    return chosen

def record(c,x,y,glue='没做',bond='没做',title='这块板的记录',w=950):
    label(c,x+w/2,y,title)
    for i,(name,value) in enumerate([('位置','当前工位'),('A点点胶',glue),('A点贴芯片',bond)]):
        yy=y+95+i*165;c.rect(x,yy,w,165,PALE if value in ['已做','已贴'] else 'white')
        c.text(x+45,yy+82,name,58,anchor='lm')
        c.text(x+w*.76,yy+82,value,58,BLUE)

def cross(c,x,y,r=90):
    c.line([(x-r,y),(x+r,y)],GRAY,5);c.line([(x,y-r),(x,y+r)],GRAY,5)

def tray(c,x,y,w=960,h=380,candidate=True):
    c.rect(x,y,w,h,PALE,GREEN,6,12)
    for row in range(2):
        for col in range(3):
            px=x+w*(col+.5)/3;py=y+h*(row+.5)/2
            c.rect(px-100,py-72,200,144,'white',LINE,3)
            if candidate or row!=0 or col!=1:chip(c,px,py,140,4 if row==0 and col==1 else 0)
    return x+w/2,y+h/4

def route(c,correction=False):
    if not correction:
        for i,title in enumerate(['进料','点胶','贴芯片','待下料','下料']):
            x=240+i*480;label(c,x,230,title,size=59)
            conveyor(c,x-205,800,410);ax,ay=product(c,x-195,585,390,200,i<3,i>=3)
            if i==1:nozzle(c,ax,ay-130);c.arrow(ax,ay-100,ax,ay-35,ORANGE)
            if i==2:chip(c,ax,ay,82);nozzle(c,ax,ay-135)
            if i<4:c.arrow(x+215,730,x+260,730)
        c.line([(160,1050),(2240,1050)],BLUE,8,True)
        label(c,1200,1170,'同一块板子向前走',BLUE)
    else:
        product(c,95,210,850,280);label(c,520,590,'板子上的A点',GREEN)
        c.line([(1000,350),(2070,350),(2070,600)],GREEN,7,True)
        for x,title in [(400,'找到芯片'),(1200,'取起并拍照'),(2050,'对准A点贴下')]:label(c,x,700,title,ORANGE,58)
        tray(c,100,850,600,260)
        nozzle(c,1180,920,True,8);camera(c,1180,1240,True)
        ax,ay=product(c,1770,900,560,220);chip(c,ax,ay,92)
        c.arrow(745,1000,920,1000,ORANGE);c.arrow(1510,1000,1690,1000,ORANGE)

def tu_record(c):
    label(c,590,180,'实物板子',GREEN);product(c,110,480)
    c.arrow(1100,640,1310,640);record(c,1380,300)

def tu_address(c):
    for n in range(2):
        x=65+n*1190;c.rect(x,220,1080,820,PALE,GREEN,6,16)
        label(c,x+540,320,f'基板{n+1}',GREEN)
        for j in range(3):
            xx=x+35+j*350;c.rect(xx,435,315,475,'white',GREEN,4)
            label(c,xx+157,510,f'基岛{j+1}',size=54)
            for k,letter in enumerate(['A','B']):
                px=xx+80+150*k;c.circle(px,690,20,GRAY)
                if n==0 and j==1 and k==0:c.circle(px,690,49,'white',BLUE,8);c.circle(px,690,20,BLUE)
                c.text(px,810,letter,62)
    label(c,1200,1190,'蓝圈选中这一次的A点',BLUE)

def tu_arrive(c):
    pair(c,'正在送入','到达点胶工位')
    for center in [600,1800]:conveyor(c,center-490,900,980)
    product(c,90,550);ax,ay=product(c,1320,550)
    nozzle(c,ax,ay-180)
    c.arrow(700,1070,1020,1070);label(c,600,1180,'板子向前走',BLUE)
    label(c,1800,1180,'准备点胶',BLUE)

def board_locate(c):
    pair(c,'原来预计的位置','相机找到实际位置')
    product(c,95,540);product(c,1360,480)
    camera(c,1840,300)
    c.arrow(1065,690,1320,630)
    label(c,600,1050,'板子可能放偏一点',GREEN,58)
    label(c,1800,1050,'用这次的位置找A点',BLUE,58)

def tu_height(c):
    pair(c,'示教时的板面','这次板面高了一点')
    for x,y in [(600,720),(1800,590)]:
        c.line([(x-440,720),(x+440,720)],LINE,4,False,True)
        c.rect(x-420,y,840,80,PALE,GREEN,6);c.circle(x,y,25,BLUE)
        c.rect(x-130,280,260,140,LIGHT,BLUE,5,12)
        label(c,x,350,'测高',BLUE,55)
        c.line([(x,440),(x,y-65)],BLUE,5,True,True)
    c.arrow(2260,720,2260,590,ORANGE)
    label(c,600,1050,'原来的高度',BLUE)
    label(c,1800,1050,'高度差记到这块基板',BLUE,58)

def tu_glue(c):
    label(c,590,180,'胶头对准A点',BLUE)
    ax,ay=product(c,110,650);nozzle(c,ax,ay-140)
    c.arrow(ax,ay-115,ax,ay-36,ORANGE)
    c.arrow(1100,700,1310,700)
    record(c,1380,320,'已做','没做')
    label(c,1200,1190,'点胶动作正常成功后写入',BLUE)

def tu_transfer(c):
    pair(c,'点胶工位','固晶工位')
    for x in [110,1330]:conveyor(c,x,790,960)
    product(c,1350,430,920,330);c.arrow(1090,620,1310,620)
    label(c,1800,960,'还是这块板子',GREEN)
    c.text(1800,1090,'A点：胶已点，芯片没贴',57,BLUE)
    c.text(600,1090,'交出原来的加工记录',57,BLUE)

def tu_refresh(c):
    pair(c,'点胶工位的位置','新工位重新准备位置')
    product(c,110,400);product(c,1345,460)
    c.arrow(1090,570,1310,620)
    for x in [600,1800]:
        label(c,x,1000,'A点的胶已点',GREEN)
        c.text(x,1120,'这项进度继续保留',58,BLUE)

def tu_bond(c):
    label(c,590,180,'芯片贴到A点',ORANGE)
    ax,ay=product(c,110,650);chip(c,ax,ay,130);nozzle(c,ax,ay-140)
    c.arrow(1100,700,1310,700);record(c,1380,320,'已做','已贴')
    label(c,1200,1190,'本次固晶动作正常成功后写入',BLUE)

def tu_out(c):
    pair(c,'加工点满足发送条件','继续向下料方向移送')
    for x in [110,1330]:
        conveyor(c,x,860,960);product(c,x+20,490,920,330,False,True)
    c.arrow(1090,660,1310,660)
    label(c,600,1100,'按各点记录判断',GREEN,58)
    label(c,1800,1100,'按输送条件前进',BLUE,58)

def tu_reset(c):
    for x,title in [(400,'刷新位置'),(1200,'清掉记录'),(2000,'重新建立')]:label(c,x,180,title,size=59)
    product(c,90,420,620,230);product(c,890,420,620,230);product(c,1690,420,620,230)
    for x,title,lines in [(400,'还是原来的记录',['重新准备位置','原有工序进度保留']),
        (1200,'当前工位不再持有',['记录入口清空','实物位置要另确认']),
        (2000,'新的一份记录',['按当前条件建立','不能当作恢复旧进度'])]:
        label(c,x,820,title,BLUE,54);c.lines(x,1010,lines,52,gap=120)

def tu_done(c):
    labels=[('实际加工成功','对应工序记完成'),('设置为不参加','这道工序跳过'),('人工改成成功','只是人工改记录')]
    for i,(title,result) in enumerate(labels):
        x=400+i*800;label(c,x,200,title,size=56)
        product(c,x-310,470,620,230)
        label(c,x,900,result,BLUE,54)
    label(c,1200,1160,'检测合格要看另外的实际结果',ORANGE)

def co_tray(c):
    ax,ay=tray(c,120,500,1120,480);camera(c,ax,270)
    c.circle(ax,ay,115,'white',BLUE,7);chip(c,ax,ay,150,4)
    label(c,680,1150,'这次要取的芯片',ORANGE)
    label(c,1810,430,'下视相机',BLUE)
    c.text(1810,610,'从上面拍槽内芯片',58)
    c.text(1810,790,'找到位置和方向',58)

def co_pick(c):
    for i,title in enumerate(['对准芯片','执行吸取','抬起芯片']):
        x=400+i*800;label(c,x,180,title)
        c.rect(x-310,900,620,65,PALE,GREEN,6)
        chip_y=820 if i<2 else 610
        chip(c,x,chip_y,220,4)
        nozzle(c,x,chip_y-80 if i else 530)
        if i==0:c.arrow(x+210,560,x+210,760)
        if i==2:c.arrow(x+210,850,x+210,585)
    label(c,1200,1160,'取起后还要按条件检查是否持片',BLUE,58)

def co_offcenter(c):
    pair(c,'理想情况','实际可能吸偏一点')
    for x,dx,dy in [(600,0,0),(1800,105,-45)]:
        c.circle(x,650,260,'white',LINE,5)
        chip(c,x+dx,650+dy,330,0 if dx==0 else -8)
        cross(c,x,650,300)
    label(c,600,1120,'芯片中心与参考重合',BLUE,56)
    label(c,1800,1120,'芯片中心偏在一边',ORANGE,56)

def co_photo(c):
    nozzle(c,740,420);chip(c,790,500,280,7);camera(c,790,1040,True)
    c.line([(660,870),(720,660)],BLUE,4,False,True)
    c.line([(920,870),(860,660)],BLUE,4,False,True)
    for y,text in [(310,'吸嘴带着芯片'),(600,'拍到芯片特征'),(1030,'上视相机朝上拍')]:label(c,1800,y,text,BLUE,59)
    c.line([(1430,320),(910,320)],LINE,4)
    c.line([(1430,600),(990,530)],LINE,4)
    c.line([(1430,1030),(940,1030)],LINE,4)

def co_align(c):
    pair(c,'芯片还偏在A点右边','芯片中心对上A点')
    for x,pivot in [(600,700),(1800,1730)]:
        c.rect(x-450,865,900,100,PALE,GREEN,6);c.circle(x,865,30,'white',BLUE,7)
        nozzle(c,pivot,570);chip(c,pivot+70,650,220)
        c.line([(pivot,585),(pivot,830)],GRAY,4,False,True)
        c.line([(x,720),(x,830)],BLUE,4,False,True)
        label(c,x,1120,'蓝圈是A点',BLUE,58)
    c.arrow(820,420,570,420,ORANGE)
    label(c,650,285,'吸嘴往左修正',ORANGE,55)
    c.text(1800,285,'横向对准后再贴下',55,ORANGE,True)

def co_rotate(c):
    pair(c,'转方向之前','转方向之后')
    for x,dx,dy,angle in [(600,100,0,0),(1800,71,-71,-45)]:
        c.circle(x,650,260,'white',LINE,4)
        chip(c,x+dx,650+dy,280,angle)
        cross(c,x,650,300)
    pts=[(1800+220*math.cos(math.radians(a)),650+220*math.sin(math.radians(a))) for a in range(0,-46,-3)]
    c.line(pts,ORANGE,7,True)
    label(c,600,1120,'灰色参考没有移动',BLUE,58)
    label(c,1800,1120,'橙色芯片中心跟着转',ORANGE,58)

def co_place(c):
    pair(c,'先在A点上方对准','执行贴装后')
    for x,chip_y,tip in [(600,615,535),(1800,820,590)]:
        c.rect(x-450,900,900,80,PALE,GREEN,6);c.circle(x,900,28,'white',BLUE,7)
        chip(c,x,chip_y,220);nozzle(c,x,tip)
    c.arrow(930,650,930,850,ORANGE)
    label(c,600,1130,'贴装高度另按参数处理',BLUE,54)
    label(c,1800,1130,'正常成功才记芯片已贴',BLUE,54)

def co_ipt(c):
    for i,title in enumerate(['放到台面','从上面拍照','吸嘴对准新位置','重新取起来']):
        x=600 if i%2==0 else 1800;y=220 if i<2 else 865
        label(c,x,y-100,title,size=58)
        c.rect(x-420,y+350,840,70,PALE,GREEN,5)
        if i==0:
            nozzle(c,x,y+110);chip(c,x,y+278,200,8)
            c.arrow(x+280,y+70,x+280,y+250,ORANGE)
        if i==1:camera(c,x,y+40);chip(c,x,y+278,200,8)
        if i==2:
            nozzle(c,x+70,y+125);chip(c,x,y+278,200,8)
            c.arrow(x+280,y+110,x+115,y+110,ORANGE)
        if i==3:
            nozzle(c,x,y+110);chip(c,x,y+182,200,8);c.arrow(x+270,y+290,x+270,y+90,ORANGE)
    c.line([(1200,130),(1200,1300)],LINE,3)

def co_counts(c):
    for i,(name,n,again) in enumerate([('快速单点',1,False),('快速双点',2,False),('普通单点',1,True),('普通双点',2,True)]):
        y=210+i*290;label(c,300,y,name,size=59)
        for j in range(n):camera(c,780+j*260,y)
        if again:
            c.arrow(1190,y,1370,y);label(c,1510,y,'转方向',ORANGE,53)
            for j in range(n):camera(c,1810+j*245,y)
        label(c,2270,y,f'{n*(2 if again else 1)}次',BLUE,56)
        c.line([(90,y+160),(2310,y+160)],LINE,3)

def co_quality(c):
    pair(c,'动作是否完成','实际贴得怎样')
    ax,ay=product(c,100,470);chip(c,ax,ay,130)
    ax,ay=product(c,1335,470);chip(c,ax+35,ay+25,130,6);camera(c,ax,300)
    label(c,600,1050,'看这次工序记录',BLUE,58)
    label(c,1800,1050,'看实际检测结果',BLUE,58)

def co_compensate(c):
    pair(c,'前面检测到偏差','后面的目标按规则修正')
    for x,dx in [(600,115),(1800,0)]:
        c.rect(x-420,520,840,350,PALE,GREEN,6)
        c.circle(x,695,65,'white',BLUE,7);chip(c,x+dx,695,210)
        c.line([(x,430),(x,970)],BLUE,4,False,True)
    c.arrow(2140,400,1840,400,ORANGE)
    label(c,600,1120,'已贴好的不回改',GRAY,58)
    label(c,1800,1120,'影响后续目标',BLUE,58)

def co_fault(c):
    for x,title in [(400,'还在料盘里'),(1200,'已在吸嘴上'),(2000,'已在中转台')]:label(c,x,200,title,size=58)
    tray(c,90,580,620,300)
    nozzle(c,1200,560,True,7)
    c.rect(1680,850,640,70,PALE,GREEN,6);chip(c,2000,773,200,7)
    label(c,1200,1170,'先核对实物停在哪一步',BLUE)

CUSTOM={name:fn for name,fn in list(globals().items()) if callable(fn) and name.startswith(('tu_','co_'))}
CUSTOM.update(tu_route=lambda c:route(c),co_route=lambda c:route(c,True),tu_locate=board_locate,co_board=board_locate)

def generate(book):
    out=ROOT/'docs/design'/book.FOLDER/'figures'
    for p in book.PAGES:
        c=Canvas(p['diagram'],out,HEIGHT);CUSTOM[p['diagram']](c);c.save()
