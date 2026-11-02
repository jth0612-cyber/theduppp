// 같이 공부 · 산사 (3D). 법당 마당을 걸어 다니고, 방석에 앉아 집중한다.
// 같은 장소에 있는 친구들의 캐릭터가 2~7초마다 받은 위치로 부드럽게 움직인다.
import * as THREE from "./vendor/three.module.min.js";

const root = document.getElementById("w3");
const stage = root.querySelector("[data-stage]");
const canvas = root.querySelector("[data-canvas]");
const $ = (s) => root.querySelector(s);
const csrf = () => (document.querySelector('meta[name="csrf-token"]') || {}).content || "";
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const isTouch = matchMedia("(pointer: coarse)").matches;

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
  if (TIME !== "day") {
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

// ---------------------------------------------------------------- 땅과 산
const pickGround = [];
{
  const g = new THREE.Mesh(new THREE.CircleGeometry(120, 48), mat(PAL.grass));
  g.rotation.x = -Math.PI / 2; scene.add(g); pickGround.push(g);
  const yard = new THREE.Mesh(new THREE.PlaneGeometry(46, 40), mat(PAL.ground));
  yard.rotation.x = -Math.PI / 2; yard.position.set(0, 0.01, 4); scene.add(yard); pickGround.push(yard);
  // 돌길
  for (let z = 1; z < 21; z += 1.15) {
    const s = box(rand(2.2, 2.6), 0.08, 0.95, 0x9b958a, rand(-0.08, 0.08), 0.04, z);
    s.rotation.y = rand(-0.04, 0.04); pickGround.push(s);
  }
  // 먼 산 (겹겹이)
  const mcol = TIME === "night" ? [0x1f2740, 0x2a3350, 0x343f5e] : TIME === "dusk" ? [0x6b6077, 0x86778a, 0xa18f9a] : [0x7f97a3, 0x98aab2, 0xb3c0c2];
  for (let i = 0; i < 16; i++) {
    const a = (i / 16) * Math.PI * 2 + srand() * 0.3, r = 95 + srand() * 40, layer = i % 3;
    const m = new THREE.Mesh(new THREE.ConeGeometry(18 + srand() * 22, 22 + srand() * 26, 6), mat(mcol[layer]));
    m.position.set(Math.cos(a) * r, 6, Math.sin(a) * r - 10); m.rotation.y = srand() * 3; scene.add(m);
  }
}

// ---------------------------------------------------------------- 나무와 대나무
function cedar(x, z, s = 1) {
  cyl(0.18 * s, 0.25 * s, 1.6 * s, 6, 0x4a3628, x, 0.8 * s, z);
  const greens = TIME === "night" ? [0x1f3328, 0x253c2f] : [0x2f4a38, 0x3a5a42];
  for (let i = 0; i < 3; i++) {
    const c = new THREE.Mesh(new THREE.ConeGeometry((1.7 - i * 0.42) * s, (2.2 - i * 0.3) * s, 7), mat(greens[i % 2]));
    c.position.set(x, (1.9 + i * 1.15) * s, z); c.rotation.y = srand() * 3; scene.add(c);
  }
}
function bamboo(x, z) {
  const col = TIME === "night" ? 0x37503a : 0x7a9a5a;
  for (let i = 0; i < 7; i++) {
    const h = 5 + srand() * 4, bx = x + (srand() - 0.5) * 2, bz = z + (srand() - 0.5) * 2;
    const b = cyl(0.07, 0.09, h, 5, col, bx, h / 2, bz); b.rotation.z = (srand() - 0.5) * 0.12;
    const leaf = new THREE.Mesh(new THREE.IcosahedronGeometry(0.7 + srand() * 0.4, 0), mat(TIME === "night" ? 0x2a3d2c : 0x5f8a4a));
    leaf.position.set(bx, h - 0.2, bz); leaf.scale.y = 0.6; scene.add(leaf);
  }
}
for (let i = 0; i < 46; i++) {
  const a = srand() * Math.PI * 2, r = 25 + srand() * 22;
  const x = Math.cos(a) * r, z = Math.sin(a) * r - 4;
  if (Math.abs(x) < 4 && z > 18) continue;
  cedar(x, z, 0.9 + srand() * 0.9);
}
[[-17, 15], [-19, 8], [17, 16], [-16, -6], [16, -8], [-20, 0], [20, 2]].forEach(([x, z]) => bamboo(x, z));

// ---------------------------------------------------------------- 일주문
{
  const red = 0x8e3b2a;
  cyl(0.28, 0.32, 4.2, 8, red, -2.6, 2.1, 20.5); cyl(0.28, 0.32, 4.2, 8, red, 2.6, 2.1, 20.5);
  box(7, 0.45, 0.5, 0x5a2a20, 0, 4.0, 20.5);
  roof(8.4, 2.4, 1.0, 0.35, 0x353a41, 0, 4.75, 20.5);
}

// ---------------------------------------------------------------- 법당
const HALL = { x: 10, zFront: -2.4, zBack: -14, floor: 1.0 };
const pickHall = [];
{
  const g = new THREE.Group(); scene.add(g);
  const stone = 0x8c8579, wood = 0x7a5440, red = 0x8e3b2a, plaster = 0xe2d8c6, tile = 0x33383f;
  box(21, 0.6, 12.2, stone, 0, 0.3, -8.2, g);
  const floor = box(20.2, 0.4, 11.6, wood, 0, 0.8, -8.2, g); pickHall.push(floor);
  // 계단 3단
  for (let i = 0; i < 3; i++) {
    const s = box(6, 0.34 * (i + 1), 0.8, stone, 0, 0.17 * (i + 1), -0.4 - i * 0.8, g); pickHall.push(s);
  }
  // 기둥
  for (const x of [-9.4, -5.6, -1.9, 1.9, 5.6, 9.4]) for (const z of [-2.7, -13.5]) cyl(0.26, 0.3, 5.4, 10, red, x, 3.7, z, g);
  // 보
  box(20, 0.5, 0.5, 0x5a2a20, 0, 6.3, -2.7, g); box(20, 0.5, 0.5, 0x5a2a20, 0, 6.3, -13.5, g);
  box(0.5, 0.5, 11, 0x5a2a20, -9.4, 6.3, -8.1, g); box(0.5, 0.5, 11, 0x5a2a20, 9.4, 6.3, -8.1, g);
  // 처마 단청 띠
  box(20.4, 0.3, 0.3, 0x3d7a6a, 0, 6.65, -2.55, g);
  // 지붕 두 겹
  roof(27, 17, 1.6, 0.62, tile, 0, 7.6, -8.1, g);
  roof(17, 8.5, 2.3, 0.18, tile, 0, 9.4, -8.1, g);
  box(14.5, 0.35, 0.35, 0x2a2e33, 0, 10.55, -8.1, g);
  // 뒷벽과 옆 창살
  box(19, 5, 0.3, plaster, 0, 3.5, -13.85, g);
  for (const x of [-9.6, 9.6]) {
    box(0.2, 5, 10.6, plaster, x, 3.5, -8.1, g);
    for (let z = -12.8; z <= -3.4; z += 0.6) box(0.24, 3.2, 0.06, 0x6b4a36, x * 0.995, 3.6, z, g);
  }
  // 편액
  const board = new THREE.Mesh(new THREE.PlaneGeometry(3.4, 0.85), new THREE.MeshBasicMaterial({ map: textTexture("靜學堂") }));
  board.position.set(0, 5.6, -2.42); g.add(board);
  // 제단: 낮은 단, 둥근 창의 빛, 촛불
  box(6, 0.7, 1.4, 0x4b2e22, 0, 1.35, -12.8, g);
  const glow = new THREE.Mesh(new THREE.CircleGeometry(1.7, 40), new THREE.MeshBasicMaterial({ color: 0xffd58a, fog: false }));
  glow.position.set(0, 4.0, -13.68); g.add(glow);
  const ring = new THREE.Mesh(new THREE.RingGeometry(1.7, 1.95, 40), mat(0x6b4a36)); ring.position.set(0, 4.0, -13.67); g.add(ring);
  const halo = new THREE.Mesh(new THREE.CircleGeometry(3.4, 40), new THREE.MeshBasicMaterial({ color: 0xffc76b, transparent: true, opacity: 0.18, fog: false, depthWrite: false }));
  halo.position.set(0, 4.0, -13.66); g.add(halo);
  for (const x of [-2.2, -1.4, 1.4, 2.2]) {
    cyl(0.07, 0.07, 0.35, 6, 0xf1e6cf, x, 1.88, -12.6, g);
    const f = new THREE.Mesh(new THREE.SphereGeometry(0.06, 6, 4), new THREE.MeshBasicMaterial({ color: 0xffc35c })); f.position.set(x, 2.1, -12.6); g.add(f);
  }
  const altarLight = new THREE.PointLight(0xffc27a, TIME === "day" ? 6 : 14, 14, 1.6); altarLight.position.set(0, 3, -11.5); g.add(altarLight);
  // 처마 아래 등
  for (const x of [-7.5, -3.7, 3.7, 7.5]) {
    cyl(0.01, 0.01, 0.5, 4, 0x222222, x, 5.6, -2.3, g);
    const l = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.22, 0.45, 10), new THREE.MeshBasicMaterial({ color: TIME === "day" ? 0xf3dcc0 : 0xffc983 }));
    l.position.set(x, 5.15, -2.3); g.add(l);
  }
}

// ---------------------------------------------------------------- 방석
const SEATS = [];
const pickSeats = [];
{
  const xs = [-6.6, -4, -1.4, 1.4, 4, 6.6], zs = [-5.0, -7.0, -9.0, -11.0];
  zs.forEach((z) => xs.forEach((x) => {
    const id = SEATS.length;
    const c = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.16, 1.0), mat(id % 2 ? 0x5b5f86 : 0x7b4a4a));
    c.position.set(x, HALL.floor + 0.08, z); c.userData.seat = id; scene.add(c);
    const edge = new THREE.Mesh(new THREE.BoxGeometry(1.04, 0.04, 1.04), mat(0xd9c38f)); edge.position.set(x, HALL.floor + 0.02, z); scene.add(edge);
    SEATS.push({ x, z, mesh: c }); pickSeats.push(c);
  }));
}

// ---------------------------------------------------------------- 석등 (마당 네 개)
const lampMeshes = [];
for (const [x, z] of [[-3.6, 4], [3.6, 4], [-3.6, 12], [3.6, 12]]) {
  const st = 0x8f8a80;
  box(0.9, 0.3, 0.9, st, x, 0.15, z); cyl(0.18, 0.22, 1.3, 8, st, x, 0.95, z); box(0.8, 0.15, 0.8, st, x, 1.65, z);
  const fire = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.5, 0.55), new THREE.MeshBasicMaterial({ color: TIME === "day" ? 0xe9dcc5 : 0xffcf86 }));
  fire.position.set(x, 1.98, z); scene.add(fire); lampMeshes.push(fire);
  roof(1.3, 1.3, 0.45, 0.15, 0x7d786f, x, 2.45, z);
  if (TIME !== "day") { const pl = new THREE.PointLight(0xffb867, PAL.lamp * 3, 9, 1.8); pl.position.set(x, 2.1, z); scene.add(pl); }
}

// ---------------------------------------------------------------- 종각 (누르면 종을 친다)
const BELL = { x: 12.5, z: 9 };
let bellMesh;
{
  const red = 0x8e3b2a;
  box(4.4, 0.5, 4.4, 0x8c8579, BELL.x, 0.25, BELL.z);
  for (const dx of [-1.7, 1.7]) for (const dz of [-1.7, 1.7]) cyl(0.17, 0.2, 3.6, 8, red, BELL.x + dx, 2.3, BELL.z + dz);
  roof(5.6, 5.6, 1.4, 0.2, 0x33383f, BELL.x, 4.7, BELL.z);
  const pts = [];
  for (let i = 0; i <= 10; i++) { const t = i / 10; pts.push(new THREE.Vector2(0.35 + Math.pow(t, 1.6) * 0.75, 1.5 - t * 1.5)); }
  bellMesh = new THREE.Mesh(new THREE.LatheGeometry(pts, 16), mat(0x6e5a3c, { side: THREE.DoubleSide }));
  bellMesh.position.set(BELL.x, 2.0, BELL.z); bellMesh.userData.bell = true; scene.add(bellMesh);
}

// ---------------------------------------------------------------- 에마 걸이 (누르면 아래 에마 칸으로)
let emaRack;
{
  emaRack = new THREE.Group(); emaRack.position.set(-8, 0, 3.5); scene.add(emaRack);
  box(0.15, 1.8, 0.15, 0x6b4a36, -1.3, 0.9, 0, emaRack); box(0.15, 1.8, 0.15, 0x6b4a36, 1.3, 0.9, 0, emaRack);
  box(2.9, 0.12, 0.12, 0x6b4a36, 0, 1.75, 0, emaRack); box(2.9, 0.12, 0.12, 0x6b4a36, 0, 1.15, 0, emaRack);
  for (let i = 0; i < 9; i++) {
    const p = box(0.32, 0.24, 0.04, 0xd8b98c, -1.1 + (i % 5) * 0.55, i < 5 ? 1.55 : 0.97, 0.08, emaRack);
    p.rotation.z = rand(-0.15, 0.15);
  }
  emaRack.traverse((o) => { if (o.isMesh) o.userData.ema = true; });
}

// ---------------------------------------------------------------- 반딧불 (해 질 녘·밤)
let flies;
if (TIME !== "day" && !reduceMotion) {
  const n = 60, p = new Float32Array(n * 3), base = [];
  for (let i = 0; i < n; i++) {
    const v = [rand(-16, 16), rand(0.5, 3.5), rand(-2, 20)];
    base.push(v); p.set(v, i * 3);
  }
  const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(p, 3));
  flies = new THREE.Points(g, new THREE.PointsMaterial({ color: 0xfff1a6, size: 0.14, transparent: true, opacity: 0.9, depthWrite: false, blending: THREE.AdditiveBlending }));
  flies.userData.base = base; scene.add(flies);
}

// ---------------------------------------------------------------- 걸을 수 있는 곳과 높이
function heightAt(x, z) {
  if (Math.abs(x) < HALL.x && z < HALL.zFront && z > HALL.zBack) return HALL.floor;
  if (Math.abs(x) < 3 && z <= 0 && z >= HALL.zFront) return Math.min(HALL.floor, (-z / -HALL.zFront) * HALL.floor);
  return 0;
}
const inHall = (x, z) => Math.abs(x) < 9.6 && z < -2.5 && z > -13.6;
function clampWalk(x, z, wantHall) {
  if (wantHall) return [Math.max(-9, Math.min(9, x)), Math.max(-13.1, Math.min(-3.0, z))];
  x = Math.max(-21, Math.min(21, x)); z = Math.max(-18, Math.min(19.5, z));
  if (Math.abs(x) < 10.8 && z < 0.6) z = 0.6;               // 법당 기단 앞까지만
  const dx = x - BELL.x, dz = z - BELL.z, d = Math.hypot(dx, dz);
  if (d < 2.8) { x = BELL.x + (dx / (d || 1)) * 2.8; z = BELL.z + (dz / (d || 1)) * 2.8; }
  return [x, z];
}
// 마당 ↔ 법당은 계단을 거쳐 간다
function route(fx, fz, tx, tz, toHall) {
  const fromHall = inHall(fx, fz);
  const [cx, cz] = clampWalk(tx, tz, toHall);
  const pts = [];
  if (fromHall !== toHall) {
    const sx = Math.max(-2, Math.min(2, fromHall ? fx : cx));
    if (fromHall) { pts.push([sx, -3.0], [sx, 0.9]); } else { pts.push([sx, 0.9], [sx, -3.0]); }
  }
  pts.push([cx, cz]);
  return pts;
}

// ---------------------------------------------------------------- 캐릭터
function nameSprite(text, me) {
  const t = textTexture(text, { w: 384, h: 96, font: "600 40px 'Noto Sans KR', sans-serif", fg: me ? "#fff" : "#2a2622", bg: me ? "rgba(30,28,24,0.82)" : "rgba(255,252,246,0.86)", radius: 48 });
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, depthTest: false, transparent: true }));
  s.scale.set(1.5, 0.375, 1); s.position.y = 1.72; s.renderOrder = 10; return s;
}
// 동자 수험생: 큰 얼굴, 털모자(방울), 목도리, 책가방. 모자·목도리·장갑이 학생이 고른 색
const SKIN = 0xf6d3b8, INK = 0x2a2420;
const toon = (c, o = {}) => new THREE.MeshToonMaterial({ color: c, ...o });
const sharedM = { robe: toon(0xeee4d2), skin: toon(SKIN), pom: toon(0xfff7ec), bag: toon(0x8a6a4f), bagTop: toon(0x6d523c), shoe: toon(0x5a4a3e),
  eye: new THREE.MeshBasicMaterial({ color: INK }), shine: new THREE.MeshBasicMaterial({ color: 0xffffff }),
  blush: new THREE.MeshBasicMaterial({ color: 0xf3a08e, transparent: true, opacity: 0.65 }) };
function part(g, m, x, y, z, parent) { const o = new THREE.Mesh(g, m); o.position.set(x, y, z); parent.add(o); return o; }
class Avatar {
  constructor({ color, nick, me = false }) {
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
    for (const sd of [-1, 1]) {
      const e = part(new THREE.SphereGeometry(0.058, 12, 8), sharedM.eye, sd * 0.15, 1.08, 0.45, U); e.scale.set(1, 1.25, 0.6);
      part(new THREE.SphereGeometry(0.016, 6, 4), sharedM.shine, sd * 0.15 + 0.015, 1.105, 0.48, U);
      const bl = part(new THREE.CircleGeometry(0.06, 14), sharedM.blush, sd * 0.25, 1.0, 0.44, U); bl.lookAt(sd * 1, 1.0, 3);
    }
    const mouth = part(new THREE.TorusGeometry(0.035, 0.011, 6, 12, Math.PI), sharedM.eye, 0, 1.01, 0.46, U); mouth.rotation.z = Math.PI;
    part(new THREE.BoxGeometry(0.42, 0.42, 0.18), sharedM.bag, 0, 0.5, -0.38, U);
    part(new THREE.BoxGeometry(0.44, 0.12, 0.2), sharedM.bagTop, 0, 0.66, -0.38, U);
    this.hands = [-1, 1].map((sd) => { const h = part(new THREE.SphereGeometry(0.1, 12, 8), this.colorMat, sd * 0.42, 0.42, 0.06, U); h.userData.side = sd; return h; });
    this.feet = [-1, 1].map((sd) => { const f = part(new THREE.SphereGeometry(0.11, 12, 8), sharedM.shoe, sd * 0.15, 0.06, 0.08, this.g); f.scale.set(1, 0.6, 1.4); f.userData.side = sd; return f; });
    const shadow = new THREE.Mesh(new THREE.CircleGeometry(0.5, 20), new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.16, depthWrite: false }));
    shadow.rotation.x = -Math.PI / 2; shadow.position.y = 0.02; this.g.add(shadow);
    this.ring = new THREE.Mesh(new THREE.RingGeometry(0.55, 0.68, 32), new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.0, depthWrite: false, side: THREE.DoubleSide }));
    this.ring.rotation.x = -Math.PI / 2; this.ring.position.y = 0.04; this.g.add(this.ring);
    this.tag = nameSprite(nick, me); this.tag.position.y = 2.15; this.g.add(this.tag);
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
    const sitting = this.pose === "sit" || this.pose === "breathe" || (this.pose === "gassho" && this.seat !== null) || (this.pose === "bow" && this.seat !== null);
    this.g.position.set(this.pos.x, ground + (sitting ? 0.16 : 0), this.pos.z);
    this.g.rotation.y = this.yaw;
    // 몸짓
    const walk = this.pose === "walk";
    const bob = walk && !reduceMotion ? Math.abs(Math.sin(this.t * 11)) * 0.07 : 0;
    this.upper.position.y = (sitting ? -0.06 : 0) + bob;
    this.upper.rotation.z = walk && !reduceMotion ? Math.sin(this.t * 11) * 0.05 : 0;
    const breathe = (this.pose === "breathe" || this.focus) && !reduceMotion ? 1 + Math.sin(this.t * (Math.PI * 2 / 6)) * 0.025 : 1;
    this.upper.scale.set(breathe, sitting ? 0.92 : 1, breathe);
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
    this.feet.forEach((f) => {
      const s = f.userData.side;
      if (sitting) { f.position.set(s * 0.22, 0.02, 0.3); f.rotation.y = -s * 1.1; }
      else { const sw = walk && !reduceMotion ? Math.sin(ph + (s > 0 ? Math.PI : 0)) : 0;
        f.position.set(s * 0.15, 0.06 + Math.max(0, sw) * 0.07, 0.08 + sw * 0.12); f.rotation.y = 0; }
    });
    if (!reduceMotion) this.pom.position.x = Math.sin(this.t * (walk ? 11 : 1.5)) * (walk ? 0.03 : 0.01);
    if (this.me) this.tag.visible = this.seat === null;
    const ringTarget = this.focus ? 0.55 + Math.sin(this.t * 2) * 0.15 : 0;
    this.ring.material.opacity += (ringTarget - this.ring.material.opacity) * Math.min(1, dt * 3);
  }
  bow() { this.pose = "bow"; this.bowT = 1.6; }
  dispose() { scene.remove(this.g); }
}

// ---------------------------------------------------------------- 나
const colors = root.dataset.colors.split(",");
let myColor = root.dataset.color;
const meName = (document.querySelector(".m-who") || {}).textContent || "나";
const me = new Avatar({ color: myColor, nick: meName.trim() || "나", me: true });
me.place(0, 11.5, Math.PI);
let state = "free";      // free | sitting | focus
let mySeat = null, planMin = parseInt(root.dataset.plan, 10) || 25, focusStart = 0;

// ---------------------------------------------------------------- 카메라 (내 캐릭터를 따라 돈다)
const cam = { yaw: 0, pitch: 0.42, dist: isTouch ? 9.5 : 8.5, tYaw: 0, tPitch: 0.42, tDist: isTouch ? 9.5 : 8.5 };
const camTarget = new THREE.Vector3();
function updateCamera(dt, snap) {
  const k = snap ? 1 : Math.min(1, dt * 5);
  cam.yaw += (cam.tYaw - cam.yaw) * k; cam.pitch += (cam.tPitch - cam.pitch) * k; cam.dist += (cam.tDist - cam.dist) * k;
  const tgt = new THREE.Vector3(me.g.position.x, me.g.position.y + (state === "free" ? 1.1 : 0.9), me.g.position.z);
  camTarget.lerp(tgt, snap ? 1 : Math.min(1, dt * 6));
  const cx = camTarget.x + Math.sin(cam.yaw) * Math.cos(cam.pitch) * cam.dist;
  const cz = camTarget.z + Math.cos(cam.yaw) * Math.cos(cam.pitch) * cam.dist;
  const cy = camTarget.y + Math.sin(cam.pitch) * cam.dist;
  camera.position.set(cx, Math.max(cy, heightAt(cx, cz) + 0.6), cz);
  camera.lookAt(camTarget);
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
  if (drag.moved) { cam.tYaw -= dx * 0.0065; cam.tPitch = Math.max(0.12, Math.min(1.25, cam.tPitch + dy * 0.0045)); }
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
  const hits = ray.intersectObjects([...pickSeats, bellMesh, ...emaRack.children, ...pickHall, ...pickGround], false);
  if (!hits.length) return;
  const h = hits[0], o = h.object;
  if (o.userData.seat !== undefined) return goSit(o.userData.seat);
  if (o.userData.bell) return goBell();
  if (o.userData.ema) { document.getElementById("notes").scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" }); return; }
  if (state === "focus") return whisper("집중 중에는 자리에 머물러요. 일어나려면 '그만하기'를 누르세요.");
  const toHall = pickHall.includes(o) || inHall(h.point.x, h.point.z);
  standUp(true);
  me.walkTo(route(me.pos.x, me.pos.z, h.point.x, h.point.z, toHall));
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
  if (k === " ") { e.preventDefault(); act("gassho"); }
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
  const hall = inHall(me.pos.x, me.pos.z);
  const onSteps = Math.abs(nx) < 2.6 && nz > -3.2 && nz < 1.0;
  const [x, z] = onSteps ? [nx, nz] : clampWalk(nx, nz, hall);
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
  if (occupiedSeats().has(id)) return whisper("그 방석에는 이미 누가 앉아 있어요.");
  const s = SEATS[id];
  standUp(true);
  me.walkTo(route(me.pos.x, me.pos.z, s.x, s.z + 0.9, true).concat([[s.x, s.z]]));
  me.onArrive = () => { sitAt(id); };
  sync(true);
}
function sitAt(id) {
  const s = SEATS[id];
  me.place(s.x, s.z); me.yaw = Math.PI; me.targetYaw = Math.PI; me.pose = "sit"; me.seat = id; mySeat = id;
  state = "sitting"; camBehind(isTouch ? 6.2 : 5.8, 0.36);
  audio.sfx("cushion");
  whisper("방석에 앉았어요. 시간을 고르고 집중을 시작해 보세요.");
  render(); sync(true);
}
function standUp(silent) {
  if (state === "free") return;
  if (state === "focus") return;
  state = "free"; me.seat = null; mySeat = null; me.pose = "stand"; cam.tDist = isTouch ? 9.5 : 8.5; cam.tPitch = 0.42;
  if (!silent) whisper("천천히 일어났어요.");
  render(); sync(true);
}
function goBell() {
  if (state === "focus") return whisper("집중이 끝나면 종을 쳐 보세요.");
  standUp(true);
  const ax = BELL.x - 3.0, az = BELL.z;
  me.walkTo(route(me.pos.x, me.pos.z, ax, az, false));
  me.onArrive = () => { me.targetYaw = Math.atan2(BELL.x - me.pos.x, BELL.z - me.pos.z); ringBell(); };
  sync(true);
}
let bellSwing = 0;
function ringBell() { bellSwing = 1; audio.sfx("bell"); whisper("데엥— 종소리가 산을 건너가요."); }

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
};
const actionsEl = $("[data-actions]"), plansEl = $("[data-plans]");
function btn(id, label, primary) { return `<button type="button" class="w3-act${primary ? " is-primary" : ""}" data-act="${id}">${ICON[id]}<span>${label}</span></button>`; }
function render() {
  let html = "";
  if (state === "free") html = btn("sit", "앉기", true) + btn("gassho", "합장") + btn("bow", "절하기") + btn("moktak", "목탁") + btn("bell", "종 치기");
  else if (state === "sitting") html = btn("focus", "집중 시작", true) + btn("breathe", "숨 고르기") + btn("moktak", "목탁") + btn("gassho", "합장") + btn("stand", "일어나기");
  else html = btn("breathe", "숨 고르기") + btn("moktak", "목탁") + btn("stop", "그만하기");
  actionsEl.innerHTML = html;
  plansEl.hidden = state !== "sitting";
  $("[data-timer]").hidden = state !== "focus";
  stage.classList.toggle("is-focus", state === "focus");
  stage.classList.toggle("is-seated", state !== "free");
  $("[data-hint]").textContent = state === "free" ? (isTouch ? "바닥을 누르면 걸어가요 · 끌어서 둘러보기 · 방석을 누르면 앉아요" : "바닥을 누르면 걸어가요 · 끌어서 둘러보기 · 방석을 누르면 앉아요 · 스페이스는 합장")
    : state === "sitting" ? "시간을 고르고 '집중 시작'을 누르세요" : "화면을 닫아도 여기까지 기록돼요";
}
actionsEl.addEventListener("click", (e) => { const b = e.target.closest("[data-act]"); if (b) act(b.dataset.act); });
function act(id) {
  if (id === "sit") { const s = nearestFreeSeat(); return s === null ? whisper("빈 방석이 없어요.") : goSit(s); }
  if (id === "stand") return standUp();
  if (id === "bell") return goBell();
  if (id === "gassho") { me.pose = me.pose === "gassho" ? (me.seat !== null ? "sit" : "stand") : "gassho"; if (me.pose === "gassho") whisper("두 손을 모으고, 오늘 공부할 것 하나를 떠올려요."); sync(true); return; }
  if (id === "bow") { me.bow(); whisper("천천히 고개를 숙여요."); sync(true); return; }
  if (id === "moktak") { audio.sfx("moktak"); moktakPop(); return; }
  if (id === "breathe") return breathe();
  if (id === "focus") return startFocus();
  if (id === "stop") return finishFocus(false);
}

// 목탁: 캐릭터 앞에 잠깐 나타났다 사라짐
const moktakObj = new THREE.Mesh(new THREE.SphereGeometry(0.22, 12, 8), mat(0x9a5a2e)); moktakObj.scale.set(1.2, 0.85, 1); moktakObj.visible = false; scene.add(moktakObj);
let moktakT = 0;
function moktakPop() { moktakT = 0.9; moktakObj.visible = true; }

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
  const prev = me.pose; me.pose = me.seat !== null ? "breathe" : prev;
  const steps = [["숨을 천천히 들이쉬어요", 4000], ["잠깐 멈추고", 2000], ["어깨 힘을 빼고 길게 내쉬어요", 6000]];
  for (let r = 0; r < 3 && breathing; r++) for (const [t, ms] of steps) { whisper(t, ms - 150); await new Promise((ok) => setTimeout(ok, ms)); }
  whisper("좋아요. 다시 공부로 돌아가요.");
  if (me.pose === "breathe") me.pose = me.seat !== null ? "sit" : "stand";
  breathing = false;
}

// ---------------------------------------------------------------- 집중 타이머 (서버가 잰 시간만 인정)
const clockEl = $("[data-clock]"), msgEl = $("[data-msg]");
const pad = (n) => (n < 10 ? "0" : "") + n;
function chosenPlan() { const c = plansEl.querySelector('input[name="plan"]:checked'); return c ? parseInt(c.value, 10) : 25; }
function startFocus() {
  if (state !== "sitting") return;
  planMin = chosenPlan(); state = "focus"; focusStart = Date.now(); me.focus = true;
  camBehind(isTouch ? 5.4 : 5.0, 0.3);
  audio.sfx("bowl"); audio.duck(true);
  whisper(planMin + "분, 지금부터 고요히.");
  render(); post(root.dataset.beat, { action: "start", plan: planMin }).then(onBeat).catch(() => {}); sync(true);
}
let finishing = false;
function finishFocus(complete) {
  if (state !== "focus" || finishing) return; finishing = true;
  const minutes = Math.floor((Date.now() - focusStart) / 60000);
  post(root.dataset.done, { minutes: complete ? planMin : minutes }).then((d) => {
    state = "sitting"; me.focus = false; audio.duck(false); audio.sfx("bowl");
    camBehind(isTouch ? 6.2 : 5.8, 0.36); render();
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
    seat: mySeat === null ? "" : mySeat, color: myColor };
}
function beatLoop() {
  if (!entered || beatBusy || document.hidden) return;
  const now = Date.now(), gap = me.moving || keyWalking > 0 ? 1800 : dirty ? 900 : 7000;
  if (now - lastSent < gap) return;
  beatBusy = true; lastSent = now; dirty = false;
  post(root.dataset.beat, myPayload()).then(onBeat).catch(() => {}).finally(() => { beatBusy = false; });
}
setInterval(beatLoop, 300);
function onBeat(d) {
  if (!d || !d.members) return;
  const seen = new Set();
  d.members.forEach((m) => {
    if (m.me) return; seen.add(m.id);
    let o = others.get(m.id);
    if (!o) {
      o = new Avatar({ color: m.color, nick: m.nick }); o.place(m.x, m.z, m.ry); others.set(m.id, o);
      if (entered) whisper(`${m.nick}님이 산사에 들어왔어요.`, 2600);
    }
    o.setColor(m.color);
    o.focus = m.status === "focus";
    o.seat = m.seat === null || m.seat === undefined ? null : m.seat;
    if (o.seat !== null && SEATS[o.seat]) {
      const s = SEATS[o.seat];
      if (Math.hypot(o.pos.x - s.x, o.pos.z - s.z) > 0.05) o.walkTo(route(o.pos.x, o.pos.z, s.x, s.z + 0.9, true).concat([[s.x, s.z]]));
      o.onArrive = () => { o.pose = m.pose === "stand" ? "sit" : m.pose; o.yaw = Math.PI; o.targetYaw = Math.PI; };
      if (!o.moving) { o.pose = ["gassho", "bow", "breathe"].includes(m.pose) ? m.pose : "sit"; o.targetYaw = Math.PI; }
    } else {
      const far = Math.hypot(o.pos.x - m.x, o.pos.z - m.z);
      if (far > 25) o.place(m.x, m.z, m.ry);
      else if (far > 0.15) o.walkTo(route(o.pos.x, o.pos.z, m.x, m.z, inHall(m.x, m.z)));
      else if (!o.moving) { o.pose = m.pose === "walk" ? "stand" : m.pose; o.targetYaw = m.ry; }
      if (m.pose === "bow" && o.bowT <= 0 && !o.moving) o.bow();
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
    const b = document.createElement("b"); b.textContent = m.nick + (m.me ? " (나)" : "");
    const s = document.createElement("span");
    s.textContent = (m.status === "focus" ? `집중 ${m.elapsed}/${m.plan}분` : m.seat !== null && m.seat !== undefined ? "방석에 앉음" : "산책 중") + ` · 오늘 ${m.today}분`;
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
  let ctx = null, master = null, on = false, buffers = {}, loops = {}, keep = null, chimeTimer = 0;
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
      loop("wind", 0.85); loop(TIME === "day" ? "birds" : "crickets", TIME === "day" ? 0.55 : 0.5); loop("chimes", 0.0); loop("steps", 0.0, 1);
      ["moktak", "bowl"].forEach(load);
      // 풍경: 가끔 바람이 불 때만 들리게
      const chime = () => { if (!on) return; const l = loops.chimes; if (l) { const t = ctx.currentTime; l.g.gain.cancelScheduledValues(t); l.g.gain.setValueAtTime(l.g.gain.value, t); l.g.gain.linearRampToValueAtTime(rand(0.2, 0.42), t + 3); l.g.gain.linearRampToValueAtTime(0.0, t + rand(9, 16)); } chimeTimer = setTimeout(chime, rand(14000, 30000)); };
      chimeTimer = setTimeout(chime, 4000);
    } catch (_) {}
    label();
  }
  function stop() {
    on = false; clearTimeout(chimeTimer); loops = {};
    if (master) { master.disconnect(); master = null; }
    if (ctx) { ctx.close(); ctx = null; buffers = {}; }
    mediaMode(false); label();
  }
  btnEl.addEventListener("click", () => (on ? stop() : start()));
  let walkLevel = 0;
  return {
    start, stop, get on() { return on; },
    walking(v, indoor) {
      const l = loops.steps; if (!l || !ctx) return;
      const target = v ? (indoor ? 0.18 : 0.55) : 0; if (Math.abs(target - walkLevel) < 0.01) return; walkLevel = target;
      l.g.gain.setTargetAtTime(target, ctx.currentTime, 0.12); l.s.playbackRate.setTargetAtTime(indoor ? 1.25 : 1, ctx.currentTime, 0.1);
    },
    duck(v) { if (master && ctx) master.gain.setTargetAtTime(v ? 0.6 : 0.9, ctx.currentTime, 1.2); },
    sfx(name) {
      if (name === "moktak") one("moktak", 0.9, rand(0.97, 1.03));
      else if (name === "bowl") one("bowl", 0.75);
      else if (name === "bell") one("bowl", 1.0, 0.42, 1400);
      else if (name === "cushion") one("steps", 0.25, 0.7, 900);
    },
  };
})();

// ---------------------------------------------------------------- 들어가기 (소리 재생은 사용자가 눌러야 시작된다)
let entered = false;
$("[data-enter-btn]").addEventListener("click", () => {
  entered = true; $("[data-enter]").hidden = true; audio.start();
  whisper("고요한 산사예요. 법당 방석에 앉아 집중을 시작해 보세요.", 4200);
  render(); sync(true);
  if (root.dataset.status === "focus") {      // 집중 중에 나갔다 돌아온 경우: 빈 방석에 앉혀 이어간다
    const s = nearestFreeSeat();
    if (s !== null) { sitAt(s); state = "focus"; me.focus = true; planMin = parseInt(root.dataset.plan, 10) || 25;
      focusStart = Date.now() - (parseInt(root.dataset.elapsed, 10) || 0) * 60000; camBehind(5.0, 0.3); render(); }
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
updateCamera(0, true);  // 처음엔 일주문 쪽에서 법당을 바라본다
function frame() {
  requestAnimationFrame(frame);
  if (document.hidden) return;
  const dt = Math.min(0.05, clock.getDelta());
  keyMove(dt);
  if (keyWalking > 0) { keyWalking -= dt; if (keyWalking <= 0 && me.pose === "walk" && !me.moving) me.pose = "stand"; }
  me.update(dt); others.forEach((o) => o.update(dt));
  audio.walking(me.pose === "walk", inHall(me.pos.x, me.pos.z));
  if (marker.material.opacity > 0) { marker.material.opacity -= dt * 0.8; marker.scale.multiplyScalar(1 + dt * 0.6); }
  if (bellSwing > 0) { bellSwing -= dt * 0.35; bellMesh.rotation.x = Math.sin((1 - bellSwing) * 14) * 0.12 * bellSwing; }
  if (moktakT > 0) {
    moktakT -= dt; const f = new THREE.Vector3(Math.sin(me.yaw), 0, Math.cos(me.yaw));
    moktakObj.position.set(me.g.position.x + f.x * 0.6, me.g.position.y + 0.5, me.g.position.z + f.z * 0.6);
    moktakObj.scale.set(1.2, 0.85 * (1 + Math.max(0, moktakT - 0.7) * 1.5), 1); if (moktakT <= 0) moktakObj.visible = false;
  }
  if (flies) {
    const p = flies.geometry.attributes.position, b = flies.userData.base, t = clock.elapsedTime;
    for (let i = 0; i < b.length; i++) p.setXYZ(i, b[i][0] + Math.sin(t * 0.3 + i) * 0.8, b[i][1] + Math.sin(t * 0.7 + i * 2) * 0.3, b[i][2] + Math.cos(t * 0.25 + i) * 0.8);
    p.needsUpdate = true; flies.material.opacity = 0.55 + Math.sin(t * 2) * 0.3;
  }
  // 집중 중에는 안개를 가까이 당겨 주변을 흐리게
  const fogFar = state === "focus" ? 22 : 95, fogNear = state === "focus" ? 4 : 26;
  scene.fog.far += (fogFar - scene.fog.far) * Math.min(1, dt * 1.5); scene.fog.near += (fogNear - scene.fog.near) * Math.min(1, dt * 1.5);
  updateCamera(dt);
  renderer.render(scene, camera);
  // 느린 기기면 화질을 낮춘다
  frames++; slowT += dt;
  if (slowT > 3) { const fps = frames / slowT; if (fps < 28 && pixelRatio > 1) { pixelRatio = Math.max(1, pixelRatio - 0.5); renderer.setPixelRatio(pixelRatio); resize(); } frames = 0; slowT = 0; }
}
render();
document.fonts && document.fonts.ready.then(() => { me.g.remove(me.tag); me.tag = nameSprite(meName.trim() || "나", true); me.g.add(me.tag); });
requestAnimationFrame(frame);
