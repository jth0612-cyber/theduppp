// 내 공부: 직접 재는 타이머의 숫자를 1초마다 올린다. 기록되는 시간은 서버가 잰 값이다.
(function () {
  "use strict";
  var el = document.querySelector("[data-timer-run]");
  if (!el) return;
  var t0 = Date.now() - (parseInt(el.dataset.timerRun, 10) || 0) * 1000, max = parseInt(el.dataset.max, 10) || 0;
  var p = function (n) { return (n < 10 ? "0" : "") + n; };
  function tick() {
    var s = Math.floor((Date.now() - t0) / 1000); if (max) s = Math.min(max, s);
    el.textContent = p(Math.floor(s / 3600)) + ":" + p(Math.floor(s / 60) % 60) + ":" + p(s % 60);
  }
  tick(); setInterval(tick, 1000);
})();
