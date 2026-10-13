# Squeeze 03-01-08: 03-01-07 + 번호 글꼴 02(Barlow Condensed Light) + 풀이 칸 원본 배경 점(아주 흐리게)
#                  + Solving 핀 3안(간격 좁힘, 회색 핀 섞음)
# 사용: python sq9.py <squeeze.pdf> <resources.pdf> <출력폴더>
import sys, os, math
import numpy as np
sys.path.insert(0, '.')
import sq8
from sq8 import (Base, set_numfont, draw_icon, icon_paths, solving_word, fins, draw_fins, Noise, sm, fadeX,
                 build, f, m, R, W, S, K, S_, K_, tint, PAL)
from sq7 import NOTE

# ── 풀이 칸: P3(가는 선 + 핀 표식 + 라벨) + 원본 배경 점 위치 그대로, 아주 흐리게 ─────────
DOT_T = 0.14            # 별색 농도 (원본 #6EC8EC ≈ 55%)
DOTS = None
def orig_dots(src):
    global DOTS
    if DOTS is None:
        MM = 72 / 25.4; DOTS = []
        for g in src[4].get_drawings():
            fl = g.get('fill')
            if fl and tuple(round(c * 255) for c in fl) == (0x6E, 0xC8, 0xEC) and g['rect'].width < 2:
                r = g['rect']; DOTS.append(((r.x0 + r.x1) / 2 / MM, (r.y0 + r.y1) / 2 / MM))
    return DOTS

def note(d):
    x0, y0, x1, y1 = NOTE
    sh = d.p.new_shape()
    for x, y in orig_dots(SRC_DOC):
        sh.draw_circle(f.Point(m(x), m(y)), m(0.25))
    sh.finish(fill=S(DOT_T), color=None); sh.commit()
    d.line(x0, y0, x1, y0, K(.35), .25)
    sq8.fin_stack(d, x0 + 0.3, y0 - 5.6, [(2.6, S_, 1), (2.2, S_, .45)], w=0.5)
    d.text(x0 + 2.4, y0 - 2.0, '풀이', 'pm', 8.2, S())

# ── Solving 3안 ─────────────────────────────────────────
GRAY = [('K', .45), ('K', .25)]
def mix_gray(items, seed, every=(4, 7), bottom_bias=True):
    """사이사이 회색: 4~7개마다 하나, 이웃끼리 연달아 오지 않게."""
    r = np.random.default_rng(seed); out = []; k = int(r.integers(*every))
    for i, it in enumerate(items):
        k -= 1
        if k <= 0:
            x, ya, yb, ink, t = it
            g = GRAY[0] if r.uniform() < .65 else GRAY[1]
            out.append((x, ya, yb, g[0], g[1])); k = int(r.integers(*every))
        else:
            out.append(it)
    return out

def icon_slot():
    ih = 5.0
    iw = icon_paths()[0].width / icon_paths()[0].height * ih
    return 243 - iw, ih

def S1(d):
    """1안: 간격 1.5mm, 길이가 매끄럽게 줄어듦 + 회색 사이사이."""
    x = solving_word(d); ix, ih = icon_slot(); draw_icon(d, ix, 276.0 - ih / 2, ih)
    r = np.random.default_rng(31); its = []; xx = x + 3.5; x1 = ix - 4.0
    inks = [(p[0], p[1]) for p in PAL]; w = np.array([p[2] for p in PAL], float); w /= w.sum()
    while xx <= x1:
        t = (xx - x - 3.5) / (x1 - x - 3.5)
        L = max(5.0 + (1.4 - 5.0) * float(sm(0, 1, t)) + 0.6 * int(r.integers(-1, 2)), 0.8)
        ink, a = inks[r.choice(len(inks), p=w)]
        its.append((xx, 273.6, 273.6 + L, ink, a * (1 - 0.45 * float(sm(.15, 1, t))))); xx += 1.5
    draw_fins(d, mix_gray(its, 3), wfin=0.3)

def S2(d):
    """2안: 간격 1.1mm, 상단처럼 층 단위로 끊긴 토막이 매달림(작은 외벽) + 회색 사이사이."""
    x = solving_word(d); ix, ih = icon_slot(); draw_icon(d, ix, 276.0 - ih / 2, ih)
    x0, x1 = x + 3.5, ix - 4.0
    bot = lambda X: 273.6 + 5.2 - 3.6 * float(sm(x0, x1, X))
    its = fins(33, x0, x1, 1.1, 273.6, bot, 1.0, lambda X, y: 0.95, gap=0.2, palette=PAL)
    draw_fins(d, mix_gray(its, 5, every=(5, 9)), lambda X, y: 1 - 0.45 * float(sm(x0 + 10, x1, X)), wfin=0.26)

def S3(d):
    """3안: 간격 1.1mm, 상단과 같은 무작위 윤곽(내려갔다 올라옴), 아래 끝 위주로 회색."""
    x = solving_word(d); ix, ih = icon_slot(); draw_icon(d, ix, 276.0 - ih / 2, ih)
    x0, x1 = x + 3.5, ix - 4.0
    na, nb = Noise(818, 26, dirs=0.3), Noise(819, 9, dirs=0.4)
    bot = lambda X: 273.6 + 1.2 + 4.0 * float(sm(-0.7, 0.7, 0.7 * na(X, 0) + 0.3 * nb(X, 0))) * (1 - 0.5 * float(sm(x0, x1, X)))
    its = fins(34, x0, x1, 1.1, 273.6, bot, 1.0, lambda X, y: 0.95, gap=0.2, palette=PAL)
    last = {}
    for i, it in enumerate(its): last[it[0]] = i
    r = np.random.default_rng(9); out = []; prev = -9
    for i, (xx, ya, yb, ink, a) in enumerate(its):
        if last[xx] == i and yb > 276.4 and xx - prev > 2.3 and r.uniform() < .55:
            out.append((xx, ya, yb, 'K', .45)); prev = xx
        else: out.append((xx, ya, yb, ink, a))
    draw_fins(d, out, lambda X, y: 1 - 0.45 * float(sm(x0 + 10, x1, X)), wfin=0.26)

SOLVINGS = [('1안', '간격 1.5mm·매끄럽게 줄어듦', S1), ('2안', '간격 1.1mm·층 토막 작은 외벽', S2), ('3안', '간격 1.1mm·무작위 윤곽', S3)]

if __name__ == '__main__':
    SRC, RESP, OUTD = sys.argv[1:4]
    os.makedirs(OUTD, exist_ok=True)
    SRC_DOC = f.open(SRC); sq8.RES = f.open(RESP)
    set_numfont('fs/ttf/barlow-condensed-300.ttf')
    for code, desc, fn in SOLVINGS:
        class C(Base):
            name = f'03-01-08(Solving {code} {desc})'
        C.note = lambda s_, d: note(d)
        C.solving = (lambda fn_: (lambda s_, d: fn_(d)))(fn)
        print(build(C, SRC_DOC, sq8.RES, f'{OUTD}/Squeeze_내지_{C.name}.pdf'), flush=True)
