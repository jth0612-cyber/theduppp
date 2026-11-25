"""복테·모의고사 1:1 첨삭.
학생: 분석 화면에서 회차마다 풀이 사진(최대 3장)과 질문을 올린다. 답을 받은 뒤에도 이어서 물을 수 있다.
강사·조교: 대기 중인 요청을 모아 보고, 글과 첨삭 사진으로 답한다. 답하면 '답변 완료'가 된다."""
import json

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

import analysis
from db import execute, query
from security import audit, delete_file, staff_required, student_required

bp = Blueprint("feedback", __name__)
MAX_BODY = 2000


def who_of(row):
    """글쓴이 표시: 강사는 '정태혁 선생님', 조교는 이름 + 조교, 학생은 이름."""
    if row["role"] == "teacher":
        return "정태혁 선생님"
    if row["role"] == "assistant":
        return f"{row['display_name'] or row['username']} 조교"
    return row["student_name"] or row["display_name"] or row["username"]


def messages(tid):
    rows = query("""SELECT m.*, u.role, u.display_name, u.username, s.name AS student_name
                    FROM feedback_msgs m LEFT JOIN users u ON u.id = m.author_id
                    LEFT JOIN students s ON s.id = u.student_id
                    WHERE m.thread_id = ? ORDER BY m.id""", (tid,))
    pics = {}
    for r in query("""SELECT i.msg_id, i.file_id FROM feedback_images i JOIN feedback_msgs m ON m.id = i.msg_id
                      WHERE m.thread_id = ? ORDER BY i.pos""", (tid,)):
        pics.setdefault(r["msg_id"], []).append(r["file_id"])
    return [dict(r, who=who_of(r), staff=r["role"] in ("teacher", "assistant"), photos=pics.get(r["id"], []))
            for r in rows]


def thread_for(mid, uid, mark_seen=False):
    t = query("SELECT * FROM feedback_threads WHERE mock_id = ? AND user_id = ?", (mid, uid), one=True)
    if t is None:
        return None, []
    if mark_seen:
        execute("UPDATE feedback_threads SET unread = 0 WHERE id = ?", (t["id"],))
    return t, messages(t["id"])


def _post(tid, body, photos):
    mid = execute("INSERT INTO feedback_msgs (thread_id, author_id, body) VALUES (?, ?, ?)", (tid, g.user["id"], body))
    for pos, fid in enumerate(photos, start=1):
        execute("INSERT INTO feedback_images (msg_id, file_id, pos) VALUES (?, ?, ?)", (mid, fid, pos))


def _read_form():
    """(본문, 사진 id 목록). 둘 다 비었거나 너무 길면 ValueError."""
    from views.student import _upload_images
    body = request.form.get("body", "").strip()
    if len(body) > MAX_BODY:
        raise ValueError(f"내용은 {MAX_BODY}자까지 적을 수 있어요.")
    has_photo = any(f and f.filename for f in request.files.getlist("image"))
    if not body and not has_photo:
        raise ValueError("내용이나 사진 중 하나는 넣어 주세요.")
    return body, _upload_images(required=False)


@bp.app_context_processor
def _counts():
    user = g.get("user")
    if user is None:
        return {}
    if user["role"] in ("teacher", "assistant"):
        return {"feedback_wait": query("SELECT COUNT(*) AS n FROM feedback_threads WHERE status = 'wait'", one=True)["n"]}
    if user["role"] == "student":
        return {"feedback_new": query("""SELECT COUNT(*) AS n FROM feedback_threads
                                         WHERE user_id = ? AND unread = 1""",
                                      (user["id"],), one=True)["n"]}
    return {}


# ---------- 학생 ----------

@bp.route("/s/feedback")
@student_required
def s_list():
    """내 첨삭 모아 보기: 1:1 첨삭과 시험지 첨삭 (지난 코멘트를 회차마다 열지 않고 찾게)."""
    rows = query("""SELECT 'feedback' AS kind, t.mock_id, t.status, t.updated_at AS at, b.title AS book, m.round_no, t.unread
                    FROM feedback_threads t JOIN mocks m ON m.id = t.mock_id JOIN books b ON b.id = m.book_id WHERE t.user_id = ?
                    UNION ALL
                    SELECT 'paper', p.mock_id, p.status, COALESCE(p.reviewed_at, p.submitted_at), b.title, m.round_no, 0
                    FROM exam_papers p JOIN mocks m ON m.id = p.mock_id JOIN books b ON b.id = m.book_id WHERE p.student_id = ?
                    ORDER BY at DESC""", (g.user["id"], g.user["student_id"]))
    return render_template("student/feedback_list.html", rows=rows)


@bp.route("/s/analysis/<int:mid>/feedback", methods=["POST"])
@student_required
def ask(mid):
    from views.books import _accessible_mocks
    if mid not in {m["id"] for m in _accessible_mocks()}:
        abort(404)
    try:
        body, photos = _read_form()
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("books.analysis_home", mock=mid) + "#feedback")
    t = query("SELECT id FROM feedback_threads WHERE mock_id = ? AND user_id = ?", (mid, g.user["id"]), one=True)
    kind = query("SELECT b.kind FROM mocks m JOIN books b ON b.id = m.book_id WHERE m.id = ?", (mid,), one=True)
    if t is None and kind["kind"] != "모의고사":                     # 1:1 피드백은 모의고사만 (복습 테스트는 시험지 첨삭)
        flash("복습 테스트는 복습 테스트 첨삭(시험지 사진)으로 요청해 주세요.", "error")
        return redirect(url_for("books.analysis_home", mock=mid) + "#paper")
    if t is None:
        tid = execute("INSERT INTO feedback_threads (mock_id, user_id) VALUES (?, ?)", (mid, g.user["id"]))
    else:
        tid = t["id"]
        execute("UPDATE feedback_threads SET status = 'wait', unread = 0, updated_at = datetime('now', 'localtime') WHERE id = ?",
                (tid,))
    _post(tid, body, photos)
    audit("feedback_ask", f"feedback:{tid}")
    flash("피드백 요청을 보냈어요.", "ok")
    return redirect(url_for("books.analysis_home", mock=mid) + "#feedback")


# ---------- 강사·조교 ----------

@bp.route("/t/feedback")
@staff_required
def t_list():
    status = request.args.get("status", "wait")
    if status not in ("wait", "done"):
        status = "wait"
    rows = query("""SELECT t.*, s.name AS student_name, s.student_no, c.name AS class_name,
                           b.title AS book_title, m.round_no, m.title AS mock_title, m.full_score,
                           e.score, (SELECT COUNT(*) FROM feedback_msgs x WHERE x.thread_id = t.id) AS n_msgs
                    FROM feedback_threads t
                    JOIN users u ON u.id = t.user_id LEFT JOIN students s ON s.id = u.student_id
                    LEFT JOIN classes c ON c.id = s.class_id
                    JOIN mocks m ON m.id = t.mock_id JOIN books b ON b.id = m.book_id
                    LEFT JOIN mock_entries e ON e.mock_id = t.mock_id AND e.user_id = t.user_id
                    WHERE t.status = ? ORDER BY t.updated_at {} LIMIT 200""".format("ASC" if status == "wait" else "DESC"),
                 (status,))
    counts = {r["status"]: r["n"] for r in query("SELECT status, COUNT(*) AS n FROM feedback_threads GROUP BY status")}
    return render_template("teacher/feedback_list.html", rows=rows, status=status, counts=counts, fmt=analysis._fmt)


@bp.route("/t/feedback/<int:tid>", methods=["GET", "POST"])
@staff_required
def t_detail(tid):
    t = query("""SELECT t.*, s.name AS student_name, s.student_no, c.name AS class_name,
                        b.title AS book_title, m.round_no, m.title AS mock_title, m.full_score, m.answer_key, m.points
                 FROM feedback_threads t
                 JOIN users u ON u.id = t.user_id LEFT JOIN students s ON s.id = u.student_id
                 LEFT JOIN classes c ON c.id = s.class_id
                 JOIN mocks m ON m.id = t.mock_id JOIN books b ON b.id = m.book_id
                 WHERE t.id = ?""", (tid,), one=True) or abort(404)
    if request.method == "POST":
        if request.form.get("action") == "reopen":
            execute("UPDATE feedback_threads SET status = 'wait' WHERE id = ?", (tid,))
            return redirect(url_for("feedback.t_detail", tid=tid))
        try:
            body, photos = _read_form()
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("feedback.t_detail", tid=tid) + "#reply")
        _post(tid, body, photos)
        execute("""UPDATE feedback_threads SET status = 'done', unread = 1, staff_id = ?, updated_at = datetime('now', 'localtime')
                   WHERE id = ?""", (g.user["id"], tid))
        audit("feedback_reply", f"feedback:{tid}")
        flash("답변을 보냈어요.", "ok")
        nxt = query("SELECT id FROM feedback_threads WHERE status = 'wait' AND id != ? ORDER BY updated_at LIMIT 1", (tid,), one=True)
        return redirect(url_for("feedback.t_detail", tid=nxt["id"]) if nxt else url_for("feedback.t_list"))
    entry = query("SELECT * FROM mock_entries WHERE mock_id = ? AND user_id = ?", (t["mock_id"], t["user_id"]), one=True)
    key, points = json.loads(t["answer_key"]), json.loads(t["points"])
    wrong = []
    if entry and entry["mode"] == "answers" and entry["answers"]:
        wrong = sorted(analysis.wrong_items(entry["answers"], key))
    # 같은 학생·같은 회차의 시험지 첨삭 (둘이 따로 쌓여 한쪽을 놓치지 않게)
    paper = query("""SELECT p.id, p.status FROM exam_papers p JOIN users u ON u.student_id = p.student_id
                     WHERE p.mock_id = ? AND u.id = ?""", (t["mock_id"], t["user_id"]), one=True)
    return render_template("teacher/feedback_detail.html", paper=paper, t=t, msgs=messages(tid), entry=entry, wrong=wrong,
                           points=points, key=key, fmt=analysis._fmt)


def delete_mock_files(mid):
    """회차·교재를 지우기 전에 그 회차 첨삭 사진 파일을 지운다 (글은 회차와 함께 지워진다)."""
    for r in query("""SELECT i.file_id FROM feedback_images i JOIN feedback_msgs m ON m.id = i.msg_id
                      JOIN feedback_threads t ON t.id = m.thread_id WHERE t.mock_id = ?""", (mid,)):
        delete_file(r["file_id"])
