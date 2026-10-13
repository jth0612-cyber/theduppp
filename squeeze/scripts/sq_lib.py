# Squeeze 내지 공용: 원본 읽기, 틀 지우기, 그리기 도우미, 매듭 튜브 렌더러.
import math, re
import pymupdf as f

MM = 72 / 25.4
W, H = 262, 371
m = lambda v: v * MM
R = lambda x0, y0, x1, y1: f.Rect(m(x0), m(y0), m(x1), m(y1))
FD = 'npm/package/dist/public/static/alternative'
FONTS = {
    'md': 'md/Million Dreams.otf',
    'pe': f'{FD}/Pretendard-ExtraLight.ttf', 'pl': f'{FD}/Pretendard-Light.ttf',
    'pr': f'{FD}/Pretendard-Regular.ttf', 'pm': f'{FD}/Pretendard-Medium.ttf',
    'ps': f'{FD}/Pretendard-SemiBold.ttf', 'pb': f'{FD}/Pretendard-Bold.ttf',
}
FO = {k: f.Font(fontfile=v) for k, v in FONTS.items()}

# 2도: 먹(K) + 별색(S, 자리표시 #00A2DB). 모든 색은 두 잉크의 농도.
K_ = (0x23 / 255, 0x1F / 255, 0x20 / 255)
S_ = (0x00 / 255, 0xA2 / 255, 0xDB / 255)
def tint(c, t): return tuple(1 - t * (1 - v) for v in c)
K = lambda t=1: tint(K_, t)
S = lambda t=1: tint(S_, t)
PAPER = (1, 1, 1)

norm = lambda t: re.sub('[‐-―−]', '-', t)

def logic_rows(src, pg):
    rows = {}
    for b in src[pg - 1].get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                y = round(s['bbox'][1] / MM)
                if s['font'].startswith('Montserrat'): rows.setdefault(y, {})['no'] = norm(s['text'])
                elif s['color'] == 0xFFFFFF: rows.setdefault(y, {})['src'] = s['text'].replace('\xa0', ' ')
    return [rows[k] for k in sorted(rows) if 'no' in rows[k]]

def prob_info(src, pg):
    no = lab = None
    for b in src[pg - 1].get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                if s['font'].startswith('Montserrat') and s['size'] > 30: no = norm(s['text'])
                if s['color'] == 0xFFFFFF and '학년도' in s['text']: lab = s['text'].replace('\xa0', ' ')
    return no, lab

def wipe(page, rects):
    for r in rects:
        page.add_redact_annot(R(*r), fill=False)
    page.apply_redactions(images=f.PDF_REDACT_IMAGE_NONE,
                          graphics=f.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED,
                          text=f.PDF_REDACT_TEXT_REMOVE)

def strip_frame(page, kind):
    if kind == 'logic':
        wipe(page, [(-5, -5, W + 5, H + 5)])
    elif kind == 'odd':
        wipe(page, [(-5, -5, W + 5, 30), (-5, 348, W + 5, H + 5), (55, 32, 112, 59), (18, 188, 246, 349)])
    elif kind == 'even':
        wipe(page, [(-5, -5, W + 5, 30), (-5, 348, W + 5, H + 5), (15, 33, 100, 49.9), (133, 271, 243, 280.6)])


class P:
    """한 쪽에 그리는 도우미. dx: 펼침면 좌표 → 이 쪽 좌표 이동량."""
    def __init__(s, page, res=None, dx=0):
        s.p, s.res, s.dx = page, res, dx
        for k, v in FONTS.items():
            page.insert_font(fontname=k, fontfile=v)
    def rect(s, x0, y0, x1, y1, fill=None, color=None, w=0.5, radius=None):
        s.p.draw_rect(R(x0, y0, x1, y1), color=color, fill=fill, width=w, radius=radius)
    def line(s, x0, y0, x1, y1, color, w=0.3, cap=0):
        s.p.draw_line(f.Point(m(x0), m(y0)), f.Point(m(x1), m(y1)), color=color, width=w, lineCap=cap)
    def width(s, text, font, size, track=0):
        return (FO[font].text_length(text, fontsize=size) + track / 1000 * size * max(len(text) - 1, 0)) / MM
    def text(s, x, y, text, font, size, color, align='l', track=0):
        """y = 기준선(mm). track = 자간(1/1000 em)."""
        wd = s.width(text, font, size, track)
        if align == 'r': x -= wd
        elif align == 'c': x -= wd / 2
        if not track:
            s.p.insert_text(f.Point(m(x), m(y)), text, fontname=font, fontsize=size, color=color)
        else:
            cx = m(x)
            for ch in text:
                s.p.insert_text(f.Point(cx, m(y)), ch, fontname=font, fontsize=size, color=color)
                cx += FO[font].text_length(ch, fontsize=size) + track / 1000 * size
        return wd
    def logo(s, x, y, h=4.4):
        clip = R(199.6, 354.2, 224.2, 359.8)
        wd = (224.2 - 199.6) * h / 5.6
        s.p.show_pdf_page(R(x, y, x + wd, y + h), s.res, 21, clip=clip)
        return wd
    def dots(s, x0, y0, x1, y1, step, r, color):
        sh = s.p.new_shape()
        y = y0
        while y <= y1 + 1e-6:
            x = x0
            while x <= x1 + 1e-6:
                sh.draw_circle(f.Point(m(x), m(y)), m(r)); x += step
            y += step
        sh.finish(fill=color, color=None); sh.commit()


# ── 매듭 튜브 ─────────────────────────────────────────────
# 말랑한 관(튜브) 둘레에 가는 선이 나선으로 감긴다. 앞면 선만 보이므로 가장자리로 갈수록 선이 촘촘해져
# 둥근 부피가 선 밀도만으로 생긴다(2도 인쇄에 적합). 관 굵기가 길이를 따라 눌렸다 부풀어(squeeze) 말랑하다.
# 깊이(z) 순서로 [종이색 테두리 → 선]을 그려 교차마다 위·아래가 갈린다.
def smooth(e0, e1, x):
    t = min(max((x - e0) / (e1 - e0), 0), 1)
    return t * t * (3 - 2 * t)

def tube(d, pts, radius, strands=14, twist=6.0, lw=0.22, edge=0.42, color=None, gap=0.6,
         chunk=6, xclip=None):
    """pts: [(x, y, z)] mm, radius: t→반지름(mm).
    짧은 구간(chunk개 조각) 단위로 깊이 정렬: [종이색 면(+틈) → 앞면 나선 선 → 윤곽선]."""
    color = color or S()
    n = len(pts) - 1
    G = []
    for i in range(n + 1):
        x, y, z = pts[i]
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, n)]
        tx, ty = b[0] - a[0], b[1] - a[1]; L = math.hypot(tx, ty) or 1
        G.append((x - d.dx, y, z, -ty / L, tx / L, radius(i / n), i / n))
    chunks = [(j, min(j + chunk, n)) for j in range(0, n, chunk)]
    chunks.sort(key=lambda c: sum(G[i][2] for i in range(c[0], c[1] + 1)) / (c[1] - c[0] + 1))
    P_ = lambda x, y: f.Point(m(x), m(y))
    sh = d.p.new_shape()
    for j0, j1 in chunks:
        seg = G[j0:j1 + 1]
        if xclip and (max(g[0] for g in seg) < xclip[0] - 15 or min(g[0] for g in seg) > xclip[1] + 15):
            continue
        # 종이색 면: 틈(gap)만큼 넓혀 아래 지나가는 관을 끊어 준다
        up = [P_(g[0] + g[3] * (g[5] + gap), g[1] + g[4] * (g[5] + gap)) for g in seg]
        dn = [P_(g[0] - g[3] * (g[5] + gap), g[1] - g[4] * (g[5] + gap)) for g in seg]
        sh.draw_polyline(up + dn[::-1] + [up[0]])
        sh.finish(fill=PAPER, color=None, closePath=True)
        for k in range(strands):
            run = []
            for g in seg + [None]:
                if g is not None:
                    a_ = 2 * math.pi * (k / strands + twist * g[6])
                    if math.sin(a_) >= -0.02:
                        run.append(P_(g[0] + g[3] * g[5] * math.cos(a_), g[1] + g[4] * g[5] * math.cos(a_)))
                        continue
                if len(run) > 1:
                    sh.draw_polyline(run); sh.finish(color=color, width=lw, lineCap=1, lineJoin=1, closePath=False)
                run = []
        for sg in (1, -1):
            sh.draw_polyline([P_(g[0] + sg * g[3] * g[5], g[1] + sg * g[4] * g[5]) for g in seg])
            sh.finish(color=color, width=edge, lineCap=1, lineJoin=1, closePath=False)
    sh.commit()

def spread_knot(n=2600, yc=11.0, X0=-14, X1=W * 2 + 14, loops=13, A=8.4, B=6.6, end=0.2):
    """펼침면(가로 524mm) 하나를 가로지르는 경로. 바깥쪽 끝에서 고리가 크게 맺히고,
    제본선 쪽으로 갈수록 고리가 풀려 완만한 물결이 된다(smoothstep)."""
    pts = []
    for i in range(n + 1):
        t = i / n
        th = 2 * math.pi * loops * t
        e = max(1 - smooth(0, end * 2.2, t), 1 - smooth(0, end * 2.2, 1 - t))   # 양 끝 1 → 가운데 0
        a = A * (0.18 + 0.82 * e); b = B * (0.32 + 0.68 * e)
        x = X0 + (X1 - X0) * t - a * math.sin(th)
        y = yc - b * math.cos(th) + 1.2 * math.sin(2 * math.pi * t)
        pts.append((x, y, math.sin(th)))
    return pts

def loop_mark(x, y, size=7.0, loops=1, n=420, flip=False):
    """작은 매듭 표식: 고리 하나(또는 몇 개)."""
    pts = []
    for i in range(n + 1):
        t = i / n
        th = 2 * math.pi * loops * t - math.pi
        L = size * 1.25
        xx = (L * t - size * 0.42 * math.sin(th))
        yy = -size * 0.36 * math.cos(th)
        pts.append((x + (L - xx if flip else xx), y + yy, math.sin(th)))
    return pts

def torus_knot(cx, cy, scale, p=3, q=7, r=0.48, tilt=24, rotz=6, n=3200):
    ct, st = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
    cz, sz = math.cos(math.radians(rotz)), math.sin(math.radians(rotz))
    pts = []
    for i in range(n + 1):
        t = 2 * math.pi * i / n
        X = (1 + r * math.cos(q * t)) * math.cos(p * t); Y = (1 + r * math.cos(q * t)) * math.sin(p * t); Z = r * math.sin(q * t)
        Y, Z = Y * ct - Z * st, Y * st + Z * ct
        X, Y = X * cz - Y * sz, X * sz + Y * cz
        pts.append((cx + scale * X, cy - scale * Y, Z))
    return pts
