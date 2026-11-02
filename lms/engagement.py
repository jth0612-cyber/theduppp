"""학생 접속 기록(연속 학습일)."""
from datetime import date, timedelta

from db import get_db, query


def record_visit(user_id):
    """오늘 첫 접속이면 기록한다."""
    db = get_db()
    db.execute("INSERT OR IGNORE INTO visits (user_id, day) VALUES (?, ?)", (user_id, date.today().isoformat()))
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
