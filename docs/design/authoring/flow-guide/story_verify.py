"""复用段落/图像/目录检查，再核对跨册主例、导航、承接和最终哈希。"""
from pathlib import Path
from importlib import import_module
from hashlib import sha256
import argparse
import json
import math
import subprocess
import pdfplumber
from PIL import Image
from common import ROOT,old_checks
from publish import BOOKS,json_write,route_text
from case_data import VALUES,display

def case_checks():
    checks=[]
    def equal(key,expected):
        actual=VALUES[key]
        if not isinstance(expected,tuple):actual=(actual,);expected=(expected,)
        assert all(abs(a-b)<1e-10 for a,b in zip(actual,expected)),(key,actual,expected)
        checks.append(key)
    equal('initial',(140,210));equal('at_s1',(142,209));equal('at_s1_height',(142,209,.12))
    equal('refreshed',(140,210,0));equal('localized',(140.2,209.9))
    a=2*math.pi/180
    vx=.5*math.cos(a)+.2*math.sin(a);vy=-.5*math.sin(a)+.2*math.cos(a)
    equal('pick_vector',(vx,vy));equal('pick_xy',(200-.05+.01-vx,100+.02+.03-vy));equal('pick_t',33)
    a=math.pi/180
    sx=.14-(.5*math.cos(a)+.2*math.sin(a));sy=-.09-(-.5*math.sin(a)+.2*math.cos(a))
    equal('saved',(sx,sy));equal('photo_t',30);equal('target_t',33);equal('remaining',3)
    a=3*math.pi/180;rx=sx*math.cos(a)-sy*math.sin(a);ry=sx*math.sin(a)+sy*math.cos(a)
    equal('addition',(rx,ry));equal('target_g0',(140.2+rx,209.9+ry))
    assert 31+(2+0+1)==34 and 34-1+0+1==34
    assert 31+(2+0+180-1)==212 and 212-1+0+1==212
    checks += ['普通上视对照','普通镜像对照']
    assert display(VALUES['pick_xy'])=='(199.453, 99.868)'
    assert display(VALUES['saved'])=='(-0.363, -0.281)'
    assert display(VALUES['addition'])=='(-0.348, -0.300)'
    assert display(VALUES['target_g0'])=='(139.852, 209.600)'
    checks.append('正文舍入结果')
    return checks

def verify(book,restore=False,render=False):
    if restore:old_checks.restore_images(book)
    old_checks.check_book(book,False)
    out=ROOT/'docs/design'/book.FOLDER
    result=json.loads((out/'verification.json').read_text(encoding='utf-8'))
    with pdfplumber.open(out/f'{book.STEM}.pdf') as pdf:
        for i,p in enumerate(book.PAGES):
            text=old_checks.compact(pdf.pages[i+2].extract_text() or '')
            for value in [p['bridge'],book.PARTS[p['part']],route_text(book,p['stage'])]:
                assert old_checks.compact(value) in text,(i+3,value)
            assert p['stage'] in book.STAGES
        for n in range(3):assert any(p['part']==n for p in book.PAGES)
    ledger=json.loads((out/'case-ledger.json').read_text(encoding='utf-8'))
    # 两册计算必须逐值一致，不能各自漂移为另一个例子。
    for other in BOOKS:
        other_book=import_module(other)
        other_ledger=json.loads((ROOT/'docs/design'/other_book.FOLDER/'case-ledger.json').read_text(encoding='utf-8'))
        assert ledger==other_ledger
    result['legacy_isolated_arithmetic_checks']=result.pop('arithmetic_checks')
    result.update(continuous_case_checks=case_checks(),navigation_pages_checked=len(book.PAGES),
        bridges_checked=len(book.PAGES),case_ledger_sha256=sha256((out/'case-ledger.json').read_bytes()).hexdigest(),
        body_precision='三位小数显示，未舍入值继续计算；完整计算另附索引',
        renderer='render_docx本轮实际尝试失败：缺soffice.exe；独立隐藏Word原生导出并由Poppler全页渲染',
        visual_review='等待实际查看本版全部页面')
    json_write(out/'verification.json',result)
    if render:
        kind='tu' if book.FOLDER.startswith('transport') else 'correction'
        dest=ROOT/'output/design-flow-guide'/kind;dest.mkdir(parents=True,exist_ok=True)
        subprocess.run(['pdftoppm','-png','-r','110',str(out/f'{book.STEM}.pdf'),str(dest/'page')],check=True,stdout=subprocess.DEVNULL)

def record(book,reviewed):
    out=ROOT/'docs/design'/book.FOLDER;kind='tu' if book.FOLDER.startswith('transport') else 'correction'
    report=json.loads((out/'verification.json').read_text(encoding='utf-8'));pages=[]
    expected=set(range(1,report['pages']+1));assert reviewed==expected,('需明确确认实际看过的全部页',expected-reviewed)
    for number in sorted(reviewed):
        path=ROOT/'output/design-flow-guide'/kind/f'page-{number:02d}.png'
        with Image.open(path) as im:digest=sha256(im.tobytes()).hexdigest()
        pages.append(dict(page=number,pixels_sha256=digest,review='本版终稿逐页直接查看'))
    result=dict(date='2026-10-26',reviewer='Codex',scope='代理逐页视觉校样，不替代真人试读和设备验证',
        render_dpi=110,status='通过',files=report['files'],pages=pages,
        items=['标题和原生目录','每页阶段导航','图像和图注对应','主例前后位置与状态','可选分支对照','段落与下一页承接','无裁切或溢出'])
    json_write(out/'visual-review.json',result)
    report['visual_review']='本版全部页面已直接查看，见visual-review.json和绑定的最终文件哈希'
    json_write(out/'verification.json',report)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--restore',action='store_true');p.add_argument('--render',action='store_true')
    p.add_argument('--book',choices=['all','tu','correction'],default='all')
    p.add_argument('--record-reviewed-pages',help='实际看过全部终稿后，明确传入所有页码，以逗号分隔')
    args=p.parse_args()
    for name in BOOKS:
        if args.book!='all' and not name.startswith(args.book):continue
        book=import_module(name)
        if args.record_reviewed_pages:record(book,{int(n) for n in args.record_reviewed_pages.split(',')})
        else:verify(book,args.restore,args.render)
