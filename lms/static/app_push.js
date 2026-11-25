// 앱(Capacitor) 안에서만: 로그인한 사용자 기기의 푸시 토큰을 서버에 등록하고, 알림을 누르면 그 화면으로 연다.
// 플러그인: @capacitor-firebase/messaging (app/package.json). 서버: /push/app-token, lms/fcm.py
(function () {
  var cap = window.Capacitor;
  var FM = cap && cap.Plugins && cap.Plugins.FirebaseMessaging;
  if (!FM || !document.body.classList.contains("has-shell")) return;
  var csrf = (document.querySelector('meta[name="csrf-token"]') || {}).content || "";
  function post(url, body) {
    return fetch(url, { method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf }, body: JSON.stringify(body) });
  }
  function send(token) {
    if (!token) return;
    try { if (localStorage.getItem("appPushToken") === token && sessionStorage.getItem("appPushSent")) return; } catch (e) {}
    post("/push/app-token", { token: token, platform: cap.getPlatform() }).then(function (r) {
      if (!r.ok) return;
      try { localStorage.setItem("appPushToken", token); sessionStorage.setItem("appPushSent", "1"); } catch (e) {}
    });
  }
  FM.addListener("tokenReceived", function (ev) { send(ev.token); });
  FM.addListener("notificationActionPerformed", function (ev) {
    var url = ev && ev.notification && ev.notification.data && ev.notification.data.url;
    if (url && url.charAt(0) === "/") location.href = url;
  });
  if (cap.getPlatform() === "android" && FM.createChannel) {
    FM.createChannel({ id: "default", name: "알림", importance: 4 }).catch(function () {});
  }
  FM.requestPermissions().then(function (p) {
    if (p.receive !== "granted") return;
    return FM.getToken().then(function (r) { send(r.token); });
  }).catch(function () {});              // Firebase 설정 파일이 없는 빌드에서는 조용히 넘어간다
  // 로그아웃하면 이 기기 토큰을 지운다 (같은 기기를 다른 사람이 쓸 때 남의 알림이 오지 않게)
  document.addEventListener("submit", function (e) {
    var f = e.target;
    if (!f.action || !/\/logout$/.test(f.action)) return;
    var t = null;
    try { t = localStorage.getItem("appPushToken"); } catch (err) {}
    if (!t) return;
    e.preventDefault();
    post("/push/app-token/delete", { token: t }).finally(function () {
      try { localStorage.removeItem("appPushToken"); sessionStorage.removeItem("appPushSent"); } catch (err) {}
      f.submit();
    });
  }, true);
})();
