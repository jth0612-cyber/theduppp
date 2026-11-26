"""학습 관리: 시험지 첨삭 · 수업 기록 · 취약 단원 · 학부모 리포트.

- 시험지 첨삭: 복테·모의 결과가 올라온 회차에서 학생이 풀이가 적힌 시험지를 사진으로 올린다 → 조교가 OMR로 틀린 문항마다
  오답 유형·메모를 단다. 학생 화면은 '시험지 제출 → 선생님 검사 → 문항별 첨삭' 세 단계로 보이고, 끝나면 알림이 간다.
- 수업 기록: 반별로 날짜·주제·수업 노트 사진을 올리면 그 반 학생 화면에 날짜순으로 쌓인다.
- 학부모 리포트: 학생마다 비밀 링크(로그인 없음). 최근 시험 득점률과 변화, 시험 결과, 단원별 성취도,
  틀린 이유(오답 분석·시험지 첨삭), 선생님 코멘트, 출결. 학부모 문자 끝에 이 링크가 붙는다."""
import json
import re
import secrets
from datetime import date, datetime, timedelta

from flask import Blueprint, abort, flash, g, make_response, redirect, render_template, request, url_for

from db import execute, query
from security import IMAGE_EXTS, audit, delete_file, save_upload, staff_required, student_required

bp = Blueprint("care", __name__)
MAX_PAPER_PHOTOS = 6
MAX_LESSON_PHOTOS = 10
ERR_TYPES = ("개념 부족", "자료 해석", "조건 독해", "계산 실수", "시간 부족", "기타")


def _photos(field, limit):
    imgs = [f for f in request.files.getlist(field) if f and f.filename]
    if len(imgs) > limit:
        raise ValueError(f"사진은 {limit}장까지 올릴 수 있어요.")
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


# ================================================================== 시험지 첨삭
# 학생이 복테·모의 시험지(풀이 과정이 적힌 것)를 사진으로 올린다 → 조교가 OMR로 틀린 문항마다 오답 유형·메모를 단다.
@bp.app_context_processor
def _paper_counts():
    """메뉴 숫자: 강사·조교는 첨삭 기다리는 시험지 수."""
    u = g.get("user")
    if u is None or u["role"] not in ("teacher", "assistant"):
        return {}
    return {"paper_wait": query("SELECT COUNT(*) AS n FROM exam_papers WHERE status = 'submitted'", one=True)["n"]}


def paper_of(mid, student_id):
    """(시험지 행, 사진 id 목록, {문항: 첨삭})"""
    p = query("SELECT * FROM exam_papers WHERE mock_id = ? AND student_id = ?", (mid, student_id), one=True)
    if not p:
        return None, [], {}
    files = [r["file_id"] for r in query("SELECT file_id FROM exam_paper_files WHERE paper_id = ? ORDER BY pos", (p["id"],))]
    marks = {r["item_no"]: dict(r) for r in query("SELECT * FROM exam_paper_marks WHERE paper_id = ?", (p["id"],))}
    return dict(p, reviewer=_staff_name(p["reviewed_by"])), files, marks


@bp.route("/s/analysis/<int:mid>/paper", methods=["POST"])
@student_required
def s_paper(mid):
    """내 결과가 올라온 회차에만 올릴 수 있다. 첨삭 전에는 다시 올리면 사진이 바뀐다."""
    me = _me()
    if not query("SELECT 1 FROM exam_results WHERE mock_id = ? AND student_id = ?", (mid, me["id"]), one=True):
        abort(404)
    p = query("SELECT * FROM exam_papers WHERE mock_id = ? AND student_id = ?", (mid, me["id"]), one=True)
    back = url_for("books.analysis_home", mock=mid) + "#paper"
    kind = query("SELECT b.kind FROM mocks m JOIN books b ON b.id = m.book_id WHERE m.id = ?", (mid,), one=True)
    if not p and (not kind or kind["kind"] != "복습 테스트"):        # 시험지 첨삭은 복습 테스트만 (모의고사는 1:1 피드백)
        flash("모의고사는 Full 모의고사 피드백으로 요청해 주세요.", "error")
        return redirect(url_for("books.analysis_home", mock=mid) + "#feedback")
    if p and p["status"] == "done":
        flash("첨삭이 끝난 시험지는 다시 올릴 수 없어요.", "error")
        return redirect(back)
    try:
        photos = _photos("image", MAX_PAPER_PHOTOS)
        if not photos:
            raise ValueError("시험지 사진을 1장 이상 올려 주세요.")
    except ValueError as e:
        flash(str(e), "error")
        return redirect(back)
    note = request.form.get("note", "").strip()[:1000]
    if p:
        old = [r["file_id"] for r in query("SELECT file_id FROM exam_paper_files WHERE paper_id = ?", (p["id"],))]
        execute("DELETE FROM exam_paper_files WHERE paper_id = ?", (p["id"],))
        for fid in old:
            delete_file(fid)
        execute("UPDATE exam_papers SET note = ?, submitted_at = datetime('now', 'localtime') WHERE id = ?", (note, p["id"]))
        pid = p["id"]
    else:
        pid = execute("INSERT INTO exam_papers (mock_id, student_id, note) VALUES (?, ?, ?)", (mid, me["id"], note))
    for pos, fid in enumerate(photos, start=1):
        execute("INSERT INTO exam_paper_files (paper_id, file_id, pos) VALUES (?, ?, ?)", (pid, fid, pos))
    audit("paper_submit", f"mock:{mid}")
    flash("시험지를 올렸어요.", "ok")
    return redirect(back)


@bp.route("/t/papers")
@staff_required
def t_papers():
    status = "done" if request.args.get("status") == "done" else "submitted"
    rows = query(f"""SELECT p.*, st.name, st.student_no, c.name AS cls, b.title AS book_title, m.round_no, r.score, m.full_score,
                            (SELECT COUNT(*) FROM exam_paper_files f WHERE f.paper_id = p.id) AS n_files
                     FROM exam_papers p JOIN students st ON st.id = p.student_id JOIN classes c ON c.id = st.class_id
                     JOIN mocks m ON m.id = p.mock_id JOIN books b ON b.id = m.book_id
                     LEFT JOIN exam_results r ON r.mock_id = p.mock_id AND r.student_id = p.student_id
                     WHERE p.status = ? ORDER BY p.submitted_at {'ASC' if status == 'submitted' else 'DESC'} LIMIT 300""", (status,))
    counts = {r["status"]: r["n"] for r in query("SELECT status, COUNT(*) AS n FROM exam_papers GROUP BY status")}
    import analysis
    return render_template("care/t_papers.html", rows=rows, status=status, counts=counts, fmt=analysis._fmt)


@bp.route("/t/papers/<int:pid>", methods=["GET", "POST"])
@staff_required
def t_paper(pid):
    import exams
    p = query("""SELECT p.*, st.name, st.student_no, c.name AS cls FROM exam_papers p
                 JOIN students st ON st.id = p.student_id JOIN classes c ON c.id = st.class_id WHERE p.id = ?""", (pid,), one=True) or abort(404)
    rep = exams.student_report(p["mock_id"], p["student_id"])
    if rep is None:
        abort(404)
    n = rep["mock"]["n_items"]
    if request.method == "POST":
        execute("DELETE FROM exam_paper_marks WHERE paper_id = ?", (pid,))
        for i in range(1, n + 1):
            reason = request.form.get(f"r{i}", "")
            reason = reason if reason in ERR_TYPES else ""
            memo = request.form.get(f"m{i}", "").strip()[:500]
            if reason or memo:
                execute("INSERT INTO exam_paper_marks (paper_id, item_no, reason, memo) VALUES (?, ?, ?, ?)", (pid, i, reason, memo))
        execute("""UPDATE exam_papers SET status = 'done', comment = ?, reviewed_by = ?, reviewed_at = datetime('now', 'localtime')
                   WHERE id = ?""", (request.form.get("comment", "").strip()[:1500], g.user["id"], pid))
        audit("paper_review", f"paper:{pid}")
        from views.pwa import notify_student
        notify_student(p["student_id"], "복습 테스트 첨삭 완료", exams.exam_title(rep["mock"]),
                       url_for("books.analysis_home", mock=p["mock_id"]) + "#paper")
        flash(f"{p['name']} 학생 복습 테스트 첨삭을 저장했어요.", "ok")
        nxt = query("SELECT id FROM exam_papers WHERE status = 'submitted' AND id != ? ORDER BY submitted_at LIMIT 1", (pid,), one=True)
        return redirect(url_for("care.t_paper", pid=nxt["id"]) if nxt else url_for("care.t_papers"))
    _, files, marks = paper_of(p["mock_id"], p["student_id"])
    fb = query("""SELECT t.id, t.status FROM feedback_threads t JOIN users u ON u.id = t.user_id
                  WHERE t.mock_id = ? AND u.student_id = ?""", (p["mock_id"], p["student_id"]), one=True)
    return render_template("care/t_paper.html", fb=fb, p=p, rep=rep, files=files, marks=marks, err_types=ERR_TYPES,
                           title=exams.exam_title(rep["mock"]), reviewer=_staff_name(p["reviewed_by"]), pct1=exams.pct1)


def paper_review_counts(month):
    """{조교 id: 그 달 시험지 첨삭 건수} — 월급 산정 표에 쓴다."""
    return {r["u"]: r["n"] for r in query("""SELECT reviewed_by AS u, COUNT(*) AS n FROM exam_papers
                                             WHERE status = 'done' AND strftime('%Y-%m', reviewed_at) = ? GROUP BY reviewed_by""", (month,))}


# ================================================================== 수업 기록
@bp.route("/s/lessons")
@student_required
def s_lessons():
    me = _me()
    rows = [dict(r, files=[x["file_id"] for x in query("SELECT file_id FROM lesson_files WHERE lesson_id = ? ORDER BY pos", (r["id"],))])
            for r in query("SELECT * FROM lessons WHERE class_id = ? ORDER BY day DESC, id DESC LIMIT 60", (me["class_id"],))]
    week_ago = (date.today() - timedelta(days=3)).isoformat()
    # 그 수업 날부터 6일 안에 올라온 강의 영상 (결석생이 놓친 주차 영상을 바로 찾게)
    vids = query("""SELECT id, title, url, created_at FROM videos WHERE class_id = ?
                    AND (expires_on IS NULL OR expires_on = '' OR expires_on >= date('now', 'localtime'))""", (me["class_id"],))
    for r in rows:
        end = (date.fromisoformat(r["day"]) + timedelta(days=6)).isoformat()
        r["videos"] = [v for v in vids if r["day"] <= v["created_at"][:10] <= end]
    return render_template("care/s_lessons.html", me=me, rows=rows, new_since=week_ago)


@bp.route("/t/lessons/<int:lid>")
@staff_required
def t_lesson(lid):
    """올린 수업 기록 한 건 (목록의 주제에서 온다)."""
    l = query("SELECT l.*, c.name AS cls FROM lessons l JOIN classes c ON c.id = l.class_id WHERE l.id = ?", (lid,), one=True)
    if l is None:
        abort(404)
    files = [x["file_id"] for x in query("SELECT file_id FROM lesson_files WHERE lesson_id = ? ORDER BY pos", (lid,))]
    return render_template("care/t_lesson.html", l=l, files=files)


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
        if not photos and not request.form.get("body", "").strip():       # 빈 기록이 '0장'으로 쌓이지 않게
            flash("노트 사진 또는 한 줄 정리를 넣어 주세요.", "error")
            return redirect(url_for("care.t_lessons", c=cid))
        lid = execute("INSERT INTO lessons (class_id, day, title, body, created_by) VALUES (?, ?, ?, ?, ?)",
                      (cid, day, title, request.form.get("body", "").strip()[:2000], g.user["id"]))
        for pos, fid in enumerate(photos, start=1):
            execute("INSERT INTO lesson_files (lesson_id, file_id, pos) VALUES (?, ?, ?)", (lid, fid, pos))
        audit("lesson_create", f"lesson:{lid}")
        from views.pwa import notify_users
        uids = [r["id"] for r in query("SELECT u.id FROM users u JOIN students s ON s.id = u.student_id WHERE s.class_id = ? AND s.active = 1", (cid,))]
        if uids:
            notify_users(uids, "수업 기록", f"{title}, 노트 {len(photos)}장" if photos else title, url_for("care.s_lessons"))
        flash("수업 기록을 올렸어요.", "ok")
        return redirect(url_for("care.t_lessons", c=cid))
    rows = query("""SELECT l.*, c.name AS cls, (SELECT COUNT(*) FROM lesson_files f WHERE f.lesson_id = l.id) AS n_files
                    FROM lessons l JOIN classes c ON c.id = l.class_id ORDER BY l.day DESC, l.id DESC LIMIT 200""")
    classes = query("SELECT id, name FROM classes WHERE archived = 0 ORDER BY is_test, name")
    return render_template("care/t_lessons.html", rows=rows, classes=classes, today=date.today().isoformat(),
                           last_cid=request.args.get("c", type=int))      # 방금 올린 반을 그대로 골라 둔다


@bp.route("/t/lessons/<int:lid>/delete", methods=["POST"])
@staff_required
def t_lesson_delete(lid):
    for r in query("SELECT file_id FROM lesson_files WHERE lesson_id = ?", (lid,)):
        delete_file(r["file_id"])
    execute("DELETE FROM lessons WHERE id = ?", (lid,))
    flash("수업 기록을 지웠어요.", "ok")
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


def parent_report(student_id, limit=6):
    import exams
    import sysdata
    s = query("SELECT s.*, c.name AS cls FROM students s JOIN classes c ON c.id = s.class_id WHERE s.id = ?", (student_id,), one=True)
    rows = query("""SELECT r.mock_id FROM exam_results r JOIN mocks m ON m.id = r.mock_id JOIN books b ON b.id = m.book_id
                    WHERE r.student_id = ? AND m.n_items > 0 AND b.is_practice = 0
                    ORDER BY m.exam_date DESC, r.updated_at DESC LIMIT ?""", (student_id, limit))
    exams_out = []
    for r in rows:
        rep = exams.student_report(r["mock_id"], student_id)
        if not rep:
            continue
        _, _, marks = paper_of(r["mock_id"], student_id)
        whys = []
        for a in rep["wrongs"]:
            k = marks.get(a["no"], {})
            if k.get("reason") or k.get("memo") or a["type"]:
                # 번호·유형은 앞에 따로 나오니 분석 문장의 '4번은 ○○ 오류입니다(…)' 머리는 떼고 고른 선지 설명만 남긴다
                text = k.get("memo") or re.sub(r"^\d+번은 (?:\S+ )*?오류(?:입니다|로,)\s*\(?", "", a["analysis"] or "").rstrip(").")
                whys.append({"no": a["no"], "type": a["type"], "text": "" if text == f"{a['no']}번" else text})
        full = rep["mock"]["full_score"]
        exams_out.append({"title": exams.exam_title(rep["mock"]), "kind": rep["mock"].get("kind") or "", "score": rep["r"]["score"], "full": full, "avg": rep["st"]["avg"],
                          "date": rep["mock"]["exam_date"], "rate": round(100 * rep["r"]["score"] / full) if full else None,
                          "n_wrong": len(rep["wrong"]), "wrong_nos": list(rep["wrong"]), "n": rep["mock"]["n_items"], "whys": whys})
    last = exams_out[0] if exams_out else None
    prev = next((e for e in exams_out[1:] if e["kind"] == last["kind"]), None) if last else None   # 같은 종류끼리 비교
    delta = (last["rate"] - prev["rate"]) if last and prev and last["rate"] is not None and prev["rate"] is not None else None
    comment = query("""SELECT x.text, x.at, x.src, x.mock_id FROM (
                         SELECT comment AS text, reviewed_at AS at, '복습 테스트 첨삭 코멘트' AS src, mock_id FROM exam_papers
                          WHERE student_id = ? AND comment != ''
                         UNION ALL SELECT ta_note, ta_at, '회차 화면의 학생 메모', mock_id FROM exam_results
                          WHERE student_id = ? AND ta_note != '') x
                       ORDER BY x.at DESC LIMIT 1""", (student_id, student_id), one=True)
    units, weak = weak_card(student_id)
    att = sysdata.attendance(sysdata.code_of_student(student_id))
    lines = []                                                 # 요약: 숫자로만
    if last:
        lines.append(f"{last['title']} {num_fmt(last['score'])}/{num_fmt(last['full'])}점, 반 평균 {last['avg']}점이에요.")
        if delta:
            lines.append(f"득점률이 이전 {last['kind'] or '시험'}보다 {abs(delta)}%p {'올랐' if delta > 0 else '내려갔'}어요.")
    if weak:
        lines.append(f"최근 시험에서 득점률이 가장 낮은 단원은 {weak['unit']['unit']}({weak['unit']['pct']}%)예요.")
    return {"s": s, "exams": exams_out, "last": last, "delta": delta, "comment": comment, "units": units[:6], "weak": weak,
            "att": att, "lines": lines}


def num_fmt(x):
    import analysis
    return analysis._fmt(x)


def rate_chart(exams_out):
    """득점률 꺾은선 (오래된 것부터): 세로축 0~100%, 가로축 회차, 반 평균 점선, 점마다 말풍선."""
    seq = [e for e in reversed(exams_out) if e["rate"] is not None]
    W, H, L, R, T, B = 640, 250, 46, 18, 26, 44
    if not seq:
        return {"pts": []}
    pw, ph = W - L - R, H - T - B
    x = lambda i: L + pw * (i + 0.5) / len(seq)
    y = lambda v: T + ph * (1 - v / 100)
    pts = []
    mixed = len({e.get("kind") for e in seq}) > 1               # 학부모 리포트처럼 복테·모의고사가 섞이면 종류를 붙인다
    for i, e in enumerate(seq):
        avg = round(100 * e["avg"] / e["full"]) if e.get("avg") is not None and e["full"] else None
        m = re.search(r"(\d+)회", e["title"] or "")
        tx = min(max(x(i), L + 100), W - R - 100)               # 말풍선이 그림 밖으로 나가지 않게
        pts.append({"x": round(x(i), 1), "y": round(y(e["rate"]), 1), "v": e["rate"], "avg": avg, "ay": round(y(avg), 1) if avg is not None else None,
                    "lab": (("복테 " if e.get("kind") == "복습 테스트" else "모의 ") if mixed else "") + (f"{m.group(1)}회" if m else str(i + 1)), "title": e["title"], "date": (e["date"] or "")[5:].replace("-", "."),
                    "score": e["score"], "full": e["full"], "avg_score": e.get("avg"), "tx": round(tx, 1),
                    "ty": round(y(e["rate"]) - 64 if y(e["rate"]) - 64 > 2 else y(e["rate"]) + 14, 1)})
    return {"w": W, "h": H, "l": L, "r": W - R, "t": T, "b": H - B, "pts": pts,
            "poly": " ".join(f"{p['x']},{p['y']}" for p in pts),
            "avg_poly": " ".join(f"{p['x']},{p['ay']}" for p in pts if p["ay"] is not None),
            "yticks": [{"v": v, "y": round(y(v), 1)} for v in (0, 25, 50, 75, 100)],
            "every": max(1, -(-len(pts) // 10))}                # 가로축 글자가 겹치지 않게 (점 10개 넘으면 건너뛰기)


def kind_view(exams_out, kind, n=6):
    """한 종류(복습 테스트 / 모의고사)만: 최근 n회, 맨 위 회차, 직전 같은 종류 대비 변화, 득점률 그래프."""
    ex = [e for e in exams_out if e["kind"] == kind][:n]
    last = ex[0] if ex else None
    prev = ex[1] if len(ex) > 1 else None
    delta = (last["rate"] - prev["rate"]) if last and prev and last["rate"] is not None and prev["rate"] is not None else None
    lines = []
    if last:
        lines.append(f"{last['title']} {num_fmt(last['score'])}/{num_fmt(last['full'])}점, 반 평균 {last['avg']}점이에요.")
        if delta:
            lines.append(f"득점률이 이전 {kind}보다 {abs(delta)}%p {'올랐' if delta > 0 else '내려갔'}어요.")
    return {"exams": ex, "last": last, "delta": delta, "chart": rate_chart(ex), "lines": lines}


@bp.route("/p/<token>")
def parent_page(token):
    """학부모 리포트 (로그인 없음, 비밀 링크). 검색 엔진에는 나오지 않는다(noindex)."""
    if len(token) < 16:
        abort(404)
    s = query("SELECT id FROM students WHERE parent_token = ? AND active = 1", (token,), one=True) or abort(404)
    rep = parent_report(s["id"], limit=12)
    import analysis
    kind = analysis.kind_arg(request.args.get("kind"), rep["last"]["kind"] if rep["last"] else "복습 테스트")
    kv = kind_view(rep["exams"], kind)
    kv["lines"] += [ln for ln in rep["lines"] if ln.startswith("최근 시험에서")]      # 요약도 그 종류만 (약한 단원 줄은 공통)
    counts = {k: sum(1 for e in rep["exams"] if e["kind"] == k) for k in analysis.KIND_KEYS.values()}
    resp = make_response(render_template("care/parent.html", r=rep, k=kv, kind=kind, kind_counts=counts, token=token, chart=kv["chart"], fmt=num_fmt))
    # 로그인 없는 화면이라 app.py 의 no-store 가 붙지 않는다. 성적·출결이 브라우저·프록시에 남지 않게 한다
    resp.headers["Cache-Control"] = "no-store"
    return resp


@bp.route("/t/students/<int:sid>/parent-link", methods=["POST"])
@staff_required
def t_parent_link(sid):
    if not query("SELECT 1 FROM students WHERE id = ?", (sid,), one=True):
        abort(404)
    parent_token(sid, renew=request.form.get("renew") == "1")
    audit("parent_link", f"student:{sid}")
    flash("학부모 리포트 링크를 새로 만들었어요. 이전 링크는 이제 열리지 않아요." if request.form.get("renew") == "1" else "학부모 리포트 링크를 만들었어요.", "ok")
    return redirect(url_for("teacher.student_detail", sid=sid) + "#parent")
