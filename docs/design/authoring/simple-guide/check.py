"""只做文档相关核对，不运行设备。"""
import argparse,json,re,subprocess,zipfile
from hashlib import sha256
from lxml import etree
from PIL import Image
import pdfplumber
from pypdf import PdfReader
from shared import ROOT,old_checks
from content import BOOKS
from make import save_json

BANNED=['第一部分','第二部分','第三部分','跟着产品完成一轮','下一页','G0','N1','D_A','T_A','WorkIndex','ComponentOffSet','本册将','阅读主线']

def check(book,restore,render):
    out=ROOT/'docs/design'/book.FOLDER;docx=out/f'{book.STEM}.docx';path=out/f'{book.STEM}.pdf'
    if restore:old_checks.restore_images(book)
    report=json.loads((out/'source-continuity.json').read_text(encoding='utf-8'))
    for row in report['files']:assert sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256']
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'}
    with zipfile.ZipFile(docx) as archive:
        xml=etree.fromstring(archive.read('word/document.xml'))
        paras=[p for p in xml.xpath('//w:body/w:p',namespaces=ns) if not any(v.lower().startswith('toc') for v in p.xpath('./w:pPr/w:pStyle/@w:val',namespaces=ns))]
        values=[''.join(p.xpath('.//w:t/text()',namespaces=ns)) for p in paras]
        assert len(xml.xpath('//wp:docPr',namespaces=ns))==len(book.PAGES)+1
        assert all(p.get('descr') for p in xml.xpath('//wp:docPr',namespaces=ns))
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages)==len(book.PAGES)+2,(book.TITLE,len(pdf.pages))
        texts=[p.extract_text() or '' for p in pdf.pages];combined=old_checks.compact(''.join(texts))
        for value in values:
            if value:assert old_checks.compact(value) in combined,value
        for word in BANNED:assert word not in ''.join(texts),word
        toc=texts[1];bounds=[]
        for i,p in enumerate(book.PAGES):
            actual=texts[i+2]
            for key in ['title','lead','caption','explain','note']:
                if p[key]:assert old_checks.compact(p[key]) in old_checks.compact(actual),(i+3,key)
            assert any(re.fullmatch(re.escape(old_checks.compact(p['title']))+r'\.{2,}'+str(i+3),old_checks.compact(line)) for line in toc.splitlines()),p['title']
        assert sum(len(p.images) for p in pdf.pages)==len(book.PAGES)+1
        for i,p in enumerate(pdf.pages):
            outside=[ch['text'] for ch in p.chars if ch['x0']<35 or ch['x1']>565 or ch['top']<10 or ch['bottom']>825]
            assert not outside,(i+1,outside)
            assert not any(w in texts[i] for w in ['\ufffd','Error!','错误!','未定义书签'])
            bounds.append(dict(page=i+1,images=len(p.images)))
        actual=[tuple(im['srcsize']) for p in pdf.pages for im in sorted(p.images,key=lambda im:im['top'])]
    expected=[]
    for name in old_checks.placements(book):
        with Image.open(out/'figures'/f'{name}.png') as im:expected.append(im.size)
    assert actual==expected
    result=dict(book=book.TITLE,revision=book.REVISION,pages=len(book.PAGES)+2,topics=len(book.PAGES),
        paragraphs_checked=len([s for s in values if s]),image_placements=len(expected),unique_figures=len(book.PAGES),
        source_files_unchanged=len(report['files']),fonts=old_checks.check_fonts(PdfReader(path)),
        removed_words_checked=BANNED,layout_bounds=bounds,
        renderer='本轮实际尝试render_docx；缺soffice.exe时用独立隐藏Word原生导出和Poppler逐页渲染',
        visual_review='等待实际逐页查看',files={f'{book.STEM}.{ext}':sha256((out/f'{book.STEM}.{ext}').read_bytes()).hexdigest() for ext in ['pdf','docx','md']})
    save_json(out/'verification.json',result)
    if render:
        kind='tu' if book.FOLDER.startswith('transport') else 'correction';dest=ROOT/'output/design-simple-guide'/kind;dest.mkdir(parents=True,exist_ok=True)
        subprocess.run(['pdftoppm','-png','-r','120',str(path),str(dest/'page')],check=True,stdout=subprocess.DEVNULL)
    print(json.dumps({k:result[k] for k in ['book','pages','topics','paragraphs_checked','image_placements']},ensure_ascii=False))

def record(book,numbers):
    out=ROOT/'docs/design'/book.FOLDER;v=json.loads((out/'verification.json').read_text(encoding='utf-8'))
    assert numbers==set(range(1,v['pages']+1))
    kind='tu' if book.FOLDER.startswith('transport') else 'correction';pages=[]
    for n in sorted(numbers):
        with Image.open(ROOT/'output/design-simple-guide'/kind/f'page-{n:02d}.png') as im:digest=sha256(im.tobytes()).hexdigest()
        pages.append(dict(page=n,pixels_sha256=digest,review='本版页面直接查看'))
    save_json(out/'visual-review.json',dict(date='2026-10-26',status='通过',reviewer='Codex',
        scope='代理逐页校样，不替代真人试读或设备验证',render_dpi=120,files=v['files'],pages=pages))
    v['visual_review']='本版全部页面已直接查看，最终哈希见visual-review.json';save_json(out/'verification.json',v)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--book',choices=['all','tu','correction'],default='all')
    p.add_argument('--restore',action='store_true');p.add_argument('--render',action='store_true');p.add_argument('--reviewed-pages')
    args=p.parse_args()
    for book in BOOKS:
        if args.book=='tu' and not book.FOLDER.startswith('transport'):continue
        if args.book=='correction' and book.FOLDER.startswith('transport'):continue
        if args.reviewed_pages:record(book,{int(n) for n in args.reviewed_pages.split(',')})
        else:check(book,args.restore,args.render)
