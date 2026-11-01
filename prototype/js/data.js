/* 정태혁 통합과학 연구소 — 디자인 시안용 예시 데이터.
   모든 이름·점수·질문은 가짜이며 실제 앱 데이터로 교체해야 한다.
   합계와 평균은 모두 아래 행(row)에서 계산한다. 따로 적어 넣은 숫자는 없다. */
(function () {
  'use strict';

  // 고정 시드 난수: 새로고침해도 같은 데이터가 나온다.
  let seed = 20261101;
  const rnd = () => { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; };
  const pick = (arr) => arr[Math.floor(rnd() * arr.length)];
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const round1 = (v) => Math.round(v * 10) / 10;

  const TODAY = '2026-11-01';
  const FULL = 50; // 주간 테스트 만점

  const SURNAMES = ['김', '이', '박', '최', '정', '강', '조', '윤', '장', '임', '한', '오', '서', '신', '권', '황', '안', '송', '류', '홍', '전', '고', '문', '양', '손'];
  const GIVEN_A = ['서', '민', '지', '하', '도', '시', '예', '윤', '수', '준', '현', '유', '채', '다', '은', '연', '태', '승', '주', '건', '재', '나', '소', '가', '우'];
  const GIVEN_B = ['연', '준', '윤', '은', '원', '우', '린', '아', '호', '빈', '현', '진', '율', '희', '민', '서', '훈', '영', '하', '경', '결', '온', '솔', '람', '인'];
  const ADJ = ['달리는', '조용한', '느긋한', '반짝이는', '꼼꼼한', '용감한', '졸린', '씩씩한', '배고픈', '수줍은', '날쌘', '차분한', '엉뚱한', '부지런한', '깡충대는', '따뜻한', '진지한', '명랑한', '고요한', '빛나는'];
  const ANIMAL = ['하마', '수달', '펭귄', '고래', '여우', '부엉이', '다람쥐', '거북이', '판다', '알파카', '고슴도치', '해달', '미어캣', '두루미', '사슴', '물개', '오리', '참새', '너구리', '라쿤']; // 코알라 제외(사용자 요청)

  const CLASS_LETTERS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'P'];
  const CLASS_SIZES = [52, 49, 47, 51, 44, 48, 46, 43, 45, 41, 47, 38];
  const CLASS_LEVEL = [33.5, 32.8, 31.6, 30.9, 30.2, 29.4, 28.7, 27.9, 27.1, 26.4, 31.2, 35.8];

  const EXAM_DATES = ['2026-09-09', '2026-09-16', '2026-09-23', '2026-09-30', '2026-10-07', '2026-10-14', '2026-10-21', '2026-10-28'];
  const EXAMS = EXAM_DATES.map((date, i) => ({ id: 'w' + (i + 1), name: `주간 테스트 ${i + 1}회`, subject: '통합과학', date, full: FULL }));

  const usedNick = new Set();
  function nickname() {
    for (;;) { const n = `${pick(ADJ)} ${pick(ANIMAL)}`; if (!usedNick.has(n)) { usedNick.add(n); return n; } }
  }
  const usedName = new Set();
  function name() {
    for (;;) { const n = pick(SURNAMES) + pick(GIVEN_A) + pick(GIVEN_B); if (!usedName.has(n)) { usedName.add(n); return n; } }
  }

  // 반마다 회차별 난이도 흔들림(같은 반은 같은 시험을 본다)
  const examShift = EXAMS.map(() => (rnd() - 0.5) * 3);

  const classes = [];
  const students = [];
  let sid = 0;
  CLASS_LETTERS.forEach((letter, ci) => {
    const cls = { id: letter, letter, order: ci + 1, name: `${letter}반`, desc: `2027학년도 재수종합 ${letter}반`, code: (letter + 'Q7' + (ci * 37 + 1103)).slice(0, 8), studentIds: [] };
    // K반은 8회에서 평균이 눈에 띄게 떨어진 반으로 둔다(대시보드의 '발견').
    for (let k = 0; k < CLASS_SIZES[ci]; k++) {
      sid += 1;
      const ability = clamp(CLASS_LEVEL[ci] + (rnd() - 0.5) * 18, 12, 48);
      const trend = (rnd() - 0.45) * 0.8;
      const scores = EXAMS.map((e, ei) => {
        if (rnd() < 0.04) return null; // 결시
        let v = ability + trend * ei + examShift[ei] + (rnd() - 0.5) * 7;
        if (letter === 'K' && ei === 7) v -= 4.5;
        return clamp(Math.round(v), 0, FULL);
      });
      const st = {
        id: 's' + sid, name: name(), nick: nickname(), classId: letter,
        examNo: `27${String(ci + 1).padStart(2, '0')}${String(k + 1).padStart(4, '0')}`,
        scores,
        days: 30 + Math.floor(rnd() * 32),
        streak: Math.floor(rnd() * 12),
        points: 0,
        account: rnd() < 0.06 ? '미발급' : '사용 중',
      };
      st.points = st.days * 10 + Math.floor(rnd() * 30) * 5;
      students.push(st); cls.studentIds.push(st.id);
    }
    classes.push(cls);
  });

  const byId = Object.fromEntries(students.map((s) => [s.id, s]));
  const classById = Object.fromEntries(classes.map((c) => [c.id, c]));

  function classAvg(cls, ei) {
    const vals = cls.studentIds.map((id) => byId[id].scores[ei]).filter((v) => v != null);
    return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
  }
  function stats(vals) {
    const v = vals.filter((x) => x != null && x !== '');
    if (!v.length) return { n: 0, avg: null, sd: null, max: null, min: null };
    const avg = v.reduce((a, b) => a + b, 0) / v.length;
    const sd = Math.sqrt(v.reduce((a, b) => a + (b - avg) ** 2, 0) / v.length);
    return { n: v.length, avg, sd, max: Math.max(...v), min: Math.min(...v) };
  }
  function rankIn(cls, ei, sidArg) {
    const me = byId[sidArg].scores[ei];
    if (me == null) return null;
    const better = cls.studentIds.filter((id) => (byId[id].scores[ei] ?? -1) > me).length;
    return better + 1;
  }
  classes.forEach((c) => {
    c.avgs = EXAMS.map((_, ei) => classAvg(c, ei));
    c.last = round1(c.avgs[7]);
    c.prev = round1(c.avgs[6]);
    c.delta = round1(c.last - c.prev); // 화면에 보이는 두 값의 차이
  });

  // 질문(답변 대기 7건 + 완료)
  const Q_SEED = [
    { cls: 'K', type: '학습', title: '[수특 통합과학-42-7]', body: '역학적 에너지 보존에서 마찰이 있는 구간을 지나면 감소량을 어디서 빼야 하는지 헷갈립니다. 풀이 3번째 줄이 이해가 안 돼요.', ago: '2일 전', at: '2026-10-30 21:14', photo: true },
    { cls: 'K', type: '학습', title: '[주간지 8회-3-12]', body: '산화 환원 반응에서 산화수 변화로 산화제를 고르는 문제인데, 해설은 전자 이동으로 설명해서 둘이 같은 결론인지 궁금합니다.', ago: '1일 전', at: '2026-10-31 08:42', photo: true },
    { cls: 'C', type: '행정', title: '[행정] 11월 모의고사 결시 처리', body: '병원 진료 때문에 11월 4일 모의고사에 결시할 것 같습니다. 성적 처리를 어떻게 하면 될까요?', ago: '1일 전', at: '2026-10-31 13:05', photo: false },
    { cls: 'A', type: '학습', title: '[수특 통합과학-88-3]', body: '판 구조론에서 섭입대와 해구가 같은 곳에 생기는 이유를 그림으로 다시 설명해 주실 수 있나요?', ago: '18시간 전', at: '2026-10-31 15:47', photo: true },
    { cls: 'G', type: '학습', title: '[워크북-17-5]', body: '주기율표에서 이온화 에너지가 2족에서 13족으로 갈 때 줄어드는 예외를 어떻게 외우면 좋을까요?', ago: '9시간 전', at: '2026-11-01 00:31', photo: true },
    { cls: 'P', type: '학습', title: '[주간지 8회-5-20]', body: 'DNA 염기 비율 문제에서 한 가닥의 (A+G)/(T+C)가 0.8이면 상보 가닥은 1.25가 맞나요? 답지는 0.8로 되어 있어서요.', ago: '3시간 전', at: '2026-11-01 06:58', photo: true },
    { cls: 'E', type: '학습', title: '[수특 통합과학-121-2]', body: '생태계 평형에서 1차 소비자가 갑자기 늘면 생산자 양이 먼저 줄어드는지, 2차 소비자가 먼저 늘어나는지 순서가 궁금합니다.', ago: '1시간 전', at: '2026-11-01 08:40', photo: true },
  ];
  const questions = Q_SEED.map((q, i) => {
    const cls = classById[q.cls];
    const s = byId[cls.studentIds[(i * 7 + 3) % cls.studentIds.length]];
    return { id: 'q' + (100 + i), status: '대기', studentId: s.id, ...q, asks: 1, thread: [] };
  });
  // K반 질문 하나는 추가 질문까지 있는 대화로
  questions[0].asks = 2;
  questions[0].thread = [
    { who: 'teacher', at: '2026-10-29 22:10', text: '마찰 구간에서 줄어든 역학적 에너지는 마찰이 한 일의 크기와 같아요. 처음 역학적 에너지에서 그만큼 빼면 됩니다.' },
    { who: 'student', at: '2026-10-30 21:14', text: '그러면 높이 h에서 출발했을 때 바닥 마찰 구간을 두 번 지나면 두 번 다 빼는 건가요? 사진 다시 올립니다.', photo: true },
  ];
  const DONE_SEED = [
    { cls: 'B', type: '학습', title: '[워크북-9-1]', body: '원소의 생성에서 빅뱅 직후 수소와 헬륨의 질량비가 3:1인 근거가 궁금합니다.', at: '2026-10-29 19:20', by: '선생님' },
    { cls: 'D', type: '행정', title: '[행정] 자료실 PDF가 안 열려요', body: '10월 4주 자료 PDF를 받으면 손상된 파일이라고 나옵니다.', at: '2026-10-29 11:02', by: '조교 (박해린)' },
    { cls: 'K', type: '학습', title: '[수특 통합과학-37-4]', body: '뉴턴 운동 제3법칙과 힘의 평형을 구분하는 방법을 알고 싶어요.', at: '2026-10-28 23:48', by: '선생님' },
  ];
  DONE_SEED.forEach((q, i) => {
    const cls = classById[q.cls];
    const s = byId[cls.studentIds[(i * 11 + 5) % cls.studentIds.length]];
    questions.push({ id: 'q' + (200 + i), status: '완료', studentId: s.id, ago: '3일 전', photo: q.type === '학습', asks: 1, thread: [{ who: q.by === '선생님' ? 'teacher' : 'assistant', name: q.by, at: q.at, text: '답변을 등록했습니다.' }], ...q });
  });

  // 대표 학생(학생 상세 화면): K반에서 8회 점수가 크게 떨어진 학생 한 명
  const K = classById.K;
  const kDrops = K.studentIds.map((id) => byId[id]).filter((s) => s.scores[6] != null && s.scores[7] != null)
    .map((s) => ({ s, d: s.scores[7] - s.scores[6] })).sort((a, b) => a.d - b.d);
  const featured = kDrops[0].s;

  // 학생별 8회 하락 폭(전체 반) 상위 4명
  const drops = students.filter((s) => s.scores[6] != null && s.scores[7] != null)
    .map((s) => ({ id: s.id, d: s.scores[7] - s.scores[6] })).sort((a, b) => a.d - b.d).slice(0, 4);
  if (!drops.some((x) => x.id === featured.id)) drops[3] = { id: featured.id, d: featured.scores[7] - featured.scores[6] };
  drops.sort((a, b) => a.d - b.d);

  const memos = [
    { kind: '상담', at: '2026-10-29', text: '8회 직전 주에 수면 시간이 줄었다고 함. 생명 시스템 단원 개념 정리 먼저, 주 2회 오답 확인하기로.' },
    { kind: '학습', at: '2026-10-15', text: '역학 시스템 계산 문제에서 단위 환산 실수가 반복됨. 풀이 마지막 줄에서 단위 확인 습관 지도.' },
    { kind: '생활', at: '2026-09-24', text: '자습실 자리 이동 요청. 창가 쪽으로 옮김.' },
  ];

  const signupsPending = 3;

  // 데이터가 서로 맞는지 확인(콘솔에서 읽는다)
  const total = classes.reduce((a, c) => a + c.studentIds.length, 0);
  console.assert(total === students.length, '반 학생 수 합계가 전체 학생 수와 다름');
  console.assert(questions.filter((q) => q.status === '대기').length === 7, '답변 대기 질문 수 불일치');

  window.LAB = {
    TODAY, FULL, EXAMS, classes, students, byId, classById, questions, featured, drops, memos, signupsPending,
    stats, rankIn, round1,
    totalStudents: total,
    totalExams: classes.length * EXAMS.length,
  };
})();
