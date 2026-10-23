# 인계: 통합과학 필기노트 "LOGIC BUILD 2" 조판 (2026-10-23 기준)

다른 계정·로컬 환경에서 이어서 작업하기 위한 문서예요. 먼저 **0절과 1절**만 읽으면 바로 돌릴 수 있어요.

---

## 0. 한눈에 보기
- **무엇:** 교재 필기노트 세 단원을 한글(HWPX) 파일로 자동 조판해요.
  - 단원은 단위변환, 산화환원, 효소예요.
  - 사용자가 만든 파이썬 생성기(`_생성스크립트`) 위에 이 저장소의 확장(`hwp/gen`)을 얹어서 만들어요.
- **결과물:** `hwp/final/`
  - `단위변환_필기노트_LOGIC BUILD 2.hwpx`
  - `산화환원_필기노트_LOGIC BUILD 2.hwpx`
  - `효소_필기노트_LOGIC BUILD 2.hwpx`
  - 보고서: `작업보고_LOGIC_BUILD_2.md` (1~6차 수정 내역), `작업보고_산화환원·효소.md` (원고에서 고치거나 보충한 곳)
  - LOGIC BUILD 1 파일 3개는 비교용으로 남겨 뒀어요.
- **다시 만들기:** `python hwp/build_all.py` (2절)
- **사용자가 확인하는 방법:** 한컴오피스(PC 또는 휴대폰)에서 열고 스크린샷을 보내 줘요.
  - 이 저장소에는 HWPX 렌더러가 없어요. 그래서 시안은 PIL로 그린 **근사 PNG**로 보여 줬어요.
- **사용자 작업 방식:**
  - 시안을 여러 개(보통 3~5개) 보고 번호로 고르는 걸 좋아해요. "시안 n개"라고 하면 그림으로 보여 주세요.
  - 이미 정한 디자인을 임의로 바꾸면 안 돼요. 예전에 Mini 예제 라벨을 멋대로 탭으로 바꿨다가 지적받았어요.
  - 한 곳을 고치면 문서 전체의 같은 요소에 모두 적용해야 해요. "왜 두 번 말하게 해"라고 지적받은 적이 있어요.
  - 문체는 원문을 보존하면서 친근한 반말로 써요. 풀이는 "문과 학생도 읽고 싶게" 짧고 명확하게 써요.

## 1. 로컬 준비 (Windows 노트북 기준)
1. 저장소를 클론하고 브랜치 `ccr-a3a8278e-8sxnuq`를 체크아웃해요.
2. Python 3.10 이상을 준비하고 `pip install -r hwp/requirements.txt`를 실행해요. 패키지는 lxml, pillow, numpy, fonttools예요.
3. **사용자 생성기 폴더**를 지정해요. 이 폴더는 저장소에 없어요. NAS 공유 "_생성스크립트"에 있는 사용자 원본이에요.
   - 노트북에 있는 경로를 환경 변수 `LB_GEN`에 넣어요.
     예: `set LB_GEN=T:\…\Logic Build\_생성스크립트`
   - 또는 `<저장소>/nas/Logic Build/_생성스크립트`에 복사해 두면 기본값으로 잡혀요. `nas/`는 .gitignore 대상이에요.
   - 필요한 파일: `build.py`, `lib.py`, `styles_more.py`, `unit_common.py`, `unit_B4.py`, `tpl/`(틀 hwpx 풀린 것), `wood_bin/`, `wood_band_light.jpg`, `bowtie_*.png`, `slat_spread.py` 등. 폴더 전체를 그대로 두면 돼요.
4. **폰트:** `hwp/final/LOGIC BUILD 2_사용폰트.zip`은 .gitignore 대상이라 저장소에는 없어요. 사용자에게는 따로 보냈어요.
   - 다시 만들려면 NAS의 `정태혁T_Line up_한글마스터 사용폰트` 폴더와 Roboto를 모으면 돼요.
   - 묶음에 없는 폰트는 사용자가 직접 설치해야 해요(9절): THE썸머캠프, GangwonEduAll(강원교육모두) Light/Bold, Eulyoo1945(을유1945).

## 2. 빌드
```
python hwp/build_all.py              # 세 단원 모두 → hwp/final/
python hwp/build_all.py redox        # 한 단원만 (unit | redox | enzyme)
```
`build_all.py`는 단원마다 다음 순서로 돌아요.
1. `hwp/gen/unit_<단원>.py raw.hwpx`
   - 사용자 생성기에 `lb.py`, `look.py`, `solbox.py`를 얹어 2단 원본을 만들어요.
   - 쪽 나누기도 이 단계에서 해요.
2. `hwp/tools/make_wide.py raw.hwpx hwp/art out.hwpx`
   - 2단을 1단으로 바꾸고, 세로선과 TAG를 지워요.
   - 본문 단 폭(325.7pt)인 상자를 전체 폭(462pt)으로 넓혀요.
   - 바탕을 흰색으로 바꾸고, 중단원 띠를 B-4 전체 폭으로 바꿔요.
3. `hwp/tools/check_wide.py`로 검사해요.
   - XML과 itemCnt, 2단·세로선·TAG·옛 바탕색·남은 마크업이 모두 0인지 확인해요.

단원별 원고 스크립트:
- `unit_unit.py` (단위변환): 사용자 원고 `_생성스크립트/unit_B4.py`를 그대로 읽어 다시 짜요. 원고 문장은 거기서 고쳐요.
- `unit_redox.py`, `unit_enzyme.py`: 원고를 DSL로 옮긴 것이에요. 원고 덤프 도구는 `gen/extract.py`, 그림은 `gen/img/`에 있어요.
- 풀이 문장은 `sol_redox.py`, `sol_enzyme.py`, `sol_unit.py`에 따로 있어요(5절).

## 3. 파일 지도
| 경로 | 역할 |
|---|---|
| `hwp/build_all.py` | 전체 빌드 |
| `hwp/gen/lb.py` | 생성기 확장 |
| `hwp/gen/look.py` | **요소 디자인** (사용자가 고른 시안을 구현, 6절). build.py의 블록 함수를 바꿔 끼워요 |
| `hwp/gen/solbox.py` | 풀이 상자(시안 E1)와 표 만들기 `grid()`, 새 문단 모양 `pp()`, 칩 `chip_runs()` |
| `hwp/gen/sol_*.py` | 다시 쓴 풀이, 정답, 썸네일 워딩에 맞춘 질문 |
| `hwp/gen/kice_map.py`, `prep_kice.py`, `img/kice/` | 기출 썸네일 대조표와 출처 라벨을 붙인 그림 (`index.json`) |
| `hwp/gen/solbox_samples.py` | 풀이 상자 시안 비교용 hwpx |
| `hwp/tools/make_wide.py`, `make_final_lib.py`, `check_wide.py` | 1단 변환과 검사 |
| `hwp/tools/make_art.py`, `emf_poly.py` | 띠와 TAG EMF 생성. 결과는 `hwp/art/`에 있어요 (`bar_B4_wide.emf`를 씀) |
| `hwp/tools/*_mock*.py` | 시안 근사 PNG (`preview/`). 실행: `python <파일> <폰트폴더> <출력폴더>` |
| `hwp/tools/synoshare.py` | 시놀로지 공유 링크 목록·내려받기 (8절) |
| `hwp/tools/make_final.py`, `tag_bar_variants.py` | LOGIC BUILD 1(2단 + TAG) 마무리용. 지금은 쓰지 않아요 |
| `hwp/tools/fix_hwpx.py`, `build_hwp2hwpx.sh`, `HwpToHwpx.java` | 초기 작업(BULLPEN 2단→1단, hwp→hwpx 변환) |
| `hwp/preview/` | 지금까지 보여 준 시안 그림과 비교용 hwpx |

## 4. 생성기 확장의 핵심 개념
- **HWPUNIT:** 1/100pt 단위예요. 본문 전체 폭은 46205(462pt)이고, 예전 본문 단 폭은 32570이에요.
- **마크업:**
  - `==형광==`
  - `**강조**`: 지금은 형광펜으로 통일했어요(E12-C).
  - `~~파란 펜~~`
  - `^{위첨자}`, `_{아래첨자}`
  - `⟦수식|폭|높이⟧`
  - `⟪그림경로|폭|높이⟫`: 경로는 `hwp/gen` 기준 상대 경로예요.
  - `«날개 주석»`: 지금은 빼고 출력해요.
- **블록(`lb.Block`)과 높이 어림:**
  - 블록마다 높이(pt)를 어림해서 앞쪽 3쪽만 계산으로 나눠요.
  - 4쪽부터는 **중단원 띠(bar)에서만 강제로 쪽을 나눠요.** 나머지는 한글이 흐름대로 배치해요(`lb.FLOW_FROM`). 빈 공간이 크게 남던 문제 때문에 이렇게 바꿨어요.
  - 소제목은 '다음 문단과 함께'로 설정했어요.
  - 풀이 상자, 탭, 표는 표 속성 `pageBreak="NONE"`으로 쪽 중간에서 쪼개지지 않게 했어요.
- **새 문단 모양:**
  - `solbox.pp(이름, align, left, intent, prev, nxt, ls, right, bf, off, keep)`로 만들어요. 문단 테두리와 배경은 borderFill로 지정해요.
  - id는 70번부터 매겨지고, `B.NEWPP`에 튜플 키로 들어가요.
- **칩:** 글자 배경(`shade`)으로 만든 라벨이에요. 예: `STEP 1`, `Q1`, `결론`, `TIP`.
- **글꼴 id (틀 header 기준):**
  - 6 Pretendard
  - 8 Pretendard ExtraBold
  - 10 Pretendard Medium
  - 11 Pretendard SemiBold
  - `B.HAND`(12) THE썸머캠프: 본문 손글씨
  - 15 GangwonEduAll Light: THEME·POINT 제목
- **스타일:** `use_style('final')`, `FONTS[0]=(12,'THE썸머캠프')`, `FONTS[3]=(15,'GangwonEduAll Light')`.
- **사용자 생성기 파일은 고치지 않아요.** 바꿀 게 있으면 lb.py나 look.py에서 덮어써요(monkey patch).

## 5. 내용 원칙과 풀이
- 원고의 문장은 빼거나 요약하지 않고 반말로만 옮겨요. 원고에서 고친 곳은 `final/작업보고_산화환원·효소.md`에 적어 두었어요.
- **풀이 형식:** 산화환원 22개, 효소 46개, 단위변환 10개를 다시 썼어요. 줄마다 다음 표시를 써요.
  - `'# 단계 제목'`: `STEP n`, `Logic n`, `1.`로 시작하면 칩이 돼요.
  - `'= 식 한 줄'`
  - `'> 결론'`: 상자 맨 아래 오른쪽에 `결론` 칩으로 나가요.
  - 표시 없는 줄은 설명 문장이에요.
- 정답(Ans) 줄은 없앴어요. 정답은 `결론` 줄 하나로만 보여 줘요.
- **기출 (Arranged KICE):**
  - NAS 썸네일 폴더 `Squeeze_2028학년도_기출`(공유 ID `MhoGdYdiL`)과 출처 이름으로 대조해서 18개를 바꿔 넣었어요. 출처 라벨을 붙였고, 크기는 LOGIC BUILD 1 기준 70%예요.
  - 썸네일이 없는 3개는 원고 그림을 그대로 썼어요: 산화환원 2025 수능 13번 화1, 2019 9월 20번 화1, 효소 2016 수능 7번 생2.
  - 워딩이 바뀐 2017 9월 6번 화1은 질문과 풀이를 새로 썼어요(`sol_redox.QS['K7']`).
  - 핵심 로직 상자는 없앴어요.

## 6. 확정된 디자인 (사용자 선택)
| 요소 | 확정 |
|---|---|
| 쪽 | 1단 전체 폭. TAG, 각주, 세로선 없음. 바탕 흰색 |
| 중단원 띠 | B-4 (`art/bar_B4_wide.emf`) |
| THEME / POINT | 제목은 무조건 한 줄(글자를 줄여서라도). THEME 왼쪽 끝 = POINT 점선 왼쪽 끝. 두 라벨 칸 폭이 같아서(`LABEL_W` 9500) 제목이 세로로 맞아요. **POINT 줄은 처음 크기의 105%** (150%로 키웠다가 그 70%로 되돌림) |
| 형광펜 | 스모키 라일락 `#DDD1E8`. 빨간 펜(`**`)도 형광펜으로 통일 |
| 본문 줄 간격 | 그대로(168%). 블록 사이 간격만 넓힘 |
| 설명 줄 | **N2**: → 화살표, 둘째 줄부터 매달린 들여쓰기, 세로선 없음. 하위 항목은 – |
| 번호 소제목 | **H5**: 아주 옅은 띠 `#FAF7F3` + 진한 번호 칩 + Pretendard SemiBold |
| 본문 STEP·Logic | **E04-A**: 진한 칩 + 제목 |
| Mini 예제 라벨 | 틀의 **브라운 글자 + 밑줄** 그대로 (`B.small_bar`). 탭으로 바꾸지 말 것 |
| 풀이 상자 | **E1**: 진한 탭, 얇은 테두리. 머리 글자는 Mini 예제 `Sol.`, Arranged KICE `Essentials` |
| 풀이 상자 안 | STEP 칩 브라운(E05-A), 식 줄 들여쓰기(E06-A), 결론은 오른쪽 `결론` 칩(E07-B) |
| Arranged KICE 머리 | **K1**: 진한 탭 `Arranged KICE n` + 다시 묶은 질문 |
| 발문 | **P5**: 얇은 베이지 테두리 상자(바탕 없음). 조건이 있으면 조건을 상자에 넣고 질문은 상자 아래에, 조건이 없으면 질문을 상자 안에 둬요. 질문 앞 브라운 `Q`/`Q1` 칩, 10.5pt. 조건 (가)(나)는 굵은 라벨 + 들여쓰기 |
| Intro·핵심·한 줄 정리 | **E10-B**: 위아래 진한 선 |
| 표 | **T3**: 첫 열 베이지 칸 + 브라운 글자, 머리 행 브라운 글자 + 밑줄 |
| TIP | **E13-A**: 라일락 TIP 칩 + 파란 손글씨 |
| 반응식 줄 | 가운데 정렬, **음영 없음** |
| 색 | 진갈색 `#3A241D`, 브라운 `#A9623A`, 베이지 `#F7F2EC`, 라일락 `#DDD1E8`/`#F1ECF6` 네 계열만 |

## 7. 남은 일
1. **한글에서 실제 모양 확인:** 쪽 넘침, 칩 크기, 제목 한 줄 맞춤(글자 폭을 어림해서 정해서 넘칠 수 있어요).
2. 썸네일 원문 오타: 2016학년도 6월 8번 생2의 "그림**은** (가)는…". 사용자가 썸네일을 고치면 `prep_kice.py`를 다시 실행해요.
3. 원고 확인 요청이 남아 있어요(작업보고_산화환원·효소.md).
   - 산화환원 마지막 KICE 2개의 정답
   - 대단원 표기(변화와 다양성 / 시스템과 상호작용)
4. 폰트 3종(9절)이 노트북에 설치돼 있어야 화면이 맞아요.

## 8. NAS (시놀로지 THedu_NAS, `jth4377.synology.me`)
- 사용자가 gofile.me 공유 링크와 비밀번호를 줘요. **비밀번호는 저장소에 적지 않아요.**
- `python hwp/tools/synoshare.py ls <공유ID> <비번>` / `get <공유ID> <비번> <저장폴더> [접두어|glob …]`
- 요령(겪은 문제):
  - 로그인은 `SYNO.Core.Sharing.Login`에 JSON 문자열로 보내요.
  - 이후 요청에는 헤더 `X-SYNO-SHARING`을 붙여요.
  - `SYNO.FolderSharing.List`의 `folder_path`는 `/<공유폴더이름>`이어야 해요. 이 이름은 `Initdata`의 `Private.filename`에서 얻어요.
- 공유 ID:
  - `v9aQVILEy` "Logic Build" (약 5GB)
  - `YpF9E7rp6` "_생성스크립트"
  - `MhoGdYdiL` "Squeeze_2028학년도_기출" (썸네일 756개. 파일 이름 = `단원_순번_주요/비주요_학년·시험·번호·과목.png`)
- 로컬에서는 사용자 PC에 NAS가 연결돼 있어요(예: `T:\통합과학_중요파일\…`). 그러면 공유 링크 없이 바로 경로를 쓰면 돼요.

## 9. 폰트
| 폰트 | 쓰는 곳 | 구하는 곳 |
|---|---|---|
| THE썸머캠프 | 본문 손글씨 전체 | 배포처를 못 찾음. 사용자에게 파일을 받아야 해요 |
| GangwonEduAll Light/Bold | THEME·POINT 제목, 띠 제목 | 강원특별자치도교육청 '강원교육 서체' (눈누 noonnu.cc/font_page/802) |
| Eulyoo1945 | 일부 라벨 | 을유문화사 (eulyoo.co.kr/member/font.html, 눈누 font_page/621) |
| Pretendard, KoPubWorld, Hahmlet, MBC 1961, 나눔스퀘어, 학교안심 수수깡, 강원교육현옥샘, Roboto | 라벨, 칩, 제목 | 폰트 묶음 zip에 들어 있어요 |
| Cambria Math, HyhwpEQ | 수식, 영문 | Windows·Office·한글에 기본 포함 |

## 10. 지난 일 요약 (시간 순)
1. BULLPEN 2단→1단(`fix_hwpx.py`), hwp→hwpx 변환기(`build_hwp2hwpx.sh`)를 만들었어요.
2. NAS를 연결하고 "Logic Build" 공유를 전부 내려받았어요.
3. **LOGIC BUILD 1:** TAG C(좌우 대칭), 중단원 띠 B-4, 바탕 `#FAF5EE`, 라일락 형광펜을 적용했어요. `make_final.py`, `make_art.py`로 만들었어요.
4. 산화환원·효소 원고를 단위변환 형식으로 자동 조판했어요(`unit_redox.py`, `unit_enzyme.py`).
5. **LOGIC BUILD 2:** 1단 전체 폭, 흰 바탕, 제목 한 줄, 기출 70%로 바꿨어요.
6. 풀이를 전부 다시 썼고, 풀이 상자 시안 A~E와 E1~E5 중 E1을 골랐어요. 이름은 Essentials로 정했어요.
7. 기출 썸네일을 대조해서 바꿔 넣었어요.
8. 요소별 시안(E01~E14 → T/H/N → P)을 차례로 골랐어요.
9. POINT 크기 조정, 발문 Q 칩, Ans 삭제, 음영 제거를 했어요.
