"""3차 시안: Mini 예제·Arranged KICE 발문 디자인 P1~P5 (음영 없음). 근사 PNG.
Usage: python3 elements_mock3.py <폰트폴더> <out_dir>"""
import os, sys
sys.argv = sys.argv[:3]
import elements_mock as M
from elements_mock import Cv, text, fL, K, ACC, INK, LINE, sheet

OUT = sys.argv[2]
MINI_Q = '그림은 X^{2+}이 들어 있는 수용액에 금속 Y와 Z를 차례로 넣었을 때, 각 과정 후 수용액 속 양이온의 종류와 개수를 나타낸 것이다. a~d를 구하시오. (단, 음이온은 반응에 참여하지 않는다.)'
CTX = [('(가)', 'X^{2+}가 3N개 들어 있는 수용액이 있다.'), ('(나)', '(가)의 수용액에 금속 Z를 aN개 넣었을 때, 수용액 속 이온은 Z^{2+} aN개가 남았다.')]
QS = [('Q1', 'a를 구하시오.'), ('Q2', 'm을 구하시오.')]
fq, fqb = fL(10.5, 'Medium'), fL(10.5, 'SemiBold')


def chip(cv, x, lab, fill=ACC):
    d = cv.d; w = d.textlength(lab, font=fL(8.5)) + 8 * K
    d.rectangle((x, cv.y + 1.5 * K, x + w, cv.y + 14 * K), fill=fill)
    d.text((x + 4 * K, cv.y + 3 * K), lab, font=fL(8.5), fill='white')
    return x + w + 6 * K


def mini_label(cv):
    cv.d.text((0, cv.y), 'Mini 예제 1', font=fL(11), fill=ACC); cv.y += int(17 * K)
    cv.d.rectangle((0, cv.y, cv.w, cv.y + 1.2 * K), fill=ACC); cv.y += int(9 * K)


def kice_label(cv):
    d = cv.d; tw = int(cv.w * 2.6 / 11); th = int(16 * K)
    d.rectangle((0, cv.y, tw, cv.y + th), fill=INK)
    d.text(((tw - d.textlength('Arranged KICE 1', font=fL(8.5))) / 2, cv.y + 3.6 * K), 'Arranged KICE 1', font=fL(8.5), fill='white')
    d.line((tw, cv.y + th, cv.w, cv.y + th), fill=LINE); cv.y += th + int(8 * K)


def body(cv, opt):
    """opt별로 조건 줄과 질문 줄을 그린다. 반환: (조건 시작 y, 끝 y)"""
    d = cv.d
    x0 = int(12 * K) if opt in ('P1', 'P5') else 0
    y0 = cv.y
    if opt == 'P5': cv.y += int(6 * K)
    for lab, s in CTX:
        d.text((x0, cv.y), lab, font=fqb, fill=ACC if opt == 'P4' else INK)
        text(cv, x0 + int(22 * K), s, font=fq, lh=1.8, color=INK if opt == 'P4' else '#1E1E1E')
    y1 = cv.y
    if opt == 'P2':
        for xx in range(0, cv.w, 5): d.point((xx, cv.y + 2 * K), fill=LINE)
        cv.y += int(8 * K)
    elif opt == 'P5':
        cv.y += int(4 * K); d.rectangle((0, y0, cv.w - 1, cv.y), outline=LINE); cv.y += int(8 * K)
    else:
        cv.y += int(5 * K)
    for lab, s in QS:
        if opt == 'P3':   # 칩 대신 브라운 Q 글자
            d.text((x0, cv.y), lab, font=fL(10.5, 'ExtraBold'), fill=ACC); x = x0 + int(22 * K)
        else:
            x = chip(cv, x0, lab, INK if opt == 'P4' else ACC)
        text(cv, int(x), s, font=fqb, lh=1.8)
    return y0, y1


def mini_body(cv, opt):
    d = cv.d; x0 = int(12 * K) if opt in ('P1', 'P5') else 0
    y0 = cv.y
    if opt == 'P5': cv.y += int(6 * K)
    if opt == 'P3':
        d.text((x0, cv.y), 'Q', font=fL(10.5, 'ExtraBold'), fill=ACC); x = x0 + int(16 * K)
    else:
        x = chip(cv, x0, 'Q', INK if opt == 'P4' else ACC)
    text(cv, int(x), MINI_Q, font=fqb, lh=1.8, indent=int(x - x) if False else 0)
    if opt == 'P5': cv.y += int(4 * K); d.rectangle((0, y0, cv.w - 1, cv.y), outline=LINE)
    return y0


def design(opt):
    cv = Cv(); d = cv.d
    mini_label(cv)
    y0 = mini_body(cv, opt)
    if opt == 'P1': d.rectangle((0, y0, 1.6 * K, cv.y - 4 * K), fill=ACC)
    if opt == 'P2': d.line((0, cv.y + 2 * K, cv.w, cv.y + 2 * K), fill=LINE)
    cv.y += int(16 * K)
    kice_label(cv)
    y0, y1 = body(cv, opt)
    if opt == 'P1': d.rectangle((0, y0, 1.6 * K, y1 - 4 * K), fill=ACC)
    return cv.crop()


ITEM = ('발문', 'Mini 예제·Arranged KICE 문제 (음영 없음)', design, ['P1', 'P2', 'P3', 'P4', 'P5'],
        {'P1': '왼쪽 브라운 얇은 선 + 들여쓰기', 'P2': '조건과 질문 사이 점선, 아래 가는 선', 'P3': '칩 없이 굵은 브라운 Q 글자 (가장 가벼움)',
         'P4': '진한 칩 + (가)(나) 브라운 라벨', 'P5': '얇은 베이지 테두리 상자 (바탕 없음)'})
print(sheet([ITEM], os.path.join(OUT, '3차_발문_P1-P5.png')))
