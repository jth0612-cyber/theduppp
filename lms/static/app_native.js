// 앱(Capacitor) 안에서만: 주요 버튼·탭·홈 아이콘을 누르면 짧은 진동. 플러그인: @capacitor/haptics
(function () {
  var H = window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.Haptics;
  if (!H) return;
  document.addEventListener("pointerdown", function (e) {
    if (e.target.closest(".btn.primary, .m-tabs a, .tabs a, .ah-apps a, .ah-stats a, .ah-card, .ah-now"))
      H.impact({ style: "LIGHT" }).catch(function () {});
  }, { passive: true });
})();
