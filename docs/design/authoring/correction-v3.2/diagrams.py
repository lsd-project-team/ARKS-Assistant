from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import math,html,shutil,json
OUT=Path(__file__).resolve().parents[4]/'docs/design/correction-process/v3.2/figures'
OUT.mkdir(exist_ok=True)
C={'ink':'#162e43','muted':'#4d6070','line':'#a5b5c1','tu':'#edf0f3','sub':'#eaf4ed','mod':'#eaf1f9','bp':'#fff0df','blue':'#245b87','green':'#356d4a','orange':'#b65f17'}
class Canvas:
    def __init__(self,name,h):
        self.name=name;self.w=2400;self.h=h
        self.im=Image.new('RGB',(self.w,h),'white');self.d=ImageDraw.Draw(self.im)
        self.svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="2400" height="{h}" viewBox="0 0 2400 {h}"><rect width="100%" height="100%" fill="white"/>']
    def text(self,x,y,s,size=48,color=None,bold=False,anchor='mm'):
        f=ImageFont.truetype('C:/Windows/Fonts/msyhbd.ttc' if bold else 'C:/Windows/Fonts/msyh.ttc',size)
        bounds=self.d.textbbox((x,y),s,font=f,anchor=anchor)
        assert bounds[0]>=0 and bounds[1]>=0 and bounds[2]<self.w and bounds[3]<self.h,(self.name,s,bounds)
        self.d.text((x,y),s,font=f,fill=color or C['ink'],anchor=anchor)
        self.svg.append(f'<text x="{x}" y="{y}" fill="{color or C["ink"]}" font-family="Microsoft YaHei" font-size="{size}" font-weight="{700 if bold else 400}" text-anchor="{"middle" if anchor=="mm" else "start"}" dominant-baseline="central">{html.escape(s)}</text>')
    def rect(self,x,y,w,h,fill='white',stroke=None,width=3):
        self.d.rectangle((x,y,x+w,y+h),fill=fill,outline=stroke or C['line'],width=width)
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke or C["line"]}" stroke-width="{width}"/>')
    def line(self,pts,color=None,width=4,arrow=False,dash=False):
        color=color or C['muted']
        if dash:
            for (x1,y1),(x2,y2) in zip(pts,pts[1:]):
                length=math.hypot(x2-x1,y2-y1)
                for a in range(0,int(length),24):
                    b=min(a+12,length)
                    self.d.line([(x1+(x2-x1)*a/length,y1+(y2-y1)*a/length),(x1+(x2-x1)*b/length,y1+(y2-y1)*b/length)],fill=color,width=width)
        else:self.d.line(pts,fill=color,width=width)
        self.svg.append('<polyline points="'+' '.join(f'{x},{y}' for x,y in pts)+f'" fill="none" stroke="{color}" stroke-width="{width}"'+(' stroke-dasharray="12 12"' if dash else '')+'/>')
        if arrow:
            (x1,y1),(x,y)=pts[-2:];a=math.atan2(y-y1,x-x1);sz=23
            poly=[(x,y),(x-sz*math.cos(a-.45),y-sz*math.sin(a-.45)),(x-sz*math.cos(a+.45),y-sz*math.sin(a+.45))]
            self.d.polygon(poly,fill=color);self.svg.append('<polygon points="'+' '.join(f'{u},{v}' for u,v in poly)+f'" fill="{color}"/>')
    def dot(self,x,y,r=12,color=None):
        col=color or C['orange'];self.d.ellipse((x-r,y-r,x+r,y+r),fill=col);self.svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}"/>')
    def box(self,x,y,w,h,title,sub='',fill=None):
        self.rect(x,y,w,h,fill or C['mod'])
        self.text(x+w/2,y+h/2-(30 if sub else 0),title,52,bold=True)
        if sub:self.text(x+w/2,y+h/2+38,sub,44,color=C['muted'])
    def save(self):
        self.im.save(OUT/(self.name+'.png'),dpi=(360,360));(OUT/(self.name+'.svg')).write_text('\n'.join(self.svg)+'</svg>',encoding='utf-8')
