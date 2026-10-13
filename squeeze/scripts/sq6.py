# Squeeze 내지 03-NN: 사진 질감 시안 (세로 핀 / 물결)
# 사용: python sq6.py <squeeze.pdf> <resources.pdf> <출력폴더> [1..5]
import sys, math, io, os
import numpy as np
sys.path.insert(0, '.')
from sq5 import (wash, label_default, foot_default, logic_list, logic_title, solving_word, NOTE,
                 SW, G, SA, side_dx, build, P, f, m, R, W, H, S, K, S_, K_, tint, PAPER)
from tex import sm, Noise, fins, Water

def fadeX(X):
    """단원명 쪽(펼침면 양 바깥)으로 smoothstep으로 연해짐 (인수인계 4b와 같은 방식)."""
    return 1 - 0.68 * np.maximum(1 - sm(19, 140, X), sm(SW - 140, SW - 19, X))
def gut(X, w=150): return np.exp(-((np.asarray(X, float) - G) / w) ** 2)

# ── 핀 그리기 ──────────────────────────────────────────────
FIN_W = 0.34
def draw_fins(d, items, tint_fn=lambda x, y: 1.0, wfin=FIN_W):
    sh = d.p.new_shape()
    for x, ya, yb, ink, t in items:
        px = x - d.dx
        if px < -1 or px > W + 1: continue
        a = t * float(tint_fn(x, (ya + yb) / 2))
        if a < 0.04: continue
        sh.draw_rect(R(px - wfin / 2, ya, px + wfin / 2, yb))
        sh.finish(fill=tint(S_ if ink == 'S' else K_, a), color=None)
    sh.commit()

def fin_cluster(d, x, y_base, n, seed, up=True, module=1.2, pitch=1.5, maxmod=4, wfin=0.3):
    """작은 핀 묶음(번호 옆·Solving 등): 기준선에서 위로 자란다."""
    r = np.random.default_rng(seed)
    sh = d.p.new_shape()
    pal = [(S_, 1), (S_, .7), (S_, .45), (S_, .25), (K_, .45)]
    for i in range(n):
        L = int(r.integers(1, maxmod + 1)) * module * (1 - 0.5 * i / max(n - 1, 1))
        ink, t = pal[int(r.integers(0, len(pal)))]
        xx = x + i * pitch
        y0, y1 = (y_base - L, y_base) if up else (y_base, y_base + L)
        sh.draw_rect(R(xx - wfin / 2, y0, xx + wfin / 2, y1)); sh.finish(fill=tint(ink, t), color=None)
    sh.commit()

# ── 물결 그리기 ────────────────────────────────────────────
BR = Noise(77, 2.2)
def draw_ripples(d, wt, x0, y0, x1, y1, alpha_fn, w=0.18, res=0.06, glint_n=0, glint_seed=9):
    """wt 물결의 줄무늬를 (x0..x1, y0..y1) 쪽 좌표 영역에 그린다. alpha_fn(X, Y)는 펼침면 좌표."""
    X0, X1 = x0 + d.dx, x1 + d.dx
    sh = d.p.new_shape()
    for xs, ys in wt.ripple_lines(X0, y0, X1, y1, res=res):
        P_ = wt.patchiness(xs, ys)
        cut = sm(-0.45, -0.1, BR(xs * 0.8, ys * 2.5))
        a = P_ * (0.35 + 0.65 * cut) * (cut > 0.05) * alpha_fn(xs, ys)
        i, L = 0, len(xs)
        while i < L - 1:
            j = min(i + 6, L - 1)
            av = float(np.mean(a[i:j + 1]))
            dx_, dy_ = abs(xs[j] - xs[i]), abs(ys[j] - ys[i])
            if av > 0.06 and float(np.min(a[i:j + 1])) > 0.02 and dy_ < 1.1 * dx_ + 0.02:
                sh.draw_polyline([f.Point(m(x - d.dx), m(y)) for x, y in zip(xs[i:j + 1], ys[i:j + 1])])
                sh.finish(color=tint(S_, min(av, 1)), width=w, closePath=False, lineCap=1, lineJoin=1)
            i = j
    sh.commit()
    if glint_n:
        g = wt.glints(glint_seed, X0, y0, X1, y1, glint_n, lambda x, y: float(alpha_fn(x, y)))
        sh = d.p.new_shape()
        for x, y, r in g:
            if x0 - 1 < x - d.dx < x1 + 1: sh.draw_circle(f.Point(m(x - d.dx), m(y)), m(r))
        sh.finish(fill=S(), color=None); sh.commit()

def water_tone(wt, alpha_fn, k_stone=0.11, k_rip=0.10):
    """물빛 톤(래스터): 돌 그림자(둥근 덩어리) + 물결 줄무늬의 밝기."""
    def fn(X, Y):
        a = alpha_fn(X, Y)
        st = wt.stones(X, Y)
        rip = (0.5 + 0.5 * np.cos(np.pi * wt.phase(X, Y))) ** 5 * wt.patchiness(X, Y)
        return a * (k_stone * st + k_rip * rip * (0.6 + 0.4 * st))
    return fn

WATER = dict(lam=0.85, amp=0.4, wx=3.0, bunch=0.18, patch_lo=-0.75)


# ═══ 03-01 세로 핀 · 머리띠 ════════════════════════════════
class F1:
    name = '03-01(세로 핀 머리띠)'
    NZ = Noise(11, 60)
    @staticmethod
    def items():
        bot = lambda X: 7 + 9 * float(gut(X, 150)) + 3.2 * float(F1.NZ(X, 0)) + 5 * float(fadeX(X))
        fl = lambda X, y: (0.78 + 0.18 * float(gut(X, 170))) * float(fadeX(X)) ** .5
        return fins(5, 1.1, SW, 2.2, 0, bot, 1.8, fl, gap=0.28,
                    palette=[('S', 1.0, 4), ('S', .7, 3), ('S', .45, 3), ('S', .25, 2), ('K', .5, 1)])
    def head(s_, d, side):
        draw_fins(d, F1.items(), lambda x, y: 0.5 + 0.5 * float(fadeX(x)))
    label = staticmethod(label_default)
    def num(s_, d, side, no, lab):
        if side == 'odd':
            d.text(108, 47, no, 'md', 30, S(), 'r')
            d.text(108, 53.6, lab, 'pr', 8.2, K(.68), 'r')
            fin_cluster(d, 108 - d.width(lab, 'pr', 8.2) - 9.5, 53.6, 6, 2, module=0.9, pitch=1.4)
        else:
            wd = d.text(19, 47, no, 'md', 30, S())
            fin_cluster(d, 19 + wd + 3.4, 46.6, 6, 3, module=1.3, pitch=1.4)
            d.text(19 + wd + 13, 46.5, lab, 'pr', 8.2, K(.68))
    def note(s_, d):
        x0, y0, x1, y1 = NOTE
        it = fins(21, x0 + 1, x1, 2.2, y0, lambda X: y0 + 3.6 + 3.6 * (1 - float(sm(x0, x1 - 60, X))), 1.8,
                  lambda X, y: 0.85 * (1 - 0.8 * float(sm(x0 + 30, x1, X))), gap=0.28)
        draw_fins(d, it)
        d.dots(x0 + 6, y0 + 13, x1 - 6, y1 - 6, 5, .17, S(.38))
        d.line(x0, y1, x1, y1, K(.2), .25)
        d.text(x0, y0 - 2.4, '풀이', 'pm', 8.2, S())
    def solving(s_, d):
        x = solving_word(d)
        it = fins(31, x + 3, 243, 2.2, 274.0, lambda X: 274.0 + 4.4 * (1 - 0.7 * float(sm(x, 243, X))), 1.1,
                  lambda X, y: 0.95 * (1 - 0.75 * float(sm(x + 10, 243, X))), gap=0.2)
        draw_fins(d, it)
    foot = staticmethod(foot_default)
    def logic(s_, d):
        logic_title(d, 'A. 고체')
        nz = Noise(41, 40)
        it = fins(42, 19, 112, 2.2, 72, lambda X: 200 + 50 * float(nz(X, 0)) + 30 * math.sin((X - 19) / 93 * math.pi), 3.6,
                  lambda X, y: 0.88 * (1 - 0.85 * float(sm(150, 290, y))), gap=0.35)
        draw_fins(d, it, lambda x, y: 1 - 0.6 * float(sm(140, 290, y)))
        logic_list(d)


# ═══ 03-02 세로 핀 · 바깥 기둥 ═════════════════════════════
class F2(F1):
    name = '03-02(세로 핀 바깥 기둥)'
    def head(s_, d, side):
        # 바깥 여백(0~13mm)을 타고 내려오는 핀 기둥: 위가 빽빽하고 아래로 엇갈리며 사라짐
        xs0, xs1 = (1.0, 13.5) if side == 'even' else (SW - 13.5, SW - 1.0)
        nz = Noise(13, 30)
        it = fins(7 if side == 'even' else 8, xs0, xs1, 1.9, 0,
                  lambda X: 120 + 60 * float(nz(X * 3, 0)) + 20 * math.sin(X), 3.0,
                  lambda X, y: 0.92 * (1 - 0.8 * float(sm(60, 190, y))), gap=0.32)
        draw_fins(d, it, lambda x, y: 1 - 0.65 * float(sm(50, 190, y)))
        # 단원명 위로 이어지는 가는 머리선 하나
        if side == 'even': d.line(15.5, 13.6, 128, 13.6, K(.35), .25)
        else: d.line(134, 13.6, W - 15.5, 13.6, K(.35), .25)
    def logic(s_, d):
        logic_title(d, 'A. 고체')
        nz = Noise(44, 26)
        it = fins(45, 19, 112, 2.2, 72, lambda X: 120 + 34 * float(nz(X, 0)), 3.0,
                  lambda X, y: 0.8 * (1 - 0.85 * float(sm(85, 150, y))), gap=0.3)
        draw_fins(d, it, lambda x, y: 1 - 0.6 * float(sm(80, 150, y)))
        logic_list(d)


# ═══ 03-03 잔물결 선 ════════════════════════════════════════
class W1:
    name = '03-03(잔물결 선)'
    wt = Water(seed=3, **WATER)
    @staticmethod
    def head_alpha(X, Y):
        return np.minimum(1.0, 1.3 * (0.6 + 0.4 * gut(X, 170)) * fadeX(X) * (1 - sm(11, 23, Y)) * sm(-1, 1.5, Y))
    def head(s_, d, side):
        draw_ripples(d, W1.wt, 0, 0, W, 24, W1.head_alpha, glint_n=70, glint_seed=5 if side == 'even' else 6)
    label = staticmethod(label_default)
    def num(s_, d, side, no, lab):
        wt = Water(seed=21, **WATER)
        if side == 'odd':
            d.text(108, 47, no, 'md', 30, S(), 'r')
            d.text(108, 53.6, lab, 'pr', 8.2, K(.68), 'r')
        else:
            wd = d.text(19, 47, no, 'md', 30, S())
            d.text(19 + wd + 4, 46.5, lab, 'pr', 8.2, K(.68))
    def note(s_, d):
        x0, y0, x1, y1 = NOTE
        a = lambda X, Y: (1 - sm(y0 + 4, y0 + 20, Y)) * (1 - 0.7 * sm(x0 + 80, x1, X)) * sm(y0 - .5, y0 + 1, Y)
        draw_ripples(d, Water(seed=31, **WATER), x0, y0, x1, y0 + 22, a, glint_n=24, glint_seed=4)
        d.dots(x0 + 6, y0 + 16, x1 - 6, y1 - 6, 5, .17, S(.38))
        d.line(x0, y0, x0 + 40, y0, S(), .35)
        d.line(x0, y1, x1, y1, K(.2), .25)
        d.text(x0, y0 - 2.4, '풀이', 'pm', 8.2, S())
    def solving(s_, d):
        x = solving_word(d)
        a = lambda X, Y: (1 - 0.85 * sm(x + 8, 243, X)) * sm(271.6, 273.2, Y) * (1 - sm(278.5, 280.5, Y))
        draw_ripples(d, Water(seed=41, **WATER), x + 3, 271.5, 243, 281, a, glint_n=8, glint_seed=3)
    foot = staticmethod(foot_default)
    def logic(s_, d):
        logic_title(d, 'A. 고체')
        rr = lambda X, Y: sm(19, 34, X) * (1 - sm(97, 112, X)) * sm(72, 96, Y) * (1 - sm(200, 260, Y))
        draw_ripples(d, Water(seed=51, **WATER), 19, 72, 112, 262, rr, glint_n=60, glint_seed=8)
        logic_list(d)


# ═══ 03-04 물빛 톤 ══════════════════════════════════════════
class W2(W1):
    name = '03-04(물빛 톤)'
    wt = Water(seed=7, lam=0.8, amp=0.45, wx=3.4, bunch=0.2, patch_scale=30, patch_lo=-0.7, stone_scale=7)
    def head(s_, d, side):
        a = lambda X, Y: (0.6 + 0.4 * gut(X, 170)) * fadeX(X) * (1 - sm(10, 26, Y))
        wash(d, 0, 0, W, 28, water_tone(W2.wt, a, k_stone=0.06, k_rip=0.2))
        g = W2.wt.glints(5 if side == 'even' else 6, d.dx, 0, d.dx + W, 18, 80, lambda x, y: float(a(x, y)))
        sh = d.p.new_shape()
        for x, y, r in g: sh.draw_circle(f.Point(m(x - d.dx), m(y)), m(r))
        sh.finish(fill=S(), color=None); sh.commit()
    def note(s_, d):
        x0, y0, x1, y1 = NOTE
        wt = Water(seed=17, lam=0.8, amp=0.45, wx=3.4, bunch=0.2, patch_scale=30, patch_lo=-0.7, stone_scale=7)
        a = lambda X, Y: (1 - sm(y0 + 6, y0 + 40, Y)) * sm(y0, y0 + 1.5, Y)
        wash(d, x0, y0, x1, y0 + 42, water_tone(wt, a, k_stone=0.035, k_rip=0.11))
        d.dots(x0 + 6, y0 + 16, x1 - 6, y1 - 6, 5, .17, S(.38))
        d.line(x0, y1, x1, y1, K(.2), .25)
        d.text(x0, y0 - 2.4, '풀이', 'pm', 8.2, S())
    def solving(s_, d):
        x = solving_word(d)
        wt = Water(seed=19, lam=0.8, amp=0.45, wx=3.4, bunch=0.2, patch_scale=30, patch_lo=-0.7, stone_scale=7)
        a = lambda X, Y: (1 - 0.85 * sm(x + 8, 243, X)) * sm(271.5, 273.5, Y) * (1 - sm(278, 281, Y))
        wash(d, x + 3, 271, 243, 282, water_tone(wt, a, k_stone=0.05, k_rip=0.22))
    def logic(s_, d):
        logic_title(d, 'A. 고체')
        wt = Water(seed=27, lam=0.8, amp=0.45, wx=3.4, bunch=0.2, patch_scale=30, patch_lo=-0.7, stone_scale=7)
        a = lambda X, Y: sm(19, 36, X) * (1 - sm(95, 112, X)) * sm(72, 100, Y) * (1 - sm(200, 270, Y))
        wash(d, 19, 72, 112, 270, water_tone(wt, a, k_stone=0.06, k_rip=0.2))
        logic_list(d)


# ═══ 03-05 핀이 물에 비침 ═══════════════════════════════════
# 첫 사진 왼쪽 건물처럼: 위에는 곧은 세로 핀, 수면(13mm) 아래로는 같은 핀이 물결에 휘며 끊겨 비친다.
class FW(F1):
    name = '03-05(핀이 물에 비침)'
    WL = 13.0
    wt = Water(seed=9, **WATER)
    @staticmethod
    def items():
        bot = lambda X: FW.WL
        fl = lambda X, y: (0.8 + 0.15 * float(gut(X, 170))) * float(fadeX(X)) ** .5
        it = fins(6, 1.1, SW, 2.2, 0, bot, 1.8, fl, gap=0.28,
                  palette=[('S', 1.0, 4), ('S', .7, 3), ('S', .45, 3), ('S', .25, 2), ('K', .5, 1)])
        return [(x, ya, min(yb, FW.WL), ink, t) for x, ya, yb, ink, t in it if ya < FW.WL - 0.5]
    def head(s_, d, side):
        items = [it for it in FW.items() if it[2] > FW.WL - 1.9]   # 수면에 닿는 핀만 비친다
        draw_fins(d, FW.items(), lambda x, y: 0.5 + 0.5 * float(fadeX(x)))
        d.line(-1, FW.WL + 0.35, W + 1, FW.WL + 0.35, K(.4), .22)
        # 반영: 같은 핀이 수면 아래로 흔들리며 이어지는 세로 획(아래로 갈수록 크게 흔들리고 끊기며 연해짐)
        n1, n2 = Noise(91, 2.6, dirs=0.35), Noise(92, 1.6)
        rng = np.random.default_rng(4)
        sh = d.p.new_shape()
        for x, ya, yb, ink, t in items:
            px = x - d.dx
            if px < -3 or px > W + 3: continue
            Lr = 6 + 7 * float(rng.uniform()) * float(0.4 + 0.6 * fadeX(x))
            run = []
            ys = np.arange(FW.WL + 0.8, FW.WL + 0.8 + Lr, 0.12)
            for y in list(ys) + [None]:
                ok = y is not None and float(n2(x * 2, y * 1.4)) > -0.35
                if ok:
                    depth = (y - FW.WL) / 13
                    ox = (0.25 + 1.5 * depth) * float(n1(x, y * 1.6))
                    run.append((px + ox, y, depth))
                    continue
                if len(run) > 3:
                    dep = run[len(run) // 2][2]
                    a = t * (0.8 - 0.75 * dep) * float(0.45 + 0.55 * fadeX(x))
                    if a > 0.05:
                        sh.draw_polyline([f.Point(m(u), m(v)) for u, v, _ in run])
                        sh.finish(color=tint(S_ if ink == 'S' else K_, a), width=FIN_W / 0.3528 * (1 + 0.8 * dep), lineCap=0, lineJoin=1, closePath=False)
                run = []
        sh.commit()
    def note(s_, d):
        W1.note(s_, d)
    def solving(s_, d):
        F1.solving(s_, d)


CONCEPTS = {'1': F1, '2': F2, '3': W1, '4': W2, '5': FW}

if __name__ == '__main__':
    SRC, RES, OUTD = sys.argv[1:4]
    which = sys.argv[4:] or list(CONCEPTS)
    os.makedirs(OUTD, exist_ok=True)
    src, res = f.open(SRC), f.open(RES)
    for k in which:
        C = CONCEPTS[k]
        print(build(C, src, res, f'{OUTD}/Squeeze_내지_{C.name}.pdf'), flush=True)
