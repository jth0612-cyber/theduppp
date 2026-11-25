"""단과/재종 구분 가입과 RFID 카드 출결 점검."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from db import execute, query  # noqa: E402
from security import hash_password  # noqa: E402

PW = "Teach3r!pass"


class TrackTest(unittest.TestCase):
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
        r = self.t.post("/t/classes", data={"name": "단과 화목반", "track": "단과"})
        self.dan = int(r.headers["Location"].rsplit("/", 1)[-1])
        r = self.t.post("/t/classes", data={"name": "재종 1반", "track": "재종"})
        self.jae = int(r.headers["Location"].rsplit("/", 1)[-1])
        with self.app.app_context():
            execute("INSERT INTO student_codes (class_id, code) VALUES (?, 'DANCODE01')", (self.dan,))
            execute("INSERT INTO student_codes (class_id, code) VALUES (?, 'JAECODE01')", (self.jae,))
            # 단과 반 시간표: 화요일 14:00~17:00
            execute("INSERT INTO timetable (class_id, weekday, starts, ends, title) VALUES (?, 1, '14:00', '17:00', '통합과학')", (self.dan,))

    def tearDown(self):
        with self.app.app_context():
            from db import close_db
            close_db()
        self.tmp.cleanup()

    def signup(self, track, code, no, name="김민수"):
        c = self.app.test_client()
        r = c.post("/signup", data={"track": track, "code": code, "name": name, "student_no": no, "password": "Signup!2026x",
                                    "confirm": "Signup!2026x", "consent": "1"})
        return c, r

    def test_pick_track_first(self):
        page = self.app.test_client().get("/signup").data.decode()
        self.assertIn("track-box", page)
        self.assertIn("단과", page)
        self.assertIn("재종", page)
        self.assertIn("카드 번호", self.app.test_client().get("/signup?track=단과").data.decode())

    def test_dangwa_uses_card_number(self):
        _, r = self.signup("단과", "DANCODE01", "abc-id")
        self.assertIn("카드 번호는", r.data.decode())                       # 카드 번호 모양이 아니면 거부
        _, r = self.signup("단과", "DANCODE01", "00 1234 5678")
        self.assertEqual(r.status_code, 302)
        with self.app.app_context():
            self.assertIsNotNone(query("SELECT 1 FROM users WHERE username = '0012345678'", one=True))
        c = self.app.test_client()                                          # 카드 번호로 로그인
        self.assertEqual(c.post("/login", data={"username": "0012345678", "password": "Signup!2026x"}).status_code, 302)

    def test_track_must_match_code(self):
        _, r = self.signup("재종", "DANCODE01", "minsu01")
        self.assertIn("단과 반 코드예요", r.data.decode())
        _, r = self.signup("재종", "JAECODE01", "minsu01")
        self.assertEqual(r.status_code, 302)

    def test_lists_are_separated(self):
        self.signup("단과", "DANCODE01", "0012345678", name="단과생")
        self.signup("재종", "JAECODE01", "jaejong1", name="재종생")
        dan = self.t.get("/t/students?track=단과").data.decode()
        self.assertIn("단과생", dan)
        self.assertNotIn("재종생", dan)
        jae = self.t.get("/t/classes?track=재종").data.decode()
        self.assertIn("재종 1반", jae)
        self.assertNotIn("단과 화목반", jae)


if __name__ == "__main__":
    unittest.main()
