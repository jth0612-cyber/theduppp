import random, math
from common import *
r = random.Random(5)
defs = lingrad("sky", [(0, "#2b3a63"), (0.55, "#6f7fa8"), (1, "#c3c4d6")]) + lingrad("water", [(0, "#5fb4b0"), (1, "#2f7d84")]) \
     + radgrad("glow", [(0, "#ffd08a", 0.9), (1, "#ffd08a", 0)]) + lingrad("steam", [(0, "#ffffff", 0), (0.5, "#ffffff", 0.5), (1, "#ffffff", 0)], 0, 0, 0, 1) \
     + radgrad("st", [(0, "#ffffff", .55), (1, "#ffffff", 0)]) + lingrad("snow", [(0, "#e8ecf4"), (1, "#c9d0e0")])
b = f'<rect width="{W}" height="{H}" fill="url(#sky)"/>'
b += ridge(300, 60, 3, "#4b5a80", 60, 1, 0.3) + ridge(330, 40, 8, "#5d6c91", 40, 1, 0.4)
# 먼 눈 덮인 숲
for i in range(40):
    x = r.uniform(-20, 1220); h = r.uniform(80, 150); base = 360 + r.uniform(-8, 8)
    b += f'<path d="M{x-h*0.28:.0f},{base} L{x:.0f},{base-h:.0f} L{x+h*0.28:.0f},{base} Z" fill="#3d4b70"/><path d="M{x-h*0.12:.0f},{base-h*0.55:.0f} L{x:.0f},{base-h:.0f} L{x+h*0.12:.0f},{base-h*0.55:.0f} Z" fill="#dfe5f0"/>'
# 눈 덮인 비탈
b += '<path d="M0,360 C300,340 700,350 1200,330 L1200,750 L0,750 Z" fill="url(#snow)"/>'
# 갓쇼 집들 (비탈 위, 불 켜진 창)
def gassho(x, y, s):
    o = f'<path d="M{x-90*s},{y} L{x},{y-150*s} L{x+90*s},{y} Z" fill="#4a3a2e"/>'
    o += f'<path d="M{x-104*s},{y+4*s} L{x},{y-162*s} L{x-12*s},{y-120*s} L{x-82*s},{y-8*s} Z" fill="#f2f4f8"/>'  # 눈 쌓인 지붕 왼쪽
    o += f'<path d="M{x+104*s},{y+4*s} L{x},{y-162*s} L{x+12*s},{y-120*s} L{x+82*s},{y-8*s} Z" fill="#dfe4ee"/>'
    o += f'<rect x="{x-70*s}" y="{y}" width="{140*s}" height="{36*s}" fill="#3a2c22"/>'
    for (wx, wy) in ((-20, -100), (20, -100), (-40, -60), (0, -60), (40, -60), (-50, -22), (-15, -22), (20, -22), (55, -22)):
        if abs(wx) * 1.7 < (150 + wy) * 0.95:
            o += f'<rect x="{x+(wx-9)*s:.0f}" y="{y+wy*s:.0f}" width="{18*s:.0f}" height="{20*s:.0f}" fill="#ffcf86"/>'
    o += f'<rect x="{x-20*s}" y="{y+8*s}" width="{40*s}" height="{24*s}" fill="#ffcf86"/>'
    o += f'<circle cx="{x}" cy="{y-40*s}" r="{120*s}" fill="url(#glow)" opacity=".25"/>'
    return o
b += gassho(220, 370, 0.85) + gassho(470, 345, 0.62) + gassho(960, 360, 0.95) + gassho(760, 330, 0.5)
# 바위 온천 (앞)
b += '<ellipse cx="600" cy="600" rx="470" ry="120" fill="#3c4250"/>'
b += '<ellipse cx="600" cy="595" rx="430" ry="100" fill="url(#water)"/>'
b += '<ellipse cx="600" cy="585" rx="300" ry="50" fill="#8fd3cc" opacity=".35"/>'
# 물 위 등불 반사
b += '<rect x="880" y="590" width="8" height="70" fill="#ffd28a" opacity=".45"/><rect x="300" y="600" width="6" height="55" fill="#ffd28a" opacity=".35"/>'
# 테두리 바위 + 눈 모자
rocks = ""
for i in range(34):
    a = i / 34 * 6.283; x = 600 + math.cos(a) * 455; y = 600 + math.sin(a) * 112
    if math.sin(a) > -0.15 or True:
        rx = r.uniform(40, 70); ry = r.uniform(24, 40)
        if math.sin(a) > 0.6: ry *= 1.15; rx *= 1.1
        rocks += f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{rx:.0f}" ry="{ry:.0f}" fill="{r.choice(["#555b66", "#626874", "#4b505a"])}"/>'
        rocks += f'<ellipse cx="{x:.0f}" cy="{y-ry*0.55:.0f}" rx="{rx*0.8:.0f}" ry="{ry*0.42:.0f}" fill="#eef1f7"/>'
b += rocks
# 대나무 홈통과 물줄기
b += '<path d="M770,470 L640,520" stroke="#8c9a52" stroke-width="14" stroke-linecap="round"/><path d="M640,522 C632,540 630,560 634,585" stroke="#e8fbff" stroke-width="7" fill="none" opacity=".8"/>'
b += '<ellipse cx="634" cy="588" rx="28" ry="7" fill="none" stroke="#e8fbff" stroke-width="3" opacity=".7"/>'
b += '<ellipse cx="790" cy="480" rx="60" ry="40" fill="#555b66"/><ellipse cx="790" cy="462" rx="48" ry="16" fill="#eef1f7"/>'
# 석등 두 개 (불빛)
for (x, y, s) in ((300, 520, 1), (900, 505, 1.1)):
    b += f'<rect x="{x-6*s}" y="{y-60*s}" width="{12*s}" height="{60*s}" fill="#6a6e78"/><rect x="{x-16*s}" y="{y-86*s}" width="{32*s}" height="{26*s}" fill="#ffd28a"/>'
    b += f'<path d="M{x-28*s},{y-86*s} L{x},{y-106*s} L{x+28*s},{y-86*s} Z" fill="#eef1f7"/><circle cx="{x}" cy="{y-72*s}" r="{80*s}" fill="url(#glow)" opacity=".55"/>'
# 김 (부드러운 구름)
for i in range(16):
    x = r.uniform(260, 940); y = r.uniform(440, 580); rr = r.uniform(50, 110)
    b += f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{rr:.0f}" ry="{rr*0.55:.0f}" fill="url(#st)"/>'
# 내리는 눈
for _ in range(260):
    x = r.uniform(0, 1200); y = r.uniform(0, 750); rr = r.uniform(1.2, 3.6)
    b += f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rr:.1f}" fill="#ffffff" opacity="{r.uniform(.5,.95):.2f}"/>'
open("onsen.svg", "w").write(svg(defs, b))
print("ok")
