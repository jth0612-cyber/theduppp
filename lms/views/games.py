"""학생 Quiz 두 갈래.
- 수능 영단어: 오늘의 20단어(카드 + 섞어 풀기: 뜻·단어·듣기·O/X·철자), 짝 맞추기, 카드 뒤집기, 스피드 O/X, 복습.
- 통과 Quiz: 단원별 5문제, 섞어 풀기 10문제(4지선다·분류·순서·빈칸·계산), O/X 스피드, 샤가프 법칙, 염기 짝 맞추기(DNA·RNA).
문제와 정답은 서버에서 만들어 game_rounds 에 저장하고, 채점도 서버에서만 한다."""
import json
from datetime import datetime, timedelta

from flask import Blueprint, abort, g, jsonify, render_template, request

import quiz
import vocab
from db import execute, query
from security import student_required

bp = Blueprint("games", __name__, url_prefix="/s/games")

ROUND_TTL = timedelta(minutes=20)
DNA_LEVELS = {1: 8, 2: 12, 3: 16}
DNA_TIME_LIMIT = 90  # 초


def _now():
    return datetime.now()


def _new_round(game, payload, answer, topic=""):
    rid = execute("""INSERT INTO game_rounds (user_id, game, topic, payload, answer, started_at)
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  (g.user["id"], game, topic, json.dumps(payload, ensure_ascii=False),
                   json.dumps(answer, ensure_ascii=False), _now().isoformat(timespec="seconds")))
    return rid


def _open_round(rid, game):
    r = query("SELECT * FROM game_rounds WHERE id = ? AND user_id = ? AND game = ?",
              (rid, g.user["id"], game), one=True)
    if r is None:
        abort(404)
    if r["finished_at"] is not None:
        abort(409)
    if datetime.fromisoformat(r["started_at"]) + ROUND_TTL < _now():
        abort(410)
    return r


def _finish(rid, score, total):
    execute("UPDATE game_rounds SET score = ?, total = ?, finished_at = ? WHERE id = ?",
            (score, total, _now().isoformat(timespec="seconds"), rid))


def _json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400)
    return data


def _best():
    return {r["game"] + ":" + r["topic"]: r for r in query(
        """SELECT game, topic, MAX(score * 100 / total) AS best, MAX(score) AS top, COUNT(*) AS plays FROM game_rounds
           WHERE user_id = ? AND finished_at IS NOT NULL AND total > 0 GROUP BY game, topic""", (g.user["id"],))}


@bp.route("/")
@student_required
def hub():
    """수능 영단어"""
    return render_template("student/games/vocab_hub.html", best=_best(), v=vocab.stats(g.user["id"]))


@bp.route("/sci")
@student_required
def sci_hub():
    """통과 Quiz"""
    parts = [(label, [(k, v[0]) for k, v in quiz.TOPICS.items() if v[2] == n]) for n, label in quiz.PARTS.items()]
    return render_template("student/games/sci_hub.html", best=_best(), parts=parts)


# ---------- 염기 짝 맞추기 ----------

@bp.route("/dna")
@student_required
def dna():
    mode = "rna" if request.args.get("mode") == "rna" else "dna"
    return render_template("student/games/dna.html", levels=DNA_LEVELS, time_limit=DNA_TIME_LIMIT, mode=mode)


@bp.route("/dna/start", methods=["POST"])
@student_required
def dna_start():
    body = _json_body()
    try:
        level = int(body.get("level", 1))
    except (TypeError, ValueError):
        level = 1
    mode = "rna" if body.get("mode") == "rna" else "dna"
    length = DNA_LEVELS.get(level, DNA_LEVELS[1])
    strand, answer = quiz.dna_round(length, mode)
    rid = _new_round("dna", {"strand": strand, "level": level, "mode": mode}, answer, topic=mode)
    return jsonify(round_id=rid, strand=strand, time_limit=DNA_TIME_LIMIT)


@bp.route("/dna/<int:rid>/submit", methods=["POST"])
@student_required
def dna_submit(rid):
    r = _open_round(rid, "dna")
    answer = json.loads(r["answer"])
    guess = str(_json_body().get("answer", "")).upper()[:len(answer)]
    elapsed = (_now() - datetime.fromisoformat(r["started_at"])).total_seconds()
    results = [i < len(guess) and guess[i] == a for i, a in enumerate(answer)]
    correct = sum(results) if elapsed <= DNA_TIME_LIMIT + 5 else 0  # 시간 초과면 0점
    perfect = correct == len(answer)
    level = json.loads(r["payload"])["level"]
    _finish(rid, correct, len(answer))
    return jsonify(correct=correct, total=len(answer), results=results, answer=answer, level=level,
                   perfect=perfect, elapsed=round(elapsed, 1), timeout=elapsed > DNA_TIME_LIMIT + 5)


# ---------- 객관식 공통 (샤가프 / 통합과학 퀴즈) ----------

_PUBLIC_KEYS = ("question", "choices", "kind", "prompt", "sub", "tiles", "n", "hint", "tag", "items", "bins", "unit", "say", "lines")
_TEXT_KINDS = ("spell", "num")
_LIST_KINDS = ("sort", "order")


def _public(items):
    return [{k: it[k] for k in _PUBLIC_KEYS if k in it} for it in items]


def _num(text):
    try:
        return float(str(text).replace(",", "").replace(" ", ""))
    except ValueError:
        return None


def _is_right(it, pick):
    kind = it.get("kind")
    if kind == "spell":
        return isinstance(pick, str) and pick.strip().lower() == it["answer_text"]
    if kind == "num":
        v = _num(pick) if isinstance(pick, str) else None
        return v is not None and abs(v - it["answer_num"]) < 1e-6
    if kind in _LIST_KINDS:
        return isinstance(pick, list) and pick == it["answer_list"]
    return isinstance(pick, int) and pick == it["answer_index"]


def _labels(it, pick):
    kind = it.get("kind")
    if kind in _TEXT_KINDS:
        unit = (" " + it["unit"]) if kind == "num" and pick not in (None, -1, "") else ""
        return ((pick + unit) if isinstance(pick, str) and pick else "(입력 안 함)"), it["answer_text"]
    if kind == "sort":                                  # 틀린 항목만 적는다
        ans = it["answer_list"]
        if not isinstance(pick, list):
            return "(안 함)", " / ".join(f"{x}→{it['bins'][b]}" for x, b in zip(it["items"], ans))
        bad = [k for k, b in enumerate(pick) if b != ans[k]]
        if not bad:
            return "모두 맞음", "모두 맞음"
        return (" / ".join(f"{it['items'][k]}→{it['bins'][pick[k]]}" for k in bad),
                " / ".join(f"{it['items'][k]}→{it['bins'][ans[k]]}" for k in bad))
    if kind == "order":
        def seq(p):
            return " → ".join(it["items"][k] for k in p)
        return (seq(pick) if isinstance(pick, list) else "(안 함)"), it["answer_text"]
    mine = it["choices"][pick] if isinstance(pick, int) and 0 <= pick < len(it["choices"]) else "(선택 안 함)"
    return mine, it["choices"][it["answer_index"]]


def _clean_pick(it, pick):
    """보낸 답을 형식에 맞게 다듬는다. 형식이 틀리면 400."""
    kind = it.get("kind")
    if kind in _TEXT_KINDS:
        if not isinstance(pick, str):
            abort(400)
        return pick.strip().lower()[:40]
    if kind in _LIST_KINDS:
        n = len(it["items"])
        hi = len(it["bins"]) if kind == "sort" else n
        if not isinstance(pick, list) or len(pick) != n or not all(isinstance(x, int) and 0 <= x < hi for x in pick):
            abort(400)
        if kind == "order" and len(set(pick)) != n:
            abort(400)
        return pick
    if not isinstance(pick, int):
        abort(400)
    return pick if 0 <= pick < len(it["choices"]) else -1


def _check_mc(r):
    """한 문제 바로 채점. 한 번 고른 답은 바꿀 수 없다(다시 보내면 처음 답을 돌려준다)."""
    items = json.loads(r["answer"])
    body = _json_body()
    i = body.get("i")
    if not isinstance(i, int) or not 0 <= i < len(items):
        abort(400)
    it = items[i]
    pick = _clean_pick(it, body.get("pick"))
    picks = json.loads(r["picks"] or "null") or [None] * len(items)
    if picks[i] is None:
        picks[i] = pick
        execute("UPDATE game_rounds SET picks = ? WHERE id = ?", (json.dumps(picks, ensure_ascii=False), r["id"]))
    done = [p for p in picks if p is not None]
    score = sum(1 for k, p in enumerate(picks) if p is not None and _is_right(items[k], p))
    return jsonify(correct=_is_right(it, picks[i]), pick=picks[i], answer_index=it.get("answer_index"),
                   answer_text=it.get("answer_text"), answer_list=it.get("answer_list"),
                   explanation=it["explanation"], answered=len(done), score=score, total=len(items))


def _grade_mc(r, label, after=None):
    items = json.loads(r["answer"])
    stored = json.loads(r["picks"] or "null")
    picks = [(-1 if p is None else p) for p in stored] if stored else _json_body().get("answers")
    if not isinstance(picks, list):
        abort(400)
    results = []
    for i, it in enumerate(items):
        pick = picks[i] if i < len(picks) and isinstance(picks[i], (int, str, list)) else -1
        mine, right = _labels(it, pick)
        results.append({"correct": _is_right(it, pick), "pick": pick, "answer_index": it.get("answer_index"),
                        "mine": mine, "answer": right, "explanation": it["explanation"]})
    score = sum(x["correct"] for x in results)
    _finish(r["id"], score, len(items))
    if after:
        after(items, results)
    return jsonify(score=score, total=len(items), results=results)


@bp.route("/chargaff")
@student_required
def chargaff():
    return render_template("student/games/mc.html", game="chargaff", title="샤가프 법칙", parent="sci",
                           intro="A=T, G=C. 전사된 RNA 문제 포함 5문제.", topics=None)


@bp.route("/chargaff/start", methods=["POST"])
@student_required
def chargaff_start():
    items = quiz.chargaff_round()
    rid = _new_round("chargaff", _public(items), items)
    return jsonify(round_id=rid, questions=_public(items), source="generated")


@bp.route("/chargaff/<int:rid>/check", methods=["POST"])
@student_required
def chargaff_check(rid):
    return _check_mc(_open_round(rid, "chargaff"))


@bp.route("/chargaff/<int:rid>/submit", methods=["POST"])
@student_required
def chargaff_submit(rid):
    return _grade_mc(_open_round(rid, "chargaff"), "샤가프 법칙")


@bp.route("/mixed")
@student_required
def mixed():
    return render_template("student/games/mc.html", game="mixed", title="섞어 풀기", parent="sci",
                           intro="TOPIC 여러 개에서 10문제. O/X, ㄱㄴㄷ, 4지선다, 분류, 순서, 계산.",
                           topics=[("all", "통합과학 1 + 2"), ("1", "통합과학 1 (TOPIC 01~19)"), ("2", "통합과학 2 (TOPIC 20~34)")],
                           topic_label="범위", pick=request.args.get("part", "all"))


@bp.route("/mixed/start", methods=["POST"])
@student_required
def mixed_start():
    part = {"1": 1, "2": 2}.get(str(_json_body().get("topic", "")))
    items = quiz.mixed_quiz(part=part)
    rid = _new_round("mixed", _public(items), items, topic=str(part or ""))
    return jsonify(round_id=rid, questions=_public(items))


@bp.route("/mixed/<int:rid>/check", methods=["POST"])
@student_required
def mixed_check(rid):
    return _check_mc(_open_round(rid, "mixed"))


@bp.route("/mixed/<int:rid>/submit", methods=["POST"])
@student_required
def mixed_submit(rid):
    return _grade_mc(_open_round(rid, "mixed"), "섞어 풀기")


# ---------- 스피드 O/X (영단어 · 통과 공통): 60초 동안 많이 맞히기 ----------

SPEED_SECONDS = 60
SPEED = {"vocab_speed": ("영단어 스피드 O/X", "단어와 뜻이 맞으면 O, 틀리면 X. 제한 60초.", "vocab"),
         "sci_speed": ("O/X 스피드", "개념 문장이 옳으면 O, 틀리면 X. 제한 60초.", "sci")}


@bp.route("/speed/<kind>")
@student_required
def speed(kind):
    if kind not in SPEED:
        abort(404)
    title, intro, parent = SPEED[kind]
    best = _best().get(kind + ":")
    return render_template("student/games/speed.html", kind=kind, title=title, intro=intro, parent=parent,
                           seconds=SPEED_SECONDS, best=best)


@bp.route("/speed/<kind>/start", methods=["POST"])
@student_required
def speed_start(kind):
    if kind not in SPEED:
        abort(404)
    items = vocab.speed_items(g.user["id"]) if kind == "vocab_speed" else quiz.speed_items()
    rid = _new_round(kind, [], items)
    return jsonify(round_id=rid, seconds=SPEED_SECONDS, items=items)


@bp.route("/speed/<kind>/<int:rid>/submit", methods=["POST"])
@student_required
def speed_submit(kind, rid):
    r = _open_round(rid, kind)
    items = json.loads(r["answer"])
    picks = _json_body().get("picks")
    if not isinstance(picks, list):
        abort(400)
    picks = [p if isinstance(p, bool) else None for p in picks[:len(items)]]
    score = sum(1 for i, p in enumerate(picks) if p is not None and p == items[i]["ok"])
    tried = sum(1 for p in picks if p is not None)
    execute("UPDATE game_rounds SET score = ?, total = ?, finished_at = ? WHERE id = ?",
            (score, max(tried, 1), _now().isoformat(timespec="seconds"), rid))
    if kind == "vocab_speed":
        for i, p in enumerate(picks):
            if p is not None:
                vocab.mark(g.user["id"], items[i]["word"], p == items[i]["ok"])
    best = query("SELECT MAX(score) AS m FROM game_rounds WHERE user_id = ? AND game = ? AND finished_at IS NOT NULL",
                 (g.user["id"], kind), one=True)["m"]
    return jsonify(score=score, tried=tried, best=best,
                   missed=[{"q": items[i]["q"], "a": items[i]["a"], "ok": items[i]["ok"], "exp": items[i]["exp"]}
                           for i, p in enumerate(picks) if p is not None and p != items[i]["ok"]][:10])


@bp.route("/quiz", endpoint="quiz")
@student_required
def quiz_page():
    pick = request.args.get("topic", "")
    title = f"TOPIC {pick} {quiz.TOPICS[pick][0]}" if pick in quiz.TOPICS else "TOPIC 퀴즈"
    return render_template("student/games/mc.html", game="quiz", title=title, pick=pick, parent="sci",
                           intro="8문제. O/X, ㄱㄴㄷ 보기, 4지선다, 분류·순서·계산이 섞여 나옵니다.", topic_label="TOPIC",
                           topics=[(k, f"TOPIC {k} {v[0]}") for k, v in quiz.TOPICS.items()])


@bp.route("/quiz/start", methods=["POST"])
@student_required
def quiz_start():
    topic = str(_json_body().get("topic", ""))
    if topic not in quiz.TOPICS:
        abort(400)
    items = quiz.bank_quiz(topic)
    rid = _new_round("quiz", _public(items), items, topic=topic)
    return jsonify(round_id=rid, questions=_public(items))


@bp.route("/quiz/<int:rid>/check", methods=["POST"])
@student_required
def quiz_check(rid):
    return _check_mc(_open_round(rid, "quiz"))


@bp.route("/quiz/<int:rid>/submit", methods=["POST"])
@student_required
def quiz_submit(rid):
    r = _open_round(rid, "quiz")
    label = quiz.TOPICS.get(r["topic"], ("퀴즈",))[0]
    return _grade_mc(r, f"퀴즈({label})")


# ---------- 영단어 (하루 20개 · 복습) ----------

@bp.route("/vocab")
@student_required
def vocab_page():
    day, words = vocab.today_set(g.user["id"])
    return render_template("student/games/vocab.html", day=day, words=[(w, vocab.MEANING[w]) for w in words],
                           v=vocab.stats(g.user["id"]), game="vocab", parent="vocab")


@bp.route("/vocab/start", methods=["POST"])
@student_required
def vocab_start():
    day, words = vocab.today_set(g.user["id"])
    items = vocab.quiz_items(words)
    rid = _new_round("vocab", _public(items), items, topic=day["day"])
    return jsonify(round_id=rid, questions=_public(items))


@bp.route("/vocab/<int:rid>/check", methods=["POST"])
@student_required
def vocab_check(rid):
    return _check_mc(_open_round(rid, "vocab"))


@bp.route("/vocab/<int:rid>/submit", methods=["POST"])
@student_required
def vocab_submit(rid):
    r = _open_round(rid, "vocab")
    return _grade_mc(r, "영단어", after=lambda items, res: vocab.record(g.user["id"], items, res, day=r["topic"]))


@bp.route("/vocab/review")
@student_required
def vocab_review():
    n = len(vocab.review_words(g.user["id"], limit=999))
    return render_template("student/games/mc.html", game="vocab_review", title="영단어 복습", topics=None, empty=n == 0, parent="vocab",
                           intro=f"틀린 단어 {n}개 중 최근 {min(n, vocab.DAILY)}개. 맞히면 목록에서 빠집니다."
                           if n else "복습할 단어가 없습니다.")


@bp.route("/vocab/review/start", methods=["POST"])
@student_required
def vocab_review_start():
    words = vocab.review_words(g.user["id"])
    if not words:
        abort(400)
    items = vocab.quiz_items(words)
    rid = _new_round("vocab_review", _public(items), items)
    return jsonify(round_id=rid, questions=_public(items))


@bp.route("/vocab/review/<int:rid>/check", methods=["POST"])
@student_required
def vocab_review_check(rid):
    return _check_mc(_open_round(rid, "vocab_review"))


@bp.route("/vocab/review/<int:rid>/submit", methods=["POST"])
@student_required
def vocab_review_submit(rid):
    r = _open_round(rid, "vocab_review")
    return _grade_mc(r, "영단어 복습", after=lambda items, res: vocab.record(g.user["id"], items, res))


# ---------- 영단어 짝 맞추기: 오늘의 단어를 5쌍씩 ----------

@bp.route("/vocab/match")
@student_required
def vocab_match():
    return render_template("student/games/match.html", best=_best().get("vocab_match:"))


@bp.route("/vocab/match/start", methods=["POST"])
@student_required
def vocab_match_start():
    _, words = vocab.today_set(g.user["id"])
    sets = vocab.match_sets(words)
    rid = _new_round("vocab_match", [], [w for st in sets for w in st])
    return jsonify(round_id=rid, sets=sets)


@bp.route("/vocab/match/<int:rid>/submit", methods=["POST"])
@student_required
def vocab_match_submit(rid):
    r = _open_round(rid, "vocab_match")
    words = [x["w"] for x in json.loads(r["answer"])]
    body = _json_body()
    wrong = {w for w in body.get("wrong", []) if isinstance(w, str)} & set(words)
    for w in words:
        vocab.mark(g.user["id"], w, w not in wrong)
    secs = body.get("seconds")
    secs = round(float(secs), 1) if isinstance(secs, (int, float)) and 0 < secs < 3600 else None
    _finish(rid, len(words) - len(wrong), len(words))
    return jsonify(score=len(words) - len(wrong), total=len(words), seconds=secs, wrong=sorted(wrong))


# ---------- 영단어 카드 뒤집기: 12장을 뒤집어 단어와 뜻 짝 찾기 ----------

@bp.route("/vocab/memory")
@student_required
def vocab_memory():
    return render_template("student/games/memory.html", best=_best().get("vocab_memory:"))


@bp.route("/vocab/memory/start", methods=["POST"])
@student_required
def vocab_memory_start():
    _, words = vocab.today_set(g.user["id"])
    ws, cards = vocab.memory_cards(words)
    rid = _new_round("vocab_memory", [], ws)
    return jsonify(round_id=rid, cards=cards)


@bp.route("/vocab/memory/<int:rid>/submit", methods=["POST"])
@student_required
def vocab_memory_submit(rid):
    """점수 = 짝 수, 총점 = 뒤집은 횟수(두 장 한 번). 한 번도 안 틀리면 100%."""
    r = _open_round(rid, "vocab_memory")
    pairs = len(json.loads(r["answer"]))
    body = _json_body()
    tries = body.get("tries")
    tries = tries if isinstance(tries, int) and pairs <= tries < 1000 else pairs * 4
    secs = body.get("seconds")
    secs = round(float(secs), 1) if isinstance(secs, (int, float)) and 0 < secs < 3600 else None
    _finish(rid, pairs, tries)
    return jsonify(pairs=pairs, tries=tries, seconds=secs, words=[(w, vocab.MEANING[w]) for w in json.loads(r["answer"])])
