// 화면이 그려지기 전에 저장된 밝기 설정을 적용한다(깜빡임 방지). 자동이면 기기 설정을 따른다.
(function () {
  try {
    var t = localStorage.getItem("theme");
    if (t === "dark" || t === "light") document.documentElement.setAttribute("data-theme", t);
  } catch (_) {}
})();
