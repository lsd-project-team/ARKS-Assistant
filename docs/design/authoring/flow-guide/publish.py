"""连续讲解版的Word Markdown 目录和计算索引来自同一正文。"""
from importlib import import_module
from hashlib import sha256
import argparse
import json
from docx.shared import Pt,RGBColor
from common import ROOT,layout
from story_figures import generate
from case_data import CASE,VALUES

BOOKS=('tu_story','correction_story')

def write(path,text):path.write_text(text,encoding='utf-8',newline='\n')
def json_write(path,value):write(path,json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def sources(book):
    path=ROOT/'docs/design'/book.BASELINE/'source-baseline.json'
    original=json.loads(path.read_text(encoding='utf-8'));checked=[]
    for item in original['files']:
        actual=sha256((ROOT/item['path']).read_bytes()).hexdigest()
        if actual!=item['sha256']:raise ValueError('源码有变化，先重新核查：'+item['path'])
        checked.append(dict(path=item['path'],sha256=actual))
    return dict(date='2026-10-26',revision=book.REVISION,scope='trunk/AKRS.ZX2200',
        prior_baseline=path.relative_to(ROOT).as_posix(),
        verification='沿用已核查的静态结论并重验依据文件哈希；本轮另复核上视及贴装主例公式，不声称重新通读或实机验收',
        files=checked,topics=[dict(page=i+3,title=p['title'],previous_topics=p['old']) for i,p in enumerate(book.PAGES)])

def route_text(book,current):return ' → '.join(('● ' if stage==current else '')+stage for stage in book.STAGES)

def companion(book,out,report,figures):
    previous=ROOT/'docs/design'/book.PREVIOUS
    baseline=ROOT/'docs/design'/book.BASELINE
    old=import_module('tu_content' if book.FOLDER.startswith('transport') else 'correction_content')
    covered={int(n) for p in book.PAGES for n in p['old'].split(';')}
    md=[f'# {book.TITLE} 阅读索引','',book.COVER_NOTE,'',
        '第一部分用于连续阅读。第二部分可以按配置选择，第三部分用于查记录或异常。页码与PDF、Word一致。','',
        '| 本版主题 | 页码 | 上版主题号 |','|---|---:|---|']
    md += [f'| {i:02d} {p["title"]} | {i+2} | {p["old"]} |' for i,p in enumerate(book.PAGES,1)]
    md += ['','旧主题没有在本版单独成页时，仍保留在上版完整说明，以下逐项给出入口。','',
        '| 上版主题 | 本版对应主题 |','|---|---|']
    for i,p in enumerate(old.PAGES,1):
        matches=[f'{j:02d}' for j,q in enumerate(book.PAGES,1) if str(i).zfill(2) in q['old'].split(';')]
        md.append(f'| {i:02d} {p["title"]} | {"、".join(matches) if matches else "参见上版保留说明"} |')
    md += ['',f'- [上版完整图解](../{previous.name}/{book.STEM}.md)',
        f'- [详细技术说明](../{baseline.name}/{book.STEM}.md)',
        f'- [详细源码入口](../{baseline.name}/source-guide.md)',
        f'- [源码核查发现](../{baseline.name}/source-findings.md)',
        '- [本版计算与代码索引](计算与代码索引.md)','- [源码连续性记录](source-continuity.json)','',
        f'本轮重验{len(report["files"])}个依据文件哈希未变。说明数字用数学式独立复算，未运行设备或整套C#业务。','']
    write(out/'阅读索引.md','\n'.join(md))
    numeric=['# 两册共用算例和代码说明','',
        '正文显示大多保留小数点后三位。以下列出未舍入的输入和计算值，图中的中间显示值不重新作为下一步输入。主例中的其他XY补偿为0，轴转换为恒等，轴后实时量为0；Z不在这个说明算例中求实际轴目标。','',
        '## 主例输入','', '```json',json.dumps(CASE,ensure_ascii=False,indent=2),'```','',
        '## 同一轮的结果','', '```json',json.dumps(VALUES,ensure_ascii=False,indent=2),'```','',
        'A点初始(140,210)；S1偏移后(142,209)，测高差0.12；交接刷新后回(140,210,0)，工序保留；S2产品定位后(140.2,209.9)。','',
        '取片T=5−2+30=33。快速上视准备T=0+30=30。贴装T=30+2+0+1=33，剩余3度。芯片偏移先按剩余3度旋转，再加入定位后的A点。取片的33度与最终33度数值相同，但来自不同阶段，不能省掉中间准备角变化。','',
        '## 可选情况的范围','',
        '- TU旋转页只把产品方向改为90度，得到A(90,240)，不接主例继续累加。',
        '- 普通上视准备T=0+0+1+30=31；非镜像相对转3度至34，保存角度−1，贴装仍34。镜像相对转181度至212，保存−1，贴装仍212。',
        '- 中转台例、带转角的产品几何、TU区域网格、温漂和手动测试各自隔离参数，属于标明条件的对照，不接主例继续累加。',
        '- 自动窗口按轮次和位置合并数据、Huber一次权重与残差项、行中位数、人工均值及发布几何的细节，保留在前两版技术说明。','',
        '## 代码名称怎样放回现场','',
        '| 名称 | 对应现场含义 |','|---|---|',
        '| TransportUnit / TU | 当前产品的位置层级和电子加工记录 |',
        '| Index / WorkIndex | 固定结构号 / 本轮加工次序 |',
        '| Info | 当前对象的过程信息，需要确认所属对象与轮次 |',
        '| D_A / T_A | 本例当前A点的点胶 / 固晶工序键 |',
        '| ComponentOffSet | 当前焊点保存的芯片XY偏移，不是绝对目标 |',
        '| ComponentAngleOffSet | 上视分支写入的角度记录，快速与普通含义不同 |',
        '| RealBondPoint3D | 转运动轴前的G0中间记录，仍可能有后续轴补偿 |',
        '| IPTVisionPos / IPTPickPos | 中转台拍照 / 重取目标，写入可早于动作成功 |','',
        '本轮为连贯例子另复核以下调用，没有修改业务源码：','',
        '- UpLookCorrectionActionNode.cs 的准备角、快速单点的中心向量、保存偏移与角度。',
        '- BondActionNode.Provider.cs 的目标T、剩余角旋转、G0追加、区域扣除与轴转换阶段。','',
        f'[上版完整正文](../{previous.name}/{book.STEM}.md)保留全部原主题；[技术版源码核查](../{baseline.name}/source-findings.md)保留入口差异和失败边界。本册为阅读重排，没有用理想行为替换原实现。','']
    write(out/'计算与代码索引.md','\n'.join(numeric))
    json_write(out/'case-ledger.json',dict(inputs=CASE,values=VALUES,display_decimals=3,
        scope='说明数学，非设备参数或实机动作验证',assumptions='其他XY补偿0，轴转换恒等，轴后实时量0，Z另算'))
    main=sum(p['main'] for p in book.PAGES)
    readme=[f'# {book.TITLE} 第{book.REVISION}版','',
        f'先完整走一轮正常流程，再按需读配置与异常。主线共{main}页，完整文档{len(book.PAGES)+2}页，{len(figures)}幅独立插图，封面复用路线图。每页有阶段提示和承接下一页的说明。','',
        '- [阅读PDF]('+book.STEM+'.pdf)','- [可编辑Word]('+book.STEM+'.docx)',
        '- [Markdown正文]('+book.STEM+'.md)','- [阅读索引与旧主题对照](阅读索引.md)',
        '- [完整计算与代码索引](计算与代码索引.md)','- [生成与维护](../../authoring/flow-guide/README.md)','',
        book.CASE_NOTE,'',
        f'源码只读，{len(report["files"])}个依据文件哈希一致。正文、页码、原生目录、字体与图像分辨率核对见verification.json；视觉核对绑定最终文件见visual-review.json。本次不包含设备运行或整套C#验证。','',
        f'[上版保留稿](../{previous.name}/README.md) · [两册总入口](../../README.md)','']
    write(out/'README.md','\n'.join(readme))

def build(book):
    out=ROOT/'docs/design'/book.FOLDER;out.mkdir(parents=True,exist_ok=True)
    report=sources(book);figures=generate(book)
    doc=layout.setup_document(book)
    doc.styles['Heading 1'].font.size=Pt(18)
    doc.styles['Normal'].paragraph_format.line_spacing=Pt(17.5)
    p=layout.paragraph(doc,book.TITLE,style='Title');p.paragraph_format.space_before=Pt(36)
    layout.paragraph(doc,book.INTRO,style='Subtitle')
    layout.add_figure(doc,out/'figures'/f'{book.PAGES[0]["diagram"]}.png',book.PAGES[0]['caption'])
    layout.paragraph(doc,book.COVER_NOTE)
    layout.paragraph(doc,book.CASE_NOTE)
    layout.paragraph(doc,'每页上方可看当前阶段，页末说明下一步。正文先讲设备动作，详细公式和代码入口另放配套索引。')
    doc.add_page_break();layout.paragraph(doc,'阅读顺序和目录',style='Title')
    ends=[max(i+3 for i,p in enumerate(book.PAGES) if p['part']==n) for n in range(3)]
    starts=[min(i+3 for i,p in enumerate(book.PAGES) if p['part']==n) for n in range(3)]
    for n in range(3):
        p=layout.paragraph(doc,f'{book.PARTS[n]}  第{starts[n]}至{ends[n]}页')
        p.paragraph_format.line_spacing=Pt(15);p.paragraph_format.space_after=Pt(3)
        for r in p.runs:r.font.size=Pt(9)
    layout.field(doc.add_paragraph(),'TOC \\o "1-1" \\h \\z \\u')
    md=[f'# {book.TITLE}','',book.INTRO,'',book.COVER_NOTE,'',book.CASE_NOTE,'']
    for i,p in enumerate(book.PAGES,1):
        doc.add_page_break()
        nav=layout.paragraph(doc,book.PARTS[p['part']]);nav.paragraph_format.space_after=Pt(2)
        nav.paragraph_format.line_spacing=Pt(13)
        for r in nav.runs:r.font.size=Pt(9);r.font.color.rgb=RGBColor(100,116,129)
        nav=layout.paragraph(doc,route_text(book,p['stage']));nav.paragraph_format.space_after=Pt(9)
        nav.paragraph_format.line_spacing=Pt(14)
        for r in nav.runs:r.font.size=Pt(9);r.font.color.rgb=RGBColor(36,107,153)
        layout.paragraph(doc,f'{i:02d} {p["title"]}',style='Heading 1')
        layout.paragraph(doc,p['lead'])
        caption=f'图{i} {p["caption"]}'
        layout.add_figure(doc,out/'figures'/f'{p["diagram"]}.png',caption+'。'+p['explain'])
        layout.paragraph(doc,caption,style='Caption')
        layout.paragraph(doc,p['explain']);layout.paragraph(doc,p['detail'])
        layout.paragraph(doc,p['remember'],True)
        bridge=layout.paragraph(doc,p['bridge']);bridge.paragraph_format.space_before=Pt(3)
        for r in bridge.runs:r.font.size=Pt(10.5)
        md.extend([f'# {i:02d} {p["title"]}','',book.PARTS[p['part']],'',route_text(book,p['stage']),'',p['lead'],'',
            f'![{caption}](figures/{p["diagram"]}.png)','',caption,'',p['explain'],'',p['detail'],'',f'**{p["remember"]}**','',p['bridge'],''])
    doc.save(out/f'{book.STEM}.docx');write(out/f'{book.STEM}.md','\n'.join(md))
    json_write(out/'source-continuity.json',report)
    companion(book,out,report,figures)
    metadata=dict(book=book.TITLE,revision=book.REVISION,topics=len(book.PAGES),expected_pages=len(book.PAGES)+2,
        main_topics=sum(p['main'] for p in book.PAGES),unique_figures=len(figures),placements=len(book.PAGES)+1,
        source_files=len(report['files']),part_ranges=[dict(part=book.PARTS[n],first=starts[n],last=ends[n]) for n in range(3)])
    json_write(out/'build-metadata.json',metadata)
    print(json.dumps(metadata,ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--book',choices=['tu','correction','all'],default='all');args=parser.parse_args()
    for name in BOOKS:
        if args.book!='all' and not name.startswith(args.book):continue
        build(import_module(name))
