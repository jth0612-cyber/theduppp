"""아직 정하지 않은 요소별 시안 3개씩 근사 미리보기 (PIL, 글꼴은 비슷한 것으로 대체).
Usage: python3 elements_mock.py <폰트폴더> <out_dir>"""
import os, re, sys
from PIL import Image, ImageDraw, ImageFont

FD, OUT = sys.argv[1:3]
os.makedirs(OUT, exist_ok=True)
K = 2.2; W = int(462 * K); PAD = int(14 * K)
ACC, INK, LILAC, LILAC_L, WARM, LINE, RED, BLUE = '#A9623A', '#3A241D', '#DDD1E8', '#F1ECF6', '#F7F2EC', '#C9B8A6', '#C0392B', '#1E5AA8'
F = lambda n, pt: ImageFont.truetype(os.path.join(FD, n), int(pt * K))
HAND = 'GangwonEduHyeonokT' and '강원교육현옥샘.ttf'
fb, fb_s = F(HAND, 10.5), F(HAND, 6.8)
fser, fser_s = F('KoPubWorld Batang Light.ttf', 10.5), F('KoPubWorld Batang Light.ttf', 6.8)
fL = lambda pt, w='Bold': F('Pretendard-%s.ttf' % w, pt)
ftitle, fopt = fL(12.5), fL(10, 'SemiBold')


class Cv:
    def __init__(s, w=W - 2 * PAD, h=1400):
        s.im = Image.new('RGB', (w, h), 'white'); s.d = ImageDraw.Draw(s.im); s.w = w; s.y = 0

    def crop(s, extra=4):
        return s.im.crop((0, 0, s.w, int(s.y + extra * K)))


def runs(s, font=None, sfont=None, color='#202020', bold_color=RED):
    """마크업 → [(글자, 글꼴, 색, 위첨자?, 형광?)]"""
    font = font or fb; sfont = sfont or fb_s
    out = []; hl = False; red = False
    for part in re.split(r'(\^\{[^}]*\}|==|\*\*)', s):
        if part == '==': hl = not hl; continue
        if part == '**': red = not red; continue
        if not part: continue
        sup = part.startswith('^{')
        t = part[2:-1] if sup else part
        out.append((t, sfont if sup else (fL(10.5 * font.size / (10.5 * K) * 0.95) if red else font), bold_color if red else color, sup, hl))
    return out


def text(cv, x, s, w=None, lh=1.68, font=None, color='#202020', indent=0, after=0, bold_color=RED):
    """줄바꿈하며 출력 (글자 단위 근사). x: 왼쪽, indent: 둘째 줄부터 들여쓰기"""
    font = font or fb
    w = w or cv.w - x
    rs = runs(s, font, None, color, bold_color)
    line_h = int(font.size * lh)
    cx, first = x, True
    d = cv.d
    for t, f, c, sup, hl in rs:
        for ch in t:
            cw = d.textlength(ch, font=f)
            if cx + cw > x + w and ch != ' ':
                cv.y += line_h; cx = x + indent
            if hl:
                d.rectangle((cx, cv.y + int(0.15 * font.size), cx + cw, cv.y + int(1.15 * font.size)), fill=LILAC)
            d.text((cx, cv.y - (int(0.25 * font.size) if sup else 0)), ch, font=f, fill=c)
            cx += cw
    cv.y += line_h + after


# ---------------------------------------------------------------- 요소별 시안
def e01(opt):   # 본문 줄 간격·문단 간격
    lh, gap = {'현재': (1.68, 0), 'A': (1.8, 4), 'B': (1.9, 6), 'C': (2.0, 8)}[opt]
    cv = Cv()
    for s in ['→ 금속(중성)이 첨가되는 상황과 달리, 새로운 수용액이 첨가되면 ==총 양(+)전하량이 증가==해. 이건 중화 반응의 첨가 유형과 같은 logic이야.',
              '→ 만약 비커에 금속만 있다면 전하량은 0이겠지. 이때 양이온이 들어 있는 수용액을 넣는다면, 당연히 **첨가하는 부피에 비례해서** 양이온의 수가 늘어날 거야.',
              '→ 그러니까 금속에 수용액을 넣는 경우는 총 양(+)전하량이 증가해.']:
        text(cv, int(8 * K), s, lh=lh, indent=int(10 * K), after=int(gap * K))
    return cv.crop()


def point_bar(cv):
    d = cv.d
    d.polygon([(0, cv.y + 4 * K), (7 * K, cv.y + 7 * K), (0, cv.y + 10 * K)], fill=INK)
    d.polygon([(14 * K, cv.y + 4 * K), (7 * K, cv.y + 7 * K), (14 * K, cv.y + 10 * K)], fill=INK)
    d.text((18 * K, cv.y + 2.5 * K), 'POINT 02', font=fL(8.5), fill=ACC)
    d.text((88 * K, cv.y + 0.5 * K), '총 이온 수가 큰 쪽이 평균 전하량은 작아', font=F(HAND, 11.5), fill='#111')
    cv.y += int(15 * K)
    for xx in range(0, cv.w, int(3 * K)): d.line((xx, cv.y, xx + 1.4 * K, cv.y), fill='#C9986C', width=2)


NOTE = '통합과학 수준의 산화 환원에서는 굳이 ‘내분’ logic을 주의 깊게 살펴볼 필요가 없어. 한편, 전하량을 평균해서 생각하는 logic은 ==모든 문항에서 중요하게 쓰일 수 있으니까== 꼭 알아 두자.'


def e02(opt):   # POINT 아래 설명 줄(→)
    cv = Cv(); point_bar(cv); cv.y += int(10 * K); d = cv.d
    if opt == 'A':   # 화살표 + 넉넉한 간격
        text(cv, 0, '→ ' + NOTE, lh=1.85, indent=int(10 * K))
    elif opt == 'B':   # 갈색 작은 점 + 들여쓰기
        d.ellipse((2 * K, cv.y + 4.2 * K, 5.2 * K, cv.y + 7.4 * K), fill=ACC)
        text(cv, int(10 * K), NOTE, lh=1.85)
    else:   # 왼쪽 옅은 세로선 + 설명
        y0 = cv.y; text(cv, int(10 * K), NOTE, lh=1.85)
        d.rectangle((2 * K, y0 + 1 * K, 3.4 * K, cv.y - 4 * K), fill='#D9C7B4')
    return cv.crop()


def e03(opt):   # 소제목 (1. 반응 전후의 총 전하량은 같아)
    cv = Cv(); d = cv.d
    t = '반응 전후의 총 전하량은 같아'
    if opt == 'A':   # 갈색 동그라미 번호
        d.ellipse((0, cv.y, 14 * K, cv.y + 14 * K), fill=ACC); d.text((4.4 * K, cv.y + 2.3 * K), '1', font=fL(8.5), fill='white')
        d.text((20 * K, cv.y + 0.5 * K), t, font=fL(11.5, 'SemiBold'), fill=INK); cv.y += int(22 * K)
    elif opt == 'B':   # 숫자 크게 + 짧은 밑줄
        d.text((0, cv.y - 2 * K), '01', font=fL(14, 'ExtraBold'), fill=ACC)
        d.text((24 * K, cv.y + 1 * K), t, font=fL(11.5, 'SemiBold'), fill=INK)
        cv.y += int(19 * K); d.rectangle((0, cv.y, 30 * K, cv.y + 1.2 * K), fill=ACC); cv.y += int(6 * K)
    else:   # 베이지 띠 위에 번호·제목
        d.rectangle((0, cv.y, cv.w, cv.y + 18 * K), fill=WARM); d.rectangle((0, cv.y, 2.5 * K, cv.y + 18 * K), fill=ACC)
        d.text((9 * K, cv.y + 3 * K), '1.  ' + t, font=fL(11, 'SemiBold'), fill=INK); cv.y += int(24 * K)
    text(cv, int(8 * K), '반응 전후의 총 전하량은 같으니까, (총 양이온 수) × (평균 전하량)은 항상 같아. 따라서 다음 관계는 항상 성립해.', lh=1.85)
    return cv.crop()


STEPS = [('STEP 1', '작은 가수로 몰빵해.', '반응 후 X^{+}, Y^{3+}가 총 5개 있으니까, ==작은 가수==인 X^{+}에 5개를 몰빵해.'),
         ('STEP 2', '부족한 전하량을 파악해.', '반응 전의 총 전하량은 7이야. X^{+}에 5개를 몰빵했을 때는 5니까, 2만큼 부족해.'),
         ('STEP 3', '부족한 만큼 큰 가수가 메워 줘야 해.', '이때 큰 가수와 작은 가수의 **‘가수 차이’**에 집중해.')]


def e04(opt):   # 본문 STEP 블록
    cv = Cv(); d = cv.d
    for k, (st, title, body) in enumerate(STEPS):
        if opt == 'A':   # 진한 칩 + 제목
            cw = 36 * K; d.rounded_rectangle((0, cv.y, cw, cv.y + 13 * K), radius=2.5 * K, fill=INK)
            d.text(((cw - d.textlength(st, font=fL(7.5))) / 2, cv.y + 2.6 * K), st, font=fL(7.5), fill='white')
            d.text((cw + 7 * K, cv.y + 0.6 * K), title, font=fL(10.5, 'SemiBold'), fill=INK); cv.y += int(19 * K)
            text(cv, int(10 * K), '→ ' + body, lh=1.85, indent=int(9 * K), after=int(8 * K))
        elif opt == 'B':   # 세로 타임라인 (동그라미 번호 + 이어진 선)
            y0 = cv.y
            d.ellipse((0, cv.y, 15 * K, cv.y + 15 * K), outline=ACC, width=int(1.3 * K), fill='white')
            d.text((5 * K, cv.y + 2.7 * K), str(k + 1), font=fL(8.5), fill=ACC)
            d.text((22 * K, cv.y + 1 * K), title, font=fL(10.5, 'SemiBold'), fill=INK); cv.y += int(20 * K)
            text(cv, int(22 * K), body, lh=1.85, after=int(10 * K))
            if k < len(STEPS) - 1:
                d.line((7.5 * K, y0 + 15 * K, 7.5 * K, cv.y + 1 * K), fill=LINE, width=int(1 * K))
        else:   # 왼쪽 STEP 칸 + 오른쪽 설명 (표처럼)
            y0 = cv.y; lw = 52 * K
            cv.y += int(5 * K)
            d.text((lw + 8 * K, cv.y), title, font=fL(10.5, 'SemiBold'), fill=INK); cv.y += int(17 * K)
            text(cv, int(lw + 8 * K), body, lh=1.85, after=int(4 * K))
            d.rectangle((0, y0, lw, cv.y), fill=WARM)
            d.text(((lw - d.textlength(st, font=fL(8.5))) / 2, y0 + 5 * K), st, font=fL(8.5), fill=ACC)
            d.line((0, cv.y, cv.w, cv.y), fill=LINE); cv.y += int(2 * K)
    return cv.crop()


SOL = [('STEP 0', '모르는 가수는 먼저 가정해 보기', ['만약 b = 2라면, B^{2+}만 8개 있어도 총 전하량이 16이 돼.', '그래서 b는 2보다 커야 하고, 3 이하니까 b = 3이야.']),
       ('STEP 1', '작은 가수로 몰빵', ['8개를 모두 A^{+}라고 가정해. → 총 전하량 8']),
       ('STEP 3', '큰 가수로 채우기', ['A^{+}와 B^{3+}의 가수 차이는 2니까, 8을 채우려면 B^{3+}가 4개 필요해.'])]


def e1_box(cv, header, draw_inner, concl_fn=None):
    """풀이 상자 E1 틀"""
    d = cv.d; tw = int(cv.w * 2 / 11); th = int(17 * K)
    d.rectangle((0, cv.y, tw, cv.y + th), fill=INK)
    d.text(((tw - d.textlength(header, font=fL(8.5))) / 2, cv.y + 4 * K), header, font=fL(8.5), fill='white')
    d.line((tw, cv.y + th, cv.w, cv.y + th), fill=LINE)
    top = cv.y + th; cv.y = top + int(8 * K)
    draw_inner(cv)
    if concl_fn:
        cy = cv.y; cv.y += int(6 * K)
        concl_fn(cv)
        d.rectangle((1, cy, cv.w - 2, cv.y), fill=WARM); cv.y = cy + int(6 * K); concl_fn(cv)
        for xx in range(0, cv.w, 5): d.point((xx, cy), fill=LINE)
    d.rectangle((0, top, cv.w - 1, cv.y), outline=LINE)


def e05(opt):   # 풀이 상자 안 STEP 제목
    cv = Cv(); d = cv.d

    def inner(cv):
        for st, title, lines in SOL:
            x = int(10 * K)
            if opt == 'A':   # 작은 브라운 칩 + 제목
                cw = 30 * K; d.rounded_rectangle((x, cv.y, x + cw, cv.y + 12 * K), radius=2 * K, fill=ACC)
                d.text((x + (cw - d.textlength(st, font=fL(7))) / 2, cv.y + 2.4 * K), st, font=fL(7), fill='white')
                d.text((x + cw + 6 * K, cv.y + 0.3 * K), title, font=fL(9.5, 'SemiBold'), fill=INK); cv.y += int(18 * K)
            elif opt == 'B':   # 번호 원 + 제목 + 옅은 밑줄
                n = st.split()[1]
                d.ellipse((x, cv.y, x + 13 * K, cv.y + 13 * K), fill=INK); d.text((x + 4.3 * K, cv.y + 2.2 * K), n, font=fL(8), fill='white')
                d.text((x + 19 * K, cv.y + 0.6 * K), title, font=fL(9.5, 'SemiBold'), fill=INK)
                cv.y += int(16 * K); d.line((x, cv.y, cv.w - x, cv.y), fill='#EADFD3'); cv.y += int(4 * K)
            else:   # STEP 글자는 브라운 영문, 제목은 진하게, 왼쪽 짧은 세로 막대
                d.rectangle((x, cv.y + 1 * K, x + 2 * K, cv.y + 12 * K), fill=ACC)
                d.text((x + 6 * K, cv.y + 1 * K), st, font=fL(8.5, 'ExtraBold'), fill=ACC)
                d.text((x + 6 * K + d.textlength(st + '  ', font=fL(8.5, 'ExtraBold')), cv.y + 0.4 * K), title, font=fL(9.5, 'SemiBold'), fill=INK)
                cv.y += int(17 * K)
            for ln in lines:
                text(cv, int((10 + (6 if opt != 'A' else 4)) * K), ln, lh=1.85)
            cv.y += int(6 * K)
    e1_box(cv, 'Point 1 Sol.', inner, lambda cv: text(cv, int(10 * K), '→ b = 3, B^{3+}는 4개', font=F(HAND, 11), color=ACC))
    return cv.crop()


def e06(opt):   # 풀이 상자 안 식 줄
    cv = Cv(); d = cv.d
    eq = '(A^{+}, B^{3+}) = (4, 4)'
    text(cv, 0, 'A^{+}와 B^{3+}의 가수 차이는 2니까, 8을 채우려면 B^{3+}가 4개 필요해.', lh=1.85)
    cv.y += int(2 * K)
    if opt == 'A':   # 들여쓰기 + 세리프 (현재와 비슷, 간격만 넉넉)
        text(cv, int(14 * K), eq, font=fser, lh=1.9)
    elif opt == 'B':   # 옅은 회갈색 바탕 띠 안에 식
        y0 = cv.y; cv.y += int(4 * K); text(cv, int(14 * K), eq, font=fser, lh=1.7); cv.y += int(2 * K)
        d.rectangle((int(8 * K), y0, cv.w, cv.y), fill='#F4EFEA'); cv.y = y0 + int(4 * K); text(cv, int(14 * K), eq, font=fser, lh=1.7); cv.y += int(4 * K)
    else:   # 가운데 정렬 + 양옆 여백
        tw_ = sum(d.textlength(t, font=f) for t, f, *_ in runs(eq, fser, fser_s))
        text(cv, int((cv.w - tw_) / 2), eq, font=fser, lh=1.9)
    return cv.crop()


def e07(opt):   # 풀이 결론 줄
    cv = Cv(); d = cv.d
    if opt == 'A':   # 베이지 띠 + 브라운 화살표 (현재와 같은 틀)
        y0 = cv.y; cv.y += int(6 * K); text(cv, int(10 * K), '→ b = 3, B^{3+}는 4개', font=F(HAND, 11), color=ACC); cv.y += int(2 * K)
        d.rectangle((0, y0, cv.w, cv.y), fill=WARM); cv.y = y0 + int(6 * K); text(cv, int(10 * K), '→ b = 3, B^{3+}는 4개', font=F(HAND, 11), color=ACC); cv.y += int(2 * K)
    elif opt == 'B':   # 오른쪽 정렬 '결론' 칩 + 답
        lab = '결론'; cw = 24 * K
        tw_ = sum(d.textlength(t, font=f) for t, f, *_ in runs('b = 3, B^{3+}는 4개', F(HAND, 11)))
        x = cv.w - tw_ - cw - 8 * K
        d.rounded_rectangle((x, cv.y + 1 * K, x + cw, cv.y + 13 * K), radius=2 * K, fill=INK)
        d.text((x + (cw - d.textlength(lab, font=fL(7.5))) / 2, cv.y + 3 * K), lab, font=fL(7.5), fill='white')
        text(cv, int(x + cw + 6 * K), 'b = 3, B^{3+}는 4개', font=F(HAND, 11), color=INK)
    else:   # 라일락 형광 밑줄 강조
        text(cv, int(10 * K), '따라서  ==b = 3, B^{3+}는 4개==', font=F(HAND, 11), color=INK)
    return cv.crop()


def e08(opt):   # 정답 줄 (Ans)
    cv = Cv(); d = cv.d; ans = 'b = 3, 4개'
    if opt == 'A':   # 오른쪽 브라운 칩 + 답 (현재 모양을 크게)
        fw = d.textlength(ans, font=fL(10, 'SemiBold')); cw = 26 * K; x = cv.w - fw - cw - 6 * K
        d.rounded_rectangle((x, cv.y, x + cw, cv.y + 13 * K), radius=6 * K, fill=ACC)
        d.text((x + (cw - d.textlength('Ans', font=fL(8))) / 2, cv.y + 2.3 * K), 'Ans', font=fL(8), fill='white')
        d.text((x + cw + 6 * K, cv.y + 0.6 * K), ans, font=fL(10, 'SemiBold'), fill=INK); cv.y += int(16 * K)
    elif opt == 'B':   # 상자 오른쪽 아래에 붙은 진한 탭
        d.line((0, cv.y, cv.w, cv.y), fill=LINE)
        lab = 'Ans  ' + ans; tw_ = d.textlength(lab, font=fL(9)) + 16 * K
        d.rectangle((cv.w - tw_, cv.y, cv.w, cv.y + 15 * K), fill=INK)
        d.text((cv.w - tw_ + 8 * K, cv.y + 3 * K), lab, font=fL(9), fill='white'); cv.y += int(18 * K)
    else:   # 왼쪽 정렬 '정답' + 점선
        d.text((0, cv.y), '정답', font=fL(9), fill=ACC)
        x = d.textlength('정답  ', font=fL(9))
        for xx in range(int(x), int(cv.w * 0.6), 5): d.point((xx, cv.y + 7 * K), fill=LINE)
        d.text((cv.w * 0.6 + 6 * K, cv.y - 0.5 * K), ans, font=fL(10, 'SemiBold'), fill=INK); cv.y += int(16 * K)
    return cv.crop()


Q = '반응 전 A^{+}가 16개 들어 있는 수용액에 금속 B를 넣는다. 반응 후 A^{+}, B^{b+}가 총 8개 존재할 때, b와 B^{b+}의 개수는? (단, b는 3 이하의 자연수이다.)'


def e09(opt):   # Mini 예제 라벨 + 발문
    cv = Cv(); d = cv.d; fq = fL(9.5, 'Medium')
    if opt == 'A':   # 진한 탭 (K1과 한 벌)
        tw = int(cv.w * 2.2 / 11); th = int(16 * K)
        d.rectangle((0, cv.y, tw, cv.y + th), fill=INK)
        d.text(((tw - d.textlength('Mini 예제 9', font=fL(8.5))) / 2, cv.y + 3.6 * K), 'Mini 예제 9', font=fL(8.5), fill='white')
        d.line((tw, cv.y + th, cv.w, cv.y + th), fill=LINE); cv.y += th + int(8 * K)
    elif opt == 'B':   # 브라운 글자 + 번호 원
        d.text((0, cv.y), 'Mini', font=fL(11, 'ExtraBold'), fill=ACC)
        x = d.textlength('Mini ', font=fL(11, 'ExtraBold'))
        d.ellipse((x, cv.y + 0.5 * K, x + 15 * K, cv.y + 15.5 * K), fill=ACC); d.text((x + 5 * K, cv.y + 2.6 * K), '9', font=fL(9), fill='white')
        cv.y += int(20 * K); d.line((0, cv.y, cv.w, cv.y), fill=INK, width=int(1 * K)); cv.y += int(8 * K)
    else:   # 왼쪽 굵은 띠 + 라벨
        d.rectangle((0, cv.y, 2.6 * K, cv.y + 14 * K), fill=ACC)
        d.text((8 * K, cv.y + 1 * K), 'Mini 예제 09', font=fL(10.5), fill=INK); cv.y += int(22 * K)
    text(cv, 0, Q, font=fq, lh=1.85)
    return cv.crop()


def e10(opt):   # Intro / 핵심 / 한 줄 정리 상자
    cv = Cv(); d = cv.d; s = '수용액을 넣으면 → 넣은 만큼 총 전하량이 늘어난다!'
    lab = '한 줄 정리'
    if opt == 'A':   # 라일락 옅은 바탕 + 왼쪽 라벨 칸
        y0 = cv.y; lw = 54 * K; cv.y += int(8 * K); text(cv, int(lw + 10 * K), s, lh=1.8); cv.y += int(2 * K)
        d.rectangle((0, y0, cv.w, cv.y), fill=LILAC_L); d.rectangle((0, y0, lw, cv.y), fill=LILAC)
        d.text(((lw - d.textlength(lab, font=fL(8.5))) / 2, y0 + 8 * K), lab, font=fL(8.5), fill=INK)
        cv.y = y0 + int(8 * K); text(cv, int(lw + 10 * K), s, lh=1.8); cv.y += int(2 * K)
    elif opt == 'B':   # 위아래 진한 선 + 라벨 위에
        d.rectangle((0, cv.y, cv.w, cv.y + 1.2 * K), fill=INK); cv.y += int(6 * K)
        d.text((4 * K, cv.y), lab, font=fL(8.5), fill=ACC); cv.y += int(15 * K)
        text(cv, int(4 * K), s, lh=1.8); cv.y += int(2 * K); d.rectangle((0, cv.y, cv.w, cv.y + 0.6 * K), fill=INK); cv.y += int(2 * K)
    else:   # 둥근 테두리 카드 + 전구 대신 작은 칩
        y0 = cv.y; cv.y += int(20 * K); text(cv, int(10 * K), s, lh=1.8); cv.y += int(4 * K)
        d.rounded_rectangle((0, y0 + 6 * K, cv.w - 1, cv.y), radius=5 * K, outline=ACC, width=int(0.8 * K))
        cw = d.textlength(lab, font=fL(8)) + 12 * K
        d.rounded_rectangle((10 * K, y0, 10 * K + cw, y0 + 13 * K), radius=6 * K, fill=ACC)
        d.text((16 * K, y0 + 2.5 * K), lab, font=fL(8), fill='white')
    return cv.crop()


ROWS = [['구분', '총 양이온 수 (n → m)', '평균 전하량'], ['m > n', '증가', '감소'], ['m = n', '일정', '일정'], ['m < n', '감소', '증가']]


def e11(opt):   # 표
    cv = Cv(); d = cv.d; ws = [2, 3, 2]; tot = sum(ws); cw = [cv.w * w / tot for w in ws]; rh = 17 * K
    for ri, row in enumerate(ROWS):
        x = 0
        for ci, c in enumerate(row):
            head = ri == 0
            if opt == 'A':   # 진한 머리 행 + 흰 글씨, 가로선만
                if head: d.rectangle((x, cv.y, x + cw[ci], cv.y + rh), fill=INK)
                col = 'white' if head else '#202020'
            elif opt == 'B':   # 베이지 머리 행 + 첫 열 베이지, 얇은 격자
                if head or ci == 0: d.rectangle((x, cv.y, x + cw[ci], cv.y + rh), fill=WARM if not head else '#EADFD3')
                d.rectangle((x, cv.y, x + cw[ci], cv.y + rh), outline=LINE)
                col = ACC if head else '#202020'
            else:   # 선 없는 줄무늬 (짝수 행 옅은 라일락)
                if ri % 2 == 0 and not head: d.rectangle((x, cv.y, x + cw[ci], cv.y + rh), fill=LILAC_L)
                col = INK
            f = fL(9) if head else F(HAND, 10)
            d.text((x + (cw[ci] - d.textlength(c, font=f)) / 2, cv.y + 3.5 * K), c, font=f, fill=col)
            x += cw[ci]
        cv.y += rh
        if opt == 'A': d.line((0, cv.y, cv.w, cv.y), fill=LINE)
        if opt == 'C' and head: d.rectangle((0, cv.y - 1.2 * K, cv.w, cv.y), fill=ACC)
    if opt == 'C': d.rectangle((0, cv.y, cv.w, cv.y + 0.6 * K), fill=ACC)
    cv.y += int(2 * K)
    return cv.crop()


EMPH = '이때 큰 가수와 작은 가수의 **‘가수 차이’**에 집중해.'


def e12(opt):   # 빨간 펜 강조
    cv = Cv(); col = {'A': '#B23A2E', 'B': ACC, 'C': INK}[opt]
    s = EMPH if opt != 'C' else '이때 큰 가수와 작은 가수의 ==‘가수 차이’==에 집중해.'
    text(cv, 0, s, lh=1.85, bold_color=col)
    return cv.crop()


def e13(opt):   # TIP 줄
    cv = Cv(); d = cv.d; s = '가수를 모를 때는 3가부터 넣어 보고, 총 전하량이 넘치면 하나씩 줄여 봐.'
    if opt == 'A':   # 라일락 TIP 칩
        cw = 24 * K; d.rounded_rectangle((0, cv.y + 1 * K, cw, cv.y + 13 * K), radius=6 * K, fill=LILAC)
        d.text(((cw - d.textlength('TIP', font=fL(8))) / 2, cv.y + 3 * K), 'TIP', font=fL(8), fill=INK)
        text(cv, int(cw + 7 * K), s, lh=1.85, color=BLUE)
    elif opt == 'B':   # 파란 손글씨 + 앞에 'Tip.'
        text(cv, 0, 'Tip. ' + s, lh=1.85, color=BLUE)
    else:   # 옅은 바탕 상자 + 굵은 TIP
        y0 = cv.y; cv.y += int(6 * K); text(cv, int(34 * K), s, lh=1.85, color=INK); cv.y += int(2 * K)
        d.rectangle((0, y0, cv.w, cv.y), fill=WARM)
        d.text((10 * K, y0 + 6.5 * K), 'TIP', font=fL(9, 'ExtraBold'), fill=ACC)
        cv.y = y0 + int(6 * K); text(cv, int(34 * K), s, lh=1.85, color=INK); cv.y += int(2 * K)
    return cv.crop()


def e14(opt):   # 가운데 반응식 줄
    cv = Cv(); d = cv.d; eq = 'Cu^{2+} + Zn → Cu + Zn^{2+}'
    tw_ = sum(d.textlength(t, font=f) for t, f, *_ in runs(eq, fser, fser_s))
    x = int((cv.w - tw_) / 2)
    if opt == 'A':   # 가운데 + 위아래 여백
        cv.y += int(4 * K); text(cv, x, eq, font=fser, lh=1.9); cv.y += int(4 * K)
    elif opt == 'B':   # 옅은 회갈색 둥근 띠
        y0 = cv.y; cv.y += int(5 * K); text(cv, x, eq, font=fser, lh=1.6); cv.y += int(3 * K)
        d.rounded_rectangle((x - 20 * K, y0, x + tw_ + 20 * K, cv.y), radius=8 * K, fill='#F4EFEA')
        cv.y = y0 + int(5 * K); text(cv, x, eq, font=fser, lh=1.6); cv.y += int(3 * K)
    else:   # 양옆 가는 선 + 가운데 식
        cv.y += int(4 * K); y0 = cv.y + int(7 * K)
        d.line((0, y0, x - 12 * K, y0), fill=LINE); d.line((x + tw_ + 12 * K, y0, cv.w, y0), fill=LINE)
        text(cv, x, eq, font=fser, lh=1.9)
    return cv.crop()


ELEMENTS = [
    ('E01', '본문 줄 간격 · 문단 간격', e01, ['현재', 'A', 'B', 'C'],
     {'현재': '줄 168%, 문단 사이 0', 'A': '줄 180%, 문단 뒤 4pt', 'B': '줄 190%, 문단 뒤 6pt', 'C': '줄 200%, 문단 뒤 8pt'}),
    ('E02', 'POINT 아래 설명 줄', e02, 'ABC', {'A': '→ 화살표 + 넉넉한 간격', 'B': '갈색 작은 점', 'C': '왼쪽 옅은 세로선'}),
    ('E03', '소제목 (1. …)', e03, 'ABC', {'A': '갈색 동그라미 번호', 'B': '큰 번호 01 + 짧은 밑줄', 'C': '베이지 띠 + 왼쪽 막대'}),
    ('E04', '본문 STEP 1·2·3', e04, 'ABC', {'A': '진한 STEP 칩 + 제목', 'B': '세로 타임라인', 'C': '왼쪽 STEP 칸 + 오른쪽 설명'}),
    ('E05', '풀이 상자 안 STEP 제목', e05, 'ABC', {'A': '브라운 STEP 칩', 'B': '번호 원 + 옅은 밑줄', 'C': '세로 막대 + STEP 0 글자'}),
    ('E06', '풀이 상자 안 식 줄', e06, 'ABC', {'A': '들여쓰기만', 'B': '옅은 바탕 띠', 'C': '가운데 정렬'}),
    ('E07', '풀이 결론 줄', e07, 'ABC', {'A': '베이지 띠 + 브라운 화살표 (지금)', 'B': '오른쪽 정렬 결론 칩', 'C': '따라서 + 라일락 형광'}),
    ('E08', '정답 (Ans) 줄', e08, 'ABC', {'A': '브라운 Ans 칩 (크게)', 'B': '진한 탭', 'C': '정답 + 점선'}),
    ('E09', 'Mini 예제 라벨 + 발문', e09, 'ABC', {'A': '진한 탭 (K1과 한 벌)', 'B': 'Mini + 번호 원', 'C': '왼쪽 굵은 띠'}),
    ('E10', 'Intro · 핵심 · 한 줄 정리 상자', e10, 'ABC', {'A': '라일락 + 왼쪽 라벨 칸', 'B': '위아래 진한 선', 'C': '둥근 테두리 + 라벨 칩'}),
    ('E11', '표', e11, 'ABC', {'A': '진한 머리 행', 'B': '베이지 머리 행·첫 열', 'C': '선 없는 줄무늬'}),
    ('E12', '빨간 펜 강조 (‘가수 차이’)', e12, 'ABC', {'A': '빨강 (지금)', 'B': '브라운', 'C': '형광펜으로 통일'}),
    ('E13', 'TIP 줄', e13, 'ABC', {'A': '라일락 TIP 칩', 'B': 'Tip. 파란 손글씨', 'C': '베이지 상자 + TIP'}),
    ('E14', '가운데 반응식 줄', e14, 'ABC', {'A': '가운데 + 여백', 'B': '옅은 둥근 띠', 'C': '양옆 가는 선'}),
]


def sheet(items, path):
    cards = []
    for code, name, fn, opts, desc in items:
        parts = []
        for o in opts:
            img = fn(o)
            lab = Image.new('RGB', (W, int(18 * K)), 'white')
            ImageDraw.Draw(lab).text((PAD, int(3 * K)), '%s-%s  %s' % (code, o, desc[o]), font=fopt, fill=ACC if o != '현재' else '#888888')
            body = Image.new('RGB', (W, img.height + int(12 * K)), 'white'); body.paste(img, (PAD, int(4 * K)))
            parts += [lab, body]
        head = Image.new('RGB', (W, int(26 * K)), '#F2EEEA')
        ImageDraw.Draw(head).text((PAD, int(6 * K)), '%s  %s' % (code, name), font=ftitle, fill='#111')
        parts = [head] + parts
        card = Image.new('RGB', (W, sum(p.height for p in parts)), 'white'); y = 0
        for p in parts:
            card.paste(p, (0, y)); y += p.height
        cards.append(card)
    out = Image.new('RGB', (W, sum(c.height + 24 for c in cards)), '#D9D4CE'); y = 0
    for c in cards:
        out.paste(c, (0, y)); y += c.height + 24
    out.save(path); return out.size


groups = [ELEMENTS[0:3], ELEMENTS[3:6], ELEMENTS[6:10], ELEMENTS[10:14]]
for i, g in enumerate(groups):
    print(sheet(g, os.path.join(OUT, '요소시안_%d_%s.png' % (i + 1, '-'.join(c for c, *_ in g)))))
