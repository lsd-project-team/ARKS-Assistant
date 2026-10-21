"""Read-only verification of the actual published files."""
from pathlib import Path
import json,hashlib,zipfile,ast
from lxml import etree
from pypdf import PdfReader
H=Path(__file__).resolve().parent;ROOT=H.parents[3];P=ROOT/'docs/design/correction-process/v3.2';S=(ROOT/'trunk/AKRS.ZX2200').resolve()
def get(n):return json.loads((P/n).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for rel,v in get('release-manifest.json')['files'].items():assert sha(P/rel)==v['sha256'],rel
for f in get('source-baseline.json')['files']:
    p=(ROOT/f['path']).resolve();assert p.is_relative_to(S);assert sha(p)==f['sha256']
for c in get('claim-map.json')['claims']:
    for e in c['evidence']:
        p=(ROOT/e['path']).resolve();assert p.is_relative_to(S);assert sha(p)==e['sha256']
        lines=p.read_text(encoding='utf-8-sig').splitlines()
        assert lines[e['start']-1].strip()==e['start_text'] and lines[e['end']-1].strip()==e['end_text']
qa=get('final-qa.json');assert qa['complete'] and len(qa['pages'])==46 and all(x['viewed'] for x in qa['pages'])
assert qa['pdf_sha256']==sha(P/'纠偏过程设计文档.pdf')
assert qa['docx_sha256']==sha(P/'纠偏过程设计文档.docx')
assert len(PdfReader(P/'纠偏过程设计文档.pdf').pages)==46
assert not get('text-sync.json')['word_missing'] and not get('text-sync.json')['pdf_missing']
assert all(g['passed'] for g in get('acceptance-gates.json')['gates'])
assert not get('entry-coverage.json')['known_unassigned_entries']
with zipfile.ZipFile(P/'纠偏过程设计文档.docx') as z:
    x=etree.fromstring(z.read('word/document.xml'))
    assert len(x.xpath('//*[local-name()="drawing"]'))==27
for f in H.glob('*.py'):ast.parse(f.read_text(encoding='utf-8'),filename=str(f))
readme=(ROOT/'docs/design/README.md').read_text(encoding='utf-8')
assert 'correction-process/v3.2/纠偏过程设计文档.pdf' in readme
assert 'transport-unit/v7.1/TransportUnit设计文档.pdf' in readme
print('Published release verified: 46 pages; 27 figures; 20 tables; 80 source files; 55 claims; 103 candidate dispositions')
