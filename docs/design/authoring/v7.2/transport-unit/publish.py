"""Publish only after direct review of every rendered final page."""
from evidence import ROOT,TMP,sha,dump
from pathlib import Path
import json,shutil,argparse
from pypdf import PdfReader
def get(n):return json.loads((TMP/n).read_text(encoding='utf-8'))
parser=argparse.ArgumentParser();parser.add_argument('--confirm-all-pages-viewed',action='store_true');args=parser.parse_args()
assert args.confirm_all_pages_viewed,'Finish the direct final-page review first'
P=ROOT/'docs/design/transport-unit/v7.2'; title='TransportUnit设计文档'
v=get('verification.json');sync=get('text-sync.json');n=len(PdfReader(TMP/(title+'.pdf')).pages)
assert n==v['page_count'] and not sync['word_missing'] and not sync['pdf_missing']
for key in ['missing_cells','missing_captions','missing_figure_notes']:assert not sync[key]
pages=ROOT/'output/tu-recheck/approved-pages'
assert len(list(pages.glob('page-*.png')))==n
continuity=json.loads((ROOT/'output/tu-recheck/visual-continuity.json').read_text(encoding='utf-8'))
assert len(continuity['pages'])==n
dump('visual-continuity.json',continuity)
dump('final-qa.json',dict(complete=True,method='Word独立隐藏实例更新目录与导出；恢复原图像流；Poppler 120dpi全页渲染及逐页校样；迭代后未变页逐像素确认与已阅页一致，变更页重新直接查看',canonical_renderer='render_docx.py已实际执行；日志报soffice.exe缺失，因此使用本机原生Word渲染后检查，未声明LibreOffice通过',pdf_sha256=sha(TMP/(title+'.pdf')),docx_sha256=sha(TMP/(title+'.docx')),pages=[dict(page=i,viewed=True,png_sha256=sha(pages/f'page-{i:02}.png'),checks='标题、正文、公式、图注、表格和页码校样；无遮挡或截断',review=continuity['pages'][i-1]['review']) for i in range(1,n+1)],repaired=['目录尾项孤页','图表索引尾部孤页','交接异常表与实例快照表仅一行落前页','重复收尾段落孤页','8.3小节标题与首段跨页'],remaining_defects=[]))
v['review']['visual_status']='complete; all actual final pages directly viewed and bound to final-qa.json';dump('verification.json',v)
questions=[
 ('一份产品由哪些对象组成','TU根、基板、基岛、焊点；每层独立Info，焊点独立步骤。','3.1、3.4'),
 ('同名A点会共用生产记录吗','配置可共享，Info与完成字典归各自运行对象。','3.1'),
 ('当前位置从哪里来','当前父坐标链逐层变换；区分局部、G0与运动轴。','4、7.6'),
 ('刷新是否创建新产品','不创建运行对象；替换坐标并清几何标记，保留步骤。','6.1、7.1'),
 ('清空载具是否把所有状态复位','清对应区段引用和有料状态；不统一清消息、移送状态或缓存别名。','6.10'),
 ('异形编辑是否立即重建区段TU','配置编辑和视图Init不直接重建旧运行树；结构变化须重建。','5.5'),
 ('同名新节点能否反查旧TU','不能据同名保证；接口比较节点对象引用，未命中抛异常。','7.6'),
 ('关闭新Mapping是否已经保存文件','关闭写回仅更新内存参与配置；该事件及SaveInformation未调用配方Save。','5.6'),
 ('生产Mapping修改的是谁','区段当前TU，参与状态与焊点步骤按选择层级处理。','5.6、8.3'),
 ('补偿模式是否保留旧产品','先替换为Ntest，Enable且配置输送时还会再建Ns2。','6.11'),
 ('两点示教只修改所选层吗','窗口先改传入对象，调用方再改其他运行角或配置；各入口目标不同。','8.7'),
 ('失败或取消会恢复什么','按各出口已经发生的赋值判断；交接、配置写回及示教没有统一事务回滚。','8.2、8.6、8.7'),
]
dump('reader-walkthrough.json',dict(method='代理按研发评审与设备调试角色定位阅读，未冒充独立真人试读',questions=[dict(question=q,answer=a,sections=s,located=True) for q,a,s in questions]))
requirements=[
 ('五类遗漏与节点反查补齐','5.5、5.6、6.10、6.11、7.6、8.7','正文及图5-3、5-4、6-6、6-7、7-2、8-3'),
 ('继续深入核查','40条结论，16条本轮新增；78个依据文件','claim-map.json、source-analysis.json、source-baseline.json'),
 ('源码范围且业务只读','限定trunk/AKRS.ZX2200，所有C#当前哈希重验','scope-discovery.json；发布前Git无trunk差异'),
 ('更新正文 PDF Word且内容同步',str(sync['body_paragraphs'])+'段正文、全部图注与表格单元格','text-sync.json、verification.json'),
 ('配图清楚','24图，新增6幅精确工程图；保留既有概念生图','image-resolution.json、illustration-provenance.json'),
 ('排版整齐','最终全部页面渲染并逐页查看，原生目录与书签核对','final-qa.json、verification.json'),
 ('保留旧版及更新入口','第7.1版及纠偏册保持原文件','根入口与Git差异核对')]
dump('acceptance-gates.json',dict(scope='trunk/AKRS.ZX2200',gates=[dict(requirement=q,coverage=c,evidence=e,passed=True) for q,c,e in requirements],limitations='静态源码、数值复算与代理阅读/版式检查；未运行整套C#业务或设备，未替代用户签收'))
for f in (P/'figures').glob('*.svg'):
    f.write_text(f.read_text(encoding='utf-8-sig'),encoding='utf-8',newline='\n')
old=json.loads((ROOT/'docs/design/transport-unit/v7.1/illustration-provenance.json').read_text(encoding='utf-8'))
old['engineering']='保留第7.1版18图；本轮新增6幅精确工程图，逐图核对对象归属、条件和写入次序。未重绘既有概念生图。'
old['final_assets']=[dict(file='figures/'+p.name,sha256=sha(p)) for p in sorted((P/'figures').glob('*.png'))]
old['engineering_additions']=[dict(png='figures/'+p.name,svg='figures/'+p.with_suffix('.svg').name,sha256_png=sha(p),sha256_svg=sha(p.with_suffix('.svg'))) for p in sorted((P/'figures').glob('p2[1-6]-*.png'))]
old['assets_sha256']={'figures/'+p.name:sha(p) for p in sorted((P/'figures').iterdir()) if p.is_file()}
dump('illustration-provenance.json',old)
findings='''# Transport Unit 第7.2版源码核查发现

范围严格限定trunk/AKRS.ZX2200，业务源码只读。扫描与实际语义核读分别记录，不以1158文件扫描声称全项目理解。

- 三个主动清空入口按方法区分整线五区段、点胶段及固晶段；清引用与NoMaterial不等于全部消息及移送状态复位。
- 新旧配方Mapping与真实生产Mapping的数据拥有者不同。新窗口关闭只把参与状态写回内存；SaveInformation与关闭事件未调用配方Save。旧窗口关闭调用保存回调。写回异常仅弹窗，可能部分修改。
- 关闭配方Mapping后IsExistTu检查全部五区段；仍需通过控制器工作/暂停检查与人工确认才能清空。
- 异形新增、删除、复制、清空修改配置节点树；Init重排配置ID与刷新界面，没有直接重建旧运行树。编程页面存在实际入口，不能仅看主菜单里被注释的入口就认定不可达。
- 克隆接口外部实现不展开；本目录调用方仅增加平移、修改显示名，没有独立改ConfigName。删除按节点引用执行，选中配置名无其他引用才清对应公共配置与四个Mark PR。
- 节点反查比较配置节点对象引用，未命中抛异常。同名、同ID或同ConfigName不能替代原节点。
- GetAllBondPositionConfigs最内层加入的是基岛节点。本目录有效调用未发现，不能据此宣称已发生生产故障。GetModuleCount返回各板最大基岛数，空基板集合会抛异常。
- 两点角度窗口与调用方可能修改不同层级。在线窗口先改传入坐标并Save；调用方在后续条件下继续复制。焊点入口在开角度窗口前已先置配置角0；后续取消没有统一回滚。离线OK不代表新角已计算。
- System2TUService从固晶区段取TU；GetSubstratePos继续转运动轴，GetModulePos仍返回G0，焊点辅助以基岛当前父链和配置点计算，不能替代生产当前焊点位姿。
- 补偿工作先创建字符串参数Ntest，再在Enable且配置输送时创建Ns2。辅助窗口局部TU与区段当前对象分开，未复制原生产记录。

本轮新增16条关键结论，旧24条保留并重新验证当前哈希与锚点。方法级入口清单191项、候选文件91项；完整已读范围见source-analysis.json，不把候选归属当作整文件深读。
'''
(TMP/'source-findings.md').write_text(findings,encoding='utf-8',newline='\n')
readme=f'''# Transport Unit设计文档 第7.2版

面向软件研发、技术评审与设备调试人员。PDF共{n}页，24幅图、24张表；新增6幅工程图。封面仅大标题和介绍。

- [阅读PDF]({title}.pdf)与[可编辑Word]({title}.docx)：同一维护正文，原生目录、公式、引用及图表索引。
- [维护正文]({title}.md)与figures：正文和PNG/SVG图源。
- [源码核查发现](source-findings.md)、[方法级入口](entry-coverage.md)、[验收记录](acceptance-audit.md)。
- source-baseline.json、claim-map.json、source-analysis.json、source-guide.md：78个依据文件、40条结论及已读区段与哈希。
- scope-discovery.json：1158个C#文件、1137个编译项、91个候选文件现态核对；entry-coverage.json列191项方法级归属。扫描不代表全文件业务理解。
- arithmetic-verification.json：12项独立数值核对；text-sync.json：{sync['body_paragraphs']}段正文、图注及表格单元格的Word/PDF一致性。
- final-qa.json、verification.json、acceptance-gates.json：当前最终文件哈希、全页直接校样、目录/索引/书签、字体与原图分辨率。
- illustration-provenance.json：既有概念生图来源和新增工程图哈希。

制作日期、哈希、阅读范围、绘图方法、运行限制与交付用途仅保留在配套资料。未运行设备或整套C#业务，未开展独立真人试读，代理自检不替代用户签收。

旧版见[7.1](../v7.1/README.md)，[两册入口](../../README.md)，[维护模板](../../authoring/v7.2/README.md)。
'''
(TMP/'README.md').write_text(readme,encoding='utf-8',newline='\n')
audit=f'''# Transport Unit第7.2版验收自检

已确认的遗漏按主题补齐，保留旧版，源码严格限定目录且只读。正式文档没有恢复制作说明页。

| 项目 | 实际结果 |
|---|---|
| 内容 | 5.5异形编辑、5.6两类Mapping、6.10三种清空、6.11辅助及补偿模式、7.6节点反查与位置服务、8.7示教写回 |
| 源码 | 78个依据文件、40条结论；新增16条实际核读范围，旧24条当前哈希及锚点复核 |
| 入口 | 1158个C#现态及Compile重验；91个候选文件、191个方法级归属；不作全目录逐文件理解声明 |
| 内容同步 | {sync['body_paragraphs']}段正文、全部图注、48项图表标题和表格单元格一致 |
| 数值 | 12项独立数值核对通过；不当作设备精度或整套C#执行结果 |
| 图文 | 24图24表，新增6幅工程图；原始图像至少300dpi |
| 排版 | 当前{n}页全部120dpi渲染并逐页直接查看；修复目录及索引孤页、两张表的一行断页及8.3首段跨页 |
| 导航 | 67项目录/书签、48项图表索引核对；可编辑Word保留原生公式 |

核查与代理阅读、版式自检已完成；未进行独立真人试读或设备运行，不能冒充用户签收。最终哈希及逐页记录见final-qa.json。
'''
(TMP/'acceptance-audit.md').write_text(audit,encoding='utf-8',newline='\n')
(P/'.gitattributes').write_text('* text=auto eol=lf\n*.png binary\n*.pdf binary\n*.docx binary\n',encoding='utf-8',newline='\n')
for f in TMP.iterdir():
    if f.is_file():
        if f.suffix in ['.json','.md','.svg','.txt']:f.write_text(f.read_text(encoding='utf-8-sig'),encoding='utf-8',newline='\n')
        shutil.copy2(f,P/f.name)
manifest={p.relative_to(P).as_posix():dict(sha256=sha(p),bytes=p.stat().st_size) for p in sorted(P.rglob('*')) if p.is_file() and p.name!='release-manifest.json'}
(P/'release-manifest.json').write_text(json.dumps(dict(revision='7.2',files=manifest),ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print('Published',n,'pages; final hashes bound; old release untouched')
