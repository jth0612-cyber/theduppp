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
# 시안 B · 수평선  (다니구치 건축관: 긴 처마선, 수면, 절제)
# ═══════════════════════════════════════════════════════════
def B_head(d, side, label):
    if side == 'even':
        d.rect(0, 11.6, 96, 13.2, S(), None)
        d.line(0, 13.2, W, 13.2, K(.8), .3)
        d.text(19, 24.5, label, 'pl', 15.5, K(), track=40)
    else:
        d.rect(W - 96, 11.6, W, 13.2, S(), None)
        d.line(0, 13.2, W, 13.2, K(.8), .3)
        d.text(243, 24.5, label, 'pl', 15.5, K(), 'r', track=40)

def B_foot(d, side, no):
    d.line(0, 351.2, W, 351.2, K(.3), .25)
    if side == 'even':
        d.text(19, 359.4, f'{no:02d}', 'pe', 15, K())
        d.text(34, 358.8, 'Squeeze', 'md', 11.5, K())
        d.text(53.2, 358.8, '기출 2', 'pl', 8.6, K(.7))
    else:
        d.text(243, 359.4, f'{no:02d}', 'pe', 15, K(), 'r')
        d.logo(205, 355, 4.2)

def B_num(d, x, y, no, lab, align='l'):
    if align == 'r':
        d.text(x, y, no, 'pe', 36, K(), 'r')
        d.rect(x - 22, y + 2.4, x, y + 3.1, S(), None)
        d.text(x, y + 8.4, lab, 'pr', 8.6, K(.75), 'r')
    else:
        wd = d.text(x, y - 1.2, no, 'pe', 34, K())
        d.rect(x + wd + 2.5, y - 4.2, x + wd + 3.1, y - .4, S(), None)
        d.text(x + wd + 5.6, y - 1.2, lab, 'pr', 8.6, K(.75))

def B_note(d):
    x0, y0, x1, y1 = 20, 190, 244, 347
    d.rect(x0, y0, x0 + 40, y0 + 1.2, S(), None)
    d.line(x0, y0 + 1.2, x1, y0 + 1.2, K(.75), .3)
    d.text(x0, y0 - 2, '풀이', 'pm', 9, S())
    y = y0 + 9
    while y < y1 - 1:
        d.line(x0, y, x1, y, K(.13), .25)
        y += 8
    d.line(x0, y1, x1, y1, K(.4), .3)

def B_solving(d):
    d.rect(134, 274.8, 140, 276.2, S(), None)
    x = 142 + d.text(142, 277.2, 'Solving', 'ps', 10.5, S(), track=120)
    d.line(x + 3, 275.5, 241.5, 275.5, K(.5), .25)

def B_logic(d, rows, unit):
    B_head(d, 'even', '기출 EXTRACT 2')
    d.text(19, 50, 'Logic Check', 'pe', 30, K())
    d.text(19, 58.5, unit, 'pr', 10.5, K(.75))
    d.rect(19, 62.5, 59, 63.7, S(), None)
    y = 38
    d.line(134, y - 6, 243, y - 6, K(.75), .3)
    for r in rows:
        d.text(134, y, r['no'], 'pl', 13, K())
        d.text(150, y - .3, r['src'], 'pr', 9.2, K(.8))
        d.text(219, y - .3, '회독', 'pl', 8.4, K(.65))
        for k in range(2):
            d.rect(229 + k * 5.4, y - 3.5, 232.6 + k * 5.4, y - .1, None, K(.7), .4)
        d.line(134, y + 4.2, 243, y + 4.2, K(.18), .25)
        y += 10.5
    B_foot(d, 'even', 4)


# ═══════════════════════════════════════════════════════════
# 시안 C · 면과 질감  (a.presse 아오야마: 절제된 면 분할, 리넨·콘크리트 결)
# ═══════════════════════════════════════════════════════════
def hatch(d, x0, y0, x1, y1, step=1.1, ang=60, color=None, w=0.22):
    """사각 영역 안에 가는 사선 결(리넨/콘크리트 패턴)."""
    sh = d.p.new_shape()
    t = math.tan(math.radians(ang))
    hgt = y1 - y0
    x = x0 - hgt / t
    while x < x1:
        ax, ay, bx, by = x, y1, x + hgt / t, y0
        # 사각형으로 자르기
        if ax < x0: ay = y1 - (x0 - ax) * t; ax = x0
        if bx > x1: by = y0 + (bx - x1) * t; bx = x1
        if ay > y0 and by < y1 and ax <= bx:
            sh.draw_line(f.Point(m(ax), m(ay)), f.Point(m(bx), m(by)))
        x += step
    sh.finish(color=color or S(.35), width=w); sh.commit()

def C_head(d, side, label):
    if side == 'even':
        d.rect(0, 0, 128, 22, S(.12), None)
        hatch(d, 0, 0, 128, 22, color=S(.5))
        d.rect(19, 16.2, 22, 19.2, S(), None)
        d.text(25, 19.2, label, 'pb', 13, K())
    else:
        d.rect(134, 0, W, 22, S(.12), None)
        hatch(d, 134, 0, W, 22, color=S(.5))
        d.rect(240, 16.2, 243, 19.2, S(), None)
        d.text(237, 19.2, label, 'pb', 13, K(), 'r')

def C_foot(d, side, no):
    if side == 'even':
        d.rect(0, 352, 26, 362, S(), None)
        d.text(19, 359.2, str(no), 'pb', 10, (1, 1, 1), 'r')
        d.text(30, 359.4, 'Squeeze', 'md', 12, K())
        d.text(49.2, 359.2, '기출 2', 'pr', 8.6, K(.7))
    else:
        d.rect(W - 26, 352, W, 362, S(), None)
        d.text(243, 359.2, str(no), 'pb', 10, (1, 1, 1))
        d.logo(203, 354.8, 4.4)

def C_num(d, x, y, no, lab, align='l'):
    wd = d.width(no, 'md', 24)
    bw = wd + 7
    bx = x - bw if align == 'r' else x
    d.rect(bx, y - 9.6, bx + bw, y + 1.4, K(), None)
    d.text(bx + 3.5, y - .9, no, 'md', 24, (1, 1, 1))
    lw = d.width(lab, 'pr', 8.6) + 5
    if align == 'r':
        lx, ly = bx + bw - lw, y + 1.4
    else:   # 짝수쪽은 바로 아래에 문제가 붙어서 출처를 오른쪽에
        lx, ly = bx + bw, y - 4.2
    d.rect(lx, ly, lx + lw, ly + 5.2, S(.18), None)
    d.text(lx + 2.5, ly + 3.7, lab, 'pr', 8.6, K(.85))

def C_note(d):
    x0, y0, x1, y1 = 20, 190, 244, 347
    d.poly([(x0, y0), (x1 - 8, y0), (x1, y0 + 8), (x1, y1), (x0, y1)], fill=S(.07), color=None)
    d.dots(x0 + 5, y0 + 13, x1 - 5, y1 - 5, 4.5, .17, S(.4))
    d.rect(x0, y0, x0 + 22, y0 + 7, K(), None)
    d.text(x0 + 4, y0 + 5.1, '풀이', 'pm', 9.5, (1, 1, 1))

def C_solving(d):
    d.rect(134, 272.4, 241.5, 280, S(.12), None)
    hatch(d, 168, 272.4, 241.5, 280, color=S(.5))
    d.rect(134, 272.4, 159, 280, K(), None)
    d.text(137.5, 278.2, 'Solving', 'md', 14, (1, 1, 1))

def C_logic(d, rows, unit):
    C_head(d, 'even', '기출 EXTRACT 2')
    d.rect(19, 34, 120, 92, S(.12), None)
    hatch(d, 19, 34, 120, 92, color=S(.5))
    d.text(25, 52, 'Logic Check', 'md', 28, K())
    d.text(25, 61, unit, 'pr', 10.5, K(.8))
    y = 40
    for i, r in enumerate(rows):
        if i % 2 == 0: d.rect(134, y - 5.5, 243, y + 3.5, S(.07), None)
        d.rect(134, y - 5.5, 147, y + 3.5, K(), None)
        d.text(140.5, y + .6, r['no'], 'md', 12.5, (1, 1, 1), 'c')
        d.text(151, y + .2, r['src'], 'pr', 9.2, K(.85))
        d.text(220, y + .2, '회독', 'pr', 8.4, K(.7))
        for k in range(2):
            d.rect(229 + k * 5.4, y - 3.2, 232.8 + k * 5.4, y + .6, (1, 1, 1), K(.6), .4)
        y += 10.5
    C_foot(d, 'even', 4)


VARIANTS = {
    'A_루버': dict(head=A_head, foot=A_foot, num=A_num, note=A_note, solving=A_solving, logic=A_logic),
    'B_수평선': dict(head=B_head, foot=B_foot, num=B_num, note=B_note, solving=B_solving, logic=B_logic),
    'C_면과질감': dict(head=C_head, foot=C_foot, num=C_num, note=C_note, solving=C_solving, logic=C_logic),
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
