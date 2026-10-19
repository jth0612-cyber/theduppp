"""BULLPEN → INNING layout: single column (INNING's column def), delete the page rule and the TAG,
widen the full-width tables to INNING's width and grow nested tables by the same amount.
usage: bullpen_layout.py bullpen.hwp inning.hwp out.hwp"""
import sys, zlib, struct
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from cfbwrite import write, read_all
from hwp_fonts import recs, pack
def load(path):
    st, cl = read_all(path); comp = bool(struct.unpack_from('<I', st[('FileHeader',)], 36)[0] & 1)
    d = st[('BodyText', 'Section0')]; return st, cl, comp, recs(zlib.decompress(d, -15) if comp else d)
def cid(r): return bytes(r[:4][::-1]).decode('latin1')
src, ref, dst = sys.argv[1:4]
st, cl, comp, rs = load(src); _, _, _, ref_rs = load(ref)
ref_cold = next(r for t, l, r in ref_rs if t == 71 and cid(r) == 'cold')
ref_w = next(struct.unpack_from('<I', r, 16)[0] for t, l, r in ref_rs if t == 71 and cid(r) == 'tbl ')   # INNING header table width
def subtree_end(i):
    lvl = rs[i][1]; j = i + 1
    while j < len(rs) and rs[j][1] > lvl: j += 1
    return j
# ---- 1. first paragraph: locate its controls in text order
assert rs[0][0] == 66 and rs[1][0] == 67
txt = list(struct.unpack_from('<%dH' % (len(rs[1][2]) // 2), rs[1][2]))
ctrl_pos = []; j = 0
while j < len(txt):
    c = txt[j]
    if c < 32 and c not in (0, 10, 13) and not (24 <= c <= 31): ctrl_pos.append(j); j += 8
    else: j += 1
top_ctrls = [i for i in range(len(rs)) if rs[i][0] == 71 and rs[i][1] == 1 and i < subtree_end(0)]
assert len(top_ctrls) == len(ctrl_pos), (len(top_ctrls), len(ctrl_pos))
def is_tag(i):
    e = subtree_end(i); s = ''
    for k in range(i, e):
        if rs[k][0] == 67: s += ''.join(chr(c) for c in struct.unpack_from('<%dH' % (len(rs[k][2]) // 2), rs[k][2]) if c >= 32)
    return cid(rs[i][2]) == 'tbl ' and s.endswith('TAG') and struct.unpack_from('<I', rs[i][2], 16)[0] < 5000
def is_rule(i):
    r = rs[i][2]; return cid(r) == 'gso ' and struct.unpack_from('<I', r, 16)[0] <= 10 and struct.unpack_from('<I', r, 20)[0] > 30000
drop = [(p, i) for p, i in zip(ctrl_pos, top_ctrls) if is_tag(i) or is_rule(i)]
assert len(drop) == 2, drop
# text: remove the 8-WCHAR control slots (back to front)
for p, _ in sorted(drop, reverse=True): del txt[p:p + 8]
rs[1][2] = bytearray(struct.pack('<%dH' % len(txt), *txt))
hdr = rs[0][2]; n, = struct.unpack_from('<I', hdr, 0); struct.pack_into('<I', hdr, 0, (n & 0x80000000) | ((n & 0x7FFFFFFF) - 8 * len(drop)))
def shift(pos):
    return pos - sum(8 for p, _ in drop if pos >= p + 8) - sum(pos - p for p, _ in drop if p <= pos < p + 8)
for k in range(1, subtree_end(0)):
    t, l, r = rs[k]
    if l != 1: continue
    if t == 68:      # PARA_CHAR_SHAPE
        pairs = struct.unpack_from('<%dI' % (len(r) // 4), r); seen = {}
        for pos, csid in zip(pairs[0::2], pairs[1::2]): seen[shift(pos)] = csid
        new = sorted(seen.items()); rs[k][2] = bytearray(b''.join(struct.pack('<II', a, b) for a, b in new))
        struct.pack_into('<H', hdr, 12, len(new))
    elif t == 69:    # LINE_SEG textpos
        for s in range(0, len(r), 36):
            tp, = struct.unpack_from('<I', r, s); struct.pack_into('<I', r, s, shift(tp))
# ---- 2. column definition: INNING's single column
for k in range(len(rs)):
    if rs[k][0] == 71 and cid(rs[k][2]) == 'cold' and rs[k][1] == 1: rs[k][2] = bytearray(ref_cold)
# ---- 3. delete rule + TAG subtrees (back to front)
for _, i in sorted(drop, key=lambda x: -x[1]): del rs[i:subtree_end(i)]
# ---- 4. widen tables
old_full = None; changes = []
def resize_table(i, new_w):
    r = rs[i][2]; old_w, = struct.unpack_from('<I', r, 16); struct.pack_into('<I', r, 16, new_w)
    lvl = rs[i][1]; e = subtree_end(i)
    cells = [k for k in range(i + 1, e) if rs[k][0] == 72 and rs[k][1] == lvl + 1]
    rows = {}
    for k in cells: rows.setdefault(struct.unpack_from('<H', rs[k][2], 10)[0], []).append(k)
    for row in rows.values():
        ws = [struct.unpack_from('<I', rs[k][2], 16)[0] for k in row]; tot = sum(ws)
        nws = [round(w * new_w / old_w) for w in ws]; nws[-1] += round(tot * new_w / old_w) - sum(nws)
        for k, w0, w1 in zip(row, ws, nws):
            c = rs[k][2]; struct.pack_into('<I', c, 16, w1)
            if len(c) >= 40 and struct.unpack_from('<I', c, 36)[0] == w0: struct.pack_into('<I', c, 36, w1)
            # paragraphs directly in this cell: widen their line segments
            ce = k + 1
            while ce < e and not (rs[ce][1] <= lvl + 1 and rs[ce][0] != 66): ce += 1
            for q in range(k + 1, ce):
                if rs[q][0] == 69 and rs[q][1] == lvl + 2:
                    seg = rs[q][2]
                    for s in range(0, len(seg), 36):
                        hs, = struct.unpack_from('<i', seg, s + 28)
                        if hs > 0: struct.pack_into('<i', seg, s + 28, hs + (w1 - w0))
    changes.append((cid(r), lvl, old_w, new_w, len(cells)))
    return old_w
top_tables = [k for k in range(len(rs)) if rs[k][0] == 71 and cid(rs[k][2]) == 'tbl ' and rs[k][1] == 1]
for k in top_tables:
    old = resize_table(k, ref_w); delta = ref_w - old
    boxcells = [c for c in range(k + 1, subtree_end(k)) if rs[c][0] == 72 and rs[c][1] == rs[k][1] + 1]
    inner = old - (sum(struct.unpack_from('<2H', rs[boxcells[0]][2], 24)) if len(boxcells) == 1 else 0)
    for q in range(k + 1, subtree_end(k)):
        if rs[q][0] == 71 and cid(rs[q][2]) == 'tbl ' and rs[q][1] == rs[k][1] + 2:
            w, = struct.unpack_from('<I', rs[q][2], 16)
            if w >= 0.85 * inner: resize_table(q, w + delta)      # full-width tables grow; smaller figure tables keep their size
            else: print('  kept size', w, 'of', inner)
for c in changes: print('  table', c)
out = pack(rs)
if comp:
    z = zlib.compressobj(9, zlib.DEFLATED, -15); out = z.compress(out) + z.flush()
st[('BodyText', 'Section0')] = out
write(dst, st, cl)
print('removed', [cid(bytes(x)) for x in ()], 'ok')
