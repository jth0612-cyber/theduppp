# Squeeze 내지·표지 리디자인 시안

## 리소스 PDF (`resources/`) ← 현재
확정안 03-01-14 D의 디자인 요소만 원본 리소스 PDF(release_point_resources)와 같은 쪽 크기·순서로 분리(53쪽).
본문 글자는 모두 비우고, 디자인 라벨(Solving·Linking·Memo·Contents·풀이·Logic Check)과 'Squeeze' 로고는 원본처럼 윤곽선.
빠른 정답 요소(원본 9~15쪽)는 뺌. O·X 표시·아이콘·따옴표·전구는 원본 그대로. 맨 뒤에 Logic Check 쪽 덧붙임.
쪽 대응표 `Squeeze_resources_03-01-14D_목록.txt`, 한눈에 보기 `한눈에_큰요소.png`·`한눈에_작은요소.png`.
다시 만들기: `python sq_res.py <squeeze.pdf> <resources.pdf> resources/Squeeze_resources_03-01-14D.pdf`

## 확정안 03-01-14 D (`finalD/`)
글꼴 조합 11(Pretendard + Cinzel) · Solving·Linking 글자 Space Grotesk · 좌상단 '과학의 기본량' Diphylleia · 상단바 03-01-11 그대로 ·
Solving·Linking 줄 파형 D(간격 1.1mm, 글자·아이콘·핀 가운데 선 정렬, 위아래 0.5mm 단차, 굵기 0.26mm). 전체 84쪽과 예시 14쪽.
다시 만들기: `python sq_final14.py <squeeze.pdf> <resources.pdf> finalD`

## 파형 모양 3안 (`wave3/`, 03-01-15)
D(간격 1.1mm, 가운데 선 정렬, 0.5mm 단차, 굵기 0.26mm) 확정, 파형 모양만 3가지.
- F 말소리: 둥근 소리 뭉치(6~10칸)와 조용한 쉼(3~5칸)이 번갈아
- G 박자: 7칸(7.7mm)마다 박이 솟고 뒤로 잦아듦
- H 한 번의 큰 숨: 작게 시작해 40% 지점에서 크게 솟았다가 아이콘 쪽으로 잦아듦
비교판 `Solving_파형_비교.png`(현재·D + F/G/H), `6쪽_Solving_{F,G,H}.png`.
다시 만들기: `python sq_wave3.py <squeeze.pdf> <resources.pdf> wave3` → `python wave_board.py wave3 'wave/*SolvingD*_예시14쪽.pdf'`

## Solving 줄 파형안 (`wave/`, 03-01-14)
음악 재생 파형처럼: 글자(대문자 높이 가운데)·아이콘·핀 줄을 하나의 가운데 선에 세로 정렬. 가운데 선은 고정하고 핀이 위아래로 똑같이 뻗으며
0.5mm 단위 단차(반 높이 0.5~3.0mm), 아이콘 쪽으로 잦아듦. 선 굵기 0.26mm 그대로.
- D 간격 1.1mm(현재와 같음) / E 간격 0.8mm
비교판 `Solving_파형_비교.png`(현재 + 03-01-13 A/B/C + D/E), `6쪽_Solving_{D,E}.png`.
다시 만들기: `python sq_wave.py <squeeze.pdf> <resources.pdf> wave` → `python wave_board.py`

## Solving 줄 3안 (`sol3/`, 03-01-13)
상단바는 03-01-11 그대로(03-01-12 상단 3안은 보류). Solving·Linking 옆 핀 줄만, 선 굵기 0.26mm 고정, 간격과 위아래 단차만 다르게.
- A 넓은 간격·낮은 단차: 간격 1.8mm, 길이 3~4mm(1mm만 오르내림), 위 기준선 고정
- B 중간 간격·큰 단차: 간격 1.4mm, 아래 끝이 1.2~6.0mm를 1.2mm 계단으로 크게 오르내림
- C 좁은 간격·위아래 단차: 간격 0.8mm, 글자 가운데 높이를 기준으로 위·아래 양쪽에 따로 단차, 아이콘 쪽으로 낮아짐
비교판 `Solving_3안_비교.png`(현재 + A/B/C), `6쪽_Solving_{A,B,C}.png`.
다시 만들기: `python sq_sol3.py <squeeze.pdf> <resources.pdf> sol3` → `python sol3_board.py sol3`

## 상단바 3안 (`head3/`, 03-01-12)
03-01-11(좌상단 17) 기준, 상단바만 눈에 띄게 변형. 윤곽·밀도/굵기·색 배분·높이/끝 처리를 안마다 다르게.
- A 촘촘·잔잔: 간격 1.4mm·굵기 0.26mm·토막 1.2mm, 잔물결 많은 낮은 윤곽(6~15mm), 아래로 갈수록 연해짐, 회색 드물게
- B 성글고 굵게·큰 물결: 간격 3.0mm·굵기 0.6mm·토막 2.4mm, 펼침면을 가로지르는 큰 물결(4.5~20.5mm), 회색 무리, 깊은 곳 아래 떨어진 토막
- C 칸 묶음·계단: 기둥 5개씩 한 칸(칸 사이 틈), 칸마다 높이 한 단씩 다른 계단 윤곽, 칸마다 한 농도(가끔 회색 칸), 아래 끝 가로 띠
비교판 `상단바_3안_비교.png`(현재 + A/B/C), 펼침면 `펼침면_{A,B,C}_{4-5,6-25}.png`, `확대_{A,B,C}.png`.
다시 만들기: `python sq_head3.py <squeeze.pdf> <resources.pdf> head3` → `python head3_board.py head3`

## 확정안 03-01-11 좌상단 17 (`final17/`)
03-01-10 + 짝수쪽 좌상단 '과학의 기본량'(Diphylleia 14.5pt, 자간 10). 전체 84쪽과 예시 14쪽.
다시 만들기: `python sq_label10.py <squeeze.pdf> <resources.pdf> final17 17 --full`

## 좌상단 글꼴 2차 (`label10b/`)
1차에서 04(Noto Serif KR SemiBold)·06(고운바탕 Bold)만 남기고 나머지 8개를 교체: 11 Noto Serif KR Medium, 12 Noto Serif KR Bold,
13 고운바탕 Regular(자간), 14 나눔명조 Bold, 15 나눔명조 Regular(자간), 16 함렛 Medium, 17 Diphylleia, 18 Grandiflora One.
다시 만들기: `python sq_label10.py <squeeze.pdf> <resources.pdf> label10b` → `python label10_board.py label10b`

## 좌상단 글꼴 10안 (`label10/`, 03-01-11)
03-01-10 기준, 짝수쪽 좌상단 '기출 EXTRACT 2' → '과학의 기본량'(영문 뺌). 이 글자의 글꼴만 01~10. 비교판 `좌상단_글꼴10안_비교.png`.
다시 만들기: `python sq_label10.py <squeeze.pdf> <resources.pdf> label10 [01 ...] [--full]` → `python label10_board.py`

## 확정안 03-01-10 (`final/`)
글꼴 조합 11(한글 제목 Pretendard SemiBold, 한글 작은 글자 Pretendard, 영문 제목 Cinzel) + Solving·Linking 글자는 조합 07의 Space Grotesk Medium(0.95배).
번호 Barlow Condensed Medium, 하단 'Squeeze' Million Dreams 그대로. 전체 84쪽과 예시 14쪽.
다시 만들기: `python sq_final11.py <squeeze.pdf> <resources.pdf> final full`

## 글꼴 조합 20종 (`combo20/`, 11~30)
고정: Solving·Linking 머리 글자와 하단 'Squeeze'(Million Dreams), 문제 번호(Barlow Condensed Medium).
바뀌는 것: 한글 제목 / 한글 작은 글자 / 영문 제목(Logic Check·Memo·Contents·단원 글자). 영문 제목은 대문자 높이를 Million Dreams에 맞춰 자동 배율.
비교판: `글꼴조합20_비교_1~4.png`. 다시 만들기: `python sq_combo20.py <squeeze.pdf> <resources.pdf> combo20 [11 12 ...]` → `python combo20_board.py`.

## 글꼴 조합 11종 (`combo/`, 00~10)
03-01-09 예시본(14쪽)에서 번호 글꼴(Barlow Condensed Medium)과 'Squeeze' 로고 글자(Million Dreams)는 고정하고, 나머지 글꼴만 조합을 바꿈.

| 조합 | 한글 제목 | 한글 작은 글자 | 영문 제목 |
|---|---|---|---|
| 00 현재 | Pretendard SemiBold | Pretendard | Million Dreams |
| 01 | 함렛 SemiBold | Pretendard | Cormorant Garamond SemiBold |
| 02 | Gothic A1 SemiBold | Gothic A1 | Barlow Condensed SemiBold |
| 03 | 고운돋움 | 고운돋움 | Fraunces SemiBold |
| 04 | Noto Serif KR SemiBold | Noto Serif KR | Playfair Display Medium |
| 05 | 나눔명조 ExtraBold | IBM Plex Sans KR | Instrument Serif |
| 06 | 고운바탕 Bold | 고운바탕 | EB Garamond |
| 07 | 나눔고딕 ExtraBold | 나눔고딕 | Space Grotesk Medium |
| 08 | 해바라기 Bold | 해바라기 | Big Shoulders Display Medium |
| 09 | 송명 | Pretendard | Bodoni Moda |
| 10 | 도현 | Pretendard | Oswald Light |

- 모두 OFL. 한글은 npm @fontsource 조각 woff를 `merge_chunks.py`로 하나의 TTF로 합쳐 씀(쓰는 글자 모두 포함 확인)
- 비교: `글꼴조합_비교_1(머리·번호·Solving·풀이).png`, `글꼴조합_비교_2(LogicCheck·차례·하단).png`(00–05), `글꼴조합_비교_1·2(06-10).png`, 조합별 실제 펼침면 `펼침면_NN.png`
- 빌드: `python sq_combo.py sq/sq.pdf hb/res.pdf combo [00 01 …]`

## 전체 시안 (`full/`)
- `Squeeze_기출EXTRACT2_내지_03-01-09_예시(A-1 한 문제).pdf`: 84쪽 전체 적용본에서 문제는 A-1(5·6쪽)만 남기고 나머지 문제 쪽을 지운 14쪽 예시(원본 쪽 1·2·3·4·5·6·25·26·55·56·81·82·83·84). 문제 쪽은 2쪽씩 지워 좌우 배치 유지, 쪽번호는 원본 그대로. `Squeeze_03-01-09_예시_썸네일.png`
- 84쪽 전체본은 `sq_full.py`로 다시 만들 수 있음
- 빌드: `python sq_full.py sq/sq.pdf hb/res.pdf <출력.pdf>`
- 쪽별 처리: 문제 홀수쪽(상단 핀 오른쪽 절반·단원명·번호·풀이 칸 4가지 높이 + 원본 점 14%) / 해설 짝수쪽(상단 핀 왼쪽 절반·번호·Solving·Linking 머리를 쪽마다 위치를 찾아 교체, 원본 아이콘 유지) / 4·26·56 Logic Check / 1 시작하기에 앞서 / 2 차례 / 25·55·81·83 MEMO / 82 빠른 정답(원본 답 36개를 읽어 다시 짬, 원본과 일치 확인) / 3·84 그대로
- 검증: 문제 그림 98개 모두 유지, 본문 글자 손실 없음

## 세로 핀 디벨롭 (`v4/`, 03-01-NN)
사진 1(오른쪽 건물 외벽의 세로 핀)에서 읽은 질감: 기둥 간격 2.2mm마다 0.34mm 핀, 층(1.8mm) 단위로 끊긴 토막, 토막마다 별색 농도 100/70/45/25%, 시작·끝이 엇갈림.
요소별 후보를 세 묶음으로 빌드해 비교한다(인수인계 17-24안 방식).

| 묶음 | 상단 | 문항 번호 | 풀이 공간 | Solving / Logic Check |
|---|---|---|---|---|
| 03-01-01 (A) | H1 다듬기: 제본선 쪽이 깊고 바깥으로 길이만 짧아짐 | N1 번호·출처만 | P1 위쪽 핀 한 줄 | 아래로 매달림 / 외벽 판 |
| 03-01-02 (B) | H2 + 옅은 외벽 격자(층 선·창틀) | N2 바깥쪽 핀 기둥 | P2 왼쪽 핀 기둥 | 아래로 매달림 / 격자 외벽 판 |
| 03-01-03 (C) | H3 아래 기준선에서 위로 자람 | N3 번호 아래 짧은 핀 줄 | P3 장식 없음 | 위로 자람 / 바닥에서 솟는 판 |

- **03-01-09 (현재)**: 03-01-08(Solving 2안) + 번호 글꼴 굵기 약 2배. Barlow Condensed 세로 획 두께(Light 300 = 53) 기준 Medium 500(96, 1.8배) / SemiBold 600(116, 2.2배) 두 가지. 크기는 같음(27.09pt). 빌드 `python sq10.py sq/sq.pdf hb/res.pdf <폴더>`. 비교: `Squeeze_내지_03-01-09_번호굵기_비교.png`
- **03-01-08 (Solving 3안 중 선택)**: 03-01-07 + 번호 글꼴 02 Barlow Condensed Light(대문자 높이를 Million Dreams 30pt에 맞춰 27.09pt) + 풀이 칸에 원본 배경 점(같은 위치 2,030개, 지름 0.5mm, 가로 3.85·세로 4.5mm 간격, 별색 14%) + Solving 핀 간격 축소·회색 섞음 3안(1안 1.5mm 매끄럽게 줄어듦 / 2안 1.1mm 층 토막 작은 외벽 / 3안 1.1mm 무작위 윤곽, 아래 끝 회색). 빌드 `python sq9.py sq/sq.pdf hb/res.pdf <폴더>`. 비교: `_Solving_3안_비교.png`, `_풀이점_확대.png`, `_비교_67쪽.png`
- **03-01-07**: 03-01-05 + Solving 연필 아이콘 복원(리소스 24쪽 원본 벡터, 높이 5mm, 'Solving'과 세로 가운데 정렬, 핀 줄은 아이콘 4.2mm 앞에서 끝) + 상단 회색 핀(먹 45/25%: 깊게 내려간 기둥의 아래 끝 토막 위주, 잡음으로 정한 구간에 모여 나옴, 이웃 기둥에 연달아 오지 않음). 빌드 `python sq8.py sq/sq.pdf hb/res.pdf <폴더> base`
- **번호 글꼴 10종** (`번호글꼴_10종_견본.png`, `python sq8.py ... fonts` / `v7_fonts.py`): Million Dreams 30pt와 대문자 높이를 맞춰 비교. 01 Big Shoulders Display, 02 Barlow Condensed, 03 Oswald, 04 Antonio, 05 Inter Tight, 06 Space Grotesk, 07 Fraunces, 08 Playfair Display, 09 Cormorant Garamond, 10 Instrument Serif (모두 OFL, npm @fontsource)
- **03-01-05**: 03-01-04 그대로, 상단 핀 아래 끝의 위아래 편차만 50%(가운데 11.75mm 기준 7.9~15.6mm). 빌드 `python sq7.py ... v4 E`. 비교: `Squeeze_내지_03-01-05_상단비교(04 대비).png`, `_비교_67쪽.png`, `_비교_45쪽.png`
- **03-01-04**: H1 + 핀 아래 끝 윤곽을 좌우 대칭이 아닌 무작위(큰·중간·잔물결 잡음 합)로 내려갔다 올라오게, 풀이 공간과 Logic Check는 P3 형태(가는 선 + 작은 핀 표식 + 라벨)로 정리, 번호 N1, Solving은 매달린 핀 줄. 빌드 `python sq7.py ... v4 D`. 비교: `Squeeze_내지_03-01-04_비교_67쪽.png`(원본 / 03-01-01 / 03-01-04)
- `후보_상단.png`, `후보_요소.png`, `후보_LogicCheck.png`: 요소별 비교 / `비교_67쪽.png`, `비교_45쪽.png`: 원본 대비 펼침면
- 빌드: `python sq7.py sq/sq.pdf hb/res.pdf v4 [A B C]` (질감 생성기 `tex.py`, 공용 `sq6.py`·`sq5.py`)

## 사진 질감 시안 5종 (`sq6.py`, 03-01~03-05)
03-01 세로 핀 머리띠 / 03-02 세로 핀 바깥 기둥 / 03-03 잔물결 선 / 03-04 물빛 톤 / 03-05 핀이 물에 비침. 03-01(세로 핀)으로 디벨롭하기로 함.

## 시안 5종 (`v2/`, 02-NN)
인수인계 4b 등고선 머리 그림의 기준을 따른 5개 방향. 공통: 펼침면(524mm) 한 장면·제본선 대칭, 0.2pt 안팎 헤어라인, smoothstep 페이드, 별색 톤 ≤12%, 2도.
공용 글자: 단원명 14pt(기준선 31), 번호 30pt(47), 출처 8.2pt, 하단 9pt(359). 여백 바깥 19mm, 단 19–128 | 134–243.

| 번호 | 방향 | 참고 | 머리 | 번호 | 풀이 공간 |
|---|---|---|---|---|---|
| 02-01 | 등고선 비틀림 | 인수인계 4b 등고선 + 매듭·회전 | 가는 선 9줄이 제본선으로 처지고 양쪽에서 한 점으로 눌렸다 반 바퀴 비틀림 | Million Dreams 별색 | 옅은 톤 + 위쪽 등고선 3줄 |
| 02-02 | 루버 | 도쿄 국립신미술관 유리 루버 | 0.85mm 간격 수직선, 길이가 물결치고 제본선 쪽이 깊음 | Pretendard ExtraLight + 루버 눈금 | 위쪽 짧은 루버 띠 |
| 02-03 | 처마와 수면 | 다니구치 건축관 | 펼침면을 가로지르는 처마 띠 + 수면에 비친 끊어진 선 | Pretendard Light + 처마 밑줄 | 처마 + 가로 괘선 |
| 02-04 | 회전 고리 | 매듭·회전 | 바깥 모서리의 회전하는 고리 구 + 둘을 잇는 궤도선 | Million Dreams 별색 | 둥근 테두리 + 작은 고리 |
| 02-05 | 말랑한 면 | a.presse 회반죽 면 | 둥근 면 두 겹 + 부드러운 그림자, 제본선 앞에서 멈춤 | 둥근 면 안 Million Dreams | 둥근 옅은 면 |

- `비교_67쪽.png`, `비교_45쪽.png`: 원본 + 5종 펼침면 / `비교_상단펼침면.png`: 머리 부분 / `비교_요소확대.png`: 시안 × 요소 150dpi
- 빌드: `python sq5.py sq/sq.pdf hb/res.pdf v2 [1 2 3 4 5]`

## 01-01 (`v/`)
인수인계 방식대로 `Squeeze_내지_01-NN(변경 요약)`으로 번호를 올리고 이전 버전은 지우지 않는다. 버전마다 원본 대비 비교 PNG와 요소 확대 PNG를 함께 둔다.

- `Squeeze_내지_01-01(매듭 코일 상단바).pdf`: 4~7쪽 시안. 상단은 펼침면 전체를 가로지르는 매듭 코일 한 장면(바깥쪽은 고리가 겹쳐 감기고 제본선 쪽은 관이 가늘게 눌려 풀림). 판화처럼 앞면 나선 선의 밀도만으로 둥근 부피를 내 2도에 맞춤. 풀이 공간·Solving·Logic Check 매듭도 같은 튜브로 통일
  - 체계: 바깥 여백 19mm, 단 19–128 | 134–243, 기준선 머리 30 / 번호 47 / 하단 359, 글자 13 / 32 / 8.4 / 9pt, 선 0.38(윤곽)·0.2(나선)·0.25(괘선)pt
- `Squeeze_내지_01-01_비교.png`: 원본과 펼침면 비교 / `_요소확대.png`: 요소별 200dpi 확대 / `_상단코일후보3종.png`: 코일 밀도 후보(가운데 안 채택)

## 이전 결과물 (`out/`)
- `A_루버.pdf`, `A2_매듭.pdf`: 원본 내지 4~7쪽(Logic Check + A-1, A-2 펼침면)에서 틀 요소만 지우고 새 틀을 벡터로 그린 시안
  - A2는 A의 가는 선을 리본으로 묶어, 고리를 만들며 꼬이는 말랑한 매듭 리본(비틀림에 따라 별색 농도가 바뀌는 면 + 가는 선, 위·아래 교차)을 상단바·풀이 공간·Solving·문항 번호·하단·Logic Check에 적용
- `비교_45쪽.png`, `비교_67쪽.png`: 원본과 시안 펼침면 비교
- `비교_부분확대.png`: 상단바, 문항 번호, Solving 머리, 하단 확대 비교
- `표지_매듭.pdf` / `.png` / `_확대.png`: (3,7) 토러스 매듭 리본 표지 시안 (매듭 아이디어를 표지로 잘못 이해해 만든 것. 참고용)

색은 2도(먹 + 별색) 기준이고, 별색은 기존 하늘색(#00A2DB)을 자리표시로만 썼다. 모든 색은 두 잉크의 농도로만 표현했다.

## 다시 만들기 (`scripts/`)
입력 파일은 저장소에 넣지 않았다. 아래처럼 작업 폴더에 둔 뒤 그 폴더에서 실행한다.

- `sq/sq.pdf`: Squeeze 기출 EXTRACT 2 내지 원본
- `hb/res.pdf`: Release Point 리소스 PDF (THedu 로고를 여기서 잘라 쓴다)
- `md/Million Dreams.otf`: Squeeze 로고 글꼴 (상용, 저장소 제외)
- `npm/package/...`: `npm pack pretendard@1.3.9` 후 압축 해제. TTF(`alternative/`)를 쓴다. OTF는 PyMuPDF에서 하이픈 등이 빠진다.

```bash
pip install pymupdf fonttools pillow numpy
python sq_variants.py sq/sq.pdf hb/res.pdf npm/package/dist/public/static sq/out
python sq_board.py sq/sq.pdf sq/out
python cover.py "$PWD/sq/out/표지_매듭.pdf"
```

- `sq_lib.py`, `sq_v01.py`: 01-NN 버전 빌드(`python sq_v01.py sq/sq.pdf hb/res.pdf <출력.pdf>`). 매듭 튜브 렌더러 `tube()`는 짧은 구간 단위로 깊이 정렬해 [종이색 면 → 앞면 나선 선 → 윤곽]을 그린다
- `v_crops.py`: 요소 확대 점검 PNG
- `sq_variants.py`: 틀 지우기(redaction) + 시안 A/A2 그리기. 시안별 함수는 `X_head/X_foot/X_num/X_note/X_solving/X_logic`. A2의 리본은 `ribbon()`(깊이 순서로 면+선), 경로는 `loop_path()`(고리 트로코이드)와 `torus_path()`.
- `knot.py`: 토러스 매듭 중심선을 따라 비틀리는 리본(또는 관). 깊이 순서로 흰 테두리와 선을 그려 위·아래 교차를 만든다.
- `cover.py`: 표지 배치.
