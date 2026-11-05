"""소도시 명상(신사·목욕탕·바닷가 역·골목 찻집) 점검: python -m unittest discover tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import execute  # noqa: E402
from tests import test_study  # noqa: E402


class RoomsTest(unittest.TestCase):
    setUp = test_study.StudyTest.setUp
    tearDown = test_study.StudyTest.tearDown
    student = test_study.StudyTest.student
    q = test_study.StudyTest.q

    def test_presence_and_focus(self):
        a, b = self.student(0), self.student(1)
        self.assertEqual(a.get("/s/rooms/nowhere").status_code, 404)
        self.assertIn("신사", a.get("/s/rooms").data.decode())
        a.get("/s/rooms/sanji")
        page = b.get("/s/rooms/sanji").data.decode()
        self.assertIn("닉0", page)                                     # 같은 장소의 친구가 보임
        r = a.post("/s/rooms/sanji/beat", data={"action": "start", "plan": "40"}).get_json()
        me = [m for m in r["members"] if m["me"]][0]
        self.assertEqual(me["status"], "focus")
        # 방금 시작했는데 40분을 주장해도 인정하지 않는다
        r = a.post("/s/rooms/sanji/done", data={"minutes": "40"}).get_json()
        self.assertEqual(r["minutes"], 0)
        self.assertEqual(self.q("SELECT COUNT(*) AS n FROM focus_logs", one=True)["n"], 0)
        # 서버 기준 50분 전에 시작했다면 계획한 40분까지 인정 (타이머는 15·40·80·100분, 그 밖의 값은 40분)
        r = a.post("/s/rooms/sanji/beat", data={"action": "start", "plan": "25"}).get_json()
        self.assertEqual([m for m in r["members"] if m["me"]][0]["plan"], 40)
        a.post("/s/rooms/sanji/beat", data={"action": "start", "plan": "40"})
        with self.app.app_context():
            execute("UPDATE room_presence SET focus_since = datetime('now', 'localtime', '-50 minutes')")
        r = a.post("/s/rooms/sanji/done", data={"minutes": "90"}).get_json()
        self.assertEqual((r["minutes"], r["today"]), (40, 40))
        self.assertNotIn("points", r)
        self.assertIn("<b>40<small>분", a.get("/s/").data.decode())   # 홈 오늘 집중
        # 떠나면 목록에서 빠진다
        a.post("/s/rooms/sanji/beat", data={"action": "leave"})
        self.assertNotIn("닉0 (나)", b.get("/s/rooms/sanji").data.decode())
        self.assertIn("학생0", self.t.get("/t/rooms").data.decode())

    def test_3d_positions(self):
        a, b = self.student(0), self.student(1)
        page = a.get("/s/rooms/sanji").data.decode()
        self.assertIn("world3d.js", page)                                # 신사는 3D
        self.assertIn("data-enter-btn", page)
        self.assertNotIn("world3d.js", a.get("/s/rooms/sanji?flat=1").data.decode())   # 그림 버전도 남김
        for p in ("sento", "eki", "kissa"):                              # 나머지 세 곳도 3D
            self.assertIn("world3d.js", a.get(f"/s/rooms/{p}").data.decode())
        a.post("/s/rooms/sanji/beat", data={"x": "3.5", "z": "-7", "ry": "3.14", "pose": "sit", "seat": "8",
                                            "color": "#5fa3c9"})
        b.get("/s/rooms/sanji")
        r = b.post("/s/rooms/sanji/beat", data={"x": "999", "z": "nan", "pose": "fly", "color": "red"}).get_json()
        friend = [m for m in r["members"] if not m["me"]][0]
        self.assertEqual((friend["x"], friend["z"], friend["pose"], friend["seat"], friend["color"]),
                         (3.5, -7.0, "sit", 8, "#5fa3c9"))
        mine = [m for m in r["members"] if m["me"]][0]
        self.assertEqual((mine["x"], mine["pose"]), (0, "stand"))        # 이상한 값은 무시
        self.assertTrue(mine["color"].startswith("#"))

    def test_notes(self):
        a = self.student(0)
        a.post("/s/rooms/eki/note", data={"body": "  기차 오기 전에   2단원 끝  "})
        n = self.q("SELECT * FROM room_notes", one=True)
        self.assertEqual(n["body"], "기차 오기 전에 2단원 끝")
        self.assertIn("기차 오기 전에", self.student(1).get("/s/rooms/eki").data.decode())
        self.assertEqual(self.student(1).post(f"/s/rooms/notes/{n['id']}/delete").status_code, 404)  # 남의 글
        for i in range(5):
            a.post("/s/rooms/eki/note", data={"body": f"줄 {i}"})
        self.assertEqual(self.q("SELECT COUNT(*) AS n FROM room_notes", one=True)["n"], 5)             # 하루 5줄
        self.t.post(f"/t/rooms/notes/{n['id']}/delete")
        self.assertEqual(self.q("SELECT COUNT(*) AS n FROM room_notes", one=True)["n"], 4)

    def _log(self, i, place, minutes, ago_days=0):
        uid = self.q("SELECT id FROM users WHERE username = ?", (f"S{i:03d}",), one=True)["id"]
        with self.app.app_context():
            execute("INSERT INTO focus_logs (user_id, place, minutes, ended_at) VALUES (?, ?, ?, datetime('now', 'localtime', ?))",
                    (uid, place, minutes, f"-{ago_days} days"))
        return uid

    def test_rank_per_place_and_king_crown(self):
        u0 = self._log(0, "sanji", 120)
        u1 = self._log(1, "sanji", 60)
        self._log(1, "eki", 300)
        a, b = self.student(0), self.student(1)
        page = b.get("/s/rooms/rank?place=sanji").data.decode()
        board = page[page.index('class="rank-list"'):]
        self.assertLess(board.index("닉0"), board.index("닉1"))           # 신사는 닉0 이 1위
        self.assertIn("2시간", page)
        self.assertIn("2<small>위</small>", page)                       # 닉1 의 내 순위
        eki = b.get("/s/rooms/rank?place=eki").data.decode()
        eki = eki[eki.index('class="rank-list"'):]
        self.assertIn("닉1", eki); self.assertNotIn("닉0", eki)          # 장소마다 따로
        self.assertIn("터줏대감 <b>닉0</b>", a.get("/s/rooms").data.decode())
        # 3D 화면: 1위에게 king 표시
        a.get("/s/rooms/sanji")
        r = b.post("/s/rooms/sanji/beat", data={}).get_json()
        kings = {m["id"]: m["king"] for m in r["members"]}
        self.assertTrue(kings[u0]); self.assertFalse(kings[u1])
        # 기간: 지난달 기록은 '이번 주'에 안 들어감
        self._log(2, "kissa", 500, ago_days=40)
        self.assertIn("아직 아무도", a.get("/s/rooms/rank?place=kissa&period=week").data.decode())
        self.assertIn("닉2", a.get("/s/rooms/rank?place=kissa&period=all").data.decode())
        self.assertEqual(a.get("/s/rooms/rank?place=nowhere").status_code, 404)

    def test_follow_and_friends(self):
        a, b = self.student(0), self.student(1)
        u1 = self.q("SELECT id FROM users WHERE username='S001'", one=True)["id"]
        u0 = self.q("SELECT id FROM users WHERE username='S000'", one=True)["id"]
        self.assertIn("닉1", a.get("/s/friends?q=닉1").data.decode())     # 닉네임으로 찾기
        a.post(f"/s/follow/{u1}")
        self.assertEqual(self.q("SELECT COUNT(*) AS n FROM follows", one=True)["n"], 1)
        fr = a.get("/s/friends").data.decode()
        self.assertIn("팔로잉", fr); self.assertIn("닉1", fr)
        self.assertIn("닉0", b.get("/s/friends").data.decode())          # b 의 팔로워에 닉0
        self.assertEqual(a.post(f"/s/follow/{u0}").status_code, 404)    # 나 자신은 안 됨
        teacher = self.q("SELECT id FROM users WHERE role='teacher'", one=True)["id"]
        self.assertEqual(a.post(f"/s/follow/{teacher}").status_code, 404)  # 선생님 계정은 안 됨
        # 팔로잉끼리 순위
        self._log(1, "sento", 30)
        self._log(2, "sento", 90)
        mine = a.get("/s/rooms/rank?place=sento&scope=follow").data.decode()
        mine = mine[mine.index('class="rank-list"'):]
        self.assertIn("닉1", mine); self.assertNotIn("닉2", mine)
        self.assertIn("닉2", a.get("/s/rooms/rank?place=sento").data.decode())
        # 소도시 명상 목록에 팔로잉 표시
        b.get("/s/rooms/sento")
        r = a.post("/s/rooms/sento/beat", data={}).get_json()
        self.assertTrue([m for m in r["members"] if m["id"] == u1][0]["follow"])
        # 다시 누르면 언팔로우, next 는 /s/ 안쪽만
        r = a.post(f"/s/follow/{u1}", data={"next": "https://evil.example/"})
        self.assertTrue(r.headers["Location"].endswith("/s/friends"))
        self.assertEqual(self.q("SELECT COUNT(*) AS n FROM follows", one=True)["n"], 0)
        self.assertEqual(a.get("/s/friends?q=50%25_").status_code, 200)   # 특수문자 검색도 오류 없음

    def test_board_chat_and_word_filter(self):
        a, b = self.student(0), self.student(1)
        a.get("/s/rooms/sento"); b.get("/s/rooms/sento")
        # 화롯가(8~11번 방석)에 앉지 않으면 칠판에 못 쓴다
        r = a.post("/s/rooms/sento/write", data={"body": "안녕"}).get_json()
        self.assertFalse(r["ok"]); self.assertIn("화롯가", r["error"])
        a.post("/s/rooms/sento/beat", data={"x": "1", "z": "1", "seat": "3"})         # 탕 자리
        self.assertFalse(a.post("/s/rooms/sento/write", data={"body": "안녕"}).get_json()["ok"])
        a.post("/s/rooms/sento/beat", data={"x": "1", "z": "1", "seat": "9"})         # 화롯가
        r = a.post("/s/rooms/sento/write", data={"body": "  오늘   2단원 끝!  "}).get_json()
        self.assertTrue(r["ok"]); self.assertEqual(r["board"][-1]["body"], "오늘 2단원 끝!")
        self.assertEqual(r["board"][-1]["nick"], "닉0")
        self.assertFalse(a.post("/s/rooms/sento/write", data={"body": "또"}).get_json()["ok"])  # 너무 빨리
        with self.app.app_context():
            execute("UPDATE room_chat SET created_at = datetime('now', 'localtime', '-1 minute')")
        r = a.post("/s/rooms/sento/write", data={"body": "시1발 졸려"}).get_json()        # 욕설 거르기
        self.assertFalse(r["ok"]); self.assertIn("바른 말", r["error"])
        self.assertEqual(self.q("SELECT COUNT(*) AS n FROM room_chat", one=True)["n"], 1)
        # 같은 장소의 친구는 beat 로 칠판 글을 받는다
        board = b.post("/s/rooms/sento/beat", data={}).get_json()["board"]
        self.assertEqual([x["body"] for x in board], ["오늘 2단원 끝!"])
        # 역 노트: 누구나 쓰고(하루 5줄), 욕설은 막힌다. 아래 남기는 글 칸과 같은 곳에 저장
        r = b.post("/s/rooms/eki/write", data={"body": "기차 오기 전에 한 단원"}).get_json()
        self.assertTrue(r["ok"]); self.assertEqual(r["board"][-1]["body"], "기차 오기 전에 한 단원")
        self.assertFalse(b.post("/s/rooms/eki/write", data={"body": "ㅂ ㅅ 같네"}).get_json()["ok"])
        b.post("/s/rooms/eki/note", data={"body": "병신"})
        self.assertEqual(self.q("SELECT COUNT(*) AS n FROM room_notes", one=True)["n"], 1)
        self.assertEqual(b.post("/s/rooms/kissa/write", data={"body": "x"}).status_code, 404)  # 판이 없는 곳
        # 선생님이 칠판 글을 지울 수 있다
        cid = self.q("SELECT id FROM room_chat", one=True)["id"]
        self.assertIn("오늘 2단원 끝!", self.t.get("/t/rooms").data.decode())
        self.t.post(f"/t/rooms/chat/{cid}/delete")
        self.assertEqual(self.q("SELECT COUNT(*) AS n FROM room_chat", one=True)["n"], 0)

    def test_fortune_once_a_day_with_charm(self):
        a, b = self.student(0), self.student(1)
        f1 = a.post("/s/rooms/fortune").get_json()
        self.assertFalse(f1["again"]); self.assertIn(f1["luck"], {"아주 좋음", "좋음", "보통", "조금 아쉬움"})
        f2 = a.post("/s/rooms/fortune").get_json()
        self.assertTrue(f2["again"]); self.assertEqual(f1["text"], f2["text"])           # 하루에 한 번, 같은 결과
        a.get("/s/rooms/sanji"); b.get("/s/rooms/sanji")
        r = b.post("/s/rooms/sanji/beat", data={}).get_json()
        friend = [m for m in r["members"] if not m["me"]][0]
        self.assertEqual(friend["charm"], f1["color"])                                    # 친구에게 행운 부적이 보임
        self.assertIsNone([m for m in r["members"] if m["me"]][0]["charm"])
        self.assertEqual(a.post("/s/rooms/fortune/tie").get_json()["tied_today"], 1)
        self.assertTrue(a.post("/s/rooms/fortune").get_json()["tied"])
        self.assertNotIn("mission", f1)                                                   # 오늘의 미션은 없앰

    def test_shared_actions_reach_friends(self):
        a, b = self.student(0), self.student(1)
        a.get("/s/rooms/sento"); b.get("/s/rooms/sento")
        u0 = self.q("SELECT id FROM users WHERE username='S000'", one=True)["id"]
        seq0 = [m for m in b.post("/s/rooms/sento/beat", data={}).get_json()["members"] if m["id"] == u0][0]["act_seq"]
        a.post("/s/rooms/sento/beat", data={"x": "0", "z": "0", "act": "splash"})
        m = [m for m in b.post("/s/rooms/sento/beat", data={}).get_json()["members"] if m["id"] == u0][0]
        self.assertEqual((m["act"], m["act_seq"]), ("splash", seq0 + 1))
        a.post("/s/rooms/sento/beat", data={"act": "hack<script>"})          # 정해진 동작만
        m = [m for m in b.post("/s/rooms/sento/beat", data={}).get_json()["members"] if m["id"] == u0][0]
        self.assertEqual(m["act_seq"], seq0 + 1)


if __name__ == "__main__":
    unittest.main()
