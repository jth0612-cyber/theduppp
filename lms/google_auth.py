"""Google 계정으로 로그인 (OpenID Connect, 승인 코드 + PKCE).

이 앱은 반 학생 전용이라 Google 로 '새 가입'은 받지 않는다.
이미 승인된 계정으로 로그인한 뒤 '내 계정'에서 Google 계정을 연결해 두면, 다음부터 Google 로 로그인할 수 있다.
GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET 이 instance/.env 에 있을 때만 켜진다."""
import base64
import hashlib
import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

from flask import Blueprint, abort, flash, g, redirect, request, session, url_for

from db import execute, query

bp = Blueprint("google", __name__, url_prefix="/auth/google")

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
_HOME = {"teacher": "teacher.dashboard", "assistant": "teacher.questions", "student": "student.home"}


def google_enabled():
    return bool(os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET"))


def _post_form(url, data):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 (고정된 https 주소만)
        return json.loads(resp.read().decode())


def _get_json(url, token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
        return json.loads(resp.read().decode())


def fetch_identity(code, verifier, redirect_uri):
    """승인 코드를 토큰으로 바꾸고 Google 사용자 정보(sub, email)를 받는다. 테스트에서 바꿔 끼운다."""
    tokens = _post_form(TOKEN_URL, {
        "code": code, "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"], "redirect_uri": redirect_uri,
        "grant_type": "authorization_code", "code_verifier": verifier,
    })
    info = _get_json(USERINFO_URL, tokens["access_token"])
    return {"sub": info["sub"], "email": info.get("email", ""), "email_verified": info.get("email_verified", False)}


@bp.route("/start")
def start():
    if not google_enabled():
        abort(404)
    mode = request.args.get("mode", "login")
    if mode not in ("login", "link"):
        abort(400)
    if mode == "link" and g.user is None:
        return redirect(url_for("auth.login"))
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(24)
    session["g_oauth"] = {"state": state, "verifier": verifier, "mode": mode}
    params = {
        "client_id": os.environ["GOOGLE_CLIENT_ID"], "redirect_uri": url_for("google.callback", _external=True),
        "response_type": "code", "scope": "openid email", "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256", "prompt": "select_account",
    }
    return redirect(f"{AUTH_URL}?{urllib.parse.urlencode(params)}")


@bp.route("/callback")
def callback():
    from security import audit, login_user  # 순환 import 방지

    saved = session.pop("g_oauth", None)
    if not google_enabled() or not saved or request.args.get("state") != saved["state"]:
        flash("Google 로그인을 다시 시도하세요. (요청이 만료되었거나 올바르지 않습니다)", "error")
        return redirect(url_for("auth.login"))
    if request.args.get("error") or not request.args.get("code"):
        flash("Google 로그인을 취소했어요.", "error")
        return redirect(url_for("auth.login") if saved["mode"] == "login" else url_for("auth.change_password"))
    try:
        ident = fetch_identity(request.args["code"], saved["verifier"], url_for("google.callback", _external=True))
    except (urllib.error.URLError, KeyError, ValueError, TimeoutError):
        flash("Google 과 연결하지 못했어요. 잠시 후 다시 시도하세요.", "error")
        return redirect(url_for("auth.login"))
    if not ident["email_verified"]:
        flash("이메일 인증이 끝난 Google 계정만 쓸 수 있어요.", "error")
        return redirect(url_for("auth.login"))

    if saved["mode"] == "link":
        if g.user is None:
            return redirect(url_for("auth.login"))
        other = query("SELECT id FROM users WHERE google_sub = ? AND id != ?", (ident["sub"], g.user["id"]), one=True)
        if other:
            flash("이 Google 계정은 이미 다른 계정에 연결되어 있어요.", "error")
        else:
            execute("UPDATE users SET google_sub = ?, google_email = ? WHERE id = ?",
                    (ident["sub"], ident["email"], g.user["id"]))
            audit("google_linked", f"user:{g.user['username']}")
            flash(f"Google 계정({ident['email']})을 연결했어요. 다음부터 Google 로 로그인할 수 있어요.", "ok")
        return redirect(url_for("auth.change_password"))

    user = query("SELECT * FROM users WHERE google_sub = ?", (ident["sub"],), one=True)
    if user is None:
        flash("이 Google 계정과 연결된 계정이 없어요. 먼저 수험번호로 로그인한 뒤 '내 계정'에서 Google 계정을 연결하세요.",
              "error")
        return redirect(url_for("auth.login"))
    if user["disabled"]:
        audit("login_disabled", f"user:{user['username']}", user_id=user["id"], username=user["username"])
        flash("사용이 중지된 계정입니다. 선생님께 문의하세요.", "error")
        return redirect(url_for("auth.login"))
    execute("UPDATE users SET failed_attempts = 0, locked_until = NULL, last_login_at = ? WHERE id = ?",
            (datetime.now().isoformat(timespec="seconds"), user["id"]))
    login_user(user)
    g.user = query("SELECT * FROM users WHERE id = ?", (user["id"],), one=True)
    audit("login_google", f"user:{user['username']}")
    if user["must_change_pw"]:
        return redirect(url_for("auth.change_password"))
    return redirect(url_for(_HOME[user["role"]]))


@bp.route("/unlink", methods=["POST"])
def unlink():
    from security import audit
    if g.user is None:
        return redirect(url_for("auth.login"))
    execute("UPDATE users SET google_sub = NULL, google_email = NULL WHERE id = ?", (g.user["id"],))
    audit("google_unlinked", f"user:{g.user['username']}")
    flash("Google 계정 연결을 해제했어요. 이제 수험번호와 비밀번호로만 로그인할 수 있어요.", "ok")
    return redirect(url_for("auth.change_password"))
