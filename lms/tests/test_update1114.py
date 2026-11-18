"""11/14 수정 묶음: 질문 사진 3장, 태혁쌤의 cast, 모의고사 총평, 1:1 첨삭, 영단어 이어 풀기, MDS 단과, 과제 삭제."""
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

    def test_core_list_and_confusable_choices(self):
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

    def test_feedback_flow(self):
        """복테&모의 분석 1:1 첨삭: 학생 요청 → 조교 답변 → 학생 알림·사진 권한."""
        with self.app.app_context():
            bid = execute("INSERT INTO books (title, expires_on) VALUES ('주간 복테', '2099-12-31')")
            mid = execute("INSERT INTO mocks (book_id, round_no, n_items, full_score, answer_key, points) VALUES (?, 1, 3, 6, ?, ?)",
                          (bid, json.dumps([1, 2, 3]), json.dumps([2, 2, 2])))
            uid = query("SELECT id FROM users WHERE username = 'minsu'", one=True)["id"]
            execute("INSERT INTO mock_entries (mock_id, user_id, mode, answers, score) VALUES (?, ?, 'answers', '123', 6)", (mid, uid))
            execute("INSERT INTO users (role, username, password_hash, display_name) VALUES ('assistant', 'ta1', ?, '박조교')", (hash_password(PW),))
            execute("INSERT INTO users (role, username, password_hash, student_id) VALUES ('student', 'other', ?, NULL)", (hash_password("Other!2026xx"),))
        page = self.s.get(f"/s/analysis?mock={mid}").data.decode()
        self.assertIn("복테&모의 분석", page); self.assertIn("1:1 첨삭", page)
        # 빈 요청은 거절
        self.s.post(f"/s/analysis/{mid}/feedback", data={"body": ""})
        with self.app.app_context():
            self.assertIsNone(query("SELECT 1 FROM feedback_threads", one=True))
        r = self.s.post(f"/s/analysis/{mid}/feedback", data={"body": "2번 풀이 봐 주세요", "image": [(io.BytesIO(PNG), "a.png")]},
                        content_type="multipart/form-data")
        self.assertEqual(r.status_code, 302)
        ta = self.app.test_client(); ta.post("/login", data={"username": "ta1", "password": PW})
        lst = ta.get("/t/feedback").data.decode()
        self.assertIn("김민수", lst); self.assertIn("주간 복테 1회", lst)
        with self.app.app_context():
            tid = query("SELECT id FROM feedback_threads", one=True)["id"]
            fid = query("SELECT file_id FROM feedback_images", one=True)["file_id"]
        self.assertIn("2번 풀이 봐 주세요", ta.get(f"/t/feedback/{tid}").data.decode())
        ta.post(f"/t/feedback/{tid}", data={"body": "부호를 확인하세요", "image": [(io.BytesIO(PNG), "b.png")]}, content_type="multipart/form-data")
        with self.app.app_context():
            self.assertEqual(query("SELECT status FROM feedback_threads", one=True)["status"], "done")
        home = self.s.get("/s/").data.decode()
        self.assertIn('class="count">1<', home)                          # 메뉴에 새 답변 표시
        page = self.s.get(f"/s/analysis?mock={mid}").data.decode()
        self.assertIn("박조교 조교", page); self.assertIn("부호를 확인하세요", page)
        self.assertNotIn('class="count">1<', self.s.get("/s/").data.decode())   # 읽으면 사라짐
        self.assertEqual(self.s.get(f"/s/file/{fid}").status_code, 200)
        other = self.app.test_client(); other.post("/login", data={"username": "other", "password": "Other!2026xx"})
        self.assertNotEqual(other.get(f"/s/file/{fid}").status_code, 200)
        # 이어서 물으면 다시 대기
        self.s.post(f"/s/analysis/{mid}/feedback", data={"body": "3번도요"})
        with self.app.app_context():
            self.assertEqual(query("SELECT status FROM feedback_threads", one=True)["status"], "wait")
        # 학생은 강사 화면 못 봄
        self.assertNotEqual(self.s.get("/t/feedback").status_code, 200)

    def test_student_menu_folds(self):
        html = self.s.get("/s/notices").data.decode()
        self.assertIn("복테&amp;모의 분석", html)
        self.assertIn('<details class="nav-fold"', html)
        self.assertIn("태혁쌤의 cast", html); self.assertNotIn("TH캐스트", html)

    def test_my_study(self):
        """내 공부: 퀴즈 푼 시간·문제 수, 주간 순위, 일별 그래프, 진도와 초기화."""
        r = self.s.post("/s/games/quiz/start", json={"topic": "13"}).get_json()
        with self.app.app_context():
            ans = json.loads(query("SELECT answer FROM game_rounds WHERE id = ?", (r["round_id"],), one=True)["answer"])
            uid = query("SELECT id FROM users WHERE username = 'minsu'", one=True)["id"]
            execute("UPDATE game_rounds SET started_at = datetime('now', 'localtime', '-50 seconds') WHERE id = ?", (r["round_id"],))
            execute("INSERT INTO focus_logs (user_id, place, minutes) VALUES (?, 'sento', 40)", (uid,))
        tf = [i for i, a in enumerate(ans) if a["kind"] == "tf"]
        for i in tf:
            self.s.post(f"/s/games/quiz/{r['round_id']}/check", json={"i": i, "pick": ans[i]["answer_index"]})
        with self.app.app_context():
            row = query("SELECT active_sec FROM game_rounds WHERE id = ?", (r["round_id"],), one=True)
            self.assertGreaterEqual(row["active_sec"], 45)
            import progress
            s = progress.today_summary(uid)
            self.assertEqual(s["solved"], len(tf)); self.assertGreaterEqual(s["minutes"], 40); self.assertEqual(s["streak"], 1)
            t13 = next(t for t in progress.topic_progress(uid) if t["code"] == "13")
            self.assertEqual(t13["done"], len(tf))
            self.assertEqual(progress.weekly_ranking(uid)["me"]["rank"], 1)
        page = self.s.get("/s/my").data.decode()
        for word in ("주간 공부 순위", "일별 이용 시간", "학습 진도", "민수", "<svg class=\"day-chart\""):
            self.assertIn(word, page)
        self.s.post("/s/my/reset", data={"topic": "13"})
        with self.app.app_context():
            t13 = next(t for t in progress.topic_progress(uid) if t["code"] == "13")
            self.assertEqual(t13["done"], 0)
            self.assertGreaterEqual(progress.today_summary(uid)["minutes"], 40)     # 공부 시간은 그대로
        self.assertEqual(self.s.post("/s/my/reset", data={"topic": "99"}).status_code, 400)
        self.assertNotEqual(self.t.get("/s/my").status_code, 200)

    def test_assistant_monthly_answer_counts(self):
        """조교 월별 답변 수: 질문마다 첫 답변은 Main, 같은 질문의 이후 답변은 부가."""
        with self.app.app_context():
            execute("INSERT INTO users (role, username, password_hash, display_name) VALUES ('assistant', 'ta2', ?, '최조교')", (hash_password(PW),))
        ta = self.app.test_client(); ta.post("/login", data={"username": "ta2", "password": PW})
        for t in ("[기출-1] 질문1", "[기출-2] 질문2"):
            self.s.post("/s/questions", data={"qtype": "학습질문", "title": t, "body": "내용", "image": [(io.BytesIO(PNG), "a.png")]},
                        content_type="multipart/form-data")
        with self.app.app_context():
            q1, q2 = [r["id"] for r in query("SELECT id FROM questions ORDER BY id")]
        ta.post(f"/t/questions/{q1}", data={"body": "답1"})                       # Main
        self.s.post(f"/s/questions/{q1}/followup", data={"body": "재질문"})
        ta.post(f"/t/questions/{q1}", data={"body": "답1-2"})                     # 부가
        self.t.post(f"/t/questions/{q2}", data={"body": "선생님 답"})            # q2 의 Main 은 선생님
        ta.post(f"/t/questions/{q2}", data={"body": "조교 보충"})                 # 부가
        with self.app.app_context():
            from views.teacher import answer_counts
            from datetime import date
            uid = query("SELECT id FROM users WHERE username = 'ta2'", one=True)["id"]
            self.assertEqual(answer_counts(date.today().strftime("%Y-%m"))[uid], {"main": 1, "extra": 2})
            self.assertEqual(answer_counts("2000-01"), {})
        page = self.t.get("/t/staff").data.decode()
        self.assertIn("월별 질문 답변 수", page); self.assertIn("최조교", page)
        csv_ = self.t.get("/t/staff/answers.csv").data.decode("utf-8-sig")
        self.assertIn("최조교,ta2,1,2,3", csv_)
        self.assertIn(">Main<", self.t.get(f"/t/questions/{q1}").data.decode())
        self.assertNotEqual(ta.get("/t/staff/answers.csv").status_code, 200)        # 조교는 못 봄
