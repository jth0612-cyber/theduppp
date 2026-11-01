"""학생 동기 부여: 접속 기록(연속 학습일)과 포인트."""
from datetime import date, timedelta

from db import execute, get_db, query

VISIT_POINTS = 10
GAME_POINTS_DAILY_CAP = 50  # 미니게임으로 하루에 받을 수 있는 최대 포인트


def record_visit(user_id):
    """오늘 첫 접속이면 기록하고 접속 포인트를 준다."""
    today = date.today().isoformat()
    db = get_db()
    cur = db.execute("INSERT OR IGNORE INTO visits (user_id, day) VALUES (?, ?)", (user_id, today))
    if cur.rowcount:
        db.execute("INSERT INTO points (user_id, amount, reason) VALUES (?, ?, '접속 포인트')",
                   (user_id, VISIT_POINTS))
    db.commit()


def streak_info(user_id):
    days = {r["day"] for r in query("SELECT day FROM visits WHERE user_id = ?", (user_id,))}
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    week = [{"label": "월화수목금토일"[i], "done": (monday + timedelta(days=i)).isoformat() in days,
             "today": monday + timedelta(days=i) == today} for i in range(7)]
    streak, d = 0, today
    while d.isoformat() in days:
        streak += 1
        d -= timedelta(days=1)
    return {"total": len(days), "streak": streak, "week": week}


def award(user_id, amount, reason):
    execute("INSERT INTO points (user_id, amount, reason) VALUES (?, ?, ?)", (user_id, amount, reason))


def balance(user_id):
    return query("SELECT COALESCE(SUM(amount), 0) AS n FROM points WHERE user_id = ?", (user_id,), one=True)["n"]


def game_points_today(user_id):
    return query("""SELECT COALESCE(SUM(amount), 0) AS n FROM points
                    WHERE user_id = ? AND reason LIKE '게임:%' AND date(created_at) = date('now', 'localtime')""",
                 (user_id,), one=True)["n"]


def award_game_points(user_id, amount, reason):
    """일일 상한을 넘지 않게 지급하고 실제 지급액을 반환."""
    amount = max(0, min(amount, GAME_POINTS_DAILY_CAP - game_points_today(user_id)))
    if amount:
        award(user_id, amount, f"게임: {reason}")
    return amount
