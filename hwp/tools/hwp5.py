"""Minimal HWP 5.0 reader: fonts, char shapes, para shapes, styles and paragraphs (with nesting level)."""
import olefile, zlib, struct, sys, collections
LANGS = ['hangul', 'latin', 'hanja', 'japanese', 'other', 'symbol', 'user']
def records(data):
    i = 0
    while i < len(data):
        h, = struct.unpack_from('<I', data, i); i += 4
        tag, lvl, size = h & 0x3FF, (h >> 10) & 0x3FF, (h >> 20) & 0xFFF
        if size == 0xFFF: size, = struct.unpack_from('<I', data, i); i += 4
        yield tag, lvl, data[i:i + size]; i += size
class Hwp:
    def __init__(self, path):
        ole = olefile.OleFileIO(path)
        hdr = ole.openstream('FileHeader').read(); self.compressed = bool(struct.unpack_from('<I', hdr, 36)[0] & 1)
        rd = lambda n: (zlib.decompress(ole.openstream(n).read(), -15) if self.compressed else ole.openstream(n).read())
        self.faces = {l: [] for l in LANGS}; self.cs = []; self.ps = []; self.styles = []
        di = list(records(rd('DocInfo')))
        idm = next(r for t, _, r in di if t == 17); counts = struct.unpack_from('<18I', idm + b'\0' * 72, 0)
        face_counts = counts[1:8]; fi = 0; order = [l for l, c in zip(LANGS, face_counts) for _ in range(c)]
        for t, _, r in di:
            if t == 19:
                n, = struct.unpack_from('<H', r, 1); self.faces[order[fi]].append(r[3:3 + 2 * n].decode('utf-16le')); fi += 1
            elif t == 21:
                f = struct.unpack_from('<7H', r, 0); rel = struct.unpack_from('<7B', r, 14 + 7 + 7)
                off = struct.unpack_from('<7b', r, 14 + 21); size, prop = struct.unpack_from('<iI', r, 42)
                color, = struct.unpack_from('<I', r, 52)
                self.cs.append(dict(face={l: self.faces[l][f[k]] if f[k] < len(self.faces[l]) else '?' for k, l in enumerate(LANGS)},
                                    size=size, bold=bool(prop & 2), italic=bool(prop & 1), relsz=rel[0], offset=off[0],
                                    color='#%02X%02X%02X' % (color & 255, (color >> 8) & 255, (color >> 16) & 255)))
            elif t == 25:
                p, = struct.unpack_from('<I', r, 0); left, right, indent, prev, nxt, ls = struct.unpack_from('<6i', r, 4)
                self.ps.append(dict(left=left, indent=indent, prev=prev, next=nxt, ls=ls, align=(p >> 2) & 7))
            elif t == 26:
                n, = struct.unpack_from('<H', r, 0); self.styles.append(r[2:2 + 2 * n].decode('utf-16le'))
        self.paras = []
        k = 0
        while ole.exists('BodyText/Section%d' % k):
            cur = None
            for t, lvl, r in records(rd('BodyText/Section%d' % k)):
                if t == 66:
                    ps_id, = struct.unpack_from('<H', r, 8); st = r[10]
                    cur = dict(sec=k, level=lvl, ps=ps_id, style=st, text='', runs=[]); self.paras.append(cur)
                elif t == 67 and cur is not None:
                    w = struct.unpack_from('<%dH' % (len(r) // 2), r); out = []; j = 0; pos = []
                    while j < len(w):
                        c = w[j]
                        if c < 32:
                            if c in (0, 10, 13) or 24 <= c <= 31: out.append('\n' if c in (10, 13) else ''); pos.append(j); j += 1
                            else: out.append('\x00'); pos.append(j); j += 8
                        else: out.append(chr(c)); pos.append(j); j += 1
                    cur['raw'] = (out, pos)
                elif t == 68 and cur is not None:
                    pairs = struct.unpack_from('<%dI' % (len(r) // 4), r); cur['cs_pairs'] = list(zip(pairs[0::2], pairs[1::2]))
            k += 1
        for p in self.paras:          # split text into runs by char shape
            out, pos = p.pop('raw', ([], []))
            pairs = p.pop('cs_pairs', [(0, 0)])
            for a, (start, cid) in enumerate(pairs):
                end = pairs[a + 1][0] if a + 1 < len(pairs) else 1 << 30
                txt = ''.join(ch for ch, q in zip(out, pos) if start <= q < end)
                p['runs'].append((cid, txt)); p['text'] += txt
