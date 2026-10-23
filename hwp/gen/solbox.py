"""풀이 상자(Point n 풀이 · 적용 풀이) — 단계 제목 / 설명 / 식 / 결론 줄로 나눠 읽기 쉽게 짜는 표.
풀이 줄 표시:  '# 단계 제목'   '= 식 한 줄'   '> 결론'   (표시 없는 줄 = 설명 문장)
시안 A~E는 같은 내용을 서로 다른 표 모양으로 보여 준다 (STYLE[0]으로 고름)."""
import copy, re
import build as B

NS = B.NS
STYLE = ['C']      # 기본 시안 (사용자 선택 전 추천안)
ACC, INK, LILAC, LILAC_L, WARM = '#A9623A', '#3A241D', '#DDD1E8', '#F1ECF6', '#F7F2EC'
FULL_W = 46205
NAMES = {'A': '노트 라인', 'B': '웜 카드', 'C': '단계 표', 'D': '위아래 굵은 선', 'E': '탭 라벨'}

# ---------------------------------------------------------------- 문단 모양 (header.xml에 새로 추가)
_PP = {}      # 이름 -> (id, spec)


def pp(name, align='LEFT', left=0, intent=0, prev=0, nxt=0, ls=160):
    if name not in _PP:
        key = ('solbox', name)
        B.NEWPP[key] = str(70 + len(B.NEWPP))
        _PP[name] = (B.NEWPP[key], dict(align=align, left=left, intent=intent, prev=prev, nxt=nxt, ls=ls))
    return _PP[name][0]


_orig_pp_xml = B.pp_xml


def _pp_xml(h):
    real = {k: v for k, v in B.NEWPP.items() if not isinstance(k, tuple)}
    saved = dict(B.NEWPP); B.NEWPP.clear(); B.NEWPP.update(real)
    try:
        out = _orig_pp_xml(h)
    finally:
        B.NEWPP.clear(); B.NEWPP.update(saved)
    base = re.search(r'<hh:paraPr id="29".*?</hh:paraPr>', h, re.S).group(0)
    for i, s in _PP.values():
        x = base.replace('id="29"', 'id="%s"' % i, 1)
        x = re.sub(r'<hh:align horizontal="[A-Z_]+"', '<hh:align horizontal="%s"' % s['align'], x, 1)
        for tag, v in (('intent', s['intent']), ('left', s['left']), ('prev', s['prev']), ('next', s['nxt'])):
            x = re.sub(r'<hc:%s value="-?\d+"' % tag, '<hc:%s value="%d"' % (tag, v), x, 1)
        x = re.sub(r'<hh:lineSpacing type="PERCENT" value="\d+"', '<hh:lineSpacing type="PERCENT" value="%d"' % s['ls'], x, 1)
        out += x
    return out


B.pp_xml = _pp_xml

# ---------------------------------------------------------------- 글자 모양
def C_BODY(): return B.cp('33', font=B.HAND, h=1000, spacing=0, color='#202020')
def C_EQ(): return B.cp('33', font=B.HAND, h=1000, spacing=0, color=INK)
def C_STEP(color=ACC): return B.cp('16', font=8, h=880, spacing=0, color=color, bold=True)
def C_HEAD(color=ACC): return B.cp('16', font=8, h=850, spacing=10, color=color, bold=True)
def C_CONC(color=INK): return B.cp('33', font=B.HAND, h=1050, spacing=0, color=color, bold=True)
def C_LBL(color='#FFFFFF'): return B.cp('16', font=8, h=800, spacing=15, color=color, bold=True)


# ---------------------------------------------------------------- 표 만들기
_SRC_TBL = B.P[206].find('.//' + NS + 'tbl')


def para(markup, cpr, pp_id):
    tc0 = _SRC_TBL.find('.//' + NS + 'tc')
    p = copy.deepcopy(tc0.find(NS + 'subList').find(NS + 'p'))
    for x in list(p):
        p.remove(x)
    p.set('paraPrIDRef', pp_id)
    rs = B.runs(markup, cpr)
    if not rs:
        r = B.E('run', charPrIDRef=cpr); r.append(B.E('t')); rs = [r]
    for r in rs:
        p.append(r)
    return p


def grid(rows, width=FULL_W, margin=(850, 850, 400, 400), out_gap=(0, 283)):
    """rows: [[(비율, borderFill id, [문단], colspan), ...], ...] → 표 문단"""
    outer = B.clone(B.P[206])
    tbl = outer.find('.//' + NS + 'tbl')
    run = tbl.getparent()
    src = copy.deepcopy(_SRC_TBL)
    tc0 = src.find('.//' + NS + 'tc')
    for tr in src.findall(NS + 'tr'):
        src.remove(tr)
    ncol = max(sum(c[3] for c in row) for row in rows)
    # 칸 폭: 첫 행(colspan 1 칸이 가장 많은 행)의 비율로 열 폭을 정한다
    base = max(rows, key=lambda r: len(r))
    tot = sum(c[0] for c in base)
    colw = [int(width * c[0] / tot) for c in base]; colw[-1] += width - sum(colw)
    for ri, row in enumerate(rows):
        tr = B.E('tr'); ci = 0
        for (ratio, bid, paras, span) in row:
            tc = copy.deepcopy(tc0)
            tc.set('borderFillIDRef', bid)
            sub = tc.find(NS + 'subList')
            sub.set('vertAlign', 'CENTER' if len(paras) == 1 else 'TOP')
            for p in sub.findall(NS + 'p'):
                sub.remove(p)
            for p in paras:
                sub.append(p)
            tc.find(NS + 'cellAddr').set('colAddr', str(ci)); tc.find(NS + 'cellAddr').set('rowAddr', str(ri))
            tc.find(NS + 'cellSpan').set('colSpan', str(span)); tc.find(NS + 'cellSpan').set('rowSpan', '1')
            tc.find(NS + 'cellSz').set('width', str(sum(colw[ci:ci + span]))); tc.find(NS + 'cellSz').set('height', '600')
            m = tc.find(NS + 'cellMargin')
            m.set('left', str(margin[0])); m.set('right', str(margin[1])); m.set('top', str(margin[2])); m.set('bottom', str(margin[3]))
            tr.append(tc); ci += span
        src.append(tr)
    src.set('rowCnt', str(len(rows))); src.set('colCnt', str(ncol))
    src.set('borderFillIDRef', B.bfc('sb_none'))
    src.find(NS + 'sz').set('width', str(width)); src.find(NS + 'sz').set('height', str(600 * len(rows)))
    im = src.find(NS + 'inMargin')
    if im is not None:
        im.set('left', '0'); im.set('right', '0')
    om = src.find(NS + 'outMargin')
    om.set('top', str(out_gap[0])); om.set('bottom', str(out_gap[1]))
    run.replace(tbl, src)
    return outer


# ---------------------------------------------------------------- 풀이 줄 → 단계 묶음
def parse(lines):
    """→ steps [(제목 또는 None, [(종류, 문장)])], 결론 목록"""
    steps, concl = [], []
    for ln in lines:
        if ln.startswith('# '):
            steps.append((ln[2:], []))
        elif ln.startswith('> '):
            concl.append(ln[2:])
        else:
            if not steps:
                steps.append((None, []))
            if ln.startswith('= '):
                steps[-1][1].append(('eq', ln[2:]))
            else:
                steps[-1][1].append(('t', ln))
    return steps, concl


def _body_paras(items, left=0):
    out = []
    for kind, s in items:
        if kind == 'eq':
            out.append(para(s, C_EQ(), pp('eq%d' % left, left=left + 1200, prev=40, nxt=40)))
        else:
            out.append(para(s, C_BODY(), pp('t%d' % left, left=left, prev=0, nxt=0)))
    return out


def _stack(steps, numbered=False, step_color=ACC, left=0, gap=380):
    """단계 제목 + 설명을 한 칸에 위에서 아래로"""
    ps = []
    for k, (title, items) in enumerate(steps):
        if title:
            mark = ('%d  ' % (k + 1)) if numbered else ''
            ps.append(para(mark + title, C_STEP(step_color), pp('st%d_%d' % (left, 1 if k else 0), left=left, prev=gap if k else 0, nxt=80)))
        ps += _body_paras(items, left + (0 if title is None else 0))
    return ps


def _concl_paras(concl, color=INK, prefix='→ '):
    return [para(prefix + c, C_CONC(color), pp('cc', left=0)) for c in concl]


# ---------------------------------------------------------------- 시안 A~E
def box(header, lines, style=None):
    st = style or STYLE[0]
    steps, concl = parse(lines)
    hd = lambda color=ACC: para(header, C_HEAD(color), pp('hd'))
    if st == 'A':   # 노트 라인: 머리 칩 + 왼쪽 세로선 + 라일락 결론 띠
        chip = para(' ' + header + ' ', C_LBL(), pp('hd'))
        rows = [[(2, B.bfc('sbA_chip', fill=ACC), [chip], 1), (9, B.bfc('sbA_blank'), [para('', C_BODY(), pp('hd'))], 1)],
                [(11, B.bfc('sbA_body', left=('SOLID', '0.5 mm', ACC)), _stack(steps), 2)]]
        if concl:
            rows.append([(11, B.bfc('sbA_conc', fill=LILAC_L, left=('SOLID', '0.5 mm', ACC)), _concl_paras(concl), 2)])
        return grid(rows, margin=(900, 700, 300, 300))
    if st == 'B':   # 웜 카드: 옅은 바탕, 테두리 없음, 번호 단계
        rows = [[(1, B.bfc('sbB_head', fill=WARM, bottom=('SOLID', '0.12 mm', '#D9C7B4')), [hd()], 1)],
                [(1, B.bfc('sbB_body', fill=WARM), _stack(steps, numbered=True), 1)]]
        if concl:
            rows.append([(1, B.bfc('sbB_conc', fill=LILAC_L), _concl_paras(concl), 1)])
        return grid(rows, margin=(1000, 1000, 450, 450))
    if st == 'C':   # 단계 표: 왼쪽 단계 이름 / 오른쪽 설명, 점선으로 구분
        line = ('DOT', '0.12 mm', '#B9A898')
        rows = [[(1, B.bfc('sbC_head', bottom=('SOLID', '0.4 mm', ACC)), [hd()], 2)]]
        for k, (title, items) in enumerate(steps):
            lab = para(title or '', C_STEP(), pp('cl', align='LEFT'))
            rows.append([(3, B.bfc('sbC_l', fill=WARM, bottom=line), [lab], 1),
                         (8, B.bfc('sbC_r', bottom=line), _body_paras(items) or [para('', C_BODY(), pp('hd'))], 1)])
        if concl:
            rows.append([(3, B.bfc('sbC_cl', fill=LILAC), [para('결론', C_STEP(INK), pp('cl'))], 1),
                         (8, B.bfc('sbC_cr', fill=LILAC_L), _concl_paras(concl, prefix=''), 1)])
        rows[0][0] = (11, rows[0][0][1], rows[0][0][2], 2)
        return grid(rows, margin=(700, 700, 300, 300))
    if st == 'D':   # 위아래 굵은 선
        bd = ('SOLID', '0.7 mm', ACC)
        rows = [[(1, B.bfc('sbD_head', top=bd), [hd()], 1)],
                [(1, B.bfc('sbD_body'), _stack(steps), 1)]]
        if concl:
            rows.append([(1, B.bfc('sbD_conc', top=('DOT', '0.12 mm', ACC), bottom=bd), _concl_paras(concl, ACC), 1)])
        else:
            rows[-1][0] = (1, B.bfc('sbD_body_end', bottom=bd), rows[-1][0][2], 1)
        return grid(rows, margin=(300, 300, 300, 300))
    if st == 'E':   # 탭 라벨: 진한 탭 + 얇은 테두리 상자
        thin = ('SOLID', '0.12 mm', '#C9B8A6')
        tab = para(header, C_LBL(), pp('tab', align='CENTER'))
        rows = [[(2, B.bfc('sbE_tab', fill=INK), [tab], 1), (9, B.bfc('sbE_tabr', bottom=thin), [para('', C_BODY(), pp('hd'))], 1)],
                [(11, B.bfc('sbE_body', left=thin, right=thin, bottom=None if concl else thin), _stack(steps, step_color=INK), 2)]]
        if concl:
            rows.append([(11, B.bfc('sbE_conc', fill=WARM, left=thin, right=thin, bottom=thin, top=('DOT', '0.12 mm', '#C9B8A6')),
                          _concl_paras(concl, ACC, prefix='→ '), 2)])
        return grid(rows, margin=(900, 900, 320, 320))
    raise ValueError(st)


def height(lines, style=None, per=27 * 46205 / 32570):
    """쪽 나누기용 높이 어림 (pt)"""
    import lb
    steps, concl = parse(lines)
    h = 30
    for title, items in steps:
        h += (22 if title else 0) + sum(17 * lb.nlines(s, per) for _, s in items)
    h += sum(20 * lb.nlines(c, per) for c in concl) + (12 if concl else 0)
    return h + (len(steps) * 10 if (style or STYLE[0]) == 'C' else 0)
