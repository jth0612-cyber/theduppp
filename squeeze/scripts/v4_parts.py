# 요소별 후보 비교(행=묶음 A/B/C, 열=요소). 인쇄 크기 비율 유지.
import pymupdf as f, sys, glob
from PIL import Image, ImageDraw, ImageFont
MM=72/25.4
D=sys.argv[1]; P=sorted(glob.glob(D+'/*.pdf')); dpi=int(sys.argv[3]) if len(sys.argv)>3 else 150
F1=ImageFont.truetype('npm/package/dist/public/static/alternative/Pretendard-SemiBold.ttf',int(dpi/6))
F2=ImageFont.truetype('npm/package/dist/public/static/alternative/Pretendard-Regular.ttf',int(dpi/7.5))
def crop(d,i,r):
    pm=d[i].get_pixmap(dpi=dpi,clip=f.Rect(*[v*MM for v in r])); return Image.frombytes('RGB',(pm.width,pm.height),pm.samples)
def spread_top(d,y1=36):
    a,b=crop(d,2,(0,0,262,y1)),crop(d,3,(0,0,262,y1))
    S=Image.new('RGB',(a.width*2+2,a.height),(170,170,170)); S.paste(a,(0,0)); S.paste(b,(a.width+2,0)); return S
def board(cols, out):
    rows=[]
    for p in P:
        d=f.open(p); rows.append((p.split('Squeeze_내지_')[1][:-4], [fn(d) for _,fn in cols]))
    cw=[max(r[1][j].width for r in rows) for j in range(len(cols))]
    rh=[max(c.height for c in r[1]) for r in rows]
    B=Image.new('RGB',(40+sum(cw)+20*len(cols),int(dpi/2.5)+sum(h+int(dpi/2.6) for h in rh)),(236,234,230)); dr=ImageDraw.Draw(B)
    x=20
    for j,(n,_) in enumerate(cols): dr.text((x,12),n,font=F2,fill=(60,60,60)); x+=cw[j]+20
    y=int(dpi/2.5)
    for (n,cs),h in zip(rows,rh):
        dr.text((20,y),n,font=F1,fill=(30,30,30)); x=20
        for j,c in enumerate(cs): B.paste(c,(x,y+int(dpi/4.5))); x+=cw[j]+20
        y+=h+int(dpi/2.6)
    B.save(out); print(out,B.size)
mode=sys.argv[2]
if mode=='head':
    board([('상단 펼침면 (6–7쪽)',spread_top)], D+'/후보_상단.png')
elif mode=='parts':
    board([('문항 번호 · 짝수쪽',lambda d:crop(d,2,(12,33,110,56))),('문항 번호 · 홀수쪽',lambda d:crop(d,3,(55,33,116,60))),
           ('풀이 공간 위쪽',lambda d:crop(d,3,(14,180,130,228))),('Solving',lambda d:crop(d,2,(130,266,246,286)))], D+'/후보_요소.png')
elif mode=='logic':
    board([('Logic Check (4쪽 왼쪽)',lambda d:crop(d,0,(10,20,130,310)))], D+'/후보_LogicCheck.png')
