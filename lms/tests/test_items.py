"""문항 그림: 조교 올리기(파일 이름 = 번호), 학생은 볼 수 있는 회차만·워터마크, 시험 분석 번호 링크, 질문 쓰기에 문항 불러오기."""
import io
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app  # noqa: E402
from db import execute, query  # noqa: E402
from security import hash_password  # noqa: E402

PW = "Test-pass-1234"


def png(w=600, h=400, color=(255, 255, 255)):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, "PNG")
    return buf.getvalue()


class Items(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False,
                               "DATABASE": os.path.join(self.tmp.name, "t.sqlite3"), "UPLOAD_DIR": os.path.join(self.tmp.name, "up")})
        os.makedirs(self.app.config["UPLOAD_DIR"], exist_ok=True)
        with self.app.app_context():
            execute("INSERT INTO users (role, username, password_hash, display_name) VALUES ('assistant', 'ta', ?, '박조교')", (hash_password(PW),))
            c = execute("INSERT INTO classes (name) VALUES ('A반')")
            s = execute("INSERT INTO students (class_id, name, student_no) VALUES (?, '김하나', '270001')", (c,))
            self.uid = execute("INSERT INTO users (role, username, password_hash, student_id) VALUES ('student', '270001', ?, ?)",
                               (hash_password(PW), s))
            self.mid = query("""SELECT m.id FROM mocks m JOIN books b ON b.id = m.book_id
                                WHERE b.title = '모의고사' AND m.round_no = 1""", one=True)["id"]
            self.other = query("""SELECT m.id FROM mocks m JOIN books b ON b.id = m.book_id
                                  WHERE b.title = '모의고사' AND m.round_no = 2""", one=True)["id"]
            execute("UPDATE mocks SET n_items = 3, full_score = 6, answer_key = '[1,2,3]', points = '[2,2,2]' WHERE id IN (?, ?)", (self.mid, self.other))
            execute("INSERT INTO mock_entries (mock_id, user_id, mode, answers, score) VALUES (?, ?, 'answers', '113', 4)", (self.mid, self.uid))
        from views import auth
        auth._ip_attempts.clear()
        self.ta, self.s = self.app.test_client(), self.app.test_client()
        self.ta.post("/login", data={"username": "ta", "password": PW})
        self.s.post("/login", data={"username": "270001", "password": PW})

    def tearDown(self):
        with self.app.app_context():
            from db import close_db
            close_db()
        self.tmp.cleanup()

    def up(self, mid, *names):
        return self.ta.post(f"/t/mocks/{mid}/items", data={"image": [(io.BytesIO(png()), n) for n in names]},
                            content_type="multipart/form-data", follow_redirects=True)

    def test_upload_view_watermark_and_question_prefill(self):
        r = self.up(self.mid, "01.png", "q02.png", "표지.png")
        self.assertIn("2장을 올렸습니다", r.data.decode()); self.assertIn("표지.png", r.data.decode())
        self.up(self.other, "01.png")
        with self.app.app_context():
            self.assertEqual(query("SELECT COUNT(*) AS n FROM mock_item_images WHERE mock_id = ?", (self.mid,), one=True)["n"], 2)
        self.up(self.mid, "2.png")                                                    # 같은 번호는 바뀐다
        with self.app.app_context():
            self.assertEqual(query("SELECT COUNT(*) AS n FROM files", one=True)["n"], 3)
        img = self.s.get(f"/items/{self.mid}/2.png")
        self.assertEqual(img.status_code, 200); self.assertIn("no-store", img.headers["Cache-Control"])
        from PIL import Image
        self.assertNotEqual(Image.open(io.BytesIO(img.data)).convert("RGB").getextrema(), ((255, 255), (255, 255), (255, 255)))   # 워터마크가 새겨짐
        self.assertEqual(self.s.get(f"/items/{self.other}/1.png").status_code, 404)    # 내 결과·평가가 없는 회차는 못 본다
        page = self.s.get(f"/s/analysis?mock={self.mid}").data.decode()
        self.assertIn(f"/s/analysis/{self.mid}/items/2", page); self.assertIn("번호를 누르면 문항", page)
        view = self.s.get(f"/s/analysis/{self.mid}/items/2").data.decode()
        self.assertIn("모의고사 1회 2번", view); self.assertIn("이 문항에 필기해서 질문", view)
        q = self.s.get(f"/s/questions?ask=1&mock={self.mid}&item=2").data.decode()
        self.assertIn("data-ink", q); self.assertIn("[모의고사 1회 2번]", q); self.assertIn("ink.js", q)
        self.assertNotIn("data-ink ", self.s.get(f"/s/questions?ask=1&mock={self.other}&item=1").data.decode())
        self.ta.post(f"/t/mocks/{self.mid}/items/2/delete")
        self.assertEqual(self.s.get(f"/items/{self.mid}/2.png").status_code, 404)


if __name__ == "__main__":
    unittest.main()
