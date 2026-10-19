"""Delete side-note reference numbers (8pt teal bold digits) from body paragraphs (not the notes themselves).
usage: drop_note_marks.py in.hwp out.hwp"""
import sys, struct, zlib
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from cfbwrite import read_all, write
from hwp_fonts import recs, pack
from hwp5 import Hwp
src, dst = sys.argv[1:3]
h = Hwp(src)
mark_cs = {i for i, c in enumerate(h.cs) if c['size'] == 800 and c['bold'] and c['color'] == '#009FBB'}
st, cl = read_all(src)
rs = recs(zlib.decompress(st[('BodyText', 'Section0')], -15))
styles = h.styles
n_del = 0
for i, (t, l, r) in enumerate(rs):
    if t != 66: continue
    if styles[r[10]].startswith('143_'): continue                # the side notes themselves go with the side column
    kids = {}
    j = i + 1
    while j < len(rs) and rs[j][1] > l:
        if rs[j][1] == l + 1 and rs[j][0] in (67, 68, 69): kids[rs[j][0]] = j
        j += 1
    if 67 not in kids or 68 not in kids: continue
    w = list(struct.unpack_from('<%dH' % (len(rs[kids[67]][2]) // 2), rs[kids[67]][2]))
    pairs = list(struct.unpack_from('<%dI' % (len(rs[kids[68]][2]) // 4), rs[kids[68]][2]))
    runs = list(zip(pairs[0::2], pairs[1::2]))
    dels = []
    for k, (pos, cs) in enumerate(runs):
        if cs not in mark_cs: continue
        end = runs[k + 1][0] if k + 1 < len(runs) else len(w)
        dels += [q for q in range(pos, min(end, len(w))) if 48 <= w[q] <= 57]
    if not dels: continue
    dset = set(dels)
    shift = lambda p: p - sum(1 for d in dels if d < p)
    w = [c for q, c in enumerate(w) if q not in dset]
    rs[kids[67]][2] = bytearray(struct.pack('<%dH' % len(w), *w))
    newp = {}
    for pos, cs in runs: newp[shift(pos)] = cs                    # later run wins at a collapsed position
    newp = sorted(newp.items())
    rs[kids[68]][2] = bytearray(b''.join(struct.pack('<II', a, b) for a, b in newp))
    struct.pack_into('<H', r, 12, len(newp))
    nc, = struct.unpack_from('<I', r, 0); struct.pack_into('<I', r, 0, (nc & 0x80000000) | ((nc & 0x7FFFFFFF) - len(dels)))
    if 69 in kids:
        seg = rs[kids[69]][2]
        for s in range(0, len(seg), 36):
            tp, = struct.unpack_from('<I', seg, s); struct.pack_into('<I', seg, s, shift(tp))
    n_del += len(dels)
z = zlib.compressobj(9, zlib.DEFLATED, -15); st[('BodyText', 'Section0')] = z.compress(pack(rs)) + z.flush()
write(dst, st, cl)
print('note reference digits removed:', n_del)
