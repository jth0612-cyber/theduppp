# 확정안: 글꼴 조합 11(Pretendard SemiBold + Pretendard + Cinzel) + Solving·Linking 글자는 조합 07의 Space Grotesk Medium.
# 사용: python sq_final11.py <squeeze.pdf> <resources.pdf> <출력폴더> [full]
import sys, os
sys.path.insert(0, '.')
import sq_lib, sq_full, sq_combo, sq_combo20
from sq_lib import f

SOL = sq_combo.FS.format('space-grotesk-500')
sq_lib.FONTS['sol'] = SOL; sq_lib.FO['sol'] = f.Font(fontfile=SOL)
sq_combo.SCALE['sol'] = sq_combo.COMBOS['07'][2]      # 07과 같은 크기(0.95)

if __name__ == '__main__':
    SRC, RES, OUTD = sys.argv[1:4]
    os.makedirs(OUTD, exist_ok=True)
    sq_combo20.setup('11')
    name = '03-01-10(Pretendard + Cinzel, Solving Space Grotesk)'
    sq_full.build_all(SRC, RES, f'{OUTD}/Squeeze_내지_{name}_예시14쪽.pdf', only=[1, 2, 3, 4, 5, 6, 25, 26, 55, 56, 81, 82, 83, 84])
    if 'full' in sys.argv[4:]:
        sq_full.build_all(SRC, RES, f'{OUTD}/Squeeze_내지_{name}_전체.pdf')
    print('ok', sq_combo.SCALE)
