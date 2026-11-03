import random, math
from common import *
r = random.Random(33)
defs = lingrad("sky", [(0, "#1d2440"), (0.6, "#3b4a72"), (1, "#7a86a8")]) + lingrad("ground", [(0, "#2a2f3c"), (1, "#3a3f4c")]) \
     + radgrad("lamp", [(0, "#ffd697", 1), (0.35, "#ffbf6a", .55), (1, "#ffb060", 0)]) + lingrad("win", [(0, "#ffe2a8"), (1, "#f2b765")]) \
     + lingrad("refl", [(0, "#ffcf86", .55), (1, "#ffcf86", 0)]) + lingrad("fog", [(0, "#8a95b5", 0), (1, "#8a95b5", .6)])
b = f'<rect width="{W}" height="{H}" fill="url(#sky)"/>'
# 언덕과 성 (안개 속 실루엣)
b += '<path d="M380,330 C460,250 560,215 640,215 C730,215 810,260 880,330 Z" fill="#2c3656"/>'
cx, cy = 640, 215
b += f'<rect x="{cx-56}" y="{cy-16}" width="112" height="20" fill="#3a4466"/>'
for (w, h, y) in ((96, 26, cy - 40), (72, 22, cy - 66), (50, 20, cy - 88)):
    b += f'<rect x="{cx-w/2+8}" y="{y}" width="{w-16}" height="{h}" fill="#c9cfe0"/>'
    b += f'<path d="M{cx-w/2-8},{y+4} Q{cx},{y-14} {cx+w/2+8},{y+4} L{cx+w/2-4},{y-6} L{cx-w/2+4},{y-6} Z" fill="#1e2640"/>'
b += f'<rect x="{cx-6}" y="{cy-110}" width="12" height="8" fill="#1e2640"/>'
b += '<rect x="0" y="220" width="1200" height="140" fill="url(#fog)"/>'
# 골목: 원근 (소실점 640,330)
VX, VY = 640, 330
b += f'<path d="M{VX-40},{VY} L{VX+40},{VY} L1200,750 L0,750 Z" fill="url(#ground)"/>'
# 돌길 줄눈
for i in range(1, 16):
    t = (i / 16) ** 1.7; y = VY + t * 420; half = 40 + t * 600
    b += f'<line x1="{VX-half:.0f}" y1="{y:.0f}" x2="{VX+half:.0f}" y2="{y:.0f}" stroke="#20242e" stroke-width="{1+t*2:.1f}"/>'
# 물길 (왼쪽)
b += f'<path d="M{VX-34},{VY} L{VX-26},{VY} L180,750 L60,750 Z" fill="#141a26"/><path d="M{VX-31},{VY} L{VX-29},{VY} L130,750 L110,750 Z" fill="#6f7fa8" opacity=".35"/>'
# 왼쪽 집들 (검은 판자 아래, 흰 회벽 위)
def side(left):
    o = ""; sg = -1 if left else 1
    for k in range(6):
        t0 = (k / 6) ** 1.5; t1 = ((k + 1) / 6) ** 1.5
        x0 = VX + sg * (40 + t0 * 640); x1 = VX + sg * (40 + t1 * 640)
        top0 = VY - 14 - t0 * 250; top1 = VY - 14 - t1 * 250; mid0 = VY - 6 - t0 * 70; mid1 = VY - 6 - t1 * 70; bot0 = VY + t0 * 420; bot1 = VY + t1 * 420
        o += f'<path d="M{x0:.0f},{top0:.0f} L{x1:.0f},{top1:.0f} L{x1:.0f},{mid1:.0f} L{x0:.0f},{mid0:.0f} Z" fill="#e6e1d6"/>'
        o += f'<path d="M{x0:.0f},{mid0:.0f} L{x1:.0f},{mid1:.0f} L{x1:.0f},{bot1:.0f} L{x0:.0f},{bot0:.0f} Z" fill="#2c2420"/>'
        o += f'<line x1="{x1:.0f}" y1="{top1:.0f}" x2="{x1:.0f}" y2="{bot1:.0f}" stroke="#1e1814" stroke-width="{2+t1*6:.0f}"/>'
        o += f'<line x1="{x0:.0f}" y1="{(top0+mid0)/2:.0f}" x2="{x1:.0f}" y2="{(top1+mid1)/2:.0f}" stroke="#2c2420" stroke-width="{1+t1*4:.1f}"/>'
        # 격자창 불빛
        wx0 = x0 + (x1 - x0) * 0.2; wx1 = x0 + (x1 - x0) * 0.75
        wy0 = mid0 + (bot0 - mid0) * 0.15; wy1 = mid1 + (bot1 - mid1) * 0.15; wb0 = mid0 + (bot0 - mid0) * 0.5; wb1 = mid1 + (bot1 - mid1) * 0.5
        f0 = (wx0 - x0) / (x1 - x0); f1 = (wx1 - x0) / (x1 - x0)
        ya = wy0 + (wy1 - wy0) * f0; yb = wy0 + (wy1 - wy0) * f1; yc = wb0 + (wb1 - wb0) * f1; yd = wb0 + (wb1 - wb0) * f0
        if k % 2 == (0 if left else 1):
            o += f'<path d="M{wx0:.0f},{ya:.0f} L{wx1:.0f},{yb:.0f} L{wx1:.0f},{yc:.0f} L{wx0:.0f},{yd:.0f} Z" fill="url(#win)"/>'
            for j in range(1, 6):
                xx = wx0 + (wx1 - wx0) * j / 6; y1 = ya + (yb - ya) * j / 6; y2 = yd + (yc - yd) * j / 6
                o += f'<line x1="{xx:.0f}" y1="{y1:.0f}" x2="{xx:.0f}" y2="{y2:.0f}" stroke="#3a2a1e" stroke-width="{1+t1*2:.1f}"/>'
        # 기와 지붕 (골목 쪽으로 내민 처마)
        rt0 = top0 - 10 - t0 * 70; rt1 = top1 - 10 - t1 * 70
        o += f'<path d="M{x0 - sg*4:.0f},{rt0:.0f} L{x1 - sg*4:.0f},{rt1:.0f} L{x1 + sg*(-40)*t1 - sg*6:.0f},{top1 + 10 + 22*t1:.0f} L{x0 + sg*(-40)*t0 - sg*6:.0f},{top0 + 10 + 22*t0:.0f} Z" fill="#1a1d26"/>'
        o += f'<path d="M{x0 + sg*(-40)*t0 - sg*6:.0f},{top0 + 10 + 22*t0:.0f} L{x1 + sg*(-40)*t1 - sg*6:.0f},{top1 + 10 + 22*t1:.0f}" stroke="#4a5270" stroke-width="{1+t1*3:.1f}"/>'
        # 둥근 등
        lx = x0 + (x1 - x0) * 0.5 - sg * 30 * ((t0 + t1) / 2); ly = (top0 + top1) / 2 + 22 + 60 * ((t0 + t1) / 2); lr = 5 + 20 * ((t0 + t1) / 2)
        o += f'<line x1="{lx:.0f}" y1="{ly-lr*2.2:.0f}" x2="{lx:.0f}" y2="{ly-lr:.0f}" stroke="#111" stroke-width="1.5"/><circle cx="{lx:.0f}" cy="{ly:.0f}" r="{lr*3:.0f}" fill="url(#lamp)" opacity=".55"/><ellipse cx="{lx:.0f}" cy="{ly:.0f}" rx="{lr*0.85:.0f}" ry="{lr:.0f}" fill="#ffe0a6"/>'
        ry = VY + ((t0 + t1) / 2) * 420
        o += f'<rect x="{lx-lr*0.4:.0f}" y="{ry:.0f}" width="{lr*0.8:.0f}" height="{lr*4:.0f}" fill="url(#refl)"/>'
    return o
b += side(True) + side(False)
# 찻집 노렌 (오른쪽 앞)
b += '<rect x="900" y="372" width="150" height="70" fill="#3b4a3a"/><line x1="950" y1="372" x2="950" y2="442" stroke="#2a3428" stroke-width="3"/><line x1="1000" y1="372" x2="1000" y2="442" stroke="#2a3428" stroke-width="3"/>'
b += '<circle cx="975" cy="405" r="16" fill="none" stroke="#f2ebdc" stroke-width="3"/>'
# 우산 쓴 사람 실루엣 (멀리)
b += '<path d="M600,380 Q620,362 640,380 Z" fill="#c8323a"/><rect x="618" y="380" width="4" height="22" fill="#1a1d26"/><rect x="612" y="384" width="16" height="26" rx="4" fill="#1a1d26"/>'
# 물웅덩이 반사
for _ in range(12):
    x = r.uniform(350, 900); y = r.uniform(520, 720)
    b += f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{r.uniform(20,60):.0f}" ry="{r.uniform(3,7):.0f}" fill="#ffcf86" opacity="{r.uniform(.08,.2):.2f}"/>'
# 빗줄기와 물결
for _ in range(240):
    x = r.uniform(0, 1220); y = r.uniform(-20, 740); L = r.uniform(18, 40)
    b += f'<line x1="{x:.0f}" y1="{y:.0f}" x2="{x-L*0.18:.0f}" y2="{y+L:.0f}" stroke="#c8d2ec" stroke-width="1.3" opacity="{r.uniform(.25,.6):.2f}"/>'
for _ in range(18):
    x = r.uniform(300, 950); y = r.uniform(500, 740)
    b += f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{r.uniform(6,14):.0f}" ry="{r.uniform(1.5,3):.1f}" fill="none" stroke="#c8d2ec" stroke-width="1" opacity=".5"/>'
open("cafe.svg", "w").write(svg(defs, b))
print("ok")
