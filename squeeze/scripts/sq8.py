# Squeeze 03-01-06: 03-01-05 + Solving 아이콘 복원(균형 조정) + 문항 번호 글꼴 견본 10종
# 사용: python sq8.py <squeeze.pdf> <resources.pdf> <출력폴더> [base | fonts]
import sys, os, math
import numpy as np
sys.path.insert(0, '.')
import sq_lib
from fontTools.ttLib import TTFont
from sq7 import (fins, draw_fins, head_bottom_rand_half, PITCH, MOD, GAP, PAL, Noise, SW, sm, H1h, P3, fin_row, fin_stack, solving_word, label_default, foot_default, build, f, m, R, W,
                 S, K, S_, K_, tint, fadeX)

RES = None

# ── Solving 아이콘: 리소스 24쪽의 원본 벡터 경로를 그대로 옮겨 별색으로 그림 ──────────
_ICON = None
def icon_paths():
    global _ICON
    if _ICON is None:
        g = [x for x in RES[23].get_drawings() if x['rect'].x0 > 99 * 72 / 25.4][0]
        _ICON = (g['rect'], g['items'], g.get('width', 1.0))
    return _ICON

def draw_icon(d, x0, y0, h):
    """원본 아이콘(7.4 × 6.28mm)을 높이 h(mm)로 (x0, y0)에 그림. 선 굵기도 같은 비율."""
    rect, items, w = icon_paths()
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

def solving_icon(d):
    """Solving | 핀 줄(점점 짧아짐) | 아이콘. 아이콘 높이 = 'Solving' 글자 높이와 같은 5.4mm, 세로 가운데 정렬."""
    x = solving_word(d)
    ih = 5.0
    iw = icon_paths()[0].width / icon_paths()[0].height * ih
    ix = 243 - iw
    draw_icon(d, ix, 276.0 - ih / 2, ih)
    fin_row(d, x + 3.5, ix - 4.2, 273.6, 5.0, 1.4, 31, fade=0.45)

# ── 문항 번호 글꼴 ─────────────────────────────────────────
MD_CAP = None
def cap_height(path):
    t = TTFont(path); upm = t['head'].unitsPerEm
    gs = t.getGlyphSet(); from fontTools.pens.boundsPen import BoundsPen
    bp = BoundsPen(gs); gs[t.getBestCmap()[ord('A')]].draw(bp)
    return (bp.bounds[3] - bp.bounds[1]) / upm

NUMFONT = {'key': 'md', 'size': 30.0}
def set_numfont(path):
    """번호 글꼴을 바꾸고, Million Dreams 30pt와 대문자 높이가 같도록 크기를 맞춘다."""
    global MD_CAP
    if MD_CAP is None: MD_CAP = cap_height('md/Million Dreams.otf')
    if path is None:
        NUMFONT.update(key='md', size=30.0); return
    sq_lib.FONTS['nf'] = path; sq_lib.FO['nf'] = f.Font(fontfile=path)
    NUMFONT.update(key='nf', size=round(30.0 * MD_CAP / cap_height(path), 2))

def num(d, side, no, lab):
    k, sz = NUMFONT['key'], NUMFONT['size']
    if side == 'odd':
        d.text(108, 47, no, k, sz, S(), 'r'); d.text(108, 53.6, lab, 'pr', 8.2, K(.68), 'r')
    else:
        wd = d.text(19, 47, no, k, sz, S()); d.text(19 + wd + 4, 46.5, lab, 'pr', 8.2, K(.68))

def logic(d):
    d.text(19, 52, 'Logic Check', 'md', 28, K())
    d.line(19, 63, 112, 63, K(.35), .25)
    fin_stack(d, 19.3, 57.4, [(2.6, S_, 1), (2.2, S_, .45)], w=0.5)
    d.text(21.4, 61.0, 'A. 고체', 'pm', 8.6, S())
    d.line(128, 40, 128, 347, K(.25), .25)
    y = 47
    d.line(136, y - 7.4, 243, y - 7.4, K(.6), .3)
    k, sz = NUMFONT['key'], NUMFONT['size'] * 13.5 / 30
    for r in d.rows:
        d.text(136, y, r['no'], k, sz, S())
        d.text(153, y - .3, r['src'], 'pr', 8.8, K(.85))
        d.text(219.5, y - .3, '회독', 'pl', 7.8, K(.55))
        for j in range(2):
            bx = 229 + j * 5.4
            d.rect(bx, y - 3.4, bx + 3.6, y + .2, None, S(), .4, radius=.3)
        d.line(136, y + 3.7, 243, y + 3.7, K(.14), .25)
        y += 10.5

# ── 상단: 회색(먹) 핀을 적재적소에 ───────────────────────
_GN = Noise(707, 70, dirs=0.4)
def head_items_gray():
    it = fins(5, 1.1, SW, PITCH, 0, head_bottom_rand_half, MOD, lambda X, y: 0.93, gap=GAP, palette=PAL)
    bottom = {}
    for i, (x, ya, yb, ink, t) in enumerate(it):
        if yb > bottom.get(x, (-1, 0))[0]: bottom[x] = (yb, i)
    rng = np.random.default_rng(17)
    out, last_gray_x = [], -99
    for i, (x, ya, yb, ink, t) in enumerate(it):
        is_bottom = bottom[x][1] == i
        deep = float(sm(10, 15, yb))                       # 윤곽이 깊게 내려간 곳
        cluster = float(sm(0.05, 0.5, _GN(x, 0)))          # 회색이 모여 나오는 구간
        p_ = (0.55 * deep * is_bottom + 0.22 * cluster * (ya > 3)) * (0.35 + 0.65 * float(fadeX(x)))
        if x - last_gray_x > PITCH * 1.5 and rng.uniform() < p_:
            out.append((x, ya, yb, 'K', 0.45 if (is_bottom or rng.uniform() < .5) else 0.25)); last_gray_x = x
        else:
            out.append((x, ya, yb, ink, t))
    return out

def H1g(d, side):
    draw_fins(d, head_items_gray(), lambda x, y: 0.55 + 0.45 * float(fadeX(x)))

class Base:
    head = lambda s_, d, side: H1g(d, side)
    label = lambda s_, d, side, unit: label_default(d, side, unit)
    num = lambda s_, d, side, no, lab: num(d, side, no, lab)
    note = lambda s_, d: P3(d)
    solving = lambda s_, d: solving_icon(d)
    foot = lambda s_, d, side, no: foot_default(d, side, no)
    logic = lambda s_, d: logic(d)

FONTS10 = [
    ('01', 'Big Shoulders Display Medium', 'fs/ttf/big-shoulders-display-500.ttf', '시카고 건축에서 나온 좁은 고딕. 세로 핀과 같은 리듬'),
    ('02', 'Barlow Condensed Light', 'fs/ttf/barlow-condensed-300.ttf', '좁고 가는 고딕. 조용하고 단정함'),
    ('03', 'Oswald Light', 'fs/ttf/oswald-300.ttf', '좁은 고딕. 세로로 긴 숫자가 핀과 어울림'),
    ('04', 'Antonio Light', 'fs/ttf/antonio-300.ttf', '아주 좁은 고딕. 기둥처럼 곧은 획'),
    ('05', 'Inter Tight Light', 'fs/ttf/inter-tight-300.ttf', '중립적인 고딕. Pretendard와 가장 잘 섞임'),
    ('06', 'Space Grotesk Regular', 'fs/ttf/space-grotesk-400.ttf', '기하학 고딕. 숫자 모양이 개성 있음'),
    ('07', 'Fraunces Regular', 'fs/ttf/fraunces-400.ttf', '둥글고 말랑한 세리프. Squeeze 느낌'),
    ('08', 'Playfair Display Medium', 'fs/ttf/playfair-display-500.ttf', '획 대비가 큰 세리프. Million Dreams와 같은 계열'),
    ('09', 'Cormorant Garamond SemiBold', 'fs/ttf/cormorant-garamond-600.ttf', '가늘고 우아한 세리프. 고급스러움'),
    ('10', 'Instrument Serif', 'fs/ttf/instrument-serif-400.ttf', '좁은 세리프. 편집 디자인 느낌'),
]

if __name__ == '__main__':
    SRC, RESP, OUTD = sys.argv[1:4]
    mode = sys.argv[4] if len(sys.argv) > 4 else 'base'
    os.makedirs(OUTD, exist_ok=True)
    src = f.open(SRC); RES = f.open(RESP)
    if mode == 'base':
        set_numfont(None)
        Base.name = '03-01-07(Solving 아이콘·상단 회색 핀)'
        print(build(Base, src, RES, f'{OUTD}/Squeeze_내지_{Base.name}.pdf'))
    else:
        for code, name, path, _ in FONTS10:
            set_numfont(path)
            Base.name = f'번호글꼴_{code}_{name}'
            print(build(Base, src, RES, f'{OUTD}/{Base.name}.pdf'), NUMFONT['size'], flush=True)
