"""학생 미니게임: 염기 짝 맞추기, 샤가프 법칙, 통합과학 퀴즈.
문제와 정답은 서버에서 만들어 game_rounds 에 저장하고, 채점도 서버에서만 한다."""
import json
from datetime import datetime, timedelta

from flask import Blueprint, abort, g, jsonify, render_template, request

import quiz
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


@bp.route("/")
@student_required
def hub():
    best = {r["game"]: r for r in query("""SELECT game, MAX(score * 100 / total) AS best, COUNT(*) AS plays
                                           FROM game_rounds WHERE user_id = ? AND finished_at IS NOT NULL
                                           GROUP BY game""", (g.user["id"],))}
    return render_template("student/games/hub.html", best=best)


# ---------- 염기 짝 맞추기 ----------

@bp.route("/dna")
@student_required
def dna():
    return render_template("student/games/dna.html", levels=DNA_LEVELS, time_limit=DNA_TIME_LIMIT)


@bp.route("/dna/start", methods=["POST"])
@student_required
def dna_start():
    try:
        level = int(_json_body().get("level", 1))
    except (TypeError, ValueError):
        level = 1
    length = DNA_LEVELS.get(level, DNA_LEVELS[1])
    strand, answer = quiz.dna_round(length)
    rid = _new_round("dna", {"strand": strand, "level": level}, answer)
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

def _public(items):
    return [{"question": it["question"], "choices": it["choices"]} for it in items]


def _check_mc(r):
    """한 문제 바로 채점. 한 번 고른 답은 바꿀 수 없다(다시 보내면 처음 답을 돌려준다)."""
    items = json.loads(r["answer"])
    body = _json_body()
    i, pick = body.get("i"), body.get("pick")
    if not isinstance(i, int) or not 0 <= i < len(items) or not isinstance(pick, int):
        abort(400)
    picks = json.loads(r["picks"] or "null") or [None] * len(items)
    if picks[i] is None:
        picks[i] = pick if 0 <= pick < len(items[i]["choices"]) else -1
        execute("UPDATE game_rounds SET picks = ? WHERE id = ?", (json.dumps(picks), r["id"]))
    it = items[i]
    done = [p for p in picks if p is not None]
    score = sum(1 for k, p in enumerate(picks) if p is not None and p == items[k]["answer_index"])
    return jsonify(correct=picks[i] == it["answer_index"], pick=picks[i], answer_index=it["answer_index"],
                   explanation=it["explanation"], answered=len(done), score=score, total=len(items))


def _grade_mc(r, label):
    items = json.loads(r["answer"])
    stored = json.loads(r["picks"] or "null")
    picks = [(-1 if p is None else p) for p in stored] if stored else _json_body().get("answers")
    if not isinstance(picks, list):
        abort(400)
    results = []
    for i, it in enumerate(items):
        pick = picks[i] if i < len(picks) and isinstance(picks[i], int) else -1
        results.append({"correct": pick == it["answer_index"], "pick": pick,
                        "answer_index": it["answer_index"], "explanation": it["explanation"]})
    score = sum(x["correct"] for x in results)
    _finish(r["id"], score, len(items))
    return jsonify(score=score, total=len(items), results=results)


@bp.route("/chargaff")
@student_required
def chargaff():
    return render_template("student/games/mc.html", game="chargaff", title="샤가프 법칙",
                           intro="DNA 이중 나선에서 A=T, G=C. 샤가프 법칙으로 염기 비율을 계산해 보세요.", topics=None)


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


@bp.route("/quiz", endpoint="quiz")
@student_required
def quiz_page():
    return render_template("student/games/mc.html", game="quiz", title="통합과학 퀴즈",
                           intro="단원을 고르면 4지선다 5문제가 나와요. 한 문제씩 고르면 바로 정답과 해설이 나와요.",
                           topics=[(k, v[0]) for k, v in quiz.TOPICS.items()])


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
