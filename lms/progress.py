"""내 공부: 공부 시간·푼 문제·연속 학습, 주간 공부 순위, 일별 이용 시간, 학습 진도.

공부 시간 = 소도시 명상 집중 기록(focus_logs) + 퀴즈·게임을 실제로 푼 시간(game_rounds.active_sec).
일별 이용 시간은 '집중 / 통과 Quiz / 영단어' 세 가지로 나눈다.
학습 진도: TOPIC마다 진술 문장 중 마지막으로 맞힌 것의 비율. 초기화하면 그 뒤에 푼 것만 센다."""
import json
from datetime import date, timedelta

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
    by_day = {}
    for (u, d), m in per.items():
        if m >= 1:
            by_day.setdefault(d, []).append(m)
    return {d: round(sum(v) / len(v)) for d, v in by_day.items()}


def today_summary(uid):
    """오늘 공부 시간(분), 오늘 푼 문제 수, 연속 학습 일수."""
    today = date.today().isoformat()
    day = daily(uid, 1)[0]
    solved = sum(_solved(r) for r in query("""SELECT picks, total, finished_at FROM game_rounds
                                               WHERE user_id = ? AND started_at >= ?""", (uid, today)))
    return {"minutes": day["total"], "solved": solved, "streak": streak(uid)}


def streak(uid):
    """오늘(오늘 기록이 없으면 어제)부터 거꾸로, 공부 기록이 있는 날이 끊기지 않고 이어진 일수."""
    days = {r["d"] for r in query("SELECT DISTINCT date(ended_at) AS d FROM focus_logs WHERE user_id = ?", (uid,))}
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
