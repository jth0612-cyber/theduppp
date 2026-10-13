import pymupdf as f, sys, glob
from PIL import Image, ImageDraw, ImageFont
FT=ImageFont.truetype('npm/package/dist/public/static/alternative/Pretendard-SemiBold.ttf',30)
def sp(path,a,b,z):
    d=f.open(path); ims=[]
    for i in (a,b):
        pm=d[i].get_pixmap(matrix=f.Matrix(z,z)); ims.append(Image.frombytes('RGB',(pm.width,pm.height),pm.samples))
    S=Image.new('RGB',(ims[0].width*2+2,ims[0].height),(180,180,180)); S.paste(ims[0],(0,0)); S.paste(ims[1],(ims[0].width+2,0)); return S
def board(items, out, cols=2, z=0.62):
    ims=[(n,sp(p,a,b,z)) for n,p,a,b in items]
    w,h=ims[0][1].size; rows=(len(ims)+cols-1)//cols
    B=Image.new('RGB',(cols*(w+20)+20,rows*(h+60)+10),(236,234,230)); dr=ImageDraw.Draw(B)
    for k,(n,im) in enumerate(ims):
        x,y=20+(k%cols)*(w+20),10+(k//cols)*(h+60); dr.text((x,y+8),n,font=FT,fill=(30,30,30)); B.paste(im,(x,y+50))
    B.save(out)
if __name__=='__main__':
    D=sys.argv[1]; P=sorted(glob.glob(D+'/*.pdf'))
    for tag,(a,b),(oa,ob) in (('67',(2,3),(5,6)),('45',(0,1),(3,4))):
        items=[('원본','sq/sq.pdf',oa,ob)]+[(p.split('Squeeze_내지_')[1][:-4],p,a,b) for p in P]
        board(items, f'{D}/비교_{tag}쪽.png', cols=2)
