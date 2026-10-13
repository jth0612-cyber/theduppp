import pymupdf as f, glob
from PIL import Image, ImageDraw, ImageFont
MM=72/25.4; dpi=110
F1=ImageFont.truetype('npm/package/dist/public/static/alternative/Pretendard-SemiBold.ttf',22)
F2=ImageFont.truetype('npm/package/dist/public/static/alternative/Pretendard-Regular.ttf',18)
cols=[('홀수쪽 단원명',4,(186,22,246,36)),('짝수쪽 머리·번호·출처',5,(14,22,106,52)),('Solving (고정)',5,(130,268,246,286)),
      ('Logic Check',3,(14,40,116,66)),('차례',1,(14,36,225,96)),('하단',5,(14,352,72,363))]
P=sorted(glob.glob('combo20/*.pdf'))
rows=[]
for p in P:
    d=f.open(p); cs=[]
    for _,i,r in cols:
        pm=d[i].get_pixmap(dpi=dpi,clip=f.Rect(*[v*MM for v in r])); cs.append(Image.frombytes('RGB',(pm.width,pm.height),pm.samples))
    rows.append((p.split('글꼴조합')[1][:-4],cs))
cw=[max(r[1][j].width for r in rows) for j in range(len(cols))]
for part in range(4):
    sel=rows[part*5:(part+1)*5]; rh=[max(c.height for c in r[1]) for r in sel]
    B=Image.new('RGB',(40+sum(cw)+16*len(cols),56+sum(h+48 for h in rh)),(236,234,230)); dr=ImageDraw.Draw(B)
    x=20
    for j,(n,_,_) in enumerate(cols): dr.text((x,16),n,font=F2,fill=(70,70,70)); x+=cw[j]+16
    y=52
    for (n,cs),h in zip(sel,rh):
        dr.text((20,y),n,font=F1,fill=(25,25,25)); x=20
        for j,c in enumerate(cs): B.paste(c,(x,y+30)); x+=cw[j]+16
        y+=h+48
    B.save(f'combo20/글꼴조합20_비교_{part+1}({sel[0][0][:2]}-{sel[-1][0][:2]}).png'); print(B.size)
