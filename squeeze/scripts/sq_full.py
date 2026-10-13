# Squeeze 기출 EXTRACT 2 전체(84쪽)에 03-01-09 디자인 적용.
# 03-01-09 = 상단 세로 핀(무작위 윤곽, 편차 50%, 회색 핀) / 번호 Barlow Condensed Medium 500 /
#            풀이 칸 P3 + 원본 배경 점 14% / Solving·Linking 머리 = 단어 + 핀 줄(2안) + 원본 아이콘
# 사용: python sq_full.py <squeeze.pdf> <resources.pdf> <출력.pdf>
import sys, re
import numpy as np
sys.path.insert(0, '.')
import sq8, sq9
from sq8 import set_numfont, H1g, NUMFONT, fin_stack
from sq9 import mix_gray, DOT_T
from sq5 import label_default, foot_default
from sq7 import fins, draw_fins, PAL, sm
from sq_lib import P, wipe, prob_info, logic_rows, f, m, R, W, H, S, K, S_, K_, tint, PAPER

MM = 72 / 25.4
CYAN = (0, 162, 219); DOTC = (0x6E, 0xC8, 0xEC)
col = lambda c: c and tuple(round(v * 255) for v in c[:3])
UNIT = {'A': ('A', '고체'), 'B': ('B', '유체'), 'C': ('C', '천체')}
UNIT_FULL = {'A': 'A. 고체', 'B': 'B. 유체', 'C': 'C. 천체'}

# ── 원본 아이콘(리소스 PDF) ─────────────────────────────────
_IC = {}
def icon(kind):
    if kind not in _IC:
        pg = 23 if kind == 'Solving' else 22
        g = [x for x in sq8.RES[pg].get_drawings() if x['rect'].x0 > 95 * MM][0]
        _IC[kind] = (g['rect'], g['items'], g.get('width', 1.0))
    return _IC[kind]

def draw_icon(d, kind, x0, y0, h):
    rect, items, w = icon(kind)
    s = m(h) / rect.height
    tx = lambda p: f.Point(m(x0) + (p.x - rect.x0) * s, m(y0) + (p.y - rect.y0) * s)
    sh = d.p.new_shape()
    for it in items:
        if it[0] == 'l': sh.draw_line(tx(it[1]), tx(it[2]))
        elif it[0] == 'c': sh.draw_bezier(tx(it[1]), tx(it[2]), tx(it[3]), tx(it[4]))
        elif it[0] == 're': sh.draw_rect(f.Rect(tx(it[1].tl), tx(it[1].br)))
        elif it[0] == 'qu': sh.draw_quad(f.Quad(*[tx(p) for p in it[1]]))
    sh.finish(color=S(), width=w * s, lineCap=1, lineJoin=1, closePath=False)
    sh.commit()
    return rect.width / rect.height * h

def section_head(d, word, kind, x0, x1, yc, seed):
    """Solving/Linking 머리: 단어(Million Dreams) | 층 토막 핀 줄 + 회색 | 원본 아이콘. yc = 세로 가운데."""
    wx = x0 + d.text(x0, yc + 2.4, word, 'md', 14, S())
    rect = icon(kind)[0]; ih = 5.0; iw = rect.width / rect.height * ih
    draw_icon(d, kind, x1 - iw, yc - ih / 2, ih)
    a, b = wx + 3.5, x1 - iw - 4.0
    top = yc - 2.4
    bot = lambda X: top + 5.2 - 3.6 * float(sm(a, b, X))
    its = fins(seed, a, b, 1.1, top, bot, 1.0, lambda X, y: 0.95, gap=0.2, palette=PAL)
    draw_fins(d, mix_gray(its, seed + 2, every=(5, 9)), lambda X, y: 1 - 0.45 * float(sm(a + 10, b, X)), wfin=0.26)

# ── 원본에서 위치 찾기 ─────────────────────────────────────
def find_tabs(page):
    """하늘색 머리 탭(25.5 × 7.4mm)과 같은 줄 끝의 아이콘 위치."""
    dr = page.get_drawings()
    tabs = [g['rect'] for g in dr if col(g.get('fill')) == CYAN and 20 < g['rect'].width / MM < 30 and 6 < g['rect'].height / MM < 9]
    out = []
    for t in sorted(tabs, key=lambda r: r.y0):
        cy = (t.y0 + t.y1) / 2
        ics = [g['rect'] for g in dr if col(g.get('color')) == CYAN and g['rect'].x0 > t.x1 + 40 * MM
               and abs((g['rect'].y0 + g['rect'].y1) / 2 - cy) < 4 * MM and g['rect'].width < 12 * MM]
        x1 = max((r.x1 for r in ics), default=t.x0 + 107.5 * MM)
        out.append((t.x0 / MM, t.y0 / MM, x1 / MM, t.y1 / MM))
    return out

def find_note(page):
    for g in page.get_drawings():
        if col(g.get('color')) == DOTC and (g.get('width') or 0) > 1.5 and g['rect'].width / MM > 100:
            return tuple(v / MM for v in g['rect'])
    return None

def find_dots(page, box):
    x0, y0, x1, y1 = box
    out = []
    for g in page.get_drawings():
        r = g['rect']
        if col(g.get('fill')) == DOTC and r.width / MM < 1:
            cx, cy = (r.x0 + r.x1) / 2 / MM, (r.y0 + r.y1) / 2 / MM
            if x0 < cx < x1 and y0 < cy < y1: out.append((cx, cy))
    return out

def dots(d, pts, t=DOT_T):
    sh = d.p.new_shape()
    for x, y in pts: sh.draw_circle(f.Point(m(x), m(y)), m(0.25))
    sh.finish(fill=S(t), color=None); sh.commit()

def p3_head(d, x0, x1, y, label, font='pm', size=8.6, color=None, lcolor=None):
    """P3 머리: 가는 선 + 작은 핀 표식(2토막) + 라벨."""
    d.line(x0, y, x1, y, lcolor or K(.35), .25)
    fin_stack(d, x0 + 0.3, y - 5.6, [(2.6, S_, 1), (2.2, S_, .45)], w=0.5)
    d.text(x0 + 2.4, y - 2.0, label, font, size, color or S())

def number(d, side, no, lab):
    sq8.num(d, side, no, lab)

def head(d, side):
    d.dx = 0 if side == 'even' else W
    H1g(d, side)
    d.dx = 0

# ── 쪽 종류별 ──────────────────────────────────────────────
def page_problem(page, src, n):
    side = 'odd' if n % 2 else 'even'
    no, lab = prob_info(src, n)
    tabs, box = find_tabs(page), find_note(page)
    dts = find_dots(page, box) if box else []
    rects = [(-5, -5, W + 5, 30), (-5, 348, W + 5, H + 5)]
    rects += [(55, 32, 112, 59)] if side == 'odd' else [(15, 33, 100, 49.9)]
    if box: rects.append((box[0] - 2, box[1] - 2, box[2] + 2, box[3] + 2))
    for t in tabs: rects.append((t[0] - 1, t[1] - 1, t[2] + 1, t[3] + 1))
    wipe(page, rects)
    d = P(page, sq8.RES)
    head(d, side)
    label_default(d, side, UNIT[no[0]])
    number(d, side, no, lab)
    if box:
        dots(d, dts)
        p3_head(d, box[0], box[2], box[1], '풀이')
    for i, t in enumerate(tabs):
        kind = 'Linking' if (len(tabs) > 1 and i == 0) else 'Solving'
        x1 = 243 if t[0] > 100 else 128
        section_head(d, kind, kind, t[0], x1, (t[1] + t[3]) / 2, 33 + i * 7 + n)
    foot_default(d, side, n)

def page_logic(page, src, n, unit):
    rows = logic_rows(src, n)
    wipe(page, [(-5, -5, W + 5, H + 5)])
    d = P(page, sq8.RES); d.rows = rows
    head(d, 'even'); label_default(d, 'even', None)
    d.text(19, 52, 'Logic Check', 'md', 28, K())
    fin_stack(d, 19.3, 57.4, [(2.6, S_, 1), (2.2, S_, .45)], w=0.5)
    d.line(19, 63, 112, 63, K(.35), .25)
    d.text(21.4, 61.0, unit, 'pm', 8.6, S())
    d.line(128, 40, 128, 347, K(.25), .25)
    y = 47
    d.line(136, y - 7.4, 243, y - 7.4, K(.6), .3)
    k, sz = NUMFONT['key'], NUMFONT['size'] * 13.5 / 30
    for r in rows:
        d.text(136, y, r['no'], k, sz, S())
        d.text(153, y - .3, r['src'], 'pr', 8.8, K(.85))
        d.text(219.5, y - .3, '회독', 'pl', 7.8, K(.55))
        for j in range(2):
            bx = 229 + j * 5.4
            d.rect(bx, y - 3.4, bx + 3.6, y + .2, None, S(), .4, radius=.3)
        d.line(136, y + 3.7, 243, y + 3.7, K(.14), .25)
        y += 10.5
    foot_default(d, 'even', n)

def page_memo(page, n, unit):
    box = find_note(page)
    dts = [p for p in find_dots(page, box) if p[1] > 62] if box else []
    wipe(page, [(-5, -5, W + 5, H + 5)])
    d = P(page, sq8.RES)
    head(d, 'odd')
    if unit: label_default(d, 'odd', unit)
    d.text(19, 52, 'Memo', 'md', 28, K())
    p3_head(d, 19, 243, 60, 'MEMO')
    dots(d, dts)
    foot_default(d, 'odd', n)

def page_intro(page, n):
    wipe(page, [(-5, -5, 95, 75)])
    d = P(page, sq8.RES)
    head(d, 'odd')
    fin_stack(d, 19.3, 30.0, [(2.6, S_, 1), (2.2, S_, .45)], w=0.5)
    d.text(21.6, 33.6, 'Squeeze 기출 2', 'pm', 8.6, S())
    d.text(19, 48, '시작하기에', 'ps', 26, K())
    d.text(19, 60, '앞서', 'ps', 26, K())
    d.line(92, 36, 92, 340, K(.2), .25)

def page_contents(page, n):
    wipe(page, [(-5, -5, W + 5, H + 5)])
    d = P(page, sq8.RES)
    head(d, 'even')
    d.text(19, 52, 'Contents', 'md', 30, K())
    d.text(19, 150, '1', NUMFONT['key'], 120, S())
    x0, x1 = 80, 220
    p3_head(d, x0, x1, 80, '기출 EXTRACT 2', font='ps', size=13, color=K())
    y = 92
    for u, pgno in (('A. 고체', '4p'), ('B. 유체', '26p'), ('C. 천체', '56p')):
        d.text(x0 + 3, y, u, 'pr', 11, K(.8)); d.text(x1, y, pgno, 'pm', 11, K(), 'r')
        d.line(x0, y + 3.6, x1, y + 3.6, K(.14), .25); y += 10.5
    p3_head(d, x0, x1, 312, '빠른 정답', font='ps', size=13, color=K())
    d.text(x0 + 3, 324, '단원별 정답 모아 보기', 'pr', 11, K(.8)); d.text(x1, 324, '82p', 'pm', 11, K(), 'r')
    d.line(x0, 327.6, x1, 327.6, K(.14), .25)

def page_answers(page, src, n):
    # 원본 글자에서 단원별 (번호, 답) 쌍 읽기
    spans = [(s['text'].strip(), s['bbox']) for b in page.get_text('dict')['blocks'] for l in b.get('lines', [])
             for s in l['spans'] if s['text'].strip()]
    heads = sorted([(bb, t) for t, bb in spans if re.match(r'^[ABC]\.', t)], key=lambda x: x[0][1])
    nums = [(bb, t) for t, bb in spans if re.match(r'^\d+$', t) and bb[1] / MM < 300]
    ans = [(bb, t) for t, bb in spans if t and t[0] in '①②③④⑤']
    data = []
    for k, (hb, ht) in enumerate(heads):
        y0 = hb[1]; y1 = heads[k + 1][0][1] if k + 1 < len(heads) else 1e9
        pairs = []
        for nb, nt in sorted([x for x in nums if y0 < x[0][1] < y1], key=lambda x: (round(x[0][1]), x[0][0])):
            cy = (nb[1] + nb[3]) / 2
            cand = [a for a in ans if abs((a[0][1] + a[0][3]) / 2 - cy) < 2 * MM and 0 < a[0][0] - nb[2] < 12 * MM]
            pairs.append([nt, min(cand, key=lambda a: a[0][0])[1] if cand else None])
        data.append((ht, pairs))
    wipe(page, [(-5, -5, W + 5, H + 5)])
    d = P(page, sq8.RES)
    head(d, 'even')
    d.text(19, 31, '빠른 정답', 'ps', 14, K())
    y = 56
    k, sz = NUMFONT['key'], 12.5
    for unit, pairs in data:
        p3_head(d, 19, 243, y, unit.replace('\xa0', ' '))
        y += 9.5
        for i, (no, ans) in enumerate(pairs):
            c, r = i % 5, i // 5
            x = 19 + c * 45; yy = y + r * 10
            d.text(x + 2, yy, no, k, sz, S())
            d.text(x + 12, yy, ans or '', 'pr', 11, K())
            if c == 0 and i: d.line(19, yy - 6.6, 243, yy - 6.6, K(.1), .25)
        y += ((len(pairs) + 4) // 5) * 10 + 12
    foot_default(d, 'even', n)

def build_all(SRC, RESP, OUT):
    src = f.open(SRC); sq8.RES = f.open(RESP); sq9.SRC_DOC = src
    set_numfont('fs/ttf/barlow-condensed-500.ttf')
    out = f.open(); out.insert_pdf(src)
    memo_unit = {25: UNIT['A'], 55: UNIT['B'], 81: UNIT['C'], 83: None}
    logic_unit = {4: 'A. 고체', 26: 'B. 유체', 56: 'C. 천체'}
    for i in range(len(out)):
        n = i + 1; page = out[i]
        if n == 1: page_intro(page, n)
        elif n == 2: page_contents(page, n)
        elif n in (3, 84): pass
        elif n in logic_unit: page_logic(page, src, n, logic_unit[n])
        elif n in memo_unit: page_memo(page, n, memo_unit[n])
        elif n == 82: page_answers(page, src, n)
        else: page_problem(page, src, n)
        print(n, end=' ', flush=True)
    print()
    out.subset_fonts()
    out.save(OUT, garbage=4, deflate=True)
    print(OUT)

if __name__ == '__main__':
    build_all(*sys.argv[1:4])
