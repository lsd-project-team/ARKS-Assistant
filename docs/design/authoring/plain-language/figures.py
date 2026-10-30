"""与各页正文一一对应的设备、产品、坐标和记录插图。"""
from drawing import (Canvas, INK, BLUE, GREEN, ORANGE, GRAY, LINE, LIGHT, PALE,
                     WARM, board, camera, nozzle, chip, conveyor, flow, two_lanes,
                     numeric_steps, ledger, scene_pair, graph)


FLOW_FIGURES = {
 'tu_create': (['读当前配方','建立产品层级','准备位置和状态','注入工序记录'], ['数量与工艺','2板 × 3岛 × 2点','本层坐标与Info','A点 D_A / T_A']),
 'tu_dispense': (['找到当前A点','检查要不要做','执行点胶','写D_A完成'], ['完整产品地址','本侧工序与参与范围','读取当前坐标','只改当前这个A点']),
 'tu_handover': (['目标接收N1','刷新坐标','清掉源引用','更新状态保存'], ['先赋同一引用','Refresh正常返回','点胶段不再持有','再通知S2来料']),
 'tu_recipe_mapping': (['配方画面','样本TU','内存参与配置','后续新产品'], ['窗口自己的对象','改哪些点参加','新画面关闭可写回','创建时读取']),
 'tu_mapping_import': (['当前配方','新建一棵TU','填文件标记','赋给目标区段'], ['结构 坐标 工序','得到新运行对象','身份 停用 完成','替换原当前产品']),
 'tu_lookup': (['当前区段TU','本轮消息地址','当前焊点','当前坐标'], ['引用有没有换过','Index或WorkIndex','核对板 岛 名称','Refresh后重新取']),
 'tu_partial_failure': (['接收N1引用','Refresh','清源和改状态','Save'], ['这一步可能已发生','此处失败可部分更新','更晚失败可能已交接','没有统一回滚']),
 'co_nine': (['先选候选','移到Mark','再次九宫格PR','取后再更新'], ['可使用存在缓存','取片角在后次PR前写','刷新周边候选','按模式更新记录']),
 'co_order': (['产品和硬补偿','焊后和单点','相机分支','减TU区域量'], ['先形成G0位置','加入启用的修正','上视或中转台','仍在G0阶段']),
 'co_home': (['操作者确认','先关闭补偿','执行整机回零','按开关再开启'], ['取消就退出','异常可退出','失败不进恢复步骤','跳过也可回零成功']),
 'co_collect': (['查询统计','分组与去重','点数检查','够轮次计算'], ['开始时间后的记录','TU索引 基板 日期','恰好等于 R × C','还要核对轮次真实']),
 'co_enable': (['计算并预览','替换XY矩阵','保存配置','生产查表'], ['Calculated仍在窗口','人工或自动启用','没有统一失败回滚','另需开关和几何匹配']),
 'co_recap': (['实物在哪','本轮拍了什么','记录了什么','贴装怎样使用'], ['料盘 吸嘴 中转台','模式 照片 返回值','当前焊点Info','参考系 符号 顺序']),
}


NUMERIC_FIGURES = {
 'tu_coordinates': ('无旋转时逐层叠加', [('岛内A点',['(10, 5)']),('加基岛位置',['(10, 5) + (10, 5)','＝ (20, 10)']),('加基板和TU',['+ (20, 0) + (100, 200)','＝ (140, 210)'])], '每一个位置都说明相对谁  单位mm'),
 'tu_station_offset': ('工位偏移直接加在TU平移上', [('配方位置',['TU = (100, 200)','A = (90, 240)']),('加S1偏移',['TU + (2, −1)','A = (92, 239)']),('再次加S1',['本侧标记已置位','A仍为 (92, 239)'])], 'Refresh后回配方坐标 不会自动再加S1'),
 'tu_divide': ('每一步都跟踪同一份N1', [('S1创建后',['配置100 + 偏移2','TU的X = 102']),('向右移40',['102 + 40','TU的X = 142']),('两种后续操作',['回移：142 − 40 = 102','刷新：回到配置100'])], '移段没有统一清掉定位 测高和加工记录'),
 'co_pick_angle': ('定位角2°  硬角5°  吸嘴校准30°', [('未翻转',['5 − 2 + 30','取片T = 33°']),('翻转',['5 + 2 + 30','取片T = 37°']),('偏心接口角',['最终轴角 − 校准角','分别为3°或7°'])], '旋转轴角 芯片角和偏心接口角要分开'),
 'co_pick_xy': ('静态华夫盒XY说明输入 单位mm', [('转换后Mark',['(200, 100)','减偏心 (0.05, −0.02)']),('取料补偿与向量',['加 (0.01, 0.03)','减 (0.506675, 0.182428)']),('取片目标',['X = 199.453325','Y = 99.867572','T = 33°'])], '本页只计算这一载具分支的XY'),
 'co_quick': ('快速单点上视的保存量 单位mm', [('先相加',['位移 (0.12, −0.08)','参考差 (0.02, −0.01)','合成 (0.14, −0.09)']),('再减示教向量',['(0.5, 0.2)','先按 −1°旋转','再从左侧合成量扣除']),('保存到当前A点',['X = −0.363414','Y = −0.281243','角度记录 = 2°'])], '先保存 到贴装时还要按剩余角转向'),
 'co_normal': ('普通非镜像上视的T轴记录', [('拍照准备',['当前T = 29°','识别角 = 2°']),('实际转动',['相对转 2 + 5 + 1 = 8°','当前T = 37°','重新拍照算XY']),('贴装入口',['保存角度 −6°','37 − 6 + 5 + 1','目标T仍为37°'])], '旋转前后的位置结果不能互换'),
 'co_consume': ('快速例子的剩余角与偏移使用', [('求剩余角',['30 + 2 + 5 + 1 = 38°','38 − 30 = 8°']),('偏移转8°',['(−0.363414, −0.281243)','转成新的G0追加量']),('追加到G0',['(−0.320736, −0.329084)','基础 (100, 200)','→ (99.679264, 199.670916)'])], '其余补偿本例为0  实际还要转运动轴'),
 'co_ipt_center': ('中转台中心与取片位置 单位mm', [('Mark到中心',['示教向量 (1, 0)','按 −3°转向','(0.998630, −0.052336)']),('接到新Mark',['新Mark (100.1, 199.9)','中心约','(101.098630, 199.847664)']),('吸嘴取片目标',['加头相机差 再减偏心','(103.048630, 198.867664)','新T = 28°'])], '先找到芯片中心 再求吸嘴对位目标'),
}


MINI_FIGURES = {
 'tu_tree': ['TU一份产品', '2块基板', '6个基岛', '12个焊点'],
 'tu_address': ['输入4看接口', 'Index 4选结构4', 'WorkIndex 4选结构6'],
 'tu_inverse': ['局部 (40, 10)', '转90° → (−10, 40)', '加原点 → (90, 240)'],
 'tu_signals': ['S1放行', '输送和软件交接成功', 'S2收到来料完成'],
 'tu_refresh_values': ['交接前 (92, 239, 0.12)', 'Refresh', '交接后 (90, 240, 0)'],
 'tu_clear_compare': ['刷新：仍是N1', '新建：得到新记录', '清空：区段入口为空'],
 'tu_failure_compare': ['Refresh失败：可两边同指N1', 'Save失败：源可能已清空'],
 'tu_recap_steps': ['D_A=false T_A=false', 'D_A=true T_A=false', 'D_A=true T_A=true'],
 'co_terms': ['PR：视觉识别任务', 'Mark：识别特征', 'T：旋转轴角', 'G0：全局参考'],
 'co_feed_decisions': ['自动通过：满足阈值', '人工OK：可能绕过阈值', 'Skip：本颗不放行'],
 'co_anchor_options': ['两点定角：角差再取Atan', '三点拟合圆：只用P1至P3'],
 'co_quick_record': ['当前焊点Info', 'ComponentOffSet存XY', '角度记录存识别角'],
 'co_mirror_modes': ['普通镜像：相对转角含180°', '快速：无同一独立镜像项'],
 'co_ipt_compare': ['上视：芯片在吸嘴上', '中转台下视：芯片在台面上'],
 'co_ipt_retry': ['执行Pick', 'RePick标签', '持片检测', 'Retry只回检测'],
 'co_z': ['Z另算', '基准与测高', '芯片厚度', '局部补偿和压合'],
 'co_grid_sign': ['基础 (100, 200)', '减区域量 (0.025, 0)', '得到 (99.975, 200)'],
 'co_median': ['原行 0  0.01  1  0.03  0.04', '中位数行 0.01  0.02  0.03  0.035  0.04'],
}


def draw_mini(name,out):
    c=Canvas(name,out,360)
    labels=MINI_FIGURES[name]
    width=2280/len(labels)
    for i,label in enumerate(labels):
        # 小条图仅作关系补充，文字不塞进装饰框。
        size=46 if len(label)<28 else 42
        c.text(60+width*(i+.5),170,label,size,BLUE,True)
        comparisons={'tu_address','tu_clear_compare','tu_failure_compare','co_terms','co_feed_decisions',
                     'co_anchor_options','co_quick_record','co_mirror_modes','co_ipt_compare','co_z'}
        if i<len(labels)-1 and name not in comparisons:
            c.arrow(60+width*(i+1)-37,260,60+width*(i+1)+37,260)
        elif i<len(labels)-1:
            c.line([(60+width*(i+1),85),(60+width*(i+1),255)],LINE,3)
    c.save()


def route(c,correction=False):
    labels=['上料段','S1点胶','S2固晶','待下料','下料段']
    for i,label in enumerate(labels):
        x=40+i*475
        c.text(x+220,90,label,56,bold=True)
        conveyor(c,x+5,555,435)
        board(c,x+70,405,300,145,False,False)
        if i==1:nozzle(c,x+210,360)
        if i==2:nozzle(c,x+210,360,True)
        if i<4:c.arrow(x+440,490,x+475,490)
    c.line([(200,790),(2200,790)],BLUE,8,True)
    c.text(1200,900,'TU跟踪当前产品的结构 位置和工序记录',57,BLUE,True)
    if correction:
        c.text(1200,255,'产品路径：先找到要贴的A点',51,GREEN,True)
        c.text(1200,1000,'芯片路径：供料定位 → 取片 → 上视或中转台纠偏 → 贴装',49,ORANGE,True)


def tu_product(c):
    c.text(1200,70,'本例整份产品  2块基板 × 每板3岛 × 每岛A/B',55,bold=True)
    for n in range(2):
        x=70+n*1180
        c.rect(x,170,1100,690,PALE,GREEN,6,14)
        c.text(x+550,245,f'基板{n+1}',56,GREEN,True)
        for j in range(3):
            left=x+40+j*350
            c.rect(left,335,320,410,'white',GREEN,4)
            c.text(left+160,405,f'基岛{j+1}',47,bold=True)
            for k,letter in enumerate(['A','B']):
                px=left+90+k*140
                c.circle(px,565,22,ORANGE)
                c.text(px,650,letter,52)
                if n==0 and j==1 and k==0:c.circle(px,565,52,'white',BLUE,7);c.circle(px,565,22,ORANGE)
    c.text(1200,960,'本册追踪蓝圈：当前TU / 基板1 / 基岛2 / A点',56,BLUE,True)


def tu_owners(c):
    c.box(800,55,800,190,'A点工艺配方','示教位置 工艺参数',LIGHT)
    for x,name,done in [(100,'基岛2的A点','D_A = true'),(1350,'基岛3的A点','D_A = false')]:
        c.arrow(1200,260,x+475,390)
        c.box(x,410,950,430,name,'读同一份配置\n保存自己的坐标\n'+done,PALE)
    c.text(1200,960,'一处完成不会替另一处完成',58,ORANGE,True)


def tu_snake(c):
    c.text(1200,60,'独立的2行3列示例  蓝箭头为实际加工顺序',54,bold=True)
    centers={}
    for index in range(1,7):
        row,col=divmod(index-1,3);x=160+col*760;y=180+row*420
        c.rect(x,y,540,280,PALE,GREEN,5)
        wi=index if row==0 else 10-index
        c.text(x+270,y+92,f'结构编号 {index}',55,bold=True)
        c.text(x+270,y+193,f'第 {wi} 个加工',49,BLUE)
        centers[index]=(x+270,y+140)
    for a,b in zip([1,2,3,6,5],[2,3,6,5,4]):
        x1,y1=centers[a];x2,y2=centers[b]
        if y1==y2:
            sign=1 if x2>x1 else -1;c.arrow(x1+sign*285,y1,x2-sign*285,y2)
        else:c.arrow(x1,y1+155,x2,y2-155)
    c.text(1200,1000,'结构6的WorkIndex是4  结构4的WorkIndex是6',50,ORANGE,True)


def tu_rotation(c):
    c.text(1200,65,'先转方向 再加TU原点',58,bold=True)
    points=graph(c,130,220,900,560,[(0,0),(40,10)])
    c.text(points[0][0]+135,points[0][1]-45,'TU原点',42,BLUE)
    c.text(points[1][0]-100,points[1][1]-70,'A (40, 10)',42,BLUE)
    c.text(620,925,'TU局部坐标 单位mm',50)
    graph(c,1380,220,850,560,[(100,200),(90,240)],['TU (100, 200)','A (90, 240)'],ORANGE)
    c.text(1800,925,'G0坐标 单位mm',50)
    c.text(1200,460,'转90°',50,BLUE,True)
    c.arrow(1080,550,1300,550)


def tu_vision_height(c):
    scene_pair(c,'相机定位改XY和方向','测高使当前基板Z增加0.12','board','board')
    c.text(600,970,'本例假定没有额外XY修正',43,GRAY)
    c.text(1800,970,'A点Z：0 → 0.12mm',46,ORANGE,True)
    c.arrow(2170,820,2170,680,ORANGE)


def tu_refresh(c):
    ledger(c,70,110,'S1处理后 N1', [('D_A','true'),('T_A','false'),('当前Z','0.12mm'),('已测高标记','true')])
    ledger(c,1370,110,'交接Refresh后 仍为N1', [('D_A','true'),('T_A','false'),('当前Z','0mm'),('已测高标记','false')])
    c.arrow(1080,510,1320,510)
    c.text(1200,900,'旧测高差0.12可能仍在Info里  新坐标不再带它',49,ORANGE,True)


def tu_s2_entry(c):
    c.box(725,55,950,190,'固晶启用且配置输送','看当前TU的IsProduct')
    c.arrow(1050,255,570,410);c.arrow(1350,255,1830,410)
    c.text(530,355,'true',54,BLUE,True);c.text(1870,355,'false',54,ORANGE,True)
    c.box(80,450,1000,340,'正常S1传来N1','保留同一份N1\n保留已点胶记录',PALE)
    c.box(1320,450,1000,340,'按S2参数重新建','新的对象和Info\n旧记录不自动复制',WARM)
    c.text(1200,950,'本册连续例走左边  并把S2偏移设为0',54,bold=True)


def tu_ledgers(c):
    ledger(c,70,120,'产品A点的工序', [('D_A','true'),('T_A','true'),('记录归属','当前N1')])
    ledger(c,1370,120,'控制器的工作消息', [('取片消息','完成'),('纠偏消息','完成'),('贴装消息','完成')])
    c.text(600,800,'Finish不清产品工序',49,GREEN,True)
    c.text(1840,800,'Finish复位消息供后续使用',45,BLUE,True)
    c.text(1200,970,'消息和产品记录是两本不同的账',57,ORANGE,True)


def tu_exit(c):
    two_lanes(c,['固晶段','待下料段','下料皮带','清当前TU'],['固晶段','导出结果','清当前TU','提示人工取走'], '配置输送时按各区段入口接力','未配置输送时按相应发送分支处理')


def tu_participation(c):
    items=[('要参加 且未做','待执行',LIGHT),('要参加 且已做','工序完成',PALE),('不参加本侧','本侧跳过',WARM)]
    for i,(a,b,color) in enumerate(items):
        x=60+i*790;c.box(x,230,700,390,a,b,color)
        c.circle(x+350,810,42,GREEN if i==1 else ORANGE)
    c.text(1200,70,'参与范围和已完成是两个问题',58,bold=True)
    c.text(1200,970,'本侧无需再做 不自动说明质量合格',54,ORANGE,True)


def tu_live_mapping(c):
    two_lanes(c,['选中一个焊点','点正常','两侧步骤未完成'], ['选中基板或基岛','点正常','传播参与范围'], '单焊点分支直接修改本点步骤','上层分支没有同样重置所有后代步骤')


def tu_search(c):
    c.text(1200,70,'S1和已配置输送S2的主要分支',56,bold=True)
    rows=[('检测有料','TU存在','保留并Refresh'),('检测有料','TU为空','确认有料才新建'),('检测无料','TU存在','确认有料则保留'),('检测无料','TU存在','确认无料则清空'),('检测无料','TU为空','保持空引用')]
    for i,row in enumerate(rows):
        y=170+i*150
        c.rect(90,y,2220,135,PALE if i%2==0 else 'white')
        for x,t in zip([420,1110,1860],row):c.text(x,y+67,t,48,bold=i==0)
    c.text(1200,1000,'保留原对象才能保留旧Info和工序',50,ORANGE,True)


def tu_clear(c):
    titles=['整线清空','只清点胶','只清固晶']
    for x,t in zip([1000,1540,2080],titles):c.text(x,80,t,50,bold=True)
    for i,region in enumerate(['上料','点胶','固晶','待下料','下料']):
        y=245+i*150;c.text(320,y,region,53,bold=True)
        for j,x in enumerate([1000,1540,2080]):
            clear=j==0 or j==1 and i==1 or j==2 and i==2
            c.circle(x,y,26,ORANGE if clear else 'white',ORANGE if clear else LINE,5)
        c.line([(140,y+70),(2300,y+70)],LINE,3)
    c.text(1200,1000,'清引用并置无料  不统一重置全部信号和消息',49,ORANGE,True)


def tu_irregular(c):
    c.text(600,75,'常规：相同模板重复',56,bold=True)
    c.text(1800,75,'异形：按实际节点展开',56,bold=True)
    board(c,120,250,950,560)
    for i,count in enumerate([2,3]):
        x=1370+i*470;c.rect(x,220,420,650,PALE,GREEN,5)
        c.text(x+210,290,f'基板{i+1}',47,bold=True)
        for j in range(count):
            c.rect(x+70,390+j*140,280,110,'white',GREEN,3)
            c.text(x+210,445+j*140,f'基岛{j+1}',44)
    c.text(1200,980,'改数量或替换节点后  旧运行树需要重新建立',51,ORANGE,True)


def tu_node_identity(c):
    two_lanes(c,['创建时节点N','原运行对象A','用N查询可找到'],['同名新节点N′','名字和ID相同','用N′查可能异常'], '原节点对象保持关联','按对象引用匹配  不自动按名字配对')


def tu_persistence(c):
    c.box(100,120,950,650,'已保存配置','配方参数\n设备相关配置\n不含完整当前TU',LIGHT)
    c.box(1350,120,950,650,'完整运行现场还涉及','当前产品树和坐标\n工序进度与消息\n机器参考关系',PALE)
    c.text(1200,950,'本主链未形成完整保存 加载和重新绑定过程',51,ORANGE,True)


def tu_helpers(c):
    numeric_steps(c,[('生产区段',['保存当前TU','部分在线示教可替换']),('辅助窗口',['可新建自己的样本','不一定赋回区段']),('补偿工作模式',['先创建测试TU','特定条件下再S2重建'])], '同样能创建TU  但对象由不同地方持有','新对象不自动复制旧产品Info',False)


def tu_recap(c):
    values=[('S1创建','(92,239,0)','false','false'),('测高和点胶','(92,239,0.12)','true','false'),('交接Refresh','(90,240,0)','true','false'),('S2成功','(90,240,0)','true','true')]
    for i,(heading,position,d,t) in enumerate(values):
        x=45+i*595
        c.text(x+280,70,heading,51,bold=True)
        board(c,x+50,210,460,240)
        c.text(x+280,550,'同一份N1',45,BLUE,True)
        c.text(x+280,655,position,43)
        c.text(x+280,775,'D_A = '+d,43,GREEN if d=='true' else GRAY)
        c.text(x+280,875,'T_A = '+t,43,GREEN if t=='true' else GRAY)
        if i<3:c.arrow(x+535,330,x+590,330)
    c.text(1200,1000,'只跟踪基板1 基岛2 A点  其余点各有记录',48,ORANGE,True)


def co_units(c):
    c.text(1200,65,'像素先标定 再进入物理位置转换',58,bold=True)
    flow(c,['相机像素','相机标定','产品或G0位置','运动轴目标'],['CenterX / Y','方向与尺度','单位mm且带参考系','控制器坐标转换'],280)
    c.text(1200,780,'说明例：10像素 × 0.01mm/像素 = 0.10mm',55,BLUE,True)
    c.text(1200,940,'真实比例和方向依本相机标定  不使用例子代替标定',47,ORANGE)


def co_product(c):
    c.text(600,90,'先看配方里的产品',56,bold=True)
    c.text(1800,90,'再找实际Mark更新本层',56,bold=True)
    camera(c,600,300);camera(c,1800,300)
    board(c,130,520,940,330)
    c.rect(1330,520,940,330,'white',LINE,3)
    board(c,1390,475,940,330)
    c.text(600,980,'下层焊点按旧位置换算',46)
    c.text(1800,980,'下层焊点跟随新位置换算',46,BLUE,True)
    c.arrow(1080,580,1310,580)


def co_product_write(c):
    two_lanes(c,['局部示教Mark','换算到G0','减头相机差','拍照移动目标'],
              ['标定相机结果','结合拍照位转G0','加头相机差','回本层局部保存'],
              '上行：先求相机该移动到哪里','下行：再把本次识别结果带回产品')


def co_feed_loop(c):
    c.box(50,110,650,220,'识别当前芯片','标定成XY物理偏差')
    c.box(870,110,650,220,'检查XY和角度','全部满足阈值？')
    c.arrow(720,220,850,220)
    c.box(1720,110,610,220,'自动通过','包含等于阈值',PALE)
    c.arrow(1540,220,1700,220,GREEN)
    c.text(1615,140,'是',48,GREEN,True)
    c.arrow(1195,350,1195,520,ORANGE)
    c.text(1350,435,'否',48,ORANGE,True)
    c.box(870,540,650,230,'检查剩余次数','有次数才校正XY',WARM)
    c.line([(850,650),(375,650),(375,350)],BLUE,7,True)
    c.text(360,760,'有：校正XY后重拍',47,BLUE)
    c.box(1720,540,610,230,'次数用完','返回未通过',WARM)
    c.arrow(1540,650,1700,650,ORANGE)
    c.text(1615,580,'无',48,ORANGE,True)
    c.text(1200,970,'角度也参加检查  这个校正调用不直接转T',52,ORANGE,True)


def co_route(c):
    c.text(230,80,'产品线',57,GREEN,True)
    board(c,70,195,620,260)
    camera(c,1020,190)
    c.text(1030,415,'定位产品A点',50,GREEN,True)
    c.arrow(735,320,860,320,GREEN)
    c.line([(1260,320),(1770,320),(1770,500)],GREEN,7,True)
    c.text(230,630,'芯片线',57,ORANGE,True)
    c.circle(280,845,125,PALE,GREEN,5)
    for x,y in [(230,800),(330,800),(230,890),(330,890)]:chip(c,x,y,65)
    c.text(280,1005,'供料定位',42)
    nozzle(c,710,820,True,8)
    c.text(710,1005,'取起芯片',42)
    camera(c,1220,770,True)
    c.text(1220,970,'上视或中转台纠偏',44,ORANGE,True)
    c.arrow(435,830,570,830,ORANGE);c.arrow(855,830,1050,830,ORANGE)
    c.line([(1380,830),(1770,830),(1770,690)],ORANGE,7,True)
    c.box(1590,515,770,175,'形成贴装目标','产品位置 + 芯片与其他补偿',PALE)
    c.text(1510,75,'两路信息汇合后让芯片贴到A点',53,bold=True)


def co_anchor(c):
    c.text(1200,65,'独立说明点 P1 P2 P3 单位mm',55,bold=True)
    graph(c,140,200,1050,620,[(0,0),(2,1),(4,3)],['P1','P2','P3'],BLUE,False)
    c.lines(1800,300,['X只选P1和P3','(0 + 4) / 2 = 2','Y只选P2和P3','(1 + 3) / 2 = 2'],52,gap=120)
    c.text(1800,890,'代表点 = (2, 2)',60,ORANGE,True)


def co_rigid(c):
    numeric_steps(c,[('旧位置',['原点 (100, 200)','示教Mark局部 (10, 0)','旧角度0']),('本次目标',['新Mark (110.2, 200.1)','指定转角 0.01rad','先平移 再绕目标转']),('更新结果',['原点约','(100.200500, 200.000002)','旧Mark换算后对上目标'])], '本页用平面几何说明对点与转向','示教Mark到达 (110.2, 200.1)  单位mm')


def co_product_retry(c):
    two_lanes(c,['距离超差','S1选Retry','人工重对点','跳过下次距离检查'], ['距离超差','S2选Retry','重新采P1/P2','再次检查距离'], 'S1的Retry','S2的Retry')


def co_uplook_counts(c):
    rows=[('快速单点',1,False),('快速双点',2,False),('普通单点',1,True),('普通双点',2,True)]
    for i,(label,n,normal) in enumerate(rows):
        y=115+i*235
        c.text(280,y,label,52,bold=True)
        for j in range(n):camera(c,760+j*260,y)
        if normal:
            c.text(1450,y,'转T',50,ORANGE,True)
            c.arrow(1180,y,1300,y)
            for j in range(n):camera(c,1770+j*260,y)
        c.text(2250,y,f'{n*(2 if normal else 1)}次',47,BLUE,True)
        c.line([(90,y+140),(2300,y+140)],LINE,3)


def co_mirror(c):
    ledger(c,70,115,'普通非镜像', [('准备T','29°'),('相对旋转','8°'),('转后T','37°'),('贴装目标','37°')])
    ledger(c,1370,115,'普通镜像', [('准备T','29°'),('相对旋转','186°'),('转后T','215°'),('贴装目标','215°')])
    c.text(1200,900,'两侧都保存角度偏移 −6°',56,ORANGE,True)
    c.text(1200,995,'输入识别2° 焊点5° 硬补偿1°  不自行把轴角模360°',44)


def co_ipt_scene(c):
    for i,title in enumerate(['1 放到中转台','2 相机拍Mark','3 吸嘴对准新中心','4 重新取起']):
        x=600 if i%2==0 else 1800;y=150 if i<2 else 650
        c.text(x,y-90,title,54,bold=True)
        c.rect(x-370,y+250,740,60,PALE,GREEN,5)
        if i==0:nozzle(c,x,y+150);chip(c,x,y+210,190,10)
        if i==1:camera(c,x,y+70);chip(c,x,y+210,190,10)
        if i==2:nozzle(c,x+70,y+120);chip(c,x,y+210,190,10);c.arrow(x+240,y+130,x+85,y+130,ORANGE)
        if i==3:nozzle(c,x,y+110,True,10);c.arrow(x+200,y+200,x+200,y+60,ORANGE)
    c.line([(1200,50),(1200,1010)],LINE,3)


def co_ipt_records(c):
    two_lanes(c,['写拍照目标','移动到拍照位','识别'],['写取片目标','移动并Pick','持片检测'], 'IPTVisionPos在移动前可已有值','IPTPickPos在实际取起前可已有值')


def co_thermal(c):
    ledger(c,70,100,'取片漂移读取', [('保存X','+0.03'),('保存Y','−0.02'),('返回XY','正值'),('超0.2mm','提示仍返回')])
    ledger(c,1370,100,'上视漂移读取', [('保存X','+0.03'),('保存Y','−0.02'),('返回XY','取负值'),('超0.2mm','抛异常')])
    c.text(1200,925,'单位mm  失败可能保留旧记录',56,ORANGE,True)


def co_postbond(c):
    numeric_steps(c,[('给定有效样本',['X偏差 10  20  30','本例通过严格<50筛选']),('换算并按比例',['均值20 ÷ 1000','补偿比例50%']),('后续目标修正',['得到 +0.01mm','不改变已贴好的点'])], '独立说明例  偏差记录按源码换算为mm','样本数满足以后  还要保证筛选后集合有效')


def co_realtime(c):
    two_lanes(c,['本轮实际传入','IPTVisionPos','IPTPickPos'], ['参考点插值','组合差仅保留X','轴转换后追加'], '注意实参顺序与方法参数名顺序相反','RealBondPoint3D记录在这一追加之前')


def co_layers(c):
    two_lanes(c,['产品G0目标','减TU区域表量','转为轴目标'], ['轴目标','驱动使用轴二维表','执行运动'], '应用程序层  TU区域补偿','驱动执行层  设备轴二维补偿')


def co_teach(c):
    graph(c,150,230,1250,610,[(0,0),(20,1)],['P1 (0, 0)','P2 (20, 1)'],BLUE)
    c.text(1200,70,'操作员采两点  在传入对象的上级参考系计算',54,bold=True)
    c.lines(1890,350,['X跨度 = 20mm','角度约 2.862405°','写入约 0.0499584rad'],50,gap=125)
    c.text(1200,990,'在线要求 X跨度≥1mm  且角度绝对值≤5°',54,ORANGE,True)


def co_teach_writes(c):
    c.text(1200,65,'各入口写入的对象不同  读每一行',55,bold=True)
    rows=[('TU入口','TU坐标','TU配置角'),('基板入口','TU坐标','基板运行与配置角'),('基岛入口','基板坐标','基岛运行与配置角'),('焊点入口','基岛坐标','焊点配置角')]
    for i,(entry,before,after) in enumerate(rows):
        y=185+i*185
        c.text(270,y+55,entry,48,bold=True)
        c.box(650,y-10,620,150,before,fill=LIGHT)
        c.arrow(1320,y+60,1460,y+60)
        c.box(1520,y-10,780,150,after,fill=PALE)
    c.text(1200,1000,'窗口先修改传入坐标并Save  调用方继续写目标',49,ORANGE,True)


def co_grid(c):
    c.text(1200,60,'四角X补偿值  当前点在正中间  单位mm',55,bold=True)
    x0,y0,w,h=380,240,1250,530
    c.rect(x0,y0,w,h,'white',GREEN,6)
    for x,y,value in [(x0,y0,'0.01'),(x0+w,y0,'0.03'),(x0,y0+h,'0.02'),(x0+w,y0+h,'0.04')]:
        c.circle(x,y,22,GREEN);c.text(x,y-70,value,56,GREEN,True)
    c.line([(x0+w/2,y0),(x0+w/2,y0+h)],LINE,4,False,True)
    c.line([(x0,y0+h/2),(x0+w,y0+h/2)],LINE,4,False,True)
    c.circle(x0+w/2,y0+h/2,27,ORANGE)
    c.text(x0+w/2,y0+h/2+90,'0.025',60,ORANGE,True)
    c.lines(2060,370,['Y补偿均为0','中心四角等权','G0目标减该量'],47,gap=130)
    c.text(1200,980,'图中四角是网格点的补偿值  不是机器位置',49)


def co_calculate_grid(c):
    c.text(1200,70,'同一个位置的多轮数据先纵向合并',57,bold=True)
    for row,values in enumerate([['第1轮','0.01','0.03','0.02'],['第2轮','0.02','0.03','0.01'],['第3轮','0.01','0.04','0.02']]):
        for col,val in enumerate(values):
            x=100+col*560;y=190+row*150
            c.rect(x,y,500,130,PALE if col==0 else 'white')
            c.text(x+250,y+65,val,49)
    for x in [940,1500,2060]:c.arrow(x,665,x,790)
    c.text(350,855,'位置代表值',50,BLUE,True)
    c.text(1500,855,'按位置合并 → 按行列放回二维表',52,BLUE,True)
    c.text(1200,1000,'X和Y分别计算  然后逐行中位数平滑',50,ORANGE,True)


def co_import(c):
    numeric_steps(c,[('原始一行',['0  0.01  1  0.03  0.04','单位mm']),('人工导入均值',['0  0.336667  0.216','0.356667  0.04']),('自动路径中位数',['0.01  0.02  0.03','0.035  0.04'])], '同一组独立说明输入  两种平滑不会得到同一张表','只说明算法差异  不是可直接发布的设备参数',False)


def co_manual(c):
    ledger(c,70,100,'手动PlacementTest', [('基础G0','(100, 200)'),('偏移XY','(0.1, −0.2)'),('当前表达式结果','(100.2, 199.6)')])
    ledger(c,1370,100,'生产上视分支', [('基础G0','(100, 200)'),('剩余转角','0°'),('该项叠加后','(100.1, 199.8)')])
    c.text(1200,820,'单位mm  其余补偿为0  轴转换说明输入为恒等',48)
    c.text(1200,970,'相同偏移值  由于路径不同得到不同目标',54,ORANGE,True)


CUSTOM = {name: value for name,value in list(globals().items())
          if callable(value) and name.startswith(('tu_', 'co_'))}


def generate(book,root):
    out=root/'docs/design'/book.FOLDER/'figures'
    used=[]
    for page in book.PAGES:
        name=page['diagram'];c=Canvas(name,out)
        if name in FLOW_FIGURES:
            labels,subs=FLOW_FIGURES[name];flow(c,labels,subs)
            if name=='co_order':
                c.text(1200,730,'记录G0 → 转运动轴 → 追加实时X',58,BLUE,True)
                c.text(1200,930,'Z高度按独立分支计算',54,ORANGE,True)
            elif name=='tu_partial_failure':
                c.line([(1140,180),(1140,850)],ORANGE,9,False,True)
                c.text(1200,960,'失败位置不同 已发生的数据修改就不同',56,ORANGE,True)
            else:
                c.text(1200,850,page['remember'],48,BLUE,True)
        elif name in NUMERIC_FIGURES:
            title,items,footer=NUMERIC_FIGURES[name];numeric_steps(c,items,title,footer,name!='co_pick_angle')
        elif name=='tu_route':route(c)
        elif name=='co_route':co_route(c)
        elif name=='co_supply':scene_pair(c,'晶圆：先找候选并定位','静态华夫盒：焊头相机识别','wafer','tray')
        else:CUSTOM[name](c)
        c.save();used.append(name)
        if page['extra']:
            draw_mini(page['extra'],out);used.append(page['extra'])
    return used
