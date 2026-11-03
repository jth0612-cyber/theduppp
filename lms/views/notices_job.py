"""공지 다시 알림: 공지를 올리고 5시간이 지났는데 아직 안 연 학생에게 한 번 더 휴대폰 알림을 보낸다.
앱이 켜져 있는 동안 10분마다 확인한다(별도 서비스 없이 앱 안에서 돈다)."""
import threading
import time

from db import execute, query

RENOTIFY_AFTER_HOURS = 5
CHECK_EVERY_SECONDS = 600


def renotify_due():
    """다시 알릴 때가 된 공지마다, 안 읽은 학생에게 알림. 보낸 공지 수를 돌려준다."""
    from views.pwa import notify_users
    rows = query(f"""SELECT * FROM notices WHERE renotified_at IS NULL
                     AND created_at <= datetime('now', 'localtime', '-{RENOTIFY_AFTER_HOURS} hours')
                     AND created_at >= datetime('now', 'localtime', '-2 days')""")
    for n in rows:
        unread = query("""SELECT u.id FROM users u JOIN students s ON s.id = u.student_id
                          WHERE s.class_id = ? AND s.active = 1 AND u.disabled = 0
                          AND u.id NOT IN (SELECT user_id FROM notice_reads WHERE notice_id = ?)""", (n["class_id"], n["id"]))
        if unread:
            notify_users([r["id"] for r in unread], "다시 알려요 · " + n["title"], n["body"], f"/s/notices/{n['id']}")
        execute("UPDATE notices SET renotified_at = datetime('now', 'localtime') WHERE id = ?", (n["id"],))
    return len(rows)


def start(app):
    def loop():
        while True:
            time.sleep(CHECK_EVERY_SECONDS)
            try:
                with app.app_context():
                    renotify_due()
            except Exception:  # noqa: BLE001 — 알림 실패가 앱을 멈추지 않게
                app.logger.exception("공지 다시 알림 실패")
    threading.Thread(target=loop, daemon=True, name="notice-renotify").start()
