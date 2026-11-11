"""조교 시스템(구글 시트) → 웹 연동 점검."""
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
SCORE_HEAD = ["학생코드", "시즌", "주차", "유형", "시험명", "날짜", "점수", "만점", "반평균", "평균대비", "전체평균", "전체평균대비", "틀린문항", "이름"]
WRONG_HEAD = ["학생코드", "시험명", "날짜", "문항번호", "내답", "정답", "반오답률", "단원", "오답유형", "분석", "다시풀기", "판단근거", "헷갈린보기", "같은답비율"]


class LinkTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False,
                               "DATABASE": os.path.join(self.tmp.name, "t.sqlite3"), "UPLOAD_DIR": os.path.join(self.tmp.name, "up")})
        os.makedirs(self.app.config["UPLOAD_DIR"], exist_ok=True)
        with self.app.app_context():
            from db import init_db
            init_db(self.app.config["DATABASE"])
            execute("INSERT INTO users (role, username, password_hash) VALUES ('teacher', 'teacher', ?)", (hash_password(PW),))
            self.cid = execute("INSERT INTO classes (name) VALUES ('시대인재 대구 MDS 점심반')")
        from views import auth
        auth._ip_attempts.clear()
        self.t = self.app.test_client()
        self.t.post("/login", data={"username": "teacher", "password": PW})
        r = self.t.post("/t/link/token")
        import re
        m = re.search(r'value="(thl_[^"]+)"', r.data.decode())
        self.token = m.group(1) if m else None
        self.assertTrue(self.token and self.token.startswith("thl_"))

    def tearDown(self):
        with self.app.app_context():
            from db import close_db
            close_db()
        self.tmp.cleanup()

    def push(self, tables, token=None):
        return self.app.test_client().post("/api/sync", json={"tables": tables},
                                           headers={"Authorization": "Bearer " + (token or self.token)})

    def tables(self):
        return {
            "🌐앱_성적": [SCORE_HEAD,
                         ["K7QM-3XPA", "S1", "6", "주간테스트", "S1 6주차 주간테스트", "2026-11-04", "44", "50", "36.2", "", "", "", "16,22", "김민수"],
                         ["ABCD-EFGH", "S1", "6", "주간테스트", "S1 6주차 주간테스트", "2026-11-04", "30", "50", "36.2", "-6.2", "", "", "1,2,3", "이영희"]],
            "🌐앱_오답노트": [WRONG_HEAD,
                           ["K7QM-3XPA", "S1 6주차 주간테스트", "2026-11-04", "16", "3", "5", "42.5%", "물질과 규칙성", "자료 해석",
                            "16번은 자료 해석 오류로, 보기 ㄴ에서 그래프 축을 거꾸로 읽은 경우입니다.", "", "보기 차이 근거", "ㄴ", "31%"],
                           ["K7QM-3XPA", "S1 6주차 주간테스트", "2026-11-04", "22", "2", "4", "64", "환경과 에너지", "", "", "", "정보 없음", "", ""],
                           ["K7QM-3XPA", "S1 6주차 주간테스트", "2026-11-04", "9", "1", "2", "10", "과학의 기초", "개념 부족", "x", "", "정정됨", "", ""]],
            "🌐앱_출결": [["학생코드", "날짜", "출결", "도착시각"], ["K7QM-3XPA", "2026-11-04", "지각", "14:07"], ["K7QM-3XPA", "2026-11-06", "출석", "13:52"]],
            "코드": [["학생코드", "반", "상태"], ["K7QM-3XPA", "시대인재 대구 MDS 점심반", "재원"], ["ABCD-EFGH", "시대인재 대구 MDS 점심반", "재원"],
                   ["ZZZZ-ZZZZ", "없는 반", "재원"]],
        }

    def signup(self, code, no="minsu01"):
        c = self.app.test_client()
        c.post("/signup", data={"code": code, "name": "김민수", "student_no": no, "password": "Signup!2026x",
                                "confirm": "Signup!2026x", "consent": "1"})
        return c

    def test_token_required(self):
        self.assertEqual(self.push(self.tables(), token="thl_wrong").status_code, 401)
        self.assertEqual(self.app.test_client().post("/api/sync", json={"tables": {}}).status_code, 401)

    def test_sync_strips_names_and_registers_codes(self):
        r = self.push(self.tables()).get_json()
        self.assertTrue(r["ok"])
        self.assertEqual(r["saved"]["성적"], 2)
        self.assertEqual(r["codes"]["added"], 2)
        self.assertEqual(r["codes"]["no_class"], ["없는 반"])
        with self.app.app_context():
            raw = " ".join(x["data"] for x in query("SELECT data FROM sys_rows"))
            self.assertNotIn("김민수", raw)
            self.assertNotIn("이영희", raw)
            self.assertIsNotNone(query("SELECT 1 FROM student_codes WHERE code = 'K7QM3XPA'", one=True))
        # 다시 보내면 표가 통째로 바뀐다 (줄이 늘지 않는다)
        self.push(self.tables())
        with self.app.app_context():
            self.assertEqual(query("SELECT COUNT(*) AS n FROM sys_rows WHERE tbl = '성적'", one=True)["n"], 2)

    def test_student_sees_only_own_records(self):
        self.push(self.tables())
        s = self.signup("k7qm-3xpa")                         # 하이픈·소문자도 같은 코드
        page = s.get("/s/scores").data.decode()
        self.assertIn("S1 6주차 주간테스트", page)
        self.assertIn("+7.8", page)                          # 평균 대비: 44 − 36.2
        self.assertNotIn("1,2,3", page)                      # 다른 학생의 틀린 문항
        wrong = s.get("/s/wrong").data.decode()
        self.assertIn("그래프 축을 거꾸로", wrong)
        self.assertIn("같은 답을 고른 반 학생 31%", wrong)
        self.assertNotIn("9번", wrong)                       # 정정된 문항은 빠진다
        self.assertIn("22번", wrong)
        att = s.get("/s/attendance").data.decode()
        self.assertIn("지각", att)
        self.assertIn("14:07", att)

    def test_redo_round_trip(self):
        self.push(self.tables())
        s = self.signup("K7QM3XPA")
        s.post("/s/redo", data={"exam": "S1 6주차 주간테스트", "no": "16", "result": "맞힘"})
        self.assertEqual(s.post("/s/redo", data={"exam": "S1 6주차 주간테스트", "no": "9", "result": "맞힘"}).status_code, 404)
        r = self.app.test_client().get("/api/sync/redo", headers={"Authorization": "Bearer " + self.token}).get_json()
        self.assertEqual(r["rows"][1][:4], ["K7QM3XPA", "S1 6주차 주간테스트", 16, "맞힘"])
        self.assertIn("is-done", s.get("/s/wrong").data.decode())

    def test_existing_account_links_code(self):
        self.push(self.tables())
        with self.app.app_context():
            sid = execute("INSERT INTO students (class_id, name, student_no) VALUES (?, '이영희', 'young')", (self.cid,))
            execute("INSERT INTO users (role, username, password_hash, student_id) VALUES ('student', 'young', ?, ?)",
                    (hash_password("Young!2026xx"), sid))
        s = self.app.test_client()
        s.post("/login", data={"username": "young", "password": "Young!2026xx"})
        self.assertIn("학생코드 연결", s.get("/s/scores").data.decode())
        s.post("/s/link", data={"code": "ABCD-EFGH"})
        self.assertIn("-6.2", s.get("/s/scores").data.decode())
        # 이미 쓰인 코드로는 다른 사람이 연결할 수 없다
        other = self.signup("ABCD-EFGH", no="thief01")
        self.assertNotIn("-6.2", other.get("/s/scores").data.decode())

    def test_csv_upload(self):
        csv_text = "학생코드,날짜,출결,도착시각\nK7QM-3XPA,2026-11-08,결석,\n"
        r = self.t.post("/t/link/upload", data={"files": (io.BytesIO(csv_text.encode("cp949")), "조교 시스템 - 🌐앱_출결.csv")},
                        content_type="multipart/form-data", follow_redirects=True)
        self.assertIn("출결 1줄", r.data.decode())
        with self.app.app_context():
            self.assertEqual(json.loads(query("SELECT data FROM sys_rows WHERE tbl = '출결'", one=True)["data"])["출결"], "결석")

    def test_book_purchase_links(self):
        r = self.t.post("/t/books/shop", data={"lineup": "smartstore.naver.com/thedu/products/1", "framing": "javascript:alert(1)",
                                               "squeeze": "", "sweep": "https://example.com/sweep"}, follow_redirects=True)
        self.assertIn("FRAMING", r.data.decode())                  # 주소가 아닌 값은 거부
        home = self.app.test_client().get("/").data.decode()
        self.assertIn("교재 구매", home)                            # 첫 화면 안내에는 입구만
        self.assertNotIn("smartstore", home)
        self.assertEqual(self.app.test_client().get("/s/books/buy").status_code, 302)   # 로그인 전에는 막힘
        s = self.signup("K7QM-3XPA") if self.push(self.tables()) else None
        page = s.get("/s/books/buy").data.decode()
        self.assertIn('href="https://smartstore.naver.com/thedu/products/1"', page)
        self.assertIn('href="https://example.com/sweep"', page)
        self.assertNotIn("javascript:", page)
        self.assertEqual(page.count("준비 중"), 2)

    def test_table_names(self):
        import sysdata
        self.assertEqual(sysdata.table_key("🌐앱_성적"), "성적")
        self.assertEqual(sysdata.table_key("학생 시스템 - 🌐앱_오답노트.csv"), "오답노트")
        self.assertIsNone(sysdata.table_key("학생DB"))


if __name__ == "__main__":
    unittest.main()
