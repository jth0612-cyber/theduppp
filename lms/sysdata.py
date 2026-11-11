"""조교 시스템(구글 시트) → 웹 연동.

시트는 학생 이름·연락처 없이 '학생코드' 기준의 앱용 표(🌐앱_성적 등)를 만든다. 웹은 그 표를 통째로 받아
(표마다 전체 교체) 저장하고, 로그인한 학생에게는 자기 코드의 줄만 보여 준다.

- 표 칸은 시트의 머리글 그대로(한글) JSON 으로 저장한다. 시트 칸이 늘거나 순서가 바뀌어도 받는 쪽은 그대로 둔다.
- 이름·연락처·학교 같은 칸이 섞여 들어오면 저장하기 전에 버린다(학생 앱으로는 학생코드만 나간다는 원칙).
- 학생이 웹에서 남긴 '다시 풀기' 결과는 따로 모아 두었다가 시트가 가져가게 한다.
"""
import csv
import hashlib
import io
import json
import re
import secrets
from datetime import datetime

from db import execute, get_db, normalize_student_code, query

# 받는 표: 이름표(시트 이름에서 🌐·앱_ 을 뗀 것) → 설명
TABLES = {
    "성적": "시험별 점수·반 평균",
    "오답노트": "틀린 문항별 오답 유형·분석",
    "리포트": "시즌·단원별 이해도",
    "과제": "과제 제출·맞은 수",
    "출결": "출석·지각·결석",
    "공부유형": "1주차 공부 유형 자가진단",
    "학습유형": "시험 오답 누적 학습 유형",
    "코드": "학생코드와 반(가입 코드 등록용)",
}
# 이 칸은 저장하지 않는다 (개인정보)
_FORBIDDEN = {"이름", "성명", "학생연락처", "학부모연락처", "연락처", "전화", "휴대폰", "학교", "수험번호", "학생ID", "메모"}
WRONG_TYPES = ("개념 부족", "자료 해석", "조건 독해", "계산 실수", "시간 부족", "기타")
STUDY_TYPES = ("안정형", "개념 다지기형", "해설 참고형", "심화 도전형", "마무리 다듬기형", "불안·과소확신형", "양치기형", "벼락치기형", "미이행형")


def now_kst():
    """한국 시간 (서버 시간대 설정에 기대지 않는다)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:  # 시간대 자료가 없는 서버
        from datetime import timedelta, timezone
        return datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")


def table_key(name):
    """'🌐앱_성적', '학생 시스템 - 🌐앱_성적.csv', '성적' → '성적'. 모르는 이름이면 None."""
    s = re.sub(r"\.(csv|txt)$", "", str(name or "").strip(), flags=re.I)
    s = s.split(" - ")[-1]                                    # 시트에서 내려받은 파일 이름: '문서 이름 - 시트 이름'
    s = re.sub(r"^[^가-힣A-Za-z0-9]+", "", s).replace(" ", "")  # 앞쪽 그림 문자(🌐)
    s = re.sub(r"^(앱|app)_?", "", s, flags=re.I)
    return s if s in TABLES else None


def _rows_from(value):
    """[[머리글...], [값...], ...] 또는 [{머리글: 값}, ...] → [{머리글: 값}, ...]"""
    if not isinstance(value, list) or not value:
        return []
    if isinstance(value[0], dict):
        return [{str(k).strip(): v for k, v in r.items()} for r in value if isinstance(r, dict)]
    head = [str(h).strip() for h in value[0]]
    out = []
    for r in value[1:]:
        if not isinstance(r, list):
            continue
        out.append({head[i]: r[i] for i in range(min(len(head), len(r))) if head[i]})
    return out


def _clean(row):
    d = {}
    for k, v in row.items():
        if not k or k in _FORBIDDEN:
            continue
        if v is None:
            v = ""
        d[k] = v if isinstance(v, (int, float)) else str(v).strip()
    return d


def store(tables, source):
    """표 여러 개를 받아 표마다 통째로 바꾼다. 반환: {표: 줄 수}, 모르는 표 이름 목록, 코드 반영 결과."""
    done, unknown, codes = {}, [], None
    db = get_db()
    for name, value in (tables or {}).items():
        key = table_key(name)
        if key is None:
            unknown.append(str(name))
            continue
        rows = [_clean(r) for r in _rows_from(value)]
        rows = [r for r in rows if normalize_student_code(str(r.get("학생코드", "")))]
        if key == "코드":
            codes = _apply_codes(rows)
        with db:
            db.execute("DELETE FROM sys_rows WHERE tbl = ?", (key,))
            db.executemany("INSERT INTO sys_rows (tbl, code, data) VALUES (?, ?, ?)",
                           [(key, normalize_student_code(str(r["학생코드"])), json.dumps(r, ensure_ascii=False)) for r in rows])
            db.execute("""INSERT INTO sys_sync (tbl, n_rows, synced_at, source) VALUES (?, ?, ?, ?)
                          ON CONFLICT(tbl) DO UPDATE SET n_rows = excluded.n_rows, synced_at = excluded.synced_at,
                          source = excluded.source""", (key, len(rows), now_kst(), source))
        done[key] = len(rows)
    return done, unknown, codes


def _apply_codes(rows):
    """'코드' 표(학생코드, 반, 상태): 웹에 같은 이름의 반이 있으면 가입 코드로 등록한다.
    이미 가입에 쓴 코드는 건드리지 않고, 퇴원생의 쓰지 않은 코드는 지운다."""
    classes = {c["name"].strip(): c["id"] for c in query("SELECT id, name FROM classes WHERE archived = 0")}
    added, removed, no_class = 0, 0, set()
    for r in rows:
        code = normalize_student_code(str(r.get("학생코드", "")))
        cname, status = str(r.get("반", "")).strip(), str(r.get("상태", "")).strip()
        have = query("SELECT * FROM student_codes WHERE code = ?", (code,), one=True)
        if status == "퇴원":
            if have and not have["student_id"]:
                execute("DELETE FROM student_codes WHERE id = ?", (have["id"],)); removed += 1
            continue
        if have:
            continue
        cid = classes.get(cname)
        if cid is None:
            if cname:
                no_class.add(cname)
            continue
        execute("INSERT INTO student_codes (class_id, code, memo) VALUES (?, ?, '조교 시스템')", (cid, code)); added += 1
    return {"added": added, "removed": removed, "no_class": sorted(no_class)}


def parse_csv(raw):
    """시트에서 내려받은 CSV (UTF-8, 안 되면 EUC-KR) → [[칸...], ...]"""
    for enc in ("utf-8-sig", "cp949"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("CSV 글자를 읽지 못했어요. 시트에서 'CSV(.csv)'로 다시 내려받아 주세요.")
    return [r for r in csv.reader(io.StringIO(text)) if any(c.strip() for c in r)]


def guess_table(head):
    """파일 이름으로 표를 모를 때 머리글로 맞힌다."""
    h = set(head)
    if {"문항번호", "오답유형"} <= h: return "오답노트"
    if {"이해도(%)"} <= h or {"맞힌배점", "전체배점"} <= h: return "리포트"
    if {"공부유형", "이번주실천"} <= h: return "공부유형"
    if {"학습유형", "코칭포인트"} <= h: return "학습유형"
    if {"출결"} <= h: return "출결"
    if {"제출", "교재"} <= h: return "과제"
    if {"점수", "만점"} <= h: return "성적"
    if {"학생코드", "반"} <= h and len(h) <= 4: return "코드"
    return None


# ---------------------------------------------------------------- 연동 토큰 (시트가 웹에 보낼 때 쓰는 열쇠)
def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def new_token():
    token = "thl_" + secrets.token_urlsafe(32)
    execute("INSERT INTO settings (key, value) VALUES ('sync_token', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (_hash(token),))
    execute("INSERT INTO settings (key, value) VALUES ('sync_token_at', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (now_kst(),))
    return token


def token_ok(header):
    m = re.match(r"^Bearer\s+(\S+)$", header or "")
    row = query("SELECT value FROM settings WHERE key = 'sync_token'", one=True)
    return bool(m and row and secrets.compare_digest(_hash(m.group(1)), row["value"]))


def token_info():
    row = query("SELECT value FROM settings WHERE key = 'sync_token_at'", one=True)
    return row["value"] if row else None


# ---------------------------------------------------------------- 학생 한 명의 자료 읽기
def code_of_student(student_id):
    if not student_id:
        return None
    r = query("SELECT code FROM student_codes WHERE student_id = ? ORDER BY used_at DESC LIMIT 1", (student_id,), one=True)
    return r["code"] if r else None


def rows(code, tbl):
    if not code:
        return []
    return [json.loads(r["data"]) for r in query("SELECT data FROM sys_rows WHERE code = ? AND tbl = ? ORDER BY id", (code, tbl))]


def num(v):
    """'57.5%', '9.3', 44, '' → float 또는 None"""
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v or "").replace("%", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def fmt(v):
    """보기 좋은 숫자: 44.0 → 44, 9.25 → 9.3"""
    if v is None:
        return ""
    v = round(v, 1)
    return str(int(v)) if v == int(v) else str(v)


def _day(v):
    s = str(v or "").strip().replace(".", "-").replace("/", "-")
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", s)
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else s


def scores(code):
    out = []
    for r in rows(code, "성적"):
        sc, full = num(r.get("점수")), num(r.get("만점"))
        avg, vs = num(r.get("반평균")), num(r.get("평균대비"))
        if vs is None and sc is not None and avg is not None:
            vs = round(sc - round(avg, 1), 1)                      # 화면에 보이는 평균(소수 한 자리)으로 계산
        out.append({"season": r.get("시즌", ""), "week": r.get("주차", ""), "kind": r.get("유형", ""), "name": r.get("시험명", ""),
                    "day": _day(r.get("날짜")), "score": sc, "full": full, "avg": avg, "vs": vs,
                    "pct": round(sc * 100 / full, 1) if sc is not None and full else None,
                    "avg_pct": round(avg * 100 / full, 1) if avg is not None and full else None,
                    "wrong": str(r.get("틀린문항", "")).strip()})
    out.sort(key=lambda x: (x["day"], x["name"]))
    return out


def wrong_notes(code):
    redo = {(r["exam"], r["item_no"]): r["result"] for r in query("SELECT * FROM sys_redo WHERE code = ?", (code,))} if code else {}
    groups = {}
    for r in rows(code, "오답노트"):
        basis = str(r.get("판단근거", "")).strip()
        if basis == "정정됨":                                     # 채점을 고쳐 더는 오답이 아닌 문항
            continue
        exam, no = str(r.get("시험명", "")).strip(), int(num(r.get("문항번호")) or 0)
        etype = str(r.get("오답유형", "")).strip()
        if basis == "정보 없음" or etype not in WRONG_TYPES:
            etype = "" if basis == "정보 없음" or not etype else "기타"
        g = groups.setdefault(exam, {"exam": exam, "day": _day(r.get("날짜")), "items": []})
        g["items"].append({"no": no, "mine": str(r.get("내답", "")).strip(), "answer": str(r.get("정답", "")).strip(),
                           "rate": num(r.get("반오답률")), "unit": r.get("단원", ""), "type": etype,
                           "analysis": str(r.get("분석", "")).strip(), "basis": basis, "guess": basis == "문항 성격 추정",
                           "confused": str(r.get("헷갈린보기", "")).strip(), "same": num(r.get("같은답비율")),
                           "redo": redo.get((exam, no)) or str(r.get("다시풀기", "")).strip()})
    out = sorted(groups.values(), key=lambda g: g["day"], reverse=True)
    for g in out:
        g["items"].sort(key=lambda i: i["no"])
        g["open"] = sum(1 for i in g["items"] if i["redo"] != "맞힘")
    return out


def type_counts(groups):
    c = {}
    for g in groups:
        for i in g["items"]:
            if i["type"]:
                c[i["type"]] = c.get(i["type"], 0) + 1
    return sorted(c.items(), key=lambda kv: -kv[1])


def report(code):
    seasons = {}
    for r in rows(code, "리포트"):
        s = str(r.get("시즌", "")).strip() or "전체"
        pct = num(r.get("이해도(%)"))
        got, total = num(r.get("맞힌배점")), num(r.get("전체배점"))
        if pct is None and got is not None and total:
            pct = round(got * 100 / total, 1)
        seasons.setdefault(s, []).append({"unit": r.get("단원", ""), "pct": pct, "got": got, "total": total})
    return seasons


def study_type(code):
    rs = rows(code, "공부유형")
    if not rs:
        return None
    r = rs[-1]
    sc = [(t, num(r.get(t))) for t in STUDY_TYPES if num(r.get(t)) is not None]
    return {"day": _day(r.get("진단일")), "main": r.get("공부유형", ""), "sub": r.get("보조유형", ""), "verdict": r.get("판정", ""),
            "desc": r.get("설명", ""), "practice": r.get("이번주실천", ""), "scores": sc}


def learn_type(code):
    rs = rows(code, "학습유형")
    if not rs:
        return None
    r = rs[-1]
    counts = [(t, int(num(r.get(t)) or 0)) for t in WRONG_TYPES if num(r.get(t))]
    return {"type": r.get("학습유형", ""), "basis": r.get("근거", ""), "coach": r.get("코칭포인트", ""), "trust": r.get("신뢰도", ""),
            "n_exams": num(r.get("시험수")), "avg_rate": num(r.get("평균득점률")), "weak": r.get("취약단원", ""), "counts": counts}


def tasks(code):
    out = [{"day": _day(r.get("날짜")), "book": r.get("교재", ""), "range": r.get("범위", ""), "submit": str(r.get("제출", "")).strip(),
            "right": num(r.get("맞은수")), "total": num(r.get("문항수"))} for r in rows(code, "과제")]
    return sorted(out, key=lambda x: x["day"], reverse=True)


def attendance(code):
    out = [{"day": _day(r.get("날짜")), "status": str(r.get("출결", "")).strip(), "arrived": str(r.get("도착시각", "")).strip()}
           for r in rows(code, "출결")]
    return sorted(out, key=lambda x: x["day"], reverse=True)


def synced_summary():
    have = {r["tbl"]: r for r in query("SELECT * FROM sys_sync")}
    return [{"key": k, "label": v, "row": have.get(k)} for k, v in TABLES.items()]
