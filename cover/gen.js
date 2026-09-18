const fs = require('fs');
const path = require('path');
const OUT = '/tmp/claude-0/-home-user-theduppp/345eda9b-761e-5f75-ac4f-d67073835841/scratchpad/seq/project';
const BLOB = '/_blob/8047aa5763fa81ac5dfa6ea043fe2937';

const SPREAD_W = 1305, SPREAD_H = 891;   // 210 + 15 spine + 210 mm  x  297 mm @ 3 px/mm
const COVER_W = 630, SPINE_W = 45, MARGIN = 42;
const FRONT_W = 630, FRONT_H = 891;
const STRIP_W = 1305, STRIP_H = 360;

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

// Stage strip: the seven objects sit on an evenly spaced straight line, so the
// tick labels are placed at the projected centre of each one.
function stripGuides(c, label) {
  const first = 112.5, step = 180;
  const ticks = [];
  for (let i = 0; i < 7; i++) {
    ticks.push(`<div style="position: absolute; left: ${first + step * i - 30}px; bottom: 18px; width: 60px; text-align: center; font-size: 10px; letter-spacing: 0.18em; color: ${c.text};">${String(i + 1).padStart(2, '0')}</div>`);
  }
  ticks.push(`<div style="position: absolute; left: ${MARGIN}px; top: 14px; font-size: 11px; letter-spacing: 0.28em; color: ${c.text};">${label}</div>`);
  return ticks.join('\n      ');
}

const DARK_G = { line: 'rgba(255,255,255,0.20)', band: 'rgba(255,255,255,0.035)', text: 'rgba(255,255,255,0.42)' };
const LIGHT_G = { line: 'rgba(22,24,38,0.26)', band: 'rgba(22,24,38,0.045)', text: 'rgba(22,24,38,0.50)' };

function board(o) {
  const guides = o.kind === 'spread' ? spreadGuides : (o.kind === 'strip' ? stripGuides : frontGuides);
  const bg = o.theme === 'light' ? '#f6f7fb' : '#05060a';

  const props = {
    theme: { editor: 'enum', options: ['dark', 'light'], default: o.theme, section: '1 배경' },
    accentA: { editor: 'color', default: '#66EDDE', options: ['#66EDDE', '#8FD8F5', '#A6F0CE', '#B9E6FF'], section: '2 컬러' },
    accentB: { editor: 'color', default: '#B891FC', options: ['#B891FC', '#A78BFA', '#DCB8F2', '#93A9F7'], section: '2 컬러' },
    glow: { editor: 'range', min: 0, max: 2, step: 0.05, default: 1, section: '2 컬러' },
    stages: { editor: 'int', min: 3, max: 9, step: 1, default: o.stages, section: '3 진화' },
    twist: { editor: 'range', min: 0, max: 1.8, step: 0.05, default: 1, section: '3 진화' },
    spin: { editor: 'range', min: 0, max: 2.5, step: 0.05, default: o.spin, section: '3 진화' },
    fuse: { editor: 'range', min: 0.01, max: 0.5, step: 0.01, default: o.fuse, section: '3 진화' },
    yaw: { editor: 'range', min: -75, max: 75, step: 1, default: o.yaw, unit: 'deg', section: '4 카메라' },
    pitch: { editor: 'range', min: -50, max: 50, step: 1, default: o.pitch, unit: 'deg', section: '4 카메라' },
    zoom: { editor: 'range', min: 0.6, max: 1.6, step: 0.02, default: 1, section: '4 카메라' },
    autoSpin: { editor: 'boolean', default: false, section: '4 카메라' },
    showGuides: { editor: 'boolean', default: true, section: '5 판형 가이드' },
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
    a { color: #66EDDE; } a:hover { color: #B891FC; }
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
      layout: '${o.layout}',
      theme: this.props.theme ?? '${o.theme}',
      accentA: this.props.accentA ?? '#66EDDE',
      accentB: this.props.accentB ?? '#B891FC',
      glow: this.props.glow ?? 1,
      stages: this.props.stages ?? ${o.stages},
      twist: this.props.twist ?? 1,
      spin: this.props.spin ?? ${o.spin},
      fuse: this.props.fuse ?? ${o.fuse},
      yaw: this.props.yaw ?? ${o.yaw},
      pitch: this.props.pitch ?? ${o.pitch},
      zoom: this.props.zoom ?? 1,
      autoSpin: this.props.autoSpin ?? false
    };
  }
  componentDidUpdate() {
    if (this.seq) this.seq.update(this.opts());
  }
  componentWillUnmount() {
    if (this.seq) { this.seq.destroy(); this.seq = null; }
  }
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
  { file: 'Main.dc.html',         title: 'B 전개도 다크',   label: 'OPTION B — 앞면 완결형', kind: 'spread', layout: 'front',    theme: 'dark',  w: SPREAD_W, h: SPREAD_H, stages: 6, yaw: -6, pitch: 6, spin: 1, fuse: 0.15 },
  { file: 'Spread-Light.dc.html', title: 'B 전개도 라이트', label: 'OPTION B — 라이트',      kind: 'spread', layout: 'front',    theme: 'light', w: SPREAD_W, h: SPREAD_H, stages: 6, yaw: -6, pitch: 6, spin: 1, fuse: 0.15 },
  { file: 'Front-Dark.dc.html',   title: '앞표지 단독 다크',   label: '앞표지 · 다크',   kind: 'front', layout: 'portrait', theme: 'dark',  w: FRONT_W, h: FRONT_H, stages: 6, yaw: -10, pitch: 8, spin: 1, fuse: 0.15 },
  { file: 'Front-Light.dc.html',  title: '앞표지 단독 라이트', label: '앞표지 · 라이트', kind: 'front', layout: 'portrait', theme: 'light', w: FRONT_W, h: FRONT_H, stages: 6, yaw: -10, pitch: 8, spin: 1, fuse: 0.15 },
  { file: 'Stages.dc.html',       title: '진화 단계',       label: '정육면체 → 눈 결정 · 7단계', kind: 'strip', layout: 'strip', theme: 'dark', w: STRIP_W, h: STRIP_H, stages: 7, yaw: 0, pitch: 0, spin: 0.35, fuse: 0.02 }
];

boards.forEach(b => { fs.writeFileSync(path.join(OUT, b.file), board(b)); console.log('wrote', b.file); });

// Index: keep every key read back from the canvas, change only what moved.
const prev = JSON.parse(fs.readFileSync('/tmp/claude-0/-home-user-theduppp/345eda9b-761e-5f75-ac4f-d67073835841/scratchpad/artifact-files/84ac175b-cc87-4fe2-947a-4b8341dc293c/project/canvas.json', 'utf8'));
const ROW2 = 1320;
prev.boards = {
  'Main.dc.html':         { x: 0,    y: 0,    w: SPREAD_W, h: SPREAD_H, title: 'B · 앞면 완결형 (다크)',  is_interactive: true },
  'Spread-Light.dc.html': { x: 1385, y: 0,    w: SPREAD_W, h: SPREAD_H, title: 'B · 앞면 완결형 (라이트)', is_interactive: true },
  'Front-Dark.dc.html':   { x: 0,    y: ROW2, w: FRONT_W,  h: FRONT_H,  title: '앞표지 단독 (다크)',   is_interactive: true },
  'Front-Light.dc.html':  { x: 710,  y: ROW2, w: FRONT_W,  h: FRONT_H,  title: '앞표지 단독 (라이트)', is_interactive: true },
  'Stages.dc.html':       { x: 1420, y: 1585, w: STRIP_W,  h: STRIP_H,  title: '진화 단계 01 → 07',    is_interactive: true }
};
prev.order = ['Main.dc.html', 'Spread-Light.dc.html', 'Front-Dark.dc.html', 'Front-Light.dc.html', 'Stages.dc.html'];
prev.notes.t1.text = 'B안 · 전개도 — 앞표지에서 수열이 완결되고, 뒤표지에는 최초의 정육면체만';
prev.notes.t1.maxW = 2690;
prev.notes.t2.text = '앞표지 단독 컷 · 진화 단계';
prev.notes.t2.maxW = 2725;
fs.writeFileSync(path.join(OUT, 'canvas.json'), JSON.stringify(prev, null, 2));
console.log('wrote canvas.json');
