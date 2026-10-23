"""make_wide 결과 검사: XML, 2단·세로선·TAG·바탕색·남은 마크업, 표 폭."""
import re, sys, zipfile
from collections import Counter
from lxml import etree
for f in sys.argv[1:]:
    z = zipfile.ZipFile(f); assert z.infolist()[0].filename == 'mimetype' and z.infolist()[0].compress_type == 0
    for n in z.namelist():
        if n.endswith('.xml') or n.endswith('.hpf'): etree.fromstring(z.read(n))
    s = z.read('Contents/section0.xml').decode(); h = z.read('Contents/header.xml').decode()
    for tag, cnt in re.findall(r'<hh:(\w+) itemCnt="(\d+)">', h):
        child = {'borderFills': 'borderFill', 'charProperties': 'charPr', 'tabProperties': 'tabPr',
                 'numberings': 'numbering', 'bullets': 'bullet', 'paraProperties': 'paraPr', 'styles': 'style'}.get(tag)
        if child: assert len(re.findall(r'<hh:%s [^>]*id=' % child, h)) == int(cnt), (tag, cnt)
    txt = ''.join(re.findall(r'<hp:t>([^<]*)</hp:t>', s))
    ws = Counter(int(x) for x in re.findall(r'<hp:tbl [^>]*>\s*<hp:sz width="(\d+)"', s))
    print(f.split('/')[-1], '| 2단', s.count('colCount="2"'), '| 세로선', len([1 for m in re.finditer(r'<hp:line .*?</hp:line>', s, re.S) if '70015' in m.group(0)]),
          '| TAG', s.count('width="3418"') + txt.count('TAG'), '| 옛 바탕', h.count('F8F1E7') + h.count('FAF5EE'),
          '| 마크업', sum(txt.count(k) for k in ('«', '»', '**', '==', '~~')), '| 띠 9번', s.count('borderFillIDRef="9"'),
          '| 쪽', s.count('pageBreak="1"') + 1, '| 표 폭 최대', max(ws), sorted(ws.items())[-6:])
