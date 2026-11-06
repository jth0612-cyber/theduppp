"""공부 도구 점검: 오답 노트, 개념 카드, 시간표, 과제, 리포트, FAQ, 설치·알림.
python -m unittest discover tests"""
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from db import execute, query  # noqa: E402
from security import hash_password  # noqa: E402
from tests.test_books import STU_PW, TEACHER_PW  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
KEY25 = "1435253411243155214331524"


class StudyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True, "WTF_CSRF_ENABLED": False, "ANALYSIS_TTL": 0,
            "DATABASE": os.path.join(self.tmp.name, "t.sqlite3"),
            "UPLOAD_DIR": os.path.join(self.tmp.name, "up"),
            "VAPID_PATH": os.path.join(self.tmp.name, "vapid.pem"),
        })
        os.makedirs(self.app.config["UPLOAD_DIR"], exist_ok=True)
        with self.app.app_context():
            from db import init_db
            init_db(self.app.config["DATABASE"])
            execute("INSERT INTO users (role, username, password_hash) VALUES ('teacher', 'teacher', ?)",
                    (hash_password(TEACHER_PW),))
            self.cid = execute("INSERT INTO classes (name, join_code) VALUES ('A반', 'AAAAAAAA')")
            self.cid2 = execute("INSERT INTO classes (name, join_code) VALUES ('B반', 'BBBBBBBB')")
            for i, cid in enumerate([self.cid, self.cid, self.cid2]):
                sid = execute("INSERT INTO students (class_id, name, student_no) VALUES (?, ?, ?)",
                              (cid, f"학생{i}", f"S{i:03d}"))
                execute("""INSERT INTO users (role, username, nickname, password_hash, student_id)
                           VALUES ('student', ?, ?, ?, ?)""", (f"S{i:03d}", f"닉{i}", hash_password(STU_PW), sid))
        from views import auth
        auth._ip_attempts.clear()
        self.t = self.app.test_client()
        self.t.post("/login", data={"username": "teacher", "password": TEACHER_PW})

    def tearDown(self):
        with self.app.app_context():
            from db import close_db
            close_db()
        self.tmp.cleanup()

    def student(self, i):
        c = self.app.test_client()
        self.assertEqual(c.post("/login", data={"username": f"S{i:03d}", "password": STU_PW}).status_code, 302)
        return c

    def q(self, sql, args=(), one=False):
        with self.app.app_context():
            return query(sql, args, one)

    # 1
    def test_guide_removed(self):
        s = self.student(0)
        self.assertEqual(s.get("/s/guide").status_code, 404)
        self.assertNotIn("내 공부법", s.get("/s/").data.decode())

    # 2
    def test_wrong_notes(self):
        r = self.t.post("/t/books", data={"title": "실전", "subject": "통합과학", "expires_on": "2099-12-31"})
        bid = int(r.headers["Location"].rsplit("/", 1)[-1])
        self.t.post(f"/t/books/{bid}/mocks", data={"round_no": "1", "n_items": "25", "full_score": "50",
                                                   "answer_key": KEY25, "high_items": "21-25", "low_items": "1-5"})
        mid = self.q("SELECT id FROM mocks", one=True)["id"]
        self.t.post(f"/t/books/{bid}/codes", data={"kind": "shared"})
        code = self.q("SELECT code FROM book_codes", one=True)["code"]
        s = self.student(0)
        s.post("/s/books/register", data={"code": code})
        ans = ("2" if KEY25[0] != "2" else "3") + KEY25[1:24] + ("2" if KEY25[24] != "2" else "3")
        s.post(f"/s/analysis/{mid}/submit", data={"mode": "answers", "quick": ans})
        page = s.get("/s/wrong").data.decode()
        self.assertIn("1번", page)
        self.assertIn("25번", page)
        self.assertNotIn(KEY25, page)
        s.post(f"/s/wrong/{mid}/1", data={"reason": "계산 실수", "memo": "부호", "reviewed": "1"})
        n = self.q("SELECT * FROM wrong_notes WHERE item_no = 1", one=True)
        self.assertEqual((n["reason"], n["memo"]), ("계산 실수", "부호"))
        self.assertIsNotNone(n["reviewed_at"])
        self.assertNotIn("w-%d-1\"" % mid, s.get("/s/wrong?view=open").data.decode())
        self.assertEqual(s.post(f"/s/wrong/{mid}/2", data={"reason": "계산 실수"}).status_code, 404)  # 맞힌 문항
        self.assertEqual(self.student(1).post(f"/s/wrong/{mid}/1", data={}).status_code, 404)        # 남의 답안
        self.assertIn("계산 실수", self.t.get("/t/students/1/report").data.decode())

    # 3
    def test_timetable_and_dday(self):
        self.t.post("/t/timetable", data={"action": "dday", "exam_day": (date.today() + timedelta(days=10)).isoformat(),
                                          "exam_label": "수능"})
        wd = date.today().weekday()
        self.t.post("/t/timetable", data={"action": "slot", "class_id": str(self.cid), "weekday": [str(wd), str((wd + 2) % 7)],
                                          "starts": "13:00", "ends": "15:50", "title": "통합과학 정규", "room": "302호"})
        self.t.post("/t/timetable", data={"action": "slot", "class_id": str(self.cid), "weekday": "1",
                                          "starts": "15:00", "ends": "14:00", "title": "거꾸로"})    # 끝이 시작보다 빠름
        self.assertEqual(self.q("SELECT COUNT(*) AS n FROM timetable", one=True)["n"], 2)
        s = self.student(0)
        page = s.get("/s/timetable").data.decode()
        self.assertIn("D-10", page)
        self.assertIn("302호", page)
        self.assertIn("13:00–15:50", page)
        self.assertIn("tt-slot tone-", page)                                 # 수업마다 색
        home = s.get("/s/").data.decode()
        self.assertIn("D-10", home)
        self.assertIn("오늘 13:00 통합과학 정규", home)
        self.assertEqual(s.get("/s/calendar").status_code, 404)              # 일정 기능 없음
        self.assertNotIn("통합과학 정규", self.student(2).get("/s/timetable").data.decode())  # 다른 반
        tid = self.q("SELECT id FROM timetable LIMIT 1", one=True)["id"]
        self.t.post(f"/t/timetable/slot/{tid}/delete")
        self.assertEqual(self.q("SELECT COUNT(*) AS n FROM timetable", one=True)["n"], 1)

    # 7 과제: 정답·해설 PDF → 학생 답 입력 → 채점·분석
    def test_tasks(self):
        pdf = open(os.path.join(os.path.dirname(__file__), "fixtures", "solution_sample.pdf"), "rb").read()
        r = self.t.post("/t/tasks", data={"class_id": str(self.cid), "title": "2단원 기출 1회", "due_on": "2099-01-01",
                                          "pdf": (io.BytesIO(pdf), "해설.pdf")}, content_type="multipart/form-data", follow_redirects=True)
        self.assertIn("정답 5개", r.data.decode())                          # PDF 에서 정답표를 읽음
        a = self.q("SELECT * FROM assignments", one=True)
        self.assertEqual(json.loads(a["answer_key"]), ["3", "5", "1", "2", "4"])
        self.assertEqual(json.loads(a["units"])[0], "물질과 규칙성")         # 해설 낱말로 단원 짐작
        self.assertIn("4", json.loads(a["solutions"]))                     # 문항별 해설
        aid, fid = a["id"], a["solution_file_id"]
        s0, s1, s2 = self.student(0), self.student(1), self.student(2)
        self.assertIn("2단원 기출 1회", s0.get("/s/tasks").data.decode())
        self.assertEqual(s0.get(f"/s/file/{fid}").status_code, 404)        # 답을 내기 전에는 해설 못 봄
        self.assertEqual(s2.get(f"/s/tasks/{aid}").status_code, 404)       # 다른 반
        s1.post(f"/s/tasks/{aid}", data={"q1": "3", "q2": "5", "q3": "1", "q4": "2", "q5": "4"})
        r = s0.post(f"/s/tasks/{aid}", data={"q1": "3", "q2": "1", "q3": "1", "q4": "2"}, follow_redirects=True)
        page = r.data.decode()
        self.assertIn("<b>3</b><span>/ 5</span>", page)
        self.assertIn("5번을 비워 두었어요", page)
        self.assertIn("다른 친구들 대부분이 맞힌 2번", page)                 # 실수 의심
        self.assertIn("이온 결합 물질은", page)                              # 틀린 문제 해설
        self.assertEqual(s0.get(f"/s/file/{fid}?inline=1").status_code, 200)  # 낸 뒤엔 해설 PDF 열림
        # 한 번만 낼 수 있음
        s0.post(f"/s/tasks/{aid}", data={"q2": "5"})
        self.assertEqual(self.q("SELECT correct FROM task_answers WHERE student_id = (SELECT id FROM students WHERE student_no='S000')", one=True)["correct"], 3)
        # 선생님: 현황·학생별 분석·정답 고치면 다시 채점
        tp = self.t.get(f"/t/tasks/{aid}").data.decode()
        self.assertIn("학생0", tp); self.assertIn("반 전체 단원별 정답률", tp)
        sid0 = self.q("SELECT id FROM students WHERE student_no='S000'", one=True)["id"]
        self.assertIn("학생0 학생의 문제점", self.t.get(f"/t/tasks/{aid}/students/{sid0}").data.decode())
        form = {"n": "5", "confirm": "1", **{f"k{i + 1}": v for i, v in enumerate(["3", "1", "1", "2", "4"])}}
        self.t.post(f"/t/tasks/{aid}", data=form)
        self.assertEqual(self.q("SELECT correct FROM task_answers WHERE student_id = ?", (sid0,), one=True)["correct"], 4)
        # 정답을 직접 적는 과제(단답 포함)
        self.t.post("/t/tasks", data={"class_id": str(self.cid), "title": "단답 연습", "answer_key": "③ ① 12 0.5"})
        b = self.q("SELECT * FROM assignments WHERE title = '단답 연습'", one=True)
        self.assertEqual(json.loads(b["answer_key"]), ["3", "1", "12", "0.5"])
        s0.post(f"/s/tasks/{b['id']}", data={"q1": "3", "q2": "2", "q3": " 12 ", "q4": "0.5"})
        self.assertEqual(self.q("SELECT correct FROM task_answers WHERE assignment_id = ?", (b["id"],), one=True)["correct"], 3)

    # 6
    def test_report_access(self):
        self.assertEqual(self.t.get("/t/students/1/report").status_code, 200)
        s = self.student(0)
        self.assertIn("학생0", s.get("/s/report").data.decode())
        self.assertEqual(s.get("/t/students/2/report").status_code, 403)

    # 8
    def test_faq(self):
        sid = self.q("SELECT id FROM students WHERE student_no = 'S000'", one=True)["id"]
        with self.app.app_context():
            qid = execute("INSERT INTO questions (student_id, title, body, qtype) VALUES (?, '몰 질문', '본문', '학습질문')",
                          (sid,))
        self.assertNotIn("자주 묻는 질문", self.student(1).get("/s/questions").data.decode())
        self.t.post(f"/t/questions/{qid}/faq")
        page = self.student(1).get("/s/questions").data.decode()
        self.assertIn("자주 묻는 질문", page)
        self.assertIn("몰 질문", page)

    # 9, 10
    def test_pwa_and_push(self):
        m = self.t.get("/manifest.webmanifest")
        self.assertEqual(m.mimetype, "application/manifest+json")
        self.assertEqual(json.loads(m.data)["display"], "standalone")
        sw = self.t.get("/sw.js")
        self.assertEqual(sw.headers["Service-Worker-Allowed"], "/")
        s = self.student(0)
        key = s.get("/push/key").get_json()["key"]
        self.assertGreater(len(key), 60)
        sub = {"endpoint": "https://push.example.com/abc", "keys": {"p256dh": "x" * 80, "auth": "y" * 20}}
        self.assertEqual(s.post("/push/subscribe", json=sub).status_code, 200)
        self.assertEqual(self.q("SELECT COUNT(*) AS n FROM push_subs", one=True)["n"], 1)
        self.assertEqual(s.post("/push/subscribe", json={"endpoint": "http://x"}).status_code, 400)
        s.post("/push/unsubscribe", json={"endpoint": sub["endpoint"]})
        self.assertEqual(self.q("SELECT COUNT(*) AS n FROM push_subs", one=True)["n"], 0)
        self.assertEqual(self.app.test_client().post("/push/subscribe", json=sub).status_code, 302)  # 로그인 필요

