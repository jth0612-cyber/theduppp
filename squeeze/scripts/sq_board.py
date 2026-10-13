import pymupdf as f, sys
from PIL import Image, ImageDraw, ImageFont
SRC, OUTD = sys.argv[1], sys.argv[2]
FT = ImageFont.truetype('npm/package/dist/public/static/alternative/Pretendard-SemiBold.ttf', 30)
def pg(path, i, z):
    pm = f.open(path)[i].get_pixmap(matrix=f.Matrix(z, z)); return Image.frombytes('RGB', (pm.width, pm.height), pm.samples)
def spread(items, z):
    a, b = [pg(p, i, z) for p, i in items]
    S = Image.new('RGB', (a.width * 2 + 2, a.height), (180, 180, 180)); S.paste(a, (0, 0)); S.paste(b, (a.width + 2, 0)); return S
V = [('원본', SRC, 3), ('A 루버', f'{OUTD}/A_루버.pdf', 0), ('B 수평선', f'{OUTD}/B_수평선.pdf', 0), ('C 면과 질감', f'{OUTD}/C_면과질감.pdf', 0)]
for tag, (p0, p1) in (('45', (0, 1)), ('67', (2, 3))):
    ims = []
    for name, path, off in V:
        im = spread([(path, p0 + off), (path, p1 + off)], 0.75)
        ims.append((name, im))
    w, h = ims[0][1].size
    B = Image.new('RGB', (w * 2 + 60, (h + 60) * 2 + 20), (236, 234, 230)); dr = ImageDraw.Draw(B)
    for k, (name, im) in enumerate(ims):
        x, y = 20 + (k % 2) * (w + 20), 10 + (k // 2) * (h + 60)
        dr.text((x, y + 8), name, font=FT, fill=(30, 30, 30)); B.paste(im, (x, y + 50))
    B.save(f'{OUTD}/비교_{tag}쪽.png')
# 부분 확대: 상단바 / 문항번호 / Solving / 하단
crops = [('상단바·단원명 (홀수쪽)', 3, (300, 0, 742.7, 80)), ('문항 번호·출처 (짝수쪽)', 2, (30, 80, 330, 160)),
         ('Solving 머리 (짝수쪽)', 2, (370, 755, 700, 800)), ('하단 (짝수쪽)', 2, (0, 985, 300, 1040))]
rows = []
for name, path, off in V:
    cs = []
    for cn, i, r in crops:
        pm = f.open(path)[i + off].get_pixmap(matrix=f.Matrix(1.6, 1.6), clip=f.Rect(*r)); cs.append(Image.frombytes('RGB', (pm.width, pm.height), pm.samples))
    rows.append((name, cs))
cw = [max(r[1][j].width for r in rows) for j in range(4)]
rh = [max(c.height for c in r[1]) for r in rows]
B = Image.new('RGB', (180 + sum(cw) + 60, sum(rh) + 70 + 30 * len(rows)), (236, 234, 230)); dr = ImageDraw.Draw(B)
x = 180
for j, (cn, _, _) in enumerate(crops): dr.text((x, 15), cn, font=ImageFont.truetype('npm/package/dist/public/static/alternative/Pretendard-Regular.ttf', 22), fill=(60, 60, 60)); x += cw[j] + 15
y = 60
for (name, cs), hh in zip(rows, rh):
    dr.text((15, y + 10), name, font=FT, fill=(30, 30, 30)); x = 180
    for j, c in enumerate(cs): B.paste(c, (x, y)); x += cw[j] + 15
    y += hh + 30
B.save(f'{OUTD}/비교_부분확대.png')
print('ok')
