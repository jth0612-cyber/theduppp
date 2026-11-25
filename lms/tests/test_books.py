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
    def test_points_must_sum_to_full(self):
        with self.assertRaises(ValueError):
            analysis.parse_points("", 20, 50)                           # 2.5점은 직접 입력해야 함
        self.assertEqual(analysis.parse_points("", 20, 40), [2] * 20)
        pts = analysis.parse_points(",".join(["2"] * 10 + ["3"] * 10), 20, 50)
        self.assertEqual(sum(pts), 50)
        with self.assertRaises(ValueError):
            analysis.parse_points(",".join(["2"] * 20), 20, 50)

    def test_points_from_levels_25_items(self):
        pts = analysis.points_from_levels("8, 12 17 20,25", "1-3, 5 9", 25, 50)
        self.assertEqual(len(pts), 25)
        self.assertEqual(sum(pts), 50)
        self.assertEqual((pts[7], pts[0], pts[3]), (2.5, 1.5, 2))
        with self.assertRaises(ValueError):                             # 개수가 안 맞으면 합이 50이 아님
            analysis.points_from_levels("8, 12", "1", 25, 50)
        with self.assertRaises(ValueError):                             # 같은 문항이 두 칸에
            analysis.points_from_levels("3", "3", 25, 50)
        with self.assertRaises(ValueError):                             # 없는 문항
            analysis.points_from_levels("26", "1", 25, 50)

    def test_half_point_bands(self):
        self.assertEqual(analysis.score_step([2, 2.5, 1.5]), 0.5)
        self.assertEqual(analysis.score_step([2, 3]), 1)
        dist = analysis.distribution([4.5, 5, 49.5, 50], 50, step=0.5)
        self.assertEqual(dist[0]["label"], "0–4.5")
        self.assertEqual(dist[1]["label"], "5–9.5")
        self.assertEqual(dist[-1]["label"], "45–50")
        self.assertEqual((dist[0]["count"], dist[1]["count"], dist[-1]["count"]), (1, 1, 2))
        self.assertEqual(analysis.bucket_label(47.5, 50, step=0.5), "45–50")
        self.assertEqual(analysis.distribution([0], 50)[0]["label"], "0–4")      # 정수 배점은 그대로

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

    def upload(self, mid, rows, n=20, name="omr.xlsx", header=None):
        """OMR 결과 엑셀을 강사 계정으로 올린다. rows: [(학생코드, 이름, 반, 답안 문자열)]"""
        import io as _io
        from openpyxl import Workbook
        wb = Workbook(); ws = wb.active
        ws.append(header or (["학생코드", "이름", "반"] + list(range(1, n + 1))))
        for code, nm, cls, ans in rows:
            ws.append([code, nm, cls] + [int(ch) if ch in "12345" else None for ch in ans])
        buf = _io.BytesIO(); wb.save(buf); buf.seek(0)
        return self.t.post(f"/t/mocks/{mid}/omr", data={"file": (buf, name)}, content_type="multipart/form-data",
                           follow_redirects=True)

    def test_no_key_item_is_wrong_for_everyone(self):
        """정답 '-' 는 전원 오답, 배점 0: 점수에 영향 없이 틀린 문항으로만 센다."""
        import io as _io
        from openpyxl import Workbook
        with self.app.app_context():
            mid = query("""SELECT m.id FROM mocks m JOIN books b ON b.id = m.book_id
                           WHERE b.title = '복습 테스트' AND b.is_practice = 0 AND m.round_no = 1""", one=True)["id"]
        wb = Workbook(); ws = wb.active
        ws.append(["학생코드", "이름", "반", 1, 2, 3])
        ws.append(["정답", "", "", 2, "-", 4])
        ws.append(["배점", "", "", 2, 0, 3])
        ws.append(["S000", "학생0", "A반", 2, 3, 4])
        buf = _io.BytesIO(); wb.save(buf); buf.seek(0)
        self.t.post(f"/t/mocks/{mid}/omr", data={"file": (buf, "o.xlsx")}, content_type="multipart/form-data")
        with self.app.app_context():
            self.assertEqual(query("SELECT full_score FROM mocks WHERE id = ?", (mid,), one=True)["full_score"], 5)
            self.assertEqual(query("SELECT score FROM exam_results WHERE mock_id = ?", (mid,), one=True)["score"], 5)
        page = self.student(0).get(f"/s/analysis?mock={mid}").data.decode()
        self.assertIn("정답 없음", page)

    def test_25_items_with_mixed_points(self):
        r = self.t.post("/t/books", data={"title": "통합과학 실전", "subject": "통합과학", "expires_on": "2099-12-31"})
        bid = int(r.headers["Location"].rsplit("/", 1)[-1])
        key = "1435253411243155214331524"
        r = self.t.post(f"/t/books/{bid}/mocks", data={"round_no": "1", "n_items": "25", "full_score": "50",
                                                       "answer_key": key, "high_items": "21-25", "low_items": "1-5"})
        self.assertEqual(r.status_code, 302)
        with self.app.app_context():
            m = query("SELECT * FROM mocks WHERE book_id = ?", (bid,), one=True)
        self.assertEqual(sum(json.loads(m["points"])), 50)
        # 1번(1.5점)과 25번(2.5점)을 틀리면 46점
        ans = ("2" if key[0] != "2" else "3") + key[1:24] + ("2" if key[24] != "2" else "3")
        self.upload(m["id"], [("S000", "학생0", "A반", ans)], n=25)
        with self.app.app_context():
            self.assertEqual(query("SELECT score FROM mock_entries WHERE mock_id = ?", (m["id"],), one=True)["score"], 46)
        page = self.student(0).get(f"/s/analysis?mock={m['id']}").data.decode()
        self.assertIn("놓친 점수", page)
        self.assertIn("4점", page)
        self.assertNotIn("점수대 분포", page)                          # 학생에게는 석차를 짐작할 분포·백분위 비공개
        self.assertNotIn("백분위", page)

    def test_omr_upload_shows_to_students(self):
        """강사가 OMR 엑셀을 올리면 그 학생 화면에 바로 채점 결과가 보인다. 학생은 답을 적을 수 없다."""
        bid, mid = self.make_book()
        s0, s1 = self.student(0), self.student(1)
        self.assertIn("아직 올라온 결과가 없어요", s0.get("/s/analysis").data.decode())
        self.assertEqual(s0.post(f"/s/analysis/{mid}/submit", data={"mode": "answers", "quick": KEY}).status_code, 404)
        # 마지막 두 문항(3점짜리) 오답 → 44점, 7번 무응답(2점) → 42점
        wrong = KEY[:18] + ("2" if KEY[18] != "2" else "3") + ("2" if KEY[19] != "2" else "3")
        blank = wrong[:6] + "0" + wrong[7:]
        r = self.upload(mid, [("S000", "학생0", "A반", wrong), ("S001", "", "", blank), ("Z999", "없는학생", "", KEY)])
        page = r.data.decode()
        self.assertIn("2명 반영", page)
        self.assertIn("번호가 학생DB에 없습니다", page)
        with self.app.app_context():
            sc = {r["username"]: r["score"] for r in query(
                "SELECT u.username, e.score FROM mock_entries e JOIN users u ON u.id = e.user_id WHERE e.mock_id = ?", (mid,))}
        self.assertEqual(sc, {"S000": 44, "S001": 42})
        page = s0.get(f"/s/analysis?mock={mid}").data.decode()
        self.assertIn("내 답안", page); self.assertIn("44", page)
        self.assertNotIn('name="quick"', page); self.assertNotIn("<input type=\"radio\"", page)
        self.assertIn("7번 2점, 내 답 무응답", s1.get(f"/s/analysis?mock={mid}").data.decode())
        # 결과가 없는 학생에게는 회차가 보이지 않는다
        self.assertEqual(self.student(2).get(f"/s/analysis?mock={mid}").status_code, 200)   # 결과 없는 학생: 빈 화면
        self.assertNotIn("내 답안", self.student(2).get("/s/analysis").data.decode())
        # 다시 올리면 새 내용으로 바뀐다
        self.upload(mid, [("S000", "학생0", "A반", KEY)])
        with self.app.app_context():
            self.assertEqual(query("SELECT score FROM mock_entries e JOIN users u ON u.id = e.user_id WHERE u.username = 'S000'",
                                   one=True)["score"], 50)
        # 빈 양식은 재원생 명단이 채워져 나온다
        form = self.t.get(f"/t/mocks/{mid}/omr-form.xlsx")
        self.assertEqual(form.status_code, 200)
        from openpyxl import load_workbook
        import io as _io
        ws = load_workbook(_io.BytesIO(form.data)).active
        self.assertEqual([c.value for c in ws[1]][:5], ["이름", "수험번호", "학생코드", "반", 1])
        self.assertEqual(ws.max_row, 15)                                   # 머리글 + 정답 줄 + 배점 줄 + 학생 12명
        self.assertEqual(load_workbook(_io.BytesIO(form.data)).sheetnames, ["OMR", "문항정보", "작성 예시"])
        # 빈 양식 그대로(문항 칸이 빈 학생) 올리면 건너뛴다
        r = self.t.post(f"/t/mocks/{mid}/omr", data={"file": (_io.BytesIO(form.data), "omr.xlsx")},
                        content_type="multipart/form-data", follow_redirects=True)
        self.assertIn("반영된 학생이 없어요", r.data.decode())             # 정답 줄을 비워 두면 학생 줄은 모두 미응시로 건너뜀
        # 조교도 올릴 수 있고, 학생은 올릴 수 없다
        with self.app.app_context():
            execute("INSERT INTO users (role, username, password_hash, display_name) VALUES ('assistant', 'ta', ?, '조교')",
                    (hash_password(TEACHER_PW),))
        ta = self.app.test_client(); ta.post("/login", data={"username": "ta", "password": TEACHER_PW})
        csv = "학생코드,답안\nS005,%s\n" % KEY
        r = ta.post(f"/t/mocks/{mid}/omr", data={"file": (_io.BytesIO(csv.encode()), "a.csv")},
                    content_type="multipart/form-data", follow_redirects=True)
        self.assertIn("1명 반영", r.data.decode())
        self.assertNotEqual(s0.post(f"/t/mocks/{mid}/omr").status_code, 302)

    def test_omr_csv_name_and_answer_column(self):
        """CSV, 학생코드 없이 이름으로, '답안' 한 칸에 이어 적은 형식도 받는다."""
        bid, mid = self.make_book()
        import io as _io
        csv = "이름,답안\n학생3,%s\n학생4,%s\n" % (" ".join(KEY[i:i + 5] for i in range(0, 20, 5)), KEY[:19])
        r = self.t.post(f"/t/mocks/{mid}/omr", data={"file": (_io.BytesIO(csv.encode("utf-8-sig")), "a.csv")},
                        content_type="multipart/form-data", follow_redirects=True)
        self.assertIn("2명 반영", r.data.decode())
        with self.app.app_context():
            sc = sorted(r["score"] for r in query("SELECT score FROM mock_entries WHERE mock_id = ?", (mid,)))
        self.assertEqual(sc, [47, 50])                                  # 20번(3점) 무응답
        bad = self.t.post(f"/t/mocks/{mid}/omr", data={"file": (_io.BytesIO(b"x"), "a.txt")},
                          content_type="multipart/form-data", follow_redirects=True)
        self.assertIn("엑셀(.xlsx) 또는 CSV", bad.data.decode())

    def test_grade_cuts_and_item_stats_appear(self):
        bid, mid = self.make_book()
        rows = []
        for i in range(12):
            ans = list(KEY)
            for j in range(i % 6):                                      # 학생마다 0~5문항 틀림
                ans[19 - j] = "5" if ans[19 - j] != "5" else "4"
            rows.append((f"S{i:03d}", f"학생{i}", "A반", "".join(ans)))
        self.upload(mid, rows)
        page = self.student(11).get(f"/s/analysis?mock={mid}&q=20").data.decode()
        self.assertIn("표준점수", page)
        self.assertIn("문항 지도", page)
        self.assertIn("20번 선지별 응답", page)
        self.assertIn("등급", page)
        teacher = self.t.get(f"/t/mocks/{mid}").data.decode()
        self.assertIn("응시 12명", teacher)
        self.assertEqual(self.student(0).get("/t/books").status_code, 403)

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
            self.assertIn("연결된 계정이 없습니다", r.data.decode())
            # 학생이 로그인한 뒤 연결
            s = self.student(0)
            r = s.get("/auth/google/start?mode=link")
            state = re.search(r"state=([^&]+)", r.headers["Location"]).group(1)
            self.assertIn("연결했습니다", s.get(f"/auth/google/callback?state={state}&code=x",
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
        self.assertIn('<span class="badge gray">고정</span>', page)
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
