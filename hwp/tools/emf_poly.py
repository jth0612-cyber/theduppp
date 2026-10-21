"""단색 다각형만으로 된 고해상도 EMF를 쓴다 (한글 틀 그림용).
shapes: [(hex색, [(x_mm, y_mm), ...]), ...]  — 단위 mm, 원점 왼쪽 위"""
import struct

PX_PER_MM = 47.24          # 원본 틀 EMF와 같은 해상도 (약 1200dpi)
DEV_PX, DEV_MM = 4724, 100


def _rec(t, payload):
    return struct.pack('<II', t, 8 + len(payload)) + payload


def write(path, w_mm, h_mm, shapes):
    px = lambda v: int(round(v * PX_PER_MM))
    W, H = px(w_mm), px(h_mm)
    body = []
    body.append(_rec(38, struct.pack('<IIiiI', 1, 5, 0, 0, 0)))          # CREATEPEN 1: PS_NULL
    body.append(_rec(37, struct.pack('<I', 1)))                           # SELECTOBJECT pen
    for i, (col, pts) in enumerate(shapes):
        c = col.lstrip('#'); r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        body.append(_rec(39, struct.pack('<IIBBBBI', 2, 0, r, g, b, 0, 0)))   # CREATEBRUSHINDIRECT 2
        body.append(_rec(37, struct.pack('<I', 2)))
        P = [(px(x), px(y)) for x, y in pts]
        xs, ys = [p[0] for p in P], [p[1] for p in P]
        body.append(_rec(3, struct.pack('<4iI', min(xs), min(ys), max(xs), max(ys), len(P)) +
                         b''.join(struct.pack('<ii', *p) for p in P)))       # POLYGON
        body.append(_rec(37, struct.pack('<I', 0x80000000)))                 # 기본 브러시로 되돌림
        body.append(_rec(40, struct.pack('<I', 2)))                           # DELETEOBJECT
    body.append(_rec(14, struct.pack('<III', 0, 16, 20)))                      # EOF
    recs = b''.join(body)
    n = len(body) + 1
    hdr_payload = struct.pack('<4i4iIIIIHHIIIiiii',
                              0, 0, W - 1, H - 1,
                              0, 0, int(w_mm * 100) - 1, int(h_mm * 100) - 1,
                              0x464D4520, 0x10000, 88 + len(recs), n, 3, 0, 0, 0, 0,
                              DEV_PX, DEV_PX, DEV_MM, DEV_MM)
    hdr = struct.pack('<II', 1, 88) + hdr_payload
    assert len(hdr) == 88
    open(path, 'wb').write(hdr + recs)
