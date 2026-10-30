"""All business source reads are confined to the explicitly requested tree."""
from pathlib import Path
import hashlib, json, re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
SCOPE=(ROOT/'trunk/AKRS.ZX2200').resolve()
OUT=ROOT/'output/correction-v3.2'
CONFIG=json.loads((HERE/'source-groups.json').read_text(encoding='utf-8'))
GROUPS=[(g['number'],g['title'],g['purpose'],g['source_ids']) for g in CONFIG]

def build():
    OUT.mkdir(parents=True,exist_ok=True)
    files=[]
    for rel in dict.fromkeys(p for _,_,_,paths in GROUPS for p in paths):
        path=(SCOPE/rel).resolve()
        assert path.is_relative_to(SCOPE),path
        raw=path.read_bytes(); lines=raw.decode('utf-8-sig').splitlines()
        anchors=[dict(line=i,symbol=s.strip()) for i,s in enumerate(lines,1)
                 if re.search(r'^\s*(?:public|private|protected|internal).*(?:\(| class | enum )',s)]
        files.append(dict(id=rel,path='trunk/AKRS.ZX2200/'+rel,
                          sha256=hashlib.sha256(raw).hexdigest(),line_count=len(lines),
                          anchors=anchors or [dict(line=1,symbol='字段定义')]))
    data=dict(date='2026-10-21',revision='3.2',scope='trunk/AKRS.ZX2200',
              external_dependencies='仅核对本目录内的调用包装；不解析目录外的硬件SDK或坐标库',
              files=files,reference_groups=CONFIG)
    (OUT/'source-baseline.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return data
