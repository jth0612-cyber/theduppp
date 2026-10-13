# Squeeze 03-01-09: 03-01-08(Solving 2안) + 번호 글꼴 굵기 약 2배 (Barlow Condensed Light 300 → 500 / 600)
import sys, os
sys.path.insert(0, '.')
import sq8, sq9
from sq8 import Base, set_numfont, build, f
if __name__ == '__main__':
    SRC, RESP, OUTD = sys.argv[1:4]
    os.makedirs(OUTD, exist_ok=True)
    sq9.SRC_DOC = f.open(SRC); sq8.RES = f.open(RESP)
    for w, nm, ratio in ((500, 'Medium', '1.8배'), (600, 'SemiBold', '2.2배')):
        set_numfont(f'fs/ttf/barlow-condensed-{w}.ttf')
        class C(Base):
            name = f'03-01-09(번호 Barlow Condensed {nm} {w}·획 {ratio}·Solving 2안)'
        C.note = lambda s_, d: sq9.note(d)
        C.solving = lambda s_, d: sq9.S2(d)
        print(build(C, sq9.SRC_DOC, sq8.RES, f'{OUTD}/Squeeze_내지_{C.name}.pdf'), sq8.NUMFONT['size'], flush=True)
