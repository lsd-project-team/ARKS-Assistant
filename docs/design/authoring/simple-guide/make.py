"""生成只含具体动作和必要说明的两册阅读稿。"""
from hashlib import sha256
from importlib import import_module
from pathlib import Path
import argparse,json
from docx.shared import Pt
from shared import ROOT,layout
from content import BOOKS
from pictures import generate

def write(path,text):path.write_text(text,encoding='utf-8',newline='\n')
def save_json(path,obj):write(path,json.dumps(obj,ensure_ascii=False,indent=2)+'\n')

def sources(book):
    baseline=ROOT/'docs/design'/book.BASELINE/'source-baseline.json'
    files=[]
    for row in json.loads(baseline.read_text(encoding='utf-8'))['files']:
        actual=sha256((ROOT/row['path']).read_bytes()).hexdigest()
        if actual!=row['sha256']:raise ValueError('源码已变化，需重新核查：'+row['path'])
        files.append(dict(path=row['path'],sha256=actual))
    return dict(date='2026-10-26',revision=book.REVISION,baseline=baseline.relative_to(ROOT).as_posix(),
        scope='沿用已核查静态结论，重验依据文件哈希；不是实机验收',files=files,
        topics=[dict(page=i+3,title=p['title'],previous_topics=p['refs']) for i,p in enumerate(book.PAGES)])

def companion(book,out,report):
    previous=Path(book.PREVIOUS).name;baseline=Path(book.BASELINE).name
    old=import_module('tu_content' if book.FOLDER.startswith('transport') else 'correction_content')
    md=[f'# {book.TITLE} 配套资料','',
        '阅读稿用具体动作说明设备运行。完整计算、接口、配置差异和失败边界保留在既有技术资料中，以下提供对应入口。','',
        '| 阅读稿主题 | 页码 | 上一版主题号 |','|---|---:|---|']
    md += [f'| {p["title"]} | {i+3} | {"、".join(str(n) for n in p["refs"])} |' for i,p in enumerate(book.PAGES)]
    md += ['',f'- [上一版完整正文](../{previous}/{book.STEM}.md)',
        f'- [上一版计算与代码索引](../{previous}/计算与代码索引.md)',
        f'- [上一版全部主题对照](../{previous}/阅读索引.md)',
        f'- [详细技术说明](../{baseline}/{book.STEM}.md)',
        f'- [源码入口](../{baseline}/source-guide.md)',f'- [源码核查发现](../{baseline}/source-findings.md)',
        '- [本轮源码哈希核对](source-continuity.json)','',
        'Mapping、异形结构、分段点胶、示教、镜像、各类补偿表及软件返回边界等细节，仍由上述完整资料查阅。阅读稿没有把省略的例外改写成统一行为。','',
        f'本轮{len(report["files"])}个依据文件哈希未变。修改范围只有文档和生成源，没有运行设备或整套C#业务。','']
    write(out/'配套资料.md','\n'.join(md))
    readme=[f'# {book.TITLE} 第{book.REVISION}版','',
        f'{len(book.PAGES)+2}页。正文每页一个设备动作或具体问题，使用大图和短句；已去掉分部名称、阶段导航、重复过渡和正文公式。','',
        f'- [PDF](%s.pdf)'%book.STEM,f'- [可编辑Word](%s.docx)'%book.STEM,f'- [Markdown正文](%s.md)'%book.STEM,
        '- [详细技术资料入口](配套资料.md)','- [生成与检查](../../authoring/simple-guide/README.md)','',
        book.SCOPE,'',
        '正文与图注一致、原生目录、页码、字体和图像清晰度见verification.json；逐页视觉确认绑定最终文件见visual-review.json。当前只包含静态文档核对，未进行实机验收。','',
        f'[上一版保留稿](../{previous}/README.md) · [两册入口](../../README.md)','']
    write(out/'README.md','\n'.join(readme))

def make(book):
    out=ROOT/'docs/design'/book.FOLDER;out.mkdir(parents=True,exist_ok=True)
    report=sources(book);generate(book)
    doc=layout.setup_document(book)
    doc.sections[0].header.paragraphs[0].text=''
    layout.set_font(doc.styles['Normal'],14)
    doc.styles['Normal'].paragraph_format.line_spacing=Pt(24)
    doc.styles['Normal'].paragraph_format.space_after=Pt(13)
    layout.set_font(doc.styles['Heading 1'],21,True)
    doc.styles['Heading 1'].paragraph_format.line_spacing=Pt(29)
    layout.set_font(doc.styles['Caption'],11.5)
    doc.styles['Caption'].paragraph_format.line_spacing=Pt(18)
    doc.styles['Caption'].paragraph_format.space_after=Pt(15)
    p=layout.paragraph(doc,book.TITLE,style='Title');p.paragraph_format.space_before=Pt(36)
    layout.paragraph(doc,book.INTRO,style='Subtitle')
    layout.add_figure(doc,out/'figures'/f'{book.PAGES[0]["diagram"]}.png',book.PAGES[0]['caption'])
    layout.paragraph(doc,book.SCOPE)
    doc.add_page_break();layout.paragraph(doc,'目录',style='Title')
    layout.field(doc.add_paragraph(),'TOC \\o "1-1" \\h \\z \\u')
    md=[f'# {book.TITLE}','',book.INTRO,'',book.SCOPE,'']
    for p in book.PAGES:
        doc.add_page_break();layout.paragraph(doc,p['title'],style='Heading 1')
        layout.paragraph(doc,p['lead'])
        layout.add_figure(doc,out/'figures'/f'{p["diagram"]}.png',p['caption']+'。'+p['explain'])
        layout.paragraph(doc,p['caption'],style='Caption')
        layout.paragraph(doc,p['explain'])
        if p['note']:layout.paragraph(doc,p['note'])
        md.extend([f'# {p["title"]}','',p['lead'],'',f'![{p["caption"]}](figures/{p["diagram"]}.png)','',p['caption'],'',p['explain'],''])
        if p['note']:md.extend([p['note'],''])
    doc.save(out/f'{book.STEM}.docx');write(out/f'{book.STEM}.md','\n'.join(md))
    save_json(out/'source-continuity.json',report);companion(book,out,report)
    meta=dict(book=book.TITLE,revision=book.REVISION,topics=len(book.PAGES),expected_pages=len(book.PAGES)+2,
        unique_figures=len(book.PAGES),image_placements=len(book.PAGES)+1,source_files=len(report['files']),
        body_chars=sum(len(p['lead']+p['explain']+p['note']) for p in book.PAGES),
        editing='去掉分部与导航、过渡句、正文坐标公式和代码字段；完整技术说明保留在配套资料')
    save_json(out/'build-metadata.json',meta);print(json.dumps(meta,ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--book',choices=['all','tu','correction'],default='all');args=parser.parse_args()
    for book in BOOKS:
        if args.book=='tu' and not book.FOLDER.startswith('transport'):continue
        if args.book=='correction' and book.FOLDER.startswith('transport'):continue
        make(book)
