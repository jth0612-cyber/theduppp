"""인증, 권한, 암호화, 업로드 검증, 감사 로그."""
import functools
import os
import secrets
import string
from datetime import datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken
from flask import abort, current_app, g, redirect, request, session, url_for

from db import execute, query

_ph = PasswordHasher()  # argon2id

MAX_FAILED_LOGINS = 5
LOCK_MINUTES = 15
MIN_PASSWORD_LEN = 10


# ---------- 비밀번호 ----------

def hash_password(pw):
    return _ph.hash(pw)


def verify_password(stored_hash, pw):
    try:
        return _ph.verify(stored_hash, pw)
    except (VerifyMismatchError, InvalidHashError):
        return False


# 계정이 없을 때도 같은 시간을 쓰도록 하는 더미 해시 (사용자 존재 여부 노출 방지)
_DUMMY_HASH = _ph.hash(secrets.token_urlsafe(16))


def password_problem(pw):
    """비밀번호 정책 위반 사유를 반환 (없으면 None)."""
    if len(pw) < MIN_PASSWORD_LEN:
        return f"비밀번호는 {MIN_PASSWORD_LEN}자 이상이어야 합니다."
    kinds = sum([
        any(c.isalpha() for c in pw),
        any(c.isdigit() for c in pw),
        any(not c.isalnum() for c in pw),
    ])
    if kinds < 2:
        return "영문, 숫자, 특수문자 중 2종류 이상을 섞어 주세요."
    return None


def generate_temp_password(length=12):
    alphabet = string.ascii_letters + string.digits
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(length))
        if any(c.isdigit() for c in pw) and any(c.isalpha() for c in pw):
            return pw


def authenticate(username, password):
    """(user_row, error_message) 반환. 계정 잠금과 실패 횟수를 관리한다."""
    user = query("SELECT * FROM users WHERE username = ?", (username,), one=True)
    if user is None:
        verify_password(_DUMMY_HASH, password)
        return None, "아이디 또는 비밀번호가 올바르지 않습니다."

    now = datetime.now()
    if user["locked_until"] and datetime.fromisoformat(user["locked_until"]) > now:
        return None, f"로그인 시도가 너무 많아 잠겼습니다. {LOCK_MINUTES}분 후 다시 시도하세요."

    if not verify_password(user["password_hash"], password):
        attempts = user["failed_attempts"] + 1
        locked = None
        if attempts >= MAX_FAILED_LOGINS:
            locked = (now + timedelta(minutes=LOCK_MINUTES)).isoformat(timespec="seconds")
            attempts = 0
        execute("UPDATE users SET failed_attempts = ?, locked_until = ? WHERE id = ?",
                (attempts, locked, user["id"]))
        audit("login_failed", f"user:{username}", user_id=user["id"], username=username)
        return None, "아이디 또는 비밀번호가 올바르지 않습니다."

    if user["disabled"]:
        audit("login_disabled", f"user:{username}", user_id=user["id"], username=username)
        return None, "사용이 중지된 계정입니다. 선생님께 문의하세요."

    if _ph.check_needs_rehash(user["password_hash"]):
        execute("UPDATE users SET password_hash = ? WHERE id = ?",
                (hash_password(password), user["id"]))
    execute("UPDATE users SET failed_attempts = 0, locked_until = NULL, last_login_at = ? WHERE id = ?",
            (now.isoformat(timespec="seconds"), user["id"]))
    return user, None


# ---------- 세션 / 권한 ----------

def login_user(user):
    session.clear()  # 세션 고정 공격 방지
    session.permanent = True
    session["uid"] = user["id"]
    session["role"] = user["role"]
    session["last_seen"] = datetime.now().isoformat(timespec="seconds")
    if user["role"] == "student":
        # 학생 계정은 한 기기에서만: 새로 로그인하면 이전 기기의 로그인은 끊긴다 (교재 분석실 동시 접속 1대)
        version = (user["session_version"] or 0) + 1
        execute("UPDATE users SET session_version = ? WHERE id = ?", (version, user["id"]))
        session["sv"] = version


def load_current_user():
    g.user = None
    uid = session.get("uid")
    if uid is None:
        return
    last_seen = session.get("last_seen")
    idle = timedelta(minutes=current_app.config["IDLE_TIMEOUT_MINUTES"])
    if not last_seen or datetime.fromisoformat(last_seen) + idle < datetime.now():
        session.clear()
        return
    user = query("SELECT * FROM users WHERE id = ?", (uid,), one=True)
    if user is None or user["role"] != session.get("role") or user["disabled"]:
        session.clear()
        return
    if user["role"] == "student" and session.get("sv") != user["session_version"]:
        session.clear()
        session["kicked"] = True  # 로그인 화면에서 "다른 기기에서 로그인" 안내
        return
    session["last_seen"] = datetime.now().isoformat(timespec="seconds")
    g.user = user


def login_required(role=None):
    """role: 허용할 역할 하나(문자열) 또는 여러 개(튜플). None 이면 로그인만 확인."""
    roles = (role,) if isinstance(role, str) else role

    def decorator(view):
        @functools.wraps(view)
        def wrapped(*args, **kwargs):
            if g.user is None:
                return redirect(url_for("auth.login", next=request.path))
            if g.user["must_change_pw"] and request.endpoint != "auth.change_password":
                return redirect(url_for("auth.change_password"))
            if roles and g.user["role"] not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


teacher_required = login_required("teacher")
staff_required = login_required(("teacher", "assistant"))  # 질문답변처럼 조교도 하는 일
student_required = login_required("student")


# ---------- 필드 암호화 ----------

def _fernet():
    return Fernet(current_app.config["FIELD_ENCRYPTION_KEY"])


def encrypt(text):
    if not text:
        return None
    return _fernet().encrypt(text.encode("utf-8")).decode("ascii")


def decrypt(token):
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken:
        return "[복호화 실패: 암호화 키를 확인하세요]"


# ---------- 업로드 검증 ----------

# 확장자 -> (MIME, 파일 시그니처 목록)
ALLOWED_UPLOADS = {
    "pdf":  ("application/pdf", [b"%PDF-"]),
    "pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", [b"PK\x03\x04"]),
    "ppt":  ("application/vnd.ms-powerpoint", [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"]),
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", [b"PK\x03\x04"]),
    "hwp":  ("application/x-hwp", [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"]),
    "png":  ("image/png", [b"\x89PNG\r\n\x1a\n"]),
    "jpg":  ("image/jpeg", [b"\xff\xd8\xff"]),
    "jpeg": ("image/jpeg", [b"\xff\xd8\xff"]),
}
IMAGE_EXTS = {"png", "jpg", "jpeg"}


def save_upload(file_storage, allowed_exts):
    """검증 후 저장하고 files.id 반환. 실패 시 ValueError."""
    original = (file_storage.filename or "").strip()
    if not original:
        raise ValueError("파일을 선택하세요.")
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if ext not in allowed_exts or ext not in ALLOWED_UPLOADS:
        raise ValueError(f"허용되지 않는 파일 형식입니다. ({', '.join(sorted(allowed_exts))})")

    data = file_storage.read(current_app.config["MAX_CONTENT_LENGTH"] + 1)
    if len(data) > current_app.config["MAX_CONTENT_LENGTH"]:
        raise ValueError("파일이 너무 큽니다.")
    if not data:
        raise ValueError("빈 파일입니다.")
    mime, signatures = ALLOWED_UPLOADS[ext]
    if not any(data.startswith(sig) for sig in signatures):
        raise ValueError("파일 내용이 확장자와 일치하지 않습니다.")

    stored = secrets.token_hex(16)
    path = os.path.join(current_app.config["UPLOAD_DIR"], stored)
    with open(path, "wb") as fh:
        fh.write(data)
    # 원본 파일명은 표시용으로만 사용 (경로 문자 제거)
    safe_original = os.path.basename(original.replace("\\", "/"))[:200]
    return execute(
        "INSERT INTO files (stored_name, original_name, mime, size, owner_id) VALUES (?, ?, ?, ?, ?)",
        (stored, safe_original, mime, len(data), g.user["id"]),
    )


def delete_file(file_id):
    row = query("SELECT stored_name FROM files WHERE id = ?", (file_id,), one=True)
    if row is None:
        return
    path = os.path.join(current_app.config["UPLOAD_DIR"], row["stored_name"])
    if os.path.exists(path):
        os.remove(path)
    execute("DELETE FROM files WHERE id = ?", (file_id,))


# ---------- 감사 로그 ----------

def audit(action, target="", user_id=None, username=None):
    user = getattr(g, "user", None)
    if user is not None and user_id is None:
        user_id, username = user["id"], user["username"]
    execute(
        "INSERT INTO audit_log (user_id, username, action, target, ip) VALUES (?, ?, ?, ?, ?)",
        (user_id, username, action, target, request.remote_addr or ""),
    )
