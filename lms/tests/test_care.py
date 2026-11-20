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

    def _exam(self):
        """모의고사 1회에 김하나 결과 반영: 3·4번(산과 염기) 틀림."""
        from openpyxl import Workbook
        wb = Workbook(); ws = wb.active; ws.title = "OMR"
        ws.append(["이름", "수험번호", 1, 2, 3, 4]); ws.append(["정답", "", 1, 2, 3, 4]); ws.append(["배점", "", 2, 2, 3, 3])
        ws.append(["김하나", "11112222", 1, 2, 1, 1])
        inf = wb.create_sheet("문항정보"); inf.append(["문항번호", "단원"])
        for i, u in ((1, "역학 시스템"), (2, "역학 시스템"), (3, "산과 염기"), (4, "산과 염기")):
            inf.append([i, u])
        buf = io.BytesIO(); wb.save(buf)
        with self.app.app_context():
            mid = query("""SELECT m.id FROM mocks m JOIN books b ON b.id = m.book_id WHERE b.title = '모의고사' AND m.round_no = 1""", one=True)["id"]
        self.ta.post(f"/t/mocks/{mid}/omr", data={"file": (io.BytesIO(buf.getvalue()), "o.xlsx")}, content_type="multipart/form-data")
        return mid

    def test_exam_paper_photo_and_item_review(self):
        mid = self._exam()
        self.assertEqual(self.c1.get("/s/homework").status_code, 404)                    # 숙제 사진 제출은 없앰
        self.assertEqual(self.c2.post(f"/s/analysis/{mid}/paper", data={"image": [(io.BytesIO(PNG), "a.png")]},
                                      content_type="multipart/form-data").status_code, 404)  # 결과 없는 학생
        self.c1.post(f"/s/analysis/{mid}/paper", data={"image": [(io.BytesIO(PNG), "a.png")], "note": "4번 풀이 봐 주세요"},
                     content_type="multipart/form-data")
        with self.app.app_context():
            p = query("SELECT * FROM exam_papers", one=True)
            fid = query("SELECT file_id FROM exam_paper_files", one=True)["file_id"]
        self.assertEqual(p["status"], "submitted")
        self.assertIn("검사 중", self.c1.get(f"/s/analysis?mock={mid}").data.decode())
        self.assertNotEqual(self.c2.get(f"/s/file/{fid}").status_code, 200)
        page = self.ta.get(f"/t/papers/{p['id']}").data.decode()
        self.assertIn("4번 풀이 봐 주세요", page); self.assertIn('name="r3"', page); self.assertNotIn('name="r1"', page)  # 틀린 문항만
        self.ta.post(f"/t/papers/{p['id']}", data={"r3": "계산 실수", "m3": "몰 비를 1:1로 계산", "r4": "자료 해석", "comment": "그래프 축부터 확인"})
        page = self.c1.get(f"/s/analysis?mock={mid}").data.decode()
        self.assertIn("몰 비를 1:1로 계산", page); self.assertIn("그래프 축부터 확인", page); self.assertIn("박조교 조교 첨삭", page)
        r = self.c1.post(f"/s/analysis/{mid}/paper", data={"image": [(io.BytesIO(PNG), "b.png")]}, content_type="multipart/form-data",
                         follow_redirects=True)
        self.assertIn("다시 올릴 수 없습니다", r.data.decode())
        with self.app.app_context():
            from datetime import date
            from views.care import paper_review_counts
            uid = query("SELECT id FROM users WHERE username = 'ta'", one=True)["id"]
            self.assertEqual(paper_review_counts(date.today().strftime("%Y-%m")), {uid: 1})

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
        mid = self._exam()
        page = self.c1.get(f"/s/analysis?mock={mid}").data.decode()
        self.assertIn("단원별 성취도", page); self.assertIn("산과 염기", page)
        self.assertIn("TOPIC 24", page)                                         # 같은 단원 Quiz 로 연결
        self.c1.post(f"/s/analysis/{mid}/paper", data={"image": [(io.BytesIO(PNG), "a.png")]}, content_type="multipart/form-data")
        with self.app.app_context():
            pid = query("SELECT id FROM exam_papers", one=True)["id"]
        self.ta.post(f"/t/papers/{pid}", data={"r3": "자료 해석", "m3": "x축을 시간으로 읽음", "comment": "그래프 축부터 확인"})
        self.ta.post(f"/t/students/{self.s1}/parent-link")
        with self.app.app_context():
            tok = query("SELECT parent_token FROM students WHERE id = ?", (self.s1,), one=True)["parent_token"]
        anon = self.app.test_client()
        page = anon.get(f"/p/{tok}").data.decode()
        for word in ("김하나", "득점률", "40", "자료 해석", "x축을 시간으로 읽음", "그래프 축부터 확인", "산과 염기", "모의고사 1회"):
            self.assertIn(word, page)
        self.assertIn("noindex", page)
        self.assertEqual(anon.get("/p/" + "x" * 24).status_code, 404)
        self.assertEqual(anon.get("/p/short").status_code, 404)
        sms = self.ta.get(f"/t/mocks/{mid}/sms").data.decode()
        self.assertIn(f"/p/{tok}", sms)

if __name__ == "__main__":
    unittest.main()
