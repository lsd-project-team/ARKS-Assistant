"""可重复生成的工程示意图，PNG和SVG使用同一组几何及文字。"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import html
import math

INK = '#172B3A'
BLUE = '#246B99'
GREEN = '#287054'
ORANGE = '#B75D21'
GRAY = '#647481'
LINE = '#B7C6CF'
LIGHT = '#EDF4F8'
PALE = '#EAF4EE'
WARM = '#FFF1E4'


class Canvas:
    def __init__(self, name, out, height=1040):
        self.name, self.out = name, Path(out)
        self.width, self.height = 2400, height
        self.im = Image.new('RGB', (self.width, height), 'white')
        self.d = ImageDraw.Draw(self.im)
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="2400" height="{height}" viewBox="0 0 2400 {height}">', '<rect width="100%" height="100%" fill="white"/>']

    def text(self, x, y, text, size=48, fill=INK, bold=False, anchor='mm'):
        font = ImageFont.truetype('C:/Windows/Fonts/msyhbd.ttc' if bold else 'C:/Windows/Fonts/msyh.ttc', size)
        bounds = self.d.textbbox((x, y), str(text), font=font, anchor=anchor)
        if not (0 <= bounds[0] <= bounds[2] <= self.width and 0 <= bounds[1] <= bounds[3] <= self.height):
            raise ValueError((self.name, text, bounds))
        self.d.text((x, y), str(text), font=font, fill=fill, anchor=anchor)
        alignment = 'middle' if anchor == 'mm' else 'start'
        self.svg.append(f'<text x="{x}" y="{y}" font-family="Microsoft YaHei" font-size="{size}" font-weight="{700 if bold else 400}" text-anchor="{alignment}" dominant-baseline="central" fill="{fill}">{html.escape(str(text))}</text>')

    def lines(self, x, y, lines, size=48, fill=INK, bold=False, gap=74):
        for index, line in enumerate(lines):
            self.text(x, y + index * gap, line, size, fill, bold)

    def rect(self, x, y, w, h, fill='white', stroke=LINE, width=4, radius=0):
        if radius:
            self.d.rounded_rectangle((x, y, x+w, y+h), radius=radius, fill=fill, outline=stroke, width=width)
        else:
            self.d.rectangle((x, y, x+w, y+h), fill=fill, outline=stroke, width=width)
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')

    def line(self, pts, color=LINE, width=5, arrow=False, dash=False):
        if dash:
            for (x1,y1),(x2,y2) in zip(pts,pts[1:]):
                length = math.hypot(x2-x1,y2-y1)
                if not length:
                    continue
                for start in range(0,int(length),30):
                    end=min(start+16,length)
                    self.d.line([(x1+(x2-x1)*start/length,y1+(y2-y1)*start/length), (x1+(x2-x1)*end/length,y1+(y2-y1)*end/length)], fill=color,width=width)
        else:
            self.d.line(pts, fill=color, width=width)
        dashes = ' stroke-dasharray="16 14"' if dash else ''
        self.svg.append('<polyline points="'+' '.join(f'{x},{y}' for x,y in pts)+f'" stroke="{color}" stroke-width="{width}" fill="none"{dashes}/>')
        if arrow:
            x,y=pts[-1]; prev_x,prev_y=pts[-2]
            angle=math.atan2(y-prev_y,x-prev_x)
            points=[(x,y),(x-27*math.cos(angle-.45),y-27*math.sin(angle-.45)),(x-27*math.cos(angle+.45),y-27*math.sin(angle+.45))]
            self.poly(points,color,color)

    def poly(self, pts, fill, stroke=LINE, width=4):
        self.d.polygon(pts, fill=fill)
        self.d.line(pts+[pts[0]], fill=stroke, width=width)
        self.svg.append('<polygon points="'+' '.join(f'{x},{y}' for x,y in pts)+f'" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')

    def circle(self,x,y,r=15,fill=ORANGE,stroke=None,width=4):
        self.d.ellipse((x-r,y-r,x+r,y+r),fill=fill,outline=stroke or fill,width=width)
        self.svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke or fill}" stroke-width="{width}"/>')

    def box(self,x,y,w,h,title,sub='',fill=LIGHT):
        self.rect(x,y,w,h,fill,radius=12)
        lines = sub.split('\n') if sub else []
        self.text(x+w/2,y+(h/2 if not lines else 64),title,54,bold=True)
        for index,line in enumerate(lines):
            self.text(x+w/2,y+145+index*68,line,44,GRAY)

    def arrow(self,x1,y1,x2,y2,color=BLUE):
        self.line([(x1,y1),(x2,y2)],color,7,True)

    def save(self):
        self.out.mkdir(parents=True,exist_ok=True)
        self.im.save(self.out/f'{self.name}.png',dpi=(360,360),optimize=True)
        (self.out/f'{self.name}.svg').write_text('\n'.join(self.svg)+'</svg>\n',encoding='utf-8',newline='\n')


def chip(c,x,y,w=150,angle=0,color=ORANGE):
    h=w*.72
    corners=[(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]
    rad=math.radians(angle)
    pts=[(x+a*math.cos(rad)-b*math.sin(rad),y+a*math.sin(rad)+b*math.cos(rad)) for a,b in corners]
    c.poly(pts,WARM,color,5)
    c.circle(x,y,9,color)
    c.circle(pts[0][0]*.75+x*.25,pts[0][1]*.75+y*.25,8,BLUE)


def camera(c,x,y,up=False):
    c.rect(x-70,y-45,140,90,LIGHT,BLUE,5,12)
    c.circle(x,y,29,'white',BLUE,5)
    end=y-100 if up else y+100
    c.line([(x-40,y-45 if up else y+45),(x,end),(x+40,y-45 if up else y+45)],BLUE,5)


def nozzle(c,x,y,holding=False,angle=0):
    c.rect(x-42,y-130,84,95,'#DCE5EB',GRAY,5)
    c.poly([(x-25,y-35),(x+25,y-35),(x+15,y),(x-15,y)],'#C5D5DF',GRAY,5)
    if holding:
        chip(c,x,y+52,150,angle)


def board(c,x,y,w=880,h=380,selected=True,labels=True):
    c.rect(x,y,w,h,PALE,GREEN,6,14)
    for row in range(2):
        for col in range(3):
            left=x+35+col*(w-55)/3
            top=y+35+row*(h-50)/2
            cw=(w-110)/3;ch=(h-100)/2
            c.rect(left,top,cw,ch,'white',GREEN,3)
            for j,letter in enumerate(['A','B']):
                px=left+cw*(.3+.4*j);py=top+ch*.52
                c.circle(px,py,14,ORANGE)
                if labels:
                    c.text(px,py+42,letter,32)
                if selected and row==0 and col==1 and j==0:
                    c.circle(px,py,31,'white',BLUE,6)
                    c.circle(px,py,13,ORANGE)


def conveyor(c,x,y,width=900):
    c.rect(x,y,width,110,'#EEF1F3',GRAY,5,45)
    for i in range(8):
        c.circle(x+65+i*(width-130)/7,y+55,32,'white',LINE,3)


def flow(c,labels,subs=None,y=300,colors=None):
    n=len(labels);left=65;gap=70;w=(2270-(n-1)*gap)/n
    for index,title in enumerate(labels):
        x=left+index*(w+gap)
        c.box(x,y,w,250,title,(subs or ['']*n)[index],(colors or [LIGHT]*n)[index])
        c.circle(x+40,y-35,29,BLUE)
        c.text(x+40,y-35,str(index+1),37,'white',True)
        if index<n-1:
            c.arrow(x+w+9,y+125,x+w+gap-9,y+125)


def two_lanes(c,top,bottom,top_title='',bottom_title=''):
    c.text(1200,85,top_title,54,bold=True)
    flow(c,top,y=180)
    c.text(1200,555,bottom_title,54,bold=True)
    flow(c,bottom,y=650,colors=[PALE]*len(bottom))


def numeric_steps(c,items,title='',footer='',arrows=True):
    c.text(1200,70,title,54,bold=True)
    count=len(items);width=2180/count
    for i,(heading,lines) in enumerate(items):
        x=110+width*i
        c.text(x+width/2,210,heading,52,BLUE,True)
        c.lines(x+width/2,360,lines,48,gap=96)
        if i<count-1 and arrows:
            c.arrow(x+width-85,525,x+width+75,525)
    if footer:
        c.text(1200,c.height-100,footer,49,ORANGE,True)


def ledger(c,x,y,title,rows,w=960):
    c.text(x+w/2,y,title,54,bold=True)
    top=y+80
    for i,(name,value) in enumerate(rows):
        c.rect(x,top+i*132,w,132,PALE if 'true' in value or '完成'==value else 'white')
        c.text(x+42,top+i*132+66,name,46,anchor='lm')
        c.text(x+w-310,top+i*132+66,value,46,BLUE,anchor='lm')


def scene_pair(c,left_title,right_title,left_kind='board',right_kind='chip'):
    for x,title,kind in [(600,left_title,left_kind),(1800,right_title,right_kind)]:
        c.text(x,90,title,56,bold=True)
        if kind=='board':
            camera(c,x,300);board(c,x-470,520,940,330)
        elif kind=='wafer':
            c.circle(x,610,230,PALE,GREEN,6)
            for row in [-1,0,1]:
                for col in [-1,0,1]:
                    chip(c,x+col*120,610+row*110,75)
            camera(c,x,270)
        elif kind=='tray':
            c.rect(x-390,480,780,380,PALE,GREEN,5)
            for i in range(3):
                for j in range(2):chip(c,x-260+i*260,585+j*160,115)
            camera(c,x,280)
        elif kind=='chip':
            nozzle(c,x,360,True,12);camera(c,x,730,True)
        elif kind=='ipt':
            c.rect(x-360,650,720,80,PALE,GREEN,5)
            chip(c,x,610,190,12);camera(c,x,300)
        c.line([(x-450,930),(x+450,930)],LINE,3)


def graph(c,x,y,w,h,points,labels=None,color=BLUE,connect=True):
    """点位图的X/Y使用相同比例；标签在调用处留出空间。"""
    c.arrow(x,y+h,x+w,y+h,GRAY);c.arrow(x,y+h,x,y,GRAY)
    c.text(x+w-15,y+h+58,'X',42,GRAY)
    c.text(x-45,y+25,'Y',42,GRAY)
    min_x,max_x=min(p[0] for p in points),max(p[0] for p in points)
    min_y,max_y=min(p[1] for p in points),max(p[1] for p in points)
    scale=min((w-160)/max(max_x-min_x,1e-6),(h-160)/max(max_y-min_y,1e-6))
    mapped=[(x+80+(a-min_x)*scale,y+h-80-(b-min_y)*scale) for a,b in points]
    if connect:c.line(mapped,color,6,True)
    for i,(px,py) in enumerate(mapped):
        c.circle(px,py,17,color)
        if labels:c.text(px+40,py-45,labels[i],42,color,anchor='lm')
    return mapped
