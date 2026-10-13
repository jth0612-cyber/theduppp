# 03-01-10 기준 (1차 01~10 → 2차: 04·06 남기고 11~18로 교체), 짝수쪽 좌상단 '기출 EXTRACT 2' → '과학의 기본량'(영문 없음). 이 글자의 글꼴만 10안.
# 사용: python sq_label10.py <squeeze.pdf> <resources.pdf> <출력폴더> [01 02 ...] [--full]
import sys, os
sys.path.insert(0, '.')
import sq_final11, sq_lib, sq5, sq_full, sq_combo, sq_combo20
from sq_lib import f, K

PT, FS = sq_combo.PT, sq_combo.FS
TEXT = '과학의 기본량'
LABELS = {   # 코드: (이름, 글꼴, 크기pt, 자간)
    '04': ('Noto Serif KR SemiBold', FS.format('noto-serif-kr-600'), 14, 0),
    '06': ('고운바탕 Bold', FS.format('gowun-batang-700'), 14, 20),
    # 2차(04·06 남기고 나머지 교체)
    '11': ('Noto Serif KR Medium', FS.format('noto-serif-kr-500'), 14, 0),
    '12': ('Noto Serif KR Bold', FS.format('noto-serif-kr-700'), 14, 0),
    '13': ('고운바탕 Regular 자간', FS.format('gowun-batang-400'), 14, 40),
    '14': ('나눔명조 Bold', FS.format('nanum-myeongjo-700'), 14, 0),
    '15': ('나눔명조 Regular 자간', FS.format('nanum-myeongjo-400'), 14, 40),
    '16': ('함렛 Medium', FS.format('hahmlet-500'), 14, 0),
    '17': ('Diphylleia', FS.format('diphylleia-400'), 14.5, 10),
    '18': ('Grandiflora One', FS.format('grandiflora-one-400'), 14.5, 10),
}
CUR = {}
_old = sq5.label_default
def label(d, side, unit):
    if side == 'even':
        d.text(19, 31, TEXT, 'lb', CUR['size'], K(), track=CUR['track'])
    else:
        _old(d, side, unit)
sq5.label_default = label; sq_full.label_default = label

def setup(code):
    name, path, size, track = LABELS[code]
    sq_lib.FONTS['lb'] = path; sq_lib.FO['lb'] = f.Font(fontfile=path)
    miss = [c for c in TEXT if c.strip() and not sq_lib.FO['lb'].has_glyph(ord(c))]
    if miss: print('  ! 글자 없음', code, miss)
    CUR.update(size=size, track=track)
    return name

if __name__ == '__main__':
    SRC, RES, OUTD = sys.argv[1:4]
    args = sys.argv[4:]; full = '--full' in args
    which = [a for a in args if a != '--full'] or list(LABELS)
    os.makedirs(OUTD, exist_ok=True)
    sq_combo20.setup('11')
    for code in which:
        name = setup(code)
        base = f'{OUTD}/Squeeze_내지_03-01-11_좌상단{code}({name})'
        sq_full.build_all(SRC, RES, base + '_예시14쪽.pdf', only=[1, 2, 3, 4, 5, 6, 25, 26, 55, 56, 81, 82, 83, 84])
        if full: sq_full.build_all(SRC, RES, base + '_전체.pdf')
        print('=>', code, name, flush=True)
