"""LINE_UP 표지 — 빨간 오브제(출렁임)만 바꾼 시안.

원본 표지에서 글자·로고·배지를 떼어 내고, 그 아래의 색 덩어리만 새로 그린 뒤
원본과 같은 세로 유리 줄무늬를 다시 입힌다.

    python3 build.py            # renders/variant-{a,b,c}.png, renders/sheet.png
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "source", "cover.png")
OUT = os.path.join(HERE, "renders")

# 세로 유리 줄무늬: 26.3 px 간격, x = 12.5 에서 한 줄이 끝난다.
PERIOD, OFFSET = 26.3, 12.5
# 한 줄이 아래 그림을 얼마나 압축해서 보여 주는지. 1 이면 굴절 없음.
REFRACT = 0.55

BG = np.array([240.0, 239.0, 239.0])
BADGE_RED = np.array([221.0, 63.0, 55.0])
# 흰 바탕 위 작은 글자의 가장 짙은 값. 책등 저자명처럼 색 위에 얹힌 글자도 이
# 회색으로 다시 얹어야 새 바탕에서 분홍빛이 돌지 않는다.
INK_DARK = np.array([90.0, 90.0, 90.0])

# 원본에서 뽑은 색. 진한 쪽 끝 값이며, 흰 바탕과 섞이면서 분홍 계열로 옅어진다.
RED = np.array([206.0, 70.0, 76.0])
CRIMSON = np.array([176.0, 52.0, 92.0])
MAGENTA = np.array([160.0, 56.0, 120.0])
LAVENDER = np.array([200.0, 140.0, 188.0])

# (종류, x0, y0, x1, y1). d = 짙은 회색 글자, r = 빨간 제목, w = 흰 글자(책등 제목)
TEXT_BOXES = [
    ("d", 50, 30, 215, 82),       # 뒤표지 상단
    ("d", 50, 1280, 310, 1328),   # 뒤표지 로고
    ("d", 980, 20, 1018, 262),    # 책등 상단
    ("d", 982, 930, 1018, 1030),  # 책등 저자
    ("d", 982, 1145, 1018, 1322), # 책등 로고
    ("d", 1068, 128, 1228, 178),  # 앞표지 부제
    ("d", 1068, 1275, 1312, 1325),# 앞표지 로고
    ("d", 1535, 1285, 1628, 1318),# 앞표지 저자
    ("r", 1065, 35, 1950, 120),   # 앞표지 제목
    ("w", 980, 325, 1020, 578),   # 책등 제목
]
BADGES = [(999.5, 669.5, 40.5), (1902.0, 1274.0, 40.5)]


# ---------------------------------------------------------------- 줄무늬 모델

def phase(width):
    return (((np.arange(width) - OFFSET) / PERIOD) % 1.0)


def fit_shading(img, bins=26):
    """줄 위치(위상)마다 out = a * 바탕색 + b 를 맞춘다.

    흰 곳과 색이 짙은 곳을 함께 넣어야 a 와 b 가 갈린다. 흰 곳에서는 줄이 거의
    안 보이고 색이 짙을수록 명암 차가 커지는 원본의 성질이 이 두 값에 담긴다.
    """
    regions = [
        (20, 150, 300, 900), (200, 260, 1100, 1900), (1180, 1250, 1300, 1800),
        (550, 800, 20, 300), (500, 700, 1050, 1300), (750, 900, 1700, 1990),
        (400, 500, 300, 900), (900, 1000, 300, 900), (1000, 1100, 1300, 1700),
    ]
    k = np.minimum((phase(img.shape[1]) * bins).astype(int), bins - 1)
    prof = []
    for y0, y1, x0, x1 in regions:
        sub, kk = img[y0:y1, x0:x1], k[x0:x1]
        prof.append([sub[:, kk == i].reshape(-1, 3).mean(0) for i in range(bins)])
    prof = np.array(prof)
    base = prof.mean(1)
    a, b = [], []
    for i in range(bins):
        A = np.stack([base.ravel(), np.ones(base.size)], 1)
        (ai, bi), *_ = np.linalg.lstsq(A, prof[:, i].ravel(), rcond=None)
        a.append(ai)
        b.append(bi)
    return np.array(a), np.array(b)


def reeded(field, shade):
    """바탕 그림(field)에 세로 유리 줄무늬를 입힌다."""
    h, w, _ = field.shape
    a, b = shade
    bins = len(a)
    x = np.arange(w)
    s = (x - OFFSET) / PERIOD
    u = s - np.floor(s)
    xc = (np.floor(s) + 0.5) * PERIOD + OFFSET
    xs = np.clip(xc + REFRACT * (x - xc), 0, w - 1)
    x0 = np.floor(xs).astype(int)
    x1 = np.minimum(x0 + 1, w - 1)
    t = (xs - x0)[None, :, None]
    sampled = field[:, x0] * (1 - t) + field[:, x1] * t

    centers = (np.arange(bins) + 0.5) / bins
    cx = np.concatenate([centers - 1, centers, centers + 1])
    ai = np.interp(u, cx, np.tile(a, 3))[None, :, None]
    bi = np.interp(u, cx, np.tile(b, 3))[None, :, None]
    return sampled * ai + bi


# ---------------------------------------------------------------- 글자 떼어 내기

def background_under(img, box, margin=14, deg=2):
    """글자 상자 안의 바탕을 열마다 세로 방향 다항식으로 추정한다.

    줄무늬가 세로라서 한 열 안에서는 바탕이 위아래로 천천히만 변한다. 글자
    픽셀은 반복해서 맞추며 빼 낸다.
    """
    _, x0, y0, x1, y1 = box
    ya, yb = max(y0 - margin, 0), min(y1 + margin, img.shape[0])
    ys = np.arange(ya, yb)
    t = (ys - ys.mean()) / (np.ptp(ys) / 2)
    V = np.stack([t ** p for p in range(deg + 1)], 1)
    out = np.zeros((y1 - y0, x1 - x0, 3))
    for j, x in enumerate(range(x0, x1)):
        col = img[ya:yb, x]
        keep = np.ones(len(ys), bool)
        keep[(ys >= y0) & (ys < y1)] = False  # 처음엔 위아래 여백만
        for _ in range(4):
            coef, *_ = np.linalg.lstsq(V[keep], col[keep], rcond=None)
            fit = V @ coef
            err = np.abs(col - fit).max(1)
            keep = err < 7
            keep[:margin] |= True
            keep[-margin:] |= True
        out[:, j] = fit[y0 - ya:y1 - ya]
    return out


def extract_text(img):
    """글자마다 (상자, 글자색, 불투명도) 를 돌려준다."""
    layers = []
    for box in TEXT_BOXES:
        kind, x0, y0, x1, y1 = box
        I = img[y0:y1, x0:x1]
        B = background_under(img, box)
        diff = np.linalg.norm(I - B, axis=2)
        if kind == "w":
            ink = np.array([255.0, 255.0, 255.0])
        elif kind == "d":
            ink = INK_DARK
        else:
            ink = np.median(I[diff > np.percentile(diff, 99)], 0)
        d = ink - B
        alpha = ((I - B) * d).sum(2) / np.maximum((d * d).sum(2), 1.0)
        alpha = np.clip((alpha - 0.06) / 0.94, 0, 1)
        layers.append((box, ink, alpha))
    return layers


def composite(base, img, layers):
    out = base.copy()
    for (kind, x0, y0, x1, y1), ink, alpha in layers:
        a = alpha[..., None]
        out[y0:y1, x0:x1] = a * ink + (1 - a) * out[y0:y1, x0:x1]
    h, w, _ = out.shape
    yy, xx = np.mgrid[0:h, 0:w]
    for cx, cy, r in BADGES:
        dist = np.hypot(xx - cx, yy - cy)
        edge = np.clip(r - dist + 0.5, 0, 1)[..., None]
        inner = (dist < r - 1.5)[..., None]
        out = np.where(inner, img, edge * BADGE_RED + (1 - edge) * out)
    return out


# ---------------------------------------------------------------- 오브제

def gaussian_blur(a, sigma):
    """분리형 가우시안 블러. 가장자리는 늘여서 채운다."""
    r = int(3 * sigma)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    for axis in (0, 1):
        pad = [(0, 0)] * a.ndim
        pad[axis] = (r, r)
        p = np.pad(a, pad, mode="edge")
        a = np.apply_along_axis(lambda v: np.convolve(v, k, mode="valid"), axis, p)
    return a


def ramp(x, stops):
    """x 위치에 따라 색을 바꾼다. stops = [(x, 색), ...]"""
    xs = np.array([s[0] for s in stops], float)
    cs = np.array([s[1] for s in stops], float)
    return np.stack([np.interp(x, xs, cs[:, c]) for c in range(3)], -1)


class Ribbon:
    """중심선 yc(x) 와 반폭 w(x) 로 정한 부드러운 띠.

    twist 가 있으면 반폭이 그 주기로 좁아졌다 넓어지며, 좁아지는 곳(띠가
    뒤집히는 곳)에 라벤더 광택이 실린다.
    """

    def __init__(self, yc, w, soft, colors, sheen=0.0, sheen_shift=None):
        self.yc, self.w, self.soft = yc, w, soft
        self.colors, self.sheen = colors, sheen
        self.sheen_shift = sheen_shift

    def render(self, X, Y):
        x = X[0]
        slope = np.gradient(self.yc)
        dy = Y - self.yc[None, :]
        dist = np.abs(dy) / np.sqrt(1 + slope ** 2)[None, :]
        w = self.w[None, :]
        dens = 1 / (1 + np.exp((dist - w) / self.soft))
        col = np.broadcast_to(ramp(x, self.colors)[None], X.shape + (3,)).copy()
        if self.sheen:
            v = dy / w  # 띠 단면 좌표, -1(위) .. 1(아래)
            v0 = self.sheen_shift[None, :]
            s = np.exp(-((v - v0) / 0.45) ** 2) * self.sheen
            col = col * (1 - s[..., None]) + LAVENDER * s[..., None]
        return dens, col


def paint(ribbons, h, w, blur):
    Y, X = np.mgrid[0:h, 0:w].astype(float)
    clear = np.ones((h, w))
    num = np.zeros((h, w, 3))
    den = np.full((h, w), 1e-6)
    for rb in ribbons:
        d, c = rb.render(X, Y)
        clear *= 1 - d
        num += d[..., None] * c
        den += d
    D = 1 - clear
    col = num / den[..., None]
    # 띠가 겹친 곳은 한 톤 깊게
    over = np.clip(den - 1, 0, 1)[..., None] * 0.18
    col = col * (1 - over) + CRIMSON * 0.85 * over
    field = BG * (1 - D[..., None]) + col * D[..., None]
    return gaussian_blur(field, blur)


def wave(x, *terms):
    """sum(A * sin(2π x / L + φ))"""
    return sum(A * np.sin(2 * np.pi * x / L + p) for A, L, p in terms)


def variant_a(h, w):
    """A. 두 번 크게 출렁이는 한 줄기 띠."""
    x = np.arange(w, dtype=float)
    # 마루(위로 솟은 곳)가 책등 바로 오른쪽에 와서 책등 제목 뒤를 덮는다.
    yc = 690 + wave(x, (215, 1270, -0.48), (30, 560, 1.1))
    tw = np.cos(2 * np.pi * x / 1270 - 0.48)
    width = 125 + 80 * np.abs(tw) + 18 * np.sin(x / 240)
    colors = [(0, RED), (450, CRIMSON), (950, MAGENTA), (1250, MAGENTA),
              (1650, CRIMSON), (2000, RED)]
    return [Ribbon(yc, width, 48, colors, sheen=0.6, sheen_shift=-0.8 * tw)]


def variant_b(h, w):
    """B. 세 줄기가 엇갈려 흐르는 물결 — LINE 이 여러 줄로 선다."""
    x = np.arange(w, dtype=float)
    out = []
    specs = [
        (500, (140, 1500, 0.3), 58, [(0, CRIMSON), (900, MAGENTA), (2000, LAVENDER * 0.92)], 0.35),
        (700, (155, 1500, 1.15), 64, [(0, RED), (1000, CRIMSON), (2000, RED)], 0.15),
        (900, (140, 1500, 2.0), 58, [(0, MAGENTA), (1000, CRIMSON), (2000, RED)], 0.25),
    ]
    for base, (A, L, p), ww, colors, sh in specs:
        yc = base + wave(x, (A, L, p), (22, 610, p * 2))
        width = ww + 14 * np.sin(2 * np.pi * x / 900 + p)
        out.append(Ribbon(yc, width, 24, colors, sheen=sh,
                          sheen_shift=-0.7 * np.cos(2 * np.pi * x / L + p)))
    return out


def variant_c(h, w):
    """C. 두 줄기가 꼬이며 교차하는 띠."""
    x = np.arange(w, dtype=float)
    # x = 350, 1650 에서 교차하고, 책등에서 가장 크게 벌어진다.
    # 위 줄기는 책등에서 가장 넓어져 책등 제목 뒤를 덮고, 아래 줄기는 거기서
    # 가장 가늘어져 뒤집히는 것처럼 보인다.
    mid = 718 + wave(x, (35, 2200, 0.5))
    swing = 255 * np.sin(2 * np.pi * (x - 350) / 2600)
    pinch = 26 * np.cos((x - 1000) / 280)
    r1 = Ribbon(mid - swing + wave(x, (25, 640, 0.0)),
                86 + pinch, 34,
                [(0, RED), (700, CRIMSON), (1300, MAGENTA), (2000, CRIMSON)],
                sheen=0.45, sheen_shift=0.7 * np.sin(x / 280))
    r2 = Ribbon(mid + swing + wave(x, (25, 640, 2.0)),
                86 - pinch, 34,
                [(0, MAGENTA), (800, CRIMSON), (1400, RED), (2000, RED)],
                sheen=0.25, sheen_shift=-0.7 * np.cos(x / 280))
    return [r1, r2]


VARIANTS = {"a": variant_a, "b": variant_b, "c": variant_c}
TITLES = {
    "a": "A  더블 웨이브",
    "b": "B  세 줄 물결",
    "c": "C  교차하는 두 줄기",
}


def to_image(a, seed=0):
    rng = np.random.default_rng(seed)
    a = a + rng.uniform(-0.5, 0.5, a.shape)  # 그라데이션 계단 방지
    return Image.fromarray(np.clip(np.round(a), 0, 255).astype(np.uint8))


def contact_sheet(paths, labels, out):
    thumbs = [Image.open(p) for p in paths]
    tw = 1000
    th = round(thumbs[0].height * tw / thumbs[0].width)
    pad, cap = 40, 56
    sheet = Image.new("RGB", (pad + 2 * (tw + pad), pad + 2 * (th + cap + pad)), (250, 250, 250))
    dr = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 30)
    except OSError:
        font = ImageFont.load_default()
    for i, (im, label) in enumerate(zip(thumbs, labels)):
        cx, cy = i % 2, i // 2
        x = pad + cx * (tw + pad)
        y = pad + cy * (th + cap + pad)
        dr.text((x, y + 6), label, fill=(40, 40, 40), font=font)
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (x, y + cap))
    sheet.save(out)


def main():
    img = np.asarray(Image.open(SRC).convert("RGB")).astype(float)
    h, w, _ = img.shape
    shade = fit_shading(img)
    layers = extract_text(img)
    os.makedirs(OUT, exist_ok=True)
    paths = []
    for key, make in VARIANTS.items():
        field = paint(make(h, w), h, w, blur=22)
        cover = composite(reeded(field, shade), img, layers)
        path = os.path.join(OUT, f"variant-{key}.png")
        to_image(cover, seed=ord(key)).save(path)
        paths.append(path)
        print("wrote", path)
    contact_sheet([SRC] + paths, ["원본"] + [TITLES[k] for k in VARIANTS],
                  os.path.join(OUT, "sheet.png"))
    print("wrote", os.path.join(OUT, "sheet.png"))


if __name__ == "__main__":
    main()
