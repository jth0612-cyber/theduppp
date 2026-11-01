---
version: 1
slug: "prototype-index-html"
primary_target: "prototype/index.html"
related_targets: []
---

## Scope
Teacher (강사) screens of 정태혁 통합과학 연구소, clickable prototype: 대시보드, 반 상세(학생), 학생 상세, 시험·성적 입력, 질문답변. Mode: Operate. Desktop and phone web. Build path: code-led (Operate).

## Audience and job
One 통합과학 instructor managing ~12 classes (A–K, P), ~550 students now, up to 1000. Most frequent job: answer the oldest waiting question; second: spot a class or student whose score dropped and open them.

## Constraints
Pure HTML/CSS/JS, no inline script, no inline style attributes (CSP), all copy Korean. User-pinned: Japanese calm select-shop mood, 5 colour proposals and 5 type proposals switchable in the prototype. Logos: THedu (primary, currentColor), 시대인재 N 재수종합 lockup (affiliation, official colours, small).

## Direction contract
THESIS: The lab's classes are elements. The dashboard's class list is a small periodic table where each 반 letter is the element symbol carrying its live state; it refuses the KPI-tile-plus-chart dashboard template.
OWN-WORLD: Tinted select-shop wall as the L-shaped frame (low-chroma tint of the chosen palette), white paper sheet inset 8px with 16px corners and a 1px edge, no shadows. One accent hue on data and the selected state only. Element cells: square, 1px edge, big symbol in the display face, tiny figures in tabular numerals at fixed corners.
STORY: The teacher sees which class needs a hand (waiting questions, score drop) before anything else, opens it in one click, and answers the oldest question from the dashboard.
FIRST VIEWPORT: Frame sidebar 228px (THedu mark + 연구소 name top, nav, affiliation lockup + teacher row bottom), 48px top bar (centred student search, 시안 picker, account). Sheet: title row "대시보드" + finding line + primary "가장 오래된 질문 답하기"; one divided KPI strip (4 cells); main column = periodic table of 12 classes (6×2) then 답변 대기 list (5 rows); 384px rail = 점수가 크게 떨어진 학생 (4) and 8회 평균이 높은 반 (3). Amended after build: the score-drop list serves STORY's second job directly; 가입 승인 대기 stays as the KPI subline and the nav count, so it is not lost.
FORM: Periodic-table classes (assigned candidate 4 of 7). seed:c0e98ea7df72b708
SIGNATURE: element cells for classes; hover/focus on a cell fills the detail strip under the table (1–8회 average trend, waiting questions, the student who dropped most), defaulting to the class that dropped most; same cell reappears large as the class identity on 반 상세 and small beside each student.
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
