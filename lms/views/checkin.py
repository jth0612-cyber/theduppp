"""RFID 카드 출결 (단과).

데스크 PC 에 /t/checkin 을 띄워 둔다. USB RFID 리더기는 카드를 대면 키보드처럼 일련번호를 치고 Enter 를 누르므로,
화면의 입력 칸이 그 번호를 받아 /t/checkin/tap 으로 보낸다(프로그램 설치 없음).
- 카드 번호 = 단과 학생의 아이디(students.student_no). 단과 반의 재원생만 찾는다.
- 하루 한 번만 기록. 다시 대면 처음 시각을 알려 준다.
- 지각: 그날 반 시간표에서 지금 진행 중이거나 다음 수업의 시작 + 지각 기준(분)을 넘으면 지각. 시간표가 없으면 출석.
"""
from datetime import datetime, timedelta

from flask import Blueprint, g, jsonify, render_template, request

from db import execute, normalize_card, query
from security import audit, staff_required

bp = Blueprint("checkin", __name__)
LATE_MIN = 5


def _now():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Seoul")).replace(tzinfo=None)
    except Exception:
        from datetime import timezone
        return datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)


def _late_min():
    r = query("SELECT value FROM settings WHERE key = 'late_minutes'", one=True)
    try:
        return max(0, min(60, int(r["value"]))) if r else LATE_MIN
    except ValueError:
        return LATE_MIN


def judge(class_id, now):
    """(상태, 기준 수업 시작 'HH:MM' 또는 None)"""
    hm = now.strftime("%H:%M")
    slots = query("SELECT starts, ends FROM timetable WHERE class_id = ? AND weekday = ? ORDER BY starts", (class_id, now.weekday()))
    slot = next((s for s in slots if s["ends"] > hm), None)          # 지금 진행 중이거나 다음 수업
    if slot is None:
        return "출석", None
    h, m = map(int, slot["starts"].split(":"))
    start = now.replace(hour=h, minute=m, second=0, microsecond=0)
    return ("지각" if now > start + timedelta(minutes=_late_min()) else "출석"), slot["starts"]


@bp.route("/t/checkin")
@staff_required
def screen():
    day = _now().date().isoformat()
    classes = query("SELECT id, name FROM classes WHERE archived = 0 AND track = '단과' ORDER BY name")
    return render_template("teacher/checkin.html", classes=classes, day=day, late=_late_min(), recent=_recent(day))


def _recent(day, limit=12):
    return query("""SELECT k.at, k.status, s.name, c.name AS class_name FROM checkins k JOIN students s ON s.id = k.student_id
                    JOIN classes c ON c.id = k.class_id WHERE k.day = ? ORDER BY k.at DESC LIMIT ?""", (day, limit))


@bp.route("/t/checkin/tap", methods=["POST"])
@staff_required
def tap():
    raw = (request.get_json(silent=True) or {}).get("card") or request.form.get("card", "")
    card = normalize_card(raw)
    if not card:
        return jsonify(ok=False, kind="bad", msg="카드 번호를 읽지 못했어요. 다시 대 주세요.")
    s = query("""SELECT s.id, s.name, s.class_id, c.name AS class_name FROM students s JOIN classes c ON c.id = s.class_id
                 WHERE s.student_no = ? AND s.active = 1 AND c.archived = 0 AND c.track = '단과'""", (card,), one=True)
    if s is None:
        return jsonify(ok=False, kind="unknown", card=card, msg="등록되지 않은 카드예요. 조교 선생님께 카드 등록을 요청해 주세요.")
    now = _now()
    day, at = now.date().isoformat(), now.strftime("%H:%M:%S")
    had = query("SELECT at, status FROM checkins WHERE student_id = ? AND day = ?", (s["id"], day), one=True)
    if had:
        return jsonify(ok=True, kind="again", name=s["name"], class_name=s["class_name"], status=had["status"], at=had["at"][:5],
                       msg=f"이미 {had['at'][:5]}에 {had['status']} 처리됐어요.")
    status, starts = judge(s["class_id"], now)
    execute("INSERT INTO checkins (student_id, class_id, day, at, status, by_user) VALUES (?, ?, ?, ?, ?, ?)",
            (s["id"], s["class_id"], day, at, status, g.user["id"]))
    audit("checkin", f"student:{s['id']} {status}")
    return jsonify(ok=True, kind=status, name=s["name"], class_name=s["class_name"], status=status, at=at[:5], starts=starts)


@bp.route("/t/checkin/today")
@staff_required
def today():
    day = _now().date().isoformat()
    cid = request.args.get("class", type=int)
    rows = query("""SELECT s.id, s.name, s.student_no, k.at, k.status FROM students s JOIN classes c ON c.id = s.class_id
                    LEFT JOIN checkins k ON k.student_id = s.id AND k.day = ?
                    WHERE s.active = 1 AND c.track = '단과' AND c.archived = 0 AND (? IS NULL OR c.id = ?)
                    ORDER BY k.at IS NULL, k.at, s.name""", (day, cid, cid))
    return jsonify(day=day, rows=[dict(r) for r in rows], recent=[dict(r) for r in _recent(day)])


def my_checkins(student_id):
    return [{"day": r["day"], "status": r["status"], "arrived": r["at"][:5]}
            for r in query("SELECT day, at, status FROM checkins WHERE student_id = ? ORDER BY day DESC", (student_id,))]
