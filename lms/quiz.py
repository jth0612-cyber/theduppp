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


def bank_quiz(code, count=8):
    """TOPIC 한 판: O/X 3 · ㄱㄴㄷ 1 · 4지선다 · 분류/순서/계산을 섞어 8문제."""
    t = quiz_topics.BY_CODE[code]
    tf = list(t["tf"])
    _rng.shuffle(tf)
    out = []
    if len(tf) >= 6:                                      # ㄱㄴㄷ 에 쓴 진술은 O/X 로 다시 내지 않는다
        trio = tf[:3]
        if not any(s[1] for s in trio):
            trio[0] = next(s for s in tf if s[1])
        out.append(make_pick(code, trio))
        tf = [s for s in tf if s not in trio]
    specials = [f() for f in _special(code)]
    _rng.shuffle(specials)
    out += specials[:3]
    mcs = list(t.get("mc", []))
    _rng.shuffle(mcs)
    out += [make_mc(code, m) for m in mcs[:2]]
    out += [make_tf(code, s) for s in tf[:max(0, count - len(out))]]
    if len(out) < count:                                  # 모자라면 남은 형식 → 계산 새로 → ㄱㄴㄷ에 쓴 진술 순으로 채운다
        out += specials[3:3 + count - len(out)]
    for _ in range(10):
        if len(out) >= count or not t.get("num"):
            break
        out.append(make_num(code, t["num"]))
    used = {it["question"] for it in out}
    out += [make_tf(code, s) for s in t["tf"] if s[0] not in used][:max(0, count - len(out))]
    out = out[:count]
    _rng.shuffle(out)
    return out


def _codes(part=None):
    return [c for c, v in TOPICS.items() if part in (None, v[2])]


def mixed_quiz(count=10, part=None):
    """여러 TOPIC에서 골고루, 형식도 섞어서."""
    codes = _codes(part)
    _rng.shuffle(codes)
    plan = ["tf", "tf", "pick", "mc", "special", "special", "tf", "pick", "special", "mc"][:count]
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
