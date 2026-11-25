"""앱(안드로이드·아이폰) 푸시 알림: Firebase 클라우드 메시징(FCM) HTTP v1. 요금 없음.

서비스 계정 키(JSON)는 instance/firebase.json 에 둔다(Firebase 콘솔 → 프로젝트 설정 → 서비스 계정 → 새 비공개 키).
파일이 없으면 앱 알림만 꺼지고 나머지는 그대로 동작한다. 새 라이브러리 없이 표준 라이브러리 + cryptography 로 서명한다.
"""
import base64
import json
import os
import sqlite3
import threading
import time
import urllib.error
import urllib.request

from flask import current_app

SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
_token = {"value": None, "exp": 0}
_lock = threading.Lock()


def key_path():
    return current_app.config.get("FIREBASE_KEY") or os.path.join(current_app.instance_path, "firebase.json")


def enabled():
    return os.path.exists(key_path())


def _b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _access_token(sa):
    """서비스 계정 JWT(RS256) → OAuth 액세스 토큰. 1시간짜리라 55분 동안 다시 쓴다."""
    with _lock:
        if _token["value"] and _token["exp"] > time.time() + 60:
            return _token["value"]
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        now = int(time.time())
        head = _b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
        claim = _b64(json.dumps({"iss": sa["client_email"], "scope": SCOPE, "aud": sa["token_uri"], "iat": now, "exp": now + 3600}).encode())
        key = serialization.load_pem_private_key(sa["private_key"].encode(), password=None)
        sig = _b64(key.sign(f"{head}.{claim}".encode(), padding.PKCS1v15(), hashes.SHA256()))
        body = f"grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer&assertion={head}.{claim}.{sig}".encode()
        req = urllib.request.Request(sa["token_uri"], data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=10) as r:
            got = json.load(r)
        _token.update(value=got["access_token"], exp=now + int(got.get("expires_in", 3600)) - 300)
        return _token["value"]


def message(token, title, body, url):
    return {"message": {"token": token, "notification": {"title": title, "body": body[:120]}, "data": {"url": url},
                        "android": {"priority": "high", "notification": {"channel_id": "default"}},
                        "apns": {"payload": {"aps": {"sound": "default"}}}}}


def _send(tokens, title, body, url, key_file, db_path):
    try:
        with open(key_file, encoding="utf-8") as f:
            sa = json.load(f)
        access = _access_token(sa)
    except Exception:  # noqa: BLE001 - 알림 실패가 앱을 멈추면 안 된다
        return
    gone = []
    for t in tokens:
        req = urllib.request.Request(f"https://fcm.googleapis.com/v1/projects/{sa['project_id']}/messages:send",
                                     data=json.dumps(message(t, title, body, url), ensure_ascii=False).encode(),
                                     headers={"Authorization": "Bearer " + access, "Content-Type": "application/json; charset=utf-8"})
        try:
            urllib.request.urlopen(req, timeout=10).close()
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):              # 앱을 지웠거나 토큰이 바뀜 (UNREGISTERED / INVALID_ARGUMENT)
                gone.append(t)
        except Exception:  # noqa: BLE001
            pass
    if gone:
        conn = sqlite3.connect(db_path)
        conn.executemany("DELETE FROM app_tokens WHERE token = ?", [(t,) for t in gone])
        conn.commit()
        conn.close()


def dispatch(tokens, title, body, url):
    """요청을 막지 않도록 뒤에서 보낸다."""
    if not tokens or not enabled():
        return
    threading.Thread(target=_send, args=(list(tokens), title, body, url, key_path(), current_app.config["DATABASE"]), daemon=True).start()
