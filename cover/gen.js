// Builds the artboards. Each one is a Cycles render placed on the trim layout,
// so the only lever left is whether the print guides are drawn.
const fs = require('fs'), path = require('path');
const OUT = '/tmp/claude-0/-home-user-theduppp/345eda9b-761e-5f75-ac4f-d67073835841/scratchpad/seq/project';
const BLOBS = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const PREV = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));

const SPREAD_W = 1305, SPREAD_H = 891;   // 210 + 15 spine + 210 mm x 297 mm @ 3 px/mm
const COVER_W = 630, SPINE_W = 45, MARGIN = 42;
const STRIP_W = 1305, STRIP_H = 560;

const DARK = { line: 'rgba(255,255,255,0.20)', band: 'rgba(255,255,255,0.035)', text: 'rgba(255,255,255,0.42)' };
const LIGHT = { line: 'rgba(22,24,38,0.26)', band: 'rgba(22,24,38,0.045)', text: 'rgba(22,24,38,0.50)' };

function spreadGuides(c, label) {
  const line = `1px dashed ${c.line}`;
  return [
    `<div style="position: absolute; left: ${COVER_W}px; top: 0px; width: ${SPINE_W}px; height: ${SPREAD_H}px; background: ${c.band}; border-left: ${line}; border-right: ${line}; box-sizing: border-box;"></div>`,
    `<div style="position: absolute; left: ${MARGIN}px; top: ${MARGIN}px; width: ${COVER_W - MARGIN * 2}px; height: ${SPREAD_H - MARGIN * 2}px; border: ${line}; box-sizing: border-box;"></div>`,
    `<div style="position: absolute; left: ${COVER_W + SPINE_W + MARGIN}px; top: ${MARGIN}px; width: ${COVER_W - MARGIN * 2}px; height: ${SPREAD_H - MARGIN * 2}px; border: ${line}; box-sizing: border-box;"></div>`,
    `<div style="position: absolute; left: 0px; bottom: 16px; width: ${COVER_W}px; text-align: center; font-size: 11px; letter-spacing: 0.24em; color: ${c.text};">뒤표지 210 × 297</div>`,
    `<div style="position: absolute; left: ${COVER_W + SPINE_W}px; bottom: 16px; width: ${COVER_W}px; text-align: center; font-size: 11px; letter-spacing: 0.24em; color: ${c.text};">앞표지 210 × 297</div>`,
    `<div style="position: absolute; left: ${COVER_W}px; top: 14px; width: ${SPINE_W}px; text-align: center; font-size: 9px; color: ${c.text};">책등<br>15</div>`,
    `<div style="position: absolute; left: ${MARGIN}px; top: 14px; font-size: 11px; letter-spacing: 0.28em; color: ${c.text};">${label}</div>`
  ].join('\n      ');
}
function frontGuides(c, label) {
  const line = `1px dashed ${c.line}`;
  return [
    `<div style="position: absolute; left: ${MARGIN}px; top: ${MARGIN}px; width: ${COVER_W - MARGIN * 2}px; height: ${SPREAD_H - MARGIN * 2}px; border: ${line}; box-sizing: border-box;"></div>`,
    `<div style="position: absolute; left: 0px; bottom: 16px; width: ${COVER_W}px; text-align: center; font-size: 11px; letter-spacing: 0.24em; color: ${c.text};">앞표지 210 × 297</div>`,
    `<div style="position: absolute; left: ${MARGIN}px; top: 14px; font-size: 11px; letter-spacing: 0.28em; color: ${c.text};">${label}</div>`
  ].join('\n      ');
}
function stripGuides(c, label) {
  return [
    `<div style="position: absolute; left: 60px; bottom: 20px; width: 200px; text-align: center; font-size: 10px; letter-spacing: 0.2em; color: ${c.text};">정육면체</div>`,
    `<div style="position: absolute; left: 330px; bottom: 20px; width: 460px; text-align: center; font-size: 10px; letter-spacing: 0.2em; color: ${c.text};">갈라지며 꼬이는 두 가닥</div>`,
    `<div style="position: absolute; left: 880px; bottom: 20px; width: 330px; text-align: center; font-size: 10px; letter-spacing: 0.2em; color: ${c.text};">결정</div>`,
    `<div style="position: absolute; left: ${MARGIN}px; top: 14px; font-size: 11px; letter-spacing: 0.28em; color: ${c.text};">${label}</div>`
  ].join('\n      ');
}

function board(o) {
  const guides = o.kind === 'spread' ? spreadGuides : (o.kind === 'strip' ? stripGuides : frontGuides);
  const g = o.theme === 'light' ? LIGHT : DARK;
  const bg = o.theme === 'light' ? '#f7f8fb' : '#05070c';
  const props = {
    showGuides: { editor: 'boolean', default: true, section: '판형 가이드' },
    $preview: { width: o.w, height: o.h }
  };
  return `<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>${o.title}</title>
<script src="./support.js"><\/script>
</head>
<body>
<x-dc>
<helmet>
  <style>
    body { margin: 0; font-family: "Helvetica Neue", "Apple SD Gothic Neo", "Noto Sans KR", Arial, sans-serif; background: ${bg}; }
    a { color: #54EBE0; } a:hover { color: #BD8CFC; }
  </style>
</helmet>
<div style="width: ${o.w}px; height: ${o.h}px; position: relative; overflow: hidden; background: ${bg};">
  <img src="${BLOBS[o.img]}" alt="${o.alt}" style="position: absolute; left: 0px; top: 0px; width: ${o.w}px; height: ${o.h}px; display: block; object-fit: cover;">
  <sc-if value="{{showGuides}}" hint-placeholder-val="{{true}}">
    <div style="position: absolute; left: 0px; top: 0px; width: ${o.w}px; height: ${o.h}px; pointer-events: none;">
      ${guides(g, o.label)}
    </div>
  </sc-if>
</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='${JSON.stringify(props)}'>
class Component extends DCLogic {
  renderVals() {
    return { showGuides: this.props.showGuides ?? true };
  }
}
<\/script>
</body>
</html>
`;
}

const boards = [
  { file: 'Main.dc.html',         img: 'spread-dark',  title: 'B 전개도 다크',   label: 'OPTION B — 앞면 완결형', alt: '앞표지에 놓인 유리 오브제 전개도, 다크', kind: 'spread', theme: 'dark',  w: SPREAD_W, h: SPREAD_H },
  { file: 'Spread-Light.dc.html', img: 'spread-light', title: 'B 전개도 라이트', label: 'OPTION B — 라이트',      alt: '앞표지에 놓인 유리 오브제 전개도, 라이트', kind: 'spread', theme: 'light', w: SPREAD_W, h: SPREAD_H },
  { file: 'Front-Dark.dc.html',   img: 'front-dark',   title: '앞표지 다크',     label: '앞표지 · 다크',   alt: '정육면체에서 결정으로 이어지는 유리 오브제, 다크', kind: 'front', theme: 'dark',  w: COVER_W, h: SPREAD_H },
  { file: 'Front-Light.dc.html',  img: 'front-light',  title: '앞표지 라이트',   label: '앞표지 · 라이트', alt: '정육면체에서 결정으로 이어지는 유리 오브제, 라이트', kind: 'front', theme: 'light', w: COVER_W, h: SPREAD_H },
  { file: 'Structure.dc.html',    img: 'structure',    title: '구조',           label: '구조 — 정육면체 · 두 가닥 · 결정', alt: '오브제를 옆에서 본 구조', kind: 'strip', theme: 'dark', w: STRIP_W, h: STRIP_H }
];
boards.forEach(b => { fs.writeFileSync(path.join(OUT, b.file), board(b)); console.log('wrote', b.file); });

const ROW2 = 1320;
PREV.boards = {
  'Main.dc.html':         { x: 0,    y: 0,    w: SPREAD_W, h: SPREAD_H, title: 'B · 앞면 완결형 (다크)' },
  'Spread-Light.dc.html': { x: 1385, y: 0,    w: SPREAD_W, h: SPREAD_H, title: 'B · 앞면 완결형 (라이트)' },
  'Front-Dark.dc.html':   { x: 0,    y: ROW2, w: COVER_W,  h: SPREAD_H, title: '앞표지 (다크)' },
  'Front-Light.dc.html':  { x: 710,  y: ROW2, w: COVER_W,  h: SPREAD_H, title: '앞표지 (라이트)' },
  'Structure.dc.html':    { x: 1420, y: 1485, w: STRIP_W,  h: STRIP_H,  title: '구조' }
};
PREV.order = ['Main.dc.html', 'Spread-Light.dc.html', 'Front-Dark.dc.html', 'Front-Light.dc.html', 'Structure.dc.html'];
PREV.notes.t1.text = 'B안 · 전개도 — 앞표지에서 수열이 완결되고, 뒤표지는 비워 둔다';
PREV.notes.t1.maxW = 2690;
PREV.notes.t2.text = '앞표지 단독 컷 · 구조';
PREV.notes.t2.maxW = 2725;
fs.writeFileSync(path.join(OUT, 'canvas.json'), JSON.stringify(PREV, null, 2));
console.log('wrote canvas.json');
