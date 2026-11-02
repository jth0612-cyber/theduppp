"""공부 도구: 공부 결 진단, 오답 노트, 개념 카드, 일정·D-day, 과제 제출함, 성적 리포트.
학생 화면(/s/...)과 선생님 화면(/t/...)을 함께 둔다. 학생은 본인 기록과 본인 반 자료만 본다."""
import calendar
import json
from datetime import date, timedelta

from flask import Blueprint, abort, flash, g, jsonify, redirect, render_template, request, url_for

import analysis
import study_guide
from db import execute, get_setting, query, set_setting
from security import (IMAGE_EXTS, audit, delete_file, login_required, save_upload, student_required,
                      teacher_required)

bp = Blueprint("study", __name__)

WRONG_REASONS = ["개념 부족", "자료 해석", "조건 놓침", "계산 실수", "시간 부족", "찍음"]
EVENT_KINDS = ["일정", "시험", "수업", "휴강", "마감"]
TASK_EXTS = IMAGE_EXTS | {"pdf"}
WEEKDAYS = "월화수목금토일"


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


def upcoming_events(class_id, limit=3):
    return query("""SELECT * FROM events WHERE (class_id IS NULL OR class_id = ?) AND day >= date('now', 'localtime')
                    ORDER BY day, id LIMIT ?""", (class_id, limit))


# =====================================================================
# 1. 공부 결 진단
# =====================================================================

@bp.route("/s/guide", methods=["GET", "POST"])
@student_required
def guide():
    row = query("SELECT * FROM study_types WHERE user_id = ?", (g.user["id"],), one=True)
    if request.method == "POST":
        code, picks = study_guide.score(request.form)
        if code is None:
            flash("모든 문항에 답해 주세요.", "error")
            return render_template("study/guide_quiz.html", questions=study_guide.QUESTIONS,
                                   picks=_partial(request.form)), 400
        execute("""INSERT INTO study_types (user_id, code, answers) VALUES (?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET code = excluded.code, answers = excluded.answers,
                   updated_at = datetime('now', 'localtime')""", (g.user["id"], code, picks))
        return redirect(url_for("study.guide"))
    if row is None or request.args.get("retake"):
        picks = row["answers"] if row else ""
        return render_template("study/guide_quiz.html", questions=study_guide.QUESTIONS, picks=picks)
    return render_template("study/guide.html", t=study_guide.describe(row["code"]), row=row)


def _partial(form):
    return "".join(form.get(f"q{i}", "-") for i in range(len(study_guide.QUESTIONS)))


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


# =====================================================================
# 3. 개념 카드
# =====================================================================

def _decks_for(class_id):
    return query("""SELECT d.*, (SELECT COUNT(*) FROM cards c WHERE c.deck_id = d.id) AS n,
                           (SELECT COUNT(*) FROM card_marks k JOIN cards c ON c.id = k.card_id
                            WHERE c.deck_id = d.id AND k.user_id = ? AND k.status = 'known') AS known,
                           (SELECT COUNT(*) FROM card_marks k JOIN cards c ON c.id = k.card_id
                            WHERE c.deck_id = d.id AND k.user_id = ? AND k.status = 'unsure') AS unsure
                    FROM decks d WHERE d.class_id IS NULL OR d.class_id = ? ORDER BY d.unit, d.title""",
                 (g.user["id"], g.user["id"], class_id))


@bp.route("/s/cards")
@student_required
def cards():
    me = _me()
    return render_template("study/cards.html", decks=_decks_for(me["class_id"]))


@bp.route("/s/cards/<int:did>")
@student_required
def deck(did):
    me = _me()
    d = query("SELECT * FROM decks WHERE id = ? AND (class_id IS NULL OR class_id = ?)", (did, me["class_id"]), one=True)
    if d is None:
        abort(404)
    mode = request.args.get("mode", "all")
    sql = """SELECT c.*, k.status FROM cards c LEFT JOIN card_marks k ON k.card_id = c.id AND k.user_id = ?
             WHERE c.deck_id = ?"""
    if mode == "unsure":
        sql += " AND k.status = 'unsure'"
    elif mode == "new":
        sql += " AND k.status IS NULL"
    rows = query(sql + " ORDER BY c.pos, c.id", (g.user["id"], did))
    return render_template("study/deck.html", d=d, cards=rows, mode=mode)


@bp.route("/s/cards/mark/<int:cid>", methods=["POST"])
@student_required
def card_mark(cid):
    me = _me()
    c = query("""SELECT c.id FROM cards c JOIN decks d ON d.id = c.deck_id
                 WHERE c.id = ? AND (d.class_id IS NULL OR d.class_id = ?)""", (cid, me["class_id"]), one=True)
    status = request.form.get("status")
    if c is None or status not in ("known", "unsure"):
        abort(404)
    execute("""INSERT INTO card_marks (user_id, card_id, status) VALUES (?, ?, ?)
               ON CONFLICT(user_id, card_id) DO UPDATE SET status = excluded.status,
               updated_at = datetime('now', 'localtime')""", (g.user["id"], cid, status))
    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify(ok=True)
    return redirect(request.referrer or url_for("study.cards"))


@bp.route("/t/cards", methods=["GET", "POST"])
@teacher_required
def t_cards():
    if request.method == "POST":
        title = request.form.get("title", "").strip()[:80]
        if not title:
            flash("묶음 이름을 입력하세요.", "error")
        else:
            cid = request.form.get("class_id") or None
            did = execute("INSERT INTO decks (title, unit, class_id) VALUES (?, ?, ?)",
                          (title, request.form.get("unit", "").strip()[:40], int(cid) if cid else None))
            audit("deck_created", f"deck:{did}")
            return redirect(url_for("study.t_deck", did=did))
    decks = query("""SELECT d.*, c.name AS class_name, (SELECT COUNT(*) FROM cards WHERE deck_id = d.id) AS n
                     FROM decks d LEFT JOIN classes c ON c.id = d.class_id ORDER BY d.unit, d.title""")
    return render_template("study/t_cards.html", decks=decks, classes=_classes(),
                           units=[u[0] for u in study_guide.UNITS])


def parse_cards(raw):
    """한 줄에 카드 하나: '앞면 | 뒷면'. 잘못된 줄은 번호와 함께 알려 준다."""
    out, bad = [], []
    for i, line in enumerate((raw or "").splitlines(), start=1):
        if not line.strip():
            continue
        if "|" not in line:
            bad.append(i)
            continue
        front, back = (x.strip() for x in line.split("|", 1))
        if not front or not back:
            bad.append(i)
            continue
        out.append((front[:300], back[:600]))
    return out, bad


@bp.route("/t/cards/<int:did>", methods=["GET", "POST"])
@teacher_required
def t_deck(did):
    d = query("SELECT * FROM decks WHERE id = ?", (did,), one=True)
    if d is None:
        abort(404)
    if request.method == "POST":
        new, bad = parse_cards(request.form.get("cards"))
        if bad:
            flash(f"{', '.join(map(str, bad))}번째 줄에 '앞면 | 뒷면' 형식이 아닌 내용이 있어요.", "error")
        elif not new:
            flash("추가할 카드를 적어 주세요.", "error")
        else:
            start = query("SELECT COALESCE(MAX(pos), 0) AS p FROM cards WHERE deck_id = ?", (did,), one=True)["p"]
            for i, (f, b) in enumerate(new, start=1):
                execute("INSERT INTO cards (deck_id, front, back, pos) VALUES (?, ?, ?, ?)", (did, f, b, start + i))
            flash(f"카드 {len(new)}장을 추가했습니다.", "ok")
            return redirect(url_for("study.t_deck", did=did))
    rows = query("""SELECT c.*, (SELECT COUNT(*) FROM card_marks WHERE card_id = c.id AND status = 'unsure') AS unsure
                    FROM cards c WHERE deck_id = ? ORDER BY pos, id""", (did,))
    return render_template("study/t_deck.html", d=d, cards=rows)


@bp.route("/t/cards/item/<int:cid>/delete", methods=["POST"])
@teacher_required
def t_card_delete(cid):
    c = query("SELECT deck_id FROM cards WHERE id = ?", (cid,), one=True)
    if c is None:
        abort(404)
    execute("DELETE FROM cards WHERE id = ?", (cid,))
    return redirect(url_for("study.t_deck", did=c["deck_id"]))


@bp.route("/t/cards/<int:did>/delete", methods=["POST"])
@teacher_required
def t_deck_delete(did):
    execute("DELETE FROM decks WHERE id = ?", (did,))
    audit("deck_deleted", f"deck:{did}")
    flash("카드 묶음을 지웠습니다.", "ok")
    return redirect(url_for("study.t_cards"))


def _classes():
    return query("SELECT id, name FROM classes WHERE archived = 0 ORDER BY name")


# =====================================================================
# 5. 일정 달력 · 시간표 · D-day
# =====================================================================

def _month_param():
    raw = request.args.get("month", "")
    try:
        y, m = (int(x) for x in raw.split("-"))
        return date(y, m, 1)
    except ValueError:
        t = date.today()
        return date(t.year, t.month, 1)


def _month_grid(first, events):
    cal = calendar.Calendar(firstweekday=0)
    by_day = {}
    for e in events:
        by_day.setdefault(e["day"], []).append(e)
    weeks = []
    for wk in cal.monthdatescalendar(first.year, first.month):
        weeks.append([{"date": d, "in": d.month == first.month, "events": by_day.get(d.isoformat(), [])} for d in wk])
    return weeks


def _shift_month(first, n):
    m = first.month - 1 + n
    return date(first.year + m // 12, m % 12 + 1, 1)


@bp.route("/s/calendar")
@student_required
def s_calendar():
    me = _me()
    first = _month_param()
    last = _shift_month(first, 1) - timedelta(days=1)
    events = query("""SELECT * FROM events WHERE (class_id IS NULL OR class_id = ?) AND day BETWEEN ? AND ?
                      ORDER BY day, id""", (me["class_id"], first.isoformat(), last.isoformat()))
    tasks = query("""SELECT id, title, due_on FROM assignments WHERE class_id = ? AND due_on BETWEEN ? AND ?""",
                  (me["class_id"], first.isoformat(), last.isoformat()))
    merged = [dict(e) for e in events] + [{"day": t["due_on"], "title": f"과제 마감: {t['title']}", "kind": "마감"}
                                          for t in tasks]
    timetable = query("SELECT * FROM timetable WHERE class_id = ? ORDER BY weekday, starts", (me["class_id"],))
    return render_template("study/calendar.html", weeks=_month_grid(first, merged), first=first, today=date.today(),
                           prev=_shift_month(first, -1), next=_shift_month(first, 1), dday=dday_info(),
                           timetable=timetable, weekdays=WEEKDAYS, upcoming=upcoming_events(me["class_id"], 5))


@bp.route("/t/calendar", methods=["GET", "POST"])
@teacher_required
def t_calendar():
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
        elif action == "event":
            d = _parse_day(request.form.get("day"))
            title = request.form.get("title", "").strip()[:80]
            kind = request.form.get("kind") if request.form.get("kind") in EVENT_KINDS else "일정"
            cid = request.form.get("class_id") or None
            if d is None or not title:
                flash("날짜와 내용을 입력하세요.", "error")
            else:
                execute("INSERT INTO events (class_id, day, title, kind) VALUES (?, ?, ?, ?)",
                        (int(cid) if cid else None, d.isoformat(), title, kind))
                flash("일정을 추가했습니다.", "ok")
                from views.pwa import notify_class
                notify_class(int(cid) if cid else None, f"새 일정 · {d.month}/{d.day}", title, url_for("study.s_calendar"))
        elif action == "slot":
            try:
                cid = int(request.form.get("class_id", ""))
                wd = int(request.form.get("weekday", ""))
                starts, ends = request.form.get("starts", ""), request.form.get("ends", "")
                title = request.form.get("title", "").strip()[:40]
                if not (0 <= wd <= 6 and len(starts) == 5 and len(ends) == 5 and title and starts < ends):
                    raise ValueError
            except ValueError:
                flash("반, 요일, 시작·끝 시간, 수업 이름을 확인하세요.", "error")
            else:
                execute("INSERT INTO timetable (class_id, weekday, starts, ends, title) VALUES (?, ?, ?, ?, ?)",
                        (cid, wd, starts, ends, title))
                flash("시간표에 추가했습니다.", "ok")
        return redirect(url_for("study.t_calendar"))
    events = query("""SELECT e.*, c.name AS class_name FROM events e LEFT JOIN classes c ON c.id = e.class_id
                      WHERE e.day >= date('now', 'localtime', '-30 days') ORDER BY e.day, e.id""")
    slots = query("""SELECT t.*, c.name AS class_name FROM timetable t JOIN classes c ON c.id = t.class_id
                     ORDER BY c.name, t.weekday, t.starts""")
    return render_template("study/t_calendar.html", events=events, slots=slots, classes=_classes(),
                           kinds=EVENT_KINDS, weekdays=WEEKDAYS, dday=dday_info(),
                           exam_label=get_setting("exam_label", "수능"))


@bp.route("/t/calendar/event/<int:eid>/delete", methods=["POST"])
@teacher_required
def t_event_delete(eid):
    execute("DELETE FROM events WHERE id = ?", (eid,))
    return redirect(url_for("study.t_calendar"))


@bp.route("/t/calendar/slot/<int:tid>/delete", methods=["POST"])
@teacher_required
def t_slot_delete(tid):
    execute("DELETE FROM timetable WHERE id = ?", (tid,))
    return redirect(url_for("study.t_calendar"))


# =====================================================================
# 7. 과제 제출함
# =====================================================================

@bp.route("/s/tasks")
@student_required
def tasks():
    me = _me()
    rows = query("""SELECT a.*, s.status, s.comment, s.submitted_at, s.file_id, s.note, f.original_name
                    FROM assignments a
                    LEFT JOIN submissions s ON s.assignment_id = a.id AND s.student_id = ?
                    LEFT JOIN files f ON f.id = s.file_id
                    WHERE a.class_id = ? ORDER BY COALESCE(a.due_on, '9999') , a.id DESC""",
                 (me["id"], me["class_id"]))
    return render_template("study/tasks.html", rows=rows, today=date.today().isoformat())


@bp.route("/s/tasks/<int:aid>", methods=["POST"])
@student_required
def task_submit(aid):
    me = _me()
    a = query("SELECT * FROM assignments WHERE id = ? AND class_id = ?", (aid, me["class_id"]), one=True)
    if a is None:
        abort(404)
    old = query("SELECT * FROM submissions WHERE assignment_id = ? AND student_id = ?", (aid, me["id"]), one=True)
    if old and old["status"] == "checked":
        flash("이미 확인이 끝난 과제예요.", "error")
        return redirect(url_for("study.tasks") + f"#a{aid}")
    note = request.form.get("note", "").strip()[:500]
    f = request.files.get("file")
    file_id = old["file_id"] if old else None
    if f and f.filename:
        try:
            new_id = save_upload(f, TASK_EXTS)
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("study.tasks") + f"#a{aid}")
        if file_id:
            delete_file(file_id)
        file_id = new_id
    if not file_id and not note:
        flash("사진이나 PDF를 올리거나 메모를 적어 주세요.", "error")
        return redirect(url_for("study.tasks") + f"#a{aid}")
    execute("""INSERT INTO submissions (assignment_id, student_id, file_id, note, status) VALUES (?, ?, ?, ?, 'submitted')
               ON CONFLICT(assignment_id, student_id) DO UPDATE SET file_id = excluded.file_id, note = excluded.note,
               status = 'submitted', submitted_at = datetime('now', 'localtime')""", (aid, me["id"], file_id, note))
    audit("task_submit", f"assignment:{aid}")
    flash("제출했어요.", "ok")
    return redirect(url_for("study.tasks") + f"#a{aid}")


@bp.route("/t/tasks", methods=["GET", "POST"])
@teacher_required
def t_tasks():
    classes = _classes()
    if request.method == "POST":
        title = request.form.get("title", "").strip()[:100]
        cid = request.form.get("class_id", type=int)
        due = _parse_day(request.form.get("due_on"))
        if not title or not cid:
            flash("반과 과제 이름을 입력하세요.", "error")
        else:
            aid = execute("INSERT INTO assignments (class_id, title, body, due_on) VALUES (?, ?, ?, ?)",
                          (cid, title, request.form.get("body", "").strip()[:2000], due.isoformat() if due else None))
            audit("task_created", f"assignment:{aid}")
            flash("과제를 냈습니다.", "ok")
            from views.pwa import notify_class
            notify_class(cid, "새 과제", title, url_for("study.tasks"))
        return redirect(url_for("study.t_tasks"))
    rows = query("""SELECT a.*, c.name AS class_name,
                           (SELECT COUNT(*) FROM students s WHERE s.class_id = a.class_id AND s.active = 1) AS n,
                           (SELECT COUNT(*) FROM submissions WHERE assignment_id = a.id) AS sub,
                           (SELECT COUNT(*) FROM submissions WHERE assignment_id = a.id AND status = 'checked') AS chk
                    FROM assignments a JOIN classes c ON c.id = a.class_id ORDER BY a.id DESC""")
    return render_template("study/t_tasks.html", rows=rows, classes=classes)


@bp.route("/t/tasks/<int:aid>")
@teacher_required
def t_task(aid):
    a = query("SELECT a.*, c.name AS class_name FROM assignments a JOIN classes c ON c.id = a.class_id WHERE a.id = ?",
              (aid,), one=True)
    if a is None:
        abort(404)
    rows = query("""SELECT st.id AS sid, st.name, st.student_no, s.id, s.status, s.note, s.comment, s.submitted_at,
                           s.file_id, f.original_name, f.mime
                    FROM students st LEFT JOIN submissions s ON s.student_id = st.id AND s.assignment_id = ?
                    LEFT JOIN files f ON f.id = s.file_id
                    WHERE st.class_id = ? AND st.active = 1 ORDER BY s.id IS NULL, st.name""", (aid, a["class_id"]))
    return render_template("study/t_task.html", a=a, rows=rows)


@bp.route("/t/submissions/<int:sid>", methods=["POST"])
@teacher_required
def t_check(sid):
    s = query("SELECT * FROM submissions WHERE id = ?", (sid,), one=True)
    if s is None:
        abort(404)
    status = request.form.get("status") if request.form.get("status") in ("checked", "redo") else "checked"
    execute("UPDATE submissions SET status = ?, comment = ?, checked_at = datetime('now', 'localtime') WHERE id = ?",
            (status, request.form.get("comment", "").strip()[:500], sid))
    flash("확인 결과를 남겼습니다.", "ok")
    return redirect(url_for("study.t_task", aid=s["assignment_id"]) + f"#s{sid}")


@bp.route("/t/tasks/<int:aid>/delete", methods=["POST"])
@teacher_required
def t_task_delete(aid):
    for r in query("SELECT file_id FROM submissions WHERE assignment_id = ? AND file_id IS NOT NULL", (aid,)):
        delete_file(r["file_id"])
    execute("DELETE FROM assignments WHERE id = ?", (aid,))
    audit("task_deleted", f"assignment:{aid}")
    flash("과제와 제출물을 지웠습니다.", "ok")
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
    mocks, reasons, focus, stype, tasks = [], [], None, None, None
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
        row = query("SELECT code FROM study_types WHERE user_id = ?", (uid,), one=True)
        stype = study_guide.describe(row["code"]) if row else None
    t = query("""SELECT COUNT(*) AS n, (SELECT COUNT(*) FROM submissions x JOIN assignments a2 ON a2.id = x.assignment_id
                                       WHERE x.student_id = ? AND a2.class_id = ?) AS sub
                 FROM assignments WHERE class_id = ?""", (student_id, s["class_id"], s["class_id"]), one=True)
    tasks = {"n": t["n"], "sub": t["sub"]}
    return {"s": s, "scores": scores, "chart": chart, "mocks": mocks, "reasons": reasons, "focus": focus,
            "stype": stype, "tasks": tasks, "today": date.today().isoformat()}


@bp.route("/t/students/<int:sid>/report")
@teacher_required
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
