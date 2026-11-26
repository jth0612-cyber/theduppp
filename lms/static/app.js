// CSP 때문에 인라인 스크립트 대신 이 파일만 사용한다.
// 사진 칸(.drop): 고른 장수를 칸 안 제목에 보여 준다
document.addEventListener("change", function (e) {
  var inp = e.target;
  if (!inp.classList || !inp.classList.contains("drop-input")) return;
  var b = inp.parentNode.querySelector('label.drop[for="' + inp.id + '"] b');
  if (!b) return;
  if (!b.hasAttribute("data-base")) b.setAttribute("data-base", b.textContent);
  var n = inp.files ? inp.files.length : 0;
  b.textContent = n ? "사진 " + n + "장 (다시 누르면 바꾸기)" : b.getAttribute("data-base");
});
// 확인 시트: window.confirm 대신 아래에서 올라오는 시트. ok() 는 '확인'을 눌렀을 때만 부른다.
function askSheet(msg, ok, danger, label) {
  var d = document.createElement("dialog");
  d.className = "sheet-dlg" + (danger ? " is-danger" : "");
  d.innerHTML = '<div class="sd-box"><p></p><div class="sd-act"><button type="button" class="btn" value="no">닫기</button><button type="button" class="btn primary" value="yes">확인</button></div></div>';
  if (label) d.querySelector("button[value=yes]").textContent = label;
  var cut = msg.search(/[?.]\s/);                      // 첫 문장은 제목, 나머지는 회색 설명 (토스 확인 시트)
  var p = d.querySelector("p");
  if (cut > 0 && cut < msg.length - 2) {
    p.textContent = msg.slice(0, cut + 1);
    var sub = document.createElement("span"); sub.className = "sd-sub"; sub.textContent = msg.slice(cut + 1).trim();
    p.insertAdjacentElement("afterend", sub);
  } else p.textContent = msg;
  document.body.appendChild(d);
  var close = function () { d.close(); d.remove(); };
  d.addEventListener("click", function (e) {
    var b = e.target.closest("button");
    if (b) { close(); if (b.value === "yes") ok(); }
    else if (e.target === d) close();
  });
  d.addEventListener("cancel", function (e) { e.preventDefault(); close(); });
  if (d.showModal) { d.showModal(); d.querySelector(".primary").focus(); }
  else { d.remove(); if (window.confirm(msg)) ok(); }
}
document.addEventListener("submit", function (e) {
  // 폼 또는 누른 버튼에 data-confirm 이 있으면 확인
  var f = e.target, sub = e.submitter;
  var msg = (sub && sub.getAttribute("data-confirm")) || f.getAttribute("data-confirm");
  if (!msg || f._confirmed) { f._confirmed = false; return; }
  e.preventDefault();
  e.stopImmediatePropagation();
  askSheet(msg, function () {
    f._confirmed = true;
    if (f.requestSubmit) f.requestSubmit(sub && sub.form === f ? sub : undefined); else f.submit();
  }, /삭제|지우|초기화/.test(msg), (function (t) { return t && t.length <= 14 ? t : ""; })(sub ? sub.textContent.replace(/\s+/g, " ").trim() : ""));
}, true);

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
  if (!form) return;                                  // 메모는 칸을 벗어날 때(change) 저장
  postForm(form).then(function () {
    var li = form.closest("li");
    var rv = form.querySelector('input[name="reviewed"]');
    if (li && rv) li.classList.toggle("is-done", rv.checked);
    flashSaved(form);
  }).catch(function () {});
});
function flashSaved(form) {
  var li = form.closest("li"); if (!li) return;          // 바로 저장되므로 저장 버튼 대신 줄이 잠깐 밝아진다
  li.classList.remove("is-saved"); void li.offsetWidth; li.classList.add("is-saved");
}
document.querySelectorAll("form[data-autosave] .w-save").forEach(function (b) { b.hidden = true; });

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
    all.forEach(function (b) { b.textContent = "알림: 홈 화면에 추가 후 사용"; });
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
  if (!b) return;
  if (!pushSupported()) {                      // 아이폰 사파리는 홈 화면에 추가한 앱에서만 알림이 된다
    b.textContent = /iPhone|iPad|iPod/.test(navigator.userAgent)
      ? "공유 버튼 → 홈 화면에 추가 → 앱에서 알림 켜기" : "이 브라우저는 알림을 지원하지 않음";
    return;
  }
  navigator.serviceWorker.ready.then(function (reg) {
    return reg.pushManager.getSubscription().then(function (sub) {
      if (sub) {
        return fetch("/push/unsubscribe", { method: "POST", credentials: "same-origin",
          headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
          body: JSON.stringify({ endpoint: sub.endpoint }) }).then(function () { return sub.unsubscribe(); });
      }
      b.textContent = "권한 창에서 '허용'을 눌러 주세요";      // 권한 창이 늦게 뜨거나 안 떠도 지금 상태를 알 수 있게
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
  }).then(pushLabel, function (err) {         // 실패 이유를 버튼에 남긴다 (조용히 아무 일도 없던 것처럼 보이지 않게)
    b.textContent = err && err.message === "denied" ? "알림: 차단됨 / 브라우저 설정에서 허용" : "알림을 켜지 못함 / 다시 누르기";
  });
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
    var fields = Array.prototype.filter.call(f.elements, function (el) { return ["title", "body"].indexOf(el.name) >= 0; });
    var qtypes = f.querySelectorAll("input[name=qtype]");
    function qv() { var c = f.querySelector("input[name=qtype]:checked"); return c ? c.value : ""; }
    var note = f.querySelector("[data-draft-note]");
    if (!f.hasAttribute("data-has-draft")) {        // 서버가 돌려준 내용이 없을 때만, 지난번에 쓰던 내용을 불러온다
      var d = store.get();
      if (d && fields.some(function (el) { return !el.value && d[el.name]; })) {
        fields.forEach(function (el) { if (!el.value && d[el.name]) el.value = d[el.name]; });
        if (!qv() && d.qtype) qtypes.forEach(function (r) { if (r.value === d.qtype) { r.checked = true; r.dispatchEvent(new Event("change", { bubbles: true })); } });
        if (note) note.hidden = false;
        var det = f.closest("details"); if (det) det.open = true;
      }
    }
    function save() {
      var v = {}, any = false;
      fields.forEach(function (el) { v[el.name] = el.value; if (el.value.trim()) any = true; });
      v.qtype = qv();
      if (any) store.set(v); else store.del();
    }
    var t; f.addEventListener("input", function () { clearTimeout(t); t = setTimeout(save, 400); });
    f.addEventListener("change", function (e) { if (e.target.name === "qtype") save(); });

    var wrap = f.querySelector("[data-photo]"); if (!wrap) return;
    var inp = wrap.querySelector("input[type=file]"), err = wrap.querySelector("[data-photo-err]"),
        pv = wrap.querySelector("[data-photo-preview]"), thumbs = pv.querySelector("[data-photo-thumbs]");
    var urls = [];
    function showErr(msg) { err.textContent = msg || ""; err.hidden = !msg; wrap.classList.toggle("has-err", !!msg); }
    function clearPhoto() { inp.value = ""; pv.hidden = true; urls.forEach(function (u) { URL.revokeObjectURL(u); }); urls = []; thumbs.textContent = ""; }
    inp.addEventListener("change", function () {
      var files = Array.prototype.slice.call(inp.files || []);
      if (!files.length) { clearPhoto(); return; }
      if (files.length > 3) { clearPhoto(); return showErr("사진은 3장까지 올릴 수 있어요."); }
      for (var i = 0; i < files.length; i++) {
        var file = files[i];
        if (!/\.(png|jpe?g)$/i.test(file.name) && !/^image\/(png|jpeg)$/.test(file.type)) {
          clearPhoto(); return showErr("PNG 및 JPG만 올릴 수 있어요. 아이폰은 스크린샷으로 올려 주세요.");
        }
        if (file.size > MAX) { clearPhoto(); return showErr("한 장에 20MB 이하만 올릴 수 있어요."); }
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
    f.addEventListener("change", function (e) {
      if (e.target.name !== "qtype") return;
      var v = qv();
      if (v !== "학습질문") showErr("");
      var t = document.getElementById("q-title");      // 유형에 맞는 제목 예시
      if (t) t.placeholder = { "행정문의": "예) 교재 환불, FRAMING 해설편 2권", "학습상담": "예) 평일 공부 계획 상담" }[v] || "[교재-페이지-번호] 예) 개념서 42p 3번";
      try {                                              // 유형의 규칙은 내용 칸·사진 칸 안 글로
        var b = document.getElementById("q-body"), bp = JSON.parse(b.getAttribute("data-ph"));
        b.placeholder = bp[v] || bp[""];
        var pn = f.querySelector("[data-photo-need]"), pp = JSON.parse(pn.getAttribute("data-ph"));
        pn.textContent = pp[v] || "PNG, JPG 3장까지, 한 장 20MB 이하";
      } catch (err) {}
      var fs = f.querySelector(".qtype-pick"); if (fs) fs.classList.remove("has-err");
    });
    f.addEventListener("submit", function (e) {
      save();
      if (qv() === "학습질문" && !(inp.files && inp.files.length)) {
        e.preventDefault(); e.stopImmediatePropagation();
        showErr("학습질문은 문제 사진이 필요해요. 쓴 내용은 그대로 있어요.");
        wrap.scrollIntoView({ behavior: "smooth", block: "center" });
        inp.focus();
      }
    });
  });
})();

// ---------- 조교 답변: 기본 인사말이 미리 들어 있고, 처음 누르면 가운데 빈 줄에서 바로 쓰기 시작 ----------
document.querySelectorAll("textarea[data-answer-tpl]").forEach(function (t) {
  var tpl = t.value, mark = "질문 남겨주셔서 고마워요.\n\n", at = tpl.indexOf(mark);
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
// 복사 버튼: data-copy="요소 id" 의 글자를 클립보드로
document.addEventListener("click", function (e) {
  var b = e.target.closest && e.target.closest("[data-copy]");
  if (!b) return;
  var el = document.getElementById(b.getAttribute("data-copy"));
  if (!el || !navigator.clipboard) return;
  navigator.clipboard.writeText(el.textContent).then(function () {
    var t = b.textContent; b.textContent = "복사됨"; setTimeout(function () { b.textContent = t; }, 1400);
  });
});
// 질문 유형이 '학습상담'일 때만 상담 조교 고르기를 보인다
(function () {
  var f = document.querySelector("form[data-qform]"), box = document.querySelector("[data-consult]"), unit = document.querySelector("[data-unit-field]");
  if (!f || !box) return;
  function sync() {
    var c = f.querySelector("input[name=qtype]:checked"), v = c ? c.value : "";
    box.hidden = v !== "학습상담"; if (unit) unit.hidden = v !== "학습질문";
  }
  f.addEventListener("change", function (e) { if (e.target.name === "qtype") sync(); }); sync();
})();
// 시험지 첨삭: 메모가 빈 문항이 있으면 저장 전에 몇 번인지 알린다
(function () {
  var f = document.querySelector(".review-form-hw");
  if (!f) return;
  f.addEventListener("submit", function (e) {
    var empty = [];
    f.querySelectorAll('input[name^="m"]').forEach(function (inp) {
      if (!inp.value.trim()) empty.push(inp.name.slice(1) + "번");
    });
    if (!empty.length || f._confirmed) { f._confirmed = false; return; }
    e.preventDefault();
    askSheet("메모가 빈 문항: " + empty.join(", ") + "\n그대로 저장할까요?", function () { f._confirmed = true; f.requestSubmit ? f.requestSubmit() : f.submit(); });
  });
})();
// 사진 크게 보기: 첨부 사진 링크를 새 탭 대신 같은 화면 위에 연다 (누르거나 Esc 로 닫기)
document.addEventListener("click", function (e) {
  var a = e.target.closest && e.target.closest('a[target="_blank"]');
  if (!a || !a.querySelector("img") || a.href.indexOf("/file/") < 0) return;
  e.preventDefault();
  var box = document.createElement("div");
  box.className = "lightbox"; box.setAttribute("role", "dialog"); box.setAttribute("aria-label", "사진 크게 보기");
  var img = document.createElement("img"); img.src = a.href; img.alt = (a.querySelector("img").alt || "사진");
  box.appendChild(img);
  var close = function () { box.remove(); document.removeEventListener("keydown", esc); };
  var esc = function (k) { if (k.key === "Escape") close(); };
  box.addEventListener("click", close); document.addEventListener("keydown", esc);
  document.body.appendChild(box);
});

// ---------- 토스 스타일: 알림은 잠깐 떴다 사라짐, 이동 중 위쪽 줄, 그림 다 불러오면 회색 자리 해제 ----------
(function () {
  document.querySelectorAll(".flash").forEach(function (f, i) {
    var wait = (f.classList.contains("error") ? 6000 : 3200) + i * 400;
    var hide = function () { f.classList.add("is-out"); setTimeout(function () { f.remove(); }, 260); };
    var t = setTimeout(hide, wait);
    f.addEventListener("click", function () { clearTimeout(t); hide(); });
  });
  var bar = document.createElement("div");
  bar.className = "nav-progress";
  document.body.appendChild(bar);
  var go = function () { bar.classList.add("is-on"); };
  document.addEventListener("click", function (e) {
    var a = e.target.closest("a[href]");
    if (!a || e.defaultPrevented || e.metaKey || e.ctrlKey || e.shiftKey || a.target || a.hasAttribute("download")) return;
    var h = a.getAttribute("href");
    if (!h || h.charAt(0) === "#" || h.indexOf("javascript:") === 0 || a.origin !== location.origin) return;
    go();
  });
  document.addEventListener("submit", function (e) { if (!e.defaultPrevented && !e.target.target) go(); });
  window.addEventListener("pageshow", function () { bar.classList.remove("is-on"); });
  document.querySelectorAll("img").forEach(function (im) {
    var done = function () { im.classList.add("is-loaded"); };
    if (im.complete) done(); else { im.addEventListener("load", done); im.addEventListener("error", done); }
  });
})();

// 큰 숫자는 0에서 올라가며 나타난다 (앱 홈 숫자, 성적표 점수)
(function () {
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  document.querySelectorAll(".ah-stats b, .ah-score b, [data-count]").forEach(function (el) {
    var t = el.firstChild;
    if (!t || t.nodeType !== 3) return;
    var m = t.nodeValue.match(/^\s*(\d+(?:\.\d+)?)\s*$/);
    if (!m) return;
    var end = parseFloat(m[1]), dec = (m[1].split(".")[1] || "").length, t0 = performance.now();
    var step = function (now) {
      var k = Math.min(1, (now - t0) / 700), v = end * (1 - Math.pow(1 - k, 3));
      t.nodeValue = v.toFixed(dec);
      if (k < 1) requestAnimationFrame(step);
    };
    t.nodeValue = (0).toFixed(dec);
    requestAnimationFrame(step);
  });
})();

// 고르면 바로 이동하는 폼(data-autosubmit): 보기·이동 버튼은 숨긴다 (토스 글: 하나만 고르는 화면은 확인 버튼 없이)
document.querySelectorAll("form[data-autosubmit]").forEach(function (f) {
  f.querySelectorAll(".js-hide").forEach(function (b) { b.hidden = true; });
  f.addEventListener("change", function (e) { if (e.target.tagName === "SELECT") f.submit(); });
});

// 설명 버튼(원 안 물음표): 설명은 화면에 늘어놓지 않고 누르면 아래에서 올라온다 (_macros.html help)
document.addEventListener("click", function (e) {
  var btn = e.target.closest && e.target.closest("[data-help]");
  if (!btn) return;
  var tpl = btn.nextElementSibling;
  if (!tpl || tpl.tagName !== "TEMPLATE") return;
  var d = document.createElement("dialog");
  d.className = "sheet-dlg help-dlg";
  d.innerHTML = '<div class="sd-box"><h2></h2><div class="help-body"></div><button type="button" class="btn primary">확인</button></div>';
  d.querySelector("h2").textContent = tpl.getAttribute("data-help-title") || "";
  d.querySelector(".help-body").appendChild(tpl.content.cloneNode(true));
  document.body.appendChild(d);
  var close = function () { d.close(); d.remove(); btn.focus(); };
  d.addEventListener("click", function (ev) { if (ev.target === d || ev.target.closest(".btn.primary")) close(); });
  d.addEventListener("cancel", function (ev) { ev.preventDefault(); close(); });
  if (d.showModal) { d.showModal(); d.querySelector(".btn.primary").focus(); }
});

// 좁은 화면의 표: 칸마다 머리글을 달아 두면 CSS(.rowcards)가 한 줄씩 묶음으로 바꿔 보여 준다.
// 칸을 합친 표(rowspan, colspan)와 따로 이름을 붙인 표는 건드리지 않는다.
// 제목 칸은 표에 적어 둔다: <table data-rc-title="열 번호(0부터)">. 추측은 번호가 없는 표에서만 한다.
// 숫자를 견주는 표는 <table data-rc="off">: 묶음으로 바꾸지 않고 가로로 민다.
document.querySelectorAll(".is-staff main table:not(.sched):not(.sched-cal):not(.mark-table):not([data-rc=off])").forEach(function (t) {
  var fixed = t.getAttribute("data-rc-title");
  var rows = t.querySelectorAll("tr"), heads = rows.length ? rows[0].children : [];
  if (rows.length < 2 || rows[0].querySelector("td") || t.querySelector("[rowspan], [colspan]") || t.querySelectorAll("tr th:first-child").length > 1) return;
  rows[0].classList.add("rc-head");
  Array.prototype.slice.call(rows, 1).forEach(function (tr) {
    var title = null;
    Array.prototype.forEach.call(tr.children, function (td, i) {
      if (heads[i]) td.setAttribute("data-th", heads[i].innerHTML.replace(/<br\s*\/?>/g, " ").replace(/<[^>]*>/g, "").replace(/\s+/g, " ").trim());
      if (!title && td.querySelector("a[href]") && !td.querySelector("form, button")) title = td;
      if (td.textContent.trim().length > 28) td.classList.add("rc-wide");
      if (String(i) !== fixed && td.children.length === 1 && td.firstElementChild.classList.contains("badge") && td.textContent.trim() === td.firstElementChild.textContent.trim()) td.classList.add("rc-tag");
      if (!td.textContent.trim() && !td.querySelector("input, select, button, img, svg")) td.classList.add("rc-none");
    });
    if (fixed !== null && tr.children[+fixed]) title = tr.children[+fixed];
    if (!title) Array.prototype.slice.call(tr.children, 0, 3).forEach(function (td) {   // 링크가 없으면 앞 세 칸 중 글이 가장 긴 칸이 제목
      if (!td.querySelector("input, select, button, .badge") && (!title || td.textContent.trim().length > title.textContent.trim().length)) title = td;
    });
    (title || tr.children[0]).classList.add("rc-title");
  });
  t.classList.add("rowcards");
});

// 이름표 연결: 입력칸 위에 이름표만 놓인 곳(.field > label + 입력칸)을 화면 낭독기가 읽을 수 있게 for/id 로 잇는다.
// 이름표가 없는 입력칸은 칸 안 글(placeholder)을 이름으로 쓴다.
(function () {
  var n = 0;
  document.querySelectorAll(".field").forEach(function (f) {
    var lab = f.querySelector(":scope > label:not([for])"), ctl = f.querySelectorAll("input:not([type=hidden]):not([type=radio]):not([type=checkbox]), select, textarea");
    if (!lab || ctl.length !== 1 || lab.contains(ctl[0])) return;
    if (!ctl[0].id) ctl[0].id = "fld-" + (++n);
    lab.htmlFor = ctl[0].id;
  });
  document.querySelectorAll("input:not([type=hidden]), select, textarea").forEach(function (c) {
    if ((c.labels && c.labels.length) || c.getAttribute("aria-label") || c.getAttribute("aria-labelledby") || c.title) return;
    var td = c.closest("td"), name = c.getAttribute("placeholder") || (td && td.getAttribute("data-th")) || "";
    if (name) c.setAttribute("aria-label", name);
  });
})();
