"""Record completed visual review; never substitute these checks for page review."""
from pathlib import Path
import sys,json,hashlib,collections
from pypdf import PdfReader
H=Path(__file__).resolve().parent;ROOT=H.parents[3];O=ROOT/'output/correction-v3.2'
assert sys.argv[1:]==['--confirm-46-pages-reviewed'],'Review every final page before using the confirmation flag'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def get(n):return json.loads((O/n).read_text(encoding='utf-8-sig'))
def dump(n,v):(O/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
pdf=O/'纠偏过程设计文档.pdf';reader=PdfReader(pdf);assert len(reader.pages)==46
verification=get('verification.json');assert verification['page_count']==46
assert verification['files']['纠偏过程设计文档.pdf']['sha256']==sha(pdf)
assert get('text-sync.json')['word_missing']==get('text-sync.json')['pdf_missing']==[]
assert all(c['passed'] for c in get('calculator-csharp.json')['checks'])
assert all(c['passed'] for c in get('new-arithmetic-verification.json')['checks'])
scope=get('scope-discovery.json')
for e in scope['scanned_files']:
    p=(ROOT/'trunk/AKRS.ZX2200'/e['file']).resolve()
    assert p.is_relative_to((ROOT/'trunk/AKRS.ZX2200').resolve())
    assert sha(p)==e['sha256'],e['file']
pages=[]
specific={
1:'仅大标题和介绍；无版本日期；封面留白及字形正常。',
2:'原生目录上半；层级、页码和点线对齐，无裁切。',
3:'原生目录下半；正文从下一页开始，无空白页。',
31:'两种补偿层级图及职责表；图中文字与箭头无交叠。',
32:'回零控制流与false分支；分支线分开，标签及图注可读。',
33:'整数转换公式、失败表及标定启停；无孤立图注或公式裁切。',
34:'两点坐标等比例，X跨度标签无缺字；公式及单位清楚。',
35:'两张示教表及调用方对象差异；表头和换行正常。',
36:'分组前提与采集流程图；启动、停止及发布路径清楚。',
37:'原始矩阵、Huber和残差公式；五组公式无重叠或漏字。',
38:'已移动中位数说明标签，避开边界窗口括线；正文和图注完整。',
39:'完整状态表与人工导入流程；未跨页拆表。',
40:'人工均值与自动中位数对比；箭头在标签处留空，无穿字。',
41:'主要接口契约表完整；长接口名称无溢出。',
42:'阅读核对与辅助路径归属；无末段孤页。',
43:'17条精简依据同页；方法短名可读，无单条孤页。',
44:'术语表及新增术语；行高、表头与边界正常。',
45:'27幅图目录独立成页，页码及链接正常。',
46:'20张表目录独立成页，无少量尾项孤页。'}
before=get('before-media-qa.json')
for i in range(1,47):
    p=O/f'review-page-{i:02}.png';assert p.is_file()
    final_hash=sha(p)
    if i not in [38,40,43,44,45,46]:assert final_hash==before[f'final-page-{i:02}.png']
    pages.append(dict(page=i,viewed=True,raster=p.name,raster_sha256=final_hash,
                      result=specific.get(i,'正文、既有工程图或概念插图、公式、图注、表格与页边界逐页查看，未发现未处理的裁切、重叠或缺字。'),
                      evidence='最终重渲染直接查看' if i in [38,40,43,44,45,46] else '已直接查看对应全页；最后同尺寸图像微调后的该页重渲染逐像素一致'))
dump('final-qa.json',dict(complete=True,pdf_sha256=sha(pdf),docx_sha256=sha(O/'纠偏过程设计文档.docx'),page_count=46,
     render='隐藏独立Word实例原生导出；两幅同尺寸图像最后微调仅替换原始PNG流；全46页再次由捆绑Poppler渲染；44页像素一致、2页重新直接查看。',
     raster_location='output/correction-v3.2',pages=pages,
     corrected_issues=['目录后空白页','图中不受字体支持的下标字形','区域平滑图括线与说明交叠','导入平滑图箭头穿过标签','源码附录与末段少量内容孤页'],
     review_kind='代理技术与视觉自检；不等于独立真人试读或用户签收'))

questions=[
('研发','四类生产定位各修改什么','产品父链、焊点偏移和IPT取片记录分别维护',5,'ComponentOffSet'),
('调试','供料重复校正会不会自动回正T','角度参与阈值，循环内主要移动XY，不直接旋转T',8,'ToRequiredAccuracy'),
('研发','八个产品入口是否共用同一跳过条件','S1/S2及层级分别判断，表4-1与表4-2逐项列出',13,'IsDoWork'),
('调试','普通双点上视为什么有四次几何采集','旋转前后各采P1/P2',18,'双点普通'),
('研发','芯片偏移何时用于贴装目标','贴装入口按剩余角旋转再追加',24,'ComponentOffSet'),
('调试','重取检测Retry是否重新执行Pick','标签在Pick之后，只返回检测',23,'RePick'),
('研发','回零true能否证明二维表生效','开关可跳过、固高false不传播；ETEL下载错误另行处理',32,'AllAxisReset'),
('调试','角度示教检查什么距离','仅X跨度，1mm及5度边界按源码判定',34,'Atan'),
('研发','基板示教改变哪个传入对象','窗口改TU坐标，调用方还写基板和配置',35,'AssistantAllRotation'),
('研发','自动采集轮次的索引从哪里来','按TuIndex而非Id分组；焊后生成链未给TuIndex赋值',36,'TuIndex'),
('调试','启用矩阵为何仍可能没有补偿','需生产开关以及起点、间距、矩阵和顺序匹配',38,'IsBondCompensate'),
('研发','自动与人工是否同一平滑算法','Huber后中位数与人工3/5点均值不同',40,'中位数'),
('调试','清空后重启是否一定为空','只置内存null，事件内没有Save',40,'Save')]
walk=[]
for role,q,a,page,token in questions:
    assert token in (reader.pages[page-1].extract_text() or ''),(page,token)
    walk.append(dict(role=role,question=q,answer=a,page=page,passed=True))
dump('reader-walkthrough.json',dict(method='按研发和设备调试问题定位最终PDF页面并核对答案；非独立真人试读',questions=walk))
coverage=get('entry-coverage.json');assert not coverage['known_unassigned_entries']
gates=[
 dict(requirement='三项补入设计文档',passed=True,evidence='第9至11章，PDF31至40页；CN01至CN25'),
 dict(requirement='再深入检查遗漏',passed=True,evidence='1158个C#文件索引、103个候选逐项归属；补入11.4人工导入编辑清空；55条结论；不把索引当作通读'),
 dict(requirement='源码限定目录且只读',passed=True,evidence='全量索引哈希再次一致；所有路径断言在trunk/AKRS.ZX2200；业务源码Git差异为空'),
 dict(requirement='Word与PDF同步',passed=True,evidence='同一正文127段完整匹配；21组原生公式；同尺寸图像更新，两端均使用相同PNG'),
 dict(requirement='图文表达',passed=True,evidence='27图20表；新增6幅SVG/PNG精确工程图；对象、输入、计算、写回、生效与失败有对应章节和图注'),
 dict(requirement='PDF与Word版式',passed=True,evidence='46页全页校样；67项目录/书签和47项图表索引逐项对页；字体嵌入、图像>=300dpi'),
 dict(requirement='新增公式和边界',passed=True,evidence='14项Python复算与18项纯C#数值类检查；既有9组几何公式重新验证'),
 dict(requirement='阅读效率',passed=True,evidence='研发与调试13个问题在最终PDF可定位；精简依据附录1页、图表索引分别成页'),
 dict(requirement='保留封面与清理要求',passed=True,evidence='封面只留大标题和介绍；没有制作说明页，哈希/工具/执行情况与入口证据边界外置'),
 dict(requirement='保留旧版并更新入口',passed=True,evidence='旧v3.1原样保留；新发布v3.2；两册总入口保留TU7.1并切换纠偏3.2')]
dump('acceptance-gates.json',dict(revision='3.2',review_type='文档技术及版式自检',gates=gates,
     runtime_boundary='自动采集窗口的直接打开入口尚不能由限定目录证明；实现已纳入，按辅助流程描述，不声称已接入每轮生产',
     publication='提交与推送由当前仓库和远端Git记录另行验证；此文档不自签Git操作结果'))
dump('source-immutability.json',dict(scope='trunk/AKRS.ZX2200',csharp_files_rechecked=len(scope['scanned_files']),all_hashes_unchanged=True,
     project_sha256=scope['project_sha256'],note='C#哈希由本轮索引逐个重新读取；其他已引用文件另在source-baseline核对'))
print('46-page review, source immutability and requirement gates recorded')
