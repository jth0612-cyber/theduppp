# 요소별 확대 점검(인수인계 f22/crops.py 방식): 실제 쪽에서 잘라 인쇄 크기 비율로 나열
import pymupdf as f, sys
from PIL import Image, ImageDraw, ImageFont
pdf, out = sys.argv[1], sys.argv[2]
d = f.open(pdf); MM = 72 / 25.4
FT = ImageFont.truetype('npm/package/dist/public/static/alternative/Pretendard-Medium.ttf', 26)
items = [('상단 코일 · 제본선 부근 (짝수쪽 오른쪽 끝)', 2, (170, 0, 262, 36)), ('상단 코일 · 제본선 부근 (홀수쪽 왼쪽 끝)', 3, (0, 0, 92, 36)),
         ('상단 바깥쪽 + 단원명 (홀수쪽)', 3, (170, 0, 262, 36)), ('문항 번호 · 출처 (짝수쪽)', 2, (14, 34, 106, 56)),
         ('문항 번호 · 출처 (홀수쪽)', 3, (60, 34, 114, 60)), ('풀이 공간 왼쪽 위', 3, (8, 180, 100, 214)),
         ('Solving', 2, (130, 266, 246, 292)), ('하단 (짝수쪽)', 2, (14, 350, 80, 364)), ('하단 (홀수쪽)', 3, (196, 350, 248, 364)),
         ('Logic Check 목록', 0, (130, 36, 246, 80)), ('Logic Check 매듭', 0, (14, 140, 120, 250))]
ims = []
for name, pg, r in items:
    pm = d[pg].get_pixmap(dpi=200, clip=f.Rect(*[v * MM for v in r]))
    ims.append((name, Image.frombytes('RGB', (pm.width, pm.height), pm.samples)))
Wd = max(i.width for _, i in ims) + 40
B = Image.new('RGB', (Wd, sum(i.height + 60 for _, i in ims) + 20), (236, 234, 230)); dr = ImageDraw.Draw(B); y = 10
for name, im in ims:
    dr.text((20, y + 8), name, font=FT, fill=(40, 40, 40)); B.paste(im, (20, y + 45)); y += im.height + 60
B.save(out)
