"""생성기 hwpx(2단: 본문 단 + 날개 단) → 1단 전체 폭 LOGIC BUILD.
TAG·날개 주석·세로선 없이 본문 상자를 좌우로 넓히고, 바탕은 흰색, 중단원 띠는 B-4(전체 폭).
Usage: python3 make_wide.py <in.hwpx> <art_dir(bar_B4_wide.emf)> <out.hwpx>"""
import io, re, sys, zipfile
import numpy as np
from PIL import Image
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from make_final_lib import recolor_emf, shift_img, add_item, max_id, copy_charpr

SRC, ART, OUT = sys.argv[1:4]
OLD, NEW = 'F8F1E7', 'FFFFFF'
FULL_W, COL_W = 46205, 32570          # 1단 전체 폭 / 예전 본문 단 폭 (HWPUNIT)
DELTA = FULL_W - COL_W
z = zipfile.ZipFile(SRC)
files = {i.filename: z.read(i) for i in z.infolist()}
infos = {i.filename: i for i in z.infolist()}

# ---------- 1. 바탕색: 흰색 ----------
changed = []
for name in list(files):
    if not name.startswith('BinData/'): continue
    ext = name.rsplit('.', 1)[-1].lower()
    if ext == 'emf':
        nb = recolor_emf(files[name], OLD, NEW)
    elif ext in ('png', 'jpg', 'bmp') and int(re.sub(r'\D', '', name) or 0) < 40:   # 틀 그림만
        nb = shift_img(files[name], ext, OLD, NEW)
    else:
        continue
    if nb != files[name]: changed.append(name)
    files[name] = nb

h = files['Contents/header.xml'].decode('utf-8')
h = h.replace('#' + OLD, '#' + NEW).replace('#FAF5EE', '#' + NEW)
h = h.replace('shadeColor="#F2D3B3"', 'shadeColor="#DDD1E8"')      # 형광펜: 스모키 라일락

# ---------- 2. 띠 그림 ----------
hpf = files['Contents/content.hpf'].decode('utf-8')
IMG_BAR = 'image%d' % (max(int(x) for x in re.findall(r'id="image(\d+)"', hpf)) + 1)
files['BinData/%s.emf' % IMG_BAR] = open(ART + '/bar_B4_wide.emf', 'rb').read()
item = re.search(r'<opf:item id="image9"[^>]*/>', hpf).group(0)
hpf = hpf.replace(item, item + item.replace('image9', IMG_BAR), 1)
files['Contents/content.hpf'] = hpf.encode('utf-8')

BF = max_id(h, 'borderFill') + 1
_side = lambda t: '<hh:%s type="NONE" width="0.12 mm" color="#000000"/>' % t
h = add_item(h, 'borderFill', 'borderFills',
             '<hh:borderFill id="%d" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0">'
             '<hh:slash type="NONE" Crooked="0" isCounter="0"/><hh:backSlash type="NONE" Crooked="0" isCounter="0"/>' % BF
             + _side('leftBorder') + _side('rightBorder') + _side('topBorder') + _side('bottomBorder')
             + '<hh:diagonal type="SOLID" width="0.1 mm" color="#000000"/>'
             '<hc:fillBrush><hc:imgBrush mode="TOTAL"><hc:img binaryItemIDRef="%s" bright="0" contrast="0" effect="REAL_PIC" alpha="0"/></hc:imgBrush></hc:fillBrush>'
             '</hh:borderFill>' % IMG_BAR)
h, CP_NUM = copy_charpr(h, '13', '#FFFFFF')
h, CP_TITLE = copy_charpr(h, '11', '#3A241D')
files['Contents/header.xml'] = h.encode('utf-8')

s = files['Contents/section0.xml'].decode('utf-8')

# ---------- 3. 2단 → 1단, 세로선·TAG 삭제 ----------
n_col = len(re.findall(r'<hp:colPr [^>]*colCount="2"', s))
s = re.sub(r'<hp:colPr ([^>]*?)layout="MIRROR" colCount="2" sameSz="0"([^>]*?)(/?)>',
           r'<hp:colPr \1layout="LEFT" colCount="1" sameSz="1"\2\3>', s)
s = re.sub(r'(<hp:colPr [^>]*colCount="1"[^>/]*>)(?:<hp:colSz [^>]*/>)+</hp:colPr>', r'\1</hp:colPr>', s)

def drop_objs(s, open_tag, close_tag, pred):
    out, pos, n = [], 0, 0
    for m in re.finditer(r'<hp:%s ' % open_tag, s):
        st = m.start()
        if st < pos: continue
        en = s.find('</hp:%s>' % close_tag, st) + len('</hp:%s>' % close_tag)
        if pred(s[st:en]):
            out.append(s[pos:st]); pos = en; n += 1
    out.append(s[pos:])
    return ''.join(out), n

s, n_line = drop_objs(s, 'line', 'line', lambda seg: max(int(x) for x in re.findall(r'height="(\d+)"', seg)) > 40000)
s, n_tag = drop_objs(s, 'tbl', 'tbl', lambda seg: re.search(r'<hp:sz width="3418"', seg[:400]) is not None)
s = s.replace('<hp:ctrl><hp:colBreak/></hp:ctrl>', '')
n_cb = s.count('columnBreak="1"')
s = s.replace('columnBreak="1"', 'columnBreak="0"')

# ---------- 4. 본문 단 폭 상자 → 전체 폭 ----------
def widen(tbl):
    """tbl 문자열 하나(맨 바깥 표)의 폭을 DELTA만큼 늘리고, 각 행의 칸을 원래 비율로 다시 나눈다."""
    w0 = int(re.search(r'<hp:sz width="(\d+)"', tbl).group(1))
    w1 = w0 + DELTA
    tbl = tbl.replace('<hp:sz width="%d"' % w0, '<hp:sz width="%d"' % w1, 1)
    # 맨 바깥 표의 행만 다룬다: 안쪽 표는 잘라 두었다가 다시 넣는다
    inner = []
    def stash(m):
        inner.append(m.group(0)); return '\x00%d\x00' % (len(inner) - 1)
    body_start = tbl.find('>', 1) + 1
    head, body = tbl[:body_start], tbl[body_start:]
    body = re.sub(r'<hp:tbl .*?</hp:tbl>', stash, body, flags=re.S) if '<hp:tbl ' in body else body
    def fix_row(m):
        row = m.group(0)
        ws = [int(x) for x in re.findall(r'<hp:cellSz width="(\d+)"', row)]
        if not ws: return row
        tot = sum(ws); new = [round(x * w1 / tot) for x in ws]; new[-1] += w1 - sum(new)
        it = iter(new)
        return re.sub(r'<hp:cellSz width="\d+"', lambda _: '<hp:cellSz width="%d"' % next(it), row)
    body = re.sub(r'<hp:tr>.*?</hp:tr>', fix_row, body, flags=re.S)
    body = re.sub('\x00(\\d+)\x00', lambda m: widen_inner(inner[int(m.group(1))], w1 / w0), body)
    return head + body

def widen_inner(tbl, ratio):
    """안쪽 표: 바깥 칸이 넓어진 비율만큼 (본문 단 폭에 가까운 표만)"""
    w0 = int(re.search(r'<hp:sz width="(\d+)"', tbl).group(1))
    if w0 < 20000: return tbl
    global DELTA
    d0 = DELTA; DELTA = int(w0 * ratio) - w0
    try: return widen(tbl)
    finally: DELTA = d0

out, pos, n_wide = [], 0, 0
depth_re = re.compile(r'<hp:tbl |</hp:tbl>')
i = 0
while True:
    m = re.compile(r'<hp:tbl ').search(s, pos)
    if not m: break
    st = m.start(); d = 0
    for t in depth_re.finditer(s, st):
        d += 1 if t.group(0) == '<hp:tbl ' else -1
        if d == 0: en = t.end(); break
    seg = s[st:en]
    w = int(re.search(r'<hp:sz width="(\d+)"', seg).group(1))
    if 25000 <= w <= 33500:
        seg = widen(seg); n_wide += 1
    out.append(s[pos:st]); out.append(seg); pos = en
out.append(s[pos:]); s = ''.join(out)

# ---------- 5. 중단원 띠 B-4 ----------
nbar, pos, out = 0, 0, []
for m in re.finditer(r'<hp:tc [^>]*borderFillIDRef="9"', s):
    t0 = s.rfind('<hp:tbl ', 0, m.start()); t1 = s.find('</hp:tbl>', m.start()) + 9
    if t0 < pos: continue
    tb = s[t0:t1]
    tb = re.sub(r'(<hp:tc [^>]*borderFillIDRef=")9"', r'\g<1>%d"' % BF, tb, count=1)
    for c in ('13', '12'):
        tb = tb.replace('<hp:run charPrIDRef="%s">' % c, '<hp:run charPrIDRef="%d">' % CP_NUM)
    tb = tb.replace('<hp:run charPrIDRef="11">', '<hp:run charPrIDRef="%d">' % CP_TITLE)
    tb = re.sub(r'(<hp:run charPrIDRef="%d"><hp:t>)   (?! )' % CP_TITLE, r'\g<1>      ', tb)
    out.append(s[pos:t0]); out.append(tb); pos = t1; nbar += 1
out.append(s[pos:]); s = ''.join(out)
assert 'borderFillIDRef="9"' not in s

s = re.sub(r'<hp:linesegarray>.*?</hp:linesegarray>', '', s, flags=re.S)
files['Contents/section0.xml'] = s.encode('utf-8')

# ---------- 6. 저장 ----------
zo = zipfile.ZipFile(OUT, 'w')
for n in [n for n in files if n == 'mimetype'] + [n for n in files if n != 'mimetype']:
    ct = zipfile.ZIP_STORED if n == 'mimetype' else zipfile.ZIP_DEFLATED
    zo.writestr(infos[n] if n in infos else zipfile.ZipInfo(n, date_time=(2026, 10, 23, 12, 0, 0)), files[n], compress_type=ct)
zo.close()
print('cols', n_col, 'lines', n_line, 'TAG', n_tag, 'colBreak', n_cb, 'widened', n_wide, 'BAR', nbar, 'recolored', len(changed))
