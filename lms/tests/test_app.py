"""기능·보안 점검: python -m unittest discover tests"""
import io
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from db import execute, query  # noqa: E402
from security import hash_password  # noqa: E402

TEACHER_PW = "Teach3r!pass"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


class AppTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "DATABASE": os.path.join(self.tmp.name, "t.sqlite3"),
            "UPLOAD_DIR": os.path.join(self.tmp.name, "up"),
        })
        os.makedirs(self.app.config["UPLOAD_DIR"], exist_ok=True)
        with self.app.app_context():
            from db import init_db
            init_db(self.app.config["DATABASE"])
            execute("INSERT INTO users (role, username, password_hash) VALUES ('teacher', 'teacher', ?)",
                    (hash_password(TEACHER_PW),))
        self.c = self.app.test_client()
        from views import auth
        auth._ip_attempts.clear()

    def tearDown(self):
        with self.app.app_context():
            from db import close_db
            close_db()
        self.tmp.cleanup()

    def login(self, client, user, pw):
        return client.post("/login", data={"username": user, "password": pw})

    def setup_class_with_students(self):
        self.login(self.c, "teacher", TEACHER_PW)
        r = self.c.post("/t/classes", data={"name": "A반"})
        cid = int(r.headers["Location"].rsplit("/", 1)[-1])
        csv_data = "이름,수험번호,연락처,목표,메모\n김민수,A001,010-1111-2222,서울대,=CMD()\n이영희,A002,,,\n"
        self.c.post(f"/t/classes/{cid}/import",
                    data={"csv": (io.BytesIO(csv_data.encode("cp949")), "s.csv")},
                    content_type="multipart/form-data")
        return cid

    def issue_accounts(self, cid):
        r = self.c.post(f"/t/classes/{cid}/accounts")
        text = r.data.decode("utf-8-sig")
        return {m[0]: m[1] for m in re.findall(r"(A\d+),(\w+)", text)}

    def student_client(self, username, temp):
        sc = self.app.test_client()
        self.login(sc, username, temp)
        new_pw = "Student!2026"
        sc.post("/password", data={"current": temp, "new": new_pw, "confirm": new_pw})
        return sc

    def ask(self, client, title, body="본문", qtype="학습질문", image=True):
        data = {"title": title, "body": body, "qtype": qtype}
        if image:
            data["image"] = (io.BytesIO(PNG), "q.png")
        r = client.post("/s/questions", data=data, content_type="multipart/form-data")
        return int(r.headers["Location"].rsplit("/", 1)[-1])

    # ---------- 기능 ----------

    def test_full_flow(self):
        cid = self.setup_class_with_students()
        with self.app.app_context():
            self.assertEqual(query("SELECT COUNT(*) n FROM students", one=True)["n"], 2)
            row = query("SELECT phone_enc FROM students WHERE student_no='A001'", one=True)
            self.assertNotIn("010", row["phone_enc"])  # 연락처는 암호화 저장

        r = self.c.post(f"/t/classes/{cid}/exams",
                        data={"name": "주간1", "exam_date": "2026-10-20", "max_score": "100"})
        eid = int(r.headers["Location"].rsplit("/", 1)[-1])
        with self.app.app_context():
            ids = {s["student_no"]: s["id"] for s in query("SELECT id, student_no FROM students")}
        self.c.post(f"/t/exams/{eid}", data={f"score_{ids['A001']}": "88", f"score_{ids['A002']}": "150"})
        with self.app.app_context():
            self.assertEqual(query("SELECT COUNT(*) n FROM scores", one=True)["n"], 1)  # 범위 밖 점수 거부

        export = self.c.get(f"/t/exams/{eid}/export").data.decode("utf-8-sig")
        self.assertIn("김민수", export)

        page = self.c.get(f"/t/students/{ids['A001']}").data.decode()
        self.assertIn("010-1111-2222", page)

        accounts = self.issue_accounts(cid)
        self.assertEqual(set(accounts), {"A001", "A002"})

        sc = self.student_client("A001", accounts["A001"])
        self.assertEqual(sc.get("/s/").status_code, 200)
        qid = self.ask(sc, "22번", "모르겠어요")
        self.c.post(f"/t/questions/{qid}", data={"body": "이렇게 풀어요"})
        self.assertIn("이렇게 풀어요", sc.get(f"/s/questions/{qid}").data.decode())
        self.assertIn("88", sc.get("/s/scores").data.decode())

    # ---------- 보안 ----------

    def test_student_cannot_access_teacher_or_other_students(self):
        cid = self.setup_class_with_students()
        accounts = self.issue_accounts(cid)
        s1 = self.student_client("A001", accounts["A001"])
        s2 = self.student_client("A002", accounts["A002"])

        self.assertEqual(s1.get("/t/").status_code, 403)
        self.assertEqual(s1.get("/t/students").status_code, 403)
        self.assertEqual(s1.post(f"/t/classes/{cid}/accounts").status_code, 403)

        qid = self.ask(s1, "비밀", "x")
        with self.app.app_context():
            fid = query("SELECT image_id FROM questions WHERE id=?", (qid,), one=True)["image_id"]
        # 질답 게시판은 공개: 다른 학생도 질문과 사진을 볼 수 있다
        self.assertEqual(s2.get(f"/s/file/{fid}").status_code, 200)
        self.assertEqual(s1.get(f"/s/file/{fid}").status_code, 200)
        # 하지만 남의 질문은 삭제할 수 없다
        self.assertEqual(s2.post(f"/s/questions/{qid}/delete").status_code, 404)
        # 남의 성적·학생 정보 페이지는 여전히 차단
        self.assertEqual(s2.get("/t/students").status_code, 403)

    def test_public_board_shows_nickname_not_real_name(self):
        cid = self.setup_class_with_students()
        accounts = self.issue_accounts(cid)
        s1 = self.student_client("A001", accounts["A001"])
        s2 = self.student_client("A002", accounts["A002"])
        qid = self.ask(s1, "공개질문")
        with self.app.app_context():
            nick = query("SELECT nickname FROM users WHERE username = 'A001'", one=True)["nickname"]
        for page in (s2.get("/s/questions").data.decode(), s2.get(f"/s/questions/{qid}").data.decode()):
            self.assertIn("공개질문", page)
            self.assertIn(nick, page)
            self.assertNotIn("김민수", page)   # 실명 노출 금지
            self.assertNotIn("A001", page)     # 수험번호 노출 금지
        mine = s2.get("/s/questions?view=mine").data.decode()
        self.assertNotIn("공개질문", mine)

    def test_nickname_auto_assigned(self):
        from nickname import ANIMALS, MODIFIERS, generate_nickname
        self.assertNotIn("코알라", ANIMALS)
        cid = self.setup_class_with_students()
        self.issue_accounts(cid)
        with self.app.app_context():
            nicks = [r["nickname"] for r in query("SELECT nickname FROM users WHERE role = 'student'")]
        self.assertEqual(len(nicks), 2)
        self.assertEqual(len(set(nicks)), 2)
        for n in nicks:
            mod, animal = n.split(" ")
            self.assertIn(mod, MODIFIERS)
            self.assertIn(animal, ANIMALS)
        # 1000명 넘게 만들어도 중복 없음
        taken = set()
        for _ in range(3000):
            taken.add(generate_nickname(lambda x: x in taken))
        self.assertEqual(len(taken), 3000)
        self.assertFalse(any("코알라" in n for n in taken))

    def test_material_only_for_own_class(self):
        cid = self.setup_class_with_students()
        r = self.c.post("/t/classes", data={"name": "다른반"})
        other = int(r.headers["Location"].rsplit("/", 1)[-1])
        self.c.post(f"/t/classes/{other}/materials", data={"title": "x", "file": (io.BytesIO(b"%PDF-1.4 test"), "a.pdf")},
                    content_type="multipart/form-data")
        with self.app.app_context():
            fid = query("SELECT file_id FROM materials", one=True)["file_id"]
        accounts = self.issue_accounts(cid)
        s1 = self.student_client("A001", accounts["A001"])
        self.assertEqual(s1.get(f"/s/file/{fid}").status_code, 404)

    def test_upload_validation(self):
        cid = self.setup_class_with_students()
        for name, data in [("evil.html", b"<script>"), ("fake.pdf", b"<html>not pdf"), ("x.exe", b"MZ")]:
            self.c.post(f"/t/classes/{cid}/materials", data={"title": "x", "file": (io.BytesIO(data), name)},
                        content_type="multipart/form-data")
        with self.app.app_context():
            self.assertEqual(query("SELECT COUNT(*) n FROM materials", one=True)["n"], 0)

    def test_must_change_password_and_lockout(self):
        cid = self.setup_class_with_students()
        accounts = self.issue_accounts(cid)
        sc = self.app.test_client()
        self.login(sc, "A001", accounts["A001"])
        r = sc.get("/s/")
        self.assertIn("/password", r.headers["Location"])  # 임시 비밀번호 상태에선 다른 화면 차단

        bad = self.app.test_client()
        for _ in range(5):
            self.login(bad, "A002", "wrong-password")
        r = self.login(bad, "A002", accounts["A002"])
        self.assertIn("잠겼습니다", r.data.decode())

    def test_xss_escaped_and_headers(self):
        self.login(self.c, "teacher", TEACHER_PW)
        self.c.post("/t/classes", data={"name": "<script>alert(1)</script>"})
        r = self.c.get("/t/classes")
        body = r.data.decode()
        self.assertNotIn("<script>alert(1)</script>", body)
        self.assertIn("&lt;script&gt;", body)
        self.assertIn("default-src 'self'", r.headers["Content-Security-Policy"])
        self.assertEqual(r.headers["X-Frame-Options"], "DENY")
        self.assertEqual(r.headers["Cache-Control"], "no-store")

    def test_csv_formula_injection_neutralized(self):
        cid = self.setup_class_with_students()
        self.c.post(f"/t/classes/{cid}/students", data={"name": "=HYPERLINK(1)", "student_no": "B1"})
        r = self.c.post(f"/t/classes/{cid}/exams", data={"name": "e", "exam_date": "2026-10-20", "max_score": "10"})
        eid = int(r.headers["Location"].rsplit("/", 1)[-1])
        out = self.c.get(f"/t/exams/{eid}/export").data.decode("utf-8-sig")
        self.assertIn("'=HYPERLINK(1)", out)

    def test_open_redirect_blocked(self):
        r = self.c.post("/login?next=//evil.com", data={"username": "teacher", "password": TEACHER_PW})
        self.assertNotIn("evil.com", r.headers["Location"])

    def test_csrf_enforced(self):
        self.app.config["WTF_CSRF_ENABLED"] = True
        self.login(self.c, "teacher", TEACHER_PW)  # 토큰 없으므로 거부되어야 함
        self.assertEqual(self.c.get("/t/").status_code, 302)


class FeatureTest(AppTest):
    """질답 개선, 공지 말머리, 강의 영상, 뉴스, 접속 기록, 미니게임."""

    def _students(self):
        cid = self.setup_class_with_students()
        accounts = self.issue_accounts(cid)
        return cid, self.student_client("A001", accounts["A001"]), self.student_client("A002", accounts["A002"])

    def test_question_types_and_privacy(self):
        _, s1, s2 = self._students()
        # 학습질문은 사진 필수
        r = s1.post("/s/questions", data={"title": "t", "body": "b", "qtype": "학습질문"})
        self.assertNotIn("/s/questions/", r.headers.get("Location", ""))
        # 행정문의는 사진 없이 가능, 다른 학생에게는 비공개
        qid = self.ask(s1, "등록 확인 부탁", qtype="행정문의", image=False)
        self.assertEqual(s1.get(f"/s/questions/{qid}").status_code, 200)
        self.assertEqual(s2.get(f"/s/questions/{qid}").status_code, 404)
        self.assertNotIn("등록 확인 부탁", s2.get("/s/questions").data.decode())
        self.assertIn("등록 확인 부탁", self.c.get("/t/questions?qtype=행정문의").data.decode())

    def test_followups_limited_and_reopen(self):
        _, s1, s2 = self._students()
        qid = self.ask(s1, "42p 3번")
        # 답변 전에는 추가 질문 불가
        s1.post(f"/s/questions/{qid}/followup", data={"body": "추가"})
        with self.app.app_context():
            self.assertEqual(query("SELECT COUNT(*) n FROM followups", one=True)["n"], 0)
        self.c.post(f"/t/questions/{qid}", data={"body": "답변1"})
        # 남의 질문에는 추가 질문 불가
        self.assertEqual(s2.post(f"/s/questions/{qid}/followup", data={"body": "끼어들기"}).status_code, 404)
        for i in range(3):
            s1.post(f"/s/questions/{qid}/followup", data={"body": f"추가{i}"})
        with self.app.app_context():
            self.assertEqual(query("SELECT COUNT(*) n FROM followups", one=True)["n"], 2)  # 최대 2번
            self.assertEqual(query("SELECT status FROM questions WHERE id=?", (qid,), one=True)["status"], "open")
        page = self.c.get(f"/t/questions/{qid}").data.decode()
        self.assertIn("추가0", page)
        self.assertIn("추가1", page)
        # 답변이 달린 질문은 학생이 지울 수 없음
        self.assertEqual(s1.post(f"/s/questions/{qid}/delete").status_code, 404)

    def test_notice_tags_and_errata(self):
        cid, s1, _ = self._students()
        self.c.post(f"/t/classes/{cid}/notices", data={"tag": "정오", "textbook": "개념서 1권",
                                                      "title": "42p 오타", "body": "3번 보기 수정"})
        self.c.post(f"/t/classes/{cid}/notices", data={"tag": "<script>", "title": "일반", "body": "x"})
        with self.app.app_context():
            tags = {r["tag"] for r in query("SELECT tag FROM notices")}
        self.assertEqual(tags, {"정오", "공지"})  # 허용되지 않은 말머리는 '공지'로
        errata = s1.get("/s/notices?tag=정오").data.decode()
        self.assertIn("개념서 1권", errata)
        self.assertNotIn("일반", errata)

    def test_video_links_validated_and_expire(self):
        cid, s1, _ = self._students()
        for url in ["javascript:alert(1)", "http://youtu.be/abcdefghijk", "https://evil.example.com/v"]:
            self.c.post(f"/t/classes/{cid}/videos", data={"title": "x", "url": url})
        self.c.post(f"/t/classes/{cid}/videos", data={"title": "지난영상", "url": "https://youtu.be/abcdefghijk",
                                                     "expires_on": "2000-01-01"})
        self.c.post(f"/t/classes/{cid}/videos", data={"title": "원소의 생성",
                                                     "url": "https://www.youtube.com/watch?v=abcdefghijk"})
        with self.app.app_context():
            self.assertEqual(query("SELECT COUNT(*) n FROM videos", one=True)["n"], 2)
        page = s1.get("/s/videos").data.decode()
        self.assertIn("원소의 생성", page)
        self.assertNotIn("지난영상", page)
        self.assertIn("i.ytimg.com/vi/abcdefghijk", page)

    def test_news_removed(self):
        _, s1, _ = self._students()
        self.assertEqual(self.c.get("/t/news").status_code, 404)
        self.assertNotIn("교육 뉴스", s1.get("/s/").data.decode())

    def test_visit_recorded_once_per_day_and_no_points(self):
        _, s1, _ = self._students()
        for _ in range(3):
            s1.get("/s/")
        with self.app.app_context():
            uid = query("SELECT id FROM users WHERE username='A001'", one=True)["id"]
            self.assertEqual(query("SELECT COUNT(*) n FROM visits WHERE user_id=?", (uid,), one=True)["n"], 1)
            sid = query("SELECT id FROM students WHERE student_no='A001'", one=True)["id"]
        page = self.c.get(f"/t/students/{sid}").data.decode()
        self.assertIn("누적 접속", page)
        self.assertNotIn("포인트", page)
        self.assertEqual(s1.get("/s/points").status_code, 404)              # 포인트 기능 없음
        self.assertEqual(self.c.post(f"/t/students/{sid}/points", data={"amount": "5"}).status_code, 404)

    def test_dna_game_scored_on_server(self):
        _, s1, s2 = self._students()
        start = s1.post("/s/games/dna/start", json={"level": 2}).get_json()
        self.assertEqual(len(start["strand"]), 12)
        self.assertNotIn("answer", start)
        pair = {"A": "T", "T": "A", "G": "C", "C": "G"}
        answer = "".join(pair[b] for b in start["strand"])
        rid = start["round_id"]
        self.assertEqual(s2.post(f"/s/games/dna/{rid}/submit", json={"answer": answer}).status_code, 404)
        res = s1.post(f"/s/games/dna/{rid}/submit", json={"answer": answer}).get_json()
        self.assertEqual(res["correct"], 12)
        self.assertNotIn("points", res)
        # 같은 판은 한 번만 제출
        self.assertEqual(s1.post(f"/s/games/dna/{rid}/submit", json={"answer": answer}).status_code, 409)

    def test_chargaff_questions_are_consistent(self):
        import quiz
        for _ in range(200):
            for item in quiz.chargaff_round():
                self.assertEqual(len(item["choices"]), 4)
                self.assertEqual(len(set(item["choices"])), 4)
                self.assertTrue(0 <= item["answer_index"] < 4)
        _, s1, _ = self._students()
        start = s1.post("/s/games/chargaff/start", json={}).get_json()
        self.assertNotIn("answer_index", str(start))  # 정답은 브라우저로 보내지 않음
        res = s1.post(f"/s/games/chargaff/{start['round_id']}/submit", json={"answers": [0, 0, 0, 0, 0]}).get_json()
        self.assertEqual(res["total"], 5)

    def test_quiz_scored_on_server(self):
        import json as _json
        _, s1, _ = self._students()
        self.assertEqual(s1.post("/s/games/quiz/start", json={"topic": "없는단원"}).status_code, 400)
        for _ in range(3):
            start = s1.post("/s/games/quiz/start", json={"topic": "life"}).get_json()
            self.assertNotIn("answer_index", str(start))
            with self.app.app_context():
                ans = _json.loads(query("SELECT answer FROM game_rounds WHERE id=?", (start["round_id"],),
                                        one=True)["answer"])
            res = s1.post(f"/s/games/quiz/{start['round_id']}/submit",
                          json={"answers": [a["answer_index"] for a in ans]}).get_json()
            self.assertEqual(res["score"], res["total"])

    def test_behind_synology_https_proxy(self):
        """시놀로지 리버스 프록시(HTTPS) 뒤에서 CSRF·보안 쿠키·실제 IP 기록이 동작하는지."""
        from unittest import mock
        with mock.patch.dict(os.environ, {"BEHIND_PROXY": "1", "SESSION_COOKIE_SECURE": "1"}):
            app = create_app({"TESTING": True, "DATABASE": os.path.join(self.tmp.name, "p.sqlite3"),
                              "UPLOAD_DIR": os.path.join(self.tmp.name, "up")})
        with app.app_context():
            execute("INSERT INTO users (role, username, password_hash) VALUES ('teacher', 'teacher', ?)",
                    (hash_password(TEACHER_PW),))
        c = app.test_client()
        proxy = {"X-Forwarded-For": "203.0.113.7", "X-Forwarded-Proto": "https",
                 "X-Forwarded-Host": "lms.example.synology.me"}
        base = "http://lms.example.synology.me"
        page = c.get(f"{base}/login", headers=proxy).data.decode()
        token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
        r = c.post(f"{base}/login", headers={**proxy, "Referer": "https://lms.example.synology.me/login"},
                   data={"csrf_token": token, "username": "teacher", "password": TEACHER_PW})
        self.assertEqual(r.status_code, 302)
        self.assertIn("/t/", r.headers["Location"])
        cookie = r.headers.get("Set-Cookie", "")
        self.assertIn("Secure", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("Strict-Transport-Security", r.headers)
        with app.app_context():
            self.assertEqual(query("SELECT ip FROM audit_log WHERE action='login'", one=True)["ip"], "203.0.113.7")
            from db import close_db
            close_db()

    def _make_assistant(self):
        r = self.c.post("/t/staff", data={"display_name": "김조교", "username": "ta_kim"})
        temp = re.findall(r'<span class="secret">([^<]+)</span>', r.data.decode())[1]
        ta = self.app.test_client()
        self.login(ta, "ta_kim", temp)
        ta.post("/password", data={"current": temp, "new": "Assist!2026", "confirm": "Assist!2026"})
        return ta

    def test_assistant_can_only_answer_questions(self):
        cid, s1, _ = self._students()
        ta = self._make_assistant()
        qid = self.ask(s1, "42p 3번")
        admin_q = self.ask(s1, "등록 문의", qtype="행정문의", image=False)
        with self.app.app_context():
            fid = query("SELECT image_id FROM questions WHERE id=?", (qid,), one=True)["image_id"]
            sid = query("SELECT id FROM students WHERE student_no='A001'", one=True)["id"]
        # 질문답변은 가능 (행정문의 포함), 첨부 사진도 볼 수 있음
        self.assertEqual(ta.get("/t/questions").status_code, 200)
        self.assertEqual(ta.get(f"/t/questions/{admin_q}").status_code, 200)
        self.assertEqual(ta.get(f"/s/file/{fid}").status_code, 200)
        page = ta.get(f"/t/questions/{qid}").data.decode()
        self.assertNotIn(f"/t/students/{sid}", page)  # 학생 상세로 가는 링크 없음
        ta.post(f"/t/questions/{qid}", data={"body": "조교가 설명할게요"})
        # 학생에게는 '조교 답변 (김조교)' 로 보임
        student_view = s1.get(f"/s/questions/{qid}").data.decode()
        self.assertIn("조교 답변", student_view)
        self.assertIn("김조교", student_view)
        # 그 밖의 강사 화면은 모두 차단
        for url in ["/t/", "/t/students", f"/t/students/{sid}", "/t/classes", f"/t/classes/{cid}",
                    "/t/audit", "/t/staff", "/t/timetable"]:
            self.assertEqual(ta.get(url).status_code, 403, url)
        self.assertEqual(ta.post(f"/t/classes/{cid}/accounts").status_code, 403)
        self.assertEqual(ta.post("/t/staff", data={"display_name": "x", "username": "ta_x"}).status_code, 403)
        # 학생 화면도 못 씀
        self.assertEqual(ta.get("/s/").status_code, 403)

    def test_assistant_disable_and_username_rules(self):
        self._students()
        ta = self._make_assistant()
        # 학생 수험번호와 겹치는 아이디는 거부
        self.c.post("/t/staff", data={"display_name": "겹침", "username": "A001"})
        self.c.post("/t/staff", data={"display_name": "이상한", "username": "<b>x</b>"})
        with self.app.app_context():
            self.assertEqual(query("SELECT COUNT(*) n FROM users WHERE role='assistant'", one=True)["n"], 1)
            uid = query("SELECT id FROM users WHERE username='ta_kim'", one=True)["id"]
        self.c.post(f"/t/staff/{uid}/toggle")
        # 사용 중지하면 지금 세션도 끊기고 다시 로그인도 안 됨
        self.assertEqual(ta.get("/t/questions").status_code, 302)
        r = self.login(self.app.test_client(), "ta_kim", "Assist!2026")
        self.assertIn("사용이 중지된 계정", r.data.decode())

    def test_old_database_migrates_to_assistant_role(self):
        import sqlite3

        from db import init_db
        path = os.path.join(self.tmp.name, "old.sqlite3")
        conn = sqlite3.connect(path)
        conn.executescript("""
            CREATE TABLE users (id INTEGER PRIMARY KEY,
                role TEXT NOT NULL CHECK (role IN ('teacher', 'student')),
                username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
                student_id INTEGER, must_change_pw INTEGER NOT NULL DEFAULT 0,
                failed_attempts INTEGER NOT NULL DEFAULT 0, locked_until TEXT, last_login_at TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')));
            INSERT INTO users (role, username, password_hash) VALUES ('teacher', 'old', 'x');
        """)
        conn.commit()
        conn.close()
        init_db(path)
        conn = sqlite3.connect(path)
        conn.execute("INSERT INTO users (role, username, password_hash) VALUES ('assistant', 'ta', 'x')")
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0], 2)
        conn.close()

    def _student_with_uploads(self, no):
        """질문 사진과 추가 질문 사진을 올린 학생을 만든다. (학생 id, 업로드 파일 경로들)"""
        cid = self.setup_class_with_students() if not hasattr(self, "_cid") else self._cid
        self._cid = cid
        self.c.post(f"/t/classes/{cid}/students", data={"name": "삭제대상", "student_no": no})
        with self.app.app_context():
            sid = query("SELECT id FROM students WHERE student_no=?", (no,), one=True)["id"]
        page = self.c.post(f"/t/students/{sid}/account").data.decode()
        temp = re.findall(r'<span class="secret">([^<]+)</span>', page)[1]
        s = self.student_client(no, temp)
        qid = self.ask(s, "사진 질문")
        self.c.post(f"/t/questions/{qid}", data={"body": "답변"})
        s.post(f"/s/questions/{qid}/followup", data={"body": "추가", "image": (io.BytesIO(PNG), "f.png")},
               content_type="multipart/form-data")
        with self.app.app_context():
            files = [r["stored_name"] for r in query("SELECT stored_name FROM files ORDER BY id DESC LIMIT 2")]
        return sid, qid, [os.path.join(self.app.config["UPLOAD_DIR"], f) for f in files]

    def test_delete_account_of_student_with_uploads_keeps_records(self):
        sid, qid, paths = self._student_with_uploads("D1")
        self.assertEqual(self.c.post(f"/t/students/{sid}/account/delete").status_code, 302)
        with self.app.app_context():
            self.assertIsNone(query("SELECT 1 FROM users WHERE student_id=?", (sid,), one=True))
            self.assertIsNotNone(query("SELECT 1 FROM questions WHERE id=?", (qid,), one=True))
        self.assertTrue(all(os.path.exists(p) for p in paths))  # 학습 기록과 사진은 유지
        # 다시 발급해도 정상
        self.assertEqual(self.c.post(f"/t/students/{sid}/account").status_code, 200)

    def test_deactivate_student_with_uploads_blocks_login(self):
        sid, _, _ = self._student_with_uploads("D2")
        r = self.c.post(f"/t/students/{sid}/edit", data={"name": "삭제대상", "student_no": "D2",
                                                        "class_id": str(self._cid)})
        self.assertEqual(r.status_code, 302)
        with self.app.app_context():
            self.assertEqual(query("SELECT active FROM students WHERE id=?", (sid,), one=True)["active"], 0)
            self.assertIsNone(query("SELECT 1 FROM users WHERE student_id=?", (sid,), one=True))
        self.assertEqual(self.login(self.app.test_client(), "D2", "Student!2026").status_code, 200)  # 로그인 실패 화면

    def test_hard_delete_erases_all_uploads(self):
        sid, qid, paths = self._student_with_uploads("D3")
        self.assertTrue(all(os.path.exists(p) for p in paths))
        self.assertEqual(self.c.post(f"/t/students/{sid}/delete", data={"confirm_name": "삭제대상"}).status_code, 302)
        with self.app.app_context():
            self.assertIsNone(query("SELECT 1 FROM students WHERE id=?", (sid,), one=True))
            self.assertIsNone(query("SELECT 1 FROM users WHERE student_id=?", (sid,), one=True))
            self.assertIsNone(query("SELECT 1 FROM questions WHERE id=?", (qid,), one=True))
            self.assertEqual(query("SELECT COUNT(*) n FROM files", one=True)["n"], 0)
        self.assertFalse(any(os.path.exists(p) for p in paths))  # 디스크에서도 삭제

    def test_old_database_files_table_migrates(self):
        import sqlite3

        from db import init_db
        path = os.path.join(self.tmp.name, "oldfiles.sqlite3")
        conn = sqlite3.connect(path)
        conn.executescript("""
            CREATE TABLE users (id INTEGER PRIMARY KEY,
                role TEXT NOT NULL CHECK (role IN ('teacher', 'assistant', 'student')),
                username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, student_id INTEGER);
            INSERT INTO users (id, role, username, password_hash) VALUES (1, 'teacher', 't', 'x');
            CREATE TABLE files (id INTEGER PRIMARY KEY, stored_name TEXT NOT NULL UNIQUE,
                original_name TEXT NOT NULL, mime TEXT NOT NULL, size INTEGER NOT NULL,
                owner_id INTEGER NOT NULL REFERENCES users(id),
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')));
            INSERT INTO files (id, stored_name, original_name, mime, size, owner_id) VALUES (7, 's', 'a.png', 'image/png', 1, 1);
        """)
        conn.commit()
        conn.close()
        init_db(path)
        init_db(path)  # 두 번 실행해도 안전
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("DELETE FROM users WHERE id = 1")
        self.assertEqual(conn.execute("SELECT id, owner_id FROM files").fetchall(), [(7, None)])
        self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
        conn.close()

    def _signup(self, client, code, name="박지민", no="S100", pw="Signup!2026", consent="1"):
        return client.post("/signup", data={"code": code, "name": name, "student_no": no,
                                            "password": pw, "confirm": pw, "consent": consent})

    def test_signup_requires_code_and_approval(self):
        cid = self.setup_class_with_students()
        with self.app.app_context():
            code = query("SELECT join_code FROM classes WHERE id=?", (cid,), one=True)["join_code"]
        self.assertEqual(len(code), 8)
        anon = self.app.test_client()
        # 틀린 코드, 동의 안 함 → 거부
        self._signup(anon, "WRONGCOD")
        self._signup(anon, code, consent="")
        with self.app.app_context():
            self.assertEqual(query("SELECT COUNT(*) n FROM signup_requests", one=True)["n"], 0)
        # 소문자·띄어쓰기 섞어 입력해도 받아줌
        r = self._signup(anon, code.lower()[:4] + " " + code.lower()[4:])
        self.assertIn("가입 신청 완료", r.data.decode())
        # 승인 전 로그인 → '승인 대기' 안내, 로그인은 안 됨
        r = self.login(anon, "S100", "Signup!2026")
        self.assertIn("승인을 기다리고", r.data.decode())
        self.assertEqual(anon.get("/s/").status_code, 302)
        # 같은 수험번호로 중복 신청 불가
        self._signup(self.app.test_client(), code, name="가짜")
        with self.app.app_context():
            self.assertEqual(query("SELECT COUNT(*) n FROM signup_requests", one=True)["n"], 1)
            rid = query("SELECT id FROM signup_requests", one=True)["id"]
        # 학생은 승인 화면 못 씀
        self.assertIn("가입 승인", self.c.get("/t/signups").data.decode())
        self.c.post("/t/signups", data={"action": "approve", "ids": [str(rid)]})
        with self.app.app_context():
            u = query("SELECT * FROM users WHERE username='S100'", one=True)
            self.assertIsNotNone(u["nickname"])
            self.assertEqual(u["must_change_pw"], 0)
            self.assertEqual(query("SELECT class_id FROM students WHERE id=?", (u["student_id"],), one=True)["class_id"], cid)
        self.login(anon, "S100", "Signup!2026")
        self.assertEqual(anon.get("/s/").status_code, 200)

    def test_signup_links_to_existing_roster_and_closed_class(self):
        cid = self.setup_class_with_students()  # 명단에 A001 김민수 (계정 없음)
        with self.app.app_context():
            code = query("SELECT join_code FROM classes WHERE id=?", (cid,), one=True)["join_code"]
        anon = self.app.test_client()
        self._signup(anon, code, name="김민수", no="A001")
        self.c.post("/t/signups", data={"action": "approve_all"})
        with self.app.app_context():
            self.assertEqual(query("SELECT COUNT(*) n FROM students WHERE student_no='A001'", one=True)["n"], 1)
            sid = query("SELECT student_id FROM users WHERE username='A001'", one=True)["student_id"]
            self.assertEqual(query("SELECT name FROM students WHERE id=?", (sid,), one=True)["name"], "김민수")
        # 이미 계정 있는 수험번호는 가입 불가
        r = self._signup(self.app.test_client(), code, name="김민수", no="A001")
        self.assertIn("이미 가입된", r.data.decode())
        # 가입 멈추기 → 코드가 맞아도 거부, 새 코드 만들면 예전 코드 무효
        self.c.post(f"/t/classes/{cid}/joincode", data={"action": "close"})
        self._signup(self.app.test_client(), code, no="S200")
        self.c.post(f"/t/classes/{cid}/joincode", data={"action": "open"})
        self.c.post(f"/t/classes/{cid}/joincode", data={"action": "regen"})
        self._signup(self.app.test_client(), code, no="S300")
        with self.app.app_context():
            self.assertEqual(query("SELECT COUNT(*) n FROM signup_requests", one=True)["n"], 0)

    def test_signup_rate_limited(self):
        anon = self.app.test_client()
        codes = [self._signup(anon, "BADCODE1", no=f"X{i}").status_code for i in range(12)]
        self.assertIn(429, codes)

    def test_quiz_bank_has_enough_questions(self):
        import quiz
        for key in quiz.TOPICS:
            self.assertGreaterEqual(len(quiz.BANK[key]), 5, key)
            items = quiz.bank_quiz(key)
            self.assertEqual(len(items), 5)
            for it in items:
                self.assertEqual(len(set(it["choices"])), 4)


# FeatureTest 는 AppTest 의 도우미만 쓰고, AppTest 의 테스트는 다시 돌리지 않는다
for _name in [n for n in vars(AppTest) if n.startswith("test_")]:
    setattr(FeatureTest, _name, None)


if __name__ == "__main__":
    unittest.main()
