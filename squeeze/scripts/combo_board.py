import pymupdf as f, glob, sys
from PIL import Image, ImageDraw, ImageFont
MM=72/25.4; dpi=120
D=sys.argv[1]; P=sorted(glob.glob(D+'/*.pdf'))
F1=ImageFont.truetype('npm/package/dist/public/static/alternative/Pretendard-SemiBold.ttf',22)
F2=ImageFont.truetype('npm/package/dist/public/static/alternative/Pretendard-Regular.ttf',18)
cols=[('홀수쪽 단원명',4,(190,22,246,36)),('짝수쪽 머리·번호·출처',5,(14,22,110,56)),('Solving',5,(130,268,246,286)),
      ('Logic Check',3,(14,40,120,66)),('Logic Check 목록',3,(132,38,246,62)),('차례',1,(14,36,225,100)),('하단',5,(14,352,72,363)),('풀이 라벨',4,(14,183,80,193))]
rows=[]
for p in P:
    d=f.open(p); cs=[]
    for _,i,r in cols:
        pm=d[i].get_pixmap(dpi=dpi,clip=f.Rect(*[v*MM for v in r])); cs.append(Image.frombytes('RGB',(pm.width,pm.height),pm.samples))
    rows.append((p.split('글꼴조합')[1][:-4],cs))
# 2단으로 배치: 위 4열, 아래 4열
def block(rows, idx):
    cw=[max(r[1][j].width for r in rows) for j in idx]; rh=[max(r[1][j].height for j in idx) for r in rows]
    B=Image.new('RGB',(40+sum(cw)+18*len(idx),60+sum(h+52 for h in rh)),(236,234,230)); dr=ImageDraw.Draw(B)
    x=20
    for k,j in enumerate(idx): dr.text((x,18),cols[j][0],font=F2,fill=(70,70,70)); x+=cw[k]+18
    y=56
    for (n,cs),h in zip(rows,rh):
        dr.text((20,y),n,font=F1,fill=(25,25,25)); x=20
        for k,j in enumerate(idx): B.paste(cs[j],(x,y+32)); x+=cw[k]+18
        y+=h+52
    return B
block(rows,[0,1,2,7]).save(D+'/글꼴조합_비교_1(머리·번호·Solving·풀이).png')
block(rows,[3,4,5,6]).save(D+'/글꼴조합_비교_2(LogicCheck·차례·하단).png')
