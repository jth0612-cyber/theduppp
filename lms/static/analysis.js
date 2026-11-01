// 분석실: 답안 입력칸(1~5만, 다섯 개씩 띄어쓰기, 칸 표시), 교재 코드 입력 형식, 시험 선택 자동 이동.
// 채점은 서버에서만 한다. 이 파일은 입력 모양만 다룬다. (CSP: 인라인 스크립트 금지)
(function () {
  "use strict";
  function groupDigits(digits) {
    return digits.replace(/(\d{5})(?=\d)/g, "$1 ");
  }

  var form = document.querySelector("[data-answer-form]");
  if (form) {
    var n = parseInt(form.getAttribute("data-n"), 10) || 20;
    var input = form.querySelector(".answer-input");
    var count = form.querySelector("[data-count]");
    var cells = form.querySelectorAll("[data-cell]");
    var render = function () {
      var digits = input.value.replace(/[^1-5]/g, "").slice(0, n);
      var caret = input.selectionStart === input.value.length;
      input.value = groupDigits(digits);
      if (caret) input.setSelectionRange(input.value.length, input.value.length);
      if (count) count.textContent = digits.length;
      for (var i = 0; i < cells.length; i++) {
        cells[i].textContent = i < digits.length ? digits[i] : "·";
        cells[i].parentNode.classList.toggle("filled", i < digits.length);
      }
    };
    input.addEventListener("input", render);
    render();
  }

  var key = document.getElementById("answer_key");
  if (key) {
    key.addEventListener("input", function () {
      var d = key.value.replace(/[^1-5]/g, "");
      key.value = groupDigits(d);
    });
  }

  var code = document.querySelector("[data-code-input]");
  if (code) {
    code.addEventListener("input", function () {
      var raw = code.value.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 12);
      code.value = raw.replace(/(.{4})(?=.)/g, "$1-");
    });
  }

  var pick = document.querySelector("[data-autosubmit]");
  if (pick) {
    var sel = pick.querySelector("select");
    var btn = pick.querySelector(".js-hide");
    if (btn) btn.hidden = true;
    sel.addEventListener("change", function () { pick.submit(); });
  }
})();
