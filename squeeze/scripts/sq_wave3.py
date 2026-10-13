# 03-01-15: 파형 D(간격 1.1mm, 가운데 선 정렬, 0.5mm 단차, 굵기 0.26mm)를 바탕으로 파형 모양만 3가지.
#  F 말소리: 둥근 소리 뭉치(6~10칸)와 그 사이 조용한 쉼(3~5칸)
#  G 박자: 일정한 간격으로 솟는 박(拍), 박 뒤로 잦아듦
#  H 한 번의 큰 숨: 글자 쪽에서 작게 시작해 가운데쯤 크게 솟았다가 아이콘 쪽으로 잦아듦
# 사용: python sq_wave3.py <squeeze.pdf> <resources.pdf> <출력폴더> [F G H]
import sys, os
import numpy as np
sys.path.insert(0, '.')
import sq_label10, sq_full, sq_combo20, sq_combo, sq_lib
from sq_full import icon, draw_icon
from sq6 import draw_fins, sm, Noise
from sq9 import mix_gray
from sq7 import PAL
from sq8 import cap_height
from sq_lib import S

KEEP = [1, 2, 3, 4, 5, 6, 25, 26, 55, 56, 81, 82, 83, 84]
PITCH, WFIN, STEP, HMAX = 1.1, 0.26, 0.5, 3.0

def make(shape):
    """shape(t, x, r, seed) → 0~1 크기. t = 줄 안의 위치(0 글자 쪽 ~ 1 아이콘 쪽)."""
    def head(d, word, kind, x0, x1, yc, seed):
        size = 14 * sq_combo.SCALE.get(sq_full.SOLFONT, 1)
        base = yc + 2.4
        mid = base - cap_height(sq_lib.FONTS[sq_full.SOLFONT]) * size * 25.4 / 72 / 2
        wx = x0 + d.text(x0, base, word, sq_full.SOLFONT, 14, S())
        rect = icon(kind)[0]; ih = 5.0; iw = rect.width / rect.height * ih
        draw_icon(d, kind, x1 - iw, mid - ih / 2, ih)
        a, b = wx + 3.5, x1 - iw - 4.0
        r = np.random.default_rng(seed)
        inks = [(p[0], p[1]) for p in PAL]; w = np.array([p[2] for p in PAL], float); w /= w.sum()
        its = []; x = a; i = 0
        while x <= b:
            v = float(np.clip(shape((x - a) / (b - a), x, i, r, seed), 0, 1))
            h = max(STEP, STEP * round(HMAX * v / STEP))
            ink, t = inks[r.choice(len(inks), p=w)]
            its.append((x, mid - h, mid + h, ink, t)); x += PITCH; i += 1
        draw_fins(d, mix_gray(its, seed + 2, every=(5, 9)), lambda X, y: 1 - 0.3 * float(sm(a + 10, b, X)), wfin=WFIN)
    return head

_PLAN = {}
def speech(t, x, i, r, seed):
    """F: 소리 뭉치(6~10칸, 가운데가 둥글게 큼) – 쉼(3~5칸, 가장 작은 높이)이 번갈아."""
    if seed not in _PLAN:
        q = np.random.default_rng(seed + 90); plan = []
        while len(plan) < 400:
            n = int(q.integers(6, 11)); amp = q.uniform(0.6, 1.0)
            plan += [amp * np.sin(np.pi * (k + 0.5) / n) ** 0.8 for k in range(n)]
            plan += [0.0] * int(q.integers(3, 6))
        _PLAN[seed] = plan
    v = _PLAN[seed][i]
    return 0.12 if v == 0 else 0.12 + v * (0.7 + 0.3 * r.uniform()) * (1 - 0.3 * t)

def beat(t, x, i, r, seed):
    """G: 7칸(7.7mm)마다 박이 솟고, 박 뒤로 지수적으로 잦아듦. 박 크기는 조금씩 다르게."""
    k = i % 7
    amp = 0.75 + 0.25 * np.sin(i // 7 * 1.7 + seed)
    return 0.12 + amp * np.exp(-k / 1.6) * (0.85 + 0.15 * r.uniform())

def swell(t, x, i, r, seed):
    """H: 한 번 크게 솟는 숨(40% 지점이 정점) + 잔떨림."""
    env = np.exp(-((t - 0.4) / 0.24) ** 2)
    return 0.12 + 0.88 * env * (0.6 + 0.4 * r.uniform())

VARS = {'F': ('말소리', make(speech)), 'G': ('박자', make(beat)), 'H': ('한 번의 큰 숨', make(swell))}

if __name__ == '__main__':
    SRC, RES, OUTD = sys.argv[1:4]
    which = sys.argv[4:] or list(VARS)
    os.makedirs(OUTD, exist_ok=True)
    sq_combo20.setup('11'); sq_label10.setup('17')
    for code in which:
        name, fn = VARS[code]
        sq_full.section_head = fn
        out = f'{OUTD}/Squeeze_내지_03-01-15_Solving{code}({name})_예시14쪽.pdf'
        sq_full.build_all(SRC, RES, out, only=KEEP)
        print('=>', out, flush=True)
