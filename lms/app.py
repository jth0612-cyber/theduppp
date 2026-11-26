"""학습 관리 시스템 - 앱 팩토리와 보안 설정."""
import os
import secrets
from datetime import timedelta

from cryptography.fernet import Fernet
from dotenv import load_dotenv
from flask import Flask, g, render_template, request
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
            fh.write("# FIELD_ENCRYPTION_KEY 를 잃어버리면 암호화된 연락처/메모를 복구할 수 없어요. 따로 안전하게 보관하세요.\n")
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
        ITEMS_ENABLED=os.environ.get("ITEMS_ENABLED") == "1",  # 문항 그림(views/items.py): 보안 검토 전까지 꺼 둔다 (2026-11-25)
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
    app.register_blueprint(pwa_bp)
    from views.link import api as link_api, bp as link_bp     # 조교 시스템(구글 시트) 연동
    app.register_blueprint(link_bp)
    app.register_blueprint(link_api)
    from views.cast import bp as cast_bp
    app.register_blueprint(cast_bp)
    from views.feedback import bp as feedback_bp
    app.register_blueprint(feedback_bp)
    from views.care import bp as care_bp                     # 숙제 인증·문항별 첨삭·수업 기록·학부모 리포트
    app.register_blueprint(care_bp)
    from views.items import bp as items_bp                   # 문항 그림 (워터마크 · 필기 질문)
    app.register_blueprint(items_bp)
    from views.schedule import bp as schedule_bp             # 수업 일정: 진도 그룹·주차·수업 칸·배부 교재·출석
    app.register_blueprint(schedule_bp)
    csrf.exempt(link_api)                                    # 시트가 열쇠(토큰)로 보내는 주소라 폼 토큰이 없다
    app.jinja_env.globals["google_enabled"] = google_enabled
    if not app.config.get("TESTING") or app.config.get("SEED_PRACTICE"):
        with app.app_context():                              # 연습반(실장 TEST반)·가상 학생 50명·연습 회차 (처음 한 번)
            import exams
            exams.seed_practice()
    from security import role_caption, shown_name
    app.jinja_env.globals["shown_name"] = shown_name
    app.jinja_env.globals["role_caption"] = role_caption

    def site_contact():
        # instance/.env 에서 읽는다. 비어 있으면 문의 버튼은 질답 게시판(행정문의)으로 연결된다
        url = os.environ.get("KAKAO_CHANNEL_URL", "").strip()
        # 오픈채팅: 로그인 못 하는 학생(비밀번호 분실)의 문의 창구. 카카오 오픈채팅 주소만 받는다
        oc = os.environ.get("KAKAO_OPENCHAT_URL", "").strip()
        return {"kakao": url if url.startswith("https://") else "",
                "openchat": oc if oc.startswith("https://open.kakao.com/") else "", "note": os.environ.get("CONTACT_NOTE", "").strip(),
                # 하단 운영자 줄 아래 연락처. 비어 있으면 줄 자체를 감춘다
                "email": os.environ.get("CONTACT_EMAIL", "").strip(), "phone": os.environ.get("CONTACT_PHONE", "").strip(),
                # 사업자 정보 (상호, 사업자등록번호, 주소). 넣은 것만 하단과 약관에 보인다
                "biz_name": os.environ.get("BIZ_NAME", "").strip(), "biz_no": os.environ.get("BIZ_REG_NO", "").strip(),
                "biz_addr": os.environ.get("BIZ_ADDRESS", "").strip()}
    app.jinja_env.globals["site_contact"] = site_contact

    def question_photos(q):
        """질문 사진 (최대 3장): 첫 장은 questions.image_id, 나머지는 question_images."""
        from db import query as _q
        ids = [q["image_id"]] if q["image_id"] else []
        ids += [r["file_id"] for r in _q("SELECT file_id FROM question_images WHERE question_id = ? ORDER BY pos", (q["id"],))]
        return ids
    app.jinja_env.globals["question_photos"] = question_photos

    from content import file_kind, host_of, video_source, youtube_id
    app.jinja_env.filters.update(file_kind=file_kind, host_of=host_of, youtube_id=youtube_id, video_source=video_source)

    # 날짜 표기는 여기 한 곳에서: 올해 11.15 / 다른 해 2025.11.15 / 시각 포함 11.15 09:05. 화면에 ISO 모양을 내지 않는다.
    import re as _re
    from datetime import date as _date

    def _when(v):
        return _re.match(r"(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2}))?", str(v or "").strip())

    def fmt_d(v):
        m = _when(v)
        if not m:
            return v or ""
        y, mo, da = m.group(1, 2, 3)
        return f"{mo}.{da}" if int(y) == _date.today().year else f"{y}.{mo}.{da}"

    def fmt_dt(v):
        m = _when(v)
        if not m:
            return v or ""
        return fmt_d(v) + (f" {m.group(4)}:{m.group(5)}" if m.group(4) else "")

    def fmt_t(v):
        m = _when(v)
        return f"{m.group(4)}:{m.group(5)}" if m and m.group(4) else ""

    app.jinja_env.filters.update(d=fmt_d, dt=fmt_dt, t=fmt_t)

    # 정적 파일 주소 끝에 수정 시각(?v=)을 붙인다: 파일이 바뀌면 주소가 바뀌므로 오래 보관해도 옛 파일이 남지 않는다
    static_mtime = {}

    @app.url_defaults
    def static_version(endpoint, values):
        if endpoint != "static" or "v" in values or not values.get("filename"):
            return
        name = values["filename"]
        if name.startswith("fonts/"):          # 글꼴은 CSS 안의 주소와 같아야 두 번 받지 않는다. 대신 아래에서 오래 보관
            return
        path = os.path.join(app.static_folder, name)
        try:
            m = int(os.path.getmtime(path)) if os.path.isfile(path) else None
        except OSError:
            m = None
        if app.debug or app.testing:
            static_mtime.pop(name, None)
        if m is not None:
            values["v"] = static_mtime.setdefault(name, m)

    @app.after_request
    def security_headers(resp):
        resp.headers["Content-Security-Policy"] = (
            # i.ytimg.com: 유튜브 강의 영상 썸네일
            "default-src 'self'; img-src 'self' data: blob: https://i.ytimg.com; style-src 'self'; script-src 'self'; "
            "frame-src https://www.youtube-nocookie.com; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        # same-origin: 외부 사이트로는 주소를 보내지 않되, HTTPS 에서 CSRF 검사에 필요한 같은 사이트 Referer 는 보낸다
        resp.headers["Referrer-Policy"] = "same-origin"
        resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.endpoint == "static":
            # 글꼴, CSS, 스크립트는 누구에게나 같은 파일이다. 로그인 후에도 보관하게 해 화면마다 다시 받지 않는다.
            # ?v= 가 붙은 주소는 1년, 안 붙은 주소(CSS 안의 글꼴, 스크립트가 직접 부르는 파일)는 바뀌었는지만 묻는다(304)
            # 글꼴은 같은 이름으로 내용이 바뀌지 않는다 (바꿀 때는 파일 이름을 바꾼다)
            if (request.args.get("v") or request.path.startswith("/static/fonts/")) and resp.status_code == 200:
                resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            else:
                resp.headers["Cache-Control"] = "no-cache"
        elif g.get("user") is not None and not resp.headers.pop("X-Private-Cache", None):
            # 로그인 후 화면은 브라우저/프록시에 캐시하지 않는다
            resp.headers["Cache-Control"] = "no-store"
        if app.config["SESSION_COOKIE_SECURE"]:
            resp.headers["Strict-Transport-Security"] = "max-age=31536000"
        return resp

    @app.errorhandler(CSRFError)
    def csrf_error(_e):
        return render_template("error.html", code=400,
                               message="시간이 지나 요청이 끊겼어요. 새로고침한 뒤 다시 해 주세요."), 400

    @app.errorhandler(403)
    def forbidden(_e):
        from flask import flash, g, redirect, request
        # 조교가 선생님 전용 버튼(삭제·계정 등)을 누른 경우: 오류 화면 대신 원래 화면으로 돌려보낸다
        if request.method == "POST" and getattr(g, "user", None) is not None and g.user["role"] == "assistant":
            flash("이 작업은 선생님만 할 수 있어요.", "error")
            ref = request.referrer or ""
            return redirect(ref if ref.startswith(request.host_url) else "/t/questions")
        return render_template("error.html", code=403, message="볼 수 없는 화면이에요."), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("error.html", code=404, message="없는 화면이에요."), 404

    @app.errorhandler(413)
    def too_large(_e):
        return render_template("error.html", code=413, message="파일이 너무 커요. 20MB까지 올릴 수 있어요."), 413

    if not app.config.get("TESTING"):
        from views import notices_job
        notices_job.start(app)
    return app


if __name__ == "__main__":
    # 기본은 이 PC 에서만 접속 가능(127.0.0.1). 외부 공개는 HTTPS 리버스 프록시 뒤에서만 하세요.
    create_app().run(host="127.0.0.1", port=5000, debug=False)
