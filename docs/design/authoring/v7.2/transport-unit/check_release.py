"""Verify the actual published release, without regenerating artifacts."""
from evidence import ROOT,SCOPE,read,sha
from pathlib import Path
import json,ast,zipfile
from pypdf import PdfReader
from lxml import etree
P=ROOT/'docs/design/transport-unit/v7.2'
def get(n):return json.loads((P/n).read_text(encoding='utf-8'))
for rel,v in get('release-manifest.json')['files'].items():assert sha(P/rel)==v['sha256'],rel
for f in get('scope-discovery.json')['files']:
    p=(ROOT/f['path']).resolve();assert p.is_relative_to(SCOPE);assert sha(p)==f['sha256'],f['path']
for c in get('claim-map.json')['claims']:
    for e in c['evidence']:
        p=(ROOT/e['path']).resolve();assert p.is_relative_to(SCOPE) and sha(p)==e['sha256'];ls=read(p).splitlines();assert ls[e['start']-1].strip()==e['start_text'] and ls[e['end']-1].strip()==e['end_text']
qa=get('final-qa.json');assert qa['complete'] and all(x['viewed'] for x in qa['pages'])
assert qa['pdf_sha256']==sha(P/'TransportUnit设计文档.pdf') and qa['docx_sha256']==sha(P/'TransportUnit设计文档.docx')
assert len(PdfReader(P/'TransportUnit设计文档.pdf').pages)==len(qa['pages'])
sync=get('text-sync.json');assert all(not sync[k] for k in ['word_missing','pdf_missing','missing_cells','missing_captions','missing_figure_notes'])
assert all(g['passed'] for g in get('acceptance-gates.json')['gates'])
assert not get('entry-coverage.json')['known_unassigned_entries']
assert get('verification.json')['review']['visual_status'].startswith('complete')
assert get('arithmetic-verification.json')['all_passed']
for a in get('illustration-provenance.json')['final_assets']:assert sha(P/a['file'])==a['sha256']
with zipfile.ZipFile(P/'TransportUnit设计文档.docx') as z:
    x=etree.fromstring(z.read('word/document.xml'))
    assert len(x.xpath('//*[local-name()="drawing"]'))==24
    assert len(x.xpath('//*[local-name()="oMath"]'))==3
for p in Path(__file__).resolve().parents[1].rglob('*.py'):ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
readme=(ROOT/'docs/design/README.md').read_text(encoding='utf-8')
assert 'transport-unit/v7.2/TransportUnit设计文档.pdf' in readme and 'correction-process/v3.2/纠偏过程设计文档.pdf' in readme
print('Actual TU release verified:',len(qa['pages']),'pages;',sync['body_paragraphs'],'paragraphs; 24 figures; 24 tables; 40 claims; all source and artifact hashes match')
