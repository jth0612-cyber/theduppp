# 03-01-13: 03-01-11 그대로 + Solving·Linking 옆 핀 줄만 3안. 선 굵기 0.26mm 고정, 간격(폭)과 위아래 단차만 다르게.
#  A 넓은 간격·낮은 단차   B 중간 간격·큰 단차   C 좁은 간격·위아래 양쪽 단차
# 사용: python sq_sol3.py <squeeze.pdf> <resources.pdf> <출력폴더> [A B C]
import sys, os
import numpy as np
sys.path.insert(0, '.')
import sq_label10, sq_full, sq_combo20
from sq_full import icon, draw_icon, SOLFONT
from sq6 import draw_fins, sm, Noise
from sq9 import mix_gray
from sq7 import PAL
from sq_lib import S

KEEP = [1, 2, 3, 4, 5, 6, 25, 26, 55, 56, 81, 82, 83, 84]
WFIN = 0.26

def frame(d, word, kind, x0, x1, yc):
    wx = x0 + d.text(x0, yc + 2.4, word, sq_full.SOLFONT, 14, S())
    rect = icon(kind)[0]; ih = 5.0; iw = rect.width / rect.height * ih
    draw_icon(d, kind, x1 - iw, yc - ih / 2, ih)
    return wx + 3.5, x1 - iw - 4.0

def column(r, x, ya, yb, module, gap=0.2, Ls=(1, 1, 2, 2, 3), fill=0.95):
    """한 기둥을 층 토막으로 나눔(ya→yb)."""
    inks = [(p[0], p[1]) for p in PAL]; w = np.array([p[2] for p in PAL], float); w /= w.sum()
    out, y = [], ya
    while y < yb - 0.05:
        L = min(int(r.choice(Ls)) * module, yb - y)
        if r.uniform() < fill:
            ink, t = inks[r.choice(len(inks), p=w)]
            out.append((x, y + gap / 2, y + L - gap / 2, ink, t))
        y += L
    return out

def fade(a, b): return lambda X, y: 1 - 0.45 * float(sm(a + 10, b, X))

def solA(d, word, kind, x0, x1, yc, seed):
    """A: 간격 1.8mm, 위 기준선 고정, 길이 3.0~4.0mm에서 한 토막(1.0mm)만 오르내림 → 낮고 고른 띠."""
    a, b = frame(d, word, kind, x0, x1, yc); r = np.random.default_rng(seed); its = []
    top = yc - 2.4; x = a
    while x <= b:
        L = 3.0 + 1.0 * int(r.integers(0, 2))
        its += column(r, x, top, top + L, 1.0, Ls=(2, 3, 3, 4), fill=1.0); x += 1.8
    draw_fins(d, mix_gray(its, seed + 2, every=(4, 7)), fade(a, b), wfin=WFIN)

def solB(d, word, kind, x0, x1, yc, seed):
    """B: 간격 1.4mm, 위 기준선 고정, 아래 끝이 1.2~6.0mm 사이를 크게 오르내림(무작위 윤곽, 1.2mm 단위 계단)."""
    a, b = frame(d, word, kind, x0, x1, yc); r = np.random.default_rng(seed); its = []
    n1, n2 = Noise(seed + 50, 14, dirs=0.3), Noise(seed + 51, 6, dirs=0.5)
    top = yc - 2.4; x = a
    while x <= b:
        v = 0.7 * float(n1(x, 0)) + 0.3 * float(n2(x, 0))
        steps = 1 + int(round(4 * float(sm(-0.7, 0.7, v))))
        its += column(r, x, top, top + steps * 1.2, 1.2, Ls=(1, 2, 2, 3)); x += 1.4
    draw_fins(d, mix_gray(its, seed + 2, every=(5, 8)), fade(a, b), wfin=WFIN)

def solC(d, word, kind, x0, x1, yc, seed):
    """C: 간격 0.8mm, 글자 가운데 높이 기준으로 위아래 양쪽에 단차(위·아래 따로 1.0mm 단위), 아이콘 쪽으로 낮아짐."""
    a, b = frame(d, word, kind, x0, x1, yc); r = np.random.default_rng(seed); its = []
    nu, nd = Noise(seed + 60, 14, dirs=0.4), Noise(seed + 61, 11, dirs=0.4)
    x = a
    while x <= b:
        k = 1 - 0.55 * float(sm(a, b, x))
        up = 1.0 * (1 + int(round(2 * k * float(sm(-0.7, 0.7, nu(x, 0))))))
        dn = 1.0 * (1 + int(round(2 * k * float(sm(-0.7, 0.7, nd(x, 0))))))
        its += column(r, x, yc - 0.3 - up, yc - 0.3 + dn, 1.0, gap=0.18, Ls=(2, 3, 4, 6)); x += 0.8
    draw_fins(d, mix_gray(its, seed + 2, every=(6, 10)), fade(a, b), wfin=WFIN)

VARS = {'A': ('넓은 간격·낮은 단차', solA), 'B': ('중간 간격·큰 단차', solB), 'C': ('좁은 간격·위아래 단차', solC)}

if __name__ == '__main__':
    SRC, RES, OUTD = sys.argv[1:4]
    which = sys.argv[4:] or list(VARS)
    os.makedirs(OUTD, exist_ok=True)
    sq_combo20.setup('11'); sq_label10.setup('17')
    for code in which:
        name, fn = VARS[code]
        sq_full.section_head = fn
        out = f'{OUTD}/Squeeze_내지_03-01-13_Solving{code}({name})_예시14쪽.pdf'
        sq_full.build_all(SRC, RES, out, only=KEEP)
        print('=>', out, flush=True)
