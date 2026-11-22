"""복습 테스트·모의고사: OMR 결과 반영, 반별 통계, 오답 분석, 학부모 문자, 누적 학습 유형.

조교 시스템 인계 문서(성적 엑셀 기반 학습 유형 분석과 학부모 문자 생성)의 규칙을 그대로 옮겼다.
- 숫자·통계 문장·학습 유형 판정은 전부 코드가 쓴다.
- 문항별 분석 문장은 문항정보(보기함정·선지분석)로 만든다. 고른 답으로 원인을 짚을 수 있는 문항만 쓴다.
- 학부모 문자는 학생이 속한 반의 통계만 쓴다. 반 응시 인원이 10명 미만이면 오답률·선택 비율 문장을 뺀다."""
import json
import re
from datetime import date, datetime

import analysis
import omr
from db import execute, query
from security import decrypt

ERR_TYPES = ("개념 부족", "자료 해석", "조건 독해", "계산 실수", "시간 부족", "기타")
SET = {
    "sign": "[정태혁 통합과학]",
    "hard": 30,              # 고난도기준(반 오답률 %)
    "detail": 3,             # 문자상세문항수
    "min_n": 10,             # 통계최소인원
    "guide": "오답은 단순 개념 부족, 자료 해석, 조건 독해 누락, 계산 실수 등의 항목으로 나눠 기록합니다.",
    "closing": "저희 플랫폼의 1:1 밀착 피드백 시스템을 적극적으로 이용하시길 추천드립니다.",
    "class_name": True,      # 문자에반이름
    "learn_type": True,      # 문자에학습유형
    "study_type": True,      # 문자에공부유형
    "max_bytes": 2000,
}
LABELS = "ㄱㄴㄷㄹㅁ"
CIRC = "①②③④⑤"


# ---------------------------------------------------------------- 공용
def pct1(x):
    """비율(%)을 소수 한 자리까지, .0 은 뺀다: 57.5, 4, 31"""
    v = round(x + 1e-9, 1)
    return str(int(v)) if v == int(v) else f"{v:.1f}"


def num(x):
    return analysis._fmt(x) if x is not None else ""


def avg1(xs):
    return round(sum(xs) / len(xs) + 1e-9, 1) if xs else None


def josa(word, a, b):
    """받침 있으면 a(을·은·이), 없으면 b(를·는·가)"""
    ch = str(word).strip()[-1:] if str(word).strip() else ""
    if "가" <= ch <= "힣":
        return a if (ord(ch) - 0xAC00) % 28 else b
    if ch in "ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎ":
        return a
    if ch.isdigit():
        return a if ch in "013678" else b
    return a


def sms_bytes(text):
    return sum(2 if ord(c) > 127 else 1 for c in text)


def exam_title(m):
    return f"{m['book_title']} {m['round_no']}회" + (f" {m['title']}" if m["title"] else "")


def load_mock(mid):
    m = query("""SELECT m.*, b.title AS book_title, b.kind, b.is_practice FROM mocks m JOIN books b ON b.id = m.book_id
                 WHERE m.id = ?""", (mid,), one=True)
    if m is None:
        return None
    d = dict(m)
    d["key"] = json.loads(m["answer_key"] or "[]")
    d["pts"] = json.loads(m["points"] or "[]")
    d["info"] = {int(k): v for k, v in (json.loads(m["items"] or "[]") or {}).items()} if (m["items"] or "[]").startswith("{") else {}
    return d


# ---------------------------------------------------------------- 학생 찾기 (인계 4.3)
def _digits(v):
    d = re.sub(r"\D", "", str(v or ""))
    return "0" + d if len(d) == 7 else d


def student_index(practice=False):
    """practice: 연습 회차면 연습반 학생만, 실제 회차면 연습반 학생은 빼고 찾는다."""
    rows = query("""SELECT s.id, s.name, s.student_no, s.phone_enc, s.parent_phone_enc, s.sms_ok, c.name AS cls,
                           u.id AS uid, u.username
                    FROM students s JOIN classes c ON c.id = s.class_id
                    LEFT JOIN users u ON u.student_id = s.id AND u.role = 'student'
                    WHERE s.active = 1 AND c.is_test = ?""", (1 if practice else 0,))
    out = []
    for r in rows:
        d = dict(r)
        d["parent8"] = _digits(decrypt(r["parent_phone_enc"]))[-8:]
        d["phone8"] = _digits(decrypt(r["phone_enc"]))[-8:]
        out.append(d)
    return out


def match(row, idx):
    """(학생, 표시, 막음 이유). 번호와 이름이 다른 학생을 가리키면 넣지 않는다."""
    raw = (row["number"] or row["phone"] or "").strip()
    d = _digits(raw)
    by_num, why = None, None
    up = raw.upper()
    exact = [s for s in idx if up and ((s["student_no"] or "").upper() == up or (s["username"] or "").upper() == up)]
    if len(d) >= 8 and not exact:
        c = [s for s in idx if s["parent8"] and s["parent8"] == d[-8:]] or \
            [s for s in idx if s["phone8"] and s["phone8"] == d[-8:]]
        if len(c) > 1 and row["name"]:
            c = [s for s in c if s["name"] == row["name"]]
        if len(c) == 1:
            by_num = c[0]
        elif len(c) > 1:
            return None, "", "같은 학부모 번호의 학생이 여럿이라 구분하지 못했습니다(이름 확인)"
        else:
            why = "같은 학부모 번호가 학생DB에 없습니다"
    elif raw:
        c = exact
        if not c and len(d) == 4:
            c4 = [s for s in idx if s["parent8"].endswith(d)]
            c = c4 if len(c4) == 1 else []
        if len(c) == 1:
            by_num = c[0]
        elif not c:
            why = "번호가 학생DB에 없습니다"
    named = [s for s in idx if row["name"] and s["name"] == row["name"]]
    if by_num:
        if row["name"] and row["name"] != by_num["name"]:
            if named:
                return None, "", f"번호는 {by_num['name']}, 이름은 {row['name']}이라 넣지 않았습니다(수험번호 오마킹 확인)"
            return by_num, f"이름 '{row['name']}'이 학생DB에 없어 번호로 넣었습니다", None
        return by_num, "", None
    if why and raw:
        if len(named) == 1:
            return named[0], f"{why}. 이름으로 찾았습니다", None
        return None, "", why
    if row["cls"] and len(named) > 1:
        named = [s for s in named if row["cls"] in s["cls"]]
    if len(named) == 1:
        return named[0], "", None
    if len(named) > 1:
        return None, "", "같은 이름이 여러 명입니다(수험번호나 반을 적어 주세요)"
    return None, "", "학생DB에 없는 학생입니다"


# ---------------------------------------------------------------- 엑셀 반영 (인계 4.5)
def _key_cell(v):
    s = str(v).strip()
    s = "".join(omr.CIRCLED.get(ch, ch) for ch in s)
    if s in ("*", "전원"):
        return "*"
    ds = re.findall(r"[1-5]", s)
    if len(ds) == 1:
        return int(ds[0])
    if len(ds) > 1:
        return ",".join(dict.fromkeys(ds))
    return ""


def apply_upload(mid, raw, filename, by_id):
    """파일 하나를 반영한다. 돌려주는 값: {"ok": n, "summary": str, "rows": [...], "warn": [...]}"""
    m = load_mock(mid)
    p = omr.read(raw, filename)
    n = p["n"] if p["has_items"] else (m["n_items"] or 0)
    if p["has_items"] and p["items"] != list(range(1, n + 1)):
        raise omr.OmrError(f"문항 번호 칸이 1~{n} 으로 이어지지 않습니다.")
    if not n:
        raise omr.OmrError("문항 수를 알 수 없습니다. 문항 번호 칸(1, 2, 3 …)을 넣어 주세요.")
    if m["n_items"] and n != m["n_items"]:
        raise omr.OmrError(f"파일의 마지막 문항은 {n}번인데 이 회차는 {m['n_items']}문항입니다. 회차를 잘못 고르지 않았는지 확인해 주세요.")
    info = dict(m["info"])
    for no, d in p["info"].items():
        if 1 <= no <= n:
            info[no] = {**info.get(no, {}), **d}
    warn = []
    # 정답: 파일의 정답 줄 > 문항정보 > 이미 저장된 정답
    key = []
    old = m["key"] if len(m["key"]) == n else [""] * n
    for i in range(1, n + 1):
        k = _key_cell(p["key"].get(i, "")) if p["key"] else ""
        if k == "" and info.get(i, {}).get("answer"):
            k = _key_cell(info[i]["answer"])
        if k == "":
            k = old[i - 1]
        key.append(k)
    mode = omr.mode_of(p, any(k != "" for k in key))
    missing = [i + 1 for i, k in enumerate(key) if k == ""]
    if mode == "choice" and missing:
        raise omr.OmrError(f"정답이 없는 문항: {', '.join(map(str, missing))}번 / 파일에 '정답' 줄을 넣거나 문항정보 시트에 정답을 적어 주세요.")
    # 배점: 파일의 배점 줄 > 문항정보 > 이미 저장된 배점 > 1
    oldp = m["pts"] if len(m["pts"]) == n else [None] * n
    pts = []
    for i in range(1, n + 1):
        v = p["points"].get(i)
        if v is None and info.get(i, {}).get("points"):
            try:
                v = float(info[i]["points"])
            except ValueError:
                v = None
        pts.append(v if v is not None else (oldp[i - 1] if oldp[i - 1] is not None else 1))
    pts = [int(x) if float(x).is_integer() else x for x in pts]
    full = sum(pts)
    answers = omr.grade(p, key, n, mode)
    idx = student_index(practice=bool(m["is_practice"]))
    seen, rows_out, ok = set(), [], 0
    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    classes = set()
    for r, ans in zip(p["rows"], answers):
        label = r["name"] or r["number"] or r["phone"]
        if ans is None:
            rows_out.append({"row": r["row"], "who": label, "state": "skip", "msg": "답안이 비어 있어 건너뜀(미응시)"})
            continue
        s, note, why = match(r, idx)
        if s is None:
            rows_out.append({"row": r["row"], "who": label, "state": "error", "msg": why})
            continue
        if s["id"] in seen:
            rows_out.append({"row": r["row"], "who": label, "state": "error", "msg": "같은 학생이 두 번 나와 두 번째 줄은 넣지 않았습니다"})
            continue
        seen.add(s["id"])
        classes.add(s["cls"])
        score = analysis.score_omr(ans, key, pts)
        msgs = [note] if note else []
        if r["score"]:
            try:
                fs = float(r["score"])
                if not (abs(fs - score) < 0.01 or (full and abs(fs - score * 100 / full) < 0.6)):
                    msgs.append(f"파일 점수 {num(fs)}와 계산 점수 {num(score)}가 다릅니다")
            except ValueError:
                pass
        execute("""INSERT INTO exam_results (mock_id, student_id, answers, score, file_score, note, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(mock_id, student_id) DO UPDATE SET answers = excluded.answers, score = excluded.score,
                   file_score = excluded.file_score, note = excluded.note, updated_at = excluded.updated_at""",
                (mid, s["id"], ans, score, r["score"], "; ".join(msgs), now))
        ok += 1
        rows_out.append({"row": r["row"], "who": label, "state": "warn" if msgs else "ok",
                         "msg": f"{s['name']} ({s['cls']}) {num(score)}점" + (" · " + "; ".join(msgs) if msgs else ""),
                         "account": bool(s["uid"])})
    absent = sorted(s["name"] for s in idx if s["cls"] in classes and s["id"] not in seen
                    and not query("SELECT 1 FROM exam_results WHERE mock_id = ? AND student_id = ?", (mid, s["id"]), one=True))
    if absent:
        warn.append(f"반 학생 중 파일에 없는 학생 {len(absent)}명: " + ", ".join(absent[:30]) + (" …" if len(absent) > 30 else ""))
    if mode != "choice":
        warn.append({"10": "1/0", "ox": "O/X", "x": "X 표시", "wrong": "틀린문항"}[mode] + " 형식이라 고른 번호가 없습니다. 오답 유형은 추정하지 않고, 선택 비율은 쓰지 않습니다.")
    if not any(info.get(i) for i in range(1, n + 1)):
        warn.append("문항정보가 비어 있어 오답 유형을 분류하지 않습니다. 문항정보 시트를 채워 다시 올리면 분석이 붙습니다.")
    if ok or m["n_items"]:                                   # 아무도 못 넣은 파일로는 회차 설정을 바꾸지 않는다
        execute("""UPDATE mocks SET n_items = ?, full_score = ?, answer_key = ?, points = ?, items = ?,
                   exam_date = CASE WHEN exam_date = '' THEN ? ELSE exam_date END WHERE id = ?""",
                (n, full, json.dumps(key, ensure_ascii=False), json.dumps(pts),
                 json.dumps({str(k): v for k, v in info.items()}, ensure_ascii=False), date.today().isoformat(), mid))
    sync_entries(mid)
    try:
        from flask import g
        g.pop("_exam_cs", None)
    except RuntimeError:
        pass
    summary = f"{ok}명 반영" + (f" · 못 넣은 줄 {sum(1 for r in rows_out if r['state'] == 'error')}개" if any(r["state"] == "error" for r in rows_out) else "")
    execute("INSERT INTO omr_uploads (mock_id, by_id, filename, summary, rows) VALUES (?, ?, ?, ?, ?)",
            (mid, by_id, filename[:200], summary + ("\n" + "\n".join(warn) if warn else ""), json.dumps(rows_out, ensure_ascii=False)))
    analysis.invalidate(mid)
    return {"ok": ok, "summary": summary, "rows": rows_out, "warn": warn}


def sync_entries(mid=None, student_id=None):
    """exam_results → mock_entries (학생 계정이 있는 학생만. 학생 화면·오답 노트가 이것을 읽는다)."""
    where, args = [], []
    if mid:
        where.append("r.mock_id = ?"); args.append(mid)
    if student_id:
        where.append("r.student_id = ?"); args.append(student_id)
    execute(f"""INSERT INTO mock_entries (mock_id, user_id, mode, answers, score, updated_at)
                SELECT r.mock_id, u.id, 'answers', r.answers, r.score, r.updated_at FROM exam_results r
                JOIN users u ON u.student_id = r.student_id AND u.role = 'student'
                {"WHERE " + " AND ".join(where) if where else ""}
                ON CONFLICT(mock_id, user_id) DO UPDATE SET mode = 'answers', answers = excluded.answers,
                score = excluded.score, updated_at = excluded.updated_at""", tuple(args))


# ---------------------------------------------------------------- 통계 (인계 5장)
def results(mid):
    return [dict(r) for r in query("""SELECT r.*, s.name, s.student_no, s.parent_phone_enc, s.sms_ok, c.name AS cls
                                      FROM exam_results r JOIN students s ON s.id = r.student_id
                                      JOIN classes c ON c.id = s.class_id WHERE r.mock_id = ? ORDER BY c.name, s.name""", (mid,))]


def group_stats(rows, key):
    """한 묶음(반 또는 전체) 통계: 인원, 평균(소수 한 자리), 문항별 오답률(%), 선지 수."""
    n = len(rows)
    out = {"n": n, "avg": avg1([r["score"] for r in rows]), "wrong": [], "counts": [], "right": []}
    for i, k in enumerate(key):
        cnt = [0] * 5
        right = wrong_none = 0
        for r in rows:
            a = r["answers"][i]
            if a in "12345":
                cnt[int(a) - 1] += 1
            if analysis.is_right(a, k):
                right += 1
            elif a not in "12345":
                wrong_none += 1
        out["counts"].append(cnt)
        out["right"].append(right)
        out["wrong"].append(100 * (n - right) / n if n else 0)
        out.setdefault("none", []).append(wrong_none)
    return out


def class_stats(mid):
    """회차 통계. 한 요청 안에서는 한 번만 계산한다 (학생마다 문자를 만들 때 반복 호출되므로)."""
    from flask import g, has_app_context
    cache = g.setdefault("_exam_cs", {}) if has_app_context() else {}
    if mid in cache:
        return cache[mid]
    cache[mid] = _class_stats(mid)
    return cache[mid]


def _class_stats(mid):
    m = load_mock(mid)
    rs = results(mid)
    by = {}
    for r in rs:
        by.setdefault(r["cls"], []).append(r)
    has_choice = any(ch in "12345" for r in rs for ch in r["answers"])
    return {"all": group_stats(rs, m["key"]), "cls": {c: group_stats(v, m["key"]) for c, v in by.items()},
            "has_choice": has_choice, "rows": rs, "mock": m}


def choice_dist(st, i, k):
    """'①1.5% ②4% ③31% ④6% ⑤57.5%' (정답 선지 비율 = 그 문항을 맞힌 학생 비율)"""
    n = st["n"]
    if not n:
        return ""
    ks = analysis.key_set(k)
    single = next(iter(ks)) if ks and len(ks) == 1 else None
    parts = []
    for c in range(1, 6):
        cnt = st["right"][i] if single == str(c) else st["counts"][i][c - 1]
        parts.append(f"{CIRC[c - 1]}{pct1(100 * cnt / n)}%")
    none = st["none"][i]
    if none:
        parts.append(f"기록없음 {pct1(100 * none / n)}%")
    return " ".join(parts)


# ---------------------------------------------------------------- 오답 분석 (인계 6장)
def parse_options(s):
    """'①ㄱ ②ㄴ ③ㄱ,ㄷ ④ㄴ,ㄷ ⑤ㄱ,ㄴ,ㄷ' → {1: {'ㄱ'}, …}"""
    out = {}
    s = "".join(omr.CIRCLED.get(ch, f" {ch}" if ch in "12345" else ch) for ch in str(s or ""))
    for m in re.finditer(r"([1-5])\s*[.):번]?\s*([ㄱ-ㅁ,\s·]+)", s):
        labels = {ch for ch in m.group(2) if ch in LABELS}
        if labels:
            out[int(m.group(1))] = labels
    return out


def _etype(t):
    t = (t or "").strip()
    return t if t in ERR_TYPES else ("기타" if t else "")


def parse_traps(s):
    """'ㄱ(O): 이유 [개념 부족] / ㄴ(X): 이유 [자료 해석]' → {'ㄱ': (True, 이유, 유형)}"""
    out = {}
    for part in re.split(r"\s*/\s*(?=[ㄱ-ㅁ]\s*[\(（])", str(s or "")):
        m = re.match(r"\s*([ㄱ-ㅁ])\s*[\(（]\s*([OXox○×])\s*[\)）]\s*[:：]?\s*(.*)$", part)
        if not m:
            continue
        body = m.group(3).strip()
        t = re.search(r"\[([^\]]+)\]\s*$", body)
        out[m.group(1)] = (m.group(2).upper() in ("O", "○"), body[:t.start()].strip() if t else body, _etype(t.group(1)) if t else "")
    return out


def parse_distractors(s):
    """'2번: 설명(유형) / 3번: 설명(유형)' → {2: (설명, 유형)}"""
    out = {}
    for part in re.split(r"\s*/\s*(?=\d\s*번?\s*[:：])", str(s or "")):
        m = re.match(r"\s*([1-5])\s*번?\s*[:：]\s*(.*)$", part)
        if not m:
            continue
        body = m.group(2).strip()
        t = re.search(r"[\(（\[]([^\)）\]]+)[\)）\]]\s*$", body)
        tp = _etype(t.group(1)) if t and t.group(1).strip() in ERR_TYPES else ""
        out[int(m.group(1))] = (body[:t.start()].strip() if tp else body, tp)
    return out


def analyze_item(no, mine, k, info):
    """틀린 문항 하나: {evidence, type, analysis, diff, trap, confused}. 숫자는 쓰지 않는다."""
    info = info or {}
    has = any(info.get(f) for f in ("concept", "misconception", "distractors", "traps"))
    res = {"no": no, "mine": mine if mine in "12345" else "", "key": analysis.key_label(k), "evidence": "정보 없음",
           "type": "", "analysis": "", "diff": "", "trap": "", "confused": ""}
    if not has:
        return res
    ks = analysis.key_set(k)
    single = int(next(iter(ks))) if ks and len(ks) == 1 else None
    if res["mine"] and info.get("format", "").startswith("합답") and single:
        opts = parse_options(info.get("options"))
        mine_i = int(res["mine"])
        if single in opts and mine_i in opts:
            traps = parse_traps(info.get("traps"))
            missed = sorted(opts[single] - opts[mine_i])        # 옳은 진술을 틀렸다고 판단
            added = sorted(opts[mine_i] - opts[single])         # 틀린 진술을 옳다고 판단
            labels = sorted(set(missed) | set(added))
            if labels:
                lab = ", ".join(labels)
                res.update(evidence="보기 차이 근거", confused=lab, diff=f"{mine_i}번과 {single}번의 차이는 보기 {lab}입니다.")
                first = labels[0]
                tr = traps.get(first)
                res["type"] = (tr[2] if tr and tr[2] else "")
                how = f"옳은 진술인 보기 {first}{josa(first, '을', '를')} 틀렸다고" if first in missed else \
                      f"틀린 진술인 보기 {first}{josa(first, '을', '를')} 옳다고"
                res["analysis"] = f"{no}번은 " + (f"{res['type']} 오류로, " if res["type"] else "") + f"{how} 판단한 경우입니다."
                if tr and tr[1]:
                    res["trap"] = f"보기 {first}: {tr[1]}"
                return res
    if res["mine"] and not info.get("format", "").startswith("합답"):
        dis = parse_distractors(info.get("distractors"))
        d = dis.get(int(res["mine"]))
        if d:
            desc = d[0].rstrip(". ")
            res.update(evidence="고른 선지 근거", type=d[1])
            res["analysis"] = (f"{no}번은 {d[1]} 오류입니다" if d[1] else f"{no}번") + f"({res['mine']}번 선지: {desc})."
            return res
    res["evidence"] = "문항 성격 추정"
    return res


def student_report(mid, student_id, cs=None):
    """한 학생의 이번 시험 분석: 점수, 반 통계, 틀린 문항별 분석."""
    cs = cs or class_stats(mid)
    m = cs["mock"]
    r = next((x for x in cs["rows"] if x["student_id"] == student_id), None)
    if r is None:
        return None
    st = cs["cls"][r["cls"]]
    enough = st["n"] >= SET["min_n"]
    all_enough = cs["all"]["n"] >= SET["min_n"]
    wrong = analysis.wrong_items(r["answers"], m["key"])
    items = []
    for no in wrong:
        i = no - 1
        mine = r["answers"][i]
        a = analyze_item(no, mine, m["key"][i], m["info"].get(no))
        a["rate"] = st["wrong"][i]
        a["rate_all"] = cs["all"]["wrong"][i]
        a["same"] = (st["counts"][i][int(mine) - 1] if mine in "12345" else 0)
        a["same_pct"] = 100 * a["same"] / st["n"] if st["n"] else 0
        a["dist"] = choice_dist(st, i, m["key"][i]) if cs["has_choice"] else ""
        a["unit"] = m["info"].get(no, {}).get("unit", "")
        a["concept"] = m["info"].get(no, {}).get("concept", "")
        a["points"] = m["pts"][i]
        items.append(a)
    return {"mock": m, "r": r, "cls": r["cls"], "st": st, "all": cs["all"], "enough": enough, "all_enough": all_enough,
            "wrong": wrong, "wrongs": items, "full": m["full_score"], "has_choice": cs["has_choice"]}


# ---------------------------------------------------------------- 학부모 문자 (인계 8장)
def _nums(items):
    return ", ".join(str(a["no"]) for a in items)


def _detail_order(items):
    g1 = [a for a in items if a["analysis"] and a["evidence"] in ("보기 차이 근거", "고른 선지 근거")]
    g2 = [a for a in items if a["analysis"] and a not in g1 and a["rate"] < SET["hard"]]
    g3 = [a for a in items if not a["analysis"] and a["mine"]]
    out = []
    for g in (g1, g2, g3):
        out += sorted(g, key=lambda a: (a["rate"], a["no"]))
    return out


def _block(a, rep):
    st, enough = rep["st"], rep["enough"]
    head = f"{a['no']}번 오답 분석"
    bits = []
    if enough:
        bits.append(f"반 오답률 {pct1(a['rate'])}%")
    elif rep["all_enough"]:
        bits.append(f"전체 오답률 {pct1(a['rate_all'])}%")
    if a["mine"]:
        bits.append(f"내 답 {a['mine']} → 정답 {a['key']}")
    else:
        bits.append(f"정답 {a['key']}")
    lines = [head + " · " + ", ".join(bits)]
    if enough and a["dist"]:
        lines.append(f"반 선택 비율: {a['dist']}")
    if a["diff"]:
        lines.append(a["diff"])
    if a["analysis"]:
        lines.append(a["analysis"])
    if enough:
        if a["rate"] < SET["hard"]:
            lines.append(f"반 학생 {pct1(100 - a['rate'])}%가 맞힌 문항에서 나온 오답이라 풀이 흐름에 대한 피드백이 필요해 보입니다.")
        elif a["mine"] and a["same_pct"] >= 15 and a["same"] >= 3:
            where = f"보기 {a['confused']}에서" if a["confused"] else "같은 지점에서"
            lines.append(f"반 학생 {pct1(a['same_pct'])}%가 같은 {a['mine']}번을 골라, 많은 학생이 {where} 헷갈린 문항입니다.")
        else:
            lines.append("반 전체가 어려워한 고난도 문항입니다.")
    return "\n".join(lines)


def compose_sms(rep, name, overall="", extra=None, detail=None):
    """학부모 분석 문자. extra: 누적 학습 유형 줄 또는 공부 유형 문단(둘 중 하나)."""
    detail = SET["detail"] if detail is None else detail
    m = rep["mock"]
    score, full = rep["r"]["score"], m["full_score"]
    avg = rep["st"]["avg"]
    where = f"{rep['cls']} 평균" if SET["class_name"] else "반 평균"
    line2 = f"{exam_title(m)} {num(score)}/{num(full)} ({where} {num(avg)})"
    line2 += f", 틀린 문항 {', '.join(map(str, rep['wrong']))}번" if rep["wrong"] else ", 만점"
    paras = [f"{SET['sign']} {name} 학생 학습 안내\n{line2}"]
    order = _detail_order(rep["wrongs"])
    picked = order[:detail]
    if SET["guide"] and any(a["type"] for a in picked):
        paras.append(SET["guide"])
    for a in sorted(picked, key=lambda a: a["no"]):
        paras.append(_block(a, rep))
    rest = [a for a in rep["wrongs"] if a not in picked]
    if rest:
        if rep["enough"]:
            easy = [a for a in rest if a["rate"] < SET["hard"]]
            hard = [a for a in rest if a["rate"] >= SET["hard"]]
            if easy:
                paras.append(f"{_nums(easy)}번 · 반 오답률 {', '.join(pct1(a['rate']) + '%' for a in easy)}로 반 학생 대부분이 맞힌 문항이라 함께 복습이 필요합니다.")
            if hard:
                paras.append(f"{_nums(hard)}번 · 반 오답률 {', '.join(pct1(a['rate']) + '%' for a in hard)}로 반 전체가 어려워한 고난도 문항입니다.")
        else:
            paras.append(f"{_nums(rest)}번도 함께 복습할 문항입니다.")
    if overall:
        paras.append(overall)
    if extra:
        paras.append(extra)
    if rep["wrong"] and SET["closing"]:
        paras.append(SET["closing"])
    text = "\n\n".join(paras)
    if sms_bytes(text) > SET["max_bytes"] and detail > 0:
        return compose_sms(rep, name, overall, extra, detail - 1)
    return text


# ---------------------------------------------------------------- 누적 학습 유형 (인계 9장)
RULE = {"minExams": 2, "minClassified": 5, "topRatio": 0.9, "advRatio": 0.75, "advEasyShare": 0.3,
        "domShare": 0.4, "domCount": 3, "hardItem": 0.5, "trend": 0.07}
TYPE_NAME = {"개념 부족": "개념 보강형", "자료 해석": "자료 해석 보강형", "조건 독해": "조건 독해 보강형",
             "계산 실수": "계산 점검형", "시간 부족": "시간 운영 보강형"}
COACH = {
    "개념 보강형": "틀린 문항의 단원 개념을 개념서로 다시 정리한 뒤, 같은 단원 문항을 다시 풉니다.",
    "자료 해석 보강형": "그래프와 표의 축, 단위, 기울기가 뜻하는 것을 말로 먼저 정리하고 푸는 연습이 필요합니다.",
    "조건 독해 보강형": "문제의 조건과 단서에 표시하며 읽고, 보기를 판단하기 전에 조건을 한 번 더 확인하는 습관이 필요합니다.",
    "계산 점검형": "풀이 방향은 맞습니다. 단위와 계산 과정을 적어 두고 검산하는 습관이 필요합니다.",
    "시간 운영 보강형": "문항 순서와 시간 배분을 정해 두고 푸는 연습이 필요합니다.",
    "심화 도전형": "기본 문항은 안정적입니다. 반 전체가 어려워한 고난도 문항 유형을 따로 모아 연습합니다.",
    "실전 완성형": "실수 없이 안정적입니다. 실전 모의고사에서 시간 운영을 점검하는 단계입니다.",
    "복합형": "오답이 한 유형으로 몰리지 않습니다. 가장 많은 두 유형부터 차례로 점검합니다.",
    "판단 보류": "시험이 더 쌓이면 유형을 판정합니다.",
}


def history(student_id, upto_mid=None):
    """학생의 시험별 분석 (오래된 것부터). upto_mid 가 있으면 그 시험까지."""
    rows = query("""SELECT r.mock_id, m.exam_date, m.created_at FROM exam_results r JOIN mocks m ON m.id = r.mock_id
                    WHERE r.student_id = ? AND m.n_items > 0 ORDER BY m.exam_date, r.updated_at""", (student_id,))
    out = []
    for r in rows:
        rep = student_report(r["mock_id"], student_id)
        if rep:
            out.append(rep)
        if upto_mid and r["mock_id"] == upto_mid:
            break
    return out


def classify_profile(hist):
    """규칙 판정. 돌려주는 값: {type, basis, coach, trust, n_exams, avg_rate, …}"""
    R = RULE
    n = len(hist)
    rates = [h["r"]["score"] / h["full"] for h in hist if h["full"]]
    avg_rate = sum(rates) / len(rates) if rates else 0
    wrongs = [a for h in hist for a in h["wrongs"]]
    rated = [a for h, a in ((h, a) for h in hist for a in h["wrongs"]) if h["enough"]]
    classified = [a for a in wrongs if a["type"]]
    counts = {t: sum(1 for a in classified if a["type"] == t) for t in ERR_TYPES}
    easy_share = (sum(1 for a in rated if a["rate"] < SET["hard"]) / len(rated)) if rated else None
    hard_total = hard_right = 0
    for h in hist:
        if not h["enough"]:
            continue
        for i, w in enumerate(h["st"]["wrong"]):
            if w >= R["hardItem"] * 100:
                hard_total += 1
                hard_right += (i + 1) not in h["wrong"]
    trend = "유지"
    if len(rates) >= 3:
        d = rates[-1] - sum(rates[:-1]) / len(rates[:-1])
        trend = "상승" if d >= R["trend"] else "하락" if d <= -R["trend"] else "유지"
    unit_tot, unit_got = {}, {}
    for h in hist:
        m = h["mock"]
        for i, p in enumerate(m["pts"]):
            u = m["info"].get(i + 1, {}).get("unit")
            if not u:
                continue
            unit_tot[u] = unit_tot.get(u, 0) + p
            unit_got[u] = unit_got.get(u, 0) + (0 if (i + 1) in h["wrong"] else p)
    weak = ""
    cand = [(unit_got[u] / unit_tot[u], u) for u in unit_tot if unit_tot[u] >= 4 and unit_got[u] / unit_tot[u] < 0.8]
    if cand:
        weak = min(cand)[1]
    by_choice = sum(1 for a in classified if a["evidence"] in ("고른 선지 근거", "보기 차이 근거"))
    share = by_choice / len(classified) if classified else 0
    trust = "높음" if share >= 0.6 else "보통" if share >= 0.2 else "낮음"
    if n < R["minExams"]:
        t = "판단 보류"
    elif avg_rate >= R["topRatio"] and (easy_share is None or easy_share <= R["advEasyShare"] or len(wrongs) <= n):
        t = "실전 완성형"
    elif len(classified) < R["minClassified"]:
        t = "판단 보류"
    elif avg_rate >= R["advRatio"] and easy_share is not None and easy_share <= R["advEasyShare"]:
        t = "심화 도전형"
    else:
        top = sorted(((c, tp) for tp, c in counts.items() if tp != "기타"), reverse=True)
        if top and top[0][0] >= R["domCount"] and top[0][0] / len(classified) >= R["domShare"] and \
                (len(top) < 2 or top[0][0] > top[1][0]):
            t = TYPE_NAME[top[0][1]]
        else:
            t = "복합형"
    basis = f"시험 {n}회, 평균 득점률 {round(avg_rate * 100)}%"
    if classified:
        top = max(((c, tp) for tp, c in counts.items()), default=(0, ""))
        basis += f", 분류된 오답 {len(classified)}개 중 {top[1]} {top[0]}개({round(100 * top[0] / len(classified))}%)"
    if easy_share is not None:
        basis += f", 쉬운 문항 오답 비율 {round(easy_share * 100)}%"
    basis += "."
    return {"type": t, "basis": basis, "coach": COACH[t], "trust": trust, "n_exams": n, "avg_rate": avg_rate,
            "counts": counts, "easy_share": easy_share, "hard_rate": (hard_right / hard_total) if hard_total else None,
            "trend": trend, "weak": weak, "n_wrong": len(wrongs), "n_classified": len(classified)}


def learn_block(p):
    if p["type"] == "판단 보류":
        return ""
    return f"누적 학습 유형: {p['type']}\n{p['basis']}\n{p['coach']}"


# ---------------------------------------------------------------- 공부 유형 문단 (인계 10장, 1주차 설문 결과가 있을 때)
def study_block(st, rep, hist):
    """st: sysdata.study_type() 결과. 잇는 문장은 신호가 없으면 뺀다."""
    if not st or not st.get("main") or st["main"].startswith("보류"):
        return ""
    main = re.split(r"[,·/]", st["main"])[0].strip()
    few = not rep["enough"]
    easy = [] if few else [a for a in rep["wrongs"] if a["rate"] < SET["hard"]]
    above = rep["st"]["avg"] is not None and rep["r"]["score"] >= rep["st"]["avg"]
    classified = [a for a in rep["wrongs"] if a["type"]]
    past_units = {a["unit"] for h in hist if h["mock"]["id"] != rep["mock"]["id"] for a in h["wrongs"] if a["unit"]}
    repeated = [a for a in rep["wrongs"] if a["unit"] and a["unit"] in past_units]
    perfect = not rep["wrong"]
    nums = lambda xs: ", ".join(str(a["no"]) for a in xs)
    s = ""
    if main == "안정형":
        if easy:
            s = f"이번 시험에서는 반 학생 대부분이 맞힌 {nums(easy)}번을 놓쳤습니다. 과제와 시험 사이에 차이가 있는지 살펴보겠습니다."
        elif not above:
            s = "이번 시험은 반 평균보다 낮았습니다. 과제와 시험 사이에 차이가 있는지 살펴보겠습니다."
        else:
            s = "이번 시험도 반 평균 이상으로, 같은 모습이 확인됩니다." if few else \
                "이번 시험도 반 평균 이상이고 반 학생 대부분이 맞힌 문항을 모두 맞혀, 같은 모습이 확인됩니다."
    elif main == "개념 다지기형":
        concept = [a for a in classified if a["type"] == "개념 부족"]
        others = [t for t in ERR_TYPES if t != "개념 부족" and any(a["type"] == t for a in classified)]
        if perfect:
            s = "이번 시험은 만점으로, 개념이 자리를 잡아 가고 있습니다."
        elif classified and len(concept) * 2 >= len(classified):
            s = f"이번 시험 오답 {len(rep['wrong'])}개 중 {len(concept)}개가 개념 부족으로 분류되어, 같은 모습이 확인됩니다."
        elif repeated:
            s = f"{nums(repeated)}번은 지난 시험에서도 틀렸던 단원({', '.join(dict.fromkeys(a['unit'] for a in repeated))})이라, 같은 모습이 확인됩니다."
        elif others:
            s = f"이번 시험 오답은 개념 부족보다 {', '.join(others[:2])} 쪽이 많았습니다."
    elif main == "해설 참고형":
        if above:
            s = "이번 시험은 반 평균 이상입니다. 혼자 끝까지 푸는 힘이 올라오고 있습니다."
        elif easy:
            s = f"혼자 푸는 시험에서 반 학생 대부분이 맞힌 {nums(easy)}번을 놓쳐, 같은 모습이 확인됩니다."
        else:
            s = "혼자 푸는 시험에서 반 평균보다 낮게 나와, 같은 모습이 확인됩니다."
    elif main == "심화 도전형":
        if few:
            s = ""
        elif perfect:
            s = "이번 시험은 고난도 문항까지 모두 맞혔습니다."
        elif not easy:
            s = f"기본 문항은 모두 맞혔고, 틀린 {nums(rep['items'])}번은 반 전체가 어려워한 문항이라 같은 모습이 확인됩니다."
        else:
            s = f"이번에는 반 학생 대부분이 맞힌 {nums(easy)}번도 놓쳐, 기본 문항 점검을 함께 하겠습니다."
    elif main.startswith("마무리 다듬기형"):
        slips = [a for a in classified if a["type"] in ("계산 실수", "조건 독해")]
        if perfect:
            s = "이번 시험은 실수 없이 만점입니다. 확인하는 습관이 자리를 잡아 가고 있습니다."
        elif slips:
            s = f"이번 시험에서도 {nums(slips)}번을 {', '.join(dict.fromkeys(a['type'] for a in slips))} 오류로 놓쳐, 같은 모습이 확인됩니다."
        elif easy:
            s = f"이번 시험에서도 반 학생 대부분이 맞힌 {nums(easy)}번을 놓쳐, 같은 모습이 확인됩니다."
        elif not few:
            s = "이번 시험에서는 쉬운 문항 실수가 없었습니다. 확인하는 습관이 자리를 잡아 가고 있습니다."
    elif main.startswith("불안"):
        if above:
            s = "이번 시험도 반 평균 이상으로, 실제 실력이 스스로 느끼는 것보다 높다는 점이 확인됩니다."
    elif main == "양치기형":
        if repeated:
            s = f"{nums(repeated)}번은 지난 시험에서도 틀렸던 단원({', '.join(dict.fromkeys(a['unit'] for a in repeated))})입니다. 오답을 다시 푸는 시간이 필요한 모습이 확인됩니다."
        elif len(hist) > 1 and rep["wrong"]:
            s = "이번 시험에서는 지난 시험과 같은 단원의 오답이 없었습니다."
    elif main == "벼락치기형":
        n = rep["mock"]["n_items"]
        start = n * 2 // 3 + 1
        back = [w for w in rep["wrong"] if w >= start]
        if len(rep["wrong"]) >= 2 and len(back) >= 0.6 * len(rep["wrong"]):
            s = f"오답 {len(rep['wrong'])}개 중 {len(back)}개가 뒤쪽 문항({start}번 이후)에 몰려 있어, 같은 모습이 확인됩니다."
    head = f"공부 유형: {st['main']}" + (f" (보조: {st['sub']})" if st.get("sub") else "")
    lines = [head, st.get("desc", "")] + ([s] if s else []) + ([f"이번 주 실천: {st['practice']}"] if st.get("practice") else [])
    return "\n".join(x for x in lines if x)


def sms_for(mid, student_id, cs=None):
    """회차 화면·문자 목록용: 그 학생 문자 전체."""
    import sysdata
    rep = student_report(mid, student_id, cs)
    if rep is None:
        return None
    hist = history(student_id, upto_mid=mid)
    extra = ""
    if SET["study_type"]:
        extra = study_block(sysdata.study_type(sysdata.code_of_student(student_id)), rep, hist)
    if not extra and SET["learn_type"]:
        extra = learn_block(classify_profile(hist))
    return compose_sms(rep, rep["r"]["name"], overall=(rep["r"].get("ta_note") or "").strip(), extra=extra)


# ---------------------------------------------------------------- 연습반 (실장 TEST반)
_SURNAMES = "김이박최정강조윤장임한오서신권황안송류홍"
_GIVEN = ["민준", "서연", "도윤", "하은", "시우", "지유", "주원", "서윤", "예준", "지민", "하준", "수아", "지호", "채원", "준서",
          "다은", "건우", "예린", "현우", "소율", "우진", "지아", "선우", "윤서", "연우"]


def seed_practice():
    """처음 한 번: 연습반 '실장 TEST반'과 가상 학생 50명, 연습 회차(복습 테스트·모의고사 각 1~10회)를 만든다.
    가상 학생의 학부모 번호는 010-9999-00NN. 실제 회차에는 섞이지 않는다.
    이미 있는 반·학생코드·회차는 건너뛴다. 여기서 오류가 나도 서버는 계속 켜진다."""
    try:
        _seed_practice()
    except Exception:                                        # noqa: BLE001 - 연습 데이터 때문에 서버가 멈추면 안 된다
        import logging
        logging.getLogger(__name__).exception("연습반 만들기 실패 (서버는 계속 실행)")


def _seed_practice():
    if query("SELECT 1 FROM settings WHERE key = 'seed_practice'", one=True):
        return
    from security import encrypt
    from db import new_join_code, join_code_taken
    c = query("SELECT id FROM classes WHERE name = '실장 TEST반' ORDER BY id LIMIT 1", one=True)
    if c:
        cid = c["id"]
        execute("UPDATE classes SET is_test = 1, join_open = 0 WHERE id = ?", (cid,))
    else:
        cid = execute("INSERT INTO classes (name, description, is_test, join_open, join_code) VALUES ('실장 TEST반', '조교 연습용 가상 반', 1, 0, ?)",
                      (new_join_code(join_code_taken),))
    for i in range(50):
        code = f"TEST{i + 1:03d}"
        if query("SELECT 1 FROM students WHERE student_no = ?", (code,), one=True):
            continue
        name = _SURNAMES[i % len(_SURNAMES)] + _GIVEN[(i * 7) % len(_GIVEN)]
        execute("""INSERT INTO students (class_id, name, student_no, parent_phone_enc, memo_enc) VALUES (?, ?, ?, ?, ?)""",
                (cid, name, code, encrypt(f"010-9999-{i + 1:04d}"), encrypt("가상 학생 (연습용)")))
    for kind in ("복습 테스트", "모의고사"):
        title = f"[연습] {kind}"
        b = query("SELECT id FROM books WHERE title = ?", (title,), one=True)
        bid = b["id"] if b else execute("INSERT INTO books (title, subject, expires_on, kind, is_practice) VALUES (?, '통합과학', '2099-12-31', ?, 1)",
                                        (title, kind))
        execute("UPDATE books SET is_practice = 1 WHERE id = ?", (bid,))
        for n in range(1, 11):
            if not query("SELECT 1 FROM mocks WHERE book_id = ? AND round_no = ?", (bid, n), one=True):
                execute("INSERT INTO mocks (book_id, round_no, n_items, full_score, answer_key, points) VALUES (?, ?, 0, 0, '[]', '[]')", (bid, n))
    execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('seed_practice', '1')")


def practice_workbook(mid):
    """연습 회차용 예시 엑셀: 실장 TEST반 50명의 가상 답안 + 정답·배점 줄 + 문항정보 (합답형·일반형 예시 포함)."""
    import random
    from openpyxl import Workbook
    m = load_mock(mid)
    n = m["n_items"] or (20 if m["kind"] == "복습 테스트" else 25)
    rng = random.Random(mid)
    key = [rng.randint(1, 5) for _ in range(n)]
    hap = min(n, 7)                                  # 7번은 합답형 예시
    key[hap - 1] = 5
    pts = [2] * n if m["kind"] == "모의고사" else [1] * n
    wb = Workbook()
    ws = wb.active
    ws.title = "OMR"
    ws.append(["이름", "수험번호", "반"] + list(range(1, n + 1)))
    ws.append(["정답", "", ""] + key)
    ws.append(["배점", "", ""] + pts)
    for s in sorted(student_index(practice=True), key=lambda s: s["student_no"]):
        skill = rng.uniform(0.45, 0.95)
        row = []
        for i, k in enumerate(key):
            hard = 0.25 if i >= n * 2 // 3 else 0
            if rng.random() < skill - hard:
                row.append(k)
            elif i == hap - 1:
                row.append(rng.choice([3, 3, 4, 1]))
            else:
                row.append(rng.choice([c for c in range(1, 6) if c != k]) if rng.random() > 0.05 else None)
        ws.append([s["name"], "9999" + s["parent8"][-4:], s["cls"]] + row)
    info = wb.create_sheet("문항정보")
    info.append(["문항번호", "정답", "배점", "단원", "핵심개념", "문항형식", "선지구성", "보기함정", "선지분석"])
    units = ["물질의 규칙성", "화학 결합", "지권의 변화", "역학 시스템", "생명 시스템"]
    for i in range(1, n + 1):
        k = key[i - 1]
        if i == hap:
            info.append([i, k, pts[i - 1], "산과 염기", "중화 반응 그래프", "합답형", "①ㄱ ②ㄴ ③ㄱ,ㄷ ④ㄴ,ㄷ ⑤ㄱ,ㄴ,ㄷ",
                         "ㄱ(O): 혼합 용액 속 이온 수를 섞기 전과 같다고 봄 [개념 부족] / ㄴ(O): 그래프 x축을 넣은 부피가 아니라 시간으로 읽음 [자료 해석] / ㄷ(O): 단위 환산을 빠뜨림 [계산 실수]", ""])
        else:
            w1, w2 = (k % 5) + 1, ((k + 1) % 5) + 1
            info.append([i, k, pts[i - 1], units[i % len(units)], "", "일반", "", "",
                         f"{w1}번: 개념의 정의를 반대로 기억함(개념 부족) / {w2}번: 문제의 조건 하나를 놓침(조건 독해)"])
    buf = __import__("io").BytesIO()
    wb.save(buf)
    return buf.getvalue()
