"""문항 그림 (보류: ITEMS_ENABLED 가 켜져 있을 때만 동작): 조교가 회차의 문항 그림을 올리면, 학생은 시험 분석에서 문항을 눌러 보고 그 그림 위에 필기해서 질문한다.

- 그림 파일은 tools/split_items.py 로 시험지 PDF 에서 자른다. 파일 이름의 숫자가 문항 번호(07.png → 7번).
- 학생에게는 아이디·날짜 워터마크를 그림에 새겨서 보낸다(Pillow). 캡처해서 돌려도 누구 것인지 남는다.
- 학생은 볼 수 있는 회차(시험 분석에 뜨는 회차)의 문항만 본다.
"""
import io
import os
import re
from datetime import date

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, send_file, url_for

from db import execute, query
from security import IMAGE_EXTS, audit, delete_file, login_required, save_upload, staff_required, student_required

bp = Blueprint("items", __name__)


def enabled():
    """보안 문제로 보류 (2026-11-25). 켜려면 환경 변수 ITEMS_ENABLED=1."""
    return bool(current_app.config.get("ITEMS_ENABLED"))


@bp.before_request
def _gate():
    if not enabled():
        abort(404)


def item_nos(mock_id):
    if not enabled():
        return set()
    return {r["item_no"] for r in query("SELECT item_no FROM mock_item_images WHERE mock_id = ?", (mock_id,))}


def exam_label(m):
    """질문 제목 머리: [모의고사 14회 7번] / [복테 14회 4번] (질답 게시판과 같은 꼴)"""
    return ("복테" if m["kind"] == "복습 테스트" else "모의고사") + f" {m['round_no']}회"


# ---------------------------------------------------------------- 조교: 올리기·지우기
@bp.route("/t/mocks/<int:mid>/items", methods=["POST"])
@staff_required
def upload(mid):
    m = query("SELECT * FROM mocks WHERE id = ?", (mid,), one=True) or abort(404)
    done, bad = [], []
    for f in request.files.getlist("image"):
        num = re.findall(r"\d+", os.path.splitext(f.filename or "")[0])
        no = int(num[-1]) if num else 0
        if not 1 <= no <= max(m["n_items"] or 60, 1):
            bad.append(f.filename)
            continue
        try:
            fid = save_upload(f, IMAGE_EXTS)
        except ValueError:
            bad.append(f.filename)
            continue
        old = query("SELECT file_id FROM mock_item_images WHERE mock_id = ? AND item_no = ?", (mid, no), one=True)
        execute("""INSERT INTO mock_item_images (mock_id, item_no, file_id) VALUES (?, ?, ?)
                   ON CONFLICT (mock_id, item_no) DO UPDATE SET file_id = excluded.file_id""", (mid, no, fid))
        if old:
            delete_file(old["file_id"])
        done.append(no)
    audit("mock_items", f"mock:{mid}:{len(done)}")
    if done:
        flash(f"문항 그림 {len(done)}장을 올렸어요 ({', '.join(str(n) for n in sorted(done))}번).", "ok")
    if bad:
        flash("파일 이름에서 문항 번호를 읽지 못했거나 그림이 아니에요: " + ", ".join(bad[:5]), "error")
    return redirect(url_for("books.teacher_mock", mid=mid, tab="eval") + "#items")


@bp.route("/t/mocks/<int:mid>/items/<int:no>/delete", methods=["POST"])
@staff_required
def remove(mid, no):
    r = query("SELECT file_id FROM mock_item_images WHERE mock_id = ? AND item_no = ?", (mid, no), one=True) or abort(404)
    execute("DELETE FROM mock_item_images WHERE mock_id = ? AND item_no = ?", (mid, no))
    delete_file(r["file_id"])
    return redirect(url_for("books.teacher_mock", mid=mid, tab="eval") + "#items")


# ---------------------------------------------------------------- 그림 (학생: 워터마크)
def _can_see(mid):
    if g.user["role"] in ("teacher", "assistant"):
        return True
    from views.books import _accessible_mocks
    return mid in {m["id"] for m in _accessible_mocks()}


def watermark(raw, text):
    """그림 위에 비스듬한 글자를 바둑판처럼 연하게 새긴다."""
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    w, h = im.size
    size = max(14, w // 28)
    font = ImageFont.load_default(size=size)
    tile = Image.new("RGBA", (int(size * len(text) * 0.75) + size * 4, size * 5), (0, 0, 0, 0))
    ImageDraw.Draw(tile).text((size, size * 2), text, font=font, fill=(80, 80, 80, 60))
    tile = tile.rotate(28, expand=True)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    tw, th = tile.size
    for row, y in enumerate(range(-th // 2, h, th // 2)):           # 줄마다 반 칸씩 엇갈리게
        for x in range(-tw + (row % 2) * tw // 2, w, tw):
            layer.paste(tile, (x, y), tile)
    out = Image.alpha_composite(im.convert("RGBA"), layer).convert("RGB")
    buf = io.BytesIO()
    out.save(buf, "PNG", optimize=True)
    buf.seek(0)
    return buf


@bp.route("/items/<int:mid>/<int:no>.png")
@login_required()
def image(mid, no):
    if not _can_see(mid):
        abort(404)
    r = query("""SELECT f.stored_name FROM mock_item_images i JOIN files f ON f.id = i.file_id
                 WHERE i.mock_id = ? AND i.item_no = ?""", (mid, no), one=True) or abort(404)
    with open(os.path.join(current_app.config["UPLOAD_DIR"], r["stored_name"]), "rb") as fh:
        raw = fh.read()
    who = g.user["username"] if g.user["role"] == "student" else "THedu " + g.user["username"]
    resp = send_file(watermark(raw, f"{who} {date.today().isoformat()} THedu"), mimetype="image/png")
    resp.headers["Cache-Control"] = "private, no-store"
    return resp


# ---------------------------------------------------------------- 학생: 문항 보기
@bp.route("/s/analysis/<int:mid>/items/<int:no>")
@student_required
def view(mid, no):
    if not _can_see(mid):
        abort(404)
    m = query("SELECT m.*, b.kind FROM mocks m JOIN books b ON b.id = m.book_id WHERE m.id = ?", (mid,), one=True) or abort(404)
    nos = sorted(item_nos(mid))
    if no not in nos:
        abort(404)
    i = nos.index(no)
    return render_template("student/item_view.html", m=m, no=no, label=exam_label(m),
                           prev=nos[i - 1] if i else None, next=nos[i + 1] if i + 1 < len(nos) else None)
