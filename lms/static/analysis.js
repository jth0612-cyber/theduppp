// 모의고사 분석: 빠른 입력칸 다섯 자리씩 띄우기, 코드 입력 네 자리씩 띄우기, 회차 선택 자동 이동.
// 채점은 서버에서만 한다. (CSP: 인라인 스크립트 금지라 이 파일로만 동작)
(function () {
  "use strict";
  var quick = document.querySelector("[data-quick]");
  if (quick) {
    var n = parseInt(quick.getAttribute("data-n"), 10) || 20;
    quick.addEventListener("input", function () {
      var d = quick.value.replace(/[^1-5]/g, "").slice(0, n);
      quick.value = d.replace(/(\d{5})(?=\d)/g, "$1 ");
      // 빠른 입력 내용을 답안지 동그라미에도 바로 표시
      for (var i = 0; i < n; i++) {
        var r = document.querySelector('input[name="a' + (i + 1) + '"][value="' + d[i] + '"]');
        if (r) r.checked = true;
      }
    });
  }
  var key = document.getElementById("answer_key");
  if (key) {
    key.addEventListener("input", function () {
      key.value = key.value.replace(/[^1-5]/g, "").replace(/(\d{5})(?=\d)/g, "$1 ");
    });
  }
  var code = document.querySelector("[data-code-input]");
  if (code) {
    code.addEventListener("input", function () {
      var raw = code.value.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 12);
      code.value = raw.replace(/(.{4})(?=.)/g, "$1 ");
    });
  }
  var pick = document.querySelector("[data-autosubmit]");
  if (pick) {
    var btn = pick.querySelector(".js-hide");
    if (btn) btn.hidden = true;
    pick.querySelector("select").addEventListener("change", function () { pick.submit(); });
  }
})();
