const fs = require('fs');
const path = require('path');
const OUT = '/tmp/claude-0/-home-user-theduppp/345eda9b-761e-5f75-ac4f-d67073835841/scratchpad/seq/project';
const BLOB = '/_blob/d683fbc00c3971b9761dbfc2cb0d328a';

const SPREAD_W = 1305, SPREAD_H = 891;   // 210 + 15 spine + 210 mm  x  297 mm @ 3 px/mm
const COVER_W = 630, SPINE_W = 45, MARGIN = 42;
const FRONT_W = 630, FRONT_H = 891;
const STRIP_W = 1305, STRIP_H = 420;

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
    `<div style="position: absolute; left: ${MARGIN}px; top: ${MARGIN}px; width: ${FRONT_W - MARGIN * 2}px; height: ${FRONT_H - MARGIN * 2}px; border: ${line}; box-sizing: border-box;"></div>`,
    `<div style="position: absolute; left: 0px; bottom: 16px; width: ${FRONT_W}px; text-align: center; font-size: 11px; letter-spacing: 0.24em; color: ${c.text};">앞표지 210 × 297</div>`,
    `<div style="position: absolute; left: ${MARGIN}px; top: 14px; font-size: 11px; letter-spacing: 0.28em; color: ${c.text};">${label}</div>`
  ].join('\n      ');
}
function stripGuides(c, label) {
  return [
    `<div style="position: absolute; left: 150px; bottom: 18px; width: 180px; text-align: center; font-size: 10px; letter-spacing: 0.2em; color: ${c.text};">정육면체</div>`,
    `<div style="position: absolute; left: 470px; bottom: 18px; width: 320px; text-align: center; font-size: 10px; letter-spacing: 0.2em; color: ${c.text};">비틀리며 갈라지는 띠</div>`,
    `<div style="position: absolute; left: 930px; bottom: 18px; width: 260px; text-align: center; font-size: 10px; letter-spacing: 0.2em; color: ${c.text};">결정</div>`,
    `<div style="position: absolute; left: ${MARGIN}px; top: 14px; font-size: 11px; letter-spacing: 0.28em; color: ${c.text};">${label}</div>`
  ].join('\n      ');
}

const DARK_G = { line: 'rgba(255,255,255,0.20)', band: 'rgba(255,255,255,0.035)', text: 'rgba(255,255,255,0.42)' };
const LIGHT_G = { line: 'rgba(22,24,38,0.26)', band: 'rgba(22,24,38,0.045)', text: 'rgba(22,24,38,0.50)' };

function board(o) {
  const guides = o.kind === 'spread' ? spreadGuides : (o.kind === 'strip' ? stripGuides : frontGuides);
  const bg = o.theme === 'light' ? '#f9fafc' : '#070a10';

  const props = {
    theme: { editor: 'enum', options: ['dark', 'light'], default: o.theme, section: '1 배경' },
    accentA: { editor: 'color', default: '#54EBE0', options: ['#54EBE0', '#7FD9F2', '#8AEFD0', '#A8E4FF'], section: '2 컬러' },
    accentB: { editor: 'color', default: '#BD8CFC', options: ['#BD8CFC', '#A78BFA', '#D8A8F0', '#8FA6F7'], section: '2 컬러' },
    accentC: { editor: 'color', default: '#52E6CC', options: ['#52E6CC', '#7FD9F2', '#C9B6FA', '#FFFFFF'], section: '2 컬러' },
    twist: { editor: 'range', min: 0, max: 2, step: 0.05, default: 0.9, section: '3 띠' },
    splits: { editor: 'int', min: 2, max: 5, step: 1, default: 3, section: '3 띠' },
    slotW: { editor: 'range', min: 0, max: 0.9, step: 0.02, default: 0.66, section: '3 띠' },
    thick: { editor: 'range', min: 0.6, max: 1.5, step: 0.02, default: 1, section: '3 띠' },
    crystalSize: { editor: 'range', min: 0.3, max: 1.1, step: 0.02, default: 0.6, section: '4 결정' },
    crystalScale: { editor: 'range', min: 1.8, max: 3, step: 0.05, default: 2.2, section: '4 결정' },
    crystalBase: { editor: 'range', min: 0.9, max: 1.5, step: 0.02, default: 1.26, section: '4 결정' },
    crystalRot: { editor: 'range', min: 0, max: 1.2, step: 0.01, default: 0.45, section: '4 결정' },
    yaw: { editor: 'range', min: -70, max: 70, step: 1, default: o.yaw, unit: 'deg', section: '5 카메라' },
    pitch: { editor: 'range', min: -50, max: 50, step: 1, default: o.pitch, unit: 'deg', section: '5 카메라' },
    zoom: { editor: 'range', min: 0.7, max: 1.5, step: 0.02, default: 1, section: '5 카메라' },
    autoSpin: { editor: 'boolean', default: false, section: '5 카메라' },
    showGuides: { editor: 'boolean', default: true, section: '6 판형 가이드' },
    $preview: { width: o.w, height: o.h }
  };

  return `<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>${o.title}</title>
<script src="./support.js"><\/script>
<script src="${BLOB}"><\/script>
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
  <canvas ref="{{bind}}" width="${o.w}" height="${o.h}" style="position: absolute; left: 0px; top: 0px; width: ${o.w}px; height: ${o.h}px; display: block; cursor: grab; touch-action: none;"></canvas>
  <sc-if value="{{showGuides}}" hint-placeholder-val="{{true}}">
    <sc-if value="{{lightTheme}}" hint-placeholder-val="{{true}}">
      <div style="position: absolute; left: 0px; top: 0px; width: ${o.w}px; height: ${o.h}px; pointer-events: none;">
      ${guides(LIGHT_G, o.label)}
      </div>
    </sc-if>
    <sc-if value="{{darkTheme}}" hint-placeholder-val="{{true}}">
      <div style="position: absolute; left: 0px; top: 0px; width: ${o.w}px; height: ${o.h}px; pointer-events: none;">
      ${guides(DARK_G, o.label)}
      </div>
    </sc-if>
  </sc-if>
</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='${JSON.stringify(props)}'>
class Component extends DCLogic {
  opts() {
    return {
      view: '${o.view}',
      theme: this.props.theme ?? '${o.theme}',
      accentA: this.props.accentA ?? '#54EBE0',
      accentB: this.props.accentB ?? '#BD8CFC',
      accentC: this.props.accentC ?? '#52E6CC',
      twist: this.props.twist ?? 0.9,
      splits: this.props.splits ?? 3,
      slotW: this.props.slotW ?? 0.66,
      thick: this.props.thick ?? 1,
      crystalSize: this.props.crystalSize ?? 0.6,
      crystalScale: this.props.crystalScale ?? 2.2,
      crystalBase: this.props.crystalBase ?? 1.26,
      crystalRot: this.props.crystalRot ?? 0.45,
      yaw: this.props.yaw ?? ${o.yaw},
      pitch: this.props.pitch ?? ${o.pitch},
      zoom: this.props.zoom ?? 1,
      autoSpin: this.props.autoSpin ?? false
    };
  }
  componentDidUpdate() { if (this.seq) this.seq.update(this.opts()); }
  componentWillUnmount() { if (this.seq) { this.seq.destroy(); this.seq = null; } }
  attach(el) {
    if (!el) return;
    if (this.seq && this.el === el) return;
    if (this.seq) this.seq.destroy();
    this.el = el;
    if (window.SEQ3D) {
      this.seq = window.SEQ3D.mount(el, this.opts());
    } else {
      var self = this;
      setTimeout(function () {
        if (window.SEQ3D && !self.seq) self.seq = window.SEQ3D.mount(el, self.opts());
      }, 400);
    }
  }
  renderVals() {
    var self = this;
    var theme = this.props.theme ?? '${o.theme}';
    return {
      bind: function (el) { self.attach(el); },
      showGuides: this.props.showGuides ?? true,
      lightTheme: theme === 'light',
      darkTheme: theme !== 'light'
    };
  }
}
<\/script>
</body>
</html>
`;
}

const boards = [
  { file: 'Main.dc.html',         title: 'B 전개도 다크',   label: 'OPTION B — 앞면 완결형', kind: 'spread', view: 'spread',   theme: 'dark',  w: SPREAD_W, h: SPREAD_H, yaw: -4, pitch: 4 },
  { file: 'Spread-Light.dc.html', title: 'B 전개도 라이트', label: 'OPTION B — 라이트',      kind: 'spread', view: 'spread',   theme: 'light', w: SPREAD_W, h: SPREAD_H, yaw: -4, pitch: 4 },
  { file: 'Front-Dark.dc.html',   title: '앞표지 단독 다크',   label: '앞표지 · 다크',   kind: 'front',  view: 'portrait', theme: 'dark',  w: FRONT_W, h: FRONT_H, yaw: -4, pitch: 4 },
  { file: 'Front-Light.dc.html',  title: '앞표지 단독 라이트', label: '앞표지 · 라이트', kind: 'front',  view: 'portrait', theme: 'light', w: FRONT_W, h: FRONT_H, yaw: -4, pitch: 4 },
  { file: 'Structure.dc.html',    title: '구조',           label: '구조 — 정육면체 · 띠 · 결정', kind: 'strip', view: 'strip', theme: 'dark', w: STRIP_W, h: STRIP_H, yaw: 0, pitch: 6 }
];
boards.forEach(b => { fs.writeFileSync(path.join(OUT, b.file), board(b)); console.log('wrote', b.file); });

const prev = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const ROW2 = 1320;
prev.boards = {
  'Main.dc.html':         { x: 0,    y: 0,    w: SPREAD_W, h: SPREAD_H, title: 'B · 앞면 완결형 (다크)',  is_interactive: true },
  'Spread-Light.dc.html': { x: 1385, y: 0,    w: SPREAD_W, h: SPREAD_H, title: 'B · 앞면 완결형 (라이트)', is_interactive: true },
  'Front-Dark.dc.html':   { x: 0,    y: ROW2, w: FRONT_W,  h: FRONT_H,  title: '앞표지 단독 (다크)',   is_interactive: true },
  'Front-Light.dc.html':  { x: 710,  y: ROW2, w: FRONT_W,  h: FRONT_H,  title: '앞표지 단독 (라이트)', is_interactive: true },
  'Structure.dc.html':    { x: 1420, y: 1555, w: STRIP_W,  h: STRIP_H,  title: '구조',                is_interactive: true }
};
prev.order = ['Main.dc.html', 'Spread-Light.dc.html', 'Front-Dark.dc.html', 'Front-Light.dc.html', 'Structure.dc.html'];
prev.notes.t1.text = 'B안 · 전개도 — 앞표지에서 수열이 완결되고, 뒤표지는 비워 둔다';
prev.notes.t1.maxW = 2690;
prev.notes.t2.text = '앞표지 단독 컷 · 구조';
prev.notes.t2.maxW = 2725;
fs.writeFileSync(path.join(OUT, 'canvas.json'), JSON.stringify(prev, null, 2));
console.log('wrote canvas.json');
