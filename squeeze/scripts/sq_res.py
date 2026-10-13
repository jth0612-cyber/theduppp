# 03-01-14 D 디자인을 리소스 PDF(release_point_resources) 형식으로: 같은 쪽 크기·순서에 새 디자인 요소만 끼움.
# - 본문 글자(문항·번호·쪽번호·단원명·'과학의 기본량' 등)는 모두 비움. 디자인 라벨(Solving·Linking·MEMO·Logic·Contents·
#   Logic Check; MEMO·Logic은 Cinzel 별색)과 'Squeeze' 로고 글자는 원본 리소스처럼 윤곽선(패스)으로 넣음.
# - 빠른 정답 요소(원본 9~15쪽)는 뺌. O·X 표시와 아이콘(17·18·20·21, 30~59쪽)은 원본 그대로.
# - 맨 뒤에 Squeeze에만 있는 Logic Check 쪽을 덧붙임.
# 사용: python sq_res.py <squeeze.pdf> <resources.pdf> <출력.pdf>
import sys
sys.path.insert(0, '.')
import sq_wave, sq_label10, sq_full, sq_combo20, sq_lib, sq8, sq9, sq5, sq_combo
from sq_lib import P, f, m, W, H, S
from sq_full import head, p3_head, dots, find_dots, page_memo, page_contents, page_logic, section_head
MM = 72 / 25.4

KEEP_WORDS = {'Solving', 'Linking', 'MEMO', 'Logic', 'Contents', 'Logic Check', 'Squeeze'}
LABEL = dict(font='md', size=10.0)   # MEMO·Logic 라벨: 영문 제목 글꼴(Cinzel), 별색
_text = P.text
TEXT = f.open(); _layer = {}            # 쪽마다 글자만 따로 쓰는 층(나중에 윤곽선으로 바꿔 얹음)
def text_filtered(s, x, y, text, font, size, color, align='l', track=0):
    if text not in KEEP_WORDS: return s.width(text, font, size, track)   # 자리(폭)만 계산, 글자는 비움
    key = (id(s.p.parent), s.p.number)
    if key not in _layer:
        TEXT.new_page(width=s.p.rect.width, height=s.p.rect.height)
        _layer[key] = (s.p.parent, s.p.number, len(TEXT) - 1)
    return _text(P(TEXT[_layer[key][2]]), x, y, text, font, size, color, align, track)
P.text = text_filtered

def outline_text():
    """글자 층을 SVG(글자→패스)로 바꿨다가 PDF로 되돌려 제 쪽 위에 얹음. 다른 요소는 손대지 않음."""
    for doc, num, tn in _layer.values():
        svg = TEXT[tn].get_svg_image(text_as_path=True)
        pdf = f.open('pdf', f.open(stream=svg.encode(), filetype='svg').convert_to_pdf())
        doc[num].show_pdf_page(doc[num].rect, pdf, 0)

def blank(doc, w=W, h=H):
    return doc.new_page(width=m(w), height=m(h))

if __name__ == '__main__':
    SRC, RESP, OUT = sys.argv[1:4]
    sq_combo20.setup('11'); sq_label10.setup('17')
    sq_full.section_head = sq_wave.VARS['D'][1]
    src = f.open(SRC); res = f.open(RESP); sq8.RES = res; sq9.SRC_DOC = src
    sq8.set_numfont('fs/ttf/barlow-condensed-500.ttf')
    new = f.open(); log = []

    def add(desc): log.append((len(new), desc))

    # 1 짝수쪽 틀: 상단 핀(짝수 쪽) + 하단 Squeeze 로고
    pg = blank(new); d = P(pg, res); head(d, 'even'); sq_full.foot_default(d, 'even', 0); add('1 짝수쪽 틀(상단 핀·하단 Squeeze)')
    # 2 홀수쪽 틀: 상단 핀(홀수 쪽) + THedu 로고
    pg = blank(new); d = P(pg, res); head(d, 'odd'); sq_full.foot_default(d, 'odd', 0); add('2 홀수쪽 틀(상단 핀·THedu)')
    # 3 MEMO 쪽: 큰 'Memo' 제목은 빼고, 선 위 라벨 'MEMO'를 Cinzel 별색으로
    _p3 = sq_full.p3_head
    sq_full.p3_head = lambda d, x0, x1, y, label, **k: _p3(d, x0, x1, y, label, color=S(), **LABEL)
    new.insert_pdf(src, from_page=24, to_page=24); page_memo(new[-1], 25, None); add('3 MEMO 쪽')
    sq_full.p3_head = _p3
    # 4 창작 문항 표식 → 작은 핀 표식(2토막)
    pg = blank(new, 37.7, 5.5); d = P(pg, res); sq8.fin_stack(d, 0.6, 0.0, [(2.6, sq_lib.S_, 1), (2.2, sq_lib.S_, .45)], w=0.5); add('4 표식 → 핀 표식')
    # 5·6 차례(글자 있음/없음)
    new.insert_pdf(src, from_page=1, to_page=1); page_contents(new[-1], 2); add('5 차례(Contents)')
    KEEP_WORDS.discard('Contents')
    new.insert_pdf(src, from_page=1, to_page=1); page_contents(new[-1], 2); add('6 차례(글자 없음)')
    KEEP_WORDS.add('Contents')
    # 7 정답 및 해설 여는 쪽 → 짝수 상단 핀 + 제목 자리 P3 선
    pg = blank(new); d = P(pg, res); head(d, 'even'); p3_head(d, 19, 243, 60, ''); sq_full.foot_default(d, 'even', 0); add('7 해설 여는 쪽(상단 핀·P3 선)')
    # 8 제목 띠(105.5×15) → P3 머리 선
    pg = blank(new, 105.5, 15.0); d = P(pg, res); p3_head(d, 0, 105.5, 10.0, ''); add('8 제목 띠 → P3 선')
    # 16 하늘색 띠(110×12) → P3 머리 선 / 17·18 따옴표 그대로 / 19 그러데이션 가는 띠 → 가는 핀 줄
    pg = blank(new, 110, 12); d = P(pg, res); p3_head(d, 0, 110, 8.0, ''); add('16 띠 → P3 선')
    for i in (16, 17): new.insert_pdf(res, from_page=i, to_page=i); add(f'{i + 1} 따옴표(원본)')
    pg = blank(new, 110, 3); d = P(pg, res); sq7 = __import__('sq7'); sq7.fin_row(d, 1, 109, 0.0, 2.6, 0.8, 19); add('19 가는 띠 → 핀 줄')
    for i in (19, 20): new.insert_pdf(res, from_page=i, to_page=i); add(f'{i + 1} 전구 아이콘(원본)')
    # 22 홀수쪽(해설) 틀
    pg = blank(new); d = P(pg, res); head(d, 'odd'); sq_full.foot_default(d, 'odd', 0); add('22 홀수쪽 틀(해설)')
    # 23 Linking 줄 / 24 Solving 줄 (파형 D)
    pg = blank(new, 108, 13); d = P(pg, res); sq_full.section_head(d, 'Linking', 'Linking', 0, 108, 3.85, 41); add('23 Linking 줄(파형 D)')
    pg = blank(new, 108, 19); d = P(pg, res); sq_full.section_head(d, 'Solving', 'Solving', 0, 108, 9.7, 47); add('24 Solving 줄(파형 D)')
    # 25~29 풀이 칸(높이별): P3 머리 + 원본 자리의 배경 점 14%
    for i in range(24, 29):
        rp = res[i]
        box = [g['rect'] for g in rp.get_drawings() if g.get('width') and g['width'] > 1.5][0]
        bx = tuple(v / MM for v in box)
        pts = [((r.x0 + r.x1) / 2 / MM, (r.y0 + r.y1) / 2 / MM) for r in (g['rect'] for g in rp.get_drawings() if g.get('fill') and g['rect'].width < 1 * MM)]
        pts = [(x, y) for x, y in pts if bx[0] < x < bx[2] and bx[1] + 3 < y < bx[3]]
        pg = blank(new); d = P(pg, res); dots(d, pts); p3_head(d, bx[0], bx[2], bx[1], 'Logic', color=S(), **LABEL); add(f'{i + 1} 풀이 칸 → Logic 라벨(높이 {bx[3] - bx[1]:.0f}mm)')
    # 30~59 O·X 표시와 아이콘: 원본 그대로
    start = len(new); new.insert_pdf(res, from_page=29, to_page=58)
    for i in range(29, 59): log.append((start + i - 28, f'{i + 1} 원본 그대로'))
    # 덧붙임: Logic Check 쪽(Squeeze 전용)
    new.insert_pdf(src, from_page=3, to_page=3); page_logic(new[-1], src, 4, 'A. 고체'); add('+ Logic Check 쪽(Squeeze 전용)')

    outline_text()
    new.save(OUT, garbage=4, deflate=True)
    with open(OUT.rsplit('.', 1)[0] + '_목록.txt', 'w') as fp:
        for k, (n, desc) in enumerate(sorted(log)): fp.write(f'{n:>2}쪽 ← 원본 {desc}\n')
    print(len(new), 'pages ->', OUT)
