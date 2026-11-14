"""11/14 수정 묶음: 질문 사진 3장, TH캐스트, 모의고사 총평, 영단어 이어 풀기, MDS 단과, 과제 삭제."""
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from db import execute, query  # noqa: E402
from security import hash_password  # noqa: E402

PW = "Teach3r!pass"
PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
       b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")


class Update1114(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False,
                               "DATABASE": os.path.join(self.tmp.name, "t.sqlite3"), "UPLOAD_DIR": os.path.join(self.tmp.name, "up")})
        os.makedirs(self.app.config["UPLOAD_DIR"], exist_ok=True)
        with self.app.app_context():
            from db import init_db
            init_db(self.app.config["DATABASE"])
            execute("INSERT INTO classes (name) VALUES ('시대인재 대구 MDS 점심반')")
            execute("DELETE FROM settings WHERE key = 'mig_mds_dangwa'")       # 배포 직후 처음 켜질 때처럼
            init_db(self.app.config["DATABASE"])
            execute("INSERT INTO users (role, username, password_hash) VALUES ('teacher', 'teacher', ?)", (hash_password(PW),))
            self.cid = query("SELECT id FROM classes", one=True)["id"]
            sid = execute("INSERT INTO students (class_id, name, student_no) VALUES (?, '김민수', 'minsu')", (self.cid,))
            execute("INSERT INTO users (role, username, password_hash, student_id, nickname) VALUES ('student', 'minsu', ?, ?, '민수')",
                    (hash_password("Minsu!2026xx"), sid))
        from views import auth
        auth._ip_attempts.clear()
        self.t = self.app.test_client(); self.t.post("/login", data={"username": "teacher", "password": PW})
        self.s = self.app.test_client(); self.s.post("/login", data={"username": "minsu", "password": "Minsu!2026xx"})

    def tearDown(self):
        with self.app.app_context():
            from db import close_db
            close_db()
        self.tmp.cleanup()

    def test_mds_is_dangwa_and_tasks_gone(self):
        with self.app.app_context():
            self.assertEqual(query("SELECT track FROM classes", one=True)["track"], "단과")
        self.assertEqual(self.s.get("/s/tasks").status_code, 404)
        self.assertEqual(self.t.get("/t/tasks").status_code, 404)
        home = self.s.get("/s/").data.decode()
        self.assertIn("공지", home); self.assertIn("질답 게시판", home); self.assertIn("교재 구매", home)
        self.assertNotIn("안 낸 과제", home)
        self.assertIn("data-back", self.s.get("/s/notices").data.decode())     # 뒤로 버튼

    def test_three_photos(self):
        files = [(io.BytesIO(PNG), f"p{i}.png") for i in range(3)]
        r = self.s.post("/s/questions", data={"qtype": "학습질문", "title": "[기출-1-2]", "body": "질문", "image": files},
                        content_type="multipart/form-data")
        self.assertEqual(r.status_code, 302)
        qid = int(r.headers["Location"].split("/questions/")[1].split("?")[0])
        page = self.s.get(f"/s/questions/{qid}").data.decode()
        self.assertEqual(page.count('class="question-img"'), 3)
        four = [(io.BytesIO(PNG), f"q{i}.png") for i in range(4)]
        r = self.s.post("/s/questions", data={"qtype": "학습질문", "title": "t", "body": "b", "image": four}, content_type="multipart/form-data")
        self.assertIn("3장까지", r.data.decode())

    def test_cast_teacher_only(self):
        self.assertEqual(self.s.get("/cast/new").status_code, 403)
        r = self.t.post("/cast/new", data={"title": "11월 편지", "body": "끝까지 가자.", "video_url": "https://youtu.be/dQw4w9WgXcQ"})
        self.assertEqual(r.status_code, 302)
        page = self.s.get(r.headers["Location"]).data.decode()
        self.assertIn("youtube-nocookie.com/embed/dQw4w9WgXcQ", page)
        self.assertIn("11월 편지", self.s.get("/s/").data.decode())
        self.assertIn("유튜브 주소만", self.t.post("/cast/new", data={"title": "x", "video_url": "https://evil.example"}, follow_redirects=True).data.decode())

    def test_vocab_resume(self):
        st = self.s.post("/s/games/vocab/start", json={}).get_json()
        rid = st["round_id"]
        with self.app.app_context():
            ans = json.loads(query("SELECT answer FROM game_rounds WHERE id=?", (rid,), one=True)["answer"])
        from tests.test_app import right_pick
        for i in range(3):
            self.s.post(f"/s/games/vocab/{rid}/check", json={"i": i, "pick": right_pick(ans[i])})
        self.assertIn("이어서 풀기", self.s.get("/s/games/vocab").data.decode())
        self.assertIn("3/20 풀이 중", self.s.get("/s/games/").data.decode())
        again = self.s.post("/s/games/vocab/start", json={"resume": 1}).get_json()
        self.assertEqual((again["round_id"], again["done"], again["score"]), (rid, 3, 3))
        self.assertNotIn("hint", json.dumps(again["questions"]))

    def test_wordmaster_list_and_confusable_choices(self):
        import vocab
        self.assertEqual(vocab.ORDER[:3], ["abandon", "feature", "colleague"])          # 책 Day 01 순서
        self.assertEqual(vocab.ORDER[20], "commercial")                                 # Day 02 첫 단어
        self.assertGreaterEqual(len(vocab.WORDS), 1600)
        self.assertEqual(vocab._near("adapt")[0], "adopt")                              # 헷갈리는 단어가 보기로
        self.assertIn("preserve", vocab._near("reserve")[:3])
        for w in vocab.ORDER[:200]:
            q = vocab._mc(w)
            self.assertEqual(len(set(q["choices"])), 4)
            others = vocab._others(w, 3)
            self.assertFalse(any(vocab._SENSE[x] & vocab._SENSE[w] for x in others))    # 정답이 둘이 되지 않게
