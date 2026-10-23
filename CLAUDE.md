# theduppp — 통합과학 필기노트 LOGIC BUILD 조판

- 작업 인계 문서: **`hwp/HANDOFF.md`** (먼저 0~2절, 확정 디자인은 6절, 남은 일은 7절)
- 빌드: `pip install -r hwp/requirements.txt` → `LB_GEN=<사용자 _생성스크립트 폴더>` → `python hwp/build_all.py`
- 결과: `hwp/final/*_LOGIC BUILD 2.hwpx`
- 사용자는 한국어로 대화하고, 시안을 번호로 골라요. 이미 정한 디자인은 임의로 바꾸지 마세요.
- 같은 요소는 문서 전체에 한꺼번에 적용하세요.
- 사용자 생성기(`_생성스크립트`)의 파일은 직접 고치지 말고, `hwp/gen/lb.py`나 `look.py`에서 덮어쓰세요.
- NAS 비밀번호 같은 비밀 정보는 저장소에 적지 마세요.
