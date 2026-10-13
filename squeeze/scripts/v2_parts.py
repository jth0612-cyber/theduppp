import pymupdf as f, sys, glob
from PIL import Image, ImageDraw, ImageFont
MM=72/25.4
D=sys.argv[1]; P=sorted(glob.glob(D+'/*.pdf'))
F1=ImageFont.truetype('npm/package/dist/public/static/alternative/Pretendard-SemiBold.ttf',24)
F2=ImageFont.truetype('npm/package/dist/public/static/alternative/Pretendard-Regular.ttf',20)
cols=[('상단·단원명(홀수쪽 바깥)',3,(150,0,262,40)),('문항 번호(짝수쪽)',2,(15,34,110,56)),('문항 번호(홀수쪽)',3,(55,34,112,60)),
      ('풀이 공간 왼쪽 위',3,(14,182,110,214)),('Solving',2,(130,268,246,288)),('하단(짝수쪽)',2,(15,352,70,363))]
rows=[]
for p in P:
    d=f.open(p); cs=[]
    for _,i,r in cols:
        pm=d[i].get_pixmap(dpi=150,clip=f.Rect(*[v*MM for v in r])); cs.append(Image.frombytes('RGB',(pm.width,pm.height),pm.samples))
    rows.append((p.split('Squeeze_내지_')[1][:-4],cs))
cw=[max(r[1][j].width for r in rows) for j in range(len(cols))]
rh=[max(c.height for c in r[1]) for r in rows]
B=Image.new('RGB',(40+sum(cw)+15*len(cols),70+sum(h+46 for h in rh)),(236,234,230)); dr=ImageDraw.Draw(B)
x=20
for j,(n,_,_) in enumerate(cols): dr.text((x,20),n,font=F2,fill=(60,60,60)); x+=cw[j]+15
y=60
for (n,cs),h in zip(rows,rh):
    dr.text((20,y),n,font=F1,fill=(30,30,30)); x=20
    for j,c in enumerate(cs): B.paste(c,(x,y+34)); x+=cw[j]+15
    y+=h+46
B.save(D+'/비교_요소확대.png'); print(B.size)
