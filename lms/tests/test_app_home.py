"""앱 홈(Capacitor 앱 사용자 에이전트 THeduApp/ 또는 ?view=app)과 과제 화면."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app  # noqa: E402
from db import execute  # noqa: E402
from security import hash_password  # noqa: E402

PW = "Test-pass-1234"
APP_UA = {"User-Agent": "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 Chrome/124 Mobile Safari/537.36 THeduApp/1.0"}


class AppHome(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False,
                               "DATABASE": os.path.join(self.tmp.name, "t.sqlite3"), "UPLOAD_DIR": os.path.join(self.tmp.name, "up")})
        with self.app.app_context():
            c = execute("INSERT INTO classes (name) VALUES ('A반')")
            self.sid = execute("INSERT INTO students (class_id, name, student_no) VALUES (?, '김하나', '270001')", (c,))
            execute("INSERT INTO users (role, username, password_hash, student_id, nickname) VALUES ('student', '270001', ?, ?, '산책하는 나무늘보')",
                    (hash_password(PW), self.sid))
            execute("INSERT INTO notices (class_id, title, body, tag) VALUES (?, '토요일 특강 안내', '내용', '공지')", (c,))
            execute("INSERT INTO student_codes (class_id, code, student_id) VALUES (?, 'A0000001', ?)", (c, self.sid))
            import sysdata
            sysdata.store({"과제": [{"학생코드": "A0000001", "날짜": "2026-11-20", "교재": "Squeeze 14호", "범위": "6단원", "제출": ""},
                                   {"학생코드": "A0000001", "날짜": "2026-11-13", "교재": "Squeeze 13호", "범위": "5단원", "제출": "O",
                                    "맞은수": 17, "문항수": 20}]}, "test")
        from views import auth
        auth._ip_attempts.clear()
        self.c = self.app.test_client()
        self.c.post("/login", data={"username": "270001", "password": PW})

    def tearDown(self):
        with self.app.app_context():
            from db import close_db
            close_db()
        self.tmp.cleanup()

    def test_app_home_only_in_app(self):
        web = self.c.get("/s/").data.decode()
        self.assertNotIn("ah-apps", web)                                  # 웹 홈은 그대로
        page = self.c.get("/s/", headers=APP_UA).data.decode()
        self.assertIn("ah-apps", page)
        for word in ("김하나", "남은 과제", "복습할 오답", "통과 Quiz", "시험 분석", "토요일 특강 안내", "has-shell"):
            self.assertIn(word, page)
        self.assertIn('aria-label="1개"', page)                           # 안 읽은 공지 1, 안 낸 과제 1
        self.assertIn("ah-apps", self.c.get("/s/?view=app").data.decode())
        self.assertIn("in-app", self.c.get("/static/inapp.js").data.decode())

    def test_tasks_page(self):
        page = self.c.get("/s/tasks").data.decode()
        self.assertIn("Squeeze 14호", page); self.assertIn('안 낸 과제 <b class="txt-danger">1개</b>', page); self.assertIn("17<small>/20</small>", page)


if __name__ == "__main__":
    unittest.main()
