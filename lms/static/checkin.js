// 카드 출결: RFID 리더기가 친 번호를 받아 보내고 결과를 크게 보여 준다
(function () {
  const root = document.querySelector("[data-checkin]");
  if (!root) return;
  const form = root.querySelector("[data-ck-form]"), input = root.querySelector("[data-ck-card]");
  const box = root.querySelector("[data-ck-result]"), st = root.querySelector("[data-ck-status]"), nm = root.querySelector("[data-ck-name]"), sub = root.querySelector("[data-ck-sub]");
  const list = root.querySelector("[data-ck-recent]"), count = root.querySelector("[data-ck-count]");
  const csrf = (document.querySelector('meta[name="csrf-token"]') || {}).content || "";
  let ac = null, hideT = 0, busy = false;
  function tone(kind) {                                   // 출석: 높은 두 음, 지각: 한 음, 오류: 낮은 두 음
    try {
      ac = ac || new (window.AudioContext || window.webkitAudioContext)();
      const seq = kind === "출석" || kind === "again" ? [[880, 0.09], [1320, 0.14]] : kind === "지각" ? [[660, 0.2]] : [[300, 0.14], [220, 0.2]];
      let t = ac.currentTime + 0.01;
      seq.forEach(([f, d]) => { const o = ac.createOscillator(), g = ac.createGain(); o.frequency.value = f; g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.18, t + 0.01); g.gain.exponentialRampToValueAtTime(0.0001, t + d); o.connect(g); g.connect(ac.destination); o.start(t); o.stop(t + d + 0.02); t += d; });
    } catch (_) {}
  }
  function show(d) {
    const kind = d.kind || (d.ok ? "출석" : "bad");
    box.hidden = false; box.className = "ck-result is-" + ({ "출석": "ok", "지각": "late", "again": "again" }[kind] || "err");
    st.textContent = d.ok ? (kind === "again" ? "이미 처리됨" : d.status) : "확인 필요";
    nm.textContent = d.ok ? d.name : (kind === "unknown" ? "등록되지 않은 카드" : "다시 대 주세요");
    sub.textContent = d.ok ? `${d.class_name} · ${d.at}${kind === "지각" && d.starts ? ` (수업 ${d.starts})` : ""}` : (d.card ? `카드 번호 ${d.card}` : d.msg || "");
    tone(kind);
    clearTimeout(hideT); hideT = setTimeout(() => { box.hidden = true; }, 4000);
    if (d.ok && kind !== "again") {
      const empty = list.querySelector("[data-ck-empty]"); if (empty) empty.remove();
      const li = document.createElement("li");
      li.innerHTML = `<time></time><span class="att-tag att-${kind === "지각" ? 2 : 1}"></span><span><span></span> <span class="small muted"></span></span>`;
      li.querySelector("time").textContent = d.at; li.querySelector(".att-tag").textContent = d.status;
      li.querySelector("span > span:first-child").textContent = d.name; li.querySelector("span > .small").textContent = d.class_name;
      list.prepend(li); while (list.children.length > 12) list.lastElementChild.remove();
      refresh();
    }
  }
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const card = input.value.trim(); input.value = "";
    if (!card || busy) return; busy = true;
    fetch(root.dataset.tap, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRFToken": csrf }, body: JSON.stringify({ card }) })
      .then((r) => (r.status === 401 || r.redirected ? { ok: false, msg: "로그인이 풀렸어요. 다시 로그인해 주세요." } : r.json()))
      .then(show).catch(() => show({ ok: false, msg: "연결이 불안정해요. 다시 대 주세요." }))
      .finally(() => { busy = false; input.focus(); });
  });
  function refresh() {
    fetch(root.dataset.today, { credentials: "same-origin" }).then((r) => r.json()).then((d) => {
      const done = d.rows.filter((r) => r.at).length; count.textContent = `${done} / ${d.rows.length}명`;
    }).catch(() => {});
  }
  refresh(); setInterval(refresh, 30000);
  // 리더기 입력을 놓치지 않게 늘 입력 칸에 커서를 둔다
  document.addEventListener("click", (e) => { if (!e.target.closest("a, button, select")) input.focus(); });
  window.addEventListener("focus", () => input.focus());
  setInterval(() => { if (document.activeElement !== input && !document.querySelector("dialog[open]")) input.focus(); }, 2000);
  const full = root.querySelector("[data-ck-full]");
  full.addEventListener("click", () => { (document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen()).catch(() => {}); input.focus(); });
})();
