from pathlib import Path
import sys,zipfile,re,json,unicodedata
from lxml import etree
import pdfplumber
H=Path(__file__).resolve().parent;ROOT=H.parents[4];O=ROOT/'output/design-publication-v7.2/transport-unit'
sys.path.insert(0,str(H));from manuscript import BLOCKS
def norm(s):
    s=re.sub(r'\*\*([^*]+)\*\*',r'\1',s)
    s=re.sub(r'(?<![A-Za-z0-9_])(p_o|p_n|U_o|U_n|a_0|a_off|T_now|T_goal|R_d)(?![A-Za-z0-9_])',lambda m:m[0].replace('_',''),s)
    return re.sub(r'\s+','',unicodedata.normalize('NFKC',s)).replace('\u200b','')
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
with zipfile.ZipFile(O/'TransportUnit设计文档.docx') as z:x=etree.fromstring(z.read('word/document.xml'))
word=norm(''.join(x.xpath('//w:t/text()|//m:t/text()',namespaces=ns)))
with pdfplumber.open(O/'TransportUnit设计文档.pdf') as pdf:
    # Native OMML subscripts sit a few points below the text baseline. Keep them
    # in their parent line instead of treating them as a separate following line.
    pdftext=norm(''.join(p.crop((60,50,557,745)).extract_text(layout=False,y_tolerance=6) or '' for p in pdf.pages))
    # Global PDF text walks across columns before completing a wrapped cell.
    # Read actual ruled table cells geometrically instead of relaxing the match.
    grids=[t for p in pdf.pages for t in p.extract_tables()]
    pdfcells=[norm(c or '') for grid in grids for row in grid for c in row]
paras=[v for k,v in BLOCKS if k=='p']
word_missing=[v for v in paras if norm(v) not in word]
pdf_missing=[v for v in paras if norm(v) not in pdftext]
report=dict(body_paragraphs=len(paras),word_missing=word_missing,pdf_missing=pdf_missing,
            method='逐段正文去空白及统一兼容字符；只规范生成器明确转换的数学下标，PDF移除页眉页脚后检索整段')
captions=[v[1] for k,v in BLOCKS if k=='figure']+[v[0] for k,v in BLOCKS if k=='table']
cells=[t for k,v in BLOCKS if k=='table' for row in [v[1]]+v[2] for t in row]
notes=[v[2] for k,v in BLOCKS if k=='figure']
report['caption_count']=len(captions);report['table_cells']=len(cells);report['figure_notes']=len(notes)
report['missing_captions']=[t for t in captions if norm(t) not in word or norm(t) not in pdftext]
report['missing_word_cells']=[t for t in cells if norm(t) not in word]
report['missing_pdf_cells']=[t for t in cells if not any(norm(t)==c for c in pdfcells)]
report['geometric_pdf_tables']=len(grids)
report['missing_cells']=report['missing_word_cells']+report['missing_pdf_cells']
report['missing_figure_notes']=[t for t in notes if norm(t) not in word or norm(t) not in pdftext]
(O/'text-sync.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert not word_missing and not pdf_missing and not report['missing_captions'] and not report['missing_cells'] and not report['missing_figure_notes'],report
print(f'All {len(paras)} manuscript paragraphs preserved in Word and PDF')
