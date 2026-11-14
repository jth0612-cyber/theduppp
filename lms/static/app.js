// CSP 때문에 인라인 스크립트 대신 이 파일만 사용한다.
document.addEventListener("submit", function (e) {
  // 폼 또는 누른 버튼에 data-confirm 이 있으면 확인
  var msg = (e.submitter && e.submitter.getAttribute("data-confirm")) || e.target.getAttribute("data-confirm");
  if (msg && !window.confirm(msg)) e.preventDefault();
});

// 점수 입력표: Enter 로 다음 칸 이동
document.addEventListener("keydown", function (e) {
  if (e.key !== "Enter" || !e.target.classList.contains("score")) return;
  e.preventDefault();
  var inputs = Array.prototype.slice.call(document.querySelectorAll("input.score"));
  var next = inputs[inputs.indexOf(e.target) + 1];
  if (next) { next.focus(); next.select(); }
});

// ---------- 공용: 인쇄, 탭 ----------
document.addEventListener("click", function (e) {
  var p = e.target.closest("[data-print]");
  if (p) { window.print(); return; }
  var tab = e.target.closest("[data-tab]");
  if (tab) {
    document.querySelectorAll("[data-tab]").forEach(function (b) {
      var on = b === tab;
      b.classList.toggle("is-on", on);
      b.setAttribute("aria-selected", on ? "true" : "false");
      var panel = document.getElementById(b.getAttribute("data-tab"));
      if (panel) panel.hidden = !on;
    });
  }
});
document.addEventListener("DOMContentLoaded", function () {
  var first = document.querySelector("[data-tab].is-on");
  document.querySelectorAll("[data-tab]").forEach(function (b) {
    var panel = document.getElementById(b.getAttribute("data-tab"));
    if (panel && b !== first) panel.hidden = true;
  });
});

function csrfToken() {
  var m = document.querySelector('meta[name="csrf-token"]');
  return m ? m.getAttribute("content") : "";
}
function postForm(form) {
  return fetch(form.action, { method: "POST", body: new FormData(form), credentials: "same-origin",
    headers: { "X-Requested-With": "fetch" } }).then(function (r) { if (!r.ok) throw r; return r.json(); });
}

// ---------- 오답 노트: 이유·복습 체크는 바로 저장 ----------
document.addEventListener("change", function (e) {
  var form = e.target.closest("form[data-autosave]");
  if (!form || e.target.name === "memo") return;
  postForm(form).then(function () {
    var li = form.closest("li");
    var rv = form.querySelector('input[name="reviewed"]');
    if (li && rv) li.classList.toggle("is-done", rv.checked);
    flashSaved(form);
  }).catch(function () {});
});
function flashSaved(form) {
  var b = form.querySelector('button[type="submit"]');
  if (!b) return;
  var old = b.textContent; b.textContent = "저장됨";
  setTimeout(function () { b.textContent = old; }, 1200);
}

// ---------- 개념 카드: 뒤집기, 표시 후 다음 카드 ----------
document.addEventListener("click", function (e) {
  var flip = e.target.closest("[data-flip]");
  if (!flip) return;
  var front = flip.querySelector(".fc-front"), back = flip.querySelector(".fc-back");
  var showBack = back.hidden;
  back.hidden = !showBack; front.hidden = showBack;
  flip.classList.toggle("is-back", showBack);
});
document.addEventListener("submit", function (e) {
  var form = e.target;
  if (!form.matches("[data-mark]")) return;
  e.preventDefault();
  var card = form.closest("[data-card]");
  postForm(form).then(function () { nextCard(card); }).catch(function () { form.submit(); });
});
function nextCard(card) {
  var deck = card.closest("[data-deck]");
  var cards = Array.prototype.slice.call(deck.querySelectorAll("[data-card]"));
  var i = cards.indexOf(card);
  card.hidden = true;
  var next = cards[i + 1];
  if (next) {
    next.hidden = false;
    deck.querySelector("[data-pos]").textContent = i + 2;
    var f = next.querySelector("[data-flip]"); if (f) f.focus();
  } else {
    deck.querySelector("[data-done]").hidden = false;
  }
}

// ---------- 밝기(자동·밝게·어둡게) ----------
document.addEventListener("click", function (e) {
  var b = e.target.closest("[data-theme-toggle]");
  if (!b) return;
  var order = ["auto", "light", "dark"];
  var cur = "auto";
  try { cur = localStorage.getItem("theme") || "auto"; } catch (_) {}
  var next = order[(order.indexOf(cur) + 1) % 3];
  try { if (next === "auto") localStorage.removeItem("theme"); else localStorage.setItem("theme", next); } catch (_) {}
  if (next === "auto") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", next);
  themeLabel();
});
function themeLabel() {
  var cur = "auto";
  try { cur = localStorage.getItem("theme") || "auto"; } catch (_) {}
  document.querySelectorAll("[data-theme-toggle]").forEach(function (b) {
    b.textContent = { auto: "화면: 자동", light: "화면: 밝게", dark: "화면: 어둡게" }[cur];
  });
}
document.addEventListener("DOMContentLoaded", themeLabel);

// ---------- 앱 설치(서비스 워커)와 알림 ----------
if ("serviceWorker" in navigator) {
  window.addEventListener("load", function () { navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(function () {}); });
}
function b64ToBytes(s) {
  var pad = "=".repeat((4 - (s.length % 4)) % 4);
  var raw = atob((s + pad).replace(/-/g, "+").replace(/_/g, "/"));
  var out = new Uint8Array(raw.length);
  for (var i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}
function pushSupported() {
  return "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
}
function pushLabel() {
  var all = document.querySelectorAll("[data-push]");
  if (!all.length) return;
  if (!pushSupported()) {
    all.forEach(function (b) { b.textContent = "알림: 홈 화면에 설치 후 사용"; b.disabled = true; });
    return;
  }
  navigator.serviceWorker.ready.then(function (reg) { return reg.pushManager.getSubscription(); }).then(function (sub) {
    all.forEach(function (b) {
      b.textContent = sub ? "알림: 켜짐" : (Notification.permission === "denied" ? "알림: 차단됨" : "알림 켜기");
      b.setAttribute("aria-pressed", sub ? "true" : "false");
    });
  });
}
document.addEventListener("DOMContentLoaded", pushLabel);
document.addEventListener("click", function (e) {
  var b = e.target.closest("[data-push]");
  if (!b || !pushSupported()) return;
  navigator.serviceWorker.ready.then(function (reg) {
    return reg.pushManager.getSubscription().then(function (sub) {
      if (sub) {
        return fetch("/push/unsubscribe", { method: "POST", credentials: "same-origin",
          headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
          body: JSON.stringify({ endpoint: sub.endpoint }) }).then(function () { return sub.unsubscribe(); });
      }
      return Notification.requestPermission().then(function (perm) {
        if (perm !== "granted") throw new Error("denied");
        return fetch("/push/key", { credentials: "same-origin" }).then(function (r) { return r.json(); });
      }).then(function (d) {
        if (!d.key) throw new Error("nokey");
        return reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64ToBytes(d.key) });
      }).then(function (s) {
        return fetch("/push/subscribe", { method: "POST", credentials: "same-origin",
          headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() }, body: JSON.stringify(s) });
      });
    });
  }).catch(function () {}).then(pushLabel);
});

// ---------- 휴대폰 전체 메뉴 ----------
function setMenu(open) {
  var m = document.getElementById("m-menu");
  var btn = document.querySelector("[data-menu-open]");
  if (!m) return;
  m.hidden = !open;
  document.body.classList.toggle("menu-open", open);
  if (btn) btn.setAttribute("aria-expanded", open ? "true" : "false");
  if (open) { var c = m.querySelector("[data-menu-close]"); if (c) c.focus(); }
  else if (btn) btn.focus();
}
document.addEventListener("click", function (e) {
  if (e.target.closest("[data-menu-open]")) setMenu(true);
  else if (e.target.closest("[data-menu-close]")) setMenu(false);
});
document.addEventListener("keydown", function (e) {
  if (e.key === "Escape" && document.body.classList.contains("menu-open")) setMenu(false);
});

// ---------- 로그인 '입장' 연출: 화면이 한 번 닫혔다가 안쪽이 열린다 ----------
document.addEventListener("submit", function (e) {
  var f = e.target;
  if (!f.hasAttribute || !f.hasAttribute("data-enter") || e.defaultPrevented || f.__entering) return;
  if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  e.preventDefault();
  f.__entering = true;
  document.documentElement.classList.add("entering");
  setTimeout(function () { f.submit(); }, 340);
});
window.addEventListener("pageshow", function (e) {   // 뒤로 가기로 돌아왔을 때 닫힌 화면이 남지 않게
  if (e.persisted) document.documentElement.classList.remove("entering");
  document.querySelectorAll("form[data-enter]").forEach(function (f) { f.__entering = false; });
});

// ---------- 질문 쓰기: 적은 내용 지키기 (임시 저장 · 사진 확인 · 미리보기) ----------
(function () {
  var MAX = 20 * 1024 * 1024 - 256 * 1024;   // 서버 한도(20MB)보다 조금 작게
  function box(key) {
    return {
      get: function () { try { return JSON.parse(localStorage.getItem(key) || "null"); } catch (e) { return null; } },
      set: function (v) { try { localStorage.setItem(key, JSON.stringify(v)); } catch (e) {} },
      del: function () { try { localStorage.removeItem(key); } catch (e) {} }
    };
  }
  // 등록을 마치고 넘어온 화면이면 임시 저장을 지운다
  document.querySelectorAll("[data-draft-clear]").forEach(function (el) {
    el.getAttribute("data-draft-clear").split(" ").forEach(function (k) { box(k).del(); });
  });
  document.querySelectorAll("form[data-qform]").forEach(function (f) {
    var store = box(f.getAttribute("data-draft-key"));
    var fields = Array.prototype.filter.call(f.elements, function (el) { return ["title", "body", "qtype"].indexOf(el.name) >= 0; });
    var note = f.querySelector("[data-draft-note]");
    if (!f.hasAttribute("data-has-draft")) {        // 서버가 돌려준 내용이 없을 때만, 지난번에 쓰던 내용을 불러온다
      var d = store.get();
      if (d && fields.some(function (el) { return !el.value && d[el.name]; })) {
        fields.forEach(function (el) { if (!el.value && d[el.name]) el.value = d[el.name]; });
        if (note) note.hidden = false;
        var det = f.closest("details"); if (det) det.open = true;
      }
    }
    function save() {
      var v = {}, any = false;
      fields.forEach(function (el) { v[el.name] = el.value; if (el.name !== "qtype" && el.value.trim()) any = true; });
      if (any) store.set(v); else store.del();
    }
    var t; f.addEventListener("input", function () { clearTimeout(t); t = setTimeout(save, 400); });

    var wrap = f.querySelector("[data-photo]"); if (!wrap) return;
    var inp = wrap.querySelector("input[type=file]"), err = wrap.querySelector("[data-photo-err]"),
        pv = wrap.querySelector("[data-photo-preview]"), thumbs = pv.querySelector("[data-photo-thumbs]"), qt = f.querySelector("[data-qtype]");
    var urls = [];
    function showErr(msg) { err.textContent = msg || ""; err.hidden = !msg; wrap.classList.toggle("has-err", !!msg); }
    function clearPhoto() { inp.value = ""; pv.hidden = true; urls.forEach(function (u) { URL.revokeObjectURL(u); }); urls = []; thumbs.textContent = ""; }
    inp.addEventListener("change", function () {
      var files = Array.prototype.slice.call(inp.files || []);
      if (!files.length) { clearPhoto(); return; }
      if (files.length > 3) { clearPhoto(); return showErr("사진은 3장까지 올릴 수 있습니다."); }
      for (var i = 0; i < files.length; i++) {
        var file = files[i];
        if (!/\.(png|jpe?g)$/i.test(file.name) && !/^image\/(png|jpeg)$/.test(file.type)) {
          clearPhoto(); return showErr("PNG·JPG만 올릴 수 있습니다. 아이폰은 스크린샷으로 올려 주세요.");
        }
        if (file.size > MAX) { clearPhoto(); return showErr("한 장에 20MB 이하만 올릴 수 있습니다."); }
      }
      showErr("");
      urls.forEach(function (u) { URL.revokeObjectURL(u); }); urls = []; thumbs.textContent = "";
      files.forEach(function (file) {
        var u = URL.createObjectURL(file); urls.push(u);
        var im = document.createElement("img"); im.src = u; im.alt = file.name; thumbs.appendChild(im);
      });
      pv.querySelector("span").textContent = files.length + "장"; pv.hidden = false;
    });
    pv.querySelector("[data-photo-clear]").addEventListener("click", function () { clearPhoto(); inp.focus(); });
    if (qt) qt.addEventListener("change", function () { if (qt.value !== "학습질문") showErr(""); });
    f.addEventListener("submit", function (e) {
      save();
      if (qt && qt.value === "학습질문" && !(inp.files && inp.files.length)) {
        e.preventDefault(); e.stopImmediatePropagation();
        showErr("학습질문은 문제 사진이 필요합니다. 쓴 내용은 그대로 있습니다.");
        wrap.scrollIntoView({ behavior: "smooth", block: "center" });
        inp.focus();
      }
    });
  });
})();

// ---------- 조교 답변: 기본 인사말이 미리 들어 있고, 처음 누르면 가운데 빈 줄에서 바로 쓰기 시작 ----------
document.querySelectorAll("textarea[data-answer-tpl]").forEach(function (t) {
  var tpl = t.value, mark = "질문 남겨주셔서 감사합니다.\n\n", at = tpl.indexOf(mark);
  if (at < 0) return;
  t.addEventListener("focus", function () {
    if (t.value !== tpl) return;               // 이미 쓰기 시작했으면 그대로
    var pos = at + mark.length;
    setTimeout(function () { t.setSelectionRange(pos, pos); }, 0);
  });
});

// 뒤로: 같은 사이트에서 왔으면 이전 화면, 아니면 홈
(function () {
  var b = document.querySelector("[data-back]");
  if (!b) return;
  b.addEventListener("click", function (e) {
    var ref = document.referrer;
    if (ref && ref.indexOf(location.origin + "/") === 0 && ref !== location.href && history.length > 1) {
      e.preventDefault(); history.back();
    }
  });
})();
