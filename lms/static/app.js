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
