"""작동 흐름 캡처 준비: tools/wireflow_crawl.js 와 학부모 리포트·주차 고치기 장면 스크립트에 데모 비밀번호를 넣은 사본을
TH/.playwright-mcp/ 에 만든다 (Playwright MCP browser_run_code_unsafe 로 돌린 뒤 지운다). 저장소에는 비밀번호가 없다.

    python tools/wireflow_capture.py make   → 사본 만들기 (boxes.json 이 있으면 설명 창 캡처용 wfhelp.js 도)
    python tools/wireflow_capture.py merge  → boxes.json 에 학부모 리포트·주차 고치기 장면을 더한다
    python tools/wireflow_capture.py clean  → 사본 지우기
"""
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = os.path.join(ROOT, "_deploy", "demo", "student-lms-demo")
PMCP = os.path.join(os.path.dirname(ROOT), ".playwright-mcp")
SHOTS = os.path.join(ROOT, "wireflow", "roles3").replace("\\", "/") + "/"
B = "http://127.0.0.1:5077"
EXTRA = r'''async (page) => {
  const ctx = await page.context().browser().newContext({viewport: {width: 1280, height: 800}, deviceScaleFactor: 2}); const pg = await ctx.newPage();
  let n = 0;
  for (const q of ["", "?kind=review", "?kind=mock"]) {
    await pg.goto("%(B)s/p/%(TOK)s" + q); await pg.waitForLoadState("networkidle").catch(() => {}); n++;
    const H = await pg.evaluate(() => Math.min(document.documentElement.scrollHeight, 3200));
    await pg.screenshot({path: "%(OUT)sparent_0" + n + ".jpg", type: "jpeg", quality: 82, fullPage: true, clip: {x: 0, y: 0, width: 1265, height: H}});
  }
  await pg.goto("%(B)s/login"); await pg.fill("input[name=username]", "ta_hanjisu"); await pg.fill("input[name=password]", "%(TA)s");
  await Promise.all([pg.waitForURL(/\/t\//), pg.locator("button[type=submit]").first().click()]);
  await pg.goto("%(B)s/t/schedule/1"); await pg.waitForLoadState("networkidle");
  await pg.evaluate(() => { const r = document.getElementById("w7"); r.querySelector("details").open = true;
    const w = document.querySelector(".sched-wrap"); w.scrollTop = r.offsetTop - 70; w.scrollIntoView({block: "start"}); });
  await pg.waitForTimeout(300);
  await pg.screenshot({path: "%(OUT)sassistant_edit.jpg", type: "jpeg", quality: 82});
  await ctx.close(); return "ok";
}'''


def creds():
    c = open(os.path.join(DEMO, "DEMO_CREDENTIALS.txt"), encoding="utf-8").read()
    return lambda u: re.search(re.escape(u) + r"\s*/\s*(\S+)", c).group(1)


if __name__ == "__main__":
    act = sys.argv[1] if len(sys.argv) > 1 else "make"
    if act == "make":
        pw = creds()
        s = open(os.path.join(ROOT, "tools", "wireflow_crawl.js"), encoding="utf-8").read()
        s = (s.replace("__STUDENT_ID__", "0012874416").replace("__STUDENT_PW__", pw("0012874416"))
             .replace("__TA_PW__", pw("ta_hanjisu")).replace("__TEACHER_PW__", pw("master")))
        open(os.path.join(PMCP, "wfcrawl.js"), "w", encoding="utf-8").write(s)
        tok = sqlite3.connect(os.path.join(DEMO, "instance", "lms.sqlite3")).execute(
            "SELECT parent_token FROM students WHERE parent_token IS NOT NULL ORDER BY id LIMIT 1").fetchone()[0]
        open(os.path.join(PMCP, "wfextra.js"), "w", encoding="utf-8").write(EXTRA % {"B": B, "TOK": tok, "OUT": SHOTS, "TA": pw("ta_hanjisu")})
        # 설명 창 캡처: boxes.json 이 있어야 한다 (화면 주소 목록). 방 안(/s/rooms/장소)은 3D 화면이라 뺀다
        bp = os.path.join(ROOT, "wireflow", "roles3", "boxes.json")
        if os.path.exists(bp):
            box = json.load(open(bp, encoding="utf-8"))
            paths = lambda r: json.dumps([k for k in box[r] if not re.fullmatch(r"/s/rooms/(?!rank)\w+", k)], ensure_ascii=False)
            h = open(os.path.join(ROOT, "tools", "wireflow_help.js"), encoding="utf-8").read()
            h = (h.replace("__OUT__", SHOTS).replace("__STUDENT_ID__", "0012874416").replace("__STUDENT_PW__", pw("0012874416"))
                 .replace("__TEACHER_PW__", pw("master")).replace("__STUDENT_PATHS__", paths("student")).replace("__TEACHER_PATHS__", paths("teacher")))
            open(os.path.join(PMCP, "wfhelp.js"), "w", encoding="utf-8").write(h)
        print("made")
    elif act == "merge":
        p = os.path.join(ROOT, "wireflow", "roles3", "boxes.json")
        d = json.load(open(p, encoding="utf-8"))
        d["parent"] = {k: {"name": f"parent_0{i}", "W": 1265, "H": 2629, "title": "", "h1": "", "links": [], "forms": []}
                       for i, k in enumerate(["/p/PARENT", "/p/PARENT?kind=review", "/p/PARENT?kind=mock"], 1)}
        d["assistant"]["/t/schedule/edit"] = {"name": "assistant_edit", "W": 1280, "H": 800, "title": "", "h1": "", "links": [], "forms": []}
        json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False)
        print("merged")
    else:
        for f in ("wfcrawl.js", "wfextra.js", "wfhelp.js"):
            if os.path.exists(os.path.join(PMCP, f)):
                os.remove(os.path.join(PMCP, f))
        print("cleaned")
