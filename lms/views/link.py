"""조교 시스템 ↔ 웹 연동 화면과 주소.

- /api/sync        시트(Apps Script)가 앱용 표를 보내는 곳. 열쇠(Bearer 토큰)가 맞아야 받는다.
- /api/sync/redo   학생이 웹에서 고른 '다시 풀기' 결과를 시트가 가져가는 곳.
- /t/link          강사·조교: 연동 상태, 열쇠 만들기, CSV 직접 올리기, 시트에 붙일 코드.
- /s/link          가입 전부터 있던 학생 계정을 학생코드와 잇기.
- /s/attendance    내 출결.
"""
from flask import Blueprint, abort, flash, g, jsonify, redirect, render_template, request, url_for

import sysdata
from db import execute, normalize_student_code, query
from security import audit, staff_required, student_required, teacher_required

api = Blueprint("link_api", __name__)
bp = Blueprint("link", __name__)

MAX_ROWS = 60000           # 한 번에 받는 줄 수 (반 2개 × 100명 × 한 해치 기록이면 충분)


@api.route("/api/sync", methods=["POST"])
def sync():
    if not sysdata.token_ok(request.headers.get("Authorization")):
        return jsonify(ok=False, error="열쇠(토큰)가 맞지 않아요."), 401
    body = request.get_json(silent=True) or {}
    tables = body.get("tables")
    if not isinstance(tables, dict) or not tables:
        return jsonify(ok=False, error="tables 가 비어 있어요."), 400
    if sum(len(v) for v in tables.values() if isinstance(v, list)) > MAX_ROWS:
        return jsonify(ok=False, error="한 번에 보내는 줄이 너무 많아요. 표를 나눠 보내 주세요."), 413
    done, unknown, codes = sysdata.store(tables, "시트 자동 연동")
    audit("sys_sync", ",".join(f"{k}:{v}" for k, v in done.items()), username="sheet")
    return jsonify(ok=True, saved=done, unknown=unknown, codes=codes, at=sysdata.now_kst())


@api.route("/api/sync/redo")
def sync_redo():
    if not sysdata.token_ok(request.headers.get("Authorization")):
        return jsonify(ok=False, error="열쇠(토큰)가 맞지 않아요."), 401
    rows = [["학생코드", "시험명", "문항번호", "다시풀기", "기록시각"]] + \
           [[r["code"], r["exam"], r["item_no"], r["result"], r["at"]] for r in query("SELECT * FROM sys_redo ORDER BY at")]
    return jsonify(ok=True, rows=rows)


# ---------------------------------------------------------------- 강사·조교 화면
def _page(**extra):
    linked = query("""SELECT COUNT(DISTINCT sc.code) AS n FROM student_codes sc JOIN sys_rows r ON r.code = sc.code
                      WHERE sc.student_id IS NOT NULL""", one=True)["n"]
    with_data = query("SELECT COUNT(DISTINCT code) AS n FROM sys_rows WHERE tbl != '코드'", one=True)["n"]
    return render_template("teacher/link.html", tables=sysdata.synced_summary(), token_at=sysdata.token_info(),
                           linked=linked, with_data=with_data, base=request.url_root.rstrip("/"),
                           redo_n=query("SELECT COUNT(*) AS n FROM sys_redo", one=True)["n"], **extra)


@bp.route("/t/link")
@staff_required
def t_link():
    return _page()


@bp.route("/t/link/token", methods=["POST"])
@teacher_required
def t_link_token():
    token = sysdata.new_token()
    audit("sys_token_new")
    flash("새 열쇠를 만들었어요. 이 화면을 벗어나면 다시 볼 수 없으니 지금 시트에 붙여 넣으세요. 이전 열쇠는 더 이상 쓸 수 없어요.", "ok")
    return _page(new_token=token)


@bp.route("/t/link/upload", methods=["POST"])
@staff_required
def t_link_upload():
    files = [f for f in request.files.getlist("files") if f and f.filename]
    if not files:
        flash("올릴 CSV 파일을 골라 주세요.", "error")
        return redirect(url_for("link.t_link"))
    tables, skipped = {}, []
    for f in files:
        try:
            grid = sysdata.parse_csv(f.read())
        except ValueError as e:
            skipped.append(f"{f.filename}: {e}")
            continue
        if not grid:
            skipped.append(f"{f.filename}: 빈 파일")
            continue
        key = sysdata.table_key(f.filename) or sysdata.guess_table([h.strip() for h in grid[0]])
        if key is None:
            skipped.append(f"{f.filename}: 어떤 표인지 알 수 없어요 (파일 이름이나 머리글을 확인해 주세요)")
            continue
        tables[key] = grid
    done, _, codes = sysdata.store(tables, f"CSV 직접 올림 ({g.user['username']})")
    audit("sys_upload", ",".join(f"{k}:{v}" for k, v in done.items()))
    if done:
        flash("반영했어요: " + ", ".join(f"{k} {v}줄" for k, v in done.items()), "ok")
    if codes and codes["no_class"]:
        flash("웹에 없는 반 이름이라 가입 코드로 넣지 못했어요: " + ", ".join(codes["no_class"]) + ". 반 이름을 시트와 똑같이 맞춰 주세요.", "error")
    for s in skipped:
        flash(s, "error")
    return redirect(url_for("link.t_link"))


# ---------------------------------------------------------------- 학생
@bp.route("/s/link", methods=["POST"])
@student_required
def s_link():
    """이미 가입한 학생이 학생코드를 넣어 시스템 기록과 잇는다 (코드는 한 사람만 쓸 수 있다)."""
    sid = g.user["student_id"]
    if sysdata.code_of_student(sid):
        flash("이미 학생코드가 연결되어 있어요.", "ok")
        return redirect(request.referrer or url_for("student.scores"))
    code = normalize_student_code(request.form.get("code", ""))
    me = query("SELECT class_id FROM students WHERE id = ?", (sid,), one=True)
    sc = query("SELECT * FROM student_codes WHERE code = ?", (code,), one=True) if code else None
    if sc is None or sc["student_id"]:
        audit("sys_link_failed", f"code:{code[:4]}")
        flash("학생코드가 맞지 않거나 이미 쓰인 코드예요. 조교 선생님께 확인해 주세요.", "error")
    elif sc["class_id"] != me["class_id"]:
        flash("다른 반의 학생코드예요. 조교 선생님께 확인해 주세요.", "error")
    else:
        execute("UPDATE student_codes SET student_id = ?, used_at = datetime('now', 'localtime') WHERE id = ?", (sid, sc["id"]))
        audit("sys_link", f"student:{sid}")
        flash("학생코드를 연결했어요. 이제 시험 결과와 오답 분석이 보여요.", "ok")
    return redirect(request.referrer or url_for("student.scores"))


@bp.route("/s/redo", methods=["POST"])
@student_required
def s_redo():
    code = sysdata.code_of_student(g.user["student_id"])
    exam, no, result = request.form.get("exam", ""), request.form.get("no", type=int), request.form.get("result", "")
    if not code or result not in ("맞힘", "또 틀림", "") or not no:
        abort(400)
    if not any(i["no"] == no for gr in sysdata.wrong_notes(code) if gr["exam"] == exam for i in gr["items"]):
        abort(404)
    if result:
        execute("""INSERT INTO sys_redo (code, exam, item_no, result, at) VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(code, exam, item_no) DO UPDATE SET result = excluded.result, at = excluded.at""",
                (code, exam, no, result, sysdata.now_kst()))
    else:
        execute("DELETE FROM sys_redo WHERE code = ? AND exam = ? AND item_no = ?", (code, exam, no))
    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify(ok=True)
    return redirect(url_for("study.wrong_notes") + "#sys")


@bp.route("/s/attendance")
@student_required
def s_attendance():
    code = sysdata.code_of_student(g.user["student_id"])
    rows = sysdata.attendance(code)
    count = {}
    for r in rows:
        count[r["status"] or "미확인"] = count.get(r["status"] or "미확인", 0) + 1
    return render_template("student/attendance.html", code=code, rows=rows, count=count)
