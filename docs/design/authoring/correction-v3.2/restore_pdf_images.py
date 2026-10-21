"""Preserve original illustration resolution without changing Word's page layout."""
from pathlib import Path
import io,zlib,json
from PIL import Image
import pdfplumber
from pypdf import PdfReader,PdfWriter
from pypdf.generic import IndirectObject,NameObject,NumberObject
from manuscript import BLOCKS

TMP=Path(__file__).resolve().parents[4]/'output/correction-v3.2';path=TMP/'纠偏过程设计文档.pdf'
plates=[v for k,v in BLOCKS if k=='figure']
with pdfplumber.open(path) as pdf:
    # Match document reading order, including the two plates on the coordinate page.
    placed=[dict(page=i+1,obj=m['stream'].objid,width=m['width'],height=m['height']) for i,p in enumerate(pdf.pages) for m in sorted(p.images,key=lambda x:x['top'])]
assert len(placed)==len(plates)
reader=PdfReader(io.BytesIO(path.read_bytes()));report=[]
for use,plate in zip(placed,plates):
    key,caption,description,width=plate
    im=Image.open(Path(__file__).resolve().parents[4]/'docs/design/correction-process/v3.2/figures'/(key+'.png')).convert('RGB')
    assert abs((im.width/im.height)/(use['width']/use['height'])-1)<.002,(key,use)
    stream=IndirectObject(use['obj'],0,reader).get_object()
    assert stream['/Subtype']=='/Image'
    stream.clear()
    stream.update({NameObject('/Type'):NameObject('/XObject'),NameObject('/Subtype'):NameObject('/Image'),NameObject('/Width'):NumberObject(im.width),NameObject('/Height'):NumberObject(im.height),NameObject('/ColorSpace'):NameObject('/DeviceRGB'),NameObject('/BitsPerComponent'):NumberObject(8),NameObject('/Filter'):NameObject('/FlateDecode')})
    stream._data=zlib.compress(im.tobytes(),9)
    stream.decoded_self=None
    report.append(dict(file='figures/'+key+'.png',page=use['page'],pixels=[im.width,im.height],display_inches=round(use['width']/72,4),effective_dpi=round(im.width/(use['width']/72),2)))
writer=PdfWriter();writer.clone_document_from_reader(reader)
temp=TMP/'original-resolution.pdf'
with temp.open('wb') as f:writer.write(f)
temp.replace(path)
(TMP/'image-resolution.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert min(x['effective_dpi'] for x in report)>=300
print(f'All {len(plates)} original illustration streams restored at >=300 dpi; layout retained')
