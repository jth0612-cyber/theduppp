"""원고 hwpx → 문단 단위 덤프(스타일명, 글자, ⟦수식⟧, [그림], 표). 사람이 읽고 원고 스크립트를 쓰기 위한 중간 자료."""
import re, sys, zipfile, json
from lxml import etree
HP = '{http://www.hancom.co.kr/hwpml/2011/paragraph}'
HC = '{http://www.hancom.co.kr/hwpml/2011/core}'

def load(path):
    z = zipfile.ZipFile(path)
    h = z.read('Contents/header.xml').decode()
    styles = dict(re.findall(r'<hh:style id="(\d+)" type="\w+" name="([^"]*)"', h))
    cpr = {}
    for m in re.finditer(r'<hh:charPr id="(\d+)" height="(\d+)" textColor="([^"]+)" shadeColor="([^"]+)"(.*?)</hh:charPr>', h, re.S):
        cpr[m.group(1)] = dict(h=int(m.group(2)), color=m.group(3), shade=m.group(4), bold='<hh:bold/>' in m.group(5),
                               sup='<hh:supscript/>' in m.group(5), sub='<hh:subscript/>' in m.group(5),
                               underline=bool(re.search(r'<hh:underline type="(?!NONE)', m.group(5))))
    secs = sorted(n for n in z.namelist() if re.match(r'Contents/section\d+\.xml', n))
    return z, styles, cpr, secs

def run_text(r, cpr, imgs):
    c = cpr.get(r.get('charPrIDRef'), {})
    out = []
    for ch in r:
        ln = etree.QName(ch).localname
        if ln == 't':
            s = ''.join(ch.itertext()) if len(ch) else (ch.text or '')
            if ch.text is None and len(ch):
                s = (ch.text or '') + ''.join(((' ' if etree.QName(x).localname in ('nbSpace', 'fwSpace') else '\t' if etree.QName(x).localname == 'tab' else '') + (x.tail or '')) for x in ch)
            elif len(ch):
                s = ch.text + ''.join(((' ' if etree.QName(x).localname in ('nbSpace', 'fwSpace') else '\t' if etree.QName(x).localname == 'tab' else '') + (x.tail or '')) for x in ch)
            if not s: continue
            if c.get('sup'): s = '^{' + s + '}'
            if c.get('sub'): s = '_{' + s + '}'
            if c.get('shade', 'none') not in ('none', '#FFFFFF'): s = '==' + s + '=='
            if c.get('color', '#000000') not in ('#000000', '#202020', '#000000FF') and not c.get('sup') and not c.get('sub'): s = '{%s}' % c['color'] + s + '{/}'
            if c.get('bold'): s = '**' + s + '**'
            out.append(s)
        elif ln == 'equation':
            sc = ch.find(HP + 'script').text or ''
            sz = ch.find(HP + 'sz')
            out.append('⟦%s|%s|%s⟧' % (sc.replace('\n', ' '), sz.get('width'), sz.get('height')))
        elif ln == 'pic':
            im = ch.find('.//' + HC + 'img'); sz = ch.find(HP + 'sz'); pos = ch.find(HP + 'pos')
            iid = im.get('binaryItemIDRef'); imgs.add(iid)
            out.append('[PIC %s %sx%s%s]' % (iid, sz.get('width'), sz.get('height'), '' if pos.get('treatAsChar') == '1' else ' float'))
        elif ln == 'tbl':
            out.append(table(ch, cpr, imgs))
        elif ln in ('rect', 'container', 'ellipse', 'line', 'polygon', 'curve', 'arc'):
            txt = ' / '.join(paras(ch, cpr, imgs, None))
            out.append('[SHAPE %s: %s]' % (ln, txt) if txt.strip() else '[SHAPE %s]' % ln)
        elif ln == 'ctrl':
            pass
    return ''.join(out)

def paras(el, cpr, imgs, styles):
    res = []
    for sl in el.iter(HP + 'subList'):
        if sl.getparent() is not None and etree.QName(sl.getparent()).localname == 'tc':
            continue
        for p in sl.findall(HP + 'p'):
            res.append(''.join(run_text(r, cpr, imgs) for r in p.findall(HP + 'run')))
    return res

def table(tbl, cpr, imgs):
    rows = []
    for tr in tbl.findall(HP + 'tr'):
        cells = []
        for tc in tr.findall(HP + 'tc'):
            span = tc.find(HP + 'cellSpan')
            txt = ' / '.join(''.join(run_text(r, cpr, imgs) for r in p.findall(HP + 'run')) for p in tc.find(HP + 'subList').findall(HP + 'p'))
            sp = '' if span is None or (span.get('colSpan') == '1' and span.get('rowSpan') == '1') else '<%sx%s>' % (span.get('colSpan'), span.get('rowSpan'))
            cells.append(sp + txt)
        rows.append(' | '.join(cells))
    sz = tbl.find(HP + 'sz')
    return '\n    [TABLE %sx%s w=%s]\n    ' % (tbl.get('rowCnt'), tbl.get('colCnt'), sz.get('width')) + '\n    '.join(rows) + '\n    [/TABLE]'

def main(path, out):
    z, styles, cpr, secs = load(path)
    imgs = set(); lines = []
    for sec in secs:
        root = etree.fromstring(z.read(sec))
        for i, p in enumerate(root.findall(HP + 'p')):
            st = styles.get(p.get('styleIDRef'), p.get('styleIDRef'))
            txt = ''.join(run_text(r, cpr, imgs) for r in p.findall(HP + 'run'))
            brk = ' ⏎PAGE' if p.get('pageBreak') == '1' else ''
            lines.append('%s#%d [%s]%s %s' % (sec[-5], i, st, brk, txt))
    open(out, 'w').write('\n'.join(lines))
    print(out, len(lines), 'paras', 'images', sorted(imgs, key=lambda s: int(re.sub(r'\D', '', s) or 0)))

if __name__ == '__main__':
    main(*sys.argv[1:3])
