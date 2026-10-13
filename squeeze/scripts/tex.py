# 사진에서 읽은 질감 생성기: 세로 핀(건물 외벽) / 물결(잔물결 줄무늬·돌 그림자·반짝임)
import math
import numpy as np
from skimage import measure

def sm(e0, e1, x):
    t = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)

class Noise:
    """매끈한 2D 잡음: 무작위 방향·파장의 사인파 합. 값 범위 대략 -1~1."""
    def __init__(self, seed, scale, n=9, spread=0.55, dirs=None):
        r = np.random.default_rng(seed)
        self.k = []
        for i in range(n):
            th = r.uniform(0, 2 * np.pi) if dirs is None else r.uniform(-dirs, dirs)
            lam = scale * r.uniform(1 - spread, 1 + spread)
            self.k.append((math.cos(th) * 2 * np.pi / lam, math.sin(th) * 2 * np.pi / lam, r.uniform(0, 2 * np.pi), r.uniform(.6, 1)))
        self.norm = math.sqrt(sum(a * a for *_, a in self.k) / 2)
    def __call__(self, X, Y):
        return sum(a * np.sin(kx * X + ky * Y + p) for kx, ky, p, a in self.k) / self.norm / 1.6

# ── 세로 핀 ───────────────────────────────────────────────
# 사진: 기둥 간격마다 가는 핀, 층 단위(모듈)로 끊긴 토막, 토막마다 다른 농도, 시작·끝이 엇갈림.
PALETTE = [('S', 1.0, 3), ('S', .7, 3), ('S', .45, 3), ('S', .25, 2), ('K', .55, 1), ('K', .3, 1)]

def fins(seed, X0, X1, pitch, top, bottom_fn, module, fill_fn, palette=PALETTE, gap=0.0):
    """→ [(x, y0, y1, ink, tint)]. bottom_fn(X): 기둥별 아래 끝(mm), fill_fn(X, y): 토막이 채워질 확률(0~1)."""
    r = np.random.default_rng(seed)
    inks = [(p[0], p[1]) for p in palette]; w = np.array([p[2] for p in palette], float); w /= w.sum()
    out = []
    x = X0
    while x <= X1 + 1e-6:
        bot = bottom_fn(x)
        nmod = int(math.floor((bot - top) / module + r.uniform(0, 1)))
        y = top
        i = 0
        while i < nmod:
            L = int(r.choice([1, 2, 2, 3, 3, 4, 5, 6]))
            L = min(L, nmod - i)
            ya, yb = top + i * module, top + (i + L) * module
            if r.uniform() < fill_fn(x, (ya + yb) / 2):
                ink, t = inks[r.choice(len(inks), p=w)]
                out.append((x, ya + gap / 2, yb - gap / 2, ink, t))
            i += L
        x += pitch
    return out

# ── 물결 ──────────────────────────────────────────────────
# 사진: 가늘고 촘촘한 물결 줄무늬가 군데군데 뭉쳐 일렁이고, 아래로 돌 그림자, 위로 반짝임 무리.
class Water:
    """가로로 늘어난 물결 줄무늬. phase = (Y + 휘어짐(X 위주)) / 간격(곳에 따라 몰림)."""
    def __init__(self, seed=1, lam=0.9, amp=0.9, wx=7.0, patch_scale=24.0, bunch=0.38, tilt=0.0, patch_lo=-0.25, stone_scale=None):
        self.lam, self.amp, self.bunch, self.tilt, self.patch_lo = lam, amp, bunch, tilt, patch_lo
        self.n1 = Noise(seed, wx, dirs=0.5)                  # 가로로 일렁이는 휘어짐
        self.n2 = Noise(seed + 5, wx * 0.38, dirs=0.7)       # 잔떨림
        self.nb = Noise(seed + 6, patch_scale * 0.5)         # 줄 간격 몰림
        self.patch = Noise(seed + 2, patch_scale)            # 줄무늬가 보이는 곳
        self.stone = Noise(seed + 3, stone_scale or patch_scale * .55, n=12)
        self.glint = Noise(seed + 4, 5.0)
    def phase(self, X, Y):
        lam = self.lam * (1 + self.bunch * self.nb(X, Y))
        return (Y + self.tilt * X + self.amp * self.n1(X, Y) + 0.35 * self.amp * self.n2(X, Y)) / lam
    def patchiness(self, X, Y):
        return sm(self.patch_lo, 0.5, self.patch(X, Y))
    def stones(self, X, Y):
        return sm(0.05, 0.45, self.stone(X, Y))
    def ripple_lines(self, x0, y0, x1, y1, res=0.07):
        nx, ny = int((x1 - x0) / res) + 1, int((y1 - y0) / res) + 1
        xs = np.linspace(x0, x1, nx); ys = np.linspace(y0, y1, ny)
        X, Y = np.meshgrid(xs, ys)
        F = np.sin(np.pi * self.phase(X, Y))
        return [(x0 + c[:, 1] * res, y0 + c[:, 0] * res) for c in measure.find_contours(F, 0.0)]
    def glints(self, seed, x0, y0, x1, y1, n, mask):
        r = np.random.default_rng(seed)
        pts = []; tries = 0
        while len(pts) < n and tries < n * 80:
            tries += 1
            x, y = r.uniform(x0, x1), r.uniform(y0, y1)
            p = float(self.patchiness(x, y) * sm(0.3, 0.8, self.glint(x, y)) * mask(x, y))
            if r.uniform() < p ** 1.5:
                for j in range(int(r.integers(2, 7))):
                    pts.append((x + r.normal(0, .7), y + r.normal(0, .16), float(r.uniform(.06, .15))))
        return pts
