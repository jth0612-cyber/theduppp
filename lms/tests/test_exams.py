"""복습 테스트·모의고사: 인계 문서 13장 검수 사례 (OMR 형식, 수험번호, 선지 분포, 합답형 분석, 학부모 문자, 학습 유형)."""
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import exams  # noqa: E402
import omr  # noqa: E402
from app import create_app  # noqa: E402
from db import execute, query  # noqa: E402
from security import encrypt, hash_password  # noqa: E402

PW = "Teach3r!pass"


def xlsx(rows, sheets=None):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "OMR"
    for r in rows:
        ws.append(r)
    for title, srows in (sheets or {}).items():
        s = wb.create_sheet(title)
        for r in srows:
            s.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class Pure(unittest.TestCase):
    def test_choice_dist_reference(self):
        """200명 중 ①3 ②8 ③62 ④12 ⑤115 → ①1.5% ②4% ③31% ④6% ⑤57.5%"""
        rows = [{"answers": a, "score": 0} for a in "1" * 3 + "2" * 8 + "3" * 62 + "4" * 12 + "5" * 115]
        st = exams.group_stats(rows, [5])
        self.assertEqual(exams.choice_dist(st, 0, 5), "①1.5% ②4% ③31% ④6% ⑤57.5%")
        self.assertEqual(exams.pct1(st["wrong"][0]), "42.5")

    def test_wrong_list_parsing(self):
        self.assertEqual(omr.parse_wrong("3,7", 10), {3: "", 7: ""})
        self.assertEqual(omr.parse_wrong("3 7 3", 10), {3: "", 7: ""})
        self.assertEqual(omr.parse_wrong("7:4, 3(2)", 10), {7: "4", 3: "2"})
        self.assertEqual(omr.parse_wrong("없음", 10), {})
        self.assertIsNone(omr.parse_wrong("", 10))                     # 빈칸 = 아직 입력 안 됨(만점과 구분)
        with self.assertRaises(omr.OmrError):
            omr.parse_wrong("11", 10)

    def test_multi_and_all_answers(self):
        import analysis
        self.assertTrue(analysis.is_right("4", "2,4"))
        self.assertFalse(analysis.is_right("3", "2,4"))
        self.assertTrue(analysis.is_right("0", "*"))
        self.assertTrue(analysis.is_right("R", 3))

    def test_hapdap_choice_analysis_overrides_type(self):
        info = {"format": "합답형", "options": "①ㄱ ②ㄴ ③ㄱ,ㄷ ④ㄴ,ㄷ ⑤ㄱ,ㄴ,ㄷ", "concept": "기울기",
                "traps": "ㄱ(O): 정의 [개념 부족] / ㄴ(O): 축의 의미를 바꿔 읽음 [자료 해석] / ㄷ(O): 이유 [계산 실수]"}
        a = exams.analyze_item(16, "3", 5, info)
        self.assertEqual(a["evidence"], "보기 차이 근거")
        self.assertEqual(a["diff"], "3번과 5번의 차이는 보기 ㄴ입니다.")
        self.assertEqual(a["type"], "자료 해석")
        self.assertIn("옳은 진술인 보기 ㄴ을 틀렸다고", a["analysis"])
        b = exams.analyze_item(16, "5", 3, info)                       # 틀린 진술을 옳다고 고름
        self.assertIn("틀린 진술인 보기 ㄴ을 옳다고", b["analysis"])
        c = exams.analyze_item(4, "2", 3, {"format": "일반", "distractors": "2번: 단위를 바꾸지 않음(계산 실수) / 4번: x(조건 독해)"})
        self.assertEqual((c["evidence"], c["type"]), ("고른 선지 근거", "계산 실수"))
        self.assertEqual(exams.analyze_item(4, "0", 3, {"concept": "중화"})["evidence"], "문항 성격 추정")
        self.assertEqual(exams.analyze_item(4, "2", 3, {})["evidence"], "정보 없음")

    def _rep(self):
        a16 = {"no": 16, "mine": "3", "key": "5", "rate": 42.5, "rate_all": 42.5, "same": 62, "same_pct": 31.0,
               "dist": "①1.5% ②4% ③31% ④6% ⑤57.5%", "diff": "3번과 5번의 차이는 보기 ㄴ입니다.",
               "analysis": "16번은 자료 해석 오류로, 보기 ㄴ에서 그래프의 x축과 y축의 의미를 오독하여 기울기의 의미를 반댓값으로 해석한 경우입니다.",
               "evidence": "보기 차이 근거", "type": "자료 해석", "confused": "ㄴ", "trap": "", "unit": "", "concept": "", "points": 3}
        a22 = {"no": 22, "mine": "", "key": "2", "rate": 64.0, "rate_all": 64.0, "same": 0, "same_pct": 0, "dist": "",
               "diff": "", "analysis": "", "evidence": "문항 성격 추정", "type": "", "confused": "", "trap": "", "unit": "",
               "concept": "", "points": 3}
        return {"mock": {"book_title": "2027 통합과학 파이널", "round_no": 1, "title": "", "full_score": 50, "n_items": 25, "id": 1},
                "r": {"score": 44}, "cls": "시대인재 대구 MDS 점심반", "st": {"avg": 36.2, "n": 200}, "enough": True,
                "all_enough": True, "wrong": [16, 22], "wrongs": [a16, a22]}

    def test_sms_matches_reference_line_by_line(self):
        want = """[정태혁 통합과학] 김OO 학생 학습 안내
2027 통합과학 파이널 1회 44/50 (시대인재 대구 MDS 점심반 평균 36.2), 틀린 문항 16, 22번

오답은 단순 개념 부족, 자료 해석, 조건 독해 누락, 계산 실수 등의 항목으로 나눠 기록합니다.

16번 오답 분석 · 반 오답률 42.5%, 내 답 3 → 정답 5
반 선택 비율: ①1.5% ②4% ③31% ④6% ⑤57.5%
3번과 5번의 차이는 보기 ㄴ입니다.
16번은 자료 해석 오류로, 보기 ㄴ에서 그래프의 x축과 y축의 의미를 오독하여 기울기의 의미를 반댓값으로 해석한 경우입니다.
반 학생 31%가 같은 3번을 골라, 많은 학생이 보기 ㄴ에서 헷갈린 문항입니다.

22번 · 반 오답률 64%로 반 전체가 어려워한 고난도 문항입니다.

저희 플랫폼의 1:1 밀착 피드백 시스템을 적극적으로 이용하시길 추천드립니다."""
        got = exams.compose_sms(self._rep(), "김OO")
        self.assertEqual(got.split("\n"), want.split("\n"))

    def test_sms_perfect_few_and_bytes(self):
        rep = self._rep()
        rep.update(wrong=[], wrongs=[])
        t = exams.compose_sms(rep, "김OO")
        self.assertIn("44/50 (시대인재 대구 MDS 점심반 평균 36.2), 만점", t)
        self.assertNotIn("1:1 밀착", t)                                # 만점이면 맺음말 없음
        rep = self._rep()
        rep["wrongs"][0]["same"] = 2                                  # 혼자 고른 답이면 "많은 학생" 문장 없음
        self.assertNotIn("많은 학생", exams.compose_sms(rep, "김OO"))
        rep = self._rep()
        rep.update(enough=False)
        t = exams.compose_sms(rep, "김OO")
        self.assertNotIn("반 오답률", t)
        self.assertNotIn("반 선택 비율", t)
        self.assertIn("22번도 함께 복습할 문항입니다.", t)
        rep = self._rep()
        long = "가" * 1100
        t = exams.compose_sms(rep, "김OO", overall=long)               # 2000바이트 넘으면 자세히 볼 문항을 줄인다
        self.assertNotIn("16번 오답 분석", t)
        self.assertIn("16, 22번 · 반 오답률", t)

    def test_study_block(self):
        rep = self._rep()
        rep["wrongs"][0]["rate"] = 20                                  # 반 학생 대부분이 맞힌 문항
        st = {"main": "안정형", "sub": "", "desc": "과제를 꾸준히 해내고, 푼 만큼 시험에서도 결과가 나오고 있습니다.",
              "practice": "과제 중 가장 어려운 3문항을 시간을 재고 풀기"}
        t = exams.study_block(st, rep, [rep])
        self.assertEqual(t.split("\n"), ["공부 유형: 안정형", st["desc"],
                                         "이번 시험에서는 반 학생 대부분이 맞힌 16번을 놓쳤습니다. 과제와 시험 사이에 차이가 있는지 살펴보겠습니다.",
                                         "이번 주 실천: 과제 중 가장 어려운 3문항을 시간을 재고 풀기"])
        st["main"] = "미이행형"
        self.assertNotIn("확인됩니다", exams.study_block(st, rep, [rep]))     # 시험으로 확인할 수 없음 → 잇는 문장 없음

    def test_profile_rules(self):
        def h(rate, wrongs, enough=True, n=10):
            return {"r": {"score": rate * 50}, "full": 50, "enough": enough, "wrong": [a["no"] for a in wrongs],
                    "wrongs": wrongs, "st": {"wrong": [10] * n}, "mock": {"pts": [5] * n, "info": {}, "id": id(wrongs)}}
        w = lambda no, t, rate=50: {"no": no, "type": t, "rate": rate, "evidence": "고른 선지 근거" if t else "문항 성격 추정"}
        self.assertEqual(exams.classify_profile([h(0.6, [w(1, "자료 해석")])])["type"], "판단 보류")
        self.assertEqual(exams.classify_profile([h(0.95, [w(1, "")]), h(0.92, [])])["type"], "실전 완성형")
        many = [w(i, "자료 해석") for i in range(1, 5)] + [w(5, "개념 부족")]
        p = exams.classify_profile([h(0.5, many[:3]), h(0.6, many[3:])])
        self.assertEqual(p["type"], "자료 해석 보강형")
        self.assertIn("분류된 오답 5개 중 자료 해석 4개(80%)", p["basis"])
        mixed = [w(1, "자료 해석"), w(2, "자료 해석"), w(3, "개념 부족"), w(4, "개념 부족"), w(5, "계산 실수")]
        self.assertEqual(exams.classify_profile([h(0.5, mixed[:3]), h(0.6, mixed[3:])])["type"], "복합형")
        adv = [w(i, "자료 해석", rate=60) for i in range(1, 6)]
        self.assertEqual(exams.classify_profile([h(0.8, adv[:3]), h(0.8, adv[3:])])["type"], "심화 도전형")


class Upload(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False, "ANALYSIS_TTL": 0, "SEED_PRACTICE": True,
                               "DATABASE": os.path.join(self.tmp.name, "t.sqlite3"), "UPLOAD_DIR": os.path.join(self.tmp.name, "up")})
        os.makedirs(self.app.config["UPLOAD_DIR"], exist_ok=True)
        with self.app.app_context():
            from db import init_db
            init_db(self.app.config["DATABASE"])
            execute("INSERT INTO users (role, username, password_hash) VALUES ('teacher', 'teacher', ?)", (hash_password(PW),))
            execute("INSERT INTO users (role, username, password_hash, display_name) VALUES ('assistant', 'ta', ?, '박조교')", (hash_password(PW),))
            a = execute("INSERT INTO classes (name) VALUES ('시대인재 대구 MDS 점심반')")
            b = execute("INSERT INTO classes (name) VALUES ('B반')")
            self.sid = {}
            for i in range(12):
                sid = execute("INSERT INTO students (class_id, name, student_no, parent_phone_enc) VALUES (?, ?, ?, ?)",
                              (a, f"학생{i:02d}", f"27{i:04d}", encrypt(f"010-1234-{5600 + i:04d}")))
                self.sid[f"학생{i:02d}"] = sid
            # 형제자매: 같은 학부모 번호
            self.sid["형"] = execute("INSERT INTO students (class_id, name, student_no, parent_phone_enc) VALUES (?, '김형', '279001', ?)", (b, encrypt("010-0777-1111")))
            self.sid["동생"] = execute("INSERT INTO students (class_id, name, student_no, parent_phone_enc) VALUES (?, '김동생', '279002', ?)", (b, encrypt("010-0777-1111")))
            execute("INSERT INTO users (role, username, password_hash, student_id) VALUES ('student', '270000', ?, ?)", (hash_password(PW), self.sid["학생00"]))
            self.mid = query("""SELECT m.id FROM mocks m JOIN books b ON b.id = m.book_id
                                WHERE b.kind = '복습 테스트' AND b.title = '복습 테스트' AND m.round_no = 3""", one=True)["id"]
        from views import auth
        auth._ip_attempts.clear()
        self.ta = self.app.test_client()
        self.ta.post("/login", data={"username": "ta", "password": PW})

    def tearDown(self):
        with self.app.app_context():
            from db import close_db
            close_db()
        self.tmp.cleanup()

    def up(self, data, name="omr.xlsx"):
        return self.ta.post(f"/t/mocks/{self.mid}/omr", data={"file": (io.BytesIO(data), name)},
                            content_type="multipart/form-data", follow_redirects=True).data.decode()

    def res(self):
        with self.app.app_context():
            return {r["name"]: (r["answers"], r["score"]) for r in query(
                "SELECT s.name, r.answers, r.score FROM exam_results r JOIN students s ON s.id = r.student_id WHERE r.mock_id = ?", (self.mid,))}

    def test_seeded_rounds(self):
        with self.app.app_context():
            for kind in ("복습 테스트", "모의고사"):
                self.assertEqual(query("""SELECT COUNT(*) AS n FROM mocks m JOIN books b ON b.id = m.book_id
                                          WHERE b.kind = ? AND b.title = ?""", (kind, kind), one=True)["n"], 50)
        page = self.ta.get("/t/books").data.decode()
        self.assertIn("복습 테스트", page); self.assertIn("모의고사", page)
        self.assertIn("복테·모의고사", page)                              # 조교 메뉴도 강사와 같다

    def test_phone_numbers_key_row_and_safety(self):
        rows = [["", "", "1번", "2번", "3번", "4번", "5번"],                # 위에 빈 줄이 있어도 머리글을 찾는다
                ["성명", "수험번호", "1번", "2번", "3번", "4번", "5번"],
                ["정답", "", "③", "2,4", "1", "*", "5"],
                ["배점", "", 2, 2, 2, 2, 2],
                ["학생00", "12345600", 3, 4, 1, None, 5],                   # 8자리 = 학부모 번호 뒤 8자리 → 10점
                ["학생01", "010-1234-5601", "③", 2, 2, 1, 5],               # 하이픈 11자리 → 3번 틀림 8점
                ["학생02", 2345602, 1, 1, 1, 1, 1],                        # 앞 0이 지워진 7자리(02345602)는 없는 번호 → 이름으로
                ["학생03", "12345699", 3, 2, 1, 1, 5],                      # 없는 번호, 이름으로 찾음
                ["학생05", "12345604", 3, 2, 1, 1, 5],                      # 번호는 학생04, 이름은 학생05 → 넣지 않음
                ["김형", "07771111", 3, 2, 1, 1, 5],                        # 형제자매 → 이름으로 가림
                ["김형", "07771111", 3, 2, 1, 1, 5]]                        # 같은 학생 두 번
        html = self.up(xlsx(rows))
        r = self.res()
        self.assertEqual(r["학생00"], ("34105", 10))
        self.assertEqual(r["학생01"][1], 8)
        self.assertIn("학생02", r); self.assertIn("학생03", r); self.assertIn("김형", r)
        self.assertNotIn("학생05", r); self.assertNotIn("학생04", r)
        self.assertIn("번호는 학생04, 이름은 학생05", html)
        self.assertIn("같은 학생이 두 번", html)
        self.assertIn("반 학생 중 파일에 없는 학생", html)
        with self.app.app_context():
            m = exams.load_mock(self.mid)
        self.assertEqual((m["n_items"], m["full_score"], m["key"]), (5, 10, [3, "2,4", 1, "*", 5]))
        # 문항 수가 다른 파일은 막는다
        bad = self.up(xlsx([["이름", "1", "2", "3"], ["정답", 1, 2, 3], ["학생00", 1, 2, 3]]))
        self.assertIn("이 회차는 5문항", bad)
        # 학생 화면에 바로: 가입한 학생은 분석 화면에서 본다
        s = self.app.test_client(); s.post("/login", data={"username": "270000", "password": PW})
        page = s.get("/s/analysis").data.decode()
        self.assertIn("복습 테스트 3회", page); self.assertIn("내 답안", page)

    def test_missing_key_stops(self):
        html = self.up(xlsx([["이름", "1", "2"], ["학생00", 1, 2]]))
        self.assertIn("정답이 없는 문항: 1, 2번", html)
        self.assertEqual(self.res(), {})

    def test_ox_10_and_wrong_list_euckr(self):
        self.up(xlsx([["이름", "연락처", "1", "2", "3"], ["학생00", "010-1234-5600", "O", "X", ""], ["학생01", "", "O", "O", "O"]]))
        r = self.res()
        self.assertEqual(r["학생00"], ("R00", 1)); self.assertEqual(r["학생01"], ("RRR", 3))
        with self.app.app_context():
            execute("DELETE FROM exam_results"); execute("UPDATE mocks SET n_items = 0, answer_key = '[]', points = '[]' WHERE id = ?", (self.mid,))
        self.up(xlsx([["이름", "1", "2", "3", "4"], ["학생00", 1, 0, 1, 1], ["학생01", 1, 1, 1, 1]]))
        self.assertEqual(self.res()["학생00"], ("R0RR", 3))
        csv = "이름,틀린문항,점수\n학생02,\"2(3), 4\",50\n학생03,없음,100\n학생04,,\n".encode("cp949")
        html = self.up(csv, "omr.csv")
        r = self.res()
        self.assertEqual(r["학생02"], ("R3R0", 2)); self.assertEqual(r["학생03"][1], 4)
        self.assertNotIn("학생04", r)                                    # 틀린문항 빈칸 = 아직 입력 안 됨
        self.assertNotIn("계산 점수", html)                               # 100점 환산 점수와 맞으면 통과

    def test_item_info_sheet_sms_and_student_view(self):
        rows = [["이름", "수험번호"] + list(range(1, 4)), ["정답", "", 5, 2, 3]]
        for i in range(12):
            rows.append([f"학생{i:02d}", f"1234{5600 + i:04d}", 3 if i < 6 else 5, 2, 3 if i % 3 else 1])
        info = [["문항번호", "정답", "배점", "단원", "핵심개념", "문항형식", "선지구성", "보기함정"],
                [1, 5, 3, "지권의 변화", "판 경계", "합답형", "①ㄱ ②ㄴ ③ㄱ,ㄷ ④ㄴ,ㄷ ⑤ㄱ,ㄴ,ㄷ",
                 "ㄱ(O): 정의 [개념 부족] / ㄴ(O): 축을 바꿔 읽음 [자료 해석] / ㄷ(O): 이유 [계산 실수]"],
                [2, 2, 2, "", "", "", "", ""], [3, 3, 2, "", "", "", "", ""]]
        self.up(xlsx(rows, {"문항정보": info}))
        with self.app.app_context():
            m = exams.load_mock(self.mid)
            self.assertEqual(m["full_score"], 7)
            text = exams.sms_for(self.mid, self.sid["학생00"])
        self.assertTrue(text.startswith("[정태혁 통합과학] 학생00 학생 학습 안내\n복습 테스트 3회 "))
        self.assertIn("1번 오답 분석 · 반 오답률 50%, 내 답 3 → 정답 5", text)
        self.assertIn("3번과 5번의 차이는 보기 ㄴ입니다.", text)
        self.assertIn("1번은 자료 해석 오류로, 옳은 진술인 보기 ㄴ을 틀렸다고 판단한 경우입니다.", text)
        self.assertIn("반 학생 50%가 같은 3번을 골라, 많은 학생이 보기 ㄴ에서 헷갈린 문항입니다.", text)
        page = self.ta.get(f"/t/mocks/{self.mid}/sms").data.decode()
        self.assertIn("학생00", page); self.assertIn("010-1234-5600", page)
        csv = self.ta.get(f"/t/mocks/{self.mid}/sms?csv=1").data.decode("utf-8-sig")
        self.assertIn("학부모연락처", csv)
        s = self.app.test_client(); s.post("/login", data={"username": "270000", "password": PW})
        page = s.get("/s/analysis").data.decode()
        self.assertIn("오답 분석", page); self.assertIn("자료 해석", page); self.assertIn("반 선택 비율", page)
        # 학생은 문자·업로드 화면을 볼 수 없다
        self.assertNotEqual(s.get(f"/t/mocks/{self.mid}/sms").status_code, 200)

    def test_practice_class_isolated(self):
        """실장 TEST반: 가상 학생 50명, 연습 회차에서만 채점되고 실제 회차에는 섞이지 않는다."""
        with self.app.app_context():
            c = query("SELECT * FROM classes WHERE is_test = 1", one=True)
            self.assertEqual(c["name"], "실장 TEST반")
            self.assertEqual(query("SELECT COUNT(*) AS n FROM students WHERE class_id = ?", (c["id"],), one=True)["n"], 50)
            pm = query("""SELECT m.id FROM mocks m JOIN books b ON b.id = m.book_id
                          WHERE b.is_practice = 1 AND b.kind = '모의고사' AND m.round_no = 1""", one=True)["id"]
        data = self.ta.get(f"/t/mocks/{pm}/practice.xlsx").data
        html = self.ta.post(f"/t/mocks/{pm}/omr", data={"file": (io.BytesIO(data), "p.xlsx")},
                            content_type="multipart/form-data", follow_redirects=True).data.decode()
        self.assertIn("50명 반영", html)
        self.assertIn("연습", html)
        self.assertEqual(self.ta.get(f"/t/mocks/{self.mid}/practice.xlsx").status_code, 404)   # 실제 회차엔 없음
        # 같은 파일을 실제 회차에 올리면 연습반 학생은 찾지 않는다
        html = self.up(data)
        self.assertNotIn("50명 반영", html)
        with self.app.app_context():
            self.assertEqual(query("SELECT COUNT(*) AS n FROM exam_results WHERE mock_id = ?", (self.mid,), one=True)["n"], 0)
            sid = query("SELECT student_id FROM exam_results WHERE mock_id = ? LIMIT 1", (pm,), one=True)["student_id"]
        # 조교 피드백: 저장하면 문자 총평 자리에 들어가고, 모음 CSV 에는 학생코드만
        self.ta.post(f"/t/mocks/{pm}/note/{sid}", data={"note": "보기 판단 근거를 한 줄로 적는 연습을 시작했습니다."})
        page = self.ta.get(f"/t/mocks/{pm}/sms").data.decode()
        self.assertIn("보기 판단 근거를 한 줄로 적는 연습을 시작했습니다.", page)
        csv = self.ta.get("/t/feedback-notes.csv").data.decode("utf-8-sig")
        self.assertIn("TEST0", csv); self.assertIn("보기 판단 근거", csv)

    def test_exam_evaluation_staff_equal_and_visible(self):
        """시험 평가: 조교도 쓰고, 학생은 내 결과가 없어도 그 회차를 열어 본다."""
        r = self.ta.post(f"/t/mocks/{self.mid}/review", data={"level": "4", "time": "빠듯", "killer": "14번, 19",
                                                              "review": "후반 그래프 문항이 길다.", "video": "https://youtu.be/dQw4w9WgXcQ"},
                         follow_redirects=True)
        self.assertIn("시험 평가를 저장했습니다", r.data.decode())
        with self.app.app_context():
            m = query("SELECT * FROM mocks WHERE id = ?", (self.mid,), one=True)
            self.assertEqual((m["eval_level"], m["eval_time"], m["eval_killer"], m["review_by"]), (4, "빠듯", "14, 19", "박조교"))
        s = self.app.test_client(); s.post("/login", data={"username": "270000", "password": PW})
        page = s.get("/s/analysis").data.decode()
        self.assertIn("시험 평가", page); self.assertIn("어려움", page); self.assertIn("14, 19번", page)
        self.assertIn("youtube-nocookie.com/embed/dQw4w9WgXcQ", page)
        self.assertIn("내 결과는 아직 올라오지 않았습니다", page)
        bad = self.ta.post(f"/t/mocks/{self.mid}/review", data={"video": "https://example.com/v"}, follow_redirects=True)
        self.assertIn("유튜브 주소만", bad.data.decode())


if __name__ == "__main__":
    unittest.main()
