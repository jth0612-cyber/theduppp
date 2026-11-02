"""교재 분석실.
학생: 교재 인증 코드 등록(내 교재) → 분석실(가채점 입력, 예상 등급컷, 점수 분포, 문항별 오답률, 선지별 선택 비율).
강사: 교재·회차(정답·배점)·인증 코드 관리, 회차별 통계 보기.
정답과 배점은 서버에만 있고, 학생 화면에는 채점 결과와 통계만 나간다."""
import csv
import io
import json
from datetime import date, datetime, timedelta

from flask import (Blueprint, Response, abort, current_app, flash, g, redirect, render_template, request,
                   url_for)

import analysis
from db import execute, query
from security import audit, student_required, teacher_required

bp = Blueprint("books", __name__)

MAX_CODE_FAILS_PER_HOUR = 10


def _today():
    return date.today().isoformat()


def _ttl():
    return current_app.config.get("ANALYSIS_TTL", 300)


def _mock_or_404(mid):
    m = query("SELECT m.*, b.title AS book_title, b.subject, b.expires_on, b.is_free, b.notice "
              "FROM mocks m JOIN books b ON b.id = m.book_id WHERE m.id = ?", (mid,), one=True)
    if m is None:
        abort(404)
    return m


def _stats(mock):
    key, full = json.loads(mock["answer_key"]), mock["full_score"]
    step = analysis.score_step(json.loads(mock["points"]))

    def load():
        rows = query("SELECT answers, score FROM mock_entries WHERE mock_id = ?", (mock["id"],))
        return analysis.compute([dict(r) for r in rows], key, full, step)
    return analysis.cached(mock["id"], _ttl(), load)


def _selected_item(stats):
    items = stats["items"]
    if not items:
        return None
    try:
        q = int(request.args.get("q", "0"))
    except ValueError:
        q = 0
    if 1 <= q <= len(items):
        return items[q - 1]
    return max(items, key=lambda it: (it["wrong_pct"], -it["no"]))


# ---------- 학생 ----------

def _my_books():
    return query("""SELECT b.*, ub.registered_at FROM user_books ub JOIN books b ON b.id = ub.book_id
                    WHERE ub.user_id = ? ORDER BY ub.registered_at DESC""", (g.user["id"],))


def _accessible_mocks():
    return query("""SELECT m.*, b.title AS book_title, b.subject FROM mocks m
                    JOIN books b ON b.id = m.book_id
                    JOIN user_books ub ON ub.book_id = b.id AND ub.user_id = ?
                    WHERE m.open = 1 AND b.expires_on >= ? ORDER BY b.title, m.round_no""",
                 (g.user["id"], _today()))


@bp.route("/s/books")
@student_required
def my_books():
    return render_template("student/books.html", books=_my_books(), today=_today())


@bp.route("/s/books/register", methods=["GET", "POST"])
@student_required
def register_book():
    if request.method == "POST":
        since = (datetime.now() - timedelta(hours=1)).isoformat(sep=" ", timespec="seconds")
        fails = query("SELECT COUNT(*) AS n FROM audit_log WHERE user_id = ? AND action = 'book_code_failed' "
                      "AND created_at >= ?", (g.user["id"], since), one=True)["n"]
        if fails >= MAX_CODE_FAILS_PER_HOUR:
            flash("코드 입력이 여러 번 맞지 않아 잠시 막아 두었어요. 1시간 뒤에 다시 시도해 주세요.", "error")
            return render_template("student/book_register.html", step=2), 429
        code = analysis.normalize_code(request.form.get("code"))
        row = query("SELECT c.*, b.title, b.expires_on FROM book_codes c JOIN books b ON b.id = c.book_id "
                    "WHERE c.code = ?", (code,), one=True) if code else None
        error = None
        if row is None:
            error = "일치하는 코드가 없어요. 12자리를 다시 확인해 주세요. 코드에는 숫자 0·1과 영문 O·I·L이 들어가지 않아요."
        elif row["expires_on"] < _today():
            error = "이용 기간이 지난 교재예요."
        elif query("SELECT 1 FROM user_books WHERE user_id = ? AND book_id = ?",
                   (g.user["id"], row["book_id"]), one=True):
            flash("이미 서가에 있는 교재예요.", "ok")
            return redirect(url_for("books.my_books"))
        elif row["max_uses"] is not None and row["uses"] >= row["max_uses"]:
            error = "이미 다른 계정에서 쓴 코드예요. 착오라면 선생님께 알려 주세요."
        if error:
            audit("book_code_failed", f"code:{(code or '')[:4]}")
            flash(error, "error")
            return render_template("student/book_register.html", step=2)
        execute("INSERT INTO user_books (user_id, book_id, code_id) VALUES (?, ?, ?)",
                (g.user["id"], row["book_id"], row["id"]))
        execute("UPDATE book_codes SET uses = uses + 1 WHERE id = ?", (row["id"],))
        audit("book_registered", f"book:{row['book_id']}")
        book = query("SELECT * FROM books WHERE id = ?", (row["book_id"],), one=True)
        first = query("SELECT id FROM mocks WHERE book_id = ? AND open = 1 ORDER BY round_no LIMIT 1",
                      (book["id"],), one=True)
        return render_template("student/book_register.html", step=3, book=book, first_mock=first)
    return render_template("student/book_register.html", step=2)


@bp.route("/s/analysis")
@student_required
def analysis_home():
    mocks = _accessible_mocks()
    if not mocks:
        return render_template("student/analysis.html", mocks=[], mock=None)
    try:
        mid = int(request.args.get("mock", mocks[0]["id"]))
    except ValueError:
        mid = mocks[0]["id"]
    if mid not in {m["id"] for m in mocks}:
        abort(404)
    mock = _mock_or_404(mid)
    key = json.loads(mock["answer_key"])
    points = json.loads(mock["points"])
    entry = query("SELECT * FROM mock_entries WHERE mock_id = ? AND user_id = ?", (mid, g.user["id"]), one=True)
    stats = _stats(mock)
    my_score = entry["score"] if entry else None
    my_wrong = set(analysis.wrong_items(entry["answers"], key)) if entry and entry["mode"] == "answers" \
        and analysis.is_complete(entry["answers"], len(key)) else set()
    mode = request.args.get("mode") or (entry["mode"] if entry else "answers")
    marks = entry["answers"] if entry and entry["mode"] == "answers" else ""
    marks = (marks + "0" * mock["n_items"])[:mock["n_items"]]
    return render_template("student/analysis.html", mocks=mocks, mock=mock, entry=entry, stats=stats,
                           my_score=my_score, my_grade=analysis.grade_for(my_score, stats["cuts"]),
                           my_wrong=my_wrong, selected=_selected_item(stats), mode=mode, mock_param=mid,
                           my_bucket=analysis.bucket_label(my_score, mock["full_score"],
                                                           step=analysis.score_step(points)), marks=marks,
                           points=points, lost=sum(points[n - 1] for n in my_wrong),
                           filled=analysis.filled_count(marks),
                           min_for_cuts=analysis.MIN_FOR_CUTS, fmt=analysis._fmt)


@bp.route("/s/analysis/<int:mid>/submit", methods=["POST"])
@student_required
def submit_entry(mid):
    if mid not in {m["id"] for m in _accessible_mocks()}:
        abort(404)
    mock = _mock_or_404(mid)
    key, points = json.loads(mock["answer_key"]), json.loads(mock["points"])
    mode = request.form.get("mode")
    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    if mode == "answers":
        if request.form.get("quick", "").strip():
            answers = analysis.parse_answers(request.form.get("quick"), mock["n_items"])
        else:
            answers = analysis.answers_from_marks(request.form, mock["n_items"])
        score = analysis.score_answers(answers, key, points)
    elif mode == "score":
        answers = ""
        try:
            score = float(request.form.get("score", ""))
        except ValueError:
            score = None
        if score is None or not 0 <= score <= mock["full_score"]:
            flash(f"점수는 0~{analysis._fmt(mock['full_score'])} 사이로 입력하세요.", "error")
            return redirect(url_for("books.analysis_home", mock=mid, mode="score"))
    else:
        abort(400)
    execute("""INSERT INTO mock_entries (mock_id, user_id, mode, answers, score, updated_at) VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(mock_id, user_id) DO UPDATE SET mode = excluded.mode, answers = excluded.answers,
               score = excluded.score, updated_at = excluded.updated_at""",
            (mid, g.user["id"], mode, answers, score, now))
    if score is None:
        flash(f"{analysis.filled_count(answers)}문항을 적어 두었어요. {mock['n_items']}문항을 모두 고르면 채점합니다.", "ok")
    else:
        flash(f"채점을 마쳤어요. {analysis._fmt(score)}점 / {analysis._fmt(mock['full_score'])}점", "ok")
    return redirect(url_for("books.analysis_home", mock=mid) + "#result")


@bp.route("/s/analysis/<int:mid>/clear", methods=["POST"])
@student_required
def clear_entry(mid):
    execute("DELETE FROM mock_entries WHERE mock_id = ? AND user_id = ?", (mid, g.user["id"]))
    flash("입력한 답안을 지웠어요.", "ok")
    return redirect(url_for("books.analysis_home", mock=mid))


# ---------- 강사 ----------

@bp.route("/t/books", methods=["GET", "POST"])
@teacher_required
def teacher_books():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        expires_on = request.form.get("expires_on", "").strip()
        try:
            date.fromisoformat(expires_on)
        except ValueError:
            expires_on = ""
        if not title or not expires_on:
            flash("교재 이름과 이용 기간(마지막 날짜)을 입력하세요.", "error")
        else:
            bid = execute("INSERT INTO books (title, subject, expires_on, is_free, notice) VALUES (?, ?, ?, ?, ?)",
                          (title[:100], request.form.get("subject", "").strip()[:40], expires_on,
                           1 if request.form.get("is_free") else 0, request.form.get("notice", "").strip()[:300]))
            audit("book_created", f"book:{bid}")
            return redirect(url_for("books.teacher_book", bid=bid))
    books = query("""SELECT b.*, (SELECT COUNT(*) FROM user_books ub WHERE ub.book_id = b.id) AS users,
                     (SELECT COUNT(*) FROM mocks m WHERE m.book_id = b.id) AS mocks
                     FROM books b ORDER BY b.created_at DESC""")
    return render_template("teacher/books.html", books=books, today=_today())


def _book_or_404(bid):
    b = query("SELECT * FROM books WHERE id = ?", (bid,), one=True)
    if b is None:
        abort(404)
    return b


@bp.route("/t/books/<int:bid>")
@teacher_required
def teacher_book(bid):
    book = _book_or_404(bid)
    mocks = query("""SELECT m.*, (SELECT COUNT(*) FROM mock_entries e WHERE e.mock_id = m.id AND e.score IS NOT NULL)
                     AS n FROM mocks m WHERE m.book_id = ? ORDER BY m.round_no""", (bid,))
    shared = query("SELECT * FROM book_codes WHERE book_id = ? AND max_uses IS NULL ORDER BY id", (bid,))
    single = query("SELECT COUNT(*) AS total, SUM(uses) AS used FROM book_codes WHERE book_id = ? "
                   "AND max_uses IS NOT NULL", (bid,), one=True)
    users = query("SELECT COUNT(*) AS n FROM user_books WHERE book_id = ?", (bid,), one=True)["n"]
    return render_template("teacher/book_detail.html", book=book, mocks=mocks, shared=shared, single=single,
                           users=users, fmt_code=analysis.format_code, fmt=analysis._fmt,
                           next_round=(max([m["round_no"] for m in mocks]) + 1) if mocks else 1)


@bp.route("/t/books/<int:bid>/edit", methods=["POST"])
@teacher_required
def edit_book(bid):
    _book_or_404(bid)
    expires_on = request.form.get("expires_on", "").strip()
    try:
        date.fromisoformat(expires_on)
    except ValueError:
        flash("이용 기간 날짜가 올바르지 않습니다.", "error")
        return redirect(url_for("books.teacher_book", bid=bid))
    execute("UPDATE books SET title = ?, subject = ?, expires_on = ?, is_free = ?, notice = ? WHERE id = ?",
            (request.form.get("title", "").strip()[:100] or "제목 없음", request.form.get("subject", "").strip()[:40],
             expires_on, 1 if request.form.get("is_free") else 0, request.form.get("notice", "").strip()[:300], bid))
    flash("교재 정보를 저장했습니다.", "ok")
    return redirect(url_for("books.teacher_book", bid=bid))


def _code_taken(c):
    return query("SELECT 1 FROM book_codes WHERE code = ?", (c,), one=True) is not None


@bp.route("/t/books/<int:bid>/codes", methods=["POST"])
@teacher_required
def make_codes(bid):
    book = _book_or_404(bid)
    kind = request.form.get("kind")
    if kind == "shared":
        code = analysis.new_code(_code_taken)
        execute("INSERT INTO book_codes (book_id, code, max_uses) VALUES (?, ?, NULL)", (bid, code))
        audit("book_codes_created", f"book:{bid} shared")
        flash(f"배포 코드를 만들었습니다: {analysis.format_code(code)} (여러 명이 같은 코드를 씁니다)", "ok")
        return redirect(url_for("books.teacher_book", bid=bid))
    try:
        count = int(request.form.get("count", "0"))
    except ValueError:
        count = 0
    if not 1 <= count <= 2000:
        flash("코드 개수는 1~2000 사이로 입력하세요.", "error")
        return redirect(url_for("books.teacher_book", bid=bid))
    codes = []
    for _ in range(count):
        c = analysis.new_code(_code_taken)
        execute("INSERT INTO book_codes (book_id, code, max_uses) VALUES (?, ?, 1)", (bid, c))
        codes.append(c)
    audit("book_codes_created", f"book:{bid} single:{count}")
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["교재", "인증 코드"])
    for c in codes:
        w.writerow([book["title"], analysis.format_code(c)])
    return Response("﻿" + out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=book{bid}_codes.csv"})


@bp.route("/t/codes/<int:cid>/delete", methods=["POST"])
@teacher_required
def delete_code(cid):
    row = query("SELECT book_id FROM book_codes WHERE id = ?", (cid,), one=True)
    if row is None:
        abort(404)
    execute("DELETE FROM book_codes WHERE id = ?", (cid,))
    audit("book_code_deleted", f"code:{cid}")
    flash("코드를 삭제했습니다. 이미 등록한 학생은 계속 쓸 수 있어요.", "ok")
    return redirect(url_for("books.teacher_book", bid=row["book_id"]))


@bp.route("/t/books/<int:bid>/mocks", methods=["POST"])
@teacher_required
def add_mock(bid):
    _book_or_404(bid)
    try:
        round_no = int(request.form.get("round_no", ""))
        n_items = int(request.form.get("n_items", analysis.DEFAULT_ITEMS))
        full = float(request.form.get("full_score", analysis.DEFAULT_FULL))
        if not (1 <= n_items <= 60 and 0 < full <= 200 and round_no >= 1):
            raise ValueError("문항 수(1~60), 만점(0~200), 회차(1 이상)를 확인하세요.")
        key = analysis.parse_key(request.form.get("answer_key"), n_items)
        if request.form.get("points", "").strip():
            points = analysis.parse_points(request.form.get("points"), n_items, full)
        elif request.form.get("high_items", "").strip() or request.form.get("low_items", "").strip():
            points = analysis.points_from_levels(request.form.get("high_items"), request.form.get("low_items"),
                                                 n_items, full)
        else:
            points = analysis.parse_points("", n_items, full)
    except ValueError as e:
        flash(str(e) if str(e) and not str(e).startswith("invalid literal") else "숫자를 확인하세요.", "error")
        return redirect(url_for("books.teacher_book", bid=bid) + "#add-mock")
    if query("SELECT 1 FROM mocks WHERE book_id = ? AND round_no = ?", (bid, round_no), one=True):
        flash(f"{round_no}회는 이미 있습니다.", "error")
        return redirect(url_for("books.teacher_book", bid=bid) + "#add-mock")
    mid = execute("""INSERT INTO mocks (book_id, round_no, title, n_items, full_score, answer_key, points)
                     VALUES (?, ?, ?, ?, ?, ?, ?)""",
                  (bid, round_no, request.form.get("title", "").strip()[:60], n_items, full,
                   json.dumps(key), json.dumps(points)))
    audit("mock_created", f"mock:{mid}")
    flash(f"{round_no}회를 추가했습니다.", "ok")
    return redirect(url_for("books.teacher_book", bid=bid))


@bp.route("/t/mocks/<int:mid>/toggle", methods=["POST"])
@teacher_required
def toggle_mock(mid):
    m = _mock_or_404(mid)
    execute("UPDATE mocks SET open = ? WHERE id = ?", (0 if m["open"] else 1, mid))
    return redirect(url_for("books.teacher_book", bid=m["book_id"]))


@bp.route("/t/mocks/<int:mid>/delete", methods=["POST"])
@teacher_required
def delete_mock(mid):
    m = _mock_or_404(mid)
    execute("DELETE FROM mocks WHERE id = ?", (mid,))
    analysis.invalidate(mid)
    audit("mock_deleted", f"mock:{mid}")
    flash(f"{m['round_no']}회와 그 가채점 기록을 삭제했습니다.", "ok")
    return redirect(url_for("books.teacher_book", bid=m["book_id"]))


@bp.route("/t/books/<int:bid>/delete", methods=["POST"])
@teacher_required
def delete_book(bid):
    book = _book_or_404(bid)
    if request.form.get("confirm_title", "").strip() != book["title"]:
        flash("교재 이름을 정확히 입력해야 삭제됩니다.", "error")
        return redirect(url_for("books.teacher_book", bid=bid))
    for m in query("SELECT id FROM mocks WHERE book_id = ?", (bid,)):
        analysis.invalidate(m["id"])
    execute("DELETE FROM books WHERE id = ?", (bid,))
    audit("book_deleted", f"book:{bid}")
    flash("교재와 회차, 코드, 가채점 기록을 모두 삭제했습니다.", "ok")
    return redirect(url_for("books.teacher_books"))


@bp.route("/t/mocks/<int:mid>")
@teacher_required
def teacher_mock(mid):
    mock = _mock_or_404(mid)
    stats = _stats(mock)
    return render_template("teacher/mock_stats.html", mock=mock, stats=stats, selected=_selected_item(stats),
                           my_wrong=set(), my_score=None, my_grade=None, my_bucket=None, mock_param=None, min_for_cuts=analysis.MIN_FOR_CUTS, fmt=analysis._fmt,
                           key=json.loads(mock["answer_key"]))
