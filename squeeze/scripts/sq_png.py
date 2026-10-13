import pymupdf as f, sys, glob
from PIL import Image
def spread(path,a,b,z):
  d=f.open(path); ims=[]
  for i in (a,b):
    pm=d[i].get_pixmap(matrix=f.Matrix(z,z)); ims.append(Image.frombytes('RGB',(pm.width,pm.height),pm.samples))
  S=Image.new('RGB',(ims[0].width*2+2,ims[0].height),(170,170,170)); S.paste(ims[0],(0,0)); S.paste(ims[1],(ims[0].width+2,0)); return S
for p in sys.argv[1:]:
  for a,b,t in ((0,1,'45'),(2,3,'67')):
    spread(p,a,b,0.8).save(p[:-4]+f'_{t}.png')
