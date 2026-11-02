import re
import time
from collections import defaultdict, deque
from datetime import datetime

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from db import execute, query
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
_NEXT_PREFIX = {"teacher": "/t/", "assistant": "/t/questions", "student": "/s/"}


def _home_for(user):
    return url_for(_HOME[user["role"]])


@bp.route("/")
def index():
    if g.user is None:
        return render_template("home.html")  # 로그인 전 첫 화면: 공지·Q&A 바로가기 (들어가면 로그인 필요)
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
        flash("다른 기기에서 같은 계정으로 로그인해서 이 기기의 로그인이 끝났어요. 학생 계정은 한 기기에서만 쓸 수 있어요.", "error")
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
    need_google = google_enabled()
    gid = signup_identity() if need_google else None
    if need_google and gid is None:          # Google 계정 확인이 먼저
        if request.method == "POST":
            flash("먼저 Google 계정으로 본인 확인을 해 주세요.", "error")
        return render_template("signup.html", form=form, step="google")
    if request.method == "POST":
        if _ip_limited(request.remote_addr or "", "signup"):
            flash("가입 시도가 너무 많습니다. 1시간 뒤에 다시 시도하세요.", "error")
            return render_template("signup.html", form=form), 429
        password = request.form.get("password", "")
        code = form["code"].upper().replace("-", "").replace(" ", "")
        cls = query("SELECT * FROM classes WHERE join_code = ? AND join_open = 1 AND archived = 0",
                    (code,), one=True) if code else None
        error = None
        if cls is None:
            error = "반 가입 코드가 올바르지 않거나, 지금은 가입을 받지 않는 반이에요. 선생님께 확인하세요."
        elif not _NAME.match(form["name"]):
            error = "이름은 한글 또는 영문 2~20자로 입력하세요."
        elif not _STUDENT_NO.match(form["student_no"]):
            error = "수험번호는 영문·숫자·- 로 3~30자입니다."
        elif password != request.form.get("confirm", ""):
            error = "비밀번호가 서로 일치하지 않습니다."
        elif problem := password_problem(password):
            error = problem
        elif request.form.get("consent") != "1":
            error = "개인정보 수집·이용에 동의해야 가입할 수 있어요."
        elif query("SELECT 1 FROM users WHERE username = ?", (form["student_no"],), one=True):
            error = "이미 가입된 수험번호예요. 로그인하거나 선생님께 비밀번호 초기화를 요청하세요."
        elif query("SELECT 1 FROM signup_requests WHERE student_no = ?", (form["student_no"],), one=True):
            error = "이미 가입 신청한 수험번호예요. 선생님 승인을 기다려 주세요."
        elif gid and (query("SELECT 1 FROM users WHERE google_sub = ?", (gid["sub"],), one=True)
                      or query("SELECT 1 FROM signup_requests WHERE google_sub = ?", (gid["sub"],), one=True)):
            error = "이 Google 계정은 이미 가입했거나 신청 중이에요."
        if error:
            flash(error, "error")
            return render_template("signup.html", form=form, gid=gid)
        rid = execute("""INSERT INTO signup_requests (class_id, name, student_no, password_hash, consent_at, ip,
                                                      google_sub, google_email)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                      (cls["id"], form["name"], form["student_no"], hash_password(password),
                       datetime.now().isoformat(timespec="seconds"), request.remote_addr or "",
                       gid["sub"] if gid else None, gid["email"] if gid else None))
        session.pop("g_signup", None)
        audit("signup_request", f"request:{rid} class:{cls['id']}", username=form["student_no"])
        return render_template("signup_done.html", class_name=cls["name"], google=bool(gid))
    return render_template("signup.html", form=form, gid=gid)
