import random, math
W, H = 1200, 750
def grain(op=0.07, freq=0.85):
    return f'''<filter id="grain" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="{freq}" numOctaves="2" stitchTiles="stitch"/>
<feColorMatrix type="saturate" values="0"/><feComponentTransfer><feFuncA type="table" tableValues="0 {op}"/></feComponentTransfer></filter>'''
def grain_rect():
    return f'<rect width="{W}" height="{H}" filter="url(#grain)"/>'
def svg(defs, body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}"><defs>{grain()}{defs}</defs>{body}{grain_rect()}</svg>'''
def lingrad(id, stops, x1=0, y1=0, x2=0, y2=1):
    s = "".join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in [(st + (1,))[:3] if len(st) == 2 else st for st in stops])
    return f'<linearGradient id="{id}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">{s}</linearGradient>'
def radgrad(id, stops, cx=0.5, cy=0.5, r=0.5):
    s = "".join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in [(st + (1,))[:3] if len(st) == 2 else st for st in stops])
    return f'<radialGradient id="{id}" cx="{cx}" cy="{cy}" r="{r}">{s}</radialGradient>'
def ridge(y, amp, seed, col, step=40, op=1, jag=0.5):
    r = random.Random(seed); pts = [(0, H)]; x = 0
    while x <= W + step:
        pts.append((x, y - amp * (0.5 + 0.5 * math.sin(x / 170 + seed)) - r.random() * amp * jag)); x += step
    pts.append((W, H))
    return f'<path d="M{" L".join(f"{a:.0f},{b:.0f}" for a, b in pts)} Z" fill="{col}" opacity="{op}"/>'
def cedar(x, base, h, w, col, col2=None):
    # 층층이 쌓인 삼나무 실루엣
    s = f'<rect x="{x - w * 0.04:.0f}" y="{base - h * 0.15:.0f}" width="{w * 0.08:.0f}" height="{h * 0.15:.0f}" fill="#3a2c24"/>'
    for i in range(5):
        t = i / 5; yy = base - h * (0.12 + t * 0.85); ww = w * (1 - t * 0.75)
        s += f'<path d="M{x - ww / 2:.0f},{yy + h * 0.24:.0f} L{x:.0f},{yy - h * 0.06:.0f} L{x + ww / 2:.0f},{yy + h * 0.24:.0f} Z" fill="{col if i % 2 == 0 or not col2 else col2}"/>'
    return s
