"""단색 다각형(구멍 있는 글자 윤곽 포함)으로 된 고해상도 EMF를 쓴다 (한글 틀 그림용).
shapes: [(hex색, [윤곽1, 윤곽2, ...]), ...]  윤곽 = [(x_mm, y_mm), ...], 원점 왼쪽 위.
한 도형 안의 여러 윤곽은 ALTERNATE 규칙으로 채워 글자 속 구멍(A, G)이 뚫린다."""
import struct

# 원본 틀 EMF(이미지배경_TAG.emf)와 같은 기준 장치 — 한글은 108바이트 머리의 szlMicrometers까지 읽으므로
# 머리를 짧게 쓰면 그림이 약 1.1배로 커져 잘린다
DEV_PX, DEV_MM = (10205, 13181), (216, 279)
PX_PER_MM = DEV_PX[0] / DEV_MM[0]


def _rec(t, payload):
    return struct.pack('<II', t, 8 + len(payload)) + payload


def write(path, w_mm, h_mm, shapes):
    px = lambda v: int(round(v * PX_PER_MM))
    W, H = px(w_mm), px(h_mm)
    body = [_rec(19, struct.pack('<I', 1)),                                 # SETPOLYFILLMODE ALTERNATE
            _rec(38, struct.pack('<IIiiI', 1, 5, 0, 0, 0)),                 # CREATEPEN 1: PS_NULL
            _rec(37, struct.pack('<I', 1))]
    for col, polys in shapes:
        if polys and isinstance(polys[0][0], (int, float)):
            polys = [polys]
        c = col.lstrip('#'); r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        body.append(_rec(39, struct.pack('<IIBBBBI', 2, 0, r, g, b, 0, 0)))  # CREATEBRUSHINDIRECT 2
        body.append(_rec(37, struct.pack('<I', 2)))
        P = [[(px(x), px(y)) for x, y in poly] for poly in polys]
        allp = [p for poly in P for p in poly]
        xs, ys = [p[0] for p in allp], [p[1] for p in allp]
        payload = struct.pack('<4iII', min(xs), min(ys), max(xs), max(ys), len(P), len(allp))
        payload += b''.join(struct.pack('<I', len(poly)) for poly in P)
        payload += b''.join(struct.pack('<ii', *p) for p in allp)
        body.append(_rec(8, payload))                                       # POLYPOLYGON
        body.append(_rec(37, struct.pack('<I', 0x80000000)))
        body.append(_rec(40, struct.pack('<I', 2)))                         # DELETEOBJECT
    body.append(_rec(14, struct.pack('<III', 0, 16, 20)))                   # EOF
    recs = b''.join(body)
    hdr = struct.pack('<II', 1, 108) + struct.pack('<4i4iIIIIHHIIIiiiiIIIii',
                                                   0, 0, W - 1, H - 1,
                                                   0, 0, int(round(w_mm * 100)) - 1, int(round(h_mm * 100)) - 1,
                                                   0x464D4520, 0x10000, 108 + len(recs), len(body) + 1, 3, 0, 0, 0, 0,
                                                   DEV_PX[0], DEV_PX[1], DEV_MM[0], DEV_MM[1],
                                                   0, 0, 0, DEV_MM[0] * 1000, DEV_MM[1] * 1000)
    assert len(hdr) == 108
    open(path, 'wb').write(hdr + recs)
    return W, H


def text_outline(fontfile, s, size_pt, tracking_pt=0.0, steps=8):
    """글자 윤곽을 mm 단위 다각형 목록으로 (기준선 y=0, 위쪽이 음수). 반환: (윤곽들, 폭mm, (ymin, ymax))"""
    from fontTools.ttLib import TTFont
    from fontTools.pens.basePen import BasePen
    f = TTFont(fontfile); gs = f.getGlyphSet(); cmap = f.getBestCmap(); upm = f['head'].unitsPerEm
    k = size_pt / upm * 25.4 / 72
    polys, x0 = [], 0.0

    class Pen(BasePen):
        def __init__(self, gs, dx):
            super().__init__(gs); self.dx = dx; self.cur = None
        def _moveTo(self, p):
            self.cur = [p]; polys.append(self.cur)
        def _lineTo(self, p):
            self.cur.append(p)
        def _curveToOne(self, p1, p2, p3):
            p0 = self.cur[-1]
            for i in range(1, steps + 1):
                t = i / steps; u = 1 - t
                self.cur.append(tuple(u**3*a + 3*u*u*t*b + 3*u*t*t*c + t**3*d for a, b, c, d in zip(p0, p1, p2, p3)))
        def _qCurveToOne(self, p1, p2):
            p0 = self.cur[-1]
            for i in range(1, steps + 1):
                t = i / steps; u = 1 - t
                self.cur.append(tuple(u*u*a + 2*u*t*b + t*t*c for a, b, c in zip(p0, p1, p2)))
        def _closePath(self):
            pass
    out = []
    for i, ch in enumerate(s):
        gn = cmap[ord(ch)]; start = len(polys)
        gs[gn].draw(Pen(gs, 0))
        for poly in polys[start:]:
            out.append([(x0 + x * k, -y * k) for x, y in poly])
        x0 += gs[gn].width * k + (tracking_pt * 25.4 / 72 if i < len(s) - 1 else 0)
    ys = [p[1] for poly in out for p in poly]; xs = [p[0] for poly in out for p in poly]
    return out, (min(xs), max(xs)), (min(ys), max(ys))
