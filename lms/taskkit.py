"""과제 채점·분석 도구.

선생님이 올린 '정답·해설 PDF'에서 정답과 문항별 해설을 읽어 오고(가능한 만큼, 선생님이 고칠 수 있게),
학생이 입력한 답을 채점해 문제점을 찾아 준다. 외부 AI 없이 규칙으로만 분석한다(비용 없음)."""
import re

UNITS = ["과학의 기초", "물질과 규칙성", "시스템과 상호작용", "변화와 다양성", "환경과 에너지", "과학과 미래사회"]
CIRCLED = {"①": "1", "②": "2", "③": "3", "④": "4", "⑤": "5"}

# 단원 짐작용 낱말 (해설 글에 많이 나올수록 그 단원)
UNIT_WORDS = {
    "과학의 기초": ["측정", "단위", "기본량", "유도량", "어림", "정보", "디지털", "아날로그", "자연 현상", "시간과 공간", "규모"],
    "물질과 규칙성": ["원소", "주기율표", "주기", "족", "금속", "비금속", "이온", "공유 결합", "이온 결합", "원자", "전자", "빅뱅", "스펙트럼",
                  "별", "핵융합", "규산염", "단백질", "핵산", "DNA", "신소재", "반도체", "초전도", "그래핀", "탄소 나노"],
    "시스템과 상호작용": ["중력", "자유 낙하", "운동량", "충격량", "관성", "지구 시스템", "지권", "수권", "기권", "생물권", "판", "지진", "화산",
                    "세포막", "물질대사", "효소", "유전자", "단백질 합성", "생명 시스템", "삼투", "확산", "전사", "번역"],
    "변화와 다양성": ["산화", "환원", "산", "염기", "중화", "pH", "지질 시대", "화석", "대멸종", "변이", "자연 선택", "진화", "생물 다양성", "광합성", "연소"],
    "환경과 에너지": ["생태계", "먹이", "에너지 흐름", "생태 피라미드", "평형", "지구 온난화", "온실", "엘니뇨", "사막화", "대기 대순환",
                 "발전기", "전자기 유도", "에너지 전환", "효율", "태양 전지", "핵발전", "화력", "신재생", "송전", "변압기"],
    "과학과 미래사회": ["감염병", "빅데이터", "인공지능", "사물 인터넷", "로봇", "윤리", "미래 사회", "과학 기술"],
}


# ---------- PDF 읽기 ----------

def pdf_pages(path):
    """PDF 각 쪽의 글자. 글자를 못 읽는 PDF(스캔 이미지)면 빈 목록."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        return [(p.extract_text() or "") for p in reader.pages]
    except Exception:  # noqa: BLE001 — 깨진 PDF 도 앱을 멈추지 않게
        return []


def guess_key(pages):
    """'1 ③ 2 ⑤ …' 또는 '1. ③' 같은 정답표를 찾아 [정답...] 으로. 1번부터 이어지는 만큼만."""
    found = {}
    for text in pages:
        for m in re.finditer(r"(?<![\d.])(\d{1,2})\s*[.)번]?\s*[:：]?\s*([①②③④⑤])", text):
            n = int(m.group(1))
            if 1 <= n <= 60 and n not in found:
                found[n] = CIRCLED[m.group(2)]
    key, i = [], 1
    while i in found:
        key.append(found[i]); i += 1
    return key


def split_solutions(pages, n):
    """문항 번호(줄 앞의 '3.' '3)' '3번')로 해설을 나눠 {번호: {page, text}}. 순서대로 나오는 번호만 쓴다."""
    marks = []
    for pi, text in enumerate(pages):
        for m in re.finditer(r"(?m)^\s*(\d{1,2})\s*(?:[.)]|번)\s*", text):
            marks.append((pi, m.start(), m.end(), int(m.group(1))))
    seq, want = [], 1
    for mk in marks:
        if mk[3] == want:
            seq.append(mk); want += 1
            if want > n:
                break
    out = {}
    for i, (pi, _s, e, num) in enumerate(seq):
        if i + 1 < len(seq) and seq[i + 1][0] == pi:
            chunk = pages[pi][e:seq[i + 1][1]]
        else:
            chunk = pages[pi][e:] + ("\n" + pages[seq[i + 1][0]][:seq[i + 1][1]] if i + 1 < len(seq) and seq[i + 1][0] == pi + 1 else "")
        chunk = re.sub(r"\s+", " ", chunk).strip()
        out[num] = {"page": pi + 1, "text": chunk[:500]}
    return out


def guess_unit(text):
    best, score = "", 0
    for unit, words in UNIT_WORDS.items():
        s = sum(text.count(w) for w in words)
        if s > score:
            best, score = unit, s
    return best


# ---------- 채점 ----------

def norm_answer(a):
    a = (a or "").strip()
    a = CIRCLED.get(a, a)
    return re.sub(r"\s+", "", a).lower()


def is_choice(k):
    return norm_answer(k) in {"1", "2", "3", "4", "5"}


def grade(key, answers):
    return [bool(answers[i]) and norm_answer(answers[i]) == norm_answer(k) for i, k in enumerate(key)]


def analyze(key, units, answers, others):
    """학생 한 명의 문제점. others: 같은 과제를 낸 다른 학생들의 답 목록(문항별 정답률·매력적 오답 계산용)."""
    n = len(key)
    ok = grade(key, answers)
    correct = sum(ok)
    # 문항별 정답률(다른 학생 기준)과 가장 많이 고른 오답
    rates, lures = [], []
    for i in range(n):
        picks = [norm_answer(o[i]) for o in others if i < len(o) and o[i]]
        right = sum(1 for p in picks if p == norm_answer(key[i]))
        rates.append(right / len(picks) if picks else None)
        wrong = [p for p in picks if p != norm_answer(key[i])]
        lures.append(max(set(wrong), key=wrong.count) if wrong else None)
    # 단원별
    by_unit = {}
    for i in range(n):
        u = (units[i] if i < len(units) else "") or "단원 미정"
        b = by_unit.setdefault(u, [0, 0]); b[1] += 1; b[0] += ok[i]
    unit_rows = sorted(([u, c, t, round(c * 100 / t)] for u, (c, t) in by_unit.items()), key=lambda r: (r[3], -r[2]))
    findings = []
    weak = [r for r in unit_rows if r[2] >= 2 and r[3] < 60 and r[0] != "단원 미정"]
    for u, c, t, p in weak[:2]:
        findings.append(("weak", f"‘{u}’ 단원에서 {t}문제 중 {t - c}문제를 틀렸어요. 이 단원 개념을 먼저 다시 보세요."))
    slips = [i + 1 for i in range(n) if not ok[i] and answers[i] and rates[i] is not None and rates[i] >= 0.7]
    if slips:
        findings.append(("slip", f"다른 친구들 대부분이 맞힌 {', '.join(map(str, slips))}번을 틀렸어요. 실수였는지, 개념 구멍인지 확인해 보세요."))
    hard = [i + 1 for i in range(n) if not ok[i] and answers[i] and rates[i] is not None and rates[i] < 0.4]
    if hard:
        findings.append(("hard", f"{', '.join(map(str, hard))}번은 많은 친구가 어려워한 문제예요. 해설을 천천히 읽고 풀이 흐름을 익히세요."))
    lured = [i + 1 for i in range(n) if not ok[i] and answers[i] and lures[i] and norm_answer(answers[i]) == lures[i]
             and is_choice(key[i])]
    if len(lured) >= 2:
        findings.append(("lure", f"{', '.join(map(str, lured))}번은 많은 친구가 고른 같은 오답(매력적인 오답)을 골랐어요. 선지를 끝까지 비교하는 습관을 들이세요."))
    if n >= 9:
        third = n // 3
        early = sum(ok[:n - third]) / (n - third); late = sum(ok[n - third:]) / third
        if early - late >= 0.3:
            findings.append(("time", f"뒤쪽 {third}문항 정답률({round(late * 100)}%)이 앞쪽({round(early * 100)}%)보다 크게 낮아요. 시간 배분이나 집중력을 점검해 보세요."))
    blanks = [i + 1 for i in range(n) if not answers[i]]
    if blanks:
        findings.append(("blank", f"{', '.join(map(str, blanks))}번을 비워 두었어요. 모르는 문제도 끝까지 골라 보는 연습을 해요."))
    if correct == n:
        findings.append(("perfect", "모두 맞혔어요! 다음 과제도 이 흐름으로 가요."))
    elif not findings:
        findings.append(("ok", "큰 약점은 보이지 않아요. 틀린 문제의 해설만 확인하고 넘어가요."))
    return {"ok": ok, "correct": correct, "total": n, "pct": round(correct * 100 / n) if n else 0,
            "rates": rates, "units": unit_rows, "findings": findings}
