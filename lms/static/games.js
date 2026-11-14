// 미니게임 화면. 서버에서 받은 글은 textContent 로만 넣는다 (XSS 방지).
(function () {
  "use strict";

  var csrf = document.querySelector('meta[name="csrf-token"]');

  function post(url, body) {
    return fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf ? csrf.content : "" },
      body: JSON.stringify(body || {})
    }).then(function (r) {
      if (r.status === 410) throw new Error("시간이 지나 끝났습니다. 다시 시작해 주세요.");
      if (r.status === 401 || r.redirected) throw new Error("로그인이 만료됐어요. 새로고침해 주세요.");
      if (!r.ok) throw new Error("오류가 났습니다. 잠시 후 다시 해 주세요.");
      return r.json();
    });
  }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }

  function show(root, role) {
    root.querySelectorAll("[data-role=start],[data-role=play],[data-role=result],[data-role=loading]")
      .forEach(function (n) { n.classList.toggle("hidden", n.getAttribute("data-role") !== role); });
  }

  // ---------- 염기 짝 맞추기 ----------
  var dna = document.getElementById("dna-game");
  if (dna) {
    var q = function (r) { return dna.querySelector("[data-role=" + r + "]"); };
    var state = null, timer = null;

    var renderStrands = function () {
      var t = q("template"), a = q("answer");
      t.textContent = ""; a.textContent = "";
      for (var i = 0; i < state.strand.length; i++) {
        t.appendChild(el("span", "cell base-" + state.strand[i], state.strand[i]));
        var b = state.input[i] || "";
        var cell = el("span", "cell" + (b ? " base-" + b : "") + (i === state.input.length ? " cursor" : ""), b || "·");
        if (state.results) cell.classList.add(state.results[i] ? "ok" : "wrong");
        a.appendChild(cell);
      }
      q("progress").textContent = state.input.length + " / " + state.strand.length;
    };

    var finish = function () {
      if (!state || state.done) return;
      state.done = true;
      clearInterval(timer);
      post(dna.dataset.start.replace(/\/start$/, "/" + state.id + "/submit"), { answer: state.input.join("") })
        .then(function (res) {
          state.results = res.results;
          renderStrands();
          q("result-title").textContent = res.timeout ? "시간 초과!" :
            (res.correct + " / " + res.total + (res.correct === res.total ? " 만점" : ""));
          q("result-detail").textContent = "걸린 시간 " + res.elapsed + "초" +
            (res.correct < res.total ? " (정답: " + res.answer + ")" : "");
          q("result").classList.remove("hidden");
        })
        .catch(function (e) { alert(e.message); });
    };

    var press = function (b) {
      if (!state || state.done) return;
      if (b === "back") state.input.pop();
      else if (state.input.length < state.strand.length) state.input.push(b);
      renderStrands();
      if (state.input.length === state.strand.length) finish();
    };

    dna.querySelectorAll("[data-level]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        post(dna.dataset.start, { level: Number(btn.dataset.level), mode: dna.dataset.mode || "dna" }).then(function (res) {
          state = { id: res.round_id, strand: res.strand, input: [], started: Date.now(), done: false, results: null };
          show(dna, "play");
          renderStrands();
          var limit = res.time_limit;
          q("timer").textContent = "⏱ " + limit + "초";
          timer = setInterval(function () {
            var left = limit - Math.floor((Date.now() - state.started) / 1000);
            q("timer").textContent = "⏱ " + Math.max(0, left) + "초";
            if (left <= 0) finish();
          }, 250);
        }).catch(function (e) { alert(e.message); });
      });
    });
    dna.querySelectorAll("[data-base]").forEach(function (btn) {
      btn.addEventListener("click", function () { press(btn.dataset.base); });
    });
    document.addEventListener("keydown", function (e) {
      if (!state || state.done) return;
      var k = e.key.toUpperCase();
      var keysOk = dna.dataset.mode === "rna" ? "AUGC" : "ATGC";
      if (keysOk.indexOf(k) >= 0 && k.length === 1) press(k);
      else if (e.key === "Backspace") { e.preventDefault(); press("back"); }
    });
    q("again").addEventListener("click", function () { state = null; show(dna, "start"); });
  }

  // ---------- 객관식 (샤가프 / 통합과학 퀴즈) ----------
  var mc = document.getElementById("mc-game");
  if (mc) {
    var m = function (r) { return mc.querySelector("[data-role=" + r + "]"); };
    var game = null;

    var renderQuestion = function () {
      var item = game.questions[game.i], kind = item.kind || "mc";
      m("progress").textContent = (game.i + 1) + " / " + game.questions.length;
      m("score").textContent = game.i ? "맞힌 문제 " + game.score : "";
      var qEl = m("question");
      qEl.textContent = ""; qEl.className = "mc-question kind-" + kind;
      if (item.tag) qEl.appendChild(el("span", "mc-tag", item.tag));
      if (item.prompt) qEl.appendChild(el("span", "mc-prompt", item.prompt));
      var main = el("span", "mc-main");
      if (kind === "fill") {
        var parts = item.question.split("___");
        main.appendChild(document.createTextNode(parts[0]));
        game.blank = el("span", "mc-blank", "\u00a0"); main.appendChild(game.blank);
        main.appendChild(document.createTextNode(parts.slice(1).join("___")));
      } else if (kind === "listen") {
        main.textContent = "?"; main.classList.add("is-hidden-word"); main.setAttribute("lang", "en");
      } else {
        main.textContent = item.question;
        if (kind === "mc" || kind === "ox") main.setAttribute("lang", "en");
      }
      game.main = main;
      qEl.appendChild(main);
      if (kind === "pick") {
        var ul = el("ol", "pk-lines");
        item.lines.forEach(function (t, n) { var li = el("li"); li.appendChild(el("b", "", "ㄱㄴㄷ".charAt(n) + ".")); li.appendChild(el("span", "", t)); ul.appendChild(li); });
        qEl.appendChild(ul);
      }
      if (item.sub) qEl.appendChild(el("span", "mc-sub", item.sub));
      var box = m("choices"), fb = m("feedback");
      box.textContent = ""; box.className = "mc-choices kind-" + kind; fb.textContent = ""; fb.className = "mc-feedback hidden";
      if (kind === "spell") return renderSpell(item, box);
      if (kind === "num") return renderNum(item, box);
      if (kind === "sort") return renderSort(item, box);
      if (kind === "order") return renderOrder(item, box);
      if (kind === "listen") {
        var say = el("button", "btn mc-say", "다시 듣기"); say.type = "button";
        say.addEventListener("click", function () { speak(item.say, main); });
        qEl.appendChild(say);
        speak(item.say, main);
      }
      var buttons = [];
      item.choices.forEach(function (c, idx) {
        var label = kind === "ox" ? (idx === 0 ? "O  " : "X  ") + c : kind === "tf" ? c : kind === "fill" ? c :
          kind === "pick" ? "①②③④⑤".charAt(idx) + " " + c : (idx + 1) + ". " + c;
        var b = el("button", "btn mc-choice" + (kind === "ox" || kind === "tf" ? (idx === 0 ? " ox-o" : " ox-x") : ""), label);
        b.type = "button";
        if (kind === "rev") b.setAttribute("lang", "en");
        b.addEventListener("click", function () { check(idx, buttons); });
        buttons.push(b); box.appendChild(b);
      });
      if (buttons[0]) buttons[0].focus({ preventScroll: true });
    };

    // 영어 발음 (브라우저 내장 음성). 소리를 낼 수 없으면 단어를 그냥 보여 준다.
    var speak = function (word, main) {
      var ss = window.speechSynthesis;
      if (!ss || !window.SpeechSynthesisUtterance) { main.textContent = word; main.classList.remove("is-hidden-word"); return; }
      ss.cancel();
      var u = new SpeechSynthesisUtterance(word);
      u.lang = "en-US"; u.rate = 0.85;
      var v = ss.getVoices().filter(function (x) { return /^en(-|_)US/i.test(x.lang); })[0];
      if (v) u.voice = v;
      ss.speak(u);
    };

    var sendPick = function (pick) {
      if (game.busy) return Promise.reject(null);
      game.busy = true;
      return post(mc.dataset.start.replace(/\/start$/, "/" + game.id + "/check"), { i: game.i, pick: pick })
        .then(function (res) { game.answers[game.i] = res.pick; game.score = res.score; game.busy = false; return res; },
              function (e) { game.busy = false; throw e; });
    };
    var fail = function (e) { if (e) alert(e.message); };

    // 계산: 숫자를 직접 입력
    var renderNum = function (item, box) {
      var row = el("div", "nm-row");
      var inp = el("input", "nm-input"); inp.type = "text"; inp.inputMode = "decimal"; inp.autocomplete = "off";
      inp.setAttribute("aria-label", "답"); inp.maxLength = 12;
      var ok = el("button", "btn primary", "확인"); ok.type = "button";
      row.appendChild(inp); row.appendChild(el("span", "nm-unit", item.unit)); row.appendChild(ok);
      box.appendChild(row);
      var go = function () {
        var v = inp.value.trim(); if (!v) { inp.focus(); return; }
        inp.disabled = true; ok.disabled = true;
        sendPick(v).then(function (res) {
          row.classList.add(res.correct ? "is-right" : "is-wrong");
          showFeedback(res, res.answer_text);
        }).catch(function (e) { inp.disabled = false; ok.disabled = false; fail(e); });
      };
      ok.addEventListener("click", go);
      inp.addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); go(); } });
      inp.focus({ preventScroll: true });
    };

    // 분류하기: 항목마다 칸을 고른다
    var renderSort = function (item, box) {
      var chosen = item.items.map(function () { return null; }), rows = [];
      var ok = el("button", "btn primary", "확인"); ok.type = "button"; ok.disabled = true;
      var long = item.bins.join("").length > 14 || item.bins.length > 3;
      var list = el("div", "so-list" + (long ? " is-long" : ""));
      item.items.forEach(function (label, r) {
        var row = el("div", "so-row"), segs = el("div", "so-segs");
        row.appendChild(el("span", "so-item", label));
        item.bins.forEach(function (bin, b) {
          var s = el("button", "so-seg", bin); s.type = "button";
          s.addEventListener("click", function () {
            chosen[r] = b;
            segs.querySelectorAll(".so-seg").forEach(function (x, k) { x.classList.toggle("is-on", k === b); x.setAttribute("aria-pressed", k === b); });
            ok.disabled = chosen.indexOf(null) >= 0;
          });
          segs.appendChild(s);
        });
        row.appendChild(segs); rows.push(row); list.appendChild(row);
      });
      box.appendChild(list); box.appendChild(ok);
      ok.addEventListener("click", function () {
        ok.disabled = true; box.querySelectorAll(".so-seg").forEach(function (x) { x.disabled = true; });
        sendPick(chosen).then(function (res) {
          var right = 0;
          rows.forEach(function (row, r) {
            var good = chosen[r] === res.answer_list[r]; if (good) right++;
            row.classList.add(good ? "is-right" : "is-wrong");
            row.querySelectorAll(".so-seg")[res.answer_list[r]].classList.add("is-answer");
          });
          ok.classList.add("is-spent");
          showFeedback(res, null, right + " / " + rows.length + "개 맞음");
        }).catch(function (e) { ok.disabled = false; box.querySelectorAll(".so-seg").forEach(function (x) { x.disabled = false; }); fail(e); });
      });
    };

    // 순서 맞추기: 눌러서 차례로 쌓고, 쌓인 것을 누르면 빠진다
    var renderOrder = function (item, box) {
      var seq = [];
      var slots = el("ol", "or-slots"), pool = el("div", "or-pool");
      var ok = el("button", "btn primary", "확인"); ok.type = "button";
      var chips = item.items.map(function (label, k) {
        var c = el("button", "or-chip", label); c.type = "button";
        c.addEventListener("click", function () {
          if (seq.indexOf(k) >= 0) return;
          seq.push(k);
          if (seq.length === item.items.length - 1) {          // 마지막 하나는 자리가 정해져 있으니 자동으로
            for (var r = 0; r < item.items.length; r++) if (seq.indexOf(r) < 0) seq.push(r);
          }
          draw();
        });
        pool.appendChild(c); return c;
      });
      var draw = function () {
        slots.textContent = "";
        for (var n = 0; n < item.items.length; n++) {
          var k = seq[n];
          var li = el("li", "or-slot" + (k === undefined ? " is-empty" : ""));
          if (k !== undefined) {
            var b = el("button", "or-placed", item.items[k]); b.type = "button";
            (function (kk) { b.addEventListener("click", function () { if (!game.busy && !slots.classList.contains("is-done")) { seq.splice(seq.indexOf(kk), 1); draw(); } }); })(k);
            li.appendChild(b);
          }
          slots.appendChild(li);
        }
        chips.forEach(function (c, k) { c.disabled = seq.indexOf(k) >= 0; });
        ok.disabled = seq.length !== item.items.length;
      };
      box.appendChild(slots); box.appendChild(pool); box.appendChild(ok);
      ok.addEventListener("click", function () {
        ok.disabled = true; slots.classList.add("is-done");
        sendPick(seq.slice()).then(function (res) {
          slots.querySelectorAll(".or-slot").forEach(function (li, n) { li.classList.add(seq[n] === res.answer_list[n] ? "is-right" : "is-wrong"); });
          pool.classList.add("hidden"); ok.classList.add("is-spent");
          showFeedback(res, res.answer_text);
        }).catch(function (e) { ok.disabled = false; slots.classList.remove("is-done"); fail(e); });
      });
      draw();
    };

    // 철자 맞추기: 글자 조각을 눌러 칸을 채운다 (지우기 · 확인)
    var renderSpell = function (item, box) {
      var typed = [], used = [];
      var slots = el("div", "sp-slots"), tiles = el("div", "sp-tiles"), ctl = el("div", "sp-ctl");
      var draw = function () {
        slots.textContent = "";
        for (var k = 0; k < item.n; k++) {
          var ch = typed[k] ? typed[k].c : "";
          slots.appendChild(el("span", "sp-slot" + (typed[k] ? " is-on" : ""), ch || "\u00a0"));
        }
        tiles.querySelectorAll("button").forEach(function (b, k) { b.disabled = used.indexOf(k) >= 0 || typed.length >= item.n; });
        ok.disabled = typed.length !== item.n;
      };
      item.tiles.forEach(function (c, k) {
        var b = el("button", "sp-tile", c); b.type = "button"; b.setAttribute("lang", "en");
        b.addEventListener("click", function () { if (typed.length < item.n) { typed.push({ c: c, k: k }); used.push(k); draw(); } });
        tiles.appendChild(b);
      });
      var back = el("button", "btn small", "지우기"); back.type = "button";
      back.addEventListener("click", function () { var t = typed.pop(); if (t) used.splice(used.indexOf(t.k), 1); draw(); });
      var ok = el("button", "btn primary", "확인"); ok.type = "button";
      ok.addEventListener("click", function () {
        tiles.querySelectorAll("button").forEach(function (b) { b.disabled = true; }); back.disabled = true; ok.disabled = true;
        checkText(typed.map(function (t) { return t.c; }).join(""), slots);
      });
      ctl.appendChild(back); ctl.appendChild(ok);
      box.appendChild(slots); box.appendChild(tiles); box.appendChild(ctl);
      game.keySpell = function (e) {
        if (e.key === "Backspace") { e.preventDefault(); back.click(); return; }
        if (e.key === "Enter") { if (!ok.disabled) ok.click(); return; }
        var k2 = e.key.toLowerCase();
        for (var k = 0; k < item.tiles.length; k++) if (item.tiles[k] === k2 && used.indexOf(k) < 0) { tiles.children[k].click(); return; }
      };
      draw();
    };

    var showFeedback = function (res, rightLabel, note) {
      var fb = m("feedback");
      fb.className = "mc-feedback " + (res.correct ? "ok" : "wrong");
      fb.textContent = "";
      fb.appendChild(el("b", "", res.correct ? "정답" : "오답" + (note ? " · " + note : rightLabel ? " · 정답 " + rightLabel : "")));
      if (res.explanation) res.explanation.split(" / ").forEach(function (t) { fb.appendChild(el("p", "", t)); });
      var last = game.i + 1 >= game.questions.length;
      var next = el("button", "btn primary", last ? "결과 보기" : "다음 문제");
      next.type = "button";
      next.addEventListener("click", function () {
        game.keySpell = null;
        game.i += 1;
        if (game.i < game.questions.length) renderQuestion(); else submit();
      });
      fb.appendChild(next);
      m("score").textContent = "맞힌 문제 " + res.score;
      if (res.correct && /^vocab/.test(mc.dataset.game || "")) {        // 영단어: 맞히면 자동으로 다음 문제
        var at = game.i;
        fb.classList.add("is-auto");
        setTimeout(function () { if (game && game.i === at && document.body.contains(next)) next.click(); }, 900);
      }
      next.focus({ preventScroll: true });
      fb.scrollIntoView({ behavior: "smooth", block: "nearest" });
    };

    var checkText = function (text, slots) {
      if (game.busy) return; game.busy = true;
      post(mc.dataset.start.replace(/\/start$/, "/" + game.id + "/check"), { i: game.i, pick: text })
        .then(function (res) {
          game.answers[game.i] = res.pick; game.score = res.score;
          slots.classList.add(res.correct ? "is-right" : "is-wrong");
          showFeedback(res, res.answer_text);
        })
        .catch(function (e) { alert(e.message); })
        .then(function () { game.busy = false; });
    };

    // 한 문제 고르면 바로 채점: 맞으면 초록, 틀리면 빨강 + 정답 초록, 해설과 '다음 문제'
    var check = function (idx, buttons) {
      if (game.busy) return; game.busy = true;
      buttons.forEach(function (b) { b.disabled = true; });
      buttons[idx].classList.add("is-picked");
      post(mc.dataset.start.replace(/\/start$/, "/" + game.id + "/check"), { i: game.i, pick: idx })
        .then(function (res) {
          game.answers[game.i] = res.pick; game.score = res.score;
          if (buttons[res.answer_index]) buttons[res.answer_index].classList.add("is-right");
          if (!res.correct && buttons[res.pick]) buttons[res.pick].classList.add("is-wrong");
          var item = game.questions[game.i];
          if (item.kind === "fill" && game.blank) {
            game.blank.textContent = item.choices[res.answer_index]; game.blank.classList.add(res.correct ? "is-right" : "is-wrong");
          }
          if (item.kind === "listen") { game.main.textContent = item.say; game.main.classList.remove("is-hidden-word"); }
          showFeedback(res, item.kind === "ox" || item.kind === "tf" ? (res.answer_index === 0 ? "O" : "X") :
            item.kind === "pick" ? "①②③④⑤".charAt(res.answer_index) + " " + item.choices[res.answer_index] :
            item.kind === "fill" || item.kind === "listen" ? item.choices[res.answer_index] : (res.answer_index + 1) + "번");
        })
        .catch(function (e) {
          buttons.forEach(function (b) { b.disabled = false; b.classList.remove("is-picked"); });
          alert(e.message);
        })
        .then(function () { game.busy = false; });
    };
    document.addEventListener("keydown", function (e) { if (game && game.keySpell && !e.target.closest("input, textarea")) game.keySpell(e); });

    var submit = function () {
      show(mc, "loading");
      post(mc.dataset.start.replace(/\/start$/, "/" + game.id + "/submit"), { answers: game.answers })
        .then(function (res) {
          m("result-title").textContent = res.score + " / " + res.total + (res.score === res.total ? " 만점" : "");
          m("result-detail").textContent = res.score === res.total ? "" : "틀린 문제 " + (res.total - res.score) + "개";
          var review = m("review");
          review.textContent = "";
          res.results.forEach(function (r, i) {
            var item = game.questions[i];
            var box = el("div", "review-item " + (r.correct ? "ok" : "wrong"));
            var q = (item.kind === "listen" ? item.say : item.question) + (item.sub ? " → " + item.sub : "") +
              (item.lines ? "  " + item.lines.map(function (t, n) { return "ㄱㄴㄷ".charAt(n) + ". " + t; }).join("  ") : "");
            box.appendChild(el("b", ""));
            box.firstChild.textContent = (r.correct ? "맞음 · " : "틀림 · ") + (i + 1) + ". " + q;
            if (!r.correct) box.appendChild(el("div", "small", "내 답: " + r.mine));
            box.appendChild(el("div", "small", "정답: " + r.answer));
            box.appendChild(el("div", "small muted", r.explanation));
            review.appendChild(box);
          });
          show(mc, "result");
        })
        .catch(function (e) { alert(e.message); show(mc, "start"); });
    };

    var startRound = function (body) {
      show(mc, "loading");
      post(mc.dataset.start, body)
        .then(function (res) {
          game = { id: res.round_id, questions: res.questions, answers: [], i: res.done || 0, score: res.score || 0, busy: false };
          if (game.i >= game.questions.length) { submit(); return; }
          show(mc, "play");
          renderQuestion();
        })
        .catch(function (e) { alert(e.message); show(mc, "start"); });
    };
    m("begin").addEventListener("click", function () {
      var topic = m("topic");
      startRound(topic ? { topic: topic.value } : {});
    });
    if (m("resume")) m("resume").addEventListener("click", function () { startRound({ resume: 1 }); });
    m("again").addEventListener("click", function () { show(mc, "start"); });
  }

  // ---------- 스피드 O/X: 60초 동안 많이 맞히기 ----------
  var sp = document.getElementById("speed-game");
  if (sp) {
    var sq = function (r) { return sp.querySelector("[data-role=" + r + "]"); };
    var run = null, tick = null;
    var drawItem = function () {
      var it = run.items[run.i];
      if (!it) return end();
      sq("tag").textContent = it.tag || "";
      sq("q").textContent = it.q; sq("a").textContent = it.a;
      var card = sq("card"); card.classList.remove("is-ok", "is-no"); void card.offsetWidth;
    };
    var pick = function (o) {
      if (!run || run.done) return;
      var it = run.items[run.i], right = (o === it.ok);
      run.picks[run.i] = o;
      if (right) { run.score++; run.combo++; } else run.combo = 0;
      sq("score").textContent = run.score;
      sq("combo").textContent = run.combo >= 3 ? run.combo + "연속" : "";
      var card = sq("card"); card.classList.add(right ? "is-ok" : "is-no");
      run.i++;
      setTimeout(drawItem, right ? 120 : 380);
    };
    var end = function () {
      if (!run || run.done) return; run.done = true; clearInterval(tick);
      show(sp, "loading");
      post(sp.dataset.start.replace(/\/start$/, "/" + run.id + "/submit"), { picks: run.picks })
        .then(function (res) {
          sq("result-title").textContent = res.score + "개 정답";
          sq("result-detail").textContent = res.tried + "개 중 " + res.score + "개" + (res.best ? " · 최고 " + res.best + "개" : "");
          var rv = sq("review"); rv.textContent = "";
          if (res.missed.length) rv.appendChild(el("p", "small muted", "틀린 문제"));
          res.missed.forEach(function (x) {
            var b = el("div", "review-item wrong");
            b.appendChild(el("b", "", x.q + (x.a ? " → " + x.a : "") + "  (" + (x.ok ? "O" : "X") + ")"));
            b.appendChild(el("div", "small muted", x.exp));
            rv.appendChild(b);
          });
          show(sp, "result");
        }).catch(function (e) { alert(e.message); show(sp, "start"); });
    };
    sq("begin").addEventListener("click", function () {
      show(sp, "loading");
      post(sp.dataset.start, {}).then(function (res) {
        run = { id: res.round_id, items: res.items, picks: [], i: 0, score: 0, combo: 0, done: false, t0: Date.now(), secs: res.seconds };
        sq("score").textContent = "0"; sq("combo").textContent = "";
        show(sp, "play"); drawItem();
        tick = setInterval(function () {
          var left = run.secs - (Date.now() - run.t0) / 1000;
          sq("time").textContent = Math.max(0, Math.ceil(left));
          sq("track").style.width = Math.max(0, left / run.secs * 100) + "%";
          if (left <= 0) end();
        }, 100);
      }).catch(function (e) { alert(e.message); show(sp, "start"); });
    });
    sp.querySelectorAll("[data-pick]").forEach(function (b) { b.addEventListener("click", function () { pick(b.dataset.pick === "o"); }); });
    document.addEventListener("keydown", function (e) {
      if (!run || run.done) return;
      if (e.key === "ArrowLeft" || e.key.toLowerCase() === "o") pick(true);
      else if (e.key === "ArrowRight" || e.key.toLowerCase() === "x") pick(false);
    });
    sq("again").addEventListener("click", function () { run = null; show(sp, "start"); });
  }

  // ---------- 짝 맞추기: 단어와 뜻을 이어요 ----------
  var mt = document.getElementById("match-game");
  if (mt) {
    var mq = function (r) { return mt.querySelector("[data-role=" + r + "]"); };
    var st = null, clk = null;
    var shuffle = function (a) { a = a.slice(); for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; } return a; };
    var drawSet = function () {
      var all = st.sets[st.k], L = mq("left"), R = mq("right");
      var set = all.filter(function (p) { return !p.d; });
      L.textContent = ""; R.textContent = ""; st.sel = null; st.left = set.length;
      mq("progress").textContent = (st.k + 1) + " / " + st.sets.length + "판";
      shuffle(set).forEach(function (p) {
        var b = el("button", "mt-item", p.w); b.type = "button"; b.dataset.w = p.w; b.setAttribute("lang", "en");
        b.addEventListener("click", function () { choose(b, "w"); }); L.appendChild(b);
      });
      shuffle(all).forEach(function (p) {
        var b = el("button", "mt-item", p.m); b.type = "button"; b.dataset.w = p.w;
        b.addEventListener("click", function () { choose(b, "m"); }); R.appendChild(b);
      });
    };
    var choose = function (b, side) {
      if (b.classList.contains("is-done")) return;
      if (!st.sel || st.sel.side === side) {
        if (st.sel) st.sel.b.classList.remove("is-sel");
        st.sel = { b: b, side: side }; b.classList.add("is-sel"); return;
      }
      var a = st.sel.b; st.sel = null; a.classList.remove("is-sel");
      if (a.dataset.w === b.dataset.w) {
        a.classList.add("is-done"); b.classList.add("is-done"); a.disabled = b.disabled = true;
        if (--st.left === 0) setTimeout(function () { st.k++; if (st.k < st.sets.length) drawSet(); else finishMatch(); }, 280);
      } else {
        var w = side === "w" ? b.dataset.w : a.dataset.w;
        if (st.wrong.indexOf(w) < 0) st.wrong.push(w);
        [a, b].forEach(function (x) { x.classList.add("is-bad"); setTimeout(function () { x.classList.remove("is-bad"); }, 420); });
      }
    };
    var finishMatch = function () {
      clearInterval(clk); var secs = (Date.now() - st.t0) / 1000;
      show(mt, "loading");
      post(mt.dataset.start.replace(/\/start$/, "/" + st.id + "/submit"), { wrong: st.wrong, seconds: secs })
        .then(function (res) {
          mq("result-title").textContent = res.score + " / " + res.total + (res.score === res.total ? " 만점" : "");
          mq("result-detail").textContent = secs.toFixed(1) + "초" + (res.wrong.length ? " · 복습으로: " + res.wrong.join(", ") : "");
          show(mt, "result");
        }).catch(function (e) { alert(e.message); show(mt, "start"); });
    };
    mq("begin").addEventListener("click", function () {
      show(mt, "loading");
      post(mt.dataset.start, {}).then(function (res) {
        st = { id: res.round_id, sets: res.sets, k: 0, wrong: [], t0: Date.now() };
        show(mt, "play"); drawSet();
        clk = setInterval(function () { mq("clock").textContent = ((Date.now() - st.t0) / 1000).toFixed(1) + "초"; }, 100);
      }).catch(function (e) { alert(e.message); show(mt, "start"); });
    });
    mq("again").addEventListener("click", function () { show(mt, "start"); });
  }

  // ---------- TOPIC 개념 게임: 중화 반응 · 산화 환원 · 전자 배치 ----------
  var pl = document.getElementById("play-game");
  if (pl) {
    var pq = function (r) { return pl.querySelector("[data-role=" + r + "]"); };
    var kind = pl.dataset.game, pg = null;
    var base = function () { return pl.dataset.start.replace(/\/start$/, "/" + pg.id); };

    var feedback = function (res, extra) {
      var fb = pq("feedback");
      fb.className = "mc-feedback " + (res.correct ? "ok" : "wrong"); fb.textContent = "";
      fb.appendChild(el("b", "", res.correct ? "정답" : "오답" + (extra ? " · " + extra : "")));
      fb.appendChild(el("p", "", res.explanation));
      var last = pg.i + 1 >= pg.stages.length;
      var nx = el("button", "btn primary", last ? "결과 보기" : "다음"); nx.type = "button";
      nx.addEventListener("click", function () { pg.i++; if (pg.i < pg.stages.length) stage(); else finish(); });
      fb.appendChild(nx);
      pq("score").textContent = "맞힘 " + res.score;
      nx.focus({ preventScroll: true }); fb.scrollIntoView({ behavior: "smooth", block: "nearest" });
    };
    var send = function (pick) {
      return post(base() + "/check", { i: pg.i, pick: pick });
    };

    // ---- 그림: 개념서 그림체 (단색 면, 얇은 회색·검정 선, 그라데이션·그림자 없음) ----
    var NS = "http://www.w3.org/2000/svg";
    var sv = function (tag, attrs, parent) {
      var e = document.createElementNS(NS, tag);
      for (var k in attrs) e.setAttribute(k, attrs[k]);
      if (parent) parent.appendChild(e);
      return e;
    };
    var txt = function (parent, x, y, text, cls, anchor) {
      var t = sv("text", { x: x, y: y, class: cls || "", "text-anchor": anchor || "middle", "dominant-baseline": "central" }, parent);
      t.textContent = text; return t;
    };
    var hash = function (n) { var x = Math.sin(n * 12.9898 + 78.233) * 43758.5453; return x - Math.floor(x); };
    // 화학식: 아래·위 첨자 문자를 작은 글자로 따로 (SDIJ 사용 디렉션: 첨자는 Regular를 작게)
    var SUB = "₀₁₂₃₄₅₆₇₈₉", SUP = "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻";
    var plain = function (ch) {
      var i = SUB.indexOf(ch); if (i >= 0) return ["sub", String(i)];
      i = SUP.indexOf(ch); if (i >= 0) return ["sup", i < 10 ? String(i) : (ch === "⁺" ? "+" : "−")];
      return [null, ch];
    };
    var chem = function (node, text) {                   // HTML
      var run = "", flush = function () { if (run) { node.appendChild(document.createTextNode(run)); run = ""; } };
      for (var i = 0; i < text.length; i++) {
        var c = plain(text[i]);
        if (!c[0]) { run += c[1]; continue; }
        flush();
        var e = document.createElement(c[0]); e.textContent = c[1];
        while (i + 1 < text.length && plain(text[i + 1])[0] === c[0]) { i++; e.textContent += plain(text[i])[1]; }
        node.appendChild(e);
      }
      flush(); return node;
    };
    var svgChem = function (t, text, size) {             // SVG <text> 안 tspan
      for (var i = 0; i < text.length; i++) {
        var c = plain(text[i]);
        if (!c[0]) { var a = sv("tspan", {}, t); a.textContent = c[1]; continue; }
        var str = c[1];
        while (i + 1 < text.length && plain(text[i + 1])[0] === c[0]) { i++; str += plain(text[i])[1]; }
        var sp = sv("tspan", { "font-size": (size * 0.62).toFixed(1), dy: c[0] === "sub" ? (size * 0.28).toFixed(1) : (-size * 0.38).toFixed(1) }, t);
        sp.textContent = str;
        var back = sv("tspan", { dy: c[0] === "sub" ? (-size * 0.28).toFixed(1) : (size * 0.38).toFixed(1), "font-size": size }, t);
        back.textContent = "\u200b";
      }
      return t;
    };
    // 개념서 TOPIC 24 이온 색
    var ION = { "H⁺": "#F4B6BE", "Cl⁻": "#BFE0B4", "Na⁺": "#D9C8E8", "OH⁻": "#A9C6EA", "H₂O": "#FFFFFF" };
    var BTB = { "노랑": "#F7E07A", "초록": "#A8D5A0", "파랑": "#9DBDE6" };

    // 열린 비커: parts = [["H⁺", 3], ...], vol = mL
    var beakerSvg = function (parts, vol, opt) {
      opt = opt || {};
      var W = opt.wide ? 230 : 150, H = 150, x0 = 10, x1 = W - 10, top = 14, bot = H - 6;
      var cap = Math.max(20, Math.ceil(vol * 1.5 / 10) * 10);
      var svg = sv("svg", { viewBox: "0 0 " + W + " " + H, class: "pl-svg", role: "img", "aria-label": opt.label || "" });
      var level = bot - (Math.min(vol, cap) / cap) * (bot - top - 6);
      if (vol > 0) sv("rect", { x: x0, y: level, width: x1 - x0, height: bot - level, fill: opt.tint ? BTB[opt.tint] : "#EAF4FB" }, svg);
      var items = [];
      parts.forEach(function (p) { for (var n = 0; n < p[1]; n++) items.push(p[0]); });
      items = items.map(function (t, i) { return { t: t, k: hash(i * 7 + items.length) }; }).sort(function (a, b) { return a.k - b.k; });
      var ax = x0 + 6, ay = level + 6, aw = x1 - x0 - 12, ah = Math.max(10, bot - 6 - ay);
      if (items.length && vol > 0) {
        var cell = Math.min(30, Math.sqrt(aw * ah / items.length));
        var cols = Math.max(1, Math.floor(aw / cell)), rows = Math.ceil(items.length / cols);
        while (rows * cell > ah && cell > 11) { cell -= 0.5; cols = Math.max(1, Math.floor(aw / cell)); rows = Math.ceil(items.length / cols); }
        var r = Math.min(11.5, cell * 0.43);
        var offX = ax + (aw - cols * cell) / 2, offY = bot - 6 - rows * cell;
        items.forEach(function (it, i) {
          var cx = offX + (i % cols + 0.5) * cell + (hash(i + 3) - 0.5) * cell * 0.22;
          var cy = offY + (Math.floor(i / cols) + 0.5) * cell + (hash(i + 11) - 0.5) * cell * 0.22;
          var g = sv("g", { class: "pl-pt" + (opt.fade ? " pt-in" : "") }, svg);
          if (opt.fade) g.style.animationDelay = i * 10 + "ms";
          sv("circle", { cx: cx.toFixed(1), cy: cy.toFixed(1), r: r, fill: ION[it.t], class: "pl-ion" }, g);
          var fs = r * (it.t.length > 2 ? 0.74 : 0.86);
          var t = sv("text", { x: cx.toFixed(1), y: (cy + fs * 0.12).toFixed(1), class: "pl-ion-t", "text-anchor": "middle", "dominant-baseline": "central", "font-size": fs.toFixed(1) }, g);
          svgChem(t, it.t, fs);
        });
      }
      // 비커 선: 옆면·바닥, 위쪽 끝은 밖으로 살짝 벌어짐
      sv("path", { d: "M" + x0 + " " + top + " L" + x0 + " " + bot + " L" + x1 + " " + bot + " L" + x1 + " " + top, class: "pl-glass" }, svg);
      sv("path", { d: "M" + (x0 - 5) + " " + (top - 4) + " L" + x0 + " " + top + " M" + x1 + " " + top + " L" + (x1 + 5) + " " + (top - 4), class: "pl-glass" }, svg);
      return svg;
    };

    var beaker = function (label, parts, vol, opt) {
      var wrap = el("figure", "pl-fig");
      wrap.appendChild(beakerSvg(parts, vol, Object.assign({ label: label }, opt || {})));
      var cap = el("figcaption", "pl-cap");
      cap.appendChild(el("span", "pl-cap-t", label));
      var lg = el("span", "pl-legend");
      parts.forEach(function (p) {
        if (!p[1]) return;
        var c = el("span", "pl-key"); var dot = el("i"); dot.style.background = ION[p[0]];
        var nm = chem(el("span", "pl-key-t"), p[0]); nm.appendChild(document.createTextNode(" " + p[1]));   // 첨자가 흐름 안에서 올라가도록 감싼다
        c.appendChild(dot); c.appendChild(nm); lg.appendChild(c);
      });
      cap.appendChild(lg); wrap.appendChild(cap);
      return wrap;
    };
    var arrowSvg = function (dir) {                      // 개념서의 분홍 화살표
      var svg = sv("svg", { viewBox: dir === "down" ? "0 0 24 30" : "0 0 30 24", class: "pl-arrow pl-arrow-" + dir, "aria-hidden": "true" });
      if (dir === "down") { sv("line", { x1: 12, y1: 2, x2: 12, y2: 20, class: "pl-arr-l" }, svg); sv("path", { d: "M6 18 L12 28 L18 18 Z", class: "pl-arr-h" }, svg); }
      else { sv("line", { x1: 2, y1: 12, x2: 20, y2: 12, class: "pl-arr-l" }, svg); sv("path", { d: "M18 6 L28 12 L18 18 Z", class: "pl-arr-h" }, svg); }
      return svg;
    };

    var stageNeutral = function (st, box) {
      var ml = 0;
      var info = el("p", "pl-q", "묽은 염산 " + st.acid_ml + " mL (H⁺ " + st.h + "개). 수산화 나트륨 수용액은 5 mL에 OH⁻ " + st.oh + "개. 몇 mL를 넣으면 완전히 중화될까요?");
      var row = el("div", "pl-beakers");
      var acid = beaker("묽은 염산 " + st.acid_ml + "\u00a0mL", [["H⁺", st.h], ["Cl⁻", st.h]], st.acid_ml);
      var plusSign = el("span", "pl-plus", "+");
      var baseHold = el("div", "pl-base");
      var after = el("div", "pl-after");
      var ctl = el("div", "pl-step");
      var minus = el("button", "btn", "− 5 mL"), plus = el("button", "btn", "+ 5 mL"), val = el("b", "pl-ml", "0 mL");
      var go = el("button", "btn primary", "섞기");
      [minus, plus, go].forEach(function (b) { b.type = "button"; });
      var draw = function () {
        val.textContent = ml + " mL"; baseHold.textContent = "";
        var n = ml / st.unit * st.oh;
        baseHold.appendChild(beaker("수산화 나트륨 수용액 " + ml + "\u00a0mL", [["Na⁺", n], ["OH⁻", n]], ml));
        minus.disabled = ml <= 0; plus.disabled = ml >= st.max_ml; go.disabled = ml <= 0;
      };
      minus.addEventListener("click", function () { ml = Math.max(0, ml - st.unit); draw(); });
      plus.addEventListener("click", function () { ml = Math.min(st.max_ml, ml + st.unit); draw(); });
      go.addEventListener("click", function () {
        [minus, plus, go].forEach(function (b) { b.disabled = true; });
        send(ml).then(function (res) {
          var L = res.left;
          after.textContent = "";
          after.appendChild(arrowSvg("down"));
          after.appendChild(beaker("혼합 용액(" + res.state + ") · BTB " + { "노랑": "노란색", "초록": "녹색", "파랑": "푸른색" }[res.color],
            [["H⁺", L["H⁺"]], ["OH⁻", L["OH⁻"]], ["Na⁺", L["Na⁺"]], ["Cl⁻", L["Cl⁻"]], ["H₂O", res.water]],
            st.acid_ml + ml, { wide: true, tint: res.color, fade: true }));
          ctl.classList.add("is-spent");
          feedback(res, "정답 " + res.answer + " mL");
        }).catch(function (e) { [minus, plus, go].forEach(function (b) { b.disabled = false; }); alert(e.message); });
      });
      row.appendChild(acid); row.appendChild(plusSign); row.appendChild(baseHold);
      ctl.appendChild(minus); ctl.appendChild(val); ctl.appendChild(plus); ctl.appendChild(go);
      box.appendChild(info); box.appendChild(row); box.appendChild(ctl); box.appendChild(after);
      draw();
    };

    // 산화 환원: 화학식 아래에 이름, 채점 뒤 산화(빨강)·환원(주황) 꺾인 화살표
    var stageRedox = function (st, box) {
      var eq = el("div", "rx-eq"), cells = { left: [], right: [] };
      var add = function (side, item, last) {
        var c = el("div", "rx-sp"); c.appendChild(chem(el("b", "rx-f"), item[0])); c.appendChild(el("span", "rx-n", item[1]));
        eq.appendChild(c); cells[side].push(c);
        if (!last) eq.appendChild(el("span", "rx-op", "+"));
      };
      st.left.forEach(function (it, i) { add("left", it, i === st.left.length - 1); });
      eq.appendChild(el("span", "rx-op rx-to", "→"));
      st.right.forEach(function (it, i) { add("right", it, i === st.right.length - 1); });
      var fig = el("div", "rx-fig"); fig.appendChild(eq);
      box.appendChild(fig);
      // 반응식은 한 줄로: 칸보다 길면 글자 크기를 줄여 맞춘다
      var fit = function () {
        eq.style.setProperty("--k", 1);
        var room = fig.clientWidth - 12, need = eq.getBoundingClientRect().width;
        if (need > room) eq.style.setProperty("--k", Math.max(0.55, room / need).toFixed(3));
      };
      fit();
      if (document.fonts && document.fonts.ready) document.fonts.ready.then(fit);
      var ask = st.ask === "red" ? "red" : "ox";
      var line = el("div", "pl-pick"); line.appendChild(el("span", "pl-pick-k", ask === "ox" ? "산화되는 물질은?" : "환원되는 물질은?"));
      var opts = el("div", "pl-opts");
      st.left.forEach(function (o, n) {
        var b2 = el("button", "so-seg", o[1]); b2.type = "button";
        b2.addEventListener("click", function () { choose(n); });
        opts.appendChild(b2);
      });
      line.appendChild(opts); box.appendChild(line);
      var bracket = function (from, to, label, up, color) {   // 개념서 fig23_1 처럼 꺾인 선 + 화살촉
        var fr = fig.getBoundingClientRect(), a = from.getBoundingClientRect(), b = to.getBoundingClientRect();
        var ax = a.left + a.width / 2 - fr.left, bx = b.left + b.width / 2 - fr.left;
        var edge = up ? Math.min(a.top, b.top) - fr.top : Math.max(a.bottom, b.bottom) - fr.top;
        var y = up ? edge - 22 : edge + 22, y0 = up ? a.top - fr.top - 3 : a.bottom - fr.top + 3, y1 = up ? b.top - fr.top - 3 : b.bottom - fr.top + 3;
        var svg = fig.querySelector("svg.rx-over") || sv("svg", { class: "rx-over", "aria-hidden": "true" }, fig);
        svg.setAttribute("viewBox", "0 0 " + fr.width + " " + fr.height);
        sv("path", { d: "M" + ax + " " + y0 + " L" + ax + " " + y + " L" + bx + " " + y + " L" + bx + " " + y1, fill: "none", stroke: color, "stroke-width": 1.3 }, svg);
        var h = up ? "M" + (bx - 4) + " " + (y1 - 7) + " L" + bx + " " + y1 + " L" + (bx + 4) + " " + (y1 - 7) + " Z"
                   : "M" + (bx - 4) + " " + (y1 + 7) + " L" + bx + " " + y1 + " L" + (bx + 4) + " " + (y1 + 7) + " Z";
        sv("path", { d: h, fill: color }, svg);
        var t = txt(svg, (ax + bx) / 2, y, label, "rx-lab"); t.setAttribute("fill", color);
        var bb = t.getBBox(); var bg = sv("rect", { x: bb.x - 4, y: bb.y - 1, width: bb.width + 8, height: bb.height + 2, fill: "#fff" });
        svg.insertBefore(bg, t);
      };
      var done = false;
      var choose = function (n) {                         // 누르면 바로 채점
        if (done) return; done = true;
        var segs = opts.querySelectorAll(".so-seg");
        segs.forEach(function (x) { x.disabled = true; });
        segs[n].classList.add("is-on");
        send(n).then(function (res) {
          segs[res[ask]].classList.add("is-answer");
          if (n !== res[ask]) segs[n].classList.add("is-bad");
          fig.classList.add("is-open");
          bracket(cells.left[res.ox], cells.right[res.ox_to], res.ox_lab, true, "#D9604A");
          bracket(cells.left[res.red], cells.right[res.red_to], res.red_lab, false, "#E8963A");
          feedback(res, (ask === "ox" ? "산화되는 물질 " : "환원되는 물질 ") + st.left[res[ask]][1]);
        }).catch(function (e) { done = false; segs.forEach(function (x) { x.disabled = false; }); segs[n].classList.remove("is-on"); alert(e.message); });
      };
    };

    // 전자 배치 모형 (개념서 TOPIC 07): 원자핵은 하늘색, 전자 껍질은 얇은 검은 원,
    // 전자는 껍질 위에 같은 간격으로(2개면 좌우), 원자가 전자는 빨강, 빈 껍질은 회색 점선
    var R0 = 15, DR = 14;
    var atomSvg = function (z, sh, noble) {
      var n = 0; sh.forEach(function (c, k) { if (c) n = k + 1; });
      var size = R0 + DR * 4 + 6;
      var svg = sv("svg", { viewBox: (-size) + " " + (-size) + " " + size * 2 + " " + size * 2, class: "pl-svg pl-atom-svg", role: "img", "aria-label": "전자 배치 모형" });
      for (var k = 0; k < 4; k++) {
        var r = R0 + DR * (k + 1);
        sv("circle", { r: r, class: k < n ? "pl-shell" : "pl-shell is-empty" }, svg);
      }
      sv("circle", { r: R0, fill: "#BFD6EE" }, svg);
      txt(svg, 0, 0.5, z + "+", "pl-nuc-t");
      sh.forEach(function (c, k) {
        var r = R0 + DR * (k + 1), outer = k === n - 1;
        for (var j = 0; j < c; j++) {
          var a = c === 2 ? Math.PI * j : (90 + 360 * j / c) * Math.PI / 180;
          sv("circle", { cx: (r * Math.cos(a)).toFixed(2), cy: (-r * Math.sin(a)).toFixed(2), r: 3.3,
                         fill: outer && !noble ? "#D9534F" : "#231F20" }, svg);
        }
      });
      return svg;
    };

    var stageShell = function (st, box) {
      var sh = [0, 0, 0, 0];
      box.appendChild(el("p", "pl-q", st.name + " · 원자 번호 " + st.z + " · 전자 " + st.z + "개"));
      var atom = el("div", "pl-atom"), ctl = el("div", "pl-shells"), left = el("p", "small muted pl-left");
      var legend = el("p", "pl-atom-key");
      [["#D9534F", "원자가 전자"], ["#231F20", "그 밖의 전자"]].forEach(function (k) {
        var s2 = el("span"); var d = el("i"); d.style.background = k[0]; s2.appendChild(d); s2.appendChild(document.createTextNode(k[1])); legend.appendChild(s2);
      });
      var go = el("button", "btn primary", "확인"); go.type = "button";
      var draw = function (done, noble) {
        atom.textContent = "";
        atom.appendChild(atomSvg(st.z, sh, noble));
        var used = sh.reduce(function (a, b) { return a + b; }, 0);
        left.textContent = "남은 전자 " + (st.z - used) + "개";
        ctl.querySelectorAll("[data-k]").forEach(function (row) {
          var k = +row.dataset.k;
          row.querySelector("b").textContent = sh[k];
          row.querySelector(".m").disabled = done || sh[k] <= 0;
          row.querySelector(".p").disabled = done || used >= st.z || sh[k] >= 8;
        });
        go.disabled = done || used !== st.z;
      };
      ["첫 번째 껍질", "두 번째 껍질", "세 번째 껍질", "네 번째 껍질"].forEach(function (t, k) {
        var row = el("div", "pl-srow"); row.dataset.k = k;
        var m = el("button", "btn small m", "−"), p = el("button", "btn small p", "+"); m.type = p.type = "button";
        m.setAttribute("aria-label", t + " 전자 빼기"); p.setAttribute("aria-label", t + " 전자 넣기");
        m.addEventListener("click", function () { sh[k]--; draw(); }); p.addEventListener("click", function () { sh[k]++; draw(); });
        row.appendChild(el("span", "", t)); row.appendChild(m); row.appendChild(el("b", "", "0")); row.appendChild(p);
        ctl.appendChild(row);
      });
      var fig = el("div", "pl-atom-fig"); fig.appendChild(atom); fig.appendChild(legend);
      var side = el("div"); side.appendChild(ctl); side.appendChild(left);
      var wrap = el("div", "pl-shellwrap"); wrap.appendChild(fig); wrap.appendChild(side);
      box.appendChild(wrap); box.appendChild(go);
      go.addEventListener("click", function () {
        go.disabled = true; ctl.querySelectorAll("button").forEach(function (b) { b.disabled = true; });
        send(sh.slice()).then(function (res) {
          go.classList.add("is-spent");
          sh = res.shells.concat([0, 0, 0, 0]).slice(0, 4);          // 정답 배치를 그린다
          draw(true, res.shells[res.shells.length - 1] === 8);
          feedback(res, "정답 " + res.shells.join(", "));
        }).catch(function (e) { draw(); alert(e.message); });
      });
      draw();
    };

    var stage = function () {
      var st = pg.stages[pg.i], box = pq("stage");
      pq("progress").textContent = (pg.i + 1) + " / " + pg.stages.length;
      box.textContent = ""; pq("feedback").className = "mc-feedback hidden";
      ({ neutral: stageNeutral, redox: stageRedox, shell: stageShell })[kind](st, box);
    };
    var finish = function () {
      show(pl, "loading");
      post(base() + "/submit", {}).then(function (res) {
        pq("result-title").textContent = res.score + " / " + res.total + (res.score === res.total ? " 만점" : "");
        pq("result-detail").textContent = res.best != null ? "최고 " + res.best + " / " + res.total : "";
        show(pl, "result");
      }).catch(function (e) { alert(e.message); show(pl, "start"); });
    };
    pq("begin").addEventListener("click", function () {
      show(pl, "loading");
      post(pl.dataset.start, {}).then(function (res) {
        pg = { id: res.round_id, stages: res.stages, i: 0 };
        pq("score").textContent = "";
        show(pl, "play"); stage();
      }).catch(function (e) { alert(e.message); show(pl, "start"); });
    });
    pq("again").addEventListener("click", function () { show(pl, "start"); });
  }

  // ---------- 영단어 카드: 누르면 뜻, '뜻 모두 보기' ----------
  var voca = document.querySelector("[data-voca]");
  if (voca) {
    voca.addEventListener("click", function (e) {
      var c = e.target.closest(".voca-card"); if (!c) return;
      c.setAttribute("aria-pressed", c.getAttribute("aria-pressed") === "true" ? "false" : "true");
    });
    var vt = document.querySelector("[data-voca-toggle]");
    if (vt) vt.addEventListener("click", function () {
      var on = vt.getAttribute("aria-pressed") !== "true";
      vt.setAttribute("aria-pressed", on ? "true" : "false"); vt.textContent = on ? "뜻 모두 가리기" : "뜻 모두 보기";
      voca.querySelectorAll(".voca-card").forEach(function (c) { c.setAttribute("aria-pressed", on ? "true" : "false"); });
    });
  }
})();
