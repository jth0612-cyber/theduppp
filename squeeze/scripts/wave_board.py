# 파형 안 비교: 현재 + 03-01-13 A/B/C + 03-01-14 D/E, 6쪽 Solving 줄 확대 (가운데 선 확인용 가는 보조선 없이)
import glob, re, sys, pymupdf as f
from PIL import Image, ImageDraw, ImageFont
D = sys.argv[1] if len(sys.argv) > 1 else 'wave'
EXTRA = sys.argv[2:]   # 앞에 같이 놓을 PDF 글롭(예: 'wave/*SolvingD*')
srcs = [('현재 03-01-11', glob.glob('final17/*_예시14쪽.pdf')[0])] + \
       [(re.search(r'Solving(.\(.*?\))', p).group(1), p) for g in EXTRA + [f'{D}/*_예시14쪽.pdf'] for p in sorted(glob.glob(g))]

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
    tiles.append((name, Image.frombytes('RGB', (pix.w, pix.h), pix.samples)))
    if p.startswith(D + '/'):
        pg.get_pixmap(dpi=200, clip=f.Rect(r.x0 - 30, r.y0 - 40, r.x0 + 440, r.y0 + 260)).save(f'{D}/6쪽_Solving_{name[0]}.png')
tw, th = tiles[0][1].size; cap, pad = 64, 30
B = Image.new('RGB', (tw + 2 * pad, len(tiles) * (th + cap + pad) + pad), 'white'); dr = ImageDraw.Draw(B)
for i, (name, im) in enumerate(tiles):
    y = pad + i * (th + cap + pad)
    dr.text((pad, y + 10), name, fill=(30, 30, 30), font=font)
    B.paste(im, (pad, y + cap)); dr.rectangle([pad, y + cap, pad + tw - 1, y + cap + th - 1], outline=(215, 215, 215), width=2)
B.save(f'{D}/Solving_파형_비교.png'); print(B.size)
