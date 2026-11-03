"""플래너: 오늘·내일 할 일을 한 줄씩 적고 과목 칩을 붙인다. 이번 주도 한눈에 본다.
그날 수업(시간표)과 마감이 다가온 과제는 자동으로 위에 보인다. 학생 본인만 본다."""
from datetime import date, timedelta

from flask import Blueprint, abort, flash, g, jsonify, redirect, render_template, request, url_for

from db import execute, query
from security import student_required
from views.study import WEEKDAYS, class_slots

bp = Blueprint("planner", __name__)

# 과목 칩: (키, 이름, 색 번호 tone-N)
SUBJECTS = [("kor", "국어", 0), ("math", "수학", 2), ("eng", "영어", 3), ("soc", "통사", 5),
            ("sci", "통과", 6), ("his", "한국사", 4), ("etc", "기타", 7)]
SUBJECT_KEYS = {k for k, _, _ in SUBJECTS}
BODY_MAX = 60
DAY_MAX = 30          # 하루 최대 할 일 수
RANGE_DAYS = 60       # 오늘 기준 앞뒤로 적을 수 있는 날


def _day(raw, default):
    try:
        d = date.fromisoformat((raw or "").strip())
    except ValueError:
        return default
    return d if abs((d - date.today()).days) <= RANGE_DAYS else default


def _student():
    s = query("SELECT id, class_id FROM students WHERE id = ? AND active = 1", (g.user["student_id"],), one=True)
    if s is None:
        abort(403)
    return s


def _items(uid, start, end):
    rows = query("""SELECT * FROM planner_items WHERE user_id = ? AND day BETWEEN ? AND ?
                    ORDER BY day, done, position, id""", (uid, start.isoformat(), end.isoformat()))
    by = {}
    for r in rows:
        by.setdefault(r["day"], []).append(r)
    return by


def _auto(student, d):
    """그날 자동으로 보이는 것: 수업, 마감이 그날~이틀 뒤인 아직 안 낸 과제."""
    classes = [s for s in class_slots(student["class_id"]) if s["weekday"] == d.weekday()]
    tasks = query("""SELECT a.id, a.title, a.due_on FROM assignments a
                     LEFT JOIN task_answers s ON s.assignment_id = a.id AND s.student_id = ?
                     WHERE a.class_id = ? AND a.due_on BETWEEN ? AND ? AND s.id IS NULL
                     ORDER BY a.due_on""",
                  (student["id"], student["class_id"], d.isoformat(), (d + timedelta(days=2)).isoformat()))
    return classes, tasks


def _label(d):
    today = date.today()
    if d == today:
        return "오늘"
    if d == today + timedelta(days=1):
        return "내일"
    if d == today - timedelta(days=1):
        return "어제"
    return f"{d.month}월 {d.day}일 {WEEKDAYS[d.weekday()]}요일"


def _back(d, view):
    nxt = request.form.get("next", "")
    if nxt.startswith("/s/planner") and "//" not in nxt:
        return redirect(nxt)
    return redirect(url_for("planner.planner", view=view, d=d.isoformat()))


@bp.route("/s/planner")
@student_required
def planner():
    student = _student()
    today = date.today()
    view = request.args.get("view", "today")
    if view == "tomorrow":
        d = today + timedelta(days=1)
    elif view == "day":
        d = _day(request.args.get("d"), today)
        view = "today" if d == today else "tomorrow" if d == today + timedelta(days=1) else "day"
    else:
        d = today
        view = "week" if view == "week" else "today"
    monday = d - timedelta(days=d.weekday())
    week_days = [monday + timedelta(days=i) for i in range(7)]
    by = _items(g.user["id"], monday, monday + timedelta(days=6))
    strip = [{"d": x, "iso": x.isoformat(), "wd": WEEKDAYS[x.weekday()], "rows": by.get(x.isoformat(), []),
              "on": x == d and view != "week", "today": x == today} for x in week_days]
    classes, tasks = _auto(student, d)
    items = by.get(d.isoformat(), [])
    # 어제까지 못 한 일 (최근 7일)
    left = query("""SELECT COUNT(*) AS n FROM planner_items WHERE user_id = ? AND done = 0 AND day < ? AND day >= ?""",
                 (g.user["id"], today.isoformat(), (today - timedelta(days=7)).isoformat()), one=True)["n"]
    week = []
    if view == "week":
        for x in week_days:
            c, t = _auto(student, x)
            week.append({"d": x, "iso": x.isoformat(), "label": _label(x), "wd": WEEKDAYS[x.weekday()],
                         "items": by.get(x.isoformat(), []), "classes": c, "tasks": t, "today": x == today})
    done_n = sum(1 for i in items if i["done"])
    return render_template("planner/planner.html", view=view, d=d, iso=d.isoformat(), label=_label(d),
                           wd=WEEKDAYS[d.weekday()], strip=strip, items=items, classes=classes, tasks=tasks,
                           done_n=done_n, subjects=SUBJECTS, subject_of={k: (n, t) for k, n, t in SUBJECTS},
                           left=left if d == today else 0, week=week, body_max=BODY_MAX,
                           prev_week=(monday - timedelta(days=7)).isoformat(), next_week=(monday + timedelta(days=7)).isoformat())


@bp.route("/s/planner/add", methods=["POST"])
@student_required
def add():
    _student()
    d = _day(request.form.get("day"), None)
    if d is None:
        abort(400)
    body = " ".join(request.form.get("body", "").split())[:BODY_MAX]
    subject = request.form.get("subject", "")
    subject = subject if subject in SUBJECT_KEYS else ""
    view = request.form.get("view", "day")
    if not body:
        flash("할 일을 한 줄 적어 주세요.", "error")
        return _back(d, view)
    n = query("SELECT COUNT(*) AS n FROM planner_items WHERE user_id = ? AND day = ?", (g.user["id"], d.isoformat()), one=True)["n"]
    if n >= DAY_MAX:
        flash(f"하루에 {DAY_MAX}개까지 적을 수 있어요.", "error")
        return _back(d, view)
    execute("INSERT INTO planner_items (user_id, day, body, subject, position) VALUES (?, ?, ?, ?, ?)",
            (g.user["id"], d.isoformat(), body, subject, n))
    return _back(d, view)


def _mine(iid):
    it = query("SELECT * FROM planner_items WHERE id = ? AND user_id = ?", (iid, g.user["id"]), one=True)
    if it is None:
        abort(404)
    return it


@bp.route("/s/planner/<int:iid>/toggle", methods=["POST"])
@student_required
def toggle(iid):
    it = _mine(iid)
    done = 0 if it["done"] else 1
    execute("UPDATE planner_items SET done = ?, done_at = CASE WHEN ? THEN datetime('now', 'localtime') END WHERE id = ?",
            (done, done, iid))
    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify(ok=True, done=bool(done))
    return _back(date.fromisoformat(it["day"]), request.form.get("view", "day"))


@bp.route("/s/planner/<int:iid>/delete", methods=["POST"])
@student_required
def delete(iid):
    it = _mine(iid)
    execute("DELETE FROM planner_items WHERE id = ?", (iid,))
    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify(ok=True)
    return _back(date.fromisoformat(it["day"]), request.form.get("view", "day"))


@bp.route("/s/planner/<int:iid>/later", methods=["POST"])
@student_required
def later(iid):
    """이 할 일을 다음 날로 넘기기."""
    it = _mine(iid)
    nd = date.fromisoformat(it["day"]) + timedelta(days=1)
    execute("UPDATE planner_items SET day = ?, done = 0 WHERE id = ?", (nd.isoformat(), iid))
    flash(f"'{it['body']}'을(를) {_label(nd)}로 넘겼어요.", "ok")
    return _back(date.fromisoformat(it["day"]), request.form.get("view", "day"))


@bp.route("/s/planner/carry", methods=["POST"])
@student_required
def carry():
    """최근 7일 동안 못 한 일을 모두 오늘로 가져오기."""
    today = date.today()
    execute("""UPDATE planner_items SET day = ? WHERE user_id = ? AND done = 0 AND day < ? AND day >= ?""",
                (today.isoformat(), g.user["id"], today.isoformat(), (today - timedelta(days=7)).isoformat()))
    flash("못 한 일을 오늘로 가져왔어요.", "ok")
    return redirect(url_for("planner.planner"))
