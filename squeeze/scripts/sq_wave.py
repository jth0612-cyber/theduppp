# 03-01-14: Solving·Linking 줄을 음악 재생 파형처럼. 글자(대문자 높이 가운데)·아이콘·핀 줄을 하나의 가운데 선에 세로 정렬,
# 가운데 선은 고정하고 핀이 위아래로 똑같이 뻗으며 단차(0.5mm 단위). 선 굵기 0.26mm 그대로.
#  D 간격 1.1mm(현재와 같음)   E 간격 0.8mm(촘촘)
# 사용: python sq_wave.py <squeeze.pdf> <resources.pdf> <출력폴더> [D E]
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
WFIN, STEP = 0.26, 0.5

def wave(pitch, hmax, seed_off):
    def head(d, word, kind, x0, x1, yc, seed):
        size = 14 * sq_combo.SCALE.get(sq_full.SOLFONT, 1)
        base = yc + 2.4                                              # 글자 기준선(원래 자리)
        mid = base - cap_height(sq_lib.FONTS[sq_full.SOLFONT]) * size * 25.4 / 72 / 2   # 대문자 높이 가운데 = 가운데 선
        wx = x0 + d.text(x0, base, word, sq_full.SOLFONT, 14, S())
        rect = icon(kind)[0]; ih = 5.0; iw = rect.width / rect.height * ih
        draw_icon(d, kind, x1 - iw, mid - ih / 2, ih)                # 아이콘도 같은 가운데 선에
        a, b = wx + 3.5, x1 - iw - 4.0
        r = np.random.default_rng(seed + seed_off)
        n1, n2 = Noise(seed + 70 + seed_off, 16, dirs=0.3), Noise(seed + 71 + seed_off, 5, dirs=0.5)
        inks = [(p[0], p[1]) for p in PAL]; w = np.array([p[2] for p in PAL], float); w /= w.sum()
        its = []; x = a
        while x <= b:
            env = 1 - 0.6 * float(sm(a, b, x))                       # 아이콘 쪽으로 잦아듦
            v = 0.6 * float(sm(-0.7, 0.7, n1(x, 0))) + 0.25 * float(sm(-0.7, 0.7, n2(x, 0))) + 0.15 * r.uniform()
            h = max(STEP, STEP * round(hmax * env * v / STEP))       # 반 높이, 0.5mm 단차
            ink, t = inks[r.choice(len(inks), p=w)]
            its.append((x, mid - h, mid + h, ink, t)); x += pitch
        draw_fins(d, mix_gray(its, seed + 2, every=(5, 9)), lambda X, y: 1 - 0.4 * float(sm(a + 10, b, X)), wfin=WFIN)
    return head

VARS = {'D': ('파형·간격 1.1mm', wave(1.1, 3.0, 0)), 'E': ('파형·간격 0.8mm', wave(0.8, 3.0, 5))}

if __name__ == '__main__':
    SRC, RES, OUTD = sys.argv[1:4]
    which = sys.argv[4:] or list(VARS)
    os.makedirs(OUTD, exist_ok=True)
    sq_combo20.setup('11'); sq_label10.setup('17')
    for code in which:
        name, fn = VARS[code]
        sq_full.section_head = fn
        out = f'{OUTD}/Squeeze_내지_03-01-14_Solving{code}({name})_예시14쪽.pdf'
        sq_full.build_all(SRC, RES, out, only=KEEP)
        print('=>', out, flush=True)
