"""공부 도구: 오답 노트, 시간표·D-day, 과제 제출함, 성적 리포트.
학생 화면(/s/...)과 선생님 화면(/t/...)을 함께 둔다. 학생은 본인 기록과 본인 반 자료만 본다."""
import json
import os
import re
from datetime import date, datetime, timedelta

from flask import Blueprint, abort, current_app, flash, g, jsonify, redirect, render_template, request, url_for

import analysis
import taskkit
from db import execute, get_setting, query, set_setting
from security import (IMAGE_EXTS, audit, delete_file, login_required, save_upload, student_required,
                      staff_required)

bp = Blueprint("study", __name__)

WRONG_REASONS = ["개념 부족", "자료 해석", "조건 독해", "계산 실수", "시간 부족", "찍음"]   # 분석·첨삭과 같은 이름
TASK_EXTS = IMAGE_EXTS | {"pdf"}
WEEKDAYS = "월화수목금토일"
UNITS = ["과학의 기초", "물질과 규칙성", "시스템과 상호작용", "변화와 다양성", "환경과 에너지", "과학과 미래사회"]


def _me():
    s = query("""SELECT s.*, c.name AS class_name FROM students s JOIN classes c ON c.id = s.class_id
                 WHERE s.id = ? AND s.active = 1""", (g.user["student_id"],), one=True)
    if s is None:
        abort(403)
    return s


def _parse_day(raw, default=None):
    try:
        return date.fromisoformat((raw or "").strip())
    except ValueError:
        return default



def dday_info():
    """설정된 수능일까지 남은 날. 없으면 None."""
    d = _parse_day(get_setting("exam_day"))
    if d is None:
        return None
    left = (d - date.today()).days
    return {"day": d.isoformat(), "left": left, "label": get_setting("exam_label", "수능")}


BREAK_AHEAD = 21       # 휴강 예정은 시작 3주 전부터 알린다


def breaks_for(class_id, ahead=BREAK_AHEAD):
    """이 반(또는 모든 반) 휴강 중 아직 끝나지 않았고 ahead 일 안에 시작하는 것. 지금 휴강 중이면 now=True."""
    today = date.today()
    rows = query("""SELECT * FROM class_breaks WHERE (class_id IS NULL OR class_id = ?) AND ends >= ? AND starts <= ?
                    ORDER BY starts""", (class_id, today.isoformat(), (today + timedelta(days=ahead)).isoformat()))
    out = []
    for r in rows:
        back = date.fromisoformat(r["ends"]) + timedelta(days=1)
        out.append(dict(r, now=r["starts"] <= today.isoformat(), back=back.isoformat(), back_left=(back - today).days))
    return out


def _week_off(brks):
    """이번 주 요일(0~6) 중 휴강인 날."""
    monday = date.today() - timedelta(days=date.today().weekday())
    days = [(monday + timedelta(days=i)).isoformat() for i in range(7)]
    return {i for i, d in enumerate(days) if any(b["starts"] <= d <= b["ends"] for b in brks)}


TONE_ORDER = [2, 0, 1, 5, 4, 6, 3, 7]   # 하늘, 벚꽃, 말차, 귤, 등꽃, 청록, 유자, 벽돌


def class_slots(class_id):
    """반 시간표. 수업 이름마다 다른 색을 순서대로 붙인다(같은 이름은 같은 색, 8개까지 겹치지 않음)."""
    rows = query("SELECT * FROM timetable WHERE class_id = ? ORDER BY weekday, starts, id", (class_id,))
    tones = {}
    for r in rows:
        key = r["title"].replace(" ", "")
        if key not in tones:
            tones[key] = TONE_ORDER[len(tones) % len(TONE_ORDER)]
    return [dict(r, tone=tones[r["title"].replace(" ", "")]) for r in rows]


def my_slots(user_id):
    return [dict(r) for r in query("SELECT * FROM my_timetable WHERE user_id = ? ORDER BY weekday, starts, id", (user_id,))]


def today_classes(user_id):
    """오늘 요일의 내 시간표 (시작 시간 순)."""
    wd = date.today().weekday()
    return [s for s in my_slots(user_id) if s["weekday"] == wd]


# =====================================================================
# 2. 오답 노트 (시험 분석에서 틀린 문항 자동 정리)
# =====================================================================

def wrong_list(user_id, only_open=False):
    from views.books import _stats
    import exams
    u = query("SELECT student_id FROM users WHERE id = ?", (user_id,), one=True)
    if u and u["student_id"]:
        exams.sync_entries(student_id=u["student_id"])
    entries = query("""SELECT e.*, m.round_no, m.title AS mtitle, m.answer_key, m.points, m.n_items, m.full_score,
                              m.book_id, b.title AS book_title, b.kind, m.id AS mid
                       FROM mock_entries e JOIN mocks m ON m.id = e.mock_id JOIN books b ON b.id = m.book_id
                       WHERE e.user_id = ? AND e.mode = 'answers' AND e.score IS NOT NULL AND m.open = 1
                       ORDER BY e.updated_at DESC""", (user_id,))
    notes = {(n["mock_id"], n["item_no"]): n for n in query("SELECT * FROM wrong_notes WHERE user_id = ?", (user_id,))}
    groups = []
    for e in entries:
        key, points = json.loads(e["answer_key"]), json.loads(e["points"])
        wrong = analysis.wrong_items(e["answers"], key)
        if not wrong:
            continue
        stats = _stats({**dict(e), "id": e["mid"]})
        rates = {it["no"]: it["wrong_pct"] for it in stats["items"]}
        items = []
        for no in wrong:
            n = notes.get((e["mid"], no))
            reviewed = bool(n and n["reviewed_at"])
            if only_open and reviewed:
                continue
            items.append({"no": no, "mine": e["answers"][no - 1], "points": points[no - 1],
                          "rate": rates.get(no), "reason": n["reason"] if n else "",
                          "memo": n["memo"] if n else "", "reviewed": reviewed})
        groups.append({"mock_id": e["mid"], "kind": e["kind"], "title": f"{e['book_title']} {e['round_no']}회", "score": e["score"],
                       "full": e["full_score"], "rows": items, "total": len(wrong),
                       "done": sum(1 for no in wrong if (e["mid"], no) in notes and notes[(e["mid"], no)]["reviewed_at"])})
    return groups


@bp.route("/s/wrong")
@student_required
def wrong_notes():
    only_open = request.args.get("view") == "open"
    groups = wrong_list(g.user["id"], only_open)
    kind = analysis.kind_arg(request.args.get("kind"), groups[0]["kind"] if groups else "복습 테스트")   # 탭: 복습 테스트 / 모의고사
    kind_counts = {k: sum(1 for gr in groups if gr["kind"] == k) for k in analysis.KIND_KEYS.values()}
    groups = [gr for gr in groups if gr["kind"] == kind]
    rounds = [(gr["mock_id"], gr["title"]) for gr in groups]       # 회차 고르기 (한 회차만 정리할 때)
    pick = request.args.get("mock", type=int)
    if pick:
        groups = [gr for gr in groups if gr["mock_id"] == pick]
    reasons = query("""SELECT w.reason, COUNT(*) AS n FROM wrong_notes w JOIN mocks m ON m.id = w.mock_id JOIN books b ON b.id = m.book_id
                       WHERE w.user_id = ? AND w.reason != '' AND b.kind = ? GROUP BY w.reason ORDER BY n DESC""", (g.user["id"], kind))
    import sysdata
    code = sysdata.code_of_student(g.user["student_id"])
    sys_groups = sysdata.wrong_notes(code)
    if only_open:
        sys_groups = [dict(gr, items=[i for i in gr["items"] if i["redo"] != "맞힘"]) for gr in sys_groups]
        sys_groups = [gr for gr in sys_groups if gr["items"]]
    return render_template("study/wrong.html", kind=kind, kind_key=next(k for k, v in analysis.KIND_KEYS.items() if v == kind),
                           kind_counts=kind_counts, rounds=rounds, pick=pick, groups=groups, reasons=WRONG_REASONS, reason_counts=reasons,
                           only_open=only_open, fmt=analysis._fmt, code=code, sys_groups=sys_groups,
                           sys_types=sysdata.type_counts(sysdata.wrong_notes(code)), sfmt=sysdata.fmt)


@bp.route("/s/wrong/<int:mid>/<int:no>", methods=["POST"])
@student_required
def wrong_update(mid, no):
    e = query("""SELECT e.answers, m.answer_key FROM mock_entries e JOIN mocks m ON m.id = e.mock_id
                 WHERE e.mock_id = ? AND e.user_id = ?""", (mid, g.user["id"]), one=True)
    if e is None or no not in analysis.wrong_items(e["answers"], json.loads(e["answer_key"])):
        abort(404)
    reason = request.form.get("reason", "")
    reason = reason if reason in WRONG_REASONS else ""
    memo = request.form.get("memo", "").strip()[:300]
    reviewed = request.form.get("reviewed") == "1"
    execute("""INSERT INTO wrong_notes (user_id, mock_id, item_no, reason, memo, reviewed_at)
               VALUES (?, ?, ?, ?, ?, CASE WHEN ? THEN datetime('now', 'localtime') END)
               ON CONFLICT(user_id, mock_id, item_no) DO UPDATE SET reason = excluded.reason, memo = excluded.memo,
               reviewed_at = excluded.reviewed_at""", (g.user["id"], mid, no, reason, memo, 1 if reviewed else 0))
    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify(ok=True)
    flash(f"{no}번을 저장했어요.", "ok")
    k = query("SELECT b.kind FROM mocks m JOIN books b ON b.id = m.book_id WHERE m.id = ?", (mid,), one=True)
    kind = "mock" if k and k["kind"] == "모의고사" else "review"
    return redirect(url_for("study.wrong_notes", view=request.args.get("view"), mock=request.args.get("mock"), kind=kind) + f"#w-{mid}-{no}")


def _classes():
    return query("SELECT id, name FROM classes WHERE archived = 0 ORDER BY name")


# =====================================================================
# 5. 시간표 · D-day
# =====================================================================

def _valid_time(t):
    return len(t) == 5 and t[2] == ":" and t[:2].isdigit() and t[3:].isdigit() and int(t[:2]) < 24 and int(t[3:]) < 60


TT_STEP = 10            # 격자 한 칸 = 10분
TT_FIRST, TT_LAST = 7, 24   # 고를 수 있는 시간 범위 (07:00 ~ 24:00)


def _mins(t):
    return int(t[:2]) * 60 + int(t[3:])


def _tt_grid(slots, off=()):
    """에브리타임처럼 요일 × 시간 격자. 칸 위치는 CSS 클래스(tt-rN, tt-spN, tt-cN)로만 정한다(CSP: 인라인 style 금지)."""
    first = min([_mins(s["starts"]) // 60 for s in slots] + [9])
    last = max([-(-_mins(s["ends"]) // 60) for s in slots] + [22])
    first, last = max(TT_FIRST, first), min(TT_LAST, last)
    days = list(range(5)) + [d for d in (5, 6) if any(s["weekday"] == d for s in slots)]
    if 5 not in days:
        days.append(5)                                   # 토요일은 늘 보여 준다 (재수생은 토요일도 공부)
    days.sort()
    col = {d: i + 1 for i, d in enumerate(days)}
    blocks = []
    for s in slots:
        if s["weekday"] not in col:
            continue
        st = max(_mins(s["starts"]), first * 60)
        en = min(_mins(s["ends"]), last * 60)
        r0 = (st - first * 60) // TT_STEP + 1
        span = max(3, -(-(en - st) // TT_STEP))
        blocks.append(dict(s, r=r0, sp=span, c=col[s["weekday"]], short=span < 6))
    hours = list(range(first, last))
    return {"days": [{"i": d, "label": WEEKDAYS[d], "c": col[d], "today": d == date.today().weekday(), "off": d in off} for d in days],
            "hours": [{"h": h, "r": (h - first) * 60 // TT_STEP + 1} for h in hours], "blocks": blocks,
            "rows": (last - first) * 60 // TT_STEP, "first": first, "ncols": len(days)}


def _slot_form():
    """시간표 칸 입력값 확인. 돌려주는 값: (요일 목록, 시작, 끝, 이름, 장소, 색) 또는 오류 문장."""
    days = sorted({int(x) for x in request.form.getlist("weekday") if x.isdigit() and 0 <= int(x) <= 6})
    starts, ends = request.form.get("starts", ""), request.form.get("ends", "")
    title = request.form.get("title", "").strip()[:30]
    room = request.form.get("room", "").strip()[:30]
    tone = request.form.get("tone", type=int)
    if not title:
        return "이름을 적어 주세요."
    if not days:
        return "요일을 하나 이상 골라 주세요."
    if not (_valid_time(starts) and _valid_time(ends)):
        return "시작 및 끝 시간을 확인해 주세요."
    if starts >= ends:
        return "끝나는 시간이 시작 시간보다 뒤여야 해요."
    if starts < f"{TT_FIRST:02d}:00" or (ends > "24:00"):
        return "07:00부터 24:00 사이로 넣어 주세요."
    return days, starts, ends, title, room, tone if tone is not None and 0 <= tone < 8 else None


def _overlap(uid, wd, starts, ends, skip=None):
    return query("""SELECT title, starts, ends FROM my_timetable WHERE user_id = ? AND weekday = ? AND id != ?
                    AND starts < ? AND ends > ? LIMIT 1""", (uid, wd, skip or 0, ends, starts), one=True)


def _auto_tone(uid, title):
    """같은 이름은 같은 색, 새 이름은 아직 안 쓴 색부터."""
    same = query("SELECT tone FROM my_timetable WHERE user_id = ? AND REPLACE(title, ' ', '') = ? LIMIT 1",
                 (uid, title.replace(" ", "")), one=True)
    if same:
        return same["tone"]
    used = [r["tone"] for r in query("SELECT DISTINCT tone FROM my_timetable WHERE user_id = ?", (uid,))]
    return next((t for t in TONE_ORDER if t not in used), TONE_ORDER[len(used) % len(TONE_ORDER)])


@bp.route("/s/timetable", methods=["GET", "POST"])
@student_required
def timetable():
    me = _me()
    uid = g.user["id"]
    if request.method == "POST":
        got = _slot_form()
        if isinstance(got, str):
            flash(got, "error")
        else:
            days, starts, ends, title, room, tone = got
            clash = next(((d, c) for d in days if (c := _overlap(uid, d, starts, ends))), None)
            if clash:
                d, c = clash
                flash(f"{WEEKDAYS[d]}요일 {c['starts']}–{c['ends']} '{c['title']}'과 시간이 중복돼요.", "error")
            else:
                tone = _auto_tone(uid, title) if tone is None else tone
                for d in days:
                    execute("INSERT INTO my_timetable (user_id, weekday, starts, ends, title, room, tone) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (uid, d, starts, ends, title, room, tone))
                flash(f"{', '.join(WEEKDAYS[d] for d in days)}요일 {starts}–{ends}에 '{title}'을 추가했어요.", "ok")
        return redirect(url_for("study.timetable"))
    slots = my_slots(uid)
    hm = datetime.now().strftime("%H:%M")
    today = [s for s in slots if s["weekday"] == date.today().weekday()]
    current = next((s for s in today if s["starts"] <= hm < s["ends"]), None)
    upnext = next((s for s in today if s["starts"] > hm), None)
    class_has = bool(me["class_id"]) and bool(query("SELECT 1 FROM timetable WHERE class_id = ? LIMIT 1", (me["class_id"],), one=True))
    brks = breaks_for(me["class_id"])
    from views.schedule import student_week
    wk = student_week(g.user["student_id"]) if g.user["student_id"] else None   # 이번 주차 진도·받을 교재 (수업 일정)
    return render_template("study/timetable.html", grid=_tt_grid(slots, _week_off(brks)), dday=dday_info(), brks=brks, me=me, weekdays=WEEKDAYS,
                           current=current, upnext=upnext, has_slots=bool(slots), class_has=class_has and not slots, wk=wk)


@bp.route("/s/timetable/<int:tid>", methods=["POST"])
@student_required
def timetable_edit(tid):
    uid = g.user["id"]
    row = query("SELECT * FROM my_timetable WHERE id = ? AND user_id = ?", (tid, uid), one=True)
    if row is None:
        abort(404)
    if request.form.get("action") == "delete":
        execute("DELETE FROM my_timetable WHERE id = ?", (tid,))
        flash(f"'{row['title']}'을 삭제했어요.", "ok")
        return redirect(url_for("study.timetable"))
    got = _slot_form()
    if isinstance(got, str):
        flash(got, "error")
        return redirect(url_for("study.timetable"))
    days, starts, ends, title, room, tone = got
    wd = days[0]
    c = _overlap(uid, wd, starts, ends, skip=tid)
    if c:
        flash(f"{WEEKDAYS[wd]}요일 {c['starts']}–{c['ends']} '{c['title']}'과 시간이 중복돼요.", "error")
    else:
        execute("UPDATE my_timetable SET weekday = ?, starts = ?, ends = ?, title = ?, room = ?, tone = ? WHERE id = ?",
                (wd, starts, ends, title, room, row["tone"] if tone is None else tone, tid))
        flash("수정했어요.", "ok")
    return redirect(url_for("study.timetable"))


@bp.route("/s/timetable/import", methods=["POST"])
@student_required
def timetable_import():
    """처음 시작할 때만: 예전에 선생님이 넣어 둔 반 시간표를 내 시간표로 한 번에 가져온다."""
    me, uid = _me(), g.user["id"]
    if query("SELECT 1 FROM my_timetable WHERE user_id = ? LIMIT 1", (uid,), one=True):
        flash("이미 내 시간표가 있어요.", "error")
        return redirect(url_for("study.timetable"))
    rows = class_slots(me["class_id"]) if me["class_id"] else []
    for r in rows:
        execute("INSERT INTO my_timetable (user_id, weekday, starts, ends, title, room, tone) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (uid, r["weekday"], r["starts"], r["ends"], r["title"], r["room"], r["tone"]))
    flash(f"반 시간표 {len(rows)}칸을 가져왔어요.", "ok")
    return redirect(url_for("study.timetable"))


@bp.route("/t/timetable", methods=["GET", "POST"])
@staff_required
def t_timetable():
    """주요 일정: 수능 D-day 및 휴강 설정 (시간표는 학생이 각자 만든다)."""
    if request.method == "POST" and request.form.get("action") == "break_del":
        execute("DELETE FROM class_breaks WHERE id = ?", (request.form.get("id", type=int),))
        flash("휴강을 삭제했어요.", "ok")
        return redirect(url_for("study.t_timetable"))
    if request.method == "POST" and request.form.get("action") == "break_add":
        s, e = _parse_day(request.form.get("starts")), _parse_day(request.form.get("ends"))
        cid = request.form.get("class_id", type=int)
        if cid and not query("SELECT 1 FROM classes WHERE id = ?", (cid,), one=True):
            abort(404)
        if s is None or e is None or e < s:
            flash("휴강 시작일 및 끝나는 날을 확인하세요.", "error")
        else:
            execute("INSERT INTO class_breaks (class_id, starts, ends, note) VALUES (?, ?, ?, ?)",
                    (cid or None, s.isoformat(), e.isoformat(), request.form.get("note", "").strip()[:40]))
            audit("break_add", f"class:{cid or 'all'} {s}~{e}")
            flash(f"{s.isoformat()}~{e.isoformat()} 휴강을 넣었어요.", "ok")
        return redirect(url_for("study.t_timetable"))
    if request.method == "POST":
        d = _parse_day(request.form.get("exam_day"))
        label = request.form.get("exam_label", "").strip()[:20] or "수능"
        if d is None:
            flash("날짜를 확인하세요.", "error")
        else:
            set_setting("exam_day", d.isoformat())
            set_setting("exam_label", label)
            flash(f"{label} 날짜를 {d.isoformat()}로 정했어요.", "ok")
        return redirect(url_for("study.t_timetable"))
    breaks = query("""SELECT b.*, c.name AS class_name FROM class_breaks b LEFT JOIN classes c ON c.id = b.class_id
                      WHERE b.ends >= ? ORDER BY b.starts""", (date.today().isoformat(),))
    classes = query("SELECT id, name FROM classes WHERE archived = 0 AND is_test = 0 ORDER BY track, name")
    return render_template("study/t_timetable.html", cid=None, dday=dday_info(), exam_label=get_setting("exam_label", "수능"),
                           breaks=breaks, classes=classes, today=date.today().isoformat())


# =====================================================================
# 6. 성적 리포트 (선생님: 학생별 / 학생: 내 리포트). 인쇄하면 A4 한 장 흐름
# =====================================================================

def build_report(student_id):
    from views.books import _stats
    from views.teacher import _score_chart
    s = query("""SELECT s.*, c.name AS class_name FROM students s JOIN classes c ON c.id = s.class_id WHERE s.id = ?""",
              (student_id,), one=True)
    if s is None:
        abort(404)
    user = query("SELECT id FROM users WHERE student_id = ?", (student_id,), one=True)
    import exams
    from collections import Counter
    hist = exams.history(student_id)   # OMR 결과(exam_results, 학생 기준). 계정이 없는 학생도 나온다 (학생 상세·학부모 리포트와 같은 출처)
    mocks, focus = [], None
    for h in hist:
        m = h["mock"]
        if m["is_practice"]:
            continue
        st = _stats(m)
        score = h["r"]["score"]
        mocks.append({"title": f"{m['book_title']} {m['round_no']}회", "score": score, "full": m["full_score"],
                      "grade": analysis.grade_for(score, st["cuts"]), "n": st["n"], "wrong": h["wrong"], "kind": m["kind"],
                      "rate": round(100 * score / m["full_score"]) if m["full_score"] else None, "date": m["exam_date"] or "",
                      "avg": h["st"]["avg"]})
    reasons = [{"reason": t, "n": n} for t, n in Counter(   # 대표 이유: 학생 선택 > 조교 첨삭 > 자동 분석 (exams.pick_reason)
        a["type"] for h in hist for a in h["wrongs"] if a["type"]).most_common()]
    if user:
        uid = user["id"]
        focus = query("""SELECT COALESCE(SUM(minutes), 0) AS m, COUNT(*) AS n FROM focus_logs
                         WHERE user_id = ? AND ended_at >= date('now', 'localtime', '-27 days')""", (uid,), one=True)
    import sysdata
    code = sysdata.code_of_student(student_id)
    sys_scores = sysdata.scores(code)
    chart = _score_chart([{"pct": round(100 * m["score"] / m["full"], 1), "label": m["title"], "date": ""} for m in mocks if m["full"]])
    if sys_scores:                                   # 조교 시스템 성적이 있으면 그것으로 흐름을 그린다
        chart = _score_chart([{"pct": r["pct"], "label": r["name"], "date": r["day"]} for r in sys_scores if r["pct"] is not None])
    from views.care import rate_chart
    kinds = []                                       # 복습 테스트와 모의고사는 따로 (인쇄라 탭 대신 칸을 나눈다)
    for k in analysis.KIND_KEYS.values():
        rows = [m for m in mocks if m["kind"] == k]
        if rows:
            kinds.append({"kind": k, "rows": rows, "chart": rate_chart(list(reversed(rows)))})
    return {"s": s, "chart": chart, "mocks": mocks, "kinds": kinds, "reasons": reasons, "focus": focus,
            "today": date.today().isoformat(), "code": code, "sys_scores": sys_scores,
            "units": sysdata.report(code), "learn": sysdata.learn_type(code), "study": sysdata.study_type(code),
            "sys_types": sysdata.type_counts(sysdata.wrong_notes(code)), "sfmt": sysdata.fmt}


@bp.route("/t/students/<int:sid>/report")
@staff_required
def t_report(sid):
    audit("report_view", f"student:{sid}")
    return render_template("study/report.html", r=build_report(sid), fmt=analysis._fmt, teacher=True)


@bp.route("/s/report")
@student_required
def s_report():
    return render_template("study/report.html", r=build_report(g.user["student_id"]), fmt=analysis._fmt, teacher=False)


# =====================================================================
# 8. 자주 묻는 질문(FAQ) 고정
# =====================================================================

@bp.route("/t/questions/<int:qid>/faq", methods=["POST"])
@login_required(("teacher", "assistant"))
def t_faq(qid):
    q = query("SELECT id, faq, qtype FROM questions WHERE id = ?", (qid,), one=True)
    if q is None or q["qtype"] != "학습질문":
        abort(404)
    execute("UPDATE questions SET faq = ? WHERE id = ?", (0 if q["faq"] else 1, qid))
    flash("자주 묻는 질문에서 뺐어요." if q["faq"] else "자주 묻는 질문으로 고정했어요.", "ok")
    return redirect(url_for("teacher.question_detail", qid=qid))


# =====================================================================
# 9. 내 공부: 오늘 요약, 주간 공부 순위, 일별 이용 시간, 학습 진도
# =====================================================================

def _day_chart(days, avg):
    """일별 이용 시간 막대(집중·통과 Quiz·영단어 쌓기) + 공부한 학생 평균 꺾은선. 단위 분."""
    import progress
    w, h, left, right, top, bottom = 420, 230, 34, 8, 12, 28
    peak = max([d["total"] for d in days] + list(avg.values()) + [30])
    step = 30 if peak <= 150 else 60 if peak <= 300 else 120
    ymax = -(-peak // step) * step
    pw, ph = w - left - right, h - top - bottom
    slot = pw / len(days)
    bw = min(34, slot * 0.5)
    y = lambda v: top + ph * (1 - v / ymax)
    bars, line = [], []
    for i, d in enumerate(days):
        cx = left + slot * (i + 0.5)
        base = 0
        for k, _ in progress.KINDS:
            if d[k]:
                bars.append({"k": k, "x": round(cx - bw / 2, 1), "y": round(y(base + d[k]), 1),
                             "w": round(bw, 1), "h": round(y(base) - y(base + d[k]), 1)})
                base += d[k]
        if d["day"] in avg:
            line.append({"x": round(cx, 1), "y": round(y(avg[d["day"]]), 1)})
    return {"w": w, "h": h, "left": left, "right": w - right, "bottom": top + ph, "bars": bars, "line": line,
            "poly": " ".join(f"{p['x']},{p['y']}" for p in line),
            "ticks": [{"v": v, "y": round(y(v), 1)} for v in range(0, ymax + 1, step)],
            "labels": [{"x": round(left + slot * (i + 0.5), 1), "t": f"{int(d['day'][5:7])}.{int(d['day'][8:])}",
                        "m": d["total"]} for i, d in enumerate(days)]}


def my_study(uid):
    import progress
    days = progress.daily(uid, 7)
    return {"sum": progress.today_summary(uid), "rank": progress.weekly_ranking(uid),
            "chart": _day_chart(days, progress.class_average(7)), "days": days, "kinds": progress.KINDS,
            "topics": progress.topic_progress(uid), "vocab": progress.vocab_progress(uid)}


@bp.route("/s/my")
@student_required
def s_my():
    me = query("""SELECT u.nickname, s.name, c.name AS class_name FROM users u LEFT JOIN students s ON s.id = u.student_id
                  LEFT JOIN classes c ON c.id = s.class_id WHERE u.id = ?""", (g.user["id"],), one=True)
    return render_template("study/my.html", me=me, m=my_study(g.user["id"]))


@bp.route("/s/my/reset", methods=["POST"])
@student_required
def s_my_reset():
    import progress
    import quiz
    topic = request.form.get("topic", "")
    if topic == "all":
        progress.reset(g.user["id"], list(quiz.TOPICS))
        flash("통과 Quiz 학습 진도를 모두 초기화했어요.", "ok")
    elif topic in quiz.TOPICS:
        progress.reset(g.user["id"], [topic])
        flash(f"TOPIC {topic} 진도를 초기화했어요.", "ok")
    else:
        abort(400)
    return redirect(url_for("study.s_my") + "#progress")
