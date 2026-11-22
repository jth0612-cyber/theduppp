// 카카오톡·네이버 등 앱 안 브라우저로 열렸을 때 기본 브라우저로 넘긴다.
// 앱 안 브라우저에서는 홈 화면 설치 및 알림이 안 되고, Google 로그인도 막힌다.
(function () {
  var ua = navigator.userAgent || "";
  var here = location.href;

  // 카카오톡·라인은 바깥 브라우저로 여는 주소가 있어 바로 넘긴다
  if (/KAKAOTALK/i.test(ua)) {
    location.href = "kakaotalk://web/openExternal?url=" + encodeURIComponent(here);
    return;
  }
  if (/\bLine\//.test(ua)) {
    if (!/[?&]openExternalBrowser=1/.test(here)) {
      location.href = here + (here.indexOf("?") < 0 ? "?" : "&") + "openExternalBrowser=1";
    }
    return;
  }
  // ponytail: 알려진 앱 목록만 잡는다. 새 앱이 생기면 여기에 이름을 추가
  if (!/NAVER\(inapp|Instagram|FBAN|FBAV|DaumApps|everytimeApp|BAND\//i.test(ua)) return;

  var android = /Android/i.test(ua);
  document.addEventListener("DOMContentLoaded", function () {
    var box = document.createElement("div");
    box.className = "flash inapp";
    box.setAttribute("role", "status");
    var msg = document.createElement("p");
    msg.textContent = android
      ? "앱 안 브라우저에서는 홈 화면 설치 및 알림이 되지 않습니다."
      : "앱 안 브라우저에서는 홈 화면 설치 및 알림이 되지 않습니다. 주소를 복사해 Safari에서 여세요.";
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn small";
    btn.textContent = android ? "Chrome으로 열기" : "주소 복사";
    btn.addEventListener("click", function () {
      if (android) {
        location.href = "intent://" + here.replace(/^https?:\/\//, "") +
          "#Intent;scheme=" + location.protocol.replace(":", "") + ";package=com.android.chrome;end";
        return;
      }
      var done = function () { btn.textContent = "복사됨"; };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(here).then(done, fallback);
      } else {
        fallback();
      }
      function fallback() {
        var t = document.createElement("textarea");
        t.value = here;
        document.body.appendChild(t);
        t.select();
        try { document.execCommand("copy"); done(); } catch (e) { window.prompt("주소", here); }
        document.body.removeChild(t);
      }
    });
    box.appendChild(msg);
    box.appendChild(btn);
    document.body.insertBefore(box, document.body.firstChild);
  });
})();
