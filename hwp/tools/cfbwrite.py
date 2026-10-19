"""Write a Compound File Binary (v3, 512-byte sectors) from {path_tuple: bytes} streams.
Storages are implied by paths; CLSIDs/state can be passed per path (root = ())."""
import struct, math
FREE, END, FATS, DIFS = 0xFFFFFFFF, 0xFFFFFFFE, 0xFFFFFFFD, 0xFFFFFFFC
NOSTREAM = 0xFFFFFFFF
def _key(name): return (len(name), name.upper())
def write(path, streams, clsids=None):
    clsids = clsids or {}
    # ---- build entry list
    entries = [dict(name='Root Entry', type=5, path=(), children=[])]
    index = {(): 0}
    def ensure(p):
        if p in index: return index[p]
        par = ensure(p[:-1]); e = dict(name=p[-1], type=1, path=p, children=[])
        index[p] = len(entries); entries.append(e); entries[par]['children'].append(index[p]); return index[p]
    for p, data in streams.items():
        par = ensure(tuple(p[:-1])); e = dict(name=p[-1], type=2, path=tuple(p), data=data, children=[])
        index[tuple(p)] = len(entries); entries.append(e); entries[par]['children'].append(index[tuple(p)])
    # ---- red-black-valid balanced sibling trees
    for e in entries:
        e.update(left=NOSTREAM, right=NOSTREAM, child=NOSTREAM, color=1)
    for e in entries:
        kids = sorted(e['children'], key=lambda i: _key(entries[i]['name']))
        if not kids: continue
        k = int(math.floor(math.log2(len(kids) + 1)))
        def build(lo, hi, depth):
            if lo > hi: return NOSTREAM
            mid = (lo + hi) // 2; node = kids[mid]
            entries[node]['color'] = 0 if depth >= k else 1      # bottom partial level red
            entries[node]['left'] = build(lo, mid - 1, depth + 1); entries[node]['right'] = build(mid + 1, hi, depth + 1)
            return node
        e['child'] = build(0, len(kids) - 1, 0)
    # ---- data placement
    sectors = []          # list of 512-byte chunks
    fat = []
    def alloc(data, mark=None):
        n = (len(data) + 511) // 512
        start = len(sectors)
        for i in range(n):
            sectors.append(data[i * 512:(i + 1) * 512].ljust(512, b'\0'))
            fat.append(start + i + 1 if i < n - 1 else END)
        return start if n else END
    mini = bytearray(); minifat = []
    for e in entries:
        if e['type'] != 2: continue
        d = e['data']
        if len(d) < 4096:
            if not d: e['start'] = END; continue
            n = (len(d) + 63) // 64; start = len(mini) // 64
            mini += d.ljust(n * 64, b'\0')
            minifat += [start + i + 1 if i < n - 1 else END for i in range(n)]
            e['start'] = start
        else:
            e['start'] = alloc(d)
    root = entries[0]
    root['start'] = alloc(bytes(mini)) if mini else END; root['size'] = len(mini)
    mf = b''.join(struct.pack('<I', x) for x in minifat)
    mf_start = alloc(mf) if mf else END; mf_count = (len(mf) + 511) // 512
    # directory
    def dirent(e):
        name = e['name'].encode('utf-16le') + b'\0\0'
        size = len(e['data']) if e['type'] == 2 else e.get('size', 0)
        start = e.get('start', 0) if e['type'] != 1 else 0
        return (name.ljust(64, b'\0') + struct.pack('<HBB3I', len(name), e['type'], e['color'], e['left'], e['right'], e['child'])
                + clsids.get(e['path'], b'\0' * 16) + struct.pack('<I', 0) + b'\0' * 16 + struct.pack('<IQ', start, size))
    dd = b''.join(dirent(e) for e in entries)
    dd = dd.ljust(((len(dd) + 511) // 512) * 512, b'\0')
    dir_start = alloc(dd)
    # FAT + DIFAT sizing
    nfat = ndif = 0
    while True:
        total = len(sectors) + nfat + ndif
        need_fat = (total + 127) // 128
        need_dif = max(0, (need_fat - 109 + 126) // 127)
        if need_fat == nfat and need_dif == ndif: break
        nfat, ndif = need_fat, need_dif
    fat_start = len(sectors)
    fat_secs = list(range(fat_start, fat_start + nfat)); dif_secs = list(range(fat_start + nfat, fat_start + nfat + ndif))
    fat += [FATS] * nfat + [DIFS] * ndif
    fat += [FREE] * (nfat * 128 - len(fat))
    fatb = b''.join(struct.pack('<I', x) for x in fat)
    for i in range(nfat): sectors.append(fatb[i * 512:(i + 1) * 512])
    rest = fat_secs[109:]
    for j in range(ndif):
        chunk = rest[j * 127:(j + 1) * 127]; chunk += [FREE] * (127 - len(chunk))
        nxt = dif_secs[j + 1] if j + 1 < ndif else END
        sectors.append(b''.join(struct.pack('<I', x) for x in chunk + [nxt]))
    head_difat = (fat_secs[:109] + [FREE] * 109)[:109]
    hdr = (bytes.fromhex('D0CF11E0A1B11AE1') + b'\0' * 16 + struct.pack('<HHHHH', 0x3E, 3, 0xFFFE, 9, 6) + b'\0' * 6
           + struct.pack('<IIIIIIIII', 0, nfat, dir_start, 0, 4096, mf_start, mf_count, dif_secs[0] if ndif else END, ndif)
           + b''.join(struct.pack('<I', x) for x in head_difat))
    assert len(hdr) == 512
    with open(path, 'wb') as f:
        f.write(hdr); f.write(b''.join(sectors))

def read_all(path):
    import olefile
    ole = olefile.OleFileIO(path)
    streams = {tuple(p): ole.openstream(p).read() for p in ole.listdir(streams=True, storages=False)}
    clsids = {}
    for p in ole.listdir(streams=True, storages=True):
        e = ole.direntries[ole._find(p)]
        if e.clsid and e.clsid != '00000000-0000-0000-0000-000000000000':
            import uuid; clsids[tuple(p)] = uuid.UUID(e.clsid).bytes_le
    if ole.root.clsid and ole.root.clsid != '00000000-0000-0000-0000-000000000000':
        import uuid; clsids[()] = uuid.UUID(ole.root.clsid).bytes_le
    return streams, clsids
