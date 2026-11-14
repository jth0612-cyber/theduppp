"""TH캐스트: 정태혁 선생님만 글을 올리는 게시판 (영상·편지). 학생·조교는 읽기만.
영상은 유튜브 주소를 넣으면 화면 안에서 바로 재생된다 (youtube-nocookie)."""
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from content import youtube_id
from db import execute, query
from security import audit, login_required, teacher_required

bp = Blueprint("cast", __name__)
viewer_required = login_required(("teacher", "assistant", "student"))


def _form():
    title = request.form.get("title", "").strip()[:120]
    body = request.form.get("body", "").strip()[:8000]
    video = request.form.get("video_url", "").strip()[:500]
    err = None
    if not title:
        err = "제목을 적어 주세요."
    elif not body and not video:
        err = "본문이나 영상 주소 중 하나는 넣어 주세요."
    elif video and not youtube_id(video):
        err = "유튜브 주소만 넣을 수 있습니다."
    return title, body, video, err


@bp.route("/cast")
@viewer_required
def cast_list():
    rows = query("SELECT * FROM casts ORDER BY pinned DESC, created_at DESC LIMIT 100")
    return render_template("cast/list.html", rows=rows)


@bp.route("/cast/<int:cid>")
@viewer_required
def cast_detail(cid):
    c = query("SELECT * FROM casts WHERE id = ?", (cid,), one=True) or abort(404)
    return render_template("cast/detail.html", c=c, yt=youtube_id(c["video_url"]) if c["video_url"] else None)


@bp.route("/cast/new", methods=["GET", "POST"])
@teacher_required
def cast_new():
    draft = None
    if request.method == "POST":
        title, body, video, err = _form()
        if err:
            flash(err, "error")
            draft = {"title": title, "body": body, "video_url": video, "pinned": request.form.get("pinned") == "1"}
        else:
            cid = execute("INSERT INTO casts (title, body, video_url, pinned, author_id) VALUES (?, ?, ?, ?, ?)",
                          (title, body, video, 1 if request.form.get("pinned") == "1" else 0, g.user["id"]))
            audit("cast_create", f"cast:{cid}")
            return redirect(url_for("cast.cast_detail", cid=cid))
    return render_template("cast/edit.html", c=draft, editing=False)


@bp.route("/cast/<int:cid>/edit", methods=["GET", "POST"])
@teacher_required
def cast_edit(cid):
    c = query("SELECT * FROM casts WHERE id = ?", (cid,), one=True) or abort(404)
    if request.method == "POST":
        if request.form.get("action") == "delete":
            execute("DELETE FROM casts WHERE id = ?", (cid,))
            audit("cast_delete", f"cast:{cid}")
            flash("글을 지웠습니다.", "ok")
            return redirect(url_for("cast.cast_list"))
        title, body, video, err = _form()
        if err:
            flash(err, "error")
        else:
            execute("UPDATE casts SET title = ?, body = ?, video_url = ?, pinned = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                    (title, body, video, 1 if request.form.get("pinned") == "1" else 0, cid))
            return redirect(url_for("cast.cast_detail", cid=cid))
    return render_template("cast/edit.html", c=c, editing=True)
