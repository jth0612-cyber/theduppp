"""데모 사진 만들기: testfile/ 의 실제 교재·시험지를 잘라 학생 필기를 얹고 휴대폰으로 찍은 것처럼 만든다.

    python tools/demo_photos.py serve <pdf폴더>     # seed_demo.py 가 띄워 두고 요청(JSON 한 줄)마다 사진을 받는다
    python tools/demo_photos.py paper <pdf폴더> <출력앞이름> <답안> <정답,…> <글씨> <시드> [쪽…]

시스템 python 으로 돌린다 (PIL·numpy·pymupdf 필요, 데모 venv 에는 없음). 결과 사진은 데모 DB 에만 들어간다.
"""
import io
import math
import os
import random
import re
import sys

import numpy as np
import pymupdf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

pymupdf.TOOLS.mupdf_display_errors(False)
FONT_DIRS = [os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts"), r"C:\Windows\Fonts"]
HANDS = {   # 사람마다 다른 글씨
    "박서윤": "나눔손글씨 성실체.ttf", "이도현": "KyoboHandwriting2019.ttf", "최민서": "나눔손글씨 중학생.ttf",
    "정하준": "NanumPen.ttf", "김나연": "나눔손글씨 또박또박.ttf", "오준혁": "나눔손글씨 고딕 아니고 고딩.ttf",
    "윤지아": "KyoboHandwriting2021sjy.ttf", "한승우": "나눔손글씨 와일드.ttf", "한지수": "나눔손글씨 바른정신.ttf",
    "김도윤": "KyoboHandwriting2020pdy.ttf",
}
MESSY = {"나눔손글씨 와일드.ttf"}          # 악필: 글자마다 크게 흔들리고 가끔 줄을 그어 지운다
OTHER_HANDS = ["나눔손글씨 수줍은 대학생.ttf", "나눔손글씨 열아홉의 반짝임.ttf", "KyoboHandwriting2022khn.ttf", "나눔손글씨 혜준체.ttf",
               "Gaegu-Regular.ttf", "나눔손글씨 동화또박.ttf"]
PDF = {"mock": "모의고사 데모.pdf", "rev": "복테 데모.pdf", "lineup": "개념서 LINE UP 데모.pdf", "framing": "기출 FRAMING 문제편 데모.pdf",
       "logic": "필기노트 LOGIC BUILD 데모.pdf"}
PENCIL, RED, BLUE, BLACK = (70, 70, 78, 215), (196, 34, 44, 225), (28, 62, 168, 225), (30, 30, 34, 225)
HILITE = (255, 236, 80, 95)


def font_path(name):
    for d in FONT_DIRS:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return os.path.join(r"C:\Windows\Fonts", "malgun.ttf")


def hand(name):
    return font_path(HANDS.get(name) or OTHER_HANDS[sum(map(ord, name)) % len(OTHER_HANDS)])


# ---------------------------------------------------------------- 시험지 문항 찾기
_docs = {}


def doc(base, key):
    if key not in _docs:
        _docs[key] = pymupdf.open(os.path.join(base, PDF[key]))
    return _docs[key]


def exam_items(d):
    """{문항: {page, rect, opts: [rect ①~⑤], bogi: {ㄱ: rect}}} (pt 좌표)"""
    found = []
    for pi, p in enumerate(d):
        for b in p.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                t = "".join(s["text"] for s in l["spans"]).strip()
                x0, y0 = l["bbox"][:2]
                if re.match(r"^\d{1,2}\.$", t) and (x0 < 100 or 430 < x0 < 460):
                    found.append((pi, 0 if x0 < 300 else 1, y0, int(t[:-1])))
    out = {}
    for pi, col, y0, no in found:
        nxt = [y for p2, c2, y, _ in found if p2 == pi and c2 == col and y > y0]
        x0 = 78 if col == 0 else 427
        rect = pymupdf.Rect(x0, y0 - 8, x0 + 336, (min(nxt) - 10) if nxt else 1095)
        p = d[pi]
        opts = []
        for ch in "①②③④⑤":
            hits = [r for r in p.search_for(ch, clip=rect)]
            opts.append(hits[-1] if hits else None)
        bogi = {}
        for lab in "ㄱㄴㄷ":
            hits = p.search_for(lab + ".", clip=rect)
            if hits:
                bogi[lab] = hits[0]
        out[no] = {"page": pi, "rect": rect, "opts": opts, "bogi": bogi}
    return out


_items = {}


def items(base, key):
    if key not in _items:
        _items[key] = exam_items(doc(base, key))
    return _items[key]


# ---------------------------------------------------------------- 그리기
class Sheet:
    """PDF 한 영역을 그림으로. pt 좌표 → 픽셀 좌표로 바꿔 필기를 얹는다."""

    def __init__(self, page, clip, dpi=180):
        self.clip, self.s = clip, dpi / 72
        pix = page.get_pixmap(dpi=dpi, clip=clip)
        self.img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("RGBA")
        self.ink = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.ink)

    def px(self, x, y):
        return ((x - self.clip.x0) * self.s, (y - self.clip.y0) * self.s)

    def box(self, r, pad=0):
        (a, b), (c, e) = self.px(r.x0, r.y0), self.px(r.x1, r.y1)
        return a - pad, b - pad, c + pad, e + pad

    def done(self):
        return Image.alpha_composite(self.img, self.ink).convert("RGB")


def wobble_ellipse(d, box, color, rng, width=3):
    x0, y0, x1, y1 = box
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    start = rng.uniform(0, 2 * math.pi)
    pts = []
    for i in range(46):
        a = start + i / 40 * 2 * math.pi                      # 한 바퀴보다 조금 더 (끝이 겹친다)
        k = 1 + 0.07 * math.sin(3 * a + start) + rng.uniform(-0.02, 0.02)
        pts.append((cx + rx * k * math.cos(a), cy + ry * k * math.sin(a)))
    d.line(pts, fill=color, width=width, joint="curve")


def stroke(d, pts, color, rng, width=3):
    pts = [(x + rng.uniform(-1, 1), y + rng.uniform(-1, 1)) for x, y in pts]
    d.line(pts, fill=color, width=width, joint="curve")


def mark_o(d, x, y, size, color, rng):
    wobble_ellipse(d, (x - size, y - size, x + size, y + size), color, rng)


def mark_x(d, x, y, size, color, rng):
    stroke(d, [(x - size, y - size), (x + size, y + size)], color, rng)
    stroke(d, [(x + size, y - size), (x - size, y + size)], color, rng)


def check(d, x, y, size, color, rng):
    stroke(d, [(x - size, y), (x - size * 0.3, y + size * 0.8), (x + size * 1.2, y - size)], color, rng)


_fonts = {}


def _font(fontfile, size):
    k = (fontfile, size)
    if k not in _fonts:
        try:
            _fonts[k] = ImageFont.truetype(fontfile, size)
        except OSError:                                       # 글꼴 파일이 일부 크기를 못 그리면 나눔펜으로
            _fonts[k] = ImageFont.truetype(font_path("NanumPen.ttf"), size)
    return _fonts[k]


_cmaps = {}
CIRCLED_LETTERS = dict(zip("㉠㉡㉢㉣㉤ⓐⓑⓒ①②③④⑤", "ㄱㄴㄷㄹㅁabc12345"))   # 손으로는 글자를 쓰고 동그라미를 친다
SUBSCRIPT = dict(zip("₀₁₂₃₄₅₆₇₈₉ⅠⅡⅢ", "0123456789ⅠⅡⅢ"))


def has_glyph(fontfile, ch):
    if fontfile not in _cmaps:
        from fontTools.ttLib import TTFont
        try:
            _cmaps[fontfile] = set(TTFont(fontfile, fontNumber=0, lazy=True).getBestCmap() or {})
        except Exception:
            _cmaps[fontfile] = set()
    return ord(ch) in _cmaps[fontfile]


def glyph_font(fontfile, ch):
    """글씨체에 없는 글자는 나눔펜, 그것도 없으면 맑은 고딕으로."""
    for f in (fontfile, font_path("NanumPen.ttf"), font_path("malgun.ttf")):
        if ch == " " or has_glyph(f, ch):
            return f
    return fontfile


def write(layer, xy, text, fontfile, size, color, rng, angle=0):
    """글자마다 크기·기울기·높이를 조금씩 흔들어 손으로 쓴 것처럼."""
    x, y = xy
    messy = os.path.basename(fontfile) in MESSY
    for line in text.split("\n"):
        cx, drift, start = x, 0.0, x
        for ch in line:
            ring = ch in CIRCLED_LETTERS
            small = ch in SUBSCRIPT and SUBSCRIPT[ch].isdigit()
            ch = CIRCLED_LETTERS.get(ch, SUBSCRIPT.get(ch, ch))
            if messy:
                drift += rng.uniform(-2.2, 2.6)                  # 줄이 점점 위아래로 흘러간다
                k = rng.uniform(0.78, 1.3)
            else:
                k = rng.choice([0.94, 0.97, 1.0, 1.03, 1.06])
            f = _font(glyph_font(fontfile, ch), int(size * k * (0.62 if small else 1)))
            g = Image.new("RGBA", (int(size * 2.2), int(size * 1.8)), (0, 0, 0, 0))
            try:
                w = f.getlength(ch) or size * 0.4
                ImageDraw.Draw(g).text((size * 0.3, size * 0.2), ch, font=f, fill=color)
            except OSError:
                f = _font(font_path("NanumPen.ttf"), size)
                w = f.getlength(ch) or size * 0.4
                ImageDraw.Draw(g).text((size * 0.3, size * 0.2), ch, font=f, fill=color)
            g = g.rotate(angle + (rng.uniform(-16, 12) - 6 if messy else rng.uniform(-6, 6)), resample=Image.BICUBIC)
            dy = (drift + rng.uniform(-6, 6) if messy else rng.uniform(-1.5, 1.5)) + (size * 0.35 if small else 0)
            layer.alpha_composite(g, (int(cx), int(y + dy - size * 0.2)))
            if ring:
                wobble_ellipse(ImageDraw.Draw(layer), (cx + size * 0.18, y + dy - size * 0.02, cx + size * 0.42 + w, y + dy + size * 0.98),
                               color, rng, width=2)
                w += size * 0.25
            cx += w * (rng.uniform(0.75, 1.25) if messy else rng.uniform(0.92, 1.02))
            if ch == " ":
                if messy and cx - start > size * 2 and rng.random() < 0.18:   # 쓰다 만 글자를 줄로 지움
                    yy = y + drift + size * 0.45
                    ImageDraw.Draw(layer).line([(start, yy + rng.uniform(-4, 4)), (cx - w, yy + rng.uniform(-4, 4)),
                                                (start + 6, yy + 8), (cx - w - 4, yy + 6)], fill=color, width=3)
                start = cx
        y += size * (1.55 if messy else 1.35)
    return cx, y


def hilite(d, box, rng):
    x0, y0, x1, y1 = box
    d.rectangle((x0 - 2, y0 + (y1 - y0) * 0.15 + rng.uniform(-1, 1), x1 + 3, y1 - (y1 - y0) * 0.05), fill=HILITE)


def underline(d, box, color, rng):
    x0, y0, x1, y1 = box
    stroke(d, [(x0, y1 + 2), ((x0 + x1) / 2, y1 + 3 + rng.uniform(-1, 1)), (x1, y1 + 1)], color, rng, width=2)


# ---------------------------------------------------------------- 사진처럼
def _coeffs(src, dst):
    m = []
    for (x, y), (u, v) in zip(dst, src):
        m.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        m.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    return np.linalg.solve(np.array(m, float), np.array(src, float).reshape(8))


def photo(img, rng, longest=1280, desk=None):
    """종이를 책상 위에 놓고 비스듬히 찍은 사진: 원근, 기울기, 그늘, 잡음, JPEG."""
    w, h = img.size
    paper = np.asarray(img.convert("RGB"), float)
    tint = np.array([rng.uniform(244, 252), rng.uniform(240, 248), rng.uniform(228, 240)]) / 255
    paper = paper * tint
    img = Image.fromarray(paper.clip(0, 255).astype("uint8"))
    mx, my = int(w * rng.uniform(0.05, 0.1)), int(h * rng.uniform(0.04, 0.09))
    cw, ch = w + 2 * mx, h + 2 * my
    desk = desk or rng.choice([(118, 92, 66), (150, 150, 146), (204, 198, 186), (62, 64, 70)])
    base = np.ones((ch, cw, 3)) * np.array(desk, float)
    base += np.random.default_rng(rng.randint(0, 1 << 30)).normal(0, 6, (ch, cw, 1))
    canvas = Image.fromarray(base.clip(0, 255).astype("uint8"))
    j = lambda a: rng.uniform(-a, a)
    dst = [(mx + j(w * .03), my + j(h * .02)), (mx + w + j(w * .03), my + j(h * .02)),
           (mx + w + j(w * .02), my + h + j(h * .02)), (mx + j(w * .02), my + h + j(h * .02))]
    co = _coeffs([(0, 0), (w, 0), (w, h), (0, h)], dst)
    warped = img.transform((cw, ch), Image.PERSPECTIVE, co, Image.BICUBIC, fillcolor=(0, 0, 0))
    mask = Image.new("L", img.size, 255).transform((cw, ch), Image.PERSPECTIVE, co, Image.BICUBIC, fillcolor=0)
    sh = mask.filter(ImageFilter.GaussianBlur(14))
    canvas = Image.composite(Image.new("RGB", (cw, ch), tuple(int(c * 0.55) for c in desk)), canvas, sh.point(lambda v: v * 0.5))
    canvas.paste(warped, (0, 0), mask)
    a = np.asarray(canvas, float)
    yy, xx = np.mgrid[0:ch, 0:cw]
    lx, ly = rng.uniform(0.2, 0.8) * cw, rng.uniform(0.1, 0.5) * ch
    light = 1.06 - 0.22 * (((xx - lx) / cw) ** 2 + ((yy - ly) / ch) ** 2)
    if rng.random() < 0.6:                                     # 휴대폰·손 그늘
        sx, sy = rng.choice([(0, ch), (cw, ch), (cw, 0)])
        dist = np.hypot((xx - sx) / cw, (yy - sy) / ch)
        light *= 1 - 0.28 * np.clip(1 - dist / rng.uniform(0.35, 0.6), 0, 1) ** 1.5
    a = a * light[..., None]
    a += np.random.default_rng(rng.randint(0, 1 << 30)).normal(0, 3.2, a.shape)
    out = Image.fromarray(a.clip(0, 255).astype("uint8")).rotate(j(2.2), resample=Image.BICUBIC, expand=False, fillcolor=desk)
    out = out.filter(ImageFilter.GaussianBlur(rng.uniform(0.4, 0.8)))
    k = longest / max(out.size)
    if k < 1:
        out = out.resize((int(out.width * k), int(out.height * k)), Image.LANCZOS)
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=rng.randint(72, 80))
    return buf.getvalue()


# ---------------------------------------------------------------- 문항 사진 (질문용)
def item_photo(base, exam, no, who, rng, pick=None, think=None, note="", pen=PENCIL):
    """시험지 한 문항 + 학생 필기. pick: 고른 선지, think: {ㄱ: True/False} 학생 판단, note: 여백 메모."""
    it = items(base, exam)[no]
    sh = Sheet(doc(base, exam)[it["page"]], it["rect"])
    f = hand(who)
    if pick and it["opts"][pick - 1]:
        wobble_ellipse(sh.d, sh.box(it["opts"][pick - 1], 7), pen, rng)
    for lab, ok in (think or {}).items():
        r = it["bogi"].get(lab)
        if r:
            x, y = sh.px(r.x0, (r.y0 + r.y1) / 2)
            if ok is None:
                write(sh.ink, (x - 34, y - 26), "?", f, 46, pen, rng)
            else:
                (mark_o if ok else mark_x)(sh.d, x - 20, y, 11, pen, rng)
    if note:
        opt = next((o for o in it["opts"] if o), None)
        oy = sh.px(0, opt.y1)[1] if opt else sh.img.height * 0.6
        need = int(oy + 40 + 72 * (note.count(chr(10)) + 1)) - sh.img.height
        img = sh.done()
        if need > 0:                                           # 선지 아래 빈칸이 모자라면 종이 아래 여백을 늘린다
            big = Image.new("RGB", (img.width, img.height + need), (255, 255, 255))
            big.paste(img, (0, 0))
            img = big
        layer = img.convert("RGBA")
        write(layer, (img.width * rng.uniform(0.3, 0.45), oy + 30), note, f, 50, pen, rng, angle=rng.uniform(-3, 3))
        return photo(layer.convert("RGB"), rng, longest=1200)
    return photo(sh.done(), rng, longest=1200)


def page_photo(base, key, page_no, who, rng, find=None, note="", pen=PENCIL, height=620, extra=()):
    """교재 한 쪽(또는 find 글자가 있는 부분) + 형광펜·밑줄·메모."""
    p = doc(base, key)[page_no - 1]
    r = p.rect
    clip = r
    hit = p.search_for(find)[0] if find and p.search_for(find) else None
    if hit:
        top = max(0, hit.y0 - 120)
        clip = pymupdf.Rect(0, top, r.width, min(r.height, top + height))
    sh = Sheet(p, clip, dpi=170)
    f = hand(who)
    if hit:
        hilite(sh.d, sh.box(hit), rng)
        for t in extra:
            for h2 in p.search_for(t, clip=clip)[:1]:
                underline(sh.d, sh.box(h2), pen, rng)
    if note:
        write(sh.ink, (sh.img.width * rng.uniform(0.5, 0.6), sh.img.height * rng.uniform(0.55, 0.75)), note, f, 54, pen, rng, angle=rng.uniform(-4, 2))
    return photo(sh.done(), rng)


def notebook_photo(lines, who, rng, title="", pen=BLUE, size=(1240, 1650)):
    """줄 노트에 손으로 정리한 판서 (교재에 없는 단원)."""
    w, h = size
    img = Image.new("RGBA", size, (252, 251, 246, 255))
    d = ImageDraw.Draw(img)
    for y in range(196, h, 76):
        d.line([(60, y), (w - 50, y)], fill=(176, 196, 222, 255), width=2)
    d.line([(150, 0), (150, h)], fill=(232, 160, 160, 255), width=2)
    for y in range(120, h, 260):
        d.ellipse((18, y, 42, y + 24), fill=(214, 210, 200, 255))
    f = hand(who)
    y = 120
    if title:
        write(img, (180, y), title, f, 66, BLACK, rng)
        y += 152
    for ln in lines:
        color = RED if ln.startswith("!") else pen
        write(img, (180 + (44 if ln.startswith("-") else 0), y), ln.lstrip("!"), f, 54, color, rng, angle=rng.uniform(-1.5, 1.5))
        y += 76
    return photo(img, rng)


def solve_photo(base, exam, no, who, rng, lines):
    """문항 사진 + 아래에 이어 쓴 풀이 (1:1 첨삭 요청)."""
    it = items(base, exam)[no]
    sh = Sheet(doc(base, exam)[it["page"]], it["rect"])
    top = sh.done()
    w = top.width
    note = Image.new("RGBA", (w, 90 + 92 * len(lines)), (251, 250, 245, 255))
    d = ImageDraw.Draw(note)
    for y in range(80, note.height, 92):
        d.line([(30, y), (w - 30, y)], fill=(200, 210, 225, 255), width=2)
    y = 18
    for ln in lines:
        write(note, (50, y), ln, hand(who), 56, PENCIL, rng)
        y += 92
    img = Image.new("RGB", (w, top.height + note.height), (255, 255, 255))
    img.paste(top, (0, 0))
    img.paste(note.convert("RGB"), (0, top.height))
    return photo(img, rng)


def paper_photos(base, exam, answers, key, who, rng, pages=None):
    """학생 답안대로 고른 선지에 동그라미, 빨간 펜으로 채점 (틀린 문항 / 표시와 정답)."""
    d = doc(base, exam)
    its = items(base, exam)
    out = []
    for pi in pages or range(len(d)):
        sh = Sheet(d[pi], d[pi].rect, dpi=130)
        for no, it in its.items():
            if it["page"] != pi or no > len(answers):
                continue
            a = answers[no - 1]
            k = key[no - 1]
            if a in "12345" and it["opts"][int(a) - 1]:
                wobble_ellipse(sh.d, sh.box(it["opts"][int(a) - 1], 5), PENCIL, rng, width=2)
            nr = it["rect"]
            x, y = sh.px(nr.x0 + 6, nr.y0 + 14)
            if k == "*" or a == str(k):
                mark_o(sh.d, x + 4, y - 2, 24, RED, rng)
            else:
                stroke(sh.d, [(x - 26, y + 26), (x + 30, y - 30)], RED, rng, width=4)
                stroke(sh.d, [(x - 20, y + 30), (x + 34, y - 24)], RED, rng, width=3)
                if k in "12345" and it["opts"][int(k) - 1]:
                    wobble_ellipse(sh.d, sh.box(it["opts"][int(k) - 1], 9), RED, rng, width=3)
        out.append(photo(sh.done(), rng, longest=1500))
    return out


# ---------------------------------------------------------------- 실행
PENS = {"pencil": PENCIL, "blue": BLUE, "red": RED, "black": BLACK}


def serve(base):
    """seed_demo.py 가 한 줄에 요청 하나(JSON)를 보내면 사진을 만들고 파일 경로를 돌려준다."""
    import json
    for line in sys.stdin:
        r = json.loads(line)
        rng = random.Random(r.get("seed", 0))
        pen = PENS[r.get("pen", "pencil")]
        op, out = r["op"], r["out"]
        try:
            if op == "item":
                data = [item_photo(base, r["exam"], r["no"], r["who"], rng, r.get("pick"), r.get("think"), r.get("note", ""), pen)]
            elif op == "page":
                data = [page_photo(base, r["key"], r["page"], r["who"], rng, r.get("find"), r.get("note", ""), pen, extra=r.get("extra", ()))]
            elif op == "note":
                data = [notebook_photo(r["lines"], r["who"], rng, r.get("title", ""), pen)]
            elif op == "solve":
                data = [solve_photo(base, r["exam"], r["no"], r["who"], rng, r["lines"])]
            elif op == "paper":
                data = paper_photos(base, r["exam"], r["answers"], r["key"], r["who"], rng, r.get("pages"))
            files = []
            for i, b in enumerate(data, 1):
                f = out if len(data) == 1 else out.replace(".jpg", f"_{i}.jpg")
                open(f, "wb").write(b)
                files.append(f)
            print(json.dumps({"files": files}), flush=True)
        except Exception as e:                                  # 사진 하나 실패해도 데모는 계속
            print(json.dumps({"files": [], "error": repr(e)}), flush=True)


def main():
    cmd, base = sys.argv[1], sys.argv[2]
    if cmd == "paper":
        prefix, answers, key, who, seed = sys.argv[3:8]
        pages = [int(p) for p in sys.argv[8:]] or None
        rng = random.Random(int(seed))
        for i, data in enumerate(paper_photos(base, "rev", answers, key.split(","), who, rng, pages), 1):
            open(f"{prefix}_{i}.jpg", "wb").write(data)
        return
    if cmd == "serve":
        serve(base)


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()
