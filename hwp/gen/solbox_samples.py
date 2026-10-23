"""풀이 상자 시안 A~E 비교용 hwpx: 시안마다 한 쪽 (효소 Mini 예제 6 풀이 + Arranged KICE 1)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lb as L
import solbox as SB
import sol_enzyme
L.use_solutions(sol_enzyme)
import unit_enzyme as U        # 원고 블록 (HEAD, 그림 경로)

if __name__ == '__main__':
    out = sys.argv[1]
    L.use_style('final')
    L.B.FONTS[0] = (12, 'THE썸머캠프')
    L.B.FONTS[3] = (15, 'GangwonEduAll Light')
    m6, k1 = sol_enzyme.SOL['M6'], sol_enzyme.SOL['K1']
    kfig = os.path.join(L.KICE_DIR, L.KICE_IMG['enzyme/image12.png'])
    pw, ph = L.Image.open(kfig).size
    w = int(29000 * L.KICE_SCALE)
    pages = []
    for st in 'ABCDE':
        blocks = [
            L.Block(lambda st=st: L.B.cf('풀이 상자 시안 %s · %s' % (st, SB.NAMES[st]), '시안'), 40),
            L.Block(lambda: L.B.small_bar('Mini 예제 6'), 20),
            L.Block(lambda st=st: SB.box('Point 3 풀이', m6, st), SB.height(m6, st)),
            L.Block(L.B.blank, 18),
            L.Block(lambda: [L.B.small_bar('Arranged KICE 1', rnd=True), L.B.question('그림 (나)는 어떤 효소 반응에서 효소의 농도가 일정할 때 이 반응의 진행에 따른 에너지를 나타낸 것이다.'),
                             L.B.question('E는 t_{1}일 때가 t_{2}일 때보다 크다. (O, X)')], 50),
            L.Block(lambda: L.figure_para([(kfig, w, int(w * ph / pw))], L.FULL_W), 200),
            L.Block(lambda st=st: SB.box('적용 풀이', k1, st), SB.height(k1, st)),
            L.Block(lambda: L.B.answer('X'), 26),
        ]
        pages.append([b.make for b in blocks])
    L.write(L.build(U.HEAD(), pages), out, '풀이 상자 시안')
    print('ok', out)
