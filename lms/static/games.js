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
      if (r.status === 410) throw new Error("시간이 너무 지났어요. 다시 시작해 주세요.");
      if (r.status === 401 || r.redirected) throw new Error("로그인이 만료됐어요. 새로고침해 주세요.");
      if (!r.ok) throw new Error("문제가 생겼어요. 잠시 후 다시 시도해 주세요.");
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
      t.appendChild(el("span", "end", "5'"));
      a.appendChild(el("span", "end", "3'"));
      for (var i = 0; i < state.strand.length; i++) {
        t.appendChild(el("span", "cell base-" + state.strand[i], state.strand[i]));
        var b = state.input[i] || "";
        var cell = el("span", "cell" + (b ? " base-" + b : "") + (i === state.input.length ? " cursor" : ""), b || "·");
        if (state.results) cell.classList.add(state.results[i] ? "ok" : "wrong");
        a.appendChild(cell);
      }
      t.appendChild(el("span", "end", "3'"));
      a.appendChild(el("span", "end", "5'"));
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
            (res.correct === res.total ? "모두 맞혔어요" : res.correct + " / " + res.total + " 맞았어요");
          q("result-detail").textContent = "걸린 시간 " + res.elapsed + "초" +
            (res.correct < res.total ? " (정답: 3'-" + res.answer + "-5')" : "");
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
        post(dna.dataset.start, { level: Number(btn.dataset.level) }).then(function (res) {
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
      if ("ATGC".indexOf(k) >= 0 && k.length === 1) press(k);
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
      var item = game.questions[game.i];
      m("progress").textContent = (game.i + 1) + " / " + game.questions.length;
      m("score").textContent = game.i ? "맞힌 문제 " + game.score : "";
      m("question").textContent = item.question;
      var box = m("choices"), fb = m("feedback");
      box.textContent = ""; fb.textContent = ""; fb.className = "mc-feedback hidden";
      var buttons = [];
      item.choices.forEach(function (c, idx) {
        var b = el("button", "btn mc-choice", (idx + 1) + ". " + c);
        b.type = "button";
        b.addEventListener("click", function () { check(idx, buttons); });
        buttons.push(b); box.appendChild(b);
      });
      if (buttons[0]) buttons[0].focus({ preventScroll: true });
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
          var fb = m("feedback");
          fb.className = "mc-feedback " + (res.correct ? "ok" : "wrong");
          fb.textContent = "";
          fb.appendChild(el("b", "", res.correct ? "정답이에요" : "아쉬워요. 정답은 " + (res.answer_index + 1) + "번"));
          if (res.explanation) fb.appendChild(el("p", "", res.explanation));
          var last = game.i + 1 >= game.questions.length;
          var next = el("button", "btn primary", last ? "결과 보기" : "다음 문제");
          next.type = "button";
          next.addEventListener("click", function () {
            game.i += 1;
            if (game.i < game.questions.length) renderQuestion(); else submit();
          });
          fb.appendChild(next);
          m("score").textContent = "맞힌 문제 " + res.score;
          next.focus({ preventScroll: true });
          fb.scrollIntoView({ behavior: "smooth", block: "nearest" });
        })
        .catch(function (e) {
          buttons.forEach(function (b) { b.disabled = false; b.classList.remove("is-picked"); });
          alert(e.message);
        })
        .then(function () { game.busy = false; });
    };

    var submit = function () {
      show(mc, "loading");
      post(mc.dataset.start.replace(/\/start$/, "/" + game.id + "/submit"), { answers: game.answers })
        .then(function (res) {
          m("result-title").textContent = res.score + " / " + res.total + (res.score === res.total ? " 만점" : " 맞았어요");
          m("result-detail").textContent = res.score === res.total ? "모두 맞혔어요." : "아래 해설로 틀린 문제를 다시 확인해 보세요.";
          var review = m("review");
          review.textContent = "";
          res.results.forEach(function (r, i) {
            var item = game.questions[i];
            var box = el("div", "review-item " + (r.correct ? "ok" : "wrong"));
            box.appendChild(el("b", "", (r.correct ? "맞음 · " : "틀림 · ") + (i + 1) + ". " + item.question));
            var mine = r.pick >= 0 ? item.choices[r.pick] : "(선택 안 함)";
            if (!r.correct) box.appendChild(el("div", "small", "내 답: " + mine));
            box.appendChild(el("div", "small", "정답: " + item.choices[r.answer_index]));
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
