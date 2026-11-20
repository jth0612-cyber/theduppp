"""학습 관리: 숙제 인증·문항별 첨삭, 수업 기록, 취약 단원, 학부모 리포트."""
import io
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from db import execute, query  # noqa: E402
from security import encrypt, hash_password  # noqa: E402

PW = "Teach3r!pass"
PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
       b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")


class Care(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False, "ANALYSIS_TTL": 0,
                               "DATABASE": os.path.join(self.tmp.name, "t.sqlite3"), "UPLOAD_DIR": os.path.join(self.tmp.name, "up")})
        os.makedirs(self.app.config["UPLOAD_DIR"], exist_ok=True)
        with self.app.app_context():
            from db import init_db
            init_db(self.app.config["DATABASE"])
            execute("INSERT INTO users (role, username, password_hash, display_name) VALUES ('assistant', 'ta', ?, '박조교')", (hash_password(PW),))
            self.a = execute("INSERT INTO classes (name) VALUES ('A반')")
            self.b = execute("INSERT INTO classes (name) VALUES ('B반')")
            self.s1 = execute("INSERT INTO students (class_id, name, student_no, parent_phone_enc) VALUES (?, '김하나', '270001', ?)",
                              (self.a, encrypt("010-1111-2222")))
            self.s2 = execute("INSERT INTO students (class_id, name, student_no) VALUES (?, '이두리', '270002')", (self.b,))
            for no, sid in (("270001", self.s1), ("270002", self.s2)):
                execute("INSERT INTO users (role, username, password_hash, student_id) VALUES ('student', ?, ?, ?)", (no, hash_password(PW), sid))
        from views import auth
        auth._ip_attempts.clear()
        self.ta = self.login("ta")
        self.c1 = self.login("270001")
        self.c2 = self.login("270002")

    def login(self, u):
        c = self.app.test_client()
        c.post("/login", data={"username": u, "password": PW})
        return c

    def tearDown(self):
        with self.app.app_context():
            from db import close_db
            close_db()
        self.tmp.cleanup()

    def test_homework_submit_and_item_review(self):
        r = self.ta.post("/t/homework", data={"title": "Squeeze 3주차", "class_id": str(self.a), "due": "2099-01-01T22:00", "n_items": "4"})
        hid = int(r.headers["Location"].rsplit("/", 1)[-1])
        self.assertIn("Squeeze 3주차", self.c1.get("/s/homework").data.decode())
        self.assertNotIn("Squeeze 3주차", self.c2.get("/s/homework").data.decode())      # 다른 반
        self.assertEqual(self.c2.get(f"/s/homework/{hid}").status_code, 404)
        self.assertIn('class="count">1<', self.c1.get("/s/homework").data.decode())   # 안 낸 숙제 수
        self.c1.post(f"/s/homework/{hid}", data={"image": [(io.BytesIO(PNG), "a.png")], "note": "4번 모르겠어요"},
                     content_type="multipart/form-data")
        with self.app.app_context():
            sub = query("SELECT * FROM hw_submissions", one=True)
            fid = query("SELECT file_id FROM hw_files", one=True)["file_id"]
        self.assertEqual(sub["status"], "submitted")
        self.assertIn("검사 중", self.c1.get(f"/s/homework/{hid}").data.decode())
        self.assertNotEqual(self.c2.get(f"/s/file/{fid}").status_code, 200)            # 남의 숙제 사진
        self.assertEqual(self.ta.get(f"/s/file/{fid}").status_code, 200)
        page = self.ta.get(f"/t/homework/review/{sub['id']}").data.decode()
        self.assertIn("4번 모르겠어요", page)
        self.ta.post(f"/t/homework/review/{sub['id']}", data={"n": "4", "v1": "O", "v2": "O", "v3": "X", "r3": "계산 실수", "m3": "부호",
                                                             "v4": "X", "r4": "개념 부족", "comment": "풀이 순서가 좋아요."})
        page = self.c1.get(f"/s/homework/{hid}").data.decode()
        self.assertIn("첨삭 완료", self.c1.get("/s/homework").data.decode())
        self.assertIn("2</b> / 4 정답", page); self.assertIn("계산 실수", page); self.assertIn("풀이 순서가 좋아요.", page)
        r = self.c1.post(f"/s/homework/{hid}", data={"image": [(io.BytesIO(PNG), "b.png")]}, content_type="multipart/form-data",
                         follow_redirects=True)
        self.assertIn("다시 올릴 수 없습니다", r.data.decode())
        with self.app.app_context():
            from datetime import date
            from views.care import hw_review_counts
            uid = query("SELECT id FROM users WHERE username = 'ta'", one=True)["id"]
            self.assertEqual(hw_review_counts(date.today().strftime("%Y-%m")), {uid: 1})

    def test_lessons_by_class(self):
        self.ta.post("/t/lessons", data={"class_id": str(self.a), "title": "TOPIC 24 중화 반응", "day": "2026-11-20",
                                         "image": [(io.BytesIO(PNG), "n.png")]}, content_type="multipart/form-data")
        self.assertIn("TOPIC 24 중화 반응", self.c1.get("/s/lessons").data.decode())
        self.assertNotIn("TOPIC 24 중화 반응", self.c2.get("/s/lessons").data.decode())
        with self.app.app_context():
            fid = query("SELECT file_id FROM lesson_files", one=True)["file_id"]
        self.assertEqual(self.c1.get(f"/s/file/{fid}").status_code, 200)
        self.assertNotEqual(self.c2.get(f"/s/file/{fid}").status_code, 200)

    def test_parent_report_and_weak_unit(self):
        # 시험: 단원이 있는 문항정보로 OMR 반영
        from openpyxl import Workbook
        wb = Workbook(); ws = wb.active; ws.title = "OMR"
        ws.append(["이름", "수험번호", 1, 2, 3, 4]); ws.append(["정답", "", 1, 2, 3, 4]); ws.append(["배점", "", 2, 2, 3, 3])
        ws.append(["김하나", "11112222", 1, 2, 1, 1])                          # 3·4번(산과 염기) 틀림
        inf = wb.create_sheet("문항정보"); inf.append(["문항번호", "단원"])
        for i, u in ((1, "역학 시스템"), (2, "역학 시스템"), (3, "산과 염기"), (4, "산과 염기")):
            inf.append([i, u])
        buf = io.BytesIO(); wb.save(buf)
        with self.app.app_context():
            mid = query("""SELECT m.id FROM mocks m JOIN books b ON b.id = m.book_id WHERE b.title = '모의고사' AND m.round_no = 1""", one=True)["id"]
        self.ta.post(f"/t/mocks/{mid}/omr", data={"file": (io.BytesIO(buf.getvalue()), "o.xlsx")}, content_type="multipart/form-data")
        page = self.c1.get(f"/s/analysis?mock={mid}").data.decode()
        self.assertIn("단원별 성취도", page); self.assertIn("산과 염기", page)
        self.assertIn("TOPIC 24", page)                                         # 같은 단원 Quiz 로 연결
        # 숙제 정답률
        r = self.ta.post("/t/homework", data={"title": "숙제1", "class_id": str(self.a), "due": "2099-01-01T22:00", "n_items": "2"})
        hid = int(r.headers["Location"].rsplit("/", 1)[-1])
        with self.app.app_context():
            execute("UPDATE homeworks SET due_at = datetime('now', 'localtime') WHERE id = ?", (hid,))
        self.c1.post(f"/s/homework/{hid}", data={"image": [(io.BytesIO(PNG), "a.png")]}, content_type="multipart/form-data")
        with self.app.app_context():
            sid = query("SELECT id FROM hw_submissions", one=True)["id"]
        self.ta.post(f"/t/homework/review/{sid}", data={"n": "2", "v1": "O", "v2": "X", "r2": "자료 해석", "comment": "그래프 축부터 확인"})
        # 학부모 링크: 강사·조교가 만들고, 로그인 없이 열린다
        self.ta.post(f"/t/students/{self.s1}/parent-link")
        with self.app.app_context():
            tok = query("SELECT parent_token FROM students WHERE id = ?", (self.s1,), one=True)["parent_token"]
        anon = self.app.test_client()
        page = anon.get(f"/p/{tok}").data.decode()
        for word in ("김하나", "숙제 정답률", "50", "자료 해석", "그래프 축부터 확인", "산과 염기", "모의고사 1회"):
            self.assertIn(word, page)
        self.assertIn("noindex", page)
        self.assertEqual(anon.get("/p/" + "x" * 24).status_code, 404)
        self.assertEqual(anon.get("/p/short").status_code, 404)
        # 학부모 문자 끝에 링크
        sms = self.ta.get(f"/t/mocks/{mid}/sms").data.decode()
        self.assertIn(f"/p/{tok}", sms)


if __name__ == "__main__":
    unittest.main()
