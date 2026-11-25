"""수업 일정: 진도 그룹(같은 진도로 묶은 반) · 주차(토~금) · 수업 칸(반 × 주차 × 시간표 칸) · 배부 교재 · 출석.

- 한 반은 진도 그룹 하나. 단과·재종은 그룹을 따로 만든다 (수업 길이·휴강이 달라 주차별 진도가 다르다).
- 주차는 기본 토~금. 토요일반이 가장 먼저, 금요일반이 가장 늦게 같은 진도를 나간다.
- 교재 한 권은 기본으로 한 주차(그 주 모든 수업)에 배정하고, 수업 칸마다 빼거나 더 넣는다.
- 수업 칸 명단 = 그 반 재원생 + 다른 반에서 와서 들은 학생. 교재는 출석(지각 포함)한 학생 수만큼 배부.
"""
from datetime import date, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from db import execute, get_db, query
from security import audit, staff_required

bp = Blueprint("schedule", __name__, url_prefix="/t")

WEEKDAYS = "월화수목금토일"
WEEK_ORDER = [5, 6, 0, 1, 2, 3, 4]                         # 한 주차 = 토 일 월 화 수 목 금
HANDOUT_KINDS = ["라인업", "프레이밍", "로직빌드", "스퀴즈", "시퀀스", "필기노트", "기타"]
STATES = ["출석", "지각", "조퇴", "결석", "다른 반"]
GOT = ("출석", "지각", "조퇴")                                # 교재를 받는 출석 상태


def hkey(h):
    """교재 정렬: 구분 순서(라인업 → … → 필기노트 → 기타), 이름 안의 숫자는 숫자 순서 (2호 < 10호)."""
    import re
    k = HANDOUT_KINDS.index(h["kind"]) if h["kind"] in HANDOUT_KINDS else len(HANDOUT_KINDS)
    return (k, [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", h["title"])])


def _d(s):
    return date.fromisoformat(s)


def _saturday(d):
    return d - timedelta(days=(d.weekday() - 5) % 7)


def _day_in(starts, ends, weekday):
    """주차 [starts, ends] 안에서 그 요일의 첫 날짜. 없으면 None."""
    d = _d(starts)
    d += timedelta(days=(weekday - d.weekday()) % 7)
    return d.isoformat() if d <= _d(ends) else None


def sync_group(gid):
    """그룹의 반·주차·시간표 칸에 맞춰 수업 칸을 만들고 날짜를 맞춘다. 반에서 빠진 칸·주차 밖 칸은 지운다."""
    db = get_db()
    weeks = db.execute("SELECT * FROM group_weeks WHERE group_id = ?", (gid,)).fetchall()
    slots = db.execute("""SELECT t.* FROM timetable t JOIN classes c ON c.id = t.class_id
                          WHERE c.group_id = ?""", (gid,)).fetchall()
    want = set()
    for w in weeks:
        for t in slots:
            day = _day_in(w["starts"], w["ends"], t["weekday"])
            if not day:
                continue
            want.add((w["id"], t["id"]))
            db.execute("""INSERT INTO sessions (week_id, class_id, slot_id, day) VALUES (?, ?, ?, ?)
                          ON CONFLICT (week_id, slot_id) DO UPDATE SET day = excluded.day""", (w["id"], t["class_id"], t["id"], day))
    for s in db.execute("""SELECT s.id, s.week_id, s.slot_id FROM sessions s JOIN group_weeks w ON w.id = s.week_id
                           WHERE w.group_id = ?""", (gid,)).fetchall():
        if (s["week_id"], s["slot_id"]) not in want:
            db.execute("DELETE FROM sessions WHERE id = ?", (s["id"],))
    db.commit()
    sync_sys_attendance(gid)


def _sys_state(text):
    t = str(text or "")
    return next((k for k in ("결석", "조퇴", "지각", "출석") if k in t), None)


def sync_sys_attendance(gid=None):
    """조교 시스템(시트) 출결 → 같은 날 그 학생 반의 수업 칸 출석. 비어 있거나 시트에서 채운 칸만 바꾸고, 손으로 고친 값은 그대로 둔다.
    시트를 받을 때(views/link.py)와 수업 칸이 새로 생길 때(sync_group) 부른다. 반환: 채운 칸 수."""
    import json
    from sysdata import _day
    db = get_db()
    rows = db.execute("""SELECT r.data, c.student_id, st.class_id FROM sys_rows r
                         JOIN student_codes c ON c.code = r.code AND c.student_id IS NOT NULL
                         JOIN students st ON st.id = c.student_id WHERE r.tbl = '출결'""").fetchall()
    if not rows:
        return 0
    where, args = ("AND w.group_id = ?", [gid]) if gid else ("", [])
    sess = {}
    for s in db.execute(f"SELECT s.id, s.class_id, s.day FROM sessions s JOIN group_weeks w ON w.id = s.week_id WHERE 1 = 1 {where}", args):
        sess.setdefault((s["class_id"], s["day"]), []).append(s["id"])
    n = 0
    for r in rows:
        d = json.loads(r["data"])
        state = _sys_state(d.get("출결"))
        for sid in sess.get((r["class_id"], _day(d.get("날짜"))), []) if state else []:
            cur = db.execute("""INSERT INTO session_students (session_id, student_id, state, src) VALUES (?, ?, ?, '시트')
                                ON CONFLICT (session_id, student_id) DO UPDATE SET state = excluded.state, src = '시트'
                                WHERE session_students.state = '' OR session_students.src = '시트'""", (sid, r["student_id"], state))
            n += cur.rowcount
    db.commit()
    return n


def _group(gid):
    return query("SELECT * FROM course_groups WHERE id = ?", (gid,), one=True) or abort(404)


def _breaks():
    return query("SELECT class_id, starts, ends, note FROM class_breaks")


def _on_break(brks, class_id, day):
    return next((b for b in brks if (b["class_id"] in (None, class_id)) and b["starts"] <= day <= b["ends"]), None)


def week_handouts(week_ids):
    out = {}
    if week_ids:
        q = ",".join("?" * len(week_ids))
        for r in query(f"""SELECT wh.week_id, h.* FROM week_handouts wh JOIN handouts h ON h.id = wh.handout_id
                           WHERE wh.week_id IN ({q}) ORDER BY h.kind, h.title""", list(week_ids)):
            out.setdefault(r["week_id"], []).append(r)
    return {k: sorted(v, key=hkey) for k, v in out.items()}


def session_view(rows, brks):
    """수업 칸 목록에 교재(주차 교재 − 뺀 것 + 넣은 것), 명단·출석 수, 휴강 여부를 붙인다."""
    if not rows:
        return []
    ids = [r["id"] for r in rows]
    q = ",".join("?" * len(ids))
    wh = week_handouts({r["week_id"] for r in rows})
    ex = {}
    for r in query(f"""SELECT sh.session_id, sh.mode, h.* FROM session_handouts sh JOIN handouts h ON h.id = sh.handout_id
                       WHERE sh.session_id IN ({q})""", ids):
        ex.setdefault(r["session_id"], []).append(r)
    marks = {}
    for r in query(f"SELECT session_id, state, guest FROM session_students WHERE session_id IN ({q})", ids):
        marks.setdefault(r["session_id"], []).append(r)
    members = {r["class_id"]: r["n"] for r in query("SELECT class_id, COUNT(*) AS n FROM students WHERE active = 1 GROUP BY class_id")}
    out = []
    for r in rows:
        s = dict(r)
        drop = {h["id"] for h in ex.get(r["id"], []) if h["mode"] == "drop"}
        hs = [dict(h, extra=False) for h in wh.get(r["week_id"], []) if h["id"] not in drop]
        hs += [dict(h, extra=True) for h in sorted(ex.get(r["id"], []), key=hkey) if h["mode"] == "add"]
        m = marks.get(r["id"], [])
        guests = sum(1 for x in m if x["guest"])
        moved = sum(1 for x in m if x["state"] == "다른 반" and not x["guest"])
        brk = _on_break(brks, r["class_id"], r["day"]) if r["status"] == "수업" else None
        s.update(handouts=hs, dropped=drop, roster=members.get(r["class_id"], 0) + guests - moved,
                 present=sum(1 for x in m if x["state"] in GOT), checked=sum(1 for x in m if x["state"]),
                 guests=guests, brk=brk, off=r["status"] == "휴강" or bool(brk) or bool(r["week_off"]))
        out.append(s)
    return out


def handout_counts(sessions):
    """교재별 배부 수: 출석 체크가 끝난 칸은 출석 수, 아직이면 명단 수(예정)."""
    tot = {}
    for s in sessions:
        if s["off"]:
            continue
        for h in s["handouts"]:
            t = tot.setdefault(h["id"], {"h": h, "given": 0, "plan": 0})
            if s["checked"]:
                t["given"] += s["present"]
            else:
                t["plan"] += s["roster"]
    return sorted(tot.values(), key=lambda t: hkey(t["h"]))


SESSION_SQL = """SELECT s.*, w.week_no, w.off AS week_off, w.group_id, c.name AS class_name, t.weekday, t.starts, t.ends,
                        t.period, t.hall, t.room
                 FROM sessions s JOIN group_weeks w ON w.id = s.week_id JOIN classes c ON c.id = s.class_id
                 JOIN timetable t ON t.id = s.slot_id"""


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- 진도 그룹 목록
@bp.route("/schedule", methods=["GET", "POST"])
@staff_required
def groups():
    if request.method == "POST":
        name = request.form.get("name", "").strip()[:40]
        track = request.form.get("track") if request.form.get("track") in ("단과", "재종") else "재종"
        try:
            first = _saturday(_d(request.form.get("first", "")))
        except ValueError:
            first = None
        n = max(1, min(60, _int(request.form.get("weeks")) or 20))
        if not name or not first:
            flash("그룹 이름과 1주차 날짜를 넣어 주세요.", "error")
            return redirect(url_for("schedule.groups"))
        gid = execute("INSERT INTO course_groups (name, track) VALUES (?, ?)", (name, track))
        db = get_db()
        for k in range(n):
            s = first + timedelta(days=7 * k)
            db.execute("INSERT INTO group_weeks (group_id, week_no, starts, ends) VALUES (?, ?, ?, ?)",
                       (gid, k + 1, s.isoformat(), (s + timedelta(days=6)).isoformat()))
        for cid in request.form.getlist("class_id"):
            db.execute("UPDATE classes SET group_id = ? WHERE id = ? AND track = ? AND group_id IS NULL", (gid, _int(cid), track))
        db.commit()
        src = _int(request.form.get("copy_from"))
        if src:
            _copy_plan(src, gid)
        sync_group(gid)
        audit("group_create", f"group:{gid}")
        flash(f"'{name}' 진도 그룹을 만들었어요 ({n}주).", "ok")
        return redirect(url_for("schedule.group", gid=gid))
    rows = query("""SELECT g.*, (SELECT COUNT(*) FROM classes c WHERE c.group_id = g.id) AS n_class,
                           (SELECT COUNT(*) FROM students s JOIN classes c ON c.id = s.class_id WHERE c.group_id = g.id AND s.active = 1) AS n_student,
                           (SELECT MIN(starts) FROM group_weeks WHERE group_id = g.id) AS first,
                           (SELECT MAX(ends) FROM group_weeks WHERE group_id = g.id) AS last,
                           (SELECT COUNT(*) FROM group_weeks WHERE group_id = g.id) AS n_week
                    FROM course_groups g ORDER BY g.track, g.name""")
    classes = query("""SELECT c.id, c.name, c.track, c.group_id, g.name AS group_name,
                              (SELECT COUNT(*) FROM students s WHERE s.class_id = c.id AND s.active = 1) AS n,
                              (SELECT COUNT(*) FROM timetable t WHERE t.class_id = c.id) AS n_slot
                       FROM classes c LEFT JOIN course_groups g ON g.id = c.group_id
                       WHERE c.archived = 0 AND c.is_test = 0 ORDER BY c.track, c.name""")
    return render_template("schedule/groups.html", groups=rows, classes=classes,
                           next_sat=_saturday(date.today() + timedelta(days=6)).isoformat())


def _copy_plan(src, dst):
    """다른 그룹의 주차별 진도·교재·시험 회차를 주차 번호대로 가져온다 (날짜는 그대로)."""
    db = get_db()
    dw = {r["week_no"]: r["id"] for r in db.execute("SELECT id, week_no FROM group_weeks WHERE group_id = ?", (dst,))}
    for w in db.execute("SELECT * FROM group_weeks WHERE group_id = ?", (src,)).fetchall():
        if w["week_no"] in dw:
            db.execute("UPDATE group_weeks SET topic = ?, review_round = ?, mock_round = ? WHERE id = ?",
                       (w["topic"], w["review_round"], w["mock_round"], dw[w["week_no"]]))
            db.execute("""INSERT OR IGNORE INTO week_handouts (week_id, handout_id)
                          SELECT ?, handout_id FROM week_handouts WHERE week_id = ?""", (dw[w["week_no"]], w["id"]))
    db.commit()


# ---------------------------------------------------------------- 그룹 화면 (주차 × 수업 칸 표 / 달력)
@bp.route("/schedule/<int:gid>")
@staff_required
def group(gid):
    g = _group(gid)
    weeks = query("SELECT * FROM group_weeks WHERE group_id = ? ORDER BY week_no", (gid,))
    classes = query("SELECT * FROM classes WHERE group_id = ? ORDER BY name", (gid,))
    slots = query("""SELECT t.*, c.name AS class_name FROM timetable t JOIN classes c ON c.id = t.class_id
                     WHERE c.group_id = ?""", (gid,))
    # 열 순서 = 주차 안에서 수업 순서 (토요일반이 맨 앞)
    slots = sorted(slots, key=lambda t: (WEEK_ORDER.index(t["weekday"]), t["starts"], t["class_name"]))
    brks = _breaks()
    sess = session_view(query(SESSION_SQL + " WHERE w.group_id = ?", (gid,)), brks)
    cell = {(s["week_id"], s["slot_id"]): s for s in sess}
    wh = week_handouts([w["id"] for w in weeks])
    by_week = {}
    for s in sess:
        by_week.setdefault(s["week_id"], []).append(s)
    week_tot = {w["id"]: handout_counts(by_week.get(w["id"], [])) for w in weeks}
    members = query("""SELECT c.id, c.name, COUNT(s.id) AS n FROM classes c LEFT JOIN students s ON s.class_id = c.id AND s.active = 1
                       WHERE c.group_id = ? GROUP BY c.id ORDER BY c.name""", (gid,))
    others = query("""SELECT id, name FROM classes WHERE archived = 0 AND is_test = 0 AND track = ? AND group_id IS NULL
                      ORDER BY name""", (g["track"],))
    view = "cal" if request.args.get("view") == "cal" else "table"
    cal = []
    if view == "cal":
        for w in weeks:
            days = []
            d0 = _d(w["starts"])
            for k in range((_d(w["ends"]) - d0).days + 1):
                d = (d0 + timedelta(days=k)).isoformat()
                days.append({"day": d, "label": WEEKDAYS[(d0 + timedelta(days=k)).weekday()],
                             "sess": sorted([s for s in by_week.get(w["id"], []) if s["day"] == d], key=lambda s: s["starts"])})
            cal.append({"w": w, "days": days})
    return render_template("schedule/group.html", grp=g, weeks=weeks, slots=slots, cell=cell, wh=wh, week_tot=week_tot,
                           members=members, others=others, classes=classes, view=view, cal=cal, weekdays=WEEKDAYS,
                           handouts=sorted(query("SELECT * FROM handouts"), key=hkey), kinds=HANDOUT_KINDS,
                           groups=query("SELECT id, name FROM course_groups WHERE id != ? ORDER BY name", (gid,)),
                           today=date.today().isoformat(), total=sum(m["n"] for m in members))


@bp.route("/schedule/<int:gid>/edit", methods=["POST"])
@staff_required
def group_edit(gid):
    g = _group(gid)
    act = request.form.get("action")
    db = get_db()
    if act == "rename":
        name = request.form.get("name", "").strip()[:40]
        if name:
            db.execute("UPDATE course_groups SET name = ? WHERE id = ?", (name, gid))
    elif act == "add_class":
        db.execute("UPDATE classes SET group_id = ? WHERE id = ? AND track = ? AND group_id IS NULL",
                   (gid, _int(request.form.get("class_id")), g["track"]))
    elif act == "remove_class":
        db.execute("UPDATE classes SET group_id = NULL WHERE id = ? AND group_id = ?", (_int(request.form.get("class_id")), gid))
    elif act == "add_weeks":
        last = db.execute("SELECT week_no, ends FROM group_weeks WHERE group_id = ? ORDER BY week_no DESC LIMIT 1", (gid,)).fetchone()
        no, s = (last["week_no"], _d(last["ends"]) + timedelta(days=1)) if last else (0, _saturday(date.today()))
        for k in range(max(1, min(20, _int(request.form.get("n")) or 1))):
            st = s + timedelta(days=7 * k)
            db.execute("INSERT INTO group_weeks (group_id, week_no, starts, ends) VALUES (?, ?, ?, ?)",
                       (gid, no + k + 1, st.isoformat(), (st + timedelta(days=6)).isoformat()))
    elif act == "copy":
        db.commit()
        _copy_plan(_int(request.form.get("src")), gid)
    elif act == "delete":
        db.execute("UPDATE classes SET group_id = NULL WHERE group_id = ?", (gid,))
        db.execute("DELETE FROM course_groups WHERE id = ?", (gid,))
        db.commit()
        audit("group_delete", f"group:{gid}")
        flash("진도 그룹을 지웠어요. 반은 그대로 있어요.", "ok")
        return redirect(url_for("schedule.groups"))
    db.commit()
    sync_group(gid)
    audit("group_edit", f"group:{gid}:{act}")
    return redirect(url_for("schedule.group", gid=gid, view=request.form.get("view") or None))


@bp.route("/schedule/weeks/<int:wid>", methods=["POST"])
@staff_required
def week_edit(wid):
    w = query("SELECT * FROM group_weeks WHERE id = ?", (wid,), one=True) or abort(404)
    db = get_db()
    act = request.form.get("action", "save")
    if act == "save":
        try:
            st, en = _d(request.form.get("starts", "")), _d(request.form.get("ends", ""))
        except ValueError:
            st = en = None
        if not st or en < st or (en - st).days > 13:
            flash("주차 날짜를 확인해 주세요 (끝이 시작보다 앞이거나 2주를 넘어요).", "error")
        else:
            db.execute("""UPDATE group_weeks SET starts = ?, ends = ?, topic = ?, note = ?, review_round = ?, mock_round = ?
                          WHERE id = ?""", (st.isoformat(), en.isoformat(), request.form.get("topic", "").strip()[:80],
                                            request.form.get("note", "").strip()[:200], _int(request.form.get("review_round")),
                                            _int(request.form.get("mock_round")), wid))
            db.execute("DELETE FROM week_handouts WHERE week_id = ?", (wid,))
            for h in request.form.getlist("handout_id"):
                db.execute("INSERT OR IGNORE INTO week_handouts (week_id, handout_id) VALUES (?, ?)", (wid, _int(h)))
    elif act in ("off", "on"):
        # 휴강 주: 그 주 진도·교재·시험 회차를 다음 주차로 한 칸씩 민다 (휴강 해제는 반대로 당긴다)
        _shift(w, push=act == "off")
    db.commit()
    sync_group(w["group_id"])
    audit("week_edit", f"week:{wid}:{act}")
    return redirect(url_for("schedule.group", gid=w["group_id"], view=request.form.get("view") or None) + f"#w{w['week_no']}")


def _shift(w, push):
    """휴강 주 넣기(push): 이 주부터 진도를 한 주씩 뒤로. 해제: 뒤 주차 진도를 한 주씩 앞으로. 이미 휴강인 다른 주는 건너뛴다."""
    db = get_db()
    after = [r for r in db.execute("SELECT * FROM group_weeks WHERE group_id = ? AND week_no > ? ORDER BY week_no",
                                   (w["group_id"], w["week_no"])).fetchall() if not r["off"]]
    def plan(r):
        return (r["topic"], r["review_round"], r["mock_round"],
                [x[0] for x in db.execute("SELECT handout_id FROM week_handouts WHERE week_id = ?", (r["id"],))])
    if push:
        plans, targets = [plan(w)] + [plan(r) for r in after], after
    else:
        plans, targets = [plan(r) for r in after], [w] + after
    db.execute("UPDATE group_weeks SET off = ? WHERE id = ?", (1 if push else 0, w["id"]))
    for r in [w] + after:
        db.execute("UPDATE group_weeks SET topic = '', review_round = NULL, mock_round = NULL WHERE id = ?", (r["id"],))
        db.execute("DELETE FROM week_handouts WHERE week_id = ?", (r["id"],))
    for r, (topic, rr, mr, hs) in zip(targets, plans):
        db.execute("UPDATE group_weeks SET topic = ?, review_round = ?, mock_round = ? WHERE id = ?", (topic, rr, mr, r["id"]))
        for h in hs:
            db.execute("INSERT OR IGNORE INTO week_handouts (week_id, handout_id) VALUES (?, ?)", (r["id"], h))
    lost = [p for p in plans[len(targets):] if p[0] or p[3]]
    if lost:
        flash(f"마지막 {len(lost)}주 진도가 넘쳐 지워졌어요. 주차를 더 만든 뒤 휴강을 다시 넣어 주세요.", "error")


# ---------------------------------------------------------------- 수업 칸: 교재 넣기·빼기, 명단·출석
@bp.route("/schedule/sessions/<int:sid>", methods=["GET", "POST"])
@staff_required
def session(sid):
    row = query(SESSION_SQL + " WHERE s.id = ?", (sid,), one=True) or abort(404)
    db = get_db()
    if request.method == "POST":
        act = request.form.get("action")
        if act == "status" and request.form.get("status") in ("수업", "휴강", "보강"):
            db.execute("UPDATE sessions SET status = ?, note = ? WHERE id = ?",
                       (request.form["status"], request.form.get("note", "").strip()[:100], sid))
        elif act == "handout":
            hid, mode = _int(request.form.get("handout_id")), request.form.get("mode")
            if mode in ("add", "drop"):
                db.execute("""INSERT INTO session_handouts (session_id, handout_id, mode) VALUES (?, ?, ?)
                              ON CONFLICT (session_id, handout_id) DO UPDATE SET mode = excluded.mode""", (sid, hid, mode))
            else:
                db.execute("DELETE FROM session_handouts WHERE session_id = ? AND handout_id = ?", (sid, hid))
        elif act == "attend":
            for k, v in request.form.items():
                if k.startswith("st_") and v in STATES + [""]:
                    stid = _int(k[3:])
                    old = db.execute("SELECT state FROM session_students WHERE session_id = ? AND student_id = ?", (sid, stid)).fetchone()
                    if old is None or old["state"] != v:          # 바꾼 칸만 손으로 고친 값으로 (그대로 둔 시트 값은 시트 값)
                        db.execute("""INSERT INTO session_students (session_id, student_id, state, src) VALUES (?, ?, ?, '')
                                      ON CONFLICT (session_id, student_id) DO UPDATE SET state = excluded.state, src = ''""", (sid, stid, v))
        elif act == "all_present":
            for s in db.execute("SELECT id FROM students WHERE class_id = ? AND active = 1", (row["class_id"],)).fetchall():
                db.execute("""INSERT INTO session_students (session_id, student_id, state) VALUES (?, ?, '출석')
                              ON CONFLICT (session_id, student_id) DO UPDATE SET state = CASE WHEN state = '' THEN '출석' ELSE state END""",
                           (sid, s["id"]))
        elif act == "guest":
            key = request.form.get("q", "").strip()
            st = (query("SELECT id, class_id, name FROM students WHERE active = 1 AND student_no = ?", (key,))
                  or query("SELECT id, class_id, name FROM students WHERE active = 1 AND name = ?", (key,))) if key else []
            if len(st) != 1:
                flash("같은 이름이 여럿이에요. 아이디(출결 번호)로 찾아 주세요." if st else "학생을 찾지 못했어요.", "error")
            elif st[0]["class_id"] == row["class_id"]:
                flash(f"{st[0]['name']} 학생은 이 반 학생이에요.", "error")
            else:
                db.execute("""INSERT INTO session_students (session_id, student_id, state, guest) VALUES (?, ?, '출석', 1)
                              ON CONFLICT (session_id, student_id) DO UPDATE SET guest = 1""", (sid, st[0]["id"]))
                flash(f"{st[0]['name']} 학생을 이 수업 명단에 넣었어요.", "ok")
        elif act == "sys":
            n = sync_sys_attendance(row["group_id"])
            flash(f"조교 시스템 출결로 {n}칸을 채웠어요." if n else "가져올 조교 시스템 출결이 없어요.", "ok" if n else "error")
        elif act == "unguest":
            db.execute("DELETE FROM session_students WHERE session_id = ? AND student_id = ? AND guest = 1",
                       (sid, _int(request.form.get("student_id"))))
        db.commit()
        audit("session_edit", f"session:{sid}:{act}")
        return redirect(url_for("schedule.session", sid=sid))
    s = session_view([row], _breaks())[0]
    marks = {r["student_id"]: r for r in query("SELECT * FROM session_students WHERE session_id = ?", (sid,))}
    roster = [dict(r, state=marks[r["id"]]["state"] if r["id"] in marks else "", src=marks[r["id"]]["src"] if r["id"] in marks else "", guest=False)
              for r in query("SELECT id, name, student_no FROM students WHERE class_id = ? AND active = 1 ORDER BY name", (row["class_id"],))]
    roster += [dict(r, state=marks[r["id"]]["state"], src=marks[r["id"]]["src"], guest=True)
               for r in query("""SELECT s.id, s.name, s.student_no, c.name AS from_class FROM session_students x
                                 JOIN students s ON s.id = x.student_id JOIN classes c ON c.id = s.class_id
                                 WHERE x.session_id = ? AND x.guest = 1 ORDER BY s.name""", (sid,))]
    week_ids = {h["id"] for h in week_handouts([row["week_id"]]).get(row["week_id"], [])}
    allh = sorted(query("SELECT * FROM handouts"), key=hkey)
    have = week_ids | {h["id"] for h in s["handouts"]}
    return render_template("schedule/session.html", s=s, roster=roster, states=STATES, weekdays=WEEKDAYS, grp=_group(row["group_id"]),
                           dropped=[h for h in allh if h["id"] in s["dropped"]], extra=[h for h in allh if h["id"] not in have])


# ---------------------------------------------------------------- 배부 교재 목록
@bp.route("/handouts", methods=["GET", "POST"])
@staff_required
def handouts():
    if request.method == "POST":
        if request.form.get("action") == "delete":
            execute("DELETE FROM handouts WHERE id = ?", (_int(request.form.get("id")),))
        else:
            kind = request.form.get("kind") if request.form.get("kind") in HANDOUT_KINDS else "기타"
            titles = [t.strip()[:40] for t in request.form.get("title", "").replace(",", "\n").splitlines() if t.strip()]
            for t in titles:
                execute("INSERT OR IGNORE INTO handouts (kind, title) VALUES (?, ?)", (kind, t))
            if titles:
                flash(f"{kind} {len(titles)}권을 넣었어요.", "ok")
        return redirect(url_for("schedule.handouts"))
    rows = sorted(query("""SELECT h.*, (SELECT COUNT(*) FROM week_handouts w WHERE w.handout_id = h.id) AS n_week
                           FROM handouts h"""), key=hkey)
    return render_template("schedule/handouts.html", rows=rows, kinds=HANDOUT_KINDS)


# ---------------------------------------------------------------- 반 시간표 칸 (요일·교시·시간·관·교실)
@bp.route("/classes/<int:cid>/slots", methods=["POST"])
@staff_required
def slots(cid):
    c = query("SELECT * FROM classes WHERE id = ?", (cid,), one=True) or abort(404)
    if request.form.get("action") == "delete":
        execute("DELETE FROM timetable WHERE id = ? AND class_id = ?", (_int(request.form.get("id")), cid))
    else:
        wd = _int(request.form.get("weekday"))
        st, en = request.form.get("starts", ""), request.form.get("ends", "")
        if wd is None or not 0 <= wd <= 6 or not st or not en or en <= st:
            flash("요일과 시간을 확인해 주세요.", "error")
            return redirect(url_for("teacher.class_detail", cid=cid, tab="times"))
        execute("""INSERT INTO timetable (class_id, weekday, starts, ends, title, period, hall, room)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (cid, wd, st, en, request.form.get("title", "").strip()[:30] or "통합과학", request.form.get("period", "").strip()[:10],
                 request.form.get("hall", "").strip()[:20], request.form.get("room", "").strip()[:20]))
    if c["group_id"]:
        sync_group(c["group_id"])
    audit("slot_edit", f"class:{cid}")
    return redirect(url_for("teacher.class_detail", cid=cid, tab="times"))


def student_week(student_id, today=None):
    """학생 시간표 위 '이번 주': 그 학생 반의 이번 주차 진도·받을 교재·시험 회차."""
    today = (today or date.today()).isoformat()
    w = query("""SELECT w.* FROM group_weeks w JOIN classes c ON c.group_id = w.group_id JOIN students s ON s.class_id = c.id
                 WHERE s.id = ? AND w.starts <= ? AND w.ends >= ?""", (student_id, today, today), one=True)
    if not w:
        return None
    sess = session_view(query(SESSION_SQL + " WHERE s.week_id = ? AND s.class_id = (SELECT class_id FROM students WHERE id = ?)",
                              (w["id"], student_id)), _breaks())
    hs = {h["id"]: h for s in sess if not s["off"] for h in s["handouts"]}
    return {"w": w, "handouts": sorted(hs.values(), key=hkey), "sessions": sess}
