// 내 시간표: 빈 칸을 누르면 그 요일·시간으로 추가, 칸을 누르면 아래에서 시트가 올라와 내용을 보여 주고 고치기·지우기
(function () {
  "use strict";
  var grid = document.querySelector("[data-tt]"), sheet = document.querySelector("[data-tt-sheet]");
  if (!grid || !sheet) return;
  var form = sheet.querySelector("[data-tt-form]"), title = sheet.querySelector("[data-tt-title]");
  var del = sheet.querySelector("[data-tt-del]"), save = sheet.querySelector("[data-tt-save]");
  var days = Array.prototype.slice.call(form.querySelectorAll('input[name="weekday"]'));
  var tones = Array.prototype.slice.call(form.querySelectorAll('input[name="tone"]'));
  var first = parseInt(grid.dataset.first, 10) || 9, rows = parseInt(grid.dataset.rows, 10) || 78;
  var editing = false, lastFocus = null;
  var pad = function (n) { return (n < 10 ? "0" : "") + n; };
  var hm = function (m) { m = Math.max(7 * 60, Math.min(23 * 60 + 55, m)); return pad(Math.floor(m / 60)) + ":" + pad(m % 60); };

  function open(opts) {
    editing = !!opts.id; lastFocus = document.activeElement;
    form.action = editing ? form.dataset.edit.replace(/\/0$/, "/" + opts.id) : form.dataset.new;
    title.textContent = editing ? "일정 고치기" : "일정 추가";
    save.textContent = editing ? "저장" : "추가하기";
    del.hidden = !editing;
    form.elements.title.value = opts.title || "";
    form.elements.room.value = opts.room || "";
    form.elements.starts.value = opts.starts || "09:00";
    form.elements.ends.value = opts.ends || "10:00";
    days.forEach(function (d) { d.checked = opts.days.indexOf(parseInt(d.value, 10)) >= 0; });
    tones.forEach(function (t) { t.checked = opts.tone !== undefined && String(opts.tone) === t.value; });
    sheet.hidden = false; document.body.classList.add("tt-open");
    setTimeout(function () { form.elements.title.focus(); }, 30);
  }
  function close() { sheet.hidden = true; document.body.classList.remove("tt-open"); if (lastFocus) lastFocus.focus(); }

  // 칸을 눌렀을 때: 내용을 먼저 보여 주는 시트. '고치기'를 눌러야 입력 화면이 열린다.
  var WD = ["월", "화", "수", "목", "금", "토", "일"];
  function info(opts) {
    var d = document.createElement("dialog"); d.className = "sheet-dlg tt-info";
    var box = document.createElement("div"); box.className = "sd-box";
    var p = document.createElement("p"); p.textContent = opts.title;
    var subEl = document.createElement("span"); subEl.className = "sd-sub";
    [WD[opts.days[0]] + " " + opts.starts + "–" + opts.ends, opts.room].filter(Boolean).forEach(function (t, i) {
      if (i) { var s = document.createElement("span"); s.className = "sep"; s.setAttribute("aria-hidden", "true"); subEl.appendChild(s); }
      subEl.appendChild(document.createTextNode(t));
    });
    var act = document.createElement("div"); act.className = "sd-act sd-act-3";
    [["닫기", "btn", "close"], ["삭제", "btn danger", "del"], ["고치기", "btn primary", "edit"]].forEach(function (b) {
      var x = document.createElement("button"); x.type = "button"; x.className = b[1]; x.value = b[2]; x.textContent = b[0]; act.appendChild(x);
    });
    box.appendChild(p); box.appendChild(subEl); box.appendChild(act); d.appendChild(box); document.body.appendChild(d);
    var shut = function () { d.close(); d.remove(); };
    d.addEventListener("click", function (e) {
      var b = e.target.closest("button");
      if (!b) { if (e.target === d) shut(); return; }
      shut();
      if (b.value === "edit") open(opts);
      if (b.value === "del") {          // 지우기는 확인 창을 거친다 (지우기 버튼의 data-confirm)
        form.action = form.dataset.edit.replace(/\/0$/, "/" + opts.id);
        if (form.requestSubmit) form.requestSubmit(del); else open(opts);
      }
    });
    d.addEventListener("cancel", function () { d.remove(); });
    d.showModal();
  }

  document.querySelector("[data-tt-new]").addEventListener("click", function () {
    var wd = (new Date().getDay() + 6) % 7; open({ days: [wd] });
  });
  grid.addEventListener("click", function (e) {
    var b = e.target.closest("[data-tt-edit]");
    if (b) {
      return info({ id: b.dataset.ttEdit, days: [parseInt(b.dataset.day, 10)], starts: b.dataset.starts, ends: b.dataset.ends,
                    title: b.dataset.title, room: b.dataset.room, tone: b.dataset.tone });
    }
    var col = e.target.closest("[data-tt-day]");
    if (col) {
      // 누른 높이로 시간을 정한다 (30분 단위), 기본 1시간짜리
      var r = col.getBoundingClientRect(), k = Math.max(0, Math.min(0.999, (e.clientY - r.top) / r.height));
      var m = first * 60 + Math.floor(k * rows * 10 / 30) * 30;
      open({ days: [parseInt(col.dataset.ttDay, 10)], starts: hm(m), ends: hm(m + 60) });
    }
  });
  // 고칠 때는 요일 하나만
  days.forEach(function (d) {
    d.addEventListener("change", function () { if (editing && d.checked) days.forEach(function (o) { if (o !== d) o.checked = false; }); });
  });
  form.elements.starts.addEventListener("change", function () {
    var s = form.elements.starts.value, e = form.elements.ends.value;
    if (s && (!e || e <= s)) { var m = parseInt(s.slice(0, 2), 10) * 60 + parseInt(s.slice(3), 10) + 60; form.elements.ends.value = hm(m); }
  });
  form.addEventListener("submit", function (e) {
    var isDel = e.submitter && e.submitter.hasAttribute("data-tt-del");
    if (!isDel && !days.some(function (d) { return d.checked; })) { e.preventDefault(); days[0].focus(); alert("요일을 하나 이상 골라 주세요."); }
  });
  sheet.addEventListener("click", function (e) { if (e.target === sheet || e.target.closest("[data-tt-close]")) close(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !sheet.hidden) close(); });
})();
