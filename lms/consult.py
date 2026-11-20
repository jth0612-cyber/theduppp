"""학습상담: 학생이 상담받을 조교를 고른다(시대인재 TA 지정처럼). 건당으로 세고, 학생 평가로 조교 간 비교가 보인다.
- 지정한 조교(와 강사)만 답할 수 있다. 지정하지 않으면 아무 조교나 먼저 답한다.
- 한 건 = 학습상담 질문 하나. 그 질문의 첫 답변을 단 조교의 건수로, 첫 답변이 달린 달에 센다."""
from datetime import date

from db import query


def assistants():
    return query("SELECT id, display_name, username, ta_intro FROM users WHERE role = 'assistant' AND disabled = 0 ORDER BY display_name")


def ta_cards():
    """학생이 조교를 고를 때 보는 정보: 소개, 이번 달·누적 상담 건수, 평균 평점, 첫 답변까지 걸린 시간(중앙값 대신 평균)."""
    month = date.today().strftime("%Y-%m")
    stats = {r["u"]: r for r in query("""
        SELECT a.author_id AS u, COUNT(*) AS total,
               SUM(strftime('%Y-%m', a.created_at) = ?) AS month,
               AVG(q.rating) AS rating, COUNT(q.rating) AS n_rating,
               AVG((julianday(a.created_at) - julianday(q.created_at)) * 24) AS hours
        FROM questions q JOIN answers a ON a.id = (SELECT MIN(x.id) FROM answers x WHERE x.question_id = q.id)
        WHERE q.qtype = '학습상담' GROUP BY a.author_id""", (month,))}
    out = []
    for t in assistants():
        s = stats.get(t["id"])
        out.append({"id": t["id"], "name": t["display_name"] or t["username"], "intro": t["ta_intro"],
                    "month": (s["month"] or 0) if s else 0, "total": s["total"] if s else 0,
                    "rating": round(s["rating"], 1) if s and s["rating"] else None, "n_rating": s["n_rating"] if s else 0,
                    "hours": round(s["hours"], 1) if s and s["hours"] is not None else None})
    return out


def consult_counts(month):
    """{조교 id: 그 달 학습상담 건수}"""
    return {r["u"]: r["n"] for r in query("""
        SELECT a.author_id AS u, COUNT(*) AS n FROM questions q
        JOIN answers a ON a.id = (SELECT MIN(x.id) FROM answers x WHERE x.question_id = q.id)
        WHERE q.qtype = '학습상담' AND strftime('%Y-%m', a.created_at) = ? GROUP BY a.author_id""", (month,))}


def can_answer(q, user):
    """지정된 학습상담은 그 조교와 강사만."""
    return not (q["qtype"] == "학습상담" and q["assignee_id"] and user["role"] == "assistant" and q["assignee_id"] != user["id"])
