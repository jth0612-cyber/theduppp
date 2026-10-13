# Solving 줄 3안 비교: 6쪽 Solving 줄 확대(현재 + A/B/C) + 안별 6쪽 하단 펼침
import glob, re, sys, pymupdf as f
from PIL import Image, ImageDraw, ImageFont
D = sys.argv[1]
srcs = [('현재 03-01-11', glob.glob('final17/*_예시14쪽.pdf')[0])] + \
       [(re.search(r'Solving(.\(.*?\))', p).group(1), p) for p in sorted(glob.glob(f'{D}/*_예시14쪽.pdf'))]
def solving_rect(pg):
    for b in pg.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                if s['text'].strip() == 'Solving': return f.Rect(s['bbox'])
font = ImageFont.truetype('npm/package/dist/public/static/alternative/Pretendard-Medium.ttf', 40)
tiles = []
for name, p in srcs:
    pg = f.open(p)[5]; r = solving_rect(pg)
    pix = pg.get_pixmap(dpi=330, clip=f.Rect(r.x0 - 8, r.y0 - 14, r.x0 + 425, r.y1 + 16))
    im = Image.frombytes('RGB', (pix.w, pix.h), pix.samples); tiles.append((name, im))
    if not name.startswith('현재'):
        pix = pg.get_pixmap(dpi=200, clip=f.Rect(r.x0 - 30, r.y0 - 40, r.x0 + 440, r.y0 + 260))
        pix.save(f'{D}/6쪽_Solving_{name[0]}.png')
tw, th = tiles[0][1].size; cap, pad = 64, 30
B = Image.new('RGB', (tw + 2 * pad, len(tiles) * (th + cap + pad) + pad), 'white'); dr = ImageDraw.Draw(B)
for i, (name, im) in enumerate(tiles):
    y = pad + i * (th + cap + pad)
    dr.text((pad, y + 10), name, fill=(30, 30, 30), font=font)
    B.paste(im, (pad, y + cap)); dr.rectangle([pad, y + cap, pad + tw - 1, y + cap + th - 1], outline=(215, 215, 215), width=2)
B.save(f'{D}/Solving_3안_비교.png'); print(B.size)
