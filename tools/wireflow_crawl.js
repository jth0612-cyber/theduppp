// 역할별 와이어플로 캡처 (Playwright MCP browser_run_code_unsafe). 로그인 뒤 본문·메뉴 링크를 따라가며 모든 화면을 찍고
// 링크·버튼 위치를 wireflow/roles3/boxes.json 에 남긴다. 같은 꼴의 주소(/t/students/3, /t/students/5)는 한 장만.
// 비밀번호는 저장소에 넣지 않는다: 실행할 때 __*_PW__ 를 DEMO_CREDENTIALS.txt 값으로 바꾼 사본을 쓴다.
async (page) => {
  const B = "http://127.0.0.1:5077";
  const OUT = "C:/Users/jsmd9/OneDrive/Desktop/TH/management/wireflow/roles3/";
  const ROLES = {
    student: ["__STUDENT_ID__", "__STUDENT_PW__", "/s/"],
    assistant: ["ta_hanjisu", "__TA_PW__", "/t/questions"],
    teacher: ["master", "__TEACHER_PW__", "/t/"],
  };
  const KEEPQ = ["kind", "tab", "view", "type", "status"];
  const SKIP = /logout|delete|remove|download|export|\.xlsx|\.pdf|\.csv|\/static\/|\/uploads?\/|\/media\/|\/files?\/|\/photo|\/img\/|\/sms|print=|\/api\//i;
  const key = (u) => {
    const url = new URL(u, B);
    const p = url.pathname.replace(/\/\d+(?=\/|$)/g, "/{id}");
    const q = KEEPQ.filter(k => url.searchParams.has(k)).map(k => k + "=" + url.searchParams.get(k)).join("&");
    return p + (q ? "?" + q : "");
  };
  const clean = (u) => {
    const url = new URL(u, B);
    const q = KEEPQ.filter(k => url.searchParams.has(k)).map(k => k + "=" + url.searchParams.get(k)).join("&");
    return url.pathname + (q ? "?" + q : "");
  };
  const all = {};
  const br = page.context().browser();
  for (const [role, [id, pw, start]] of Object.entries(ROLES)) {
    const ctx = await br.newContext({serviceWorkers: "block", viewport: {width: 1280, height: 800}, deviceScaleFactor: 2});   // 2배율: 작동 흐름 카드가 또렷하게
    const pg = await ctx.newPage();
    await pg.goto(B + "/login");
    await pg.fill("input[name=username]", id); await pg.fill("input[name=password]", pw);
    await Promise.all([pg.waitForURL(/\/(t|s)\//), pg.locator("button[type=submit]").first().click()]);
    const pages = {}, seen = new Set(), queue = [start];
    seen.add(key(start));
    let n = 0;
    while (queue.length && n < 90) {
      const path = queue.shift();
      const r = await pg.goto(B + path).catch(() => null);
      if (!r || r.status() >= 400 || !pg.url().startsWith(B)) continue;
      if (clean(pg.url()) !== path && key(pg.url()) !== key(path)) continue;   // 다른 곳으로 넘어가면 건너뜀
      await pg.waitForLoadState("networkidle").catch(() => {});
      await pg.waitForTimeout(250);
      n++;
      const name = role + "_" + String(n).padStart(2, "0");
      const info = await pg.evaluate(() => {
        const W = document.documentElement.scrollWidth, H = Math.min(document.documentElement.scrollHeight, 3200);
        const pct = (r) => [r.left / W * 100, (r.top + scrollY) / H * 100, r.width / W * 100, r.height / H * 100].map(v => +v.toFixed(2));
        const vis = (el) => { const r = el.getBoundingClientRect(); return r.width > 2 && r.height > 2 && (r.top + scrollY) < H
          && getComputedStyle(el).visibility !== "hidden"; };
        const txt = (el) => (el.innerText || el.value || el.getAttribute("aria-label") || el.title || "").replace(/\s+/g, " ").trim().slice(0, 40);
        const links = [...document.querySelectorAll("a[href]")].filter(vis).map(a => ({
          href: a.getAttribute("href"), text: txt(a), nav: !!a.closest(".nav, nav, aside, .sidebar"), box: pct(a.getBoundingClientRect())}));
        const forms = [...document.querySelectorAll("form button[type=submit], form button:not([type]), form input[type=submit]")].filter(vis).map(b => ({
          action: b.form.getAttribute("action") || location.pathname, method: (b.form.method || "get").toLowerCase(), text: txt(b),
          box: pct(b.getBoundingClientRect())}));
        const h1 = document.querySelector("h1"); return {W, H, title: document.title, h1: h1 ? h1.innerText.trim() : "", links, forms};
      });
      await pg.screenshot({path: OUT + name + ".jpg", type: "jpeg", quality: 82, fullPage: true,
        clip: {x: 0, y: 0, width: info.W, height: info.H}});
      pages[path] = {name, ...info};
      for (const l of info.links) {
        if (!l.href || l.href.startsWith("#") || /^(mailto|tel|javascript):/.test(l.href)) continue;
        const u = new URL(l.href, B + path);
        if (u.origin !== B || SKIP.test(u.pathname + u.search)) continue;
        const k = key(u.href);
        if (seen.has(k)) continue;
        seen.add(k); queue.push(clean(u.href));
      }
    }
    all[role] = pages;
    await ctx.close();
  }
  await page.context().request.post("http://127.0.0.1:5099/", {data: JSON.stringify(all)});   // 받는 쪽: tools/wireflow_recv.py
  return JSON.stringify(Object.fromEntries(Object.entries(all).map(([r, p]) => [r, Object.keys(p).length])));
}
