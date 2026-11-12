import re
import time
from collections import defaultdict, deque
from datetime import datetime

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from db import TRACKS, execute, nickname_taken, normalize_card, normalize_student_code, query
from security import (audit, authenticate, hash_password, login_required, login_user,
                      password_problem, verify_password)

bp = Blueprint("auth", __name__)

# IP 단위 시도 제한 (계정 잠금과 별도로, 아이디·가입 코드를 바꿔가며 시도하는 공격 대비)
_ip_attempts = defaultdict(deque)
_LIMITS = {"login": (300, 20), "signup": (3600, 10)}  # 종류: (기간 초, 최대 횟수)


def _ip_limited(ip, kind="login"):
    window, limit = _LIMITS[kind]
    now = time.monotonic()
    q = _ip_attempts[(kind, ip)]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        return True
    q.append(now)
    return False


def _safe_next(target):
    # 외부 사이트로의 리다이렉트(오픈 리다이렉트) 차단
    if target and target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return None


_HOME = {"teacher": "teacher.dashboard", "assistant": "teacher.questions", "student": "student.home"}
# 로그인 후 next 로 돌아갈 수 있는 경로 (역할 밖의 화면으로 보내 403 이 나지 않게)
_NEXT_PREFIX = {"teacher": "/t/", "assistant": "/t/", "student": "/s/"}


def _home_for(user):
    return url_for(_HOME[user["role"]])


@bp.route("/")
def index():
    if g.user is None:
        return render_template("home.html")  # 로그인 전 첫 화면: 공지·Q&A·모의고사 분석·교재 구매 바로가기 (들어가면 로그인 필요)
    return redirect(_home_for(g.user))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user is not None:
        return redirect(_home_for(g.user))
    if request.method == "POST":
        if _ip_limited(request.remote_addr or ""):
            flash("로그인 시도가 너무 많습니다. 잠시 후 다시 시도하세요.", "error")
            return render_template("login.html"), 429
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user, error = authenticate(username, password)
        if error:
            pending = query("SELECT password_hash FROM signup_requests WHERE student_no = ?", (username,), one=True)
            if pending and verify_password(pending["password_hash"], password):
                error = "가입 승인을 기다리고 있어요. 선생님이 승인하면 로그인할 수 있어요."
            flash(error, "error")
            return render_template("login.html", username=username)
        login_user(user)
        g.user = query("SELECT * FROM users WHERE id = ?", (user["id"],), one=True)
        audit("login", f"user:{username}")
        if user["must_change_pw"]:
            return redirect(url_for("auth.change_password"))
        nxt = _safe_next(request.args.get("next"))
        if nxt and not nxt.startswith(_NEXT_PREFIX[user["role"]]):
            nxt = None
        return redirect(nxt or _home_for(user))
    if session.pop("kicked", None):
        flash("다른 기기에서 로그인해 이 기기는 로그아웃됐습니다.", "error")
    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    if g.user is not None:
        audit("logout")
    session.clear()
    return redirect(url_for("auth.login"))


@bp.route("/password", methods=["GET", "POST"])
@login_required()
def change_password():
    if request.method == "POST":
        current = request.form.get("current", "")
        new = request.form.get("new", "")
        confirm = request.form.get("confirm", "")
        if not verify_password(g.user["password_hash"], current):
            flash("현재 비밀번호가 올바르지 않습니다.", "error")
        elif new != confirm:
            flash("새 비밀번호가 서로 일치하지 않습니다.", "error")
        elif new == current:
            flash("현재와 다른 비밀번호를 사용하세요.", "error")
        elif problem := password_problem(new):
            flash(problem, "error")
        else:
            execute("UPDATE users SET password_hash = ?, must_change_pw = 0 WHERE id = ?",
                    (hash_password(new), g.user["id"]))
            audit("password_changed")
            flash("비밀번호를 변경했습니다.", "ok")
            return redirect(_home_for(g.user))
    return render_template("change_password.html")


# ---------- 학생 회원가입 (반 가입 코드 + 선생님 승인) ----------

_NAME = re.compile(r"^[가-힣A-Za-z ]{2,20}$")
_STUDENT_NO = re.compile(r"^[A-Za-z0-9-]{3,30}$")


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    if g.user is not None:
        return redirect(_home_for(g.user))
    from google_auth import google_enabled, signup_identity
    form = {k: request.form.get(k, "").strip() for k in ("code", "name", "student_no")}
    # 먼저 단과/재종을 고른다. 단과는 RFID 카드 번호가 아이디, 재종은 자유 아이디
    track = request.values.get("track", "")
    track = track if track in TRACKS else ""
    if track == "단과":
        form["student_no"] = normalize_card(form["student_no"]) or form["student_no"]
    need_google = google_enabled()
    gid = signup_identity() if need_google else None
    if need_google and gid is None:          # Google 계정 확인이 먼저
        if request.method == "POST":
            flash("먼저 Google 계정으로 본인 확인을 해 주세요.", "error")
        return render_template("signup.html", form=form, step="google", track=track)
    if request.method == "POST":
        if _ip_limited(request.remote_addr or "", "signup"):
            flash("가입 시도가 너무 많습니다. 1시간 뒤에 다시 시도하세요.", "error")
            return render_template("signup.html", form=form, track=track), 429
        password = request.form.get("password", "")
        code = normalize_student_code(form["code"])
        sc = query("""SELECT sc.*, c.name AS class_name, c.track FROM student_codes sc JOIN classes c ON c.id = sc.class_id
                      WHERE sc.code = ? AND c.archived = 0""", (code,), one=True) if code else None
        # 틀린 칸 바로 아래에 알려 준다 (위쪽 알림창 대신 인라인 에러)
        error, field = None, None
        if not track:
            error, field = "단과와 재종 중 하나를 골라 주세요.", "track"
        elif sc is None:
            error, field = "학생코드가 올바르지 않아요. 조교 선생님께 받은 코드를 다시 확인해 주세요.", "code"
        elif sc["student_id"]:
            error, field = "이미 가입에 쓴 코드예요. 착오라면 선생님께 알려 주세요.", "code"
        elif sc["track"] != track:
            error, field = f"이 학생코드는 {sc['track']} 반 코드예요. 위에서 {sc['track']}을 골라 주세요.", "code"
        elif not _NAME.match(form["name"]):
            error, field = "이름은 한글 또는 영문 2~20자로 입력하세요.", "name"
        elif track == "단과" and not normalize_card(form["student_no"]):
            error, field = "카드 번호는 카드에 적힌 숫자(또는 영문 A~F 섞인 번호) 4~20자예요.", "student_no"
        elif track == "재종" and not _STUDENT_NO.match(form["student_no"]):
            error, field = "아이디는 영문·숫자·- 로 3~30자입니다.", "student_no"
        elif problem := password_problem(password):
            error, field = problem, "password"
        elif password != request.form.get("confirm", ""):
            error, field = "비밀번호가 서로 일치하지 않습니다.", "confirm"
        elif request.form.get("consent") != "1":
            error, field = "개인정보 수집·이용에 동의해야 가입할 수 있어요.", "consent"
        elif query("SELECT 1 FROM users WHERE username = ?", (form["student_no"],), one=True):
            error, field = ("이미 등록된 카드예요. 카드를 잘못 받았다면 조교 선생님께 알려 주세요." if track == "단과"
                            else "이미 쓰이고 있는 아이디예요. 다른 아이디를 정해 주세요."), "student_no"
        elif (roster := query("SELECT * FROM students WHERE student_no = ?", (form["student_no"],), one=True)) and \
                (roster["class_id"] != sc["class_id"] or not roster["active"]):
            error, field = "이미 쓰이고 있는 아이디예요. 다른 아이디를 정해 주세요.", "student_no"
        elif gid and query("SELECT 1 FROM users WHERE google_sub = ?", (gid["sub"],), one=True):
            error = "이 Google 계정은 이미 가입했어요. 로그인해 주세요."
        if error:
            if sc is None:
                audit("signup_code_failed", f"code:{code[:4]}")
            if field is None:
                flash(error, "error")
            return render_template("signup.html", form=form, gid=gid, errors={field: error} if field else {}, track=track)
        # 코드가 맞으면 승인 없이 바로 계정을 만든다 (코드 = 본인 확인)
        from nickname import generate_nickname
        roster = query("SELECT * FROM students WHERE student_no = ? AND class_id = ?", (form["student_no"], sc["class_id"]), one=True)
        if roster:                                   # 선생님이 미리 넣어 둔 명단과 연결
            sid = roster["id"]
        else:
            sid = execute("INSERT INTO students (class_id, name, student_no) VALUES (?, ?, ?)",
                          (sc["class_id"], form["name"], form["student_no"]))
        uid = execute("""INSERT INTO users (role, username, nickname, password_hash, student_id, google_sub, google_email)
                         VALUES ('student', ?, ?, ?, ?, ?, ?)""",
                      (form["student_no"], generate_nickname(nickname_taken), hash_password(password), sid,
                       gid["sub"] if gid else None, gid["email"] if gid else None))
        execute("UPDATE student_codes SET student_id = ?, used_at = datetime('now', 'localtime') WHERE id = ?", (sid, sc["id"]))
        session.pop("g_signup", None)
        audit("signup_code", f"student:{sid} class:{sc['class_id']} consent:{datetime.now().isoformat(timespec='seconds')}",
              username=form["student_no"])
        user = query("SELECT * FROM users WHERE id = ?", (uid,), one=True)
        login_user(user)
        g.user = user
        flash(f"가입했어요. {sc['class_name']}에 오신 걸 환영해요!", "ok")
        return redirect(_home_for(user))
    return render_template("signup.html", form=form, gid=gid, errors={}, track=track)
