# Squeeze 내지 03-01 디벨롭: 세로 핀(건물 외벽) 요소별 후보.
# 묶음 A=(H1,N1,P1) B=(H2,N2,P2) C=(H3,N3,P3)
# 사용: python sq7.py <squeeze.pdf> <resources.pdf> <출력폴더> [A B C]
import sys, math, os
import numpy as np
sys.path.insert(0, '.')
from sq6 import (fins, draw_fins, fadeX, gut, Noise, sm, FIN_W, label_default, foot_default, logic_list, logic_title,
                 solving_word, NOTE, SW, G, build, f, m, R, W, S, K, S_, K_, tint)

PAL = [('S', 1.0, 4), ('S', .7, 3), ('S', .45, 3), ('S', .25, 2)]
PITCH, MOD, GAP = 2.2, 1.8, 0.28
NZ = Noise(11, 60)

def head_bottom(X):
    """기둥별 아래 끝: 제본선 쪽이 깊고 바깥으로 짧아짐(흩뿌림 없이 길이로만 줄어듦)."""
    return 5.2 + 11 * float(gut(X, 160)) + 2.4 * float(NZ(X, 0)) + 4 * float(fadeX(X))

def head_items():
    return fins(5, 1.1, SW, PITCH, 0, head_bottom, MOD, lambda X, y: 0.93, gap=GAP, palette=PAL)

HEAD_TINT = lambda x, y: 0.42 + 0.58 * float(fadeX(x))

def facade_grid(d, bottom, x0, x1, top=0.0, module=MOD, pitch=PITCH, xoff=1.1):
    """외벽 격자: 층 선(가로)과 창틀(세로) 헤어라인. 핀이 있는 높이까지만."""
    sh = d.p.new_shape()
    Xs = np.arange(x0, x1, 0.4)
    B = np.array([bottom(X) for X in Xs])
    k = 1
    while True:
        y = top + k * module
        if y > B.max(): break
        inside = B > y
        i = 0
        while i < len(Xs):
            if inside[i]:
                j = i
                while j + 1 < len(Xs) and inside[j + 1]: j += 1
                if Xs[j] - Xs[i] > 0.5:
                    sh.draw_line(f.Point(m(Xs[i] - d.dx), m(y)), f.Point(m(Xs[j] - d.dx), m(y)))
                    sh.finish(color=K(.12 * float(np.mean(fadeX(Xs[i:j + 1])) * .5 + .06)), width=0.14)
                i = j + 1
            else:
                i += 1
        k += 1
    X = x0 + xoff
    while X < x1:
        b = bottom(X)
        sh.draw_line(f.Point(m(X - d.dx), m(top)), f.Point(m(X - d.dx), m(b)))
        sh.finish(color=K(.07 + .05 * float(fadeX(X))), width=0.12)
        X += pitch
    sh.commit()

# ── 상단 후보 ────────────────────────────────────────────
def H1(d, side):
    draw_fins(d, head_items(), HEAD_TINT)

def H2(d, side):
    facade_grid(d, head_bottom, d.dx - 2, d.dx + W + 2)
    draw_fins(d, head_items(), HEAD_TINT)

BASE = 19.0
def H3(d, side):
    it = fins(5, 1.1, SW, PITCH, 0, lambda X: head_bottom(X) - 1.5, MOD, lambda X, y: 0.93, gap=GAP, palette=PAL)
    draw_fins(d, [(x, BASE - yb, BASE - ya, ink, t) for x, ya, yb, ink, t in it], HEAD_TINT)
    d.line(max(19 - d.dx, -1), BASE + 0.45, min(SW - 19 - d.dx, W + 1), BASE + 0.45, K(.45), .25)

# ── 번호 후보 ────────────────────────────────────────────
def N_text(d, side, no, lab):
    if side == 'odd':
        d.text(108, 47, no, 'md', 30, S(), 'r'); d.text(108, 53.6, lab, 'pr', 8.2, K(.68), 'r')
    else:
        wd = d.text(19, 47, no, 'md', 30, S()); d.text(19 + wd + 4, 46.5, lab, 'pr', 8.2, K(.68)); return wd

def N1(d, side, no, lab):
    N_text(d, side, no, lab)

def fin_stack(d, x, y0, segs, w=0.55):
    """세로 핀 한 줄: (길이, 잉크, 농도) 토막을 위에서 아래로."""
    y = y0
    for L, ink, t in segs:
        d.rect(x - w / 2, y, x + w / 2, y + L, tint(ink, t), None); y += L + GAP

def N2(d, side, no, lab):
    N_text(d, side, no, lab)
    if side == 'odd': fin_stack(d, 111.2, 37.2, [(5.4, S_, 1), (3.6, S_, .45), (7.2, S_, .7)])
    else: fin_stack(d, 15.8, 37.2, [(5.4, S_, 1), (2.6, S_, .45), (1.6, S_, .7)])

def N3(d, side, no, lab):
    wd = d.width(no, 'md', 30)
    N_text(d, side, no, lab)
    x0 = 108 - wd if side == 'odd' else 19
    r = np.random.default_rng(len(no) + (1 if side == 'odd' else 0))
    pal = [(S_, 1), (S_, .7), (S_, .45), (S_, .25)]
    x = x0 + 0.3
    while x < x0 + wd:
        L = 0.9 * int(r.integers(1, 3))
        ink, t = pal[int(r.integers(0, 4))]
        d.rect(x - 0.15, 48.3, x + 0.15, 48.3 + L, tint(ink, t), None); x += 1.1

def fin_row(d, x0, x1, y, L0, L1, seed, up=False, module=0.6, w=FIN_W, fade=0.7):
    """기둥마다 핀 하나: 길이가 L0→L1로 매끄럽게 줄고(모듈 단위로 살짝 엇갈림), 농도는 팔레트에서."""
    r = np.random.default_rng(seed)
    inks = [(p_[0], p_[1]) for p_ in PAL]; wts = np.array([p_[2] for p_ in PAL], float); wts /= wts.sum()
    sh = d.p.new_shape()
    x = x0
    while x <= x1:
        t = (x - x0) / max(x1 - x0, 1e-6)
        L = L0 + (L1 - L0) * float(sm(0, 1, t)) + module * int(r.integers(-1, 2))
        L = max(L, 0.6)
        ink, a = inks[r.choice(len(inks), p=wts)]
        a *= 1 - fade * float(sm(0.15, 1, t))
        ya, yb = (y - L, y) if up else (y, y + L)
        sh.draw_rect(R(x - w / 2, ya, x + w / 2, yb)); sh.finish(fill=tint(S_ if ink == 'S' else K_, a), color=None)
        x += PITCH
    sh.commit()

# ── 풀이 후보 ────────────────────────────────────────────
def P_base(d, x0, y0, x1, y1, dots_x=None):
    d.dots(dots_x or x0 + 6, y0 + 13, x1 - 6, y1 - 6, 5, .17, S(.38))
    d.line(x0, y1, x1, y1, K(.2), .25)

def P1(d):
    x0, y0, x1, y1 = NOTE
    fin_row(d, x0 + 1, x1, y0, 7.2, 1.2, 21)
    P_base(d, x0, y0, x1, y1)
    d.text(x0, y0 - 2.4, '풀이', 'pm', 8.2, S())

def P2(d):
    x0, y0, x1, y1 = NOTE
    nz = Noise(23, 20)
    it = fins(22, x0 + 1, x0 + 12, PITCH, y0, lambda X: y0 + 60 + 22 * float(nz(X * 2, 0)), MOD * 2,
              lambda X, y: 0.93, gap=GAP, palette=PAL)
    draw_fins(d, it, lambda x, y: 1 - 0.75 * float(sm(y0 + 10, y0 + 80, y)))
    d.line(x0 + 14.5, y0, x1, y0, K(.35), .25)
    P_base(d, x0, y0, x1, y1, dots_x=x0 + 20)
    d.text(x0 + 16, y0 + 5, '풀이', 'pm', 8.2, S())

def P3(d):
    x0, y0, x1, y1 = NOTE
    d.line(x0, y0, x1, y0, K(.35), .25)
    fin_stack(d, x0 + 0.3, y0 - 5.6, [(2.6, S_, 1), (2.2, S_, .45)], w=0.5)
    P_base(d, x0, y0, x1, y1)
    d.text(x0 + 2.4, y0 - 2.0, '풀이', 'pm', 8.2, S())

# ── Solving / Logic ──────────────────────────────────────
def solving_hang(d):
    x = solving_word(d)
    fin_row(d, x + 3.5, 243, 273.6, 5.0, 0.9, 31)

def solving_rise(d):
    x = solving_word(d)
    fin_row(d, x + 3.5, 243, 278.6, 5.0, 0.9, 31, up=True)

def logic_panel(d, grid=False, rise=False):
    logic_title(d, 'A. 고체')
    nz = Noise(41, 40)
    bot = lambda X: 190 + 40 * float(nz(X, 0)) + 26 * math.sin((X - 19) / 93 * math.pi)
    it = fins(42, 20.1, 112, PITCH, 72, bot, 3.6, lambda X, y: 0.9, gap=0.35, palette=PAL)
    if rise:
        top, base = 72, 300
        it = [(x, base - (yb - top), base - (ya - top), ink, t) for x, ya, yb, ink, t in it]
        draw_fins(d, it, lambda x, y: 1 - 0.6 * float(sm(230, 100, y)))
        d.line(19, base + 0.5, 112, base + 0.5, K(.45), .25)
    else:
        if grid: facade_grid(d, bot, 19, 113, top=72, module=3.6)
        draw_fins(d, it, lambda x, y: 1 - 0.6 * float(sm(140, 280, y)))
    logic_list(d)


# ── 03-01-04: 무작위 윤곽(좌우 대칭 아님) + 정리된 풀이·Logic Check ─────────────
_RA, _RB, _RC = Noise(303, 140, dirs=0.3), Noise(304, 55, dirs=0.4), Noise(305, 18, dirs=0.5)
def head_bottom_rand(X):
    """핀 아래 끝: 큰 물결 + 중간 물결 + 잔물결을 섞어 무작위로 내려갔다 올라옴(제본선 대칭 아님)."""
    v = 0.55 * float(_RA(X, 0)) + 0.35 * float(_RB(X, 0)) + 0.18 * float(_RC(X, 0))
    return 4.0 + 15.5 * float(sm(-0.75, 0.75, v))

def H1r(d, side):
    it = fins(5, 1.1, SW, PITCH, 0, head_bottom_rand, MOD, lambda X, y: 0.93, gap=GAP, palette=PAL)
    draw_fins(d, it, lambda x, y: 0.55 + 0.45 * float(fadeX(x)))

def logic_clean(d):
    """Logic Check: P3와 같은 언어 - 가는 선 + 작은 핀 표식 + 제목. 큰 장식 없음."""
    d.text(19, 52, 'Logic Check', 'md', 28, K())
    d.line(19, 63, 112, 63, K(.35), .25)
    fin_stack(d, 19.3, 57.4, [(2.6, S_, 1), (2.2, S_, .45)], w=0.5)
    d.text(21.4, 61.0, 'A. 고체', 'pm', 8.6, S())
    logic_list(d)

def make(name, H, N, Pn, solving, grid=False, rise=False, logic=None):
    class C:
        pass
    C.name = name
    C.head = lambda s_, d, side: H(d, side)
    C.label = lambda s_, d, side, unit: label_default(d, side, unit)
    C.num = lambda s_, d, side, no, lab: N(d, side, no, lab)
    C.note = lambda s_, d: Pn(d)
    C.solving = lambda s_, d: solving(d)
    C.foot = lambda s_, d, side, no: foot_default(d, side, no)
    C.logic = (lambda s_, d: logic(d)) if logic else (lambda s_, d: logic_panel(d, grid, rise))
    return C

SETS = {
    'A': make('03-01-01(A 다듬기·번호 그대로·풀이 위쪽 핀)', H1, N1, P1, solving_hang),
    'B': make('03-01-02(B 외벽 격자·번호 옆 핀 기둥·풀이 왼쪽 기둥)', H2, N2, P2, solving_hang, grid=True),
    'C': make('03-01-03(C 아래서 자람·번호 아래 핀 줄·풀이 장식 없음)', H3, N3, P3, solving_rise, rise=True),
    'D': make('03-01-04(H1 무작위 윤곽·풀이와 Logic Check 정리)', H1r, N1, P3, solving_hang, logic=logic_clean),
}

if __name__ == '__main__':
    SRC, RES, OUTD = sys.argv[1:4]
    which = sys.argv[4:] or list(SETS)
    os.makedirs(OUTD, exist_ok=True)
    src, res = f.open(SRC), f.open(RES)
    for k in which:
        C = SETS[k]
        print(build(C, src, res, f'{OUTD}/Squeeze_내지_{C.name}.pdf'), flush=True)
