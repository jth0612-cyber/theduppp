"""함께 공부하는 장소: 일본 소도시의 네 곳(신사, 눈 내리는 노천탕, 바닷가 작은 역, 비 오는 골목 찻집)에
학생들이 모여 각자 집중 타이머를 돌린다. 실시간 연결 없이 25초마다 '여기 있어요' 신호를 보내 서로를 본다.
집중 시간은 서버가 잰 시간(focus_since)을 넘겨 인정하지 않는다."""
from datetime import date, datetime, timedelta

from flask import Blueprint, abort, flash, g, jsonify, redirect, render_template, request, url_for

from db import execute, get_db, query
from security import audit, student_required, staff_required, teacher_only, teacher_required
from wordfilter import bad_word

bp = Blueprint("rooms", __name__)

# key: (이름, 지역 느낌 한 줄, 남기는 글 이름, 남기는 글 안내, 소리)
PLACES = {
    "sanji": ("신사(神社)", "본당 방석 24개 · 오늘의 운세, 소원판", "에마", "소원판에 오늘의 다짐을 걸어 두세요", "wind"),
    "sento": ("노천탕", "탕 자리 8개, 화롯가 방석 4개 · 화롯가 칠판", "휴게소 칠판", "몸 녹이고 나가며 한 줄 남기기", "water"),
    "eki": ("바닷가 역", "승강장 의자 · 3분마다 열차가 지나가요 · 역 노트", "역 노트", "기차를 기다리며 노트에 한 줄", "waves"),
    "kissa": ("골목 찻집", "창가·바 자리, 다다미방 · 늘 비 오는 저녁", "냅킨 메모", "냅킨에 적어 두고 가기", "rain"),
}
# 장소 카드의 여행 포스터: 세로 일본어 이름, 영어 이름
POSTER = {"sanji": ("神社", "SHRINE"), "sento": ("露天風呂", "OPEN-AIR BATH"), "eki": ("汐見浜駅", "SEASIDE STATION"),
          "kissa": ("喫茶 雨音", "ALLEY CAFÉ")}
ENTER_TEXT = {"sanji": "신사에 들어가기", "sento": "온천에 들어가기", "eki": "역으로 올라가기", "kissa": "찻집 문 열기"}
# 3D 장소 안 판(칠판·역 노트)에 학생 글을 띄우는 곳
#  chat : 정해진 자리에 앉은 학생만 짧게 쓰는 칠판 (노천탕 화롯가 방석 8~11번)
#  notes: 그 장소에 남기는 글(하루 5줄)을 판에 보여 준다
BOARDS = {"sento": {"kind": "chat", "seats": {8, 9, 10, 11}, "max": 40},
          "eki": {"kind": "notes", "max": 40}}
BOARD_LINES = 5
CHAT_GAP_SECONDS = 4
CHAT_DAY_MAX = 60
# 오늘의 운세: (운, 한마디, 오늘의 미션(플래너에 넣을 수 있음), 과목 칩, 행운 부적 색, 부적 이름)
FORTUNES = [
    ("아주 좋음", "오늘 푼 문제가 시험에 그대로 나올 것 같은 날이에요. 어려운 단원도 오늘은 술술 풀려요.", "제일 자신 없는 단원 기출 5문제", "sci", "#e2ae25", "금빛 부적"),
    ("아주 좋음", "자료 해석에 강한 하루예요. 그래프와 표가 눈에 쏙쏙 들어와요.", "그래프·표 해석 문제 10개", "sci", "#e2ae25", "금빛 부적"),
    ("좋음", "틀린 문제 하나가 큰 깨달음이 되는 날이에요. 오답 노트를 펼쳐 보세요.", "오답 노트 3문제 다시 풀기", "sci", "#e0708a", "벚꽃 부적"),
    ("좋음", "모르는 건 바로 묻는 날! 질문 하나가 막힌 길을 열어 줘요.", "막힌 문제 1개 질답 게시판에 올리기", "sci", "#e0708a", "벚꽃 부적"),
    ("좋음", "암기가 잘 되는 날이에요. 짧게 여러 번 보는 게 좋아요.", "개념 카드 한 바퀴 돌리기", "sci", "#4b8fd6", "하늘 부적"),
    ("보통", "한 단원만 끝까지 해내면 충분한 날이에요. 작은 완주가 큰 힘이 돼요.", "한 단원 끝까지 풀기", "sci", "#5fa865", "잎새 부적"),
    ("보통", "25분만 집중해도 잘한 날이에요. 타이머부터 켜 보세요.", "25분 집중 두 번", "etc", "#5fa865", "잎새 부적"),
    ("조금 아쉬움", "오늘은 조금 지칠 수 있어요. 천천히 가도 멈추지만 않으면 돼요. 내일은 더 좋아요!", "쉬운 문제 10개로 몸 풀기", "sci", "#9673d4", "보랏빛 부적"),
]
LOW_LUCK = "조금 아쉬움"
PRESENT_SECONDS = 70          # 이 시간 안에 신호가 있으면 '여기 있음'
PLAN_CHOICES = (25, 50, 90)
NOTE_MAX = 60
# 3D 장소 (나머지는 그림 버전)
PLACES_3D = set(PLACES)
POSES = {"stand", "walk", "sit", "gassho", "bow", "breathe"}
AVATAR_COLORS = ["#e8805c", "#e6a23c", "#7cb87a", "#5fa3c9", "#9b86d1", "#d97aa0", "#8c7a6b", "#4f9e94"]


def _place_or_404(place):
    if place not in PLACES:
        abort(404)
    return PLACES[place]


def _members(place):
    return query(f"""SELECT u.id, u.nickname, u.avatar_color, p.status, p.focus_since, p.plan_min,
                            p.px, p.pz, p.ry, p.pose, p.seat,
                            (SELECT idx FROM room_fortunes rf WHERE rf.user_id = u.id AND rf.day = date('now', 'localtime')) AS fortune,
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


def _member_json(m, me, king=None, follows=()):
    return {"id": m["id"], "nick": m["nickname"] or "익명", "me": m["id"] == me, "status": m["status"],
            "king": m["id"] == king, "follow": m["id"] in follows,
            "charm": FORTUNES[m["fortune"]][4] if m["fortune"] is not None and m["fortune"] < len(FORTUNES) else None,
            "elapsed": _elapsed_min(m["focus_since"]) if m["status"] == "focus" else 0,
            "plan": m["plan_min"], "today": m["today"],
            "x": round(m["px"], 2), "z": round(m["pz"], 2), "ry": round(m["ry"], 2), "pose": m["pose"],
            "seat": m["seat"], "color": m["avatar_color"] or AVATAR_COLORS[m["id"] % len(AVATAR_COLORS)]}


def _pos_args():
    """브라우저가 보낸 위치·자세. 이상한 값은 버린다."""
    def num(name, lo, hi):
        v = request.form.get(name, type=float)
        return None if v is None or v != v else max(lo, min(hi, v))
    pose = request.form.get("pose")
    seat = request.form.get("seat", type=int)
    return num("x", -40, 40), num("z", -40, 40), num("ry", -7, 7), pose if pose in POSES else None, \
        seat if seat is not None and 0 <= seat < 200 else None


# ---------- 터줏대감 순위 (장소별 집중 시간) ----------
PERIODS = {"week": "이번 주", "month": "이번 달", "all": "전체"}


def _since(period):
    today = date.today()
    if period == "week":
        return (today - timedelta(days=today.weekday())).isoformat()
    if period == "month":
        return today.replace(day=1).isoformat()
    return "0000"


def _ranking(place, since, ids=None, limit=10):
    """장소에서 since 이후 집중한 시간이 많은 학생 순. ids 를 주면 그 학생들만(팔로잉 순위)."""
    extra, args = "", [place, since]
    if ids is not None:
        ids = list(ids) or [0]
        extra = f" AND u.id IN ({','.join('?' * len(ids))})"
        args += ids
    rows = query(f"""SELECT u.id, u.nickname, u.avatar_color, SUM(f.minutes) AS m, MIN(f.ended_at) AS first
                     FROM focus_logs f JOIN users u ON u.id = f.user_id
                     WHERE f.place = ? AND f.ended_at >= ? AND u.role = 'student' AND u.disabled = 0{extra}
                     GROUP BY u.id ORDER BY m DESC, first LIMIT ?""", args + [limit])
    return [dict(r, rank=i + 1) for i, r in enumerate(rows)]


def _my_rank(place, since, uid):
    mine = query("SELECT COALESCE(SUM(minutes), 0) AS m FROM focus_logs WHERE place = ? AND ended_at >= ? AND user_id = ?",
                 (place, since, uid), one=True)["m"]
    if not mine:
        return {"m": 0, "rank": None}
    ahead = query("""SELECT COUNT(*) AS n FROM (SELECT f.user_id FROM focus_logs f JOIN users u ON u.id = f.user_id
                     WHERE f.place = ? AND f.ended_at >= ? AND u.role = 'student' AND u.disabled = 0
                     GROUP BY f.user_id HAVING SUM(f.minutes) > ?)""", (place, since, mine), one=True)["n"]
    return {"m": mine, "rank": ahead + 1}


def _king(place):
    """이번 주 이 장소의 터줏대감(1위) user id."""
    top = _ranking(place, _since("week"), limit=1)
    return top[0]["id"] if top else None


def _following(uid):
    return {r["followee_id"] for r in query("SELECT followee_id FROM follows WHERE follower_id = ?", (uid,))}


@bp.app_template_filter("avatar_cls")
def avatar_cls(color):
    return f"sw-{AVATAR_COLORS.index(color) if color in AVATAR_COLORS else 6}"


@bp.app_template_filter("hm")
def hm(minutes):
    minutes = int(minutes or 0)
    if minutes < 60:
        return f"{minutes}분"
    h, m = divmod(minutes, 60)
    return f"{h}시간 {m}분" if m else f"{h}시간"


# ---------- 학생 ----------

@bp.route("/s/rooms")
@student_required
def rooms():
    today = date.today()
    monday = (today - timedelta(days=today.weekday())).isoformat()
    week = query("SELECT COALESCE(SUM(minutes), 0) AS m FROM focus_logs WHERE user_id = ? AND ended_at >= ?",
                 (g.user["id"], monday), one=True)["m"]
    kings = {p: (_ranking(p, _since("week"), limit=1) or [None])[0] for p in PLACES}
    return render_template("rooms/index.html", places=PLACES, counts=_counts(),
                           today=_my_today(g.user["id"]), week=week, kings=kings, poster=POSTER)


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
    tpl = "rooms/room3d.html" if place in PLACES_3D and request.args.get("flat") != "1" else "rooms/room.html"
    my_color = query("SELECT avatar_color FROM users WHERE id = ?", (g.user["id"],), one=True)["avatar_color"]
    king, follows = _king(place), _following(g.user["id"])
    return render_template(tpl, key=place, info=info, places=PLACES, me=me, colors=AVATAR_COLORS,
                           my_color=my_color or AVATAR_COLORS[g.user["id"] % len(AVATAR_COLORS)],
                           elapsed=_elapsed_min(me["focus_since"]) if me["status"] == "focus" else 0,
                           members=[_member_json(m, g.user["id"], king, follows) for m in _members(place)],
                           rank=_ranking(place, _since("week"), limit=5), my_rank=_my_rank(place, _since("week"), g.user["id"]),
                           notes=notes, today=_my_today(g.user["id"]), plans=PLAN_CHOICES, note_max=NOTE_MAX,
                           enter_text=ENTER_TEXT.get(place, "들어가기"), follows=follows,
                           board_on=place in BOARDS)


@bp.route("/s/rooms/rank")
@student_required
def rank():
    place = request.args.get("place", "sanji")
    _place_or_404(place)
    period = request.args.get("period", "week")
    period = period if period in PERIODS else "week"
    scope = "follow" if request.args.get("scope") == "follow" else "all"
    uid = g.user["id"]
    follows = _following(uid)
    since = _since(period)
    rows = _ranking(place, since, ids=(follows | {uid}) if scope == "follow" else None, limit=30)
    return render_template("rooms/rank.html", places=PLACES, place=place, period=period, scope=scope,
                           periods=PERIODS, rows=rows, follows=follows, me=uid, my_rank=_my_rank(place, since, uid))


def _safe_next(default):
    nxt = request.form.get("next", "")
    return nxt if nxt.startswith("/s/") and "//" not in nxt else default


@bp.route("/s/follow/<int:uid>", methods=["POST"])
@student_required
def follow(uid):
    me = g.user["id"]
    target = query("SELECT id, nickname FROM users WHERE id = ? AND role = 'student' AND disabled = 0", (uid,), one=True)
    if target is None or uid == me:
        abort(404)
    if query("SELECT 1 FROM follows WHERE follower_id = ? AND followee_id = ?", (me, uid), one=True):
        execute("DELETE FROM follows WHERE follower_id = ? AND followee_id = ?", (me, uid))
        flash(f"{target['nickname']}님 팔로우를 그만뒀어요.", "ok")
    else:
        execute("INSERT INTO follows (follower_id, followee_id) VALUES (?, ?)", (me, uid))
        flash(f"{target['nickname']}님을 팔로우했어요.", "ok")
    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify(ok=True, following=uid in _following(me))
    return redirect(_safe_next(url_for("rooms.friends")))


def _friend_rows(sql, args, me):
    since = _since("week")
    rows = query(f"""SELECT u.id, u.nickname, u.avatar_color, p.place, p.status,
                            p.last_seen >= datetime('now', 'localtime', '-{PRESENT_SECONDS} seconds') AS here,
                            (SELECT COALESCE(SUM(minutes), 0) FROM focus_logs f WHERE f.user_id = u.id
                             AND date(f.ended_at) = date('now', 'localtime')) AS today,
                            (SELECT COALESCE(SUM(minutes), 0) FROM focus_logs f WHERE f.user_id = u.id
                             AND f.ended_at >= ?) AS week
                     FROM users u LEFT JOIN room_presence p ON p.user_id = u.id
                     WHERE u.role = 'student' AND u.disabled = 0 AND {sql}
                     ORDER BY here DESC, today DESC, u.nickname""", [since] + list(args))
    return rows


@bp.route("/s/friends")
@student_required
def friends():
    me = g.user["id"]
    q = request.args.get("q", "").strip()[:20]
    following = _friend_rows("u.id IN (SELECT followee_id FROM follows WHERE follower_id = ?)", (me,), me)
    followers = _friend_rows("u.id IN (SELECT follower_id FROM follows WHERE followee_id = ?)", (me,), me)
    esc = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    found = _friend_rows("u.nickname LIKE ? ESCAPE '\\' AND u.id != ?", (f"%{esc}%", me), me)[:10] if len(q) >= 2 else []
    return render_template("rooms/friends.html", following=following, followers=followers, found=found, q=q,
                           follows=_following(me), places=PLACES)


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
    x, z, ry, pose, seat = _pos_args()
    if x is not None and z is not None and action != "leave":
        db.execute("UPDATE room_presence SET px = ?, pz = ?, ry = COALESCE(?, ry), pose = COALESCE(?, pose), seat = ? "
                   "WHERE user_id = ?", (x, z, ry, pose, seat, uid))
    color = request.form.get("color")
    if color in AVATAR_COLORS:
        db.execute("UPDATE users SET avatar_color = ? WHERE id = ?", (color, uid))
    db.commit()
    king, follows = _king(place), _following(uid)
    return jsonify(members=[_member_json(m, uid, king, follows) for m in _members(place)], today=_my_today(uid),
                   board=_board(place))


@bp.route("/s/rooms/<place>/done", methods=["POST"])
@student_required
def done(place):
    """집중 끝(타이머 완료 또는 중간에 멈춤). 서버가 잰 시간까지만 기록한다."""
    _place_or_404(place)
    uid = g.user["id"]
    me = query("SELECT * FROM room_presence WHERE user_id = ? AND place = ?", (uid, place), one=True)
    if me is None or me["status"] != "focus":
        return jsonify(ok=False, minutes=0, today=_my_today(uid))
    asked = request.form.get("minutes", type=int) or 0
    minutes = max(0, min(asked, _elapsed_min(me["focus_since"]), me["plan_min"]))
    execute("UPDATE room_presence SET status = 'rest', focus_since = NULL, last_seen = datetime('now', 'localtime') "
            "WHERE user_id = ?", (uid,))
    if minutes >= 5:
        execute("INSERT INTO focus_logs (user_id, place, minutes) VALUES (?, ?, ?)", (uid, place, minutes))
    return jsonify(ok=True, minutes=minutes, today=_my_today(uid))


def _board(place):
    """장소 안 판에 띄울 최근 글 (오래된 것부터)."""
    b = BOARDS.get(place)
    if b is None:
        return None
    if b["kind"] == "chat":
        rows = query("""SELECT c.id, c.body, u.nickname FROM room_chat c JOIN users u ON u.id = c.user_id
                        WHERE c.place = ? AND date(c.created_at) = date('now', 'localtime')
                        ORDER BY c.id DESC LIMIT ?""", (place, BOARD_LINES))
    else:
        rows = query("""SELECT n.id, n.body, u.nickname FROM room_notes n JOIN users u ON u.id = n.user_id
                        WHERE n.place = ? ORDER BY n.created_at DESC, n.id DESC LIMIT ?""", (place, BOARD_LINES))
    return [{"id": r["id"], "nick": r["nickname"] or "익명", "body": r["body"]} for r in reversed(rows)]


def _fortune_json(idx, again, tied):
    luck, text, mission, subject, color, charm = FORTUNES[idx]
    return {"luck": luck, "text": text, "mission": mission, "subject": subject, "color": color, "charm": charm,
            "low": luck == LOW_LUCK, "again": again, "tied": bool(tied), "day": date.today().isoformat()}


@bp.route("/s/rooms/fortune", methods=["POST"])
@student_required
def fortune():
    """오늘의 운세 뽑기: 하루에 한 번. 뽑으면 오늘 하루 캐릭터에 행운 부적이 달리고, 오늘의 미션을 플래너에 넣을 수 있다."""
    import random
    uid, day = g.user["id"], date.today().isoformat()
    row = query("SELECT * FROM room_fortunes WHERE user_id = ? AND day = ?", (uid, day), one=True)
    if row:
        return jsonify(_fortune_json(row["idx"] % len(FORTUNES), True, row["tied"]))
    idx = random.randrange(len(FORTUNES))
    execute("INSERT INTO room_fortunes (user_id, day, idx) VALUES (?, ?, ?)", (uid, day, idx))
    return jsonify(_fortune_json(idx, False, 0))


@bp.route("/s/rooms/fortune/tie", methods=["POST"])
@student_required
def fortune_tie():
    """아쉬운 운세는 종이를 줄에 묶어 두고 간다(묶어 둔 사람 수가 판에 보인다)."""
    execute("UPDATE room_fortunes SET tied = 1 WHERE user_id = ? AND day = ?", (g.user["id"], date.today().isoformat()))
    n = query("SELECT COUNT(*) AS n FROM room_fortunes WHERE day = ? AND tied = 1", (date.today().isoformat(),), one=True)["n"]
    return jsonify(ok=True, tied_today=n)


@bp.route("/s/rooms/<place>/write", methods=["POST"])
@student_required
def write(place):
    """3D 화면 안에서 판에 한 줄 쓰기."""
    _place_or_404(place)
    b = BOARDS.get(place)
    if b is None:
        abort(404)
    uid = g.user["id"]
    body = " ".join(request.form.get("body", "").split())[:b["max"]]

    def fail(msg):
        return jsonify(ok=False, error=msg, board=_board(place))
    if not body:
        return fail("한 줄을 적어 주세요.")
    if bad_word(body):
        return fail("다른 친구들도 보는 곳이에요. 바른 말로 적어 주세요.")
    if b["kind"] == "chat":
        me = query(f"""SELECT seat FROM room_presence WHERE user_id = ? AND place = ?
                       AND last_seen >= datetime('now', 'localtime', '-{PRESENT_SECONDS} seconds')""", (uid, place), one=True)
        if me is None or me["seat"] not in b["seats"]:
            return fail("화롯가 방석에 앉은 사람만 칠판에 쓸 수 있어요.")
        last = query("SELECT created_at FROM room_chat WHERE user_id = ? ORDER BY id DESC LIMIT 1", (uid,), one=True)
        if last and (datetime.now() - datetime.fromisoformat(last["created_at"])).total_seconds() < CHAT_GAP_SECONDS:
            return fail("조금 천천히 적어 주세요.")
        if query("""SELECT COUNT(*) AS n FROM room_chat WHERE user_id = ?
                    AND date(created_at) = date('now', 'localtime')""", (uid,), one=True)["n"] >= CHAT_DAY_MAX:
            return fail("오늘은 칠판에 충분히 적었어요. 내일 또 만나요.")
        execute("INSERT INTO room_chat (place, user_id, body) VALUES (?, ?, ?)", (place, uid, body))
    else:
        if query("""SELECT COUNT(*) AS n FROM room_notes WHERE user_id = ?
                    AND created_at >= datetime('now', 'localtime', '-1 day')""", (uid,), one=True)["n"] >= 5:
            return fail("하루에 다섯 줄까지 남길 수 있어요.")
        execute("INSERT INTO room_notes (place, user_id, body) VALUES (?, ?, ?)", (place, uid, body))
    return jsonify(ok=True, board=_board(place))


@bp.route("/s/rooms/<place>/note", methods=["POST"])
@student_required
def note(place):
    _place_or_404(place)
    body = " ".join(request.form.get("body", "").split())[:NOTE_MAX]
    if not body:
        flash("한 줄을 적어 주세요.", "error")
    elif bad_word(body):
        flash("다른 친구들도 보는 곳이에요. 바른 말로 적어 주세요.", "error")
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
@staff_required
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
    chat = query("""SELECT c.*, u.nickname, s.name FROM room_chat c JOIN users u ON u.id = c.user_id
                    LEFT JOIN students s ON s.id = u.student_id ORDER BY c.id DESC LIMIT 60""")
    return render_template("rooms/t_rooms.html", places=PLACES, now=now, week=week, notes=notes, chat=chat)


@bp.route("/t/rooms/chat/<int:cid>/delete", methods=["POST"])
@staff_required
def t_chat_delete(cid):
    execute("DELETE FROM room_chat WHERE id = ?", (cid,))
    audit("room_chat_delete", f"chat:{cid}")
    flash("칠판 글을 지웠습니다.", "ok")
    return redirect(url_for("rooms.t_rooms"))


@bp.route("/t/rooms/notes/<int:nid>/delete", methods=["POST"])
@staff_required
def t_note_delete(nid):
    execute("DELETE FROM room_notes WHERE id = ?", (nid,))
    audit("room_note_deleted", f"note:{nid}")
    flash("글을 지웠습니다.", "ok")
    return redirect(url_for("rooms.t_rooms"))
