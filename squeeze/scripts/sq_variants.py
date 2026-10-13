# Squeeze 내지 틀 교체 시안: 원본 4~7쪽에서 틀 요소만 지우고 새 틀을 벡터로 그린다.
# 사용: python sq_variants.py <squeeze.pdf> <resources.pdf> <fontdir> <outdir>
import sys, os, math, re
import pymupdf as f

SRC, RES, FD, OUT = sys.argv[1:5]
os.makedirs(OUT, exist_ok=True)
MM = 72 / 25.4
W, H = 262, 371
m = lambda v: v * MM
R = lambda x0, y0, x1, y1: f.Rect(m(x0), m(y0), m(x1), m(y1))

FONTS = {
    'md': 'md/Million Dreams.otf',
    'pt': f'{FD}/alternative/Pretendard-Thin.ttf', 'pe': f'{FD}/alternative/Pretendard-ExtraLight.ttf', 'pl': f'{FD}/alternative/Pretendard-Light.ttf',
    'pr': f'{FD}/alternative/Pretendard-Regular.ttf', 'pm': f'{FD}/alternative/Pretendard-Medium.ttf',
    'ps': f'{FD}/alternative/Pretendard-SemiBold.ttf', 'pb': f'{FD}/alternative/Pretendard-Bold.ttf',
}
FO = {k: f.Font(fontfile=v) for k, v in FONTS.items()}

# 2도: 먹(K) + 별색(S). 별색은 자리표시(기존 하늘색). 농도 t(0~1)로만 쓴다.
K_ = (0x23 / 255, 0x1F / 255, 0x20 / 255)
S_ = (0x00 / 255, 0xA2 / 255, 0xDB / 255)
def tint(c, t): return tuple(1 - t * (1 - v) for v in c)
K = lambda t=1: tint(K_, t)
S = lambda t=1: tint(S_, t)

src = f.open(SRC)
res = f.open(RES)

norm = lambda t: re.sub('[\u2010-\u2015\u2212]', '-', t)

# ── 원본 문항 정보(4쪽 Logic Check 목록) ───────────────────────────
def logic_rows(pg):
    rows = {}
    for b in src[pg - 1].get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                y = round(s['bbox'][1] / MM)
                if s['font'].startswith('Montserrat'): rows.setdefault(y, {})['no'] = norm(s['text'])
                elif s['color'] == 0xFFFFFF: rows.setdefault(y, {})['src'] = s['text'].replace('\xa0', ' ')
    return [rows[k] for k in sorted(rows) if 'no' in rows[k]]

def prob_info(pg):
    no = lab = None
    for b in src[pg - 1].get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                if s['font'].startswith('Montserrat') and s['size'] > 30: no = norm(s['text'])
                if s['color'] == 0xFFFFFF and '학년도' in s['text']: lab = s['text'].replace('\xa0', ' ')
    return no, lab

# ── 틀 지우기 ───────────────────────────────────────────────
def wipe(page, rects, everything=False):
    if everything:
        rects = [(0, 0, W, H)]
    for r in rects:
        page.add_redact_annot(R(*r), fill=False)
    page.apply_redactions(images=f.PDF_REDACT_IMAGE_NONE,
                          graphics=f.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED,
                          text=f.PDF_REDACT_TEXT_REMOVE)

def strip_frame(page, kind):
    if kind == 'logic':
        wipe(page, None, everything=True)
    elif kind == 'odd':
        wipe(page, [(-5, -5, W + 5, 30), (-5, 348, W + 5, H + 5), (55, 32, 112, 59), (18, 188, 246, 349)])
    elif kind == 'even':
        wipe(page, [(-5, -5, W + 5, 30), (-5, 348, W + 5, H + 5), (15, 33, 100, 49.9), (133, 271, 243, 280.6)])

# ── 그리기 도우미 ─────────────────────────────────────────────
class P:
    def __init__(s, page):
        s.p = page
        for k, v in FONTS.items():
            page.insert_font(fontname=k, fontfile=v)
    def rect(s, x0, y0, x1, y1, fill=None, color=None, w=0.5, op=1):
        s.p.draw_rect(R(x0, y0, x1, y1), color=color, fill=fill, width=w, fill_opacity=op, stroke_opacity=op)
    def line(s, x0, y0, x1, y1, color, w=0.3):
        s.p.draw_line(f.Point(m(x0), m(y0)), f.Point(m(x1), m(y1)), color=color, width=w)
    def poly(s, pts, fill=None, color=None, w=0.3, closed=True):
        sh = s.p.new_shape()
        sh.draw_polyline([f.Point(m(x), m(y)) for x, y in pts] + ([f.Point(m(pts[0][0]), m(pts[0][1]))] if closed else []))
        sh.finish(color=color, fill=fill, width=w, closePath=closed)
        sh.commit()
    def circle(s, x, y, r, fill=None, color=None, w=0.3):
        s.p.draw_circle(f.Point(m(x), m(y)), m(r), color=color, fill=fill, width=w)
    def width(s, text, font, size, track=0):
        # track: 1/1000 em
        return (FO[font].text_length(text, fontsize=size) + track / 1000 * size * max(len(text) - 1, 0)) / MM
    def text(s, x, y, text, font, size, color, align='l', track=0):
        """y = 기준선(mm). track = 자간(1/1000 em)."""
        wd = s.width(text, font, size, track)
        if align == 'r': x -= wd
        elif align == 'c': x -= wd / 2
        if not track:
            s.p.insert_text(f.Point(m(x), m(y)), text, fontname=font, fontsize=size, color=color)
        else:
            cx = m(x)
            for ch in text:
                s.p.insert_text(f.Point(cx, m(y)), ch, fontname=font, fontsize=size, color=color)
                cx += FO[font].text_length(ch, fontsize=size) + track / 1000 * size
        return wd
    def logo(s, x, y, h=5.3, color_keep=True):
        # THedu 로고(벡터)를 리소스 22쪽에서 잘라 와 배치. 원본 높이 5.3mm.
        clip = R(199.6, 354.2, 224.2, 359.8)
        wd = (224.2 - 199.6) * h / 5.6
        s.p.show_pdf_page(R(x, y, x + wd, y + h), res, 21, clip=clip)
        return wd
    def dots(s, x0, y0, x1, y1, step, r, color):
        sh = s.p.new_shape()
        y = y0
        while y <= y1 + 1e-6:
            x = x0
            while x <= x1 + 1e-6:
                sh.draw_circle(f.Point(m(x), m(y)), m(r)); x += step
            y += step
        sh.finish(fill=color, color=None); sh.commit()


# ═══════════════════════════════════════════════════════════
# 시안 A · 루버  (국립신미술관: 물결치는 유리 루버, 가는 수직선의 반복)
# ═══════════════════════════════════════════════════════════
def louver(d, x0, x1, top, base, amp, period, step=1.15, w=0.34, color=None, fade=True, phase=0, rev=False):
    """x0~x1 구간에 수직 헤어라인. 길이는 물결(base + amp*sin) * 감쇠."""
    sh = d.p.new_shape()
    n = int(abs(x1 - x0) / step)
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t
        k = (1 - t) ** 1.6 if fade else 1
        L = (base + amp * math.sin(2 * math.pi * (t * (x1 - x0) / period) + phase)) * k
        if L < 0.25: continue
        sh.draw_line(f.Point(m(x), m(top)), f.Point(m(x), m(top + L)))
    sh.finish(color=color or S(), width=w); sh.commit()

def A_head(d, side, label):
    if side == 'even':
        louver(d, 0, 150, 0, 10, 4, 46)
        d.line(0, 15.5, 150, 15.5, K(.85), .35)
        d.text(19, 25.5, label, 'ps', 15, K(), track=-10)
    else:
        louver(d, W, 112, 0, 10, 4, 46, phase=math.pi)
        d.line(112, 15.5, W, 15.5, K(.85), .35)
        d.text(243, 25.5, label, 'ps', 15, K(), 'r', track=-10)

def A_foot(d, side, no):
    if side == 'even':
        d.text(19, 359, str(no), 'pm', 10, K())
        louver(d, 27, 33, 355.2, 4.2, 0, 10, step=1.15, fade=False)
        x = 36 + d.text(36, 359.2, 'Squeeze', 'md', 13, S())
        d.text(x + 2.2, 359, '기출 2', 'pl', 9, K(.7))
    else:
        d.text(243, 359, str(no), 'pm', 10, K(), 'r')
        louver(d, 229, 235, 355.2, 4.2, 0, 10, step=1.15, fade=False)
        d.logo(198, 354.6, 4.6)

def A_num(d, x, y, no, lab, align='l'):
    # 문항 번호: Million Dreams / 출처: 루버 다발 + 가는 글자
    if align == 'r':
        d.text(x, y, no, 'md', 34, S(), 'r')
        louver(d, x - 46, x - 40.5, y + 3.2, 3.8, 0, 10, fade=False)
        d.text(x, y + 6.6, lab, 'pr', 8.6, K(.75), 'r')
    else:
        wd = d.text(x, y, no, 'md', 34, S())
        louver(d, x + wd + 3, x + wd + 8.5, y - 6.6, 3.8, 0, 10, fade=False)
        d.text(x + wd + 10.5, y - 3.1, lab, 'pr', 8.6, K(.75))

def A_note(d):
    x0, y0, x1, y1 = 20, 190, 244, 347
    louver(d, x0, x1, y0, 2.6, 0, 10, step=1.15, fade=False, w=.25)
    d.line(x0, y0 + 2.6, x1, y0 + 2.6, S(), .35)
    d.dots(x0 + 4, y0 + 8, x1 - 4, y1 - 4, 4.5, .17, S(.45))
    d.line(x0, y1, x1, y1, K(.5), .3)
    d.text(x0 + 1, y0 + 9, 'Note', 'md', 14, S())

def A_solving(d):
    x = 134 + d.text(134, 278.8, 'Solving', 'md', 16, S())
    louver(d, x + 3, 241.5, 274.2, 4.2, 1.4, 22, step=1.15)
    d.line(x + 3, 278.4, 241.5, 278.4, S(.6), .25)

def A_logic(d, rows, unit):
    A_head(d, 'even', '기출 EXTRACT 2')
    d.text(19, 50, 'Logic Check', 'md', 30, K())
    d.text(19, 58.5, unit, 'pl', 11, K(.75))
    louver(d, 19, 112, 64, 6, 2.5, 30, step=1.15)
    d.line(128, 34, 128, 347, K(.35), .3)
    y = 40
    for r in rows:
        d.text(136, y, r['no'], 'md', 15, S())
        d.text(152, y - .4, r['src'], 'pr', 9.4, K(.85))
        d.text(214, y - .4, '회독', 'pl', 8.5, K(.7))
        for k in range(2):
            d.rect(223.5 + k * 5.2, y - 3.6, 227.3 + k * 5.2, y - .2, None, S(), .5)
        d.line(136, y + 3.4, 233, y + 3.4, K(.18), .25)
        y += 10.5
    A_foot(d, 'even', 4)


# ═══════════════════════════════════════════════════════════
# 시안 A2 · 매듭  (A 루버의 가는 선 + 꼬이며 매듭짓는 말랑한 리본)
# 가는 선 여러 가닥이 모인 리본이 고리를 만들며 비틀리고(회전), 교차점마다 위·아래가 갈린다.
# 리본 면은 비틀림 각도에 따라 별색 농도가 부드럽게 바뀌어 말랑한 고무줄 같은 질감을 낸다.
# ═══════════════════════════════════════════════════════════
def loop_path(x0, x1, yc, loops, a, b, n=900, decay=0.9, phase=0):
    """x0→x1로 가며 고리를 만드는 경로(트로코이드). 갈수록 고리가 풀린다. (x, y, z) 목록."""
    sg = 1 if x1 > x0 else -1
    pts = []
    for i in range(n + 1):
        t = i / n
        th = 2 * math.pi * loops * t + phase
        k = (1 - t) ** decay
        x = x0 + (x1 - x0) * t - sg * a * k * math.sin(th)
        y = yc - b * k * math.cos(th)
        pts.append((x, y, math.sin(th) * k))
    return pts

def torus_path(cx, cy, scale, p=3, q=7, r=0.5, tilt=22, rotz=8, n=2400):
    ct, st = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
    cz, sz = math.cos(math.radians(rotz)), math.sin(math.radians(rotz))
    pts = []
    for i in range(n + 1):
        t = 2 * math.pi * i / n
        X = (1 + r * math.cos(q * t)) * math.cos(p * t); Y = (1 + r * math.cos(q * t)) * math.sin(p * t); Z = r * math.sin(q * t)
        Y, Z = Y * ct - Z * st, Y * st + Z * ct
        X, Y = X * cz - Y * sz, X * sz + Y * cz
        pts.append((cx + scale * X, cy - scale * Y, Z))
    return pts

def ribbon(d, pts, width, turns, strands=9, lw=0.22, edge=0.42, taper=True, phase=0.6,
           shade=(0.05, 0.2), line=None):
    """pts 경로를 따라 비틀리는 리본. 깊이(z) 순서로 면 + 선을 그려 교차의 위·아래를 만든다."""
    line = line or S()
    n = len(pts) - 1
    C = []
    for i in range(n + 1):
        x, y, z = pts[i]
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, n)]
        tx, ty = b[0] - a[0], b[1] - a[1]; L = math.hypot(tx, ty) or 1
        t = i / n
        phi = 2 * math.pi * turns * t + phase
        hw = width / 2 * ((0.3 + 0.7 * (1 - t) ** 0.6) if taper else 1)
        C.append((x, y, z, -ty / L, tx / L, hw * math.cos(phi), math.cos(phi)))
    order = sorted(range(n), key=lambda i: (C[i][2] + C[i + 1][2]) / 2)
    sh = d.p.new_shape()
    off = [-1 + 2 * k / (strands - 1) for k in range(strands)]
    for i in order:
        x0, y0, _, nx0, ny0, h0, c0 = C[i]
        x1, y1, _, nx1, ny1, h1, c1 = C[i + 1]
        # 이웃 조각과 이음새가 보이지 않게 앞뒤로 살짝 겹친다
        ex, ey = (x1 - x0) * 0.35, (y1 - y0) * 0.35
        q = [(x0 - ex + nx0 * h0, y0 - ey + ny0 * h0), (x1 + ex + nx1 * h1, y1 + ey + ny1 * h1),
             (x1 + ex - nx1 * h1, y1 + ey - ny1 * h1), (x0 - ex - nx0 * h0, y0 - ey - ny0 * h0)]
        cc = abs(c0 + c1) / 2
        tn = shade[0] + (shade[1] - shade[0]) * cc ** 0.7
        sh.draw_polyline([f.Point(m(px), m(py)) for px, py in q] + [f.Point(m(q[0][0]), m(q[0][1]))])
        sh.finish(fill=S(tn), color=None, closePath=True)
        for k, s_ in enumerate(off):
            sh.draw_line(f.Point(m(x0 + nx0 * h0 * s_), m(y0 + ny0 * h0 * s_)),
                         f.Point(m(x1 + nx1 * h1 * s_), m(y1 + ny1 * h1 * s_)))
            sh.finish(color=line, width=edge if k in (0, strands - 1) else lw, lineCap=1, lineJoin=1)
    sh.commit()

def K_head(d, side, label):
    if side == 'even':
        ribbon(d, loop_path(-6, 160, 12, 7, 7.2, 6.8, n=1400, decay=0.45), 4.6, 5, strands=9, shade=(0.06, 0.32))
        d.text(19, 28, label, 'ps', 15, K(), track=-10)
    else:
        ribbon(d, loop_path(W + 6, 102, 12, 7, 7.2, 6.8, n=1400, decay=0.45), 4.6, 5, strands=9, shade=(0.06, 0.32))
        d.text(243, 28, label, 'ps', 15, K(), 'r', track=-10)

def K_mark(d, x, y, wd=11, flip=False):
    """작은 매듭 표식(고리 하나)."""
    x0, x1 = (x + wd, x) if flip else (x, x + wd)
    ribbon(d, loop_path(x0, x1, y, 1, wd * 0.3, wd * 0.24, n=260, decay=0.0, phase=-math.pi), wd * 0.2, 1.0,
           strands=5, lw=0.18, edge=0.32, taper=False, shade=(0.08, 0.3))

def K_foot(d, side, no):
    if side == 'even':
        d.text(19, 359, str(no), 'pm', 10, K())
        K_mark(d, 25.5, 357.2, 8)
        x = 37 + d.text(37, 359.2, 'Squeeze', 'md', 13, S())
        d.text(x + 2.2, 359, '기출 2', 'pl', 9, K(.7))
    else:
        d.text(243, 359, str(no), 'pm', 10, K(), 'r')
        K_mark(d, 228, 357.2, 8, flip=True)
        d.logo(198, 354.6, 4.6)

def K_num(d, x, y, no, lab, align='l'):
    if align == 'r':
        d.text(x, y, no, 'md', 34, S(), 'r')
        K_mark(d, x - 49, y + 4.4, 8)
        d.text(x, y + 6.6, lab, 'pr', 8.6, K(.75), 'r')
    else:
        wd = d.text(x, y, no, 'md', 34, S())
        K_mark(d, x + wd + 3.5, y - 4.4, 8)
        d.text(x + wd + 15, y - 3.1, lab, 'pr', 8.6, K(.75))

def K_note(d):
    x0, y0, x1, y1 = 20, 190, 244, 347
    d.p.draw_rect(R(x0, y0, x1, y1), color=None, fill=S(.05), radius=6 / (y1 - y0))
    d.dots(x0 + 6, y0 + 14, x1 - 6, y1 - 6, 4.5, .17, S(.45))
    ribbon(d, loop_path(x0 - 4, x0 + 96, y0 + 1, 3, 4.6, 4.2, n=700, decay=0.5), 4, 2, strands=7, shade=(0.06, 0.3))
    d.text(x0 + 3, y0 + 12, 'Note', 'md', 14, S())

def K_solving(d):
    x = 134 + d.text(134, 278.8, 'Solving', 'md', 16, S())
    ribbon(d, loop_path(x + 3, 243, 275.6, 3, 4.2, 3.6, n=600, decay=0.5), 3.6, 1.8, strands=7, shade=(0.06, 0.3))

def K_logic(d, rows, unit):
    K_head(d, 'even', '기출 EXTRACT 2')
    d.text(19, 52, 'Logic Check', 'md', 30, K())
    d.text(19, 60.5, unit, 'pl', 11, K(.75))
    ribbon(d, torus_path(66, 152, 31), 6.2, 9, strands=9, taper=False, shade=(0.05, 0.26))
    d.line(128, 36, 128, 347, K(.35), .3)
    y = 42
    for r in rows:
        d.text(136, y, r['no'], 'md', 15, S())
        d.text(152, y - .4, r['src'], 'pr', 9.4, K(.85))
        d.text(214, y - .4, '회독', 'pl', 8.5, K(.7))
        for k in range(2):
            d.p.draw_rect(R(223.5 + k * 5.2, y - 3.6, 227.3 + k * 5.2, y - .2), color=S(), width=.5, radius=.3)
        d.line(136, y + 3.4, 233, y + 3.4, K(.18), .25)
        y += 10.5
    K_foot(d, 'even', 4)


VARIANTS = {
    'A_루버': dict(head=A_head, foot=A_foot, num=A_num, note=A_note, solving=A_solving, logic=A_logic),
    'A2_매듭': dict(head=K_head, foot=K_foot, num=K_num, note=K_note, solving=K_solving, logic=K_logic),
}
UNIT = {'A': '고체', 'B': '유체', 'C': '천체'}

def build(name, V, pages=(4, 5, 6, 7)):
    out = f.open()
    out.insert_pdf(src, from_page=pages[0] - 1, to_page=pages[-1] - 1)
    rows = logic_rows(4)
    for i, pg in enumerate(pages):
        page = out[i]
        if pg == 4:
            strip_frame(page, 'logic'); d = P(page); V['logic'](d, rows, 'A. 고체'); continue
        no, lab = prob_info(pg)
        side = 'odd' if pg % 2 else 'even'
        strip_frame(page, side); d = P(page)
        if side == 'odd':
            V['head'](d, 'odd', UNIT[no[0]])
            V['num'](d, 108, 47, no, lab, 'r')
            V['note'](d)
        else:
            V['head'](d, 'even', '기출 EXTRACT 2')
            V['num'](d, 19, 47, no, lab)
            V['solving'](d)
        V['foot'](d, side, pg)
    out.subset_fonts()
    out.save(f'{OUT}/{name}.pdf', garbage=4, deflate=True)
    return f'{OUT}/{name}.pdf'

if __name__ == '__main__':
    for k, v in VARIANTS.items():
        print(build(k, v))
