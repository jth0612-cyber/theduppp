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


def _others(w, n):
    pool = [x for x, _ in WORDS if x != w and MEANING[x] != MEANING[w]]
    return _rng.sample(pool, n)


def _mc(w):                       # 단어 → 뜻 (4지)
    others = _others(w, 3)
    choices = [MEANING[w]] + [MEANING[x] for x in others]
    order = list(range(4)); _rng.shuffle(order)
    return {"kind": "mc", "question": w, "prompt": "뜻을 고르세요", "choices": [choices[k] for k in order],
            "answer_index": order.index(0), "explanation": f"{w} — {MEANING[w]}", "word": w}


def _rev(w):                      # 뜻 → 단어 (4지)
    choices = [w] + _others(w, 3)
    order = list(range(4)); _rng.shuffle(order)
    return {"kind": "rev", "question": MEANING[w], "prompt": "알맞은 단어를 고르세요", "choices": [choices[k] for k in order],
            "answer_index": order.index(0), "explanation": f"{w} — {MEANING[w]}", "word": w}


def _listen(w):                   # 발음을 듣고 뜻 고르기 (단어는 답한 뒤에 보인다)
    it = _mc(w)
    it.update(kind="listen", prompt="듣고 뜻을 고르세요", say=w)
    return it


def _ox(w):                       # 단어와 뜻이 맞는 짝인지 (O/X)
    right = _rng.random() < 0.5
    shown = MEANING[w] if right else MEANING[_others(w, 1)[0]]
    return {"kind": "ox", "question": w, "sub": shown, "prompt": "이 뜻이 맞나요?", "choices": ["맞아요", "아니에요"],
            "answer_index": 0 if right else 1, "explanation": f"{w} — {MEANING[w]}", "word": w}


def _spell(w):                    # 뜻을 보고 글자 조각으로 철자 맞추기
    letters = list(w.lower())
    decoys = _rng.sample([c for c in "abcdefghilmnoprstuy" if c not in letters] or list("xyz"), 2)
    tiles = letters + decoys
    _rng.shuffle(tiles)
    return {"kind": "spell", "question": MEANING[w], "prompt": "글자를 순서대로 눌러 단어를 완성하세요", "tiles": tiles,
            "n": len(letters), "hint": w[0], "answer_text": w.lower(), "explanation": f"{w} — {MEANING[w]}", "word": w}


def quiz_items(words):
    """섞어 풀기: 단어마다 형식을 달리한다 (뜻 고르기 · 단어 고르기 · 듣고 고르기 · O/X · 철자 맞추기)."""
    makers = [_mc, _rev, _listen, _ox, _spell, _rev, _listen, _spell, _mc, _ox]
    items = []
    for i, w in enumerate(words):
        make = makers[i % len(makers)]
        if make is _spell and not (3 <= len(w) <= 11 and w.isalpha()):
            make = _mc
        items.append(make(w))
    _rng.shuffle(items)
    return items


def match_sets(words, size=5):
    """짝 맞추기: 5쌍씩 묶음."""
    ws = list(words); _rng.shuffle(ws)
    return [[{"w": w, "m": MEANING[w]} for w in ws[i:i + size]] for i in range(0, len(ws), size) if len(ws[i:i + size]) >= 3]


def memory_cards(words, pairs=6):
    """카드 뒤집기: 단어 카드와 뜻 카드 6쌍(12장)을 섞는다."""
    ws = _rng.sample(list(words), min(pairs, len(words)))
    cards = [{"t": w, "k": i, "en": True} for i, w in enumerate(ws)] + [{"t": MEANING[w], "k": i, "en": False} for i, w in enumerate(ws)]
    _rng.shuffle(cards)
    return ws, cards


def speed_items(uid, n=40):
    """스피드 O/X: 오늘 단어와 지금까지 본 단어에서 섞어 낸다."""
    seen = [r["word"] for r in query("SELECT word FROM vocab_marks WHERE user_id = ? ORDER BY last DESC LIMIT 200", (uid,)) if r["word"] in MEANING]
    _, today = today_set(uid)
    pool = list(dict.fromkeys(today + seen)) or [w for w, _ in WORDS[:60]]
    out = []
    for i in range(n):
        w = _rng.choice(pool)
        right = _rng.random() < 0.5
        out.append({"word": w, "q": w, "a": MEANING[w] if right else MEANING[_others(w, 1)[0]], "ok": right, "exp": f"{w} — {MEANING[w]}"})
    return out


def mark(uid, word, ok):
    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    execute("""INSERT INTO vocab_marks (user_id, word, n_right, n_wrong, last) VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(user_id, word) DO UPDATE SET n_right = n_right + excluded.n_right, n_wrong = n_wrong + excluded.n_wrong,
               last = excluded.last""", (uid, word, 1 if ok else 0, 0 if ok else 1, now))


def record(uid, items, results, day=None):
    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    for it, r in zip(items, results):
        if r["pick"] is None or r["pick"] == -1 or r["pick"] == "":
            continue
        mark(uid, it["word"], r["correct"])
    if day:
        score = sum(1 for r in results if r["correct"])
        execute("""UPDATE vocab_days SET score = MAX(COALESCE(score, 0), ?), total = ?, done_at = COALESCE(done_at, ?)
                   WHERE user_id = ? AND day = ?""", (score, len(items), now, uid, day))
