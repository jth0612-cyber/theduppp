# 인계: BULLPEN/INNING 한글 문서 조판 (2단 → 1단)

## 1. 목표
- 교재용 한글(HWP/HWPX) 페이지 중 **BULLPEN** 페이지를 **INNING** 페이지처럼 본문 폭 전체를 쓰는 레이아웃으로 바꾼다.
- 사용자 확정: **"일단 저거만 하면 됨"**. 레이아웃 작업은 2단 → 1단 변환만 한다.
- **남은 일: 폰트 변경.** 사용자가 다른 프로젝트에서 폰트 규칙을 이미 정해 두었다. 그 규칙을 받아 적용해야 한다(아래 5절).

## 2. 문제와 원인 (BULLPEN)
- 증상: 내용이 왼쪽 약 2/3에만 들어가 있고, 오른쪽에 세로 선이 그어져 있다.
- 원인(`Contents/section0.xml`):
  - `<hp:colPr type="NEWSPAPER" layout="MIRROR" colCount="2">`로 2단으로 되어 있다. 단 너비는 23119 : 8042(gap 1607) 비율이다.
  - 쪽 높이만 한 세로선 `<hp:line>`이 있다(폭 1, 높이 70015, 회색 #808080, 쪽 기준 오른쪽 정렬).
  - 제목 상자와 본문 분홍 상자는 1×1 표이고, 폭이 **32570**(왼쪽 단 폭)이다.
  - 상자 안의 표 ❶~❹는 폭이 30904, 29486, 29459, 29459이다.
- INNING은 원래 `colCount="1"`이고 상자 폭이 46176으로, 본문 전체 폭이다.

## 3. 적용한 수정 (`tools/fix_hwpx.py`)
1. `colPr` → `colCount="1"`, `layout="LEFT"`, `sameSz="1"`로 바꾸고 자식 `colSz`를 지운다.
2. 세로 구분선을 지운다. 조건: `<hp:line>` 중 폭 ≤ 10이고 높이 > 40000.
3. 본문 폭 = 쪽 폭 − 좌우 여백 = 61228 − 7937 − 7086 = **46205**.
   - 가장 넓은 표(32570)와의 차이 Δ = 13635.
   - 폭이 최대폭의 85% 이상인 표는 모두 `width += Δ`로 넓힌다.
   - 각 행의 `cellSz`는 원래 비율대로 다시 나누고, 반올림 오차는 마지막 칸에서 맞춘다.
4. `hp:linesegarray`(줄 배치 캐시)를 지워서, 한글이 새 폭에 맞춰 줄바꿈을 다시 하게 한다.
5. ZIP으로 다시 묶을 때 `mimetype`을 첫 항목에 **무압축(STORED)**으로 넣는다.
6. 1단 문서(INNING 등)에서는 `cols_was_multi=False`라서 표를 건드리지 않는다.

사용법:
```sh
python3 tools/fix_hwpx.py in.hwpx out.hwpx   # lxml 필요
```

### 남겨 둔 것 / 확인 필요
- 오른쪽 단에 있던 작은 **"TAG" 라벨**(3418 폭 표 + EMF 그림, 문단 기준 오른쪽 정렬)은 그대로 두었다. 1단으로 바뀌면서 오른쪽 여백 쪽으로 밀려났을 수 있다. 사용자가 아직 확인하지 않았다.
- 상자 높이는 그대로라서, 폭이 넓어진 만큼 아래쪽에 빈 공간이 생길 수 있다.
- 이 환경에서는 HWPX를 화면으로 그려볼 수 없었다(LibreOffice 미지원). 그래서 결과는 사용자가 한컴 앱에서 눈으로 확인해야 한다.

## 4. HWP → HWPX 변환
- `tools/build_hwp2hwpx.sh <작업폴더>`를 실행한다.
  - neolord0/hwp2hwpx를 클론하고 Maven으로 빌드한다. hwplib, hwpxlib는 Maven Central에서 받는다.
  - CLI `tools/HwpToHwpx.java`를 컴파일하고 `<작업폴더>/hwp2hwpx.sh`를 만든다.
- 사용: `<작업폴더>/hwp2hwpx.sh in.hwp out.hwpx` → `python3 tools/fix_hwpx.py out.hwpx final.hwpx`
- 필요한 것: JDK 8 이상(21에서 확인), Maven, GitHub clone 접근.
- 주의할 점:
  - 원본 pom이 Java 7 타깃이라 빌드 스크립트에서 8로 바꾼다.
  - 테스트 소스는 컴파일이 안 돼서 `-Dmaven.test.skip=true`로 건너뛴다.
  - 비공식 변환기라 수식, 그림이 완전히 같게 옮겨진다는 보장이 없다.
  - 결과는 hwpx로만 나온다. hwp가 필요하면 한글에서 "다른 이름으로 저장"으로 바꾼다.
  - 같은 문서라면, 한컴 앱이 직접 저장한 hwpx를 받아서 고치는 쪽이 원본에 더 가깝다.

## 5. 남은 작업: 폰트
현재 문서에 쓰인 폰트(글자 수 기준). 두 표 모두 `header.xml`의 `hh:fontface`를 기준으로 했다.

| 파일 | 주요 폰트 |
|---|---|
| BULLPEN 미시/거시 | 을유1945, Pretendard SemiBold, Pretendard, KoPubWorld바탕체 Light, Pretendard ExtraBold |
| INNING 헬륨 원자핵 | KoPubWorld바탕체 Light(본문), 을유1945, Pretendard |
| INNING 거리 측정 | 을유1945, KoPubWorld바탕체 Light, Pretendard |
| INNING 라디안 | KoPubWorld바탕체 Light, 을유1945, Pretendard, KoPubWorld돋움체 Light |
| INNING 스펙트럼 선 | 을유1945, KoPubWorld바탕체 Light, Pretendard |

- 폰트 목록은 `Contents/header.xml`의 `<hh:fontface lang="HANGUL|LATIN|...">` 안 `<hh:font face="...">`에 있다.
- 글자 모양(`<hh:charPr>`)은 `<hh:fontRef hangul=".." latin="..">`로 폰트 id를 참조한다.
- 바꾸는 방법은 두 가지다.
  - 같은 id의 `face` 이름만 바꾼다(역할별 1:1 매핑일 때 가장 간단하다).
  - `fontRef` id를 바꿔 다른 폰트를 가리키게 한다.
- 수식(`hp:equation`)은 폰트를 따로 지정하므로 따로 다룬다.
- **폰트 규칙은 사용자가 다른 프로젝트에서 정한 것을 받아서 적용한다.**

## 6. 작업 방식 (사용자 합의)
- 사용자가 휴대폰에서 파일을 **5개씩** 첨부한다(hwp 또는 hwpx).
- 파일마다 처리하는 것:
  - 2단(BULLPEN 등)이면 1단으로 변환한다.
  - 1단(INNING)이면 레이아웃은 그대로 둔다.
  - (추가 예정) 폰트를 변경한다.
- 지금까지 본 것과 구조가 다른 파일은 억지로 고치지 말고 사용자에게 알린다.
- 결과는 hwpx로 채팅에 보내고, 저장소 `hwp/`에도 커밋한다.
- 첨부 파일 이름은 한글이 `_`로 깨져서 들어온다. 문서 제목은 본문 텍스트(`hp:t`)의 앞부분으로 알아낸다.

## 7. 산출물 / 위치
- 저장소: `jth0612-cyber/theduppp`, 브랜치 `ccr-a3a8278e-8sxnuq`
- `hwp/BULLPEN_01_1단.hwpx`: 미시/거시 BULLPEN을 1단으로 바꾼 결과. 한컴 앱이 저장한 hwpx를 원본으로 썼다.
- `hwp/tools/fix_hwpx.py`, `hwp/tools/build_hwp2hwpx.sh`, `hwp/tools/HwpToHwpx.java`
- 1차 묶음 5개(INNING 4 + BULLPEN 1)를 처리했다.
  - INNING 4개는 이미 1단이라 변경하지 않았다.
  - BULLPEN은 위 산출물과 같은 문서다.
