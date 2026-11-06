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


def today_classes(class_id):
    """오늘 요일의 수업 (지금 이후 수업이 먼저 오도록 시작 시간 순)."""
    wd = date.today().weekday()
    return [s for s in class_slots(class_id) if s["weekday"] == wd]


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
    return render_template("study/wrong.html", groups=groups, reasons=WRONG_REASONS, reason_counts=reasons,
                           only_open=only_open, fmt=analysis._fmt)


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

def _week_columns(slots):
    today = date.today().weekday()
    cols = [{"i": i, "label": WEEKDAYS[i], "today": i == today, "slots": [s for s in slots if s["weekday"] == i]}
            for i in range(7)]
    # 주말에 수업이 없으면 월~금만 보여 준다
    if not any(c["slots"] for c in cols[5:]):
        cols = cols[:5]
    return cols


def _valid_time(t):
    return len(t) == 5 and t[2] == ":" and t[:2].isdigit() and t[3:].isdigit() and int(t[:2]) < 24 and int(t[3:]) < 60


@bp.route("/s/timetable")
@student_required
def timetable():
    me = _me()
    slots = class_slots(me["class_id"])
    now = date.today()
    hm = datetime.now().strftime("%H:%M")
    today = [s for s in slots if s["weekday"] == now.weekday()]
    current = next((s for s in today if s["starts"] <= hm < s["ends"]), None)
    upnext = next((s for s in today if s["starts"] > hm), None)
    return render_template("study/timetable.html", cols=_week_columns(slots), dday=dday_info(), me=me,
                           current=current, upnext=upnext, has_slots=bool(slots))


@bp.route("/t/timetable", methods=["GET", "POST"])
@staff_required
def t_timetable():
    if request.method == "POST":
        teacher_only()  # 조교는 보기만
    classes = _classes()
    cid = request.values.get("class_id", type=int) or (classes[0]["id"] if classes else None)
    if request.method == "POST":
        action = request.form.get("action")
        if action == "dday":
            d = _parse_day(request.form.get("exam_day"))
            label = request.form.get("exam_label", "").strip()[:20] or "수능"
            if d is None:
                flash("날짜를 확인하세요.", "error")
            else:
                set_setting("exam_day", d.isoformat())
                set_setting("exam_label", label)
                flash(f"{label} 날짜를 {d.isoformat()}로 정했습니다.", "ok")
        elif action == "slot":
            days = [int(x) for x in request.form.getlist("weekday") if x.isdigit() and 0 <= int(x) <= 6]
            starts, ends = request.form.get("starts", ""), request.form.get("ends", "")
            title = request.form.get("title", "").strip()[:40]
            room = request.form.get("room", "").strip()[:30]
            if not cid or not days or not title or not (_valid_time(starts) and _valid_time(ends)) or starts >= ends:
                flash("반, 요일(하나 이상), 시작·끝 시간, 수업 이름을 확인하세요.", "error")
            else:
                for wd in days:
                    execute("INSERT INTO timetable (class_id, weekday, starts, ends, title, room) VALUES (?, ?, ?, ?, ?, ?)",
                            (cid, wd, starts, ends, title, room))
                flash(f"{', '.join(WEEKDAYS[d] for d in days)}요일에 '{title}'을 넣었습니다.", "ok")
        return redirect(url_for("study.t_timetable", class_id=cid))
    slots = class_slots(cid) if cid else []
    return render_template("study/t_timetable.html", classes=classes, cid=cid, cols=_week_columns(slots),
                           slots=slots, weekdays=WEEKDAYS, dday=dday_info(), exam_label=get_setting("exam_label", "수능"))


@bp.route("/t/timetable/slot/<int:tid>/delete", methods=["POST"])
@teacher_required
def t_slot_delete(tid):
    row = query("SELECT class_id FROM timetable WHERE id = ?", (tid,), one=True)
    if row is None:
        abort(404)
    execute("DELETE FROM timetable WHERE id = ?", (tid,))
    return redirect(url_for("study.t_timetable", class_id=row["class_id"]))


# =====================================================================
# 7. 과제: 정답·해설 PDF 를 올리면, 학생이 답을 입력하는 순간 채점하고 문제점을 분석
# =====================================================================

def _task_or_404(aid, class_id=None):
    a = query("SELECT * FROM assignments WHERE id = ?" + (" AND class_id = ?" if class_id else ""),
              (aid, class_id) if class_id else (aid,), one=True)
    if a is None:
        abort(404)
    a = dict(a)
    a["key"] = json.loads(a.get("answer_key") or "[]")
    a["unit_list"] = json.loads(a.get("units") or "[]")
    a["sol"] = {int(k): v for k, v in json.loads(a.get("solutions") or "{}").items()}
    return a


def _task_analysis(a, student_id):
    mine = query("SELECT * FROM task_answers WHERE assignment_id = ? AND student_id = ?", (a["id"], student_id), one=True)
    if mine is None:
        return None, None
    answers = json.loads(mine["answers"])
    others = [json.loads(r["answers"]) for r in query("SELECT answers FROM task_answers WHERE assignment_id = ? AND student_id != ?",
                                                     (a["id"], student_id))]
    return mine, dict(taskkit.analyze(a["key"], a["unit_list"], answers, others), answers=answers)


@bp.route("/s/tasks")
@student_required
def tasks():
    me = _me()
    rows = query("""SELECT a.id, a.title, a.body, a.due_on, a.answer_key, t.correct, t.total, t.created_at AS done_at
                    FROM assignments a LEFT JOIN task_answers t ON t.assignment_id = a.id AND t.student_id = ?
                    WHERE a.class_id = ? ORDER BY t.id IS NOT NULL, COALESCE(a.due_on, '9999'), a.id DESC""",
                 (me["id"], me["class_id"]))
    rows = [dict(r, n=len(json.loads(r["answer_key"] or "[]"))) for r in rows]
    return render_template("study/tasks.html", rows=rows, today=date.today().isoformat())


@bp.route("/s/tasks/<int:aid>", methods=["GET", "POST"])
@student_required
def task(aid):
    me = _me()
    a = _task_or_404(aid, me["class_id"])
    if not a["key"]:
        flash("선생님이 아직 정답을 올리지 않은 과제예요.", "error")
        return redirect(url_for("study.tasks"))
    done = query("SELECT 1 FROM task_answers WHERE assignment_id = ? AND student_id = ?", (aid, me["id"]), one=True)
    if request.method == "POST" and not done:
        answers = [(request.form.get(f"q{i + 1}") or "").strip()[:20] for i in range(len(a["key"]))]
        if not any(answers):
            flash("답을 하나 이상 입력하세요.", "error")
            return redirect(url_for("study.task", aid=aid))
        correct = sum(taskkit.grade(a["key"], answers))
        execute("INSERT INTO task_answers (assignment_id, student_id, answers, correct, total) VALUES (?, ?, ?, ?, ?)",
                (aid, me["id"], json.dumps(answers, ensure_ascii=False), correct, len(a["key"])))
        audit("task_answered", f"assignment:{aid}")
        return redirect(url_for("study.task", aid=aid))
    mine, an = _task_analysis(a, me["id"])
    return render_template("study/task.html", a=a, mine=mine, an=an, choice=[taskkit.is_choice(k) for k in a["key"]])


def _save_solution_pdf(a_id, f):
    """정답·해설 PDF 저장 → 정답표·문항별 해설·단원 짐작. (찾은 정답 수, 찾은 해설 수)"""
    fid = save_upload(f, {"pdf"})
    row = query("SELECT stored_name FROM files WHERE id = ?", (fid,), one=True)
    pages = taskkit.pdf_pages(os.path.join(current_app.config["UPLOAD_DIR"], row["stored_name"]))
    old = query("SELECT * FROM assignments WHERE id = ?", (a_id,), one=True)
    key = json.loads(old["answer_key"] or "[]") or taskkit.guess_key(pages)
    sol = taskkit.split_solutions(pages, len(key) or 40)
    units = json.loads(old["units"] or "[]")
    if len(units) < len(key):
        units = units + [taskkit.guess_unit(sol.get(i + 1, {}).get("text", "")) for i in range(len(units), len(key))]
    if old["solution_file_id"]:
        delete_file(old["solution_file_id"])
    execute("UPDATE assignments SET solution_file_id = ?, answer_key = ?, units = ?, solutions = ? WHERE id = ?",
            (fid, json.dumps(key), json.dumps(units, ensure_ascii=False), json.dumps(sol, ensure_ascii=False), a_id))
    return len(key), len(sol)


def _parse_key(raw):
    """'3 1 5 2 4' / '31524' / '③①⑤' / 단답 '12, 0.5' 같은 입력을 정답 목록으로."""
    raw = (raw or "").strip()
    if not raw:
        return []
    for c, d in taskkit.CIRCLED.items():
        raw = raw.replace(c, " " + d + " ")
    parts = [p for p in re.split(r"[\s,/]+", raw) if p]
    if len(parts) == 1 and parts[0].isdigit() and len(parts[0]) > 2 and set(parts[0]) <= set("12345"):
        parts = list(parts[0])
    return parts[:80]


@bp.route("/t/tasks", methods=["GET", "POST"])
@staff_required
def t_tasks():
    classes = _classes()
    if request.method == "POST":
        title = request.form.get("title", "").strip()[:100]
        cid = request.form.get("class_id", type=int)
        due = _parse_day(request.form.get("due_on"))
        if not title or not cid:
            flash("반과 과제 이름을 입력하세요.", "error")
            return redirect(url_for("study.t_tasks"))
        key = _parse_key(request.form.get("answer_key"))
        aid = execute("INSERT INTO assignments (class_id, title, body, due_on, answer_key) VALUES (?, ?, ?, ?, ?)",
                      (cid, title, request.form.get("body", "").strip()[:2000], due.isoformat() if due else None, json.dumps(key)))
        f = request.files.get("pdf")
        if f and f.filename:
            try:
                nk, ns = _save_solution_pdf(aid, f)
                flash(f"정답·해설 PDF 에서 정답 {nk}개, 문항별 해설 {ns}개를 찾았어요. 아래에서 확인하고 고쳐 주세요.", "ok")
            except ValueError as e:
                flash(str(e), "error")
        audit("task_created", f"assignment:{aid}")
        a = _task_or_404(aid)
        if a["key"]:
            from views.pwa import notify_class
            notify_class(cid, "새 과제", title, url_for("study.task", aid=aid))
        return redirect(url_for("study.t_task", aid=aid))
    rows = query("""SELECT a.*, c.name AS class_name,
                           (SELECT COUNT(*) FROM students s WHERE s.class_id = a.class_id AND s.active = 1) AS n,
                           (SELECT COUNT(*) FROM task_answers WHERE assignment_id = a.id) AS sub,
                           (SELECT ROUND(AVG(correct * 100.0 / total)) FROM task_answers WHERE assignment_id = a.id) AS avg
                    FROM assignments a JOIN classes c ON c.id = a.class_id ORDER BY a.id DESC""")
    rows = [dict(r, items=len(json.loads(r["answer_key"] or "[]"))) for r in rows]
    return render_template("study/t_tasks.html", rows=rows, classes=classes)


@bp.route("/t/tasks/<int:aid>", methods=["GET", "POST"])
@staff_required
def t_task(aid):
    a = _task_or_404(aid)
    if request.method == "POST":
        f = request.files.get("pdf")
        if f and f.filename:
            try:
                nk, ns = _save_solution_pdf(aid, f)
                flash(f"PDF 를 새로 읽었어요. 정답 {nk}개, 해설 {ns}개.", "ok")
            except ValueError as e:
                flash(str(e), "error")
            return redirect(url_for("study.t_task", aid=aid))
        if query("SELECT 1 FROM task_answers WHERE assignment_id = ?", (aid,), one=True) and request.form.get("confirm") != "1":
            flash("이미 답을 낸 학생이 있어요. 정답을 바꾸면 그 학생들도 다시 채점돼요. 한 번 더 저장을 누르세요.", "error")
            return redirect(url_for("study.t_task", aid=aid, confirm=1))
        n = request.form.get("n", type=int) or 0
        n = max(0, min(80, n))
        key = [(request.form.get(f"k{i + 1}") or "").strip()[:20] for i in range(n)]
        while key and not key[-1]:
            key.pop()
        units = [(request.form.get(f"u{i + 1}") or "") if (request.form.get(f"u{i + 1}") or "") in taskkit.UNITS else ""
                 for i in range(len(key))]
        execute("UPDATE assignments SET answer_key = ?, units = ? WHERE id = ?",
                (json.dumps(key), json.dumps(units, ensure_ascii=False), aid))
        for r in query("SELECT id, answers FROM task_answers WHERE assignment_id = ?", (aid,)):   # 다시 채점
            ans = json.loads(r["answers"]); ans = (ans + [""] * len(key))[:len(key)]
            execute("UPDATE task_answers SET correct = ?, total = ? WHERE id = ?", (sum(taskkit.grade(key, ans)), len(key), r["id"]))
        flash("정답과 단원을 저장했어요.", "ok")
        return redirect(url_for("study.t_task", aid=aid))
    a = _task_or_404(aid)
    a["class_name"] = query("SELECT name FROM classes WHERE id = ?", (a["class_id"],), one=True)["name"]
    rows = query("""SELECT st.id AS sid, st.name, st.student_no, t.correct, t.total, t.answers, t.created_at
                    FROM students st LEFT JOIN task_answers t ON t.student_id = st.id AND t.assignment_id = ?
                    WHERE st.class_id = ? AND st.active = 1 ORDER BY t.id IS NULL, t.correct DESC, st.name""", (aid, a["class_id"]))
    all_ans = [json.loads(r["answers"]) for r in rows if r["answers"]]
    items = []
    for i, k in enumerate(a["key"]):
        picks = [taskkit.norm_answer(x[i]) for x in all_ans if i < len(x) and x[i]]
        right = sum(1 for p in picks if p == taskkit.norm_answer(k))
        dist = {c: picks.count(c) for c in "12345"} if taskkit.is_choice(k) else {}
        items.append({"no": i + 1, "key": k, "unit": a["unit_list"][i] if i < len(a["unit_list"]) else "",
                      "rate": round(right * 100 / len(picks)) if picks else None, "dist": dist, "n": len(picks),
                      "sol": a["sol"].get(i + 1)})
    units = {}
    for it in items:
        if it["rate"] is not None:
            u = units.setdefault(it["unit"] or "단원 미정", []); u.append(it["rate"])
    unit_rates = sorted(((u, round(sum(v) / len(v))) for u, v in units.items()), key=lambda x: x[1])
    return render_template("study/t_task.html", a=a, rows=rows, items=items, unit_rates=unit_rates, units=taskkit.UNITS,
                           n_slots=max(len(a["key"]), 25), confirm=request.args.get("confirm") == "1")


@bp.route("/t/tasks/<int:aid>/students/<int:sid>")
@staff_required
def t_task_student(aid, sid):
    a = _task_or_404(aid)
    st = query("SELECT * FROM students WHERE id = ?", (sid,), one=True)
    mine, an = _task_analysis(a, sid)
    if st is None or mine is None:
        abort(404)
    return render_template("study/task.html", a=a, mine=mine, an=an, choice=[taskkit.is_choice(k) for k in a["key"]], target=st)


@bp.route("/t/tasks/<int:aid>/delete", methods=["POST"])
@teacher_required
def t_task_delete(aid):
    a = query("SELECT solution_file_id FROM assignments WHERE id = ?", (aid,), one=True)
    if a and a["solution_file_id"]:
        delete_file(a["solution_file_id"])
    for r in query("SELECT file_id FROM submissions WHERE assignment_id = ? AND file_id IS NOT NULL", (aid,)):
        delete_file(r["file_id"])
    execute("DELETE FROM assignments WHERE id = ?", (aid,))
    audit("task_deleted", f"assignment:{aid}")
    flash("과제와 학생 답을 지웠습니다.", "ok")
    return redirect(url_for("study.t_tasks"))


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
    mocks, reasons, focus, tasks = [], [], None, None
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
    t = query("""SELECT COUNT(*) AS n, (SELECT COUNT(*) FROM task_answers x JOIN assignments a2 ON a2.id = x.assignment_id
                                       WHERE x.student_id = ? AND a2.class_id = ?) AS sub,
                        (SELECT ROUND(AVG(x.correct * 100.0 / x.total)) FROM task_answers x JOIN assignments a2 ON a2.id = x.assignment_id
                                       WHERE x.student_id = ? AND a2.class_id = ?) AS avg
                 FROM assignments WHERE class_id = ?""", (student_id, s["class_id"], student_id, s["class_id"], s["class_id"]), one=True)
    tasks = {"n": t["n"], "sub": t["sub"], "avg": t["avg"]}
    return {"s": s, "scores": scores, "chart": chart, "mocks": mocks, "reasons": reasons, "focus": focus,
            "tasks": tasks, "today": date.today().isoformat()}


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
