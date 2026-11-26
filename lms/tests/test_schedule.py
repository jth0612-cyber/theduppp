"""수업 일정: 진도 그룹 · 주차(토~금) · 수업 칸 · 배부 교재 넣기/빼기 · 출석 · 휴강 주 밀기."""
import os
import sys
import tempfile
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app  # noqa: E402
from db import execute, query  # noqa: E402
from security import hash_password  # noqa: E402

PW = "Test-pass-1234"


class Schedule(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False,
                               "DATABASE": os.path.join(self.tmp.name, "t.sqlite3"), "UPLOAD_DIR": os.path.join(self.tmp.name, "up")})
        with self.app.app_context():
            execute("INSERT INTO users (role, username, password_hash, display_name) VALUES ('assistant', 'ta', ?, '박조교')", (hash_password(PW),))
            self.sat = execute("INSERT INTO classes (name, track) VALUES ('토요일반', '단과')")
            self.fri = execute("INSERT INTO classes (name, track) VALUES ('금요일반', '단과')")
            self.jae = execute("INSERT INTO classes (name, track) VALUES ('재종반', '재종')")
            self.a = execute("INSERT INTO students (class_id, name, student_no) VALUES (?, '김하나', '270001')", (self.sat,))
            self.b = execute("INSERT INTO students (class_id, name, student_no) VALUES (?, '이두리', '270002')", (self.sat,))
            self.c = execute("INSERT INTO students (class_id, name, student_no) VALUES (?, '박세나', '270003')", (self.fri,))
            execute("INSERT INTO users (role, username, password_hash, student_id) VALUES ('student', '270001', ?, ?)", (hash_password(PW), self.a))
        from views import auth
        auth._ip_attempts.clear()
        self.ta = self.client("ta")
        # 수업 시간: 토요일반 토 10:00, 금요일반 금 18:20 (관·교실 포함)
        self.ta.post(f"/t/classes/{self.sat}/slots", data={"weekday": "5", "period": "", "starts": "10:00", "ends": "13:30", "hall": "M3관", "room": "101"})
        self.ta.post(f"/t/classes/{self.fri}/slots", data={"weekday": "4", "period": "5교시", "starts": "18:20", "ends": "20:00", "hall": "목동관", "room": "603"})
        self.ta.post("/t/handouts", data={"kind": "스퀴즈", "title": "SQ-고체1, SQ-고체2"})
        self.ta.post("/t/handouts", data={"kind": "필기노트", "title": "필기노트 1호"})
        self.first = date.today() - timedelta(days=(date.today().weekday() - 5) % 7)     # 이번 주차 토요일
        self.ta.post("/t/schedule", data={"name": "단과 S1", "track": "단과", "first": (self.first + timedelta(days=2)).isoformat(),
                                          "weeks": "3", "class_id": [str(self.sat), str(self.fri), str(self.jae)]})
        with self.app.app_context():
            self.gid = query("SELECT id FROM course_groups", one=True)["id"]
            self.w = [r["id"] for r in query("SELECT id FROM group_weeks ORDER BY week_no")]
            self.h = {r["title"]: r["id"] for r in query("SELECT id, title FROM handouts")}

    def client(self, u):
        c = self.app.test_client()
        c.post("/login", data={"username": u, "password": PW})
        return c

    def tearDown(self):
        with self.app.app_context():
            from db import close_db
            close_db()
        self.tmp.cleanup()

    def sess(self, cid, wk=0):
        with self.app.app_context():
            return query("SELECT * FROM sessions WHERE class_id = ? AND week_id = ?", (cid, self.w[wk]), one=True)

    def test_weeks_and_cells(self):
        with self.app.app_context():
            wk = query("SELECT * FROM group_weeks ORDER BY week_no")
            self.assertEqual((wk[0]["starts"], wk[0]["ends"]), (self.first.isoformat(), (self.first + timedelta(days=6)).isoformat()))  # 토~금
            self.assertIsNone(query("SELECT group_id FROM classes WHERE id = ?", (self.jae,), one=True)["group_id"])   # 재종은 단과 그룹에 안 들어감
            self.assertEqual(query("SELECT COUNT(*) AS n FROM sessions", one=True)["n"], 6)                          # 2반 × 3주
        self.assertEqual(self.sess(self.sat)["day"], self.first.isoformat())                                         # 토요일반이 주차 첫날
        self.assertEqual(self.sess(self.fri)["day"], (self.first + timedelta(days=6)).isoformat())                   # 금요일반이 마지막
        page = self.ta.get(f"/t/schedule/{self.gid}").data.decode()
        self.assertIn("has-shell", page)                                                             # 메뉴가 보인다 (템플릿 변수 g 덮어쓰기 방지)
        for u in ("/t/schedule", "/t/handouts", f"/t/schedule/sessions/{self.sess(self.sat)['id']}"):
            self.assertIn("has-shell", self.ta.get(u).data.decode(), u)
        self.assertIn("1주차", page); self.assertIn("목동관 603", page)
        self.assertLess(page.index("토요일반</b>"), page.index("금요일반</b>"))                                       # 열 순서 = 토 → 금
        self.assertEqual(self.ta.get(f"/t/schedule/{self.gid}?view=cal").status_code, 200)
        self.assertEqual(self.ta.get(f"/t/classes/{self.sat}?tab=times").status_code, 200)
        # 주차 날짜를 직접 바꾸면 수업 칸 날짜도 따라간다
        self.ta.post(f"/t/schedule/weeks/{self.w[0]}", data={"action": "save", "starts": (self.first + timedelta(days=1)).isoformat(),
                                                           "ends": (self.first + timedelta(days=7)).isoformat()})
        self.assertEqual(self.sess(self.sat)["day"], (self.first + timedelta(days=7)).isoformat())

    def test_lesson_note_from_session(self):
        s = self.sess(self.sat)
        page = self.ta.get(f"/t/schedule/sessions/{s['id']}").data.decode()
        self.assertIn('id="lesson"', page); self.assertIn(f'name="session" value="{s["id"]}"', page)
        r = self.ta.post("/t/lessons", data={"class_id": self.sat, "day": s["day"], "session": s["id"], "title": "TOPIC 01 기본량", "body": "단위 정리"})
        self.assertTrue(r.headers["Location"].endswith(f"/t/schedule/sessions/{s['id']}#lesson"))     # 올린 뒤 수업 칸으로 돌아온다
        with self.app.app_context():
            l = query("SELECT * FROM lessons", one=True)
        self.assertEqual((l["class_id"], l["day"]), (self.sat, s["day"]))
        page = self.ta.get(f"/t/schedule/sessions/{s['id']}").data.decode()
        self.assertIn("TOPIC 01 기본량", page); self.assertIn(f"/t/lessons/{l['id']}", page)
        self.assertNotIn("TOPIC 01 기본량", self.ta.get(f"/t/schedule/sessions/{self.sess(self.fri)['id']}").data.decode())   # 다른 반 칸에는 안 보인다

    def test_handouts_attendance_counts(self):
        sq1, note = self.h["SQ-고체1"], self.h["필기노트 1호"]
        self.ta.post(f"/t/schedule/weeks/{self.w[0]}", data={"action": "save", "starts": self.first.isoformat(),
                                                           "ends": (self.first + timedelta(days=6)).isoformat(), "topic": "고체1",
                                                           "handout_id": [str(sq1)], "review_round": "1"})
        s_sat, s_fri = self.sess(self.sat)["id"], self.sess(self.fri)["id"]
        self.ta.post(f"/t/schedule/sessions/{s_fri}", data={"action": "handout", "handout_id": str(sq1), "mode": "drop"})   # 금요일반만 빼기
        self.ta.post(f"/t/schedule/sessions/{s_fri}", data={"action": "handout", "handout_id": str(note), "mode": "add"})   # 금요일반만 더 넣기
        # 토요일반: 김하나 출석, 이두리 결석 / 금요일반 박세나가 토요일반 수업을 들음
        self.ta.post(f"/t/schedule/sessions/{s_sat}", data={"action": "attend", f"st_{self.a}": "출석", f"st_{self.b}": "결석"})
        self.ta.post(f"/t/schedule/sessions/{s_sat}", data={"action": "guest", "q": "270003"})
        self.ta.post(f"/t/schedule/sessions/{s_fri}", data={"action": "attend", f"st_{self.c}": "다른 반"})
        with self.app.test_request_context():
            from views.schedule import SESSION_SQL, _breaks, handout_counts, session_view
            ss = session_view(query(SESSION_SQL + " WHERE s.week_id = ?", (self.w[0],)), _breaks())
            by = {s["class_id"]: s for s in ss}
            self.assertEqual([h["id"] for h in by[self.sat]["handouts"]], [sq1])
            self.assertEqual([h["id"] for h in by[self.fri]["handouts"]], [note])
            self.assertEqual((by[self.sat]["present"], by[self.sat]["roster"]), (2, 3))      # 김하나 + 박세나(다른 반에서 옴)
            self.assertEqual(by[self.fri]["roster"], 0)                                      # 박세나는 이번 주 다른 반
            tot = {t["h"]["id"]: t for t in handout_counts(ss)}
            self.assertEqual(tot[sq1]["given"], 2)
        page = self.ta.get(f"/t/schedule/sessions/{s_sat}").data.decode()
        self.assertIn("박세나", page); self.assertIn("금요일반", page)
        # 학생 시간표: 이번 주차 진도·교재·복테 회차
        stu = self.client("270001").get("/s/timetable").data.decode()
        self.assertIn("1주차", stu); self.assertIn("고체1", stu); self.assertIn("SQ-고체1", stu); self.assertIn("복습 테스트 1회", stu)

    def test_off_week_pushes_plan(self):
        for k, t in enumerate(("고체1", "고체2", "")):
            if t:
                self.ta.post(f"/t/schedule/weeks/{self.w[k]}", data={"action": "save", "starts": (self.first + timedelta(days=7 * k)).isoformat(),
                                                                   "ends": (self.first + timedelta(days=7 * k + 6)).isoformat(), "topic": t,
                                                                   "handout_id": [str(self.h["SQ-" + t])]})
        self.ta.post(f"/t/schedule/weeks/{self.w[1]}", data={"action": "off"})                # 2주차 중간고사 휴강
        with self.app.app_context():
            wk = query("SELECT * FROM group_weeks ORDER BY week_no")
            hs = {w["id"]: [r["handout_id"] for r in query("SELECT handout_id FROM week_handouts WHERE week_id = ?", (w["id"],))] for w in wk}
        self.assertEqual([w["topic"] for w in wk], ["고체1", "", "고체2"]); self.assertEqual(wk[1]["off"], 1)
        self.assertEqual(hs[self.w[2]], [self.h["SQ-고체2"]]); self.assertEqual(hs[self.w[1]], [])
        self.ta.post(f"/t/schedule/weeks/{self.w[1]}", data={"action": "on"})                 # 휴강 풀기 → 다시 당긴다
        with self.app.app_context():
            self.assertEqual([w["topic"] for w in query("SELECT topic FROM group_weeks ORDER BY week_no")], ["고체1", "고체2", ""])

    def test_sys_attendance_fills_cells(self):
        """조교 시스템 출결(시트) → 같은 날 그 반 수업 칸. 손으로 고친 칸은 그대로."""
        day = self.first.isoformat()
        with self.app.app_context():
            for code, sid in (("A0000001", self.a), ("A0000002", self.b)):
                execute("INSERT INTO student_codes (class_id, code, student_id) VALUES (?, ?, ?)", (self.sat, code, sid))
        s_sat = self.sess(self.sat)["id"]
        self.ta.post(f"/t/schedule/sessions/{s_sat}", data={"action": "attend", f"st_{self.b}": "결석"})   # 손으로 결석
        with self.app.test_request_context():
            import sysdata
            from views.schedule import sync_sys_attendance
            sysdata.store({"출결": [{"학생코드": "A0000001", "날짜": day.replace("-", "."), "출결": "지각", "도착시각": "10:12"},
                                   {"학생코드": "A0000002", "날짜": day, "출결": "출석"}]}, "test")
            sync_sys_attendance()
            st = {r["student_id"]: (r["state"], r["src"]) for r in query("SELECT * FROM session_students WHERE session_id = ?", (s_sat,))}
        self.assertEqual(st[self.a], ("지각", "시트"))
        self.assertEqual(st[self.b], ("결석", ""))                                               # 손으로 고친 값은 시트가 안 바꾼다
        self.assertIn("시트", self.ta.get(f"/t/schedule/sessions/{s_sat}").data.decode())

    def test_slot_delete_removes_cells_and_staff_only(self):
        with self.app.app_context():
            tid = query("SELECT id FROM timetable WHERE class_id = ?", (self.fri,), one=True)["id"]
        self.ta.post(f"/t/classes/{self.fri}/slots", data={"action": "delete", "id": str(tid)})
        with self.app.app_context():
            self.assertEqual(query("SELECT COUNT(*) AS n FROM sessions WHERE class_id = ?", (self.fri,), one=True)["n"], 0)
        self.assertIn(self.client("270001").get(f"/t/schedule/{self.gid}").status_code, (302, 403))


if __name__ == "__main__":
    unittest.main()
