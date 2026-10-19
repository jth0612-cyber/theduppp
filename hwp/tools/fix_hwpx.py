"""Usage: python3 fix_hwpx.py in.hwpx out.hwpx  -- 2단 -> 1단, 단 구분 세로선 제거, 상자/표 폭 확장"""
import sys, zipfile
from lxml import etree
P='{http://www.hancom.co.kr/hwpml/2011/paragraph}'
src,dst=sys.argv[1],sys.argv[2]
zi=zipfile.ZipFile(src)
out=zipfile.ZipFile(dst,'w')
items=sorted(zi.infolist(),key=lambda i:i.filename!='mimetype')
for it in items:
    b=zi.read(it)
    if it.filename.startswith('Contents/section') and it.filename.endswith('.xml'):
        root=etree.fromstring(b)
        pp=root.find('.//'+P+'pagePr'); m=pp.find(P+'margin')
        full=int(pp.get('width'))-int(m.get('left'))-int(m.get('right'))
        if pp.get('landscape')=='NARROWLY': full=int(pp.get('height'))-int(m.get('left'))-int(m.get('right'))
        multi=False
        for c in root.iter(P+'colPr'):
            if int(c.get('colCount','1'))>1: multi=True
            for ch in list(c): c.remove(ch)
            c.set('colCount','1'); c.set('layout','LEFT'); c.set('sameSz','1'); c.set('sameGap','0')
        lines=0
        for ln in list(root.iter(P+'line')):
            sz=ln.find(P+'sz')
            if int(sz.get('width'))<=10 and int(sz.get('height'))>40000:
                ln.getparent().remove(ln); lines+=1
        tbls=list(root.iter(P+'tbl'))
        old=max(int(t.find(P+'sz').get('width')) for t in tbls) if tbls else 0
        delta=full-old if multi and old<full else 0
        n=0
        if delta:
            for t in tbls:
                sz=t.find(P+'sz'); w=int(sz.get('width'))
                if w<old*0.85: continue
                nw=w+delta; sz.set('width',str(nw)); n+=1
                for tr in t.findall(P+'tr'):
                    cells=[tc.find(P+'cellSz') for tc in tr.findall(P+'tc')]
                    ws=[int(c.get('width')) for c in cells]
                    new=[round(x*nw/w) for x in ws]
                    if sum(ws)==w: new[-1]+=nw-sum(new)
                    for c,x in zip(cells,new): c.set('width',str(x))
            for ls in list(root.iter(P+'linesegarray')): ls.getparent().remove(ls)
        print(f'{src}: {it.filename} cols_was_multi={multi} lines_removed={lines} tables_widened={n} {old}->{old+delta}')
        b=b'<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'+etree.tostring(root,encoding='UTF-8')
    ct=zipfile.ZIP_STORED if it.filename=='mimetype' else it.compress_type
    out.writestr(it,b,compress_type=ct)
out.close()
