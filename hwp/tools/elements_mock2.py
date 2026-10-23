"""2차 요소 시안 (표 T1~T5, 소제목 H1~H5, 설명 줄 N1~N5) + 확정 사항 반영 미리보기. 근사 PNG.
Usage: python3 elements_mock2.py <폰트폴더> <out_dir>"""
import os, sys
sys.argv = sys.argv[:3]
import elements_mock as M
from elements_mock import Cv, text, runs, F, fL, K, ACC, INK, LILAC, LILAC_L, WARM, LINE, HAND, fser, fser_s, sheet, e1_box

OUT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)
ROWS = [['접두어', '읽기', '규모', '예시'], ['k', '킬로', '10^{3}', '1 km = 10^{3} m'], ['c', '센티', '10^{−2}', '1 cm = 10^{−2} m'], ['m', '밀리', '10^{−3}', '1 mA = 10^{−3} A']]


def ctext(cv, x, w, y, s, font, color):
    s = s.replace('−', '-')
    tw = sum(cv.d.textlength(t, font=f) for t, f, *_ in runs(s, font, fser_s if font == fser else M.fb_s))
    cv.y = y; text(cv, int(x + (w - tw) / 2), s, font=font, color=color, lh=1.0)


def tab(opt):
    cv = Cv(); d = cv.d; ws = [1, 1, 1, 2]; tot = sum(ws); cw = [cv.w * w / tot for w in ws]; rh = 18 * K
    y = 0
    if opt in ('T1', 'T5'): d.rectangle((0, 0, cv.w, 1.3 * K), fill=INK if opt == 'T1' else ACC); y = 1.3 * K
    if opt == 'T2': d.rectangle((0, 0, cv.w, rh * len(ROWS)), fill=WARM)
    for ri, row in enumerate(ROWS):
        x = 0; head = ri == 0
        for ci, c in enumerate(row):
            if opt == 'T3' and ci == 0 and not head: d.rectangle((x, y, x + cw[ci], y + rh), fill=WARM)
            if opt == 'T4':
                if head: d.rectangle((x, y, x + cw[ci], y + rh), fill=LILAC_L)
                d.rectangle((x, y, x + cw[ci], y + rh), outline=LINE)
            hf = fL(9, 'SemiBold')
            if head:
                col = ACC if opt in ('T2', 'T5', 'T3') else INK
                ctext(cv, x, cw[ci], y + 4 * K, c, hf, col)
            else:
                f = fser if any(ch.isascii() and ch.isalnum() for ch in c) and not any('가' <= ch <= '힣' for ch in c) else M.fb
                col = (ACC if (opt == 'T3' and ci == 0) else '#202020')
                ctext(cv, x, cw[ci], y + 3.5 * K, c, f, col)
            x += cw[ci]
        y += rh
        if opt == 'T1': d.rectangle((0, y - (0.6 * K if head else 0.25 * K), cv.w, y), fill=INK if head else LINE) if (head or ri == len(ROWS) - 1) else None
        if opt == 'T2' and not head and ri < len(ROWS) - 1: d.line((8 * K, y, cv.w - 8 * K, y), fill='white', width=int(1.2 * K))
        if opt == 'T2' and head: d.line((8 * K, y, cv.w - 8 * K, y), fill=ACC, width=int(0.6 * K))
        if opt == 'T3' and head: d.line((0, y, cv.w, y), fill=ACC, width=int(0.8 * K))
        if opt == 'T3' and not head: d.line((0, y, cv.w, y), fill='#EADFD3')
        if opt == 'T5':
            if head: d.line((0, y, cv.w, y), fill=ACC, width=int(0.5 * K))
            elif ri < len(ROWS) - 1:
                for xx in range(0, cv.w, 5): d.point((xx, y), fill=LINE)
    if opt == 'T1': d.rectangle((0, y - 1.3 * K, cv.w, y), fill=INK)
    if opt == 'T5': d.rectangle((0, y, cv.w, y + 1.3 * K), fill=ACC); y += 1.3 * K
    cv.y = y + 2 * K
    return cv.crop()


H = '최댓값을 이용한 반응물(기질) 농도의 대소 비교'
BODY = '생성물 농도의 최댓값은 처음 넣은 반응물(기질)의 양으로 정해져. 그래서 최댓값이 큰 쪽이 반응물(기질)도 많았던 거야.'


def head(opt):
    cv = Cv(); d = cv.d; ft = fL(11.5, 'SemiBold')
    if opt == 'H1':   # 브라운 원 번호
        d.ellipse((0, 0, 15 * K, 15 * K), fill=ACC); d.text((5 * K, 2.4 * K), '1', font=fL(9), fill='white')
        d.text((21 * K, 0.8 * K), H, font=ft, fill=INK); cv.y = int(24 * K)
    elif opt == 'H2':   # 큰 번호 01 + 전체 가는 선
        d.text((0, -1.5 * K), '01', font=fL(14, 'ExtraBold'), fill=ACC)
        d.text((25 * K, 1 * K), H, font=ft, fill=INK)
        cv.y = int(21 * K); d.line((0, cv.y, cv.w, cv.y), fill=LINE); cv.y += int(8 * K)
    elif opt == 'H3':   # 번호는 브라운, 제목 아래 짧은 밑줄
        d.text((0, 0), '1.', font=ft, fill=ACC); d.text((14 * K, 0), H, font=ft, fill=INK)
        cv.y = int(19 * K); d.rectangle((0, cv.y, 40 * K, cv.y + 1.4 * K), fill=ACC); cv.y += int(8 * K)
    elif opt == 'H4':   # 왼쪽 짧은 막대 (띠 없음)
        d.rectangle((0, 1 * K, 2.6 * K, 15 * K), fill=ACC)
        d.text((9 * K, 0.6 * K), '1.  ' + H, font=ft, fill=INK); cv.y = int(24 * K)
    else:   # H5 아주 옅은 띠, 막대 없이 번호 칩
        d.rectangle((0, 0, cv.w, 20 * K), fill='#FAF7F3')
        cw = 15 * K; d.rectangle((6 * K, 3.5 * K, 6 * K + cw, 16.5 * K), fill=INK)
        d.text((6 * K + 5 * K, 4.5 * K), '1', font=fL(9), fill='white')
        d.text((6 * K + cw + 7 * K, 2.3 * K), H, font=ft, fill=INK); cv.y = int(27 * K)
    text(cv, 0, BODY, lh=1.75)
    return cv.crop()


NOTES = ['예를 들어 질량의 기본 단위인 kg(킬로그램), 길이의 기본 단위인 m(미터), 시간의 기본 단위인 s(초)를 이용해서 힘을 계산하면, 그 단위는 ==무조건 N(뉴턴)==이야.',
         '이건 1 N(뉴턴)이 질량 1 kg인 물체를 1 m/s^{2}의 가속도로 만드는 힘의 단위로 정의되기 때문이야.']


def note(opt):
    cv = Cv(); d = cv.d
    for s in NOTES:
        if opt == 'N1':   # 들여쓰기만
            text(cv, int(10 * K), s, lh=1.75, after=int(4 * K))
        elif opt == 'N2':   # → 화살표 (매달린 들여쓰기)
            text(cv, int(4 * K), '→ ' + s, lh=1.75, indent=int(10 * K), after=int(4 * K))
        elif opt == 'N3':   # 브라운 점
            d.ellipse((5 * K, cv.y + 4.6 * K, 8 * K, cv.y + 7.6 * K), fill=ACC)
            text(cv, int(14 * K), s, lh=1.75, after=int(4 * K))
        elif opt == 'N4':   # 브라운 대시
            d.rectangle((4 * K, cv.y + 6 * K, 10 * K, cv.y + 6.9 * K), fill=ACC)
            text(cv, int(15 * K), s, lh=1.75, after=int(4 * K))
        else:   # N5 들여쓰기 없이 문단처럼, 문단 사이 넉넉
            text(cv, 0, s, lh=1.75, after=int(8 * K))
    return cv.crop()


def confirmed(_):
    """확정 사항: Mini 예제 = 브라운 글자 + 밑줄, 풀이 상자 머리 'Sol.', 결론만 남기고 Ans 삭제"""
    cv = Cv(); d = cv.d
    d.text((0, 0), 'Mini 예제 1', font=fL(11), fill=ACC); cv.y = int(18 * K)
    d.rectangle((0, cv.y, cv.w, cv.y + 1.2 * K), fill=ACC); cv.y += int(9 * K)
    text(cv, 0, '가속도는 단위 시간당 속도의 변화량으로, 그 단위는 속도의 단위를 시간의 단위로 나눈 것에 해당한다. 이때 가속도의 차원을 표현해 보시오.', font=fL(9.5, 'SemiBold'), lh=1.8)
    cv.y += int(6 * K)

    def inner(cv):
        x = int(10 * K)
        cv.d.text((x, cv.y), '속도의 차원부터', font=fL(9.5, 'SemiBold'), fill=INK); cv.y += int(16 * K)
        text(cv, x, '속도 = (길이) ÷ (시간)이니까 차원은 L^{1}t^{−1}이야.', lh=1.8)
        cv.y += int(4 * K)
        cv.d.text((x, cv.y), '한 번 더 시간으로 나누기', font=fL(9.5, 'SemiBold'), fill=INK); cv.y += int(16 * K)
        text(cv, x, '가속도 = (속도) ÷ (시간) = (길이) ÷ (시간)^{2}', lh=1.8)
        text(cv, int(x + 12 * K), 'L^{1}t^{−1} ÷ t = L^{1}t^{−2}', font=fser, lh=1.8)

    def concl(cv):
        lab = '결론'; cw = 24 * K; s = 'L^{1}t^{-2}'
        tw_ = sum(cv.d.textlength(t, font=f) for t, f, *_ in runs(s, fser, fser_s))
        x = cv.w - tw_ - cw - 16 * K
        cv.d.rectangle((x, cv.y + 1 * K, x + cw, cv.y + 13 * K), fill=INK)
        cv.d.text((x + (cw - cv.d.textlength(lab, font=fL(7.5))) / 2, cv.y + 3 * K), lab, font=fL(7.5), fill='white')
        text(cv, int(x + cw + 6 * K), s, font=fser, lh=1.4)
    e1_box(cv, 'Sol.', inner)
    # e1_box 결론 칸(배경 없이 점선 위)
    y0 = cv.y
    for xx in range(0, cv.w, 5): d.point((xx, y0), fill=LINE)
    cv.y += int(5 * K); concl(cv); cv.y += int(3 * K)
    d.line((0, y0, 0, cv.y), fill=LINE); d.line((cv.w - 1, y0, cv.w - 1, cv.y), fill=LINE); d.line((0, cv.y, cv.w, cv.y), fill=LINE)
    return cv.crop()


ITEMS = [
    ('표', '기본 표', tab, ['T1', 'T2', 'T3', 'T4', 'T5'],
     {'T1': '위아래 진한 굵은 선 + 머리 아래 선 (논문 표)', 'T2': '옅은 베이지 바탕 + 흰 구분선', 'T3': '첫 열 강조 (베이지 칸, 브라운 글자)',
      'T4': '얇은 격자 + 옅은 라일락 머리 행', 'T5': '위아래 브라운 선 + 점선 행 구분'}),
    ('소제목', '번호 소제목 (1. …)', head, ['H1', 'H2', 'H3', 'H4', 'H5'],
     {'H1': '브라운 원 번호', 'H2': '큰 번호 01 + 가는 선', 'H3': '브라운 번호 + 짧은 밑줄', 'H4': '왼쪽 짧은 막대 (띠 없음)', 'H5': '아주 옅은 띠 + 진한 번호 칩'}),
    ('설명 줄', '설명 줄 (세로선 뺀 뒤)', note, ['N1', 'N2', 'N3', 'N4', 'N5'],
     {'N1': '들여쓰기만', 'N2': '→ 화살표', 'N3': '브라운 점', 'N4': '브라운 대시', 'N5': '들여쓰기 없이 문단처럼'}),
]
print(sheet([('확정', '확정 반영: Mini 예제 밑줄 라벨 · Sol. 상자 · 결론만 (Ans 삭제)', confirmed, ['보기'], {'보기': '이렇게 바뀝니다'})],
            os.path.join(OUT, '2차_0_확정반영.png')))
for i, it in enumerate(ITEMS):
    print(sheet([it], os.path.join(OUT, '2차_%d_%s.png' % (i + 1, it[0]))))
