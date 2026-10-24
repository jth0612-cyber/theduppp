"""LOGIC BUILD 2 여섯 단원(단위변환·산화환원·효소·중력장·중화반응·DNA)을 한 번에 다시 만든다.
Usage:  python hwp/build_all.py [단원 ...]          예) python hwp/build_all.py redox
환경 변수:
  LB_GEN   사용자 생성기 폴더(_생성스크립트: build.py, styles_more.py, tpl/, unit_B4.py …). 기본: <저장소>/nas/Logic Build/_생성스크립트
결과: hwp/final/<단원>_필기노트_LOGIC BUILD 2.hwpx  (중간 파일은 임시 폴더)"""
import os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GEN, TOOLS, ART, FINAL = (os.path.join(HERE, x) for x in ('gen', 'tools', 'art', 'final'))
UNITS = {'unit': '단위변환', 'redox': '산화환원', 'enzyme': '효소', 'gravity': '중력장', 'neutral': '중화반응', 'dna': 'DNA'}


def run(*a):
    print('>', ' '.join(a)); subprocess.run([sys.executable, *a], check=True, cwd=GEN)


if __name__ == '__main__':
    todo = sys.argv[1:] or list(UNITS)
    with tempfile.TemporaryDirectory() as tmp:
        outs = []
        for k in todo:
            raw = os.path.join(tmp, k + '_raw.hwpx')
            out = os.path.join(FINAL, '%s_필기노트_LOGIC BUILD 2.hwpx' % UNITS[k])
            run(os.path.join(GEN, 'unit_%s.py' % k), raw)
            run(os.path.join(TOOLS, 'make_wide.py'), raw, ART, out)
            outs.append(out)
        run(os.path.join(TOOLS, 'check_wide.py'), *outs)
