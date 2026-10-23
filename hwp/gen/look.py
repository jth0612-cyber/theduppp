"""LOGIC BUILD 2 요소 디자인 (사용자 선택: K1, E01-현재, E02-C, E03-C, E04-A, E05-A, E06-A, E07-B,
E08-A, E09-A, E10-B, E11-A, E12-C, E13-A, E14-B). 색은 진갈색·브라운·베이지·라일락 네 가지만 쓴다.
build.py의 블록 함수(B.note, B.cf, B.table …)를 바꿔 끼운다."""
import re
import build as B
import solbox as SB
from solbox import ACC, INK, LILAC, LILAC_L, WARM, pp, para, grid, chip_runs, STEP_RE

HP = B.NS
LINE = '#C9B8A6'
BAND = '#F4EFEA'


def body_p(rs, pp_id):
    """본문(맨 바깥) 문단: 틀의 빈 문단을 복제해 문단 모양과 run을 채운다"""
    p = B.clone(B.P[1])
    for x in list(p):
        p.remove(x)
    p.set('paraPrIDRef', pp_id)
    for r in rs:
        p.append(r)
    return p


def _hl(s):
    """E12-C: 빨간 펜(**…**)도 형광펜으로 통일"""
    return re.sub(r'\*\*(.+?)\*\*', r'==\1==', s)


_orig_runs = B.runs
B.runs = lambda markup, cpr, ref=True: _orig_runs(_hl(markup), cpr, ref)

# ---------------------------------------------------------------- E02-C 설명 줄: 왼쪽 옅은 세로선
NOTE_BF = lambda: B.bfc('lk_note', left=('SOLID', '0.7 mm', '#DCCDBE'))


def _note_pp(depth):
    return pp('lk_note%d' % depth, align='JUSTIFY', left=1300 + 1500 * depth, ls=168, bf=NOTE_BF(), off=(700, 0, 60, 60))


def note(s):
    return body_p(B.runs(s, B.BODY()), _note_pp(0))


def sub(s):
    return body_p(B.inline('– ', B.BODY()) + B.runs(s, B.BODY()), _note_pp(1))


B.note, B.sub, B.ex = note, sub, note

# ---------------------------------------------------------------- E03-C 소제목 / E04-A 본문 STEP 제목
def C_H(): return B.cp('16', font=11, h=1100, spacing=0, color=INK)


def heading(s):
    s = re.sub(r'==|\*\*|~~', '', s)
    m = STEP_RE.match(s)
    if m and not m.group(1).isdigit():   # STEP 1. … / Logic 1. … → 진한 칩 + 제목
        return body_p(chip_runs(m.group(1), INK, h=820) + B.inline(m.group(2), C_H()),
                      pp('lk_hstep', left=0, prev=900, nxt=250, ls=160, keep=True))
    bf = B.bfc('lk_h', fill=WARM, left=('SOLID', '1.0 mm', ACC))
    return body_p(B.inline(s, C_H()), pp('lk_h', left=0, prev=1100, nxt=450, ls=160, bf=bf, off=(900, 0, 260, 260), keep=True, connect=False))


B.h1 = heading

# ---------------------------------------------------------------- E13-A TIP: 라일락 칩 + 파란 손글씨
def tip(s):
    pen = B.cp('34', font=B.PEN, h=B.STYLE.get('note_h', 1000), spacing=0, color=B.STYLE['blue'])
    return body_p(chip_runs('TIP', LILAC, INK) + B.runs(s, pen), pp('lk_tip', left=1300, prev=500, nxt=500, ls=168))


B.tip = tip

# ---------------------------------------------------------------- E08-A 정답: 오른쪽 브라운 Ans 칩
def answer(s):
    return body_p(chip_runs('Ans', ACC, h=820) + B.inline(s, B.cp('16', font=11, h=1000, spacing=0, color=INK)),
                  pp('lk_ans', align='RIGHT', prev=200, nxt=600, ls=160))


B.answer = answer

# ---------------------------------------------------------------- E10-B Intro·핵심·한 줄 정리: 위아래 진한 선
def cf(s, label='cf.'):
    lab = para(label, B.cp('16', font=11, h=850, spacing=0, color=ACC), pp('lk_cf_lab', ls=150))
    body = para(s, B.CFBODY(), pp('lk_cf_body', ls=175))
    rows = [[(1, B.bfc('lk_cf_top', top=('SOLID', '0.4 mm', INK)), [lab], 1)],
            [(1, B.bfc('lk_cf_bot', bottom=('SOLID', '0.25 mm', INK)), [body], 1)]]
    return grid(rows, margin=(300, 300, 260, 260), out_gap=(400, 600))


B.cf = cf

# ---------------------------------------------------------------- E11-A 표: 진한 머리 행, 가로선만
def table(rows, widths=None, total=None):
    n = len(rows[0]); widths = widths or [1] * n
    hc = B.cp('16', font=11, h=900, spacing=0, color='#FFFFFF')
    out = []
    for ri, row in enumerate(rows):
        cells = []
        for ci, val in enumerate(row):
            if ri == 0:
                cells.append((widths[ci], B.bfc('lk_th', fill=INK), [para(val, hc, pp('lk_td', align='CENTER', ls=150))], 1))
            else:
                cells.append((widths[ci], B.bfc('lk_td', bottom=('SOLID', '0.12 mm', LINE)), [para(val, B.CELL(), pp('lk_td', align='CENTER', ls=150))], 1))
        out.append(cells)
    return grid(out, margin=(400, 400, 220, 220), out_gap=(300, 500))


B.table = table

# ---------------------------------------------------------------- E14-B 가운데 반응식: 옅은 띠
def center_p(markup, width_pt):
    side = max(0, int((462 - width_pt - 60) / 2 / 10) * 1000)   # 띠 폭을 식 길이에 맞춤 (10pt 단위)
    bf = B.bfc('lk_eq', fill=BAND)
    return body_p(B.runs(markup, B.BODY()), pp('lk_eq%d' % side, align='CENTER', left=side, right=side, prev=500, nxt=500, ls=160,
                                            bf=bf, off=(0, 0, 220, 220), connect=False))


# ---------------------------------------------------------------- E09-A / K1 머리 탭 (풀이 상자 E1 탭과 같은 모양)
def tab_head(label, ratio=2.2):
    tab = para(label, SB.C_LBL(), pp('tab', align='CENTER'))
    blank = para('', SB.C_BODY(), pp('hd'))
    rows = [[(ratio, B.bfc('lk_tab', fill=INK), [tab], 1), (11 - ratio, B.bfc('lk_tabr', bottom=('SOLID', '0.12 mm', LINE)), [blank], 1)]]
    return grid(rows, margin=(300, 300, 230, 230), out_gap=(500, 350))


def C_Q(): return B.cp('16', font=10, h=950, spacing=0, color='#1E1E1E')


def question(s):
    return body_p(B.runs(s, C_Q()), pp('lk_q', align='JUSTIFY', ls=175, nxt=150))


# ---------------------------------------------------------------- K1 다시 묶은 질문: 조건은 베이지 상자, 질문은 Q 칩
ASK = re.compile(r'(\(O, X\)|구하시오|쓰시오|찾으시오|비교하시오|서술하시오|\?)\s*\.?\s*$')


def split_qs(lines):
    """→ (조건·설명 줄, [(번호, 질문)])"""
    ctx, qs = [], []
    for ln in lines:
        parts = [p for p in re.split(r'\s{2,}(?=Q\d+\.)', ln) if p.strip()]
        for p in parts:
            m = re.match(r'^(?:Q(\d+)\.|(\d+)\.)\s*(.*)$', p)
            if m:
                qs.append((m.group(1) or m.group(2), m.group(3)))
            elif ASK.search(p):
                qs.append((None, p))
            else:
                ctx.append(p)
    if len(qs) > 1 and all(n is None for n, _ in qs):
        qs = [(str(i + 1), q) for i, (_, q) in enumerate(qs)]
    return ctx, qs


def kice_head(label, lines):
    ctx, qs = split_qs(lines)
    out = [tab_head(label, 2.6)]
    if ctx:
        ps = []
        for c in ctx:
            m = re.match(r'^(\([가-하]\)|\[[^\]]+\])\s*(.*)$', c)
            if m:   # (가) … 는 라벨을 굵게, 둘째 줄부터 들여쓰기
                ps.append(para(m.group(2), C_Q(), pp('lk_ctx', align='JUSTIFY', left=2000, intent=-2000, ls=175, nxt=80),
                               pre=B.inline(m.group(1) + ' ', B.cp('16', font=11, h=950, spacing=0, color=INK))))
            else:
                ps.append(para(c, C_Q(), pp('lk_ctx0', align='JUSTIFY', ls=175, nxt=80)))
        out.append(grid([[(1, B.bfc('lk_ctxbox', fill=WARM), ps, 1)]], margin=(900, 900, 450, 450), out_gap=(0, 350)))
    for num, q in qs:
        lab = 'Q%s' % num if num else 'Q'
        out.append(body_p(chip_runs(lab, ACC, h=820) + B.runs(q, B.cp('16', font=11, h=950, spacing=0, color='#1E1E1E')),
                          pp('lk_kq', align='JUSTIFY', left=2300, intent=-2300, ls=170, nxt=200)))
    return out
