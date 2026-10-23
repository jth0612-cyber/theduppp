"""LOGIC BUILD 1 틀 그림(EMF) 생성: TAG 리본(좌수/우수), 중단원 띠 B-4.
Usage: python3 make_art.py <Pretendard-Bold.ttf> <out_dir> [바탕색 hex]
       1단 전체 폭용 띠 bar_B4_wide.emf(462.05pt)도 함께 만든다."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from emf_poly import write, text_outline

FONT, OUT = sys.argv[1:3]
PAPER_ARG = '#' + sys.argv[3] if len(sys.argv) > 3 else None
mm = lambda pt: pt * 25.4 / 72
ACC, CREAM, PAPER, BAR = '#A9623A', '#EFDFCB', '#FAF5EE', '#5A3A2E'
PAPER = PAPER_ARG or PAPER

# TAG: 표 칸 42 x 11.4pt. 원본 TAG 그림은 칸 오른쪽 끝 1.39pt 안쪽에서 끝나야 세로선과 맞음 → +0.8pt 여백
BOX_W, BOX_H, INSET, GAP, NOTCH = 42.0, 11.4, 1.39 + 0.8, 0.8, 4.5
glyphs, (gx0, gx1), (gy0, gy1) = text_outline(FONT, 'TAG', 8.6, tracking_pt=0.7)
def tag(path, mirror):
    w, h, n = mm(BOX_W), mm(BOX_H), mm(NOTCH)
    L = mm(BOX_W - INSET)                      # 리본 길이 (좌수·우수 같음)
    if not mirror:   # 좌수: 홈 왼쪽, 오른쪽 끝 = 세로선 − 0.8pt
        x0 = 0.0; body = [(x0, 0), (x0 + L, 0), (x0 + L, h), (x0, h), (x0 + n, h / 2)]; cx = x0 + (n + L) / 2
    else:            # 우수: 좌수의 좌우 대칭, 왼쪽 끝 = 세로선 + 0.8pt, 홈 오른쪽
        x0 = mm(GAP); body = [(x0, 0), (x0 + L, 0), (x0 + L - n, h / 2), (x0 + L, h), (x0, h)]; cx = x0 + (L - n) / 2
    dx = cx - (gx0 + gx1) / 2; dy = h / 2 - (gy0 + gy1) / 2
    return write(path, w, h, [(ACC, body), ('#FFFFFF', [[(x + dx, y + dy) for x, y in p] for p in glyphs])])

# 중단원 띠 B-4: 325.7 x 22.67pt (1단 전체 폭이면 462.05pt), 번호 블록 36pt(홈 6pt), 이음매 1.2pt, 밑줄 1pt
def bar(path, width_pt=325.7):
    Wd, H = mm(width_pt), mm(22.67); W, d, g, Lw = mm(36), mm(6), mm(1.2), mm(1.0)
    return write(path, Wd, H, [
        (CREAM, [(W - d, 0), (Wd, 0), (Wd, H), (W - d, H), (W, H / 2)]),
        (PAPER, [(W - d - g, 0), (W - d, 0), (W, H / 2), (W - d, H), (W - d - g, H), (W - g, H / 2)]),
        (ACC, [(0, 0), (W - d - g, 0), (W - g, H / 2), (W - d - g, H), (0, H)]),
        (BAR, [(0, H - Lw), (Wd, H - Lw), (Wd, H), (0, H)])])

os.makedirs(OUT, exist_ok=True)
print(tag(os.path.join(OUT, 'tag_L.emf'), False), tag(os.path.join(OUT, 'tag_R.emf'), True), bar(os.path.join(OUT, 'bar_B4.emf')),
      bar(os.path.join(OUT, 'bar_B4_wide.emf'), 462.05))
