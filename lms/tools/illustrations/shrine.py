import random, math
from common import *
r = random.Random(11)
defs = lingrad("sky", [(0, "#c9dde2"), (0.55, "#efe6d6"), (1, "#f6eadb")]) + lingrad("path", [(0, "#b9b0a2"), (1, "#d8cfc0")]) \
     + lingrad("mist", [(0, "#f4ece0", 0), (0.5, "#f4ece0", 0.85), (1, "#f4ece0", 0)]) + lingrad("ver", [(0, "#d9532f"), (1, "#b83d22")], 0, 0, 1, 0) \
     + lingrad("roof", [(0, "#5f7d73"), (1, "#3f5952")]) + radgrad("sun", [(0, "#fff6e4", 0.9), (1, "#fff6e4", 0)])
b = f'<rect width="{W}" height="{H}" fill="url(#sky)"/>'
b += '<circle cx="780" cy="170" r="260" fill="url(#sun)"/>'
b += ridge(330, 70, 2, "#b7c6c1", 50, 1, 0.3) + ridge(360, 50, 5, "#9fb3aa", 40, 1, 0.4)
b += '<rect x="0" y="300" width="1200" height="120" fill="url(#mist)"/>'
# 삼나무 숲
trees = ""
for i in range(46):
    x = r.uniform(-20, 1220); h = r.uniform(170, 300)
    if 470 < x < 730: h *= 0.75
    trees += cedar(x, 470 + r.uniform(-10, 15), h, r.uniform(60, 95), "#2e4a3b" if r.random() < 0.6 else "#36553f", "#294336")
b += trees
# 땅
b += '<path d="M0,470 L1200,470 L1200,750 L0,750 Z" fill="#cdbfa8"/>'
b += '<path d="M0,470 C300,455 900,455 1200,470 L1200,520 L0,520 Z" fill="#b9ab93" opacity=".6"/>'
# 본전 (배전): 돌 기단, 기둥, 녹청 동판 지붕, 치기·가쓰오기
hx, hy = 600, 445
b += f'<rect x="{hx-170}" y="{hy-8}" width="340" height="26" fill="#a39a8a"/>'
b += f'<rect x="{hx-150}" y="{hy-95}" width="300" height="90" fill="#f2ebdc"/>'
for px in (-140, -70, 0, 70, 140):
    b += f'<rect x="{hx+px-7}" y="{hy-100}" width="14" height="95" fill="url(#ver)"/>'
b += f'<rect x="{hx-155}" y="{hy-104}" width="310" height="12" fill="#b23b22"/>'
b += f'<rect x="{hx-45}" y="{hy-78}" width="90" height="70" fill="#4a3226"/><rect x="{hx-38}" y="{hy-72}" width="76" height="62" fill="#e9c98a" opacity=".55"/>'
b += f'<path d="M{hx-235},{hy-100} C{hx-170},{hy-112} {hx-120},{hy-140} {hx-95},{hy-190} L{hx+95},{hy-190} C{hx+120},{hy-140} {hx+170},{hy-112} {hx+235},{hy-100} Z" fill="url(#roof)"/>'
b += f'<path d="M{hx-235},{hy-100} C{hx-170},{hy-108} {hx-150},{hy-112} {hx-120},{hy-118} L{hx+120},{hy-118} C{hx+150},{hy-112} {hx+170},{hy-108} {hx+235},{hy-100} L{hx+235},{hy-94} L{hx-235},{hy-94} Z" fill="#2f433d"/>'
b += f'<rect x="{hx-100}" y="{hy-196}" width="200" height="9" fill="#2a3a35"/>'
for kx in (-60, -20, 20, 60):
    b += f'<rect x="{hx+kx-11}" y="{hy-206}" width="22" height="10" rx="5" fill="#c9a24a"/>'
b += f'<path d="M{hx-96},{hy-188} L{hx-128},{hy-236} L{hx-118},{hy-238} L{hx-88},{hy-192} Z" fill="#2a3a35"/><path d="M{hx+96},{hy-188} L{hx+128},{hy-236} L{hx+118},{hy-238} L{hx+88},{hy-192} Z" fill="#2a3a35"/>'
# 금줄
b += f'<path d="M{hx-110},{hy-86} Q{hx},{hy-62} {hx+110},{hy-86}" stroke="#c9a35a" stroke-width="9" fill="none" stroke-linecap="round"/>'
for sx in (-60, 0, 60):
    yy = hy - 74 + (0 if sx == 0 else -6)
    b += f'<path d="M{hx+sx},{yy} l7,0 l0,8 l6,0 l0,9 l6,0 l0,10 l-7,0 l0,-9 l-6,0 l0,-9 l-6,0 Z" fill="#fffdf6"/>'
# 돌길 (원근)
b += '<path d="M540,470 L660,470 L860,750 L340,750 Z" fill="url(#path)"/>'
for i in range(14):
    t = (i / 14) ** 1.6; y = 470 + t * 280; w = 60 + t * 260
    b += f'<line x1="{600-w:.0f}" y1="{y:.0f}" x2="{600+w:.0f}" y2="{y:.0f}" stroke="#a69c8c" stroke-width="{1+t*2:.1f}"/>'
# 석등
def lantern(x, y, s):
    o = f'<rect x="{x-14*s}" y="{y-10*s}" width="{28*s}" height="{10*s}" fill="#8f877a"/>'
    o += f'<rect x="{x-5*s}" y="{y-60*s}" width="{10*s}" height="{50*s}" fill="#9b9385"/>'
    o += f'<rect x="{x-15*s}" y="{y-86*s}" width="{30*s}" height="{24*s}" fill="#f3e2bc"/><rect x="{x-15*s}" y="{y-86*s}" width="{30*s}" height="{24*s}" fill="none" stroke="#8f877a" stroke-width="{3*s}"/>'
    o += f'<path d="M{x-26*s},{y-86*s} L{x},{y-108*s} L{x+26*s},{y-86*s} Z" fill="#7f786c"/><circle cx="{x}" cy="{y-110*s}" r="{4*s}" fill="#7f786c"/>'
    return o
b += lantern(455, 540, 1.0) + lantern(745, 540, 1.0) + lantern(380, 640, 1.5) + lantern(820, 640, 1.5)
# 고마이누 (작게)
for sx, flip in ((505, 1), (695, -1)):
    b += f'<g transform="translate({sx},492) scale({flip},1)"><rect x="-16" y="-6" width="32" height="10" fill="#8a8274"/><path d="M-12,-6 L-12,-26 Q-12,-40 0,-42 Q14,-42 14,-30 L14,-6 Z" fill="#a39b8d"/><circle cx="4" cy="-38" r="9" fill="#8f877a"/></g>'
# 도리이 (앞, 크게)
b += '<rect x="300" y="150" width="34" height="600" fill="url(#ver)"/><rect x="866" y="150" width="34" height="600" fill="url(#ver)"/>'
b += '<rect x="292" y="700" width="50" height="50" fill="#262020"/><rect x="858" y="700" width="50" height="50" fill="#262020"/>'
b += '<rect x="250" y="236" width="700" height="24" fill="#c64626"/>'
b += '<rect x="580" y="170" width="40" height="66" fill="#c64626"/><rect x="586" y="178" width="28" height="50" fill="#2a2320"/><rect x="590" y="182" width="20" height="42" fill="none" stroke="#d9b45a" stroke-width="2"/>'
b += '<path d="M200,150 Q600,128 1000,150 L1004,168 Q600,148 196,168 Z" fill="#c64626"/>'
b += '<path d="M168,118 Q600,96 1032,118 L1050,100 L1046,124 Q600,104 154,124 L150,100 Z" fill="#221c1c"/>'
b += '<path d="M176,124 Q600,104 1024,124 L1022,142 Q600,124 178,142 Z" fill="#221c1c"/>'
# 벚나무 가지 (왼쪽 위에서 늘어짐)
b += '<path d="M-20,40 C80,60 160,40 240,90 C300,130 330,120 400,160 M150,52 C190,10 230,0 290,-10 M240,90 C250,150 230,200 260,240 M80,58 C70,120 100,160 90,210" stroke="#3b2a26" stroke-width="9" fill="none" stroke-linecap="round"/>'
pinks = ["#f6cfd8", "#f0b8c6", "#fbe2e7", "#e9a6b8"]
blos = ""
for (cx, cy, n, rad) in ((60, 70, 26, 70), (190, 60, 30, 80), (300, 120, 24, 70), (250, 220, 18, 55), (95, 200, 18, 55), (390, 165, 14, 45), (280, 10, 18, 60)):
    for _ in range(n):
        a = r.uniform(0, 6.28); d = r.uniform(0, rad)
        x = cx + math.cos(a) * d; y = cy + math.sin(a) * d * 0.75; rr = r.uniform(7, 16)
        blos += f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rr:.1f}" fill="{r.choice(pinks)}" opacity="{r.uniform(.85,1):.2f}"/>'
b += blos
# 흩날리는 꽃잎
for _ in range(70):
    x = r.uniform(0, 1200); y = r.uniform(0, 740); rot = r.uniform(0, 180)
    b += f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{r.uniform(3,6):.1f}" ry="{r.uniform(1.5,3):.1f}" fill="{r.choice(pinks)}" transform="rotate({rot:.0f} {x:.0f} {y:.0f})" opacity=".9"/>'
open("shrine.svg", "w").write(svg(defs, b))
print("ok")
