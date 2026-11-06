"""미니 Quiz · 영단어: 수능 영단어를 하루 20개씩. 오늘의 단어는 그날 처음 열 때 정해지고 하루 동안 그대로다.
틀린 단어는 복습에 모이고, 복습에서 맞히면(맞힌 횟수 ≥ 틀린 횟수) 빠진다."""
import json
import os
import random
from datetime import date, datetime

from db import execute, query

DAILY = 20


def _load():
    words, seen = [], set()
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    for fn in sorted(os.listdir(d)):
        if not (fn.startswith("vocab_csat") and fn.endswith(".txt")):
            continue
        with open(os.path.join(d, fn), encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line or line.startswith("#") or "\t" not in line:
                    continue
                w, m = line.split("\t", 1)
                if w not in seen:
                    seen.add(w)
                    words.append((w.strip(), m.strip()))
    return words


WORDS = _load()
MEANING = dict(WORDS)
# 날마다 여러 알파벳이 섞이도록 순서를 한 번 섞어 둔다 (모든 학생이 같은 순서)
ORDER = [w for w, _ in WORDS]
random.Random(2028).shuffle(ORDER)
_rng = random.SystemRandom()


def today_set(uid):
    """오늘의 단어 20개 (없으면 다음 20개로 만든다)."""
    day = date.today().isoformat()
    row = query("SELECT * FROM vocab_days WHERE user_id = ? AND day = ?", (uid, day), one=True)
    if row is None:
        n = query("SELECT COUNT(*) AS n FROM vocab_days WHERE user_id = ?", (uid,), one=True)["n"]
        start = (n * DAILY) % len(ORDER)
        words = [ORDER[(start + i) % len(ORDER)] for i in range(DAILY)]
        execute("INSERT OR IGNORE INTO vocab_days (user_id, day, day_no, words) VALUES (?, ?, ?, ?)",
                (uid, day, n + 1, json.dumps(words, ensure_ascii=False)))
        row = query("SELECT * FROM vocab_days WHERE user_id = ? AND day = ?", (uid, day), one=True)
    return row, [w for w in json.loads(row["words"]) if w in MEANING]


def review_words(uid, limit=DAILY):
    rows = query("""SELECT word FROM vocab_marks WHERE user_id = ? AND n_wrong > n_right
                    ORDER BY last DESC LIMIT ?""", (uid, limit))
    return [r["word"] for r in rows if r["word"] in MEANING]


def stats(uid):
    row = query("""SELECT COUNT(*) AS seen, COALESCE(SUM(n_wrong > n_right), 0) AS review FROM vocab_marks WHERE user_id = ?""",
                (uid,), one=True)
    today = query("SELECT * FROM vocab_days WHERE user_id = ? AND day = ?", (uid, date.today().isoformat()), one=True)
    days = query("SELECT COUNT(*) AS n FROM vocab_days WHERE user_id = ? AND done_at IS NOT NULL", (uid,), one=True)["n"]
    return {"seen": row["seen"], "review": row["review"], "total": len(WORDS), "days_done": days,
            "today": dict(today) if today else None}


def quiz_items(words):
    """한 단어에 한 문제: 대부분 '단어 → 뜻', 4문제마다 1문제는 '뜻 → 단어'."""
    items = []
    pool = [w for w, _ in WORDS]
    for i, w in enumerate(words):
        others = _rng.sample([x for x in pool if x != w and MEANING[x] != MEANING[w]], 3)
        if i % 4 == 3:
            choices = [w] + others
            q = f"‘{MEANING[w]}’에 맞는 단어는?"
        else:
            choices = [MEANING[w]] + [MEANING[x] for x in others]
            q = w
        order = list(range(4))
        _rng.shuffle(order)
        items.append({"question": q, "choices": [choices[k] for k in order], "answer_index": order.index(0),
                      "explanation": f"{w} — {MEANING[w]}", "word": w})
    _rng.shuffle(items)
    return items


def record(uid, items, results, day=None):
    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    for it, r in zip(items, results):
        if r["pick"] is None or r["pick"] < 0:
            continue
        ok = 1 if r["correct"] else 0
        execute("""INSERT INTO vocab_marks (user_id, word, n_right, n_wrong, last) VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(user_id, word) DO UPDATE SET n_right = n_right + excluded.n_right, n_wrong = n_wrong + excluded.n_wrong,
                   last = excluded.last""", (uid, it["word"], ok, 1 - ok, now))
    if day:
        score = sum(1 for r in results if r["correct"])
        execute("""UPDATE vocab_days SET score = MAX(COALESCE(score, 0), ?), total = ?, done_at = COALESCE(done_at, ?)
                   WHERE user_id = ? AND day = ?""", (score, len(items), now, uid, day))
