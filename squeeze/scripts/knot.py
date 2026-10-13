# 표지 그래픽: 토러스 매듭을 중심선으로, 여러 가닥이 비틀리며 감기는 케이블을 3D 투영.
# 깊이 순서대로 (흰 테두리 + 선) 세그먼트를 그려 실제 위/아래 교차(매듭)를 만든다. 결과는 SVG.
import numpy as np, sys, math

def knot_svg(path, W, H, cx, cy, scale, p=3, q=7, R=1.0, r=0.42, tube=0.13, strands=14, twist=11,
             tilt=58, rotz=18, n=5200, lw=0.32, halo=1.5, spot_every=7, spot='#00A2DB', ink='#231F20',
             bg=None, halo_col='#FFFFFF', mode='tube'):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    # 토러스 매듭 중심선
    c = np.stack([(R + r * np.cos(q * t)) * np.cos(p * t), (R + r * np.cos(q * t)) * np.sin(p * t), r * np.sin(q * t)], 1)
    d = np.gradient(c, axis=0); T = d / np.linalg.norm(d, axis=1)[:, None]
    # 회전 최소화 프레임(평행 이동)
    N = np.zeros_like(T); a = np.array([0, 0, 1.0])
    N[0] = np.cross(T[0], a); N[0] /= np.linalg.norm(N[0])
    for i in range(1, n):
        v = N[i - 1] - np.dot(N[i - 1], T[i]) * T[i]; N[i] = v / np.linalg.norm(v)
    B = np.cross(T, N)
    # 닫힌 곡선에서 프레임 어긋남(홀로노미) 보정각
    ang0 = math.atan2(np.dot(np.cross(N[-1], N[0]), T[0]), np.dot(N[-1], N[0]))
    # 뷰 회전
    ct, st = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
    cz, sz = math.cos(math.radians(rotz)), math.sin(math.radians(rotz))
    Rx = np.array([[1, 0, 0], [0, ct, -st], [0, st, ct]]); Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    M = Rz @ Rx
    segs = []
    for k in range(strands):
        if mode == 'tube':
            phi = 2 * np.pi * k / strands + twist * t + ang0 * t / (2 * np.pi)
            P = c + tube * (np.cos(phi)[:, None] * N + np.sin(phi)[:, None] * B)
        else:   # 리본: 평평한 띠가 중심선을 따라 비틀리며 회전
            sk = -1 + 2 * k / (strands - 1)
            phi = twist * t + ang0 * t / (2 * np.pi)
            P = c + tube * sk * (np.cos(phi)[:, None] * N + np.sin(phi)[:, None] * B)
        P = P @ M.T
        col = spot if (spot_every and k % spot_every == 0) else ink
        X = cx + scale * P[:, 0]; Y = cy - scale * P[:, 1]; Z = P[:, 2]
        for i in range(n):
            j = (i + 1) % n
            segs.append(((Z[i] + Z[j]) / 2, X[i], Y[i], X[j], Y[j], col))
    segs.sort(key=lambda s: s[0])
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">']
    if bg: out.append(f'<rect width="{W}" height="{H}" fill="{bg}"/>')
    # 묶음: 같은 깊이 근처 세그먼트를 연속으로 쓰되, 순서는 유지
    for z, x0, y0, x1, y1, col in segs:
        out.append(f'<path d="M{x0:.3f} {y0:.3f}L{x1:.3f} {y1:.3f}" stroke="{halo_col}" stroke-width="{halo * 0.3528:.3f}" stroke-linecap="butt"/>'
                   f'<path d="M{x0:.3f} {y0:.3f}L{x1:.3f} {y1:.3f}" stroke="{col}" stroke-width="{lw * 0.3528:.3f}" stroke-linecap="round"/>')
    out.append('</svg>')
    open(path, 'w').write('\n'.join(out))

if __name__ == '__main__':
    import pymupdf as f
    tests = [(2, 5, 3), (3, 7, 4), (3, 5, 5), (2, 7, 3)]
    for p, q, tw in tests:
        knot_svg(f'cv/test_{p}_{q}.svg', 120, 120, 60, 60, 38, p=p, q=q, n=3000, strands=22, mode='ribbon', tube=0.16, twist=tw, halo=1.1, spot_every=0)
        doc = f.open(f'cv/test_{p}_{q}.svg'); doc[0].get_pixmap(dpi=110).save(f'cv/test_{p}_{q}.png')
