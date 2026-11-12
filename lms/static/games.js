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
        c.addEventListener("click", function () { if (seq.indexOf(k) < 0) { seq.push(k); draw(); } });
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
          var ch = typed[k] ? typed[k].c : (k === 0 && !typed.length ? item.hint : "");
          slots.appendChild(el("span", "sp-slot" + (typed[k] ? " is-on" : k === 0 && !typed.length ? " is-hint" : ""), ch || "\u00a0"));
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

    m("begin").addEventListener("click", function () {
      var topic = m("topic");
      show(mc, "loading");
      post(mc.dataset.start, topic ? { topic: topic.value } : {})
        .then(function (res) {
          game = { id: res.round_id, questions: res.questions, answers: [], i: 0, score: 0, busy: false };
          show(mc, "play");
          renderQuestion();
        })
        .catch(function (e) { alert(e.message); show(mc, "start"); });
    });
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
      var set = st.sets[st.k], L = mq("left"), R = mq("right");
      L.textContent = ""; R.textContent = ""; st.sel = null; st.left = set.length;
      mq("progress").textContent = (st.k + 1) + " / " + st.sets.length + "판";
      shuffle(set).forEach(function (p) {
        var b = el("button", "mt-item", p.w); b.type = "button"; b.dataset.w = p.w; b.setAttribute("lang", "en");
        b.addEventListener("click", function () { choose(b, "w"); }); L.appendChild(b);
      });
      shuffle(set).forEach(function (p) {
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

  // ---------- 카드 뒤집기: 단어 카드와 뜻 카드 짝 찾기 ----------
  var mm = document.getElementById("memory-game");
  if (mm) {
    var mmq = function (r) { return mm.querySelector("[data-role=" + r + "]"); };
    var mg = null, mclk = null;
    var mmDone = function () {
      clearInterval(mclk); var secs = (Date.now() - mg.t0) / 1000;
      show(mm, "loading");
      post(mm.dataset.start.replace(/\/start$/, "/" + mg.id + "/submit"), { tries: mg.tries, seconds: secs })
        .then(function (res) {
          mmq("result-title").textContent = res.tries + "번 만에 " + res.pairs + "쌍";
          mmq("result-detail").textContent = secs.toFixed(1) + "초" + (res.tries === res.pairs ? " · 한 번도 안 틀림" : "");
          var ul = mmq("words"); ul.textContent = "";
          res.words.forEach(function (p) { var li = el("li"); var b = el("b", "", p[0]); b.setAttribute("lang", "en"); li.appendChild(b); li.appendChild(el("span", "", p[1])); ul.appendChild(li); });
          show(mm, "result");
        }).catch(function (e) { alert(e.message); show(mm, "start"); });
    };
    var flip = function (b) {
      if (mg.lock || b.classList.contains("is-up")) return;
      b.classList.add("is-up"); b.setAttribute("aria-pressed", "true");
      mg.open.push(b);
      if (mg.open.length < 2) return;
      mg.tries++;
      mmq("progress").textContent = mg.found + " / " + mg.pairs + "쌍 · " + mg.tries + "번";
      var a = mg.open[0], c = mg.open[1]; mg.open = [];
      if (a.dataset.k === c.dataset.k && a.dataset.en !== c.dataset.en) {
        mg.found++;
        [a, c].forEach(function (x) { x.classList.add("is-match"); x.disabled = true; });
        mmq("progress").textContent = mg.found + " / " + mg.pairs + "쌍 · " + mg.tries + "번";
        if (mg.found === mg.pairs) setTimeout(mmDone, 450);
      } else {
        mg.lock = true;
        setTimeout(function () { [a, c].forEach(function (x) { x.classList.remove("is-up"); x.setAttribute("aria-pressed", "false"); }); mg.lock = false; }, 750);
      }
    };
    mmq("begin").addEventListener("click", function () {
      show(mm, "loading");
      post(mm.dataset.start, {}).then(function (res) {
        mg = { id: res.round_id, pairs: res.cards.length / 2, found: 0, tries: 0, open: [], lock: false, t0: Date.now() };
        var bd = mmq("board"); bd.textContent = "";
        res.cards.forEach(function (c, n) {
          var b = el("button", "mm-card" + (c.en ? " is-en" : "")); b.type = "button";
          b.dataset.k = c.k; b.dataset.en = c.en ? "1" : "0"; b.setAttribute("aria-pressed", "false");
          b.setAttribute("aria-label", (n + 1) + "번 카드");
          var face = el("span", "mm-face", c.t); if (c.en) face.setAttribute("lang", "en");
          b.appendChild(el("span", "mm-back")); b.appendChild(face);
          b.addEventListener("click", function () { flip(b); });
          bd.appendChild(b);
        });
        mmq("progress").textContent = "0 / " + mg.pairs + "쌍";
        show(mm, "play");
        mclk = setInterval(function () { mmq("clock").textContent = ((Date.now() - mg.t0) / 1000).toFixed(1) + "초"; }, 100);
      }).catch(function (e) { alert(e.message); show(mm, "start"); });
    });
    mmq("again").addEventListener("click", function () { show(mm, "start"); });
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

    // 이온 입자 그리기: [["H⁺", 3, "ion-h"], ...]
    var beaker = function (label, parts, tint) {
      var bx = el("div", "pl-beaker" + (tint ? " tint-" + tint : ""));
      var dots = el("div", "pl-dots");
      parts.forEach(function (p) { for (var n = 0; n < p[1]; n++) dots.appendChild(el("span", "pl-ion " + p[2], p[0])); });
      bx.appendChild(dots); bx.appendChild(el("span", "pl-label", label));
      return bx;
    };

    var stageNeutral = function (st, box) {
      var ml = 0;
      var info = el("p", "pl-q", "묽은 염산 " + st.acid_ml + " mL (H⁺ " + st.h + "개). 수산화 나트륨 수용액은 5 mL에 OH⁻ " + st.oh + "개. 몇 mL를 넣으면 완전히 중화될까요?");
      var row = el("div", "pl-beakers");
      var acid = beaker("염산 " + st.acid_ml + " mL", [["H⁺", st.h, "ion-h"], ["Cl⁻", st.h, "ion-cl"]]);
      var baseHold = el("div");
      var ctl = el("div", "pl-step");
      var minus = el("button", "btn", "− 5 mL"), plus = el("button", "btn", "+ 5 mL"), val = el("b", "pl-ml", "0 mL");
      var go = el("button", "btn primary", "섞기");
      [minus, plus, go].forEach(function (b) { b.type = "button"; });
      var draw = function () {
        val.textContent = ml + " mL"; baseHold.textContent = "";
        var n = ml / st.unit * st.oh;
        baseHold.appendChild(beaker("NaOH " + ml + " mL", [["Na⁺", n, "ion-na"], ["OH⁻", n, "ion-oh"]]));
        minus.disabled = ml <= 0; plus.disabled = ml >= st.max_ml;
      };
      minus.addEventListener("click", function () { ml = Math.max(0, ml - st.unit); draw(); });
      plus.addEventListener("click", function () { ml = Math.min(st.max_ml, ml + st.unit); draw(); });
      go.addEventListener("click", function () {
        [minus, plus, go].forEach(function (b) { b.disabled = true; });
        send(ml).then(function (res) {
          row.textContent = "";
          var L = res.left;
          row.appendChild(beaker("섞은 뒤 · " + res.state + " · BTB " + res.color, [["H⁺", L["H⁺"], "ion-h"], ["OH⁻", L["OH⁻"], "ion-oh"],
            ["Na⁺", L["Na⁺"], "ion-na"], ["Cl⁻", L["Cl⁻"], "ion-cl"], ["H₂O", res.water, "ion-w"]], res.color));
          ctl.classList.add("is-spent");
          feedback(res, "정답 " + res.answer + " mL");
        }).catch(function (e) { [minus, plus, go].forEach(function (b) { b.disabled = false; }); alert(e.message); });
      });
      row.appendChild(acid); row.appendChild(baseHold);
      ctl.appendChild(minus); ctl.appendChild(val); ctl.appendChild(plus); ctl.appendChild(go);
      box.appendChild(info); box.appendChild(row); box.appendChild(ctl);
      draw();
    };

    var stageRedox = function (st, box) {
      var pick = { ox: null, red: null };
      box.appendChild(el("p", "pl-eq", st.eq));
      var rows = {}, go = el("button", "btn primary", "확인"); go.type = "button"; go.disabled = true;
      [["ox", "산화되는 물질"], ["red", "환원되는 물질"]].forEach(function (r) {
        var line = el("div", "pl-pick"); line.appendChild(el("span", "pl-pick-k", r[1]));
        var opts = el("div", "pl-opts");
        st.opts.forEach(function (o, n) {
          var b = el("button", "so-seg", o); b.type = "button";
          b.addEventListener("click", function () {
            pick[r[0]] = n;
            opts.querySelectorAll(".so-seg").forEach(function (x, k) { x.classList.toggle("is-on", k === n); });
            go.disabled = pick.ox === null || pick.red === null;
          });
          opts.appendChild(b);
        });
        line.appendChild(opts); rows[r[0]] = opts; box.appendChild(line);
      });
      box.appendChild(go);
      go.addEventListener("click", function () {
        go.disabled = true; box.querySelectorAll(".so-seg").forEach(function (b) { b.disabled = true; });
        send(pick).then(function (res) {
          ["ox", "red"].forEach(function (k) {
            var segs = rows[k].querySelectorAll(".so-seg");
            segs[res[k]].classList.add("is-answer");
            if (pick[k] !== res[k]) segs[pick[k]].classList.add("is-bad");
          });
          go.classList.add("is-spent");
          feedback(res, "산화 " + st.opts[res.ox] + " · 환원 " + st.opts[res.red]);
        }).catch(function (e) { go.disabled = false; alert(e.message); });
      });
    };

    var stageShell = function (st, box) {
      var sh = [0, 0, 0, 0];
      box.appendChild(el("p", "pl-q", st.name + " · 원자 번호 " + st.z + " · 전자 " + st.z + "개"));
      var atom = el("div", "pl-atom"), ctl = el("div", "pl-shells"), left = el("p", "small muted");
      var go = el("button", "btn primary", "확인"); go.type = "button";
      var draw = function () {
        atom.textContent = "";
        atom.appendChild(el("span", "pl-nuc", "+" + st.z));
        for (var k = 0; k < 4; k++) {
          var ring = el("span", "pl-ring r" + k);
          for (var e = 0; e < sh[k]; e++) {
            var d = el("i", "pl-e"); var a = (e / Math.max(sh[k], 1)) * 2 * Math.PI - Math.PI / 2;
            d.style.left = (50 + 50 * Math.cos(a)) + "%"; d.style.top = (50 + 50 * Math.sin(a)) + "%";
            ring.appendChild(d);
          }
          atom.appendChild(ring);
        }
        var used = sh.reduce(function (a, b) { return a + b; }, 0);
        left.textContent = "남은 전자 " + (st.z - used) + "개";
        ctl.querySelectorAll("[data-k]").forEach(function (row) {
          var k = +row.dataset.k;
          row.querySelector("b").textContent = sh[k];
          row.querySelector(".m").disabled = sh[k] <= 0;
          row.querySelector(".p").disabled = used >= st.z || sh[k] >= 8;
        });
        go.disabled = used !== st.z;
      };
      ["첫째 껍질", "둘째 껍질", "셋째 껍질", "넷째 껍질"].forEach(function (t, k) {
        var row = el("div", "pl-srow"); row.dataset.k = k;
        var m = el("button", "btn small m", "−"), p = el("button", "btn small p", "+"); m.type = p.type = "button";
        m.addEventListener("click", function () { sh[k]--; draw(); }); p.addEventListener("click", function () { sh[k]++; draw(); });
        row.appendChild(el("span", "", t)); row.appendChild(m); row.appendChild(el("b", "", "0")); row.appendChild(p);
        ctl.appendChild(row);
      });
      var wrap = el("div", "pl-shellwrap"); wrap.appendChild(atom); wrap.appendChild(ctl);
      box.appendChild(wrap); box.appendChild(left); box.appendChild(go);
      go.addEventListener("click", function () {
        go.disabled = true; ctl.querySelectorAll("button").forEach(function (b) { b.disabled = true; });
        send(sh.slice()).then(function (res) { go.classList.add("is-spent"); feedback(res, "정답 " + res.shells.join(", ")); })
          .catch(function (e) { draw(); alert(e.message); });
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
