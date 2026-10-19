import sys, zlib, struct
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from cfbwrite import read_all
from hwp_fonts import recs
NAMES = {66:'PARA',67:'TEXT',68:'PCS',69:'LSEG',70:'RANGE',71:'CTRL',72:'LIST',73:'PAGEDEF',74:'FNSHAPE',75:'PBORDER',76:'SHAPECOMP',77:'TABLE',78:'LINE',79:'RECT',80:'ELLIPSE',81:'ARC',82:'POLY',83:'CURVE',84:'OLE',85:'PIC',86:'CONTAINER',87:'CTRLDATA',88:'EQEDIT'}
def body(path):
    st, _ = read_all(path)
    comp = bool(struct.unpack_from('<I', st[('FileHeader',)], 36)[0] & 1)
    d = st[('BodyText', 'Section0')]; d = zlib.decompress(d, -15) if comp else d
    return recs(d)
if __name__ == '__main__':
    rs = body(sys.argv[1])
    for i, (t, l, r) in enumerate(rs):
        extra = ''
        if t == 71:
            cid = r[:4][::-1].decode('latin1')
            extra = cid
            if cid in ('tbl ', 'gso ') and len(r) >= 46:
                prop, y, x, w, h = struct.unpack_from('<IiiII', r, 4)
                extra += f' prop={prop:08x} vert={(prop>>3)&3} horz={(prop>>8)&3} valign={(prop>>5)&7} halign={(prop>>10)&7} treatAsChar={prop&1} wrap={(prop>>21)&7} y={y} x={x} w={w} h={h}'
        elif t == 66:
            nch, = struct.unpack_from('<I', r, 0); extra = f'nchars={nch & 0x7fffffff}'
        elif t == 67:
            extra = repr(''.join(chr(c) if c >= 32 else '·' for c in struct.unpack_from('<%dH' % (len(r)//2), r))[:50])
        elif t == 73:
            extra = str(struct.unpack_from('<9I', r, 0))
        elif t == 76:
            extra = r[:8].hex()
        if t in (69, 68): continue
        print(i, '  ' * l + NAMES.get(t, str(t)), len(r), extra)
