"""개인정보처리방침, 이용약관, 개인정보 삭제 요청 점검."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from db import execute, query  # noqa: E402
from security import hash_password  # noqa: E402

PW = "Teach3r!pass"


class LegalTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False,
                               "DATABASE": os.path.join(self.tmp.name, "t.sqlite3"), "UPLOAD_DIR": os.path.join(self.tmp.name, "up")})
        os.makedirs(self.app.config["UPLOAD_DIR"], exist_ok=True)
        with self.app.app_context():
            from db import init_db
            init_db(self.app.config["DATABASE"])
            execute("INSERT INTO users (role, username, password_hash) VALUES ('teacher', 'teacher', ?)", (hash_password(PW),))
        from views import auth
        auth._ip_attempts.clear()
        self.t = self.app.test_client()
        self.t.post("/login", data={"username": "teacher", "password": PW})
        r = self.t.post("/t/classes", data={"name": "재종 1반", "track": "재종"})
        cid = int(r.headers["Location"].rsplit("/", 1)[-1])
        with self.app.app_context():
            execute("INSERT INTO student_codes (class_id, code) VALUES (?, 'JAECODE01')", (cid,))
        self.s = self.app.test_client()
        self.s.post("/signup", data={"track": "재종", "code": "JAECODE01", "name": "김민수", "student_no": "minsu01",
                                     "password": "Signup!2026x", "confirm": "Signup!2026x", "consent": "1", "consent_parent": "1"})

    def tearDown(self):
        with self.app.app_context():
            from db import close_db
            close_db()
        self.tmp.cleanup()

    def test_pages_open_without_login(self):
        c = self.app.test_client()
        p = c.get("/privacy")
        self.assertEqual(p.status_code, 200)
        page = p.data.decode()
        for word in ("모으는 정보", "보관 기간", "lms_session", "만 14세 미만", "개인정보 보호책임자"):
            self.assertIn(word, page)
        t = c.get("/terms")
        self.assertEqual(t.status_code, 200)
        self.assertIn("요금을 받지 않고", t.data.decode())
        login = c.get("/login").data.decode()                      # 로그인 화면 아래에서 바로 갈 수 있다
        self.assertIn('href="/privacy"', login)
        self.assertIn('href="/terms"', login)
        self.assertIn("만 14세 이상", c.get("/signup?track=재종").data.decode())

    def test_erase_request_goes_to_staff_once(self):
        self.assertIn("개인정보 삭제 요청", self.s.get("/password").data.decode())
        r = self.s.post("/s/erase-request")
        self.assertEqual(r.status_code, 302)
        self.s.post("/s/erase-request")                            # 다시 눌러도 한 건만
        with self.app.app_context():
            rows = query("SELECT qtype, status FROM questions WHERE title = '개인정보 삭제 요청'")
        self.assertEqual([(x["qtype"], x["status"]) for x in rows], [("행정문의", "open")])
        self.assertIn("개인정보 삭제 요청", self.t.get("/t/questions?status=open").data.decode())
        self.assertEqual(self.app.test_client().post("/s/erase-request").status_code, 302)   # 로그인 안 하면 로그인 화면으로


if __name__ == "__main__":
    unittest.main()
