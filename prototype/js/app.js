/* 정태혁 통합과학 연구소 — 강사 화면 시안.
   CSP를 지키기 위해 인라인 스크립트·style 속성을 쓰지 않는다(크기는 CSSOM으로만 지정). */
(function () {
  'use strict';
  const L = window.LAB;
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const nf1 = new Intl.NumberFormat('ko-KR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const nf0 = new Intl.NumberFormat('ko-KR');
  const MINUS = '−';
  const sign1 = (v) => (v > 0 ? '+' : v < 0 ? MINUS : '') + nf1.format(Math.abs(v));
  const sign0 = (v) => (v > 0 ? '+' : v < 0 ? MINUS : '') + nf0.format(Math.abs(v));
  const fmtDate = (d) => { const [, m, dd] = d.split('-'); return `${Number(m)}월 ${Number(dd)}일`; };
  const LAST = L.EXAMS.length - 1;
  const waiting = () => L.questions.filter((q) => q.status === '대기');
  const qByClass = (cid) => waiting().filter((q) => q.classId === cid || L.byId[q.studentId].classId === cid).length;

  /* ---------- 설정(시안 선택)은 이 브라우저에만 저장 ---------- */
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 저장 불가: 무시 */ } },
  };
  const root = document.documentElement;
  const params = new URLSearchParams(location.search);
  root.dataset.palette = params.get('palette') || store.get('lab.palette') || 'matsu';
  root.dataset.type = params.get('type') || store.get('lab.type') || 't1';
  const picker = $('[data-picker]');
  picker.palette.value = root.dataset.palette;
  picker.type.value = root.dataset.type;
  picker.addEventListener('change', (e) => {
    const { name, value } = e.target;
    root.dataset[name] = value;
    store.set('lab.' + name, value);
  });

  /* ---------- 메뉴 ---------- */
  const NAV = [
    { group: null, items: [['#/', '대시보드', 'home']] },
    { group: '수업', items: [['#/class/K', '반 관리', 'class'], ['#/students', '학생 관리', 'students'], ['#/exams/K', '시험·성적', 'exams'], ['#/qna', '질문답변', 'qna', () => waiting().length]] },
    { group: '게시', items: [['#/notices', '공지', 'notices'], ['#/files', '자료실', 'files'], ['#/videos', '강의 영상', 'videos'], ['#/news', '교육 뉴스', 'news']] },
    { group: '관리', items: [['#/signups', '가입 승인', 'signups', () => L.signupsPending], ['#/assistants', '조교 계정', 'assistants'], ['#/audit', '접근 기록', 'audit']] },
  ];
  function renderNav(active) {
    const html = NAV.map((g) => `<div class="nav-group">${g.group ? `<div class="nav-label">${g.group}</div>` : ''}${g.items.map(([href, label, key, count]) => {
      const c = count ? count() : 0;
      return `<a href="${href}"${key === active ? ' aria-current="page"' : ''}><span>${label}</span>${c ? `<span class="count num" aria-label="${c}건">${c}</span>` : ''}</a>`;
    }).join('')}</div>`).join('');
    $$('[data-nav]').forEach((n) => { n.innerHTML = html; });
  }
  const mnav = $('[data-mnav]');
  $('[data-open-nav]').addEventListener('click', () => mnav.showModal());
  $('[data-close-nav]').addEventListener('click', () => mnav.close());
  mnav.addEventListener('click', (e) => { if (e.target.closest('a')) mnav.close(); });

  /* ---------- 학생 검색 ---------- */
  const search = $('[data-search]');
  const results = $('[data-results]');
  let hit = 0;
  function findStudents(q) {
    q = q.trim();
    if (!q) return [];
    return L.students.filter((s) => s.name.includes(q) || s.examNo.startsWith(q)).slice(0, 6);
  }
  function showResults() {
    const list = findStudents(search.value);
    if (!search.value.trim()) { results.hidden = true; return; }
    hit = Math.min(hit, Math.max(0, list.length - 1));
    results.innerHTML = list.length
      ? list.map((s, i) => `<a href="#/student/${s.id}"${i === hit ? ' class="on"' : ''}><span class="chip-el">${s.classId}</span><span>${esc(s.name)} <small>${esc(s.nick)}</small></span><small class="num">${s.examNo}</small></a>`).join('')
      : `<p>‘${esc(search.value.trim())}’에 맞는 학생이 없습니다. 이름 일부나 수험번호 앞자리로 찾아보세요.</p>`;
    results.hidden = false;
  }
  search.addEventListener('input', () => { hit = 0; showResults(); });
  search.addEventListener('keydown', (e) => {
    const items = $$('a', results);
    if (e.key === 'ArrowDown') { hit = Math.min(items.length - 1, hit + 1); showResults(); e.preventDefault(); }
    if (e.key === 'ArrowUp') { hit = Math.max(0, hit - 1); showResults(); e.preventDefault(); }
    if (e.key === 'Enter' && items[hit]) { location.hash = items[hit].getAttribute('href'); clear(); }
    if (e.key === 'Escape') clear();
  });
  function clear() { search.value = ''; results.hidden = true; search.blur(); }
  results.addEventListener('click', (e) => { if (e.target.closest('a')) clear(); });
  document.addEventListener('click', (e) => { if (!e.target.closest('.search')) results.hidden = true; });
  document.addEventListener('keydown', (e) => {
    if (e.key === '/' && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) { e.preventDefault(); search.focus(); }
  });
  $('[data-msearch]').addEventListener('keydown', (e) => {
    if (e.key !== 'Enter') return;
    const s = findStudents(e.target.value)[0];
    if (s) { location.hash = `#/student/${s.id}`; mnav.close(); e.target.value = ''; }
  });

  /* ---------- 공통 조각 ---------- */
  const elCell = (c, opts = {}) => {
    const q = qByClass(c.id);
    const drop = c.delta <= -2;
    return `<a class="el${drop ? ' warn' : ''}${opts.big ? ' el-big' : ''}" data-cid="${c.id}" href="#/class/${c.id}" aria-label="${c.name}, 학생 ${c.studentIds.length}명, 8회 평균 ${nf1.format(c.last)}점, 7회보다 ${sign1(c.delta)}점${q ? `, 답변 대기 ${q}건` : ''}">
      <span class="el-top"><span class="num">${c.order}</span>${q ? `<span class="el-q num">${q}</span>` : ''}</span>
      <span class="el-sym">${c.letter}</span>
      <span class="el-name num">학생 ${c.studentIds.length}명</span>
      <span class="el-avg num">${nf1.format(c.last)}<small class="${drop ? 'neg' : ''}">${sign1(c.delta)}</small></span>
    </a>`;
  };
  const who = (s) => `${esc(s.nick)} <span class="dot">·</span> ${esc(s.name)} <span class="chip-el" aria-label="${s.classId}반">${s.classId}</span>`;
  const isOld = (q) => /일 전/.test(q.ago) && parseInt(q.ago, 10) >= 2;
  const placeholder = (title, line) => `
    <div class="title-row"><div><h1>${title}</h1><p class="lede">${line}</p></div></div>
    <div class="empty"><b>이 화면은 다음 시안에서 만듭니다.</b><span>이번 시안은 대시보드, 반 상세, 학생 상세, 시험·성적 입력, 질문답변 다섯 화면입니다.</span><a class="btn btn-sm" href="#/">대시보드로 돌아가기</a></div>`;


  /* 원소 칸에 올리면 보이는 반 상세 띠: 1–8회 평균 추이, 답변 대기, 가장 많이 떨어진 학생 */
  function elDetail(c) {
    const q = qByClass(c.id);
    const studs = c.studentIds.map((id) => L.byId[id]).filter((s) => s.scores[LAST] != null && s.scores[LAST - 1] != null);
    const worstS = studs.sort((a, b) => (a.scores[LAST] - a.scores[LAST - 1]) - (b.scores[LAST] - b.scores[LAST - 1]))[0];
    const W = 220, H = 56, lo = 20, hi = 40;
    const pts = c.avgs.map((v, i) => `${(i * (W - 4) / (c.avgs.length - 1) + 2).toFixed(1)},${(H - 14 - ((v - lo) / (hi - lo)) * (H - 20)).toFixed(1)}`).join(' ');
    return `<span class="sym" aria-hidden="true">${c.letter}</span>
      <div><h3>${c.name} · 학생 ${c.studentIds.length}명</h3>
        <p class="num">8회 평균 <b>${nf1.format(c.last)}</b> (7회 대비 <span class="${c.delta <= -2 ? 'neg' : ''}">${sign1(c.delta)}</span>) · 답변 대기 <b>${q}건</b></p>
        <p>가장 많이 떨어진 학생 <a href="#/student/${worstS.id}"><b>${esc(worstS.name)}</b></a> <span class="num neg">${sign0(worstS.scores[LAST] - worstS.scores[LAST - 1])}점</span></p></div>
      <div class="spark-wrap"><svg class="spark" viewBox="0 0 ${W} ${H}" role="img" aria-label="${c.name} 1–8회 평균 추이"><line class="b" x1="0" x2="${W}" y1="${H - 12}" y2="${H - 12}"/><polyline class="t" points="${pts}"/><text x="0" y="${H}">1회</text><text x="${W}" y="${H}" text-anchor="end">8회</text></svg></div>`;
  }
  function bindDash() {
    const box = $('[data-eldetail]');
    const show = (a) => { $$('[data-cid]').forEach((x) => x.classList.toggle('on', x === a)); box.innerHTML = elDetail(L.classById[a.dataset.cid]); };
    $$('[data-cid]').forEach((a) => { a.addEventListener('mouseenter', () => show(a)); a.addEventListener('focus', () => show(a)); });
  }

  /* ---------- 대시보드 ---------- */
  function dashboard() {
    const w = waiting().sort((a, b) => a.at.localeCompare(b.at));
    const oldest = w[0];
    const worst = [...L.classes].sort((a, b) => a.delta - b.delta)[0];
    const lastExam = L.EXAMS[LAST];
    const recent = [...L.classes].sort((a, b) => b.last - a.last).slice(0, 3);
    return `
    <div class="title-row">
      <div>
        <h1>대시보드</h1>
        <p class="lede">답변 대기 질문 <b class="num">${w.length}건</b>, 가장 오래된 질문은 ${esc(oldest.ago)} · ${worst.name} 8회 평균이 7회보다 <b class="num neg">${sign1(worst.delta)}점</b></p>
      </div>
      <div class="actions"><a class="btn btn-primary" href="#/qna/${oldest.id}">가장 오래된 질문 답하기</a></div>
    </div>

    <dl class="kpis">
      <div class="kpi"><dt>답변 대기</dt><dd class="num">${w.length}<small>건</small></dd><p>학습 ${w.filter((q) => q.type === '학습').length} · 행정 ${w.filter((q) => q.type === '행정').length}</p></div>
      <div class="kpi"><dt>재원 학생</dt><dd class="num">${nf0.format(L.totalStudents)}<small>명</small></dd><p>가입 승인 대기 ${L.signupsPending}명</p></div>
      <div class="kpi"><dt>담당 반</dt><dd class="num">${L.classes.length}<small>개</small></dd><p>A–K, P</p></div>
      <div class="kpi"><dt>등록한 시험</dt><dd class="num">${L.totalExams}<small>개</small></dd><p>반마다 주간 테스트 ${L.EXAMS.length}회</p></div>
    </dl>

    <div class="board">
      <div class="stack">
        <section class="card" aria-labelledby="h-classes">
          <div class="card-head"><h2 id="h-classes">담당 반</h2><span class="meta">${lastExam.name} 평균 · ${lastExam.full}점 만점</span></div>
          <div class="ptable" data-ptable>${L.classes.map((c) => elCell(c)).join('')}</div>
          <div class="el-detail" data-eldetail aria-live="polite">${elDetail(worst)}</div>
          <div class="key"><span><i></i>답변 대기 질문</span><span>오른쪽 아래: 7회 대비 평균 변화</span><span>테두리가 붉은 칸: 2점 넘게 떨어진 반</span></div>
        </section>
        <section class="card" aria-labelledby="h-q">
          <div class="card-head"><h2 id="h-q">답변 대기 질문</h2><a class="meta" href="#/qna">전체 ${w.length}건 보기</a></div>
          <ul class="qlist">${w.slice(0, 5).map((q) => {
            const s = L.byId[q.studentId];
            return `<li class="qrow">
              <div>
                <div class="qt">${q.type === '행정' ? '<span class="pill warn">행정문의</span>' : ''}<b class="num">${esc(q.title)}</b><span>${esc(q.body)}</span></div>
                <div class="qsub">${who(s)}${q.asks > 1 ? `<span class="dot">·</span><span>추가 질문 ${q.asks - 1}회</span>` : ''}</div>
              </div>
              <span class="qage${isOld(q) ? ' old' : ''}">${esc(q.ago)}</span>
              <a class="btn btn-sm" href="#/qna/${q.id}">답하기</a>
            </li>`;
          }).join('')}</ul>
        </section>
      </div>

      <aside class="rail" aria-label="보조 정보">
        <section>
          <h2>점수가 크게 떨어진 학생</h2>
          <div class="card"><ul class="rows">${L.drops.map(({ id, d }) => {
            const s = L.byId[id];
            return `<li><a class="two" href="#/student/${s.id}"><b>${esc(s.name)} <span class="chip-el">${s.classId}</span></b><small>${s.examNo}</small></a><span class="fig num"><span class="neg">${sign0(d)}점</span><small>7회 ${s.scores[LAST - 1]} → 8회 ${s.scores[LAST]}</small></span></li>`;
          }).join('')}</ul></div>
        </section>
        <section>
          <h2>8회 평균이 높은 반</h2>
          <div class="card"><ul class="rows">${recent.map((c) => {
            const st = L.stats(c.studentIds.map((id) => L.byId[id].scores[LAST]));
            return `<li><a class="two" href="#/class/${c.id}"><b>${c.name}</b><small>응시 ${st.n}명 · ${fmtDate(lastExam.date)}</small></a><span class="fig num">${nf1.format(c.last)}<small>최고 ${st.max} · 최저 ${st.min}</small></span></li>`;
          }).join('')}</ul>
          <a class="more" href="#/exams/K">시험·성적으로 가기</a></div>
        </section>
      </aside>
    </div>`;
  }

  /* ---------- 반 상세(학생 탭) ---------- */
  function classView(cid) {
    const c = L.classById[cid] || L.classById.K;
    const studs = c.studentIds.map((id) => L.byId[id]);
    const q = qByClass(c.id);
    return `
    <a class="back" href="#/"><svg class="i" viewBox="0 0 16 16"><path d="M10 3.5 5.5 8l4.5 4.5"/></svg>반 관리</a>
    <div class="class-head">
      <div class="el el-big" aria-hidden="true"><span class="el-top"><span class="num">${c.order}</span>${q ? `<span class="el-q num">${q}</span>` : ''}</span><span class="el-sym">${c.letter}</span><span></span><span></span></div>
      <div>
        <h1 class="title-like">${c.name}</h1>
        <p class="lede">${esc(c.desc)} · 가입 코드 <b class="num">${c.code}</b> (가입 받는 중)</p>
        <div class="facts">
          <span>재원 학생<b class="num">${studs.length}명</b></span>
          <span>8회 평균<b class="num">${nf1.format(c.last)}<span class="${c.delta <= -2 ? 'neg' : 'muted'}"> ${sign1(c.delta)}</span></b></span>
          <span>답변 대기<b class="num">${q}건</b></span>
        </div>
      </div>
      <div class="actions"><button class="btn" type="button">CSV 일괄 등록</button><button class="btn btn-primary" type="button">학생 등록</button></div>
    </div>
    <nav class="tabs" aria-label="반 메뉴">
      <a href="#/class/${c.id}" aria-current="page">학생<span class="count num">${studs.length}</span></a>
      <a href="#/exams/${c.id}">시험·성적<span class="count num">${L.EXAMS.length}</span></a>
      <a href="#/notices">공지</a><a href="#/files">자료실</a><a href="#/videos">강의 영상</a>
    </nav>
    <div class="toolbar">
      <label><span class="sr">이 반에서 학생 찾기</span><input class="input" type="search" placeholder="이 반에서 이름·수험번호 찾기" data-filter></label>
      <span class="muted num" data-count>${studs.length}명 · 8회 점수 낮은 순</span>
    </div>
    <div class="tbl-wrap"><table class="tbl" data-table>
      <thead><tr><th>이름</th><th class="hide-sm">수험번호</th><th class="r">8회 점수</th><th class="r hide-sm">반 평균 대비</th><th class="r hide-sm">누적 접속</th><th class="r hide-sm">포인트</th><th class="hide-sm">계정</th></tr></thead>
      <tbody>${studs.map((s) => ({ s, v: s.scores[LAST] })).sort((a, b) => (a.v ?? -1) - (b.v ?? -1)).map(({ s, v }) => `
        <tr data-name="${esc(s.name)}" data-no="${s.examNo}">
          <td class="id"><a href="#/student/${s.id}">${esc(s.name)}</a><small>${esc(s.nick)}</small><span class="sm-only num">${s.examNo} · 반 평균 대비 ${v == null ? '—' : sign1(v - c.last)} · 접속 ${s.days}일 · ${nf0.format(s.points)}P${s.account === '미발급' ? ' · 계정 미발급' : ''}</span></td>
          <td class="num hide-sm">${s.examNo}</td>
          <td class="r num">${v == null ? '<span class="dash">결시</span>' : `${v}<span class="unit"> /${L.FULL}</span>`}</td>
          <td class="r num hide-sm">${v == null ? '<span class="dash">—</span>' : `<span class="${v - c.last <= -10 ? 'neg' : ''}">${sign1(v - c.last)}</span>`}</td>
          <td class="r num hide-sm">${s.days}<span class="unit">일</span></td>
          <td class="r num hide-sm">${nf0.format(s.points)}<span class="unit">P</span></td>
          <td class="hide-sm">${s.account === '미발급' ? '<span class="pill warn">계정 미발급</span>' : '<span class="pill">사용 중</span>'}</td>
        </tr>`).join('')}</tbody>
    </table></div>
    <div class="pager"><span class="num">1–${studs.length} / ${studs.length}명</span><span>50명씩 보기</span></div>`;
  }
  function bindClass() {
    const f = $('[data-filter]');
    if (!f) return;
    f.addEventListener('input', () => {
      const q = f.value.trim();
      let n = 0;
      $$('[data-table] tbody tr').forEach((tr) => { const on = !q || tr.dataset.name.includes(q) || tr.dataset.no.startsWith(q); tr.hidden = !on; if (on) n++; });
      $('[data-count]').textContent = q ? `${n}명 찾음` : `${n}명 · 8회 점수 낮은 순`;
    });
  }

  /* ---------- 학생 상세 ---------- */
  function studentView(id) {
    const s = L.byId[id] || L.featured;
    const c = L.classById[s.classId];
    const last = s.scores[LAST], prev = s.scores[LAST - 1];
    const rank = L.rankIn(c, LAST, s.id);
    const qs = L.questions.filter((q) => q.studentId === s.id);
    return `
    <div class="title-row">
      <div>
        <div class="crumb"><a href="#/class/${c.id}">${c.name}</a><span class="sep">/</span><h1>${esc(s.name)}</h1></div>
        <div class="meta-line"><span class="chip-el">${c.letter}</span><span class="num">수험번호 ${s.examNo}</span><span>닉네임 ${esc(s.nick)}</span>
          <span class="secret">연락처 <span class="num" data-phone>010-••••-••••</span><button class="btn btn-text btn-sm" type="button" data-reveal>보기</button></span></div>
      </div>
      <div class="actions">
        <button class="btn" type="button">정보 수정</button>
        <button class="btn" type="button">반 이동</button>
        <div class="menu"><button class="btn icon-btn" type="button" aria-label="더 보기" aria-expanded="false" data-more><svg class="i" viewBox="0 0 16 16"><circle cx="3.5" cy="8" r=".75"/><circle cx="8" cy="8" r=".75"/><circle cx="12.5" cy="8" r=".75"/></svg></button>
          <div class="menu-pop" hidden data-more-pop><button type="button">비밀번호 초기화</button><button type="button">포인트 지급</button><hr><button type="button" class="btn-danger">퇴원 처리</button><button type="button" class="btn-danger">영구 삭제…</button></div></div>
      </div>
    </div>

    <dl class="kpis k5">
      <div class="kpi"><dt>8회 점수</dt><dd class="num lead">${last ?? '—'}<small>/${L.FULL}</small></dd><p class="num">7회 ${prev ?? '—'}점에서 <span class="${last - prev < 0 ? 'neg' : ''}">${last != null && prev != null ? sign0(last - prev) : '—'}</span></p></div>
      <div class="kpi"><dt>반 평균 대비</dt><dd class="num">${last == null ? '—' : sign1(last - c.last)}<small>점</small></dd><p class="num">${c.name} 8회 평균 ${nf1.format(c.last)}</p></div>
      <div class="kpi"><dt>반 석차</dt><dd class="num">${rank ?? '—'}<small>/ ${c.studentIds.length}</small></dd><p>8회 기준, 동점은 같은 석차</p></div>
      <div class="kpi"><dt>누적 접속</dt><dd class="num">${s.days}<small>일</small></dd><p class="num">연속 ${s.streak}일</p></div>
      <div class="kpi"><dt>보유 포인트</dt><dd class="num">${nf0.format(s.points)}<small>P</small></dd><p>하루 첫 접속 +10P</p></div>
    </dl>

    <div class="detail">
      <div class="stack">
        <section class="card" aria-labelledby="h-trend">
          <div class="card-head"><h2 id="h-trend">성적 추이</h2><div class="legend"><span><i></i>${esc(s.name)}</span><span><i class="avg"></i>${c.name} 평균</span></div></div>
          <svg class="chart" data-chart role="img" aria-label="${esc(s.name)}의 주간 테스트 1–8회 점수와 ${c.name} 평균"></svg>
        </section>
        <section class="card" aria-labelledby="h-rec">
          <div class="card-head"><h2 id="h-rec">시험 기록</h2><span class="meta">${L.FULL}점 만점</span></div>
          <div class="tbl-wrap"><table class="tbl">
            <thead><tr><th>시험</th><th class="hide-sm">날짜</th><th class="r">점수</th><th class="r hide-sm">득점률</th><th class="r">반 평균</th><th class="r">석차</th></tr></thead>
            <tbody>${L.EXAMS.map((e, i) => ({ e, i })).reverse().map(({ e, i }) => { const v = s.scores[i]; const r = L.rankIn(c, i, s.id); return `
              <tr><td>${e.name}</td><td class="num hide-sm">${e.date}</td>
              <td class="r num">${v == null ? '<span class="dash">결시</span>' : v}</td>
              <td class="r num hide-sm">${v == null ? '<span class="dash">—</span>' : nf1.format((v / e.full) * 100) + '<span class="unit">%</span>'}</td>
              <td class="r num">${nf1.format(c.avgs[i])}</td>
              <td class="r num">${r == null ? '<span class="dash">—</span>' : `${r}<span class="unit"> /${c.studentIds.length}</span>`}</td></tr>`; }).join('')}</tbody>
          </table></div>
        </section>
      </div>
      <aside class="rail">
        <section>
          <h2>학습·상담 메모</h2>
          <div class="card">
            <form class="memo-form" data-memo>
              <label class="sr" for="memo">새 메모</label>
              <textarea class="input" id="memo" name="memo" placeholder="상담 내용이나 학습 관찰을 적어 두세요" required></textarea>
              <div class="row"><select class="select" name="kind" aria-label="메모 분류"><option>상담</option><option>학습</option><option>생활</option></select><button class="btn btn-primary" type="submit">메모 저장</button></div>
            </form>
            <ul class="memo-list" data-memos>${L.memos.map(memoItem).join('')}</ul>
          </div>
        </section>
        <section>
          <h2>질문 기록</h2>
          <div class="card">${qs.length ? `<ul class="rows">${qs.map((q) => `<li><a class="two" href="#/qna/${q.id}"><b class="num">${esc(q.title)}</b><small>${esc(q.at)}</small></a><span class="pill ${q.status === '대기' ? 'acc' : ''}">${q.status === '대기' ? '답변 대기' : '답변 완료'}</span></li>`).join('')}</ul>`
            : '<p class="muted">아직 올린 질문이 없습니다.</p>'}</div>
        </section>
      </aside>
    </div>`;
  }
  function memoItem(m) { return `<li><div class="memo-head"><span class="pill">${esc(m.kind)}</span><span class="num">${esc(m.at)}</span></div><p>${esc(m.text)}</p></li>`; }
  function bindStudent(id) {
    const s = L.byId[id] || L.featured;
    const c = L.classById[s.classId];
    drawTrend($('[data-chart]'), s.scores, c.avgs);
    const more = $('[data-more]');
    const pop = $('[data-more-pop]');
    more.addEventListener('click', () => { pop.hidden = !pop.hidden; more.setAttribute('aria-expanded', String(!pop.hidden)); });
    document.addEventListener('click', (e) => { if (!e.target.closest('.menu')) { pop.hidden = true; more.setAttribute('aria-expanded', 'false'); } });
    $('[data-reveal]').addEventListener('click', (e) => {
      $('[data-phone]').textContent = '010-4821-73' + s.examNo.slice(-2);
      e.target.remove();
    });
    $('[data-memo]').addEventListener('submit', (e) => {
      e.preventDefault();
      const f = e.target;
      L.memos.unshift({ kind: f.kind.value, at: L.TODAY, text: f.memo.value.trim() });
      $('[data-memos]').innerHTML = L.memos.map(memoItem).join('');
      f.reset();
    });
  }

  /* 성적 추이: 한 학생 선(강조색)과 반 평균 선(회색). 0–50점 고정 눈금 */
  function drawTrend(svg, mine, avgs) {
    const NS = 'http://www.w3.org/2000/svg';
    const W = Math.max(280, svg.clientWidth || 600), H = 210, pl = 28, pr = 74, pt = 22, pb = 26;
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    svg.innerHTML = '';
    const add = (tag, attrs, txt) => { const n = document.createElementNS(NS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); if (txt != null) n.textContent = txt; svg.appendChild(n); return n; };
    const n = mine.length;
    const x = (i) => pl + (i * (W - pl - pr)) / (n - 1);
    const y = (v) => pt + (1 - v / L.FULL) * (H - pt - pb);
    [0, 10, 20, 30, 40, 50].forEach((t) => {
      add('line', { x1: pl, x2: W - pr, y1: y(t), y2: y(t), class: t === 0 ? 'base' : 'grid' });
      add('text', { x: pl - 8, y: y(t) + 4, 'text-anchor': 'end', class: 'tick num' }, t);
    });
    const step = W < 420 ? 2 : 1;
    for (let i = 0; i < n; i += step) add('text', { x: x(i), y: H - 6, 'text-anchor': i === 0 ? 'start' : 'middle', class: 'tick' }, `${i + 1}회`);
    const path = (vals) => vals.map((v, i) => (v == null ? null : [x(i), y(v)])).reduce((d, p, i, arr) => (p ? d + `${d && arr[i - 1] ? 'L' : 'M'}${p[0].toFixed(1)},${p[1].toFixed(1)}` : d), '');
    add('path', { d: path(avgs), class: 'l-avg' });
    add('path', { d: path(mine), class: 'l-me' });
    mine.forEach((v, i) => { if (v == null) add('text', { x: x(i), y: y(avgs[i]) - 10, 'text-anchor': 'middle', class: 'gap' }, '결시'); });
    const li = n - 1;
    // 끝 값 표시: 두 값이 14px 안에 붙으면 위쪽 값은 위로, 아래쪽 값은 아래로 벌린다
    let ym = mine[li] != null ? y(mine[li]) + 4 : null, ya = y(avgs[li]) + 4;
    if (ym != null && Math.abs(ym - ya) < 15) { const mid = (ym + ya) / 2; if (mine[li] >= avgs[li]) { ym = mid - 8; ya = mid + 8; } else { ym = mid + 8; ya = mid - 8; } }
    if (mine[li] != null) { add('circle', { cx: x(li), cy: y(mine[li]), r: 3.5, class: 'dot' }); add('text', { x: x(li) + 8, y: ym, class: 'end num' }, `${mine[li]}점`); }
    add('text', { x: x(li) + 8, y: ya, class: 'end a num' }, `평균 ${nf1.format(avgs[li])}`);
    const d = mine[li] != null && mine[li - 1] != null ? mine[li] - mine[li - 1] : 0;
    if (d <= -5) {
      const mx = (x(li) + x(li - 1)) / 2;
      add('line', { x1: mx, x2: mx, y1: pt - 6, y2: Math.min(y(mine[li - 1]), y(mine[li])) - 6, class: 'annl' });
      add('text', { x: mx, y: pt - 10, 'text-anchor': 'middle', class: 'ann num' }, `8회 ${sign0(d)}점`);
    }
  }

  /* ---------- 시험·성적 입력 ---------- */
  function examView(cid) {
    const c = L.classById[cid] || L.classById.K;
    const studs = c.studentIds.map((id) => L.byId[id]);
    // 9회(오늘) 점수를 입력하는 중: 앞쪽 일부만 입력된 상태로 시작
    if (!c.draft) c.draft = studs.map((s, i) => (i < Math.round(studs.length * 0.66) && s.scores[LAST] != null ? Math.max(0, Math.min(L.FULL, s.scores[LAST] + ((i * 7) % 9) - 3)) : ''));
    return `
    <div class="title-row">
      <div>
        <div class="crumb"><a href="#/class/${c.id}">${c.name}</a><span class="sep">/</span><h1>주간 테스트 9회 점수 입력</h1></div>
        <p class="lede num">통합과학 · ${fmtDate(L.TODAY)} · ${L.FULL}점 만점 · 점수를 넣고 Enter를 누르면 다음 학생으로 넘어갑니다</p>
      </div>
      <div class="actions"><button class="btn" type="button">CSV 내보내기</button><button class="btn btn-primary" type="button" data-save>저장</button></div>
    </div>
    <dl class="kpis k5" data-stats></dl>
    <div class="toolbar"><span class="save-stamp" data-stamp>자동 저장 안 됨 · 저장을 눌러야 반영됩니다</span><span class="muted">수험번호 순</span></div>
    <div class="tbl-wrap"><table class="tbl exam">
      <colgroup><col class="c-rank"><col class="c-name"><col class="c-no"><col class="c-score"><col class="c-rate"><col class="c-prev"></colgroup>
      <thead><tr><th class="r">석차</th><th>이름</th><th class="hide-sm">수험번호</th><th class="l-score">점수</th><th class="r hide-sm">득점률</th><th class="r hide-sm">지난 8회</th></tr></thead>
      <tbody>${studs.map((s, i) => `
        <tr data-i="${i}">
          <td class="r num" data-rank><span class="dash">—</span></td>
          <td class="id"><a href="#/student/${s.id}">${esc(s.name)}</a></td>
          <td class="num hide-sm">${s.examNo}</td>
          <td class="l-score"><label class="sr" for="sc${i}">${esc(s.name)} 점수</label><input class="score-in num" id="sc${i}" inputmode="numeric" autocomplete="off" value="${c.draft[i]}" data-score="${i}"><span class="err" data-err hidden></span></td>
          <td class="r num hide-sm" data-rate><span class="dash">—</span></td>
          <td class="r num hide-sm">${s.scores[LAST] ?? '<span class="dash">결시</span>'}</td>
        </tr>`).join('')}</tbody>
    </table></div>`;
  }
  function bindExam(cid) {
    const c = L.classById[cid] || L.classById.K;
    const inputs = $$('[data-score]');
    const valid = (v) => v === '' || (/^\d{1,2}$/.test(v) && Number(v) <= L.FULL);
    function recompute() {
      const vals = c.draft.map((v) => (v === '' || !valid(String(v)) ? null : Number(v)));
      const st = L.stats(vals);
      $('[data-stats]').innerHTML = `
        <div class="kpi"><dt>입력</dt><dd class="num">${st.n}<small>/ ${vals.length}명</small></dd><p>남은 학생 ${vals.length - st.n}명</p></div>
        <div class="kpi"><dt>평균</dt><dd class="num">${st.n ? nf1.format(st.avg) : '—'}</dd><p class="num">8회 반 평균 ${nf1.format(c.last)}</p></div>
        <div class="kpi"><dt>표준편차</dt><dd class="num">${st.n ? nf1.format(st.sd) : '—'}</dd><p>입력한 점수 기준</p></div>
        <div class="kpi"><dt>최고</dt><dd class="num">${st.n ? st.max : '—'}</dd><p>${L.FULL}점 만점</p></div>
        <div class="kpi"><dt>최저</dt><dd class="num">${st.n ? st.min : '—'}</dd><p>&nbsp;</p></div>`;
      $$('tbody tr[data-i]').forEach((tr) => {
        const i = Number(tr.dataset.i), v = vals[i];
        const r = v == null ? null : vals.filter((x) => x != null && x > v).length + 1;
        $('[data-rank]', tr).innerHTML = r == null ? '<span class="dash">—</span>' : `${r}`;
        $('[data-rate]', tr).innerHTML = v == null ? '<span class="dash">—</span>' : `${nf1.format((v / L.FULL) * 100)}<span class="unit">%</span>`;
      });
    }
    inputs.forEach((inp) => {
      const i = Number(inp.dataset.score);
      const mark = () => {
        const ok = valid(inp.value.trim());
        inp.classList.toggle('bad', !ok);
        inp.classList.toggle('filled', ok && inp.value.trim() !== '');
        const err = inp.nextElementSibling;
        err.hidden = ok;
        err.textContent = ok ? '' : `0–${L.FULL} 사이 숫자`;
        inp.setAttribute('aria-invalid', String(!ok));
      };
      mark();
      inp.addEventListener('input', () => { c.draft[i] = inp.value.trim(); mark(); recompute(); $('[data-stamp]').textContent = '저장하지 않은 변경이 있습니다'; });
      inp.addEventListener('focus', () => { inp.closest('tr').classList.add('cur'); inp.select(); });
      inp.addEventListener('blur', () => inp.closest('tr').classList.remove('cur'));
      inp.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === 'ArrowDown') { e.preventDefault(); inputs[Math.min(inputs.length - 1, i + 1)].focus(); }
        if (e.key === 'ArrowUp') { e.preventDefault(); inputs[Math.max(0, i - 1)].focus(); }
      });
    });
    $('[data-save]').addEventListener('click', () => {
      const bad = inputs.find((x) => x.classList.contains('bad'));
      if (bad) { bad.focus(); $('[data-stamp]').textContent = '잘못 입력한 칸이 있어 저장하지 않았습니다'; return; }
      const t = new Date();
      $('[data-stamp]').textContent = `저장했습니다 · ${String(t.getHours()).padStart(2, '0')}:${String(t.getMinutes()).padStart(2, '0')}`;
    });
    recompute();
  }

  /* ---------- 질문답변 ---------- */
  let qFilter = { status: '대기', type: '전체' };
  function qnaView(qid) {
    const list = L.questions.filter((q) => (qFilter.status === '전체' || q.status === qFilter.status) && (qFilter.type === '전체' || q.type === qFilter.type))
      .sort((a, b) => (qFilter.status === '대기' ? a.at.localeCompare(b.at) : b.at.localeCompare(a.at)));
    const cur = L.questions.find((q) => q.id === qid) || list[0];
    const n = (st) => L.questions.filter((q) => st === '전체' || q.status === st).length;
    const s = cur ? L.byId[cur.studentId] : null;
    return `
    <div class="title-row"><div><h1>질문답변</h1><p class="lede">오래된 질문부터 · 답변을 등록하면 다음 대기 질문으로 넘어갑니다</p></div></div>
    <div class="inbox" data-pane="${qid ? 'detail' : 'list'}">
      <div class="inbox-list">
        <nav class="tabs" aria-label="상태">${['대기', '완료', '전체'].map((st) => `<a href="#/qna" data-status="${st}"${qFilter.status === st ? ' aria-current="page"' : ''}>${st === '대기' ? '답변 대기' : st === '완료' ? '답변 완료' : '전체'}<span class="count num">${n(st)}</span></a>`).join('')}</nav>
        <div class="inbox-filter"><label class="sr" for="qtype">유형</label><select class="select" id="qtype" data-qtype>${['전체', '학습', '행정'].map((t) => `<option value="${t}"${qFilter.type === t ? ' selected' : ''}>${t === '전체' ? '모든 유형' : t === '학습' ? '학습질문' : '행정문의'}</option>`).join('')}</select></div>
        <div class="inbox-items">${list.length ? list.map((q) => { const st = L.byId[q.studentId]; return `
          <a href="#/qna/${q.id}"${cur && q.id === cur.id ? ' aria-current="true"' : ''}>
            <div class="top"><b class="num">${esc(q.title)}</b><span class="${q.status === '대기' && isOld(q) ? 'old' : ''}">${esc(q.ago)}</span></div>
            <p>${esc(q.body)}</p>
            <div class="who">${who(st)}${q.type === '행정' ? '<span class="pill warn">행정문의</span>' : q.status === '완료' ? '<span class="pill">답변 완료</span>' : ''}</div>
          </a>`; }).join('') : '<p class="inbox-empty">이 조건에 맞는 질문이 없습니다.</p>'}</div>
      </div>
      ${cur ? `<article class="thread" aria-labelledby="h-thread">
        <a class="back-link" href="#/qna"><svg class="i" viewBox="0 0 16 16"><path d="M10 3.5 5.5 8l4.5 4.5"/></svg>목록</a>
        <div class="thread-head">
          <div><h2 id="h-thread" class="num">${esc(cur.title)}</h2><div class="meta-line">${who(s)}<span>·</span><span class="num">질문 횟수 ${cur.asks}/3</span>${cur.type === '행정' ? '<span class="pill warn">행정문의 · 비공개</span>' : '<span class="pill">학습질문 · 닉네임 공개</span>'}</div></div>
          <a class="btn btn-sm" href="#/student/${s.id}">학생 보기</a>
        </div>
        <div class="msg"><div class="msg-head"><b>${esc(s.nick)}</b><time class="num">${esc(cur.thread.length ? '2026-10-29 21:30' : cur.at)}</time></div><p>${esc(cur.thread.length ? '높이 h에서 출발한 물체가 마찰 구간을 지나는 문제인데, 감소한 에너지를 어디서 빼야 하는지 헷갈립니다.' : cur.body)}</p>${cur.photo ? attach(1) : ''}</div>
        ${cur.thread.map((m) => m.who === 'student'
          ? `<div class="msg"><div class="msg-head"><b>${esc(s.nick)}</b><span class="pill">추가 질문 1/2</span><time class="num">${esc(m.at)}</time></div><p>${esc(m.text)}</p>${m.photo ? attach(2) : ''}</div>`
          : `<div class="msg t"><div class="msg-head"><b>${m.who === 'teacher' ? '선생님 답변' : esc(m.name)}</b><time class="num">${esc(m.at)}</time></div><p>${esc(m.text)}</p></div>`).join('')}
        ${cur.status === '대기' ? `<form class="composer" data-answer>
          <label class="field"><span>답변</span><textarea class="input" name="a" placeholder="풀이의 어느 줄에서 막혔는지 짚어 주세요" required></textarea></label>
          <div class="row"><button class="btn btn-text btn-sm" type="button">사진 첨부</button><div class="actions"><button class="btn" type="submit" value="stay">답변만 등록</button><button class="btn btn-primary" type="submit" value="next">등록하고 다음 질문</button></div></div>
        </form>` : `<div class="composer"><div class="row"><span class="muted">답변 완료 · ${esc(cur.by || '선생님')}</span><button class="btn btn-sm" type="button" data-reopen>답변 대기로 되돌리기</button></div></div>`}
      </article>` : '<div class="thread"><div class="empty"><b>대기 중인 질문이 없습니다.</b><span>새 질문이 올라오면 여기에 가장 오래된 것부터 보입니다.</span></div></div>'}
    </div>`;
  }
  const attach = (k) => `<button class="attach" type="button"><span class="thumb"><svg class="i" viewBox="0 0 16 16"><rect x="2.5" y="3" width="11" height="10" rx="1.5"/><path d="m3 11 3-3 2.5 2.5L10 9l3 3"/></svg></span><span>첨부 사진 · IMG_20${41 + k}.jpg</span></button>`;
  function bindQna(qid) {
    $$('[data-status]').forEach((a) => a.addEventListener('click', (e) => { e.preventDefault(); qFilter.status = a.dataset.status; render(); }));
    const t = $('[data-qtype]');
    if (t) t.addEventListener('change', () => { qFilter.type = t.value; render(); });
    const f = $('[data-answer]');
    if (f) f.addEventListener('submit', (e) => {
      e.preventDefault();
      const cur = L.questions.find((q) => q.id === qid) || L.questions.find((q) => q.status === '대기');
      cur.thread.push({ who: 'teacher', at: '2026-11-01 09:30', text: f.a.value.trim() });
      cur.status = '완료'; cur.by = '선생님';
      const next = waiting().sort((a, b) => a.at.localeCompare(b.at))[0];
      location.hash = e.submitter && e.submitter.value === 'next' && next ? `#/qna/${next.id}` : `#/qna/${cur.id}`;
      if (!(e.submitter && e.submitter.value === 'next' && next)) render();
    });
    const r = $('[data-reopen]');
    if (r) r.addEventListener('click', () => { const cur = L.questions.find((q) => q.id === qid); if (cur) { cur.status = '대기'; render(); } });
  }

  /* ---------- 라우터 ---------- */
  const view = $('#view');
  function render() {
    const parts = (location.hash.replace(/^#\/?/, '') || '').split('/');
    const [r, arg] = parts;
    let html = '', active = 'home', bind = null;
    switch (r) {
      case '': html = dashboard(); bind = bindDash; break;
      case 'class': html = classView(arg); active = 'class'; bind = bindClass; break;
      case 'student': html = studentView(arg); active = 'students'; bind = () => bindStudent(arg); break;
      case 'exams': html = examView(arg); active = 'exams'; bind = () => bindExam(arg); break;
      case 'qna': html = qnaView(arg); active = 'qna'; bind = () => bindQna(arg); break;
      case 'students': location.replace('#/class/K'); return;
      default: {
        const map = { notices: ['공지', '말머리(공지·정오·일정·시험·자료)로 반별 공지를 올립니다.'], files: ['자료실', 'PDF, PPT, HWP 등 수업 자료를 반별로 올립니다.'], videos: ['강의 영상', '유튜브·비메오·구글 드라이브 링크와 만료일을 등록합니다.'], news: ['교육 뉴스', '학생 홈에 보일 교육 뉴스를 등록합니다.'], signups: ['가입 승인', `승인 대기 ${L.signupsPending}명 · 명단과 대조해 승인합니다.`], assistants: ['조교 계정', '질문답변 화면만 쓰는 조교 계정을 관리합니다.'], audit: ['접근 기록', '로그인, 열람, 내보내기 기록과 IP를 봅니다.'] };
        const m = map[r] || ['찾을 수 없는 화면', '주소를 확인해 주세요.'];
        html = placeholder(m[0], m[1]); active = r;
      }
    }
    renderNav(active);
    view.innerHTML = html;
    if (bind) bind();
    document.title = `${(view.querySelector('h1') || {}).textContent || '대시보드'} · 정태혁 통합과학 연구소`;
    window.scrollTo(0, 0);
  }
  window.addEventListener('hashchange', render);
  let rt;
  window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(() => { const ch = $('[data-chart]'); if (ch) { const id = (location.hash.split('/')[2]) || L.featured.id; const s = L.byId[id] || L.featured; drawTrend(ch, s.scores, L.classById[s.classId].avgs); } }, 120); });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { const ch = $('[data-chart]'); if (ch) render(); });
  render();
})();
