"""Structural checks and independent arithmetic, separate from visual review."""
from pathlib import Path
import json,re,hashlib,zipfile,sys,cmath,math
from lxml import etree
from pypdf import PdfReader
import pdfplumber
ROOT=Path(__file__).resolve().parents[4];BASE=ROOT/'output'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def compact(t):return re.sub(r'\s+','',t).replace('\u200b','')
def verify_book(folder,title,expected_equations,revision):
 p=BASE/folder
 sys.path.insert(0,str(Path(__file__).resolve().parent));sys.modules.pop('manuscript',None);sys.modules.pop('refine',None);sys.modules.pop('readability',None);sys.modules.pop('revision',None)
 from manuscript import BLOCKS
 sys.path.pop(0)
 b=json.loads((p/'source-baseline.json').read_text(encoding='utf-8'))
 for f in b['files']:
  assert f['path'].startswith('trunk/AKRS.ZX2200/')
  assert sha(ROOT/f['path'])==f['sha256'],f['id']
  lines=(ROOT/f['path']).read_text(encoding='utf-8-sig').splitlines()
  for a in f['anchors']:assert a['symbol'] in lines[a['line']-1],(f['id'],a)
 z=zipfile.ZipFile(p/(title+'.docx'));x=etree.fromstring(z.read('word/document.xml'))
 ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math','wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'}
 assert any('TOC ' in t for t in x.xpath('//w:instrText/text()',namespaces=ns))
 if folder=='correction-v3.2':
  assert not any(re.search(r'(?<![A-Za-z0-9_])(?:p_o|p_n|U_o|U_n|a_0|T_now|T_goal|R_d)(?![A-Za-z0-9_])',t) for t in x.xpath('//w:t/text()',namespaces=ns))
 math_objects=x.xpath('//m:oMath',namespaces=ns)
 display_equations=[q for q in x.xpath('//w:p[m:oMath]',namespaces=ns) if re.search(r'\(\d+-\d+\)$',''.join(q.xpath('./w:r/w:t/text()',namespaces=ns)))]
 assert len(display_equations)==expected_equations,(folder,len(display_equations))
 marks=set(x.xpath('//w:bookmarkStart/@w:name',namespaces=ns));links=x.xpath('//w:hyperlink/@w:anchor',namespaces=ns)
 assert all(a in marks for a in links)
 figs=[v for k,v in BLOCKS if k=='figure'];tables=[v for k,v in BLOCKS if k=='table']
 alt=x.xpath('//wp:docPr',namespaces=ns);assert len(alt)==len(figs) and all(q.get('descr') for q in alt)
 assert len(x.xpath('//w:tbl',namespaces=ns))==len(tables)
 for tb in x.xpath('//w:tbl',namespaces=ns):assert tb.xpath('./w:tr[1]/w:trPr/w:tblHeader',namespaces=ns)
 reader=PdfReader(p/(title+'.pdf'));pdf=pdfplumber.open(p/(title+'.pdf'));texts=[q.extract_text() or '' for q in pdf.pages]
 assert not any(any(bad in t for bad in ['\ufffd','未找到目录项','未定义书签','Error!','错误!']) for t in texts)
 assert not [(i+1,line) for i,t in enumerate(texts) for line in t.splitlines() if re.fullmatch(r'(?:\[\d+\])+',line.strip())], 'Reference alone on a line'
 assert not any(bad in compact(''.join(texts)) for bad in ['编写说明','源码与算例','交付文件','已读范围','文件哈希','未运行设备','内置生图工具','Word保留可编辑'])
 toc=[];indices=[]
 for n,t in enumerate(texts,1):
  for line in t.splitlines():
   m=re.match(r'^(.+?)\s*\.{3,}\s*(\d+)\s*$',line)
   if not m:continue
   name,dest=m.group(1),int(m.group(2));assert 1<=dest<=len(texts)
   assert compact(name) in compact(texts[dest-1]),(name,dest)
   if name.startswith(('图','表')):indices.append({'title':name,'page':dest})
   else:toc.append({'title':name,'page':dest})
 assert len(toc)==sum(k in ('chapter','section','sub') for k,v in BLOCKS),(len(toc),folder)
 assert len(indices)==len(figs)+len(tables)
 fonts={}
 for page in reader.pages:
  for font in page['/Resources'].get('/Font',{}).values():
   f=font.get_object();embedded=False
   for d in f.get('/DescendantFonts',[f]):
    d=d.get_object();fd=d.get('/FontDescriptor')
    if fd:embedded=embedded or any(k in fd for k in ['/FontFile','/FontFile2','/FontFile3'])
   fonts[str(f.get('/BaseFont'))]=embedded
 assert all(fonts.values())
 heads=sorted({c['fontname'] for page in pdf.pages for c in page.chars if c['size']>12.5 and c['text'].strip()})
 assert all('MicrosoftYaHei-Bold' in n for n in heads),heads
 tocfaces=sorted({c['fontname'] for page in [page for page,t in zip(pdf.pages,texts) if len(re.findall(r'\.{3,}',t))>5] for c in page.chars if c['text'].strip() and 85<c['top']<738})
 assert all('MicrosoftYaHei' in n for n in tocfaces),tocfaces
 layout=[]
 for i,page in enumerate(pdf.pages,1):
  out=[c['text'] for c in page.chars if c['x0']<55 or c['x1']>557 or c['top']<15 or c['bottom']>780]
  assert not out,(i,out)
  layout.append({'page':i,'images':len(page.images),'body_bottom':round(max([c['bottom'] for c in page.chars if 85<c['top']<740]+[im['bottom'] for im in page.images]+[0]),2)})
 assert sum(len(page.images) for page in pdf.pages)==len(figs)
 res=json.loads((p/'image-resolution.json').read_text(encoding='utf-8'));assert len(res)==len(figs) and min(q['effective_dpi'] for q in res)>=300
 # Also compare PDF image stream dimensions with the original-resolution report.
 actual=[(int(im['srcsize'][0]),int(im['srcsize'][1])) for page in pdf.pages for im in sorted(page.images,key=lambda im:im['top'])]
 assert actual==[tuple(q['pixels']) for q in res],actual
 outline=[]
 def walk(items):
  for obj in items:
   if isinstance(obj,list):walk(obj)
   else:outline.append({'title':obj.title,'page':reader.get_destination_page_number(obj)+1})
 walk(reader.outline);assert len(outline)==len(toc)
 report={'revision':revision,'date':'2026-10-21','page_count':len(pdf.pages),'source_files':len(b['files']),'source_baseline_verified':True,'checks':{'native_toc':True,'toc_entries':toc,'bookmarks':outline,'caption_index_page_numbers':indices,'all_fonts_embedded':fonts,'heading_font_faces_in_actual_pdf':heads,'toc_font_faces_in_actual_pdf':tocfaces,'heading_and_toc_font_fallback_absent':True,'linked_reference_targets_valid':True,'word_native_equations':expected_equations,'native_inline_math_count':len(math_objects)-expected_equations,'figures_have_alt_text':True,'tables_repeat_header':True,'no_out_of_page_text':True,'image_resolution':res},'layout':layout,'review':{'visual_status':'pending complete page review','render_pipeline':'独立隐藏Word实例更新字段并原生导出PDF；恢复原始PNG流；捆绑Poppler渲染。捆绑LibreOffice不可用，已尝试规范渲染入口。PDF/A导出选项不代替第三方合规认证。'},'limits':['基于源码静态追踪与独立算例；未运行设备或整套C#业务流程；纯数值类另有C#复算记录','阅读和技术评审用途；说明输入不代表实际配方或设备精度'],'files':{title+ext:{'sha256':sha(p/(title+ext)),'bytes':(p/(title+ext)).stat().st_size} for ext in ['.docx','.pdf','.md']}}
 qa_path=p/'final-qa.json'
 if qa_path.exists():
  qa=json.loads(qa_path.read_text(encoding='utf-8'))
  if qa.get('complete') and qa.get('pdf_sha256')==sha(p/(title+'.pdf')) and qa.get('docx_sha256')==sha(p/(title+'.docx')) and len(qa.get('pages',[]))==len(pdf.pages) and all(q.get('viewed') for q in qa['pages']):
   report['review']['visual_status']='complete; exact current PDF and Word hashes match final-qa.json'
 (p/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(folder,{'pages':len(pdf.pages),'toc':len(toc),'figures':len(figs),'tables':len(tables),'source_files':len(b['files'])})

def arithmetic():
 p=BASE/'correction-v3.2';example_file=p/'arithmetic-examples.json'
 if not example_file.exists():example_file=ROOT/'docs/design/correction-process/v3.2/arithmetic-examples.json'
 r=json.loads(example_file.read_text(encoding='utf-8'));e={x['id']:x for x in r['examples']};checks=[]
 def c(a):return complex(*a)
 def close(z,arr):assert abs(z-c(arr))<1e-10,(z,arr)
 a=e['A01'];i=a['input'];o=a['output'];D=c(i['initial_origin']);old=c(i['old_anchor']);new=c(i['new_anchor']);ang=i['update_angle_rad'];u=D+new;dn=(D+(new-old)-u)*cmath.exp(1j*ang)+u
 close(dn,o['new_origin']);close(dn+old*cmath.exp(1j*ang),o['target_parent_point']);checks.append('A01')
 a=e['A02'];i=a['input'];assert abs(math.atan(i['new_angle_rad']-i['old_angle_rad'])-i['upper_global_angle_rad']-a['output']['actual_rad'])<1e-12;checks.append('A02')
 a=e['A03'];i=a['input'];s=[v for j,v in enumerate(i['angles_deg']) if i['use_angle'][2 if j==3 else j]];assert sum(s)/len(s)==a['output']['actual_mean_deg'];checks.append('A03')
 for key in ['A04','A05']:
  a=e[key];i=a['input'];o=a['output']
  if key=='A04':d=c(i['calibrated_pixel_distance_mm']);m=c(i['machine_position_minus_glass_reference_mm']);angle=i['match_angle_deg']
  else:d=sum(map(c,i['calibrated_pixel_distances_mm']))/2;m=sum(map(c,i['machine_positions_minus_glass_reference_mm']))/2;angle=sum(i['match_angles_deg'])/2
  off=m+d-c(i['taught_center_distance_mm'])*cmath.exp(-1j*math.radians(angle-i['taught_center_angle_deg']))
  close(off,o['ComponentOffSet_mm']);assert angle==o['ComponentAngleOffSet_deg'];checks.append(key)
 a=e['A06'];i=a['input'];o=a['output'];close(c(i['post_rotation_calibrated_pixel_distance_mm'])+c(i['post_rotation_machine_minus_glass_mm'])-c(i['taught_center_distance_mm']),o['ComponentOffSet_mm']);assert -(i['target_global_angle_deg']+i['bond_hard_angle_deg'])==o['ComponentAngleOffSet_deg'];checks.append('A06')
 for key in ['A07','A08']:
  a=e[key];i=a['input'];o=a['output']
  if key=='A07':taught=c(i['taught_mark_mm']);measured=c(i['recognized_mark_in_camera_g0_mm']);angle=i['match_angle_deg']
  else:taught=sum(map(c,i['taught_marks_mm']))/2;measured=sum(map(c,i['recognized_marks_mm']))/2;angle=sum(i['match_angles_deg'])/2
  centre=(c(i['taught_chip_center_mm'])-taught)*cmath.exp(-1j*math.radians(angle+i['taught_downlook_angle_deg']))+measured
  close(centre,o['chip_center_mm']);close(centre+c(i['head_camera_offset_mm'])-c(i['nozzle_offset_at_new_angle_mm']),o['pick_position_g0_mm']);assert i['current_t_deg']-angle==o['pick_axis_t_deg'];checks.append(key)
 a=e['A09'];i=a['input'];o=a['output'];target=i['current_t_deg']+i['ComponentAngleOffSet_deg']+i['target_global_angle_deg']+i['bond_hard_angle_deg'];assert target==o['next_axis_t_deg'];off=c(i['ComponentOffSet_mm'])*cmath.exp(1j*math.radians(target-i['current_t_deg']));close(off,o['xy_addition_mm']);close(off*cmath.exp(-1j*math.radians(target-i['current_t_deg'])),i['ComponentOffSet_mm']);checks.append('A09')
 (p/'arithmetic-verification.json').write_text(json.dumps({'method':'独立Python复数旋转交叉复算；未运行C#或设备','examples_passed':checks,'tolerance':1e-10},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('Independent arithmetic verified:',checks)

if __name__=="__main__":
 verify_book("correction-v3.2","纠偏过程设计文档",21,"3.2")
 arithmetic()
