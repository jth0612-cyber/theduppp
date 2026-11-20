"""학습 관리: 숙제 인증 · 문항별 첨삭 · 수업 기록 · 취약 단원 · 학부모 리포트.

- 숙제: 강사·조교가 숙제(반·마감·문항 수)를 낸다 → 학생이 풀이 사진을 올린다 → 조교가 문항마다 O/X, 오답 유형, 메모를 단다.
  학생 화면은 '제출 → 선생님 검사 → 문항별 첨삭' 세 단계로 보인다. 첨삭을 마치면 학생에게 알림이 간다.
- 수업 기록: 반별로 날짜·주제·수업 노트 사진을 올리면 그 반 학생 화면에 날짜순으로 쌓인다.
- 학부모 리포트: 학생마다 비밀 링크(로그인 없음). 이번 주 숙제 제출·정답률, 4주 정답률 변화, 시험 결과, 단원별 성취도,
  틀린 이유, 선생님 코멘트, 출결. 학부모 문자 끝에 이 링크가 붙는다."""
import json
import secrets
from datetime import date, datetime, timedelta

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from db import execute, query
from security import IMAGE_EXTS, audit, delete_file, save_upload, staff_required, student_required

bp = Blueprint("care", __name__)
MAX_HW_PHOTOS = 6
MAX_LESSON_PHOTOS = 10
ERR_TYPES = ("개념 부족", "자료 해석", "조건 독해", "계산 실수", "시간 부족", "기타")


def _photos(field, limit):
    imgs = [f for f in request.files.getlist(field) if f and f.filename]
    if len(imgs) > limit:
        raise ValueError(f"사진은 {limit}장까지 올릴 수 있습니다.")
    saved = []
    try:
        for f in imgs:
            saved.append(save_upload(f, IMAGE_EXTS))
    except ValueError:
        for fid in saved:
            delete_file(fid)
        raise
    return saved


def _me():
    s = query("""SELECT s.*, c.name AS class_name FROM students s JOIN classes c ON c.id = s.class_id
                 WHERE s.id = ? AND s.active = 1""", (g.user["student_id"],), one=True)
    if s is None:
        abort(403)
    return s


def _staff_name(uid):
    u = query("SELECT role, display_name, username FROM users WHERE id = ?", (uid,), one=True) if uid else None
    if not u:
        return ""
    return "정태혁 선생님" if u["role"] == "teacher" else f"{u['display_name'] or u['username']} 조교"


# ================================================================== 숙제
@bp.app_context_processor
def _hw_counts():
    """메뉴 숫자: 학생은 마감 전 안 낸 숙제, 강사·조교는 검사 기다리는 제출."""
    u = g.get("user")
    if u is None:
        return {}
    if u["role"] in ("teacher", "assistant"):
        return {"hw_wait": query("SELECT COUNT(*) AS n FROM hw_submissions WHERE status = 'submitted'", one=True)["n"]}
    if u["role"] == "student" and u["student_id"]:
        s = query("SELECT class_id FROM students WHERE id = ?", (u["student_id"],), one=True)
        if s:
            return {"hw_todo": query("""SELECT COUNT(*) AS n FROM homeworks h WHERE (h.class_id IS NULL OR h.class_id = ?)
                                        AND h.due_at >= datetime('now', 'localtime')
                                        AND h.id NOT IN (SELECT homework_id FROM hw_submissions WHERE student_id = ?)""",
                                     (s["class_id"], u["student_id"]), one=True)["n"]}
    return {}


def hw_for_student(student_id, class_id):
    return [dict(r) for r in query("""
        SELECT h.*, s.id AS sub_id, s.status, s.submitted_at, s.reviewed_at,
               (SELECT COUNT(*) FROM hw_marks k WHERE k.submission_id = s.id AND k.verdict = 'O') AS n_o,
               (SELECT COUNT(*) FROM hw_marks k WHERE k.submission_id = s.id AND k.verdict = 'X') AS n_x
        FROM homeworks h LEFT JOIN hw_submissions s ON s.homework_id = h.id AND s.student_id = ?
        WHERE h.class_id IS NULL OR h.class_id = ? ORDER BY h.due_at DESC, h.id DESC LIMIT 100""", (student_id, class_id))]


@bp.route("/s/homework")
@student_required
def s_homework():
    me = _me()
    return render_template("care/s_homework.html", me=me, rows=hw_for_student(me["id"], me["class_id"]),
                           now=datetime.now().isoformat(sep=" ", timespec="minutes"))


def _hw_visible(hid, me):
    h = query("SELECT * FROM homeworks WHERE id = ? AND (class_id IS NULL OR class_id = ?)", (hid, me["class_id"]), one=True)
    return h or abort(404)


def submission_detail(sub_id):
    files = [r["file_id"] for r in query("SELECT file_id FROM hw_files WHERE submission_id = ? ORDER BY pos", (sub_id,))]
    marks = {r["item_no"]: dict(r) for r in query("SELECT * FROM hw_marks WHERE submission_id = ?", (sub_id,))}
    return files, marks


@bp.route("/s/homework/<int:hid>", methods=["GET", "POST"])
@student_required
def s_homework_detail(hid):
    me = _me()
    h = _hw_visible(hid, me)
    sub = query("SELECT * FROM hw_submissions WHERE homework_id = ? AND student_id = ?", (hid, me["id"]), one=True)
    if request.method == "POST":
        if sub and sub["status"] == "done":
            flash("첨삭이 끝난 숙제는 다시 올릴 수 없습니다.", "error")
            return redirect(url_for("care.s_homework_detail", hid=hid))
        try:
            photos = _photos("image", MAX_HW_PHOTOS)
            if not photos:
                raise ValueError("풀이 사진을 1장 이상 올려 주세요.")
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("care.s_homework_detail", hid=hid))
        note = request.form.get("note", "").strip()[:1000]
        if sub:                                               # 검사 전이면 다시 올릴 수 있다 (사진은 새로 올린 것으로 바뀜)
            old = [r["file_id"] for r in query("SELECT file_id FROM hw_files WHERE submission_id = ?", (sub["id"],))]
            execute("DELETE FROM hw_files WHERE submission_id = ?", (sub["id"],))
            for fid in old:
                delete_file(fid)
            execute("UPDATE hw_submissions SET note = ?, submitted_at = datetime('now', 'localtime') WHERE id = ?", (note, sub["id"]))
            sid = sub["id"]
        else:
            sid = execute("INSERT INTO hw_submissions (homework_id, student_id, note) VALUES (?, ?, ?)", (hid, me["id"], note))
        for pos, fid in enumerate(photos, start=1):
            execute("INSERT INTO hw_files (submission_id, file_id, pos) VALUES (?, ?, ?)", (sid, fid, pos))
        audit("hw_submit", f"homework:{hid}")
        flash("숙제를 제출했습니다.", "ok")
        return redirect(url_for("care.s_homework_detail", hid=hid))
    files, marks = submission_detail(sub["id"]) if sub else ([], {})
    return render_template("care/s_homework_detail.html", me=me, h=h, sub=sub, files=files, marks=marks,
                           reviewer=_staff_name(sub["reviewed_by"]) if sub else "",
                           late=bool(sub and sub["submitted_at"] > h["due_at"]))


@bp.route("/t/homework", methods=["GET", "POST"])
@staff_required
def t_homework():
    if request.method == "POST":
        title = request.form.get("title", "").strip()[:120]
        due = request.form.get("due", "").strip().replace("T", " ")
        try:
            datetime.fromisoformat(due)
        except ValueError:
            due = ""
        cid = request.form.get("class_id", type=int)
        if not title or not due:
            flash("숙제 이름과 마감 일시를 넣어 주세요.", "error")
        else:
            n = max(0, min(request.form.get("n_items", type=int) or 0, 100))
            hid = execute("INSERT INTO homeworks (class_id, title, body, due_at, n_items, created_by) VALUES (?, ?, ?, ?, ?, ?)",
                          (cid or None, title, request.form.get("body", "").strip()[:2000], due[:16], n, g.user["id"]))
            audit("hw_create", f"homework:{hid}")
            flash("숙제를 냈습니다.", "ok")
            return redirect(url_for("care.t_homework_detail", hid=hid))
    rows = query("""SELECT h.*, c.name AS class_name,
                           (SELECT COUNT(*) FROM hw_submissions s WHERE s.homework_id = h.id) AS n_sub,
                           (SELECT COUNT(*) FROM hw_submissions s WHERE s.homework_id = h.id AND s.status = 'submitted') AS n_wait,
                           (SELECT COUNT(*) FROM students s JOIN classes c2 ON c2.id = s.class_id WHERE s.active = 1
                              AND ((h.class_id IS NULL AND c2.is_test = 0) OR s.class_id = h.class_id)) AS n_target
                    FROM homeworks h LEFT JOIN classes c ON c.id = h.class_id ORDER BY h.due_at DESC LIMIT 200""")
    classes = query("SELECT id, name FROM classes WHERE archived = 0 ORDER BY is_test, name")
    return render_template("care/t_homework.html", rows=rows, classes=classes,
                           default_due=(date.today() + timedelta(days=2)).isoformat() + "T22:00")


@bp.route("/t/homework/<int:hid>")
@staff_required
def t_homework_detail(hid):
    h = query("SELECT h.*, c.name AS class_name FROM homeworks h LEFT JOIN classes c ON c.id = h.class_id WHERE h.id = ?", (hid,), one=True) or abort(404)
    subs = query("""SELECT s.*, st.name, st.student_no, c.name AS cls,
                           (SELECT COUNT(*) FROM hw_files f WHERE f.submission_id = s.id) AS n_files,
                           (SELECT COUNT(*) FROM hw_marks k WHERE k.submission_id = s.id AND k.verdict = 'X') AS n_x
                    FROM hw_submissions s JOIN students st ON st.id = s.student_id JOIN classes c ON c.id = st.class_id
                    WHERE s.homework_id = ? ORDER BY s.status = 'done', s.submitted_at""", (hid,))
    missing = query("""SELECT st.name, c.name AS cls FROM students st JOIN classes c ON c.id = st.class_id
                       WHERE st.active = 1 AND (? IS NULL AND c.is_test = 0 OR st.class_id = ?)
                       AND st.id NOT IN (SELECT student_id FROM hw_submissions WHERE homework_id = ?)
                       ORDER BY c.name, st.name""", (h["class_id"], h["class_id"], hid))
    return render_template("care/t_homework_detail.html", h=h, subs=subs, missing=missing)


@bp.route("/t/homework/<int:hid>/delete", methods=["POST"])
@staff_required
def t_homework_delete(hid):
    for r in query("""SELECT f.file_id FROM hw_files f JOIN hw_submissions s ON s.id = f.submission_id WHERE s.homework_id = ?""", (hid,)):
        delete_file(r["file_id"])
    execute("DELETE FROM homeworks WHERE id = ?", (hid,))
    audit("hw_delete", f"homework:{hid}")
    flash("숙제를 지웠습니다.", "ok")
    return redirect(url_for("care.t_homework"))


@bp.route("/t/homework/review/<int:sid>", methods=["GET", "POST"])
@staff_required
def t_review(sid):
    sub = query("""SELECT s.*, st.name, st.student_no, c.name AS cls, h.title, h.n_items, h.id AS hid
                   FROM hw_submissions s JOIN students st ON st.id = s.student_id JOIN classes c ON c.id = st.class_id
                   JOIN homeworks h ON h.id = s.homework_id WHERE s.id = ?""", (sid,), one=True) or abort(404)
    n = sub["n_items"] or request.form.get("n", type=int) or 0
    if request.method == "POST":
        n = max(0, min(request.form.get("n", type=int) or sub["n_items"] or 0, 100))
        execute("DELETE FROM hw_marks WHERE submission_id = ?", (sid,))
        for i in range(1, n + 1):
            v = request.form.get(f"v{i}", "")
            v = v if v in ("O", "X") else ""
            reason = request.form.get(f"r{i}", "")
            reason = reason if (reason in ERR_TYPES and v == "X") else ""
            memo = request.form.get(f"m{i}", "").strip()[:500]
            if v or memo:
                execute("INSERT INTO hw_marks (submission_id, item_no, verdict, reason, memo) VALUES (?, ?, ?, ?, ?)",
                        (sid, i, v, reason, memo))
        execute("""UPDATE hw_submissions SET status = 'done', comment = ?, reviewed_by = ?,
                   reviewed_at = datetime('now', 'localtime') WHERE id = ?""",
                (request.form.get("comment", "").strip()[:1500], g.user["id"], sid))
        audit("hw_review", f"submission:{sid}")
        from views.pwa import notify_student
        notify_student(sub["student_id"], "숙제 첨삭 완료", sub["title"], url_for("care.s_homework_detail", hid=sub["hid"]))
        flash(f"{sub['name']} 학생 첨삭을 저장했습니다.", "ok")
        nxt = query("SELECT id FROM hw_submissions WHERE homework_id = ? AND status = 'submitted' AND id != ? ORDER BY submitted_at LIMIT 1",
                    (sub["hid"], sid), one=True)
        return redirect(url_for("care.t_review", sid=nxt["id"]) if nxt else url_for("care.t_homework_detail", hid=sub["hid"]))
    files, marks = submission_detail(sid)
    if not n and marks:
        n = max(marks)
    return render_template("care/t_review.html", sub=sub, files=files, marks=marks, n=n or 10, err_types=ERR_TYPES,
                           reviewer=_staff_name(sub["reviewed_by"]))


def hw_review_counts(month):
    """{조교 id: 그 달 숙제 첨삭 건수} — 월급 산정 표에 쓴다."""
    return {r["u"]: r["n"] for r in query("""SELECT reviewed_by AS u, COUNT(*) AS n FROM hw_submissions
                                             WHERE status = 'done' AND strftime('%Y-%m', reviewed_at) = ? GROUP BY reviewed_by""", (month,))}


# ================================================================== 수업 기록
@bp.route("/s/lessons")
@student_required
def s_lessons():
    me = _me()
    rows = [dict(r, files=[x["file_id"] for x in query("SELECT file_id FROM lesson_files WHERE lesson_id = ? ORDER BY pos", (r["id"],))])
            for r in query("SELECT * FROM lessons WHERE class_id = ? ORDER BY day DESC, id DESC LIMIT 60", (me["class_id"],))]
    week_ago = (date.today() - timedelta(days=3)).isoformat()
    return render_template("care/s_lessons.html", me=me, rows=rows, new_since=week_ago)


@bp.route("/t/lessons", methods=["GET", "POST"])
@staff_required
def t_lessons():
    if request.method == "POST":
        cid = request.form.get("class_id", type=int)
        title = request.form.get("title", "").strip()[:120]
        day = request.form.get("day", "") or date.today().isoformat()
        try:
            date.fromisoformat(day)
        except ValueError:
            day = date.today().isoformat()
        if not cid or not title or not query("SELECT 1 FROM classes WHERE id = ?", (cid,), one=True):
            flash("반과 주제를 넣어 주세요.", "error")
            return redirect(url_for("care.t_lessons"))
        try:
            photos = _photos("image", MAX_LESSON_PHOTOS)
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("care.t_lessons"))
        lid = execute("INSERT INTO lessons (class_id, day, title, body, created_by) VALUES (?, ?, ?, ?, ?)",
                      (cid, day, title, request.form.get("body", "").strip()[:2000], g.user["id"]))
        for pos, fid in enumerate(photos, start=1):
            execute("INSERT INTO lesson_files (lesson_id, file_id, pos) VALUES (?, ?, ?)", (lid, fid, pos))
        audit("lesson_create", f"lesson:{lid}")
        from views.pwa import notify_users
        uids = [r["id"] for r in query("SELECT u.id FROM users u JOIN students s ON s.id = u.student_id WHERE s.class_id = ? AND s.active = 1", (cid,))]
        if uids:
            notify_users(uids, "수업 기록", f"{title} · 노트 {len(photos)}장", url_for("care.s_lessons"))
        flash("수업 기록을 올렸습니다.", "ok")
        return redirect(url_for("care.t_lessons"))
    rows = query("""SELECT l.*, c.name AS cls, (SELECT COUNT(*) FROM lesson_files f WHERE f.lesson_id = l.id) AS n_files
                    FROM lessons l JOIN classes c ON c.id = l.class_id ORDER BY l.day DESC, l.id DESC LIMIT 200""")
    classes = query("SELECT id, name FROM classes WHERE archived = 0 ORDER BY is_test, name")
    return render_template("care/t_lessons.html", rows=rows, classes=classes, today=date.today().isoformat())


@bp.route("/t/lessons/<int:lid>/delete", methods=["POST"])
@staff_required
def t_lesson_delete(lid):
    for r in query("SELECT file_id FROM lesson_files WHERE lesson_id = ?", (lid,)):
        delete_file(r["file_id"])
    execute("DELETE FROM lessons WHERE id = ?", (lid,))
    flash("수업 기록을 지웠습니다.", "ok")
    return redirect(url_for("care.t_lessons"))


# ================================================================== 취약 단원
def unit_scores(student_id, limit=6):
    """최근 복테·모의(문항정보에 단원이 있는 시험)에서 단원별 득점률. [{unit, got, total, pct}] 낮은 순."""
    import exams
    tot, got = {}, {}
    rows = query("""SELECT r.mock_id FROM exam_results r JOIN mocks m ON m.id = r.mock_id JOIN books b ON b.id = m.book_id
                    WHERE r.student_id = ? AND m.n_items > 0 AND b.is_practice = 0
                    ORDER BY m.exam_date DESC, r.updated_at DESC LIMIT ?""", (student_id, limit))
    for r in rows:
        rep = exams.student_report(r["mock_id"], student_id)
        if not rep:
            continue
        m = rep["mock"]
        for i, p in enumerate(m["pts"]):
            u = (m["info"].get(i + 1, {}) or {}).get("unit")
            if not u:
                continue
            tot[u] = tot.get(u, 0) + p
            got[u] = got.get(u, 0) + (0 if (i + 1) in rep["wrong"] else p)
    out = [{"unit": u, "got": got[u], "total": tot[u], "pct": round(100 * got[u] / tot[u]) if tot[u] else 0} for u in tot]
    return sorted(out, key=lambda x: (x["pct"], -x["total"]))


def topic_for_unit(unit):
    """단원 이름과 통과 Quiz TOPIC 제목이 겹치면 그 TOPIC."""
    import quiz_topics
    u = (unit or "").replace(" ", "")
    for t in quiz_topics.TOPICS:
        tt = t["title"].replace(" ", "")
        if tt and (tt in u or u in tt):
            return t
    return None


def weak_card(student_id):
    us = unit_scores(student_id)
    weak = next((u for u in us if u["total"] >= 4 and u["pct"] < 80), None)
    if not weak:
        return us, None
    import exams
    wrongs = []
    for r in query("""SELECT r.mock_id FROM exam_results r JOIN mocks m ON m.id = r.mock_id WHERE r.student_id = ? AND m.n_items > 0""", (student_id,)):
        rep = exams.student_report(r["mock_id"], student_id)
        if rep:
            wrongs += [(exams.exam_title(rep["mock"]), a["no"]) for a in rep["wrongs"] if a["unit"] == weak["unit"]]
    return us, {"unit": weak, "wrongs": wrongs, "topic": topic_for_unit(weak["unit"])}


# ================================================================== 학부모 리포트
def parent_token(student_id, renew=False):
    s = query("SELECT parent_token FROM students WHERE id = ?", (student_id,), one=True)
    if s and s["parent_token"] and not renew:
        return s["parent_token"]
    tok = secrets.token_urlsafe(18)
    execute("UPDATE students SET parent_token = ? WHERE id = ?", (tok, student_id))
    return tok


def _week_hw(student_id, class_id, start, end):
    hws = query("""SELECT h.id FROM homeworks h WHERE (h.class_id IS NULL OR h.class_id = ?) AND h.due_at >= ? AND h.due_at < ?""",
                (class_id, start, end))
    ids = [h["id"] for h in hws]
    if not ids:
        return {"assigned": 0, "submitted": 0, "o": 0, "x": 0, "rate": None}
    marks = query(f"""SELECT k.verdict, COUNT(*) AS n FROM hw_marks k JOIN hw_submissions s ON s.id = k.submission_id
                      WHERE s.student_id = ? AND s.homework_id IN ({','.join('?' * len(ids))}) GROUP BY k.verdict""", [student_id] + ids)
    c = {r["verdict"]: r["n"] for r in marks}
    sub = query(f"SELECT COUNT(*) AS n FROM hw_submissions WHERE student_id = ? AND homework_id IN ({','.join('?' * len(ids))})",
                [student_id] + ids, one=True)["n"]
    o, x = c.get("O", 0), c.get("X", 0)
    return {"assigned": len(ids), "submitted": sub, "o": o, "x": x, "rate": round(100 * o / (o + x)) if o + x else None}


def parent_report(student_id):
    import exams
    import sysdata
    s = query("SELECT s.*, c.name AS cls FROM students s JOIN classes c ON c.id = s.class_id WHERE s.id = ?", (student_id,), one=True)
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    weeks = []
    for k in range(3, -1, -1):                                 # 3주 전 ~ 이번 주
        st = monday - timedelta(days=7 * k)
        w = _week_hw(student_id, s["class_id"], st.isoformat(), (st + timedelta(days=7)).isoformat())
        w["label"] = "이번 주" if k == 0 else ("지난주" if k == 1 else f"{k}주 전")
        weeks.append(w)
    this, last = weeks[-1], weeks[-2]
    delta = (this["rate"] - last["rate"]) if this["rate"] is not None and last["rate"] is not None else None
    # 틀린 이유: 이번 주 숙제 오답(유형·메모) + 최근 시험 오답 분석
    reasons = [dict(r) for r in query("""
        SELECT h.title, k.item_no, k.reason, k.memo FROM hw_marks k JOIN hw_submissions sb ON sb.id = k.submission_id
        JOIN homeworks h ON h.id = sb.homework_id
        WHERE sb.student_id = ? AND k.verdict = 'X' AND sb.reviewed_at >= ? ORDER BY sb.reviewed_at DESC LIMIT 6""",
        (student_id, (today - timedelta(days=14)).isoformat()))]
    exams_out = []
    for r in query("""SELECT r.mock_id FROM exam_results r JOIN mocks m ON m.id = r.mock_id JOIN books b ON b.id = m.book_id
                      WHERE r.student_id = ? AND m.n_items > 0 AND b.is_practice = 0 ORDER BY m.exam_date DESC LIMIT 4""", (student_id,)):
        rep = exams.student_report(r["mock_id"], student_id)
        if rep:
            exams_out.append({"title": exams.exam_title(rep["mock"]), "score": rep["r"]["score"], "full": rep["mock"]["full_score"],
                              "avg": rep["st"]["avg"], "date": rep["mock"]["exam_date"],
                              "wrongs": [a for a in rep["wrongs"] if a["type"]][:3]})
    comment = query("""SELECT x.text, x.at FROM (
                         SELECT comment AS text, reviewed_at AS at FROM hw_submissions WHERE student_id = ? AND comment != ''
                         UNION ALL SELECT ta_note, ta_at FROM exam_results WHERE student_id = ? AND ta_note != '') x
                       ORDER BY x.at DESC LIMIT 1""", (student_id, student_id), one=True)
    units, weak = weak_card(student_id)
    att = sysdata.attendance(sysdata.code_of_student(student_id)) if hasattr(sysdata, "attendance") else None
    lines = []                                                 # 이번 주 요약: 숫자로만
    if this["assigned"]:
        lines.append(f"숙제 {this['assigned']}개 중 {this['submitted']}개를 제출했습니다.")
    if this["rate"] is not None:
        lines.append(f"첨삭한 문항 정답률은 {this['rate']}%" + (f"로 지난주보다 {abs(delta)}%p {'올랐' if delta > 0 else '내려갔'}습니다." if delta else "입니다."))
    if weak:
        lines.append(f"최근 시험에서 득점률이 가장 낮은 단원은 {weak['unit']['unit']}({weak['unit']['pct']}%)입니다.")
    return {"s": s, "weeks": weeks, "this": this, "delta": delta, "reasons": reasons, "exams": exams_out,
            "comment": comment, "units": units[:6], "weak": weak, "att": att, "lines": lines,
            "period": f"{monday.month}.{monday.day}~{(monday + timedelta(days=6)).month}.{(monday + timedelta(days=6)).day}"}


def rate_chart(weeks):
    pts = [(i, w["rate"]) for i, w in enumerate(weeks) if w["rate"] is not None]
    W, H, L, R, T, B = 320, 120, 28, 28, 22, 22
    x = lambda i: L + (W - L - R) * (i / (len(weeks) - 1))
    y = lambda v: T + (H - T - B) * (1 - v / 100)
    return {"w": W, "h": H, "pts": [{"x": round(x(i), 1), "y": round(y(v), 1), "v": v} for i, v in pts],
            "poly": " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in pts),
            "labels": [{"x": round(x(i), 1), "t": w["label"]} for i, w in enumerate(weeks)], "base": H - B}


@bp.route("/p/<token>")
def parent_page(token):
    """학부모 리포트 (로그인 없음, 비밀 링크). 검색 엔진에는 나오지 않는다(noindex)."""
    if len(token) < 16:
        abort(404)
    s = query("SELECT id FROM students WHERE parent_token = ? AND active = 1", (token,), one=True) or abort(404)
    rep = parent_report(s["id"])
    return render_template("care/parent.html", r=rep, chart=rate_chart(rep["weeks"]))


@bp.route("/t/students/<int:sid>/parent-link", methods=["POST"])
@staff_required
def t_parent_link(sid):
    if not query("SELECT 1 FROM students WHERE id = ?", (sid,), one=True):
        abort(404)
    parent_token(sid, renew=request.form.get("renew") == "1")
    audit("parent_link", f"student:{sid}")
    flash("학부모 리포트 링크를 새로 만들었습니다. 이전 링크는 더 이상 열리지 않습니다." if request.form.get("renew") == "1" else "학부모 리포트 링크를 만들었습니다.", "ok")
    return redirect(url_for("teacher.student_detail", sid=sid) + "#parent")
