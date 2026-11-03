import random, math
from common import *
r = random.Random(21)
defs = lingrad("sky", [(0, "#7fb2dc"), (0.6, "#cfe2ec"), (1, "#f6e9d4")]) + lingrad("sea", [(0, "#3f7fb0"), (1, "#6fb0c4")]) \
     + radgrad("sun", [(0, "#fffaf0", 1), (0.2, "#fff2d6", .7), (1, "#fff2d6", 0)]) + lingrad("gravel", [(0, "#a9a39b"), (1, "#8f8a83")]) \
     + lingrad("steel", [(0, "#e4e7ea"), (0.5, "#c3c8cd"), (1, "#9ea4aa")])
b = f'<rect width="{W}" height="{H}" fill="url(#sky)"/>'
b += '<circle cx="250" cy="250" r="260" fill="url(#sun)"/>'
# 엷은 구름
for (x, y, w) in ((700, 110, 260), (980, 70, 200), (420, 60, 160)):
    b += f'<ellipse cx="{x}" cy="{y}" rx="{w}" ry="{w*0.09:.0f}" fill="#ffffff" opacity=".55"/>'
# 바다
b += '<rect x="0" y="330" width="1200" height="90" fill="url(#sea)"/>'
for _ in range(60):
    x = r.uniform(0, 1200); y = r.uniform(336, 410); w = r.uniform(10, 50)
    b += f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="2" fill="#ffffff" opacity="{r.uniform(.25,.7):.2f}"/>'
# 곶과 등대
b += '<path d="M860,332 C940,290 1060,280 1200,300 L1200,345 L860,345 Z" fill="#4f7a55"/><path d="M900,330 C980,300 1080,296 1200,310 L1200,345 L900,345 Z" fill="#5d8a5f"/>'
b += '<rect x="1040" y="262" width="12" height="36" fill="#f6f2ea"/><rect x="1038" y="256" width="16" height="8" fill="#c84a3a"/>'
# 비탈 마을 (지붕만 보임)
b += '<path d="M0,400 C300,390 900,392 1200,384 L1200,545 L0,545 Z" fill="#78a35a"/>'
for (x, c) in ((380, "#4a6e9a"), (520, "#b85a5a"), (660, "#3e6a8a"), (820, "#c87a8e")):
    b += f'<path d="M{x-46},{410} L{x},{388} L{x+46},{410} Z" fill="{c}"/><rect x="{x-38}" y="410" width="76" height="22" fill="#f1ece2"/>'
for _ in range(30):
    x = r.uniform(0, 1200); y = r.uniform(400, 470)
    b += f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{r.uniform(18,40):.0f}" ry="{r.uniform(10,20):.0f}" fill="{r.choice(["#5f8f3e","#6e9e48","#4f7a36"])}"/>'
# 선로
b += '<rect x="0" y="470" width="1200" height="16" fill="#5a5450"/><rect x="0" y="472" width="1200" height="3" fill="#b0a08a"/><rect x="0" y="480" width="1200" height="3" fill="#b0a08a"/>'
# 기차 (313계 모양, 오른쪽에서 들어오는 중)
tx = 860
b += f'<path d="M{tx},428 L{tx+360},428 L{tx+360},482 L{tx},482 Z" fill="url(#steel)"/>'
b += f'<path d="M{tx-26},440 Q{tx-30},428 {tx-6},426 L{tx+10},426 L{tx+10},482 L{tx-26},482 Z" fill="#cfd3d7"/>'
b += f'<rect x="{tx-24}" y="436" width="30" height="16" rx="3" fill="#1f2327"/>'
b += f'<rect x="{tx-26}" y="458" width="390" height="7" fill="#e3642b"/>'
for i in range(6):
    b += f'<rect x="{tx+30+i*52}" y="436" width="34" height="16" rx="2" fill="#2b3137"/>'
b += f'<rect x="{tx+118}" y="434" width="20" height="44" fill="#b4b9be"/><rect x="{tx+250}" y="434" width="20" height="44" fill="#b4b9be"/>'
b += f'<rect x="{tx-22}" y="468" width="10" height="5" rx="2" fill="#fff6dc"/>'
# 승강장 (콘크리트 판 + 철골 다리)
b += '<rect x="120" y="476" width="900" height="22" fill="#9c9894"/><rect x="120" y="476" width="900" height="4" fill="#e8c23a"/>'
for x in range(150, 1000, 70):
    b += f'<rect x="{x}" y="498" width="8" height="40" fill="#6a6e72"/>'
# 노란 난간 + 계단
Y = "#e6b92a"
b += f'<rect x="120" y="436" width="560" height="5" fill="{Y}"/><rect x="120" y="456" width="560" height="4" fill="{Y}"/>'
b += f'<rect x="770" y="436" width="250" height="5" fill="{Y}"/><rect x="770" y="456" width="250" height="4" fill="{Y}"/>'
for x in list(range(120, 690, 56)) + list(range(770, 1030, 56)):
    b += f'<rect x="{x}" y="436" width="5" height="42" fill="{Y}"/>'
for i in range(6):
    b += f'<rect x="{690+i*6}" y="{498+i*10}" width="{84-i*2}" height="8" fill="#8e8a86"/>'
b += f'<path d="M684,436 L684,520 M684,436 L700,560" stroke="{Y}" stroke-width="5" fill="none"/><path d="M770,436 L770,520 M770,436 L790,560" stroke="{Y}" stroke-width="5" fill="none"/>'
# 역 이름판
b += '<rect x="400" y="410" width="160" height="40" fill="#f6f6f2" stroke="#5a5a5a" stroke-width="2"/><rect x="406" y="416" width="26" height="28" fill="#2f9e5a"/>'
b += '<rect x="442" y="420" width="104" height="9" fill="#2a2a2a"/><rect x="452" y="434" width="84" height="5" fill="#6a6a6a"/>'
b += '<rect x="476" y="450" width="5" height="28" fill="#9a9a9a"/>'
# 큰 삼나무 (왼쪽)
for (x, h, w) in ((70, 520, 230), (190, 430, 180), (-30, 460, 200)):
    b += cedar(x, 560, h, w, "#244a2e", "#2d5a36")
# 전봇대와 전선
for x in (300, 980):
    b += f'<rect x="{x}" y="230" width="8" height="330" fill="#8a8680"/><rect x="{x-24}" y="246" width="56" height="5" fill="#6a6660"/>'
b += '<path d="M0,262 Q150,280 304,250 Q640,290 984,250 Q1100,270 1200,262" stroke="#2a2a2a" stroke-width="1.6" fill="none"/>'
b += '<path d="M0,276 Q150,294 304,262 Q640,302 984,262 Q1100,284 1200,276" stroke="#2a2a2a" stroke-width="1.2" fill="none"/>'
# 엑스 표지와 반사 거울
b += '<rect x="1072" y="430" width="5" height="130" fill="#9a9a9a"/><g transform="translate(1074,420) rotate(45)"><rect x="-22" y="-22" width="44" height="44" fill="#fff" stroke="#e8784a" stroke-width="5"/></g>'
b += '<path d="M1062,410 L1086,430 M1086,410 L1062,430" stroke="#111" stroke-width="5"/>'
b += '<rect x="905" y="380" width="5" height="180" fill="#b0b0b0"/><circle cx="907" cy="372" r="26" fill="#6ea8d8" stroke="#d86a3a" stroke-width="6"/>'
# 자갈 마당 (앞)
b += '<path d="M0,540 L1200,540 L1200,750 L0,750 Z" fill="url(#gravel)"/>'
for _ in range(500):
    x = r.uniform(0, 1200); y = r.uniform(545, 750); rr = r.uniform(1, 3.2)
    b += f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{rr:.1f}" ry="{rr*0.6:.1f}" fill="{r.choice(["#6f6c69","#c4c0b8","#7d7975"])}"/>'
# 안내판 (앞 왼쪽)
b += '<rect x="230" y="600" width="12" height="70" fill="#b4b0a8"/><rect x="380" y="600" width="12" height="70" fill="#b4b0a8"/><rect x="214" y="560" width="194" height="64" fill="#e8ecee" stroke="#5a5a5a" stroke-width="3"/>'
b += '<rect x="226" y="572" width="80" height="8" fill="#1f8a5c"/><rect x="226" y="588" width="160" height="4" fill="#8a8a8a"/><rect x="226" y="598" width="140" height="4" fill="#8a8a8a"/><rect x="226" y="608" width="150" height="4" fill="#8a8a8a"/>'
# 풀 (오른쪽 앞)
for _ in range(80):
    x = r.uniform(1000, 1220); y = r.uniform(600, 760); hgt = r.uniform(30, 80)
    b += f'<path d="M{x:.0f},{y:.0f} q{r.uniform(-8,8):.0f},{-hgt/2:.0f} {r.uniform(-14,14):.0f},{-hgt:.0f}" stroke="{r.choice(["#6e9e48","#86b25a","#5f8f3e"])}" stroke-width="3" fill="none"/>'
open("station.svg", "w").write(svg(defs, b))
print("ok")
