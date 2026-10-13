# 03-01-09 예시본(14쪽)을 글꼴 조합만 바꿔 여러 벌 만든다. 번호 글꼴(Barlow Condensed Medium)과
# 'Squeeze' 로고 글자(Million Dreams)는 고정.
# 역할 → 글꼴 키: ps 한글 제목 / pm 한글 중간 / pr 한글 본문형 / pl 한글 가는 / md 영문 제목
# 사용: python sq_combo.py <squeeze.pdf> <resources.pdf> <출력폴더> [00 01 ...]
import sys, os
sys.path.insert(0, '.')
import sq_lib, sq5, sq_full
from sq_lib import f, K

PT = 'npm/package/dist/public/static/alternative/Pretendard-{}.ttf'
FS = 'fs/ttf/{}.ttf'
COMBOS = {
    '00': ('현재 Pretendard + Million Dreams', dict(ps=PT.format('SemiBold'), pm=PT.format('Medium'), pr=PT.format('Regular'), pl=PT.format('Light'), md='md/Million Dreams.otf'), 1.0),
    '01': ('함렛 + Pretendard + Cormorant Garamond', dict(ps=FS.format('hahmlet-600'), pm=PT.format('Medium'), pr=PT.format('Regular'), pl=PT.format('Light'), md=FS.format('cormorant-garamond-600')), 1.12),
    '02': ('Gothic A1 + Barlow Condensed', dict(ps=FS.format('gothic-a1-600'), pm=FS.format('gothic-a1-500'), pr=FS.format('gothic-a1-400'), pl=FS.format('gothic-a1-300'), md=FS.format('barlow-condensed-600')), 1.08),
    '03': ('고운돋움 + Fraunces', dict(ps=FS.format('gowun-dodum-400'), pm=FS.format('gowun-dodum-400'), pr=FS.format('gowun-dodum-400'), pl=FS.format('gowun-dodum-400'), md=FS.format('fraunces-600')), 0.98),
    '04': ('Noto Serif KR + Playfair Display', dict(ps=FS.format('noto-serif-kr-600'), pm=FS.format('noto-serif-kr-500'), pr=FS.format('noto-serif-kr-400'), pl=FS.format('noto-serif-kr-300'), md=FS.format('playfair-display-500')), 0.98),
    '05': ('나눔명조 + IBM Plex Sans KR + Instrument Serif', dict(ps=FS.format('nanum-myeongjo-800'), pm=FS.format('ibm-plex-sans-kr-500'), pr=FS.format('ibm-plex-sans-kr-400'), pl=FS.format('ibm-plex-sans-kr-300'), md=FS.format('instrument-serif-400')), 1.1),
}
USED = ('고체유체천체기출빠른정답풀이회독학년도월번지대수능시작하기에앞서단원별모아보기 EXTRACT 2 MEMO Memo Contents '
        'Logic Check Solving Linking ABC.-0123456789p Squeeze')

# 'Squeeze' 로고 글자는 Million Dreams로 고정
sq_lib.FONTS['logo'] = 'md/Million Dreams.otf'; sq_lib.FO['logo'] = f.Font(fontfile='md/Million Dreams.otf')
def foot(d, side, no):
    if side == 'even':
        d.text(19, 359, str(no), 'pm', 9, K())
        x = 27 + d.text(27, 359.2, 'Squeeze', 'logo', 11.5, K())
        d.text(x + 1.8, 359, '기출 2', 'pl', 7.8, K(.6))
    else:
        d.text(243, 359, str(no), 'pm', 9, K(), 'r')
        d.logo(206.5, 355.3, 4.0)
sq5.foot_default = foot; sq_full.foot_default = foot

# 영문 제목 글꼴 배율(글꼴마다 크기감이 달라 Million Dreams와 비슷하게)
SCALE = {'md': 1.0}
_text, _width = sq_lib.P.text, sq_lib.P.width
sq_lib.P.text = lambda s, x, y, text, font, size, color, align='l', track=0: _text(s, x, y, text, font, size * SCALE.get(font, 1), color, align, track)
sq_lib.P.width = lambda s, text, font, size, track=0: _width(s, text, font, size * SCALE.get(font, 1), track)

def apply(code):
    name, roles, sc = COMBOS[code]
    for k, p in roles.items():
        sq_lib.FONTS[k] = p; sq_lib.FO[k] = f.Font(fontfile=p)
        miss = [c for c in set(USED) if c.strip() and not sq_lib.FO[k].has_glyph(ord(c))]
        if miss: print('  ! 글자 없음', code, k, ''.join(sorted(miss)))
    SCALE['md'] = sc
    return name

if __name__ == '__main__':
    SRC, RES, OUTD = sys.argv[1:4]
    which = sys.argv[4:] or list(COMBOS)
    os.makedirs(OUTD, exist_ok=True)
    keep = [1, 2, 3, 4, 5, 6, 25, 26, 55, 56, 81, 82, 83, 84]
    for code in which:
        name = apply(code)
        out = f'{OUTD}/Squeeze_내지_03-01-09_글꼴조합{code}({name}).pdf'
        sq_full.build_all(SRC, RES, out, only=keep)   # 남길 14쪽만 그림
        print('=>', out, flush=True)
