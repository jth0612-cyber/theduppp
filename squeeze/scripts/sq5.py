# Squeeze 내지 시안 5종 (02-01 ~ 02-05). 인수인계 4b 등고선 머리 그림의 기준을 따른다:
#  - 펼침면(가로 524mm) 전체가 한 장면, 제본선(X=262) 기준 대칭
#  - 0.2pt 안팎의 헤어라인, smoothstep 페이드, 아주 옅은 별색 톤(≤12%)
#  - 2도(먹 + 별색). 별색은 자리표시 #00A2DB
# 사용: python sq5.py <squeeze.pdf> <resources.pdf> <출력폴더> [시안번호...]
import sys, math, io, os
import numpy as np
from PIL import Image
sys.path.insert(0, '.')
from sq_lib import *

SW, G = W * 2, W            # 펼침면 폭, 제본선
SA = np.array(S_)

def sm(e0, e1, x):
    t = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)
def bump(x, c, w): return np.exp(-((np.asarray(x, float) - c) / w) ** 2)

# ── 그리기 기본 ────────────────────────────────────────────
def wash(d, x0, y0, x1, y1, fn, dpi=360):
    """별색 농도 이미지(부드러운 톤). fn(X, Y) → 0~1, X는 펼침면 좌표."""
    nx, ny = max(int((x1 - x0) / 25.4 * dpi), 2), max(int((y1 - y0) / 25.4 * dpi), 2)
    xs = x0 + (np.arange(nx) + .5) * (x1 - x0) / nx + d.dx
    ys = y0 + (np.arange(ny) + .5) * (y1 - y0) / ny
    X, Y = np.meshgrid(xs, ys)
    t = np.clip(fn(X, Y), 0, 1)[..., None]
    rgb = 255 * (1 - t * (1 - SA))
    buf = io.BytesIO(); Image.fromarray(np.round(rgb).astype(np.uint8)).save(buf, 'PNG')
    d.p.insert_image(R(x0, y0, x1, y1), stream=buf.getvalue())

def vline(d, pts, alpha, w=0.22, ink=None, step=1.2):
    """농도가 길이를 따라 변하는 선. pts: 펼침면 좌표 [(X, y)], alpha: 각 점 농도."""
    ink = SA if ink is None else np.array(ink)
    sh = d.p.new_shape(); i = 0; n = len(pts)
    while i < n - 1:
        j = i + 1; L = 0
        while j < n - 1 and L < step:
            L += math.hypot(pts[j][0] - pts[j - 1][0], pts[j][1] - pts[j - 1][1]); j += 1
        a = float(np.mean(alpha[i:j + 1]))
        if a > 0.02:
            seg = [f.Point(m(x - d.dx), m(y)) for x, y in pts[i:j + 1]]
            if max(p.x for p in seg) > -20 and min(p.x for p in seg) < m(W) + 20:
                sh.draw_polyline(seg)
                sh.finish(color=tuple(1 - a * (1 - c) for c in ink), width=w, lineCap=1, lineJoin=1, closePath=False)
        i = j
    sh.commit()

def ellipse(d, cx, cy, a, b, rot, w, color, n=180):
    c, s = math.cos(rot), math.sin(rot)
    pts = [f.Point(m(cx - d.dx + a * math.cos(t) * c - b * math.sin(t) * s), m(cy + a * math.cos(t) * s + b * math.sin(t) * c))
           for t in np.linspace(0, 2 * math.pi, n)]
    d.p.draw_polyline(pts, color=color, width=w, closePath=True)

def side_dx(side): return 0 if side == 'even' else W

# ── 공용 글자 체계 ─────────────────────────────────────────
# 머리 기준선 31, 번호 47, 하단 359 / 단원명 11.5pt, 출처 8.2pt, 하단 9pt
def label_default(d, side, unit):
    if side == 'even':
        x = 19 + d.text(19, 31, '기출', 'ps', 14, K())
        d.text(x + 2.2, 31, 'EXTRACT 2', 'pl', 14, K(), track=50)
    else:
        w2 = d.width(unit[1], 'ps', 14)
        d.text(243, 31, unit[1], 'ps', 14, K(), 'r')
        d.text(243 - w2 - 2.6, 31.4, unit[0], 'md', 16.5, S(), 'r')

def foot_default(d, side, no):
    if side == 'even':
        d.text(19, 359, str(no), 'pm', 9, K())
        x = 27 + d.text(27, 359.2, 'Squeeze', 'md', 11.5, K())
        d.text(x + 1.8, 359, '기출 2', 'pl', 7.8, K(.6))
    else:
        d.text(243, 359, str(no), 'pm', 9, K(), 'r')
        d.logo(206.5, 355.3, 4.0)

def num_md(d, side, no, lab, color=None, size=30):
    color = color or S()
    if side == 'odd':
        d.text(108, 47, no, 'md', size, color, 'r')
        d.text(108, 53.6, lab, 'pr', 8.2, K(.68), 'r')
    else:
        wd = d.text(19, 47, no, 'md', size, color)
        d.text(19 + wd + 4, 46.5, lab, 'pr', 8.2, K(.68))
        return wd

def logic_list(d, numfont='md', numcolor=None, box='round'):
    numcolor = numcolor or S()
    d.line(128, 40, 128, 347, K(.25), .25)
    y = 47
    d.line(136, y - 7.4, 243, y - 7.4, K(.6), .3)
    for r in d.rows:
        if numfont == 'md': d.text(136, y, r['no'], 'md', 13.5, numcolor)
        else: d.text(136, y - .2, r['no'], numfont, 11.5, numcolor)
        d.text(153, y - .3, r['src'], 'pr', 8.8, K(.85))
        d.text(219.5, y - .3, '회독', 'pl', 7.8, K(.55))
        for k in range(2):
            bx = 229 + k * 5.4
            if box == 'round': d.rect(bx, y - 3.4, bx + 3.6, y + .2, None, S(), .4, radius=.3)
            else: d.rect(bx, y - 3.4, bx + 3.6, y + .2, None, K(.7), .3)
        d.line(136, y + 3.7, 243, y + 3.7, K(.14), .25)
        y += 10.5

def logic_title(d, unit, font='md'):
    if font == 'md': d.text(19, 52, 'Logic Check', 'md', 28, K())
    else: d.text(19, 51, 'Logic Check', font, 26, K())
    d.text(19, 60, unit, 'pl', 10.5, K(.65))

def solving_word(d, color=None):
    return 134 + d.text(134, 278.4, 'Solving', 'md', 14, color or S())

NOTE = (20, 190, 244, 347)


# ═══ 01 등고선 비틀림 ═══════════════════════════════════════
# 인수인계 4b 등고선을 그대로 잇는다: 가는 선 9줄이 제본선으로 완만하게 처지고, 양쪽 바깥 절반에서
# 띠가 한 점으로 눌렸다가(squeeze) 뒤집혀 나오며 반 바퀴 비틀린다(회전·매듭).
class C01:
    name = '02-01(등고선 비틀림)'
    N, P = 9, 1.15
    @staticmethod
    def band(X):
        s = bump(X, G, 150)
        yc = 9.5 + 5.5 * s
        c = np.cos(np.pi * sm(150, 200, X)) * 0 + 1
        # 비틀림: X=175, 349 부근에서 간격 부호가 바뀜(두 번 → 원래 순서로 복귀)
        c = np.cos(np.pi * (sm(150, 200, X) + sm(324, 374, X)))
        fade = 1 - 0.62 * np.maximum(1 - sm(19, 120, X), sm(SW - 120, SW - 19, X))
        return s, yc, c, fade
    def head(s_, d, side):
        X = np.linspace(-4, SW + 4, 2400)
        s, yc, c, fade = C01.band(X)
        # 톤: 위쪽 가장자리에서 띠 아래까지 은은하게(인수인계 톤 깔기와 같은 방식)
        def tone(XX, YY):
            ss, yy, cc, ff = C01.band(XX)
            depth = yy + C01.N * C01.P * np.abs(cc) / 2 + 3
            return 0.11 * np.clip((depth - YY) / depth, 0, 1) ** 0.8 * (0.25 + 0.75 * ss) * ff * sm(-1, 3, depth - YY)
        wash(d, 0, 0, W, 26, tone)
        for k in range(C01.N):
            o = (k - (C01.N - 1) / 2) * C01.P
            y = yc + o * c
            a = (0.32 + 0.5 * s) * fade * (0.75 + 0.25 * np.abs(c))
            vline(d, list(zip(X, y)), a, w=0.22)
    label = staticmethod(label_default)
    def num(s_, d, side, no, lab):
        num_md(d, side, no, lab)
    def note(s_, d):
        x0, y0, x1, y1 = NOTE
        wash(d, x0, y0, x1, y1, lambda XX, YY: 0.035 * sm(y0 + 2, y0 + 30, YY) + 0 * XX)
        X = np.linspace(x0, x1, 900)
        for k in range(3):
            y = y0 + k * 1.1 + 0 * X
            a = 1.0 - 0.22 * k + 0 * X
            a = a * (1 - 0.8 * sm(x0 + 60, x1, X))
            vline(d, list(zip(X, y)), a, w=0.22)
        d.dots(x0 + 6, y0 + 10, x1 - 6, y1 - 6, 5, .17, S(.38))
        d.line(x0, y1, x1, y1, K(.2), .25)
        d.text(x0, y0 - 2.4, '풀이', 'pm', 8.2, S())
    def solving(s_, d):
        x = solving_word(d)
        X = np.linspace(x + 3, 243, 600)
        for k in range(3):
            y = 275.2 + k * 1.0 + 0 * X
            vline(d, list(zip(X, y)), (0.8 - 0.22 * k) * (1 - 0.85 * sm(x + 20, 243, X)), w=0.22)
    foot = staticmethod(foot_default)
    def logic(s_, d):
        logic_title(d, 'A. 고체')
        # 세로로 흐르는 등고선 띠가 가운데서 한 번 비틀림
        Y = np.linspace(70, 340, 1600)
        c = np.cos(np.pi * sm(180, 236, Y))
        xc = 60 + 14 * np.sin((Y - 70) / 270 * np.pi) ** 2
        for k in range(11):
            o = (k - 5) * 1.6
            a = (0.35 + 0.45 * bump(Y, 208, 90)) * (0.7 + 0.3 * np.abs(c))
            vline(d, list(zip(xc + o * c, Y)), a, w=0.22)
        logic_list(d)


# ═══ 02 루버 ═══════════════════════════════════════════════
# 국립신미술관의 물결치는 유리 루버: 0.85mm 간격 수직 헤어라인. 길이가 펼침면 전체에서 물결치며,
# 제본선 쪽이 깊고 단원명 쪽으로 smoothstep으로 짧아지고 연해진다.
class C02:
    name = '02-02(루버)'
    @staticmethod
    def L(X):
        s = bump(X, G, 130)
        return 6.5 + 8.5 * s + 2.4 * np.sin(2 * np.pi * (X - G) / 88) * (1 - 0.6 * s), s
    def head(s_, d, side):
        X0 = np.arange(0.425, SW, 0.85)
        L, s = C02.L(X0)
        fade = 1 - 0.65 * np.maximum(1 - sm(19, 130, X0), sm(SW - 130, SW - 19, X0))
        wash(d, 0, 0, W, 24, lambda XX, YY: 0.06 * sm(-0.5, 2.5, C02.L(XX)[0] - YY) * (0.3 + 0.7 * bump(XX, G, 130)))
        sh = d.p.new_shape()
        for x, l, ss, ff in zip(X0, L, s, fade):
            px = x - d.dx
            if px < -1 or px > W + 1: continue
            a = (0.38 + 0.52 * ss) * ff
            sh.draw_line(f.Point(m(px), 0), f.Point(m(px), m(l)))
            sh.finish(color=S(a), width=0.2, lineCap=1)
        sh.commit()
    label = staticmethod(label_default)
    def num(s_, d, side, no, lab):
        if side == 'odd':
            d.text(108, 47, no, 'pe', 30, K(), 'r')
            d.text(108, 53.6, lab, 'pr', 8.2, K(.68), 'r')
            lx = 108 - d.width(lab, 'pr', 8.2) - 2.2
            for i in range(6): d.line(lx - i * 0.85, 50.6, lx - i * 0.85, 53.6, S(.9 - .12 * i), .2)
        else:
            wd = d.text(19, 47, no, 'pe', 30, K())
            for i in range(6): d.line(19 + wd + 3 + i * 0.85, 40.2, 19 + wd + 3 + i * 0.85, 46.6 - i * 0.5, S(.9 - .1 * i), .2)
            d.text(19 + wd + 10.5, 46.5, lab, 'pr', 8.2, K(.68))
    def note(s_, d):
        x0, y0, x1, y1 = NOTE
        sh = d.p.new_shape()
        for i, x in enumerate(np.arange(x0, x1 + .01, 0.85)):
            l = 2.2 + 1.2 * math.sin(i / 9)
            a = 0.85 * (1 - 0.75 * float(sm(x0 + 40, x1, x)))
            sh.draw_line(f.Point(m(x), m(y0)), f.Point(m(x), m(y0 + l))); sh.finish(color=S(a), width=0.2, lineCap=1)
        sh.commit()
        d.dots(x0 + 6, y0 + 10, x1 - 6, y1 - 6, 5, .17, S(.38))
        d.line(x0, y1, x1, y1, K(.2), .25)
        d.text(x0, y0 - 2.4, '풀이', 'pm', 8.2, S())
    def solving(s_, d):
        x = solving_word(d)
        sh = d.p.new_shape()
        for i, xx in enumerate(np.arange(x + 3, 243, 0.85)):
            l = 3.6 * (1 - 0.85 * float(sm(x + 3, 243, xx))) + 0.4
            sh.draw_line(f.Point(m(xx), m(278.4 - l)), f.Point(m(xx), m(278.4)))
            sh.finish(color=S(0.9 - 0.6 * float(sm(x, 243, xx))), width=0.2, lineCap=1)
        sh.commit()
    foot = staticmethod(foot_default)
    def logic(s_, d):
        logic_title(d, 'A. 고체')
        sh = d.p.new_shape()
        for i, x in enumerate(np.arange(19, 112, 0.85)):
            t = (x - 19) / 93
            L = 26 + 12 * math.sin(2 * math.pi * t * 1.3 + .6) + 10 * (1 - t)
            # 위 끝선 고정, 아래로 내려가며 3구간으로 끊어 smoothstep처럼 연해짐
            for k, (a0, a1) in enumerate(((0, .55), (.55, .8), (.8, 1))):
                sh.draw_line(f.Point(m(x), m(72 + L * a0)), f.Point(m(x), m(72 + L * a1)))
                sh.finish(color=S((0.75 - 0.25 * t) * (1, .55, .25)[k]), width=0.2, lineCap=1)
        sh.commit()
        logic_list(d)


# ═══ 03 처마와 수면 ═════════════════════════════════════════
# 다니구치 건축관: 펼침면을 가로지르는 긴 처마(별색 띠 1.1mm)와 그 아래 수면에 비친 가는 선들.
class C03:
    name = '02-03(처마와 수면)'
    def head(s_, d, side):
        # 처마: 바깥 여백(19)부터 제본선을 넘어 반대쪽 여백까지
        x0, x1 = 19 - d.dx, SW - 19 - d.dx
        d.rect(max(x0, -1), 12.5, min(x1, W + 1), 13.3, S(), None)
        d.line(-1, 13.3, W + 1, 13.3, K(.55), .25)
        # 수면 반사: 아래로 갈수록 간격이 벌어지고 연해지며, 끊어진 선(물결)
        rng = np.random.default_rng(7)
        ys = [15.0, 16.4, 18.1, 20.1]
        for k, y in enumerate(ys):
            X = 19.0
            while X < SW - 19:
                L = float(rng.uniform(6, 26) * (1 + .5 * k))
                gap = float(rng.uniform(1.5, 5) * (1 + .6 * k))
                xe = min(X + L, SW - 19)
                fadeX = float(0.25 + 0.75 * bump((X + xe) / 2, G, 170))
                a = (0.85 - 0.17 * k) * fadeX
                if a > 0.04:
                    d.line(X - d.dx, y, xe - d.dx, y, S(a), .22, cap=1)
                X = xe + gap
    def label(s_, d, side, unit):
        if side == 'even':
            x = 19 + d.text(19, 31, '기출', 'pm', 13.5, K())
            d.text(x + 2.2, 31, 'EXTRACT 2', 'pl', 13.5, K(), track=110)
        else:
            w2 = d.width(unit[1], 'pm', 13.5, 60)
            d.text(243 - w2, 31, unit[1], 'pm', 13.5, K(), track=60)
            d.text(243 - w2 - 2.6, 31.2, unit[0], 'pl', 13.5, S(), 'r')
    def num(s_, d, side, no, lab):
        if side == 'odd':
            d.text(108, 46, no, 'pl', 26, K(), 'r')
            d.rect(108 - 14, 48.6, 108, 49.5, S(), None)
            d.text(108, 54.2, lab, 'pr', 8.2, K(.68), 'r')
        else:
            wd = d.text(19, 46, no, 'pl', 26, K())
            d.rect(19, 47.6, 19 + wd, 48.3, S(), None)
            d.text(19 + wd + 4, 45.6, lab, 'pr', 8.2, K(.68))
    def note(s_, d):
        x0, y0, x1, y1 = NOTE
        d.rect(x0, y0 - .55, x0 + 34, y0 + .55, S(), None)
        d.line(x0, y0 + .55, x1, y0 + .55, K(.5), .25)
        y = y0 + 10
        while y < y1 - 2:
            d.line(x0, y, x1, y, K(.1), .25); y += 9
        d.text(x0 + 37, y0 - 1.6, '풀이', 'pm', 8.2, S())
    def solving(s_, d):
        x = solving_word(d)
        d.rect(x + 3, 276.0, x + 17, 277.0, S(), None)
        d.line(x + 3, 277.0, 243, 277.0, K(.45), .25)
    def foot(s_, d, side, no):
        d.line(19, 352.4, 243, 352.4, K(.2), .25)
        foot_default(d, side, no)
    def logic(s_, d):
        logic_title(d, 'A. 고체', font='pe')
        d.rect(19, 64, 59, 65.1, S(), None)
        rng = np.random.default_rng(3)
        for k, y in enumerate([66.6, 68.0, 69.7, 71.7, 74.0]):
            X = 19.0
            while X < 112:
                L = float(rng.uniform(4, 16)); xe = min(X + L, 112)
                d.line(X, y, xe, y, S(0.6 - 0.11 * k), .22, cap=1)
                X = xe + float(rng.uniform(1.5, 4) * (1 + .5 * k))
        logic_list(d, numfont='pl', numcolor=K(), box='square')


# ═══ 04 회전 고리 ═══════════════════════════════════════════
# 여러 개의 가는 원이 축을 두고 조금씩 돌아가며 겹쳐, 교차점(매듭)이 수없이 생긴다.
# 펼침면 양 바깥 모서리에 걸린 두 구(球)를, 제본선 위로 지나는 궤도선 하나가 잇는다.
class C04:
    name = '02-04(회전 고리)'
    @staticmethod
    def rings(d, cx, cy, R, n=16, rot1=-0.35, rot2=0.9, w=0.16, amax=0.9, amin=0.35):
        for j, rot in enumerate((rot1, rot2)):
            for i in range(n):
                phi = math.pi * (i + 0.5) / n
                b = R * abs(math.cos(phi))
                a = amin + (amax - amin) * (math.sin(phi) ** 2) * (1 if j == 0 else 0.7)
                ellipse(d, cx, cy, R, b, rot, w, S(a))
    def head(s_, d, side):
        cx = 12 if side == 'even' else SW - 12
        wash(d, 0, 0, W, 34, lambda XX, YY: 0.10 * np.exp(-((np.hypot(XX - cx, YY - 4) / 28) ** 2)))
        C04.rings(d, cx, 4, 19.5, rot1=-0.35 if side == 'even' else 0.35, rot2=0.9 if side == 'even' else -0.9)
        # 궤도선: 두 구를 잇는 큰 타원 호(제본선에서 가장 낮다)
        X = np.linspace(0, SW, 1600)
        y = -42 + 58 * np.sqrt(np.clip(1 - ((X - G) / 262) ** 2, 0, 1))
        a = 0.55 * (1 - 0.4 * bump(X, G, 120)) + 0 * X
        vline(d, list(zip(X, y)), a, w=0.2)
    def label(s_, d, side, unit):
        label_default(d, side, unit)
    def num(s_, d, side, no, lab):
        num_md(d, side, no, lab)
    def note(s_, d):
        x0, y0, x1, y1 = NOTE
        d.rect(x0, y0, x1, y1, None, S(.5), .3, radius=4 / (y1 - y0))
        d.dots(x0 + 7, y0 + 11, x1 - 7, y1 - 7, 5, .17, S(.38))
        wl = d.width('풀이', 'pm', 8.2)
        d.rect(x0 + 11, y0 - 2.5, x0 + 14 + wl, y0 + 2.5, PAPER, None)
        d.text(x0 + 12.5, y0 + 1.2, '풀이', 'pm', 8.2, S())
        C04.rings(d, x0 + 4.5, y0, 3.6, n=7, w=0.14, amin=.5)
    def solving(s_, d):
        x = solving_word(d)
        d.line(x + 3, 276.2, 236, 276.2, S(.6), .22)
        C04.rings(d, 239.5, 276.2, 3.2, n=7, w=0.14, amin=.5)
    foot = staticmethod(foot_default)
    def logic(s_, d):
        logic_title(d, 'A. 고체')
        wash(d, 14, 120, 118, 300, lambda XX, YY: 0.08 * np.exp(-((np.hypot(XX - 66, YY - 205) / 52) ** 2)))
        C04.rings(d, 66, 205, 40, n=22, w=0.16)
        logic_list(d)


# ═══ 05 말랑한 면 ═══════════════════════════════════════════
# 회반죽 벽처럼 둥근 면 두 겹이 위에서 내려오고, 아래로 부드러운 그림자. 양쪽 면이 제본선을 향해
# 눌려 오다 멈춘다(Squeeze). 선은 거의 쓰지 않는다.
def sd_rrect(X, Y, x0, y0, x1, y1, r):
    cx, cy, hx, hy = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2 - r, (y1 - y0) / 2 - r
    qx, qy = np.abs(X - cx) - hx, np.abs(Y - cy) - hy
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r

class C05:
    name = '02-05(말랑한 면)'
    @staticmethod
    def slabs(X, Y):
        out = np.zeros_like(X)
        for xa, xb in ((-20, 246), (SW - 246, SW + 20)):
            d1 = sd_rrect(X, Y, xa, -30, xb, 21, 10)
            d2 = sd_rrect(X, Y, xa, -30, xa + (xb - xa) * 0.62 if xa < 0 else xb - (xb - xa) * 0.62, 14.5, 8) if False else None
            shadow = 0.07 * np.exp(-np.clip(d1, 0, None) / 1.6) * (d1 > 0) * sm(-2, 6, Y - 10)
            out = np.maximum(out, 0.075 * sm(0.35, -0.35, d1) + shadow)
            inner = sd_rrect(X, Y, xa if xa < 0 else xb - 150, -30, xa + 150 if xa < 0 else xb, 14.5, 7.5)
            out = out + 0.06 * sm(0.35, -0.35, inner) + 0.035 * np.exp(-np.clip(inner, 0, None) / 1.2) * (inner > 0) * (d1 < 0)
        return out
    def head(s_, d, side):
        wash(d, 0, 0, W, 28, C05.slabs)
    def label(s_, d, side, unit):
        label_default(d, side, unit)
    def num(s_, d, side, no, lab):
        wd = d.width(no, 'md', 21)
        if side == 'odd':
            x1 = 108; x0 = x1 - wd - 8
            d.rect(x0, 38.6, x1, 48.4, S(.12), None, radius=0.5)
            d.text(x0 + 4, 46.0, no, 'md', 21, K())
            d.text(108, 53.8, lab, 'pr', 8.2, K(.68), 'r')
        else:
            d.rect(19, 38.6, 19 + wd + 8, 48.4, S(.12), None, radius=0.5)
            d.text(23, 46.0, no, 'md', 21, K())
            d.text(19 + wd + 11.5, 45.4, lab, 'pr', 8.2, K(.68))
    def note(s_, d):
        x0, y0, x1, y1 = NOTE
        wash(d, x0 - 3, y0 - 3, x1 + 3, y1 + 4,
             lambda XX, YY: 0.05 * sm(0.3, -0.3, sd_rrect(XX, YY, x0, y0, x1, y1, 5))
             + 0.05 * np.exp(-np.clip(sd_rrect(XX, YY, x0, y0, x1, y1, 5), 0, None) / 1.3) * (sd_rrect(XX, YY, x0, y0, x1, y1, 5) > 0) * sm(-1, 2, YY - (y0 + 6)))
        d.dots(x0 + 7, y0 + 13, x1 - 7, y1 - 7, 5, .17, S(.35))
        wl = d.width('풀이', 'pm', 8.2)
        d.rect(x0 + 5, y0 + 4, x0 + 13 + wl, y0 + 9.6, S(.16), None, radius=0.5)
        d.text(x0 + 9, y0 + 8, '풀이', 'pm', 8.2, K())
    def solving(s_, d):
        wd = d.width('Solving', 'md', 13)
        d.rect(134, 272.4, 134 + wd + 8, 280.2, S(.14), None, radius=0.5)
        d.text(138, 278.2, 'Solving', 'md', 13, K())
        d.rect(134 + wd + 11, 275.9, 243, 276.7, S(.14), None, radius=0.5)
    foot = staticmethod(foot_default)
    def logic(s_, d):
        logic_title(d, 'A. 고체')
        wash(d, 14, 70, 122, 330, lambda XX, YY: 0.06 * sm(0.3, -0.3, sd_rrect(XX, YY, 19, 76, 112, 300, 12))
             + 0.05 * np.exp(-np.clip(sd_rrect(XX, YY, 19, 76, 112, 300, 12), 0, None) / 1.6) * (sd_rrect(XX, YY, 19, 76, 112, 300, 12) > 0) * sm(0, 4, YY - 90)
             + 0.07 * sm(0.3, -0.3, sd_rrect(XX, YY, 19, 76, 112, 150, 12)))
        logic_list(d)


CONCEPTS = {'1': C01, '2': C02, '3': C03, '4': C04, '5': C05}
UNIT = {'A': ('A', '고체'), 'B': ('B', '유체'), 'C': ('C', '천체')}

def build(C, src, res, out_pdf, pages=(4, 5, 6, 7)):
    c = C()
    out = f.open()
    out.insert_pdf(src, from_page=pages[0] - 1, to_page=pages[-1] - 1)
    rows = logic_rows(src, 4)
    for i, pg in enumerate(pages):
        page = out[i]
        side = 'odd' if pg % 2 else 'even'
        if pg == 4:
            strip_frame(page, 'logic')
        else:
            strip_frame(page, side)
        d = P(page, res); d.rows = rows
        d.dx = side_dx(side); c.head(d, side); d.dx = 0
        if pg == 4:
            c.label(d, 'even', None); c.logic(d); c.foot(d, 'even', 4); continue
        no, lab = prob_info(src, pg)
        c.label(d, side, UNIT[no[0]])
        c.num(d, side, no, lab)
        (c.note if side == 'odd' else c.solving)(d)
        c.foot(d, side, pg)
    out.subset_fonts()
    out.save(out_pdf, garbage=4, deflate=True)
    return out_pdf

if __name__ == '__main__':
    SRC, RES, OUTD = sys.argv[1:4]
    which = sys.argv[4:] or list(CONCEPTS)
    os.makedirs(OUTD, exist_ok=True)
    src, res = f.open(SRC), f.open(RES)
    for k in which:
        C = CONCEPTS[k]
        print(build(C, src, res, f'{OUTD}/Squeeze_내지_{C.name}.pdf'))
