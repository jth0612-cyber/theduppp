# fontsource의 조각 woff들을 하나의 TTF로 합침 (같은 글꼴의 서로 다른 글자 범위 조각)
import sys, glob, re
from fontTools.ttLib import TTFont
from fontTools.merge import Merger, Options
name, w, out = sys.argv[1], sys.argv[2], sys.argv[3]
files = sorted(glob.glob(f'x/fontsource-{name}/package/files/{name}-*-{w}-normal.woff'))
files = [p for p in files if not re.search(r'-(cyrillic|greek|vietnamese|latin-ext)-', p)]
tmp = []
for i, p in enumerate(files):
    t = TTFont(p); t.flavor = None
    q = f'/tmp/claude-0/-home-user-theduppp/3cb8851e-dc2c-53a1-978b-98ab2edd3e98/scratchpad/fs/tmpc_{i}.ttf'; t.save(q); tmp.append(q)
opts = Options(drop_tables=['vhea', 'vmtx', 'GSUB', 'GPOS', 'GDEF', 'BASE', 'JSTF', 'MATH', 'STAT', 'meta'])
m = Merger(options=opts).merge(tmp)
m.save(out)
cm = m.getBestCmap()
print(out, len(files), 'hangul', sum(0xAC00 <= c <= 0xD7A3 for c in cm), 'latin', all(ord(c) in cm for c in 'Aa09-.'))
