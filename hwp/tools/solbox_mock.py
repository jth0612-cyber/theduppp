"""풀이 상자 시안 A~E 근사 미리보기 PNG (한글 렌더러가 없어 PIL로 그림; 글꼴은 비슷한 것으로 대체).
Usage: python3 solbox_mock.py <폰트폴더> <out.png> [시안,시안,...] [머리1] [머리2]"""
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'gen'))
from PIL import Image, ImageDraw, ImageFont
FD, OUT = sys.argv[1:3]
import importlib.util
spec = importlib.util.spec_from_file_location('sol_enzyme', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'gen', 'sol_enzyme.py'))
SE = importlib.util.module_from_spec(spec); spec.loader.exec_module(SE)
K = 2.2                       # px / pt
W = int(462 * K)
ACC, INK, LILAC, LILAC_L, WARM = '#A9623A', '#3A241D', '#DDD1E8', '#F1ECF6', '#F7F2EC'
f_body = ImageFont.truetype(os.path.join(FD, '강원교육현옥샘.ttf'), int(10.5 * K))
f_conc = ImageFont.truetype(os.path.join(FD, 'Pretendard-SemiBold.ttf'), int(10 * K))
f_step = ImageFont.truetype(os.path.join(FD, 'Pretendard-Bold.ttf'), int(8.8 * K))
f_head = ImageFont.truetype(os.path.join(FD, 'Pretendard-Bold.ttf'), int(8.5 * K))
f_title = ImageFont.truetype(os.path.join(FD, 'Pretendard-Bold.ttf'), int(12 * K))
NAMES = {'A': '노트 라인', 'B': '웜 카드', 'C': '단계 표', 'D': '위아래 굵은 선', 'E': '탭 라벨',
         'E1': '탭 라벨 (기본)', 'E2': '브라운 탭', 'E3': '열린 상자', 'E4': '왼쪽 굵은 띠', 'E5': '머리 띠 전체 폭'}
STYLES = sys.argv[3].split(',') if len(sys.argv) > 3 else list('ABCDE')
H1, H2 = (sys.argv[4], sys.argv[5]) if len(sys.argv) > 5 else ('Point 3 풀이', '적용 풀이')


def clean(s):
    s = re.sub(r'_\{([^}]*)\}', r'\1', s); s = re.sub(r'\^\{([^}]*)\}', r'\1', s)
    return re.sub(r'⟦[^⟧]*⟧|⟪[^⟫]*⟫', '□', s).replace('−', '-')


def parse(lines):
    steps, concl = [], []
    for ln in lines:
        if ln.startswith('# '): steps.append((ln[2:], []))
        elif ln.startswith('> '): concl.append(ln[2:])
        else:
            if not steps: steps.append((None, []))
            steps[-1][1].append(('eq', ln[2:]) if ln.startswith('= ') else ('t', ln))
    return steps, concl


def wrap(d, s, font, width):
    out, cur = [], ''
    for ch in clean(s):
        if d.textlength(cur + ch, font=font) > width and cur:
            out.append(cur); cur = ch
        else:
            cur += ch
    return out + [cur]


def render(st, header, lines):
    im = Image.new('RGB', (W, 2000), 'white'); d = ImageDraw.Draw(im)
    steps, concl = parse(lines)
    LH = int(10.5 * K * 1.6)
    pad = int(9 * K)

    def text_block(x, y, w, items, step_color=ACC, numbered=False, label_col=None):
        for k, (title, its) in enumerate(steps if items is None else items):
            if title:
                y += int(4 * K) if k else 0
                d.text((x, y), (('%d  ' % (k + 1)) if numbered else '') + title, font=f_step, fill=step_color); y += int(8.8 * K * 1.7)
            for kind, s in its:
                xx = x + (int(12 * K) if kind == 'eq' else 0)
                for ln in wrap(d, s, f_body, w - (xx - x)):
                    d.text((xx, y), ln, font=f_body, fill=INK if kind == 'eq' else '#202020'); y += LH
        return y

    def conc(x, y, w, color=INK, prefix='→ '):
        for c in concl:
            for ln in wrap(d, prefix + c, f_conc, w):
                d.text((x, y), ln, font=f_conc, fill=color); y += int(10 * K * 1.6)
        return y

    y0 = 0
    if st == 'A':
        tw = d.textlength(header, font=f_head) + 2 * pad
        d.rectangle((0, 0, tw, int(16 * K)), fill=ACC); d.text((pad, int(3.5 * K)), header, font=f_head, fill='white')
        y = int(16 * K) + int(6 * K); top = y
        y = text_block(pad + int(3 * K), y, W - 2 * pad, None) + int(4 * K)
        d.rectangle((0, top - int(4 * K), int(1.4 * K), y), fill=ACC)
        if concl:
            cy = y; y = conc(pad + int(3 * K), y + int(5 * K), W - 2 * pad) + int(4 * K)
            d.rectangle((int(1.4 * K), cy, W, y), fill=LILAC_L); d.rectangle((0, cy, int(1.4 * K), y), fill=ACC)
            conc(pad + int(3 * K), cy + int(5 * K), W - 2 * pad)
    elif st == 'B':
        y = int(30 * K) + text_block(0, 0, 0, []) - 0
        y = int(28 * K)
        tmp_y = text_block(pad + int(2 * K), y, W - 2 * pad, None, numbered=True) + int(6 * K)
        d.rectangle((0, 0, W, tmp_y), fill=WARM)
        d.text((pad, int(9 * K)), header, font=f_head, fill=ACC); d.line((0, int(24 * K), W, int(24 * K)), fill='#D9C7B4', width=1)
        y = text_block(pad + int(2 * K), y, W - 2 * pad, None, numbered=True) + int(6 * K)
        if concl:
            cy = y; d.rectangle((0, cy, W, cy + len(concl) * int(16 * K) + int(10 * K)), fill=LILAC_L)
            y = conc(pad + int(2 * K), cy + int(5 * K), W - 2 * pad) + int(5 * K)
    elif st == 'C':
        d.text((int(7 * K), int(5 * K)), header, font=f_head, fill=ACC); y = int(20 * K)
        d.rectangle((0, y - int(1.4 * K), W, y), fill=ACC)
        lw = int(W * 3 / 11)
        for title, its in steps:
            ry = y
            ye = text_block(lw + int(7 * K), y + int(5 * K), W - lw - int(14 * K), [(None, its)]) + int(4 * K)
            d.rectangle((0, ry, lw, ye), fill=WARM)
            for ln in wrap(d, title or '', f_step, lw - int(14 * K)):
                d.text((int(7 * K), ry + int(6 * K)), ln, font=f_step, fill=ACC); ry += int(8.8 * K * 1.6)
            for xx in range(0, W, 6): d.point((xx, ye), fill='#B9A898')
            y = ye
        if concl:
            ye = y + len(concl) * int(16 * K) + int(10 * K)
            d.rectangle((0, y, lw, ye), fill=LILAC); d.rectangle((lw, y, W, ye), fill=LILAC_L)
            d.text((int(7 * K), y + int(6 * K)), '결론', font=f_step, fill=INK)
            conc(lw + int(7 * K), y + int(5 * K), W - lw - int(14 * K), prefix=''); y = ye
    elif st == 'D':
        d.rectangle((0, 0, W, int(2 * K)), fill=ACC)
        d.text((int(3 * K), int(7 * K)), header, font=f_head, fill=ACC)
        y = text_block(int(3 * K), int(24 * K), W - int(6 * K), None) + int(5 * K)
        if concl:
            for xx in range(0, W, 5): d.point((xx, y), fill=ACC)
            y = conc(int(3 * K), y + int(5 * K), W - int(6 * K), ACC) + int(5 * K)
        d.rectangle((0, y, W, y + int(2 * K)), fill=ACC); y += int(2 * K)
    elif st == 'E':
        tw = int(W * 2 / 11)
        d.rectangle((0, 0, tw, int(17 * K)), fill=INK)
        hw = d.textlength(header, font=f_head); d.text(((tw - hw) / 2, int(4 * K)), header, font=f_head, fill='white')
        top = int(17 * K)
        y = text_block(pad, top + int(6 * K), W - 2 * pad, None, step_color=INK) + int(5 * K)
        if concl:
            cy = y; ye = cy + len(concl) * int(16 * K) + int(10 * K)
            d.rectangle((0, cy, W - 1, ye), fill=WARM)
            conc(pad, cy + int(5 * K), W - 2 * pad, ACC, prefix='→ '); y = ye
        d.rectangle((0, top, W - 1, y), outline='#C9B8A6')
    elif st in ('E1', 'E2', 'E3', 'E4', 'E5'):
        y = render_e(d, st, header, steps, concl, text_block, conc, pad)
    return im.crop((0, 0, W, y + 2))


def render_e(d, st, header, steps, concl, text_block, conc, pad):
    thin, dotc = '#C9B8A6', '#C9B8A6'
    tab_fill, step_c, conc_fill, conc_c = INK, INK, WARM, ACC
    if st == 'E2':
        tab_fill, step_c, conc_fill, conc_c, thin = ACC, ACC, LILAC_L, INK, '#D9B79A'
    th = int(17 * K)
    if st == 'E5':
        d.rectangle((0, 0, W - 1, th), fill=INK); d.text((pad, int(4 * K)), header, font=f_head, fill='white')
    else:
        tw = int(W * 2 / 11)
        d.rectangle((0, 0, tw, th), fill=tab_fill)
        hw = d.textlength(header, font=f_head); d.text(((tw - hw) / 2, int(4 * K)), header, font=f_head, fill='white')
        if st != 'E4':
            d.line((tw, th, W, th), fill=thin)
    y = text_block(pad, th + int(6 * K), W - 2 * pad, None, step_color=step_c) + int(5 * K)
    if concl:
        cy = y; ye = cy + len(concl) * int(16 * K) + int(10 * K)
        d.rectangle((0, cy, W - 1, ye), fill=conc_fill)
        for xx in range(0, W, 5): d.point((xx, cy), fill=dotc)
        conc(pad, cy + int(5 * K), W - 2 * pad, conc_c, prefix='→ '); y = ye
    if st in ('E1', 'E2'):
        d.rectangle((0, th, W - 1, y), outline=thin)
    elif st == 'E3':
        d.line((0, y, W, y), fill=thin)
    elif st == 'E4':
        d.rectangle((0, th, int(2.8 * K), y), fill=INK)
    elif st == 'E5':
        d.rectangle((0, th, W - 1, y), outline=INK)
    return y


cards = []
for st in STYLES:
    a = render(st, H1, SE.SOL['M6']); b = render(st, H2, SE.SOL['K1'])
    hdr = int(26 * K)
    card = Image.new('RGB', (W + 2 * int(14 * K), hdr + a.height + b.height + int(40 * K)), 'white')
    dd = ImageDraw.Draw(card)
    dd.text((int(14 * K), int(6 * K)), '시안 %s · %s' % (st, NAMES[st]), font=f_title, fill='#111111')
    card.paste(a, (int(14 * K), hdr)); card.paste(b, (int(14 * K), hdr + a.height + int(18 * K)))
    cards.append(card)
cw = cards[0].width
H = sum(c.height for c in cards) + 20 * len(cards)
sheet = Image.new('RGB', (cw, H), '#E9E6E2'); y = 0
for c in cards:
    sheet.paste(c, (0, y)); y += c.height + 20
sheet.save(OUT); print(sheet.size)
