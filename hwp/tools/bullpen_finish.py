"""After bullpen_layout: top-level line segments to INNING width; drop empty side-column filler paragraphs.
usage: bullpen_finish.py in.hwp inning.hwp out.hwp"""
import sys, struct, zlib
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from hwpdump import body
from cfbwrite import read_all, write
from hwp_fonts import pack
src, ref, dst = sys.argv[1:4]
rs = body(src); b = body(ref)
full = max(struct.unpack_from('<i', r, s + 28)[0] for t, l, r in b if t == 69 and l == 1 for s in range(0, len(r), 36))
main_w = None
for t, l, r in rs:
    if t == 69 and l == 1:
        for s in range(0, len(r), 36):
            v, = struct.unpack_from('<i', r, s + 28)
            if v > 20000: main_w = v; struct.pack_into('<i', r, s + 28, full)
side = [i for i, (t, l, r) in enumerate(rs) if t == 69 and l == 1 and 0 < struct.unpack_from('<i', r, 28)[0] < 20000]
if side:
    start = side[0] - 2
    assert rs[start][0] == 66 and rs[start][1] == 0 and not any(t == 67 for t, l, r in rs[start:])
    del rs[start:]
    last = max(i for i, (t, l, r) in enumerate(rs) if t == 66 and l == 0)
    n, = struct.unpack_from('<I', rs[last][2], 0); struct.pack_into('<I', rs[last][2], 0, n | 0x80000000)
st, cl = read_all(src)
z = zlib.compressobj(9, zlib.DEFLATED, -15); st[('BodyText', 'Section0')] = z.compress(pack(rs)) + z.flush()
write(dst, st, cl)
print('line width', main_w, '->', full, '| side filler paragraphs removed', len(side))
