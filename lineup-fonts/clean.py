# 표지 시안에서 제목·부제 영역을 지우고 세로 줄무늬만 남긴 배경을 만든다.
# 줄무늬는 세로로 균일하므로, 제목 아래 빈 띠를 위로 늘려 덮으면 된다.
from PIL import Image
import sys
# src-*.jpg 는 원본 평면 표지 시안(2448×1848) 이미지. 저장소에는 결과물만 둔다.
for src, x0, x1, out in [("src-blue.jpg", 576, 1872, "bg-blue.jpg"),
                          ("src-purple.jpg", 591, 1857, "bg-purple.jpg")]:
    im = Image.open(src).convert("RGB").crop((x0, 0, x1, 1848))
    strip = im.crop((0, 300, im.width, 312))
    im.paste(strip.resize((im.width, 300)), (0, 0))
    im = im.resize((im.width * 2 // 3, 1848 * 2 // 3), Image.LANCZOS)
    im.save(out, quality=84)
    print(out, im.size)
