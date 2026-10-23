"""LOGIC BUILD 단원 원고용 확장 — 사용자의 생성기(_생성스크립트/build.py) 위에 얹어 쓴다.

추가하는 것
- 인라인 마크업: ⟦수식|폭|높이⟧(크기 지정 수식), ⟪그림경로|폭|높이⟫(글자처럼 넣는 작은 그림), _{아래첨자}
- 블록: center(가운데 줄), figure(가운데 그림 줄), mini(그림·표가 들어가는 Mini 예제), kice(Arranged KICE)
- 자동 쪽 나누기: 블록마다 높이를 어림해서 한 쪽(본문 단·날개 단)이 넘치지 않게 pages 목록을 만든다.
  (한글 렌더러가 없어 실제 높이를 잴 수 없으므로, 17-27안 미리보기에서 잰 값으로 넉넉하게 어림한다)
"""
import os, re, sys, math

GEN = os.environ.get('LB_GEN', '/home/user/theduppp/nas/Logic Build/_생성스크립트')
sys.path.insert(0, GEN)
from unit_common import *            # noqa: F401,F403  (build의 블록 함수들)
from styles_more import theme as _theme, point as _point
import build as B
from PIL import Image

HP = B.NS
HC = '{http://www.hancom.co.kr/hwpml/2011/core}'
COL_W = 31000          # 그림의 기본 최대 폭 (HWPUNIT). 원고 크기보다 키우지는 않는다
FULL_W = 46205         # 1단 전체 폭 (쪽 폭 61228 − 좌 7937 − 우 7086)
WIDE = 46205 / 32570   # 예전 본문 단 대비 넓어진 비율

# ---------------------------------------------------------------- 글자 모양: 아래첨자 지원
_orig_cpr_xml = B.cpr_xml


def _cpr_xml(h):
    out = _orig_cpr_xml(h)
    for (base, mods), i in B.NEWCPR.items():
        if dict(mods).get('sub'):
            out = re.sub(r'(<hh:charPr id="%s".*?)</hh:charPr>' % i,
                         lambda m: m.group(1) + ('<hh:subscript/>' if '<hh:subscript/>' not in m.group(1) else '') + '</hh:charPr>',
                         out, count=1, flags=re.S)
    return out


B.cpr_xml = _cpr_xml


# ---------------------------------------------------------------- 인라인
def eq_sized(script, w=None, h=None, unit='1100'):
    e = B.eq(script, unit)
    sz = e.find(HP + 'sz')
    if w: sz.set('width', str(w))
    if h: sz.set('height', str(h))
    return e


def img_size(path):
    if path.lower().endswith('.emf'):
        return None
    return Image.open(path).size


def pic_elem(path, w, h):
    iid = B.add_image(path)
    return B.pic(iid, int(w), int(h))


TOK = re.compile(r'(\^\{[^}]*\}|_\{[^}]*\}|⟦[^⟧]*⟧|⟪[^⟫]*⟫)')


def _inline(text, cpr):
    out = []
    for sp in TOK.split(text):
        if not sp:
            continue
        if sp.startswith('^{') or sp.startswith('_{'):
            c = B.cp(cpr, sup=True) if sp[0] == '^' else B.cp(cpr, sub=True)
            r = B.E('run', charPrIDRef=c); t = B.E('t'); t.text = sp[2:-1]; r.append(t); out.append(r)
            continue
        r = B.E('run', charPrIDRef=cpr)
        if sp.startswith('⟦'):
            sc, *wh = sp[1:-1].split('|')
            r.append(eq_sized(sc, *(int(x) for x in wh)))
        elif sp.startswith('⟪'):
            path, w, h = sp[1:-1].split('|')
            r.append(pic_elem(path, w, h)); r.append(B.E('t'))
        else:
            t = B.E('t'); t.text = sp; r.append(t)
        out.append(r)
    return out


B.inline = _inline


# ---------------------------------------------------------------- 높이 어림 (pt)
def ems(s):
    """한 줄 폭을 '글자 너비(em)'로 어림. 수식·그림은 지정 폭으로."""
    total = 0.0
    for tok in TOK.split(re.sub(r'«[^»]*»|==|\*\*|~~', '', s)):
        if not tok:
            continue
        if tok.startswith('⟦') or tok.startswith('⟪'):
            parts = tok[1:-1].split('|')
            total += (int(parts[1]) / 100 / 11 if len(parts) > 1 else 3)
            continue
        if tok[0] in '^_':
            total += 0.6 * len(tok[2:-1]); continue
        for ch in tok:
            o = ord(ch)
            if 0xAC00 <= o <= 0xD7A3 or 0x3131 <= o <= 0x318E or ch in '㉠㉡㉢㉣①②③④⑤ⅠⅡⅢ':
                total += 1.0
            elif ch == ' ':
                total += 0.32
            elif ch in '.,:;\'"‘’“”()[]·':
                total += 0.4
            else:
                total += 0.6
    return total


def nlines(s, per_line):
    return max(1, math.ceil(ems(s) / per_line))


def notes_of(s):
    return []          # 날개 단(각주)을 쓰지 않는다


_orig_runs = B.runs


def _runs(markup, cpr, ref=True):
    return _orig_runs(re.sub(r'«[^»]*»', '', markup), cpr, ref)


B.runs = _runs


class Block:
    def __init__(self, make, h, notes=(), brk=False, keep_next=False):
        self.make, self.h, self.notes, self.brk, self.keep_next = make, h, list(notes), brk, keep_next


def _b(make, h, *texts, **kw):
    ns = [n for t in texts for n in notes_of(t)]
    return Block(make, h, ns, **kw)


# ---------------------------------------------------------------- 블록 (높이와 함께)
LINE_NOTE, PER_NOTE = 18.5, 27 * WIDE      # 손글씨 본문 줄 간격, 한 줄 em (1단 전체 폭)
LINE_BOX, PER_BOX = 16.8, 28.5 * WIDE      # 풀이 상자
LINE_Q, PER_Q = 13.6, 38 * WIDE            # 문제(8pt)
LINE_CF, PER_CF = 17.6, 26 * WIDE          # Intro·예)·한 줄 정리 상자


def note(s): return _b(lambda: B.note(s), LINE_NOTE * nlines('→ ' + s, PER_NOTE) + 1, s)
def sub(s): return _b(lambda: B.sub(s), LINE_NOTE * nlines('     - ' + s, PER_NOTE) + 1, s)
def plain(s): return _b(lambda: B.ex(s), LINE_NOTE * nlines(s, PER_NOTE) + 1, s)
def tip(s): return _b(lambda: B.tip(s), LINE_NOTE * nlines('TIP ' + s, PER_NOTE - 2) + 4, s)
def cf(s, label='cf.'): return _b(lambda: B.cf(s, label), LINE_CF * nlines(label + ' ' + s, PER_CF) + 24, s)
def blank(): return Block(B.blank, 18)
def fit_h(title, avail_pt, h_max):
    """제목이 avail_pt 폭 한 줄에 들어가는 글자 크기(HWPUNIT, 1/100pt)"""
    return int(min(h_max, avail_pt * 100 / max(1.0, ems(title) * 1.04)) // 25 * 25)


_WOOD = os.path.join(GEN, 'wood_band_light.jpg')
_CRACK = ('SOLID', '0.25 mm', '#3A241D')


LABEL_W = 9000          # THEME/POINT 라벨 칸 폭 (같게 해서 제목 글자 시작 위치를 세로로 맞춘다)
POINT_W = 44935         # POINT 줄 폭 (P[93] 문단에서 시작)
THEME_W = FULL_W - 532  # THEME 막대: 왼쪽 = POINT 점선 왼쪽 끝(P[93] 첫 줄 시작 532), 오른쪽 = 본문 오른쪽 끝


def theme_el(n, title, en=''):
    """우드 THEME 막대. POINT와 같은 문단 위치·같은 라벨 칸 폭, 제목은 한 줄에 맞춘다"""
    st = B.STYLE
    body = B.bfc('t2', img=B.add_image(_WOOD), bottom=_CRACK)
    c1 = B.inline('THEME %02d' % n, B.LABEL(800, '#3A241D', 25, 8))
    h = fit_h(title, (THEME_W - LABEL_W) / 100 - 22, 1450)
    c2 = B.styled(title, B.cp('20', font=st.get('title_font', B.HAND), h=h, spacing=0, color=st['ink'], bold=st.get('title_bold', False)))
    return B.bar_table([(LABEL_W, B.bfc('t1', fill='#D7A77E', bottom=_CRACK), c1, 'C'), (THEME_W - LABEL_W, body, c2, 'L')],
                       1900, width=THEME_W, proto_i=93)


def point_el(n, title):
    """POINT 줄: 라벨 칸(나비 + POINT 01) | 제목 칸, 갈색 점선 밑줄"""
    st = B.STYLE
    h = fit_h(title, (POINT_W - LABEL_W) / 100 - 22, 1200)
    t = B.styled(title, B.cp('22', font=st.get('title_font', B.HAND), h=h, spacing=0, bold=st.get('point_bold', True), color='#111111'))
    bw = st.get('bowtie', ('bowtie_h.png', 1450, 786))
    icon = B.pic_run(B.add_image(os.path.join(GEN, bw[0])), bw[1], bw[2])
    lab = icon + B.inline('  POINT %02d' % n, B.LABEL(800, '#A9623A', 20, 8))
    dash = ('DASH', '0.3 mm', '#C9986C')
    return B.bar_table([(LABEL_W, B.bfc('p1', bottom=dash), lab, 'L'), (POINT_W - LABEL_W, B.bfc('p1', bottom=dash), t, 'L')],
                       1350, width=POINT_W, proto_i=93, bottom_gap=480)


def theme(n, title): return Block(lambda: theme_el(n, title), 40, keep_next=True)
def point(n, title): return Block(lambda: point_el(n, title), 26, keep_next=True)
def h(s): return Block(lambda: B.h1(re.sub(r'==|\*\*|~~', '', s)), 26, keep_next=True)      # 소제목 (틀의 ① 소제목 문단)
def bar(num, title): return Block(lambda: B.bar(num, title), 44, brk=True, keep_next=True)


def center(markup):
    """가운데 반응식 줄 (E14-B: 식 길이에 맞춘 옅은 띠)"""
    return _b(lambda: LK().center_p(markup, ems(markup) * 11), LINE_NOTE * nlines(markup, PER_NOTE) + 18, markup)


def key(s, label='핵심'):
    """핵심 문장 상자 (원고의 굵은 글씨 상자)"""
    return cf(s, label)


def fit(items, max_w=COL_W, gap=600):
    """[(경로, 폭, 높이)] → 한 줄에 들어가도록 같은 비율로 줄인 크기"""
    tot = sum(w for _, w, _ in items) + gap * (len(items) - 1)
    k = min(1.0, max_w / tot)
    return [(p, int(w * k), int(h * k)) for p, w, h in items], k


def figure_para(items, max_w=COL_W):
    items, _ = fit(items, max_w)
    p = B.clone(B.P[1]); p.set('paraPrIDRef', '1')
    for r in p.findall(HP + 'run'):
        p.remove(r)
    for i, (path, w, h) in enumerate(items):
        if i:
            r = B.E('run', charPrIDRef='0'); t = B.E('t'); t.text = '   '; r.append(t); p.append(r)
        r = B.E('run', charPrIDRef='0'); r.append(pic_elem(path, w, h)); r.append(B.E('t')); p.append(r)
    return p


def figure_h(items, max_w=COL_W):
    items, _ = fit(items, max_w)
    return max(h for _, _, h in items) / 100 + 14


def figure(*items, max_w=COL_W):
    """items: (경로, 폭, 높이) — 원고에 놓인 크기(HWPUNIT). 넓으면 본문 폭에 맞춰 줄인다."""
    return Block(lambda: figure_para(list(items), max_w), figure_h(list(items), max_w))


def table(rows, widths=None):
    hs = []
    for ri, row in enumerate(rows):
        ws = widths or [1] * len(row)
        tot = sum(ws)
        hs.append(max(nlines(c, max(4, 46 * WIDE * w / tot)) for c, w in zip(row, ws)))
    h = sum(14 + 11 * (n - 1) for n in hs) + 30
    ns = [n for row in rows for c in row for n in notes_of(c)]
    return Block(lambda: B.table(rows, widths), h, ns)


# ---------------------------------------------------------------- Mini 예제 / Arranged KICE
def LK():
    import look
    return look


def _qpara(s):
    return B.question(s)


import solbox as SB
SOLS = {'SOL': {}, 'ANS': {}, 'QS': {}}     # 다시 쓴 풀이 (sol_*.py) — 키 'M3', 'K2' 등


def use_solutions(mod):
    SOLS.update(SOL=mod.SOL, ANS=getattr(mod, 'ANS', {}), QS=getattr(mod, 'QS', {}))


def _sol_block(header, key, sol, keep):
    lines = SOLS['SOL'].get(key) or _clean(sol)
    return Block(lambda: SB.box(header, lines), SB.height(lines), keep_next=keep)


def _clean(lines):
    return [re.sub(r'\*\*', '', x) for x in lines]


def mini(n, q, sol, ans, pt='Point 1', figs=(), q_after=(), tables=(), fig_w=COL_W):
    """q: 발문(문자열 또는 줄 목록), figs: 그림 줄 목록 [ [(경로,w,h),...], ... ], q_after: 그림 뒤 발문 줄,
    tables: 발문 사이에 넣을 표 [(rows, widths)], sol: 풀이 줄, ans: 정답(None이면 생략)"""
    qs = [q] if isinstance(q, str) else list(q)
    qa = list(q_after)
    sol = _clean(sol)
    blocks = []
    h_head = 18 + sum(LINE_Q * nlines(x, PER_Q) for x in qs) + 6
    makes = [lambda: B.small_bar(f'Mini 예제 {n}')] + [(lambda x=x: LK().question(x)) for x in qs]
    blocks.append(Block(lambda ms=makes: [m() for m in ms], h_head, [m for x in qs for m in notes_of(x)], keep_next=True))
    for f in figs:
        blocks.append(Block(lambda f=f: figure_para(f, fig_w), figure_h(f, fig_w), keep_next=True))
    for rows, widths in tables:
        tb = table(rows, widths); tb.keep_next = True; blocks.append(tb)
    if qa:
        blocks.append(Block(lambda: [LK().question(x) for x in qa], sum(LINE_Q * nlines(x, PER_Q) for x in qa) + 4,
                            [m for x in qa for m in notes_of(x)], keep_next=True))
    blocks.append(_sol_block('Sol.', 'M%d' % n, sol, False))
    blocks.append(Block(B.blank, 22))
    return blocks


KICE_SOL = 'Essentials'     # Arranged KICE 풀이 상자 이름 (예전 '적용 풀이')
KICE_SCALE = 0.7      # 기출 문항 그림은 LOGIC BUILD 1에 넣던 크기의 70%


KICE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'img', 'kice')
try:
    import json as _json
    KICE_IMG = _json.load(open(os.path.join(KICE_DIR, 'index.json'), encoding='utf-8'))   # 원고 그림 경로 끝부분 → 썸네일 그림
except FileNotFoundError:
    KICE_IMG = {}


def kice(n, qs, fig, sol, ans=None, logic=None, fig_w=None, label='Arranged KICE'):
    """Arranged KICE: 다시 묶은 질문 → 기출 문항 그림(썸네일, 70%) → 적용 풀이 → 정답 (핵심 로직 상자는 뺐다)"""
    key = 'K%d' % n
    qs = SOLS['QS'].get(key, qs)
    ans = SOLS['ANS'].get(key, ans)
    k = min(1.0, 29000 / fig[1]) * KICE_SCALE      # LOGIC BUILD 1에 넣던 크기(29000 안으로 줄인 것)의 70%
    w = int(fig[1] * k)
    rel = '/'.join(fig[0].split('/')[-2:])
    if rel in KICE_IMG:                            # 썸네일 폴더의 교육과정 맞춤 그림 (출처 라벨을 붙여 둔 것)
        path = os.path.join(KICE_DIR, KICE_IMG[rel])
        pw, ph = Image.open(path).size
        fig = (path, w, int(w * ph / pw))
    else:
        fig = (fig[0], w, int(fig[2] * k))
    blocks = []
    h_head = 20 + sum(LINE_Q * nlines(x, PER_Q) for x in qs) + 6
    blocks.append(Block(lambda: LK().kice_head(f'{label} {n}', qs), h_head + 40, keep_next=True))
    blocks.append(Block(lambda: figure_para([fig], FULL_W), figure_h([fig], FULL_W)))
    blocks.append(_sol_block(KICE_SOL, key, sol, False))
    blocks.append(Block(B.blank, 22))
    return blocks


# ---------------------------------------------------------------- 쪽 나누기
CAP_FIRST, CAP = 548.0, 672.0       # 본문 단 높이 (첫 쪽은 단원 머리 아래부터)
SIDE_CAP = 600.0                     # 날개 단 높이 (TAG 아래)
SIDE_PER, SIDE_LINE = 10.5, 15.0     # 날개 주석 한 줄 em, 줄 간격


def note_h(s):
    return SIDE_LINE * max(1, math.ceil(ems(s) / SIDE_PER)) + 18


PAGE_BRK = []      # 쪽마다 중단원 띠로 시작하는지
FLOW_FROM = 3      # 이 쪽부터는 띠가 아니면 강제 쪽 나눔 없이 이어 붙인다 (빈 공간 방지)


def paginate(blocks, report=None):
    flat = []
    for b in blocks:
        if isinstance(b, (list, tuple)):
            flat += list(b)
        else:
            flat.append(b)
    pages, cur, used, side, info = [], [], 0.0, 0.0, []

    def close():
        nonlocal cur, used, side
        while cur and cur[-1].make is B.blank:
            used -= cur.pop().h
        if cur:
            pages.append(cur); info.append((used, side))
        cur, used, side = [], 0.0, 0.0

    i = 0
    while i < len(flat):
        b = flat[i]
        cap = CAP_FIRST if not pages else CAP
        if b.brk and cur:
            close(); cap = CAP
        # 함께 붙어 있어야 하는 묶음(keep_next)의 높이
        j, grp = i, [b]
        while flat[j].keep_next and j + 1 < len(flat):
            j += 1; grp.append(flat[j])
        gh = sum(x.h for x in grp)
        gs = sum(note_h(n) for x in grp for n in x.notes)
        if cur and (used + gh > cap or side + gs > SIDE_CAP):
            close(); cap = CAP
        if not cur and b.make is B.blank:
            i += 1; continue
        for x in grp:
            cur.append(x); used += x.h; side += sum(note_h(n) for n in x.notes)
        i = j + 1
    close()
    # 짧은 꼬리 쪽(다음이 강제 쪽 나눔이거나 끝)은 앞 쪽에 붙인다 — 높이 어림이 넉넉하므로 6%까지 허용
    i = 1
    while i < len(pages):
        u, s_ = info[i]
        nxt_brk = i + 1 >= len(pages) or pages[i + 1][0].brk
        if u < 130 and nxt_brk and not pages[i][0].brk and info[i - 1][0] + u <= CAP * 1.06 and info[i - 1][1] + s_ <= SIDE_CAP:
            pages[i - 1] += pages[i]; info[i - 1] = (info[i - 1][0] + u, info[i - 1][1] + s_)
            del pages[i]; del info[i]
            continue
        i += 1
    if report is not None:
        report.extend(info)
    PAGE_BRK[:] = [bool(pg[0].brk) for pg in pages]
    out = []
    for pg in pages:
        ms = []
        for x in pg:
            ms.append(x.make)
        out.append(ms)
    return out


def flatten_pages(pages):
    """Block.make가 문단 목록을 돌려줄 수 있으므로, build()가 받을 수 있게 하나씩 편다."""
    res = []
    for ms in pages:
        page = []
        for m in ms:
            page.append(m)
        res.append(page)
    return res


def build(head_p, pages):
    """1단 전체 폭용: 쪽마다 TAG·세로선·날개 주석을 넣지 않는다 (블록이 문단 목록을 돌려줘도 됨)."""
    body = []
    for k, blocks in enumerate(pages):
        B.NOTES.clear()
        ps = []
        for b in blocks:
            v = b() if callable(b) else b
            ps += v if isinstance(v, list) else [v]
        if k == 0:
            ps = [head_p] + ps
        else:
            first = ps[0]
            if k >= FLOW_FROM and k < len(PAGE_BRK) and not PAGE_BRK[k]:
                body += ps
                continue
            first.set('pageBreak', '1')
            r0 = first.find(HP + 'run')
            if r0 is None:
                r0 = B.E('run', charPrIDRef='0'); first.insert(0, r0)
            if k == 1:
                for c in B.HDR2:
                    c = B.clone(c); ts = list(c.iter(HP + 't'))
                    ts[0].text, ts[1].text = B.HEADINFO['no'], ' ' + B.HEADINFO['title']
                    r0.insert(0, c)
            if k == 2 and B.STYLE.get('odd_body'):   # build.build와 같은 처리 (본문 홀수쪽 머리말 그림)
                path, size, pos = B.STYLE['odd_body']
                iid = B.add_image(path)
                B.STYLE['pic_size'] = dict(B.STYLE.get('pic_size', {}), **{iid: size})
                B.STYLE['pic_pos'] = dict(B.STYLE.get('pic_pos', {}), **{iid: pos})
                for c in head_p.iter(HP + 'ctrl'):
                    h = c.find(HP + 'header')
                    if h is not None and h.get('applyPageType') == 'ODD':
                        c2 = B.clone(c); c2.find(HP + 'header').set('id', '12')
                        for im in c2.iter(HC + 'img'):
                            im.set('binaryItemIDRef', iid)
                        r0.insert(0, c2)
        body += ps
    return body


import look  # noqa: E402,F401  (요소 디자인: build.py 블록 함수 바꿔 끼우기)
