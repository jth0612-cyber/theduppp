// 플래너: 체크를 누르면 새로고침 없이 바로 표시 (실패하면 보통 폼 전송으로 돌아간다)
(function () {
  var list = document.querySelector("[data-list]");
  var bar = document.querySelector("[data-bar]");
  function refresh() {
    if (!bar || !list) return;
    var total = list.querySelectorAll("[data-item]").length, done = list.querySelectorAll(".p-item.is-done").length;
    var pct = total ? Math.round(done * 100 / total) : 0;
    bar.style.width = pct + "%";
    var n = document.querySelector("[data-done-n]"), p = document.querySelector("[data-pct]");
    if (n) n.textContent = done; if (p) p.textContent = pct + "%";
  }
  refresh();
  document.querySelectorAll("form[data-toggle]").forEach(function (f) {
    f.addEventListener("submit", function (e) {
      e.preventDefault();
      var li = f.closest("[data-item]"), btn = f.querySelector("button");
      var on = !li.classList.contains("is-done");
      li.classList.toggle("is-done", on); btn.setAttribute("aria-pressed", on ? "true" : "false"); refresh();
      fetch(f.action, { method: "POST", body: new FormData(f), credentials: "same-origin", headers: { "X-Requested-With": "fetch" } })
        .then(function (r) { if (!r.ok) throw r; })
        .catch(function () { li.classList.toggle("is-done", !on); refresh(); f.submit(); });
    });
  });
  // 메뉴 바깥을 누르면 닫기
  document.addEventListener("click", function (e) {
    document.querySelectorAll(".p-more[open]").forEach(function (d) { if (!d.contains(e.target)) d.removeAttribute("open"); });
  });
  // 고른 칩을 다시 누르면 선택 해제
  document.querySelectorAll(".p-chips label").forEach(function (l) {
    l.addEventListener("click", function (e) {
      var r = l.querySelector("input");
      if (e.target === r) return;
      if (r.checked) { e.preventDefault(); r.checked = false; }
    });
  });
})();
