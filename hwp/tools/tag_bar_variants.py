"""실제 미리보기 PDF(한글이 출력한 것) 위에서 TAG·중단원 띠만 시안으로 바꿔 그린 미리보기를 만든다.
Usage: python3 tag_bar_variants.py <미리보기.pdf> <폰트폴더1> [<폰트폴더2> ...] <out_dir>
"""
import os, sys, glob
import pymupdf as fitz

SRC, *FONTDIRS, OUT = sys.argv[1:]
PAPER = (0xF8/255, 0xF1/255, 0xE7/255)
def C(h): h = h.lstrip('#'); return tuple(int(h[i:i+2], 16)/255 for i in (0, 2, 4))
BAR, ACC, TAN, INK, DEEP, ORN = C('5A3A2E'), C('A9623A'), C('D7A77E'), C('3A241D'), C('8E4E2B'), C('9E6E48')
WHITE = (1, 1, 1)

def ff(name):
    for d in FONTDIRS:
        for p in glob.glob(os.path.join(d, '**', name), recursive=True):
            return p
    raise SystemExit('font not found: ' + name)
FONTS = {'pblack': ff('Pretendard-Black.ttf'), 'pbold': ff('Pretendard-Bold.ttf'),
         'hbold': ff('Hahmlet-Bold.ttf'), 'hsemi': ff('Hahmlet-SemiBold.ttf'), 'kbatang': ff('KoPubWorld Batang Medium.ttf')}
WOOD = ff('wood_band_light.jpg')

base = fitz.open(SRC)
# 중단원 띠 제목 글꼴(강원교육모두 Bold)은 PDF에 들어 있는 것을 그대로 꺼내 쓴다
for x in base[5].get_fonts():
    if 'GangwonEduAllBold' in x[3]:
        name, ext, _, buf = base.extract_font(x[0]); raw = os.path.join(OUT, '_gangwon_raw.' + ext)
        os.makedirs(OUT, exist_ok=True); open(raw, 'wb').write(buf)
        # 부분 글꼴에는 cmap이 없어서 PDF의 ToUnicode 표로 다시 만들어 준다
        import re
        from fontTools.ttLib import TTFont, newTable
        from fontTools.ttLib.tables._c_m_a_p import cmap_format_4
        tu = int(re.search(r'/ToUnicode (\d+) 0 R', base.xref_object(x[0])).group(1))
        pairs = re.findall(r'<([0-9a-fA-F]{4})>\s*<([0-9a-fA-F]{4})>', base.xref_stream(tu).decode())
        tt = TTFont(raw); order = tt.getGlyphOrder()
        t = cmap_format_4(4); t.platformID, t.platEncID, t.language = 3, 1, 0
        t.cmap = {int(u, 16): order[int(g, 16)] for g, u in pairs if u.lower() != 'ffff' and int(g, 16) < len(order)}
        cm = newTable('cmap'); cm.tableVersion = 0; cm.tables = [t]; tt['cmap'] = cm
        FONTS['gangwon'] = os.path.join(OUT, '_gangwon.ttf'); tt.save(FONTS['gangwon'])

def text(pg, x, y, s, font, size, color, align='left', box_w=0, spacing=0, render=0, stroke=None, width=0.6):
    fn = 'f_' + font
    pg.insert_font(fontname=fn, fontfile=FONTS[font])
    f = fitz.Font(fontfile=FONTS[font])
    w = f.text_length(s, fontsize=size) + spacing * (len(s) - 1)
    if align == 'center': x = x + (box_w - w) / 2
    if align == 'right': x = x - w
    if spacing:
        for ch in s:
            pg.insert_text((x, y), ch, fontname=fn, fontsize=size, color=color, render_mode=render, stroke_opacity=1, border_width=width)
            x += f.text_length(ch, fontsize=size) + spacing
    else:
        kw = dict(render_mode=render, border_width=width) if render else {}
        if render: kw['color'] = stroke; kw['fill'] = color
        pg.insert_text((x, y), s, fontname=fn, fontsize=size, color=kw.pop('color', color), **kw)
    return w

def poly(pg, pts, fill, color=None, width=0):
    sh = pg.new_shape(); sh.draw_polyline(pts + [pts[0]]); sh.finish(fill=fill, color=color, width=width, closePath=True); sh.commit()

def rect(pg, r, fill, color=None, width=0, radius=None):
    sh = pg.new_shape(); sh.draw_rect(r, radius=radius); sh.finish(fill=fill, color=color, width=width); sh.commit()

def line(pg, a, b, color, width):
    sh = pg.new_shape(); sh.draw_line(a, b); sh.finish(color=color, width=width); sh.commit()

def mid(t, h, size, k=0.36): return t + h / 2 + size * k

# ---------- TAG (R = 오른쪽 끝, T = 윗변, H = 높이) ----------
def tag_current(pg, R, T, H): pass

def tag_A(pg, R, T, H):   # 나비장 키
    W, n = 31, 2.6
    poly(pg, [(R-W, T), (R-W/2, T+n), (R, T), (R, T+H), (R-W/2, T+H-n), (R-W, T+H)], BAR)
    text(pg, R-W, mid(T, H, 7.2), 'TAG', 'pblack', 7.2, WHITE, 'center', W, spacing=0.6)

def tag_B(pg, R, T, H):   # 원목 명판
    r = fitz.Rect(R-33, T, R-1.5, T+H)
    pg.insert_image(r, filename=WOOD, keep_proportion=False)
    rect(pg, r, None, ORN, 0.5, radius=0.12)
    for cx in (r.x0+3, r.x1-3):
        sh = pg.new_shape(); sh.draw_circle((cx, T+H/2), 0.8); sh.finish(fill=INK); sh.commit()
    text(pg, r.x0, mid(T, H, 7.2), 'TAG', 'pblack', 7.2, INK, 'center', r.width, spacing=0.7)

def tag_C(pg, R, T, H):   # 제비꼬리 리본
    W = 34
    poly(pg, [(R-W, T), (R, T), (R, T+H), (R-W, T+H), (R-W+4.5, T+H/2)], ACC)
    text(pg, R-W+3, mid(T, H, 8), 'TAG', 'pbold', 8, WHITE, 'center', W-3, spacing=0.6)

def tag_D(pg, R, T, H):   # 인덱스 탭
    W, rr = 31, 4
    sh = pg.new_shape()
    sh.draw_line((R, T), (R-W+rr, T)); sh.draw_curve((R-W+rr, T), (R-W, T), (R-W, T+rr))
    sh.draw_line((R-W, T+rr), (R-W, T+H-rr)); sh.draw_curve((R-W, T+H-rr), (R-W, T+H), (R-W+rr, T+H)); sh.draw_line((R-W+rr, T+H), (R, T+H))
    sh.finish(fill=C('F1E0CB'), color=BAR, width=0.6, closePath=False); sh.commit()
    text(pg, R-W, mid(T, H, 7.6, 0.34), 'TAG', 'hsemi', 7.6, BAR, 'center', W, spacing=1.2)

def tag_E(pg, R, T, H):   # 미니멀 눈금
    text(pg, R-3, T+H-3.2, 'TAG', 'hbold', 8.6, DEEP, 'right', spacing=1.6)
    y = T + H; line(pg, (R-31, y), (R-1.5, y), BAR, 0.7)
    x = R - 31
    k = 0
    while x <= R - 1.4:
        line(pg, (x, y), (x, y - (2.6 if k % 5 == 0 else 1.3)), BAR, 0.35); x += 2.5; k += 1

TAGS = [('현재', tag_current), ('TAG A · 나비장 키', tag_A), ('TAG B · 원목 명판', tag_B), ('TAG C · 제비꼬리 리본', tag_C),
        ('TAG D · 인덱스 탭', tag_D), ('TAG E · 미니멀 눈금', tag_E)]

# ---------- 중단원 띠 (X0..X1, Y0..Y1) ----------
NUM, TITLE = '01', 'SI 단위계의 해석'

def bar_A(pg, X0, Y0, X1, Y1):   # 줄자
    rect(pg, fitz.Rect(X0, Y0, X1, Y1), TAN)
    rect(pg, fitz.Rect(X0+5, Y0+3.5, X0+27, Y1-6.5), BAR)
    text(pg, X0+5, mid(Y0+3.5, Y1-Y0-10, 12), NUM, 'pblack', 12, WHITE, 'center', 22)
    text(pg, X0+34, mid(Y0, Y1-Y0-4, 12), TITLE, 'gangwon', 12, INK)
    x, k = X0, 0
    while x <= X1:
        line(pg, (x, Y1), (x, Y1 - (4.4 if k % 10 == 0 else 2.8 if k % 5 == 0 else 1.6)), BAR, 0.4); x += 2.5; k += 1
    line(pg, (X0, Y1), (X1, Y1), BAR, 0.6)

def bar_B(pg, X0, Y0, X1, Y1):   # 주먹장 결합
    H = Y1 - Y0; W = 36; d = 6
    poly(pg, [(X0+W-d, Y0), (X1, Y0), (X1, Y1), (X0+W-d, Y1), (X0+W, Y0+H/2)], BAR)
    poly(pg, [(X0, Y0), (X0+W-d-1.2, Y0), (X0+W-1.2, Y0+H/2), (X0+W-d-1.2, Y1), (X0, Y1)], ACC)
    text(pg, X0+4, mid(Y0, H, 16), NUM, 'pblack', 16, WHITE, 'center', W-12)
    text(pg, X0+W+8, mid(Y0, H, 12), TITLE, 'gangwon', 12, WHITE)

def bar_C(pg, X0, Y0, X1, Y1):   # 명조 + 이중선
    w = text(pg, X0+2, Y1-5.5, NUM, 'hbold', 19, DEEP)
    text(pg, X0+2+w+9, Y1-6.5, TITLE, 'hsemi', 13, INK)
    rect(pg, fitz.Rect(X0, Y1-3.2, X1, Y1-1.6), BAR)
    rect(pg, fitz.Rect(X0, Y1-0.6, X1, Y1), BAR)

def bar_D(pg, X0, Y0, X1, Y1):   # 원목 슬랫
    H = Y1 - Y0
    pg.insert_image(fitz.Rect(X0+30, Y0, X1, Y1), filename=WOOD, keep_proportion=False)
    rect(pg, fitz.Rect(X0, Y0, X0+30, Y1), INK)
    text(pg, X0, mid(Y0, H, 15), NUM, 'pblack', 15, C('F3D9BE'), 'center', 30)
    text(pg, X0+40, mid(Y0, H, 12), TITLE, 'gangwon', 12, INK)
    line(pg, (X0, Y1), (X1, Y1), INK, 1.2)

def bar_E(pg, X0, Y0, X1, Y1):   # 큰 외곽선 숫자
    rect(pg, fitz.Rect(X0, Y1-4.5, X1, Y1), BAR)
    w = text(pg, X0+2, Y1+1.5, NUM, 'pblack', 34, PAPER, render=1, stroke=ACC, width=0.03)
    text(pg, X0+2+w+8, Y1-8, TITLE, 'gangwon', 13, INK)

BARS = [('막대 A · 줄자', bar_A), ('막대 B · 주먹장 결합', bar_B), ('막대 C · 명조 제목 + 이중선', bar_C),
        ('막대 D · 원목 슬랫', bar_D), ('막대 E · 큰 외곽선 숫자', bar_E)]

def tag_boxes(pg):
    out = []
    for dr in pg.get_drawings():
        r = dr['rect']; f = dr.get('fill')
        if f and abs(f[0]-0.3529) < 0.01 and 10 < r.height < 13 and 30 < r.width < 35:
            out.append(r)
    return out

def apply(doc, tagfn=None, barfn=None):
    for pno in range(len(doc)):
        pg = doc[pno]
        if tagfn and tagfn is not tag_current:
            for r in tag_boxes(pg):
                pg.add_redact_annot(r, fill=PAPER)
                pg.apply_redactions(images=0, graphics=1, text=0)
                rect(pg, fitz.Rect(r.x0-0.2, r.y0-0.2, r.x1-0.25, r.y1+0.2), PAPER)
                tagfn(pg, r.x1, r.y0, r.height)
        if barfn:
            for dr in pg.get_drawings():
                r = dr['rect']; f = dr.get('fill')
                if f and abs(f[0]-0.3529) < 0.01 and 20 < r.height < 25 and r.width > 300:
                    cover = fitz.Rect(r.x0-0.5, r.y0-0.5, r.x1+0.5, r.y1+0.5)
                    pg.add_redact_annot(cover, fill=PAPER); pg.apply_redactions(images=0, graphics=1, text=0)
                    barfn(pg, r.x0, r.y0, r.x1, r.y1)

def label(pg, s):
    pg.insert_font(fontname='lab', fontfile=FONTS['pbold'])
    pg.insert_text((24, 28), s, fontname='lab', fontsize=11, color=C('B5523B'))

# 결과 1: 시안별 6~8쪽을 이어 붙인 PDF, 결과 2: 6쪽 확대 PNG
os.makedirs(OUT, exist_ok=True)
book = fitz.open(); crops = []
variants = [(n, f, None) for n, f in TAGS] + [(n, None, f) for n, f in BARS]
for name, tf, bf in variants:
    d = fitz.open(SRC); d.select([5, 6, 7])
    apply(d, tf, bf)
    for p in d: label(p, name)
    book.insert_pdf(d)
    pix = d[0].get_pixmap(dpi=300, clip=fitz.Rect(140, 150, 545, 260))
    crops.append((name, pix))
book.save(os.path.join(OUT, 'TAG·막대_시안_미리보기.pdf'), garbage=3, deflate=True)
for i, (name, pix) in enumerate(crops):
    pix.save(os.path.join(OUT, 'crop_%02d.png' % i))
print('ok', len(variants))
