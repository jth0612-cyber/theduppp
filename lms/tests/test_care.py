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

    def test_missing_students_confirmed_absent(self):
        """결과가 올라온 반의 재원생 중 결과가 없는 학생이 누락으로 뜨고, 결시로 확인하면 빠진다. 다음 행동 버튼도 따라 바뀐다."""
        mid = self._exam()
        with self.app.app_context():
            s3 = execute("INSERT INTO students (class_id, name, student_no) VALUES (?, '박세나', '270003')", (self.a,))
        page = self.ta.get(f"/t/mocks/{mid}").data.decode()
        self.assertIn("누락 학생 1명 확인", page); self.assertNotIn("학부모 문자 보기", page)
        omr = self.ta.get(f"/t/mocks/{mid}?tab=omr").data.decode()
        self.assertIn("박세나", omr); self.assertNotIn("이두리", omr)                      # 결과가 없는 B반 학생은 누락이 아니다
        self.assertNotIn(f'name="sid" value="{s3}" checked', omr)                        # 수업 출석 기록이 결석이 아니면 미리 고르지 않는다
        self.ta.post(f"/t/mocks/{mid}/absent", data={"sid": [str(s3), str(self.s2)]})    # 누락이 아닌 학생은 무시한다
        with self.app.app_context():
            self.assertEqual([r["student_id"] for r in query("SELECT student_id FROM exam_absent WHERE mock_id = ?", (mid,))], [s3])
        page = self.ta.get(f"/t/mocks/{mid}").data.decode()
        self.assertIn("학부모 문자 보기", page); self.assertNotIn("명 확인", page)
        self.ta.post(f"/t/mocks/{mid}/absent", data={"undo": "1"})
        self.assertIn("누락 학생 1명 확인", self.ta.get(f"/t/mocks/{mid}").data.decode())
        self.assertNotEqual(self.c1.post(f"/t/mocks/{mid}/absent", data={"sid": str(s3)}).status_code, 302)   # 학생은 못 한다
        # 보강 예정: 다른 반 수업에서 보기로 한 학생. 누락에서 빠지고, 결과가 올라오면 보강 예정에서도 사라진다
        self.ta.post(f"/t/mocks/{mid}/absent", data={"sid": str(s3), "kind": "makeup"})
        omr = self.ta.get(f"/t/mocks/{mid}?tab=omr").data.decode()
        self.assertIn("보강 예정 1명", omr); self.assertIn("학부모 문자 보기", omr)
        with self.app.app_context():
            import exams
            execute("INSERT INTO exam_results (mock_id, student_id, answers, score) VALUES (?, ?, '1234', 10)", (mid, s3))
            self.assertEqual(exams.missing_students(mid), ([], [], []))

    def test_game_board_ranks_within_class(self):
        """게임 시작 화면의 세 칸: 같은 반끼리만 견주고, 기록이 없으면 하는 법 한 줄이 나온다."""
        with self.app.app_context():
            s3 = execute("INSERT INTO students (class_id, name, student_no) VALUES (?, '박세나', '270003')", (self.a,))
            u = {r["username"]: r["id"] for r in query("SELECT id, username FROM users")}
            u3 = execute("INSERT INTO users (role, username, password_hash, student_id) VALUES ('student', '270003', ?, ?)", (hash_password(PW), s3))
            for uid, score in ((u["270001"], 7), (u["270001"], 4), (u3, 9), (u["270002"], 10)):      # 270002 는 B반
                execute("""INSERT INTO game_rounds (user_id, game, topic, payload, answer, score, total, started_at, finished_at)
                           VALUES (?, 'mixed', '', '[]', '[]', ?, 10, datetime('now'), datetime('now'))""", (uid, score))
        page = self.c1.get("/s/games/mixed").data.decode()
        flat = re.sub(r"<[^>]+>|\s+", "", page)
        self.assertIn("내최고기록7/10", flat); self.assertIn("반1등9/10", flat); self.assertIn("내순위2위/2명", flat)
        self.assertNotIn("g-board", self.c1.get("/s/games/chargaff").data.decode())          # 기록 없음: 하는 법 한 줄
        self.assertIn("A=T, G=C 규칙으로", self.c1.get("/s/games/chargaff").data.decode())

    def test_home_first_card_continues_last_study(self):
        """홈 첫 카드: 하던 학습이 없으면 오늘의 20단어, 있으면 그 학습으로. 웹 홈과 앱 홈이 같다."""
        for u in ("/s/", "/s/?view=app"):                                # 오늘 복습을 안 했으면 취약 단원 복습이 첫 카드
            self.assertIn('class="ah-go" href="/s/games/daily"', self.c1.get(u).data.decode())
        with self.app.app_context():                                     # 오늘 복습을 끝낸 뒤의 첫 카드를 본다
            me = query("SELECT id FROM users WHERE username = '270001'", one=True)["id"]
            execute("""INSERT INTO game_rounds (user_id, game, topic, payload, answer, score, total, started_at, finished_at)
                       VALUES (?, 'daily', '01', '[]', '[]', 5, 5, datetime('now', 'localtime', '-20 days'), datetime('now', 'localtime'))""", (me,))
        for u in ("/s/", "/s/?view=app"):
            page = self.c1.get(u).data.decode()
            self.assertIn('class="ah-go" href="/s/games/vocab"', page); self.assertNotIn("이어서 학습하기", page)
        with self.app.app_context():
            uid = query("SELECT id FROM users WHERE username = '270001'", one=True)["id"]
            for game, topic in (("quiz", "06"), ("dna", "rna"), ("play_shell", ""), ("sci_speed", ""), ("mixed", "")):
                execute("""INSERT INTO game_rounds (user_id, game, topic, payload, answer, score, total, started_at, finished_at)
                           VALUES (?, ?, ?, '[]', '[]', 3, 10, datetime('now', 'localtime'), datetime('now', 'localtime'))""", (uid, game, topic))
                for u in ("/s/", "/s/?view=app"):
                    r = self.c1.get(u)
                    self.assertEqual(r.status_code, 200, (game, u)); self.assertIn("이어서 학습하기", r.data.decode())
        self.assertIn('class="ah-go" href="/s/games/mixed"', self.c1.get("/s/").data.decode())

    def test_question_scrap(self):
        """질답 스크랩: 볼 수 있는 질문만 켜고 끌 수 있고, 스크랩 탭에는 내 것만 모인다."""
        with self.app.app_context():
            q1 = execute("INSERT INTO questions (student_id, title, body, qtype) VALUES (?, '공개 질문', '내용', '학습질문')", (self.s2,))
            q2 = execute("INSERT INTO questions (student_id, title, body, qtype) VALUES (?, '남의 행정문의', '내용', '행정문의')", (self.s2,))
        self.assertIn("스크랩한 질문이 없어요", self.c1.get("/s/questions?view=scrap").data.decode())
        self.c1.post(f"/s/questions/{q1}/scrap")
        self.assertIn("공개 질문", self.c1.get("/s/questions?view=scrap").data.decode())
        self.assertIn("스크랩 해제", self.c1.get(f"/s/questions/{q1}").data.decode())
        self.assertNotIn("공개 질문", self.c2.get("/s/questions?view=scrap").data.decode())      # 남의 스크랩은 안 보인다
        self.assertEqual(self.c1.post(f"/s/questions/{q2}/scrap").status_code, 404)             # 볼 수 없는 질문
        self.c1.post(f"/s/questions/{q1}/scrap")
        self.assertIn("스크랩한 질문이 없어요", self.c1.get("/s/questions?view=scrap").data.decode())

    def test_question_report_block_and_moderate(self):
        """신고하면 신고한 학생에게만 바로 안 보이고, 조교가 숨기면 쓴 학생 말고는 안 보인다. 차단하면 그 학생의 글이 안 보인다."""
        with self.app.app_context():
            q1 = execute("INSERT INTO questions (student_id, title, body, qtype) VALUES (?, '이상한 글', '내용', '학습질문')", (self.s2,))
            q2 = execute("INSERT INTO questions (student_id, title, body, qtype) VALUES (?, '멀쩡한 글', '내용', '학습질문')", (self.s2,))
            s3 = execute("INSERT INTO students (class_id, name, student_no) VALUES (?, '박세나', '270003')", (self.a,))
            execute("INSERT INTO users (role, username, password_hash, student_id) VALUES ('student', '270003', ?, ?)", (hash_password(PW), s3))
        c3 = self.login("270003")
        self.assertEqual(self.c2.post(f"/s/questions/{q1}/report", data={"reason": "욕설이나 비방"}).status_code, 400)   # 내 글은 신고할 수 없다
        self.c1.post(f"/s/questions/{q1}/report", data={"reason": "욕설이나 비방"})
        self.assertNotIn("이상한 글", self.c1.get("/s/questions").data.decode())                 # 신고한 학생에게는 바로 안 보인다
        self.assertEqual(self.c1.get(f"/s/questions/{q1}").status_code, 404)
        self.assertIn("이상한 글", c3.get("/s/questions").data.decode())                        # 다른 학생에게는 아직 보인다
        lst = self.ta.get("/t/questions?status=all").data.decode()
        self.assertIn("신고 1", lst); self.assertIn("이상한 글", self.ta.get("/t/questions?status=all&reported=1").data.decode())
        self.assertNotIn("멀쩡한 글", self.ta.get("/t/questions?status=all&reported=1").data.decode())
        self.assertIn("욕설이나 비방", self.ta.get(f"/t/questions/{q1}").data.decode())
        self.ta.post(f"/t/questions/{q1}/moderate", data={"action": "hide"})
        self.assertNotIn("이상한 글", c3.get("/s/questions").data.decode())                     # 숨기면 다른 학생에게 안 보인다
        self.assertIn("신고를 받아", self.c2.get(f"/s/questions/{q1}").data.decode())            # 쓴 학생에게는 보이고 숨김 안내
        self.assertNotEqual(self.c1.post(f"/t/questions/{q1}/moderate", data={"action": "show"}).status_code, 302)   # 학생은 못 한다
        self.c1.post(f"/s/questions/{q2}/block")                                                # 차단: 그 학생의 다른 글도 안 보인다
        self.assertNotIn("멀쩡한 글", self.c1.get("/s/questions").data.decode())
        self.assertIn("차단한 학생 1명", self.c1.get("/password").data.decode())
        self.c1.post("/s/blocks/clear")
        self.assertIn("멀쩡한 글", self.c1.get("/s/questions").data.decode())

    def test_account_delete_keeps_school_records(self):
        """계정 삭제: 비밀번호 확인 뒤 로그인 계정과 앱 활동만 지운다. 성적과 질문은 남고 가입 코드는 다시 쓸 수 있다."""
        mid = self._exam()
        with self.app.app_context():
            uid = query("SELECT id FROM users WHERE username = '270001'", one=True)["id"]
            q1 = execute("INSERT INTO questions (student_id, title, body, qtype) VALUES (?, '남는 질문', '내용', '학습질문')", (self.s1,))
            execute("""INSERT INTO game_rounds (user_id, game, topic, payload, answer, score, total, started_at)
                       VALUES (?, 'mixed', '', '[]', '[]', 3, 10, datetime('now'))""", (uid,))
            code = execute("INSERT INTO student_codes (class_id, code, student_id, used_at) VALUES (?, 'ABCD2345', ?, datetime('now'))", (self.a, self.s1))
        self.assertEqual(self.app.test_client().get("/account-deletion").status_code, 200)      # 안내는 로그인 없이 열린다
        self.c1.post("/s/account-delete", data={"password": "틀린비밀번호"})
        with self.app.app_context():
            self.assertIsNotNone(query("SELECT 1 FROM users WHERE id = ?", (uid,), one=True))   # 비밀번호가 다르면 그대로
        r = self.c1.post("/s/account-delete", data={"password": PW})
        self.assertIn("/login", r.headers["Location"])
        with self.app.app_context():
            self.assertIsNone(query("SELECT 1 FROM users WHERE id = ?", (uid,), one=True))
            self.assertIsNone(query("SELECT 1 FROM game_rounds WHERE user_id = ?", (uid,), one=True))
            self.assertIsNotNone(query("SELECT 1 FROM exam_results WHERE mock_id = ? AND student_id = ?", (mid, self.s1), one=True))
            self.assertIsNotNone(query("SELECT 1 FROM questions WHERE id = ?", (q1,), one=True))
            self.assertIsNone(query("SELECT student_id FROM student_codes WHERE id = ?", (code,), one=True)["student_id"])
        self.assertNotEqual(self.c1.get("/s/").status_code, 200)                                # 로그인이 풀린다
        self.assertIn("탈퇴한 학생", self.c2.get(f"/s/questions/{q1}").data.decode())

    def test_daily_review_card_and_round(self):
        """홈 첫 카드는 오늘 안 풀었으면 취약 단원 복습 5문제. 한 판 끝내면 이어서 학습하기로 바뀐다."""
        self._exam()                                                    # 산과 염기 문항을 틀렸다
        home = self.c1.get("/s/").data.decode()
        self.assertIn("취약 단원 복습 5문제", home); self.assertIn('href="/s/games/daily"', home)
        r = self.c1.post("/s/games/daily/start", json={}).get_json()
        self.assertEqual(len(r["questions"]), 5)
        self.assertEqual(self.c1.post(f"/s/games/daily/{r['round_id']}/submit", json={"answers": [0] * 5}).status_code, 200)
        home = self.c1.get("/s/").data.decode()
        self.assertNotIn("취약 단원 복습 5문제", home); self.assertIn("오늘의 20단어", home)       # 끝내면 다른 학습으로 넘어간다
        with self.app.app_context():
            execute("UPDATE game_rounds SET finished_at = datetime('now', 'localtime', '-4 days') WHERE game = 'daily'")
        self.assertIn("사흘 전에 복습한 단원", self.c1.get("/s/").data.decode())               # 사흘 뒤 같은 단원을 다시

    def test_room_board_report_and_public_erase_request(self):
        """칠판 글 신고: 신고한 학생에게는 안 보이고 조교 화면에 표시된다. 로그인 없이 낸 삭제 요청은 행정문의로 들어온다."""
        with self.app.app_context():
            u2 = query("SELECT id FROM users WHERE username = '270002'", one=True)["id"]
            cid = execute("INSERT INTO room_chat (place, user_id, body) VALUES ('sento', ?, '이상한 말')", (u2,))
        self.assertIn("이상한 말", self.c1.get("/s/rooms/sento/board").data.decode())
        self.assertEqual(self.c2.post("/s/rooms/sento/report", data={"id": cid}).status_code, 400)      # 내 글은 신고할 수 없다
        self.c1.post("/s/rooms/sento/report", data={"id": cid, "action": "report"})
        self.assertNotIn("이상한 말", self.c1.get("/s/rooms/sento/board").data.decode())
        self.assertIn("신고 1", self.ta.get("/t/rooms").data.decode())
        anon = self.app.test_client()
        anon.post("/account-deletion", data={"name": "김하나", "student_no": "270001"})
        anon.post("/account-deletion", data={"name": "없는사람", "student_no": "999"})                   # 맞지 않아도 같은 답
        with self.app.app_context():
            self.assertEqual(query("SELECT COUNT(*) AS n FROM questions WHERE title = '개인정보 삭제 요청'", one=True)["n"], 1)

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

    def test_my_study_timer_counts_seconds(self):
        import progress
        with self.app.app_context():
            uid = query("SELECT id FROM users WHERE username = '270001'", one=True)["id"]
        page = self.c1.get("/s/my").data.decode()
        self.assertIn("측정 시작", page); self.assertIn("00:00:00", page); self.assertIn("직접 측정", page)
        self.assertIn("오늘은 기록이 없어요", page); self.assertNotIn("0초", page)
        self.c1.post("/s/my/timer", data={"action": "start"})
        self.assertIn("측정 끝내기", self.c1.get("/s/my").data.decode())
        with self.app.app_context():                                   # 최소 제한 없음: 20초도 기록한다
            execute("UPDATE study_timers SET started_at = datetime('now', 'localtime', '-20 seconds') WHERE user_id = ?", (uid,))
        self.assertIn("초 기록했어요", self.c1.post("/s/my/timer", data={"action": "stop"}, follow_redirects=True).data.decode())
        with self.app.app_context():
            self.assertTrue(20 <= query("SELECT seconds FROM timer_logs", one=True)["seconds"] <= 24)
            execute("DELETE FROM timer_logs")
        self.c1.post("/s/my/timer", data={"action": "start"})
        with self.app.app_context():                                   # 1분 35초 잰 것으로
            execute("UPDATE study_timers SET started_at = datetime('now', 'localtime', '-95 seconds') WHERE user_id = ?", (uid,))
        self.assertIn("1분 3", self.c1.post("/s/my/timer", data={"action": "stop"}, follow_redirects=True).data.decode())
        with self.app.app_context():
            sec = query("SELECT seconds FROM timer_logs WHERE user_id = ?", (uid,), one=True)["seconds"]
            self.assertTrue(95 <= sec <= 99)
            s = progress.today_summary(uid)
            self.assertEqual(s["seconds"], sec); self.assertEqual(s["minutes"], 2); self.assertEqual(s["streak"], 1)
            self.assertEqual(progress.weekly_ranking(uid)["me"]["minutes"], 2)
            self.assertIsNone(query("SELECT 1 FROM focus_logs", one=True))        # 소도시 명상 기록과 섞이지 않는다
        self.assertIn("00:01:3", self.c1.get("/s/my").data.decode())
        # 한 번에 100분까지만
        self.c1.post("/s/my/timer", data={"action": "start"})
        with self.app.app_context():
            execute("UPDATE study_timers SET started_at = datetime('now', 'localtime', '-5 hours') WHERE user_id = ?", (uid,))
        self.assertIn("100분까지만", self.c1.post("/s/my/timer", data={"action": "stop"}, follow_redirects=True).data.decode())
        with self.app.app_context():
            self.assertEqual(query("SELECT MAX(seconds) AS s FROM timer_logs", one=True)["s"], 100 * 60)
        # 소도시 명상에서 집중을 시작하면 직접 측정은 거기서 끝난다, 집중 중에는 측정을 시작할 수 없다
        self.c1.post("/s/my/timer", data={"action": "start"})
        self.c1.post("/s/rooms/sento/beat", data={"action": "start", "plan": "40"})
        with self.app.app_context():
            self.assertIsNone(query("SELECT 1 FROM study_timers", one=True))
        self.assertIn("집중 중이에요", self.c1.post("/s/my/timer", data={"action": "start"}, follow_redirects=True).data.decode())

    def test_date_filters_and_no_iso_on_screen(self):
        from datetime import date
        f = self.app.jinja_env.filters
        y = date.today().year
        self.assertEqual(f["d"](f"{y}-08-09"), "08.09")                       # 올해는 월.일
        self.assertEqual(f["d"](f"{y - 1}-11-15 09:05:33"), f"{y - 1}.11.15")  # 다른 해는 연도까지
        self.assertEqual(f["dt"](f"{y}-11-15T09:05:33"), "11.15 09:05")        # 시각은 분까지, T 와 초는 내지 않는다
        self.assertEqual(f["dt"](f"{y}-11-15"), "11.15"); self.assertEqual(f["t"](f"{y}-11-15 09:05"), "09:05")
        self.assertEqual(f["d"](None), ""); self.assertEqual(f["d"]("미정"), "미정")
        mid = self._exam()
        for c, u in ((self.c1, "/s/scores"), (self.c1, f"/s/analysis?mock={mid}"), (self.c1, "/s/wrong"), (self.ta, f"/t/mocks/{mid}"), (self.ta, "/t/audit")):
            page = re.sub(r"<(script|style)[^>]*>.*?</>|<[^>]+>", " ", c.get(u).data.decode(), flags=re.S)
            self.assertIsNone(re.search(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}", page), u)   # 화면 글에 ISO 시각이 없다
        w = self.c1.get("/s/wrong").data.decode()
        self.assertIn("전체 ", w); self.assertIn('정답 <u class="ans-key">3</u>', w); self.assertIn("산과 염기", w)   # 오답 노트: 기준, 정답, 단원

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
        for word in ("김하나", "100점 환산", "40", "자료 해석", "x축을 시간으로 읽음", "그래프 축부터 확인", "산과 염기", "복습 테스트 1회"):
            self.assertIn(word, page)
        self.assertIn("noindex", page)
        self.assertEqual(anon.get("/p/" + "x" * 24).status_code, 404)
        self.assertEqual(anon.get("/p/short").status_code, 404)
        lst = self.ta.get(f"/t/mocks/{mid}/sms").data.decode()                      # 목록에는 문자 원문이 없고, 학생을 눌러야 열린다
        self.assertIn(f"sid={self.s1}", lst); self.assertNotIn(f"/p/{tok}", lst)
        sms = self.ta.get(f"/t/mocks/{mid}/sms?sid={self.s1}").data.decode()
        self.assertIn(f"/p/{tok}", sms); self.assertIn("문자 복사", sms)
        self.assertIn("찾는 학생이 없어요", self.ta.get(f"/t/mocks/{mid}/sms?q=없는이름").data.decode())
        self.assertEqual(self.ta.get(f"/t/mocks/{mid}/sms?sid=99999").status_code, 404)

if __name__ == "__main__":
    unittest.main()
