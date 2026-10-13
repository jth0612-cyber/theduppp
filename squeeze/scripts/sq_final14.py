# 확정안 03-01-14 D: 03-01-11(글꼴 조합 11 + Solving·Linking Space Grotesk + 좌상단 '과학의 기본량' Diphylleia)
# + Solving·Linking 줄 파형 D(간격 1.1mm, 가운데 선 정렬, 0.5mm 단차). 전체 84쪽과 예시 14쪽.
# 사용: python sq_final14.py <squeeze.pdf> <resources.pdf> <출력폴더>
import sys, os
sys.path.insert(0, '.')
import sq_wave, sq_label10, sq_full, sq_combo20

if __name__ == '__main__':
    SRC, RES, OUTD = sys.argv[1:4]
    os.makedirs(OUTD, exist_ok=True)
    sq_combo20.setup('11'); sq_label10.setup('17')
    sq_full.section_head = sq_wave.VARS['D'][1]
    base = f'{OUTD}/Squeeze_내지_03-01-14D(확정)'
    sq_full.build_all(SRC, RES, base + '_예시14쪽.pdf', only=sq_wave.KEEP)
    sq_full.build_all(SRC, RES, base + '_전체.pdf')
    print('ok')
