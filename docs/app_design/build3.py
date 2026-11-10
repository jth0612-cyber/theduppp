import pathlib, json
D = pathlib.Path(__file__).parent
ns = {"__file__": str(D / "build.py")}
exec((D / "build.py").read_text().split("CSS = (D")[0], ns)
phone, spark, ring, ME, AVG = ns["phone"], ns["spark"], ns["ring"], ns["ME"], ns["AVG"]
ICON = {x["label"]: x["svg"] for x in json.loads((D / "icons.json").read_text())}

# ---------------------------------------------------------------- 홈 (모든 기능 한 화면)
grid = [("공지", "공지", ""), ("시간표", "시간표", ""), ("과제", "과제", "2"), ("자료실", "자료실", ""),
        ("강의 영상", "강의 영상", ""), ("질답 게시판", "질답", "1"), ("소도시 명상", "소도시 명상", ""), ("미니 Quiz", "미니 Quiz", ""),
        ("오답 노트", "오답 노트", "3"), ("모의고사 분석", "모의고사 분석", ""), ("내 성적", "내 성적", ""), ("내 리포트", "내 리포트", "")]
cells = "".join(f'<div class="gi"><span class="gic">{ICON[k]}{f"<em>{b}</em>" if b else ""}</span><span>{lab}</span></div>' for k, lab, b in grid)
home = f'''
<div class="h-top"><div><span class="k">A반 · 씩씩한 표범</span><h1>김○○</h1></div><div class="dd-box"><span>수능</span><b>D-10</b></div></div>
<div class="h-now"><div class="hn-l"><span class="dot-live"></span><div><b>통합과학 정규</b><span>10:30–12:00 · 3강의실</span></div></div><div class="hn-r"><span>다음</span><b>13:00 자습</b></div></div>
<div class="h-stats"><div><b>120<small>분</small></b><span>오늘 집중</span></div><div><b>2</b><span>남은 과제</span></div><div><b>3</b><span>복습할 오답</span></div><div><b>12<small>/20</small></b><span>영단어</span></div></div>
<div class="h-grid">{cells}</div>
<div class="h-two">
  <div class="ht score"><div class="bh"><span class="k">6주차 주간테스트</span></div><b class="sc">92<small> / 반 평균 74.7</small></b>{spark(ME, AVG, 160, 44)}</div>
  <div class="ht ans"><span class="cap">조교 답변</span><b>개념서 42p 3번</b><span class="s">전기장 방향은 (+)전하가 받는 힘의 방향…</span></div>
</div>
<ul class="h-list"><li><span class="tg">공지</span><b>토요일 특강 안내</b><em>11.03</em></li><li><span class="tg">영상</span><b>원소의 생성 · 3주차</b><em>71:11</em></li></ul>
'''

# ---------------------------------------------------------------- 기능별 카드
def card(key, title, body, cls=""):
    return f'<section class="fc {cls}" id="f-{key}"><div class="fc-h"><span class="fc-i">{ICON[title]}</span><b>{title}</b></div>{body}</section>'

C = []
C.append(card("notice", "공지", '''
<ul class="nl"><li><span class="tg2 t-pin">고정</span><div><b>이번 주 토요일 특강 안내</b><span>11.03 · 읽음 38 · 공감 12</span></div></li>
<li><span class="tg2 t-red">정오</span><div><b>42p 3번 보기 정오</b><span>11.01 · 개념서 1권</span></div></li>
<li><span class="tg2 t-sky">일정</span><div><b>7주차 주간테스트 범위</b><span>10.31 · 전기장 · 생태계 평형</span></div></li></ul>'''))

slots = [(0, 0, 2, "국어 정규", "c1"), (1, 0, 2, "국어 정규", "c1"), (2, 0, 2, "국어 정규", "c1"), (3, 0, 2, "국어 정규", "c1"), (4, 0, 2, "국어 정규", "c1"),
         (0, 2, 2, "통합과학", "c2"), (1, 2, 2, "수학 정규", "c3"), (2, 2, 2, "통합과학", "c2"), (3, 2, 2, "수학 정규", "c3"), (4, 2, 2, "영어 정규", "c4"),
         (0, 5, 2, "자습", "c5"), (1, 5, 2, "인강", "c6"), (2, 5, 2, "자습", "c5"), (3, 5, 2, "인강", "c6"), (4, 5, 2, "자습", "c5")]
tt = "".join(f'<i class="tb {c}{" now" if (d,r)==(0,2) else ""}" style="grid-column:{d+2};grid-row:{r+2}/span {sp}">{t}</i>' for d, r, sp, t, c in slots)
hours = "".join(f'<span class="th" style="grid-row:{i+2}">{h}</span>' for i, h in enumerate(["08", "09", "10", "11", "12", "13", "14"]))
days = "".join(f'<span class="td{" on" if i==0 else ""}" style="grid-column:{i+2}">{d}</span>' for i, d in enumerate("월화수목금"))
C.append(card("tt", "시간표", f'<div class="ttg">{days}{hours}{tt}</div>'))

C.append(card("task", "과제", '''
<ul class="tk"><li><div><b>Squeeze S1 15호 풀이</b><span>20문항 · 마감 11.10</span></div><em class="due">D-1</em><span class="btn-s">답 입력</span></li>
<li><div><b>2단원 기출 1회</b><span>5문항 · 제출 완료</span></div><b class="got">4<small>/5</small></b></li>
<li class="res"><span>자동 채점</span><i class="ok">1</i><i class="ok">2</i><i class="no">3</i><i class="ok">4</i><i class="ok">5</i><span class="s">해설 열림</span></li></ul>'''))

C.append(card("mat", "자료실", '''
<ul class="fl"><li><span class="pdf">PDF</span><div><b>Squeeze S1 15호</b><span>2.4MB · 11.07</span></div></li>
<li><span class="pdf">PDF</span><div><b>2단원 필기노트</b><span>1.8MB · 11.05</span></div></li>
<li><span class="pdf">PDF</span><div><b>FRAMING 2단원 해설</b><span>3.1MB · 11.03</span></div></li></ul>'''))

C.append(card("video", "강의 영상", '''
<div class="vid"><img src="lecture.jpg" alt=""><span class="play"></span><span class="dur">71:11</span></div>
<div class="vt"><b>원소의 생성 · 3주차</b><span>12.31까지 시청 가능</span></div>'''))

C.append(card("qa", "질답 게시판", '''
<div class="q"><div class="qh"><span class="tg2 t-pine">답변 완료</span><span class="s">학습질문 · 씩씩한 표범</span></div><b>개념서 42p 3번</b><p>전기장 방향이 왜 이렇게 되는지 모르겠어요. 보기 ㄴ에서 막혔어요.</p></div>
<div class="a"><div class="ah"><span class="cap">조교</span><b>김조교</b><span class="s">09:02</span></div><p>전기장 방향은 (+)전하가 받는 힘의 방향이에요. 그림에서 (+)전하는 오른쪽으로 힘을 받으니 ㄴ은 옳은 보기예요.</p></div>'''))

C.append(card("room", "소도시 명상", '''
<div class="rm"><img src="room.jpg" alt=""><span class="live"><i></i>노천탕 23명</span><span class="tmr">54:53</span></div>
<div class="rp">''' + "".join(f'<div><b>{n}</b><span>{k}명</span></div>' for n, k in [("노천탕", 23), ("바닷가 역", 14), ("골목 찻집", 9)]) + '''</div>''', "dark"))

C.append(card("quiz", "미니 Quiz", '''
<div class="qz2"><div class="vc"><span class="k">오늘의 20단어 · Day 3</span><b>perspective</b><span>관점, 원근법</span><div class="bar"><i style="width:60%"></i></div><span class="s">12 / 20</span></div>
<div class="sq"><span class="k">통합과학 · 물질과 규칙성</span><b>원자가 전자 수가 같아 화학적 성질이 비슷한 원소들의 세로줄은?</b>
<div class="op"><span>주기</span><span class="right">족</span><span>전자 껍질</span></div><span class="okmsg">정답 · 같은 족 원소는 원자가 전자 수가 같다</span></div></div>'''))

C.append(card("wrong", "오답 노트", '''
<div class="wn"><div class="wh"><b class="no">16번</b><span>내 답 2 · 정답 4 · 반 오답률 18%</span></div>
<div class="rs"><span>개념 부족</span><span class="on">자료 해석</span><span>조건 놓침</span><span>계산 실수</span><span>시간 부족</span><span>찍음</span></div>
<div class="memo">그래프 기울기 의미를 거꾸로 읽음</div><div class="redo"><span class="chk">✓</span>다시 풀어서 맞힘</div></div>'''))

qs = [(3, 12), (8, 26), (11, 41), (16, 18), (19, 52), (22, 35), (25, 64)]
mine = {16, 22, 25}
bars = "".join(f'<div class="mq{" mine" if n in mine else ""}"><span>{n}</span><div class="bar"><i style="width:{p}%"></i></div><b>{p}%</b></div>' for n, p in qs)
C.append(card("mock", "모의고사 분석", f'''
<div class="mk-h"><div><span class="k">2027 통합과학 파이널 1회</span><b class="big2">40.5<small>/50</small></b></div><div class="mk-r"><span>반 평균 36.2</span><span>틀린 문항 3</span></div></div>
<div class="mqs"><div class="mq head"><span>문항</span><span>반 오답률</span><span></span></div>{bars}</div>'''))

rows = [("6주차", 92, 74.7), ("5주차", 88, 80.4), ("4주차", 85, 77.0), ("3주차", 81, 73.3)]
C.append(card("score", "내 성적", '<table class="st"><tr><th>시험</th><th>내 점수</th><th>반 평균</th><th></th></tr>' + "".join(
    f'<tr><td>{n} 주간테스트</td><td><b>{m}</b></td><td>{a}</td><td class="up">+{m-a:.1f}</td></tr>' for n, m, a in rows) + '</table>'))

UNITS = [("과학의 기초", 92, "u1"), ("물질과 규칙성", 81, "u2"), ("시스템과 상호작용", 74, "u3"), ("변화와 다양성", 88, "u4"), ("환경과 에너지", 63, "u5")]
C.append(card("report", "내 리포트", f'''
<div class="rp-h"><b>1–6주차</b><span class="lg"><i class="me"></i>나 <i class="av"></i>반 평균</span></div>{spark(ME, AVG, 330, 80)}
<div class="units">{''.join(f'<div><span class="ud {c}"></span><span class="un">{n}</span><div class="bar"><i class="{c}" style="width:{v}%"></i></div><b>{v}%</b></div>' for n,v,c in UNITS)}</div>
<div class="hab"><span>소도시 명상 4주 · 17시간 45분</span><span>과제 제출 4/4</span></div>'''))

CSS = (D / "mock.css").read_text() + (D / "mock2.css").read_text() + (D / "mock3.css").read_text()
html = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>홈과 기능</title><style>{CSS}</style></head><body>
{phone("h0", home)}<div class="cards">{''.join(C)}</div></body></html>'''
(D / "mock3.html").write_text(html)
print([c.split('id="')[1].split('"')[0] for c in C])
