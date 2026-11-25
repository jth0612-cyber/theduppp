"""채점기 엑셀(OMR) 읽기 — 조교 시스템 인계 문서 4장 규칙을 그대로 따른다.

입력: .xlsx 또는 .csv(UTF-8, 안 되면 EUC-KR). .xls 는 읽지 않는다.
칸 자동 판별: 앞 10행 중 (서로 다른 문항 번호 칸 수 + 열쇠말 수 × 3)이 가장 큰 행이 머리글.
  문항 칸: 1, 1번, 문1, Q1, #1   이름: 이름·성명(없으면 한글 2~4자 값이 가장 많은 칸)
  번호: 수험·학번·번호·응시·ID·코드·고유   전화: 전화·연락처·휴대·핸드폰·폰·뒷자리
  점수: 점수·총점·득점   틀린문항: 틀린·오답   반: 반·학급
  정답 행: 앞 4칸 중 하나가 정답·답·KEY·답안·모범답안   배점 행: 앞 4칸 중 하나가 배점
답안 모드(파일 전체로 판단): 고른 번호 / 1·0 / O·X / X만 / 틀린문항 칸
결과 답안 문자열: 문항마다 '1'~'5' 고른 번호, 'R' 맞음(고른 번호 기록 없음), '0' 틀림(고른 번호 없음).
둘째 시트 '문항정보'가 있으면 문항번호·정답·배점·단원·핵심개념·… 을 함께 읽는다."""
import csv
import io
import re

CIRCLED = {"①": "1", "②": "2", "③": "3", "④": "4", "⑤": "5"}
KEY_WORDS = {"정답", "답", "key", "답안", "모범답안"}
INFO_COLS = {"문항번호": "no", "번호": "no", "문항": "no", "정답": "answer", "배점": "points", "단원": "unit",
             "핵심개념": "concept", "요구역량": "skill", "난이도": "difficulty", "문항요약": "summary",
             "오답시의미": "misconception", "문항형식": "format", "선지구성": "options", "보기함정": "traps",
             "선지분석": "distractors"}


class OmrError(ValueError):
    pass


def _norm(v):
    return re.sub(r"\s+", "", str(v if v is not None else "")).lower()


def _sheets(raw, filename):
    name = (filename or "").lower()
    if name.endswith(".csv"):
        for enc in ("utf-8-sig", "cp949"):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise OmrError("CSV 글자를 읽지 못했습니다. UTF-8 로 저장해 주세요.")
        return [list(r) for r in csv.reader(io.StringIO(text))], None
    if name.endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook
        try:
            wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
        except Exception:
            raise OmrError("엑셀 파일을 열지 못했습니다. .xlsx 로 다시 저장해 올려 주세요.")
        val = lambda ws: [["" if v is None else v for v in r] for r in ws.iter_rows(values_only=True)]
        main = val(wb.worksheets[0])
        info = next((val(ws) for ws in wb.worksheets[1:] if _norm(ws.title) == "문항정보"), None)
        wb.close()
        return main, info
    if name.endswith(".xls"):
        raise OmrError(".xls 는 읽지 않습니다. 엑셀에서 .xlsx 로 다시 저장해 올려 주세요.")
    raise OmrError("엑셀(.xlsx) 또는 CSV 파일만 올릴 수 있습니다.")


def item_no(v):
    """머리글 '1', '1번', '문1', 'Q1', '#1', 1.0 → 1"""
    if isinstance(v, (int, float)) and not isinstance(v, bool) and float(v).is_integer() and 1 <= v <= 100:
        return int(v)
    m = re.fullmatch(r"(?:문|q|#|문항)?(\d{1,3})(?:번)?", _norm(v))
    return int(m.group(1)) if m and 1 <= int(m.group(1)) <= 100 else None


def _kind_of(h):
    k = _norm(h)
    if not k or item_no(h):
        return None
    if k in ("이름", "성명", "학생", "학생이름"):
        return "name"
    if any(w in k for w in ("전화", "연락처", "휴대", "핸드폰", "뒷자리")) or k.endswith("폰"):
        return "phone"
    if any(w in k for w in ("수험", "학번", "번호", "응시", "id", "코드", "고유")):
        return "number"
    if any(w in k for w in ("점수", "총점", "득점")):
        return "score"
    if any(w in k for w in ("틀린", "오답")):
        return "wrong"
    if k in ("반", "학급", "반이름", "반명"):
        return "cls"
    if k in ("답안", "답", "마킹", "omr", "학생답안"):
        return "answers"
    return None


def _header(rows):
    best, best_i = -1, None
    for i, r in enumerate(rows[:10]):
        nos = {item_no(v) for v in r if item_no(v)}
        kws = sum(1 for v in r if _kind_of(v))
        sc = len(nos) + kws * 3
        if sc > best and (nos or kws):
            best, best_i = sc, i
    if best_i is None:
        raise OmrError("머리글 줄을 찾지 못했습니다. 첫 줄에 이름, 수험번호, 문항 번호(1, 2, 3 …)를 적어 주세요.")
    return best_i


def _txt(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def _is_hangul_name(v):
    return bool(re.fullmatch(r"[가-힣]{2,4}", _txt(v)))


def read(raw, filename):
    """파일을 읽어 표 구조만 돌려준다 (채점은 grade)."""
    rows, info_rows = _sheets(raw, filename)
    if not rows:
        raise OmrError("빈 파일입니다.")
    hi = _header(rows)
    head = rows[hi]
    cols, items = {}, {}
    for i, h in enumerate(head):
        no = item_no(h)
        if no:
            items.setdefault(no, i)
            continue
        k = _kind_of(h)
        if k and k not in cols:
            cols[k] = i
    body = rows[hi + 1:]
    key_row = points_row = None
    data = []
    for ri, r in enumerate(body, start=hi + 2):
        first = {_norm(v) for v in r[:4]}
        if first & KEY_WORDS and key_row is None:
            key_row = r
            continue
        if "배점" in first and points_row is None:
            points_row = r
            continue
        if not any(_txt(v) for v in r):
            continue
        data.append((ri, r))
    if "name" not in cols:                                    # 이름 칸이 없으면 한글 2~4자 값이 가장 많은 칸
        counts = {}
        for _, r in data:
            for i, v in enumerate(r):
                if i not in items.values() and _is_hangul_name(v):
                    counts[i] = counts.get(i, 0) + 1
        if counts:
            cols["name"] = max(counts, key=counts.get)
    get = lambda r, k: _txt(r[cols[k]]) if k in cols and cols[k] < len(r) else ""
    if not items and "answers" in cols:                      # 문항 칸 대신 '답안' 한 칸에 이어 적은 형식: 14352 53411 …
        split = lambda v: [ch for ch in re.sub(r"[\s,./-]", "", _txt(v))]
        width = max([len(split(r[cols["answers"]])) for _, r in data if cols["answers"] < len(r)] or [0])
        items = {i: i for i in range(1, width + 1)}
        points_row = None
        conv = []
        for ri, r in data:
            chars = split(r[cols["answers"]]) if cols["answers"] < len(r) else []
            conv.append((ri, r, {i + 1: ch for i, ch in enumerate(chars)}))
        if key_row is not None:
            kc = split(key_row[cols["answers"]]) if cols["answers"] < len(key_row) else []
            key_row = None
            pre_key = {i + 1: ch for i, ch in enumerate(kc) if ch.strip()}
        else:
            pre_key = {}
    else:
        conv = [(ri, r, None) for ri, r in data]
        pre_key = None
    out = []
    for ri, r, cells in conv:
        out.append({"row": ri, "name": get(r, "name"), "number": get(r, "number"), "phone": get(r, "phone"),
                    "cls": get(r, "cls"), "score": get(r, "score"), "wrong": get(r, "wrong"),
                    "cells": cells if cells is not None else {no: (r[c] if c < len(r) else "") for no, c in items.items()}})
    if not out:
        raise OmrError("학생 줄이 없습니다.")
    n = max(items) if items else 0
    key = {no: _txt(key_row[c]) for no, c in items.items() if c < len(key_row) and _txt(key_row[c])} if key_row else (pre_key or {})
    points = {}
    if points_row:
        for no, c in items.items():
            try:
                points[no] = float(_txt(points_row[c]))
            except (ValueError, IndexError):
                pass
    return {"rows": out, "n": n, "items": sorted(items), "has_items": bool(items), "has_wrong": "wrong" in cols,
            "key": key, "points": points, "info": parse_info(info_rows) if info_rows else {}}


def parse_info(rows):
    """'문항정보' 시트: 머리글 줄 아래로 문항마다 한 줄. {문항번호: {answer, points, unit, …}}"""
    for hi, head in enumerate(rows[:5]):
        cols = {i: INFO_COLS[_norm(h)] for i, h in enumerate(head) if _norm(h) in INFO_COLS}
        if "no" in cols.values():
            break
    else:
        return {}
    out = {}
    for r in rows[hi + 1:]:
        d = {f: _txt(r[i]) for i, f in cols.items() if i < len(r)}
        no = item_no(d.get("no", ""))
        if no:
            d.pop("no", None)
            out[no] = {k: v for k, v in d.items() if v}
    return out


# ---------------------------------------------------------------- 답안 해석
def choice(v):
    """한 칸 → '1'~'5' 또는 '' (무응답·두 개 마킹·판독 불가)"""
    s = _txt(v)
    s = "".join(CIRCLED.get(ch, ch) for ch in s)
    return s if s in ("1", "2", "3", "4", "5") else ""


def mode_of(parsed, has_key):
    if not parsed["has_items"]:
        if parsed["has_wrong"]:
            return "wrong"
        raise OmrError("문항 칸(1, 2, 3 …)이나 '틀린문항' 칸이 없습니다.")
    vals = [_norm(v) for r in parsed["rows"] for v in r["cells"].values() if _txt(v)]
    if any(v in ("o", "○", "◯") for v in vals):
        return "ox"
    if vals and all(v in ("x", "×") for v in vals):
        return "x"
    if vals and all(v in ("0", "1") for v in vals) and not has_key:
        return "10"
    return "choice"


def parse_wrong(text, n):
    """'3,7' · '3/7' · '3(2),7(4)' · '7:4, 3(2)' · '없음' → {문항: 고른 번호 또는 ''}. 빈칸은 None(미입력)."""
    t = _txt(text)
    if not t:
        return None
    if t in ("없음", "만점", "-"):
        return {}
    out = {}
    for part in re.split(r"[,/\s]+", t):
        if not part:
            continue
        m = re.fullmatch(r"(\d{1,3})(?:\((\d)\)|:(\d))?", part)
        if not m:
            raise OmrError(f"틀린문항 '{t}'을 읽지 못했습니다.")
        no = int(m.group(1))
        if not 1 <= no <= n:
            raise OmrError(f"틀린문항 {no}번은 문항 범위(1~{n}) 밖입니다.")
        out.setdefault(no, m.group(2) or m.group(3) or "")
    return out


def grade(parsed, key, n, mode):
    """줄마다 답안 문자열. key: 문항 순서대로 정답(없으면 None 목록)."""
    out = []
    for r in parsed["rows"]:
        if mode == "wrong":
            w = parse_wrong(r["wrong"], n)
            if w is None:
                out.append(None)
                continue
            ans = "".join((w[i] or "0") if i in w else "R" for i in range(1, n + 1))
        else:
            chars = []
            for i in range(1, n + 1):
                v = r["cells"].get(i, "")
                if mode == "choice":
                    c = choice(v)
                    chars.append(c if c else "0")
                elif mode == "10":
                    chars.append("R" if _norm(v) == "1" else "0")
                elif mode == "ox":
                    chars.append("R" if _norm(v) in ("o", "○", "◯") else "0")
                else:
                    chars.append("0" if _norm(v) in ("x", "×") else "R")
            blank = all(not _txt(r["cells"].get(i, "")) for i in range(1, n + 1))
            if blank and mode != "x":                         # 문항 칸이 모두 빔 = 시험 안 봄
                out.append(None)
                continue
            ans = "".join(chars)
        out.append(ans)
    return out


def template(n, students, info=None):
    """빈 양식 .xlsx. OMR 시트: 이름·수험번호·학생코드·반·1…N, 정답 줄과 배점 줄. 문항정보 시트. 작성 예시 시트."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    bold, fill, keyfill = Font(bold=True), PatternFill("solid", fgColor="E7EFEA"), PatternFill("solid", fgColor="FFF4D6")
    wb = Workbook()
    ws = wb.active
    ws.title = "OMR"
    ws.append(["이름", "수험번호", "학생코드", "반"] + list(range(1, n + 1)))
    ws.append(["정답", "", "", ""])
    ws.append(["배점", "", "", ""])
    for name, num, code, cls in students:
        ws.append([name, num, code, cls])
    for c in ws[1]:
        c.font, c.fill, c.alignment = bold, fill, Alignment(horizontal="center")
    for row in (2, 3):
        for c in ws[row]:
            c.fill = keyfill
        ws.cell(row, 1).font = bold
    for col, w in zip("ABCD", (10, 12, 10, 18)):
        ws.column_dimensions[col].width = w
    for i in range(5, n + 5):
        ws.column_dimensions[get_column_letter(i)].width = 4.5
    ws.freeze_panes = "E4"
    inf = wb.create_sheet("문항정보")
    heads = ["문항번호", "정답", "배점", "단원", "핵심개념", "요구역량", "난이도", "오답시의미", "문항형식", "선지구성", "보기함정", "선지분석"]
    inf.append(heads)
    for i in range(1, n + 1):
        d = (info or {}).get(str(i)) or (info or {}).get(i) or {}
        inf.append([i] + [d.get(INFO_COLS[h], "") for h in heads[1:]])
    for c in inf[1]:
        c.font, c.fill = bold, fill
    for col, w in zip("ABCDEFGHIJKL", (8, 6, 6, 14, 16, 12, 6, 24, 8, 26, 40, 40)):
        inf.column_dimensions[col].width = w
    ex = wb.create_sheet("작성 예시")
    for line in (
        ["OMR 시트"],
        ["1. 채점기 엑셀을 그대로 붙여 넣어도 됩니다. 이름과 수험번호 칸, 문항 번호 칸(1, 1번, 문1, Q1)을 알아서 찾습니다."],
        ["2. 문항 칸에는 학생이 마킹한 번호(1~5)를 적습니다. 빈칸, 두 개 마킹, *는 무응답(오답)입니다. O/X 나 1/0 으로 적어도 됩니다."],
        ["3. '정답' 줄에 정답을 적습니다. 복수 정답은 2,4  전원 정답은 *  정답 없음(전원 오답)은 -. 정답 줄이 없으면 문항정보 시트의 정답을 씁니다."],
        ["4. '배점' 줄이 비면 문항정보 시트의 배점, 그것도 비면 1점입니다. 점수 = 맞힌 문항 배점의 합."],
        ["5. 수험번호 = 학부모 휴대폰 번호에서 010을 뺀 8자리. 없으면 학생코드, 그것도 없으면 이름으로 찾습니다."],
        ["6. 문항 칸이 모두 빈 줄(시험을 안 본 학생)은 건너뜁니다. 같은 회차를 다시 올리면 그 학생 결과는 새 내용으로 바뀝니다."],
        [],
        ["문항정보 시트 (선택. 채우면 오답 유형 분석과 학부모 문자가 자세해집니다)"],
        ["문항형식: 합답형 / 일반"],
        ["선지구성(합답형): ①ㄱ ②ㄴ ③ㄱ,ㄷ ④ㄴ,ㄷ ⑤ㄱ,ㄴ,ㄷ"],
        ["보기함정(합답형): ㄱ(O): 반대로 판단하게 되는 이유 [개념 부족] / ㄴ(X): 이유 [자료 해석]"],
        ["선지분석(일반): 2번: 이 선지를 고르게 되는 이유(조건 독해) / 3번: 이유(계산 실수)"],
        ["오답 유형: 개념 부족, 자료 해석, 조건 독해, 계산 실수, 시간 부족, 기타"],
    ):
        ex.append(line)
    ex["A1"].font = bold
    ex["A9"].font = bold
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
