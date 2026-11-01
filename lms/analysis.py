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


def parse_answers(raw, n_items):
    """학생 답안: 1~5 숫자만 남기고 최대 n_items 개. (부분 입력 허용)"""
    return "".join(ch for ch in (raw or "") if ch in "12345")[:n_items]


def score_answers(answers, key, points):
    if len(answers) != len(key):
        return None
    return sum(p for a, k, p in zip(answers, key, points) if int(a) == k)


def wrong_items(answers, key):
    return [i + 1 for i, (a, k) in enumerate(zip(answers, key)) if int(a) != k]


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


def distribution(scores, full_score, buckets=10):
    """점수 구간별 비율(%). 마지막 구간은 만점을 포함한다."""
    width = full_score / buckets
    counts = [0] * buckets
    for sc in scores:
        idx = min(buckets - 1, int(sc // width)) if width else 0
        counts[idx] += 1
    n = len(scores) or 1
    out = []
    for i, c in enumerate(counts):
        lo = round(i * width)
        hi = round(full_score) if i == buckets - 1 else round((i + 1) * width) - 1
        out.append({"label": f"{lo}–{hi}", "pct": round(100 * c / n), "count": c})
    return out


def bucket_label(score, full_score, buckets=10):
    if score is None:
        return None
    width = full_score / buckets
    i = min(buckets - 1, int(score // width)) if width else 0
    lo = round(i * width)
    hi = round(full_score) if i == buckets - 1 else round((i + 1) * width) - 1
    return f"{lo}–{hi}"


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


def compute(entries, key, full_score):
    """entries: [{'answers': str, 'score': float|None}] (같은 회차의 모든 제출)."""
    complete = [e for e in entries if e["score"] is not None]
    scores = [float(e["score"]) for e in complete]
    answer_rows = [e["answers"] for e in complete if e["answers"] and len(e["answers"]) == len(key)]
    return {
        "n": len(scores),
        "n_answers": len(answer_rows),
        "cuts": grade_cuts(scores),
        "dist": distribution(scores, full_score) if scores else [],
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
