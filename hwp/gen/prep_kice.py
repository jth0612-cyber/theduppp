"""기출 썸네일(NAS 'Squeeze_2028학년도_기출')을 원고 기출 그림 자리에 쓰도록 준비한다.
원고 그림처럼 위에 회색 출처 라벨(예: 2016학년도 6월 8번 생2)을 붙여 img/kice/에 저장하고 index.json을 만든다.
Usage: python3 prep_kice.py <썸네일 폴더> <Pretendard-Medium.ttf>"""
import glob, json, os, sys
from PIL import Image, ImageDraw, ImageFont
from kice_map import MAP

THUMBS, FONT = sys.argv[1:3]
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'img', 'kice')
os.makedirs(OUT, exist_ok=True)
index = {}
for (unit, n), (label, pre) in sorted(MAP.items()):
    if not pre:
        continue
    src = glob.glob(os.path.join(THUMBS, pre + '_*.png'))
    assert len(src) == 1, (pre, src)
    im = Image.open(src[0]).convert('RGB')
    W = im.width
    size = int(W * 0.026); pad_x, pad_y = int(size * 0.45), int(size * 0.22)
    f = ImageFont.truetype(FONT, size)
    x0, y0, x1, y1 = f.getbbox(label)
    cw, ch = x1 - x0 + 2 * pad_x, int(size * 1.0) + 2 * pad_y
    gap = int(size * 0.7)
    out = Image.new('RGB', (W, ch + gap + im.height), 'white')
    d = ImageDraw.Draw(out)
    d.rounded_rectangle((0, 0, cw, ch), radius=int(size * 0.25), fill='#8E8E8E')
    d.text((pad_x - x0, (ch - (y1 - y0)) // 2 - y0), label, font=f, fill='white')
    out.paste(im, (0, ch + gap))
    name = '%s_%02d_%s.png' % (unit, n, label.replace(' ', '_'))
    out.save(os.path.join(OUT, name), optimize=True)
    index['%s/image%d.png' % (unit, n)] = name
json.dump(index, open(os.path.join(OUT, 'index.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(index), 'images')
