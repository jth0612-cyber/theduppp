const fs = require('fs');
const path = require('path');
const OUT = '/tmp/claude-0/-home-user-theduppp/345eda9b-761e-5f75-ac4f-d67073835841/scratchpad/seq/project';
const BLOB = '/_blob/68eb73d0a76003504b636bb586dc6b08';

const SPREAD_W = 1305, SPREAD_H = 891;   // 210mm + 15mm spine + 210mm  x  297mm  @ 3px/mm
const COVER_W = 630, SPINE_W = 45, MARGIN = 42;
const FRONT_W = 630, FRONT_H = 891;

function spreadGuides(c, label) {
  const line = `1px dashed ${c.line}`;
  return [
    `<div style="position: absolute; left: ${COVER_W}px; top: 0px; width: ${SPINE_W}px; height: ${SPREAD_H}px; background: ${c.band}; border-left: ${line}; border-right: ${line}; box-sizing: border-box;"></div>`,
    `<div style="position: absolute; left: ${MARGIN}px; top: ${MARGIN}px; width: ${COVER_W - MARGIN * 2}px; height: ${SPREAD_H - MARGIN * 2}px; border: ${line}; box-sizing: border-box;"></div>`,
    `<div style="position: absolute; left: ${COVER_W + SPINE_W + MARGIN}px; top: ${MARGIN}px; width: ${COVER_W - MARGIN * 2}px; height: ${SPREAD_H - MARGIN * 2}px; border: ${line}; box-sizing: border-box;"></div>`,
    `<div style="position: absolute; left: 0px; bottom: 16px; width: ${COVER_W}px; text-align: center; font-size: 11px; letter-spacing: 0.24em; color: ${c.text};">뒤표지 210 × 297</div>`,
    `<div style="position: absolute; left: ${COVER_W + SPINE_W}px; bottom: 16px; width: ${COVER_W}px; text-align: center; font-size: 11px; letter-spacing: 0.24em; color: ${c.text};">앞표지 210 × 297</div>`,
    `<div style="position: absolute; left: ${COVER_W}px; top: 14px; width: ${SPINE_W}px; text-align: center; font-size: 9px; letter-spacing: 0.02em; color: ${c.text};">책등<br>15</div>`,
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

const DARK_G = { line: 'rgba(255,255,255,0.20)', band: 'rgba(255,255,255,0.035)', text: 'rgba(255,255,255,0.40)' };
const LIGHT_G = { line: 'rgba(22,24,38,0.26)', band: 'rgba(22,24,38,0.045)', text: 'rgba(22,24,38,0.48)' };

function board(o) {
  const guides = o.kind === 'spread' ? spreadGuides : frontGuides;
  const bgDark = '#05060a', bgLight = '#f6f7fb';
  const bg = o.theme === 'light' ? bgLight : bgDark;

  const props = {
    theme: { editor: 'enum', options: ['dark', 'light'], default: o.theme, section: '1 배경' },
    accentA: { editor: 'color', default: '#7FE7DC', options: ['#7FE7DC', '#8FD8F5', '#A6F0CE', '#B9E6FF'], section: '2 컬러' },
    accentB: { editor: 'color', default: '#C4A9F4', options: ['#C4A9F4', '#A78BFA', '#DCB8F2', '#93A9F7'], section: '2 컬러' },
    glow: { editor: 'range', min: 0, max: 2, step: 0.05, default: 1, section: '2 컬러' },
    stages: { editor: 'int', min: 3, max: 9, step: 1, default: o.stages, section: '3 진화' },
    twist: { editor: 'range', min: 0, max: 1.4, step: 0.05, default: 0.55, section: '3 진화' },
    spin: { editor: 'range', min: 0, max: 2.5, step: 0.05, default: 1, section: '3 진화' },
    fuse: { editor: 'range', min: 0.01, max: 0.7, step: 0.01, default: 0.18, section: '3 진화' },
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
    a { color: #7FE7DC; } a:hover { color: #C4A9F4; }
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
      accentA: this.props.accentA ?? '#7FE7DC',
      accentB: this.props.accentB ?? '#C4A9F4',
      glow: this.props.glow ?? 1,
      stages: this.props.stages ?? ${o.stages},
      twist: this.props.twist ?? 0.55,
      spin: this.props.spin ?? 1,
      fuse: this.props.fuse ?? 0.18,
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
  { file: 'Main.dc.html', title: 'A 관통형 전개도', label: 'OPTION A — 관통형', kind: 'spread', layout: 'through', theme: 'dark', w: SPREAD_W, h: SPREAD_H, stages: 7, yaw: -8, pitch: 7 },
  { file: 'Spread-B.dc.html', title: 'B 앞면 완결형 전개도', label: 'OPTION B — 앞면 완결형', kind: 'spread', layout: 'front', theme: 'dark', w: SPREAD_W, h: SPREAD_H, stages: 6, yaw: -6, pitch: 6 },
  { file: 'Spread-C.dc.html', title: 'C 책등 확산형 전개도', label: 'OPTION C — 책등 확산형', kind: 'spread', layout: 'bloom', theme: 'dark', w: SPREAD_W, h: SPREAD_H, stages: 9, yaw: 0, pitch: 9 },
  { file: 'Spread-A-Light.dc.html', title: 'A 관통형 라이트', label: 'OPTION A — 라이트', kind: 'spread', layout: 'through', theme: 'light', w: SPREAD_W, h: SPREAD_H, stages: 7, yaw: -8, pitch: 7 },
  { file: 'Front-Dark.dc.html', title: '앞표지 단독 다크', label: '앞표지 · 다크', kind: 'front', layout: 'portrait', theme: 'dark', w: FRONT_W, h: FRONT_H, stages: 6, yaw: -10, pitch: 8 },
  { file: 'Front-Light.dc.html', title: '앞표지 단독 라이트', label: '앞표지 · 라이트', kind: 'front', layout: 'portrait', theme: 'light', w: FRONT_W, h: FRONT_H, stages: 6, yaw: -10, pitch: 8 }
];

boards.forEach(b => {
  fs.writeFileSync(path.join(OUT, b.file), board(b));
  console.log('wrote', b.file);
});

const GAP = 80, ROW2 = 1320;
const canvas = {
  v: 3,
  createdOnFiles: { v: 1, at: new Date().toISOString().replace(/\.\d+Z$/, 'Z') },
  title: 'SEQUENCE 표지 오브제',
  launch: { view: 'canvas' },
  pages: [],
  boards: {
    'Main.dc.html':          { x: 0,    y: 0,    w: SPREAD_W, h: SPREAD_H, title: 'A · 관통형 (다크)',        is_interactive: true },
    'Spread-B.dc.html':      { x: 1385, y: 0,    w: SPREAD_W, h: SPREAD_H, title: 'B · 앞면 완결형 (다크)',   is_interactive: true },
    'Spread-C.dc.html':      { x: 2770, y: 0,    w: SPREAD_W, h: SPREAD_H, title: 'C · 책등 확산형 (다크)',   is_interactive: true },
    'Spread-A-Light.dc.html':{ x: 0,    y: ROW2, w: SPREAD_W, h: SPREAD_H, title: 'A · 관통형 (라이트)',      is_interactive: true },
    'Front-Dark.dc.html':    { x: 1385, y: ROW2, w: FRONT_W,  h: FRONT_H,  title: '앞표지 단독 (다크)',        is_interactive: true },
    'Front-Light.dc.html':   { x: 2095, y: ROW2, w: FRONT_W,  h: FRONT_H,  title: '앞표지 단독 (라이트)',      is_interactive: true }
  },
  order: ['Main.dc.html', 'Spread-B.dc.html', 'Spread-C.dc.html', 'Spread-A-Light.dc.html', 'Front-Dark.dc.html', 'Front-Light.dc.html'],
  notes: {
    t1: { x: 0, y: -330, text: '전개도 3안 — 뒤표지 · 책등 · 앞표지 (다크)', kind: 'title1', maxW: 4075 },
    t2: { x: 0, y: 990,  text: '라이트 버전 · 앞표지 단독 컷', kind: 'title1', maxW: 2725 }
  },
  designSystems: []
};
fs.writeFileSync(path.join(OUT, 'canvas.json'), JSON.stringify(canvas, null, 2));
console.log('wrote canvas.json');
