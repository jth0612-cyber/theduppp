// 역할별 기능 둘러보기 녹화 (Playwright MCP browser_run_code_unsafe, __ROLE__ = student|ta|teacher). 화면은 _deploy/videos/frames_<역할>/ 에 찍히고 tools/frames_to_mp4.py 로 잇는다.
async (page) => {
  const ROLE = "__ROLE__";
  const B = "http://127.0.0.1:5077";
  const OUT = "C:/Users/jsmd9/AppData/Local/Temp/claude/e4ebe662e72fced6/0bf3fcd4-e3c5-4aa6-89ae-1c66135f742f/scratchpad/vid";
  const ACC = {student: ["__STUDENT_ID__", "__STUDENT_PW__", "학생 박서윤 (대구 토요일 A반)"],   // 실행 전에 DEMO_CREDENTIALS.txt 값으로 바꾼다 (저장소에는 비밀번호를 넣지 않는다)
               ta: ["ta_hanjisu", "__TA_PW__", "조교 한지수"],
               teacher: ["master", "__TEACHER_PW__", "선생님 정태혁"]}[ROLE];
  const br = page.context().browser();
  const ctx = await br.newContext({serviceWorkers: "block", viewport: {width: 1280, height: 800}});
  const FR = `C:/Users/jsmd9/OneDrive/Desktop/TH/management/_deploy/videos/frames_${ROLE}/`;
  await ctx.addInitScript(() => {
    const mk = () => {
      if (document.getElementById("__cur")) return;
      const c = document.createElement("div"); c.id = "__cur";
      Object.assign(c.style, {position: "fixed", width: "22px", height: "22px", marginLeft: "-11px", marginTop: "-11px", borderRadius: "50%",
        background: "rgba(255,110,66,.45)", border: "2px solid #FF6E42", zIndex: 2147483647, pointerEvents: "none", transition: "transform .12s",
        left: (sessionStorage.getItem("__cx") || 640) + "px", top: (sessionStorage.getItem("__cy") || 400) + "px"});
      document.body.appendChild(c);
      const cap = document.createElement("div"); cap.id = "__cap";
      Object.assign(cap.style, {position: "fixed", left: "50%", bottom: "24px", transform: "translateX(-50%)", background: "rgba(9,38,52,.92)",
        color: "#F9F9F9", padding: "12px 24px", borderRadius: "10px", font: "600 19px 'Noto Sans KR', sans-serif", zIndex: 2147483646,
        pointerEvents: "none", maxWidth: "86%", textAlign: "center", lineHeight: "1.45", whiteSpace: "pre-line", borderLeft: "5px solid #FF6E42"});
      const t = sessionStorage.getItem("__cap") || "";
      cap.textContent = t; cap.style.display = t ? "block" : "none";
      document.body.appendChild(cap);
      document.addEventListener("mousemove", e => { c.style.left = e.clientX + "px"; c.style.top = e.clientY + "px";
        sessionStorage.setItem("__cx", e.clientX); sessionStorage.setItem("__cy", e.clientY); }, true);
      document.addEventListener("mousedown", () => { c.style.transform = "scale(.65)"; }, true);
      document.addEventListener("mouseup", () => { c.style.transform = "scale(1)"; }, true);
    };
    if (document.readyState !== "loading") mk(); else document.addEventListener("DOMContentLoaded", mk);
  });
  const pg = await ctx.newPage();
  let rec = true, n = 0; const times = []; const t0 = Date.now();
  const loop = (async () => { while (rec) { const t = Date.now();
    try { await pg.screenshot({path: FR + String(t - t0).padStart(7, "0") + ".jpg", type: "jpeg", quality: 80, timeout: 3000}); n++; } catch (e) {}
    const d = Date.now() - t; if (d < 90) await new Promise(r => setTimeout(r, 90 - d)); } })();
  const wait = ms => pg.waitForTimeout(ms);
  const cap = async t => { await pg.evaluate(t => { sessionStorage.setItem("__cap", t); const c = document.getElementById("__cap");
    if (c) { c.textContent = t; c.style.display = t ? "block" : "none"; } }, t).catch(() => {}); };
  const settle = async () => { await pg.waitForLoadState("networkidle").catch(() => {}); await wait(700); };
  const go = async (path, t, ms = 2600) => { await cap(""); await pg.goto(B + path); await settle(); if (t) await cap(t); await wait(ms); };
  const move = async loc => { const b = await loc.boundingBox().catch(() => null); if (!b) return false;
    await pg.mouse.move(b.x + Math.min(b.width / 2, 120), b.y + b.height / 2, {steps: 28}); return true; };
  const point = async (sel, t, ms = 2300) => { const loc = pg.locator(sel).first(); if (!(await loc.count())) return false;
    await loc.scrollIntoViewIfNeeded().catch(() => {}); await wait(350); await move(loc); if (t) await cap(t); await wait(ms); return true; };
  const click = async (sel, t, ms = 2600) => { const loc = pg.locator(sel).first(); if (!(await loc.count())) return false;
    await loc.scrollIntoViewIfNeeded().catch(() => {}); await wait(300); await move(loc); await wait(350); await cap("");
    await Promise.all([pg.waitForLoadState("load").catch(() => {}), loc.click()]); await settle(); if (t) await cap(t); await wait(ms); return true; };
  const scroll = async (n = 3, step = 380, ms = 1500) => { for (let i = 0; i < n; i++) { await pg.mouse.wheel(0, step); await wait(ms); } };
  const href = async sel => pg.locator(sel).first().getAttribute("href").catch(() => null);

  // ---------- 로그인 ----------
  await pg.goto(B + "/login"); await settle();
  await cap(`${ACC[2]}으로 로그인합니다`); await wait(1800);
  await move(pg.locator("input[name=username]")); await pg.locator("input[name=username]").pressSequentially(ACC[0], {delay: 70});
  await move(pg.locator("input[name=password]")); await pg.locator("input[name=password]").pressSequentially(ACC[1], {delay: 60});
  await wait(500); await move(pg.locator("button[type=submit]").first());
  await Promise.all([pg.waitForURL(/\/(t|s)\//), pg.locator("button[type=submit]").first().click()]); await settle();

  if (ROLE === "student") {
    await go("/s/", "홈: 최근 7일 새로 온 것 · 공지 · 질답 · cast를 한 화면에"); await scroll(2);
    await go("/s/notices", "공지: 내 반 공지 (고정 · 과제 · 정오)");
    await click("main a[href*='/s/notices/']", "공지 상세: 읽음 표시 · 좋아요"); await scroll(1);
    await go("/s/questions", "질답 게시판: 학습질문은 닉네임으로 공개, 행정문의는 나만 보기");
    await point("text=자주 묻는 질문", "자주 묻는 질문: 선생님이 골라 둔 질문", 2000);
    await click("main a[href*='/s/questions/']:has-text('확신 없음')", "질문 상세: 내 필기가 담긴 문제 사진과 조교 답변 (맞혔지만 확신 없는 문항)"); await scroll(2);
    await go("/s/questions", "");
    await click("main a:has-text('질문 쓰기')", "질문 쓰기: 유형 · 단원 · 문제 사진(학습질문은 필수)");
    await point("#q-unit", "학습질문은 대단원을 고르면 조교가 단원별로 모아 봅니다", 2400);
    await go("/s/analysis?kind=review", "시험 분석: 복습 테스트 탭 (10문항 · 문항당 1점)");
    await point(".kind-tabs", "복습 테스트와 모의고사는 탭으로 나뉩니다", 2200);
    await point(".pick select", "다른 회차 보기: 이 탭의 회차만", 2000);
    await scroll(2, 360, 1600);
    await cap("내 답안 · 성적표: 내가 고른 답, 정답, 원점수, 반 평균, 예상 등급"); await wait(2400);
    await point("#h-paper", "복습 테스트 첨삭: 시험지 사진을 올리면 조교가 틀린 문항마다 첨삭", 2800); await scroll(2);
    await point("#h-wa", "오답 분석: 고른 선지로 틀린 이유를 짚어 줍니다", 2600); await scroll(3);
    await point("#h-cuts", "등급 기준표 · 문항 지도 (석차 · 백분위 · 점수대 분포는 학생에게 비공개)", 2800); await scroll(2);
    await go("/s/analysis?kind=mock", "모의고사 탭: Full 모의고사 25문항 50점");
    await point("#h-fb", "Full 모의고사 피드백: 풀이 사진으로 1:1 질문, 조교가 답합니다", 2800); await scroll(2);
    await go("/s/wrong", "오답 노트: 틀린 문항마다 이유 고르기 · 복습 표시"); await scroll(2);
    await go("/s/scores", "내 성적: 복습 테스트 득점률 그래프");
    const dots = pg.locator(".rc-hit");
    for (const i of [3, 8, 12]) { if (await dots.count() > i) { await move(dots.nth(i)); await cap("점에 마우스를 올리면 그 회차 점수 · 반 평균 · 날짜"); await wait(1500); } }
    await click(".kind-tabs a:has-text('모의고사')", "모의고사 탭으로 바꾸면 모의고사만"); await scroll(1);
    await go("/s/report", "내 리포트: 인쇄 · PDF로 저장 (복테와 모의고사 칸을 나눔)"); await scroll(3);
    await go("/s/feedback", "1:1 관리: 받은 복습 테스트 첨삭 · Full 모의고사 피드백 모아 보기");
    await go("/s/lessons", "수업 기록: 조교가 올린 판서 사진 (날짜별)"); await scroll(2);
    await go("/s/timetable", "시간표: 내 일정 · 수능 D-day · 휴강 안내");
    await go("/s/materials", "자료실: 반 자료");
    await go("/s/videos", "강의 영상: 보충 영상");
    await go("/cast", "태혁쌤의 cast: 주간 영상 메시지");
    await go("/s/games/", "수능 영단어: 날마다 단어 묶음");
    await go("/s/games/sci", "통과 Quiz: TOPIC별 개념 퀴즈"); await scroll(1);
    await go("/s/rooms", "소도시 명상: 집중 타이머 · 최근 4주 기록"); await scroll(2);
    await go("/s/my", "내 공부: 오늘 요약 · 주간 공부 순위 · 일별 이용 시간"); await scroll(2);
    await go("/s/attendance", "출결: 조교 시스템에서 불러온 출결");
    await go("/s/books/buy", "교재 구매: 교재별 구매 링크");
  } else {
    const T = ROLE === "teacher";
    await go("/t/", T ? "대시보드 (선생님): 오늘 할 일 · 최근 회차" : "대시보드 (조교): 답변 대기 · 복습 테스트 첨삭 · Full 모의고사 피드백"); await scroll(1);
    await go("/t/questions", "질문답변: 학습질문 · 학습상담 · 행정문의");
    await click("main a:has-text('변화와 다양성')", "단원 칩으로 거르기", 1800);
    await go("/t/questions?status=all", "");
    await click("main a[href*='/t/questions/']", "질문 상세: 학생 사진 · 답변 쓰기 · 자주 묻는 질문 고정"); await scroll(2);
    await go("/t/papers", "1:1 관리 > 복습 테스트 첨삭: 학생이 올린 시험지");
    await click("main a[href*='/t/papers/']", "시험지 사진과 틀린 문항 목록 (OMR 결과로 미리 표시)", 2600);
    await point("select", "문항마다 오답 유형 · 메모, 코멘트는 학생 화면과 학부모 리포트로", 2600); await scroll(2);
    await go("/t/feedback", "1:1 관리 > Full 모의고사 피드백: 대기 목록");
    await click("main a[href*='/t/feedback/']", "학생 풀이 사진과 대화, 틀린 문항 요약 → 글 · 사진으로 답변"); await scroll(2);
    await go("/t/lessons", "수업 기록: 반을 골라 판서 사진 올리기 · 반별 기록"); await scroll(1);
    await go("/t/books", "복테 · 모의고사: 1~50회, 결과가 올라온 회차");
    await click("main a.has[href*='/t/mocks/']", "회차 화면: 시험 평가 · OMR 엑셀 올리기 · 통계"); await scroll(4, 380, 1700);
    if (T) {
      const sms = await href("main a[href$='/sms']");
      if (sms) await go(sms, "학부모 문자: 학생별 분석 문자 + 학부모 리포트 링크", 3000);
    }
    await go("/t/classes", "반: 단과 4반 · 재종 4반");
    await click("main a[href*='/t/classes/']", "반 상세: 학생 탭 (가입 코드 · 계정 발급)"); await scroll(1);
    for (const [tab, t] of [["공지", T ? "공지 탭: 공지 쓰기 (여러 반에 같이)" : "공지 탭"], ["자료실", "자료실 탭"], ["강의 영상", "강의 영상 탭"]]) {
      await click(`nav.tabs a:has-text('${tab}')`, t, 2000);
    }
    await go("/t/students?q=박서윤", "학생 검색");
    const sd = await href("main a[href*='/t/students/']");
    await go(sd || "/t/students/1", "학생 상세: 성적 추이 (복습 테스트 / 모의고사 탭)"); await scroll(1);
    await click(".kind-tabs a:has-text('모의고사')", "모의고사 탭", 2000); await scroll(2);
    const plink = await pg.evaluate(() => (document.body.innerHTML.match(/\/p\/[\w-]{20,}/) || [null])[0]);
    if (plink && T) { await go(plink, "학부모 리포트: 로그인 없이 링크로 열림 (복테 / 모의고사 탭)"); await scroll(3); }
    await go((sd || "/t/students/1") + "/report", "성적 리포트: 인쇄 · PDF"); await scroll(2);
    await go("/cast", T ? "태혁쌤의 cast: 영상 메시지 쓰기" : "태혁쌤의 cast");
    await go("/t/timetable", "주요 일정: 수능 D-day · 휴강 입력 (반별 · 시작 3주 전부터 학생 시간표에)"); await scroll(1);
    await go("/t/rooms", "소도시 명상 현황: 반별 집중 시간");
    await go("/t/link", "조교 시스템 연동: 출결 · 공부 유형 · 성적 CSV");
    await go("/t/signups", "가입 승인");
    await go("/t/audit", "접근 기록: 누가 어떤 학생 정보를 봤는지");
    if (T) { await go("/t/staff", "조교 계정 (선생님만): 조교 추가 · 월별 답변 · 첨삭 건수"); await scroll(1); }
  }
  await cap("끝"); await wait(1500);
  rec = false; await loop;
  await ctx.close();
  return `frames ${n}, ${Math.round((Date.now() - t0) / 1000)}s`;
}
