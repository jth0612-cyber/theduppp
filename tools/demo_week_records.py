"""4차 토론 1, 2번: 데모 DB 손보기.  사용: python d4data.py <lms.sqlite3 경로>
1) 출결: '출석'인데 등원 시각이 수업 시작보다 50분대 뒤로 찍힌 것(시 빼기를 빠뜨린 생성 오류)을 한 시간 앞으로.
2) 같은 반 학생들의 이번 주 학습 기록(게임, 집중, 직접 측정)을 넣어 순위에 차이가 보이게. 다시 돌려도 겹쳐 쌓이지 않는다."""
import json, random, sqlite3, sys
from datetime import date, datetime, timedelta

db = sqlite3.connect(sys.argv[1], timeout=20); db.row_factory = sqlite3.Row
TAG = '{"demo4": 1}'                                             # 이 스크립트가 넣은 게임 기록 표시 (payload)

# ---- 1) 출결 등원 시각
n_fix = 0
for r in db.execute("SELECT id, data FROM sys_rows WHERE tbl = '출결'").fetchall():
    d = json.loads(r["data"]); t = str(d.get("도착시각", ""))
    if d.get("출결") == "출석" and len(t) == 5 and t[2] == ":" and int(t[3:]) >= 50:
        d["도착시각"] = f"{int(t[:2]) - 1:02d}:{t[3:]}"
        db.execute("UPDATE sys_rows SET data = ? WHERE id = ?", (json.dumps(d, ensure_ascii=False), r["id"])); n_fix += 1

# ---- 2) 이번 주 학습 기록
db.execute("DELETE FROM game_rounds WHERE payload = ?", (TAG,))
db.execute("DELETE FROM focus_logs WHERE ended_at LIKE '%:07'")          # 이 스크립트가 넣은 것은 초를 07 로 둔다
db.execute("DELETE FROM timer_logs WHERE ended_at LIKE '%:07'")      # 이 스크립트가 넣은 것은 초를 07 로 둔다
today = date.today(); monday = today - timedelta(days=today.weekday())
days = [monday + timedelta(days=i) for i in range((today - monday).days + 1)]
places = [r[0] for r in db.execute("SELECT DISTINCT place FROM focus_logs")] or ["sento"]
GAMES = [("sci_speed", "", 20, (9, 34)), ("vocab_speed", "", 20, (10, 30)), ("mixed", "", 10, (3, 10)), ("chargaff", "", 5, (1, 5)),
         ("vocab_match", "", 20, (11, 20)), ("play_shell", "", 6, (2, 6)), ("play_redox", "", 6, (2, 6)), ("play_neutral", "", 6, (1, 6)), ("dna", "dna", 8, (3, 8))]
n_g = n_f = n_t = 0
users = db.execute("""SELECT u.id, u.username, s.class_id FROM users u JOIN students s ON s.id = u.student_id
                      JOIN classes c ON c.id = s.class_id WHERE u.role = 'student' AND c.is_test = 0""").fetchall()
for u in users:
    rng = random.Random(u["id"] * 7919)
    effort = rng.choice((0.4, 0.6, 0.8, 1.0, 1.2, 1.5))             # 학생마다 꾸준함이 다르게
    for g, topic, total, (lo, hi) in GAMES:
        if rng.random() > 0.55 * min(effort, 1.2) + 0.2:
            continue
        for _ in range(rng.randint(1, 3)):
            d = rng.choice(days); at = datetime(d.year, d.month, d.day, rng.randint(16, 22), rng.randint(0, 59), 7)
            score = rng.randint(lo, hi)
            tot = score + rng.randint(0, 6) if g.endswith("speed") else total      # 스피드는 푼 만큼이 분모
            db.execute("""INSERT INTO game_rounds (user_id, game, topic, payload, answer, score, total, started_at, finished_at, last_at, active_sec)
                          VALUES (?, ?, ?, ?, '[]', ?, ?, ?, ?, ?, ?)""",
                       (u["id"], g, topic, TAG, score, tot, at.isoformat(" "), (at + timedelta(minutes=3)).isoformat(" "),
                        (at + timedelta(minutes=3)).isoformat(" "), rng.randint(60, 240)))
            n_g += 1
    for d in days:
        if rng.random() < 0.5 * effort:
            at = datetime(d.year, d.month, d.day, rng.randint(18, 23), rng.randint(0, 59), 7)
            db.execute("INSERT INTO focus_logs (user_id, place, minutes, ended_at) VALUES (?, ?, ?, ?)", (u["id"], rng.choice(places), rng.choice((25, 40, 50, 60, 80)), at.isoformat(" ")))
            n_f += 1
        if rng.random() < 0.3 * effort:
            at = datetime(d.year, d.month, d.day, rng.randint(14, 22), rng.randint(0, 59), 7)
            db.execute("INSERT INTO timer_logs (user_id, seconds, ended_at) VALUES (?, ?, ?)", (u["id"], rng.randint(900, 5400), at.isoformat(" ")))
            n_t += 1
db.commit()
try:
    db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
except sqlite3.OperationalError:
    pass
print(f"출결 시각 {n_fix}건, 게임 {n_g}판, 집중 {n_f}건, 직접 측정 {n_t}건, 학생 {len(users)}명")
