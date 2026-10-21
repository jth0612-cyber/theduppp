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

def tag_C(pg, R, T, H, mirror=False):   # 제비꼬리 리본 (mirror: 우수, R 대신 왼쪽 끝 L)
    W = 34
    if mirror:
        L = R
        poly(pg, [(L, T), (L+W, T), (L+W-4.5, T+H/2), (L+W, T+H), (L, T+H)], ACC)
        text(pg, L, mid(T, H, 8), 'TAG', 'pbold', 8, WHITE, 'center', W-3, spacing=0.6)
        return
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

import io
from PIL import Image, ImageDraw
def tex_poly(pg, pts, fill, overlay=None, alpha=0.0, scale=8):
    # 나뭇결(사진) 또는 단색으로 다각형을 채운다. 사진은 다각형 모양으로 오려서 넣는다.
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    box = fitz.Rect(min(xs), min(ys), max(xs), max(ys))
    if fill != 'wood':
        poly(pg, pts, fill); return
    W, H = max(1, int(box.width*scale)), max(1, int(box.height*scale))
    im = Image.open(WOOD).convert('RGB').resize((W, H))
    if overlay:
        ov = Image.new('RGB', (W, H), tuple(int(c*255) for c in overlay)); im = Image.blend(im, ov, alpha)
    m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).polygon([((x-box.x0)*scale, (y-box.y0)*scale) for x, y in pts], fill=255)
    im.putalpha(m); b = io.BytesIO(); im.save(b, 'PNG'); pg.insert_image(box, stream=b.getvalue())

def make_bar_B(block, body, num_c, title_c, seam='paper', bottom=None, ov_block=(None, 0), ov_body=(None, 0)):
    def f(pg, X0, Y0, X1, Y1):
        H = Y1 - Y0; W = 36; d = 6
        tex_poly(pg, [(X0+W-d, Y0), (X1, Y0), (X1, Y1), (X0+W-d, Y1), (X0+W, Y0+H/2)], body, *ov_body)
        if seam is not None:
            sc = PAPER if seam == 'paper' else seam
            poly(pg, [(X0+W-d-1.2, Y0), (X0+W-d, Y0), (X0+W, Y0+H/2), (X0+W-d, Y1), (X0+W-d-1.2, Y1), (X0+W-1.2, Y0+H/2)], sc)
        tex_poly(pg, [(X0, Y0), (X0+W-d-1.2, Y0), (X0+W-1.2, Y0+H/2), (X0+W-d-1.2, Y1), (X0, Y1)], block, *ov_block)
        if bottom: line(pg, (X0, Y1), (X1, Y1), bottom, 1.0)
        text(pg, X0+4, mid(Y0, H, 16), NUM, 'pblack', 16, num_c, 'center', W-12)
        text(pg, X0+W+8, mid(Y0, H, 12), TITLE, 'gangwon', 12, title_c)
    return f

BARS_B = [('막대 B · 기본 (주황 + 진갈)', make_bar_B(ACC, BAR, WHITE, WHITE)),
          ('B-1 · 주황 + 원목결', make_bar_B(ACC, 'wood', WHITE, INK, bottom=INK)),
          ('B-2 · 원목 + 월넛(아주 진한 갈색)', make_bar_B('wood', C('2E1C16'), INK, C('F3E2CC'))),
          ('B-3 · 진갈 + 탄색 (밝은 바탕)', make_bar_B(BAR, TAN, C('F3D9BE'), INK)),
          ('B-4 · 톤온톤 크림 + 갈색 밑줄', make_bar_B(ACC, C('EFDFCB'), WHITE, INK, bottom=BAR)),
          ('B-5 · 짙은 원목 + 원목 (나뭇결 두 톤)', make_bar_B('wood', 'wood', C('F3E2CC'), INK, bottom=INK, ov_block=(INK, 0.62)))]

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
                rule = [d['rect'].x0 for d in pg.get_drawings() if d['rect'].width < 1 and d['rect'].height > 600]
                if rule and r.x0 > rule[0] and tagfn is tag_C:   # 우수: 세로선 오른쪽에 붙여 대칭
                    tagfn(pg, rule[0], r.y0, r.height, mirror=True)
                else:
                    tagfn(pg, r.x1, r.y0, r.height)
        if barfn:
            for dr in pg.get_drawings():
                r = dr['rect']; f = dr.get('fill')
                if f and abs(f[0]-0.3529) < 0.01 and 20 < r.height < 25 and r.width > 300:
                    cover = fitz.Rect(r.x0-0.5, r.y0-0.5, r.x1+0.5, r.y1+0.5)
                    pg.add_redact_annot(cover, fill=PAPER); pg.apply_redactions(images=0, graphics=1, text=0)
                    barfn(pg, r.x0, r.y0, r.x1, r.y1)

OLD_PAPER = PAPER
def repaper(doc, new):
    # 바탕색 바꾸기: 그리기 명령의 바탕색을 바꾸고, 그림 속 바탕색 부분도 같이 옮긴다
    old_s = ' '.join('%.4f' % v for v in OLD_PAPER).encode()
    new_s = ' '.join('%.4f' % v for v in new).encode()
    done = set()
    for pg in doc:
        for x in pg.get_contents():
            st = doc.xref_stream(x)
            if old_s in st: doc.update_stream(x, st.replace(old_s, new_s))
        for img in pg.get_images(full=True):
            xr, smask = img[0], img[1]
            if xr in done: continue
            done.add(xr)
            pix = fitz.Pixmap(doc, xr)
            if pix.n - pix.alpha != 3: continue
            im = Image.frombytes('RGB', (pix.width, pix.height), fitz.Pixmap(pix, 0).samples if pix.alpha else pix.samples)
            o = [v*255 for v in OLD_PAPER]; n = [v*255 for v in new]
            px = im.load(); W, H = im.size
            import numpy as np
            a = np.asarray(im).astype(np.float32)
            dist = np.sqrt(((a - np.array(o))**2).sum(-1))
            w = np.clip(1 - dist/70, 0, 1)[..., None]
            a = np.clip(a + w*(np.array(n) - np.array(o)), 0, 255).astype(np.uint8)
            b = io.BytesIO(); Image.fromarray(a).save(b, 'JPEG' if img[8] == 'DCTDecode' else 'PNG', quality=92)
            pg.replace_image(xr, stream=b.getvalue())

def label(pg, s):
    pg.insert_font(fontname='lab', fontfile=FONTS['pbold'])
    pg.insert_text((24, 28), s, fontname='lab', fontsize=11, color=C('B5523B'))

# 결과 1: 시안별 6~8쪽을 이어 붙인 PDF, 결과 2: 6쪽 확대 PNG
os.makedirs(OUT, exist_ok=True)
book = fitz.open(); crops = []
PAPERS = [p for p in os.environ.get('PAPERS', '').split(',') if p]   # 예: PAPERS=FAF5EE,FCF9F3
FIX = os.environ.get('FIXED_TAG')
BSET = os.environ.get('BAR_SET') == 'B'
ONLY = os.environ.get('ONLY_BAR')   # 예: ONLY_BAR=4 → BARS_B[4] 하나만   # 예: FIXED_TAG=C → TAG를 C로 고정하고 막대 시안만
if FIX:
    ft = dict(A=tag_A, B=tag_B, C=tag_C, D=tag_D, E=tag_E)[FIX]
    variants = ([] if BSET else [('현재 막대 + TAG ' + FIX, ft, None)]) + [(n + ' + TAG ' + FIX, ft, f) for n, f in (([BARS_B[int(ONLY)]] if ONLY else BARS_B) if BSET else BARS)]
else:
    variants = [(n, f, None) for n, f in TAGS] + [(n, None, f) for n, f in BARS]
if PAPERS:
    variants = [(v[0] + ' · 바탕 #' + pp, v[1], v[2], pp) for v in variants for pp in PAPERS]
else:
    variants = [(v[0], v[1], v[2], None) for v in variants]
for name, tf, bf, pp in variants:
    d = fitz.open(SRC)
    if not os.environ.get("ALL_PAGES"): d.select([5, 6, 7])
    if pp:
        PAPER = C(pp); repaper(d, PAPER)
    else:
        PAPER = OLD_PAPER
    apply(d, tf, bf)
    if not os.environ.get("NO_LABEL"):
        for p in d: label(p, name)
    book.insert_pdf(d)
    pix = d[0].get_pixmap(dpi=300, clip=fitz.Rect(140, 150, 545, 260))
    crops.append((name, pix))
book.save(os.path.join(OUT, 'TAG·막대_시안_미리보기.pdf'), garbage=3, deflate=True)
for i, (name, pix) in enumerate(crops):
    pix.save(os.path.join(OUT, 'crop_%02d.png' % i))
print('ok', len(variants))
