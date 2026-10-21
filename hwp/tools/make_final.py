"""17-27안 hwpx → 최종안: TAG C(좌우 대칭) + 중단원 띠 B-4 + 바탕색 옅게.
Usage: python3 make_final.py <17-27.hwpx> <art_dir(tag_L/tag_R/bar_B4.emf)> <out.hwpx>"""
import io, re, sys, zipfile
import numpy as np
from PIL import Image

SRC, ART, OUT = sys.argv[1:4]
OLD, NEW = 'F8F1E7', 'FAF5EE'
ODD_SHIFT = -10330           # 우수 TAG: 바깥 단 → 세로선 바로 오른쪽 (HWPUNIT)
z = zipfile.ZipFile(SRC)
files = {i.filename: z.read(i) for i in z.infolist()}
infos = {i.filename: i for i in z.infolist()}

def rgb(h): return np.array([int(h[i:i+2], 16) for i in (0, 2, 4)], float)

# ---------- 1. 바탕색 ----------
def shift(a, thr):
    d = np.sqrt(((a - rgb(OLD))**2).sum(-1)); w = np.clip(1 - d/thr, 0, 1)[..., None]
    return np.clip(a + w*(rgb(NEW) - rgb(OLD)), 0, 255)

def recolor_emf(b):
    import struct
    d = bytearray(b); off = 0; old = bytes(rgb(OLD).astype(int).tolist()); new = bytes(rgb(NEW).astype(int).tolist())
    while off < len(d):
        t, sz = struct.unpack_from('<II', d, off)
        pos = {39: off+16, 95: off+40, 24: off+8, 38: off+24}.get(t)
        if pos is not None and bytes(d[pos:pos+3]) == old: d[pos:pos+3] = new
        if t == 81:   # STRETCHDIBITS
            offBmi, cbBmi, offBits, cbBits = struct.unpack_from('<4I', d, off+48)
            w, h, _, bpp = struct.unpack_from('<iiHH', d, off+offBmi+4)
            if bpp in (24, 32) and cbBits:
                n = bpp // 8
                raw = np.frombuffer(bytes(d[off+offBits:off+offBits+cbBits]), np.uint8)
                stride = ((w*n + 3)//4)*4
                if len(raw) >= stride*abs(h):
                    px = raw[:stride*abs(h)].reshape(abs(h), stride)[:, :w*n].reshape(abs(h), w, n).astype(float)
                    rgbp = px[..., [2, 1, 0]]; rgbp = shift(rgbp, 70)
                    px[..., 0], px[..., 1], px[..., 2] = rgbp[..., 2], rgbp[..., 1], rgbp[..., 0]
                    full = raw[:stride*abs(h)].reshape(abs(h), stride).copy()
                    full[:, :w*n] = px.reshape(abs(h), w*n).astype(np.uint8)
                    d[off+offBits:off+offBits+stride*abs(h)] = full.tobytes()
        off += sz
    return bytes(d)

changed = []
for name in list(files):
    if not name.startswith('BinData/'): continue
    ext = name.rsplit('.', 1)[-1].lower()
    if ext == 'emf':
        nb = recolor_emf(files[name])
    elif ext in ('png', 'jpg', 'bmp'):
        im = Image.open(io.BytesIO(files[name])); mode = im.mode
        im = im.convert('RGBA'); a = np.asarray(im).astype(float)
        before = a[..., :3].astype(np.uint8).copy()
        a[..., :3] = shift(a[..., :3], 40)
        if (a[..., :3].astype(np.uint8) == before).all(): continue   # 바탕색이 없는 그림은 그대로
        out = Image.fromarray(a.astype(np.uint8), 'RGBA')
        if mode != 'RGBA' and 'A' not in mode: out = out.convert('RGB')
        b = io.BytesIO(); out.save(b, {'png': 'PNG', 'jpg': 'JPEG', 'bmp': 'BMP'}[ext], **({'quality': 95} if ext == 'jpg' else {}))
        nb = b.getvalue()
    else:
        continue
    if nb != files[name]: changed.append(name)
    files[name] = nb

h = files['Contents/header.xml'].decode('utf-8')
h = h.replace('#' + OLD, '#' + NEW)
HL_OLD, HL_NEW = 'F2D3B3', 'DDD1E8'   # 형광펜: 피치 → 스모키 라일락(단색)
h = h.replace('shadeColor="#%s"' % HL_OLD, 'shadeColor="#%s"' % HL_NEW)

# ---------- 2. 새 그림 (TAG 오른쪽 리본, 띠) ----------
files['BinData/image9.emf'] = open(ART + '/tag_L.emf', 'rb').read()
files['BinData/image43.emf'] = open(ART + '/tag_R.emf', 'rb').read()
files['BinData/image44.emf'] = open(ART + '/bar_B4.emf', 'rb').read()
hpf = files['Contents/content.hpf'].decode('utf-8')
item = re.search(r'<opf:item id="image9"[^>]*/>', hpf).group(0)
hpf = hpf.replace(item, item + item.replace('image9', 'image43') + item.replace('image9', 'image44'), 1)
files['Contents/content.hpf'] = hpf.encode('utf-8')

def add_item(h, tag, block_tag, xml):
    m = re.search(r'<hh:%s itemCnt="(\d+)">' % block_tag, h)
    n = int(m.group(1))
    h = h.replace(m.group(0), '<hh:%s itemCnt="%d">' % (block_tag, n+1), 1)
    return h.replace('</hh:%s>' % block_tag, xml + '</hh:%s>' % block_tag, 1)

def max_id(h, tag): return max(int(x) for x in re.findall(r'<hh:%s id="(\d+)"' % tag, h))

# 띠 바탕: 그림 채우기 테두리/배경
bf55 = re.search(r'<hh:borderFill id="55".*?</hh:borderFill>', h, re.S).group(0)
BF = max_id(h, 'borderFill') + 1
bf = re.sub(r'id="55"', 'id="%d"' % BF, bf55, count=1).replace('binaryItemIDRef="image40"', 'binaryItemIDRef="image44"')
bf = re.sub(r'<hh:bottomBorder [^>]*/>', '<hh:bottomBorder type="NONE" width="0.12 mm" color="#000000"/>', bf)
h = add_item(h, 'borderFill', 'borderFills', bf)

# 글자 모양: 번호 흰색, 제목 진갈색
def copy_charpr(h, src, color):
    cp = re.search(r'<hh:charPr id="%s".*?</hh:charPr>' % src, h, re.S).group(0)
    nid = max_id(h, 'charPr') + 1
    cp = re.sub(r'id="%s"' % src, 'id="%d"' % nid, cp, 1)
    cp = re.sub(r'textColor="#[0-9A-Fa-f]{6}"', 'textColor="%s"' % color, cp, 1)
    return add_item(h, 'charPr', 'charProperties', cp), nid
h, CP_NUM = copy_charpr(h, '13', '#FFFFFF')
h, CP_TITLE = copy_charpr(h, '11', '#3A241D')

# TAG 문단: 가운데 정렬, 오른쪽 여백 0
pp = re.search(r'<hh:paraPr id="17".*?</hh:paraPr>', h, re.S).group(0)
PP = max_id(h, 'paraPr') + 1
pp = re.sub(r'id="17"', 'id="%d"' % PP, pp, 1).replace('horizontal="RIGHT"', 'horizontal="CENTER"')
pp = re.sub(r'(<hc:right value=")\d+', r'\g<1>0', pp)
files['Contents/header.xml'] = h.encode('utf-8')

# ---------- 3. 본문 ----------
s = files['Contents/section0.xml'].decode('utf-8')
# 3-1 중단원 띠
i = s.find('   SI 단위계의 해석')
t0 = s.rfind('<hp:tbl ', 0, i); t1 = s.find('</hp:tbl>', i) + 9
tb = s[t0:t1]
tb = re.sub(r'(<hp:tc [^>]*borderFillIDRef=")9"', r'\g<1>%d"' % BF, tb, 1)
tb = tb.replace('<hp:run charPrIDRef="13">', '<hp:run charPrIDRef="%d">' % CP_NUM)
tb = tb.replace('<hp:run charPrIDRef="12">', '<hp:run charPrIDRef="%d">' % CP_NUM)
tb = tb.replace('<hp:run charPrIDRef="11">', '<hp:run charPrIDRef="%d">' % CP_TITLE)
tb = tb.replace('<hp:t>   SI 단위계의 해석</hp:t>', '<hp:t>      SI 단위계의 해석</hp:t>')
tb = re.sub(r'<hp:linesegarray>.*?</hp:linesegarray>', '', tb, flags=re.S)
s = s[:t0] + tb + s[t1:]

# 3-2 TAG: 글자까지 그림(EMF)에 넣고, 칸을 왼쪽으로 늘린다 (오른쪽 끝 고정 → 좌수 세로선과 일치)
#      짝수 번째(0부터) = 좌수, 홀수 번째 = 우수(좌우 대칭, 왼쪽 끝 = 세로선)
TAG_W = 4200                     # 42pt
EMF_W, EMF_H = 700, 190          # tag_L/R.emf 의 픽셀 크기 (emf_poly 해상도)
ODD_OFFSET = 12466 - TAG_W       # 우수: (문단 오른쪽 541.14pt − 세로선 416.48pt)×100 − 칸 폭
out, pos, k = [], 0, 0
for m in re.finditer(r'<hp:tbl [^>]*>\s*<hp:sz width="3418"', s):
    st = m.start(); en = s.find('</hp:tbl>', st) + 9
    if '<hp:t>TAG</hp:t>' not in s[st:en]: continue
    seg = s[st:en]
    seg = seg.replace('<hp:sz width="3418"', '<hp:sz width="%d"' % TAG_W, 1)
    seg = seg.replace('<hp:cellSz width="3418"', '<hp:cellSz width="%d"' % TAG_W)
    seg = seg.replace('<hp:orgSz width="3420"', '<hp:orgSz width="%d"' % TAG_W)
    seg = seg.replace('<hp:sz width="3420"', '<hp:sz width="%d"' % TAG_W)
    seg = seg.replace('centerX="1710"', 'centerX="%d"' % (TAG_W // 2))
    seg = seg.replace('<hc:pt1 x="3420"', '<hc:pt1 x="%d"' % TAG_W).replace('<hc:pt2 x="3420"', '<hc:pt2 x="%d"' % TAG_W)
    seg = re.sub(r'<hp:imgClip [^>]*/>', '<hp:imgClip left="0" right="%d" top="0" bottom="%d"/>' % ((EMF_W-1)*600, (EMF_H-1)*600), seg)
    seg = seg.replace('<hp:t>TAG</hp:t>', '')
    seg = re.sub(r'<hp:linesegarray>.*?</hp:linesegarray>', '', seg, flags=re.S)
    if k % 2 == 1:
        seg = seg.replace('binaryItemIDRef="image9"', 'binaryItemIDRef="image43"')
        seg = re.sub(r'horzOffset="\d+"', 'horzOffset="%d"' % ODD_OFFSET, seg, count=1)
    out.append(s[pos:st]); out.append(seg); pos = en; k += 1
out.append(s[pos:]); s = ''.join(out)
files['Contents/section0.xml'] = s.encode('utf-8')

# ---------- 4. 저장 ----------
zo = zipfile.ZipFile(OUT, 'w')
order = [n for n in files if n == 'mimetype'] + [n for n in files if n != 'mimetype']
for n in order:
    ct = zipfile.ZIP_STORED if n == 'mimetype' else zipfile.ZIP_DEFLATED
    zo.writestr(zipfile.ZipInfo(n, date_time=(2026, 10, 21, 12, 0, 0)) if n not in infos else infos[n], files[n], compress_type=ct)
zo.close()
print('TAG', k, 'BF', BF, 'CP', CP_NUM, CP_TITLE, 'PP', PP, 'recolored', len(changed), changed)
