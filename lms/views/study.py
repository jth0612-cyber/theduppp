"""공부 도구: 오답 노트, 시간표·D-day, 과제 제출함, 성적 리포트.
학생 화면(/s/...)과 선생님 화면(/t/...)을 함께 둔다. 학생은 본인 기록과 본인 반 자료만 본다."""
import json
import os
import re
from datetime import date, datetime

from flask import Blueprint, abort, current_app, flash, g, jsonify, redirect, render_template, request, url_for

import analysis
import taskkit
from db import execute, get_setting, query, set_setting
from security import (IMAGE_EXTS, audit, delete_file, login_required, save_upload, student_required,
                      staff_required, teacher_only, teacher_required)

bp = Blueprint("study", __name__)

WRONG_REASONS = ["개념 부족", "자료 해석", "조건 놓침", "계산 실수", "시간 부족", "찍음"]
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
# 2. 오답 노트 (모의고사 분석에서 틀린 문항 자동 정리)
# =====================================================================

def wrong_list(user_id, only_open=False):
    from views.books import _stats
    entries = query("""SELECT e.*, m.round_no, m.title AS mtitle, m.answer_key, m.points, m.n_items, m.full_score,
                              m.book_id, b.title AS book_title, m.id AS mid
                       FROM mock_entries e JOIN mocks m ON m.id = e.mock_id JOIN books b ON b.id = m.book_id
                       JOIN user_books ub ON ub.book_id = b.id AND ub.user_id = e.user_id
                       WHERE e.user_id = ? AND e.mode = 'answers' AND e.score IS NOT NULL
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
        groups.append({"mock_id": e["mid"], "title": f"{e['book_title']} {e['round_no']}회", "score": e["score"],
                       "full": e["full_score"], "rows": items, "total": len(wrong),
                       "done": sum(1 for no in wrong if (e["mid"], no) in notes and notes[(e["mid"], no)]["reviewed_at"])})
    return groups


@bp.route("/s/wrong")
@student_required
def wrong_notes():
    only_open = request.args.get("view") == "open"
    groups = wrong_list(g.user["id"], only_open)
    reasons = query("""SELECT reason, COUNT(*) AS n FROM wrong_notes WHERE user_id = ? AND reason != ''
                       GROUP BY reason ORDER BY n DESC""", (g.user["id"],))
    import sysdata
    code = sysdata.code_of_student(g.user["student_id"])
    sys_groups = sysdata.wrong_notes(code)
    if only_open:
        sys_groups = [dict(gr, items=[i for i in gr["items"] if i["redo"] != "맞힘"]) for gr in sys_groups]
        sys_groups = [gr for gr in sys_groups if gr["items"]]
    return render_template("study/wrong.html", groups=groups, reasons=WRONG_REASONS, reason_counts=reasons,
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
    return redirect(url_for("study.wrong_notes", view=request.args.get("view")) + f"#w-{mid}-{no}")


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


def _tt_grid(slots):
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
    return {"days": [{"i": d, "label": WEEKDAYS[d], "c": col[d], "today": d == date.today().weekday()} for d in days],
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
        return "시작·끝 시간을 확인해 주세요."
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
                flash(f"{WEEKDAYS[d]}요일 {c['starts']}–{c['ends']} '{c['title']}'과 시간이 겹쳐요.", "error")
            else:
                tone = _auto_tone(uid, title) if tone is None else tone
                for d in days:
                    execute("INSERT INTO my_timetable (user_id, weekday, starts, ends, title, room, tone) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (uid, d, starts, ends, title, room, tone))
                flash(f"{', '.join(WEEKDAYS[d] for d in days)}요일 {starts}–{ends}에 '{title}'을 넣었어요.", "ok")
        return redirect(url_for("study.timetable"))
    slots = my_slots(uid)
    hm = datetime.now().strftime("%H:%M")
    today = [s for s in slots if s["weekday"] == date.today().weekday()]
    current = next((s for s in today if s["starts"] <= hm < s["ends"]), None)
    upnext = next((s for s in today if s["starts"] > hm), None)
    class_has = bool(me["class_id"]) and bool(query("SELECT 1 FROM timetable WHERE class_id = ? LIMIT 1", (me["class_id"],), one=True))
    return render_template("study/timetable.html", grid=_tt_grid(slots), dday=dday_info(), me=me, weekdays=WEEKDAYS,
                           current=current, upnext=upnext, has_slots=bool(slots), class_has=class_has and not slots)


@bp.route("/s/timetable/<int:tid>", methods=["POST"])
@student_required
def timetable_edit(tid):
    uid = g.user["id"]
    row = query("SELECT * FROM my_timetable WHERE id = ? AND user_id = ?", (tid, uid), one=True)
    if row is None:
        abort(404)
    if request.form.get("action") == "delete":
        execute("DELETE FROM my_timetable WHERE id = ?", (tid,))
        flash(f"'{row['title']}'을 지웠어요.", "ok")
        return redirect(url_for("study.timetable"))
    got = _slot_form()
    if isinstance(got, str):
        flash(got, "error")
        return redirect(url_for("study.timetable"))
    days, starts, ends, title, room, tone = got
    wd = days[0]
    c = _overlap(uid, wd, starts, ends, skip=tid)
    if c:
        flash(f"{WEEKDAYS[wd]}요일 {c['starts']}–{c['ends']} '{c['title']}'과 시간이 겹쳐요.", "error")
    else:
        execute("UPDATE my_timetable SET weekday = ?, starts = ?, ends = ?, title = ?, room = ?, tone = ? WHERE id = ?",
                (wd, starts, ends, title, room, row["tone"] if tone is None else tone, tid))
        flash("고쳤어요.", "ok")
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
    flash(f"반 시간표 {len(rows)}칸을 가져왔어요. 이제 마음대로 고칠 수 있어요.", "ok")
    return redirect(url_for("study.timetable"))


@bp.route("/t/timetable", methods=["GET", "POST"])
@staff_required
def t_timetable():
    """수능 D-day 설정 (시간표는 학생이 각자 만든다)."""
    if request.method == "POST":
        teacher_only()  # 조교는 보기만
        d = _parse_day(request.form.get("exam_day"))
        label = request.form.get("exam_label", "").strip()[:20] or "수능"
        if d is None:
            flash("날짜를 확인하세요.", "error")
        else:
            set_setting("exam_day", d.isoformat())
            set_setting("exam_label", label)
            flash(f"{label} 날짜를 {d.isoformat()}로 정했습니다.", "ok")
        return redirect(url_for("study.t_timetable"))
    return render_template("study/t_timetable.html", cid=None, dday=dday_info(), exam_label=get_setting("exam_label", "수능"))


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
    scores = query("""SELECT e.name, e.exam_date, e.max_score, sc.score, ROUND(sc.score * 100.0 / e.max_score, 1) AS pct,
                             (SELECT ROUND(AVG(score) * 100.0 / e.max_score, 1) FROM scores WHERE exam_id = e.id) AS avg_pct
                      FROM scores sc JOIN exams e ON e.id = sc.exam_id WHERE sc.student_id = ?
                      ORDER BY e.exam_date, e.id""", (student_id,))
    chart = _score_chart([{"pct": r["pct"], "label": r["name"], "date": r["exam_date"]} for r in scores])
    mocks, reasons, focus = [], [], None
    if user:
        uid = user["id"]
        for e in query("""SELECT e.*, m.round_no, m.full_score, m.answer_key, m.points, m.id AS mid, b.title AS book_title
                          FROM mock_entries e JOIN mocks m ON m.id = e.mock_id JOIN books b ON b.id = m.book_id
                          WHERE e.user_id = ? AND e.score IS NOT NULL ORDER BY m.book_id, m.round_no""", (uid,)):
            st = _stats({**dict(e), "id": e["mid"]})
            wrong = analysis.wrong_items(e["answers"], json.loads(e["answer_key"])) if e["mode"] == "answers" else []
            mocks.append({"title": f"{e['book_title']} {e['round_no']}회", "score": e["score"], "full": e["full_score"],
                          "grade": analysis.grade_for(e["score"], st["cuts"]), "n": st["n"], "wrong": wrong})
        reasons = query("""SELECT reason, COUNT(*) AS n FROM wrong_notes WHERE user_id = ? AND reason != ''
                           GROUP BY reason ORDER BY n DESC""", (uid,))
        focus = query("""SELECT COALESCE(SUM(minutes), 0) AS m, COUNT(*) AS n FROM focus_logs
                         WHERE user_id = ? AND ended_at >= date('now', 'localtime', '-27 days')""", (uid,), one=True)
    import sysdata
    code = sysdata.code_of_student(student_id)
    sys_scores = sysdata.scores(code)
    if sys_scores:                                   # 조교 시스템 성적이 있으면 그것으로 흐름을 그린다
        chart = _score_chart([{"pct": r["pct"], "label": r["name"], "date": r["day"]} for r in sys_scores if r["pct"] is not None])
    return {"s": s, "scores": scores, "chart": chart, "mocks": mocks, "reasons": reasons, "focus": focus,
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
    flash("자주 묻는 질문에서 뺐습니다." if q["faq"] else "자주 묻는 질문으로 고정했습니다.", "ok")
    return redirect(url_for("teacher.question_detail", qid=qid))
