// 설명 버튼(원 안 물음표)을 화면마다 눌러 설명 창이 열린 모습을 찍는다 (Playwright MCP browser_run_code_unsafe).
// wireflow_crawl.js 가 남긴 boxes.json 의 주소를 돌고, 결과(제목, 설명 글, 화면 주소)는 wireflow/roles3/help.json 에 남긴다.
// 비밀번호는 저장소에 넣지 않는다: 실행할 때 __*_PW__ 를 DEMO_CREDENTIALS.txt 값으로 바꾼 사본을 쓴다 (tools/wireflow_capture.py make).
async (page) => {
  const B = "http://127.0.0.1:5077";
  const OUT = "__OUT__";
  const ROLES = { student: ["__STUDENT_ID__", "__STUDENT_PW__", __STUDENT_PATHS__], teacher: ["master", "__TEACHER_PW__", __TEACHER_PATHS__] };
  const all = {};
  const br = page.context().browser();
  for (const [role, [id, pw, paths]] of Object.entries(ROLES)) {
    const ctx = await br.newContext({serviceWorkers: "block", viewport: {width: 1280, height: 800}, deviceScaleFactor: 2, reducedMotion: "reduce"});
    const pg = await ctx.newPage();
    await pg.goto(B + "/login");
    await pg.fill("input[name=username]", id); await pg.fill("input[name=password]", pw);
    await Promise.all([pg.waitForURL(/\/(t|s)\//), pg.locator("button[type=submit]").first().click()]);
    const out = [], seen = new Set();
    for (const path of paths) {
      const r = await pg.goto(B + path, {waitUntil: "domcontentloaded"}).catch(() => null);
      if (!r || r.status() >= 400) continue;
      await pg.waitForTimeout(200);
      const n = await pg.locator("[data-help]").count();
      for (let i = 0; i < n; i++) {
        const btn = pg.locator("[data-help]").nth(i);
        if (!(await btn.isVisible().catch(() => false))) continue;      // 접힌 칸 안의 버튼은 건너뛴다
        const title = await btn.evaluate(b => (b.nextElementSibling && b.nextElementSibling.getAttribute("data-help-title")) || "");
        if (!title || seen.has(title)) continue;
        seen.add(title);
        await btn.scrollIntoViewIfNeeded(); await btn.click();
        await pg.waitForSelector("dialog.help-dlg[open]", {timeout: 3000}).catch(() => {});
        await pg.waitForTimeout(350);
        const text = await pg.evaluate(() => { const d = document.querySelector("dialog.help-dlg .help-body"); return d ? d.innerText.replace(/\s+/g, " ").trim() : ""; });
        const name = role + "_help_" + String(out.length + 1).padStart(2, "0");
        await pg.screenshot({path: OUT + name + ".jpg", type: "jpeg", quality: 82});
        out.push({name, path, title, text});
        await pg.keyboard.press("Escape"); await pg.waitForTimeout(150);
      }
    }
    all[role] = out;
    await ctx.close();
  }
  await page.context().request.post("http://127.0.0.1:5099/help", {data: JSON.stringify(all)});   // 받는 쪽: tools/wireflow_recv.py
  return JSON.stringify(Object.fromEntries(Object.entries(all).map(([r, p]) => [r, p.length])));
}
