# 단위변환 (단위와 단위 변환): 사용자 원고 스크립트 _생성스크립트/unit_B4.py 를 그대로 읽어
# 1단 전체 폭 블록(lb.py)으로 다시 조판한다. 날개 주석·TAG 없이 쪽은 자동으로 나눈다.
import os, re, sys
import lb as L

SRC = os.path.join(L.GEN, 'unit_B4.py')


def question(s): return L.Block(lambda: L.B.question(s), L.LINE_Q * L.nlines(s, L.PER_Q) + 6, keep_next=True)
def small_bar(s): return L.Block(lambda: L.B.small_bar(s), 20, keep_next=True)
def answer(s): return L.Block(lambda: L.B.answer(s), 26)
def box(head, lines):
    lines = L._clean(lines)
    return L.Block(lambda: L.B.box(head, lines), 26 + sum(L.LINE_BOX * L.nlines(x, L.PER_BOX) for x in lines) + 10)


def load():
    common = open(os.path.join(L.GEN, 'unit_common.py'), encoding='utf-8').read()   # 공용 표(PREFIX_TABLE 등)
    src = common + '\n' + open(SRC, encoding='utf-8').read()
    src = src[:src.index('\nout = sys.argv[1]')]
    src = re.sub(r'^(from|import) .*$', '', src, flags=re.M)
    ns = {k: getattr(L, k) for k in ('note', 'sub', 'tip', 'cf', 'blank', 'theme', 'point', 'bar', 'table')}
    ns.update(head=L.B.head, h1=L.h, question=question, small_bar=small_bar, answer=answer, box=box, sys=sys, os=os)
    exec(compile(src, SRC, 'exec'), ns)
    # Mini 예제의 풀이 상자 뒤 정답까지는 한 묶음으로
    blocks = []
    for page in ns['pages']:
        for x in page:
            b = x()
            blocks += b if isinstance(b, list) else [b]
    for a, b in zip(blocks, blocks[1:]):
        if b.make.__qualname__.startswith('answer'):
            a.keep_next = True
    return ns['HEAD'], blocks


if __name__ == '__main__':
    out = sys.argv[1]
    L.use_style('final')
    L.B.FONTS[0] = (12, 'THE썸머캠프')
    L.B.FONTS[3] = (15, 'GangwonEduAll Light')
    HEAD, blocks = load()
    rep = []
    pages = L.paginate(blocks, rep)
    for i, (u, s) in enumerate(rep):
        print('page %d: 본문 %.0fpt' % (i + 6, u))
    L.write(L.build(HEAD(), pages), out, '단위와 단위 변환')
    print('ok', out, len(pages), 'pages')
