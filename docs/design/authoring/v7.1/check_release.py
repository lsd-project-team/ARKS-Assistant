"""Read-only checks of the two published editions and their scoped evidence."""
from pathlib import Path
import hashlib
import json
import py_compile
import re

ROOT = Path(__file__).resolve().parents[4]
DESIGN = ROOT / 'docs/design'
SCOPE = (ROOT / 'trunk/AKRS.ZX2200').resolve()

def read(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def source(relative):
    path = (ROOT / relative).resolve()
    assert path.is_relative_to(SCOPE), relative
    return path

def check_book(folder, version, expected_pages, expected_claims):
    book = DESIGN / folder / version
    report = read(book / 'verification.json')
    qa = read(book / 'final-qa.json')
    baseline = read(book / 'source-baseline.json')
    claims = read(book / 'claim-map.json')['claims']
    paths = set()
    for entry in baseline['files']:
        p = source(entry['path'])
        assert sha(p) == entry['sha256'], entry['path']
        lines = p.read_text(encoding='utf-8-sig').splitlines()
        assert len(lines) == entry['line_count']
        for anchor in entry['anchors']:
            assert anchor['symbol'] in lines[anchor['line']-1]
        paths.add(entry['path'])
    assert len(claims) == expected_claims
    for claim in claims:
        assert claim['sections'] and claim['conclusion'] and claim['evidence']
        for evidence in claim['evidence']:
            assert evidence['path'] in paths
            p = source(evidence['path'])
            assert sha(p) == evidence['sha256']
            lines = p.read_text(encoding='utf-8-sig').splitlines()
            assert lines[evidence['start']-1].strip() == evidence['start_text']
            assert lines[evidence['end']-1].strip() == evidence['end_text']
    coverage = read(book / 'entry-coverage.json')
    assert not coverage['known_unassigned_entries']
    assert len(coverage['entries']) == 65
    assert sha(SCOPE/'AKRS.ZX2200.csproj') == coverage['compiled_project_sha256']
    for entry in coverage['entries']:
        p = source('trunk/AKRS.ZX2200/'+entry['file'])
        assert sha(p) == entry['sha256']
        assert all(entry[k] for k in ['section','entry_kind','review_conclusion','disposition'])
        lines = p.read_text(encoding='utf-8-sig').splitlines()
        for match in entry.get('matches',[]):
            assert match['text'] == lines[match['line']-1].strip()
    assert report['page_count'] == expected_pages
    assert qa['complete'] and len(qa['pages']) == expected_pages
    assert [p['page'] for p in qa['pages']] == list(range(1,expected_pages+1))
    assert all(p['viewed'] and p['raster_sha256'] for p in qa['pages'])
    for name, info in report['files'].items():
        assert sha(book/name) == info['sha256'], name
        if name.endswith('.pdf'): assert qa['pdf_sha256'] == info['sha256']
        if name.endswith('.md'):
            text = (book/name).read_text(encoding='utf-8')
            assert '\tag{' not in text  # a literal TAB followed by ag is invalid
            assert '\\tag{' in text
    for image in read(book/'illustration-provenance.json')['final_assets']:
        assert sha(book/image['file']) == image['sha256']
    syntax = read(book/'scope-syntax-audit.json')
    assert len(syntax['files']) == 1158
    assert sum(f['compiled'] for f in syntax['files']) == 1137
    assert len(syntax['tu_constructors']) == 35
    assert len({a['type'] for a in syntax['registered_actions'] if a['compiled']}) == 10
    assert not syntax['unassigned_discovered_entry_files']
    for f in syntax['files']:
        assert not f['parse_error'] and sha(source(f['path'])) == f['sha256']
    guards = read(book/'revision-verification.json')
    assert guards['guard_cases'] == 1024 and all(g['passed'] for g in guards['guards'])
    assert len(guards['numeric_examples']) == 10 and all(g['passed'] for g in guards['numeric_examples'])
    gates = read(book/'acceptance-gates.json')
    assert all(gates[k]['passed'] for k in ('source_gate','calculation_gate','reading_gate','visual_gate'))
    assert not gates['publication_pending'] and all(r['closed'] for r in gates['requirements'])
    walk = read(book/'reader-walkthrough.json')
    assert walk['pdf_sha256'] == qa['pdf_sha256']
    assert all(q['location_verified'] for q in walk['questions'])
    assert len(walk['questions']) == (8 if folder == 'transport-unit' else 10)
    for page in qa['pages']:
        raster = ROOT/qa['raster_location']/page['raster']
        if raster.exists(): assert sha(raster) == page['raster_sha256']
    print(folder,version,{'pages':expected_pages,'baseline_files':len(paths),'claims':len(claims),'entries':65})

if __name__ == '__main__':
    check_book('transport-unit','v7.1',39,24)
    check_book('correction-process','v3.1',34,30)
    # Compile syntax only. Do not execute builders or overwrite final publications.
    for p in Path(__file__).parent.rglob('*.py'):
        py_compile.compile(str(p),doraise=True)
    for p in DESIGN.rglob('README.md'):
        if '/v7.1/' not in p.as_posix() and '/v3.1/' not in p.as_posix() and p.parent != DESIGN and p.parent.parent != DESIGN:
            continue
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if '://' not in target and not target.startswith('#'):
                assert (p.parent/target.split('#')[0]).exists(),(p,target)
    print('Release hashes, scoped evidence, entry assignment, source locators, template syntax and README links verified')
