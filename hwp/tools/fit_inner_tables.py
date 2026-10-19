"""Make every table nested in the full-width box exactly as wide as the box's text area
(box width - cell margins - the nested table's own outer margins), so all of them share the same edges.
usage: fit_inner_tables.py in.hwp out.hwp"""
import sys, struct, zlib
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from hwpdump import body
from cfbwrite import read_all, write
from hwp_fonts import pack
src, dst = sys.argv[1:3]
rs = body(src)
def end(i):
    l = rs[i][1]; j = i + 1
    while j < len(rs) and rs[j][1] > l: j += 1
    return j
def is_tbl(i): return rs[i][0] == 71 and bytes(rs[i][2][:4][::-1]) == b'tbl '
def cells(i): return [k for k in range(i + 1, end(i)) if rs[k][0] == 72 and rs[k][1] == rs[i][1] + 1]
def resize(i, new_w):
    r = rs[i][2]; old_w, = struct.unpack_from('<I', r, 16); struct.pack_into('<I', r, 16, new_w)
    lvl = rs[i][1]; e = end(i); rows = {}
    for k in cells(i): rows.setdefault(struct.unpack_from('<H', rs[k][2], 10)[0], []).append(k)
    for row in rows.values():
        ws = [struct.unpack_from('<I', rs[k][2], 16)[0] for k in row]; tot = sum(ws)
        nws = [round(w * new_w / tot) for w in ws]; nws[-1] += new_w - sum(nws)
        for k, w0, w1 in zip(row, ws, nws):
            c = rs[k][2]; struct.pack_into('<I', c, 16, w1)
            if len(c) >= 40 and struct.unpack_from('<I', c, 36)[0] == w0: struct.pack_into('<I', c, 36, w1)
            ce = k + 1
            while ce < e and not (rs[ce][1] <= lvl + 1 and rs[ce][0] != 66): ce += 1
            for q in range(k + 1, ce):
                if rs[q][0] == 69 and rs[q][1] == lvl + 2:
                    seg = rs[q][2]
                    for s in range(0, len(seg), 36):
                        hs, = struct.unpack_from('<i', seg, s + 28)
                        if hs > 0: struct.pack_into('<i', seg, s + 28, hs + (w1 - w0))
    return old_w
box = next(i for i in range(len(rs)) if is_tbl(i) and rs[i][1] == 1 and any(is_tbl(q) for q in range(i + 1, end(i))))
bw, = struct.unpack_from('<I', rs[box][2], 16); bc = rs[cells(box)[0]][2]
ml, mr = struct.unpack_from('<2H', bc, 24)
for q in range(box + 1, end(box)):
    if is_tbl(q) and rs[q][1] == rs[box][1] + 2:
        ol, orr = struct.unpack_from('<2h', rs[q][2], 28)
        target = bw - ml - mr - ol - orr
        cur, = struct.unpack_from('<I', rs[q][2], 16)
        if cur < 0.85 * target: print('  inner table kept', cur); continue
        old = resize(q, target); print('  inner table', old, '->', target)
st, cl = read_all(src)
z = zlib.compressobj(9, zlib.DEFLATED, -15); st[('BodyText', 'Section0')] = z.compress(pack(rs)) + z.flush()
write(dst, st, cl)
