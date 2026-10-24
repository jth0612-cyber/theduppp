"""검은 바탕 손필기 메모(아이패드 다크 모드) 그림을 흰 바탕으로 바꾼다. 색상은 유지하고 밝기만 뒤집은 뒤 바탕을 흰색으로, 여백을 잘라낸다.
Usage: python3 lighten_notes.py <img 폴더>   (평균 밝기 0.3 미만인 png만 바꾸고, 원본은 *_dark.png로 남긴다)"""
import glob, os, sys
import numpy as np
from PIL import Image
for p in sorted(glob.glob(os.path.join(sys.argv[1], 'image*.png'))):
    if p.endswith('_dark.png'):
        continue
    a = np.asarray(Image.open(p).convert('RGB')).astype(float) / 255
    if a.mean() >= 0.3:
        continue
    os.replace(p, p[:-4] + '_dark.png')
    mx, mn = a.max(-1, keepdims=True), a.min(-1, keepdims=True)
    b = np.clip(a + (1 - mx - mn), 0, 1)                     # 밝기 뒤집기 (색상 유지)
    sat = (b.max(-1) - b.min(-1)); lum = b.mean(-1)
    b[(sat < 0.12) & (lum > 0.62)] = 1.0                      # 회색 바탕 → 흰색
    ink = (b.mean(-1) < 0.9)
    ys, xs = np.where(ink)
    im = Image.fromarray((b * 255).astype('uint8'))
    if len(xs):
        pad = 20
        im = im.crop((max(0, xs.min() - pad), max(0, ys.min() - pad), min(im.width, xs.max() + pad), min(im.height, ys.max() + pad)))
    im.save(p, optimize=True)
    print(os.path.basename(p), im.size)
