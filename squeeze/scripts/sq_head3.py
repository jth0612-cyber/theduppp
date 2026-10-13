# 03-01-12: 03-01-11(좌상단 17 Diphylleia) 기준, 상단바만 3안으로 눈에 띄게 변형.
#  A 촘촘·잔잔  B 성글고 굵게·큰 물결  C 칸 묶음·계단
# 사용: python sq_head3.py <squeeze.pdf> <resources.pdf> <출력폴더> [A B C]
import sys, os
import numpy as np
sys.path.insert(0, '.')
import sq_label10, sq_full, sq_combo20
from sq6 import draw_fins, fadeX, sm, Noise, SW
from tex import fins
from sq_lib import W

KEEP = [1, 2, 3, 4, 5, 6, 25, 26, 55, 56, 81, 82, 83, 84]

def add_gray(it, seed, p_bottom, p_mid, every=1.5, pitch=2.2, tints=(.45, .25)):
    """기둥 아래 끝(깊은 곳)과 중간 토막 일부를 먹(K)으로. 이웃 기둥끼리는 연달아 오지 않게."""
    bottom = {}
    for i, (x, ya, yb, ink, t) in enumerate(it):
        if yb > bottom.get(x, (-1, 0))[0]: bottom[x] = (yb, i)
    r = np.random.default_rng(seed); out, last = [], -99
    for i, (x, ya, yb, ink, t) in enumerate(it):
        p = p_bottom(yb) if bottom[x][1] == i else p_mid
        p *= 0.35 + 0.65 * float(fadeX(x))
        if x - last > pitch * every and r.uniform() < p:
            out.append((x, ya, yb, 'K', tints[0] if r.uniform() < .6 else tints[1])); last = x
        else: out.append((x, ya, yb, ink, t))
    return out

# ── A: 촘촘·잔잔 ─ 간격 1.4mm·굵기 0.26mm·토막 1.2mm, 낮고 잔물결 많은 윤곽, 연한 농도 위주, 아래 끝은 연해지며 사라짐
_A1, _A2, _A3 = Noise(411, 90, dirs=0.3), Noise(412, 24, dirs=0.5), Noise(413, 7, dirs=0.6)
def botA(X):
    v = 0.45 * float(_A1(X, 0)) + 0.35 * float(_A2(X, 0)) + 0.3 * float(_A3(X, 0))
    return 6.0 + 9.0 * float(sm(-0.8, 0.8, v))
PAL_A = [('S', 1.0, 4), ('S', .7, 4), ('S', .45, 3), ('S', .25, 2)]
def itemsA():
    it = fins(21, 0.7, SW, 1.4, 0, botA, 1.2, lambda X, y: 0.9, gap=0.22, palette=PAL_A)
    return add_gray(it, 23, lambda yb: 0.25 * float(sm(8, 12, yb)), 0.04, every=2.5, pitch=1.4, tints=(.35, .2))
def headA(d, side):
    draw_fins(d, itemsA(), lambda x, y: (0.55 + 0.45 * float(fadeX(x))) * (1 - 0.4 * float(sm(5, 15, y))), wfin=0.26)

# ── B: 성글고 굵게·큰 물결 ─ 간격 3.0mm·굵기 0.6mm·토막 2.4mm, 펼침면을 가로지르는 큰 물결 2번, 진한 별색과 회색 무리,
#       깊은 곳 아래에 떨어진 작은 토막(물방울)
_B1, _B2 = Noise(521, 190, dirs=0.2), Noise(522, 40, dirs=0.4)
def botB(X):
    v = 0.75 * float(_B1(X, 0)) + 0.3 * float(_B2(X, 0))
    return 4.5 + 16.0 * float(sm(-0.7, 0.7, v))
PAL_B = [('S', 1.0, 5), ('S', .7, 2), ('S', .45, 3), ('S', .25, 1)]
_BG = Noise(523, 45, dirs=0.4)
def itemsB():
    it = fins(31, 1.5, SW, 3.0, 0, botB, 2.4, lambda X, y: 0.95, gap=0.35, palette=PAL_B)
    out, r, low = [], np.random.default_rng(37), {}
    for x, ya, yb, ink, t in it:
        if yb > low.get(x, -1): low[x] = yb
    for x, ya, yb, ink, t in it:
        if float(_BG(x, 0)) > 0.25 and r.uniform() < 0.45: ink, t = 'K', (.45 if r.uniform() < .6 else .25)
        out.append((x, ya, yb, ink, t))
    for x, yb in low.items():                    # 물방울: 깊은 기둥 아래 떨어진 짧은 토막
        if yb > 13 and r.uniform() < 0.35:
            out.append((x, yb + 1.4, yb + 2.4, 'S', .45))
    return out
def headB(d, side):
    draw_fins(d, itemsB(), lambda x, y: 0.5 + 0.5 * float(fadeX(x)), wfin=0.6)

# ── C: 칸 묶음·계단 ─ 기둥 5개(간격 2.0mm)를 한 칸으로 묶고 칸 사이 4mm 틈, 칸마다 높이가 한 단씩 달라지는 계단 윤곽,
#       칸마다 한 농도(가끔 회색 칸), 아래 끝은 가는 가로 띠로 마감
_C1 = Noise(631, 120, dirs=0.3)
PAL_C = [('S', 1.0), ('S', .7), ('S', .45), ('S', .25)]
def itemsC():
    r = np.random.default_rng(41); out = []; ends = []
    x = 1.0; k = 0; MODC = 1.6
    while x < SW:
        lvl = 5 + int(round(4 * float(sm(-0.7, 0.7, _C1(x + 4, 0))))) + int(r.integers(-1, 2))
        bot = max(lvl, 3) * MODC
        gray = r.uniform() < 0.16 and k > 0
        base = ('K', .45) if gray else PAL_C[int(r.choice(4, p=[.35, .3, .2, .15]))]
        for j in range(5):
            xx = x + j * 2.0
            if xx > SW: break
            y = 0.0
            while y < bot - 0.01:
                L = min(int(r.choice([1, 2, 2, 3, 4])) * MODC, bot - y)
                ink, t = base if r.uniform() < 0.8 else (base[0], max(base[1] - .25, .2))
                out.append((xx, y + 0.15, y + L - 0.15, ink, t)); y += L
        ends.append((x - 0.3, x + 8.3, bot + 0.9, base))
        x += 5 * 2.0 + 2.0; k += 1
    return out, ends
def headC(d, side):
    it, ends = itemsC()
    tf = lambda x, y: 0.55 + 0.45 * float(fadeX(x))
    draw_fins(d, it, tf, wfin=0.32)
    from sq_lib import R
    from sq6 import tint, S_, K_
    sh = d.p.new_shape()
    for x0, x1, y, (ink, t) in ends:
        if x1 - d.dx < -1 or x0 - d.dx > W + 1: continue
        a = t * float(tf((x0 + x1) / 2, y))
        sh.draw_rect(R(x0 - d.dx, y, x1 - d.dx, y + 0.3)); sh.finish(fill=tint(S_ if ink == 'S' else K_, a), color=None)
    sh.commit()

VARS = {'A': ('촘촘·잔잔', headA), 'B': ('성글고 굵게·큰 물결', headB), 'C': ('칸 묶음·계단', headC)}

if __name__ == '__main__':
    SRC, RES, OUTD = sys.argv[1:4]
    which = sys.argv[4:] or list(VARS)
    os.makedirs(OUTD, exist_ok=True)
    sq_combo20.setup('11'); sq_label10.setup('17')
    for code in which:
        name, fn = VARS[code]
        def head(d, side, fn=fn):
            d.dx = 0 if side == 'even' else W
            fn(d, side); d.dx = 0
        sq_full.head = head
        out = f'{OUTD}/Squeeze_내지_03-01-12_상단{code}({name})_예시14쪽.pdf'
        sq_full.build_all(SRC, RES, out, only=KEEP)
        print('=>', out, flush=True)
