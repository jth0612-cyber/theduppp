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
        """복습 테스트 1회에 김하나 결과 반영: 3·4번(산과 염기) 틀림. (시험지 첨삭은 복습 테스트만)"""
        from openpyxl import Workbook
        wb = Workbook(); ws = wb.active; ws.title = "OMR"
        ws.append(["이름", "수험번호", 1, 2, 3, 4]); ws.append(["정답", "", 1, 2, 3, 4]); ws.append(["배점", "", 2, 2, 3, 3])
        ws.append(["김하나", "11112222", 1, 2, 1, 1])
        inf = wb.create_sheet("문항정보"); inf.append(["문항번호", "단원"])
        for i, u in ((1, "역학 시스템"), (2, "역학 시스템"), (3, "산과 염기"), (4, "산과 염기")):
            inf.append([i, u])
        buf = io.BytesIO(); wb.save(buf)
        with self.app.app_context():
            mid = query("""SELECT m.id FROM mocks m JOIN books b ON b.id = m.book_id WHERE b.title = '복습 테스트' AND m.round_no = 1""", one=True)["id"]
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
        self.assertIn("다시 올릴 수 없어요", r.data.decode())
        with self.app.app_context():
            from datetime import date
            from views.care import paper_review_counts
            uid = query("SELECT id FROM users WHERE username = 'ta'", one=True)["id"]
            self.assertEqual(paper_review_counts(date.today().strftime("%Y-%m")), {uid: 1})

    def test_staff_opens_student_omr_and_scores_show_wrong_numbers(self):
        mid = self._exam()
        page = self.ta.get(f"/t/mocks/{mid}").data.decode()
        self.assertIn(f"/t/mocks/{mid}/omr/{self.s1}", page)                              # 회차 화면의 학생 이름이 OMR로 간다
        omr = self.ta.get(f"/t/mocks/{mid}/omr/{self.s1}").data.decode()
        self.assertIn("김하나", omr); self.assertIn("틀린 문항 2개", omr); self.assertIn("3, 4", omr)
        self.assertEqual(self.ta.get(f"/t/mocks/{mid}/omr/{self.s2}").status_code, 404)   # 결과 없는 학생
        self.assertNotEqual(self.c1.get(f"/t/mocks/{mid}/omr/{self.s1}").status_code, 200)  # 학생은 못 본다
        mine = self.c1.get("/s/scores").data.decode()
        self.assertIn("틀린 문항 2개", mine); self.assertIn("3, 4", mine)

    def test_followup_comes_right_after_main_answer(self):
        with self.app.app_context():
            from views.student import question_thread
            uid = query("SELECT id FROM users WHERE username = 'ta'", one=True)["id"]
            q = execute("INSERT INTO questions (student_id, title, body) VALUES (?, 't', 'b')", (self.s1,))
            for body, at in (("메인", "2026-11-01 10:00:00"), ("부가", "2026-11-01 11:00:00"), ("추가 답변", "2026-11-01 13:00:00")):
                execute("INSERT INTO answers (question_id, author_id, body, created_at) VALUES (?, ?, ?, ?)", (q, uid, body, at))
            execute("INSERT INTO followups (question_id, body, created_at) VALUES (?, '추가 질문', '2026-11-01 12:00:00')", (q,))
            self.assertEqual([m["body"] for m in question_thread(q)], ["메인", "추가 질문", "추가 답변", "부가"])
            # 메인 답변의 시각이 추가 질문보다 늦게 찍혀 있어도 메인 답변이 먼저
            execute("UPDATE answers SET created_at = '2026-11-01 12:30:00' WHERE question_id = ? AND body = '메인'", (q,))
            execute("DELETE FROM answers WHERE question_id = ? AND body = '부가'", (q,))
            self.assertEqual([m["body"] for m in question_thread(q)], ["메인", "추가 질문", "추가 답변"])

    def test_one_to_one_split_by_kind(self):
        """1:1 관리: 복습 테스트는 시험지 첨삭만, 모의고사는 1:1 피드백만."""
        rmid = self._exam()
        with self.app.app_context():
            mmid = query("""SELECT m.id FROM mocks m JOIN books b ON b.id = m.book_id WHERE b.title = '모의고사' AND m.round_no = 1""", one=True)["id"]
        self.c1.post(f"/s/analysis/{rmid}/feedback", data={"body": "봐 주세요"})
        with self.app.app_context():
            self.assertIsNone(query("SELECT 1 FROM feedback_threads", one=True))         # 복테에는 1:1 피드백 없음
            execute("INSERT INTO exam_results (mock_id, student_id, answers, score) VALUES (?, ?, '', 0)", (mmid, self.s1))
        self.c1.post(f"/s/analysis/{mmid}/paper", data={"image": [(io.BytesIO(PNG), "a.png")]}, content_type="multipart/form-data")
        with self.app.app_context():
            self.assertIsNone(query("SELECT 1 FROM exam_papers", one=True))              # 모의고사에는 시험지 첨삭 없음
        page = self.c1.get(f"/s/analysis?mock={rmid}").data.decode()
        self.assertIn('id="h-paper"', page); self.assertNotIn('id="h-fb"', page)       # 복테 회차: 시험지 첨삭 칸만
        nav = self.ta.get("/t/").data.decode()
        self.assertIn("질문과 첨삭", nav); self.assertNotIn("1:1 관리", nav)             # 답할 것 세 가지는 한 메뉴
        for u in ("/t/questions", "/t/papers", "/t/feedback"):                            # 세 목록 위에 서로 오가는 칩
            page = self.ta.get(u).data.decode()
            self.assertIn('aria-label="질문과 첨삭"', page); self.assertIn("복습 테스트 첨삭", page); self.assertIn("모의고사 피드백", page)

    def test_lessons_by_class(self):
        self.ta.post("/t/lessons", data={"class_id": str(self.a), "title": "TOPIC 24 중화 반응", "day": "2026-11-20",
                                         "image": [(io.BytesIO(PNG), "n.png")]}, content_type="multipart/form-data")
        self.assertIn("TOPIC 24 중화 반응", self.c1.get("/s/lessons").data.decode())
        self.assertNotIn("TOPIC 24 중화 반응", self.c2.get("/s/lessons").data.decode())
        with self.app.app_context():
            fid = query("SELECT file_id FROM lesson_files", one=True)["file_id"]
        self.assertEqual(self.c1.get(f"/s/file/{fid}").status_code, 200)
        self.assertNotEqual(self.c2.get(f"/s/file/{fid}").status_code, 200)

    def test_staff_opens_lesson_and_question_filters_fold(self):
        self.ta.post("/t/lessons", data={"class_id": self.a, "title": "TOPIC 24 중화 반응", "body": "몰 비 1:1", "image": [(io.BytesIO(PNG), "n.png")]},
                     content_type="multipart/form-data")
        with self.app.app_context():
            lid = query("SELECT id FROM lessons", one=True)["id"]
        self.assertIn(f'href="/t/lessons/{lid}"', self.ta.get("/t/lessons").data.decode())
        page = self.ta.get(f"/t/lessons/{lid}").data.decode()
        self.assertIn("몰 비 1:1", page); self.assertIn("노트 1장", page); self.assertIn("question-img", page)
        self.assertEqual(self.ta.get("/t/lessons/9999").status_code, 404)
        self.assertNotEqual(self.c1.get(f"/t/lessons/{lid}").status_code, 200)
        q = self.ta.get("/t/questions?status=all&qtype=학습질문").data.decode()
        self.assertIn('<details class="filter-fold">', q); self.assertIn("모든 단원", q)

    def test_lesson_needs_photo_or_note(self):
        self.ta.post("/t/lessons", data={"class_id": str(self.a), "title": "빈 기록", "day": "2026-11-20"})
        self.ta.post("/t/lessons", data={"class_id": str(self.a), "title": "글만", "day": "2026-11-20", "body": "중화 반응 정리"})
        with self.app.app_context():
            self.assertEqual([r["title"] for r in query("SELECT title FROM lessons")], ["글만"])
        self.assertIn("사진 없음", self.ta.get("/t/lessons").data.decode())

    def test_question_unit_filter(self):
        r = self.c1.post("/s/questions", data={"qtype": "학습질문", "unit": "물질과 규칙성", "title": "[개념서-42-3]", "body": "질문",
                                               "image": [(io.BytesIO(PNG), "q.png")]}, content_type="multipart/form-data")
        self.assertEqual(r.status_code, 302)
        with self.app.app_context():
            self.assertEqual(query("SELECT unit FROM questions", one=True)["unit"], "물질과 규칙성")
            execute("INSERT INTO questions (student_id, title, body, unit) VALUES (?, '[기출-10-1]', 'x', '환경과 에너지')", (self.s1,))
        page = self.ta.get("/t/questions?unit=물질과 규칙성").data.decode()
        self.assertIn("[개념서-42-3]", page); self.assertNotIn("[기출-10-1]", page)

    def test_rooms_four_week_history(self):
        from datetime import date, timedelta
        with self.app.app_context():
            uid = query("SELECT id FROM users WHERE username = '270001'", one=True)["id"]
            last_week = (date.today() - timedelta(days=7)).isoformat() + " 12:00:00"
            execute("INSERT INTO focus_logs (user_id, place, minutes, ended_at) VALUES (?, 'sento', 75, ?)", (uid, last_week))
        page = self.c1.get("/s/rooms").data.decode()
        self.assertIn("최근 4주 기록", page); self.assertIn("1시간 15분", page)

    def test_class_break_on_timetable(self):
        from datetime import date, timedelta
        today = date.today()
        mon = today - timedelta(days=today.weekday())
        self.ta.post("/t/timetable", data={"action": "break_add", "class_id": str(self.a), "starts": mon.isoformat(),
                                           "ends": (mon + timedelta(days=13)).isoformat(), "note": "중간고사"})
        self.ta.post("/t/timetable", data={"action": "break_add", "class_id": str(self.a), "starts": "2026-01-02", "ends": "2026-01-01"})
        with self.app.app_context():
            self.assertEqual(query("SELECT COUNT(*) AS n FROM class_breaks", one=True)["n"], 1)   # 끝이 시작보다 앞이면 거부
        page = self.c1.get("/s/timetable").data.decode()
        self.assertIn("휴강 중", page); self.assertIn("중간고사", page); self.assertIn("<small>휴강</small>", page)
        self.assertNotIn("중간고사", self.c2.get("/s/timetable").data.decode())   # 다른 반

    def test_pick_reason_rule(self):
        from exams import pick_reason
        self.assertEqual(pick_reason("계산 실수", "자료 해석", "자료 해석"), "자료 해석")   # 과반
        self.assertEqual(pick_reason("계산 실수", "자료 해석", "개념 부족"), "계산 실수")   # 모두 다름 → 학생
        self.assertEqual(pick_reason("", "자료 해석", "개념 부족"), "자료 해석")           # 둘이 다름 → 조교
        self.assertEqual(pick_reason("", "", "개념 부족"), "개념 부족")
        self.assertEqual(pick_reason("", "", ""), "")

    def test_report_uses_representative_reason(self):
        mid = self._exam()
        self.c1.get(f"/s/analysis?mock={mid}")                                    # 내 답안 가져오기
        self.c1.post(f"/s/wrong/{mid}/3", data={"reason": "개념 부족"})
        self.c1.post(f"/s/analysis/{mid}/paper", data={"image": [(io.BytesIO(PNG), "a.png")]}, content_type="multipart/form-data")
        with self.app.app_context():
            pid = query("SELECT id FROM exam_papers", one=True)["id"]
        self.ta.post(f"/t/papers/{pid}", data={"r3": "계산 실수", "r4": "자료 해석"})
        with self.app.test_request_context():
            import exams
            ws = {a["no"]: a for a in exams.student_report(mid, self.s1)["wrongs"]}
        self.assertEqual(ws[3]["type"], exams.pick_reason("개념 부족", "계산 실수", ws[3]["auto_type"]))
        self.assertEqual(ws[4]["type"], exams.pick_reason("", "자료 해석", ws[4]["auto_type"]))

    def test_staff_report_without_account(self):
        """계정이 없는 학생도 OMR 결과가 성적 리포트에 나온다 (예전에는 계정 기준 표만 읽어 비었다)."""
        with self.app.app_context():
            execute("DELETE FROM users WHERE student_id = ?", (self.s1,))
        self._exam()
        page = self.ta.get(f"/t/students/{self.s1}/report").data.decode()
        self.assertNotIn("기록된 시험 성적이 없습니다", page)
        self.assertIn("복습 테스트 1회", page); self.assertIn("4 / 10", page)

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
        resp = anon.get(f"/p/{tok}")
        self.assertEqual(resp.headers["Cache-Control"], "no-store")
        page = resp.data.decode()
        for word in ("김하나", "득점률", "40", "자료 해석", "x축을 시간으로 읽음", "그래프 축부터 확인", "산과 염기", "복습 테스트 1회"):
            self.assertIn(word, page)
        self.assertIn("noindex", page)
        self.assertEqual(anon.get("/p/" + "x" * 24).status_code, 404)
        self.assertEqual(anon.get("/p/short").status_code, 404)
        sms = self.ta.get(f"/t/mocks/{mid}/sms").data.decode()
        self.assertIn(f"/p/{tok}", sms)

if __name__ == "__main__":
    unittest.main()
