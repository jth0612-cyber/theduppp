"""Round-2 fonts for INNING / BULLPEN (HWP 5.0). Like hwp_fonts.py, plus a split rule: text in the
BULLPEN 지시문 style shares its char shape with the table body, so it gets its own cloned shape.
usage: hwp_fonts2.py in.hwp out.hwp"""
import sys, zlib, struct, collections
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from cfbwrite import write, read_all
from hwp_fonts import recs, pack, face_name, make_face, LANGS
RULES = {   # (hangul face, size, bold, color) -> (new face, bold, template for face-type info)
 # INNING 라벨 Pretendard 24pt + 굵게: unchanged (original)
 ('Pretendard', 1400, True, '#E78246'): ('SUIT', True, 'Pretendard'),                  # INNING 주제 제목: SUIT Bold = family SUIT + bold style
 ('Pretendard', 1050, True, '#E78246'): ('나눔바른고딕', True, 'Pretendard'),             # INNING 소제목
 # INNING 본문 KoPubWorld바탕체 Light 10.5: unchanged
 ('Pretendard ExtraBold', 1100, False, '#C24D97'): ('Pretendard Black', False, 'Pretendard'),   # BULLPEN 라벨
 ('Pretendard SemiBold', 1000, False, '#000000'): ('SUIT', True, 'Pretendard'),   # BULLPEN 제목: SUIT Bold = family SUIT + bold style
 ('Pretendard', 800, False, '#000000'): ('SUIT', False, 'Pretendard'),                  # BULLPEN 표 본문
 ('Pretendard', 900, True, '#C24D97'): ('Hahmlet SemiBold', False, 'KoPubWorld바탕체 Light'),  # BULLPEN 소제목
 ('Pretendard SemiBold', 800, False, '#000000'): ('SUIT SemiBold', False, 'Pretendard'),  # BULLPEN 표 머리글
 # table / side-note family, other variants met in the batch: keep it SUIT
 ('Pretendard SemiBold', 800, False, '#FFFFFF'): ('SUIT SemiBold', False, 'Pretendard'),  # 흰 표 머리글
 ('Pretendard', 800, True, '#000000'): ('SUIT', True, 'Pretendard'),                    # 8pt 굵게 → SUIT Bold
 ('Pretendard', 800, True, '#009FBB'): ('SUIT', True, 'Pretendard'),                    # 8pt 청록 굵게(측주 번호 등)
}
# a 9pt magenta bold run inside a sentence that is otherwise 9pt magenta regular is emphasis, not a 소제목:
# keep it in the original font there (cloned shape), so the line does not mix two families
KEEP_IF_PARA_HAS = {('Pretendard', 900, True, '#C24D97'): ('Pretendard', 900, False, '#C24D97')}
SPLIT = {('제목3(회색박스)', ('Pretendard', 800, False, '#000000')): ('SUIT Medium', False, 'Pretendard')}   # BULLPEN 지시문
def main(src, dst):
    streams, clsids = read_all(src)
    comp = bool(struct.unpack_from('<I', streams[('FileHeader',)], 36)[0] & 1)
    unz = lambda b: zlib.decompress(b, -15) if comp else b
    rs = recs(unz(streams[('DocInfo',)])); body = recs(unz(streams[('BodyText', 'Section0')]))
    idm = next(r for r in rs if r[0] == 17)[2]; counts = list(struct.unpack_from('<%dI' % (len(idm) // 4), idm))
    face_idx = [k for k, r in enumerate(rs) if r[0] == 19]; groups = {}; pos = 0
    for li, l in enumerate(LANGS): groups[l] = face_idx[pos:pos + counts[1 + li]]; pos += counts[1 + li]
    names = {l: [face_name(rs[k][2]) for k in groups[l]] for l in LANGS}
    styles = [bytes(r[2:2 + 2 * struct.unpack_from('<H', r, 0)[0]]).decode('utf-16le') for t, _, r in rs if t == 26]
    wanted = sorted({(v[0], v[2]) for v in list(RULES.values()) + list(SPLIT.values())})
    new_id = {l: {} for l in LANGS}; inserts = []
    for li, l in enumerate(LANGS):
        added = []
        for face, tplname in wanted:
            if face in names[l]: new_id[l][face] = names[l].index(face); continue
            tpl = next((rs[k][2] for k in groups[l] if face_name(rs[k][2]) == tplname), rs[groups[l][0]][2])
            new_id[l][face] = counts[1 + li] + len(added); added.append(make_face(tpl, face))
        inserts.append((groups[l][-1], added)); counts[1 + li] += len(added)
    for after, added in sorted(inserts, key=lambda x: -x[0]):
        for a in reversed(added): rs.insert(after + 1, [19, rs[after][1], a])
    cs_recs = [r for r in rs if r[0] == 21]
    def key(r):
        f = struct.unpack_from('<7H', r, 0); size, prop = struct.unpack_from('<iI', r, 42); color, = struct.unpack_from('<I', r, 52)
        return (names['hangul'][f[0]], size, bool(prop & 2), '#%02X%02X%02X' % (color & 255, (color >> 8) & 255, (color >> 16) & 255))
    keys = [key(r[2]) for r in cs_recs]
    def refont(r, face, bold):
        struct.pack_into('<7H', r, 0, *[new_id[l][face] for l in LANGS])
        prop, = struct.unpack_from('<I', r, 46); struct.pack_into('<I', r, 46, (prop | 2) if bold else (prop & ~2))
    # split: clone shapes used inside the SPLIT styles, repoint those paragraphs
    clone_of = {}; rep = collections.Counter()
    for i, (t, l, r) in enumerate(body):
        if t != 66: continue
        st = styles[r[10]]
        pcs = body[i + 1] if i + 1 < len(body) and body[i + 1][0] == 68 else None
        j = i + 1
        while j < len(body) and body[j][1] > l and body[j][0] != 68: j += 1
        if j >= len(body) or body[j][0] != 68: continue
        pr = body[j][2]; pairs = list(struct.unpack_from('<%dI' % (len(pr) // 4), pr))
        for n in range(1, len(pairs), 2):
            sk = (st, keys[pairs[n]])
            if sk not in SPLIT: continue
            if pairs[n] not in clone_of:
                c = [21, cs_recs[pairs[n]][1], bytearray(cs_recs[pairs[n]][2])]; refont(c[2], *SPLIT[sk][:2])
                last = max(k for k, x in enumerate(rs) if x[0] == 21); rs.insert(last + 1, c)
                clone_of[pairs[n]] = len(cs_recs); cs_recs.append(c); keys.append(('(split)',)); counts[9] += 1
            pairs[n] = clone_of[pairs[n]]; rep[f'split {sk[0]} {sk[1]} -> {SPLIT[sk][0]}'] += 1
        body[j][2] = bytearray(struct.pack('<%dI' % len(pairs), *pairs))
    keep_clone = {}
    for i, (t, l, r) in enumerate(body):
        if t != 66: continue
        j = i + 1
        while j < len(body) and body[j][1] > l and body[j][0] != 68: j += 1
        if j >= len(body) or body[j][0] != 68 or body[j][1] != l + 1: continue
        pr = body[j][2]; pairs = list(struct.unpack_from('<%dI' % (len(pr) // 4), pr))
        ks = [keys[pairs[n]] if pairs[n] < len(keys) else None for n in range(1, len(pairs), 2)]
        changed = False
        for n in range(1, len(pairs), 2):
            k = keys[pairs[n]] if pairs[n] < len(keys) else None
            if k in KEEP_IF_PARA_HAS and KEEP_IF_PARA_HAS[k] in ks:
                if pairs[n] not in keep_clone:
                    c = [21, cs_recs[pairs[n]][1], bytearray(cs_recs[pairs[n]][2])]
                    last = max(q for q, x in enumerate(rs) if x[0] == 21); rs.insert(last + 1, c)
                    keep_clone[pairs[n]] = len(cs_recs); cs_recs.append(c); keys.append(('(kept)',) + k[1:]); counts[9] += 1
                pairs[n] = keep_clone[pairs[n]]; changed = True; rep[f'kept emphasis {k}'] += 1
        if changed: body[j][2] = bytearray(struct.pack('<%dI' % len(pairs), *pairs))
    struct.pack_into('<%dI' % len(counts), idm, 0, *counts)
    for r, k in zip(cs_recs, keys):
        if k in RULES: refont(r[2], *RULES[k][:2]); rep[f'{k[0]} {k[1]/100:g}{"B" if k[2] else ""} {k[3]} -> {RULES[k][0]}{" +굵게" if RULES[k][1] else ""}'] += 1
    z = lambda b: (lambda c: c.compress(b) + c.flush())(zlib.compressobj(9, zlib.DEFLATED, -15)) if comp else b
    streams[('DocInfo',)] = z(pack(rs)); streams[('BodyText', 'Section0')] = z(pack(body))
    write(dst, streams, clsids)
    for k, v in sorted(rep.items()): print('  ', v, k)
if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
