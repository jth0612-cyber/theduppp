# 상단 핀 + 머리 글자 자리 확인용(시험 글자는 확인 그림에만, 결과 PDF에는 없음)
import sys; sys.path.insert(0, '.')
import sq_res27 as Z
from sq_res27 import P, f, m, R, W, H, S, head
import sq_combo20, sq_label10, sq8, sq_lib
from PIL import Image
sq_combo20.setup('11'); sq_label10.setup('17')
sq8.RES = f.open('hb/res.pdf')
doc = f.open()
for side, txt, x, al in (('even', '교육청 EXTRACT', 23, 'l'), ('odd', '2027학년도 교육청', 244, 'r')):
    pg = doc.new_page(width=m(W), height=m(60)); d = P(pg, sq8.RES); head(d, side)
    pg.insert_font(fontname='pr', fontfile=sq_lib.FONTS['pr'])
    wd = sq_lib.FO['pr'].text_length(txt, fontsize=13) / (72 / 25.4)
    xx = x - wd if al == 'r' else x
    pg.insert_text(f.Point(m(xx), m(19.5)), txt, fontname='pr', fontsize=13, color=S())
ims = []
for p in doc:
    px = p.get_pixmap(dpi=110); ims.append(Image.frombytes('RGB', (px.w, px.h), px.samples))
B = Image.new('RGB', (ims[0].width * 2 + 30, ims[0].height), (240, 241, 242))
B.paste(ims[0], (0, 0)); B.paste(ims[1], (ims[0].width + 30, 0)); B.save(sys.argv[1])
