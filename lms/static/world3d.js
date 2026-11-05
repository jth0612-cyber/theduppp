// 소도시 명상 3D 공통 엔진. 장소(신사·노천탕·바닷가 역·골목 찻집)는 places/*.js 가 그리고,
// 캐릭터·카메라·조작·친구 동기화·집중 타이머·소리는 여기서 함께 쓴다.
import * as THREE from "./vendor/three.module.min.js";

const root = document.getElementById("w3");
const PLACE = (await import(`./places/${root.dataset.room}.js`)).default;
const stage = root.querySelector("[data-stage]");
const canvas = root.querySelector("[data-canvas]");
const $ = (s) => root.querySelector(s);
const csrf = () => (document.querySelector('meta[name="csrf-token"]') || {}).content || "";
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const isTouch = matchMedia("(pointer: coarse)").matches;
// 받침에 따라 조사 고르기 (방석을 / 자리를)
const josa = (w, a, b) => { const c = w.charCodeAt(w.length - 1) - 0xac00; return w + (c >= 0 && c % 28 ? a : b); };

// ---------------------------------------------------------------- 렌더러
let renderer;
try {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: "high-performance" });
} catch (e) {
  location.replace(root.dataset.flat);
  throw e;
}
let pixelRatio = Math.min(window.devicePixelRatio || 1, isTouch ? 1.5 : 2);
renderer.setPixelRatio(pixelRatio);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 400);

// ---------------------------------------------------------------- 시간대별 색
const hour = new Date().getHours();
const TIME = hour >= 6 && hour < 17 ? "day" : hour >= 17 && hour < 19 ? "dusk" : "night";
const PAL = {
  day:   { top: 0x8fb6d4, horizon: 0xf0e6d4, fog: 0xe8e0cf, hemiSky: 0xfff3dc, hemiGround: 0x6c7a58, hemi: 1.05, sun: 0xfff0d2, sunI: 1.5, ground: 0xc4b69c, grass: 0x7d9363, lamp: 0.5 },
  dusk:  { top: 0x46527a, horizon: 0xf2a676, fog: 0xd8a88a, hemiSky: 0xffd2b0, hemiGround: 0x4f4a48, hemi: 0.85, sun: 0xffad73, sunI: 1.1, ground: 0xb09a86, grass: 0x66734f, lamp: 1.2 },
  night: { top: 0x0b1226, horizon: 0x2b3456, fog: 0x1b2238, hemiSky: 0x6f80b8, hemiGround: 0x1d1d26, hemi: 0.55, sun: 0x9db0e6, sunI: 0.35, ground: 0x5d5a5e, grass: 0x34433a, lamp: 2.2 },
}[TIME];
if (PLACE.palette) PLACE.palette(PAL, TIME);

scene.fog = new THREE.Fog(PAL.fog, 26, 95);
scene.background = new THREE.Color(PAL.fog);

// 하늘: 위는 짙고 지평선은 밝은 둥근 천장
{
  const g = new THREE.SphereGeometry(220, 32, 16);
  const top = new THREE.Color(PAL.top), hor = new THREE.Color(PAL.horizon), cols = [];
  const pos = g.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    const t = Math.max(0, Math.min(1, pos.getY(i) / 120 + 0.08));
    const c = hor.clone().lerp(top, Math.pow(t, 0.7));
    cols.push(c.r, c.g, c.b);
  }
  g.setAttribute("color", new THREE.Float32BufferAttribute(cols, 3));
  const sky = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide, fog: false }));
  scene.add(sky);
  if (TIME !== "day" && PLACE.moon !== false) {
    const moon = new THREE.Mesh(new THREE.CircleGeometry(5, 32), new THREE.MeshBasicMaterial({ color: 0xf4ead2, fog: false }));
    moon.position.set(-60, 70, -150); moon.lookAt(0, 0, 0); scene.add(moon);
  }
}

const hemi = new THREE.HemisphereLight(PAL.hemiSky, PAL.hemiGround, PAL.hemi);
scene.add(hemi);
const sun = new THREE.DirectionalLight(PAL.sun, PAL.sunI);
sun.position.set(-30, 40, 25);
scene.add(sun);

// ---------------------------------------------------------------- 재료 도우미
const matCache = new Map();
function mat(color, opts = {}) {
  const key = color + JSON.stringify(opts);
  if (!matCache.has(key)) matCache.set(key, new THREE.MeshLambertMaterial({ color, flatShading: true, ...opts }));
  return matCache.get(key);
}
function box(w, h, d, color, x, y, z, parent = scene) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat(color));
  m.position.set(x, y, z); parent.add(m); return m;
}
function cyl(rt, rb, h, seg, color, x, y, z, parent = scene) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, seg), mat(color));
  m.position.set(x, y, z); parent.add(m); return m;
}
// 직사각형 지붕(사각 뿔대). w,d: 처마 폭/깊이, top: 꼭대기 비율
function roof(w, d, h, top, color, x, y, z, parent = scene) {
  const g = new THREE.CylinderGeometry(top, 1, h, 4, 1);
  g.rotateY(Math.PI / 4);
  const m = new THREE.Mesh(g, mat(color));
  m.scale.set(w / Math.SQRT2, 1, d / Math.SQRT2);
  m.position.set(x, y, z); parent.add(m); return m;
}
function textTexture(text, { w = 512, h = 128, font = "600 64px 'Noto Serif KR', serif", fg = "#e9c46a", bg = "#2a211c", radius = 10 } = {}) {
  const c = document.createElement("canvas"); c.width = w; c.height = h;
  const x = c.getContext("2d");
  if (bg) { x.fillStyle = bg; roundRect(x, 0, 0, w, h, radius); x.fill(); }
  x.fillStyle = fg; x.font = font; x.textAlign = "center"; x.textBaseline = "middle";
  x.fillText(text, w / 2, h / 2 + 2);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
  return t;
}
function roundRect(x, l, t, w, h, r) {
  x.beginPath(); x.moveTo(l + r, t); x.arcTo(l + w, t, l + w, t + h, r); x.arcTo(l + w, t + h, l, t + h, r);
  x.arcTo(l, t + h, l, t, r); x.arcTo(l, t, l + w, t, r); x.closePath();
}
const rand = (a, b) => a + Math.random() * (b - a);
let seed = 7;
const srand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);

// ---------------------------------------------------------------- 나무와 대나무
// 나무: 휘어진 줄기와 가지를 세우고, 가지 끝마다 '잎 뭉치 카드'(잎을 그린 반투명 판 네 장)를 붙인다.
// 잎 뭉치는 종류별로 한 번에 그린다(인스턴싱) — 수백 그루도 가볍다.
const flora = (() => {
  const R = (a, b) => a + Math.random() * (b - a);
  function leafTex(kind) {
    const c = document.createElement("canvas"); c.width = c.height = 128; const x = c.getContext("2d");
    if (kind === "needle") {                 // 솔잎·삼나무: 가운데서 사방으로 뻗은 가는 바늘
      for (let i = 0; i < 260; i++) {
        const a = R(0, Math.PI * 2), r0 = R(0, 16), r1 = R(28, 60), g = Math.floor(R(140, 255));
        x.strokeStyle = `rgb(${g},${g},${g})`; x.lineWidth = R(1, 2.4); x.beginPath();
        x.moveTo(64 + Math.cos(a) * r0, 64 + Math.sin(a) * r0 * 0.8); x.lineTo(64 + Math.cos(a) * r1, 64 + Math.sin(a) * r1 * 0.8); x.stroke();
      }
    } else if (kind === "grass") {           // 풀: 아래에서 위로 휘어 올라가는 잎
      for (let i = 0; i < 60; i++) {
        const bx = R(24, 104), h = R(50, 124), bend = R(-26, 26), g = Math.floor(R(140, 255));
        x.strokeStyle = `rgb(${g},${g},${g})`; x.lineWidth = R(1.5, 3.5); x.beginPath(); x.moveTo(bx, 128); x.quadraticCurveTo(bx + bend * 0.3, 128 - h * 0.6, bx + bend, 128 - h); x.stroke();
      }
    } else {                                 // 넓은 잎·꽃잎: 작은 잎을 겹쳐 둥글게, 가장자리는 성기게
      const petal = kind === "petal";
      for (let i = 0; i < 190; i++) {
        const a = R(0, Math.PI * 2), d = Math.pow(Math.random(), 0.65) * 54, g = Math.floor(R(150, 255));
        x.fillStyle = `rgb(${g},${g},${g})`; x.save(); x.translate(64 + Math.cos(a) * d, 64 + Math.sin(a) * d); x.rotate(R(0, Math.PI));
        x.beginPath(); x.ellipse(0, 0, petal ? R(3.5, 5.5) : R(5, 9), petal ? R(3, 4.5) : R(2.2, 3.8), 0, 0, Math.PI * 2); x.fill(); x.restore();
      }
    }
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; return t;
  }
  function cards(withTop) {
    const gs = [0, Math.PI / 3, (2 * Math.PI) / 3].map((r) => { const g = new THREE.PlaneGeometry(1, 1); g.rotateY(r); return g; });
    if (withTop) { const h = new THREE.PlaneGeometry(1, 1); h.rotateX(-Math.PI / 2); gs.push(h); }
    const pos = [], uv = [], nor = [], idx = []; let off = 0;
    gs.forEach((g) => { pos.push(...g.attributes.position.array); uv.push(...g.attributes.uv.array); nor.push(...g.attributes.normal.array);
      g.index.array.forEach((i) => idx.push(i + off)); off += g.attributes.position.count; });
    const m = new THREE.BufferGeometry();
    m.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3)); m.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2));
    m.setAttribute("normal", new THREE.Float32BufferAttribute(nor, 3)); m.setIndex(idx); return m;
  }
  const geoFull = cards(true), geoCross = cards(false), kinds = {}, barkM = {}, tmpC = new THREE.Color(), UP = new THREE.Vector3(0, 1, 0);
  const kind = (n) => kinds[n] || (kinds[n] = { tex: leafTex(n), items: [] });
  const bark = (c) => barkM[c] || (barkM[c] = new THREE.MeshLambertMaterial({ color: c }));
  function limb(a, b, r0, r1, col) {
    const d = new THREE.Vector3().subVectors(b, a), len = d.length();
    const m = new THREE.Mesh(new THREE.CylinderGeometry(r1, r0, len, 6, 1), bark(col));
    m.position.copy(a).addScaledVector(d, 0.5); m.quaternion.setFromUnitVectors(UP, d.normalize()); scene.add(m); return m;
  }
  function leaf(name, p, size, color, jit = 0.1) {
    tmpC.set(color).offsetHSL((Math.random() - 0.5) * 0.025, (Math.random() - 0.5) * 0.08, (Math.random() - 0.5) * jit);
    kind(name).items.push({ p: p.clone(), s: size * R(0.8, 1.2), r: Math.random() * Math.PI * 2, c: tmpC.clone() });
  }
  function finish() {
    const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), sc = new THREE.Vector3();
    Object.entries(kinds).forEach(([name, k]) => {
      if (!k.items.length) return;
      const mat = new THREE.MeshLambertMaterial({ map: k.tex, alphaTest: 0.5, side: THREE.DoubleSide });
      const im = new THREE.InstancedMesh(name === "grass" ? geoCross : geoFull, mat, k.items.length);
      k.items.forEach((it, i) => {
        e.set(name === "grass" ? 0 : (Math.random() - 0.5) * 0.5, it.r, name === "grass" ? 0 : (Math.random() - 0.5) * 0.5); q.setFromEuler(e);
        sc.set(it.s, it.s * (name === "needle" ? 0.8 : 1), it.s); m4.compose(it.p, q, sc); im.setMatrixAt(i, m4); im.setColorAt(i, it.c);
      });
      im.instanceMatrix.needsUpdate = true; im.instanceColor.needsUpdate = true; scene.add(im); k.items = [];
    });
  }
  return { limb, leaf, finish };
})();
const V3 = (x, y, z) => new THREE.Vector3(x, y, z);
const night = TIME === "night";
// 넓은 잎 나무 · 벚나무(kind: "petal")
function broadTree(x, z, s = 1, o = {}) {
  const y0 = o.y || 0, leafC = o.leaf || (night ? 0x2c4a34 : 0x55803f), barkC = o.bark || 0x4a3a30, kn = o.kind || "leaf";
  const top = V3(x + (srand() - 0.5) * 0.5 * s, y0 + (o.h || 2.3) * s, z + (srand() - 0.5) * 0.4 * s);
  const mid = V3((x + top.x) / 2 + (srand() - 0.5) * 0.2 * s, (y0 + top.y) / 2, (z + top.z) / 2);
  flora.limb(V3(x, y0, z), mid, 0.26 * s, 0.2 * s, barkC); flora.limb(mid, top, 0.2 * s, 0.14 * s, barkC);
  const n = o.branches || 5;
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2 + srand() * 0.8, up = 0.5 + srand() * 1.1, out = (1.3 + srand() * 1.0) * s * (o.spread || 1);
    const m = V3(top.x + Math.cos(a) * out * 0.5, top.y + up * 0.5 * s, top.z + Math.sin(a) * out * 0.5);
    const e = V3(top.x + Math.cos(a) * out, top.y + up * s - (o.weeping ? 0.8 * s : 0), top.z + Math.sin(a) * out);
    flora.limb(top, m, 0.11 * s, 0.07 * s, barkC); flora.limb(m, e, 0.07 * s, 0.035 * s, barkC);
    for (let k = 0; k < 7; k++) {
      const t = 0.3 + srand() * 0.8;
      flora.leaf(kn, V3(m.x + (e.x - m.x) * t + (srand() - 0.5) * 0.9 * s, m.y + (e.y - m.y) * t + (srand() - 0.3) * 0.7 * s - (o.weeping ? srand() * 0.9 * s : 0),
        m.z + (e.z - m.z) * t + (srand() - 0.5) * 0.9 * s), (1.0 + srand() * 0.5) * s, leafC);
    }
  }
  for (let k = 0; k < 14; k++) {                              // 수관 위쪽 채우기 (위는 조금 밝게)
    const a = srand() * Math.PI * 2, r = Math.sqrt(srand()) * 1.6 * s * (o.spread || 1), up = (0.5 + srand() * 1.3) * s;
    flora.leaf(kn, V3(top.x + Math.cos(a) * r, top.y + up, top.z + Math.sin(a) * r), (1.1 + srand() * 0.5) * s, new THREE.Color(leafC).offsetHSL(0, 0, up / s * 0.03 - 0.02));
  }
}
// 해송: 비스듬히 휜 줄기, 옆으로 뻗은 가지 끝에 납작한 솔잎 방석
function pineTree(x, z, s = 1, o = {}) {
  const y0 = o.y || 0, leafC = o.leaf || (night ? 0x213a2a : 0x3b6a44), barkC = 0x5a463a;
  const la = srand() * Math.PI * 2, lean = (0.5 + srand() * 0.8) * s, pts = [V3(x, y0, z)];
  for (let i = 1; i <= 4; i++) {
    const t = i / 4, p = V3(x + Math.cos(la) * lean * t + Math.sin(t * 5 + x) * 0.15 * s, y0 + t * 4.3 * s, z + Math.sin(la) * lean * t);
    flora.limb(pts[i - 1], p, (0.26 - 0.045 * i) * s, (0.22 - 0.045 * i) * s, barkC); pts.push(p);
  }
  const pad = (c, r) => { for (let k = 0; k < 10; k++) { const a = srand() * Math.PI * 2, d = Math.sqrt(srand()) * r;
    flora.leaf("needle", V3(c.x + Math.cos(a) * d, c.y + (srand() - 0.3) * 0.22 * r, c.z + Math.sin(a) * d), (0.75 + srand() * 0.3) * s, leafC); } };
  pts.slice(2).forEach((p, i) => {
    const nb = 2 + Math.floor(srand() * 2);
    for (let b = 0; b < nb; b++) {
      const a = srand() * Math.PI * 2, L = (1.0 + srand() * 1.3) * s * (1 - i * 0.18);
      const e = V3(p.x + Math.cos(a) * L, p.y + (srand() * 0.4 - 0.1) * s, p.z + Math.sin(a) * L);
      flora.limb(p, e, 0.07 * s, 0.03 * s, barkC); pad(e, (0.8 + srand() * 0.4) * s);
    }
  });
  pad(V3(pts[4].x, pts[4].y + 0.2 * s, pts[4].z), 1.3 * s);
}
// 삼나무: 곧은 줄기, 위로 갈수록 좁아지는 층층 솔잎 (snow: 눈이 얹힘)
function cedarTree(x, z, s = 1, o = {}) {
  const y0 = o.y || 0, H = (6 + srand() * 2) * s, leafC = o.leaf || (night ? 0x1f3226 : 0x3a6044);
  flora.limb(V3(x, y0, z), V3(x, y0 + H, z), 0.28 * s, 0.05 * s, 0x4a3628);
  for (let y = 1.5 * s; y < H; y += 0.42 * s) {
    const t = y / H, Rr = (1 - t) * 1.9 * s + 0.25 * s, n = Math.max(3, Math.round(Rr * 5));
    for (let k = 0; k < n; k++) {
      const a = (k / n) * Math.PI * 2 + srand() * 0.6, d = Rr * (0.55 + srand() * 0.45);
      flora.leaf("needle", V3(x + Math.cos(a) * d, y0 + y - d * 0.25, z + Math.sin(a) * d), (0.9 + Rr * 0.35) * (0.8 + srand() * 0.3),
        o.snow && srand() < 0.4 ? 0xe9edf4 : leafC);
    }
  }
  flora.leaf("needle", V3(x, y0 + H + 0.2 * s, z), 0.8 * s, leafC);
}
// 덤불 · 풀숲
function bush(x, z, s = 1, o = {}) {
  const y0 = o.y || 0, c = o.leaf || (night ? 0x2e4430 : 0x5f8f3e);
  for (let k = 0; k < 6; k++) { const a = srand() * Math.PI * 2, d = srand() * 0.6 * s; flora.leaf("leaf", V3(x + Math.cos(a) * d, y0 + (0.3 + srand() * 0.4) * s, z + Math.sin(a) * d), (0.8 + srand() * 0.4) * s, c); }
}
function grass(x, z, s = 1, o = {}) {
  flora.leaf("grass", V3(x, (o.y || 0) + 0.5 * s, z), s, o.leaf || (night ? 0x3a4e34 : 0x7aa652), 0.14);
}
const cedar = (x, z, s = 1) => cedarTree(x, z, s);
function bamboo(x, z) {
  const col = TIME === "night" ? 0x37503a : 0x7a9a5a;
  for (let i = 0; i < 7; i++) {
    const h = 5 + srand() * 4, bx = x + (srand() - 0.5) * 2, bz = z + (srand() - 0.5) * 2;
    const b = cyl(0.07, 0.09, h, 5, col, bx, h / 2, bz); b.rotation.z = (srand() - 0.5) * 0.12;
    for (let k = 0; k < 5; k++) flora.leaf("leaf", V3(bx + (srand() - 0.5) * 1.0, h - 1.6 + k * 0.4, bz + (srand() - 0.5) * 1.0), 0.8 + srand() * 0.4, TIME === "night" ? 0x2a3d2c : 0x6a9a4e);
  }
}

// ---------------------------------------------------------------- 장소 짓기
const trees = { broad: broadTree, pine: pineTree, cedar: cedarTree, bush, grass };
const K = { THREE, scene, camera, TIME, PAL, mat, box, cyl, roof, textTexture, rand, srand, cedar, bamboo, trees, reduceMotion, isTouch };
const P = PLACE.build(K);
flora.finish();
// 카메라가 벽·기둥·천장 속으로 들어가지 않게, 장소의 큰 물체를 '가림막'으로 모아 둔다 (작은 소품·잎·투명한 것은 뺀다)
const occluders = [];
scene.traverse((o) => {
  if (!o.isMesh || o.isInstancedMesh || o.userData.noOcclude) return;
  const m = o.material; if (!m || m.transparent || m.side === THREE.BackSide) return;
  if (!o.geometry.boundingSphere) o.geometry.computeBoundingSphere();
  const sc = Math.max(o.scale.x, o.scale.y, o.scale.z);
  if (o.geometry.boundingSphere.radius * sc < 0.55) return;
  occluders.push(o);
});
const occRay = new THREE.Raycaster();
const shown = (o) => { for (let x = o; x; x = x.parent) if (!x.visible) return false; return true; };
const heightAt = P.heightAt;
const SEATS = P.seats;
const fliesArea = P.fliesArea || [-16, 16, -2, 20];

// ---------------------------------------------------------------- 반딧불 (해 질 녘·밤)
let flies;
if (TIME !== "day" && !reduceMotion && P.fireflies !== false) {
  const n = 60, p = new Float32Array(n * 3), base = [];
  for (let i = 0; i < n; i++) {
    const v = [rand(fliesArea[0], fliesArea[1]), rand(0.5, 3.5), rand(fliesArea[2], fliesArea[3])];
    base.push(v); p.set(v, i * 3);
  }
  const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(p, 3));
  flies = new THREE.Points(g, new THREE.PointsMaterial({ color: 0xfff1a6, size: 0.14, transparent: true, opacity: 0.9, depthWrite: false, blending: THREE.AdditiveBlending }));
  flies.userData.base = base; scene.add(flies);
}

// ---------------------------------------------------------------- 캐릭터
function nameSprite(text, me, cap) {
  if (cap) return capSprite(text, me, cap);
  const t = textTexture(text, { w: 384, h: 96, font: "600 40px 'Noto Sans KR', sans-serif", fg: me ? "#fff" : "#2a2622", bg: me ? "rgba(30,28,24,0.82)" : "rgba(255,252,246,0.86)", radius: 48 });
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, depthTest: false, transparent: true }));
  s.scale.set(1.5, 0.375, 1); s.position.y = 1.72; s.renderOrder = 10; return s;
}
// ---------------------------------------------------------------- 열공 단계 효과
// 집중이 길어질수록: 5분 발밑 온기 → 15분 어깨 위로 오르는 불티 → 40분 등 뒤 불꽃 → 80분 푸른 불꽃
const FOCUS_STAGES = [5, 15, 40, 80];
const stageFor = (min) => FOCUS_STAGES.reduce((n, m) => (min >= m ? n + 1 : n), 0);
const glowTex = (() => {
  const c = document.createElement("canvas"); c.width = c.height = 128; const x = c.getContext("2d");
  const g = x.createRadialGradient(64, 64, 4, 64, 64, 62); g.addColorStop(0, "rgba(255,214,140,0.95)"); g.addColorStop(0.45, "rgba(255,150,60,0.45)"); g.addColorStop(1, "rgba(255,120,40,0)");
  x.fillStyle = g; x.fillRect(0, 0, 128, 128); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
})();
const flameTex = (() => {
  // 아래는 둥글고 위로 갈수록 가늘게 갈라지는 불꽃 한 장: 바깥은 진하고 안쪽은 밝게
  const c = document.createElement("canvas"); c.width = 128; c.height = 256; const x = c.getContext("2d");
  const shape = (k) => { x.beginPath(); x.moveTo(64, 8 + 20 * (1 - k)); x.bezierCurveTo(64 + 46 * k, 70, 64 + 60 * k, 150, 64 + 52 * k, 196); x.bezierCurveTo(64 + 40 * k, 244, 64 - 40 * k, 244, 64 - 52 * k, 196); x.bezierCurveTo(64 - 60 * k, 150, 64 - 46 * k, 70, 64, 8 + 20 * (1 - k)); x.closePath(); };
  let g = x.createLinearGradient(0, 250, 0, 0); g.addColorStop(0, "rgba(255,255,255,0.0)"); g.addColorStop(0.18, "rgba(255,255,255,0.9)"); g.addColorStop(0.75, "rgba(255,255,255,0.75)"); g.addColorStop(1, "rgba(255,255,255,0)");
  shape(1); x.fillStyle = g; x.globalAlpha = 0.85; x.fill();
  // 가운데 밝은 심지 (색을 곱해도 밝게 남도록 거의 흰색)
  shape(0.5); g = x.createRadialGradient(64, 190, 4, 64, 170, 90); g.addColorStop(0, "rgba(255,255,255,1)"); g.addColorStop(1, "rgba(255,255,255,0.15)");
  x.globalAlpha = 1; x.fillStyle = g; x.fill();
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
})();
const _away = new THREE.Vector3(), _side = new THREE.Vector3();
const auraTex = (() => {
  // 가운데는 비고 테두리 쪽이 밝은 세로 타원: 캐릭터 둘레로 '기운'이 비치는 모양
  const c = document.createElement("canvas"); c.width = 128; c.height = 256; const x = c.getContext("2d");
  x.translate(64, 140); x.scale(1, 1.9);
  const g = x.createRadialGradient(0, 0, 0, 0, 0, 62); g.addColorStop(0, "rgba(255,255,255,0.15)"); g.addColorStop(0.62, "rgba(255,255,255,0.5)"); g.addColorStop(0.8, "rgba(255,255,255,0.95)"); g.addColorStop(1, "rgba(255,255,255,0)");
  x.fillStyle = g; x.beginPath(); x.arc(0, 0, 62, 0, Math.PI * 2); x.fill();
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
})();
// 40분 이후 등 뒤 불꽃. 시안: a 불길(입자) · b 만화 오라(셰이더) · c 은은한 기운
const FLAME_STYLE = (new URLSearchParams(location.search).get("flame") || "b").slice(0, 1);
const RAMP_HOT = [[1, 0.8, 0.28], [1, 0.48, 0.1], [0.84, 0.18, 0.05], [0.48, 0.07, 0.03]];
const RAMP_BLUE = [[0.55, 0.82, 1], [0.28, 0.55, 1], [0.14, 0.28, 0.9], [0.08, 0.1, 0.45]];
function rampAt(r, k) { const i = Math.min(r.length - 2, Math.floor(k * (r.length - 1))), f = k * (r.length - 1) - i; return r[i].map((v, j) => v + (r[i + 1][j] - v) * f); }
function makeFire(style) {
  if (style === "b") {
    const mat = new THREE.ShaderMaterial({
      transparent: true, depthWrite: false,
      uniforms: { uT: { value: 0 }, uA: { value: new THREE.Color() }, uB: { value: new THREE.Color() }, uC: { value: new THREE.Color() }, uO: { value: 0 } },
      vertexShader: "varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }",
      fragmentShader: `varying vec2 vUv; uniform float uT, uO; uniform vec3 uA, uB, uC;
        float h(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
        float n(vec2 p){ vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
          return mix(mix(h(i), h(i + vec2(1, 0)), f.x), mix(h(i + vec2(0, 1)), h(i + vec2(1, 1)), f.x), f.y); }
        float fbm(vec2 p){ float v = 0.0, a = 0.5; for (int k = 0; k < 4; k++) { v += a * n(p); p *= 2.03; a *= 0.5; } return v; }
        void main(){
          vec2 u = vUv; float x = abs(u.x - 0.5) * 2.0, y = u.y;
          float nz = fbm(vec2(u.x * 3.2, y * 2.2 - uT * 1.7)) + 0.5 * fbm(vec2(u.x * 7.0 + 3.0, y * 4.0 - uT * 3.1));
          float f = 1.0 - x * (1.15 + 0.9 * y) - y * 0.95 + (nz - 0.62) * 0.95;
          f *= smoothstep(0.0, 0.12, y);
          if (f < 0.06) discard;
          vec3 c = f > 0.5 ? uA : f > 0.26 ? uB : uC;
          float a = smoothstep(0.06, 0.1, f) * uO;
          gl_FragColor = vec4(c, a);
        }` });
    const m = new THREE.Mesh(new THREE.PlaneGeometry(2.3, 3.1), mat); m.renderOrder = 1; scene.add(m);
    return {
      parts: [m],
      update(av, dt, n, on) {
        mat.uniforms.uT.value = reduceMotion ? 0.5 : av.t;
        const r = n >= 4 ? RAMP_BLUE : RAMP_HOT;
        mat.uniforms.uA.value.setRGB(...r[0]); mat.uniforms.uB.value.setRGB(...r[1]); mat.uniforms.uC.value.setRGB(...r[2]);
        mat.uniforms.uO.value += ((on ? 0.95 : 0) - mat.uniforms.uO.value) * Math.min(1, dt * 2.5);
        m.visible = mat.uniforms.uO.value > 0.01;
        m.quaternion.copy(camera.quaternion);
        const big = n >= 4 ? 1.18 : 1; m.scale.set(big, big, 1);
        m.position.copy(av.g.position).addScaledVector(_away, 0.45); m.position.y += av.upper.position.y + 1.45 * big - 0.15;
      } };
  }
  // a: 작은 불덩이가 계속 피어오르는 불길 / c: 등 뒤가 은은하게 빛나고 가는 불줄기가 천천히
  const calm = style === "c", N = calm ? 16 : 54, sprites = [];
  for (let i = 0; i < N; i++) {
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: flameTex, transparent: true, depthWrite: false, opacity: 0 }));
    sp.visible = false; sp.renderOrder = 1; sp.userData = { life: 0, total: 1, x: 0, y: 0, vx: 0, vy: 0, s: 1 }; scene.add(sp); sprites.push(sp);
  }
  let halo = null;
  if (calm) { halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: auraTex, transparent: true, depthWrite: false, opacity: 0 })); halo.renderOrder = 0; scene.add(halo); }
  let level = 0, acc = 0;
  return {
    parts: halo ? sprites.concat([halo]) : sprites,
    update(av, dt, n, on) {
      level += ((on ? 1 : 0) - level) * Math.min(1, dt * 2.5);
      const ramp = n >= 4 ? RAMP_BLUE : RAMP_HOT, big = n >= 4 ? 1.2 : 1;
      const base = av.g.position, y0 = base.y + av.upper.position.y;
      if (halo) {
        halo.visible = level > 0.01; halo.material.opacity = level * (0.85 + (reduceMotion ? 0 : Math.sin(av.t * 1.6) * 0.1));
        halo.material.color.setRGB(...rampAt(ramp, 0.2)); halo.scale.set(2.5 * big, 3.3 * big, 1);
        halo.position.copy(base).addScaledVector(_away, 0.55); halo.position.y = y0 + 1.05;
      }
      acc = Math.min(4, acc + (on ? (calm ? 6 : 58) : 0) * dt);
      sprites.forEach((sp) => {
        const u = sp.userData;
        if (u.life <= 0) {
          if (!on || acc < 1) { sp.visible = false; return; }
          acc -= 1;
          u.x = (Math.random() - 0.5) * (calm ? 1.2 : 1.35) * big; u.y = calm ? 0.4 + Math.random() * 0.5 : 0.2 + Math.random() * 0.5;
          u.vx = -u.x * (calm ? 0.15 : 0.6); u.vy = calm ? 0.45 + Math.random() * 0.3 : 1.5 + Math.random() * 0.9;
          u.total = u.life = calm ? 2.6 + Math.random() * 1.2 : 0.7 + Math.random() * 0.45; u.s = calm ? 1.4 + Math.random() * 0.6 : 0.8 + Math.random() * 0.45;
        }
        u.life -= dt; const k = 1 - Math.max(0, u.life) / u.total;
        u.x += (u.vx + (reduceMotion ? 0 : Math.sin(av.t * 6 + u.s * 9) * (calm ? 0.05 : 0.18))) * dt; u.y += u.vy * dt * big;
        sp.visible = level > 0.01;
        sp.material.color.setRGB(...rampAt(ramp, calm ? 0.15 + k * 0.5 : 0.12 + k * 0.85));
        sp.material.opacity = level * (calm ? Math.sin(k * Math.PI) * 0.9 : (k < 0.12 ? k / 0.12 : 1 - (k - 0.12) / 0.88) * 0.95);
        const sz = calm ? u.s * (0.35 + 0.15 * Math.sin(k * Math.PI)) : u.s * (1 - k * 0.65) * big;
        if (calm) sp.scale.set(sz * 0.55, sz * 1.6, 1); else sp.scale.set(sz * 0.8, sz * 1.5, 1);
        sp.position.copy(base).addScaledVector(_away, 0.5).addScaledVector(_side, u.x); sp.position.y = y0 + u.y;
      });
    } };
}

// 조교·선생님 이름표: 초록 캡션 + 본명
function capSprite(text, me, cap) {
  const c = document.createElement("canvas"); c.width = 384; c.height = 96; const x = c.getContext("2d");
  const rr = (x0, y0, w, h, r) => { x.beginPath(); x.moveTo(x0 + r, y0); x.arcTo(x0 + w, y0, x0 + w, y0 + h, r); x.arcTo(x0 + w, y0 + h, x0, y0 + h, r); x.arcTo(x0, y0 + h, x0, y0, r); x.arcTo(x0, y0, x0 + w, y0, r); x.fill(); };
  x.font = "700 30px 'Noto Sans KR', sans-serif"; const cw = x.measureText(cap).width + 26;
  x.font = "600 40px 'Noto Sans KR', sans-serif"; const nw = Math.min(384 - cw - 44, x.measureText(text).width);
  const W = Math.min(384, cw + nw + 44), X = (384 - W) / 2;
  x.fillStyle = me ? "rgba(30,28,24,0.82)" : "rgba(255,252,246,0.9)"; rr(X, 4, W, 88, 44);
  x.fillStyle = "#2c6852"; rr(X + 12, 22, cw, 52, 14);
  x.fillStyle = "#fff"; x.font = "700 30px 'Noto Sans KR', sans-serif"; x.textBaseline = "middle"; x.textAlign = "center"; x.fillText(cap, X + 12 + cw / 2, 49);
  x.fillStyle = me ? "#fff" : "#2a2622"; x.font = "600 40px 'Noto Sans KR', sans-serif"; x.textAlign = "left"; x.fillText(text, X + 22 + cw, 50, nw);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, depthTest: false, transparent: true }));
  s.scale.set(1.5, 0.375, 1); s.position.y = 1.72; s.renderOrder = 10; return s;
}
// 동자 수험생: 큰 얼굴, 털모자(방울), 목도리, 책가방. 모자·목도리·장갑이 학생이 고른 색
const SKIN = 0xf6d3b8, INK = 0x2a2420;
const toon = (c, o = {}) => new THREE.MeshToonMaterial({ color: c, ...o });
const sharedM = { robe: toon(0xeee4d2), skin: toon(SKIN), pom: toon(0xfff7ec), bag: toon(0x8a6a4f), bagTop: toon(0x6d523c), shoe: toon(0x5a4a3e),
  eye: new THREE.MeshBasicMaterial({ color: INK }), shine: new THREE.MeshBasicMaterial({ color: 0xffffff }),
  blush: new THREE.MeshBasicMaterial({ color: 0xf3a08e, transparent: true, opacity: 0.65 }) };
const crownM = new THREE.MeshToonMaterial({ color: 0xf0c040 });
function part(g, m, x, y, z, parent) { const o = new THREE.Mesh(g, m); o.position.set(x, y, z); parent.add(o); return o; }
// 입김: 하얀 구름이 입 앞에서 몽글 피어올라 사라진다
const puffTex = (() => {
  const c = document.createElement("canvas"); c.width = c.height = 64; const x = c.getContext("2d");
  const gr = x.createRadialGradient(32, 32, 2, 32, 32, 30); gr.addColorStop(0, "rgba(255,255,255,0.95)"); gr.addColorStop(0.6, "rgba(255,255,255,0.55)"); gr.addColorStop(1, "rgba(255,255,255,0)");
  x.fillStyle = gr; x.fillRect(0, 0, 64, 64); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
})();
const puffs = [];
function spawnPuff(av) {
  let p = puffs.find((q) => q.life <= 0);
  if (!p) { if (puffs.length > 24) return; p = { s: new THREE.Sprite(new THREE.SpriteMaterial({ map: puffTex, transparent: true, depthWrite: false })) }; scene.add(p.s); puffs.push(p); }
  const f = new THREE.Vector3(Math.sin(av.yaw), 0, Math.cos(av.yaw));
  p.s.position.set(av.g.position.x + f.x * 0.55, av.g.position.y + av.upper.position.y + 1.0, av.g.position.z + f.z * 0.55);
  p.v = f.multiplyScalar(0.45).add(new THREE.Vector3((Math.random() - 0.5) * 0.12, 0.16, (Math.random() - 0.5) * 0.12));
  p.life = p.total = 1.8; p.s.visible = true;
}
function updatePuffs(dt) {
  puffs.forEach((p) => {
    if (p.life <= 0) return; p.life -= dt;
    const k = 1 - Math.max(0, p.life) / p.total;
    p.s.position.addScaledVector(p.v, dt); p.s.scale.setScalar(0.12 + k * 0.32);
    p.s.material.opacity = Math.sin(Math.min(1, k * 1.4) * Math.PI) * 0.75;
    if (p.life <= 0) p.s.visible = false;
  });
}
class Avatar {
  constructor({ color, nick, cap = null, me = false }) {
    this.me = me; this.g = new THREE.Group(); this.upper = new THREE.Group(); this.g.add(this.upper);
    this.colorMat = toon(color); this.rimMat = toon(new THREE.Color(color).offsetHSL(0, 0, 0.18));
    const U = this.upper;
    part(new THREE.CylinderGeometry(0.3, 0.44, 0.62, 20), sharedM.robe, 0, 0.42, 0, U);
    const scarf = part(new THREE.TorusGeometry(0.24, 0.085, 10, 20), this.colorMat, 0, 0.74, 0, U); scarf.rotation.x = Math.PI / 2;
    const tail = part(new THREE.BoxGeometry(0.12, 0.28, 0.06), this.colorMat, 0.14, 0.58, 0.27, U); tail.rotation.z = 0.15;
    this.head = part(new THREE.SphereGeometry(0.48, 28, 20), sharedM.skin, 0, 1.16, 0, U);
    const hat = part(new THREE.SphereGeometry(0.5, 28, 14, 0, Math.PI * 2, 0, Math.PI * 0.5), this.colorMat, 0, 1.22, 0, U); hat.scale.y = 0.95;
    const rim = part(new THREE.TorusGeometry(0.47, 0.07, 10, 28), this.rimMat, 0, 1.24, 0, U); rim.rotation.x = Math.PI / 2;
    this.pom = part(new THREE.SphereGeometry(0.12, 14, 10), sharedM.pom, 0, 1.74, 0, U);
    this.eyes = [];
    for (const sd of [-1, 1]) {
      const e = part(new THREE.SphereGeometry(0.058, 12, 8), sharedM.eye, sd * 0.15, 1.08, 0.45, U); e.scale.set(1, 1.25, 0.6); this.eyes.push(e);
      part(new THREE.SphereGeometry(0.016, 6, 4), sharedM.shine, sd * 0.15 + 0.015, 1.105, 0.48, U);
      const bl = part(new THREE.CircleGeometry(0.06, 14), sharedM.blush, sd * 0.25, 1.0, 0.44, U); bl.lookAt(sd * 1, 1.0, 3);
    }
    const mouth = part(new THREE.TorusGeometry(0.035, 0.011, 6, 12, Math.PI), sharedM.eye, 0, 1.01, 0.46, U); mouth.rotation.z = Math.PI; this.mouth = mouth;
    this.oh = part(new THREE.TorusGeometry(0.03, 0.012, 6, 14), sharedM.eye, 0, 1.0, 0.465, U); this.oh.visible = false;   // 숨 내쉴 때 '후-' 입
    this.breathT = -1; this.puffT = 0;
    part(new THREE.BoxGeometry(0.42, 0.42, 0.18), sharedM.bag, 0, 0.5, -0.38, U);
    part(new THREE.BoxGeometry(0.44, 0.12, 0.2), sharedM.bagTop, 0, 0.66, -0.38, U);
    this.hands = [-1, 1].map((sd) => { const h = part(new THREE.SphereGeometry(0.1, 12, 8), this.colorMat, sd * 0.42, 0.42, 0.06, U); h.userData.side = sd; return h; });
    this.feet = [-1, 1].map((sd) => { const f = part(new THREE.SphereGeometry(0.11, 12, 8), sharedM.shoe, sd * 0.15, 0.06, 0.08, this.g); f.scale.set(1, 0.6, 1.4); f.userData.side = sd; return f; });
    const shadow = new THREE.Mesh(new THREE.CircleGeometry(0.5, 20), new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.16, depthWrite: false }));
    shadow.rotation.x = -Math.PI / 2; shadow.position.y = 0.02; this.g.add(shadow);
    this.ring = new THREE.Mesh(new THREE.RingGeometry(0.55, 0.68, 32), new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.0, depthWrite: false, side: THREE.DoubleSide }));
    this.ring.rotation.x = -Math.PI / 2; this.ring.position.y = 0.04; this.g.add(this.ring);
    this.tag = nameSprite(nick, me, cap); this.tag.position.y = 2.15; this.g.add(this.tag);
    this.pos = new THREE.Vector3(); this.path = []; this.yaw = 0; this.pose = "stand"; this.t = Math.random() * 10;
    this.focus = false; this.seat = null; this.bowT = 0; this.speed = me ? 3.6 : 3.8;
    scene.add(this.g);
  }
  setColor(c) { this.colorMat.color.set(c); this.rimMat.color.set(new THREE.Color(c).offsetHSL(0, 0, 0.18)); this.ring.material.color.set(c); }
  place(x, z, yaw) { this.pos.set(x, heightAt(x, z), z); if (yaw !== undefined) this.yaw = yaw; this.path = []; }
  walkTo(points) { this.path = points.map(([x, z]) => new THREE.Vector3(x, 0, z)); if (this.pose !== "walk") this.pose = "walk"; }
  get moving() { return this.path.length > 0; }
  update(dt) {
    this.t += dt;
    if (this.path.length) {
      const tgt = this.path[0], dx = tgt.x - this.pos.x, dz = tgt.z - this.pos.z, d = Math.hypot(dx, dz);
      const step = this.speed * dt;
      if (d <= step) { this.pos.x = tgt.x; this.pos.z = tgt.z; this.path.shift(); if (!this.path.length && this.pose === "walk") { this.pose = "stand"; this.onArrive && this.onArrive(); } }
      else { this.pos.x += (dx / d) * step; this.pos.z += (dz / d) * step; this.targetYaw = Math.atan2(dx, dz); }
    }
    if (this.targetYaw !== undefined) {
      let dy = this.targetYaw - this.yaw; dy = Math.atan2(Math.sin(dy), Math.cos(dy)); this.yaw += dy * Math.min(1, dt * 10);
    }
    const ground = heightAt(this.pos.x, this.pos.z);
    const sitting = (this.seat !== null && this.pose !== "walk") || this.pose === "sit";
    const seatInfo = this.seat !== null ? SEATS[this.seat] : null;
    const lift = sitting ? (seatInfo && seatInfo.lift !== undefined ? seatInfo.lift : 0.16) : 0;
    this.g.position.set(this.pos.x, (sitting && seatInfo && seatInfo.y !== undefined ? seatInfo.y : ground) + lift, this.pos.z);
    this.g.rotation.y = this.yaw;
    // 몸짓
    const walk = this.pose === "walk";
    const bob = walk && !reduceMotion ? Math.abs(Math.sin(this.t * 11)) * 0.07 : 0;
    this.upper.position.y = (sitting ? -0.06 : 0) + bob;
    this.upper.rotation.z = walk && !reduceMotion ? Math.sin(this.t * 11) * 0.05 : 0;
    const breathe = this.focus && !reduceMotion ? 1 + Math.sin(this.t * (Math.PI * 2 / 6)) * 0.025 : 1;
    this.upper.scale.set(breathe, sitting ? 0.92 : 1, breathe);
    this.breatheMotion(dt);
    // 절: 잠깐 앞으로 숙였다 돌아옴
    if (this.bowT > 0) { this.bowT -= dt; const k = Math.sin(Math.min(1, (1.6 - this.bowT) / 1.6) * Math.PI); this.upper.rotation.x = k * 0.75; if (this.bowT <= 0) { this.upper.rotation.x = 0; if (this.pose === "bow") this.pose = this.seat !== null ? "sit" : "stand"; } }
    const gassho = this.pose === "gassho" || this.pose === "bow";
    const ph = this.t * 11;
    this.hands.forEach((h) => {
      const s = h.userData.side;
      if (gassho) h.position.set(s * 0.05, 0.66, 0.4);
      else if (sitting) h.position.set(s * 0.18, 0.36, 0.32);
      else h.position.set(s * 0.42, 0.42 + (walk ? Math.sin(ph + (s > 0 ? Math.PI : 0)) * 0.04 : 0), walk ? Math.sin(ph + (s > 0 ? 0 : Math.PI)) * 0.14 : 0.06);
    });
    this.gestureMotion(dt);
    this.feet.forEach((f) => {
      const s = f.userData.side;
      if (sitting) { f.position.set(s * 0.22, 0.02, 0.3); f.rotation.y = -s * 1.1; }
      else { const sw = walk && !reduceMotion ? Math.sin(ph + (s > 0 ? Math.PI : 0)) : 0;
        f.position.set(s * 0.15, 0.06 + Math.max(0, sw) * 0.07, 0.08 + sw * 0.12); f.rotation.y = 0; }
    });
    if (!reduceMotion) this.pom.position.x = Math.sin(this.t * (walk ? 11 : 1.5)) * (walk ? 0.03 : 0.01);
    if (this.me) this.tag.visible = this.seat === null;
    if (this.timer && this.timer.visible) { this.timer.position.y = this.tag.position.y + 0.48; this.drawFocusTimer(); }
    const ringTarget = this.focus ? 0.55 + Math.sin(this.t * 2) * 0.15 : 0;
    this.ring.material.opacity += (ringTarget - this.ring.material.opacity) * Math.min(1, dt * 3);
    this.focusFx(dt);
  }
  // 숨 고르기: 4초 들이쉬며 어깨가 살짝 올라가고 고개가 뒤로, 2초 멈춤(눈 감음), 6초 '후-' 하고 입김을 내쉰다
  breatheMotion(dt) {
    const on = this.pose === "breathe" && !reduceMotion;
    if (!on) {
      if (this.breathT >= 0) { this.breathT = -1; this.eyes.forEach((e) => e.scale.set(1, 1.25, 0.6)); this.mouth.visible = true; this.oh.visible = false; this.upper.rotation.x = 0; }
      return;
    }
    if (this.breathT < 0) this.breathT = 0;
    this.breathT += dt;
    const c = this.breathT % 12, ease = (x) => 0.5 - Math.cos(Math.PI * x) / 2;
    const k = c < 4 ? ease(c / 4) : c < 6 ? 1 : 1 - ease((c - 6) / 6);
    this.upper.position.y += k * 0.06;
    this.upper.scale.x *= 1 + k * 0.05; this.upper.scale.z *= 1 + k * 0.05; this.upper.scale.y *= 1 + k * 0.04;
    this.upper.rotation.x = -k * 0.12;
    const shut = c > 3.2 ? 0.18 : 1.25;                 // 들이쉬기 끝부터 눈을 꼭 감는다 (^ ^)
    this.eyes.forEach((e) => { e.scale.y += (shut - e.scale.y) * Math.min(1, dt * 10); });
    const exhale = c >= 6 && c < 10.5;
    this.mouth.visible = !exhale; this.oh.visible = exhale;
    if (exhale) { this.oh.scale.setScalar(0.9 + Math.sin(this.breathT * 9) * 0.12); this.puffT -= dt; if (this.puffT <= 0) { spawnPuff(this); this.puffT = 0.55; } }
  }
  bow() { this.pose = "bow"; this.bowT = 1.6; }
  // 짧은 몸짓: splash(두 손으로 물 쳐 올리기), sip(찻잔을 들어 후- 불고 한 모금, 내려놓기)
  gesture(name, secs) { this.gName = name; this.gT = 0; this.gDur = secs; }
  gestureMotion(dt) {
    if (!this.gName) { if (this.cup) this.cup.visible = false; return; }
    this.gT += dt; const k = Math.min(1, this.gT / this.gDur), ease = (x) => 0.5 - Math.cos(Math.PI * Math.min(1, Math.max(0, x))) / 2;
    const [L, Rh] = this.hands;
    if (this.gName === "splash") {
      const w = Math.sin(k * Math.PI);                        // 앞으로 낮게 → 위로 쳐 올림
      L.position.set(-0.16, 0.3 + w * 0.34, 0.36 + w * 0.12); Rh.position.set(0.16, 0.3 + w * 0.34, 0.36 + w * 0.12);
      this.upper.rotation.x = 0.25 * Math.sin(k * Math.PI);
    } else if (this.gName === "sip") {
      if (!this.cup) {                                           // 손에 드는 나무 찻잔 + 김
        const c = new THREE.Group();
        const body = new THREE.Mesh(new THREE.CylinderGeometry(0.075, 0.06, 0.12, 16), toon(0xc89a6a)); c.add(body);
        const tea = new THREE.Mesh(new THREE.CircleGeometry(0.066, 16), toon(0x3a2418)); tea.rotation.x = -Math.PI / 2; tea.position.y = 0.055; c.add(tea);
        const plate = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.1, 0.015, 18), toon(0xe9dcc6)); plate.position.y = -0.065; c.add(plate);
        this.steam = [0, 1, 2].map((i) => { const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: puffTex, transparent: true, depthWrite: false, opacity: 0 })); sp.scale.setScalar(0.08); c.add(sp); return sp; });
        this.upper.add(c); this.cup = c;
      }
      this.cup.visible = true;
      // 0~0.25 찻잔을 들어 올림, 0.25~0.45 후- 불기, 0.45~0.75 한 모금(고개 뒤로), 0.75~1 내려놓기
      const up = k < 0.25 ? ease(k / 0.25) : k < 0.75 ? 1 : 1 - ease((k - 0.75) / 0.25);
      const drink = k > 0.45 && k < 0.75 ? Math.sin(((k - 0.45) / 0.3) * Math.PI) : 0;
      Rh.position.set(0.08 + 0.1 * (1 - up), 0.4 + up * 0.52, 0.32 + up * 0.14);
      L.position.set(-0.05 - 0.1 * (1 - up), 0.36 + up * 0.48, 0.34 + up * 0.12);
      this.cup.position.set(0.02, Rh.position.y + 0.07, Rh.position.z + 0.02); this.cup.rotation.x = -drink * 0.7;
      this.head.rotation.x = -drink * 0.18; this.upper.rotation.x = -drink * 0.06;
      const blow = k > 0.25 && k < 0.45;
      this.mouth.visible = !blow && !drink; this.oh.visible = blow;
      this.steam.forEach((sp, i) => { const t = (this.gT * 0.8 + i / 3) % 1; sp.position.set(Math.sin(t * 6 + i) * 0.02, 0.1 + t * 0.25, (blow ? 0.05 + t * 0.2 : 0)); sp.material.opacity = (1 - t) * 0.55 * (1 - drink); sp.scale.setScalar(0.06 + t * 0.12); });
    }
    if (k >= 1) { this.gName = null; this.upper.rotation.x = 0; this.head.rotation.x = 0; this.mouth.visible = true; this.oh.visible = false; if (this.cup) this.cup.visible = false; }
  }
  // 오늘의 운세를 뽑으면 하루 동안 가방에 작은 행운 부적이 달린다 (친구들에게도 보인다)
  setCharm(color) {
    if ((this.charmColor || null) === (color || null)) return;
    this.charmColor = color || null;
    if (this.charm) { this.upper.remove(this.charm); this.charm = null; }
    if (!color) return;
    const c = new THREE.Group();
    const cord = new THREE.Mesh(new THREE.CylinderGeometry(0.008, 0.008, 0.12, 4), new THREE.MeshBasicMaterial({ color: 0xc8323a })); cord.position.y = 0.06; c.add(cord);
    const bag = new THREE.Mesh(new THREE.BoxGeometry(0.11, 0.15, 0.03), toon(color)); bag.position.y = -0.06; c.add(bag);
    const knot = new THREE.Mesh(new THREE.SphereGeometry(0.022, 8, 6), toon(0xfff4dc)); knot.position.y = 0.015; c.add(knot);
    c.position.set(0.23, 0.42, -0.48); this.upper.add(c); this.charm = c;
  }
  // 이번 주 이 장소의 터줏대감(1위)은 머리 위에 작은 금관
  // 집중 중인 친구 머리 위: 남은 시간이 1초마다 줄어드는 작은 타이머 (둥근 진행 띠 + 분:초)
  setFocusLeft(left, plan) {
    if (left === null || left === undefined) { this.focusEnd = null; if (this.timer) this.timer.visible = false; return; }
    const end = Date.now() + left * 1000;
    if (!this.focusEnd || Math.abs(end - this.focusEnd) > 2500) this.focusEnd = end;   // 신호가 늦게 와도 덜컥거리지 않게
    this.focusPlan = (plan || 40) * 60;
    if (!this.timer) {
      const c = document.createElement("canvas"); c.width = 256; c.height = 96;
      const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, depthTest: false, transparent: true }));
      sp.scale.set(1.25, 0.47, 1); sp.renderOrder = 11; this.g.add(sp); this.timer = sp; this.timerCanvas = c; this.timerShown = "";
    }
    this.timer.visible = true;
  }
  drawFocusTimer() {
    if (!this.timer || !this.focusEnd || !this.timer.visible) return;
    const left = Math.max(0, Math.round((this.focusEnd - Date.now()) / 1000));
    const txt = String(Math.floor(left / 60)).padStart(2, "0") + ":" + String(left % 60).padStart(2, "0");
    if (txt === this.timerShown) return; this.timerShown = txt;
    const c = this.timerCanvas, x = c.getContext("2d"); x.clearRect(0, 0, 256, 96);
    x.fillStyle = "rgba(20,24,22,.78)"; x.beginPath(); x.moveTo(48, 8); x.arcTo(248, 8, 248, 88, 40); x.arcTo(248, 88, 8, 88, 40); x.arcTo(8, 88, 8, 8, 40); x.arcTo(8, 8, 248, 8, 40); x.fill();
    const k = 1 - left / this.focusPlan;                                     // 진행 띠
    x.lineWidth = 7; x.strokeStyle = "rgba(255,255,255,.18)"; x.beginPath(); x.arc(52, 48, 24, 0, Math.PI * 2); x.stroke();
    x.strokeStyle = "#9fd6bf"; x.beginPath(); x.arc(52, 48, 24, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * k); x.stroke();
    x.fillStyle = "#fff"; x.font = "700 46px 'Noto Sans KR', sans-serif"; x.textBaseline = "middle"; x.textAlign = "left"; x.fillText(txt, 92, 50);
    this.timer.material.map.needsUpdate = true;
  }
  setKing(v) {
    if (!!v === !!this.crown) return;
    if (v) {
      const c = new THREE.Group();
      const band = new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.17, 0.09, 16, 1, true), crownM); c.add(band);
      for (let i = 0; i < 5; i++) { const a = (i / 5) * Math.PI * 2; const t = new THREE.Mesh(new THREE.ConeGeometry(0.045, 0.13, 6), crownM); t.position.set(Math.cos(a) * 0.15, 0.1, Math.sin(a) * 0.15); c.add(t); }
      const gem = new THREE.Mesh(new THREE.SphereGeometry(0.035, 8, 6), new THREE.MeshBasicMaterial({ color: 0xd8405a })); gem.position.set(0, 0.01, 0.17); c.add(gem);
      c.position.y = 1.93; this.upper.add(c); this.crown = c; this.tag.position.y = 2.35;
    } else { this.upper.remove(this.crown); this.crown = null; this.tag.position.y = 2.15; }
  }
  setFocusStage(n) {
    if (n === this.stage) return;
    const up = n > (this.stage || 0); this.stage = n;
    if (n >= 1 && !this.glow) {
      this.glow = new THREE.Mesh(new THREE.PlaneGeometry(1.9, 1.9), new THREE.MeshBasicMaterial({ map: glowTex, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, opacity: 0 }));
      this.glow.rotation.x = -Math.PI / 2; this.glow.position.y = 0.05; this.g.add(this.glow);
    }
    if (n >= 2 && !this.embers) {
      const N = 26, geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(N * 3), 3));
      geo.setAttribute("color", new THREE.BufferAttribute(new Float32Array(N * 3), 3));
      const pts = new THREE.Points(geo, new THREE.PointsMaterial({ size: 0.17, map: puffTex, vertexColors: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
      pts.frustumCulled = false; scene.add(pts);
      this.embers = { pts, life: new Float32Array(N), total: new Float32Array(N), v: new Float32Array(N * 3) };
    }
    if (n >= 3 && !this.fire) this.fire = makeFire(FLAME_STYLE);
    if (this.me && up && this.onStageUp) this.onStageUp(n);
  }
  focusFx(dt) {
    const n = this.stage || 0, shown = this.g.visible;
    if (this.glow) {
      const tgt = n >= 1 ? (n >= 3 ? 0.95 : 0.8) + (reduceMotion ? 0 : Math.sin(this.t * 2.2) * 0.15) : 0;
      this.glow.material.opacity += (tgt - this.glow.material.opacity) * Math.min(1, dt * 2);
      this.glow.scale.setScalar(n >= 4 ? 1.35 : n >= 3 ? 1.2 : 1.05);
    }
    if (this.embers) {
      const E = this.embers, pos = E.pts.geometry.attributes.position, col = E.pts.geometry.attributes.color, N = E.life.length;
      const on = n >= 2 && shown, gp = this.g.position, top = this.upper.position.y;
      const tint = n >= 4 ? [0.35, 0.65, 1] : [1, 0.42, 0.08];
      for (let i = 0; i < N; i++) {
        if (E.life[i] <= 0) {
          if (!on || Math.random() > dt * (n >= 3 ? 14 : 8)) { col.setXYZ(i, 0, 0, 0); continue; }
          const a = Math.random() * Math.PI * 2, r = 0.25 + Math.random() * 0.25;
          pos.setXYZ(i, gp.x + Math.cos(a) * r, gp.y + top + 0.5 + Math.random() * 0.6, gp.z + Math.sin(a) * r);
          E.v[i * 3] = (Math.random() - 0.5) * 0.15; E.v[i * 3 + 1] = 0.55 + Math.random() * 0.5; E.v[i * 3 + 2] = (Math.random() - 0.5) * 0.15;
          E.life[i] = E.total[i] = 1.1 + Math.random() * 0.9;
        }
        E.life[i] -= dt;
        const k = Math.max(0, E.life[i] / E.total[i]), w = reduceMotion ? 0 : Math.sin((this.t + i) * 7) * 0.08;
        pos.setXYZ(i, pos.getX(i) + (E.v[i * 3] + w) * dt, pos.getY(i) + E.v[i * 3 + 1] * dt, pos.getZ(i) + E.v[i * 3 + 2] * dt);
        const f = Math.sin(k * Math.PI);
        col.setXYZ(i, tint[0] * f, tint[1] * f, tint[2] * f);
      }
      pos.needsUpdate = true; col.needsUpdate = true;
    }
    if (this.fire) {
      // 보는 사람 카메라 반대쪽(=캐릭터 등 뒤)에 세워, 어느 쪽에서 봐도 캐릭터 뒤에서 타오른다
      _away.subVectors(this.g.position, camera.position); _away.y = 0;
      if (_away.lengthSq() < 1e-4) _away.set(0, 0, -1); _away.normalize(); _side.set(-_away.z, 0, _away.x);
      this.fire.update(this, dt, n, n >= 3 && shown);
    }
  }
  dispose() {
    scene.remove(this.g);
    if (this.embers) { scene.remove(this.embers.pts); this.embers.pts.geometry.dispose(); }
    if (this.fire) this.fire.parts.forEach((f) => scene.remove(f));
  }
}

// ---------------------------------------------------------------- 나
const colors = root.dataset.colors.split(",");
let myColor = root.dataset.color;
const meName = root.dataset.meName || (document.querySelector(".m-who") || {}).textContent || "나", meCap = root.dataset.meCap || null;
const me = new Avatar({ color: myColor, nick: meName.trim() || "나", cap: meCap, me: true });
me.onStageUp = (n) => whisper(["5분째 집중 중. 발밑이 따뜻해졌어요.", "15분! 어깨 위로 불티가 오르기 시작해요.", "40분! 등 뒤로 열공 불꽃이 타올라요.", "80분! 푸른 불꽃까지 왔어요. 대단해요."][n - 1], 4200);
me.place(P.spawn.x, P.spawn.z, P.spawn.yaw !== undefined ? P.spawn.yaw : Math.PI);
// 장소 사진(썸네일) 찍기: ?shot=1&cam=x,y,z&look=x,y,z&fov=45 → 내 캐릭터를 숨기고 카메라를 그 자리에 고정
const QS = new URLSearchParams(location.search);
const SHOT = QS.has("shot") && QS.get("cam") ? { p: QS.get("cam").split(",").map(Number), t: (QS.get("look") || "0,0,0").split(",").map(Number), fov: +QS.get("fov") || 50 } : null;
if (QS.has("shot")) me.g.visible = false;
let state = "free";      // free | sitting | focus
let mySeat = null, planMin = parseInt(root.dataset.plan, 10) || 40, focusStart = 0;

// ---------------------------------------------------------------- 카메라 (내 캐릭터를 따라 돈다)
const CAM = Object.assign({ free: isTouch ? 9.5 : 8.5, seated: isTouch ? 6.4 : 6.0, focus: isTouch ? 5.8 : 5.4, pitch: 0.42, seatPitch: 0.36, focusPitch: 0.3 }, P.cam || {});
const cam = { yaw: P.spawn.camYaw || 0, pitch: CAM.pitch, dist: CAM.free, tYaw: P.spawn.camYaw || 0, tPitch: CAM.pitch, tDist: CAM.free };
const camTarget = new THREE.Vector3();
let camFree = CAM.free, camLift = 0, camYawOff = 0;
const camDir = new THREE.Vector3(), _tmpDir = new THREE.Vector3();
function updateCamera(dt, snap) {
  // 부드럽게 따라가기: 손으로 돌릴 때는 빠르게, 저절로 돌아갈 때는 천천히 (지수 감쇠라 화면 빠르기와 상관없이 같은 느낌)
  const ky = snap ? 1 : 1 - Math.exp(-dt * (drag && drag.moved ? 14 : 4.5));
  const kd = snap ? 1 : 1 - Math.exp(-dt * 5);
  cam.yaw += (cam.tYaw - cam.yaw) * ky; cam.pitch += (cam.tPitch - cam.pitch) * ky; cam.dist += (cam.tDist - cam.dist) * kd;
  const tgt = new THREE.Vector3(me.g.position.x, me.g.position.y + (state === "free" ? 1.3 : 1.15), me.g.position.z);
  camTarget.lerp(tgt, snap ? 1 : 1 - Math.exp(-dt * 8));
  // 카메라와 캐릭터 사이에 벽이 있으면: 조금 더 위에서 내려다보는 각도로 비켜 보고, 그래도 막히면 벽 앞까지만
  const freeAt = (pitch, dir, yo = 0) => {
    const yw = cam.yaw + yo;
    dir.set(Math.sin(yw) * Math.cos(pitch), Math.sin(pitch), Math.cos(yw) * Math.cos(pitch));
    occRay.set(camTarget, dir); occRay.far = cam.dist + 0.4;
    const h = occRay.intersectObjects(occluders, false).find((x) => shown(x.object));
    return h ? Math.max(0.9, h.distance - 0.35) : cam.dist;
  };
  let free = freeAt(cam.pitch, camDir), lift = 0;
  if (free < cam.dist * 0.75) {
    for (const extra of [0.3, 0.6, 0.85]) {
      const p2 = Math.min(1.35, cam.pitch + extra), f2 = freeAt(p2, _tmpDir);
      if (f2 > free + 0.6) { free = f2; lift = p2 - cam.pitch; if (f2 >= cam.dist * 0.75) break; }
    }
  }
  // 위로 비켜도 막히면(천장 있는 실내) 어깨 너머로 옆으로 조금 돌아서 본다
  let yawOff = 0;
  if (free < cam.dist * 0.6 && !(drag && drag.moved)) {
    let best = free;
    for (const yo of [0.5, -0.5, 0.9, -0.9]) { const f = freeAt(cam.pitch + lift, _tmpDir, yo); if (f > best + 0.5) { best = f; yawOff = yo; } }
    free = best;
  }
  camYawOff = snap ? yawOff : camYawOff + (yawOff - camYawOff) * (1 - Math.exp(-dt * 2.2));
  camLift += (lift - camLift) * (1 - Math.exp(-dt * (lift > camLift ? 10 : 2.5)));
  const pe = cam.pitch + camLift, ye = cam.yaw + camYawOff;
  if (Math.abs(camYawOff - yawOff) > 0.02 || Math.abs(camLift - lift) > 0.02) free = Math.min(free, freeAt(pe, _tmpDir, camYawOff));   // 도는 중에도 벽을 뚫지 않게
  camDir.set(Math.sin(ye) * Math.cos(pe), Math.sin(pe), Math.cos(ye) * Math.cos(pe));
  camFree = free < camFree || snap ? free : camFree + (free - camFree) * (1 - Math.exp(-dt * 2.5));
  const d = Math.min(cam.dist, camFree);
  const cx = camTarget.x + camDir.x * d, cz = camTarget.z + camDir.z * d, cy = camTarget.y + camDir.y * d;
  camera.position.set(cx, Math.max(cy, heightAt(cx, cz) + 0.5), cz);
  camera.lookAt(camTarget);
  // 카메라가 캐릭터에 너무 붙으면 내 캐릭터를 잠깐 숨긴다 (머리 속이 보이지 않게)
  me.g.visible = !QS.has("shot") && d > 2.2;   // 벽 때문에 카메라가 바짝 붙으면 머리가 화면을 가리지 않게 숨긴다
  if (me.tag) me.tag.material.opacity = Math.max(0, Math.min(1, (d - 2.2) / 1.2));   // 가까우면 내 이름표는 흐리게
  if (SHOT) { camera.position.set(...SHOT.p); camera.lookAt(...SHOT.t); if (camera.fov !== SHOT.fov) { camera.fov = SHOT.fov; camera.updateProjectionMatrix(); } }
}
function camBehind(dist, pitch) {
  const want = me.yaw + Math.PI, d = Math.atan2(Math.sin(want - cam.tYaw), Math.cos(want - cam.tYaw));
  cam.tYaw += d; if (dist) cam.tDist = dist; if (pitch) cam.tPitch = pitch;
}

// ---------------------------------------------------------------- 입력: 누르기·끌기·확대
const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
const pointers = new Map();
let drag = null, pinch = null;
canvas.addEventListener("pointerdown", (e) => {
  canvas.setPointerCapture(e.pointerId);
  pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
  if (pointers.size === 1) drag = { x: e.clientX, y: e.clientY, sx: e.clientX, sy: e.clientY, t: performance.now(), moved: false };
  if (pointers.size === 2) { const [a, b] = [...pointers.values()]; pinch = { d: Math.hypot(a.x - b.x, a.y - b.y), dist: cam.tDist }; drag = null; }
});
canvas.addEventListener("pointermove", (e) => {
  if (!pointers.has(e.pointerId)) return;
  pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
  if (pinch && pointers.size === 2) {
    const [a, b] = [...pointers.values()];
    cam.tDist = Math.max(3, Math.min(18, pinch.dist * pinch.d / Math.max(20, Math.hypot(a.x - b.x, a.y - b.y)))); return;
  }
  if (!drag) return;
  const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
  if (Math.hypot(e.clientX - drag.sx, e.clientY - drag.sy) > 6) drag.moved = true;
  if (drag.moved) { cam.tYaw -= dx * 0.0065; cam.tPitch = Math.max(0.06, Math.min(1.05, cam.tPitch + dy * 0.0045)); }
  drag.x = e.clientX; drag.y = e.clientY;
});
function endPointer(e) {
  pointers.delete(e.pointerId);
  if (pointers.size < 2) pinch = null;
  if (drag && !drag.moved && performance.now() - drag.t < 450) tap(e.clientX, e.clientY);
  if (pointers.size === 0) drag = null;
}
canvas.addEventListener("pointerup", endPointer);
canvas.addEventListener("pointercancel", (e) => { pointers.delete(e.pointerId); drag = null; pinch = null; });
canvas.addEventListener("wheel", (e) => { e.preventDefault(); cam.tDist = Math.max(3, Math.min(18, cam.tDist * (1 + Math.sign(e.deltaY) * 0.1))); }, { passive: false });

const marker = new THREE.Mesh(new THREE.RingGeometry(0.25, 0.35, 24), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0, depthWrite: false }));
marker.rotation.x = -Math.PI / 2; scene.add(marker);

function tap(cx, cy) {
  if (!entered) return;
  const r = canvas.getBoundingClientRect();
  ndc.set(((cx - r.left) / r.width) * 2 - 1, -((cy - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(ndc, camera);
  const hits = ray.intersectObjects(P.picks, false);
  if (!hits.length) return;
  const h = hits[0], o = h.object;
  if (o.userData.seat !== undefined) return goSit(o.userData.seat);
  if (o.userData.notes) { document.getElementById("notes").scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" }); return; }
  if (o.userData.action) return act(o.userData.action, o);
  if (state === "focus") return whisper("집중 중에는 자리에 머물러요. 일어나려면 '그만하기'를 누르세요.");
  const pts = P.planWalk(me.pos, h.point, o);
  if (!pts || !pts.length) return;
  standUp(true);
  me.walkTo(pts);
  me.onArrive = null;
  marker.position.set(me.path[me.path.length - 1].x, heightAt(h.point.x, h.point.z) + 0.05, me.path[me.path.length - 1].z);
  marker.material.opacity = 0.9; marker.scale.setScalar(1);
  sync(true);
}

// 키보드: 방향키·WASD 로 걷기, 스페이스로 합장
const keys = new Set();
window.addEventListener("keydown", (e) => {
  if (!entered || e.target.closest("input, textarea, select")) return;
  const k = e.key.toLowerCase();
  if (["arrowup", "arrowdown", "arrowleft", "arrowright", "w", "a", "s", "d"].includes(k)) { keys.add(k); e.preventDefault(); }
  if (k === " ") { e.preventDefault(); act(P.spaceAction || "gassho"); }
});
window.addEventListener("keyup", (e) => keys.delete(e.key.toLowerCase()));
function keyMove(dt) {
  if (!keys.size || state === "focus") return;
  let f = 0, s = 0;
  if (keys.has("arrowup") || keys.has("w")) f += 1; if (keys.has("arrowdown") || keys.has("s")) f -= 1;
  if (keys.has("arrowleft") || keys.has("a")) s -= 1; if (keys.has("arrowright") || keys.has("d")) s += 1;
  if (!f && !s) return;
  standUp(true);
  // 카메라가 보는 방향이 앞, 그 오른쪽이 오른쪽
  const fx = -Math.sin(cam.yaw), fz = -Math.cos(cam.yaw);
  const dirx = fx * f + -fz * s, dirz = fz * f + fx * s;
  const len = Math.hypot(dirx, dirz) || 1, nx = me.pos.x + (dirx / len) * 3 * dt, nz = me.pos.z + (dirz / len) * 3 * dt;
  const [x, z] = P.step(me.pos.x, me.pos.z, nx, nz);
  me.path = []; me.pos.x = x; me.pos.z = z; me.targetYaw = Math.atan2(dirx, dirz); me.pose = "walk"; keyWalking = 0.15;
}
let keyWalking = 0;

// ---------------------------------------------------------------- 앉기·일어나기·종
function occupiedSeats() { const s = new Set(); others.forEach((o) => { if (o.seat !== null) s.add(o.seat); }); return s; }
function nearestFreeSeat() {
  const occ = occupiedSeats(); let best = null, bd = 1e9;
  SEATS.forEach((s, i) => { if (occ.has(i)) return; const d = Math.hypot(s.x - me.pos.x, s.z - me.pos.z); if (d < bd) { bd = d; best = i; } });
  return best;
}
function goSit(id) {
  if (state === "focus") return whisper("집중 중이에요. 자리를 옮기려면 먼저 '그만하기'를 누르세요.");
  if (occupiedSeats().has(id)) return whisper(`그 ${P.seatNoun}에는 이미 누가 있어요.`);
  standUp(true);
  me.walkTo(P.planSeat(me.pos, id));
  me.onArrive = () => { sitAt(id); };
  sync(true);
}
function sitAt(id) {
  const s = SEATS[id], yaw = s.yaw !== undefined ? s.yaw : Math.PI;
  me.place(s.x, s.z); me.yaw = yaw; me.targetYaw = yaw; me.pose = "sit"; me.seat = id; mySeat = id; me.lastSeat = id;
  state = "sitting"; camBehind(s.camDist || CAM.seated, s.camPitch || CAM.seatPitch);
  audio.sfx((typeof P.sitSound === "function" ? P.sitSound(s) : P.sitSound) || "cushion");
  whisper((typeof P.sitText === "function" ? P.sitText(s) : P.sitText) || "자리에 앉았어요. 시간을 고르고 집중을 시작해 보세요.");
  render(); sync(true);
}
function standUp(silent) {
  if (state === "free") return;
  if (state === "focus") return;
  state = "free"; me.seat = null; mySeat = null; me.pose = "stand"; cam.tDist = CAM.free; cam.tPitch = CAM.pitch;
  if (SEATS[me.lastSeat] && P.leaveSeat) { const [x, z] = P.leaveSeat(SEATS[me.lastSeat]); me.place(x, z); }
  if (!silent) whisper("천천히 일어났어요.");
  render(); sync(true);
}
// 장소가 쓰는 공통 기능
const pops = [];
const E = {
  THREE, scene, me, whisper: (...a) => whisper(...a), sfx: (n) => audio.sfx(n), sync: (n) => sync(n),
  get state() { return state; }, get others() { return others; },
  walk(points, onArrive) { if (state === "focus") return false; standUp(true); me.walkTo(points); me.onArrive = onArrive || null; sync(true); return true; },
  face(x, z) { me.targetYaw = Math.atan2(x - me.pos.x, z - me.pos.z); },
  pose(p) { me.pose = p; sync(true); },
  look(yaw, dist, pitch) { const d = Math.atan2(Math.sin(yaw - cam.tYaw), Math.cos(yaw - cam.tYaw)); cam.tYaw += d; if (dist) cam.tDist = dist; if (pitch) cam.tPitch = pitch; },
  sit(id) { goSit(id); },
  nearestSeat(filter) {
    const occ = occupiedSeats(); let best = null, bd = 1e9;
    SEATS.forEach((s, i) => { if (occ.has(i) || (filter && !filter(s))) return; const d = Math.hypot(s.x - me.pos.x, s.z - me.pos.z); if (d < bd) { bd = d; best = i; } });
    return best;
  },
  get audioOn() { return audio.on; },
  post: (url, data) => post(url, data),
  root,
  // 화면 가운데 카드 (운세 결과 같은 것). buttons: [{label, primary, onClick}] — onClick 이 false 를 돌려주면 닫지 않는다
  card(build, buttons) {
    const old = stage.querySelector(".w3-card"); if (old) old.remove();
    const el = document.createElement("div"); el.className = "w3-card"; el.setAttribute("role", "dialog"); el.setAttribute("aria-modal", "false");
    const body = document.createElement("div"); body.className = "w3-card-body"; build(body); el.appendChild(body);
    const row = document.createElement("div"); row.className = "w3-card-actions";
    (buttons || [{ label: "닫기" }]).forEach((b) => {
      const btn = document.createElement("button"); btn.type = "button"; btn.className = "btn" + (b.primary ? " primary" : ""); btn.textContent = b.label;
      btn.addEventListener("click", () => { const keep = b.onClick && b.onClick(btn) === false; if (!keep) el.remove(); }); row.appendChild(btn);
    });
    el.appendChild(row); stage.appendChild(el); return el;
  },
  // 친구들에게도 보이는 동작: 내 화면에서 바로 하고, 다음 신호에 실어 보낸다
  share(name) { pendingAct = name; sync(true); },
  pop(obj, secs, av) {
    if (av && av !== me) { const c = obj.clone(); c.userData = { ...obj.userData, tmp: true }; scene.add(c); obj = c; }   // 친구 몫은 복사본
    pops.push({ obj, t: secs || 1, total: secs || 1, av: av || me }); obj.visible = true;
  },
};

function playAct(name, av, mine) {
  if (P.remote && P.remote[name]) return P.remote[name](E, av, mine);
  if (name === "bow") av.bow();
}

// ---------------------------------------------------------------- 동작 메뉴
const ICON = {
  sit: '<svg viewBox="0 0 24 24"><path d="M4 17h16M6 17l1-4h10l1 4M9 13V9a3 3 0 0 1 6 0v4"/></svg>',
  focus: '<svg viewBox="0 0 24 24"><circle cx="12" cy="13" r="7"/><path d="M12 13V9M9 3h6"/></svg>',
  breathe: '<svg viewBox="0 0 24 24"><path d="M4 9c3-3 6 3 9 0s5-1 7 0M4 14c3-3 6 3 9 0s5-1 7 0"/></svg>',
  gassho: '<svg viewBox="0 0 24 24"><path d="M12 3v9M12 3l-3 9v6l3 3 3-3v-6l-3-9"/></svg>',
  bow: '<svg viewBox="0 0 24 24"><circle cx="9" cy="7" r="2.5"/><path d="M9 10c3 0 6 2 7 5M6 21l3-8 7 2"/></svg>',
  moktak: '<svg viewBox="0 0 24 24"><ellipse cx="11" cy="14" rx="7" ry="5.5"/><path d="M8 14h6M15 4l5 5"/></svg>',
  stand: '<svg viewBox="0 0 24 24"><circle cx="12" cy="5" r="2.5"/><path d="M12 8v8M8 21l4-5 4 5M7 12h10"/></svg>',
  stop: '<svg viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>',
  bell: '<svg viewBox="0 0 24 24"><path d="M6 16c1-1 1-3 1-6a5 5 0 0 1 10 0c0 3 0 5 1 6zM10 19a2 2 0 0 0 4 0"/></svg>',
  dot: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/></svg>',
};
const actionsEl = $("[data-actions]"), plansEl = $("[data-plans]"), chatEl = $("[data-chat]");
// 판(칠판·역 노트)에 한 줄 쓰기
if (chatEl) chatEl.addEventListener("submit", (e) => {
  e.preventDefault();
  const inp = chatEl.querySelector("input"), body = inp.value.trim(); if (!body) return;
  const b = chatEl.querySelector("button"); b.disabled = true;
  post(root.dataset.write, { body }).then((d) => {
    if (d.board && P.board) P.board(d.board);
    if (d.ok) { inp.value = ""; inp.blur(); audio.sfx(P.writeSound || "cushion"); if (P.chat && P.chat.done) whisper(P.chat.done); }
    else whisper(d.error || "다시 시도해 주세요.", 3600);
  }).catch(() => whisper("연결이 불안정해요. 잠시 뒤 다시 눌러 주세요.")).finally(() => { b.disabled = false; });
});
Object.assign(ICON, P.icons || {});
const LABEL = Object.assign({ sit: "앉기", focus: "집중 시작", breathe: "숨 고르기", gassho: "합장", bow: "절하기", stand: "일어나기", stop: "그만하기" }, P.labels || {});
function btn(id, primary) { return `<button type="button" class="w3-act${primary ? " is-primary" : ""}" data-act="${id}">${ICON[id] || ICON.dot}<span>${LABEL[id] || id}</span></button>`; }
function render() {
  let html = "";
  html = (P.actions[state] || []).map((id, i) => btn(id, i === 0 && state !== "focus")).join("");
  actionsEl.innerHTML = html;
  plansEl.hidden = state !== "sitting";
  if (chatEl) {
    const can = !!(P.chat && P.chat.can(mySeat !== null ? SEATS[mySeat] : null, state));
    chatEl.hidden = !can; if (can && P.chat.placeholder) chatEl.querySelector("input").placeholder = P.chat.placeholder;
  }
  $("[data-timer]").hidden = state !== "focus";
  stage.classList.toggle("is-focus", state === "focus");
  stage.classList.toggle("is-seated", state !== "free");
  $("[data-hint]").textContent = state === "free" ? (isTouch ? `바닥을 누르면 걸어가요 · 끌어서 둘러보기 · ${josa(P.seatNoun, "을", "를")} 누르면 앉아요` : `바닥을 누르면 걸어가요 · 끌어서 둘러보기 · ${josa(P.seatNoun, "을", "를")} 누르면 앉아요 · 스페이스는 ${LABEL[P.spaceAction || "gassho"]}`)
    : state === "sitting" ? "시간을 고르고 '집중 시작'을 누르세요" : "화면을 닫아도 여기까지 기록돼요";
}
actionsEl.addEventListener("click", (e) => { const b = e.target.closest("[data-act]"); if (b) act(b.dataset.act); });
function act(id, obj) {
  if (P.custom && P.custom[id]) return P.custom[id](E, obj);
  if (id === "sit") { const s = nearestFreeSeat(); return s === null ? whisper(`빈 ${josa(P.seatNoun, "이", "가")} 없어요.`) : goSit(s); }
  if (id === "stand") return standUp();
  if (id === "gassho") { me.pose = me.pose === "gassho" ? (me.seat !== null ? "sit" : "stand") : "gassho"; if (me.pose === "gassho") whisper("두 손을 모으고, 오늘 공부할 것 하나를 떠올려요."); sync(true); return; }
  if (id === "bow") { me.bow(); whisper("천천히 고개를 숙여요."); E.share("bow"); return; }
  if (id === "breathe") return breathe();
  if (id === "focus") return startFocus();
  if (id === "stop") return finishFocus(false);
}

// ---------------------------------------------------------------- 속삭임(화면 위 안내 문장)
const whisperEl = $("[data-whisper]"); let whisperTimer = 0;
function whisper(text, ms = 3200) {
  whisperEl.textContent = text; whisperEl.classList.add("is-on");
  clearTimeout(whisperTimer); whisperTimer = setTimeout(() => whisperEl.classList.remove("is-on"), ms);
}

// 숨 고르기: 4초 들이쉬고, 2초 멈추고, 6초 내쉬기 × 3
let breathing = false;
async function breathe() {
  if (breathing) return; breathing = true;
  me.pose = "breathe"; sync(true);
  const steps = [["숨을 천천히 들이쉬어요", 4000], ["잠깐 멈추고", 2000], ["어깨 힘을 빼고 길게 내쉬어요", 6000]];
  for (let r = 0; r < 3 && breathing; r++) for (const [t, ms] of steps) { whisper(t, ms - 150); await new Promise((ok) => setTimeout(ok, ms)); }
  whisper("좋아요. 다시 공부로 돌아가요.");
  if (me.pose === "breathe") me.pose = me.seat !== null ? "sit" : "stand";
  breathing = false; sync(true);
}

// ---------------------------------------------------------------- 집중 타이머 (서버가 잰 시간만 인정)
const clockEl = $("[data-clock]"), msgEl = $("[data-msg]");
const pad = (n) => (n < 10 ? "0" : "") + n;
function chosenPlan() { const c = plansEl.querySelector('input[name="plan"]:checked'); return c ? parseInt(c.value, 10) : 40; }
function startFocus() {
  if (state !== "sitting") return;
  planMin = chosenPlan(); state = "focus"; focusStart = Date.now(); me.focus = true;
  me.setFocusLeft(planMin * 60, planMin);   // 친구들이 보는 것처럼 내 머리 위에도 남은 시간
  camBehind(CAM.focus, CAM.focusPitch);
  audio.sfx("bowl"); audio.duck(true);
  whisper(P.focusText ? P.focusText(planMin) : planMin + "분, 지금부터 고요히.");
  render(); post(root.dataset.beat, { action: "start", plan: planMin }).then(onBeat).catch(() => {}); sync(true);
}
let finishing = false;
function finishFocus(complete) {
  if (state !== "focus" || finishing) return; finishing = true;
  const minutes = Math.floor((Date.now() - focusStart) / 60000);
  post(root.dataset.done, { minutes: complete ? planMin : minutes }).then((d) => {
    state = "sitting"; me.focus = false; me.setFocusLeft(null); audio.duck(false); audio.sfx("bowl");
    camBehind(CAM.seated, CAM.seatPitch); render();
    const m = d.minutes >= 5 ? `${d.minutes}분 기록했어요. 오늘 모두 ${d.today}분.` : `5분이 안 돼서 기록하지 않았어요. 오늘 ${d.today}분.`;
    whisper(complete ? "수고했어요. " + m : m, 5000); msgEl.textContent = m;
    sync(true);
  }).catch(() => whisper("연결이 불안정해요. 잠시 뒤 다시 눌러 주세요.")).finally(() => { finishing = false; });
}
function tickTimer() {
  if (state !== "focus") return;
  const left = Math.max(0, planMin * 60 - Math.floor((Date.now() - focusStart) / 1000));
  clockEl.textContent = pad(Math.floor(left / 60)) + ":" + pad(left % 60);
  if (left === 0) finishFocus(true);
}
setInterval(tickTimer, 500);

// ---------------------------------------------------------------- 친구들 (서버와 주고받기)
const others = new Map();
if (QS.has("debug")) window.__w3 = { others, me: () => me, cam: () => ({ d: camera.position.distanceTo(camTarget), dist: cam.dist, pitch: cam.pitch + camLift }),
  fakeFocus: (min) => { focusStart = Date.now() - min * 60000; } };
const listEl = root.querySelector("[data-members]");
function post(url, data) {
  const fd = new FormData(); fd.append("csrf_token", csrf());
  Object.entries(data || {}).forEach(([k, v]) => fd.append(k, v));
  return fetch(url, { method: "POST", body: fd, credentials: "same-origin" }).then((r) => { if (!r.ok) throw r; return r.json(); });
}
let lastSent = 0, dirty = true, beatBusy = false;
function sync(now) { dirty = true; if (now) lastSent = 0; }
function myPayload() {
  return { x: me.pos.x.toFixed(2), z: me.pos.z.toFixed(2), ry: me.yaw.toFixed(2), pose: me.pose === "walk" && !me.moving ? "stand" : me.pose,
    seat: mySeat === null ? "" : mySeat, color: myColor, ...(pendingAct ? { act: pendingAct } : {}) };
}
let pendingAct = "";
const seenAct = new Map();   // 친구 id → 마지막으로 본 동작 번호
function beatLoop() {
  if (!entered || beatBusy || document.hidden) return;
  const now = Date.now(), gap = me.moving || keyWalking > 0 ? 1800 : dirty ? 900 : 7000;
  if (now - lastSent < gap) return;
  beatBusy = true; lastSent = now; dirty = false;
  const payload = myPayload(), sentAct = pendingAct; pendingAct = "";
  post(root.dataset.beat, payload).then(onBeat).catch(() => { if (sentAct && !pendingAct) pendingAct = sentAct; }).finally(() => { beatBusy = false; });
}
setInterval(beatLoop, 300);
function onBeat(d) {
  if (!d || !d.members) return;
  if (d.board && P.board) P.board(d.board);
  const seen = new Set();
  d.members.forEach((m) => {
    if (m.me) { me.setKing(m.king); me.setCharm(m.charm); me.setFocusLeft(m.status === "focus" ? m.left : null, m.plan); return; } seen.add(m.id);
    let o = others.get(m.id);
    if (!o) {
      o = new Avatar({ color: m.color, nick: m.nick, cap: m.cap }); o.place(m.x, m.z, m.ry); others.set(m.id, o);
      if (entered) whisper(m.cap ? `${m.nick} ${m.cap === "선생님" ? "선생님이" : "조교님이"} 들어왔어요.` : `${m.nick}님이 들어왔어요.`, 2600);
    }
    o.setColor(m.color); o.setKing(m.king); o.setCharm(m.charm);
    // 친구가 한 동작을 내 화면에서도 보여 준다 (처음 본 순간의 번호는 기록만)
    if (seenAct.has(m.id) && m.act_seq > seenAct.get(m.id) && m.act) playAct(m.act, o, false);
    seenAct.set(m.id, m.act_seq || 0);
    o.focus = m.status === "focus";
    o.setFocusLeft(o.focus ? m.left : null, m.plan);
    o.setFocusStage(o.focus ? stageFor(m.elapsed || 0) : 0);
    o.seat = m.seat === null || m.seat === undefined ? null : m.seat;
    if (o.seat !== null && SEATS[o.seat]) {
      const s = SEATS[o.seat];
      const sy = s.yaw !== undefined ? s.yaw : Math.PI;
      if (Math.hypot(o.pos.x - s.x, o.pos.z - s.z) > 0.05 && !o.moving) o.walkTo(P.planSeat(o.pos, o.seat));
      o.onArrive = () => { o.pose = m.pose === "stand" ? "sit" : m.pose; o.yaw = sy; o.targetYaw = sy; };
      if (!o.moving) { o.pose = ["gassho", "bow", "breathe"].includes(m.pose) ? m.pose : "sit"; o.targetYaw = sy; }
    } else {
      const far = Math.hypot(o.pos.x - m.x, o.pos.z - m.z);
      if (far > 25) o.place(m.x, m.z, m.ry);
      else if (far > 0.15) o.walkTo(P.planTo(o.pos, m.x, m.z));
      else if (!o.moving) { o.pose = m.pose === "walk" ? "stand" : m.pose; o.targetYaw = m.ry; }

    }
  });
  others.forEach((o, id) => { if (!seen.has(id)) { o.dispose(); others.delete(id); } });
  root.querySelectorAll("[data-count]").forEach((c) => (c.textContent = d.members.length + "명"));
  drawList(d.members);
}
function drawList(ms) {
  listEl.innerHTML = "";
  ms.forEach((m) => {
    const li = document.createElement("li");
    li.className = (m.status === "focus" ? "is-focus" : "") + (m.me ? " is-me" : "");
    const seat = document.createElement("i"); seat.className = "seat"; seat.setAttribute("aria-hidden", "true");
    const b = document.createElement("b");
    if (m.cap) { const c = document.createElement("span"); c.className = "cap"; c.textContent = m.cap; b.append(c, " "); }
    b.append(m.nick + (m.me ? " (나)" : ""));
    if (m.king) { const k = document.createElement("small"); k.className = "here-tag is-king"; k.textContent = "터줏대감"; b.append(" ", k); }
    else if (m.follow) { const k = document.createElement("small"); k.className = "here-tag"; k.textContent = "팔로잉"; b.append(" ", k); }
    const s = document.createElement("span");
    s.textContent = (m.status === "focus" ? `집중 ${m.elapsed}/${m.plan}분` : m.seat !== null && m.seat !== undefined ? `${P.seatNoun}에 앉음` : "산책 중") + ` · 오늘 ${m.today}분`;
    li.append(seat, b, s); listEl.appendChild(li);
  });
}

// 내 캐릭터 색
root.querySelectorAll("[data-color-pick]").forEach((b) => b.addEventListener("click", () => {
  myColor = b.dataset.colorPick; me.setColor(myColor);
  root.querySelectorAll("[data-color-pick]").forEach((x) => { const on = x === b; x.classList.toggle("is-on", on); x.setAttribute("aria-pressed", on ? "true" : "false"); });
  sync(true);
}));

// 떠날 때: 집중 중이면 거기까지 기록, 아니면 자리 비움
window.addEventListener("pagehide", () => {
  const fd = new FormData(); fd.append("csrf_token", csrf());
  if (state === "focus") { fd.append("minutes", Math.floor((Date.now() - focusStart) / 60000)); navigator.sendBeacon(root.dataset.done, fd); }
  else { fd.append("action", "leave"); navigator.sendBeacon(root.dataset.beat, fd); }
});

// ---------------------------------------------------------------- 소리
const audio = (() => {
  const base = root.dataset.audio;
  let ctx = null, master = null, on = false, buffers = {}, loops = {}, keep = null, timers = [];
  const STEPS = Object.assign({ f: "common/steps", out: 0.55, in: 0.18 }, (P.sounds || {}).steps || {});
  const btnEl = $("[data-sound]");
  function label() { btnEl.textContent = on ? "소리 끄기" : "소리 켜기"; btnEl.setAttribute("aria-pressed", on ? "true" : "false"); }
  function mediaMode(v) {
    try { if (navigator.audioSession) navigator.audioSession.type = v ? "playback" : "auto"; } catch (_) {}
    if (v) { if (!keep) { keep = new Audio("/static/silence.wav"); keep.loop = true; keep.setAttribute("playsinline", ""); } keep.play().catch(() => {}); }
    else if (keep) keep.pause();
  }
  function load(name) {
    if (buffers[name]) return Promise.resolve(buffers[name]);
    return fetch(base + name + ".mp3").then((r) => r.arrayBuffer()).then((ab) => new Promise((ok, no) => ctx.decodeAudioData(ab, ok, no))).then((b) => (buffers[name] = b));
  }
  function loop(name, gain, rate = 1) {
    return load(name).then((b) => {
      if (!on || loops[name]) return;
      const s = ctx.createBufferSource(); s.buffer = b; s.loop = true; s.loopStart = 0.06; s.loopEnd = b.duration - 0.06; s.playbackRate.value = rate;
      const g = ctx.createGain(); g.gain.value = 0; g.gain.linearRampToValueAtTime(gain, ctx.currentTime + 2.5);
      s.connect(g); g.connect(master); s.start(0, Math.random() * (b.duration - 1)); loops[name] = { s, g, base: gain };
    }).catch(() => {});
  }
  function one(name, gain = 1, rate = 1, lowpass) {
    if (!on) return;
    load(name).then((b) => {
      const s = ctx.createBufferSource(); s.buffer = b; s.playbackRate.value = rate;
      const g = ctx.createGain(); g.gain.value = gain; let node = s;
      if (lowpass) { const f = ctx.createBiquadFilter(); f.type = "lowpass"; f.frequency.value = lowpass; node.connect(f); node = f; }
      node.connect(g); g.connect(master); s.start();
    }).catch(() => {});
  }
  function start() {
    try {
      mediaMode(true);
      if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)();
      if (ctx.state === "suspended") ctx.resume();
      if (on) return label(); on = true;
      master = ctx.createGain(); master.gain.value = 0.9; master.connect(ctx.destination);
      const S = P.sounds || {};
      const fits = (w) => !w || (w === "day" ? TIME === "day" : w === "dusk" ? TIME === "dusk" : TIME !== "day");
      (S.loops || []).forEach((l) => { if (fits(l.when)) loop(l.f, l.g, l.rate || 1); });
      loop(STEPS.f, 0.0, 1);
      Object.values(S.sfx || {}).forEach((x) => load(x.f));
      // 가끔 불어오는 소리(풍경·갈매기 등): 정해진 간격마다 커졌다 작아진다
      (S.gusts || []).forEach((gst) => {
        if (!fits(gst.when)) return;
        loop(gst.f, 0.0);
        const blow = () => { if (!on) return; const l = loops[gst.f]; if (l) { const t = ctx.currentTime; l.g.gain.cancelScheduledValues(t); l.g.gain.setValueAtTime(l.g.gain.value, t); l.g.gain.linearRampToValueAtTime(rand(gst.max * 0.5, gst.max), t + 3); l.g.gain.linearRampToValueAtTime(0.0, t + rand(9, 16)); } timers.push(setTimeout(blow, rand(gst.every[0] * 1000, gst.every[1] * 1000))); };
        timers.push(setTimeout(blow, 4000));
      });
    } catch (_) {}
    label();
  }
  function stop() {
    on = false; timers.forEach(clearTimeout); timers = []; loops = {};
    if (master) { master.disconnect(); master = null; }
    if (ctx) { ctx.close(); ctx = null; buffers = {}; }
    mediaMode(false); label();
  }
  btnEl.addEventListener("click", () => (on ? stop() : start()));
  let walkLevel = 0;
  return {
    start, stop, get on() { return on; },
    walking(v, indoor) {
      const l = loops[STEPS.f]; if (!l || !ctx) return;
      const target = v ? (indoor ? STEPS.in : STEPS.out) : 0; if (Math.abs(target - walkLevel) < 0.01) return; walkLevel = target;
      l.g.gain.setTargetAtTime(target, ctx.currentTime, 0.12); l.s.playbackRate.setTargetAtTime(indoor ? 1.25 : 1, ctx.currentTime, 0.1);
    },
    duck(v) { if (master && ctx) master.gain.setTargetAtTime(v ? 0.6 : 0.9, ctx.currentTime, 1.2); },
    sfx(name) {
      const x = Object.assign({ bowl: { f: "common/bowl", g: 0.75 }, cushion: { f: "common/steps", g: 0.25, rate: 0.7, lp: 900 } }, (P.sounds || {}).sfx || {})[name];
      if (x) one(x.f, x.g, (x.rate || 1) * (x.jitter ? rand(0.97, 1.03) : 1), x.lp);
    },
    raw(f, g, rate, lp) { one(f, g, rate, lp); },
  };
})();

// ---------------------------------------------------------------- 들어가기 (소리 재생은 사용자가 눌러야 시작된다)
let entered = false;
$("[data-enter-btn]").addEventListener("click", () => {
  entered = true; $("[data-enter]").hidden = true; audio.start();
  whisper(P.welcome, 4200);
  render(); sync(true);
  if (root.dataset.status === "focus") {      // 집중 중에 나갔다 돌아온 경우: 빈 방석에 앉혀 이어간다
    const s = nearestFreeSeat();
    if (s !== null) { sitAt(s); state = "focus"; me.focus = true; planMin = parseInt(root.dataset.plan, 10) || 40;
      focusStart = Date.now() - (parseInt(root.dataset.elapsed, 10) || 0) * 60000; camBehind(CAM.focus, CAM.focusPitch); render(); }
  }
});

// ---------------------------------------------------------------- 크기·그리기
function resize() {
  const w = stage.clientWidth, h = stage.clientHeight;
  renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(stage); resize();

const clock = new THREE.Clock();
let frames = 0, slowT = 0;
if (P.fog) { scene.fog.near = P.fog.near; scene.fog.far = P.fog.far; }
updateCamera(0, true);
function frame() {
  requestAnimationFrame(frame);
  if (document.hidden) return;
  const dt = Math.min(0.05, clock.getDelta());
  keyMove(dt);
  if (keyWalking > 0) { keyWalking -= dt; if (keyWalking <= 0 && me.pose === "walk" && !me.moving) me.pose = "stand"; }
  me.setFocusStage(state === "focus" ? stageFor((Date.now() - focusStart) / 60000) : 0);
  me.update(dt); others.forEach((o) => o.update(dt)); updatePuffs(dt);
  audio.walking(me.pose === "walk", P.indoor ? P.indoor(me.pos.x, me.pos.z) : false);
  if (marker.material.opacity > 0) { marker.material.opacity -= dt * 0.8; marker.scale.multiplyScalar(1 + dt * 0.6); }
  // 잠깐 나타나는 물건(목탁·찻잔 등): 캐릭터 앞에 띄웠다가 사라진다
  for (let i = pops.length - 1; i >= 0; i--) {
    const p = pops[i], av = p.av || me; p.t -= dt; const f = new THREE.Vector3(Math.sin(av.yaw), 0, Math.cos(av.yaw));
    p.obj.position.set(av.g.position.x + f.x * 0.62, av.g.position.y + (p.obj.userData.popY || 0.55), av.g.position.z + f.z * 0.62);
    const k = 1 + Math.max(0, p.t - (p.total - 0.2)) * 2.5; p.obj.scale.setScalar(k * (p.obj.userData.popScale || 1));
    if (p.t <= 0) { p.obj.visible = false; if (p.obj.userData.tmp) scene.remove(p.obj); pops.splice(i, 1); }
  }
  if (P.update) P.update(dt, clock.elapsedTime, E);
  if (flies) {
    const p = flies.geometry.attributes.position, b = flies.userData.base, t = clock.elapsedTime;
    for (let i = 0; i < b.length; i++) p.setXYZ(i, b[i][0] + Math.sin(t * 0.3 + i) * 0.8, b[i][1] + Math.sin(t * 0.7 + i * 2) * 0.3, b[i][2] + Math.cos(t * 0.25 + i) * 0.8);
    p.needsUpdate = true; flies.material.opacity = 0.55 + Math.sin(t * 2) * 0.3;
  }
  // 집중 중에는 안개를 가까이 당겨 주변을 흐리게
  const FOG = Object.assign({ near: 26, far: 95, fnear: 4, ffar: 22 }, P.fog || {});
  const fogFar = state === "focus" ? FOG.ffar : FOG.far, fogNear = state === "focus" ? FOG.fnear : FOG.near;
  scene.fog.far += (fogFar - scene.fog.far) * Math.min(1, dt * 1.5); scene.fog.near += (fogNear - scene.fog.near) * Math.min(1, dt * 1.5);
  updateCamera(dt);
  renderer.render(scene, camera);
  // 느린 기기면 화질을 낮춘다
  frames++; slowT += dt;
  if (slowT > 3) { const fps = frames / slowT; if (fps < 28 && pixelRatio > 1) { pixelRatio = Math.max(1, pixelRatio - 0.5); renderer.setPixelRatio(pixelRatio); resize(); } frames = 0; slowT = 0; }
}
render();
document.fonts && document.fonts.ready.then(() => { me.g.remove(me.tag); me.tag = nameSprite(meName.trim() || "나", true, meCap); me.tag.position.y = me.crown ? 2.35 : 2.15; me.g.add(me.tag); });
requestAnimationFrame(frame);
