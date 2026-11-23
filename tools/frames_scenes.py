"""녹화 프레임에서 장면만 골라낸다: 화면이 멈춰 있는 구간마다 한 장, 이미 나온 장면과 거의 같으면 뺀다.

    python tools/frames_scenes.py <프레임 폴더> <출력 폴더> <앞이름>
"""
import os
import sys

import numpy as np
from PIL import Image

src, out, prefix = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(out, exist_ok=True)
frames = sorted(f for f in os.listdir(src) if f.endswith(".jpg"))


def small(f):
    return np.asarray(Image.open(os.path.join(src, f)).convert("L").resize((96, 60)), float)


def dhash(a):
    return (a[:, 1:] > a[:, :-1]).flatten()


vecs = [small(f) for f in frames]
# 1) 멈춘 구간: 앞 프레임과 차이가 작으면 같은 구간
runs, cur = [], [0]
for i in range(1, len(frames)):
    if np.abs(vecs[i] - vecs[i - 1]).mean() < 2.0:
        cur.append(i)
    else:
        runs.append(cur)
        cur = [i]
runs.append(cur)
# 2) 0.6초 넘게 멈춘 구간의 끝 쪽 프레임 (자막이 다 뜬 뒤)
cands = []
for r in runs:
    t = int(frames[r[-1]][:-4]) - int(frames[r[0]][:-4])
    if t >= 600 or len(r) >= 6:
        cands.append(r[max(0, len(r) - 2)])
# 3) 이미 고른 장면과 거의 같으면 뺀다 (dHash 거리)
kept, hashes = [], []
for i in cands:
    h = dhash(vecs[i])
    if all((h != k).sum() > 260 for k in hashes):
        kept.append(i)
        hashes.append(h)
for n, i in enumerate(kept, 1):
    Image.open(os.path.join(src, frames[i])).convert("RGB").save(os.path.join(out, f"{prefix}_{n:02d}.jpg"), quality=84)
print(prefix, "frames", len(frames), "still runs", len(cands), "scenes", len(kept))
