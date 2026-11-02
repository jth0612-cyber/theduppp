"""같이 공부(산사·목욕탕·바닷가 역·골목 찻집) 점검: python -m unittest discover tests"""
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
        self.assertIn("산사", a.get("/s/rooms").data.decode())
        a.get("/s/rooms/sanji")
        page = b.get("/s/rooms/sanji").data.decode()
        self.assertIn("닉0", page)                                     # 같은 장소의 친구가 보임
        r = a.post("/s/rooms/sanji/beat", data={"action": "start", "plan": "25"}).get_json()
        me = [m for m in r["members"] if m["me"]][0]
        self.assertEqual(me["status"], "focus")
        # 방금 시작했는데 25분을 주장해도 인정하지 않는다
        r = a.post("/s/rooms/sanji/done", data={"minutes": "25"}).get_json()
        self.assertEqual(r["minutes"], 0)
        self.assertEqual(self.q("SELECT COUNT(*) AS n FROM focus_logs", one=True)["n"], 0)
        # 서버 기준 30분 전에 시작했다면 계획한 25분까지 인정
        a.post("/s/rooms/sanji/beat", data={"action": "start", "plan": "25"})
        with self.app.app_context():
            execute("UPDATE room_presence SET focus_since = datetime('now', 'localtime', '-30 minutes')")
        r = a.post("/s/rooms/sanji/done", data={"minutes": "90"}).get_json()
        self.assertEqual((r["minutes"], r["today"]), (25, 25))
        self.assertNotIn("points", r)
        self.assertIn("<b>25<small>분", a.get("/s/").data.decode())   # 홈 오늘 집중
        # 떠나면 목록에서 빠진다
        a.post("/s/rooms/sanji/beat", data={"action": "leave"})
        self.assertNotIn("닉0 (나)", b.get("/s/rooms/sanji").data.decode())
        self.assertIn("학생0", self.t.get("/t/rooms").data.decode())

    def test_3d_positions(self):
        a, b = self.student(0), self.student(1)
        page = a.get("/s/rooms/sanji").data.decode()
        self.assertIn("sanji3d.js", page)                                # 산사는 3D
        self.assertIn("data-enter-btn", page)
        self.assertNotIn("sanji3d.js", a.get("/s/rooms/sanji?flat=1").data.decode())   # 그림 버전도 남김
        self.assertNotIn("sanji3d.js", a.get("/s/rooms/eki").data.decode())
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


if __name__ == "__main__":
    unittest.main()
