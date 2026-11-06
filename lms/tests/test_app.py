"""기능·보안 점검: python -m unittest discover tests"""
import io
import os
import re
import sys
import tempfile
import unittest
from datetime import date
from unittest import mock

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
        return int(r.headers["Location"].split("?")[0].rsplit("/", 1)[-1])

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

    def test_question_form_keeps_what_was_written(self):
        _, s1, _ = self._students()
        # 사진 없이 학습질문을 올리면: 등록되지 않지만, 적은 제목·내용은 그대로 돌려주고 사진 칸에 안내
        r = s1.post("/s/questions", data={"title": "개념서 42p 3번", "body": "보기 ㄴ에서 막혔어요", "qtype": "학습질문"})
        page = r.data.decode()
        self.assertEqual(r.status_code, 400)
        self.assertIn('value="개념서 42p 3번"', page)
        self.assertIn("보기 ㄴ에서 막혔어요</textarea>", page)
        self.assertIn("사진만 붙여서 다시 등록하면 돼요", page)
        self.assertIn('<option value="학습질문" selected', page)
        with self.app.app_context():
            self.assertEqual(query("SELECT COUNT(*) n FROM questions", one=True)["n"], 0)
        # 이어서 사진만 붙여 보내면 등록
        qid = self.ask(s1, "개념서 42p 3번", body="보기 ㄴ에서 막혔어요")
        self.assertIn("보기 ㄴ에서 막혔어요", s1.get(f"/s/questions/{qid}").data.decode())

    def test_followup_keeps_body_on_error(self):
        _, s1, _ = self._students()
        qid = self.ask(s1, "42p 3번")
        self.c.post(f"/t/questions/{qid}", data={"body": "답변"})
        r = s1.post(f"/s/questions/{qid}/followup", data={"body": "추가로 궁금", "image": (io.BytesIO(b"not an image"), "x.gif")},
                    content_type="multipart/form-data")
        self.assertEqual(r.status_code, 400)
        self.assertIn("추가로 궁금</textarea>", r.data.decode())

    def test_week_best_questions(self):
        _, s1, s2 = self._students()
        hot = self.ask(s1, "많이 본 질문")
        self.ask(s1, "덜 본 질문")
        self.assertNotIn("이번 주 많이 본 질문", s2.get("/s/questions").data.decode())
        for _ in range(3):
            s2.get(f"/s/questions/{hot}")          # 같은 사람이 여러 번 봐도 하루 한 번
        s1.get(f"/s/questions/{hot}")              # 작성자 본인은 세지 않음
        with self.app.app_context():
            self.assertEqual(query("SELECT COUNT(*) n FROM question_views", one=True)["n"], 1)
            uid = query("SELECT id FROM users WHERE role='student' ORDER BY id DESC LIMIT 1", one=True)["id"]
            execute("INSERT INTO question_views (question_id, user_id, day) VALUES (?, ?, date('now','localtime','-1 day'))",
                    (hot, uid))
        page = s2.get("/s/questions").data.decode()
        if date.today().weekday() == 0:   # 월요일이면 어제 본 기록은 지난주
            self.assertNotIn("이번 주 많이 본 질문", page)
        else:
            self.assertIn("이번 주 많이 본 질문", page)
            self.assertIn("조회 2", page)
            self.assertLess(page.index("이번 주 많이 본 질문"), page.index("<table"))

    def test_staff_can_join_rooms_with_caption(self):
        _, s1, _ = self._students()
        ta = self._make_assistant()
        self.assertEqual(ta.get("/s/rooms").status_code, 200)
        self.assertEqual(self.c.get("/s/rooms/sanji").status_code, 200)        # 선생님도
        page = ta.get("/s/rooms/sanji").data.decode()
        self.assertIn('data-me-name="김조교" data-me-cap="조교"', page)
        r = s1.post("/s/rooms/sanji/beat", data={}).get_json()
        tas = [m for m in r["members"] if m.get("cap") == "조교"]
        self.assertEqual((tas[0]["nick"], tas[0]["cap"]), ("김조교", "조교"))
        teacher = [m for m in r["members"] if m.get("cap") == "선생님"]
        self.assertEqual(len(teacher), 1)
        self.assertIn('<span class="cap">조교</span> 김조교', s1.get("/s/rooms/sanji").data.decode())
        # 조교도 집중 기록은 남지만, 학생 순위(터줏대감)에는 들지 않는다
        ta.post("/s/rooms/sanji/beat", data={"action": "start", "plan": "15"})
        with self.app.app_context():
            execute("UPDATE room_presence SET focus_since = datetime('now', 'localtime', '-30 minutes')")
        self.assertEqual(ta.post("/s/rooms/sanji/done", data={"minutes": "15"}).get_json()["minutes"], 15)
        self.assertEqual(ta.get("/s/rooms/rank?place=sanji").status_code, 200)
        with self.app.app_context():
            from views.rooms import _ranking, _since
            ta_id = query("SELECT id FROM users WHERE username='ta_kim'", one=True)["id"]
            self.assertNotIn(ta_id, [r["id"] for r in _ranking("sanji", _since("week"))])
        # 메뉴에 '소도시 명상'
        self.assertIn("/s/rooms", ta.get("/t/questions").data.decode())

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

    def test_notice_reads_and_renotify(self):
        cid, s1, s2 = self._students()
        self.c.post(f"/t/classes/{cid}/notices", data={"title": "내일 휴강", "body": "자습 하세요"})
        with self.app.app_context():
            nid = query("SELECT id FROM notices", one=True)["id"]
        s1.get(f"/s/notices/{nid}")
        self.assertIn("1명 읽음", s1.get(f"/s/notices/{nid}").data.decode())   # 같은 학생은 한 번만
        page = self.c.get(f"/t/classes/{cid}?tab=notices").data.decode()
        self.assertRegex(page, r"<b>1/\d+명 읽음</b>")                       # 반 인원 중 읽은 수
        from unittest import mock
        from views import notices_job
        with self.app.app_context():
            # 아직 5시간이 안 됨 → 다시 알리지 않음
            self.assertEqual(notices_job.renotify_due(), 0)
            execute("UPDATE notices SET created_at = datetime('now', 'localtime', '-6 hours')")
            with mock.patch("views.pwa.notify_users") as sent:
                self.assertEqual(notices_job.renotify_due(), 1)
                self.assertEqual(notices_job.renotify_due(), 0)               # 한 번만
            sent.assert_called_once()
            readers = {r["user_id"] for r in query("SELECT user_id FROM notice_reads")}
            self.assertTrue(all(u not in readers for u in sent.call_args[0][0]))  # 읽은 학생은 빼고

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

    def test_quiz_checks_each_question_right_away(self):
        import json as _json
        _, s1, s2 = self._students()
        start = s1.post("/s/games/quiz/start", json={"topic": "life"}).get_json()
        rid = start["round_id"]
        with self.app.app_context():
            ans = _json.loads(query("SELECT answer FROM game_rounds WHERE id=?", (rid,), one=True)["answer"])
        # 1번: 맞게 고르면 바로 정답·해설
        r = s1.post(f"/s/games/quiz/{rid}/check", json={"i": 0, "pick": ans[0]["answer_index"]}).get_json()
        self.assertTrue(r["correct"]); self.assertEqual((r["score"], r["answered"]), (1, 1)); self.assertTrue(r["explanation"])
        # 2번: 틀리면 정답 번호를 알려 주고, 다시 보내도 처음 답이 그대로 (답 바꾸기 불가)
        wrong = (ans[1]["answer_index"] + 1) % len(ans[1]["choices"])
        r = s1.post(f"/s/games/quiz/{rid}/check", json={"i": 1, "pick": wrong}).get_json()
        self.assertFalse(r["correct"]); self.assertEqual(r["answer_index"], ans[1]["answer_index"])
        r = s1.post(f"/s/games/quiz/{rid}/check", json={"i": 1, "pick": ans[1]["answer_index"]}).get_json()
        self.assertFalse(r["correct"]); self.assertEqual(r["score"], 1)
        self.assertEqual(s2.post(f"/s/games/quiz/{rid}/check", json={"i": 2, "pick": 0}).status_code, 404)   # 남의 판
        self.assertEqual(s1.post(f"/s/games/quiz/{rid}/check", json={"i": 9, "pick": 0}).status_code, 400)
        for i in range(2, len(ans)):
            s1.post(f"/s/games/quiz/{rid}/check", json={"i": i, "pick": ans[i]["answer_index"]})
        # 마지막 결과는 서버에 남은 답으로 (화면이 보낸 답을 믿지 않음)
        res = s1.post(f"/s/games/quiz/{rid}/submit", json={"answers": [a["answer_index"] for a in ans]}).get_json()
        self.assertEqual(res["score"], len(ans) - 1)

    def test_vocab_daily_20_and_review(self):
        import json as _json
        import vocab
        _, s1, s2 = self._students()
        self.assertGreaterEqual(len(vocab.WORDS), 600)
        page = s1.get("/s/games/vocab").data.decode()
        self.assertIn("Day 1", page)
        with self.app.app_context():
            day = query("SELECT * FROM vocab_days", one=True)
        words = _json.loads(day["words"])
        self.assertEqual(len(words), 20)
        self.assertIn(words[0], page)
        self.assertEqual(s1.get("/s/games/vocab").data.decode().count('class="voca-card"'), 20)   # 하루 동안 같은 20개
        start = s1.post("/s/games/vocab/start", json={}).get_json()
        self.assertEqual(len(start["questions"]), 20)
        self.assertNotIn("answer_index", str(start))
        rid = start["round_id"]
        with self.app.app_context():
            ans = _json.loads(query("SELECT answer FROM game_rounds WHERE id=?", (rid,), one=True)["answer"])
        for i, a in enumerate(ans):                       # 앞의 3개만 틀리게
            pick = a["answer_index"] if i >= 3 else (a["answer_index"] + 1) % 4
            r = s1.post(f"/s/games/vocab/{rid}/check", json={"i": i, "pick": pick}).get_json()
            self.assertEqual(r["correct"], i >= 3)
        res = s1.post(f"/s/games/vocab/{rid}/submit", json={}).get_json()
        self.assertEqual(res["score"], 17)
        with self.app.app_context():
            self.assertEqual(query("SELECT COUNT(*) n FROM vocab_marks", one=True)["n"], 20)
            self.assertEqual(query("SELECT score FROM vocab_days", one=True)["score"], 17)
        hub = s1.get("/s/games/").data.decode()
        self.assertIn("3<small>단어</small>", hub)               # 복습 3개
        # 복습에서 맞히면 빠진다
        rv = s1.post("/s/games/vocab/review/start", json={}).get_json()
        self.assertEqual(len(rv["questions"]), 3)
        with self.app.app_context():
            ans = _json.loads(query("SELECT answer FROM game_rounds WHERE id=?", (rv["round_id"],), one=True)["answer"])
        for i, a in enumerate(ans):
            s1.post(f"/s/games/vocab/review/{rv['round_id']}/check", json={"i": i, "pick": a["answer_index"]})
        s1.post(f"/s/games/vocab/review/{rv['round_id']}/submit", json={})
        self.assertEqual(s1.post("/s/games/vocab/review/start", json={}).status_code, 400)
        self.assertIn("0<small>단어</small>", s1.get("/s/games/").data.decode())
        # 다른 학생은 자기 Day 1 (같은 순서로 시작)
        self.assertIn("Day 1", s2.get("/s/games/vocab").data.decode())
        self.assertEqual(s2.post(f"/s/games/vocab/{rid}/check", json={"i": 0, "pick": 0}).status_code, 404)

    def test_quiz_hub_shows_categories(self):
        _, s1, _ = self._students()
        hub = s1.get("/s/games/").data.decode()
        for t in ("영단어", "오늘의 20단어", "통합과학", "역학 시스템", "샤가프 법칙", "염기 짝 맞추기"):
            self.assertIn(t, hub)
        self.assertIn('value="mechanics" selected', s1.get("/s/games/quiz?topic=mechanics").data.decode())

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

    def test_assistant_sees_more_but_cannot_manage(self):
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
        self.assertIn("안녕하세요 :) 김조교 조교입니다.", page)                      # 조교 답변 기본 인사말
        self.assertIn("혹여나 더 궁금하신 게 있으시다면 편하게 질문 남겨주세요!", page)
        self.assertNotIn("조교입니다.", self.c.get(f"/t/questions/{qid}").data.decode())   # 선생님 칸은 비어 있음
        ta.post(f"/t/questions/{qid}", data={"body": "조교가 설명할게요"})
        # 학생에게는 '[조교] 김조교 답변' 으로 보임 (본명 앞에 캡션)
        student_view = s1.get(f"/s/questions/{qid}").data.decode()
        self.assertIn('<span class="cap">조교</span> 김조교 답변', student_view)
        # 조교도 볼 수 있는 화면 (보기 위주로 열어 둠)
        for url in ["/t/", "/t/students", f"/t/students/{sid}", "/t/classes", f"/t/classes/{cid}",
                    "/t/timetable", "/t/tasks", "/t/rooms", "/t/books", f"/t/students/{sid}/report"]:
            self.assertEqual(ta.get(url).status_code, 200, url)
        # 계정·기록·삭제 같은 관리 일은 선생님만
        for url in ["/t/audit", "/t/staff", "/t/signups"]:
            self.assertEqual(ta.get(url).status_code, 403, url)
        r = ta.post(f"/t/classes/{cid}/accounts", headers={"Referer": f"http://localhost/t/classes/{cid}"})
        self.assertEqual(r.status_code, 302)                                  # 오류 화면 대신 안내하고 돌려보냄
        self.assertIn("선생님만", ta.get(f"/t/classes/{cid}").data.decode())
        ta.post("/t/staff", data={"display_name": "x", "username": "ta_x"})
        ta.post(f"/t/students/{sid}/delete")
        ta.post("/t/classes", data={"name": "몰래 만든 반"})
        with self.app.app_context():
            self.assertEqual(query("SELECT COUNT(*) n FROM users WHERE username='ta_x'", one=True)["n"], 0)
            self.assertIsNotNone(query("SELECT id FROM students WHERE id=?", (sid,), one=True))
            self.assertIsNone(query("SELECT id FROM classes WHERE name='몰래 만든 반'", one=True))
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

    def test_signup_requires_google_when_enabled(self):
        cid = self.setup_class_with_students()
        with self.app.app_context():
            code = query("SELECT join_code FROM classes WHERE id=?", (cid,), one=True)["join_code"]
        ident = {"sub": "g-777", "email": "jimin@example.com", "email_verified": True}
        with mock.patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "cid", "GOOGLE_CLIENT_SECRET": "sec"}), \
                mock.patch("google_auth.fetch_identity", return_value=ident):
            anon = self.app.test_client()
            # Google 확인 전에는 가입서 대신 'Google 계정으로 시작하기'만 보이고, 바로 보내도 거부
            page = anon.get("/signup").data.decode()
            self.assertIn("Google 계정으로 시작하기", page)
            self.assertNotIn('name="student_no"', page)
            self._signup(anon, code)
            with self.app.app_context():
                self.assertEqual(query("SELECT COUNT(*) n FROM signup_requests", one=True)["n"], 0)
            # Google 확인 → 이메일이 보이는 가입서 → 신청
            r = anon.get("/auth/google/start?mode=signup")
            state = re.search(r"state=([^&]+)", r.headers["Location"]).group(1)
            self.assertTrue(anon.get(f"/auth/google/callback?state={state}&code=x").headers["Location"].endswith("/signup"))
            self.assertIn("jimin@example.com", anon.get("/signup").data.decode())
            self.assertIn("가입 신청 완료", self._signup(anon, code).data.decode())
            # 승인 전 Google 로그인 → 대기 안내
            r = anon.get("/auth/google/start?mode=login")
            state = re.search(r"state=([^&]+)", r.headers["Location"]).group(1)
            self.assertIn("승인 대기", anon.get(f"/auth/google/callback?state={state}&code=x", follow_redirects=True).data.decode())
            # 같은 Google 계정으로 또 가입 시도 → 막힘
            other = self.app.test_client()
            r = other.get("/auth/google/start?mode=signup")
            state = re.search(r"state=([^&]+)", r.headers["Location"]).group(1)
            self.assertIn("이미 가입 신청", other.get(f"/auth/google/callback?state={state}&code=x", follow_redirects=True).data.decode())
            # 선생님 화면에 이메일이 보이고, 승인하면 Google 로 바로 로그인
            self.assertIn("jimin@example.com", self.c.get("/t/signups").data.decode())
            with self.app.app_context():
                rid = query("SELECT id FROM signup_requests", one=True)["id"]
            self.c.post("/t/signups", data={"action": "approve", "ids": [str(rid)]})
            with self.app.app_context():
                u = query("SELECT * FROM users WHERE username='S100'", one=True)
                self.assertEqual((u["google_sub"], u["google_email"]), ("g-777", "jimin@example.com"))
            fresh = self.app.test_client()
            r = fresh.get("/auth/google/start?mode=login")
            state = re.search(r"state=([^&]+)", r.headers["Location"]).group(1)
            r = fresh.get(f"/auth/google/callback?state={state}&code=x")
            self.assertTrue(r.headers["Location"].endswith("/s/"))

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
