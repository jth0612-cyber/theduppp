"""내 공부: 공부 시간·푼 문제·연속 학습, 주간 공부 순위, 일별 이용 시간, 학습 진도.

공부 시간 = 직접 잰 시간(timer_logs) + 소도시 명상 집중 기록(focus_logs) + 퀴즈·게임을 실제로 푼 시간(game_rounds.active_sec).
직접 잰 시간은 일별 그래프와 순위에서 '집중'에 넣는다.
일별 이용 시간은 '집중 / 통과 Quiz / 영단어' 세 가지로 나눈다.
학습 진도: TOPIC마다 진술 문장 중 마지막으로 맞힌 것의 비율. 초기화하면 그 뒤에 푼 것만 센다."""
import json
from datetime import date, datetime, timedelta

from db import execute, query

KINDS = (("focus", "집중"), ("quiz", "통과 Quiz"), ("vocab", "영단어"))


def _kind(game):
    return "vocab" if game.startswith("vocab") else "quiz"


def _solved(r):
    picks = json.loads(r["picks"] or "null")
    if isinstance(picks, list):
        return sum(1 for p in picks if p is not None)
    return (r["total"] or 0) if r["finished_at"] else 0


def week_start(today=None):
    today = today or date.today()
    return today - timedelta(days=today.weekday())


# ---------------------------------------------------------------- 하루 단위 집계
def daily(uid, days=7):
    """최근 days일 [{day, focus, quiz, vocab, total}] (분)."""
    today = date.today()
    first = today - timedelta(days=days - 1)
    out = {(first + timedelta(days=i)).isoformat(): {"focus": 0, "quiz": 0, "vocab": 0} for i in range(days)}
    for r in query("""SELECT date(ended_at) AS d, SUM(minutes) AS m FROM focus_logs
                      WHERE user_id = ? AND ended_at >= ? GROUP BY d""", (uid, first.isoformat())):
        if r["d"] in out:
            out[r["d"]]["focus"] += r["m"] or 0
    sec = {}
    for r in query("""SELECT date(ended_at) AS d, SUM(seconds) AS s FROM timer_logs
                      WHERE user_id = ? AND ended_at >= ? GROUP BY d""", (uid, first.isoformat())):
        if r["d"] in out:
            sec[(r["d"], "focus")] = r["s"] or 0
    for r in query("""SELECT date(started_at) AS d, game, SUM(active_sec) AS s FROM game_rounds
                      WHERE user_id = ? AND started_at >= ? GROUP BY d, game""", (uid, first.isoformat())):
        if r["d"] in out:
            k = (r["d"], _kind(r["game"]))
            sec[k] = sec.get(k, 0) + (r["s"] or 0)
    for (d, k), s in sec.items():
        out[d][k] += round(s / 60)
    return [dict(v, day=d, total=v["focus"] + v["quiz"] + v["vocab"]) for d, v in out.items()]


def class_average(days=7):
    """그날 공부 기록이 있는 학생들의 평균 공부 시간(분). {day: 분}"""
    first = (date.today() - timedelta(days=days - 1)).isoformat()
    per = {}
    for r in query("""SELECT f.user_id AS u, date(f.ended_at) AS d, SUM(f.minutes) AS m FROM focus_logs f
                      JOIN users x ON x.id = f.user_id AND x.role = 'student'
                      WHERE f.ended_at >= ? GROUP BY u, d""", (first,)):
        per[(r["u"], r["d"])] = per.get((r["u"], r["d"]), 0) + (r["m"] or 0)
    for r in query("""SELECT gr.user_id AS u, date(gr.started_at) AS d, SUM(gr.active_sec) AS s FROM game_rounds gr
                      JOIN users x ON x.id = gr.user_id AND x.role = 'student'
                      WHERE gr.started_at >= ? GROUP BY u, d""", (first,)):
        per[(r["u"], r["d"])] = per.get((r["u"], r["d"]), 0) + (r["s"] or 0) / 60
    for r in query("""SELECT t.user_id AS u, date(t.ended_at) AS d, SUM(t.seconds) AS s FROM timer_logs t
                      JOIN users x ON x.id = t.user_id AND x.role = 'student'
                      WHERE t.ended_at >= ? GROUP BY u, d""", (first,)):
        per[(r["u"], r["d"])] = per.get((r["u"], r["d"]), 0) + (r["s"] or 0) / 60
    by_day = {}
    for (u, d), m in per.items():
        if m >= 1:
            by_day.setdefault(d, []).append(m)
    return {d: round(sum(v) / len(v)) for d, v in by_day.items()}


def today_summary(uid):
    """오늘 공부 시간(분, 초), 종류별 초, 돌고 있는 타이머, 오늘 푼 문제 수, 연속 학습 일수."""
    today = date.today().isoformat()
    day = daily(uid, 1)[0]
    solved = sum(_solved(r) for r in query("""SELECT picks, total, finished_at FROM game_rounds
                                               WHERE user_id = ? AND started_at >= ?""", (uid, today)))
    one = lambda sql: query(sql, (uid, today), one=True)["s"] or 0
    game = {"quiz": 0, "vocab": 0}
    for r in query("SELECT game, SUM(active_sec) AS s FROM game_rounds WHERE user_id = ? AND started_at >= ? GROUP BY game", (uid, today)):
        game[_kind(r["game"])] += r["s"] or 0
    parts = [("직접 측정", one("SELECT SUM(seconds) AS s FROM timer_logs WHERE user_id = ? AND ended_at >= ?")),
             ("소도시 명상", 60 * one("SELECT SUM(minutes) AS s FROM focus_logs WHERE user_id = ? AND ended_at >= ?")),
             ("통과 Quiz", game["quiz"]), ("영단어", game["vocab"])]
    return {"minutes": day["total"], "seconds": sum(s for _, s in parts), "parts": parts,
            "running": timer_elapsed(uid), "timer_max": TIMER_MAX_SEC, "solved": solved, "streak": streak(uid)}


# ---------------------------------------------------------------- 직접 재는 타이머 (서버가 잰 시간만 인정)
TIMER_MIN_SEC = 1             # 최소 제한 없음 (사용자 결정, 2026-11-27). 0초만 남기지 않는다
TIMER_MAX_SEC = 100 * 60      # 한 번에 100분까지 (사용자 결정, 2026-11-27. 소도시 명상의 가장 긴 집중 시간과 같다)


def timer_elapsed(uid):
    """돌고 있는 타이머가 지금까지 잰 초 (없으면 None)."""
    r = query("SELECT started_at FROM study_timers WHERE user_id = ?", (uid,), one=True)
    if r is None:
        return None
    return max(0, min(TIMER_MAX_SEC, int((datetime.now() - datetime.fromisoformat(r["started_at"])).total_seconds())))


def timer_start(uid):
    execute("INSERT OR IGNORE INTO study_timers (user_id) VALUES (?)", (uid,))


def timer_stop(uid):
    """타이머를 끝낸다. 돌려주는 값: 잰 초(돌고 있지 않았으면 None). 1초 이상이면 기록한다."""
    sec = timer_elapsed(uid)
    if sec is None:
        return None
    execute("DELETE FROM study_timers WHERE user_id = ?", (uid,))
    if sec >= TIMER_MIN_SEC:
        execute("INSERT INTO timer_logs (user_id, seconds) VALUES (?, ?)", (uid, sec))
    return sec


def streak(uid):
    """오늘(오늘 기록이 없으면 어제)부터 거꾸로, 공부 기록이 있는 날이 끊기지 않고 이어진 일수."""
    days = {r["d"] for r in query("SELECT DISTINCT date(ended_at) AS d FROM focus_logs WHERE user_id = ?", (uid,))}
    days |= {r["d"] for r in query("SELECT DISTINCT date(ended_at) AS d FROM timer_logs WHERE user_id = ?", (uid,))}
    days |= {r["d"] for r in query("""SELECT DISTINCT date(started_at) AS d FROM game_rounds
                                      WHERE user_id = ? AND (active_sec > 0 OR finished_at IS NOT NULL)""", (uid,))}
    d = date.today()
    if d.isoformat() not in days:
        d -= timedelta(days=1)
    n = 0
    while d.isoformat() in days:
        n += 1
        d -= timedelta(days=1)
    return n


# ---------------------------------------------------------------- 주간 순위
def weekly_ranking(uid, top=3):
    """이번 주(월요일부터) 공부 시간 순위. 상위 top명과 내 순위."""
    since = week_start().isoformat()
    total = {}
    for r in query("""SELECT f.user_id AS u, SUM(f.minutes) AS m FROM focus_logs f WHERE f.ended_at >= ? GROUP BY u""", (since,)):
        total[r["u"]] = total.get(r["u"], 0) + (r["m"] or 0)
    for r in query("SELECT user_id AS u, SUM(active_sec) AS s FROM game_rounds WHERE started_at >= ? GROUP BY u", (since,)):
        total[r["u"]] = total.get(r["u"], 0) + (r["s"] or 0) / 60
    for r in query("SELECT user_id AS u, SUM(seconds) AS s FROM timer_logs WHERE ended_at >= ? GROUP BY u", (since,)):
        total[r["u"]] = total.get(r["u"], 0) + (r["s"] or 0) / 60
    users = {r["id"]: r for r in query("""SELECT id, nickname, username FROM users
                                          WHERE role = 'student' AND disabled = 0""")}
    rows = sorted(((round(m), u) for u, m in total.items() if u in users and round(m) > 0), key=lambda x: (-x[0], x[1]))
    ranked = [{"rank": i + 1, "minutes": m, "name": users[u]["nickname"] or "학생", "me": u == uid}
              for i, (m, u) in enumerate(rows)]
    mine = next((r for r in ranked if r["me"]), None)
    end = week_start() + timedelta(days=6)
    return {"top": ranked[:top], "me": mine, "n": len(ranked),
            "label": f"{week_start().month}.{week_start().day}~{end.month}.{end.day}"}


# ---------------------------------------------------------------- 학습 진도
def reset_at(uid, topic):
    r = query("SELECT reset_at FROM quiz_resets WHERE user_id = ? AND topic = ?", (uid, topic), one=True)
    return r["reset_at"] if r else ""


def reset(uid, topics):
    from datetime import datetime
    now = datetime.now().isoformat(timespec="seconds")
    for t in topics:
        execute("""INSERT INTO quiz_resets (user_id, topic, reset_at) VALUES (?, ?, ?)
                   ON CONFLICT(user_id, topic) DO UPDATE SET reset_at = excluded.reset_at""", (uid, t, now))


def topic_progress(uid):
    """TOPIC 01~34: [{code, title, pct, done, total}]. 진술 문장 중 마지막으로 맞힌 것의 비율."""
    import quiz
    import quiz_topics
    from views.games import _is_right
    resets = {r["topic"]: r["reset_at"] for r in query("SELECT topic, reset_at FROM quiz_resets WHERE user_id = ?", (uid,))}
    last = {}                                   # (topic, 진술) -> 맞혔는지 (가장 최근 것)
    for r in query("""SELECT game, topic, answer, picks, started_at FROM game_rounds
                      WHERE user_id = ? AND game IN ('quiz', 'mixed') AND picks IS NOT NULL ORDER BY id DESC LIMIT 3000""", (uid,)):
        items, picks = json.loads(r["answer"]), json.loads(r["picks"] or "null") or []
        for i, it in enumerate(items):
            if i >= len(picks) or picks[i] is None:
                continue
            code = it.get("topic") or r["topic"]
            if r["started_at"] <= resets.get(code, ""):
                continue
            ok = _is_right(it, picks[i])
            for st in quiz.statements_of(it):
                last.setdefault((code, st), ok)
    out = []
    for t in quiz_topics.TOPICS:
        pool = {x[0] for x in t["tf"]}
        done = sum(1 for st in pool if last.get((t["code"], st)))
        out.append({"code": t["code"], "title": t["title"], "done": done, "total": len(pool),
                    "pct": round(done * 100 / len(pool)) if pool else 0})
    return out


def vocab_progress(uid):
    """평가원 빈출 단어(Day 01~50) 중 맞힌 횟수가 틀린 횟수 이상인 단어 비율."""
    import vocab
    book = {w for w, _ in vocab._BOOK}
    n = sum(1 for r in query("SELECT word FROM vocab_marks WHERE user_id = ? AND n_right > 0 AND n_right >= n_wrong", (uid,))
            if r["word"] in book)
    return {"done": n, "total": len(book), "pct": round(n * 100 / len(book)) if book else 0}
