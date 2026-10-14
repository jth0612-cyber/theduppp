# Squeeze 2027 리소스 6종(sq27_*_resources.pdf)에 확정안 03-01-14 D 디자인을 그대로 입힘.
# 각 파일의 쪽 수·크기·순서는 그대로 두고, 바꾼 디자인 요소만 새것으로 갈아 끼운다.
#  · 상단 탭·띠·그러데이션 → 상단 세로 핀(쪽 방향대로)      · 하단 로고 → Squeeze(짝수)/THedu(홀수)
#  · Solving·Linking·Fact Check·Flow Point·빈출 선지 탭 줄 → 파형 D 줄(글자 Space Grotesk, 한글은 Pretendard SemiBold)
#  · 풀이 칸 → 'Logic' 라벨(Cinzel 별색) + 흐린 배경 점      · MEMO 쪽 → 'MEMO' 라벨(Cinzel 별색), 큰 제목 없음
#  · 차례 → 'Contents'(Cinzel) + 원래 선 자리에 P3 선       · Logic Check 쪽·회독 줄 → 새 Logic Check 모양
#  · 회색 띠(105.5×15) → P3 선 / 창작 문항 표식 → 핀 표식 / 그러데이션 가는 띠(110×3) → 가는 핀 줄
#  · 규격 안내 쪽(분홍 안내선·치수)은 안내선·치수·본문 견본은 두고 디자인 요소만 바꿔 같은 자리에 다시 짬
#    (제목 → Diphylleia, 번호 → Barlow Condensed Medium 별색, 출처 → 회색 글자(상자 없음))
#  · O·X 표시, 아이콘(전구·열쇠·말풍선·2nd~5th·화살표 등), 팔각 조각, 재단 틀은 원본 그대로
#  · 그 밖의 글자는 모두 비움. 새로 넣은 라벨 글자는 윤곽선(패스).
# 사용: python sq_res27.py <squeeze.pdf> <release_point_resources.pdf> <sq27 폴더> <출력 폴더>
import sys, os, re
import numpy as np
sys.path.insert(0, '.')
import sq_wave, sq_label10, sq_full, sq_combo20, sq_combo, sq_lib, sq8, sq9, sq7
from sq_lib import P, f, m, R, W, H, S, K, S_, K_
from sq_full import head, p3_head, dots, page_memo, page_logic, draw_fins, PAL, sm
from sq6 import Noise
from sq9 import mix_gray
from sq8 import cap_height
MM = 72 / 25.4
CY = (0, 174, 239)
BLUES = {CY, (0x40, 0x7F, 0xB8), (0x3F, 0x7F, 0xB7), (0xA3, 0xB9, 0xDB)}
rgb = lambda c: c and tuple(round(v * 255) for v in c[:3])

# ── 글자: 새로 쓰는 글자만 별도 층에 써 두었다가 윤곽선으로 얹음 ─────────────────
_text = P.text
def _init(s, page, res=None, dx=0):
    s.p, s.res, s.dx = page, res, dx               # 글꼴은 글자 층에서만 필요(그림 쪽엔 넣지 않음 → 파일 가벼움)
P.__init__ = _init
_fonted = set()
def _font_page(tp):
    if tp.number not in _fonted:
        for k, v in sq_lib.FONTS.items(): tp.insert_font(fontname=k, fontfile=v)
        _fonted.add(tp.number)
TEXT = f.open(); _layer = {}
def text_layer(s, x, y, text, font, size, color, align='l', track=0):
    key = (id(s.p.parent), s.p.number)
    if key not in _layer:
        TEXT.new_page(width=s.p.rect.width, height=s.p.rect.height)
        _layer[key] = (s.p.parent, s.p.number, len(TEXT) - 1)
    tp = TEXT[_layer[key][2]]; _font_page(tp)
    return _text(P(tp), x, y, text, font, size, color, align, track)
P.text = text_layer
SILENT = [False]                                   # True면 글자는 쓰지 않고 폭만 계산(쪽 틀의 쪽번호 등)
def _maybe(s, x, y, text, font, size, color, align='l', track=0):
    if SILENT[0] or text.strip().isdigit() or text in ('기출 2',): return s.width(text, font, size, track)
    return text_layer(s, x, y, text, font, size, color, align, track)
P.text = _maybe

def outline_text(doc):
    for key, (d_, num, tn) in list(_layer.items()):
        if d_ is not doc: continue
        svg = TEXT[tn].get_svg_image(text_as_path=True)
        pdf = f.open('pdf', f.open(stream=svg.encode(), filetype='svg').convert_to_pdf())
        doc[num].show_pdf_page(doc[num].rect, pdf, 0)
        del _layer[key]

# ── 원본 손질 ────────────────────────────────────────────
def redact(page, rects, text=True, mode='covered'):
    """rects(mm) 안의 그림을 지움. mode: covered=완전히 덮인 것만 / touched=닿은 것까지. 이미지는 그대로."""
    if not rects: return
    g = {'covered': f.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED, 'touched': f.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED,
         'none': f.PDF_REDACT_LINE_ART_NONE}[mode]
    groups = [[r] for r in rects] if mode == 'covered' else [rects]     # 겹친 상자끼리는 '덮임' 판정이 안 되어 하나씩
    for grp in groups:
        for r in grp: page.add_redact_annot(R(*r), fill=False)
        page.apply_redactions(images=f.PDF_REDACT_IMAGE_NONE, graphics=g,
                              text=f.PDF_REDACT_TEXT_REMOVE if text else f.PDF_REDACT_TEXT_NONE)

def spans(page):
    return [s for b in page.get_text('dict')['blocks'] for l in b.get('lines', []) for s in l['spans'] if s['text'].strip()]

def is_guide_text(s):
    return 'Montserrat-Thin' in s['font'] and s['color'] in (0x010202, 0x231916, 0x231F20)

def strip_text(page, keep=lambda s: False):
    rs = [tuple(v / MM for v in s['bbox']) for s in spans(page) if not keep(s)]
    redact(page, rs, text=True, mode='none')

def fills(page, color=None, minw=0, maxw=1e9, minh=0, maxh=1e9):
    out = []
    for g in page.get_drawings():
        r = g['rect']; w, h = r.width / MM, r.height / MM
        c_ = rgb(g.get('fill'))
        if (color is None or c_ == color or (isinstance(color, set) and c_ in color)) and minw <= w <= maxw and minh <= h <= maxh:
            out.append(tuple(v / MM for v in r))
    return out

def new_like(doc, page):
    return doc.new_page(width=page.rect.width, height=page.rect.height)

def on_trim(page, ox, oy, draw):
    """262×371 판에 그린 것을 (ox, oy) 자리에 얹음(판 밖은 잘림)."""
    tmp = f.open(); tp = tmp.new_page(width=m(W), height=m(H))
    draw(P(tp, sq8.RES)); outline_text(tmp)
    page.show_pdf_page(R(ox, oy, ox + W, oy + H), tmp, 0)

# ── 새 디자인 요소 ─────────────────────────────────────────
ICON_SRC = {}
def set_icon(kind, page, xmin):
    g = [x for x in page.get_drawings() if x['rect'].x0 > xmin * MM and x.get('color')]
    r = g[0]['rect']
    for x in g[1:]: r |= x['rect']
    items = [it for x in g for it in x['items']]
    sq_full._IC[kind] = (r, items, g[0].get('width', 1.0))

def wave_row(d, word, kind, x0, x1, yc, seed, font=None):
    """파형 D 줄: 글자 | 위아래 단차 핀(가운데 선 정렬) | 아이콘(있으면)."""
    fk = font or sq_full.SOLFONT
    size = 14 * sq_combo.SCALE.get(fk, 1)
    base = yc + 2.4
    capr = cap_height(sq_lib.FONTS[fk]) if fk != 'ps' else 0.70
    mid = base - capr * size * 25.4 / 72 / 2
    wx = x0 + d.text(x0, base, word, fk, 14, S())
    b = x1
    if kind:
        rect = sq_full.icon(kind)[0]; ih = 5.0; iw = rect.width / rect.height * ih
        sq_full.draw_icon(d, kind, x1 - iw, mid - ih / 2, ih); b = x1 - iw - 4.0
    a = wx + 3.5
    r = np.random.default_rng(seed)
    n1, n2 = Noise(seed + 70, 16, dirs=0.3), Noise(seed + 71, 5, dirs=0.5)
    inks = [(p[0], p[1]) for p in PAL]; w = np.array([p[2] for p in PAL], float); w /= w.sum()
    its = []; x = a
    while x <= b:
        env = 1 - 0.6 * float(sm(a, b, x))
        v = 0.6 * float(sm(-0.7, 0.7, n1(x, 0))) + 0.25 * float(sm(-0.7, 0.7, n2(x, 0))) + 0.15 * r.uniform()
        h = max(0.5, 0.5 * round(3.0 * env * v / 0.5))
        ink, t = inks[r.choice(len(inks), p=w)]
        its.append((x, mid - h, mid + h, ink, t)); x += 1.1
    draw_fins(d, mix_gray(its, seed + 2, every=(5, 9)), lambda X, y: 1 - 0.4 * float(sm(a + 10, b, X)), wfin=0.26)

LABEL = dict(font='md', size=10.0)
def frame(d, side):
    head(d, side)
    SILENT[0] = False
    sq_full.foot_default(d, side, 0)

def logic_box(d, bx, pts):
    dots(d, pts); p3_head(d, bx[0], bx[2], bx[1], 'Logic', color=S(), **LABEL)

def box_dots(page, bx):
    pts = [((r[0] + r[2]) / 2, (r[1] + r[3]) / 2) for r in fills(page, maxw=1, maxh=1)]
    return [(x, y) for x, y in pts if bx[0] < x < bx[2] and bx[1] + 3 < y < bx[3]]

def restyle_title(d, s):
    """규격 쪽 제목 → 좌상단 라벨 글꼴(Diphylleia, 먹)로 같은 기준선에."""
    d.text(s['origin'][0] / MM, s['origin'][1] / MM, s['text'].strip(), 'lb', sq_label10.CUR['size'], K(), track=sq_label10.CUR['track'])

def restyle_number(d, s):
    k, sz = sq8.NUMFONT['key'], sq8.NUMFONT['size']
    return text_layer(d, s['origin'][0] / MM, s['origin'][1] / MM, s['text'].strip(), k, sz, S())

def restyle_source(d, s, x=None):
    d.text(x if x is not None else s['bbox'][0] / MM, s['origin'][1] / MM, s['text'].strip(), 'pr', 8.2, K(.68))

# ── 쪽 처리 ───────────────────────────────────────────────
def side_of(page):
    """THedu 로고(오른쪽 아래)면 홀수, Squeeze 로고면 짝수. 로고가 없으면 상단 탭이 오른쪽인지로."""
    logo = [r for r in fills(page, (0x6D, 0x6E, 0x71)) if r[1] > 340]
    if logo:
        n_ = len(logo)
        return 'even' if n_ >= 7 else 'odd'          # Squeeze 로고는 조각 7개 이상, THedu는 5개
    tabs = [r for r in fills(page, CY) if r[1] < 1 and r[3] < 25]
    if tabs: return 'odd' if tabs[0][0] > 60 else 'even'
    return 'even'

def page_frame(page, keep_center=True):
    """쪽 틀: 원본의 가운데 단 구분선만 남기고 새 상단 핀·로고."""
    side = side_of(page)
    centers = [g for g in page.get_drawings() if rgb(g.get('color')) in ((0x23, 0x1F, 0x20), (0x5A, 0x5A, 0x5C))
               and g['rect'].width < 1 and g['rect'].height > 200 * MM]
    out = page.parent; num = page.number
    redact(page, [(-5, -5, W + 5, H + 5)], text=True, mode='touched')
    page = out[num]; d = P(page, sq8.RES)
    if keep_center:
        for g in centers:
            r = g['rect']; d.line(r.x0 / MM, r.y0 / MM, r.x0 / MM, r.y1 / MM, K(), g.get('width') or .5)
    frame(d, side)
    return d, side

def main_pdf(src, res, path, out):
    """sq27_main_resources"""
    d0 = f.open(path); new = f.open(); new.insert_pdf(d0)
    set_icon('Fact Check', d0[37], 95); set_icon('Solving', d0[38], 95); set_icon('Linking', d0[46], 95)
    log = []
    for i in range(len(new)):
        pg = new[i]; n = i + 1; w = pg.rect.width / MM
        if n in (1, 2): spec_flow(pg, n); log.append((n, '기출 FLOW 규격: 머리 띠 → 상단 핀 + 제목 Diphylleia, Flow Point·빈출 선지 탭 → 파형 줄'))
        elif n in (10, 11): spec_problem(pg, n); log.append((n, '문항 규격: 머리 탭 → 상단 핀, 제목·번호·출처 새 글꼴, Linking·Solving·Fact Check → 파형 줄'))
        elif n in (3, 4, 5, 12, 13, 46): page_frame(pg, keep_center=False); log.append((n, '쪽 틀 → 상단 핀 + 로고'))
        elif n in (6, 7):
            word = 'Flow Point' if n == 6 else '빈출 선지'
            redact(pg, [(-1, -1, w + 1, 10)], True, 'touched'); pg = new[i]
            wave_row(P(pg, sq8.RES), word, None, 0, w, 4.25, 60 + n, font=None if n == 6 else 'ps'); log.append((n, f'{word} 탭 → 파형 줄'))
        elif n in (38, 39, 47):
            kind = {38: 'Fact Check', 39: 'Solving', 47: 'Linking'}[n]
            yc = {38: 3.7, 39: 9.7, 47: 3.85}[n]
            redact(pg, [(-1, -1, w + 1, pg.rect.height / MM + 1)], True, 'touched'); pg = new[i]
            wave_row(P(pg, sq8.RES), kind, kind, 0, 108, yc, 40 + n); log.append((n, f'{kind} 줄 → 파형 D'))
        elif 40 <= n <= 44:
            bx = [tuple(v / MM for v in g['rect']) for g in pg.get_drawings() if (g.get('width') or 0) > 1.9][0]
            pts = box_dots(pg, bx)
            redact(pg, [(-5, -5, W + 5, H + 5)], True, 'touched'); pg = new[i]
            logic_box(P(pg, sq8.RES), bx, pts); log.append((n, f'풀이 칸 → Logic 라벨(높이 {bx[3] - bx[1]:.0f}mm)'))
        elif n == 61:
            redact(pg, [(-5, -5, W + 5, H + 5)], True, 'touched'); pg = new[i]
            logic_page(pg); log.append((n, 'Logic Check 쪽 → 새 Logic Check'))
        else: log.append((n, '원본 그대로(아이콘·표시)'))
        outline_text(new)
    return new, log

def logic_page(pg):
    d = P(pg, sq8.RES)
    head(d, 'even')
    d.text(19, 52, 'Logic Check', 'md', 28, K())
    sq8.fin_stack(d, 19.3, 57.4, [(2.6, S_, 1), (2.2, S_, .45)], w=0.5)
    d.line(19, 63, 112, 63, K(.35), .25)
    d.line(128, 40, 128, 347, K(.25), .25)
    d.line(136, 39.6, 243, 39.6, K(.6), .3)
    SILENT[0] = False; sq_full.foot_default(d, 'even', 0)

def check_row(pg, w):
    """회독 줄(112×10) → 둥근 네모 두 개(별색 선) + 아래 가는 선."""
    d = P(pg, sq8.RES)
    for j in range(2):
        bx = w - 10.6 + j * 5.4
        d.rect(bx, 3.4, bx + 3.6, 7.0, None, S(), .4, radius=.3)
    d.line(0, 9.6, w, 9.6, K(.14), .25)

def spec_flow(pg, n):
    """main 1·2: 기출 FLOW 규격 쪽."""
    ox, oy = (18, 14.5) if n == 1 else (0, 14.5)
    side = 'even' if n == 1 else 'odd'
    sp = spans(pg)
    title = [s for s in sp if s['size'] > 20 and not is_guide_text(s)]
    blue = (0x40, 0x7F, 0xB8)
    head_r = [r for r in fills(pg, blue) if r[1] <= oy + 0.5 and r[3] <= oy + 31]
    tab = [r for r in fills(pg, blue) if 7 < r[3] - r[1] < 10 and r[1] > 200][0]
    line = [tuple(v / MM for v in g['rect']) for g in pg.get_drawings() if rgb(g.get('color')) == blue and abs(g['rect'].y0 - tab[1] * MM - (tab[3] - tab[1]) / 2 * MM) < 2 * MM and g['rect'].height < 1]
    word = 'Flow Point' if n == 1 else '빈출 선지'
    rs = list(head_r) + [tab] + line + [tuple(v / MM for v in s['bbox']) for s in sp if s in title or (s['bbox'][1] / MM > tab[1] - 1 and s['bbox'][3] / MM < tab[3] + 1)]
    redact(pg, [(r[0] - 1, r[1] - 1, r[2] + 1, r[3] + 1) for r in rs], True, 'covered')
    pg = pg.parent[pg.number]
    on_trim(pg, ox, oy, lambda d: head(d, side))
    d = P(pg, sq8.RES)
    for s in title:
        d.text(s['origin'][0] / MM, oy + 29.0, s['text'].strip(), 'lb', 22, K(), track=sq_label10.CUR['track'])
    x1 = max(l[2] for l in line) if line else tab[2] + 180
    wave_row(d, word, None, tab[0], x1, (tab[1] + tab[3]) / 2, 70 + n, font=None if n == 1 else 'ps')

def spec_problem(pg, n):
    """main 10·11 / pro 1·2: 문항 규격 쪽. 안내선·견본 본문은 두고 디자인 요소만 바꿈."""
    doc = pg.parent; num = pg.number
    sp = spans(pg)
    title = [s for s in sp if 'Bold' in s['font'] and s['size'] >= 17 and '탐사' in s['text']]
    numbers = [s for s in sp if 'Montserrat-Thin' in s['font'] and s['color'] not in (0x010202, 0x231916, 0x231F20) and s['size'] > 30]
    sources = [s for s in sp if s['color'] == 0xFFFFFF and '학년도' in s['text']]
    head_tab = [r for r in fills(pg) if r[3] - r[1] < 5 and (r[3] - r[1]) > 3 and r[2] - r[0] > 10 and r[1] < 30]
    chips = [r for r in fills(pg, (0x93, 0x95, 0x98)) if r[3] - r[1] < 7]
    tabs = [r for r in fills(pg, BLUES) if 6.5 < r[3] - r[1] < 9 and 20 < r[2] - r[0] < 40]
    # 탭 줄의 선·아이콘·탭 글자(흰 윤곽)
    row_items = []
    for t in tabs:
        cy = (t[1] + t[3]) / 2
        for g in pg.get_drawings():
            r = tuple(v / MM for v in g['rect'])
            if abs((r[1] + r[3]) / 2 - cy) < 4.5 and r[0] >= t[0] - .5 and r[2] - r[0] < 140 and (r[3] - r[1]) < 9:
                if rgb(g.get('fill')) in BLUES | {(255, 255, 255)} or rgb(g.get('color')) in BLUES: row_items.append(r)
    rows = []
    for t in sorted(tabs, key=lambda r: (r[0], r[1])):
        cy = (t[1] + t[3]) / 2
        ends = [r[2] for r in row_items if abs((r[1] + r[3]) / 2 - cy) < 4.5 and r[0] > t[0]]
        rows.append((t, max(ends) if ends else t[2] + 80))
    # 종류: 폭 30mm 넘으면 Fact Check, 같은 단에서 위가 Linking·아래가 Solving
    kinds = []
    for t, x1 in rows:
        if t[2] - t[0] > 30: kinds.append('Fact Check')
        else:
            same = sorted([r for r, _ in rows if abs(r[0] - t[0]) < 2 and r[2] - r[0] <= 30], key=lambda r: r[1])
            kinds.append('Linking' if len(same) > 1 and t == same[0] else 'Solving')
    rs = head_tab + chips + row_items + [t for t, _ in rows]
    rs += [tuple(v / MM for v in s['bbox']) for s in title + numbers + sources]
    redact(pg, [(r[0] - 1, r[1] - 1, r[2] + 1, r[3] + 1) for r in rs], True, 'covered')
    pg = doc[num]
    # 판 원점: 분홍 안내선 가운데 가장 왼쪽·위
    ox, oy = trim_origin(pg)
    side = 'even' if (title and title[0]['origin'][0] / MM - ox < 100) else 'odd'
    on_trim(pg, ox, oy, lambda d: head(d, side))
    d = P(pg, sq8.RES)
    for s in title: restyle_title(d, s)
    for s in numbers:
        wd = restyle_number(d, s)
    for s in sources:
        chip = [c for c in chips if c[0] <= s['bbox'][0] / MM <= c[2]]
        restyle_source(d, s, x=chip[0][0] if chip else None)
    for (t, x1), kind in zip(rows, kinds):
        wave_row(d, kind, kind, t[0], x1, (t[1] + t[3]) / 2, 90 + int(t[1]))

def trim_origin(pg):
    gs = [g['rect'] for g in pg.get_drawings() if rgb(g.get('color')) in ((0xD3, 0x26, 0x7F), (0xD5, 0x28, 0x7F), (0xEC, 0x00, 0x8C))]
    labels = {s['text'].strip(): s for s in spans(pg) if is_guide_text(s)}
    vs = sorted({round(r.x0 / MM, 1) for r in gs if r.width < 1}); hs = sorted({round(r.y0 / MM, 1) for r in gs if r.height < 1})
    # '0' 표시가 있는 안내선을 원점으로, 없으면 치수 표시 하나로 역산
    ox = oy = None
    for v in vs:
        for t, s in labels.items():
            try: val = float(t)
            except ValueError: continue
            if abs(s['bbox'][1] / MM - min(l['bbox'][1] / MM for l in labels.values())) < 3 and abs((s['bbox'][0] + s['bbox'][2]) / 2 / MM - v) < 4:
                ox = v - val; break
        if ox is not None: break
    for h in hs:
        for t, s in labels.items():
            try: val = float(t)
            except ValueError: continue
            if abs((s['bbox'][1] + s['bbox'][3]) / 2 / MM - h) < 4 and (s['bbox'][0] / MM < 25 or s['bbox'][0] / MM > pg.rect.width / MM - 25):
                oy = h - val; break
        if oy is not None: break
    return ox or 0, oy or 0

def pro_pdf(src, res, path, out):
    d0 = f.open(path); new = f.open(); new.insert_pdf(d0); log = []
    for i in range(len(new)):
        pg = new[i]; n = i + 1; w = pg.rect.width / MM; h = pg.rect.height / MM
        if n in (1, 2): spec_problem(pg, n); log.append((n, '문항 규격: 머리 탭 → 상단 핀, 제목·번호·출처 새 글꼴'))
        elif n in (3, 4): page_frame(pg); log.append((n, '쪽 틀 → 상단 핀 + 로고(가운데 단 구분선 유지)'))
        elif n == 5:
            redact(pg, [(-5, -5, W + 5, H + 5)], True, 'touched'); pg = new[i]
            memo_page(pg); log.append((n, 'MEMO 쪽 → MEMO 라벨(Cinzel 별색) + 흐린 점'))
        elif n == 6:
            sp = spans(pg); src_s = [s for s in sp if s['color'] == 0xFFFFFF]
            chip = fills(pg, (0x93, 0x95, 0x98))
            redact(pg, chip + [tuple(v / MM for v in s['bbox']) for s in src_s], True, 'covered'); pg = new[i]
            d = P(pg, sq8.RES)
            for s in src_s: restyle_source(d, s, x=chip[0][0] if chip else None)
            log.append((n, '출처 규격: 회색 상자 없이 회색 글자'))
        elif n == 7:
            redact(pg, [(-1, -1, w + 1, h + 1)], True, 'touched'); pg = new[i]
            sq8.fin_stack(P(pg, sq8.RES), 0.6, 0.0, [(2.6, S_, 1), (2.2, S_, .45)], w=0.5); log.append((n, '창작 문항 표식 → 핀 표식'))
        elif n == 8:
            redact(pg, [(-1, -1, w + 1, h + 1)], True, 'touched'); pg = new[i]
            sq7.fin_row(P(pg, sq8.RES), 1, w - 1, 0.0, 2.6, 0.8, 19); log.append((n, '그러데이션 가는 띠 → 가는 핀 줄'))
        elif n == 11:
            redact(pg, [(-5, -5, W + 5, H + 5)], True, 'touched'); pg = new[i]
            logic_page(pg); log.append((n, 'Logic Check 쪽 → 새 Logic Check'))
        elif n == 12:
            redact(pg, [(-1, -1, w + 1, h + 1)], True, 'touched'); pg = new[i]
            check_row(pg, w); log.append((n, '회독 줄 → 둥근 네모 두 개 + 가는 선'))
        else: log.append((n, '원본 그대로(아이콘)'))
        outline_text(new)
    return new, log

MEMO_DOTS = None
def memo_page(pg):
    global MEMO_DOTS
    if MEMO_DOTS is None:
        sp = sq9.SRC_DOC[24]; box = sq_full.find_note(sp)
        MEMO_DOTS = [p for p in sq_full.find_dots(sp, box) if p[1] > 62]
    d = P(pg, sq8.RES)
    head(d, 'odd')
    p3_head(d, 19, 243, 60, 'MEMO', color=S(), **LABEL)
    dots(d, MEMO_DOTS)
    SILENT[0] = False; sq_full.foot_default(d, 'odd', 0)

def sol_pdf(src, res, path, out):
    d0 = f.open(path); new = f.open(); new.insert_pdf(d0); log = []
    for i in range(len(new)):
        pg = new[i]; n = i + 1; w = pg.rect.width / MM; h = pg.rect.height / MM
        if n in (1, 2):
            d, side = page_frame(pg)
            p3_head(d, 19, 243, 22, ''); log.append((n, '정답 및 해설 쪽 → 상단 핀 + 제목 자리 P3 선 + 로고(가운데 단 구분선 유지)'))
        elif n == 3:
            redact(pg, [(-1, -1, w + 1, h + 1)], True, 'touched'); pg = new[i]
            p3_head(P(pg, sq8.RES), 0, w, 10.0, ''); log.append((n, '회색 띠 → P3 선'))
        elif n == 25:
            sp = spans(pg); body = [s for s in sp if not is_guide_text(s)]
            box = [r for r in fills(pg) if r[2] - r[0] > 50]; tab = [r for r in fills(pg) if 10 < r[2] - r[0] < 20]
            redact(pg, box + tab + [tuple(v / MM for v in s['bbox']) for s in body], True, 'covered'); pg = new[i]
            d = P(pg, sq8.RES); b = box[0]
            no = [s for s in body if s['text'].strip().isdigit()]; wd_ = [s for s in body if not s['text'].strip().isdigit()]
            p3_head(d, b[0], b[2], b[3], '')
            x = b[0] + 2.4
            if no: x += text_layer(d, x, b[3] - 2.0, no[0]['text'].strip(), sq8.NUMFONT['key'], 12, S()) + 2.0
            for s in wd_: x += text_layer(d, x, b[3] - 2.0, s['text'].strip(), 'ps', 11, K())
            log.append((n, '별표 규격: 회색 상자 → P3 선 + 번호(Barlow 별색)·제목'))
        elif n == 26:
            sp = spans(pg); body = [s for s in sp if not is_guide_text(s) and s['text'].strip() not in '①②③④⑤']
            redact(pg, [tuple(v / MM for v in s['bbox']) for s in body], True, 'none'); pg = new[i]
            d = P(pg, sq8.RES)
            for s in body:
                t = s['text'].strip(); x, y = s['origin'][0] / MM, s['origin'][1] / MM
                if t.isdigit(): text_layer(d, x, y, t, sq8.NUMFONT['key'], 17 * 0.9, S())
                else: text_layer(d, x, y, t.replace('②', '').strip(), 'pm', 9.5, S());
            log.append((n, '정답 번호 규격: 번호 Barlow 별색, 글자 Pretendard'))
        else: log.append((n, '원본 그대로(아이콘·규격)'))
        outline_text(new)
    return new, log

def toc_pdf(src, res, path, out):
    d0 = f.open(path); new = f.open(); new.insert_pdf(d0); log = []
    for i in range(len(new)):
        pg = new[i]; n = i + 1; w = pg.rect.width / MM; h = pg.rect.height / MM
        if n == 1:
            gray = [r for r in fills(pg, (0xDC, 0xDD, 0xDE)) if r[2] - r[0] > 50]
            redact(pg, [(r[0] - 1, r[1] - 1, r[2] + 1, r[3] + 1) for r in gray] + [(108, 300, 130, 312.5)], True, 'covered'); pg = new[i]; strip_text(pg); pg = new[i]
            d = P(pg, sq8.RES); head(d, 'odd')
            sq8.fin_stack(d, 19.3, 30.0, [(2.6, S_, 1), (2.2, S_, .45)], w=0.5)
            d.line(92, 36, 92, 340, K(.2), .25)
            log.append((n, '시작하기에 앞서 → 상단 핀 + 핀 표식 + 세로 선, 회색 단 없앰, 글자 비움(아이콘·구분선 유지)'))
        elif n in (3, 4, 5, 9):
            has_title = any(s['text'].strip() == 'Contents' for s in spans(pg))
            lines = [g['rect'].y0 / MM for g in pg.get_drawings() if rgb(g.get('color')) == CY and g['rect'].x0 / MM > 70]
            redact(pg, [(-5, -5, W + 5, H + 5)], True, 'touched'); pg = new[i]
            d = P(pg, sq8.RES); head(d, 'even')
            if has_title: text_layer(d, 19, 52, 'Contents', 'md', 30, K())
            for y in lines: p3_head(d, 80, 220, y, '')
            log.append((n, f'차례 → 상단 핀{" + Contents(Cinzel)" if has_title else ""} + 원래 선 자리에 P3 선 {len(lines)}개'))
        elif n in (6, 8, 10):
            lines = [g['rect'].y0 / MM for g in pg.get_drawings() if rgb(g.get('color')) == CY]
            redact(pg, [(-1, -1, w + 1, h + 1)], True, 'touched'); pg = new[i]
            d = P(pg, sq8.RES)
            for y in lines: p3_head(d, 80, 220, max(y, 6.0), '')
            log.append((n, '차례 항목 머리 → P3 선(글자 비움)'))
        elif n in (7, 11):
            strip_text(pg); log.append((n, '글자 비움(로고·도형 유지)'))
        else: log.append((n, '원본 그대로'))
        outline_text(new)
    return new, log

def ans_pdf(src, res, path, out):
    d0 = f.open(path); new = f.open(); new.insert_pdf(d0); log = []
    for i in range(len(new)):
        pg = new[i]; n = i + 1; w = pg.rect.width / MM; h = pg.rect.height / MM
        if n == 2:
            redact(pg, [(-5, -5, W + 5, H + 5)], True, 'touched'); pg = new[i]
            head(P(pg, sq8.RES), 'even'); log.append((n, '빠른 정답 쪽 → 상단 핀(회색 바탕·탭 없앰, 글자 비움)'))
        elif n in (3, 4, 5):
            redact(pg, [(-1, -1, w + 1, h + 1)], True, 'touched'); pg = new[i]
            d = P(pg, sq8.RES)
            col = {3: (S_, 1), 4: (S_, .45), 5: (K_, .45)}[n]
            d.line(0, 8.7, w, 8.7, K(.35), .25)
            sq8.fin_stack(d, 0.3, 3.1, [(2.6, col[0], col[1]), (2.2, col[0], col[1] * .45)], w=0.5)
            log.append((n, '단원 탭 → P3 선(핀 표식 색만 별색/연한 별색/먹)'))
        elif n in (6, 7, 8):
            redact(pg, [(-1, -1, w + 1, h + 1)], True, 'touched'); pg = new[i]
            P(pg, sq8.RES).line(0, 10.5, w, 10.5, K(.1), .25)
            log.append((n, '번호 네모 → 없음(번호는 별색 글자), 줄 구분 가는 선'))
        else: log.append((n, '원본 그대로'))
        outline_text(new)
    return new, log

def off_pdf(src, res, path, out):
    d0 = f.open(path); new = f.open(); new.insert_pdf(d0)
    return new, [(1, '원본 그대로(재단 틀, 디자인 요소 없음)')]

JOBS = [('sq27_main_resources.pdf', main_pdf), ('sq27_pro_resources.pdf', pro_pdf), ('sq27_sol_resources.pdf', sol_pdf),
        ('sq27_toc_resources.pdf', toc_pdf), ('sq27_ans_resources.pdf', ans_pdf), ('sq27_off_resources.pdf', off_pdf)]

if __name__ == '__main__':
    SRC, RESP, IND, OUTD = sys.argv[1:5]
    os.makedirs(OUTD, exist_ok=True)
    sq_combo20.setup('11'); sq_label10.setup('17')
    src = f.open(SRC); res = f.open(RESP); sq8.RES = res; sq9.SRC_DOC = src
    sq8.set_numfont('fs/ttf/barlow-condensed-500.ttf')
    which = sys.argv[5:]
    for name, fn in JOBS:
        if which and not any(w in name for w in which): continue
        new, log = fn(src, res, f'{IND}/{name}', OUTD)
        out = f'{OUTD}/{name.replace(".pdf", "_03-01-14D.pdf")}'
        new.subset_fonts(); new.save(out, garbage=4, deflate=True)
        with open(out.replace('.pdf', '_목록.txt'), 'w') as fp:
            for n, desc in log: fp.write(f'{n:>2}쪽: {desc}\n')
        print(len(new), 'pages ->', out, flush=True)
