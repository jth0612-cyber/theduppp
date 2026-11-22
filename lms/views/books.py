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
from security import audit, decrypt, member_required, staff_required, student_required, teacher_required

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
        rows = query("SELECT answers, score FROM exam_results WHERE mock_id = ?", (mock["id"],))
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
    return query("""SELECT m.*, b.title AS book_title, b.subject, b.kind,
                           EXISTS (SELECT 1 FROM mock_entries e WHERE e.mock_id = m.id AND e.user_id = ?) AS mine,
                           EXISTS (SELECT 1 FROM omr_uploads o WHERE o.mock_id = m.id) AS uploaded
                    FROM mocks m JOIN books b ON b.id = m.book_id
                    WHERE m.open = 1 AND b.is_practice = 0 AND (
                          EXISTS (SELECT 1 FROM mock_entries e WHERE e.mock_id = m.id AND e.user_id = ?)
                          OR m.review != '' OR m.eval_level IS NOT NULL OR m.eval_video != '')
                    ORDER BY b.kind, m.round_no DESC""", (g.user["id"], g.user["id"]))


@bp.route("/s/books/register", methods=["GET", "POST"])
@student_required
def register_book():
    if request.method == "POST":
        since = (datetime.now() - timedelta(hours=1)).isoformat(sep=" ", timespec="seconds")
        fails = query("SELECT COUNT(*) AS n FROM audit_log WHERE user_id = ? AND action = 'book_code_failed' "
                      "AND created_at >= ?", (g.user["id"], since), one=True)["n"]
        if fails >= MAX_CODE_FAILS_PER_HOUR:
            flash("코드 입력이 여러 번 맞지 않아 잠시 차단했습니다. 1시간 뒤에 다시 시도해 주세요.", "error")
            return render_template("student/book_register.html", step=2), 429
        code = analysis.normalize_code(request.form.get("code"))
        row = query("SELECT c.*, b.title, b.expires_on FROM book_codes c JOIN books b ON b.id = c.book_id "
                    "WHERE c.code = ?", (code,), one=True) if code else None
        error = None
        if row is None:
            error = "일치하는 코드가 없습니다. 12자리를 다시 확인해 주세요. 코드에는 숫자 0 및 1과 영문 O·I·L이 포함되지 않습니다."
        elif row["expires_on"] < _today():
            error = "이용 기간이 지난 교재입니다."
        elif query("SELECT 1 FROM user_books WHERE user_id = ? AND book_id = ?",
                   (g.user["id"], row["book_id"]), one=True):
            flash("이미 등록한 교재입니다.", "ok")
            return redirect(url_for("books.analysis_home"))
        elif row["max_uses"] is not None and row["uses"] >= row["max_uses"]:
            error = "이미 다른 계정에서 사용한 코드입니다. 착오라면 선생님께 알려 주세요."
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
    """복테&모의 분석: 강사·조교가 올린 OMR 결과로 채점된 내 답안·성적표·오답 분석·학습 유형·통계·총평·1:1 첨삭.
    학생이 답을 적는 칸은 없다."""
    import exams
    if g.user["student_id"]:
        exams.sync_entries(student_id=g.user["student_id"])      # 가입 전에 올라온 결과도 가져온다
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
    why_open = "새 1:1 첨삭 답변이 있는 회차" if unread and mid == unread["mock_id"] and "mock" not in request.args else ""
    key, points = json.loads(mock["answer_key"]), json.loads(mock["points"])
    entry = query("SELECT * FROM mock_entries WHERE mock_id = ? AND user_id = ?", (mid, g.user["id"]), one=True)
    from content import youtube_id
    ev = {"level": EVAL_LEVELS.get(mock["eval_level"]), "n": mock["eval_level"], "yt": youtube_id(mock["eval_video"]) if mock["eval_video"] else None}
    if entry is None:                                          # 내 결과가 없는 회차: 시험 평가만
        stats = _stats(mock) if mock["n_items"] else None
        absent = bool(query("SELECT 1 FROM omr_uploads WHERE mock_id = ? LIMIT 1", (mid,), one=True))   # OMR은 올라왔는데 내 답안이 없음 = 미응시
        return render_template("student/analysis.html", absent=absent, why_open=why_open, mocks=mocks, mock=mock, entry=None, ev=ev, kinds=KINDS, stats=stats,
                               fmt=analysis._fmt)
    stats = _stats(mock)
    my_score = entry["score"]
    marks = ((entry["answers"] or "") + "0" * mock["n_items"])[:mock["n_items"]]
    my_wrong = set(analysis.wrong_items(marks, key)) if entry["mode"] == "answers" else set()
    from views.feedback import thread_for
    fb, fb_msgs = thread_for(mid, g.user["id"], mark_seen=True)
    rep = exams.student_report(mid, g.user["student_id"]) if g.user["student_id"] else None
    prof = exams.classify_profile(exams.history(g.user["student_id"])) if rep else None
    from views.care import paper_of, weak_card
    units, weak = weak_card(g.user["student_id"]) if g.user["student_id"] else ([], None)
    from views.care import unit_scores
    season_units = [u for u in unit_scores(g.user["student_id"], limit=500) if u["pct"] < 80][:5] if g.user["student_id"] else []
    paper, paper_files, paper_marks = paper_of(mid, g.user["student_id"]) if g.user["student_id"] else (None, [], {})
    return render_template("student/analysis.html", why_open=why_open, mocks=mocks, mock=mock, entry=entry, stats=stats, fb=fb, fb_msgs=fb_msgs,
                           rep=rep, prof=prof, pct1=exams.pct1, key_label=analysis.key_label, ev=ev, units=units, season_units=season_units, weak=weak, paper=paper, paper_files=paper_files, paper_marks=paper_marks,
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
@staff_required
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
    rounds = {}
    for r in query("""SELECT m.id, m.round_no, m.n_items, m.exam_date, b.kind, b.is_practice,
                             (SELECT COUNT(*) FROM exam_results x WHERE x.mock_id = m.id) AS n
                      FROM mocks m JOIN books b ON b.id = m.book_id
                      WHERE (b.title = b.kind OR b.title = '[연습] ' || b.kind) ORDER BY m.round_no"""):
        rounds.setdefault(r["kind"] if not r["is_practice"] else "[연습] " + r["kind"], []).append(r)
    return render_template("teacher/books.html", books=books, today=_today(), shop=SHOP_BOOKS, links=shop_links(),
                           rounds=rounds, kinds=KINDS + ("[연습] 복습 테스트", "[연습] 모의고사"))


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
@staff_required
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
@staff_required
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
@staff_required
def delete_code(cid):
    row = query("SELECT book_id FROM book_codes WHERE id = ?", (cid,), one=True)
    if row is None:
        abort(404)
    execute("DELETE FROM book_codes WHERE id = ?", (cid,))
    audit("book_code_deleted", f"code:{cid}")
    flash("코드를 삭제했습니다. 이미 등록한 학생은 계속 사용할 수 있습니다.", "ok")
    return redirect(url_for("books.teacher_book", bid=row["book_id"]))


@bp.route("/t/books/<int:bid>/mocks", methods=["POST"])
@staff_required
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
@staff_required
def toggle_mock(mid):
    m = _mock_or_404(mid)
    execute("UPDATE mocks SET open = ? WHERE id = ?", (0 if m["open"] else 1, mid))
    return redirect(url_for("books.teacher_book", bid=m["book_id"]))


@bp.route("/t/mocks/<int:mid>/delete", methods=["POST"])
@staff_required
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


EVAL_LEVELS = {1: "매우 쉬움", 2: "쉬움", 3: "보통", 4: "어려움", 5: "매우 어려움"}
EVAL_TIMES = ("여유", "적당", "빠듯")


@bp.route("/t/mocks/<int:mid>/review", methods=["POST"])
@staff_required
def mock_review(mid):
    """시험 평가: 강사·조교 누구나 쓰고 고친다. 학생이 이 회차를 열면 맨 위에 보인다(내 결과가 없어도)."""
    from content import youtube_id
    _mock_or_404(mid)
    text = request.form.get("review", "").strip()[:4000]
    level = request.form.get("level", type=int)
    level = level if level in EVAL_LEVELS else None
    tm = request.form.get("time", "")
    tm = tm if tm in EVAL_TIMES else ""
    killer = ", ".join(re.findall(r"\d{1,2}", request.form.get("killer", "")))[:80]
    video = request.form.get("video", "").strip()[:500]
    if video and not youtube_id(video):
        flash("해설 영상은 유튜브 주소만 넣을 수 있습니다.", "error")
        return redirect(url_for("books.teacher_mock", mid=mid) + "#eval")
    filled = bool(text or level or tm or killer or video)
    who = (g.user["display_name"] or g.user["username"]) if g.user["role"] == "assistant" else "정태혁 선생님"
    execute("""UPDATE mocks SET review = ?, eval_level = ?, eval_time = ?, eval_killer = ?, eval_video = ?,
               review_by = ?, review_at = datetime('now', 'localtime') WHERE id = ?""",
            (text, level, tm, killer, video, who if filled else "", mid))
    audit("mock_review", f"mock:{mid}")
    flash("시험 평가를 저장했습니다. 학생 화면에 바로 보입니다." if filled else "시험 평가를 지웠습니다.", "ok")
    return redirect(url_for("books.teacher_mock", mid=mid) + "#eval")


@bp.route("/t/mocks/<int:mid>")
@staff_required
def teacher_mock(mid):
    """회차 화면 (강사·조교 같은 화면): 엑셀 올리기, 올린 결과, 반별 통계, 학생 결과, 학부모 문자, 총평, 문항 통계."""
    import exams
    mock = _mock_or_404(mid)
    m = exams.load_mock(mid)
    up = query("SELECT u.*, x.display_name, x.username, x.role FROM omr_uploads u LEFT JOIN users x ON x.id = u.by_id "
               "WHERE u.mock_id = ? ORDER BY u.id DESC LIMIT 1", (mid,), one=True)
    up_rows = json.loads(up["rows"]) if up else []
    ctx = {"mock": mock, "m": m, "up": up, "up_rows": up_rows, "fmt": analysis._fmt, "pct1": exams.pct1,
           "levels": EVAL_LEVELS, "times": EVAL_TIMES,
           "key_label": analysis.key_label, "min_n": exams.SET["min_n"]}
    if m["n_items"]:
        cs = exams.class_stats(mid)
        stats = _stats(mock)
        ctx.update(cs=cs, stats=stats, selected=_selected_item(stats), key=m["key"], entries=[
            dict(r, wrong=len(analysis.wrong_items(r["answers"], m["key"]))) for r in cs["rows"]],
            my_wrong=set(), my_score=None, my_grade=None, my_bucket=None, mock_param=None, min_for_cuts=analysis.MIN_FOR_CUTS)
    return render_template("teacher/mock_stats.html", **ctx)


@bp.route("/t/mocks/<int:mid>/omr", methods=["POST"])
@staff_required
def omr_upload(mid):
    """채점기 엑셀(OMR)을 올리면 학생마다 채점해 저장하고, 학생 화면·학부모 문자에 바로 반영된다."""
    import exams
    import omr
    _mock_or_404(mid)
    f = request.files.get("file")
    if not f or not f.filename:
        flash("엑셀 파일을 골라 주세요.", "error")
        return redirect(url_for("books.teacher_mock", mid=mid) + "#omr")
    data = f.read(10 * 1024 * 1024 + 1)
    if len(data) > 10 * 1024 * 1024:
        flash("파일이 10MB를 넘습니다.", "error")
        return redirect(url_for("books.teacher_mock", mid=mid) + "#omr")
    try:
        res = exams.apply_upload(mid, data, f.filename, g.user["id"])
    except omr.OmrError as e:
        flash(str(e), "error")
        return redirect(url_for("books.teacher_mock", mid=mid) + "#omr")
    audit("omr_upload", f"mock:{mid} rows:{res['ok']}")
    flash(f"{res['summary']}. 학생 화면에 바로 보입니다." if res["ok"] else "반영된 학생이 없습니다. 아래 줄별 결과를 확인해 주세요.",
          "ok" if res["ok"] else "error")
    return redirect(url_for("books.teacher_mock", mid=mid) + "#omr")


@bp.route("/t/mocks/<int:mid>/omr-form.xlsx")
@staff_required
def omr_template(mid):
    """빈 양식: 재원생 이름·수험번호(학부모 번호 뒤 8자리)·학생코드·반이 채워져 있다."""
    import exams
    import omr
    m = exams.load_mock(mid) or abort(404)
    n = m["n_items"] or request.args.get("n", type=int) or (20 if m["kind"] == "복습 테스트" else 25)
    n = max(1, min(n, 60))
    students = [(s["name"], s["parent8"], s["student_no"], s["cls"]) for s in sorted(exams.student_index(), key=lambda s: (s["cls"], s["name"]))]
    data = omr.template(n, students, m["info"])
    from urllib.parse import quote
    name = f"OMR_{exams.exam_title(m)}.xlsx"
    return Response(data, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename=omr.xlsx; filename*=UTF-8''{quote(name)}"})


@bp.route("/t/mocks/<int:mid>/entries/clear", methods=["POST"])
@staff_required
def omr_clear(mid):
    _mock_or_404(mid)
    execute("DELETE FROM exam_results WHERE mock_id = ?", (mid,))
    execute("DELETE FROM mock_entries WHERE mock_id = ?", (mid,))
    analysis.invalidate(mid)
    audit("omr_clear", f"mock:{mid}")
    flash("이 회차의 학생 결과를 모두 지웠습니다.", "ok")
    return redirect(url_for("books.teacher_mock", mid=mid) + "#omr")


@bp.route("/t/mocks/<int:mid>/sms")
@staff_required
def mock_sms(mid):
    """학부모 문자: 학생마다 분석 문자. 복사하거나 CSV 로 받아 문자 서비스에 붙여 넣는다."""
    import exams
    m = exams.load_mock(mid) or abort(404)
    if not m["n_items"]:
        abort(404)
    cs = exams.class_stats(mid)
    out = []
    from views.care import parent_token
    root = request.url_root.rstrip("/")
    for r in cs["rows"]:
        text = exams.sms_for(mid, r["student_id"], cs)
        text += f"\n\n학생 리포트: {root}{url_for('care.parent_page', token=parent_token(r['student_id']))}"
        phone = decrypt(r["parent_phone_enc"])
        state = "수신미동의" if not r["sms_ok"] else ("연락처없음" if not phone else "")
        out.append({"r": r, "text": text, "phone": phone, "state": state, "bytes": exams.sms_bytes(text)})
    if request.args.get("csv"):
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["반", "이름", "학부모연락처", "상태", "문자"])
        for x in out:
            w.writerow([x["r"]["cls"], x["r"]["name"], x["phone"], x["state"] or "발송 가능", x["text"]])
        audit("sms_csv", f"mock:{mid}")
        from urllib.parse import quote
        return Response("\ufeff" + buf.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment; filename=sms.csv; filename*=UTF-8''{quote('문자_' + exams.exam_title(m) + '.csv')}"})
    audit("sms_view", f"mock:{mid}")
    return render_template("teacher/mock_sms.html", m=m, rows=out, title=exams.exam_title(m))


@bp.route("/t/mocks/<int:mid>/practice.xlsx")
@staff_required
def practice_file(mid):
    """연습 회차 전용: 실장 TEST반 가상 학생 50명의 예시 OMR 엑셀."""
    import exams
    m = exams.load_mock(mid) or abort(404)
    if not m["is_practice"]:
        abort(404)
    from urllib.parse import quote
    return Response(exams.practice_workbook(mid), mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename=practice.xlsx; filename*=UTF-8''{quote('연습_' + exams.exam_title(m) + '.xlsx')}"})


@bp.route("/t/mocks/<int:mid>/note/<int:sid>", methods=["POST"])
@staff_required
def ta_note(mid, sid):
    """조교가 직접 쓴 피드백: 학부모 문자의 총평 자리에 들어가고, 나중에 피드백 방향을 정리하는 자료로 모은다."""
    text = request.form.get("note", "").strip()[:1500]
    if not query("SELECT 1 FROM exam_results WHERE mock_id = ? AND student_id = ?", (mid, sid), one=True):
        abort(404)
    execute("UPDATE exam_results SET ta_note = ?, ta_by = ?, ta_at = datetime('now', 'localtime') WHERE mock_id = ? AND student_id = ?",
            (text, g.user["id"], mid, sid))
    audit("ta_note", f"mock:{mid} student:{sid}")
    flash("피드백을 저장했습니다. 문자에 바로 들어갑니다." if text else "피드백을 지웠습니다.", "ok")
    return redirect(url_for("books.mock_sms", mid=mid) + f"#s{sid}")


@bp.route("/t/feedback-notes.csv")
@staff_required
def ta_notes_csv():
    """조교 피드백 모음 (피드백 방향 정리용). 학생 이름·연락처는 넣지 않고 학생코드만 쓴다."""
    import exams
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["시험", "종류", "날짜", "반", "학생코드", "점수", "만점", "반 평균", "틀린 문항", "오답 유형", "조교 피드백", "작성자", "작성일"])
    for r in query("""SELECT r.*, s.student_no, c.name AS cls, x.display_name, x.role FROM exam_results r
                      JOIN students s ON s.id = r.student_id JOIN classes c ON c.id = s.class_id
                      LEFT JOIN users x ON x.id = r.ta_by WHERE r.ta_note != '' ORDER BY r.mock_id, c.name"""):
        rep = exams.student_report(r["mock_id"], r["student_id"])
        if not rep:
            continue
        types = ", ".join(f"{a['no']}번 {a['type']}" for a in rep["wrongs"] if a["type"])
        w.writerow([exams.exam_title(rep["mock"]), rep["mock"]["kind"], rep["mock"]["exam_date"], r["cls"], r["student_no"],
                    analysis._fmt(r["score"]), analysis._fmt(rep["mock"]["full_score"]), rep["st"]["avg"],
                    ", ".join(map(str, rep["wrong"])), types, r["ta_note"],
                    r["display_name"] or ("정태혁 선생님" if r["role"] == "teacher" else ""), r["ta_at"] or ""])
    audit("ta_notes_csv", "")
    return Response("\ufeff" + buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=feedback-notes.csv"})
