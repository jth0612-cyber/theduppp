"""원고 hwpx의 그림(BinData)을 img/<단원>/imageN.png 로 꺼낸다 (bmp·jpg → png, png 그대로, emf는 그대로 둔다).
Usage: python3 extract_img.py <원고.hwpx> <단원이름>"""
import io, os, sys, zipfile
from PIL import Image
src, unit = sys.argv[1:3]
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'img', unit)
os.makedirs(out, exist_ok=True)
z = zipfile.ZipFile(src); n = 0
for name in z.namelist():
    if not name.startswith('BinData/'):
        continue
    base, ext = os.path.splitext(os.path.basename(name)); ext = ext.lower()
    data = z.read(name)
    if ext == '.emf':
        open(os.path.join(out, base + '.emf'), 'wb').write(data)
    else:
        im = Image.open(io.BytesIO(data))
        if im.mode not in ('RGB', 'RGBA', 'L'):
            im = im.convert('RGBA' if 'A' in im.mode or im.mode == 'P' else 'RGB')
        im.save(os.path.join(out, base + '.png'), optimize=True)
    n += 1
print(unit, n, 'images ->', out)
