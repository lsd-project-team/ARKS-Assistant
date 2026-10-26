"""发布核对：正文一致、图像清晰、目录页码、源码连续性及独立数值复算。"""
from pathlib import Path
from hashlib import sha256
from importlib import import_module
import argparse
import io
import json
import math
import re
import subprocess
import zipfile
import zlib

from PIL import Image
from lxml import etree
import pdfplumber
from pypdf import PdfReader, PdfWriter
from pypdf.generic import IndirectObject, NameObject, NumberObject

from build import ROOT, BOOKS


def compact(text):
    return re.sub(r'\s+','',text).replace('\u200b','')


def placements(book):
    names=[book.PAGES[0]['diagram']]
    for page in book.PAGES:
        names.append(page['diagram'])
        if page['extra']:names.append(page['extra'])
    return names


def restore_images(book):
    """Word可能压缩插图；按阅读顺序恢复同尺寸的原始PNG流。"""
    out=ROOT/'docs/design'/book.FOLDER
    path=out/f'{book.STEM}.pdf'
    with pdfplumber.open(path) as pdf:
        used=[dict(obj=img['stream'].objid,page=number+1,width=img['width'],height=img['height'])
              for number,page in enumerate(pdf.pages)
              for img in sorted(page.images,key=lambda image:image['top'])]
    names=placements(book)
    assert len(names)==len(used),(book.TITLE,len(names),len(used))
    reader=PdfReader(io.BytesIO(path.read_bytes()))
    restored=[]
    for placement,name in zip(used,names):
        image=Image.open(out/'figures'/f'{name}.png').convert('RGB')
        ratio=(image.width/image.height)/(placement['width']/placement['height'])
        assert abs(ratio-1)<.002,(name,ratio)
        stream=IndirectObject(placement['obj'],0,reader).get_object()
        stream.clear()
        stream.update({NameObject('/Type'):NameObject('/XObject'),NameObject('/Subtype'):NameObject('/Image'),
                       NameObject('/Width'):NumberObject(image.width),NameObject('/Height'):NumberObject(image.height),
                       NameObject('/ColorSpace'):NameObject('/DeviceRGB'),NameObject('/BitsPerComponent'):NumberObject(8),
                       NameObject('/Filter'):NameObject('/FlateDecode')})
        stream._data=zlib.compress(image.tobytes(),9)
        stream.decoded_self=None
        restored.append(dict(figure=name,page=placement['page'],pixels=[image.width,image.height],
                             dpi=round(image.width/(placement['width']/72),1)))
    writer=PdfWriter();writer.clone_document_from_reader(reader)
    with path.open('wb') as handle:writer.write(handle)
    assert min(row['dpi'] for row in restored)>=300
    (out/'image-resolution.json').write_text(json.dumps(restored,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


def arithmetic():
    """用独立数学式核对文中说明输入，不运行设备或业务流程。"""
    def rotate(x,y,degrees):
        angle=math.radians(degrees)
        return x*math.cos(angle)-y*math.sin(angle),x*math.sin(angle)+y*math.cos(angle)
    def close(actual,expected):
        assert len(actual)==len(expected)
        assert all(abs(a-b)<.0000011 for a,b in zip(actual,expected)),(actual,expected)
    checks=[]
    a=rotate(40,10,90);close((100+a[0],200+a[1]),(90,240));checks.append('TU逐层与90度旋转')
    close((90+2,240-1,0+.12),(92,239,.12));checks.append('TU工位偏移与测高')
    assert 2*3*2==12 and 1+2+6+12==21;checks.append('产品对象及焊点数量')
    assert [1,2,3,6,5,4][3]==6;checks.append('蛇形第四加工对象')
    v=rotate(.5,.2,-2)
    close((200-.05+.01-v[0],100+.02+.03-v[1]),(199.453325,99.867572));checks.append('静态华夫盒取片XY')
    assert 5-2+30==33 and 5+2+30==37;checks.append('翻转与未翻转取片角')
    v=rotate(.5,.2,-1);quick=(.14-v[0],-.09-v[1])
    close(quick,(-.363414,-.281243));checks.append('快速上视保存偏移')
    added=rotate(*quick,8);close(added,(-.320736,-.329084));checks.append('快速偏移剩余8度旋转')
    close((100+added[0],200+added[1]),(99.679264,199.670916));checks.append('快速例追加G0目标')
    assert 29+(2+5+1)==37 and 37-6+5+1==37;checks.append('普通非镜像角度追踪')
    assert 29+(2+5+180-1)==215 and 215-6+5+1==215;checks.append('普通镜像角度追踪')
    v=rotate(1,0,-3);center=(100.1+v[0],199.9+v[1])
    close(center,(101.098630,199.847664))
    close((center[0]+2-.05,center[1]-1+.02),(103.048630,198.867664));checks.append('中转台中心与取片G0')
    close((math.atan(1/20),math.degrees(math.atan(1/20))),(.0499584,2.862405));checks.append('两点角度示教单位')
    close((math.atan(.1),),(.09966865,));checks.append('产品两点定角保留Atan')
    close(((.01+.03+.02+.04)/4,100-.025,200),(.025,99.975,200));checks.append('TU网格中心与相减符号')
    import statistics
    row=[0,.01,1,.03,.04]
    med=[statistics.median(row[max(0,i-2):min(5,i+3)]) for i in range(5)]
    close(med,[.01,.02,.03,.035,.04]);checks.append('自动行中位数边界')
    avg=[row[0],sum(row[:3])/3,sum(row)/5,sum(row[2:])/3,row[-1]]
    close(avg,[0,.336667,.216,.356667,.04]);checks.append('人工导入3点与5点均值')
    close(((10+20+30)/3/1000*.5,),(.01,));checks.append('焊后样本单位与比例')
    close((100+.1+.1,200-.2-.2),(100.2,199.6));checks.append('手动目标独立路径')
    # 先平移锚点，再围绕新锚点旋转的说明几何。
    dx,dy=100+.2-110.2,200+.1-200.1
    rad=.01
    origin=(dx*math.cos(rad)-dy*math.sin(rad)+110.2,dx*math.sin(rad)+dy*math.cos(rad)+200.1)
    close(origin,(100.200500,200.000002));checks.append('产品锚点平移旋转说明模型')
    return checks


def check_fonts(reader):
    fonts={}
    for page in reader.pages:
        for indirect in page['/Resources'].get('/Font',{}).values():
            font=indirect.get_object();embedded=False
            for item in font.get('/DescendantFonts',[font]):
                descriptor=item.get_object().get('/FontDescriptor')
                if descriptor:embedded |= any(key in descriptor for key in ['/FontFile','/FontFile2','/FontFile3'])
            fonts[str(font.get('/BaseFont'))]=embedded
    assert all(fonts.values()),fonts
    return fonts


def check_book(book,render=False):
    out=ROOT/'docs/design'/book.FOLDER
    docx=out/f'{book.STEM}.docx';pdf_path=out/f'{book.STEM}.pdf'
    reader=PdfReader(pdf_path)
    report=json.loads((out/'source-continuity.json').read_text(encoding='utf-8'))
    for item in report['files']:
        assert sha256((ROOT/item['path']).read_bytes()).hexdigest()==item['sha256']
    namespace={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
               'wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'}
    with zipfile.ZipFile(docx) as archive:
        xml=etree.fromstring(archive.read('word/document.xml'))
        # Word目录的点线是排版生成的；正文逐段核对，目录另按标题与页码核对。
        body_paragraphs=[p for p in xml.xpath('//w:body/w:p',namespaces=namespace)
                         if not any(style.lower().startswith('toc') for style in p.xpath('./w:pPr/w:pStyle/@w:val',namespaces=namespace))]
        paragraphs=[''.join(p.xpath('.//w:t/text()',namespaces=namespace)) for p in body_paragraphs]
        shapes=xml.xpath('//wp:docPr',namespaces=namespace)
        assert len(shapes)==len(placements(book)) and all(shape.get('descr') for shape in shapes)
        assert any('TOC ' in text for text in xml.xpath('//w:instrText/text()',namespaces=namespace))
    with pdfplumber.open(pdf_path) as pdf:
        texts=[page.extract_text() or '' for page in pdf.pages]
        assert len(pdf.pages)==len(book.PAGES)+2,(book.TITLE,len(pdf.pages))
        combined=compact(''.join(texts))
        missing=[p for p in paragraphs if p and compact(p) not in combined]
        assert not missing,missing[:3]
        topic_pages=[]
        for index,topic in enumerate(book.PAGES):
            actual_page=index+3;heading=f'{index+1:02d} {topic["title"]}'
            assert compact(heading) in compact(texts[actual_page-1]),(actual_page,heading)
            for key in ['lead','explain','detail','remember']:
                assert compact(topic[key]) in compact(texts[actual_page-1]),(actual_page,key)
            topic_pages.append(dict(topic=index+1,title=topic['title'],page=actual_page))
        toc_text=texts[1]
        for row in topic_pages:
            assert compact(row['title']) in compact(toc_text),row
            assert re.search(re.escape(row['title'])+r'\s*\.{2,}\s*'+str(row['page'])+r'(?:\s|$)',toc_text),row
        assert sum(len(p.images) for p in pdf.pages)==len(placements(book))
        bounds=[]
        for index,page in enumerate(pdf.pages):
            assert not any(bad in texts[index] for bad in ['\ufffd','Error!','错误!','未定义书签','未找到目录项'])
            outside=[ch['text'] for ch in page.chars if ch['x0']<35 or ch['x1']>565 or ch['top']<10 or ch['bottom']>825]
            assert not outside,(index+1,outside)
            body=[ch for ch in page.chars if 42<ch['top']<795]
            bounds.append(dict(page=index+1,body_bottom=round(max([ch['bottom'] for ch in body]+[0]),2),images=len(page.images)))
        actual_images=[(int(im['srcsize'][0]),int(im['srcsize'][1])) for page in pdf.pages for im in sorted(page.images,key=lambda row:row['top'])]
    expected_images=[]
    for name in placements(book):
        with Image.open(out/'figures'/f'{name}.png') as image:expected_images.append(image.size)
    assert actual_images==expected_images
    result=dict(book=book.TITLE,revision=book.REVISION,pages=len(reader.pages),topics=len(book.PAGES),
                unique_figures=len(set(placements(book))),image_placements=len(placements(book)),
                text_paragraphs_checked=len([p for p in paragraphs if p]),
                source_files_unchanged=len(report['files']),fonts=check_fonts(reader),topic_pages=topic_pages,
                layout_bounds=bounds,arithmetic_checks=arithmetic(),
                renderer='Word原生导出；规范render_docx实际尝试，缺soffice.exe；采用原生PDF和Poppler全页渲染',
                visual_review='等待实际逐页查看',
                files={f'{book.STEM}.{suffix}':sha256((out/f'{book.STEM}.{suffix}').read_bytes()).hexdigest() for suffix in ['docx','pdf','md']})
    (out/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    if render:
        dest=ROOT/'output/design-plain-language'/('tu' if book.FOLDER.startswith('transport') else 'correction')
        dest.mkdir(parents=True,exist_ok=True)
        subprocess.run(['pdftoppm','-png','-r','110',str(pdf_path),str(dest/'page')],check=True,stdout=subprocess.DEVNULL)
    print(json.dumps({k:result[k] for k in ['book','pages','unique_figures','image_placements','text_paragraphs_checked','source_files_unchanged']},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--restore',action='store_true');parser.add_argument('--render',action='store_true')
    parser.add_argument('--book',choices=['tu','correction','all'],default='all')
    args=parser.parse_args()
    for name in BOOKS:
        if args.book=='tu' and name!='tu_content':continue
        if args.book=='correction' and name!='correction_content':continue
        book=import_module(name)
        if args.restore:restore_images(book)
        check_book(book,args.render)
