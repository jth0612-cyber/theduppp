"""학습 관리 시스템 - 앱 팩토리와 보안 설정."""
import os
import secrets
from datetime import timedelta

from cryptography.fernet import Fernet
from dotenv import load_dotenv
from flask import Flask, g, render_template
from flask_wtf.csrf import CSRFError, CSRFProtect

import db
from security import load_current_user

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
ENV_PATH = os.path.join(INSTANCE_DIR, ".env")

csrf = CSRFProtect()


def _ensure_secrets():
    """최초 실행 시 비밀키와 암호화 키를 instance/.env 에 생성한다."""
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    if not os.path.exists(ENV_PATH):
        with open(ENV_PATH, "w", encoding="utf-8") as fh:
            fh.write("# 이 파일은 절대 공유하거나 git 에 올리지 마세요.\n")
            fh.write("# FIELD_ENCRYPTION_KEY 를 잃어버리면 암호화된 연락처/메모를 복구할 수 없습니다. 따로 안전하게 보관하세요.\n")
            fh.write(f"SECRET_KEY={secrets.token_hex(32)}\n")
            fh.write(f"FIELD_ENCRYPTION_KEY={Fernet.generate_key().decode()}\n")
            fh.write("# HTTPS 로 배포할 때 1 로 바꾸세요\n")
            fh.write("SESSION_COOKIE_SECURE=0\n")
    load_dotenv(ENV_PATH)


def create_app(test_config=None):
    _ensure_secrets()
    app = Flask(__name__, instance_path=INSTANCE_DIR)
    app.config.update(
        SECRET_KEY=os.environ["SECRET_KEY"],
        FIELD_ENCRYPTION_KEY=os.environ["FIELD_ENCRYPTION_KEY"].encode(),
        DATABASE=os.environ.get("LMS_DATABASE") or os.path.join(INSTANCE_DIR, "lms.sqlite3"),
        UPLOAD_DIR=os.path.join(INSTANCE_DIR, "uploads"),
        MAX_CONTENT_LENGTH=20 * 1024 * 1024,  # 20MB
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE") == "1",
        SESSION_COOKIE_NAME="lms_session",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        IDLE_TIMEOUT_MINUTES=60,
        WTF_CSRF_TIME_LIMIT=None,
    )
    if test_config:
        app.config.update(test_config)

    if os.environ.get("BEHIND_PROXY") == "1":
        # 시놀로지 리버스 프록시 뒤: 실제 접속 IP(로그인 제한·접근 기록용)와 https 여부를 프록시 헤더에서 읽는다
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)
    db.init_db(app.config["DATABASE"])
    csrf.init_app(app)
    app.teardown_appcontext(db.close_db)
    app.before_request(load_current_user)

    from views.auth import bp as auth_bp
    from views.games import bp as games_bp
    from views.student import bp as student_bp
    from views.teacher import bp as teacher_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(games_bp)
    from google_auth import bp as google_bp, google_enabled
    from views.books import bp as books_bp
    app.register_blueprint(google_bp)
    app.register_blueprint(books_bp)
    from views.pwa import bp as pwa_bp
    from views.rooms import bp as rooms_bp
    from views.study import bp as study_bp
    app.register_blueprint(rooms_bp)
    app.register_blueprint(study_bp)
    from views.planner import bp as planner_bp
    app.register_blueprint(planner_bp)
    app.register_blueprint(pwa_bp)
    app.jinja_env.globals["google_enabled"] = google_enabled

    def site_contact():
        # instance/.env 에서 읽는다. 비어 있으면 문의 버튼은 질답 게시판(행정문의)으로 연결된다
        url = os.environ.get("KAKAO_CHANNEL_URL", "").strip()
        return {"kakao": url if url.startswith("https://") else "", "note": os.environ.get("CONTACT_NOTE", "").strip()}
    app.jinja_env.globals["site_contact"] = site_contact

    from content import file_kind, host_of, video_source, youtube_id
    app.jinja_env.filters.update(file_kind=file_kind, host_of=host_of, youtube_id=youtube_id, video_source=video_source)

    @app.after_request
    def security_headers(resp):
        resp.headers["Content-Security-Policy"] = (
            # i.ytimg.com: 유튜브 강의 영상 썸네일
            "default-src 'self'; img-src 'self' data: https://i.ytimg.com; style-src 'self'; script-src 'self'; "
            "object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        # same-origin: 외부 사이트로는 주소를 보내지 않되, HTTPS 에서 CSRF 검사에 필요한 같은 사이트 Referer 는 보낸다
        resp.headers["Referrer-Policy"] = "same-origin"
        resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if g.get("user") is not None:
            # 로그인 후 화면은 브라우저/프록시에 캐시하지 않는다
            resp.headers["Cache-Control"] = "no-store"
        if app.config["SESSION_COOKIE_SECURE"]:
            resp.headers["Strict-Transport-Security"] = "max-age=31536000"
        return resp

    @app.errorhandler(CSRFError)
    def csrf_error(_e):
        return render_template("error.html", code=400,
                               message="요청이 만료되었습니다. 페이지를 새로고침한 뒤 다시 시도하세요."), 400

    @app.errorhandler(403)
    def forbidden(_e):
        from flask import flash, g, redirect, request
        # 조교가 선생님 전용 버튼(삭제·계정 등)을 누른 경우: 오류 화면 대신 원래 화면으로 돌려보낸다
        if request.method == "POST" and getattr(g, "user", None) is not None and g.user["role"] == "assistant":
            flash("이 작업은 선생님만 할 수 있어요.", "error")
            ref = request.referrer or ""
            return redirect(ref if ref.startswith(request.host_url) else "/t/questions")
        return render_template("error.html", code=403, message="접근 권한이 없습니다."), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("error.html", code=404, message="페이지를 찾을 수 없습니다."), 404

    @app.errorhandler(413)
    def too_large(_e):
        return render_template("error.html", code=413, message="파일이 너무 큽니다. (최대 20MB)"), 413

    return app


if __name__ == "__main__":
    # 기본은 이 PC 에서만 접속 가능(127.0.0.1). 외부 공개는 HTTPS 리버스 프록시 뒤에서만 하세요.
    create_app().run(host="127.0.0.1", port=5000, debug=False)
