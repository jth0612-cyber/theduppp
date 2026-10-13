# Squeeze 내지 01-01: 매듭 코일 상단바(펼침면 연속) + 판화풍 튜브로 통일한 틀.
# 사용: python sq_v01.py <squeeze.pdf> <resources.pdf> <출력.pdf>
import sys, math
sys.path.insert(0, '.')
from sq_lib import *

SRC, RES, OUT = sys.argv[1:4]
src, res = f.open(SRC), f.open(RES)

# ── 체계 ────────────────────────────────────────────────
# 여백: 바깥 19mm. 단: 짝수 19–128 | 134–243, 홀수 문제 단 119–228(번호는 왼쪽 여백 끝 108에 맞춤)
# 기준선: 머리 글자 30, 번호 47, 하단 359. 선 굵기: 윤곽 0.38pt, 나선 0.2pt, 괘선 0.25pt
# 글자: 머리 13pt / 번호 32pt / 출처 8.4pt / 하단 9pt
LBL, NUM, SRCSZ, FOOT = 13, 32, 8.4, 9

def env(t, end):
    return max(1 - smooth(0, end * 2.2, t), 1 - smooth(0, end * 2.2, 1 - t))

COIL = dict(loops=30, A=13, B=6.0, end=0.24)
def head_coil(d, side):
    """펼침면 전체를 가로지르는 코일. 짝수쪽은 펼침면 왼쪽 절반, 홀수쪽은 오른쪽 절반."""
    L, e_ = COIL['loops'], COIL['end']
    rad = lambda t: 1.85 * (0.5 + 0.5 * env(t, e_)) * (0.86 + 0.14 * math.cos(2 * math.pi * L * t))
    d.dx = 0 if side == 'even' else W
    tube(d, spread_knot(n=6000, yc=12, **COIL), rad, strands=13, twist=L * 2.2, lw=0.2, edge=0.38,
         xclip=(0, W))
    d.dx = 0

def short_coil(d, x0, x1, y, loops, A, B, r, taper=(0.15, 0.85)):
    """짧은 코일: 양 끝이 가늘게 눌린다."""
    n = 220 * loops
    pts = []
    for i in range(n + 1):
        t = i / n
        th = 2 * math.pi * loops * t
        e = smooth(0, taper[0], t) * (1 - smooth(taper[1], 1, t))
        pts.append((x0 + (x1 - x0) * t - A * (0.35 + 0.65 * e) * math.sin(th), y - B * (0.4 + 0.6 * e) * math.cos(th), math.sin(th)))
    tube(d, pts, lambda t: r * (0.45 + 0.55 * smooth(0, taper[0], t) * (1 - smooth(taper[1], 1, t))),
         strands=11, twist=loops * 2.2, lw=0.18, edge=0.34)

def head_label(d, side, unit=None):
    if side == 'even':
        x = 19 + d.text(19, 30, '기출', 'ps', LBL, K())
        d.text(x + 2.2, 30, 'EXTRACT 2', 'pl', LBL, K(), track=40)
    else:
        w2 = d.width(unit[1], 'ps', LBL)
        d.text(243, 30, unit[1], 'ps', LBL, K(), 'r')
        d.text(243 - w2 - 2.4, 30.4, unit[0], 'md', LBL + 2, S(), 'r')

def number(d, side, no, lab):
    if side == 'odd':     # 왼쪽 여백 끝(108)에 오른쪽 맞춤, 출처는 아래
        d.text(108, 47, no, 'md', NUM, S(), 'r')
        d.line(108 - 30, 50.6, 108, 50.6, K(.35), .25)
        d.text(108, 55.2, lab, 'pr', SRCSZ, K(.7), 'r')
    else:                 # 왼쪽 단 시작(19), 출처는 오른쪽 세로 괘선 뒤
        wd = d.text(19, 47, no, 'md', NUM, S())
        d.line(19 + wd + 3, 39.6, 19 + wd + 3, 46.6, K(.35), .25)
        d.text(19 + wd + 5.6, 46.4, lab, 'pr', SRCSZ, K(.7))

def note(d):
    x0, y0, x1, y1 = 20, 190, 244, 347
    d.rect(x0, y0, x1, y1, None, S(.55), .35, radius=4 / (y1 - y0))
    d.dots(x0 + 7, y0 + 12, x1 - 7, y1 - 7, 5, .18, S(.42))
    short_coil(d, 12, 60, y0, 5, 6.5, 3.4, 1.15)       # 테두리를 넘나들며 엮인 코일
    wl = d.width('풀이', 'pm', 8.6)
    d.rect(62.5, y0 - 2.5, 62.5 + wl + 3, y0 + 2.5, PAPER, None)
    d.text(64, y0 + 1.3, '풀이', 'pm', 8.6, S())

def solving(d):
    x = 134 + d.text(134, 278.6, 'Solving', 'md', 15, S())
    short_coil(d, x + 4, 243, 276.2, 9, 4.6, 2.6, 0.95, taper=(0.04, 0.55))

def footer(d, side, no):
    if side == 'even':
        d.text(19, 359, str(no), 'pm', FOOT + .5, K())
        x = 28 + d.text(28, 359.2, 'Squeeze', 'md', 12, K())
        d.text(x + 2, 359, '기출 2', 'pl', FOOT - 1, K(.6))
    else:
        d.text(243, 359, str(no), 'pm', FOOT + .5, K(), 'r')
        d.logo(205.5, 355.2, 4.2)

def logic(d, rows, unit):
    head_coil(d, 'even'); head_label(d, 'even')
    d.text(19, 52, 'Logic Check', 'md', 30, K())
    d.text(19, 60.5, unit, 'pl', 11, K(.7))
    tube(d, torus_knot(66, 196, 31, r=0.4, n=4000), lambda t: 1.75, strands=12, twist=30, lw=0.2, edge=0.36, chunk=5)
    d.line(128, 40, 128, 347, K(.3), .25)
    y = 46
    d.line(136, y - 7.2, 243, y - 7.2, K(.5), .3)
    for r in rows:
        d.text(136, y, r['no'], 'md', 14, S())
        d.text(153, y - .3, r['src'], 'pr', 9, K(.85))
        d.text(219, y - .3, '회독', 'pl', 8, K(.6))
        for k in range(2):
            d.rect(228.6 + k * 5.6, y - 3.5, 232.4 + k * 5.6, y + .3, None, S(), .45, radius=.28)
        d.line(136, y + 3.6, 243, y + 3.6, K(.15), .25)
        y += 10.5
    footer(d, 'even', 4)

UNIT = {'A': ('A', '고체'), 'B': ('B', '유체'), 'C': ('C', '천체')}

def build(pages=(4, 5, 6, 7)):
    out = f.open()
    out.insert_pdf(src, from_page=pages[0] - 1, to_page=pages[-1] - 1)
    rows = logic_rows(src, 4)
    for i, pg in enumerate(pages):
        page = out[i]
        if pg == 4:
            strip_frame(page, 'logic'); logic(P(page, res), rows, 'A. 고체'); continue
        no, lab = prob_info(src, pg)
        side = 'odd' if pg % 2 else 'even'
        strip_frame(page, side); d = P(page, res)
        head_coil(d, side)
        head_label(d, side, UNIT[no[0]])
        number(d, side, no, lab)
        (note if side == 'odd' else solving)(d)
        footer(d, side, pg)
    out.subset_fonts()
    out.save(OUT, garbage=4, deflate=True)
    print(OUT)

build()
