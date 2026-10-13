import pymupdf as f, sys
sys.path.insert(0,'.')
from PIL import Image, ImageDraw, ImageFont
from sq8 import FONTS10
MM=72/25.4; dpi=140
F1=ImageFont.truetype('npm/package/dist/public/static/alternative/Pretendard-SemiBold.ttf',24)
F2=ImageFont.truetype('npm/package/dist/public/static/alternative/Pretendard-Regular.ttf',19)
rows=[('00','Million Dreams (현재)','v7/Squeeze_내지_03-01-06(Solving 아이콘 복원).pdf','Squeeze 로고 글꼴. 장식적인 세리프')]
rows+=[(c,n,f'v7/fonts/번호글꼴_{c}_{n}.pdf',desc) for c,n,_,desc in FONTS10]
def crop(d,i,r):
    pm=d[i].get_pixmap(dpi=dpi,clip=f.Rect(*[v*MM for v in r])); return Image.frombytes('RGB',(pm.width,pm.height),pm.samples)
cols=[('짝수쪽 번호',2,(14,33,100,52)),('홀수쪽 번호',3,(66,33,113,58)),('Logic Check 목록',0,(132,38,200,72))]
data=[]
for c,n,p,desc in rows:
    d=f.open(p); data.append((c,n,desc,[crop(d,i,r) for _,i,r in cols]))
cw=[max(r[3][j].width for r in data) for j in range(3)]; rh=[max(x.height for x in r[3]) for r in data]
Wd=40+390+sum(cw)+60
B=Image.new('RGB',(Wd,70+sum(h+24 for h in rh)),(236,234,230)); dr=ImageDraw.Draw(B)
x=430
for j,(n,_,_) in enumerate(cols): dr.text((x,20),n,font=F2,fill=(70,70,70)); x+=cw[j]+20
y=60
for (c,n,desc,cs),h in zip(data,rh):
    dr.text((20,y+6),f'{c}  {n}',font=F1,fill=(25,25,25)); dr.text((20,y+40),desc,font=F2,fill=(90,90,90))
    x=430
    for j,im in enumerate(cs): B.paste(im,(x,y)); x+=cw[j]+20
    y+=h+24
B.save('v7/번호글꼴_10종_견본.png'); print(B.size)
