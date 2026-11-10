import pathlib, re
D = pathlib.Path(__file__).parent
tabs = (D / "tabs.html").read_text()
tabs = re.sub(r'\s+href="[^"]*"', "", tabs).replace("<a ", "<span ").replace("</a>", "</span>").replace("<button", "<span").replace("</button>", "</span>")
logo = (D / "logo.html").read_text()

def tabs_for(active):
    t = tabs.replace(' class="active" aria-current="page"', ' class=""')
    parts = t.split('<span class=""')
    out = parts[0]
    for i, p in enumerate(parts[1:]):
        out += ('<span class="active"' if i == active else '<span class=""') + p
    return out

def spark(vals, avg, w=300, h=96, pad=8):
    lo, hi = 50, 100
    xs = [pad + i * (w - 2 * pad) / (len(vals) - 1) for i in range(len(vals))]
    y = lambda v: h - pad - (v - lo) / (hi - lo) * (h - 2 * pad)
    me = " ".join(f"{x:.1f},{y(v):.1f}" for x, v in zip(xs, vals))
    av = " ".join(f"{x:.1f},{y(v):.1f}" for x, v in zip(xs, avg))
    area = f"{xs[0]:.1f},{h} " + me + f" {xs[-1]:.1f},{h}"
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y(v):.1f}" r="3"/>' for x, v in zip(xs, vals))
    return (f'<svg class="spark" viewBox="0 0 {w} {h}" preserveAspectRatio="none" aria-hidden="true">'
            f'<polygon class="sp-area" points="{area}"/><polyline class="sp-avg" points="{av}"/>'
            f'<polyline class="sp-me" points="{me}"/><g class="sp-dot">{dots}</g></svg>')

ME = [72, 78, 81, 85, 88, 92]; AVG = [70.2, 73.2, 73.3, 77.0, 80.4, 74.7]

def ring(pct, size=88, sw=9, label="", sub=""):
    r = (size - sw) / 2; c = 2 * 3.14159 * r
    return (f'<div class="ring" style="--s:{size}px"><svg viewBox="0 0 {size} {size}"><circle cx="{size/2}" cy="{size/2}" r="{r}" class="rg-bg" stroke-width="{sw}"/>'
            f'<circle cx="{size/2}" cy="{size/2}" r="{r}" class="rg-fg" stroke-width="{sw}" stroke-dasharray="{c*pct:.1f} {c:.1f}" transform="rotate(-90 {size/2} {size/2})"/></svg>'
            f'<div class="rg-t"><b>{label}</b><span>{sub}</span></div></div>')

HEAD = f'<header class="top">{logo}<span class="lab">통합과학 lab</span><span class="who">씩씩한 표범</span></header>'

def phone(n, body, active=0, dark=False):
    return f'<section class="phone v{n}{" dark" if dark else ""}" id="v{n}"><div class="status"><b>9:41</b><span class="sb"><i></i><i></i><i></i><em></em></span></div>{HEAD}<main class="sheet">{body}</main>{tabs_for(active)}</section>'

# ---------- 시안 1: 소나무 카드 (오늘 하루를 한 장에)
v1 = f'''
<div class="hello"><span>11월 9일 월요일 · A반</span><h1>김○○님, 오늘도 반가워요</h1></div>
<div class="pine">
  <div class="pine-top"><div><span class="k">수능</span><b class="dd">D-10</b></div>{ring(120/180, 84, 8, "120분", "오늘 집중")}</div>
  <div class="now"><span class="dot-live"></span><div><b>지금 · 통합과학 정규</b><span>10:30–12:00 · 3강의실</span></div><span class="next">다음 13:00 자습</span></div>
</div>
<div class="row3">
  <div><b>2</b><span>남은 과제</span></div><div><b>3</b><span>복습할 오답</span></div><div><b>12<small>/20</small></b><span>오늘 영단어</span></div>
</div>
<div class="answer"><span class="cap">조교</span><div><b>김조교님이 답변했어요</b><p>개념서 42p 3번 · 보기 ㄴ은 양전하가 받는 힘의 방향으로…</p></div></div>
<h2 class="sec">이번 주 과제</h2>
<ul class="todo"><li><span>Squeeze S1 15호 풀이</span><em class="due">D-1</em></li><li><span>FRAMING 2단원 1~20번</span><em>D-2</em></li></ul>
<div class="mini"><div class="bh"><span class="k">주간테스트 흐름</span><span class="up">92점 · 반 평균 +17</span></div>{spark(ME, AVG, 300, 54)}</div>
'''

# ---------- 시안 2: 벤토 그리드
v2 = f'''
<div class="hello"><span>A반 · 씩씩한 표범</span><h1>김○○님</h1></div>
<div class="bento">
  <div class="b dd-tile"><span class="k">수능</span><b>D-10</b><span class="s">11월 19일 목요일</span></div>
  <div class="b">{ring(120/180, 74, 8, "120", "분")}<span class="s c">오늘 집중 · 목표 180분</span></div>
  <div class="b wide score"><div class="bh"><span class="k">모의고사 흐름</span><span class="up">+17점</span></div>{spark(ME, AVG, 300, 70)}<div class="lg"><i class="me"></i>나 <i class="av"></i>반 평균</div></div>
  <div class="b vocab"><span class="k">오늘의 20단어</span><b class="word">perspective</b><span class="s">관점, 원근법</span><div class="bar"><i style="width:60%"></i></div><span class="s">12 / 20</span></div>
  <div class="b room"><span class="k light">소도시 명상</span><b>23명</b><span class="s light">지금 노천탕에서 집중 중</span></div>
  <div class="b half"><span class="k">남은 과제</span><b class="num">2</b><span class="s">Squeeze S1 15호 · D-1</span></div>
  <div class="b half"><span class="k">복습할 오답</span><b class="num">3</b><span class="s">파이널 1회 16·22·25번</span></div>
  <div class="b wide ans"><span class="cap">조교</span><span><b>개념서 42p 3번</b>에 답변이 왔어요</span><span class="go">›</span></div>
</div>
'''

# ---------- 시안 3: 오늘 타임라인
v3 = f'''
<div class="hello row"><div><span>11월 9일 월요일</span><h1>오늘의 흐름</h1></div><div class="dd-pill">수능 D-10</div></div>
<div class="focusbar"><div class="fb-h"><b>오늘 집중 120분</b><span>목표 180분</span></div><div class="bar thick"><i style="width:66%"></i></div><div class="streak">{''.join(f'<i class="{"on" if i<6 else ""}">{d}</i>' for i,d in enumerate("월화수목금토일"))}</div></div>
<ol class="tl">
  <li class="done"><time>08:30</time><div><b>국어 정규</b><span>2강의실</span></div></li>
  <li class="now"><time>10:30</time><div><b>통합과학 정규</b><span>3강의실 · 지금 수업 중</span></div></li>
  <li><time>13:00</time><div><b>자습 · Squeeze S1 15호</b><span>과제 마감 내일</span></div></li>
  <li><time>15:00</time><div><b>오답 3문항 다시 풀기</b><span>파이널 1회 16 · 22 · 25번</span></div></li>
  <li><time>19:00</time><div><b>소도시 명상 80분</b><span>노천탕 화롯가</span></div></li>
  <li><time>21:30</time><div><b>오늘의 20단어 확인 퀴즈</b><span>Day 3 · 12/20 외움</span></div></li>
</ol>
'''

# ---------- 시안 4: 성적 중심
v4 = f'''
<div class="hello"><span>A반 · 김○○님</span><h1>점수가 오르고 있어요</h1></div>
<div class="scorecard">
  <div class="sc-h"><div><span class="k">6주차 주간테스트</span><b class="big">92<small>/100</small></b></div><div class="delta">반 평균보다<br><b>+17.3</b></div></div>
  {spark(ME, AVG, 300, 96)}
  <div class="lg"><i class="me"></i>내 점수 <i class="av"></i>반 평균<span class="r">1–6주차</span></div>
</div>
<h2 class="sec">자주 틀리는 이유</h2>
<div class="why"><div><span>자료 해석</span><div class="bar"><i style="width:62%"></i></div><b>5</b></div><div><span>조건 놓침</span><div class="bar"><i style="width:38%"></i></div><b>3</b></div><div><span>계산 실수</span><div class="bar"><i style="width:22%"></i></div><b>2</b></div></div>
<div class="cta"><div><b>오답 3문항 다시 풀기</b><span>맞히면 목록에서 지워져요</span></div><span class="btn">풀기</span></div>
'''

# ---------- 시안 5: 소도시 명상 중심 (어두운 화면)
v5 = f'''
<div class="hero"><img src="room.jpg" alt=""><div class="hero-in"><span class="live"><i></i>지금 23명 집중 중</span><h1>노천탕 화롯가에<br>자리가 남아 있어요</h1><span class="enter">들어가기</span></div></div>
<div class="statgrid">
  <div>{ring(120/180, 70, 7, "120", "분")}<span>오늘 집중</span></div>
  <div><b class="n">D-10</b><span>수능</span></div>
  <div><b class="n">7<small>일</small></b><span>연속 출석</span></div>
</div>
<ul class="list">
  <li><span class="tg">과제</span><b>Squeeze S1 15호 풀이</b><em class="due">D-1</em></li>
  <li><span class="tg">오답</span><b>파이널 1회 16 · 22 · 25번</b><em>3문항</em></li>
  <li><span class="tg ok">답변</span><b>개념서 42p 3번</b><em>김조교</em></li>
  <li><span class="tg">단어</span><b>오늘의 20단어 Day 3</b><em>12/20</em></li>
</ul>
'''

CSS = (D / "mock.css").read_text()
html = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>메인 화면 시안</title><style>{CSS}</style></head><body>
{phone(1, v1)}{phone(2, v2)}{phone(3, v3)}{phone(4, v4)}{phone(5, v5, 0, True)}
</body></html>'''
(D / "mock.html").write_text(html)
