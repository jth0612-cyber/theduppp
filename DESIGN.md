---
name: 정태혁 통합과학 lab
description: 통합과학 강사 한 명이 반·학생·성적·질문을 다루는 개인 연구소의 관리 도구. 색이 든 편집샵 벽 위에 흰 종이 한 장, 그 위의 작은 주기율표.
colors:
  frame: "#e1e8e0"
  sheet: "#fcfdfc"
  raised: "#f3f5f0"
  active: "#dfe4dc"
  edge: "#dde1d8"
  rule: "#eaede6"
  control: "#c3c9bf"
  ink: "#1b1f1a"
  muted: "#555c53"
  faint: "#646b61"
  accent: "#2c6852"
  accent-soft: "#e2ede7"
  accent-ink: "#1d4a3a"
  positive: "#2c6852"
  negative: "#b3261e"
  pill-neg-bg: "#f9e7e4"
  pill-neg-ink: "#7d1d13"
  pill-warn-bg: "#f8f0de"
  pill-warn-ink: "#6e4510"
typography:
  display:
    fontFamily: "Noto Serif KR, Noto Sans KR, serif"
    fontSize: "24px"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.02em"
  element-symbol:
    fontFamily: "Noto Serif KR, Noto Sans KR, serif"
    fontSize: "38px"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Noto Serif KR, Noto Sans KR, serif"
    fontSize: "20px"
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: "-0.01em"
  figure:
    fontFamily: "Noto Sans KR, system-ui, sans-serif"
    fontSize: "24px"
    fontWeight: 500
    lineHeight: 1.25
    letterSpacing: "-0.01em"
    fontFeature: "\"tnum\""
  title:
    fontFamily: "Noto Sans KR, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 600
    letterSpacing: "-0.01em"
  lede:
    fontFamily: "Noto Sans KR, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.55
  body:
    fontFamily: "Noto Sans KR, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: "-0.005em"
  label:
    fontFamily: "Noto Sans KR, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.3
rounded:
  sheet: "16px"
  card: "12px"
  ctl: "8px"
  cell: "4px"
  pill: "4px"
  full: "50%"
spacing:
  inset: "8px"
  cell-gap: "8px"
  gap: "16px"
  column-gap: "24px"
  pad: "28px"
  pad-sm: "16px"
  ctl: "36px"
  ctl-touch: "44px"
  bar: "48px"
  side: "228px"
  rail: "384px"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.sheet}"
    rounded: "{rounded.ctl}"
    padding: "0 14px"
    height: "{spacing.ctl}"
  button-secondary:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    rounded: "{rounded.ctl}"
    padding: "0 14px"
    height: "{spacing.ctl}"
  button-secondary-hover:
    backgroundColor: "{colors.raised}"
  button-text:
    textColor: "{colors.ink}"
    rounded: "{rounded.ctl}"
    padding: "0 8px"
    height: "{spacing.ctl}"
  input:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    rounded: "{rounded.ctl}"
    padding: "0 12px"
    height: "{spacing.ctl}"
  sheet:
    backgroundColor: "{colors.sheet}"
    rounded: "{rounded.sheet}"
    padding: "26px 28px 40px"
  card:
    backgroundColor: "{colors.sheet}"
    rounded: "{rounded.card}"
    padding: "20px"
  element-cell:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    typography: "{typography.element-symbol}"
    rounded: "{rounded.cell}"
    padding: "9px 10px"
  element-cell-hover:
    backgroundColor: "{colors.raised}"
  element-chip:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    rounded: "3px"
    size: "22px"
  nav-item:
    textColor: "{colors.muted}"
    rounded: "{rounded.ctl}"
    padding: "0 10px"
    height: "34px"
  nav-item-active:
    backgroundColor: "{colors.active}"
    textColor: "{colors.accent-ink}"
  pill:
    backgroundColor: "{colors.raised}"
    textColor: "{colors.muted}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "0 7px"
    height: "20px"
  pill-accent:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.accent-ink}"
  pill-warn:
    backgroundColor: "{colors.pill-warn-bg}"
    textColor: "{colors.pill-warn-ink}"
  pill-neg:
    backgroundColor: "{colors.pill-neg-bg}"
    textColor: "{colors.pill-neg-ink}"
---

# Design System: 정태혁 통합과학 lab

## Overview

**Creative North Star: "편집샵 벽의 주기율표 (The Select-Shop Periodic Table)"**

일본의 차분한 편집샵처럼, 옅게 색이 든 벽(프레임) 위에 흰 종이 한 장(시트)을 8px 안쪽에 걸어 둔다. 프레임은 왼쪽 사이드바와 위쪽 48px 바가 만드는 L자이고, 내용은 모두 종이 위에 놓인다. 그림자로 띄우지 않고 1px 테두리와 면의 밝기 차이만으로 층을 나눈다. 차분함은 장식을 빼서가 아니라 정돈된 정보로 만든다.

이 연구소의 반(A–K, P)은 원소다. 반은 정사각에 가까운 "원소 칸"으로 그리며, 큰 반 글자가 원소 기호 자리에, 작은 숫자(순번, 답변 대기 수, 학생 수, 평균, 변화)가 정해진 모서리에 고정 폭 숫자로 놓인다. 같은 원소 칸이 대시보드에서는 표로, 반 상세에서는 큰 칸으로, 학생 옆에서는 작은 칩으로 다시 나온다.

강조색은 한 가지뿐이고 데이터와 "지금 선택된 것"에만 쓴다. 주요 버튼은 강조색이 아니라 먹색(잉크)이다. 빨강은 점수 하락, 오래된 질문, 입력 오류에만 쓴다. 한 강사가 1000명을 다루는 밀도라 화면은 촘촘하되, 숫자는 항상 고정 폭으로 줄이 맞는다.

**정한 것 (2026-11-01, 사용자 선택).** 색은 소나무(matsu), 글꼴은 Noto 계열(본문 본고딕 Noto Sans KR, 제목·원소 기호 본명조 Noto Serif KR)이다. 이름은 "정태혁 통합과학 lab". 다른 색 4안은 시안의 "색 고르기"에서 비교용으로만 남겨 두었다.

**Key Characteristics:**
- 색이 든 L자 프레임 + 8px 안쪽에 놓인 흰 시트(모서리 16px, 1px 테두리), 그림자 없음
- 반 = 원소 칸: 큰 기호, 모서리에 고정된 작은 고정 폭 숫자
- 강조색 하나, 데이터와 선택 상태에만
- 주요 버튼은 먹색, 빨강은 하락·지연·오류에만
- 둥근 모서리는 바깥에서 안으로 16 → 12 → 8 → 4px로 작아진다
- 모든 문구는 한국어, `word-break: keep-all`

## Colors

낮은 채도의 벽색 하나, 거의 흰 종이, 먹색 글자, 그리고 그 팔레트 고유의 강조색 하나로 이루어진 조용한 배색이다. 아래 이름과 역할은 5안 모두에 공통이고, 값은 frontmatter(기본값 matsu)와 아래 후보 표에 있다.

### Primary
- **솔잎색 (accent)**: 데이터와 선택 상태 전용. 성적 추이의 내 점수 선, 스파크라인, 원소 칸의 답변 대기 점, 현재 메뉴 옆 점, 포커스 테두리, 입력 커서.
- **짙은 솔잎 (accent-ink)**: 강조색 위·옆의 글자. 메뉴의 대기 수, 현재 메뉴 글자, 원소 칸의 답변 대기 수, 강조 알약 글자.
- **옅은 솔잎 (accent-soft)**: 강조의 면. 강사 답변 말풍선 배경, 성적 입력 중인 행, 포커스 링(3px), 텍스트 선택.

### Neutral
- **벽 (frame)**: L자 프레임(사이드바, 상단 바, 휴대폰 메뉴)의 배경. 팔레트의 성격이 가장 크게 드러나는 면.
- **종이 (sheet)**: 시트, 카드, 입력칸, 원소 칸, 팝오버의 배경.
- **한 단 올린 면 (raised)**: hover 배경, 원소 칸 상세 띠, 입력이 끝난 칸, 비활성 버튼.
- **선택 면 (active)**: 현재 메뉴, 선택된 질문, 고른 시안 옵션.
- **테두리 (edge)**: 시트·카드·원소 칸·KPI 띠의 1px 테두리.
- **구분선 (rule)**: 목록 행 사이, 표 행 사이의 1px 선. edge보다 한 단 옅다.
- **조작 테두리 (control)**: 버튼·입력칸의 테두리, 점선 빈 상태, 스크롤바.
- **먹 (ink)**: 본문 글자, 주요 버튼 배경, 선택된 원소 칸 테두리, 탭 밑줄.
- **보조 글자 (muted)**: 설명, 단위, 표 머리, 메타 정보.
- **흐린 글자 (faint)**: 원소 칸 순번, 자리표시 글자, 검색 아이콘, 구분 점.

### 상태색
- **오름 (positive)** / **내림 (negative)**: 점수 변화의 부호. negative는 하락 수치, 2일 이상 지난 질문, 2점 넘게 떨어진 반의 칸 테두리(negative 45% 섞음), 입력 오류에 쓴다.
- **경고 알약 (pill-warn-bg / pill-warn-ink)**, **위험 알약 (pill-neg-bg / pill-neg-ink)**: 5안 공통 값. "행정문의", "계정 미발급" 같은 분류 표시.

### 색 5안 (소나무 확정, 나머지는 비교용)

| 토큰 | 1. 소나무 matsu (확정) | 2. 먹과 주홍 sumi | 3. 이끼 koke | 4. 니가타의 바다 umi | 5. 호지차 hojicha |
|---|---|---|---|---|---|
| frame | #e1e8e0 | #e7e7e5 | #e0e5d1 | #dce5ec | #e8ddd1 |
| sheet | #fcfdfc | #ffffff | #fbfbfa | #fcfdfe | #fcfcfb |
| raised | #f3f5f0 | #f4f4f3 | #f1f2ea | #f1f4f6 | #f4f0eb |
| active | #dfe4dc | #dededb | #d9ddcd | #d6dee4 | #ddd5cc |
| edge | #dde1d8 | #e0e0dd | #dbdfd1 | #d9e0e5 | #e0d9d1 |
| rule | #eaede6 | #ededeb | #e8eae0 | #e7ecef | #ece7e1 |
| control | #c3c9bf | #c7c7c3 | #c1c6b4 | #bfc9d0 | #c9c0b6 |
| ink | #1b1f1a | #151515 | #20241c | #13202a | #28221e |
| muted | #555c53 | #595955 | #555b4c | #4f5d68 | #5e544c |
| faint | #646b61 | #64645f | #61675a | #5c6a75 | #6a5f56 |
| accent | #2c6852 | #b03c27 | #5a6a1f | #1c5a80 | #74492e |
| accent-soft | #e2ede7 | #f6e5e0 | #e8ecd6 | #e0ebf3 | #f0e6dd |
| accent-ink | #1d4a3a | #7e2a1b | #414d16 | #13435f | #573622 |
| positive | #2c6852 | #2f6b48 | #5a6a1f | #2f6b48 | #2f6b48 |
| negative | #b3261e | #8e1b2b | #b3261e | #b3261e | #a3241b |

먹과 주홍(sumi)은 강조색이 붉은 계열이라 negative를 더 깊은 자주빛 빨강(#8e1b2b)으로 떼어 놓았다. 다른 안을 고를 때도 accent와 negative가 같은 색으로 읽히지 않아야 한다.

### Named Rules
**The One Accent Rule.** 강조색(accent 계열)은 한 가지이고 데이터(점수 선, 대기 수, 점)와 선택·포커스 상태에만 쓴다. 장식, 제목, 아이콘 색, 주요 버튼에는 쓰지 않는다.

**The Red Means Drop Rule.** negative는 점수 하락, 오래 기다린 질문, 2점 넘게 떨어진 반, 입력 오류에만 쓴다. 그 외의 강조에 빨강을 빌려 쓰지 않는다.

**The Wall Carries the Palette Rule.** 팔레트의 성격은 벽(frame)과 강조색 두 곳에서만 드러난다. 시트와 카드는 거의 흰 종이로 남겨 둔다.

## Typography

**Display Font:** Noto Serif KR 600 (본명조) — 화면 제목, 원소 기호, lab 이름, 질문 스레드 제목
**Body Font:** Noto Sans KR 400/500/600/700 (본고딕, system-ui·sans-serif 대체)

**Character:** 본문은 단정한 본고딕이고, 제목·원소 기호·lab 이름만 본명조로 바뀌어 편집샵 인쇄물의 결을 더한다. 같은 Noto 가족이라 두 글꼴의 획 굵기와 비례가 잘 맞는다.

**글꼴 불러오기 (열린 결정).** 시안은 Google Fonts(fonts.googleapis.com / fonts.gstatic.com)에서 글꼴을 받는다. Flask 앱은 CSP가 엄격하므로 옮길 때 둘 중 하나를 정해야 한다. (가) 고른 글꼴 파일을 앱 안에 직접 두고(self-host) `font-src 'self'`로 둔다. (나) CSP에 `style-src https://fonts.googleapis.com`과 `font-src https://fonts.gstatic.com`을 허용한다. 아직 정하지 않았다. 시안은 이미 Noto Sans KR과 Noto Serif KR 600만 불러온다.

### Hierarchy
- **Display** (제목 글꼴, 24px, 줄 높이 1.25, 자간 -0.02em; 휴대폰 22px): 화면 제목(대시보드, 반 이름, 학생 이름).
- **Element Symbol** (제목 글꼴, 38px, 줄 높이 1): 원소 칸의 반 글자. 큰 칸 48px(휴대폰 34px), 상세 띠 40px, 작은 칩 13px.
- **Headline** (제목 글꼴, 20px, 줄 높이 1.35): 질문 스레드 제목.
- **Figure** (본문 글꼴 500, 24px, 고정 폭 숫자): KPI 띠의 숫자. 단위는 14px muted로 붙인다.
- **Title** (600, 16px, 자간 -0.01em): 카드·오른쪽 열의 섹션 제목.
- **Lede** (400, 15px, muted): 제목 아래 한 줄 요약. 핵심 수치만 ink 600으로 굵게.
- **Body** (400, 14px, 줄 높이 1.55, 자간 -0.005em): 모든 본문과 표. 질문 본문은 줄 높이 1.7, 최대 폭 680px.
- **Label** (400–600, 12px): 표 머리, 메타, 알약, 원소 칸의 작은 숫자(11–12px).

### Named Rules
**The Display Face Is for Names Rule.** 제목 글꼴은 이름에만 쓴다: 화면 제목, 반 기호, 연구소 이름, 질문 제목. 섹션 제목·버튼·숫자·본문은 본문 글꼴이다.

**The Tabular Figures Rule.** 점수, 인원, 날짜, 순번, 질문 번호는 모두 고정 폭 숫자(`tnum`)로 쓴다. 표와 원소 칸에서 숫자 자리가 줄마다 맞아야 한다.

**The Keep-All Rule.** 한국어 문장은 `word-break: keep-all`로 어절 단위로 줄을 바꾼다.

## Layout

L자 프레임 + 시트 구조. 데스크톱(1440 기준)에서 사이드바 228px, 상단 바 48px, 시트는 오른쪽·아래로 8px 안쪽에 놓이고 안쪽 여백은 좌우 28px(위 26px, 아래 40px)이다. 내용 폭 1148px = 본문 열 + 24px + 오른쪽 열 384px. 본문 열 안의 카드 사이 간격은 16px, 원소 칸 사이 간격은 8px.

KPI는 카드 여러 개가 아니라 1px 세로선으로 나뉜 한 줄의 띠(4칸 또는 5칸)다. 목록과 표는 행 사이 1px 구분선(rule)만 쓰고, 표 행 높이는 48px(휴대폰 56px)이다.

반응형:
- **1240px 이하**: 오른쪽 열 320px, 주기율표 4열.
- **1080px 이하**: 사이드바가 사라지고 상단 바의 메뉴 버튼이 전체 화면 메뉴(dialog, 벽색 배경)를 연다. 시트는 좌우 8px 안쪽. 본문·오른쪽 열이 한 줄로 쌓이고 오른쪽 열은 2단, 주기율표는 다시 6열.
- **760px 이하**: 시트가 화면 끝까지 붙고(모서리 0, 위 테두리만) 안쪽 여백 16px, 조작 높이 44px(터치 영역). 검색은 메뉴 안으로, 주기율표 3열, KPI 2×2, 제목 줄의 버튼은 폭을 나눠 채운다. 질문답변은 목록과 스레드를 한 번에 하나만 보여 준다.

## Elevation & Depth

평평하다. 시트, 카드, 원소 칸, KPI 띠에는 그림자가 없고, 층은 벽 → 종이의 밝기 차이와 1px 테두리(edge)로만 나눈다. hover는 면을 raised로 한 단 올리고, 원소 칸만 위로 2px 움직인다. 그림자는 다른 내용 위에 떠서 겹치는 층(검색 결과, 더보기 메뉴, 시안 고르기 팝오버)에만 쓴다.

### Shadow Vocabulary
- **떠 있는 층** (`box-shadow: 0 10px 28px rgb(0 0 0 / .08)`): 검색 결과 목록, 더보기 메뉴.
- **시안 고르기** (`box-shadow: 0 14px 36px rgb(0 0 0 / .10)`): 시안 고르기 팝오버.
- **포커스 링** (`box-shadow: 0 0 0 3px` accent-soft): 입력칸 포커스. 오류일 때는 pill-neg-bg.

### Named Rules
**The Paper on the Wall Rule.** 종이 위에 놓인 것(카드, 원소 칸, KPI, 표)은 그림자를 갖지 않는다. 그림자는 내용 위로 겹쳐 뜨는 임시 층만의 것이다.

## Shapes

둥근 모서리는 바깥 그릇에서 안쪽 알맹이로 갈수록 작아진다: 시트 16px → 카드·KPI 띠·팝오버·질문함 12px → 버튼·입력칸·메뉴 항목·상세 띠 8px → 원소 칸·알약·kbd 4px → 작은 원소 칩 3px. 원(50%)은 아바타와 6px 상태 점에만 쓴다. 테두리는 항상 1px 실선이고, 점선은 "아직 없음" 빈 상태에만 쓴다. 아이콘은 16px, 선 굵기 1.5, 둥근 끝의 선 SVG다.

### Named Rules
**The Nesting Radius Rule.** 안에 든 것은 담는 것보다 모서리가 크지 않다(16 → 12 → 8 → 4).

## Components

### Buttons
조용하고 단단하다. 높이 36px(휴대폰 44px), 모서리 8px, 글자 500.
- **Primary:** 먹(ink) 배경에 종이색 글자. 화면마다 하나("가장 오래된 질문 답하기" 같은 다음 할 일). hover 시 먹 86%로 살짝 옅어진다.
- **Secondary:** 종이 배경, control 테두리. hover 시 raised 배경, 테두리 muted.
- **Text:** 테두리·배경 없음, hover 시 raised. 아이콘 버튼은 정사각 36px.
- **Small:** 높이 30px, 13px. 목록 행의 "답하기", 상단 바의 "시안 고르기".
- **Active / Disabled:** 누르면 1px 내려간다. 비활성은 투명도를 낮추지 않고 raised 면 + faint 글자로 바꾼다.

### Chips (알약)
- **Style:** 높이 20px, 모서리 4px, 12px 500. 기본은 raised + muted.
- **Variants:** accent(답변 대기), warn(행정문의, 계정 미발급), neg(위험). 상태를 분류만 하고 누를 수 없다.

### Cards / Containers
- **Corner Style:** 12px.
- **Background:** 종이(sheet).
- **Shadow Strategy:** 없음(Elevation 참고).
- **Border:** 1px edge.
- **Internal Padding:** 20px. 머리 줄은 16px 600 제목 + 오른쪽 12px muted 메타.

### KPI 띠
4칸(대시보드) 또는 5칸(학생 상세, 시험) 한 줄, 칸 사이 1px edge 세로선, 바깥 모서리 12px. 칸 안: 13px muted 이름, 24px 숫자 + 14px 단위, 12px muted 보조 줄. 휴대폰에서는 2×2.

### Inputs / Fields
- **Style:** 종이 배경, 1px control 테두리, 모서리 8px, 높이 36px. 검색칸은 32px, edge 테두리, 오른쪽에 `/` 키 표시.
- **Focus:** 테두리 ink + 3px accent-soft 링.
- **Error:** 성적 입력칸은 테두리 negative + 3px pill-neg-bg 링, 옆에 12px negative 문구. 입력이 끝난 칸은 raised 배경.

### Navigation
사이드바 메뉴는 높이 34px(휴대폰 44px), 모서리 8px, 기본 muted 글자. hover는 active 55% 면. 현재 페이지는 active 면 + accent-ink 600 글자 + 앞의 6px 강조색 점. 대기 수는 오른쪽에 12px accent-ink. 메뉴 묶음 이름(수업·게시·관리)은 12px. 탭은 글자만 있고 현재 탭은 ink 600 + 아래 2px ink 밑줄.

### 원소 칸 (Signature)
반 하나 = 원소 칸 하나. 1px edge 테두리, 모서리 4px, 종이 배경, 가로:세로 1:0.92. 위쪽 줄에 순번(11px faint)과 답변 대기 수(6px 강조 점 + accent-ink 600), 가운데 큰 반 기호, 아래에 "학생 N명"(12px muted)과 8회 평균(14px 600) + 변화(12px, 하락이면 negative). 2점 넘게 떨어진 반은 테두리를 negative 45%로 섞는다. hover·focus 시 테두리 ink, 배경 raised, 위로 2px; 선택된 칸도 같은 모습. 대시보드에서는 칸 아래 raised 상세 띠(모서리 8px)에 그 반의 기호, 요약, 1–8회 스파크라인을 보여 주고, 기본은 가장 많이 떨어진 반이다. 반 상세 머리에는 큰 칸(104px, 휴대폰 76px), 학생 이름 옆에는 22px 칩으로 같은 칸이 다시 나온다.

### 질문 행과 스레드
목록 행은 [교재-페이지-번호] 제목(600) + 본문 한 줄 말줄임, 아래 13px muted 메타(닉네임 · 이름 · 원소 칩), 오른쪽에 경과 시간(오래되면 negative 600)과 작은 "답하기" 버튼. 스레드에서 학생 글은 바탕 없이, 강사 답변은 accent-soft 면(모서리 12px)에 놓는다.

## Do's and Don'ts

### Do:
- **Do** 새 화면도 벽(frame) 위 8px 안쪽에 모서리 16px, 1px edge의 시트 한 장으로 시작한다.
- **Do** 반은 언제나 원소 칸(또는 22px 원소 칩)으로 표시하고, 숫자는 정해진 모서리에 고정 폭으로 둔다.
- **Do** 요약 수치는 1px 세로선으로 나뉜 KPI 띠 한 줄로 묶는다.
- **Do** 화면마다 주요(먹색) 버튼은 하나만 두고, 그 화면의 다음 할 일을 문구로 쓴다.
- **Do** 색·글꼴은 토큰(`--frame`, `--accent`, `--font-display` 등)으로만 쓴다. 그래야 5안 전환과 최종 1안 확정이 한 곳에서 끝난다.
- **Do** 본문 대비 4.5:1 이상을 지킨다. 벽(frame) 위의 12px 글자는 muted를 쓴다(matsu·umi에서 faint는 벽 위에서 4.5:1에 못 미친다).
- **Do** 휴대폰(760px 이하)에서 누르는 것은 모두 44px 이상으로 키운다.

### Don't:
- **Don't** 카드, 시트, 원소 칸, KPI에 그림자를 넣지 않는다. 그림자는 떠서 겹치는 층에만.
- **Don't** 강조색을 주요 버튼, 제목, 아이콘, 장식 면에 쓰지 않는다.
- **Don't** 빨강(negative)을 하락·지연·오류 외의 강조에 쓰지 않는다.
- **Don't** 아이콘이 든 색깔 KPI 타일 여러 개와 큰 차트를 나열하는 대시보드 틀로 바꾸지 않는다.
- **Don't** 이모지, 아이콘 글꼴, 글자 기호를 아이콘 대신 쓰지 않는다. 아이콘은 16px 선 SVG.
- **Don't** 시대인재 N 재수종합 로고를 크게 쓰거나 색을 바꾸지 않는다. 사이드바 아래 13px 높이, 공식 색 그대로의 소속 표시로만 둔다. 주 로고는 THedu(currentColor)다.
