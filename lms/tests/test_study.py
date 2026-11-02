"""공부 도구 점검: 공부 결 진단, 오답 노트, 개념 카드, 시간표, 과제, 리포트, FAQ, 설치·알림.
python -m unittest discover tests"""
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import study_guide  # noqa: E402
from app import create_app  # noqa: E402
from db import execute, query  # noqa: E402
from security import hash_password  # noqa: E402
from tests.test_books import STU_PW, TEACHER_PW  # noqa: E402
from views.study import parse_cards  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
KEY25 = "1435253411243155214331524"


class GuideMathTest(unittest.TestCase):
    def test_score_and_describe(self):
        form = {f"q{i}": "a" for i in range(12)}
        code, picks = study_guide.score(form)
        self.assertEqual(code, "SVRI")
        self.assertEqual(picks, "a" * 12)
        form = {f"q{i}": "b" for i in range(12)}
        self.assertEqual(study_guide.score(form)[0], "PWFT")
        self.assertEqual(study_guide.score({"q0": "a"}), (None, None))     # 빠진 문항
        d = study_guide.describe("PVRT")
        self.assertEqual(d["name"], "실험실형")
        self.assertEqual(len(d["units"]), len(study_guide.UNITS))

    def test_parse_cards(self):
        cards, bad = parse_cards("이온 결합 | 양이온과 음이온\n\n잘못된 줄\n공유 결합|전자쌍 공유\n | 앞면 없음")
        self.assertEqual(cards, [("이온 결합", "양이온과 음이온"), ("공유 결합", "전자쌍 공유")])
        self.assertEqual(bad, [3, 5])


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
    def test_guide_flow(self):
        s = self.student(0)
        self.assertIn("공부 결 진단", s.get("/s/guide").data.decode())
        self.assertEqual(s.post("/s/guide", data={"q0": "a"}).status_code, 400)
        form = {f"q{i}": ("a" if i < 6 else "b") for i in range(12)}
        s.post("/s/guide", data=form)
        page = s.get("/s/guide").data.decode()
        self.assertIn("설계도형", page)
        self.assertIn("단원별 공부법", page)
        self.assertEqual(self.q("SELECT code FROM study_types", one=True)["code"], "SVFT")

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
    def test_cards(self):
        self.t.post("/t/cards", data={"title": "결합", "unit": "물질과 규칙성", "class_id": str(self.cid)})
        did = self.q("SELECT id FROM decks", one=True)["id"]
        self.t.post(f"/t/cards/{did}", data={"cards": "이온 결합 | 정전기적 인력\n공유 결합 | 전자쌍 공유"})
        cards = self.q("SELECT id FROM cards ORDER BY pos")
        self.assertEqual(len(cards), 2)
        s = self.student(0)
        self.assertIn("결합", s.get("/s/cards").data.decode())
        r = s.post(f"/s/cards/mark/{cards[0]['id']}", data={"status": "unsure"}, headers={"X-Requested-With": "fetch"})
        self.assertEqual(r.get_json(), {"ok": True})
        page = s.get(f"/s/cards/{did}?mode=unsure").data.decode()
        self.assertIn("이온 결합", page)
        self.assertNotIn("공유 결합", page)
        other = self.student(2)                                          # 다른 반에는 안 보임
        self.assertEqual(other.get(f"/s/cards/{did}").status_code, 404)
        self.assertEqual(other.post(f"/s/cards/mark/{cards[0]['id']}", data={"status": "known"}).status_code, 404)

    # 5
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
        home = s.get("/s/").data.decode()
        self.assertIn("D-10", home)
        self.assertIn("오늘 13:00 통합과학 정규", home)
        self.assertEqual(s.get("/s/calendar").status_code, 404)              # 일정 기능 없음
        self.assertEqual(s.get("/s/planner").status_code, 404)
        self.assertNotIn("통합과학 정규", self.student(2).get("/s/timetable").data.decode())  # 다른 반
        tid = self.q("SELECT id FROM timetable LIMIT 1", one=True)["id"]
        self.t.post(f"/t/timetable/slot/{tid}/delete")
        self.assertEqual(self.q("SELECT COUNT(*) AS n FROM timetable", one=True)["n"], 1)

    # 7
    def test_tasks(self):
        self.t.post("/t/tasks", data={"class_id": str(self.cid), "title": "기출 풀이", "due_on": "2099-01-01"})
        aid = self.q("SELECT id FROM assignments", one=True)["id"]
        s = self.student(0)
        self.assertIn("기출 풀이", s.get("/s/tasks").data.decode())
        r = s.post(f"/s/tasks/{aid}", data={"note": "다 풀었어요", "file": (io.BytesIO(PNG), "a.png")},
                   content_type="multipart/form-data")
        self.assertEqual(r.status_code, 302)
        sub = self.q("SELECT * FROM submissions", one=True)
        self.assertEqual(s.get(f"/s/file/{sub['file_id']}").status_code, 200)            # 본인 제출물
        self.assertEqual(self.student(1).get(f"/s/file/{sub['file_id']}").status_code, 404)  # 친구는 못 봄
        self.assertEqual(self.student(2).post(f"/s/tasks/{aid}", data={"note": "x"}).status_code, 404)
        self.assertIn("학생0", self.t.get(f"/t/tasks/{aid}").data.decode())
        self.t.post(f"/t/submissions/{sub['id']}", data={"status": "checked", "comment": "좋아요"})
        page = s.get("/s/tasks").data.decode()
        self.assertIn("확인 완료", page)
        self.assertIn("좋아요", page)

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


if __name__ == "__main__":
    unittest.main()
