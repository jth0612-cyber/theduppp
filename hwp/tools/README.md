# INNING / BULLPEN 조판 도구 (HWP 5.0 바이너리 직접 수정)

한글 없이 .hwp 파일을 직접 고친다. 필요: Python 3, `pip install olefile`.

순서 (파일 하나당):
```sh
python3 hwp_fonts2.py in.hwp a.hwp                       # 확정 폰트 적용 (모든 INNING/BULLPEN)
# BULLPEN이고 측주 단이 비어 있을 때만 1단으로 변환:
python3 bullpen_layout.py a.hwp inning_ref.hwp b.hwp     # 1단, TAG·세로선 제거, 표 폭 확대 (INNING 파일을 기준으로 씀)
python3 bullpen_finish.py b.hwp inning_ref.hwp c.hwp     # 줄 폭을 INNING 폭으로, 측주 단 빈 줄 제거
python3 fit_inner_tables.py c.hwp out.hwp                # 상자 안 전폭 표를 상자 안쪽 폭에 정확히 맞춤
```

확정 폰트 (hwp_fonts2.py RULES):
| 층위 | 폰트 |
|---|---|
| INNING 라벨 24pt | Pretendard + 굵게 (원본) |
| INNING 주제 제목 14pt | SUIT + 굵게 (= SUIT Bold) |
| INNING 소제목 ❶❷ 10.5pt | 나눔바른고딕 + 굵게 |
| INNING 본문 10.5pt | KoPubWorld바탕체 Light (원본) |
| BULLPEN 라벨 11pt | Pretendard Black |
| BULLPEN 제목 10pt | SUIT + 굵게 |
| BULLPEN 지시문 8pt | SUIT Medium (표 본문과 글자 모양이 같아 복제해 분리) |
| BULLPEN 소제목 ❶❷ 9pt | Hahmlet SemiBold |
| BULLPEN 표 8pt | 본문 SUIT, 머리글 SUIT SemiBold, 굵게는 SUIT + 굵게 |

주의: SUIT Bold 파일은 윈도우에 'SUIT' 글꼴의 굵게로 등록되므로 글꼴 이름은 'SUIT' + 굵게로 넣어야 한다.
