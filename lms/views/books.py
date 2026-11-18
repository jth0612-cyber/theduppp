"""교재 분석실.
학생: 교재 인증 코드 등록(내 교재) → 분석실(가채점 입력, 예상 등급컷, 점수 분포, 문항별 오답률, 선지별 선택 비율).
강사: 교재·회차(정답·배점)·인증 코드 관리, 회차별 통계 보기.
정답과 배점은 서버에만 있고, 학생 화면에는 채점 결과와 통계만 나간다."""
import csv
import io
import json
import re
from datetime import date, datetime, timedelta

from flask import (Blueprint, Response, abort, current_app, flash, g, redirect, render_template, request,
                   url_for)

import analysis
from db import execute, query
from security import audit, member_required, staff_required, student_required, teacher_only, teacher_required

bp = Blueprint("books", __name__)

MAX_CODE_FAILS_PER_HOUR = 10


def _today():
    return date.today().isoformat()


def _ttl():
    return current_app.config.get("ANALYSIS_TTL", 300)


def _mock_or_404(mid):
    m = query("SELECT m.*, b.title AS book_title, b.subject, b.expires_on, b.is_free, b.notice, b.kind "
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

KINDS = ("복습 테스트", "모의고사")


def _accessible_mocks():
    """학생이 볼 수 있는 회차: 강사가 올린 OMR 결과에 이 학생 답안이 있는 회차 (열려 있는 것만)."""
    return query("""SELECT m.*, b.title AS book_title, b.subject, b.kind FROM mocks m
                    JOIN books b ON b.id = m.book_id
                    JOIN mock_entries e ON e.mock_id = m.id AND e.user_id = ?
                    WHERE m.open = 1 ORDER BY b.kind, m.created_at DESC, m.round_no DESC""", (g.user["id"],))


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
            flash("이미 등록한 교재예요.", "ok")
            return redirect(url_for("books.analysis_home"))
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
    """복테&모의 분석: 강사가 올린 OMR 결과로 채점된 내 답안·성적표·통계·총평·1:1 첨삭. 학생이 답을 적는 칸은 없다."""
    mocks = _accessible_mocks()
    if not mocks:
        return render_template("student/analysis.html", mocks=[], mock=None, kinds=KINDS)
    ids = {m["id"] for m in mocks}
    unread = query("SELECT mock_id FROM feedback_threads WHERE user_id = ? AND unread = 1 ORDER BY updated_at DESC LIMIT 1",
                   (g.user["id"],), one=True)
    default = unread["mock_id"] if unread and unread["mock_id"] in ids else mocks[0]["id"]
    try:
        mid = int(request.args.get("mock", default))
    except ValueError:
        mid = default
    if mid not in ids:
        abort(404)
    mock = _mock_or_404(mid)
    key, points = json.loads(mock["answer_key"]), json.loads(mock["points"])
    entry = query("SELECT * FROM mock_entries WHERE mock_id = ? AND user_id = ?", (mid, g.user["id"]), one=True)
    stats = _stats(mock)
    my_score = entry["score"]
    marks = ((entry["answers"] or "") + "0" * mock["n_items"])[:mock["n_items"]]
    my_wrong = set(analysis.wrong_items(marks, key)) if entry["mode"] == "answers" else set()
    from views.feedback import thread_for
    fb, fb_msgs = thread_for(mid, g.user["id"], mark_seen=True)
    return render_template("student/analysis.html", mocks=mocks, mock=mock, entry=entry, stats=stats, fb=fb, fb_msgs=fb_msgs,
                           kinds=KINDS, key=key, my_score=my_score, my_grade=analysis.grade_for(my_score, stats["cuts"]),
                           my_wrong=my_wrong, selected=_selected_item(stats), mock_param=mid,
                           my_bucket=analysis.bucket_label(my_score, mock["full_score"], step=analysis.score_step(points)),
                           marks=marks, points=points, lost=sum(points[n - 1] for n in my_wrong),
                           min_for_cuts=analysis.MIN_FOR_CUTS, fmt=analysis._fmt)


# ---------- 강사 ----------

# 첫 화면(로그인 전) 교재 표지마다 붙는 구매 링크. 열쇠: settings 'buy_<key>'
SHOP_BOOKS = [("lineup", "LINE UP", "개념서"), ("framing", "FRAMING", "기출문제집"), ("logic", "LOGIC BUILD", "심층 분석서"), ("note", "필기노트", "TOPIC별"),
              ("squeeze", "Squeeze", "주간지 Season 1&2"), ("sweep", "SWEEP", "주간지 Season 3")]
SHOP_ALT = {"lineup": "LINE UP 통합과학 II(빨강)와 I 두 권", "framing": "FRAMING 흰 표지(통합과학 I-1), 회색 표지(I-2), 검은 표지(II) 세 권",
            "logic": "LOGIC BUILD 앞표지와 뒤표지",
            "note": "필기노트 TOPIC 07, 09, 01 쪽",
            "squeeze": "Squeeze Season 1과 Season 2 주간지 두 권", "sweep": "SWEEP 주간지 앞표지와 보라색 뒤표지"}


def shop_links():
    have = {r["key"][4:]: r["value"] for r in query("SELECT key, value FROM settings WHERE substr(key, 1, 4) = 'buy_'")}
    return {k: have.get(k, "") for k, _, _ in SHOP_BOOKS}


def _clean_url(raw):
    """http(s) 주소만 받는다. 'smartstore.naver.com/...'처럼 앞을 빼먹으면 https:// 를 붙인다."""
    from urllib.parse import urlparse
    u = (raw or "").strip()[:500]
    if not u:
        return ""
    if not re.match(r"^https?://", u, re.I):
        u = "https://" + u
    p = urlparse(u)
    return u if p.scheme in ("http", "https") and "." in p.netloc and " " not in u else None


@bp.route("/t/books/shop", methods=["POST"])
@teacher_required
def shop_save():
    bad = []
    for key, name, _ in SHOP_BOOKS:
        url = _clean_url(request.form.get(key, ""))
        if url is None:
            bad.append(name)
            continue
        if url:
            execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", ("buy_" + key, url))
        else:
            execute("DELETE FROM settings WHERE key = ?", ("buy_" + key,))
    audit("shop_links")
    if bad:
        flash("주소 모양이 아니라 저장하지 못했어요: " + ", ".join(bad), "error")
    else:
        flash("구매 링크를 저장했습니다.", "ok")
    return redirect(url_for("books.teacher_books") + "#shop")


@bp.route("/s/books/buy")
@member_required
def shop():
    links = shop_links()
    return render_template("student/shop.html", books=[{"key": k, "name": n, "sub": sub, "url": links[k], "alt": SHOP_ALT[k]} for k, n, sub in SHOP_BOOKS])


@bp.route("/t/books", methods=["GET", "POST"])
@staff_required
def teacher_books():
    if request.method == "POST":
        teacher_only()  # 조교는 보기만
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
            kind = request.form.get("kind") if request.form.get("kind") in KINDS else "모의고사"
            bid = execute("INSERT INTO books (title, subject, expires_on, is_free, notice, kind) VALUES (?, ?, ?, ?, ?, ?)",
                          (title[:100], request.form.get("subject", "").strip()[:40], expires_on,
                           1 if request.form.get("is_free") else 0, request.form.get("notice", "").strip()[:300], kind))
            audit("book_created", f"book:{bid}")
            return redirect(url_for("books.teacher_book", bid=bid))
    books = query("""SELECT b.*, (SELECT COUNT(*) FROM user_books ub WHERE ub.book_id = b.id) AS users,
                     (SELECT COUNT(*) FROM mocks m WHERE m.book_id = b.id) AS mocks
                     FROM books b ORDER BY b.created_at DESC""")
    return render_template("teacher/books.html", books=books, today=_today(), shop=SHOP_BOOKS, links=shop_links())


def _book_or_404(bid):
    b = query("SELECT * FROM books WHERE id = ?", (bid,), one=True)
    if b is None:
        abort(404)
    return b


@bp.route("/t/books/<int:bid>")
@staff_required
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
    kind = request.form.get("kind") if request.form.get("kind") in KINDS else _book_or_404(bid)["kind"]
    execute("UPDATE books SET title = ?, subject = ?, expires_on = ?, is_free = ?, notice = ?, kind = ? WHERE id = ?",
            (request.form.get("title", "").strip()[:100] or "제목 없음", request.form.get("subject", "").strip()[:40],
             expires_on, 1 if request.form.get("is_free") else 0, request.form.get("notice", "").strip()[:300], kind, bid))
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
    from views.feedback import delete_mock_files
    delete_mock_files(mid)
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
    from views.feedback import delete_mock_files
    for m in query("SELECT id FROM mocks WHERE book_id = ?", (bid,)):
        analysis.invalidate(m["id"])
        delete_mock_files(m["id"])
    execute("DELETE FROM books WHERE id = ?", (bid,))
    audit("book_deleted", f"book:{bid}")
    flash("교재와 회차, 코드, 가채점 기록을 모두 삭제했습니다.", "ok")
    return redirect(url_for("books.teacher_books"))


@bp.route("/t/mocks/<int:mid>/review", methods=["POST"])
@staff_required
def mock_review(mid):
    """모의고사 총평: 강사·조교가 쓰고, 학생 분석 화면 맨 위에 보인다."""
    _mock_or_404(mid)
    text = request.form.get("review", "").strip()[:4000]
    from flask import g as _g
    who = (_g.user["display_name"] or _g.user["username"]) if _g.user["role"] == "assistant" else "정태혁 선생님"
    execute("UPDATE mocks SET review = ?, review_by = ?, review_at = datetime('now', 'localtime') WHERE id = ?",
            (text, who if text else "", mid))
    audit("mock_review", f"mock:{mid}")
    flash("총평을 저장했습니다." if text else "총평을 지웠습니다.", "ok")
    return redirect(url_for("books.teacher_mock", mid=mid))


@bp.route("/t/mocks/<int:mid>")
@staff_required
def teacher_mock(mid):
    mock = _mock_or_404(mid)
    stats = _stats(mock)
    key = json.loads(mock["answer_key"])
    entries = [dict(r, wrong=len(analysis.wrong_items(r["answers"], key))) for r in query(
        """SELECT e.*, s.name, s.student_no, c.name AS cls FROM mock_entries e JOIN users u ON u.id = e.user_id
           LEFT JOIN students s ON s.id = u.student_id LEFT JOIN classes c ON c.id = s.class_id
           WHERE e.mock_id = ? ORDER BY e.score DESC, s.name""", (mid,))]
    return render_template("teacher/mock_stats.html", mock=mock, stats=stats, selected=_selected_item(stats), entries=entries,
                           my_wrong=set(), my_score=None, my_grade=None, my_bucket=None, mock_param=None, min_for_cuts=analysis.MIN_FOR_CUTS, fmt=analysis._fmt,
                           key=json.loads(mock["answer_key"]))


# ---------- OMR 결과 엑셀 올리기 (강사) ----------

def _student_index():
    """학생 찾기용: 학생코드·아이디 → user, 이름 → [user...]"""
    rows = query("""SELECT u.id AS uid, u.username, s.student_no, s.name, c.name AS cls FROM students s
                    JOIN classes c ON c.id = s.class_id LEFT JOIN users u ON u.student_id = s.id AND u.role = 'student'
                    WHERE s.active = 1""")
    by_code, by_name = {}, {}
    for r in rows:
        for k in (r["student_no"], r["username"]):
            if k:
                by_code[str(k).strip().upper()] = r
        by_name.setdefault(r["name"], []).append(r)
    return by_code, by_name


def _match(row, by_code, by_name):
    if row["code"]:
        r = by_code.get(row["code"].upper())
        if r is None:
            return None, "학생코드 없음"
    else:
        cands = by_name.get(row["name"], [])
        if row["cls"] and len(cands) > 1:
            cands = [c for c in cands if row["cls"] in c["cls"]]
        if not cands:
            return None, "이름 없음"
        if len(cands) > 1:
            return None, "같은 이름이 여러 명 (학생코드나 반을 적어 주세요)"
        r = cands[0]
    if not r["uid"]:
        return None, "아직 가입 전"
    return r, None


@bp.route("/t/mocks/<int:mid>/omr", methods=["POST"])
@teacher_required
def omr_upload(mid):
    """OMR 결과 엑셀을 올리면 학생마다 채점해 저장한다. 같은 학생은 새 파일 내용으로 바뀐다."""
    import omr
    mock = _mock_or_404(mid)
    key, points = json.loads(mock["answer_key"]), json.loads(mock["points"])
    f = request.files.get("file")
    if not f or not f.filename:
        flash("엑셀 파일을 골라 주세요.", "error")
        return redirect(url_for("books.teacher_mock", mid=mid) + "#omr")
    try:
        rows = omr.read(f.read(5 * 1024 * 1024 + 1)[:5 * 1024 * 1024], f.filename, mock["n_items"])
    except Exception as e:                                   # 깨진 파일·형식 오류
        flash(str(e) if isinstance(e, ValueError) else "파일을 읽지 못했습니다. 엑셀(.xlsx)로 다시 저장해 올려 주세요.", "error")
        return redirect(url_for("books.teacher_mock", mid=mid) + "#omr")
    by_code, by_name = _student_index()
    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    done, missed, seen = 0, [], set()
    for row in rows:
        r, why = _match(row, by_code, by_name)
        if r is None or r["uid"] in seen:
            missed.append(f"{row['row']}줄 {row['code'] or row['name']}: {why or '같은 학생이 두 번'}")
            continue
        seen.add(r["uid"])
        score = analysis.score_omr(row["answers"], key, points)
        execute("""INSERT INTO mock_entries (mock_id, user_id, mode, answers, score, updated_at) VALUES (?, ?, 'answers', ?, ?, ?)
                   ON CONFLICT(mock_id, user_id) DO UPDATE SET mode = 'answers', answers = excluded.answers,
                   score = excluded.score, updated_at = excluded.updated_at""", (mid, r["uid"], row["answers"], score, now))
        done += 1
    analysis.invalidate(mid)
    audit("omr_upload", f"mock:{mid} rows:{done}")
    flash(f"{done}명 결과를 반영했습니다. 학생 화면에 바로 보입니다." if done else "반영된 학생이 없습니다.", "ok" if done else "error")
    if missed:
        flash(f"반영 못 한 줄 {len(missed)}개 — " + " / ".join(missed[:15]) + (" …" if len(missed) > 15 else ""), "error")
    return redirect(url_for("books.teacher_mock", mid=mid) + "#omr")


@bp.route("/t/mocks/<int:mid>/omr-form.xlsx")
@staff_required
def omr_template(mid):
    """빈 양식: 지금 재원 중인 학생의 학생코드·이름·반이 미리 채워져 있다."""
    import omr
    mock = _mock_or_404(mid)
    students = [(r["student_no"], r["name"], r["cls"]) for r in query(
        """SELECT s.student_no, s.name, c.name AS cls FROM students s JOIN classes c ON c.id = s.class_id
           WHERE s.active = 1 ORDER BY c.name, s.name""")]
    data = omr.template(mock["n_items"], students)
    name = f"OMR_{mock['book_title']}_{mock['round_no']}회.xlsx"
    from urllib.parse import quote
    return Response(data, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename=omr.xlsx; filename*=UTF-8''{quote(name)}"})


@bp.route("/t/mocks/<int:mid>/entries/clear", methods=["POST"])
@teacher_required
def omr_clear(mid):
    _mock_or_404(mid)
    execute("DELETE FROM mock_entries WHERE mock_id = ?", (mid,))
    analysis.invalidate(mid)
    audit("omr_clear", f"mock:{mid}")
    flash("이 회차의 학생 결과를 모두 지웠습니다.", "ok")
    return redirect(url_for("books.teacher_mock", mid=mid) + "#omr")
