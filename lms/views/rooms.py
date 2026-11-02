"""함께 공부하는 장소: 일본 소도시의 네 곳(산사, 온천 마을 목욕탕, 바닷가 작은 역, 비 오는 골목 찻집)에
학생들이 모여 각자 집중 타이머를 돌린다. 실시간 연결 없이 25초마다 '여기 있어요' 신호를 보내 서로를 본다.
집중 시간은 서버가 잰 시간(focus_since)을 넘겨 인정하지 않는다."""
from datetime import date, datetime, timedelta

from flask import Blueprint, abort, flash, g, jsonify, redirect, render_template, request, url_for

from db import execute, get_db, query
from engagement import award
from security import audit, student_required, teacher_required

bp = Blueprint("rooms", __name__)

# key: (이름, 지역 느낌 한 줄, 남기는 글 이름, 남기는 글 안내, 소리)
PLACES = {
    "sanji": ("산사", "이끼 낀 돌계단 위, 바람과 먼 종소리", "에마", "소원판에 오늘의 다짐을 걸어 두세요", "wind"),
    "sento": ("목욕탕", "온천 마을 골목 끝, 굴뚝에서 김이 오르는 곳", "탈의실 칠판", "다 씻고 나가며 한 줄 남기기", "water"),
    "eki": ("바닷가 역", "하루 몇 번 기차가 서는 작은 무인역", "역 노트", "기다리는 동안 노트에 한 줄", "waves"),
    "kissa": ("골목 찻집", "비 오는 밤, 창가 자리가 비어 있는 찻집", "냅킨 메모", "냅킨에 적어 두고 가기", "rain"),
}
PRESENT_SECONDS = 70          # 이 시간 안에 신호가 있으면 '여기 있음'
PLAN_CHOICES = (25, 50, 90)
POINTS_PER_25 = 5
FOCUS_POINTS_DAILY_CAP = 40
NOTE_MAX = 60


def _place_or_404(place):
    if place not in PLACES:
        abort(404)
    return PLACES[place]


def _members(place):
    return query(f"""SELECT u.id, u.nickname, p.status, p.focus_since, p.plan_min,
                            (SELECT COALESCE(SUM(minutes), 0) FROM focus_logs f
                             WHERE f.user_id = u.id AND date(f.ended_at) = date('now', 'localtime')) AS today
                     FROM room_presence p JOIN users u ON u.id = p.user_id
                     WHERE p.place = ? AND p.last_seen >= datetime('now', 'localtime', '-{PRESENT_SECONDS} seconds')
                     ORDER BY p.status = 'focus' DESC, today DESC, u.nickname""", (place,))


def _counts():
    rows = query(f"""SELECT place, COUNT(*) AS n, SUM(status = 'focus') AS focus FROM room_presence
                     WHERE last_seen >= datetime('now', 'localtime', '-{PRESENT_SECONDS} seconds') GROUP BY place""")
    return {r["place"]: r for r in rows}


def _my_today(user_id):
    return query("""SELECT COALESCE(SUM(minutes), 0) AS m FROM focus_logs
                    WHERE user_id = ? AND date(ended_at) = date('now', 'localtime')""", (user_id,), one=True)["m"]


def _elapsed_min(since):
    if not since:
        return 0
    return int((datetime.now() - datetime.fromisoformat(since)).total_seconds() // 60)


def _member_json(m, me):
    return {"nick": m["nickname"] or "익명", "me": m["id"] == me, "status": m["status"],
            "elapsed": _elapsed_min(m["focus_since"]) if m["status"] == "focus" else 0,
            "plan": m["plan_min"], "today": m["today"]}


# ---------- 학생 ----------

@bp.route("/s/rooms")
@student_required
def rooms():
    today = date.today()
    monday = (today - timedelta(days=today.weekday())).isoformat()
    week = query("SELECT COALESCE(SUM(minutes), 0) AS m FROM focus_logs WHERE user_id = ? AND ended_at >= ?",
                 (g.user["id"], monday), one=True)["m"]
    return render_template("rooms/index.html", places=PLACES, counts=_counts(),
                           today=_my_today(g.user["id"]), week=week)


@bp.route("/s/rooms/<place>")
@student_required
def room(place):
    info = _place_or_404(place)
    # 들어오면 바로 '여기 있음'. 다른 장소에 있었다면 옮긴다(집중 중이던 시간은 버리지 않도록 화면에서 먼저 끝내게 한다)
    execute("""INSERT INTO room_presence (user_id, place, status) VALUES (?, ?, 'rest')
               ON CONFLICT(user_id) DO UPDATE SET place = excluded.place,
               status = CASE WHEN room_presence.place = excluded.place THEN room_presence.status ELSE 'rest' END,
               focus_since = CASE WHEN room_presence.place = excluded.place THEN room_presence.focus_since END,
               last_seen = datetime('now', 'localtime')""", (g.user["id"], place))
    me = query("SELECT * FROM room_presence WHERE user_id = ?", (g.user["id"],), one=True)
    notes = query("""SELECT n.id, n.body, n.created_at, u.nickname, n.user_id = ? AS mine FROM room_notes n
                     JOIN users u ON u.id = n.user_id WHERE n.place = ? ORDER BY n.created_at DESC LIMIT 40""",
                  (g.user["id"], place))
    return render_template("rooms/room.html", key=place, info=info, places=PLACES, me=me,
                           elapsed=_elapsed_min(me["focus_since"]) if me["status"] == "focus" else 0,
                           members=[_member_json(m, g.user["id"]) for m in _members(place)],
                           notes=notes, today=_my_today(g.user["id"]), plans=PLAN_CHOICES, note_max=NOTE_MAX)


@bp.route("/s/rooms/<place>/beat", methods=["POST"])
@student_required
def beat(place):
    _place_or_404(place)
    action = request.form.get("action", "")
    uid = g.user["id"]
    db = get_db()
    if action == "start":
        plan = request.form.get("plan", type=int)
        plan = plan if plan in PLAN_CHOICES else 25
        db.execute("""INSERT INTO room_presence (user_id, place, status, focus_since, plan_min)
                      VALUES (?, ?, 'focus', datetime('now', 'localtime'), ?)
                      ON CONFLICT(user_id) DO UPDATE SET place = excluded.place, status = 'focus',
                      focus_since = excluded.focus_since, plan_min = excluded.plan_min,
                      last_seen = datetime('now', 'localtime')""", (uid, place, plan))
    elif action == "leave":
        db.execute("DELETE FROM room_presence WHERE user_id = ?", (uid,))
    else:
        db.execute("""INSERT INTO room_presence (user_id, place) VALUES (?, ?)
                      ON CONFLICT(user_id) DO UPDATE SET place = excluded.place,
                      last_seen = datetime('now', 'localtime')""", (uid, place))
    db.commit()
    return jsonify(members=[_member_json(m, uid) for m in _members(place)], today=_my_today(uid))


@bp.route("/s/rooms/<place>/done", methods=["POST"])
@student_required
def done(place):
    """집중 끝(타이머 완료 또는 중간에 멈춤). 서버가 잰 시간까지만 기록한다."""
    _place_or_404(place)
    uid = g.user["id"]
    me = query("SELECT * FROM room_presence WHERE user_id = ? AND place = ?", (uid, place), one=True)
    if me is None or me["status"] != "focus":
        return jsonify(ok=False, minutes=0, points=0, today=_my_today(uid))
    asked = request.form.get("minutes", type=int) or 0
    minutes = max(0, min(asked, _elapsed_min(me["focus_since"]), me["plan_min"]))
    execute("UPDATE room_presence SET status = 'rest', focus_since = NULL, last_seen = datetime('now', 'localtime') "
            "WHERE user_id = ?", (uid,))
    points = 0
    if minutes >= 5:
        execute("INSERT INTO focus_logs (user_id, place, minutes) VALUES (?, ?, ?)", (uid, place, minutes))
        earned = query("""SELECT COALESCE(SUM(amount), 0) AS n FROM points WHERE user_id = ? AND reason LIKE '집중:%'
                          AND date(created_at) = date('now', 'localtime')""", (uid,), one=True)["n"]
        points = max(0, min((minutes // 25) * POINTS_PER_25, FOCUS_POINTS_DAILY_CAP - earned))
        if points:
            award(uid, points, f"집중: {PLACES[place][0]} {minutes}분")
    return jsonify(ok=True, minutes=minutes, points=points, today=_my_today(uid))


@bp.route("/s/rooms/<place>/note", methods=["POST"])
@student_required
def note(place):
    _place_or_404(place)
    body = " ".join(request.form.get("body", "").split())[:NOTE_MAX]
    if not body:
        flash("한 줄을 적어 주세요.", "error")
    elif query("""SELECT COUNT(*) AS n FROM room_notes WHERE user_id = ?
                  AND created_at >= datetime('now', 'localtime', '-1 day')""", (g.user["id"],), one=True)["n"] >= 5:
        flash("하루에 다섯 줄까지 남길 수 있어요.", "error")
    else:
        execute("INSERT INTO room_notes (place, user_id, body) VALUES (?, ?, ?)", (place, g.user["id"], body))
    return redirect(url_for("rooms.room", place=place) + "#notes")


@bp.route("/s/rooms/notes/<int:nid>/delete", methods=["POST"])
@student_required
def note_delete(nid):
    n = query("SELECT place FROM room_notes WHERE id = ? AND user_id = ?", (nid, g.user["id"]), one=True)
    if n is None:
        abort(404)
    execute("DELETE FROM room_notes WHERE id = ?", (nid,))
    return redirect(url_for("rooms.room", place=n["place"]) + "#notes")


# ---------- 선생님 ----------

@bp.route("/t/rooms")
@teacher_required
def t_rooms():
    now = {}
    for p in PLACES:
        now[p] = _members(p)
    week = query("""SELECT s.id AS sid, s.name, s.student_no, c.name AS class_name, SUM(f.minutes) AS m, COUNT(*) AS n
                    FROM focus_logs f JOIN users u ON u.id = f.user_id JOIN students s ON s.id = u.student_id
                    JOIN classes c ON c.id = s.class_id
                    WHERE f.ended_at >= date('now', 'localtime', '-6 days')
                    GROUP BY s.id ORDER BY m DESC LIMIT 100""")
    notes = query("""SELECT n.*, u.nickname, s.name FROM room_notes n JOIN users u ON u.id = n.user_id
                     LEFT JOIN students s ON s.id = u.student_id ORDER BY n.created_at DESC LIMIT 60""")
    return render_template("rooms/t_rooms.html", places=PLACES, now=now, week=week, notes=notes)


@bp.route("/t/rooms/notes/<int:nid>/delete", methods=["POST"])
@teacher_required
def t_note_delete(nid):
    execute("DELETE FROM room_notes WHERE id = ?", (nid,))
    audit("room_note_deleted", f"note:{nid}")
    flash("글을 지웠습니다.", "ok")
    return redirect(url_for("rooms.t_rooms"))
