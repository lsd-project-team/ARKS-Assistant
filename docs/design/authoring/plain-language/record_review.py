"""只在实际看完页面后记录视觉校样；修改页面必须重新查看。"""
from pathlib import Path
from hashlib import sha256
from importlib import import_module
import argparse
import json

from PIL import Image
from build import ROOT, BOOKS


def record(book,baseline,reviewed):
    out=ROOT/'docs/design'/book.FOLDER
    kind='tu' if book.FOLDER.startswith('transport') else 'correction'
    verification=json.loads((out/'verification.json').read_text(encoding='utf-8'))
    pages=[]
    for number in range(1,verification['pages']+1):
        relative=Path(kind)/f'page-{number:02d}.png'
        path=ROOT/'output/design-plain-language'/relative
        with Image.open(path) as image:
            digest=sha256(image.tobytes()).hexdigest()
        same=baseline.get(str(relative))==digest
        # 基线只允许来自已经逐页看过的PNG；像素发生变化的页必须明确重新查看。
        assert same or number in reviewed,('尚未确认查看修改页',kind,number)
        pages.append(dict(page=number,pixels_sha256=digest,
                          review='终稿直接查看' if number in reviewed else '已直接查看的基线与终稿像素一致'))
    result=dict(date='2026-10-26',reviewer='Codex',scope='全页代理视觉校样，不替代真人试读或设备验证',
                render_dpi=110,files=verification['files'],pages=pages,
                corrected_issues=['插图段落固定行高裁切','默认Title蓝色边线',
                                  '坐标图标注避让','可选方式改为并排对照','图注与实际图的对应','取片示意和标签间距'],
                status='通过')
    (out/'visual-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    verification['visual_review']='全页代理视觉校样通过，见visual-review.json及最终文件哈希'
    (out/'verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(f'{kind}: {len(pages)} pages bound to final file hashes')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--baseline',required=True)
    parser.add_argument('--tu',required=True)
    parser.add_argument('--correction',required=True)
    parser.add_argument('--confirm-baseline-reviewed',action='store_true',required=True)
    args=parser.parse_args()
    baseline=json.loads(Path(args.baseline).read_text(encoding='utf-8'))
    for name in BOOKS:
        book=import_module(name)
        selection=args.tu if name=='tu_content' else args.correction
        record(book,baseline,{int(part) for part in selection.split(',') if part})
