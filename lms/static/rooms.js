// 같이 공부: 타이머, 25초마다 '여기 있어요' 신호, 장소별 배경 소리(파일 없이 브라우저에서 합성).
(function () {
function initRoom(room) {
  var beatUrl = room.getAttribute("data-beat"), doneUrl = room.getAttribute("data-done");
  var clock = room.querySelector("[data-clock]"), stateEl = room.querySelector("[data-state]");
  var startBtn = room.querySelector("[data-start]"), stopBtn = room.querySelector("[data-stop]");
  var msg = room.querySelector("[data-msg]"), list = room.querySelector("[data-members]"), count = room.querySelector("[data-count]");
  var status = room.getAttribute("data-status");
  var plan = parseInt(room.getAttribute("data-plan"), 10) || 25;
  var startTs = status === "focus" ? Date.now() - (parseInt(room.getAttribute("data-elapsed"), 10) || 0) * 60000 : 0;
  var tick = null;

  function token() { var m = document.querySelector('meta[name="csrf-token"]'); return m ? m.getAttribute("content") : ""; }
  function post(url, data) {
    var fd = new FormData(); fd.append("csrf_token", token());
    Object.keys(data || {}).forEach(function (k) { fd.append(k, data[k]); });
    return fetch(url, { method: "POST", body: fd, credentials: "same-origin" }).then(function (r) { return r.json(); });
  }
  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function chosenPlan() { var c = room.querySelector('input[name="plan"]:checked'); return c ? parseInt(c.value, 10) : 25; }

  function render() {
    var focusing = status === "focus";
    startBtn.hidden = focusing; stopBtn.hidden = !focusing;
    room.querySelectorAll('input[name="plan"]').forEach(function (i) { i.disabled = focusing; });
    room.classList.toggle("is-focus", focusing);
    if (!focusing) { clock.textContent = pad(chosenPlan()) + ":00"; stateEl.textContent = "준비"; return; }
    var left = Math.max(0, plan * 60 - Math.floor((Date.now() - startTs) / 1000));
    clock.textContent = pad(Math.floor(left / 60)) + ":" + pad(left % 60);
    stateEl.textContent = "집중 중";
    if (left === 0) finish(plan, true);
  }

  function drawMembers(ms) {
    if (!ms) return;
    list.innerHTML = "";
    ms.forEach(function (m) {
      var li = document.createElement("li");
      li.className = (m.status === "focus" ? "is-focus" : "") + (m.me ? " is-me" : "");
      var seat = document.createElement("i"); seat.className = "seat"; seat.setAttribute("aria-hidden", "true");
      var b = document.createElement("b"); b.textContent = m.nick + (m.me ? " (나)" : "");
      var s = document.createElement("span");
      s.textContent = (m.status === "focus" ? "집중 " + m.elapsed + "/" + m.plan + "분" : "쉬는 중") + " · 오늘 " + m.today + "분";
      li.appendChild(seat); li.appendChild(b); li.appendChild(s); list.appendChild(li);
    });
    count.textContent = ms.length + "명";
  }

  function beat(extra) { return post(beatUrl, extra).then(function (d) { drawMembers(d.members); return d; }).catch(function () {}); }

  function begin() {
    plan = chosenPlan();
    status = "focus"; startTs = Date.now();
    render(); sound.start(); sound.bell(0.35);
    beat({ action: "start", plan: plan });
    msg.textContent = plan + "분 집중을 시작했어요. 화면을 닫아도 기록은 여기까지 남아요.";
  }

  var finishing = false;
  function finish(minutes, complete) {
    if (finishing) return; finishing = true;
    post(doneUrl, { minutes: minutes }).then(function (d) {
      status = "rest"; render();
      if (complete) sound.bell(0.6);
      msg.textContent = d.minutes >= 5
        ? d.minutes + "분 기록했어요. 오늘 모두 " + d.today + "분."
        : "5분이 안 돼서 기록하지 않았어요. 오늘 " + d.today + "분.";
      beat();
    }).catch(function () { msg.textContent = "연결이 불안정해요. 잠시 뒤 다시 해 주세요."; })
      .then(function () { finishing = false; });
  }

  startBtn.addEventListener("click", begin);
  stopBtn.addEventListener("click", function () { finish(Math.floor((Date.now() - startTs) / 60000), false); });
  room.addEventListener("change", function (e) { if (e.target.name === "plan") render(); });

  tick = setInterval(render, 1000);
  render();
  setInterval(function () { if (!document.hidden) beat(); }, 25000);

  // 페이지를 떠나면: 집중 중이면 거기까지 기록, 아니면 자리 비움
  window.addEventListener("pagehide", function () {
    var fd = new FormData(); fd.append("csrf_token", token());
    if (status === "focus") { fd.append("minutes", Math.floor((Date.now() - startTs) / 60000)); navigator.sendBeacon(doneUrl, fd); }
    else { fd.append("action", "leave"); navigator.sendBeacon(beatUrl, fd); }
  });

  // ---------- 배경 소리 ----------
  var sound = (function () {
    var ctx = null, master = null, on = false, timers = [];
    var kind = room.getAttribute("data-sound");
    function noise(type) {
      var len = ctx.sampleRate * 4, buf = ctx.createBuffer(1, len, ctx.sampleRate), d = buf.getChannelData(0);
      var b0 = 0, b1 = 0, b2 = 0, last = 0;
      for (var i = 0; i < len; i++) {
        var w = Math.random() * 2 - 1;
        if (type === "pink") { b0 = 0.99765 * b0 + w * 0.099; b1 = 0.963 * b1 + w * 0.2965; b2 = 0.57 * b2 + w * 1.0526; d[i] = (b0 + b1 + b2 + w * 0.1848) * 0.2; }
        else if (type === "brown") { last = (last + 0.02 * w) / 1.02; d[i] = last * 3.5; }
        else d[i] = w * 0.5;
      }
      var src = ctx.createBufferSource(); src.buffer = buf; src.loop = true; return src;
    }
    function filt(type, f, q) { var x = ctx.createBiquadFilter(); x.type = type; x.frequency.value = f; if (q) x.Q.value = q; return x; }
    function lfo(param, rate, depth, base) {
      var o = ctx.createOscillator(), gn = ctx.createGain(); o.frequency.value = rate; gn.gain.value = depth;
      param.value = base; o.connect(gn); gn.connect(param); o.start(); return o;
    }
    function chain(src, nodes, gain) {
      var g = ctx.createGain(); g.gain.value = gain; var cur = src;
      nodes.forEach(function (n) { cur.connect(n); cur = n; }); cur.connect(g); g.connect(master); src.start(); return g;
    }
    function bell(vol) {
      if (!ctx) return;
      var t = ctx.currentTime, base = 196;
      [1, 2.76, 5.4, 8.93].forEach(function (r, i) {
        var o = ctx.createOscillator(), g = ctx.createGain();
        o.frequency.value = base * r; g.gain.setValueAtTime(0.0001, t);
        g.gain.exponentialRampToValueAtTime(vol * [0.5, 0.25, 0.12, 0.06][i], t + 0.02);
        g.gain.exponentialRampToValueAtTime(0.0001, t + 7 - i);
        o.connect(g); g.connect(ctx.destination); o.start(t); o.stop(t + 7.5);
      });
    }
    function drip() {
      var t = ctx.currentTime, o = ctx.createOscillator(), g = ctx.createGain();
      o.frequency.setValueAtTime(900 + Math.random() * 700, t); o.frequency.exponentialRampToValueAtTime(400, t + 0.12);
      g.gain.setValueAtTime(0.06, t); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.2);
      o.connect(g); g.connect(master); o.start(t); o.stop(t + 0.25);
    }
    function every(fn, min, max) {
      (function loop() { timers.push(setTimeout(function () { if (on) { fn(); loop(); } }, min + Math.random() * (max - min))); })();
    }
    function build() {
      master = ctx.createGain(); master.gain.value = 0.55; master.connect(ctx.destination);
      if (kind === "wind") {
        var g = chain(noise("pink"), [filt("lowpass", 520)], 0.25); lfo(g.gain, 0.07, 0.15, 0.25);
        every(function () { bell(0.18); }, 40000, 75000);
      } else if (kind === "water") {
        chain(noise("brown"), [filt("lowpass", 650)], 0.35);
        every(drip, 900, 3800);
      } else if (kind === "waves") {
        var w = chain(noise("brown"), [filt("lowpass", 900)], 0.35); lfo(w.gain, 0.085, 0.3, 0.35);
      } else {
        chain(noise("white"), [filt("highpass", 1200), filt("lowpass", 7000)], 0.09);
        chain(noise("pink"), [filt("lowpass", 300)], 0.18);
      }
    }
    var btn = room.querySelector("[data-sound-toggle]");
    function label() { if (btn) { btn.textContent = on ? "소리 끄기" : "소리 켜기"; btn.setAttribute("aria-pressed", on ? "true" : "false"); } }
    // 아이폰 무음 스위치: 브라우저가 만든 소리는 '알림음'으로 취급돼 꺼진다.
    // '미디어 재생'으로 취급받도록 (1) iOS 17+ 오디오 세션을 playback 으로, (2) 무음 파일을 함께 반복 재생.
    var keepAlive = null;
    function mediaMode(onOff) {
      try { if (navigator.audioSession) navigator.audioSession.type = onOff ? "playback" : "auto"; } catch (_) {}
      if (onOff) {
        if (!keepAlive) {
          keepAlive = new Audio("/static/silence.wav");
          keepAlive.loop = true; keepAlive.setAttribute("playsinline", ""); keepAlive.preload = "auto";
        }
        var p = keepAlive.play(); if (p && p.catch) p.catch(function () {});
      } else if (keepAlive) { keepAlive.pause(); }
    }
    function start() {
      mediaMode(true);
      try {
        if (!ctx) { ctx = new (window.AudioContext || window.webkitAudioContext)(); }
        if (ctx.state === "suspended") ctx.resume();
        if (!on) { on = true; build(); }
      } catch (_) {}
      label();
    }
    function stop() {
      on = false; timers.forEach(clearTimeout); timers = [];
      if (master) { master.disconnect(); master = null; }
      if (ctx) { ctx.close(); ctx = null; }
      mediaMode(false);
      label();
    }
    if (btn) btn.addEventListener("click", function () { on ? stop() : start(); });
    return { start: start, stop: stop, bell: function (v) { if (ctx) bell(v); } };
  })();
}
window.initRoom = initRoom;
var first = document.querySelector("[data-room]");
if (first && !window.LAB_PREVIEW) initRoom(first);
})();
