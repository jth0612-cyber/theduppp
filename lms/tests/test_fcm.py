"""앱 푸시: 기기 토큰 등록·삭제, notify_users 가 앱 토큰에도 보내는지, FCM 서명·메시지 모양, 끝난 토큰 지우기."""
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app  # noqa: E402
from db import execute, query  # noqa: E402
from security import hash_password  # noqa: E402

PW = "Test-pass-1234"
UA = {"User-Agent": "Mozilla/5.0 (Linux; Android 15) Chrome/124 Mobile THeduApp/1.0"}


class Fcm(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.key = os.path.join(self.tmp.name, "firebase.json")
        self.app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False, "FIREBASE_KEY": self.key,
                               "DATABASE": os.path.join(self.tmp.name, "t.sqlite3"), "UPLOAD_DIR": os.path.join(self.tmp.name, "up")})
        with self.app.app_context():
            c = execute("INSERT INTO classes (name) VALUES ('A반')")
            s = execute("INSERT INTO students (class_id, name, student_no) VALUES (?, '김하나', '270001')", (c,))
            self.uid = execute("INSERT INTO users (role, username, password_hash, student_id) VALUES ('student', '270001', ?, ?)",
                               (hash_password(PW), s))
        from views import auth
        auth._ip_attempts.clear()
        self.c = self.app.test_client()
        self.c.post("/login", data={"username": "270001", "password": PW})

    def tearDown(self):
        with self.app.app_context():
            from db import close_db
            close_db()
        self.tmp.cleanup()

    def test_token_register_delete_and_script_only_in_app(self):
        self.assertEqual(self.c.post("/push/app-token", json={"token": "", "platform": "android"}).status_code, 400)
        self.c.post("/push/app-token", json={"token": "tok-1", "platform": "android"})
        self.c.post("/push/app-token", json={"token": "tok-1", "platform": "android"})      # 같은 기기는 한 줄
        with self.app.app_context():
            self.assertEqual(query("SELECT COUNT(*) AS n FROM app_tokens", one=True)["n"], 1)
        self.assertIn("app_push.js", self.c.get("/s/", headers=UA).data.decode())
        self.assertNotIn("app_push.js", self.c.get("/s/").data.decode())
        self.c.post("/push/app-token/delete", json={"token": "tok-1"})
        with self.app.app_context():
            self.assertIsNone(query("SELECT 1 FROM app_tokens", one=True))

    def test_notify_users_reaches_app_tokens(self):
        self.c.post("/push/app-token", json={"token": "tok-1", "platform": "ios"})
        with self.app.app_context(), mock.patch("fcm.dispatch") as d:
            from views.pwa import notify_users
            notify_users([self.uid], "새 공지", "토요일 특강", "/s/notices/1")
        d.assert_called_once_with(["tok-1"], "새 공지", "토요일 특강", "/s/notices/1")

    def test_send_signs_and_drops_dead_tokens(self):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        pem = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
        json.dump({"client_email": "x@p.iam.gserviceaccount.com", "private_key": pem, "project_id": "p",
                   "token_uri": "https://oauth2.googleapis.com/token"}, open(self.key, "w"))
        self.c.post("/push/app-token", json={"token": "dead", "platform": "android"})
        self.c.post("/push/app-token", json={"token": "live", "platform": "android"})
        sent = []

        class R(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *a): self.close()

        def fake(req, timeout=10):
            if "oauth2" in req.full_url:
                self.assertIn(b"assertion=", req.data)
                return R(json.dumps({"access_token": "AT", "expires_in": 3600}).encode())
            body = json.loads(req.data)
            sent.append(body["message"]["token"])
            self.assertEqual(req.headers["Authorization"], "Bearer AT")
            self.assertEqual(body["message"]["data"]["url"], "/s/")
            if body["message"]["token"] == "dead":
                raise urllib.error.HTTPError(req.full_url, 404, "NOT_FOUND", {}, None)
            return R(b"{}")
        import fcm
        fcm._token.update(value=None, exp=0)
        with self.app.app_context(), mock.patch("urllib.request.urlopen", side_effect=fake):
            fcm._send(["dead", "live"], "제목", "본문", "/s/", self.key, self.app.config["DATABASE"])
            self.assertEqual(sent, ["dead", "live"])
            self.assertEqual([r["token"] for r in query("SELECT token FROM app_tokens")], ["live"])


if __name__ == "__main__":
    unittest.main()
