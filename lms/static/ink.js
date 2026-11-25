// 질문 쓰기: 문항 불러오기(회차·번호 고르면 그 문항으로 다시 열기)와 문항 그림 위 필기.
// 필기한 그림은 사진 첨부 칸의 첫 장으로 들어가 함께 올라간다 (views/items.py 의 워터마크 그림 위에 그린다).
(function () {
  var pickM = document.querySelector("[data-ip-mock]"), pickN = document.querySelector("[data-ip-no]");
  if (pickM && pickN) {
    function fill() {
      var opt = pickM.options[pickM.selectedIndex], nos = (opt && opt.dataset.nos || "").split(",").filter(Boolean);
      pickN.innerHTML = '<option value="">번호</option>' + nos.map(function (n) {
        return '<option value="' + n + '"' + (n === pickN.dataset.cur ? " selected" : "") + ">" + n + "번</option>"; }).join("");
    }
    fill();
    pickM.addEventListener("change", function () { pickN.dataset.cur = ""; fill(); });
    pickN.addEventListener("change", function () {
      if (!pickM.value || !pickN.value) return;
      location.href = location.pathname + "?ask=1&mock=" + pickM.value + "&item=" + pickN.value + "#ask";
    });
  }

  var box = document.querySelector("[data-ink]");
  if (!box) return;
  var cv = box.querySelector("canvas"), ctx = cv.getContext("2d"), form = box.closest("form");
  var input = form && form.querySelector("input[type=file][name=image]");
  var bg = new Image(), strokes = [], cur = null, color = "#1a1a1a", userFiles = [];
  function redraw() {
    ctx.drawImage(bg, 0, 0);
    strokes.forEach(function (s) {
      ctx.strokeStyle = s.c; ctx.lineWidth = s.w; ctx.lineCap = "round"; ctx.lineJoin = "round";
      ctx.beginPath(); s.p.forEach(function (q, i) { i ? ctx.lineTo(q[0], q[1]) : ctx.moveTo(q[0], q[1]); }); ctx.stroke();
    });
  }
  // 사진 첨부 칸 = [필기한 문항 그림] + 학생이 고른 사진 (3장까지)
  function attach() {
    if (!input || !window.DataTransfer) return;
    cv.toBlob(function (blob) {
      var dt = new DataTransfer();
      dt.items.add(new File([blob], box.dataset.name || "문항.png", { type: "image/png" }));
      userFiles.slice(0, 2).forEach(function (f) { dt.items.add(f); });
      input.files = dt.files;
      input.dispatchEvent(new Event("change", { bubbles: true }));
    }, "image/png");
  }
  if (input) input.addEventListener("change", function (e) {
    if (e.isTrusted) userFiles = Array.prototype.filter.call(input.files, function (f) { return f.name !== box.dataset.name; });
    if (e.isTrusted) attach();
  });
  function pos(e) {
    var r = cv.getBoundingClientRect();
    return [(e.clientX - r.left) * cv.width / r.width, (e.clientY - r.top) * cv.height / r.height];
  }
  cv.addEventListener("pointerdown", function (e) {
    cv.setPointerCapture(e.pointerId);
    cur = { c: color, w: Math.max(2, cv.width / 260) * (e.pointerType === "pen" && e.pressure ? 0.6 + e.pressure : 1), p: [pos(e)] };
    strokes.push(cur); redraw();
  });
  cv.addEventListener("pointermove", function (e) { if (!cur) return; cur.p.push(pos(e)); redraw(); });
  function end() { if (cur) { cur = null; attach(); } }
  cv.addEventListener("pointerup", end); cv.addEventListener("pointercancel", end);
  box.querySelectorAll("[data-pen]").forEach(function (b) {
    b.addEventListener("click", function () {
      color = b.dataset.pen;
      box.querySelectorAll("[data-pen]").forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
    });
  });
  box.querySelector("[data-ink-undo]").addEventListener("click", function () { strokes.pop(); redraw(); attach(); });
  box.querySelector("[data-ink-clear]").addEventListener("click", function () { strokes = []; redraw(); attach(); });
  bg.onload = function () { cv.width = bg.naturalWidth; cv.height = bg.naturalHeight; redraw(); attach(); };
  bg.src = box.dataset.src;
})();
