"""Arranged KICE 머리(라벨 + 다시 묶은 질문) 시안 5개 근사 미리보기 PNG.
Usage: python3 kice_head_mock.py <폰트폴더> <out.png>"""
import os, re, sys
from PIL import Image, ImageDraw, ImageFont
FD, OUT = sys.argv[1:3]
K = 2.2; W = int(462 * K)
ACC, INK, LILAC, LILAC_L, WARM, LINE = '#A9623A', '#3A241D', '#DDD1E8', '#F1ECF6', '#F7F2EC', '#C9B8A6'
F = lambda name, pt: ImageFont.truetype(os.path.join(FD, name), int(pt * K))
fq, fqb = F('Pretendard-Medium.ttf', 9.5), F('Pretendard-Bold.ttf', 9.5)
fsup = F('Pretendard-Medium.ttf', 6.2)
flab, fbig, ftitle = F('Pretendard-Bold.ttf', 8.5), F('Pretendard-ExtraBold.ttf', 20), F('Pretendard-Bold.ttf', 12)
COND = [('(가)', 'X^{2+}가 3N개 들어 있는 수용액이 있다.'),
        ('(나)', '(가)의 수용액에 금속 Z를 aN개 넣었을 때, 수용액 속 이온은 Z^{2+} aN개가 남았다.'),
        ('(다)', 'Y^{m+}가 3N개 들어 있는 수용액을 준비한다.'),
        ('(라)', '(다)의 수용액에 금속 Z를 3N개 넣었을 때, 수용액 속 이온은 Y^{m+} N개, Z^{2+} 3N개가 남았다.')]
QS = [('Q1', 'a를 구하시오.'), ('Q2', 'm을 구하시오.')]
LH = int(9.5 * K * 1.75)


def rich(d, x, y, s, font=fq, fill='#1E1E1E'):
    """^{..} 위첨자를 그리며 한 줄 출력, 끝 x 반환"""
    for part in re.split(r'(\^\{[^}]*\})', s):
        if part.startswith('^{'):
            t = part[2:-1]; d.text((x, y - int(1.5 * K)), t, font=fsup, fill=fill); x += d.textlength(t, font=fsup)
        elif part:
            d.text((x, y), part, font=font, fill=fill); x += d.textlength(part, font=font)
    return x


def width(d, s, font=fq):
    return sum(d.textlength(p[2:-1], font=fsup) if p.startswith('^{') else d.textlength(p, font=font) for p in re.split(r'(\^\{[^}]*\})', s) if p)


def conds(d, x, y, w, label_w=int(22 * K), lab_fill=INK, lab_font=fqb, gap=LH):
    for lab, s in COND:
        d.text((x, y), lab, font=lab_font, fill=lab_fill)
        # 줄바꿈(단어 단위 근사)
        words, line, yy = s.split(' '), '', y
        for wd in words:
            t = (line + ' ' + wd).strip()
            if width(d, t) > w - label_w and line:
                rich(d, x + label_w, yy, line); yy += gap; line = wd
            else:
                line = t
        rich(d, x + label_w, yy, line); y = yy + gap
    return y


def design(n):
    im = Image.new('RGB', (W, 900), 'white'); d = ImageDraw.Draw(im)
    if n == 1:   # 진한 탭 + 얇은 선 (풀이 상자 E1과 한 벌), 조건은 베이지 상자, 질문은 Q 칩
        tw = int(W * 2.6 / 11); th = int(17 * K)
        d.rectangle((0, 0, tw, th), fill=INK); t = 'Arranged KICE 1'
        d.text(((tw - d.textlength(t, font=flab)) / 2, int(4 * K)), t, font=flab, fill='white'); d.line((tw, th, W, th), fill=LINE)
        y0 = th + int(8 * K); y = conds(d, int(10 * K), y0 + int(7 * K), W - int(20 * K)) + int(3 * K)
        d.rectangle((0, y0, W - 1, y), fill=WARM); conds(d, int(10 * K), y0 + int(7 * K), W - int(20 * K))
        y += int(8 * K)
        for q, s in QS:
            cw = int(20 * K); d.rounded_rectangle((0, y, cw, y + int(13 * K)), radius=int(3 * K), fill=ACC)
            d.text(((cw - d.textlength(q, font=flab)) / 2, y + int(2.3 * K)), q, font=flab, fill='white')
            rich(d, cw + int(7 * K), y + int(1 * K), s, fqb); y += int(18 * K)
    elif n == 2:   # 큰 번호 + 작은 영문 라벨, 조건은 왼쪽 라벨 칸 표
        d.text((0, 0), '01', font=fbig, fill=ACC)
        nx = d.textlength('01', font=fbig) + int(8 * K)
        d.text((nx, int(3 * K)), 'ARRANGED KICE', font=flab, fill=INK)
        d.text((nx, int(14 * K)), '기출 다시 묶기', font=F('Pretendard-Medium.ttf', 7.5), fill='#8A7A6C')
        y = int(30 * K); d.rectangle((0, y, W, y + int(1.6 * K)), fill=INK); y += int(6 * K)
        lw = int(26 * K)
        for lab, s in COND:
            y0 = y
            yy = conds.__wrapped__ if False else None
            # 한 행씩
            words, line, yy = s.split(' '), '', y + int(5 * K)
            rows = []
            for wd in words:
                t = (line + ' ' + wd).strip()
                if width(d, t) > W - lw - int(16 * K) and line: rows.append(line); line = wd
                else: line = t
            rows.append(line)
            h = len(rows) * LH + int(8 * K)
            d.rectangle((0, y0, lw, y0 + h), fill=WARM)
            d.text(((lw - d.textlength(lab, font=fqb)) / 2, y0 + int(5 * K)), lab, font=fqb, fill=ACC)
            for i, r in enumerate(rows): rich(d, lw + int(8 * K), y0 + int(5 * K) + i * LH, r)
            d.line((0, y0 + h, W, y0 + h), fill=LINE); y = y0 + h
        y += int(10 * K)
        for q, s in QS:
            d.ellipse((0, y, int(14 * K), y + int(14 * K)), outline=ACC, width=int(1.2 * K))
            d.text((int(3.2 * K), y + int(2.8 * K)), q[1], font=flab, fill=ACC)
            rich(d, int(20 * K), y + int(1.5 * K), s, fqb); y += int(19 * K)
    elif n == 3:   # 전체 폭 진한 머리 띠 + 자간 넓은 흰 글씨, 조건은 왼쪽 갈색 세로선
        th = int(18 * K); d.rectangle((0, 0, W, th), fill=INK)
        d.text((int(8 * K), int(4.3 * K)), 'A R R A N G E D   K I C E   0 1', font=flab, fill='white')
        y = th + int(10 * K); top = y
        y = conds(d, int(12 * K), y, W - int(14 * K))
        d.rectangle((0, top - int(2 * K), int(1.6 * K), y - int(4 * K)), fill=ACC)
        y += int(4 * K)
        for xx in range(0, W, 6): d.point((xx, y), fill=LINE)
        y += int(8 * K)
        for q, s in QS:
            d.rectangle((0, y + int(2 * K), int(10 * K), y + int(12 * K)), outline=INK, width=int(1 * K))
            rich(d, int(16 * K), y + int(1 * K), q + '.  ' + s, fqb); y += int(18 * K)
    elif n == 4:   # 미니멀: 왼쪽 굵은 띠 라벨 + 밑줄, 질문은 라일락 띠
        d.rectangle((0, 0, int(2.8 * K), int(16 * K)), fill=INK)
        d.text((int(8 * K), int(1 * K)), 'Arranged KICE', font=ftitle, fill=INK)
        tx = int(8 * K) + d.textlength('Arranged KICE  ', font=ftitle)
        d.text((tx, int(1 * K)), '1', font=ftitle, fill=ACC)
        d.line((0, int(19 * K), W, int(19 * K)), fill=LINE, width=1)
        y = conds(d, 0, int(27 * K), W, label_fill := None or INK) if False else conds(d, 0, int(27 * K), W)
        y += int(6 * K)
        for q, s in QS:
            h = int(16 * K); d.rectangle((0, y, W, y + h), fill=LILAC_L)
            d.text((int(8 * K), y + int(3 * K)), q, font=fqb, fill=ACC)
            rich(d, int(30 * K), y + int(3 * K), s, fqb); y += h + int(4 * K)
    elif n == 5:   # 카드: 베이지 카드 전체 + 탭, 질문은 점선 아래 Q.
        tw = int(W * 2.6 / 11); th = int(17 * K)
        d.rectangle((0, 0, tw, th), fill=ACC); t = 'Arranged KICE 1'
        d.text(((tw - d.textlength(t, font=flab)) / 2, int(4 * K)), t, font=flab, fill='white')
        y0 = th; y = conds(d, int(12 * K), y0 + int(10 * K), W - int(24 * K))
        yq = y + int(4 * K); yend = yq + int(10 * K) + len(QS) * int(18 * K)
        d.rectangle((0, y0, W - 1, yend), fill=WARM)
        conds(d, int(12 * K), y0 + int(10 * K), W - int(24 * K))
        for xx in range(int(12 * K), W - int(12 * K), 6): d.point((xx, yq), fill=ACC)
        y = yq + int(7 * K)
        for q, s in QS:
            d.text((int(12 * K), y), q, font=fqb, fill=ACC); rich(d, int(34 * K), y, s, fqb); y += int(18 * K)
        y = yend
    return im.crop((0, 0, W, y + int(4 * K)))


NAMES = {1: '탭 + 베이지 조건 상자 (풀이 상자 E1과 한 벌)', 2: '큰 번호 + 조건 표', 3: '진한 머리 띠 + 갈색 세로선',
         4: '미니멀 + 라일락 질문 띠', 5: '베이지 카드 + 브라운 탭'}
cards = []
for n in range(1, 6):
    a = design(n); pad = int(14 * K); hdr = int(26 * K)
    c = Image.new('RGB', (W + 2 * pad, hdr + a.height + pad), 'white')
    ImageDraw.Draw(c).text((pad, int(6 * K)), '시안 K%d · %s' % (n, NAMES[n]), font=ftitle, fill='#111')
    c.paste(a, (pad, hdr)); cards.append(c)
sheet = Image.new('RGB', (cards[0].width, sum(c.height + 20 for c in cards)), '#E9E6E2'); y = 0
for c in cards: sheet.paste(c, (0, y)); y += c.height + 20
sheet.save(OUT); print(sheet.size)
