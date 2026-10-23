"""LOGIC BUILD 2 요소 디자인. 사용자 선택: KICE 머리 K1, 줄 간격 현재, 설명 줄 N2, 번호 소제목 H5, 본문 STEP E04-A,
풀이 STEP E05-A, 식 줄 E06-A, 결론 E07-B(Ans 줄은 없앰), Intro 상자 E10-B, 표 T3, 강조 E12-C, TIP E13-A, 반응식 E14-B.
Mini 예제 라벨은 틀의 밑줄 라벨 그대로. 색은 진갈색·브라운·베이지·라일락 네 가지만 쓴다.
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

# ---------------------------------------------------------------- N2 설명 줄: → 화살표, 둘째 줄부터 매달린 들여쓰기 (세로선 없음)
def _note_pp(depth):
    return pp('lk_note%d' % depth, align='JUSTIFY', left=1700 + 1500 * depth, intent=-1300, ls=168, nxt=60)


def note(s):
    return body_p(B.runs('→\u2002' + s, B.BODY()), _note_pp(0))


def sub(s):
    return body_p(B.runs('–\u2002' + s, B.BODY()), _note_pp(1))


B.note, B.sub, B.ex = note, sub, note

# ---------------------------------------------------------------- E03-C 소제목 / E04-A 본문 STEP 제목
def C_H(): return B.cp('16', font=11, h=1100, spacing=0, color=INK)


def heading(s):
    s = re.sub(r'==|\*\*|~~', '', s)
    m = STEP_RE.match(s)
    if m and not m.group(1).isdigit():   # STEP 1. … / Logic 1. … → 진한 칩 + 제목
        return body_p(chip_runs(m.group(1), INK, h=820) + B.inline(m.group(2), C_H()),
                      pp('lk_hstep', left=0, prev=900, nxt=250, ls=160, keep=True))
    bf = B.bfc('lk_h5', fill='#FAF7F3')
    ppid = pp('lk_h5', left=0, prev=1100, nxt=450, ls=160, bf=bf, off=(600, 0, 240, 240), keep=True, connect=False)
    m = re.match(r'^(\d+|\[\d+\])[.]?\s+(.*)$', s)
    if m:   # 1. 제목 → 진한 번호 칩 + 제목
        return body_p(chip_runs(m.group(1).strip('[]'), INK, h=820) + B.inline(m.group(2), C_H()), ppid)
    return body_p(B.inline(s, C_H()), ppid)


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

# ---------------------------------------------------------------- T3 표: 첫 열 강조 (베이지 칸·브라운 글자), 머리 행은 브라운 글자 + 밑줄
def table(rows, widths=None, total=None):
    n = len(rows[0]); widths = widths or [1] * n
    hc = B.cp('16', font=11, h=900, spacing=0, color=ACC)
    fc = B.cp(B.CELL(), color=ACC)
    ppc = pp('lk_td', align='CENTER', ls=150)
    out = []
    for ri, row in enumerate(rows):
        cells = []
        for ci, val in enumerate(row):
            if ri == 0:
                cells.append((widths[ci], B.bfc('lk_th3', bottom=('SOLID', '0.3 mm', ACC)), [para(val, hc, ppc)], 1))
            elif ci == 0:
                cells.append((widths[ci], B.bfc('lk_tf3', fill=WARM, bottom=('SOLID', '0.12 mm', '#FFFFFF')), [para(val, fc, ppc)], 1))
            else:
                cells.append((widths[ci], B.bfc('lk_td3', bottom=('SOLID', '0.12 mm', '#EADFD3')), [para(val, B.CELL(), ppc)], 1))
        out.append(cells)
    return grid(out, margin=(400, 400, 220, 220), out_gap=(300, 500))


B.table = table

# ---------------------------------------------------------------- E14-B 가운데 반응식: 옅은 띠
def center_p(markup, width_pt):
    """가운데 반응식 줄: 음영 없이 가운데 정렬 + 위아래 여백"""
    return body_p(B.runs(markup, B.BODY()), pp('lk_eq', align='CENTER', prev=450, nxt=450, ls=160))


# ---------------------------------------------------------------- E09-A / K1 머리 탭 (풀이 상자 E1 탭과 같은 모양)
def tab_head(label, ratio=2.2):
    tab = para(label, SB.C_LBL(), pp('tab', align='CENTER'))
    blank = para('', SB.C_BODY(), pp('hd'))
    rows = [[(ratio, B.bfc('lk_tab', fill=INK), [tab], 1), (11 - ratio, B.bfc('lk_tabr', bottom=('SOLID', '0.12 mm', LINE)), [blank], 1)]]
    return grid(rows, margin=(300, 300, 230, 230), out_gap=(500, 350))


def C_Q(): return B.cp('16', font=10, h=1050, spacing=0, color='#1E1E1E')
def C_QB(): return B.cp('16', font=11, h=1050, spacing=0, color='#1E1E1E')


def question(s):
    return body_p(B.runs(s, C_Q()), pp('lk_q', align='JUSTIFY', ls=175, nxt=150))


# ---------------------------------------------------------------- K1 다시 묶은 질문: 조건은 베이지 상자, 질문은 Q 칩
ASK = re.compile(r'(\(O, X\)|시오|\?)\s*\.?\s*$')   # 묻는 문장 (…시오. / …? / (O, X))


def split_qs(lines):
    """→ (조건·설명 줄, [(번호, 질문)])"""
    ctx, qs = [], []
    for ln in lines:
        parts = [p for p in re.split(r'\s{2,}(?=Q\d+\.)', ln) if p.strip()]
        for p in parts:
            m = re.match(r'^(?:Q(\d*)\.|(\d+)\.)\s*(.*)$', p)
            if m:
                qs.append((m.group(1) or m.group(2) or '', m.group(3)))
            elif ASK.search(p):
                qs.append((None, p))
            else:
                ctx.append(p)
    if len(qs) > 1 and all(n is None for n, _ in qs):
        qs = [(str(i + 1), q) for i, (_, q) in enumerate(qs)]
    return ctx, qs


def kice_head(label, lines):
    return [tab_head(label, 2.6)] + q_block(lines)


Q_STYLE = ['p5']      # 발문 디자인: 'p5'(얇은 베이지 테두리 상자, 바탕 없음 — 사용자 선택) / 'plain'(상자 없음) / 'box'(베이지 음영 상자)


def P5_LINE():
    t = ('SOLID', '0.12 mm', LINE)
    return dict(left=t, right=t, top=t, bottom=t)


def q_block(lines):
    """발문: 조건·설명은 베이지 상자, 묻는 문장은 브라운 Q 칩 (Mini 예제와 Arranged KICE 공통)"""
    ctx, qs = split_qs(lines)
    out = []
    if ctx:
        ps = []
        for c in ctx:
            m = re.match(r'^(\([가-하]\)|\[[^\]]+\])\s*(.*)$', c)
            if m:   # (가) … 는 라벨을 굵게, 둘째 줄부터 들여쓰기
                ps.append(para(m.group(2), C_Q(), pp('lk_ctx', align='JUSTIFY', left=2000, intent=-2000, ls=175, nxt=80),
                               pre=B.inline(m.group(1) + ' ', B.cp('16', font=11, h=950, spacing=0, color=INK))))
            else:
                ps.append(para(c, C_Q(), pp('lk_ctx0', align='JUSTIFY', ls=175, nxt=80)))
        if Q_STYLE[0] == 'p5':   # P5: 얇은 베이지 테두리 상자 (바탕 없음) 안에 조건, 질문은 상자 아래
            out.append(grid([[(1, B.bfc('lk_p5box', **P5_LINE()), ps, 1)]], margin=(900, 900, 420, 420), out_gap=(0, 350)))
        elif Q_STYLE[0] == 'box':
            out.append(grid([[(1, B.bfc('lk_ctxbox', fill=WARM), ps, 1)]], margin=(900, 900, 450, 450), out_gap=(0, 350)))
        else:   # 음영 없음: 조건 문단을 그대로 (표 칸 문단 → 본문 문단으로 옮김)
            for p in ps:
                p.set('paraPrIDRef', pp('lk_ctx_plain', align='JUSTIFY', ls=175, nxt=100) if p.get('paraPrIDRef') == pp('lk_ctx0', align='JUSTIFY', ls=175, nxt=80)
                      else pp('lk_ctx_plain_lab', align='JUSTIFY', left=2000, intent=-2000, ls=175, nxt=100))
                out.append(body_p(list(p), p.get('paraPrIDRef')))
    if Q_STYLE[0] == 'p5' and not ctx and qs:   # 조건 없이 질문만 있으면 질문을 상자 안에
        ps = [para(q, C_QB(), pp('lk_kq_in', align='JUSTIFY', left=2400, intent=-2400, ls=170, nxt=60), pre=chip_runs('Q%s' % n if n else 'Q', ACC, h=880))
              for n, q in qs]
        return out + [grid([[(1, B.bfc('lk_p5box', **P5_LINE()), ps, 1)]], margin=(900, 900, 420, 420), out_gap=(0, 400))]
    for num, q in qs:
        lab = 'Q%s' % num if num else 'Q'
        out.append(body_p(chip_runs(lab, ACC, h=880) + B.runs(q, C_QB()),
                          pp('lk_kq', align='JUSTIFY', left=2400, intent=-2400, ls=170, nxt=200)))
    return out
