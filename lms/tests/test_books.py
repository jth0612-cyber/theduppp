"""교재 분석실·Google 로그인·한 기기 로그인 점검: python -m unittest discover tests"""
import json
import os
import re
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import analysis  # noqa: E402
from app import create_app  # noqa: E402
from db import execute, query  # noqa: E402
from security import hash_password  # noqa: E402

TEACHER_PW = "Teach3r!pass"
STU_PW = "Student!2026"
KEY = "14352534112431552143"  # 20문항


class AnalysisMathTest(unittest.TestCase):
    def test_code_normalize_and_format(self):
        self.assertEqual(analysis.normalize_code("abcd-efgh-jkmn"), "ABCDEFGHJKMN")
        self.assertIsNone(analysis.normalize_code("ABCD-EFGH-JKM"))     # 11자리
        self.assertEqual(analysis.format_code("ABCDEFGHJKMN"), "ABCD-EFGH-JKMN")

    def test_points_must_sum_to_full(self):
        with self.assertRaises(ValueError):
            analysis.parse_points("", 20, 50)                           # 2.5점은 직접 입력해야 함
        self.assertEqual(analysis.parse_points("", 20, 40), [2] * 20)
        pts = analysis.parse_points(",".join(["2"] * 10 + ["3"] * 10), 20, 50)
        self.assertEqual(sum(pts), 50)
        with self.assertRaises(ValueError):
            analysis.parse_points(",".join(["2"] * 20), 20, 50)

    def test_grade_cuts_and_percentile(self):
        scores = list(range(1, 101))                                    # 1~100점 100명
        cuts = analysis.grade_cuts(scores)
        self.assertEqual([c["raw"] for c in cuts], [97, 90, 78, 61, 41, 24, 12, 5])
        self.assertEqual(analysis.grade_for(97, cuts), 1)
        self.assertEqual(analysis.grade_for(96, cuts), 2)
        self.assertEqual(analysis.grade_for(1, cuts), 9)
        self.assertEqual(cuts[0]["pct"], 96)
        self.assertEqual(analysis.grade_cuts(scores[:5]), [])           # 10명 미만이면 등급컷 없음

    def test_item_stats(self):
        key = [1, 2, 3]
        stats = analysis.item_stats(["123", "113", "223", "121"], key)
        self.assertEqual([it["wrong_pct"] for it in stats], [25, 25, 25])
        self.assertEqual(stats[1]["choices"], [25, 75, 0, 0, 0])
        self.assertTrue(stats[1]["top"])


class BooksTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True, "WTF_CSRF_ENABLED": False, "ANALYSIS_TTL": 0,
            "DATABASE": os.path.join(self.tmp.name, "t.sqlite3"),
            "UPLOAD_DIR": os.path.join(self.tmp.name, "up"),
        })
        os.makedirs(self.app.config["UPLOAD_DIR"], exist_ok=True)
        with self.app.app_context():
            from db import init_db
            init_db(self.app.config["DATABASE"])
            execute("INSERT INTO users (role, username, password_hash) VALUES ('teacher', 'teacher', ?)",
                    (hash_password(TEACHER_PW),))
            cid = execute("INSERT INTO classes (name, join_code) VALUES ('A반', 'AAAAAAAA')")
            for i in range(12):
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
        r = c.post("/login", data={"username": f"S{i:03d}", "password": STU_PW})
        self.assertEqual(r.status_code, 302)
        return c

    def make_book(self, expires="2099-12-31"):
        r = self.t.post("/t/books", data={"title": "파이널 모의고사", "subject": "통합과학", "expires_on": expires,
                                          "is_free": "1", "notice": "배포 코드로 이용하세요"})
        bid = int(r.headers["Location"].rsplit("/", 1)[-1])
        r = self.t.post(f"/t/books/{bid}/mocks", data={"round_no": "1", "n_items": "20", "full_score": "50",
                                                       "answer_key": "14352 53411 24315 52143",
                                                       "points": ",".join(["2"] * 10 + ["3"] * 10)})
        self.assertEqual(r.status_code, 302)
        with self.app.app_context():
            mid = query("SELECT id FROM mocks WHERE book_id = ?", (bid,), one=True)["id"]
        return bid, mid

    def shared_code(self, bid):
        self.t.post(f"/t/books/{bid}/codes", data={"kind": "shared"})
        with self.app.app_context():
            return query("SELECT code FROM book_codes WHERE book_id = ? AND max_uses IS NULL", (bid,), one=True)["code"]

    def test_register_code_and_score_on_server(self):
        bid, mid = self.make_book()
        s = self.student(0)
        # 등록 전에는 분석실에 회차가 없다
        self.assertIn("아직 서가에 등록한 교재가 없어요", s.get("/s/analysis").data.decode())
        self.assertEqual(s.post(f"/s/analysis/{mid}/submit", data={"mode": "answers", "quick": KEY}).status_code, 404)
        code = self.shared_code(bid)
        r = s.post("/s/books/register", data={"code": analysis.format_code(code).lower()})
        self.assertIn("서가에 추가했어요", r.data.decode())
        page = s.get(f"/s/analysis?mock={mid}").data.decode()
        self.assertIn("답안지", page)
        self.assertNotIn(KEY, page)                                     # 정답은 화면에 나가지 않음
        # 부분 입력은 채점하지 않음
        s.post(f"/s/analysis/{mid}/submit", data={"mode": "answers", "quick": "14352"})
        with self.app.app_context():
            e = query("SELECT * FROM mock_entries WHERE mock_id = ?", (mid,), one=True)
            self.assertIsNone(e["score"])
        # 마지막 두 문항(3점짜리)을 틀리면 44점
        wrong = KEY[:18] + ("2" if KEY[18] != "2" else "3") + ("2" if KEY[19] != "2" else "3")
        s.post(f"/s/analysis/{mid}/submit", data={"mode": "answers", "quick": " ".join(wrong)})
        with self.app.app_context():
            self.assertEqual(query("SELECT score FROM mock_entries WHERE mock_id = ?", (mid,), one=True)["score"], 44)
        self.assertIn("44", s.get(f"/s/analysis?mock={mid}").data.decode())

    def test_single_use_code_and_expired_book(self):
        bid, _ = self.make_book()
        r = self.t.post(f"/t/books/{bid}/codes", data={"kind": "single", "count": "2"})
        codes = re.findall(r"[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}", r.data.decode("utf-8-sig"))
        self.assertEqual(len(codes), 2)
        a, b = self.student(0), self.student(1)
        self.assertIn("서가에 추가했어요", a.post("/s/books/register", data={"code": codes[0]}).data.decode())
        self.assertIn("이미 다른 계정에서 쓴 코드", b.post("/s/books/register", data={"code": codes[0]}).data.decode())
        bid2, _ = self.make_book(expires="2000-01-01")
        old = self.shared_code(bid2)
        self.assertIn("이용 기간이 지난", b.post("/s/books/register", data={"code": old}).data.decode())

    def test_code_guessing_is_limited(self):
        s = self.student(0)
        for _ in range(10):
            s.post("/s/books/register", data={"code": "ZZZZ-ZZZZ-ZZZZ"})
        self.assertEqual(s.post("/s/books/register", data={"code": "ZZZZ-ZZZZ-ZZZZ"}).status_code, 429)

    def test_grade_cuts_and_item_stats_appear(self):
        bid, mid = self.make_book()
        code = self.shared_code(bid)
        for i in range(12):
            s = self.student(i)
            s.post("/s/books/register", data={"code": code})
            ans = list(KEY)
            for j in range(i % 6):                                      # 학생마다 0~5문항 틀림
                ans[19 - j] = "5" if ans[19 - j] != "5" else "4"
            s.post(f"/s/analysis/{mid}/submit", data={"mode": "answers", "quick": "".join(ans)})
        page = s.get(f"/s/analysis?mock={mid}&q=20").data.decode()
        self.assertIn("표준점수", page)
        self.assertIn("문항 지도", page)
        self.assertIn("20번 선지별 응답", page)
        self.assertIn("등급", page)
        teacher = self.t.get(f"/t/mocks/{mid}").data.decode()
        self.assertIn("채점 12명", teacher)
        # 다른 학생의 답안은 볼 수 없고, 남의 회차에 제출할 수 없다
        self.assertEqual(self.student(0).get("/t/books").status_code, 403)

    def test_bubble_sheet_submission(self):
        bid, mid = self.make_book()
        s = self.student(0)
        s.post("/s/books/register", data={"code": self.shared_code(bid)})
        marks = {f"a{i + 1}": KEY[i] for i in range(20)}
        marks.pop("a7")                                                  # 7번 비움 → 채점 안 함
        s.post(f"/s/analysis/{mid}/submit", data={"mode": "answers", **marks})
        with self.app.app_context():
            e = query("SELECT * FROM mock_entries WHERE mock_id = ?", (mid,), one=True)
            self.assertEqual(e["answers"][6], "0")
            self.assertIsNone(e["score"])
        marks["a7"] = KEY[6]
        s.post(f"/s/analysis/{mid}/submit", data={"mode": "answers", **marks})
        with self.app.app_context():
            self.assertEqual(query("SELECT score FROM mock_entries WHERE mock_id = ?", (mid,), one=True)["score"], 50)
        page = s.get(f"/s/analysis?mock={mid}").data.decode()
        self.assertIn('name="a7" value="{}" checked'.format(KEY[6]), page)

    def test_score_only_mode(self):
        bid, mid = self.make_book()
        s = self.student(0)
        s.post("/s/books/register", data={"code": self.shared_code(bid)})
        s.post(f"/s/analysis/{mid}/submit", data={"mode": "score", "score": "60"})   # 만점 초과
        s.post(f"/s/analysis/{mid}/submit", data={"mode": "score", "score": "41"})
        with self.app.app_context():
            e = query("SELECT * FROM mock_entries WHERE mock_id = ?", (mid,), one=True)
            self.assertEqual((e["mode"], e["score"]), ("score", 41))

    def test_student_one_device(self):
        first = self.student(0)
        self.assertEqual(first.get("/s/").status_code, 200)
        self.student(0)                                                 # 다른 기기에서 로그인
        r = first.get("/s/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("다른 기기", first.get("/login").data.decode())
        # 강사는 여러 기기 허용
        other = self.app.test_client()
        other.post("/login", data={"username": "teacher", "password": TEACHER_PW})
        self.assertEqual(self.t.get("/t/").status_code, 200)

    def test_google_link_and_login(self):
        with mock.patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "cid", "GOOGLE_CLIENT_SECRET": "sec"}), \
                mock.patch("google_auth.fetch_identity",
                           return_value={"sub": "g-123", "email": "s0@example.com", "email_verified": True}):
            anon = self.app.test_client()
            # 연결 전에는 Google 로 로그인할 수 없다
            r = anon.get("/auth/google/start?mode=login")
            self.assertIn("accounts.google.com", r.headers["Location"])
            state = re.search(r"state=([^&]+)", r.headers["Location"]).group(1)
            r = anon.get(f"/auth/google/callback?state={state}&code=x", follow_redirects=True)
            self.assertIn("연결된 계정이 없어요", r.data.decode())
            # 학생이 로그인한 뒤 연결
            s = self.student(0)
            r = s.get("/auth/google/start?mode=link")
            state = re.search(r"state=([^&]+)", r.headers["Location"]).group(1)
            self.assertIn("연결했어요", s.get(f"/auth/google/callback?state={state}&code=x",
                                             follow_redirects=True).data.decode())
            # 이제 Google 로 로그인
            anon = self.app.test_client()
            r = anon.get("/auth/google/start?mode=login")
            state = re.search(r"state=([^&]+)", r.headers["Location"]).group(1)
            r = anon.get(f"/auth/google/callback?state={state}&code=x")
            self.assertTrue(r.headers["Location"].endswith("/s/"))
            # state 가 다르면 거부
            r = anon.get("/auth/google/callback?state=wrong&code=x", follow_redirects=True)
            self.assertIn("다시 시도", r.data.decode())

    def test_google_hidden_when_not_configured(self):
        os.environ.pop("GOOGLE_CLIENT_ID", None)
        self.assertNotIn("Google", self.app.test_client().get("/login").data.decode())
        self.assertEqual(self.app.test_client().get("/auth/google/start").status_code, 404)

    def test_notice_pin_search_views_likes_and_public_home(self):
        with self.app.app_context():
            cid = query("SELECT id FROM classes", one=True)["id"]
        self.t.post(f"/t/classes/{cid}/notices", data={"tag": "공지", "title": "시즌2 커리큘럼", "body": "내용", "pinned": "1"})
        self.t.post(f"/t/classes/{cid}/notices", data={"tag": "정오", "title": "7주차 정오", "body": "3번 정답 ②"})
        s = self.student(0)
        page = s.get("/s/notices").data.decode()
        self.assertLess(page.index("시즌2 커리큘럼"), page.index("7주차 정오"))      # 고정 공지가 위
        self.assertIn("고정 공지", page)
        found = s.get("/s/notices?q=정답").data.decode()
        self.assertIn("7주차 정오", found)
        self.assertNotIn("시즌2 커리큘럼", found)
        self.assertNotIn("시즌2", s.get("/s/notices?q=%25").data.decode())          # % 는 글자 그대로 검색
        with self.app.app_context():
            nid = query("SELECT id FROM notices WHERE title = '시즌2 커리큘럼'", one=True)["id"]
        s.get(f"/s/notices/{nid}")
        s.get(f"/s/notices/{nid}")                                                  # 같은 로그인은 한 번만
        self.student(1).get(f"/s/notices/{nid}")
        s2 = self.student(1)
        s2.get(f"/s/notices/{nid}")
        s2.post(f"/s/notices/{nid}/like")
        with self.app.app_context():
            self.assertEqual(query("SELECT views FROM notices WHERE id = ?", (nid,), one=True)["views"], 3)
            self.assertEqual(query("SELECT COUNT(*) AS c FROM notice_likes", one=True)["c"], 1)
        s2.post(f"/s/notices/{nid}/like")                                           # 다시 누르면 취소
        with self.app.app_context():
            self.assertEqual(query("SELECT COUNT(*) AS c FROM notice_likes", one=True)["c"], 0)
        # 로그인 전 첫 화면은 공개, 공지는 로그인 필요
        anon = self.app.test_client()
        home = anon.get("/").data.decode()
        self.assertIn("질문 게시판", home)
        self.assertNotIn("온라인", home)
        self.assertEqual(anon.get("/s/notices").status_code, 302)


if __name__ == "__main__":
    unittest.main()
