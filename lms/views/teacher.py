"""강사 화면: 반, 학생, 시험/성적, 학습 메모, 질문답변, 공지, 자료."""
import csv
import io
import math
import re
from datetime import date

from flask import (Blueprint, Response, abort, flash, g, redirect, render_template, request,
                   url_for)

from content import NOTICE_TAGS, QUESTION_TYPES, VIDEO_HOSTS, validate_https_url
from db import execute, get_db, join_code_taken, new_join_code, nickname_taken, query
from engagement import streak_info
from nickname import generate_nickname
from views.student import question_thread
from security import (audit, decrypt, delete_file, encrypt, generate_temp_password,
                      hash_password, save_upload, staff_required, teacher_required)

bp = Blueprint("teacher", __name__, url_prefix="/t")

PAGE_SIZE = 50
MATERIAL_EXTS = {"pdf", "pptx", "ppt", "docx", "hwp", "png", "jpg", "jpeg"}
NOTE_CATEGORIES = ["학습", "상담", "성적", "생활", "기타"]


# ---------- 공통 헬퍼 ----------

def _get_class(cid):
    row = query("SELECT * FROM classes WHERE id = ?", (cid,), one=True)
    if row is None:
        abort(404)
    return row


def _get_student(sid):
    row = query("""SELECT s.*, c.name AS class_name FROM students s
                   JOIN classes c ON c.id = s.class_id WHERE s.id = ?""", (sid,), one=True)
    if row is None:
        abort(404)
    return row


def _text(name, max_len=200, required=True):
    value = request.form.get(name, "").strip()
    if required and not value:
        raise ValueError("필수 항목을 입력하세요.")
    if len(value) > max_len:
        raise ValueError(f"입력이 너무 깁니다. (최대 {max_len}자)")
    return value


def _page():
    try:
        return max(1, int(request.args.get("page", 1)))
    except ValueError:
        return 1


def _csv_cell(value):
    # 엑셀 수식 주입(CSV injection) 방지
    s = "" if value is None else str(value)
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


def _csv_response(filename, header, rows):
    buf = io.StringIO()
    buf.write("﻿")  # 엑셀에서 한글이 깨지지 않도록 BOM
    writer = csv.writer(buf)
    writer.writerow(header)
    for r in rows:
        writer.writerow([_csv_cell(v) for v in r])
    return Response(buf.getvalue(), mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
                             "Cache-Control": "no-store"})


def _score_chart(points):
    """성적 추이(백분율)를 인라인 SVG 용 좌표로 변환."""
    if not points:
        return None
    w, h, pad = 600, 160, 24
    n = len(points)
    coords = []
    for i, p in enumerate(points):
        x = pad + (w - 2 * pad) * (i / (n - 1) if n > 1 else 0.5)
        y = pad + (h - 2 * pad) * (1 - p["pct"] / 100)
        coords.append({"x": round(x, 1), "y": round(y, 1), **p})
    return {"w": w, "h": h, "pad": pad, "coords": coords,
            "polyline": " ".join(f"{c['x']},{c['y']}" for c in coords)}


# ---------- 대시보드 ----------

@bp.route("/")
@teacher_required
def dashboard():
    stats = query("""SELECT
        (SELECT COUNT(*) FROM classes WHERE archived = 0) AS classes,
        (SELECT COUNT(*) FROM students s JOIN classes c ON c.id = s.class_id
           WHERE s.active = 1 AND c.archived = 0) AS students,
        (SELECT COUNT(*) FROM questions WHERE status = 'open') AS open_questions,
        (SELECT COUNT(*) FROM exams) AS exams""", one=True)
    classes = query("""SELECT c.*, COUNT(s.id) AS student_count FROM classes c
                       LEFT JOIN students s ON s.class_id = c.id AND s.active = 1
                       WHERE c.archived = 0 GROUP BY c.id ORDER BY c.name""")
    open_questions = query("""SELECT q.id, q.title, q.created_at, s.name, c.name AS class_name
                              FROM questions q JOIN students s ON s.id = q.student_id
                              JOIN classes c ON c.id = s.class_id
                              WHERE q.status = 'open' ORDER BY q.created_at LIMIT 10""")
    recent_exams = query("""SELECT e.*, c.name AS class_name,
                              (SELECT ROUND(AVG(score), 1) FROM scores WHERE exam_id = e.id) AS avg,
                              (SELECT COUNT(*) FROM scores WHERE exam_id = e.id) AS n
                            FROM exams e JOIN classes c ON c.id = e.class_id
                            ORDER BY e.exam_date DESC, e.id DESC LIMIT 8""")
    return render_template("teacher/dashboard.html", stats=stats, classes=classes,
                           open_questions=open_questions, recent_exams=recent_exams)


# ---------- 반 ----------

@bp.route("/classes", methods=["GET", "POST"])
@teacher_required
def classes():
    if request.method == "POST":
        try:
            name = _text("name", 60)
            desc = _text("description", 300, required=False)
        except ValueError as e:
            flash(str(e), "error")
        else:
            cid = execute("INSERT INTO classes (name, description, join_code) VALUES (?, ?, ?)",
                          (name, desc, new_join_code(join_code_taken)))
            audit("class_create", f"class:{cid}")
            flash(f"'{name}' 반을 만들었습니다.", "ok")
            return redirect(url_for("teacher.class_detail", cid=cid))
    show_archived = request.args.get("archived") == "1"
    rows = query("""SELECT c.*, COUNT(s.id) AS student_count FROM classes c
                    LEFT JOIN students s ON s.class_id = c.id AND s.active = 1
                    WHERE c.archived = ? GROUP BY c.id ORDER BY c.name""", (int(show_archived),))
    return render_template("teacher/classes.html", classes=rows, show_archived=show_archived)


@bp.route("/classes/<int:cid>")
@teacher_required
def class_detail(cid):
    cls = _get_class(cid)
    tab = request.args.get("tab", "students")
    ctx = {"cls": cls, "tab": tab}
    if tab == "students":
        q = request.args.get("q", "").strip()
        page = _page()
        where, args = "s.class_id = ?", [cid]
        if q:
            where += " AND (s.name LIKE ? OR s.student_no LIKE ?)"
            args += [f"%{q}%", f"%{q}%"]
        total = query(f"SELECT COUNT(*) AS n FROM students s WHERE {where}", args, one=True)["n"]
        ctx["students"] = query(f"""
            SELECT s.id, s.name, s.student_no, s.target, s.active,
                   u.id AS account_id, u.last_login_at,
                   (SELECT ROUND(AVG(sc.score * 100.0 / e.max_score), 1) FROM scores sc
                      JOIN exams e ON e.id = sc.exam_id WHERE sc.student_id = s.id) AS avg_pct,
                   (SELECT COUNT(*) FROM questions WHERE student_id = s.id AND status = 'open') AS open_q
            FROM students s LEFT JOIN users u ON u.student_id = s.id
            WHERE {where} ORDER BY s.active DESC, s.name LIMIT ? OFFSET ?""",
            args + [PAGE_SIZE, (page - 1) * PAGE_SIZE])
        ctx.update(q=q, page=page, pages=max(1, math.ceil(total / PAGE_SIZE)), total=total)
    elif tab == "exams":
        ctx["exams"] = query("""SELECT e.*, COUNT(sc.id) AS n, ROUND(AVG(sc.score), 1) AS avg,
                                       MAX(sc.score) AS max, MIN(sc.score) AS min
                                FROM exams e LEFT JOIN scores sc ON sc.exam_id = e.id
                                WHERE e.class_id = ? GROUP BY e.id
                                ORDER BY e.exam_date DESC, e.id DESC""", (cid,))
        ctx["today"] = date.today().isoformat()
    elif tab == "notices":
        ctx["notices"] = query("""SELECT n.*, (SELECT COUNT(*) FROM notice_likes l WHERE l.notice_id = n.id) AS likes
                                  FROM notices n WHERE n.class_id = ? ORDER BY n.pinned DESC, n.created_at DESC""",
                               (cid,))
        ctx["tags"] = NOTICE_TAGS
    elif tab == "videos":
        ctx["videos"] = query("SELECT * FROM videos WHERE class_id = ? ORDER BY created_at DESC", (cid,))
        ctx["today"] = date.today().isoformat()
    elif tab == "materials":
        ctx["materials"] = query("""SELECT m.*, f.original_name, f.size FROM materials m
                                    JOIN files f ON f.id = m.file_id
                                    WHERE m.class_id = ? ORDER BY m.created_at DESC""", (cid,))
    else:
        abort(404)
    return render_template("teacher/class_detail.html", **ctx)


@bp.route("/classes/<int:cid>/edit", methods=["POST"])
@teacher_required
def class_edit(cid):
    _get_class(cid)
    try:
        name = _text("name", 60)
        desc = _text("description", 300, required=False)
    except ValueError as e:
        flash(str(e), "error")
    else:
        archived = 1 if request.form.get("archived") == "1" else 0
        execute("UPDATE classes SET name = ?, description = ?, archived = ? WHERE id = ?",
                (name, desc, archived, cid))
        audit("class_edit", f"class:{cid}")
        flash("반 정보를 저장했습니다.", "ok")
    return redirect(url_for("teacher.class_detail", cid=cid, tab="students"))


# ---------- 학생 ----------

def _student_fields():
    return {
        "name": _text("name", 40),
        "student_no": _text("student_no", 30),
        "target": _text("target", 60, required=False),
        "phone": _text("phone", 30, required=False),
        "memo": _text("memo", 1000, required=False),
    }


@bp.route("/classes/<int:cid>/students", methods=["POST"])
@teacher_required
def student_create(cid):
    _get_class(cid)
    try:
        f = _student_fields()
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("teacher.class_detail", cid=cid))
    if query("SELECT 1 FROM students WHERE student_no = ?", (f["student_no"],), one=True):
        flash("이미 등록된 수험번호입니다.", "error")
        return redirect(url_for("teacher.class_detail", cid=cid))
    sid = execute("""INSERT INTO students (class_id, name, student_no, target, phone_enc, memo_enc)
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  (cid, f["name"], f["student_no"], f["target"], encrypt(f["phone"]), encrypt(f["memo"])))
    audit("student_create", f"student:{sid}")
    flash(f"{f['name']} 학생을 등록했습니다.", "ok")
    return redirect(url_for("teacher.class_detail", cid=cid))


@bp.route("/classes/<int:cid>/import", methods=["POST"])
@teacher_required
def student_import(cid):
    """CSV 일괄 등록. 헤더: 이름,수험번호,연락처,목표,메모 (연락처 이후는 선택)"""
    _get_class(cid)
    upload = request.files.get("csv")
    if not upload or not upload.filename.lower().endswith(".csv"):
        flash("CSV 파일을 선택하세요.", "error")
        return redirect(url_for("teacher.class_detail", cid=cid))
    raw = upload.read(5 * 1024 * 1024 + 1)
    if len(raw) > 5 * 1024 * 1024:
        flash("CSV 파일이 너무 큽니다. (최대 5MB)", "error")
        return redirect(url_for("teacher.class_detail", cid=cid))
    for enc in ("utf-8-sig", "cp949"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        flash("파일 인코딩을 읽을 수 없습니다. UTF-8 또는 CP949(엑셀 기본)로 저장하세요.", "error")
        return redirect(url_for("teacher.class_detail", cid=cid))

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or "이름" not in reader.fieldnames or "수험번호" not in reader.fieldnames:
        flash("첫 줄에 '이름,수험번호' 열 제목이 있어야 합니다.", "error")
        return redirect(url_for("teacher.class_detail", cid=cid))

    db = get_db()
    existing = {r["student_no"] for r in query("SELECT student_no FROM students")}
    added, skipped = 0, []
    for line_no, row in enumerate(reader, start=2):
        name = (row.get("이름") or "").strip()
        no = (row.get("수험번호") or "").strip()
        if not name or not no or len(name) > 40 or len(no) > 30:
            skipped.append(f"{line_no}행(형식 오류)")
            continue
        if no in existing:
            skipped.append(f"{line_no}행({no} 중복)")
            continue
        db.execute("""INSERT INTO students (class_id, name, student_no, target, phone_enc, memo_enc)
                      VALUES (?, ?, ?, ?, ?, ?)""",
                   (cid, name, no, (row.get("목표") or "").strip()[:60],
                    encrypt((row.get("연락처") or "").strip()[:30]),
                    encrypt((row.get("메모") or "").strip()[:1000])))
        existing.add(no)
        added += 1
        if added > 3000:
            break
    db.commit()
    audit("student_import", f"class:{cid} added:{added}")
    flash(f"{added}명을 등록했습니다." + (f" 건너뜀: {', '.join(skipped[:10])}" +
          (f" 외 {len(skipped) - 10}건" if len(skipped) > 10 else "") if skipped else ""),
          "ok" if added else "error")
    return redirect(url_for("teacher.class_detail", cid=cid))


@bp.route("/students")
@teacher_required
def students():
    q = request.args.get("q", "").strip()
    page = _page()
    where, args = "1 = 1", []
    if q:
        where = "(s.name LIKE ? OR s.student_no LIKE ?)"
        args = [f"%{q}%", f"%{q}%"]
    total = query(f"SELECT COUNT(*) AS n FROM students s WHERE {where}", args, one=True)["n"]
    rows = query(f"""SELECT s.id, s.name, s.student_no, s.target, s.active, c.name AS class_name
                     FROM students s JOIN classes c ON c.id = s.class_id
                     WHERE {where} ORDER BY s.name LIMIT ? OFFSET ?""",
                 args + [PAGE_SIZE, (page - 1) * PAGE_SIZE])
    return render_template("teacher/students.html", students=rows, q=q, page=page,
                           pages=max(1, math.ceil(total / PAGE_SIZE)), total=total)


@bp.route("/students/<int:sid>")
@teacher_required
def student_detail(sid):
    s = _get_student(sid)
    audit("student_view", f"student:{sid}")
    scores = query("""SELECT e.id AS exam_id, e.name, e.subject, e.exam_date, e.max_score, sc.score,
                        ROUND(sc.score * 100.0 / e.max_score, 1) AS pct,
                        (SELECT ROUND(AVG(score), 1) FROM scores WHERE exam_id = e.id) AS class_avg,
                        (SELECT COUNT(*) + 1 FROM scores x WHERE x.exam_id = e.id AND x.score > sc.score) AS rank,
                        (SELECT COUNT(*) FROM scores WHERE exam_id = e.id) AS n
                      FROM scores sc JOIN exams e ON e.id = sc.exam_id
                      WHERE sc.student_id = ? ORDER BY e.exam_date, e.id""", (sid,))
    chart = _score_chart([{"pct": r["pct"], "label": r["name"], "date": r["exam_date"]} for r in scores])
    notes = [dict(n, body=decrypt(n["body_enc"]))
             for n in query("SELECT * FROM notes WHERE student_id = ? ORDER BY created_at DESC", (sid,))]
    questions = query("SELECT * FROM questions WHERE student_id = ? ORDER BY created_at DESC LIMIT 20", (sid,))
    account = query("SELECT id, username, nickname, last_login_at, must_change_pw, locked_until FROM users WHERE student_id = ?",
                    (sid,), one=True)
    all_classes = query("SELECT id, name FROM classes WHERE archived = 0 ORDER BY name")
    engagement = None
    if account:
        engagement = {"streak": streak_info(account["id"])}
    return render_template("teacher/student_detail.html", s=s, phone=decrypt(s["phone_enc"]),
                           memo=decrypt(s["memo_enc"]), scores=scores, chart=chart, notes=notes,
                           questions=questions, account=account, all_classes=all_classes,
                           note_categories=NOTE_CATEGORIES, engagement=engagement)


@bp.route("/students/<int:sid>/edit", methods=["POST"])
@teacher_required
def student_edit(sid):
    _get_student(sid)
    try:
        f = _student_fields()
        class_id = int(request.form.get("class_id", ""))
    except ValueError as e:
        flash(str(e) if str(e) else "입력값을 확인하세요.", "error")
        return redirect(url_for("teacher.student_detail", sid=sid))
    _get_class(class_id)
    dup = query("SELECT 1 FROM students WHERE student_no = ? AND id != ?", (f["student_no"], sid), one=True)
    dup = dup or query("SELECT 1 FROM users WHERE username = ? AND (student_id IS NULL OR student_id != ?)",
                       (f["student_no"], sid), one=True)
    if dup:
        flash("이미 등록된 수험번호입니다.", "error")
        return redirect(url_for("teacher.student_detail", sid=sid))
    active = 1 if request.form.get("active") == "1" else 0
    execute("""UPDATE students SET class_id = ?, name = ?, student_no = ?, target = ?,
               phone_enc = ?, memo_enc = ?, active = ? WHERE id = ?""",
            (class_id, f["name"], f["student_no"], f["target"], encrypt(f["phone"]),
             encrypt(f["memo"]), active, sid))
    if not active:
        # 비활성(퇴원) 학생은 로그인 차단
        execute("DELETE FROM users WHERE student_id = ?", (sid,))
    else:
        # 학생 아이디는 수험번호와 같게 유지
        execute("UPDATE users SET username = ? WHERE student_id = ?", (f["student_no"], sid))
    audit("student_edit", f"student:{sid}")
    flash("학생 정보를 저장했습니다.", "ok")
    return redirect(url_for("teacher.student_detail", sid=sid))


@bp.route("/students/<int:sid>/delete", methods=["POST"])
@teacher_required
def student_delete(sid):
    s = _get_student(sid)
    if request.form.get("confirm_name", "").strip() != s["name"]:
        flash("삭제하려면 학생 이름을 정확히 입력하세요.", "error")
        return redirect(url_for("teacher.student_detail", sid=sid))
    # 개인정보 파기: 질문·추가 질문 첨부 사진까지 지운다. 기록을 지운 뒤 파일을 지워야 중간에 실패해도 기록이 깨지지 않는다
    file_ids = [r["image_id"] for r in query("""
        SELECT image_id FROM questions WHERE student_id = ? AND image_id IS NOT NULL
        UNION
        SELECT f.image_id FROM followups f JOIN questions q ON q.id = f.question_id
        WHERE q.student_id = ? AND f.image_id IS NOT NULL""", (sid, sid))]
    execute("DELETE FROM students WHERE id = ?", (sid,))
    for file_id in file_ids:
        delete_file(file_id)
    audit("student_delete", f"student:{sid} no:{s['student_no']}")
    flash(f"{s['name']} 학생과 관련 기록을 모두 삭제했습니다.", "ok")
    return redirect(url_for("teacher.class_detail", cid=s["class_id"]))


@bp.route("/students/<int:sid>/notes", methods=["POST"])
@teacher_required
def note_create(sid):
    _get_student(sid)
    try:
        body = _text("body", 3000)
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("teacher.student_detail", sid=sid))
    category = request.form.get("category", "학습")
    if category not in NOTE_CATEGORIES:
        category = "기타"
    execute("INSERT INTO notes (student_id, category, body_enc) VALUES (?, ?, ?)",
            (sid, category, encrypt(body)))
    audit("note_create", f"student:{sid}")
    return redirect(url_for("teacher.student_detail", sid=sid) + "#notes")


@bp.route("/notes/<int:nid>/delete", methods=["POST"])
@teacher_required
def note_delete(nid):
    note = query("SELECT * FROM notes WHERE id = ?", (nid,), one=True)
    if note is None:
        abort(404)
    execute("DELETE FROM notes WHERE id = ?", (nid,))
    audit("note_delete", f"student:{note['student_id']} note:{nid}")
    return redirect(url_for("teacher.student_detail", sid=note["student_id"]) + "#notes")


# ---------- 학생 계정 ----------

def _issue_account(student):
    temp = generate_temp_password()
    existing = query("SELECT id FROM users WHERE student_id = ?", (student["id"],), one=True)
    if existing:
        execute("""UPDATE users SET password_hash = ?, must_change_pw = 1, failed_attempts = 0,
                   locked_until = NULL, username = ? WHERE id = ?""",
                (hash_password(temp), student["student_no"], existing["id"]))
    else:
        if query("SELECT 1 FROM users WHERE username = ?", (student["student_no"],), one=True):
            raise ValueError(f"아이디 {student['student_no']} 가 이미 사용 중입니다.")
        # 닉네임은 가입 시 자동으로 정해진다 (질답 게시판에서 실명 대신 표시)
        execute("""INSERT INTO users (role, username, nickname, password_hash, student_id, must_change_pw)
                   VALUES ('student', ?, ?, ?, ?, 1)""",
                (student["student_no"], generate_nickname(nickname_taken), hash_password(temp), student["id"]))
    return temp


@bp.route("/students/<int:sid>/account", methods=["POST"])
@teacher_required
def student_account(sid):
    s = _get_student(sid)
    if not s["active"]:
        flash("비활성 학생에게는 계정을 발급할 수 없습니다.", "error")
        return redirect(url_for("teacher.student_detail", sid=sid))
    try:
        temp = _issue_account(s)
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("teacher.student_detail", sid=sid))
    audit("account_issue", f"student:{sid}")
    # 임시 비밀번호는 저장하지 않고 이 응답에서 한 번만 보여준다
    return render_template("teacher/temp_password.html", s=s, username=s["student_no"], temp=temp)


@bp.route("/students/<int:sid>/account/delete", methods=["POST"])
@teacher_required
def student_account_delete(sid):
    _get_student(sid)
    execute("DELETE FROM users WHERE student_id = ?", (sid,))
    audit("account_delete", f"student:{sid}")
    flash("학생 계정을 삭제했습니다. 학습 기록은 유지됩니다.", "ok")
    return redirect(url_for("teacher.student_detail", sid=sid))


@bp.route("/classes/<int:cid>/accounts", methods=["POST"])
@teacher_required
def class_accounts(cid):
    """계정이 없는 학생들에게 일괄 발급하고 임시 비밀번호 CSV 를 한 번만 내려준다."""
    cls = _get_class(cid)
    targets = query("""SELECT s.* FROM students s LEFT JOIN users u ON u.student_id = s.id
                       WHERE s.class_id = ? AND s.active = 1 AND u.id IS NULL ORDER BY s.name""", (cid,))
    if not targets:
        flash("새로 발급할 학생이 없습니다. (이미 모두 계정이 있음)", "ok")
        return redirect(url_for("teacher.class_detail", cid=cid))
    rows = []
    for s in targets:
        try:
            rows.append((s["name"], s["student_no"], _issue_account(s)))
        except ValueError:
            rows.append((s["name"], s["student_no"], "(발급 실패: 아이디 중복)"))
    audit("account_bulk_issue", f"class:{cid} count:{len(rows)}")
    return _csv_response(f"accounts_class{cls['id']}.csv", ["이름", "아이디", "임시비밀번호"], rows)


# ---------- 시험 / 성적 ----------

@bp.route("/classes/<int:cid>/exams", methods=["POST"])
@teacher_required
def exam_create(cid):
    _get_class(cid)
    try:
        name = _text("name", 80)
        subject = _text("subject", 40, required=False)
        exam_date = date.fromisoformat(request.form.get("exam_date", "")).isoformat()
        max_score = float(request.form.get("max_score", "100"))
        if not 0 < max_score <= 1000:
            raise ValueError("만점은 0보다 크고 1000 이하여야 합니다.")
    except ValueError as e:
        flash(str(e) if "입력" in str(e) or "만점" in str(e) else "입력값을 확인하세요.", "error")
        return redirect(url_for("teacher.class_detail", cid=cid, tab="exams"))
    eid = execute("INSERT INTO exams (class_id, name, subject, exam_date, max_score) VALUES (?, ?, ?, ?, ?)",
                  (cid, name, subject, exam_date, max_score))
    audit("exam_create", f"exam:{eid}")
    return redirect(url_for("teacher.exam_detail", eid=eid))


def _get_exam(eid):
    row = query("""SELECT e.*, c.name AS class_name FROM exams e JOIN classes c ON c.id = e.class_id
                   WHERE e.id = ?""", (eid,), one=True)
    if row is None:
        abort(404)
    return row


@bp.route("/exams/<int:eid>", methods=["GET", "POST"])
@teacher_required
def exam_detail(eid):
    exam = _get_exam(eid)
    students = query("""SELECT s.id, s.name, s.student_no, sc.score FROM students s
                        LEFT JOIN scores sc ON sc.student_id = s.id AND sc.exam_id = ?
                        WHERE s.class_id = ? AND s.active = 1 ORDER BY s.name""", (eid, exam["class_id"]))
    if request.method == "POST":
        db = get_db()
        errors, saved = [], 0
        for s in students:
            raw = request.form.get(f"score_{s['id']}", "").strip()
            if raw == "":
                db.execute("DELETE FROM scores WHERE exam_id = ? AND student_id = ?", (eid, s["id"]))
                continue
            try:
                val = float(raw)
                if not 0 <= val <= exam["max_score"] or math.isnan(val):
                    raise ValueError
            except ValueError:
                errors.append(s["name"])
                continue
            db.execute("""INSERT INTO scores (exam_id, student_id, score) VALUES (?, ?, ?)
                          ON CONFLICT (exam_id, student_id) DO UPDATE SET score = excluded.score""",
                       (eid, s["id"], val))
            saved += 1
        db.commit()
        audit("scores_save", f"exam:{eid} count:{saved}")
        if errors:
            flash(f"0~{exam['max_score']:g} 범위가 아닌 값은 저장하지 않았습니다: {', '.join(errors[:10])}", "error")
        else:
            flash(f"{saved}명의 점수를 저장했습니다.", "ok")
        return redirect(url_for("teacher.exam_detail", eid=eid))

    vals = sorted((s["score"] for s in students if s["score"] is not None), reverse=True)
    stats = None
    if vals:
        mean = sum(vals) / len(vals)
        sd = math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals))
        stats = {"n": len(vals), "avg": round(mean, 1), "max": vals[0], "min": vals[-1],
                 "sd": round(sd, 1), "total": len(students)}
    ranks = {v: vals.index(v) + 1 for v in set(vals)}
    return render_template("teacher/exam_detail.html", exam=exam, students=students,
                           stats=stats, ranks=ranks)


@bp.route("/exams/<int:eid>/export")
@teacher_required
def exam_export(eid):
    exam = _get_exam(eid)
    rows = query("""SELECT s.name, s.student_no, sc.score FROM students s
                    LEFT JOIN scores sc ON sc.student_id = s.id AND sc.exam_id = ?
                    WHERE s.class_id = ? AND s.active = 1 ORDER BY sc.score DESC, s.name""",
                 (eid, exam["class_id"]))
    audit("scores_export", f"exam:{eid}")
    return _csv_response(f"exam{eid}.csv", ["이름", "수험번호", f"점수(/{exam['max_score']:g})"],
                         [(r["name"], r["student_no"], "" if r["score"] is None else r["score"]) for r in rows])


@bp.route("/exams/<int:eid>/delete", methods=["POST"])
@teacher_required
def exam_delete(eid):
    exam = _get_exam(eid)
    execute("DELETE FROM exams WHERE id = ?", (eid,))
    audit("exam_delete", f"exam:{eid}")
    flash(f"'{exam['name']}' 시험과 점수를 삭제했습니다.", "ok")
    return redirect(url_for("teacher.class_detail", cid=exam["class_id"], tab="exams"))


# ---------- 질문답변 ----------

@bp.route("/questions")
@staff_required
def questions():
    status = request.args.get("status", "open")
    if status not in ("open", "answered", "all"):
        status = "open"
    page = _page()
    where, args = ("1 = 1", []) if status == "all" else ("q.status = ?", [status])
    qtype = request.args.get("qtype", "")
    if qtype in QUESTION_TYPES:
        where += " AND q.qtype = ?"
        args = args + [qtype]
    total = query(f"SELECT COUNT(*) AS n FROM questions q WHERE {where}", args, one=True)["n"]
    rows = query(f"""SELECT q.*, s.name, s.student_no, c.name AS class_name, u.nickname,
                            (SELECT COUNT(*) FROM followups WHERE question_id = q.id) AS followup_count
                     FROM questions q
                     JOIN students s ON s.id = q.student_id JOIN classes c ON c.id = s.class_id
                     LEFT JOIN users u ON u.student_id = s.id
                     WHERE {where} ORDER BY q.created_at {'ASC' if status == 'open' else 'DESC'}
                     LIMIT ? OFFSET ?""", args + [PAGE_SIZE, (page - 1) * PAGE_SIZE])
    return render_template("teacher/questions.html", questions=rows, status=status, page=page,
                           qtype=qtype, qtypes=QUESTION_TYPES, pages=max(1, math.ceil(total / PAGE_SIZE)))


@bp.route("/questions/<int:qid>", methods=["GET", "POST"])
@staff_required
def question_detail(qid):
    q = query("""SELECT q.*, s.name, s.student_no, s.id AS sid, c.name AS class_name, u.nickname FROM questions q
                 JOIN students s ON s.id = q.student_id JOIN classes c ON c.id = s.class_id
                 LEFT JOIN users u ON u.student_id = s.id
                 WHERE q.id = ?""", (qid,), one=True)
    if q is None:
        abort(404)
    if request.method == "POST":
        try:
            body = _text("body", 5000)
        except ValueError as e:
            flash(str(e), "error")
        else:
            execute("INSERT INTO answers (question_id, author_id, body) VALUES (?, ?, ?)",
                    (qid, g.user["id"], body))
            execute("UPDATE questions SET status = 'answered' WHERE id = ?", (qid,))
            audit("question_answer", f"question:{qid}")
            flash("답변을 등록했습니다.", "ok")
            from views.pwa import notify_student
            notify_student(q["sid"], "질문에 답변이 달렸어요", q["title"], url_for("student.question_detail", qid=qid))
            nxt = query("SELECT id FROM questions WHERE status = 'open' ORDER BY created_at LIMIT 1", one=True)
            if request.form.get("go_next") == "1" and nxt:
                return redirect(url_for("teacher.question_detail", qid=nxt["id"]))
            return redirect(url_for("teacher.question_detail", qid=qid))
    return render_template("teacher/question_detail.html", q=q, thread=question_thread(qid))


@bp.route("/questions/<int:qid>/reopen", methods=["POST"])
@staff_required
def question_reopen(qid):
    execute("UPDATE questions SET status = 'open' WHERE id = ?", (qid,))
    return redirect(url_for("teacher.question_detail", qid=qid))


# ---------- 공지 / 자료 ----------

@bp.route("/classes/<int:cid>/notices", methods=["POST"])
@teacher_required
def notice_create(cid):
    _get_class(cid)
    try:
        title = _text("title", 120)
        body = _text("body", 5000)
        textbook = _text("textbook", 60, required=False)
    except ValueError as e:
        flash(str(e), "error")
    else:
        tag = request.form.get("tag", "공지")
        if tag not in NOTICE_TAGS:
            tag = "공지"
        nid = execute("INSERT INTO notices (class_id, tag, textbook, title, body, pinned) VALUES (?, ?, ?, ?, ?, ?)",
                      (cid, tag, textbook, title, body, 1 if request.form.get("pinned") else 0))
        audit("notice_create", f"notice:{nid}")
        flash("공지를 등록했습니다.", "ok")
        from views.pwa import notify_class
        notify_class(cid, f"새 {tag}", title, url_for("student.notice_detail", nid=nid))
    return redirect(url_for("teacher.class_detail", cid=cid, tab="notices"))


@bp.route("/notices/<int:nid>/pin", methods=["POST"])
@teacher_required
def notice_pin(nid):
    n = query("SELECT * FROM notices WHERE id = ?", (nid,), one=True)
    if n is None:
        abort(404)
    execute("UPDATE notices SET pinned = ? WHERE id = ?", (0 if n["pinned"] else 1, nid))
    return redirect(url_for("teacher.class_detail", cid=n["class_id"], tab="notices"))


@bp.route("/notices/<int:nid>/delete", methods=["POST"])
@teacher_required
def notice_delete(nid):
    n = query("SELECT * FROM notices WHERE id = ?", (nid,), one=True)
    if n is None:
        abort(404)
    execute("DELETE FROM notices WHERE id = ?", (nid,))
    audit("notice_delete", f"notice:{nid}")
    return redirect(url_for("teacher.class_detail", cid=n["class_id"], tab="notices"))


@bp.route("/classes/<int:cid>/materials", methods=["POST"])
@teacher_required
def material_create(cid):
    _get_class(cid)
    try:
        title = _text("title", 120)
        file_id = save_upload(request.files.get("file"), MATERIAL_EXTS)
    except ValueError as e:
        flash(str(e), "error")
    else:
        mid = execute("INSERT INTO materials (class_id, title, file_id) VALUES (?, ?, ?)", (cid, title, file_id))
        audit("material_upload", f"material:{mid}")
        flash("자료를 올렸습니다.", "ok")
    return redirect(url_for("teacher.class_detail", cid=cid, tab="materials"))


@bp.route("/materials/<int:mid>/delete", methods=["POST"])
@teacher_required
def material_delete(mid):
    m = query("SELECT * FROM materials WHERE id = ?", (mid,), one=True)
    if m is None:
        abort(404)
    execute("DELETE FROM materials WHERE id = ?", (mid,))
    delete_file(m["file_id"])
    audit("material_delete", f"material:{mid}")
    return redirect(url_for("teacher.class_detail", cid=m["class_id"], tab="materials"))


# ---------- 강의 영상 (외부 링크 + 만료일) ----------

@bp.route("/classes/<int:cid>/videos", methods=["POST"])
@teacher_required
def video_create(cid):
    _get_class(cid)
    try:
        title = _text("title", 120)
        url = validate_https_url(request.form.get("url"), VIDEO_HOSTS)
        duration = _text("duration", 10, required=False)
        expires = request.form.get("expires_on", "").strip()
        expires = date.fromisoformat(expires).isoformat() if expires else None
    except ValueError as e:
        msg = str(e)
        flash(msg if any(k in msg for k in ("입력", "주소", "링크")) else "만료일 형식을 확인하세요.", "error")
    else:
        vid = execute("INSERT INTO videos (class_id, title, url, duration, expires_on) VALUES (?, ?, ?, ?, ?)",
                      (cid, title, url, duration, expires))
        audit("video_create", f"video:{vid}")
        flash("강의 영상을 등록했습니다.", "ok")
    return redirect(url_for("teacher.class_detail", cid=cid, tab="videos"))


@bp.route("/videos/<int:vid>/delete", methods=["POST"])
@teacher_required
def video_delete(vid):
    v = query("SELECT * FROM videos WHERE id = ?", (vid,), one=True)
    if v is None:
        abort(404)
    execute("DELETE FROM videos WHERE id = ?", (vid,))
    audit("video_delete", f"video:{vid}")
    return redirect(url_for("teacher.class_detail", cid=v["class_id"], tab="videos"))


# ---------- 조교 계정 ----------

_USERNAME = re.compile(r"^[A-Za-z0-9_.-]{3,30}$")


def _get_assistant(uid):
    row = query("SELECT * FROM users WHERE id = ? AND role = 'assistant'", (uid,), one=True)
    if row is None:
        abort(404)
    return row


@bp.route("/staff", methods=["GET", "POST"])
@teacher_required
def staff():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        try:
            display_name = _text("display_name", 20)
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("teacher.staff"))
        if not _USERNAME.match(username):
            flash("아이디는 영문·숫자·_ . - 로 3~30자입니다. (예: ta_kim)", "error")
        elif query("SELECT 1 FROM users WHERE username = ?", (username,), one=True) or                 query("SELECT 1 FROM students WHERE student_no = ?", (username,), one=True):
            flash("이미 쓰이고 있는 아이디입니다. (학생 수험번호와도 겹치면 안 됩니다)", "error")
        else:
            temp = generate_temp_password()
            uid = execute("""INSERT INTO users (role, username, display_name, password_hash, must_change_pw)
                             VALUES ('assistant', ?, ?, ?, 1)""", (username, display_name, hash_password(temp)))
            audit("assistant_create", f"user:{uid}")
            return render_template("teacher/staff_password.html", username=username, display_name=display_name,
                                   temp=temp)
    rows = query("""SELECT u.*, (SELECT COUNT(*) FROM answers WHERE author_id = u.id) AS answer_count
                    FROM users u WHERE role = 'assistant' ORDER BY disabled, display_name""")
    return render_template("teacher/staff.html", staff=rows)


@bp.route("/staff/<int:uid>/reset", methods=["POST"])
@teacher_required
def staff_reset(uid):
    a = _get_assistant(uid)
    temp = generate_temp_password()
    execute("""UPDATE users SET password_hash = ?, must_change_pw = 1, failed_attempts = 0, locked_until = NULL
               WHERE id = ?""", (hash_password(temp), uid))
    audit("assistant_reset", f"user:{uid}")
    return render_template("teacher/staff_password.html", username=a["username"], display_name=a["display_name"],
                           temp=temp)


@bp.route("/staff/<int:uid>/toggle", methods=["POST"])
@teacher_required
def staff_toggle(uid):
    a = _get_assistant(uid)
    disabled = 0 if a["disabled"] else 1
    execute("UPDATE users SET disabled = ? WHERE id = ?", (disabled, uid))
    audit("assistant_disable" if disabled else "assistant_enable", f"user:{uid}")
    flash(f"{a['display_name']} 조교 계정을 {'사용 중지' if disabled else '다시 사용'}했습니다.", "ok")
    return redirect(url_for("teacher.staff"))


# ---------- 학생 회원가입 승인 ----------

@bp.app_context_processor
def _pending_signups():
    user = g.get("user")
    if user is None or user["role"] != "teacher":
        return {}
    return {"pending_signups": query("SELECT COUNT(*) AS n FROM signup_requests", one=True)["n"]}


@bp.route("/classes/<int:cid>/joincode", methods=["POST"])
@teacher_required
def class_joincode(cid):
    _get_class(cid)
    action = request.form.get("action")
    if action == "regen":
        execute("UPDATE classes SET join_code = ? WHERE id = ?", (new_join_code(join_code_taken), cid))
        flash("새 가입 코드를 만들었습니다. 예전 코드는 더 이상 쓸 수 없어요.", "ok")
    elif action in ("open", "close"):
        execute("UPDATE classes SET join_open = ? WHERE id = ?", (1 if action == "open" else 0, cid))
        flash("가입을 받습니다." if action == "open" else "가입 받기를 멈췄습니다.", "ok")
    audit("joincode_" + (action or "unknown"), f"class:{cid}")
    return redirect(url_for("teacher.class_detail", cid=cid))


def _approve(req):
    """가입 신청 1건 승인. 성공하면 None, 실패하면 사유 문자열."""
    if query("SELECT 1 FROM users WHERE username = ?", (req["student_no"],), one=True):
        return f"{req['name']}({req['student_no']}): 이미 같은 아이디의 계정이 있습니다."
    if req["google_sub"] and query("SELECT 1 FROM users WHERE google_sub = ?", (req["google_sub"],), one=True):
        return f"{req['name']}({req['student_no']}): 이 Google 계정은 이미 다른 계정에 연결되어 있습니다."
    student = query("SELECT * FROM students WHERE student_no = ?", (req["student_no"],), one=True)
    if student is None:
        sid = execute("INSERT INTO students (class_id, name, student_no) VALUES (?, ?, ?)",
                      (req["class_id"], req["name"], req["student_no"]))
    elif not student["active"]:
        return f"{req['name']}({req['student_no']}): 퇴원 처리된 학생입니다. 학생 정보에서 재원으로 바꾼 뒤 승인하세요."
    else:
        sid = student["id"]  # 선생님이 미리 등록해 둔 명단과 연결 (반·이름은 명단 기준)
    execute("""INSERT INTO users (role, username, nickname, password_hash, student_id, google_sub, google_email)
               VALUES ('student', ?, ?, ?, ?, ?, ?)""",
            (req["student_no"], generate_nickname(nickname_taken), req["password_hash"], sid,
             req["google_sub"], req["google_email"]))
    execute("DELETE FROM signup_requests WHERE id = ?", (req["id"],))
    audit("signup_approve", f"student:{sid} consent:{req['consent_at']}")
    return None


@bp.route("/signups", methods=["GET", "POST"])
@teacher_required
def signups():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "approve_all":
            ids = [r["id"] for r in query("SELECT id FROM signup_requests")]
        else:
            ids = [int(x) for x in request.form.getlist("ids") if x.isdigit()]
        reqs = [r for r in (query("SELECT * FROM signup_requests WHERE id = ?", (i,), one=True) for i in ids) if r]
        if action in ("approve", "approve_all"):
            errors = [e for e in (_approve(r) for r in reqs) if e]
            done = len(reqs) - len(errors)
            if done:
                flash(f"{done}명을 승인했습니다.", "ok")
            for e in errors[:10]:
                flash(e, "error")
        elif action == "reject":
            for r in reqs:
                execute("DELETE FROM signup_requests WHERE id = ?", (r["id"],))
                audit("signup_reject", f"request:{r['id']} no:{r['student_no']}")
            flash(f"{len(reqs)}건을 거절했습니다. 신청 정보는 지웠어요.", "ok")
        return redirect(url_for("teacher.signups"))
    rows = query("""SELECT r.*, c.name AS class_name, s.name AS roster_name, s.class_id AS roster_class_id,
                           rc.name AS roster_class_name
                    FROM signup_requests r JOIN classes c ON c.id = r.class_id
                    LEFT JOIN students s ON s.student_no = r.student_no
                    LEFT JOIN classes rc ON rc.id = s.class_id
                    ORDER BY c.name, r.created_at""")
    return render_template("teacher/signups.html", requests=rows)


# ---------- 감사 로그 ----------

@bp.route("/audit")
@teacher_required
def audit_log():
    page = _page()
    total = query("SELECT COUNT(*) AS n FROM audit_log", one=True)["n"]
    rows = query("SELECT * FROM audit_log ORDER BY id DESC LIMIT ? OFFSET ?",
                 (PAGE_SIZE * 2, (page - 1) * PAGE_SIZE * 2))
    return render_template("teacher/audit.html", rows=rows, page=page,
                           pages=max(1, math.ceil(total / (PAGE_SIZE * 2))))
