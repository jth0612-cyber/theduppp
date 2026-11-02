// 정태혁 통합과학 lab 서비스 워커: 정적 파일만 저장하고, 로그인 후 화면(개인 정보)은 저장하지 않는다.
const CACHE = "lab-static-v2";
const PRECACHE = ["/static/style.css", "/static/app.js", "/static/theme.js", "/static/offline.html",
  "/static/fonts/NotoSansKR-var.woff2", "/static/icons/icon-192.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;
  if (req.mode === "navigate") {
    // 화면은 항상 서버에서 받고, 끊겼을 때만 안내 화면
    e.respondWith(fetch(req).catch(() => caches.match("/static/offline.html")));
    return;
  }
  if (url.pathname.startsWith("/static/")) {
    // 업데이트가 바로 보이도록 항상 서버에서 먼저 받고, 끊겼을 때만 저장본을 쓴다
    e.respondWith(fetch(req).then((res) => {
      if (res.ok && res.status === 200) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); }
      return res;
    }).catch(() => caches.match(req)));
  }
});

self.addEventListener("push", (e) => {
  let data = {};
  try { data = e.data ? e.data.json() : {}; } catch (_) { data = { title: "새 소식", body: e.data ? e.data.text() : "" }; }
  e.waitUntil(self.registration.showNotification(data.title || "정태혁 통합과학 lab", {
    body: data.body || "", icon: "/static/icons/icon-192.png", badge: "/static/icons/icon-192.png",
    data: { url: data.url || "/" }, lang: "ko",
  }));
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const target = new URL((e.notification.data && e.notification.data.url) || "/", location.origin).href;
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((list) => {
    for (const c of list) { if (c.url === target && "focus" in c) return c.focus(); }
    return self.clients.openWindow(target);
  }));
});
