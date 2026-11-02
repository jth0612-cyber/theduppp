"""교재 분석실: 교재 인증 코드, 가채점 채점, 예상 등급컷·점수 분포·문항별 오답률 계산.
정답과 배점은 서버에만 두고, 채점과 통계도 서버에서만 한다."""
import json
import math
import secrets
import time

# 수능 9등급 누적 비율(%) — 1등급 4%, 2등급 11%, ... 8등급 96%, 나머지 9등급
GRADE_CUM = [4, 11, 23, 40, 60, 77, 89, 96]
MIN_FOR_CUTS = 10          # 이 인원보다 적으면 등급컷을 보여주지 않는다
RANGE_PCT = 2              # 추정 범위: 누적 비율 ±2%p 에 해당하는 점수
CHOICES = 5
# 통합과학(2028 수능~): 25문항 50점, 배점 1.5·2·2.5점 혼합
DEFAULT_ITEMS = 25
DEFAULT_FULL = 50
BASE_POINT, HIGH_POINT, LOW_POINT = 2, 2.5, 1.5

# 헷갈리는 글자(0/O, 1/I/L)를 뺀 대문자·숫자. 12자리면 약 7.9×10^17 가지
_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LEN = 12


# ---------- 교재 코드 ----------

def normalize_code(raw):
    """사용자가 입력한 코드를 저장 형식(대문자 12자리, 구분자 없음)으로 바꾼다."""
    s = "".join(ch for ch in (raw or "").upper() if ch.isalnum())
    s = s.replace("O", "0").replace("I", "1").replace("L", "1")  # 흔한 오타는 아래 검사에서 걸러진다
    return s if len(s) == CODE_LEN and all(ch in _ALPHABET for ch in s) else None


def new_code(is_taken):
    while True:
        code = "".join(secrets.choice(_ALPHABET) for _ in range(CODE_LEN))
        if not is_taken(code):
            return code


def format_code(code):
    return "-".join(code[i:i + 4] for i in range(0, len(code), 4))


# ---------- 시험(회차) 정답·배점 ----------

def parse_key(raw, n_items):
    """정답 문자열(예: '14352 53411 ...')을 길이 n_items 의 숫자 목록으로. 잘못되면 ValueError."""
    digits = [ch for ch in (raw or "") if not ch.isspace() and ch not in ",-"]
    if len(digits) != n_items or any(ch not in "12345" for ch in digits):
        raise ValueError(f"정답은 1~5 숫자 {n_items}개여야 합니다. (지금 {len(digits)}개)")
    return [int(ch) for ch in digits]


def parse_points(raw, n_items, full_score):
    """배점 문자열(예: '2,2,3,...'). 비우면 만점을 문항 수로 똑같이 나눈다. 합이 만점과 같아야 한다."""
    raw = (raw or "").strip()
    if not raw:
        each = full_score / n_items
        if each != int(each):
            raise ValueError("만점이 문항 수로 나누어떨어지지 않습니다. 배점을 직접 입력하세요.")
        return [int(each)] * n_items
    parts = [p for p in raw.replace(" ", ",").split(",") if p]
    try:
        pts = [float(p) for p in parts]
    except ValueError:
        raise ValueError("배점은 숫자를 쉼표로 구분해 입력하세요.") from None
    if len(pts) != n_items or any(p <= 0 for p in pts):
        raise ValueError(f"배점은 양수 {n_items}개여야 합니다. (지금 {len(pts)}개)")
    if abs(sum(pts) - full_score) > 1e-9:
        raise ValueError(f"배점의 합({_fmt(sum(pts))})이 만점({_fmt(full_score)})과 같아야 합니다.")
    return [int(p) if p == int(p) else p for p in pts]


def parse_item_numbers(raw, n_items):
    """'3, 7 12-14' 같은 문항 번호 목록. 범위(12-14)도 받는다."""
    out = set()
    for part in (raw or "").replace(",", " ").replace("·", " ").split():
        try:
            if "-" in part or "~" in part:
                a, b = part.replace("~", "-").split("-", 1)
                rng = range(int(a), int(b) + 1)
            else:
                rng = [int(part)]
        except ValueError:
            raise ValueError(f"문항 번호 '{part}'를 읽지 못했습니다. 숫자와 쉼표로 적어 주세요.") from None
        for n in rng:
            if not 1 <= n <= n_items:
                raise ValueError(f"{n}번은 없는 문항입니다. (1~{n_items}번)")
            out.add(n)
    return out


def points_from_levels(high_raw, low_raw, n_items, full_score):
    """2.5점·1.5점 문항 번호만 받고 나머지는 2점으로 채운다. 합이 만점과 같아야 한다."""
    high = parse_item_numbers(high_raw, n_items)
    low = parse_item_numbers(low_raw, n_items)
    both = high & low
    if both:
        raise ValueError(f"{', '.join(map(str, sorted(both)))}번이 2.5점과 1.5점에 모두 들어 있습니다.")
    pts = [HIGH_POINT if i in high else LOW_POINT if i in low else BASE_POINT for i in range(1, n_items + 1)]
    total = sum(pts)
    if abs(total - full_score) > 1e-9:
        raise ValueError(f"배점의 합이 {_fmt(total)}점입니다. 만점 {_fmt(full_score)}점이 되도록 "
                         f"2.5점과 1.5점 문항 수를 맞춰 주세요. (지금 2.5점 {len(high)}개, 1.5점 {len(low)}개)")
    return pts


def score_step(points):
    """점수가 움직이는 가장 작은 단위: 모두 정수면 1, 0.5점 배점이 있으면 0.5."""
    if all(float(p) == int(p) for p in points):
        return 1
    return 0.5 if all(float(p) * 2 == int(float(p) * 2) for p in points) else 0.1


def parse_answers(raw, n_items):
    """빠른 입력(숫자를 1번부터 차례로): 1~5만 남기고 n_items 칸으로. 빈 칸은 '0'."""
    digits = "".join(ch for ch in (raw or "") if ch in "12345")[:n_items]
    return digits + "0" * (n_items - len(digits))


def answers_from_marks(form, n_items):
    """답안지(문항마다 ①~⑤ 선택): a1..aN 값. 고르지 않은 문항은 '0'."""
    out = []
    for i in range(1, n_items + 1):
        v = (form.get(f"a{i}") or "").strip()
        out.append(v if v in ("1", "2", "3", "4", "5") else "0")
    return "".join(out)


def is_complete(answers, n_items):
    return len(answers) == n_items and "0" not in answers


def filled_count(answers):
    return sum(1 for ch in (answers or "") if ch in "12345")


def score_answers(answers, key, points):
    if not is_complete(answers, len(key)):
        return None
    return sum(p for a, k, p in zip(answers, key, points) if int(a) == k)


def wrong_items(answers, key):
    return [i + 1 for i, (a, k) in enumerate(zip(answers, key)) if a in "12345" and int(a) != k]


def _fmt(x):
    return str(int(x)) if x == int(x) else f"{x:g}"


# ---------- 통계 ----------

def _stats_of(scores):
    n = len(scores)
    mean = sum(scores) / n
    sd = math.sqrt(sum((s - mean) ** 2 for s in scores) / n)
    return mean, sd


def standard_score(x, mean, sd):
    """탐구 영역식 표준점수: 평균 50, 표준편차 10."""
    return 50 if sd == 0 else round(50 + 10 * (x - mean) / sd)


def percentile_of(x, scores):
    """백분위: 나보다 낮은 비율 + 동점자의 절반."""
    below = sum(1 for s in scores if s < x)
    ties = sum(1 for s in scores if s == x)
    return round(100 * (below + ties / 2) / len(scores))


def grade_cuts(scores):
    """등급별 원점수 컷과 그 점수의 표준점수·백분위, 추정 범위."""
    if len(scores) < MIN_FOR_CUTS:
        return []
    n = len(scores)
    s = sorted(scores, reverse=True)
    mean, sd = _stats_of(scores)
    rows = []
    for grade, pct in enumerate(GRADE_CUM, start=1):
        cut = s[max(1, math.ceil(n * pct / 100)) - 1]
        lo = s[min(n, math.ceil(n * (pct + RANGE_PCT) / 100)) - 1]
        hi = s[max(1, math.ceil(n * max(pct - RANGE_PCT, 0.0001) / 100)) - 1]
        rows.append({"grade": grade, "raw": cut, "std": standard_score(cut, mean, sd),
                     "pct": percentile_of(cut, scores), "lo": lo, "hi": hi})
    return rows


def grade_for(score, cuts):
    if score is None or not cuts:
        return None
    for row in cuts:
        if score >= row["raw"]:
            return row["grade"]
    return 9


def _band(i, width, full_score, buckets, step):
    lo = round(i * width / step) * step
    hi = full_score if i == buckets - 1 else round(((i + 1) * width - step) / step) * step
    return f"{_fmt(lo)}–{_fmt(hi)}"


def distribution(scores, full_score, buckets=10, step=1):
    """점수 구간별 비율(%). 마지막 구간은 만점을 포함한다. step: 점수 단위(0.5점 배점이면 0.5)."""
    width = full_score / buckets
    counts = [0] * buckets
    for sc in scores:
        idx = min(buckets - 1, int(sc // width)) if width else 0
        counts[idx] += 1
    n = len(scores) or 1
    return [{"label": _band(i, width, full_score, buckets, step), "pct": round(100 * c / n), "count": c}
            for i, c in enumerate(counts)]


def bucket_label(score, full_score, buckets=10, step=1):
    if score is None:
        return None
    width = full_score / buckets
    i = min(buckets - 1, int(score // width)) if width else 0
    return _band(i, width, full_score, buckets, step)


def item_stats(answer_rows, key):
    """완성된 답안들로 문항별 오답률(%)과 선지별 선택 비율(%)."""
    n = len(answer_rows)
    items = []
    for i, k in enumerate(key):
        picks = [0] * CHOICES
        for a in answer_rows:
            picks[int(a[i]) - 1] += 1
        wrong = n - picks[k - 1]
        items.append({"no": i + 1, "wrong_pct": round(100 * wrong / n) if n else 0,
                      "choices": [round(100 * p / n) if n else 0 for p in picks]})
    top = sorted((it for it in items if it["wrong_pct"] > 0), key=lambda it: (-it["wrong_pct"], it["no"]))[:3]
    top_nos = {it["no"] for it in top}
    for it in items:
        it["top"] = it["no"] in top_nos
    return items


def compute(entries, key, full_score, step=1):
    """entries: [{'answers': str, 'score': float|None}] (같은 회차의 모든 제출)."""
    complete = [e for e in entries if e["score"] is not None]
    scores = [float(e["score"]) for e in complete]
    answer_rows = [e["answers"] for e in complete if e["answers"] and is_complete(e["answers"], len(key))]
    return {
        "n": len(scores),
        "n_answers": len(answer_rows),
        "cuts": grade_cuts(scores),
        "dist": distribution(scores, full_score, step=step) if scores else [],
        "items": item_stats(answer_rows, key) if answer_rows else [],
        "computed_at": time.strftime("%H:%M"),
    }


# 회차별 통계 캐시: 5분마다 다시 계산 (화면에 "○○:○○ 기준 · 5분마다 갱신")
_cache = {}


def cached(mock_id, ttl, loader):
    now = time.monotonic()
    hit = _cache.get(mock_id)
    if hit and now - hit[0] < ttl:
        return hit[1]
    data = loader()
    _cache[mock_id] = (now, data)
    return data


def invalidate(mock_id):
    _cache.pop(mock_id, None)


def dumps(obj):
    return json.dumps(obj, ensure_ascii=False)
