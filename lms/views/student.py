"""학생 화면: 홈, 공지, 자료, 강의 영상, 내 성적, 질답 게시판.
성적·자료·공지·영상은 본인/본인 반으로 제한한다. 질답 게시판은 학습질문만 전체 공개(작성자는 닉네임)하고,
행정문의는 본인과 선생님만 본다."""
import os

from flask import (Blueprint, abort, current_app, flash, g, redirect, render_template, request,
                   send_file, session, url_for)

from content import MAX_FOLLOWUPS, NOTICE_TAGS, QUESTION_TYPES
from db import execute, query
from engagement import record_visit, streak_info
from security import IMAGE_EXTS, audit, delete_file, login_required, save_upload, student_required

bp = Blueprint("student", __name__, url_prefix="/s")


@bp.before_request
def _track_visit():
    user = g.get("user")
    if user is not None and user["role"] == "student" and not user["must_change_pw"]:
        record_visit(user["id"])


def _me():
    s = query("""SELECT s.*, c.name AS class_name FROM students s JOIN classes c ON c.id = s.class_id
                 WHERE s.id = ? AND s.active = 1""", (g.user["student_id"],), one=True)
    if s is None:
        abort(403)
    return s


def _visible_videos(class_id):
    return query("""SELECT * FROM videos WHERE class_id = ?
                    AND (expires_on IS NULL OR expires_on >= date('now', 'localtime'))
                    ORDER BY created_at DESC""", (class_id,))


@bp.route("/")
@student_required
def home():
    me = _me()
    notices = query("SELECT * FROM notices WHERE class_id = ? ORDER BY created_at DESC LIMIT 5", (me["class_id"],))
    materials = query("""SELECT m.*, f.original_name, f.size FROM materials m JOIN files f ON f.id = m.file_id
                         WHERE m.class_id = ? ORDER BY m.created_at DESC LIMIT 5""", (me["class_id"],))
    questions = query("SELECT * FROM questions WHERE student_id = ? ORDER BY created_at DESC LIMIT 5", (me["id"],))
    news = query("SELECT * FROM news ORDER BY created_at DESC LIMIT 4")
    from views.study import dday_info, upcoming_events, wrong_list
    open_wrong = sum(len(gr["rows"]) for gr in wrong_list(g.user["id"], only_open=True))
    focus_today = query("""SELECT COALESCE(SUM(minutes), 0) AS m FROM focus_logs
                           WHERE user_id = ? AND date(ended_at) = date('now', 'localtime')""",
                        (g.user["id"],), one=True)["m"]
    tasks_due = query("""SELECT a.id, a.title, a.due_on FROM assignments a
                         LEFT JOIN submissions s ON s.assignment_id = a.id AND s.student_id = ?
                         WHERE a.class_id = ? AND s.id IS NULL ORDER BY COALESCE(a.due_on, '9999') LIMIT 3""",
                      (me["id"], me["class_id"]))
    return render_template("student/home.html", me=me, notices=notices, materials=materials, questions=questions,
                           news=news, streak=streak_info(g.user["id"]),
                           dday=dday_info(), events=upcoming_events(me["class_id"]), open_wrong=open_wrong,
                           tasks_due=tasks_due, focus_today=focus_today)


@bp.route("/notices")
@student_required
def notices():
    me = _me()
    tag = request.args.get("tag", "")
    if tag not in NOTICE_TAGS:
        tag = ""
    q = request.args.get("q", "").strip()[:50]
    sql = """SELECT n.*, (SELECT COUNT(*) FROM notice_likes l WHERE l.notice_id = n.id) AS likes
             FROM notices n WHERE n.class_id = ?"""
    args = [me["class_id"]]
    if tag:
        sql += " AND n.tag = ?"
        args.append(tag)
    if q:
        like = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        sql += " AND (n.title LIKE ? ESCAPE '\\' OR n.body LIKE ? ESCAPE '\\')"
        args += [like, like]
    sql += " ORDER BY n.textbook, n.created_at DESC" if tag == "정오" else " ORDER BY n.pinned DESC, n.created_at DESC"
    rows = query(sql, tuple(args))
    return render_template("student/notices.html", me=me, notices=rows, tag=tag, tags=NOTICE_TAGS, q=q)


@bp.route("/notices/<int:nid>")
@student_required
def notice_detail(nid):
    me = _me()
    n = query("SELECT * FROM notices WHERE id = ? AND class_id = ?", (nid, me["class_id"]), one=True)
    if n is None:
        abort(404)
    seen = session.get("seen_notices", [])
    if nid not in seen:  # 같은 로그인에서는 한 번만 조회수에 센다
        execute("UPDATE notices SET views = views + 1 WHERE id = ?", (nid,))
        session["seen_notices"] = (seen + [nid])[-100:]
        n = query("SELECT * FROM notices WHERE id = ?", (nid,), one=True)
    likes = query("SELECT COUNT(*) AS c FROM notice_likes WHERE notice_id = ?", (nid,), one=True)["c"]
    liked = query("SELECT 1 FROM notice_likes WHERE notice_id = ? AND user_id = ?", (nid, g.user["id"]), one=True)
    return render_template("student/notice_detail.html", n=n, likes=likes, liked=bool(liked))


@bp.route("/notices/<int:nid>/like", methods=["POST"])
@student_required
def notice_like(nid):
    me = _me()
    if query("SELECT 1 FROM notices WHERE id = ? AND class_id = ?", (nid, me["class_id"]), one=True) is None:
        abort(404)
    if query("SELECT 1 FROM notice_likes WHERE notice_id = ? AND user_id = ?", (nid, g.user["id"]), one=True):
        execute("DELETE FROM notice_likes WHERE notice_id = ? AND user_id = ?", (nid, g.user["id"]))
    else:
        execute("INSERT INTO notice_likes (notice_id, user_id) VALUES (?, ?)", (nid, g.user["id"]))
    return redirect(url_for("student.notice_detail", nid=nid))


@bp.route("/materials")
@student_required
def materials():
    me = _me()
    rows = query("""SELECT m.*, f.original_name, f.size FROM materials m JOIN files f ON f.id = m.file_id
                    WHERE m.class_id = ? ORDER BY m.created_at DESC""", (me["class_id"],))
    return render_template("student/materials.html", me=me, materials=rows)


@bp.route("/videos")
@student_required
def videos():
    me = _me()
    return render_template("student/videos.html", me=me, videos=_visible_videos(me["class_id"]))


@bp.route("/scores")
@student_required
def scores():
    me = _me()
    # 본인 점수와 반 평균만 보여준다 (다른 학생 점수/석차 비공개)
    rows = query("""SELECT e.name, e.subject, e.exam_date, e.max_score, sc.score,
                      (SELECT ROUND(AVG(score), 1) FROM scores WHERE exam_id = e.id) AS class_avg
                    FROM scores sc JOIN exams e ON e.id = sc.exam_id
                    WHERE sc.student_id = ? ORDER BY e.exam_date DESC, e.id DESC""", (me["id"],))
    return render_template("student/scores.html", me=me, scores=rows)


# ---------- 질답 게시판 ----------

QUESTIONS_PER_PAGE = 30
# 학습질문은 공개, 행정문의는 작성자 본인만 (선생님은 강사 화면에서 모두 봄)
_VISIBLE = "(q.qtype = '학습질문' OR q.student_id = ?)"
_PUBLIC_QUESTION_SELECT = """
    SELECT q.id, q.title, q.body, q.image_id, q.qtype, q.status, q.created_at,
           COALESCE(u.nickname, '익명') AS nickname,
           (SELECT COUNT(*) FROM answers WHERE question_id = q.id) AS answer_count,
           (SELECT COUNT(*) FROM followups WHERE question_id = q.id) AS followup_count,
           (q.student_id = ?) AS is_mine
    FROM questions q LEFT JOIN users u ON u.student_id = q.student_id"""


def _upload_image(required):
    img = request.files.get("image")
    if not img or not img.filename:
        if required:
            raise ValueError("학습질문은 문제(와 해설) 사진을 꼭 첨부해 주세요.")
        return None
    return save_upload(img, IMAGE_EXTS)


@bp.route("/questions", methods=["GET", "POST"])
@student_required
def questions():
    me = _me()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        qtype = request.form.get("qtype", "")
        if qtype not in QUESTION_TYPES:
            flash("질문 유형을 선택하세요.", "error")
        elif not title or not body:
            flash("제목과 내용을 입력하세요.", "error")
        elif len(title) > 120 or len(body) > 5000:
            flash("제목은 120자, 내용은 5000자 이내로 입력하세요.", "error")
        else:
            try:
                image_id = _upload_image(required=qtype == "학습질문")
            except ValueError as e:
                flash(str(e), "error")
                return redirect(url_for("student.questions", ask=1) + "#ask")
            qid = execute("INSERT INTO questions (student_id, title, body, image_id, qtype) VALUES (?, ?, ?, ?, ?)",
                          (me["id"], title, body, image_id, qtype))
            audit("question_create", f"question:{qid}")
            flash("질문을 등록했습니다.", "ok")
            return redirect(url_for("student.question_detail", qid=qid))
    view = "mine" if request.args.get("view") == "mine" else "all"
    qtype = request.args.get("qtype", "")
    q = request.args.get("q", "").strip()[:50]
    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1
    where, args = [_VISIBLE], [me["id"]]
    if view == "mine":
        where.append("q.student_id = ?")
        args.append(me["id"])
    if qtype in QUESTION_TYPES:
        where.append("q.qtype = ?")
        args.append(qtype)
    if q:
        where.append("(q.title LIKE ? OR q.body LIKE ?)")
        args += [f"%{q}%", f"%{q}%"]
    where_sql = " AND ".join(where)
    total = query(f"SELECT COUNT(*) AS n FROM questions q WHERE {where_sql}", args, one=True)["n"]
    rows = query(f"""{_PUBLIC_QUESTION_SELECT} WHERE {where_sql}
                     ORDER BY q.created_at DESC LIMIT ? OFFSET ?""",
                 [me["id"]] + args + [QUESTIONS_PER_PAGE, (page - 1) * QUESTIONS_PER_PAGE])
    faqs = query("""SELECT id, title FROM questions WHERE faq = 1 AND qtype = '학습질문'
                    ORDER BY created_at DESC LIMIT 20""") if page == 1 and not q else []
    return render_template("student/questions.html", me=me, questions=rows, view=view, q=q, page=page, faqs=faqs,
                           qtype=qtype, qtypes=QUESTION_TYPES,
                           pages=max(1, -(-total // QUESTIONS_PER_PAGE)), total=total)


def _get_visible_question(qid, me):
    q = query(f"{_PUBLIC_QUESTION_SELECT} WHERE q.id = ? AND {_VISIBLE}", (me["id"], qid, me["id"]), one=True)
    if q is None:
        abort(404)
    return q


def question_thread(qid):
    """선생님 답변과 학생 추가 질문을 시간순으로 합친 대화."""
    items = [dict(r, kind="answer") for r in
             query("""SELECT a.body, a.created_at, NULL AS image_id, u.role AS author_role,
                             u.display_name AS author_name
                      FROM answers a LEFT JOIN users u ON u.id = a.author_id
                      WHERE a.question_id = ?""", (qid,))]
    items += [dict(r, kind="followup") for r in
              query("SELECT body, created_at, image_id FROM followups WHERE question_id = ?", (qid,))]
    return sorted(items, key=lambda r: r["created_at"])


@bp.route("/questions/<int:qid>")
@student_required
def question_detail(qid):
    me = _me()
    q = _get_visible_question(qid, me)
    can_follow_up = q["is_mine"] and q["answer_count"] > 0 and q["followup_count"] < MAX_FOLLOWUPS
    return render_template("student/question_detail.html", me=me, q=q, thread=question_thread(qid),
                           can_follow_up=can_follow_up, max_followups=MAX_FOLLOWUPS)


@bp.route("/questions/<int:qid>/followup", methods=["POST"])
@student_required
def question_followup(qid):
    me = _me()
    q = _get_visible_question(qid, me)
    if not q["is_mine"]:
        abort(404)
    if q["answer_count"] == 0:
        flash("선생님 답변이 달린 뒤에 추가 질문을 할 수 있어요.", "error")
    elif q["followup_count"] >= MAX_FOLLOWUPS:
        flash(f"추가 질문은 {MAX_FOLLOWUPS}번까지 가능합니다. 새 질문으로 올려 주세요.", "error")
    else:
        body = request.form.get("body", "").strip()
        if not body or len(body) > 3000:
            flash("추가 질문 내용을 3000자 이내로 입력하세요.", "error")
        else:
            try:
                image_id = _upload_image(required=False)
            except ValueError as e:
                flash(str(e), "error")
                return redirect(url_for("student.question_detail", qid=qid))
            execute("INSERT INTO followups (question_id, body, image_id) VALUES (?, ?, ?)", (qid, body, image_id))
            execute("UPDATE questions SET status = 'open' WHERE id = ?", (qid,))
            audit("question_followup", f"question:{qid}")
            flash("추가 질문을 보냈습니다.", "ok")
    return redirect(url_for("student.question_detail", qid=qid) + "#thread")


@bp.route("/questions/<int:qid>/delete", methods=["POST"])
@student_required
def question_delete(qid):
    me = _me()
    q = query("SELECT * FROM questions WHERE id = ? AND student_id = ? AND status = 'open'",
              (qid, me["id"]), one=True)
    if q is None or query("SELECT 1 FROM answers WHERE question_id = ?", (qid,), one=True):
        abort(404)
    execute("DELETE FROM questions WHERE id = ?", (qid,))
    if q["image_id"]:
        delete_file(q["image_id"])
    flash("질문을 삭제했습니다.", "ok")
    return redirect(url_for("student.questions"))


# ---------- 파일 다운로드 (강사/학생 공용, 권한 확인 후 전송) ----------

def _can_access_file(file_id):
    if g.user["role"] == "teacher":
        return True
    if g.user["role"] == "assistant":
        # 조교는 질문·추가 질문에 첨부된 사진만
        return query("""SELECT 1 FROM questions WHERE image_id = ?
                        UNION SELECT 1 FROM followups WHERE image_id = ?""", (file_id, file_id), one=True) is not None
    sid = g.user["student_id"]
    return query("""SELECT 1 FROM materials m JOIN students s ON s.class_id = m.class_id
                    WHERE m.file_id = ? AND s.id = ? AND s.active = 1
                    UNION
                    SELECT 1 FROM questions WHERE image_id = ? AND (qtype = '학습질문' OR student_id = ?)
                    UNION
                    SELECT 1 FROM followups f JOIN questions q ON q.id = f.question_id
                    WHERE f.image_id = ? AND (q.qtype = '학습질문' OR q.student_id = ?)
                    UNION
                    SELECT 1 FROM submissions WHERE file_id = ? AND student_id = ?""",
                 (file_id, sid, file_id, sid, file_id, sid, file_id, sid), one=True) is not None


@bp.route("/file/<int:fid>", endpoint="file")
@login_required()
def download(fid):
    f = query("SELECT * FROM files WHERE id = ?", (fid,), one=True)
    if f is None or not _can_access_file(fid):
        abort(404)
    path = os.path.join(current_app.config["UPLOAD_DIR"], f["stored_name"])
    if not os.path.exists(path):
        abort(404)
    inline = f["mime"].startswith("image/") and request.args.get("inline") == "1"
    audit("file_download", f"file:{fid}")
    resp = send_file(path, mimetype=f["mime"], as_attachment=not inline,
                     download_name=f["original_name"], max_age=0)
    resp.headers["Cache-Control"] = "no-store"
    return resp
