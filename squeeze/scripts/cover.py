# Squeeze 표지 시안: (3,7) 토러스 매듭을 따라 비틀리며 도는 리본(가는 선 24가닥). 2도(먹 + 별색).
import sys; sys.path.insert(0, '.')
from knot import knot_svg
import pymupdf as f

W, H = 262, 371
MM = 72 / 25.4
m = lambda v: v * MM
FD = 'npm/package/dist/public/static/alternative'
OUT = sys.argv[1]

knot_svg('cv/cover_art.svg', W, H, 150, 168, 92, p=3, q=7, r=0.5, tilt=22, rotz=8, n=4200,
         strands=24, mode='ribbon', tube=0.15, twist=4, halo=1.0, lw=0.3, spot_every=11)
art = f.open('cv/cover_art.svg')
art_pdf = f.open('pdf', art.convert_to_pdf())

doc = f.open()
pg = doc.new_page(width=m(W), height=m(H))
pg.show_pdf_page(pg.rect, art_pdf, 0)
for k, fn in {'md': 'md/Million Dreams.otf', 'pl': f'{FD}/Pretendard-Light.ttf',
              'pr': f'{FD}/Pretendard-Regular.ttf', 'pm': f'{FD}/Pretendard-Medium.ttf'}.items():
    pg.insert_font(fontname=k, fontfile=fn)
K = (0x23 / 255, 0x1F / 255, 0x20 / 255); S = (0, 0xA2 / 255, 0xDB / 255)
font = {k: f.Font(fontfile=v) for k, v in {'pl': f'{FD}/Pretendard-Light.ttf'}.items()}

def spaced(x, y, text, fn, size, color, track):
    cx = m(x)
    for ch in text:
        pg.insert_text(f.Point(cx, m(y)), ch, fontname=fn, fontsize=size, color=color)
        cx += f.Font(fontfile={'pl': f'{FD}/Pretendard-Light.ttf', 'pr': f'{FD}/Pretendard-Regular.ttf', 'pm': f'{FD}/Pretendard-Medium.ttf'}[fn]).text_length(ch, fontsize=size) + track / 1000 * size

# 제목 블록 (왼쪽 아래)
pg.draw_line(f.Point(m(22), m(296)), f.Point(m(22 + 34), m(296)), color=S, width=1.2)
pg.insert_text(f.Point(m(20), m(326)), 'Squeeze', fontname='md', fontsize=96, color=K)
spaced(22.5, 340, '기출 EXTRACT 2', 'pl', 17, K, 160)
spaced(22.5, 350, 'A. 고체   B. 유체   C. 천체', 'pr', 9, K, 80)
# 오른쪽 아래 로고
res = f.open('hb/res.pdf')
clip = f.Rect(m(199.6), m(354.2), m(224.2), m(359.8))
pg.show_pdf_page(f.Rect(m(207), m(344), m(207 + 24.6 * 1.25), m(344 + 5.6 * 1.25)), res, 21, clip=clip)
doc.subset_fonts()
doc.save(OUT, garbage=4, deflate=True)
pg.get_pixmap(dpi=60).save(OUT[:-4] + '.png')
pg.get_pixmap(dpi=300, clip=f.Rect(m(150), m(120), m(230), m(200))).save(OUT[:-4] + '_확대.png')
print(OUT)
