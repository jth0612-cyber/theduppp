"""make_final.py / make_wide.py 공용: 바탕색 바꾸기, header.xml 항목 추가."""
import io, re, struct
import numpy as np
from PIL import Image


def rgb(h): return np.array([int(h[i:i+2], 16) for i in (0, 2, 4)], float)


def shift(a, thr, old, new):
    d = np.sqrt(((a - rgb(old))**2).sum(-1)); w = np.clip(1 - d/thr, 0, 1)[..., None]
    return np.clip(a + w*(rgb(new) - rgb(old)), 0, 255)


def recolor_emf(b, old, new):
    d = bytearray(b); off = 0
    ob = bytes(rgb(old).astype(int).tolist()); nb = bytes(rgb(new).astype(int).tolist())
    while off < len(d):
        t, sz = struct.unpack_from('<II', d, off)
        pos = {39: off+16, 95: off+40, 24: off+8, 38: off+24}.get(t)
        if pos is not None and bytes(d[pos:pos+3]) == ob: d[pos:pos+3] = nb
        if t == 81:   # STRETCHDIBITS
            offBmi, cbBmi, offBits, cbBits = struct.unpack_from('<4I', d, off+48)
            w, h, _, bpp = struct.unpack_from('<iiHH', d, off+offBmi+4)
            if bpp in (24, 32) and cbBits:
                n = bpp // 8
                raw = np.frombuffer(bytes(d[off+offBits:off+offBits+cbBits]), np.uint8)
                stride = ((w*n + 3)//4)*4
                if len(raw) >= stride*abs(h):
                    px = raw[:stride*abs(h)].reshape(abs(h), stride)[:, :w*n].reshape(abs(h), w, n).astype(float)
                    rgbp = shift(px[..., [2, 1, 0]], 70, old, new)
                    px[..., 0], px[..., 1], px[..., 2] = rgbp[..., 2], rgbp[..., 1], rgbp[..., 0]
                    full = raw[:stride*abs(h)].reshape(abs(h), stride).copy()
                    full[:, :w*n] = px.reshape(abs(h), w*n).astype(np.uint8)
                    d[off+offBits:off+offBits+stride*abs(h)] = full.tobytes()
        off += sz
    return bytes(d)


def shift_img(data, ext, old, new):
    im = Image.open(io.BytesIO(data)); mode = im.mode
    a = np.asarray(im.convert('RGBA')).astype(float)
    before = a[..., :3].astype(np.uint8).copy()
    a[..., :3] = shift(a[..., :3], 40, old, new)
    if (a[..., :3].astype(np.uint8) == before).all(): return data   # 바탕색이 없는 그림은 그대로
    out = Image.fromarray(a.astype(np.uint8), 'RGBA')
    if 'A' not in mode: out = out.convert('RGB')
    b = io.BytesIO(); out.save(b, {'png': 'PNG', 'jpg': 'JPEG', 'bmp': 'BMP'}[ext], **({'quality': 95} if ext == 'jpg' else {}))
    return b.getvalue()


def add_item(h, tag, block_tag, xml):
    m = re.search(r'<hh:%s itemCnt="(\d+)">' % block_tag, h)
    h = h.replace(m.group(0), '<hh:%s itemCnt="%d">' % (block_tag, int(m.group(1)) + 1), 1)
    return h.replace('</hh:%s>' % block_tag, xml + '</hh:%s>' % block_tag, 1)


def max_id(h, tag): return max(int(x) for x in re.findall(r'<hh:%s id="(\d+)"' % tag, h))


def copy_charpr(h, src, color):
    cp = re.search(r'<hh:charPr id="%s".*?</hh:charPr>' % src, h, re.S).group(0)
    nid = max_id(h, 'charPr') + 1
    cp = re.sub(r'id="%s"' % src, 'id="%d"' % nid, cp, 1)
    cp = re.sub(r'textColor="#[0-9A-Fa-f]{6}"', 'textColor="%s"' % color, cp, 1)
    return add_item(h, 'charPr', 'charProperties', cp), nid
