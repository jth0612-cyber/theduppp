# 좌상단 글꼴 10안 비교판: 6쪽 좌상단(머리 핀 + 라벨 + A-1) 확대
import glob, re, sys, pymupdf as f
D = sys.argv[1] if len(sys.argv) > 1 else 'label10'
from PIL import Image, ImageDraw, ImageFont
MM = 72 / 25.4
fs = sorted(glob.glob(f'{D}/*_예시14쪽.pdf'))
crop = f.Rect(0, 0, 135 * MM, 48.6 * MM)
tiles = []
for p in fs:
    d = f.open(p); pg = d[5]
    pix = pg.get_pixmap(dpi=220, clip=crop)
    tiles.append((re.search(r'좌상단(\d\d)\((.*?)\)', p).groups(), Image.frombytes('RGB', (pix.w, pix.h), pix.samples)))
tw, th = tiles[0][1].size; cap = 70; pad = 30
B = Image.new('RGB', (2 * tw + 3 * pad, 5 * (th + cap) + 6 * pad), 'white'); dr = ImageDraw.Draw(B)
font = ImageFont.truetype('npm/package/dist/public/static/alternative/Pretendard-Medium.ttf', 40)
for i, ((code, name), im) in enumerate(tiles):
    x = pad + (i % 2) * (tw + pad); y = pad + (i // 2) * (th + cap + pad)
    dr.text((x, y + 10), f'{code}  {name}', fill=(30, 30, 30), font=font)
    B.paste(im, (x, y + cap)); dr.rectangle([x, y + cap, x + tw - 1, y + cap + th - 1], outline=(215, 215, 215), width=2)
B.save(f'{D}/좌상단_글꼴10안_비교.png'); print(B.size)
