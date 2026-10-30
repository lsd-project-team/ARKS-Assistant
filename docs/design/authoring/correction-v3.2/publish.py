"""Publish verified artifacts while preserving the retained editions."""
from pathlib import Path
import json,hashlib,shutil,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3];O=ROOT/'output/correction-v3.2';P=ROOT/'docs/design/correction-process/v3.2'
sys.path.insert(0,str(H));from manuscript import BLOCKS
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
qa=read(O/'final-qa.json');v=read(O/'verification.json');g=read(O/'acceptance-gates.json')
assert qa['complete'] and len(qa['pages'])==46 and all(x['viewed'] for x in qa['pages'])
assert qa['pdf_sha256']==sha(O/'纠偏过程设计文档.pdf')
assert qa['docx_sha256']==sha(O/'纠偏过程设计文档.docx')
assert all(x['passed'] for x in g['gates'])
for name,record in v['files'].items():assert sha(O/name)==record['sha256']
for name in [
'纠偏过程设计文档.pdf','纠偏过程设计文档.docx','纠偏过程设计文档.md',
'source-baseline.json','source-analysis.json','claim-map.json','source-guide.md','source-findings.md',
'scope-discovery.json','entry-coverage.json','entry-coverage.md','source-immutability.json',
'calculator-csharp.json','calculator-reference.json','new-arithmetic-verification.json',
'arithmetic-examples.json','arithmetic-verification.json','verification.json','text-sync.json',
'image-resolution.json','final-qa.json','reader-walkthrough.json','acceptance-gates.json',
'media-pixel-comparison.json','media-refresh.json']:
    shutil.copy2(O/name,P/name)
structure=read(O/'book-structure.json');structure['source_files']=len(read(P/'source-baseline.json')['files'])
dump(P/'book-structure.json',structure)
figures=[b for k,b in BLOCKS if k=='figure'];keys={b[0] for b in figures}
# Remove only unused files in this newly created edition; old editions are read-only.
fig_root=(P/'figures').resolve()
for path in fig_root.iterdir():
    assert path.resolve().is_relative_to(fig_root)
    if path.is_file() and path.suffix in ['.svg','.png'] and path.stem not in keys:path.unlink()
for path in fig_root.glob('*.svg'):
    path.write_bytes(path.read_bytes().replace(b'\r\n',b'\n'))
provenance=read(P/'illustration-provenance.json');provenance['revision']='3.2'
provenance['final_assets']=[dict(file='figures/'+b[0]+'.png',sha256=sha(fig_root/(b[0]+'.png'))) for b in figures]
provenance['engineering_additions']=[dict(figure=b[1],png='figures/'+b[0]+'.png',svg='figures/'+b[0]+'.svg',
    sha256_png=sha(fig_root/(b[0]+'.png')),sha256_svg=sha(fig_root/(b[0]+'.svg')),
    method='Python按同一坐标精确绘制PNG与SVG；计算、参考系与控制流逐项核对') for b in figures if b[0].startswith(('c24','c25','c26','c27','c28','c29'))]
provenance['final_review']='沿用并核对既有三幅内置生图概念场景；新增六幅精确工程图。最终修正缺字、括线/标注重叠及箭头穿字，全部页面校样。'
dump(P/'illustration-provenance.json',provenance)
lines=['# 纠偏第3.2版文档验收自检','','本记录针对设计文档的源码依据、计算、阅读与版式，不代替设备验证或用户签收。','',
'| 要求 | 本轮结果与证据 |','|---|---|']
for gate in g['gates']:lines.append('|'+gate['requirement']+'|'+gate['evidence']+'|')
lines+=['','## 交付与章节定位','','- 设备轴二维补偿：31至33页，图9-1/9-2、表9-1/9-2。',
'- 两点角度示教：34至35页，图10-1、表10-1/10-2。','- 区域补偿表自动生成与人工维护：36至40页，图11-1至11-3、表11-1。',
'- 辅助标定与诊断归属：42页，表12-3。','',
'## 范围和证据边界','','新增三项实现及人工维护路径全部有正文归属。自动采集窗口直接打开入口尚不能由本目录证明，已明确为辅助实现的证据边界；不能以窗口存在证明生产自动调用。',
'现有56个源码依据文件哈希和原结论锚点一致；本轮依据文件共80个，关键结论55条，其中25条新增。当前全目录索引1158个C#文件、103个候选文件归属完成；索引不等同于逐文件业务通读。',
'纯CompensateCalculator类18项C#复算通过；新增14项独立Python图示/边界和既有9组几何公式复算通过。未运行设备、整套C#业务或外部驱动SDK。',
'最终46页全部校样；末次同尺寸标注调整后46页重渲染，44页像素一致，38及40页重新直接查看。详细逐页证据见final-qa.json。',
'本轮保留旧版并切换两册总入口。Git提交与推送以实际仓库和远端记录为准。','']
(P/'acceptance-audit.md').write_text('\n'.join(lines),encoding='utf-8')
# The edition's .gitattributes preserves canonical text bytes on Windows and
# fresh clones; binary PDFs, Word documents and PNGs are never normalized.
for path in P.rglob('*'):
    if path.is_file() and path.suffix in ['.md','.json','.svg']:
        path.write_bytes(path.read_bytes().replace(b'\r\n',b'\n'))
manifest={}
for path in sorted(P.rglob('*')):
    if path.is_file() and path.name!='release-manifest.json':manifest[path.relative_to(P).as_posix()]=dict(sha256=sha(path),bytes=path.stat().st_size)
dump(P/'release-manifest.json',dict(revision='3.2',files=manifest))
print('Published verified correction 3.2:',len(manifest),'files; old editions retained')
