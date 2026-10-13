import pymupdf as f, sys, glob
from PIL import Image, ImageDraw, ImageFont
MM=72/25.4; FT=ImageFont.truetype('npm/package/dist/public/static/alternative/Pretendard-SemiBold.ttf',28)
rows=[]
for p in sorted(glob.glob(sys.argv[1]+'/*.pdf')):
    d=f.open(p); ims=[]
    for i in (2,3):
        pm=d[i].get_pixmap(dpi=int(sys.argv[3]) if len(sys.argv)>3 else 90,clip=f.Rect(0,0,262*MM,62*MM)); ims.append(Image.frombytes('RGB',(pm.width,pm.height),pm.samples))
    S=Image.new('RGB',(ims[0].width*2+2,ims[0].height),(170,170,170)); S.paste(ims[0],(0,0)); S.paste(ims[1],(ims[0].width+2,0))
    rows.append((p.split('_')[-1][:-4],S))
w,h=rows[0][1].size
B=Image.new('RGB',(w+40,(h+56)*len(rows)+10),(236,234,230)); dr=ImageDraw.Draw(B)
for k,(n,im) in enumerate(rows):
    y=10+k*(h+56); dr.text((20,y+6),n,font=FT,fill=(30,30,30)); B.paste(im,(20,y+44))
B.save(sys.argv[2])
