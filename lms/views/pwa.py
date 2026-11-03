"""휴대폰 홈 화면 설치(PWA)와 새 공지·답변 알림(웹 푸시).
알림은 브라우저 회사의 무료 푸시 서버(구글·애플·모질라)를 거쳐 전달된다. 별도 가입이나 요금은 없다.
서명용 키(VAPID)는 처음 쓸 때 instance/vapid.pem 에 만들어 두고 밖으로 내보내지 않는다."""
import base64
import json
import os
import sqlite3
import threading

from flask import (Blueprint, Response, abort, current_app, g, jsonify, request,
                   send_from_directory)

from db import execute, query
from security import login_required

bp = Blueprint("pwa", __name__)

try:  # 알림 라이브러리가 없어도 앱은 그대로 동작한다
    from py_vapid import Vapid01
    from pywebpush import WebPushException, webpush
    from cryptography.hazmat.primitives import serialization
except ImportError:  # pragma: no cover
    Vapid01 = None

_vapid_lock = threading.Lock()


def _vapid_path():
    return current_app.config.get("VAPID_PATH") or os.path.join(current_app.instance_path, "vapid.pem")


def _vapid():
    if Vapid01 is None:
        return None
    path = _vapid_path()
    with _vapid_lock:
        if not os.path.exists(path):
            v = Vapid01()
            v.generate_keys()
            v.save_key(path)
            os.chmod(path, 0o600)
    return Vapid01.from_file(path)


def public_key():
    v = _vapid()
    if v is None:
        return ""
    raw = v.public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def push_enabled():
    return Vapid01 is not None and not current_app.config.get("TESTING")


# ---------- 설치(PWA) ----------

@bp.route("/manifest.webmanifest")
def manifest():
    data = {
        "name": "정태혁 통합과학 lab",
        "short_name": "통합과학 lab",
        "start_url": "/?source=app",
        "scope": "/",
        "display": "standalone",
        "background_color": "#f2f3f2",
        "theme_color": "#1d1b18",
        "lang": "ko",
        "icons": [
            {"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "/static/icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    return Response(json.dumps(data, ensure_ascii=False), mimetype="application/manifest+json")


@bp.route("/sw.js")
def service_worker():
    resp = send_from_directory(os.path.join(current_app.root_path, "static"), "sw.js", mimetype="text/javascript",
                               max_age=0)
    resp.headers["Service-Worker-Allowed"] = "/"
    resp.headers["Cache-Control"] = "no-cache"
    return resp


# ---------- 알림 구독 ----------

@bp.route("/push/key")
@login_required()
def push_key():
    return jsonify(key=public_key() if Vapid01 else "")


@bp.route("/push/subscribe", methods=["POST"])
@login_required()
def push_subscribe():
    data = request.get_json(silent=True) or {}
    endpoint = str(data.get("endpoint", ""))
    keys = data.get("keys") or {}
    if not endpoint.startswith("https://") or len(endpoint) > 1000 or not keys.get("p256dh") or not keys.get("auth"):
        abort(400)
    execute("""INSERT INTO push_subs (user_id, endpoint, p256dh, auth) VALUES (?, ?, ?, ?)
               ON CONFLICT(endpoint) DO UPDATE SET user_id = excluded.user_id, p256dh = excluded.p256dh,
               auth = excluded.auth""", (g.user["id"], endpoint, str(keys["p256dh"])[:200], str(keys["auth"])[:100]))
    return jsonify(ok=True)


@bp.route("/push/unsubscribe", methods=["POST"])
@login_required()
def push_unsubscribe():
    data = request.get_json(silent=True) or {}
    execute("DELETE FROM push_subs WHERE endpoint = ? AND user_id = ?", (str(data.get("endpoint", "")), g.user["id"]))
    return jsonify(ok=True)


# ---------- 보내기 (요청을 막지 않도록 뒤에서) ----------

def _send(subs, payload, db_path, vapid_path):
    gone = []
    for s in subs:
        try:
            webpush(subscription_info={"endpoint": s["endpoint"], "keys": {"p256dh": s["p256dh"], "auth": s["auth"]}},
                    data=payload, vapid_private_key=vapid_path, vapid_claims={"sub": "mailto:admin@localhost"},
                    ttl=86400, timeout=10)
        except WebPushException as e:
            if e.response is not None and e.response.status_code in (404, 410):
                gone.append(s["endpoint"])  # 구독이 끝난 브라우저
        except Exception:  # noqa: BLE001 - 알림 실패가 앱을 멈추면 안 된다
            pass
    if gone:
        conn = sqlite3.connect(db_path)
        conn.executemany("DELETE FROM push_subs WHERE endpoint = ?", [(e,) for e in gone])
        conn.commit()
        conn.close()


def _dispatch(subs, title, body, url):
    if not subs or not push_enabled():
        return
    _vapid()
    payload = json.dumps({"title": title, "body": body[:120], "url": url}, ensure_ascii=False)
    threading.Thread(target=_send, args=([dict(s) for s in subs], payload, current_app.config["DATABASE"],
                                         _vapid_path()), daemon=True).start()


def notify_users(user_ids, title, body, url="/"):
    ids = list({int(u) for u in user_ids})
    if not ids:
        return
    marks = ",".join("?" * len(ids))
    _dispatch(query(f"SELECT * FROM push_subs WHERE user_id IN ({marks})", ids), title, body, url)


def notify_student(student_id, title, body, url="/"):
    u = query("SELECT id FROM users WHERE student_id = ?", (student_id,), one=True)
    if u:
        notify_users([u["id"]], title, body, url)


def notify_class(class_id, title, body, url="/"):
    """class_id 가 None 이면 모든 학생."""
    if class_id is None:
        rows = query("SELECT u.id FROM users u WHERE u.role = 'student'")
    else:
        rows = query("""SELECT u.id FROM users u JOIN students s ON s.id = u.student_id
                        WHERE s.class_id = ? AND s.active = 1""", (class_id,))
    notify_users([r["id"] for r in rows], title, body, url)
