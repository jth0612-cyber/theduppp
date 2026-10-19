"""Re-font an HWP 5.0 file: add face names, repoint char shapes by rule, rewrite the compound file.
usage: hwp_fonts.py in.hwp out.hwp"""
import sys, zlib, struct, collections
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from cfbwrite import write, read_all
LANGS = ['hangul', 'latin', 'hanja', 'japanese', 'other', 'symbol', 'user']
# (current hangul face, size, bold, color) -> (new face, bold, template family for face-type info)
RULES = {
 # INNING
 ('Pretendard', 2400, True, '#E78246'): ('SUIT ExtraBold', False, 'Pretendard'),
 ('Pretendard', 1400, True, '#E78246'): ('Hahmlet SemiBold', False, 'KoPubWorld바탕체 Light'),
 ('Pretendard', 1050, True, '#E78246'): ('나눔바른고딕', True, 'Pretendard'),
 ('KoPubWorld바탕체 Light', 1050, False, '#000000'): ('Hahmlet Light', False, 'KoPubWorld바탕체 Light'),
 # BULLPEN
 ('Pretendard ExtraBold', 1100, False, '#C24D97'): ('LINE Seed Sans KR Bold', False, 'Pretendard'),
 ('Pretendard SemiBold', 1000, False, '#000000'): ('Spoqa Han Sans Neo Bold', False, 'Pretendard'),
 ('Pretendard', 800, False, '#000000'): ('SUIT', False, 'Pretendard'),
 ('Pretendard', 900, True, '#C24D97'): ('나눔바른고딕', True, 'Pretendard'),
 ('Pretendard SemiBold', 800, False, '#000000'): ('SUIT SemiBold', False, 'Pretendard'),
}
def recs(data):
    out = []; i = 0
    while i < len(data):
        h, = struct.unpack_from('<I', data, i); i += 4
        tag, lvl, size = h & 0x3FF, (h >> 10) & 0x3FF, (h >> 20) & 0xFFF
        if size == 0xFFF: size, = struct.unpack_from('<I', data, i); i += 4
        out.append([tag, lvl, bytearray(data[i:i + size])]); i += size
    return out
def pack(rs):
    b = bytearray()
    for tag, lvl, r in rs:
        if len(r) >= 0xFFF: b += struct.pack('<II', tag | (lvl << 10) | (0xFFF << 20), len(r))
        else: b += struct.pack('<I', tag | (lvl << 10) | (len(r) << 20))
        b += r
    return bytes(b)
def face_name(r):
    n, = struct.unpack_from('<H', r, 1); return r[3:3 + 2 * n].decode('utf-16le')
def make_face(tpl, name):
    p = tpl[0]; n, = struct.unpack_from('<H', tpl, 1); i = 3 + 2 * n
    if p & 0x80: i += 1; m, = struct.unpack_from('<H', tpl, i); i += 2 + 2 * m
    typeinfo = tpl[i:i + 10] if p & 0x40 else b''
    nm = name.encode('utf-16le')
    return bytearray(bytes([(p & 0x40) | 0x20 | (p & 0x01)]) + struct.pack('<H', len(name)) + nm + typeinfo + struct.pack('<H', len(name)) + nm)

def main(src, dst):
    streams, clsids = read_all(src)
    hdr = streams[('FileHeader',)]; compressed = bool(struct.unpack_from('<I', hdr, 36)[0] & 1)
    di = streams[('DocInfo',)]; di = zlib.decompress(di, -15) if compressed else di
    rs = recs(di)
    idm = next(r for r in rs if r[0] == 17)[2]
    counts = list(struct.unpack_from('<%dI' % (len(idm) // 4), idm))
    face_idx = [k for k, r in enumerate(rs) if r[0] == 19]
    groups = {}; pos = 0
    for li, l in enumerate(LANGS):
        groups[l] = face_idx[pos:pos + counts[1 + li]]; pos += counts[1 + li]
    names = {l: [face_name(rs[k][2]) for k in groups[l]] for l in LANGS}
    # add new faces at the end of each language group
    wanted = sorted({(v[0], v[2]) for v in RULES.values()})
    new_id = {l: {} for l in LANGS}; inserts = []
    for li, l in enumerate(LANGS):
        added = []
        for face, tplname in wanted:
            if face in names[l]: new_id[l][face] = names[l].index(face); continue
            tpl = next((rs[k][2] for k in groups[l] if face_name(rs[k][2]) == tplname), rs[groups[l][0]][2])
            new_id[l][face] = counts[1 + li] + len(added); added.append(make_face(tpl, face))
        inserts.append((groups[l][-1], added)); counts[1 + li] += len(added)
    for after, added in sorted(inserts, key=lambda x: -x[0]):
        lvl = rs[after][1]
        for a in reversed(added): rs.insert(after + 1, [19, lvl, a])
    struct.pack_into('<%dI' % len(counts), idm, 0, *counts)
    # char shapes
    rep = collections.Counter(); untouched = collections.Counter()
    for tag, lvl, r in rs:
        if tag != 21: continue
        f = struct.unpack_from('<7H', r, 0); size, prop = struct.unpack_from('<iI', r, 42); color, = struct.unpack_from('<I', r, 52)
        col = '#%02X%02X%02X' % (color & 255, (color >> 8) & 255, (color >> 16) & 255)
        key = (names['hangul'][f[0]], size, bool(prop & 2), col)
        if key not in RULES: untouched[key] += 1; continue
        face, bold, _ = RULES[key]
        struct.pack_into('<7H', r, 0, *[new_id[l][face] for l in LANGS])
        prop = (prop | 2) if bold else (prop & ~2)
        struct.pack_into('<I', r, 46, prop)
        rep[f'{key[0]} {size/100:g}{"B" if key[2] else ""} {col} -> {face}{" +굵게" if bold else ""}'] += 1
    out = pack(rs)
    if compressed:
        c = zlib.compressobj(9, zlib.DEFLATED, -15); out = c.compress(out) + c.flush()
    streams[('DocInfo',)] = out
    write(dst, streams, clsids)
    for k, v in rep.items(): print('  changed', v, k)
    for k, v in untouched.items(): print('  kept   ', v, k)
if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
