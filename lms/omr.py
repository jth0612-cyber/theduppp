"""복테·모의고사 OMR 결과 엑셀 읽기와 빈 양식 만들기.

양식: 첫 줄(머리글)에 '학생코드', '이름', 그리고 문항 번호 1, 2, 3 … N.
  - 문항 칸에는 학생이 고른 번호(1~5). 비우거나 다른 값이면 무응답(오답 처리).
  - 문항 칸 대신 '답안' 칸 하나에 '13524 21435 …'처럼 이어 적어도 된다.
  - 문항 칸이 모두 빈 줄(시험을 안 본 학생)은 건너뛴다.
  - 학생은 학생코드로 찾고, 코드가 없으면 이름(같은 이름이 둘 이상이면 '반' 칸까지)으로 찾는다.
.xlsx 와 .csv(쉼표) 를 받는다. 머리글은 처음 10줄 안에 있으면 된다."""
import csv
import io
import re

CODE_KEYS = ("학생코드", "코드", "수험번호", "학번", "아이디", "id")
NAME_KEYS = ("이름", "성명", "학생")
CLASS_KEYS = ("반", "학급", "반이름")
ANSWER_KEYS = ("답안", "답", "마킹", "omr")


def _cells(raw, filename):
    name = (filename or "").lower()
    if name.endswith(".csv"):
        text = raw.decode("utf-8-sig", errors="replace")
        return [list(r) for r in csv.reader(io.StringIO(text))]
    if name.endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
        ws = wb.worksheets[0]
        rows = [["" if v is None else v for v in r] for r in ws.iter_rows(values_only=True)]
        wb.close()
        return rows
    raise ValueError("엑셀(.xlsx) 또는 CSV 파일만 올릴 수 있습니다.")


def _norm(v):
    return re.sub(r"\s+", "", str(v)).lower()


def _item_no(v):
    """머리글 '1', '1번', 'Q1', 1.0 → 1"""
    if isinstance(v, (int, float)) and float(v).is_integer():
        return int(v)
    m = re.fullmatch(r"(?:q|문항)?(\d{1,2})(?:번)?", _norm(v))
    return int(m.group(1)) if m else None


def _choice(v):
    if isinstance(v, (int, float)) and float(v).is_integer() and 1 <= int(v) <= 5:
        return str(int(v))
    s = str(v).strip()
    circled = {"①": "1", "②": "2", "③": "3", "④": "4", "⑤": "5"}
    s = circled.get(s, s)
    return s if s in ("1", "2", "3", "4", "5") else "0"


def read(raw, filename, n_items):
    """[{'row': 줄 번호, 'code': str, 'name': str, 'cls': str, 'answers': 'n_items 글자'}]"""
    rows = _cells(raw, filename)
    for hi, head in enumerate(rows[:10]):
        keys = [_norm(h) for h in head]
        col = lambda names: next((i for i, k in enumerate(keys) if k in names), None)
        c_code, c_name, c_cls, c_ans = col(CODE_KEYS), col(NAME_KEYS), col(CLASS_KEYS), col(ANSWER_KEYS)
        items = {}
        for i, h in enumerate(head):
            no = _item_no(h)
            if no and 1 <= no <= n_items and i not in (c_code, c_name, c_cls):
                items.setdefault(no, i)
        if (c_code is not None or c_name is not None) and (len(items) == n_items or c_ans is not None):
            break
    else:
        raise ValueError(f"머리글 줄을 찾지 못했습니다. 첫 줄에 '학생코드'(또는 '이름')와 문항 번호 1~{n_items}를 적어 주세요.")
    out = []
    for ri, r in enumerate(rows[hi + 1:], start=hi + 2):
        get = lambda c: str(r[c]).strip() if c is not None and c < len(r) and r[c] not in (None, "") else ""
        code, name, cls = get(c_code), get(c_name), get(c_cls)
        if code.endswith(".0"):
            code = code[:-2]
        if not code and not name:
            continue
        if len(items) == n_items:
            ans = "".join(_choice(r[items[no]]) if items[no] < len(r) else "0" for no in range(1, n_items + 1))
        else:
            digits = "".join(ch if ch in "12345" else "0" for ch in re.sub(r"[\s,./-]", "", get(c_ans)))
            ans = (digits + "0" * n_items)[:n_items]
        if set(ans) == {"0"}:                                 # 문항 칸이 모두 빔 = 시험 안 봄
            continue
        out.append({"row": ri, "code": code, "name": name, "cls": cls, "answers": ans})
    if not out:
        raise ValueError("학생 줄이 없습니다.")
    return out


def template(n_items, students):
    """빈 양식 .xlsx: 학생코드 · 이름 · 반 · 1 … N. students: [(코드, 이름, 반)]"""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = Workbook()
    ws = wb.active
    ws.title = "OMR"
    ws.append(["학생코드", "이름", "반"] + list(range(1, n_items + 1)))
    for code, name, cls in students:
        ws.append([code, name, cls])
    bold, fill = Font(bold=True), PatternFill("solid", fgColor="E7EFEA")
    for c in ws[1]:
        c.font, c.fill, c.alignment = bold, fill, Alignment(horizontal="center")
    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 10
    ws.column_dimensions["C"].width = 16
    from openpyxl.utils import get_column_letter
    for i in range(4, n_items + 4):
        ws.column_dimensions[get_column_letter(i)].width = 4.5
    ws.freeze_panes = "D2"
    # 둘째 시트: 작성 규칙과 예시 (올릴 때는 첫 시트만 읽는다)
    ex = wb.create_sheet("작성 예시")
    for line in (["작성 규칙"],
                 ["1. 첫 시트(OMR)만 읽습니다. 첫 줄 머리글은 바꾸지 마세요."],
                 ["2. 문항 칸에는 학생이 마킹한 번호 1~5만 적습니다. 빈칸·중복 마킹은 무응답(오답)으로 처리됩니다."],
                 ["3. 학생은 학생코드로 찾습니다. 코드가 없으면 이름(동명이인은 반)으로 찾습니다."],
                 ["4. 문항 칸이 모두 빈 줄(시험을 안 본 학생)은 건너뜁니다. 지우지 않아도 됩니다."],
                 ["5. 같은 회차를 다시 올리면 그 학생 결과는 새 파일 내용으로 바뀝니다."],
                 [],
                 ["학생코드", "이름", "반"] + list(range(1, min(n_items, 10) + 1)),
                 ["270001", "김민수", "A반"] + [1, 4, 3, 5, 2, 5, 3, 4, 1, 1][:min(n_items, 10)],
                 ["270002", "이서연", "B반"] + [1, 4, None, 5, 2, 5, 3, 4, 2, 1][:min(n_items, 10)]):
        ex.append(line)
    ex["A1"].font = bold
    for c in ex[8]:
        c.font, c.fill = bold, fill
    ex.column_dimensions["A"].width = 12
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
