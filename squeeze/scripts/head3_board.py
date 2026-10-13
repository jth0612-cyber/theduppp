# 상단바 3안 비교: 6·25쪽 펼침면 위쪽(현재 + A/B/C) + 안별 펼침면 이미지
import glob, re, sys, pymupdf as f
from PIL import Image, ImageDraw, ImageFont
MM = 72 / 25.4; D = sys.argv[1]
srcs = [('현재 03-01-11', glob.glob('final17/*_예시14쪽.pdf')[0])] + \
       [(re.search(r'상단(.\(.*?\))', p).group(1), p) for p in sorted(glob.glob(f'{D}/*_예시14쪽.pdf'))]
def spread(d, a, dpi, clip_h=None):
    w, h = d[a].rect.width, d[a].rect.height
    o = f.Document(); p = o.new_page(width=2 * w, height=h)
    p.show_pdf_page(f.Rect(0, 0, w, h), d, a); p.show_pdf_page(f.Rect(w, 0, 2 * w, h), d, a + 1)
    pix = p.get_pixmap(dpi=dpi, clip=f.Rect(0, 0, 2 * w, clip_h * MM) if clip_h else None)
    return Image.frombytes('RGB', (pix.w, pix.h), pix.samples)
font = ImageFont.truetype('npm/package/dist/public/static/alternative/Pretendard-Medium.ttf', 42)
tiles = []
for name, p in srcs:
    d = f.open(p); tiles.append((name, spread(d, 5, 160, 40)))
    if name.startswith('현재'): continue
    code = name[0]
    for a, tag in ((5, '6-25'), (3, '4-5')):
        spread(d, a, 110).save(f'{D}/펼침면_{code}_{tag}.png')
tw, th = tiles[0][1].size; cap, pad = 70, 30
B = Image.new('RGB', (tw + 2 * pad, len(tiles) * (th + cap + pad) + pad), 'white'); dr = ImageDraw.Draw(B)
for i, (name, im) in enumerate(tiles):
    y = pad + i * (th + cap + pad)
    dr.text((pad, y + 10), name, fill=(30, 30, 30), font=font)
    B.paste(im, (pad, y + cap)); dr.rectangle([pad, y + cap, pad + tw - 1, y + cap + th - 1], outline=(215, 215, 215), width=2)
B.save(f'{D}/상단바_3안_비교.png'); print(B.size)
