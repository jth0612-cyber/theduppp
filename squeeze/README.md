# Squeeze 내지·표지 리디자인 시안

## 결과물 (`out/`)
- `A_루버.pdf`, `B_수평선.pdf`, `C_면과질감.pdf`: 원본 내지 4~7쪽(Logic Check + A-1, A-2 펼침면)에서 틀 요소만 지우고 새 틀을 벡터로 그린 시안
- `비교_45쪽.png`, `비교_67쪽.png`: 원본과 시안 3종 펼침면 비교
- `비교_부분확대.png`: 상단바, 문항 번호, Solving 머리, 하단 확대 비교
- `표지_매듭.pdf` / `.png` / `_확대.png`: (3,7) 토러스 매듭 리본 표지 시안

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

- `sq_variants.py`: 틀 지우기(redaction) + 시안 A/B/C 그리기. 시안별 함수는 `X_head/X_foot/X_num/X_note/X_solving/X_logic`.
- `knot.py`: 토러스 매듭 중심선을 따라 비틀리는 리본(또는 관). 깊이 순서로 흰 테두리와 선을 그려 위·아래 교차를 만든다.
- `cover.py`: 표지 배치.
