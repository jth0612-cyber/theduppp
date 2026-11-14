"""미니 Quiz · 영단어: 워드마스터 하이퍼 2000 (Day 01~50)을 하루 20개씩, 그 뒤로 수능 영단어. 오늘의 단어는 그날 처음 열 때 정해지고 하루 동안 그대로다.
틀린 단어는 복습에 모이고, 복습에서 맞히면(맞힌 횟수 ≥ 틀린 횟수) 빠진다."""
import difflib
import json
import os
import random
import re
from datetime import date, datetime

from db import execute, query

DAILY = 20


def _load():
    """data/vocab_*.txt 를 이름 순서로 읽는다. vocab_a_wordmaster(책 순서 Day 01~50)가 먼저, 나머지는 뒤에 붙는다."""
    book, extra, seen = [], [], set()
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    for fn in sorted(os.listdir(d)):
        if not (fn.startswith("vocab_") and fn.endswith(".txt")):
            continue
        dest = book if fn.startswith("vocab_a_") else extra
        with open(os.path.join(d, fn), encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line or line.startswith("#") or "\t" not in line:
                    continue
                w, m = line.split("\t", 1)
                w = w.strip()
                if w not in seen:
                    seen.add(w)
                    dest.append((w, m.strip()))
    return book, extra


_BOOK, _EXTRA = _load()
WORDS = _BOOK + _EXTRA
MEANING = dict(WORDS)
# 순서: 책 Day 01~50 은 책 순서 그대로(하루 20개 = 책의 하루), 그 뒤 단어는 한 번 섞어 둔다
_tail = [w for w, _ in _EXTRA]
random.Random(2028).shuffle(_tail)
ORDER = [w for w, _ in _BOOK] + _tail
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


# ---------- 헷갈리는 보기 고르기 ----------
def _senses(m):
    return {x.strip() for x in re.split(r"[,;]", re.sub(r"\(.*?\)", "", m)) if x.strip()}


def _pos(m):
    """뜻의 끝말로 품사를 어림한다: v 동사 / a 형용사 / n 명사 (여러 개일 수 있다)."""
    out = set()
    for x in _senses(m):
        if x.endswith("다"):
            out.add("v")
        elif x.endswith(("한", "의", "인", "는", "운", "된", "은", "적")):
            out.add("a")
        elif x.endswith(("게", "히", "이", "로")) and len(x) <= 5:
            out.add("d")
        else:
            out.add("n")
    return out


_POS = {w: _pos(m) for w, m in WORDS}
_SENSE = {w: _senses(m) for w, m in WORDS}
_near_cache = {}


def _near(w):
    """w 와 헷갈리기 쉬운 단어 12개: 철자가 닮았고(같은 머리·꼬리, 비슷한 길이) 품사가 겹치는 것부터."""
    if w in _near_cache:
        return _near_cache[w]
    lw = w.lower()
    scored = []
    for x in MEANING:
        if x == w or _SENSE[x] & _SENSE[w]:                 # 뜻이 겹치면 정답이 둘이 되므로 뺀다
            continue
        lx = x.lower()
        sc = difflib.SequenceMatcher(None, lw, lx).ratio()
        if lx[:3] == lw[:3]:
            sc += 0.25
        elif lx[:2] == lw[:2]:
            sc += 0.12
        if lx[-3:] == lw[-3:]:
            sc += 0.15
        if _POS[x] & _POS[w]:
            sc += 0.3                                       # 품사가 같아야 그럴듯하다
        sc -= abs(len(lx) - len(lw)) * 0.02
        scored.append((sc, x))
    scored.sort(reverse=True)
    _near_cache[w] = [x for _, x in scored[:12]]
    return _near_cache[w]


def _others(w, n):
    """오답 보기 n개: 철자가 닮고 품사가 같은 단어에서 고른다."""
    near = _near(w)
    if n == 1:
        picks = [_rng.choice(near[:4])]
    else:                                                   # 가장 헷갈리는 둘은 늘 넣고, 나머지는 판마다 바꾼다
        picks = near[:2] + _rng.sample(near[2:9], max(0, n - 2))
        _rng.shuffle(picks)
    out = []
    for x in picks:                                         # 보기끼리도 뜻이 겹치지 않게
        if not any(_SENSE[x] & _SENSE[y] for y in out):
            out.append(x)
    for x in near:
        if len(out) >= n:
            break
        if x not in out and not any(_SENSE[x] & _SENSE[y] for y in out):
            out.append(x)
    return out[:n]


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
            "n": len(letters), "answer_text": w.lower(), "explanation": f"{w} — {MEANING[w]}", "word": w}


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
    """짝 맞추기: 5쌍씩 묶고, 뜻 칸에는 짝 없는 뜻을 하나 섞는다 (마지막 쌍이 저절로 정해지지 않게)."""
    ws = list(words); _rng.shuffle(ws)
    sets = []
    for i in range(0, len(ws), size):
        part = ws[i:i + size]
        if len(part) < 3:
            continue
        decoy = _rng.choice([x for x, _ in WORDS if x not in words and MEANING[x] not in {MEANING[w] for w in part}])
        sets.append([{"w": w, "m": MEANING[w]} for w in part] + [{"w": "", "m": MEANING[decoy], "d": True}])
    return sets


def wide_pool(uid, n=60):
    """게임용 단어 묶음: 오늘 단어 + 복습할 단어 + 이미 본 단어 + 앞으로 나올 단어를 섞는다
    (게임마다, 판마다 단어가 달라지도록)."""
    _, today = today_set(uid)
    review = review_words(uid, limit=30)
    seen = [r["word"] for r in query("SELECT word FROM vocab_marks WHERE user_id = ? ORDER BY last DESC LIMIT 300", (uid,))
            if r["word"] in MEANING]
    seen = _rng.sample(seen, min(len(seen), 20))
    start = ORDER.index(today[-1]) + 1 if today and today[-1] in ORDER else 0
    ahead = [ORDER[(start + i) % len(ORDER)] for i in range(80)]
    ahead = _rng.sample(ahead, 20)
    pool = list(dict.fromkeys(_rng.sample(today, min(10, len(today))) + review[:10] + seen + ahead))
    _rng.shuffle(pool)
    return pool[:n]


def speed_items(uid, n=40):
    """스피드 O/X: 넓은 단어 묶음에서."""
    pool = wide_pool(uid, 60)
    out = []
    for _ in range(n):
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
