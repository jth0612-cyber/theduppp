"""시험지 PDF → 문항별 그림(PNG). 조교가 '문항 그림'으로 올릴 파일을 만든다 (PC에서, 시스템 python + pymupdf).

    python tools/split_items.py "시험지.pdf" 출력폴더 [--pick 1,3,9]

문항 번호('1.' '2.' …)를 찾아 그 아래 칸을 자른다(2배 해상도). --pick 을 주면 그 번호만 순서대로 01.png, 02.png … 로
다시 번호를 매긴다(복습 테스트처럼 시험지 일부만 쓸 때). 결과 파일 이름의 숫자가 사이트의 문항 번호가 된다.
"""
import os
import sys

import pymupdf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from demo_photos import exam_items  # noqa: E402


def _trim(path, pad=16):
    """아래·옆 빈 여백을 잘라 낸다."""
    from PIL import Image, ImageChops
    im = Image.open(path).convert("RGB")
    box = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).getbbox()
    if box:
        x0, y0, x1, y1 = box
        im.crop((max(0, x0 - pad), max(0, y0 - pad), min(im.width, x1 + pad), min(im.height, y1 + pad))).save(path)


def split(pdf, out, pick=None, zoom=2.0):
    os.makedirs(out, exist_ok=True)
    d = pymupdf.open(pdf)
    items = exam_items(d)
    order = pick or sorted(items)
    made = []
    for new_no, no in enumerate(order, 1):
        it = items.get(no)
        if not it:
            continue
        pix = d[it["page"]].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=it["rect"])
        path = os.path.join(out, f"{(new_no if pick else no):02d}.png")
        pix.save(path)
        _trim(path)
        made.append(path)
    return made


if __name__ == "__main__":
    args = sys.argv[1:]
    pick = None
    if "--pick" in args:
        i = args.index("--pick")
        pick = [int(x) for x in args[i + 1].split(",")]
        args = args[:i] + args[i + 2:]
    files = split(args[0], args[1], pick)
    print(len(files), "items ->", args[1])
