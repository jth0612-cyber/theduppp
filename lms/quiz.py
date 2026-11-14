"""통과 Quiz 문제 생성. 범위: 2022 개정 통합과학 (퓨린·피리미딘, 수소 결합, 5'·3' 방향, 금속 결합은 다루지 않는다).

- 염기 짝 맞추기(DNA 상보 가닥 · DNA→RNA 전사) / 샤가프 법칙: 서버에서 무작위로 만든다 (정답이 계산으로 정해짐).
- TOPIC 퀴즈: quiz_topics 의 문제은행(O/X·ㄱㄴㄷ·4지선다·분류·순서·계산)에서 섞어 낸다.
"""
import random
import secrets

import quiz_topics

_rng = random.SystemRandom()

# ---------- 염기 짝 맞추기 ----------

PAIR = {"A": "T", "T": "A", "G": "C", "C": "G"}
# 전사: DNA 주형 가닥 → RNA (T 대신 U)
TRANSCRIBE = {"A": "U", "T": "A", "G": "C", "C": "G"}


def dna_round(length, mode="dna"):
    strand = "".join(secrets.choice("ATGC") for _ in range(length))
    table = TRANSCRIBE if mode == "rna" else PAIR
    return strand, "".join(table[b] for b in strand)


# ---------- 샤가프 법칙 ----------

def _choices(answer, spread, lo=0, hi=None):
    opts = {answer}
    while len(opts) < 4:
        cand = answer + _rng.choice([-1, 1]) * _rng.randint(1, 4) * spread
        if cand >= lo and (hi is None or cand <= hi):
            opts.add(cand)
    opts = sorted(opts)
    return opts, opts.index(answer)


def _chargaff_question(kind):
    if kind == "percent":
        a = _rng.randrange(12, 40, 2)
        target = _rng.choice(["T", "G", "C"])
        ans = a if target == "T" else 50 - a
        choices, idx = _choices(ans, 2, 0, 100)
        q = f"이중 가닥 DNA에서 아데닌(A)이 전체 염기의 {a}%일 때, {target}의 비율은?"
        exp = (f"샤가프 법칙: A=T, G=C. 그래서 T={a}%이고, G+C=100-2×{a}={100 - 2 * a}%, "
               f"G=C={50 - a}%입니다.")
        return q, [f"{c}%" for c in choices], idx, exp
    if kind == "count":
        n = _rng.randrange(200, 1001, 100)
        a = _rng.randrange(n // 10, n // 2 - 10, 10)
        ans = n // 2 - a
        choices, idx = _choices(ans, 10, 0)
        q = f"염기 {n}개로 이루어진 이중 가닥 DNA에 아데닌(A)이 {a}개 있습니다. 구아닌(G)은 몇 개일까요?"
        exp = f"A=T={a}개이므로 G+C={n}-2×{a}={n - 2 * a}개, G=C={ans}개입니다."
        return q, [f"{c}개" for c in choices], idx, exp
    if kind == "gc":
        gc = _rng.randrange(30, 72, 2)
        ans = (100 - gc) // 2
        choices, idx = _choices(ans, 2, 0, 100)
        q = f"이중 가닥 DNA에서 G+C의 비율이 {gc}%입니다. 아데닌(A)의 비율은?"
        exp = f"A+T=100-{gc}={100 - gc}%이고 A=T이므로 A={ans}%입니다."
        return q, [f"{c}%" for c in choices], idx, exp
    if kind == "strand":
        a, t, g = _rng.randrange(10, 35), _rng.randrange(10, 35), _rng.randrange(10, 30)
        c = 100 - a - t - g
        target = _rng.choice(["A", "G"])
        ans = t if target == "A" else c
        choices, idx = _choices(ans, 3, 0, 100)
        q = (f"DNA의 한 가닥(Ⅰ)에서 A={a}%, T={t}%, G={g}%, C={c}%입니다. "
             f"이와 상보적인 가닥(Ⅱ)에서 {target}의 비율은?")
        partner = "T" if target == "A" else "C"
        exp = f"가닥 Ⅱ의 {target}는 가닥 Ⅰ의 {partner}와 짝을 이룹니다. 그래서 {partner}의 비율 {ans}%와 같습니다."
        return q, [f"{x}%" for x in choices], idx, exp
    if kind == "rna":
        a, t, g = _rng.randrange(10, 35), _rng.randrange(10, 35), _rng.randrange(10, 30)
        c = 100 - a - t - g
        target = _rng.choice(["U", "A", "G"])
        ans = {"U": a, "A": t, "G": c}[target]
        choices, idx = _choices(ans, 3, 0, 100)
        q = (f"DNA 주형 가닥에서 A={a}%, T={t}%, G={g}%, C={c}%입니다. "
             f"이 가닥으로부터 전사된 RNA에서 {target}의 비율은?")
        partner = {"U": "A", "A": "T", "G": "C"}[target]
        exp = f"RNA의 {target}는 주형 가닥의 {partner}와 짝을 이룹니다(RNA에는 T 대신 U). 그래서 {partner}의 비율 {ans}%와 같습니다."
        return q, [f"{x}%" for x in choices], idx, exp
    # pair: 이중 가닥 DNA에서 늘 성립하는 관계
    q = "이중 가닥 DNA에서 항상 성립하는 관계는?"
    opts = ["A의 양 = T의 양", "A의 양 = G의 양", "T의 양 = C의 양", "A+T의 양 = G+C의 양"]
    exp = "A는 T와, G는 C와 짝을 이루므로 A와 T의 양이 같고 G와 C의 양이 같습니다. A+T와 G+C는 생물마다 달라요."
    return q, opts, 0, exp


def chargaff_round():
    kinds = ["percent", "count", "gc", "strand", _rng.choice(["rna", "pair"])]
    _rng.shuffle(kinds)
    return [dict(zip(("question", "choices", "answer_index", "explanation"), _chargaff_question(k)))
            for k in kinds]


# ---------- TOPIC 퀴즈 (개념서 TOPIC 01~34) ----------

import quiz_more

# 추가 진술 합치기 (같은 문장은 한 번만)
for _t in quiz_topics.TOPICS:
    _have = {x[0] for x in _t["tf"]}
    _t["tf"] = list(_t["tf"]) + [x for x in quiz_more.MORE.get(_t["code"], []) if x[0] not in _have]

TOPICS = {t["code"]: (t["title"], t["std"], t["part"]) for t in quiz_topics.TOPICS}
_GA = "ㄱㄴㄷ"


def _label(code):
    return f"TOPIC {code} {TOPICS[code][0]}"


def make_tf(code, stmt):
    text, ok, exp = stmt
    return {"kind": "tf", "question": text, "choices": ["O", "X"], "answer_index": 0 if ok else 1,
            "explanation": ("옳다. " if ok else "옳지 않다. ") + exp, "topic": code}


def make_pick(code, stmts):
    """ㄱㄴㄷ 보기: 진술 3개 중 옳은 것을 모두 고른 조합."""
    right = tuple(i for i, s in enumerate(stmts) if s[1])
    subsets = [(0,), (1,), (2,), (0, 1), (0, 2), (1, 2), (0, 1, 2)]
    others = [x for x in subsets if x != right]
    opts = sorted(_rng.sample(others, 4) + [right], key=lambda x: (len(x), x))
    label = lambda x: ", ".join(_GA[i] for i in x)
    exp = " / ".join(f"{_GA[i]}. {'옳다' if s[1] else '옳지 않다'} — {s[2]}" for i, s in enumerate(stmts))
    return {"kind": "pick", "question": "옳은 것만을 있는 대로 고른 것은?", "lines": [s[0] for s in stmts],
            "choices": [label(x) for x in opts], "answer_index": opts.index(right), "explanation": exp, "topic": code}


def make_mc(code, item):
    q, choices, ans, exp = item
    order = list(range(len(choices)))
    _rng.shuffle(order)
    return {"kind": "mc", "question": q, "choices": [choices[i] for i in order], "answer_index": order.index(ans),
            "explanation": exp, "topic": code}


def make_sort(code, item):
    prompt, bins, pool, exp = item
    n = min(len(pool), 6 if len(bins) <= 2 else 7)
    for _ in range(40):                                   # 칸마다 하나 이상
        pick = _rng.sample(pool, n)
        if {b for _, b in pick} == set(range(len(bins))):
            break
    return {"kind": "sort", "question": prompt, "bins": bins, "items": [x for x, _ in pick],
            "answer_list": [b for _, b in pick], "explanation": exp, "topic": code}


def make_order(code, item):
    prompt, seq, exp = item
    if len(seq) > 6:                                     # 길면 5개만 골라 순서는 유지
        keep = sorted(_rng.sample(range(len(seq)), 5))
        seq = [seq[i] for i in keep]
    shown = list(seq)
    while shown == seq:
        _rng.shuffle(shown)
    return {"kind": "order", "question": prompt, "items": shown, "answer_list": [shown.index(x) for x in seq],
            "explanation": exp, "answer_text": " → ".join(seq), "topic": code}


def make_num(code, fn):
    q, val, unit, exp = fn()
    val = round(float(val), 6)
    return {"kind": "num", "question": q, "unit": unit, "answer_num": val,
            "answer_text": f"{quiz_topics._fmt(val)} {unit}", "explanation": exp, "topic": code}


def _special(code):
    """그 TOPIC에서 낼 수 있는 특수 형식 문제 하나씩."""
    t = quiz_topics.BY_CODE[code]
    out = []
    if t.get("sort"):
        out.append(lambda: make_sort(code, _rng.choice(t["sort"])))
    if t.get("order"):
        out.append(lambda: make_order(code, _rng.choice(t["order"])))
    if t.get("num"):
        out.append(lambda: make_num(code, t["num"]))
    return out


def make_best(code, stmts, want_true):
    """4지선다 '옳은 것은?'(참 1 + 거짓 3) / '옳지 않은 것은?'(참 3 + 거짓 1). 보기는 진술 문장."""
    order = list(range(4))
    _rng.shuffle(order)
    picked = [stmts[i] for i in order]
    ans = next(i for i, x in enumerate(picked) if x[1] == want_true)
    odd = picked[ans]
    exp = odd[2] or ("옳은 설명이에요." if want_true else "옳지 않은 설명이에요.")
    others = [f"{x[0]} → {x[2]}" for x in picked if x is not odd and x[2] and not x[1]] if want_true else []
    if others:
        exp += " / 나머지 중 틀린 것: " + " / ".join(others[:2])
    return {"kind": "mc", "question": "옳은 것은?" if want_true else "옳지 않은 것은?", "choices": [x[0] for x in picked],
            "answer_index": ans, "explanation": exp, "topic": code, "stmts": [x[0] for x in picked]}


def _weighted(pool, n, history):
    """진술을 고를 때: 처음 보는 것과 전에 틀린 것을 먼저 (같은 문제를 다시 볼 확률을 낮춘다)."""
    def w(x):
        h = (history or {}).get(x[0])
        if h is None:
            return 3.0
        return 4.0 if h.get("wrong") else 0.6
    pool = list(pool)
    out = []
    for _ in range(min(n, len(pool))):
        tot = sum(w(x) for x in pool)
        r = _rng.random() * tot
        for i, x in enumerate(pool):
            r -= w(x)
            if r <= 0:
                out.append(pool.pop(i))
                break
        else:
            out.append(pool.pop())
    return out


def bank_quiz(code, count=10, history=None):
    """TOPIC 한 판 10문제: O/X 4 · ㄱㄴㄷ 1 · 옳은 것/옳지 않은 것 1 · 분류·순서·계산 · 4지선다.
    history: {진술: {"wrong": bool}} — 처음 보는 진술과 전에 틀린 진술이 먼저 나온다."""
    t = quiz_topics.BY_CODE[code]
    trues = [x for x in t["tf"] if x[1]]
    falses = [x for x in t["tf"] if not x[1]]
    order = _weighted(t["tf"], len(t["tf"]), history)          # 이번 판에 쓸 진술 순서
    used, out = set(), []

    def take(cond, n):
        got = [x for x in order if x[0] not in used and cond(x)][:n]
        used.update(x[0] for x in got)
        return got

    # ㄱㄴㄷ 1문제 (옳은 진술이 하나는 있게)
    trio = take(lambda x: True, 3)
    if len(trio) == 3:
        if not any(x[1] for x in trio):
            extra = take(lambda x: x[1], 1)
            if extra:
                trio[0] = extra[0]
        out.append(make_pick(code, trio))
    # 옳은 것은? / 옳지 않은 것은? 1문제
    want = _rng.random() < 0.5
    if len(trues) >= 3 and len(falses) >= 3:
        one = take(lambda x: x[1] == want, 1)
        three = take(lambda x: x[1] != want, 3)
        if len(one) == 1 and len(three) == 3:
            out.append(make_best(code, one + three, want))
    # 분류·순서·계산 중 2개, 직접 만든 4지선다 1개
    specials = [f() for f in _special(code)]
    _rng.shuffle(specials)
    out += specials[:2]
    mcs = list(t.get("mc", []))
    _rng.shuffle(mcs)
    out += [make_mc(code, m) for m in mcs[:1]]
    # 나머지는 O/X
    out += [make_tf(code, x) for x in take(lambda x: True, max(0, count - len(out)))]
    out = out[:count]
    _rng.shuffle(out)
    return out


def statements_of(item):
    """채점 기록용: 이 문제에 쓰인 진술 문장들."""
    if item.get("kind") == "tf":
        return [item["question"]]
    if item.get("kind") == "pick":
        return list(item.get("lines", []))
    return list(item.get("stmts", []))


def _codes(part=None):
    return [c for c, v in TOPICS.items() if part in (None, v[2])]


def mixed_quiz(count=10, part=None):
    """여러 TOPIC에서 골고루, 형식도 섞어서."""
    codes = _codes(part)
    _rng.shuffle(codes)
    plan = ["tf", "tf", "pick", "best", "special", "special", "tf", "pick", "special", "mc"][:count]
    _rng.shuffle(plan)
    out, k = [], 0
    for kind in plan:
        for _ in range(len(codes)):
            code = codes[k % len(codes)]
            k += 1
            t = quiz_topics.BY_CODE[code]
            if kind == "tf":
                it = make_tf(code, _rng.choice(t["tf"]))
            elif kind == "pick" and len(t["tf"]) >= 3:
                trio = _rng.sample(t["tf"], 3)
                if not any(s[1] for s in trio):
                    continue
                it = make_pick(code, trio)
            elif kind == "mc" and t.get("mc"):
                it = make_mc(code, _rng.choice(t["mc"]))
            elif kind == "best":
                want = _rng.random() < 0.5
                ones = [x for x in t["tf"] if x[1] == want]
                threes = [x for x in t["tf"] if x[1] != want]
                if not ones or len(threes) < 3:
                    continue
                it = make_best(code, [_rng.choice(ones)] + _rng.sample(threes, 3), want)
            elif kind == "special" and _special(code):
                it = _rng.choice(_special(code))()
            else:
                continue
            it["tag"] = _label(code)
            out.append(it)
            break
    return out


def speed_items(n=40, topic=None):
    """O/X 스피드: 개념 진술 하나를 보고 옳으면 O, 틀리면 X."""
    pool = [(c, s) for c in _codes() for s in quiz_topics.BY_CODE[c]["tf"] if topic in (None, c)]
    picks = _rng.sample(pool, min(n, len(pool)))
    return [{"q": s[0], "a": "", "ok": s[1], "exp": s[2], "tag": _label(c)} for c, s in picks]
