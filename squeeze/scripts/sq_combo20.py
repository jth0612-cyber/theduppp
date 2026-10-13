# 글꼴 조합 20종(11~30). 고정: 번호(Barlow Condensed Medium), Solving·Linking 머리 글자와 'Squeeze' 로고(Million Dreams).
# 바뀌는 것: ps 한글 제목 / pm·pr·pl 한글 작은 글자 / md 영문 제목(Logic Check·Memo·Contents·단원 글자 A/B/C)
# 영문 제목 글꼴은 대문자 높이를 Million Dreams에 맞춰 자동 배율.
# 사용: python sq_combo20.py <squeeze.pdf> <resources.pdf> <출력폴더> [11 12 ...]
import sys, os
sys.path.insert(0, '.')
import sq_lib, sq_full, sq_combo
from sq8 import cap_height
from sq_lib import f

PT = sq_combo.PT; FS = sq_combo.FS
sq_lib.FONTS['sol'] = 'md/Million Dreams.otf'; sq_lib.FO['sol'] = f.Font(fontfile='md/Million Dreams.otf')
sq_full.SOLFONT = 'sol'

FAM = {   # 한글 작은 글자 묶음: (pm, pr, pl)
    'Pretendard': (PT.format('Medium'), PT.format('Regular'), PT.format('Light')),
    'Gothic A1': (FS.format('gothic-a1-500'), FS.format('gothic-a1-400'), FS.format('gothic-a1-300')),
    'IBM Plex Sans KR': (FS.format('ibm-plex-sans-kr-500'), FS.format('ibm-plex-sans-kr-400'), FS.format('ibm-plex-sans-kr-300')),
    'Noto Serif KR': (FS.format('noto-serif-kr-500'), FS.format('noto-serif-kr-400'), FS.format('noto-serif-kr-300')),
    '나눔고딕': (FS.format('nanum-gothic-700'), FS.format('nanum-gothic-400'), FS.format('nanum-gothic-400')),
    '고운바탕': (FS.format('gowun-batang-400'),) * 3,
    '고운돋움': (FS.format('gowun-dodum-400'),) * 3,
}
TITLE = {
    'Pretendard SemiBold': PT.format('SemiBold'), '함렛 SemiBold': FS.format('hahmlet-600'),
    'Gothic A1 SemiBold': FS.format('gothic-a1-600'), 'Noto Serif KR SemiBold': FS.format('noto-serif-kr-600'),
    '나눔명조 ExtraBold': FS.format('nanum-myeongjo-800'), '고운바탕 Bold': FS.format('gowun-batang-700'),
    '나눔고딕 ExtraBold': FS.format('nanum-gothic-800'), '해바라기 Bold': FS.format('sunflower-700'),
    '도현': FS.format('do-hyeon-400'), '송명': FS.format('song-myung-400'),
    'IBM Plex Sans KR Medium': FS.format('ibm-plex-sans-kr-500'), '고운돋움': FS.format('gowun-dodum-400'),
}
EN = {
    'Cinzel': FS.format('cinzel-400'), 'Libre Caslon': FS.format('libre-caslon-400'), 'Inter Tight Light': FS.format('inter-tight-300'),
    'Playfair Display': FS.format('playfair-display-500'), 'EB Garamond': FS.format('eb-garamond-400'),
    'Space Grotesk Medium': FS.format('space-grotesk-500'), 'Montserrat Bold': FS.format('montserrat-700'),
    'Antonio Light': FS.format('antonio-300'), 'Cormorant Garamond': FS.format('cormorant-garamond-600'),
    'Bodoni Moda': FS.format('bodoni-moda-400'), 'Fraunces': FS.format('fraunces-400'),
    'Instrument Serif': FS.format('instrument-serif-400'), 'Barlow Condensed SemiBold': FS.format('barlow-condensed-600'),
    'Oswald Light': FS.format('oswald-300'), 'Big Shoulders Display': FS.format('big-shoulders-display-500'),
    'Space Grotesk': FS.format('space-grotesk-400'), 'Million Dreams': 'md/Million Dreams.otf',
}
C20 = {
    '11': ('Pretendard SemiBold', 'Pretendard', 'Cinzel'),
    '12': ('Pretendard SemiBold', 'Pretendard', 'Libre Caslon'),
    '13': ('Pretendard SemiBold', 'Pretendard', 'Inter Tight Light'),
    '14': ('함렛 SemiBold', 'Gothic A1', 'Playfair Display'),
    '15': ('함렛 SemiBold', 'Noto Serif KR', 'EB Garamond'),
    '16': ('함렛 SemiBold', 'IBM Plex Sans KR', 'Space Grotesk Medium'),
    '17': ('Gothic A1 SemiBold', 'Gothic A1', 'Montserrat Bold'),
    '18': ('Gothic A1 SemiBold', 'Pretendard', 'Antonio Light'),
    '19': ('Noto Serif KR SemiBold', 'Pretendard', 'Cormorant Garamond'),
    '20': ('Noto Serif KR SemiBold', 'Gothic A1', 'Bodoni Moda'),
    '21': ('나눔명조 ExtraBold', '나눔고딕', 'Libre Caslon'),
    '22': ('나눔명조 ExtraBold', 'Pretendard', 'Cinzel'),
    '23': ('고운바탕 Bold', '고운돋움', 'Fraunces'),
    '24': ('고운바탕 Bold', 'Pretendard', 'Instrument Serif'),
    '25': ('나눔고딕 ExtraBold', '나눔고딕', 'Barlow Condensed SemiBold'),
    '26': ('해바라기 Bold', 'Pretendard', 'Oswald Light'),
    '27': ('도현', 'Gothic A1', 'Big Shoulders Display'),
    '28': ('송명', '고운바탕', 'Cormorant Garamond'),
    '29': ('IBM Plex Sans KR Medium', 'IBM Plex Sans KR', 'Space Grotesk'),
    '30': ('고운돋움', 'Pretendard', 'Million Dreams'),
}
MD_CAP = cap_height('md/Million Dreams.otf')

def setup(code):
    t, fam, en = C20[code]
    pm, pr, pl = FAM[fam]
    sc = max(0.85, min(1.3, MD_CAP / cap_height(EN[en])))
    sq_combo.COMBOS[code] = (f'{t} + {fam} + {en}', dict(ps=TITLE[t], pm=pm, pr=pr, pl=pl, md=EN[en]), round(sc, 3))
    return sq_combo.apply(code)

if __name__ == '__main__':
    SRC, RES, OUTD = sys.argv[1:4]
    which = sys.argv[4:] or list(C20)
    os.makedirs(OUTD, exist_ok=True)
    keep = [1, 2, 3, 4, 5, 6, 25, 26, 55, 56, 81, 82, 83, 84]
    for code in which:
        name = setup(code)
        out = f'{OUTD}/Squeeze_내지_03-01-09_글꼴조합{code}({name}).pdf'
        sq_full.build_all(SRC, RES, out, only=keep)
        print('=>', code, name, sq_combo.SCALE['md'], flush=True)
