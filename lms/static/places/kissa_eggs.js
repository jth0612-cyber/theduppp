// 골목 찻집 · 건물 사이 틈에 숨은 것들 (여섯).
// 골목을 걷다가 집과 집 사이를 들여다보면 보인다. 누르면 반응하고, 몇 개 찾았는지 알려 준다.
// 모델은 모두 앞(+z)을 보게 만든 뒤, 골목 쪽을 향하도록 돌려 놓는다. 틈이 좁아서(0.75~1.15m) 폭은 ±0.45 안쪽.
export function buildEggs(K, { dark }) {
  const { THREE, scene, textTexture } = K;
  const V2 = (x, y) => new THREE.Vector2(x, y), V3 = (x, y, z) => new THREE.Vector3(x, y, z);
  const picks = [], tick = [], onTap = {};
  // 재질: 매끈한 면 + 어두운 틈에서도 형태가 읽히게 약한 자체 밝기
  const L = (color, e = dark ? 0.3 : 0.12, o = {}) => new THREE.MeshLambertMaterial({ color, emissive: new THREE.Color(color).multiplyScalar(e), ...o });
  const B = (color, o = {}) => new THREE.MeshBasicMaterial({ color, ...o });
  const put = (geo, m, parent, x = 0, y = 0, z = 0, rx = 0, ry = 0, rz = 0) => { const o = new THREE.Mesh(geo, m); o.position.set(x, y, z); o.rotation.set(rx, ry, rz); o.userData.noOcclude = true; parent.add(o); return o; };
  const bx = (w, h, d) => new THREE.BoxGeometry(w, h, d), sp = (r, a = 16, b = 12) => new THREE.SphereGeometry(r, a, b), cy = (a, b, h, s = 16, open = false) => new THREE.CylinderGeometry(a, b, h, s, 1, open);
  const lathe = (pts, seg = 20) => new THREE.LatheGeometry(pts.map(([x, y]) => V2(x, y)), seg);
  const tube = (pts, r, seg = 24) => new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts.map((p) => V3(...p))), seg, r, 8);
  const canvasTex = (w, h, draw) => { const c = document.createElement("canvas"); c.width = w; c.height = h; draw(c.getContext("2d"), w, h); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; return t; };
  // 은은한 빛 번짐 (가운데가 밝고 가장자리로 사라진다)
  const glowTex = canvasTex(64, 64, (x) => { const g = x.createRadialGradient(32, 32, 0, 32, 32, 32); g.addColorStop(0, "rgba(255,255,255,1)"); g.addColorStop(0.35, "rgba(255,255,255,.45)"); g.addColorStop(1, "rgba(255,255,255,0)"); x.fillStyle = g; x.fillRect(0, 0, 64, 64); });
  const halo = (color, size, parent, x, y, z, op = 0.8) => { const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color, transparent: true, opacity: op, depthWrite: false, blending: THREE.AdditiveBlending })); s.scale.set(size, size, 1); s.position.set(x, y, z); parent.add(s); return s; };
  const pool = (color, w, d, parent, x, z, op = 0.5) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d), new THREE.MeshBasicMaterial({ map: glowTex, color, transparent: true, opacity: op, depthWrite: false, blending: THREE.AdditiveBlending })); m.rotation.x = -Math.PI / 2; m.position.set(x, 0.025, z); parent.add(m); return m; };
  // 나무 판자 질감 (세로 판자 + 나뭇결)
  const plankTex = (base, line, n = 5) => canvasTex(128, 128, (x) => { x.fillStyle = base; x.fillRect(0, 0, 128, 128); for (let i = 0; i < 260; i++) { x.fillStyle = `rgba(${Math.random() < 0.5 ? "0,0,0" : "255,235,200"},${Math.random() * 0.06})`; x.fillRect(Math.random() * 128, Math.random() * 128, 1 + Math.random() * 2, 6 + Math.random() * 30); } x.fillStyle = line; for (let i = 1; i < n; i++) x.fillRect((i * 128) / n - 1, 0, 2, 128); });
  const woodDark = new THREE.MeshLambertMaterial({ map: plankTex("#3b2c22", "#221912"), emissive: 0x0c0806 });
  const woodWarm = new THREE.MeshLambertMaterial({ map: plankTex("#8a5e36", "#5a3c22", 4), emissive: dark ? 0x241408 : 0x0c0704 });
  const stone = L(0x8f8c86, dark ? 0.22 : 0.08), stoneD = L(0x6c6a66, dark ? 0.22 : 0.08);

  function spot(id, x, z, faceRight, hit) {             // 틈 하나: 뒤를 막는 판자벽 + 누르는 투명 상자
    const g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = faceRight ? -Math.PI / 2 : Math.PI / 2; scene.add(g);
    const h = new THREE.Mesh(bx(hit[0], hit[1], hit[2]), new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false }));
    h.position.set(0, hit[1] / 2, hit[3] || 0); h.userData.action = "egg"; h.userData.egg = id; h.userData.noOcclude = true; g.add(h); picks.push(h);
    return g;
  }
  const fence = (g, w, z = -1.5, h = 2.3) => put(bx(w, h, 0.06), woodDark, g, 0, h / 2, z);

  // ================================================================ ① 검은 고양이
  {
    const g = spot("cat", -3.75, -21, false, [0.95, 1.5, 1.0]); fence(g, 1.0);
    // 나무 상자 둘 (아래는 크게, 위는 비뚤게) + 우유 접시
    put(bx(0.62, 0.36, 0.5), woodWarm, g, 0, 0.18, -0.1); put(bx(0.66, 0.03, 0.54), L(0x5a3c22), g, 0, 0.37, -0.1);
    put(bx(0.46, 0.3, 0.42), woodWarm, g, 0.04, 0.535, -0.12, 0, 0.18, 0);
    put(cy(0.085, 0.07, 0.02, 20), L(0x6f9ac8), g, -0.24, 0.02, 0.33); put(cy(0.07, 0.07, 0.006, 20), B(0xf6f3ea), g, -0.24, 0.033, 0.33);
    const fur = L(0x34343e, dark ? 0.5 : 0.28), white = L(0xf2efe8, dark ? 0.4 : 0.12), pink = L(0xe79aa0, 0.4);
    const cat = new THREE.Group(); cat.position.set(0.04, 0.685, -0.1); cat.rotation.y = 0.18; g.add(cat);
    put(lathe([[0, 0], [0.13, 0.01], [0.165, 0.09], [0.15, 0.2], [0.105, 0.31], [0.07, 0.36], [0, 0.37]]), fur, cat);           // 앉은 몸 (아래가 통통한 물방울)
    put(sp(0.085), white, cat, 0, 0.2, 0.085).scale.set(0.8, 1.15, 0.5);                                                         // 가슴 흰 털
    for (const sx of [-1, 1]) { put(cy(0.03, 0.034, 0.24, 10), fur, cat, sx * 0.05, 0.12, 0.125); put(sp(0.04), white, cat, sx * 0.05, 0.02, 0.15).scale.set(1, 0.6, 1.25); }   // 앞다리와 흰 발
    for (const sx of [-1, 1]) put(sp(0.07), fur, cat, sx * 0.13, 0.05, 0.02).scale.set(0.9, 0.7, 1.3);                           // 뒷발
    const tail = new THREE.Group(); tail.position.set(0, 0.04, -0.13); cat.add(tail);
    put(tube([[0, 0, 0], [0.1, 0.01, -0.07], [0.21, 0.02, -0.03], [0.26, 0.05, 0.09], [0.22, 0.1, 0.19], [0.17, 0.16, 0.22]], 0.028), fur, tail);
    put(sp(0.03), white, tail, 0.17, 0.16, 0.22);
    const head = new THREE.Group(); head.position.set(0, 0.46, 0.03); cat.add(head);
    put(sp(0.135, 20, 16), fur, head).scale.set(1.08, 0.92, 0.95);
    for (const sx of [-1, 1]) {
      put(sp(0.05), fur, head, sx * 0.075, -0.035, 0.085).scale.set(1.1, 0.8, 0.9);                                              // 볼
      const ear = new THREE.Group(); ear.position.set(sx * 0.085, 0.1, 0); ear.rotation.z = -sx * 0.28; head.add(ear);
      put(new THREE.ConeGeometry(0.052, 0.11, 4), fur, ear, 0, 0.04, 0, 0, Math.PI / 4, 0).scale.set(1, 1, 0.55);
      put(new THREE.ConeGeometry(0.03, 0.07, 4), pink, ear, 0, 0.035, 0.012, 0, Math.PI / 4, 0).scale.set(1, 1, 0.4);
      if (sx > 0) g.userData.earR = ear;
      for (let i = -1; i <= 1; i++) put(bx(0.13, 0.004, 0.004), B(0xf4f1ea), head, sx * 0.14, -0.04 + i * 0.012, 0.1, 0, sx * 0.25, sx * i * 0.16);   // 수염
    }
    put(sp(0.014), pink, head, 0, -0.022, 0.128);                                                                                // 코
    const eyes = [-1, 1].map((sx) => {
      const e = new THREE.Group(); e.position.set(sx * 0.058, 0.02, 0.105); e.rotation.y = sx * 0.3; head.add(e);
      put(sp(0.033, 14, 12), B(0xd9e86a), e).scale.set(1, 1.08, 0.45);
      put(sp(0.018, 10, 10), B(0x111111), e, 0, 0, 0.012).scale.set(0.42, 1.25, 0.4);
      put(sp(0.007, 6, 6), B(0xffffff), e, 0.011, 0.014, 0.018);
      return e;
    });
    put(new THREE.TorusGeometry(0.098, 0.013, 8, 24), L(0xc0392b, 0.45), cat, 0, 0.365, 0.015, Math.PI / 2 + 0.12, 0, 0);     // 빨간 목줄
    const bell = put(sp(0.022, 10, 8), L(0xe8c14a, 0.6), cat, 0, 0.335, 0.105);
    let blinkUntil = 0, look = 0;
    tick.push((dt, t, E, now) => {
      tail.rotation.y = Math.sin(t * 1.5) * 0.45 + Math.sin(t * 0.6) * 0.2;
      const closed = now < blinkUntil || (t % 4.7) < 0.13; eyes.forEach((e) => { e.scale.y += ((closed ? 0.1 : 1) - e.scale.y) * Math.min(1, dt * 22); });
      if (g.userData.earR) g.userData.earR.rotation.x = (t % 6.1) < 0.25 ? Math.sin(((t % 6.1) / 0.25) * Math.PI) * 0.5 : 0;        // 가끔 귀를 쫑긋
      // 지나가는 사람을 눈으로 따라간다
      const dz = E.me.pos.z - (-21), want = Math.max(-0.9, Math.min(0.9, Math.atan2(-dz, 3.5))) - cat.rotation.y;
      look += (want - look) * Math.min(1, dt * 3); head.rotation.y = look; head.rotation.z = Math.sin(t * 0.7) * 0.04;
      bell.position.x = Math.sin(t * 3) * 0.002;
    });
    onTap.cat = (E, now) => { blinkUntil = now + 1.5; E.blip([[720, 520, 0.16], [540, 660, 0.2]], 0.06); };
  }

  // ================================================================ ② 여우 사당
  {
    const g = spot("shrine", -3.95, -7.7, false, [1.1, 1.55, 1.3]); fence(g, 1.15, -1.7);
    put(bx(1.0, 0.05, 1.5), stoneD, g, 0, 0.025, -0.55);
    for (let i = 0; i < 3; i++) put(bx(0.32, 0.03, 0.2), stone, g, (i % 2 ? 0.03 : -0.03), 0.065, 0.02 - i * 0.26, 0, (i - 1) * 0.08, 0);   // 디딤돌
    for (let i = 0; i < 7; i++) { const m = put(new THREE.CircleGeometry(0.05 + Math.random() * 0.05, 7), B(dark ? 0x2f4a30 : 0x5f8a46), g, (Math.random() - 0.5) * 0.9, 0.052, -0.2 - Math.random() * 1.0, -Math.PI / 2); m.scale.x = 1.4; }   // 이끼
    // 도리이: 살짝 안으로 기운 기둥, 검은 받침, 끝이 들린 지붕 보
    const red = L(0xc8392b, dark ? 0.42 : 0.16), black = L(0x231d1a, 0.2);
    for (const sx of [-1, 1]) { put(cy(0.034, 0.04, 1.2, 12), red, g, sx * 0.4, 0.6, 0.18, 0, 0, sx * 0.035); put(cy(0.05, 0.055, 0.1, 12), black, g, sx * 0.42, 0.05, 0.18); }
    put(bx(0.94, 0.05, 0.05), red, g, 0, 0.95, 0.18);                                                                            // 누키(아래 가로대)
    put(bx(0.9, 0.06, 0.07), red, g, 0, 1.165, 0.18);
    for (const sx of [-1, 1]) put(bx(0.2, 0.06, 0.07), red, g, sx * 0.52, 1.185, 0.18, 0, 0, sx * 0.2);                          // 끝이 들린다
    put(bx(0.94, 0.03, 0.1), black, g, 0, 1.21, 0.18); for (const sx of [-1, 1]) put(bx(0.22, 0.03, 0.1), black, g, sx * 0.55, 1.235, 0.18, 0, 0, sx * 0.2);
    put(bx(0.13, 0.18, 0.02), new THREE.MeshBasicMaterial({ map: textTexture("稲荷", { w: 96, h: 132, fg: "#e9c46a", bg: "#2a211c", radius: 4, font: "600 40px 'Noto Serif KR', serif" }) }), g, 0, 1.06, 0.215);
    // 금줄과 흰 종이 술
    put(tube([[-0.38, 0.9, 0.2], [-0.2, 0.84, 0.22], [0, 0.82, 0.23], [0.2, 0.84, 0.22], [0.38, 0.9, 0.2]], 0.016, 20), L(0xd9c08a, 0.35), g);
    const shide = [-0.2, 0, 0.2].map((x) => { const s = new THREE.Group(); s.position.set(x, 0.82, 0.235); g.add(s); for (let k = 0; k < 3; k++) put(bx(0.035, 0.05, 0.004), B(0xfbf8f0), s, (k % 2 ? 0.014 : -0.014), -0.035 - k * 0.045, 0); return s; });
    // 작은 사당: 돌 받침, 격자문에서 새는 불빛, 맞배지붕
    put(bx(0.46, 0.2, 0.4), stone, g, 0, 0.15, -0.95); put(bx(0.4, 0.06, 0.34), stoneD, g, 0, 0.28, -0.95);
    put(bx(0.32, 0.3, 0.26), L(0x5a3c26, dark ? 0.3 : 0.12), g, 0, 0.46, -0.95);
    const door = canvasTex(64, 64, (x) => { x.fillStyle = "#ffcf7a"; x.fillRect(0, 0, 64, 64); x.fillStyle = "#3a2618"; for (let i = 0; i <= 6; i++) { x.fillRect(i * 10 + 1, 0, 3, 64); x.fillRect(0, i * 10 + 1, 64, 3); } x.fillRect(30, 0, 5, 64); });
    put(new THREE.PlaneGeometry(0.22, 0.22), new THREE.MeshBasicMaterial({ map: door }), g, 0, 0.45, -0.815);
    for (const sx of [-1, 1]) put(bx(0.26, 0.025, 0.4), L(0x3a3f44, 0.2), g, sx * 0.105, 0.68, -0.95, 0, 0, -sx * 0.62);
    put(bx(0.04, 0.035, 0.44), L(0x2a2e33, 0.2), g, 0, 0.765, -0.95); put(sp(0.02), L(0xe8c14a, 0.6), g, 0, 0.79, -0.74);
    // 여우 한 쌍: 앉은 몸, 뾰족한 주둥이와 귀, 세운 꼬리, 붉은 턱받이
    const cer = L(0xf6f3ec, dark ? 0.45 : 0.14), cerD = L(0x2a2420, 0.2);
    [-1, 1].forEach((sx) => {
      const f = new THREE.Group(); f.position.set(sx * 0.3, 0, -0.45); f.rotation.y = -sx * 0.5; g.add(f);
      put(bx(0.17, 0.16, 0.2), stone, f, 0, 0.13, 0); put(bx(0.2, 0.03, 0.23), stoneD, f, 0, 0.225, 0);
      put(lathe([[0, 0], [0.06, 0.005], [0.068, 0.05], [0.055, 0.13], [0.038, 0.19], [0, 0.2]], 14), cer, f, 0, 0.24, -0.01);
      put(cy(0.014, 0.016, 0.13, 8), cer, f, -0.022, 0.305, 0.05); put(cy(0.014, 0.016, 0.13, 8), cer, f, 0.022, 0.305, 0.05);
      put(sp(0.046, 14, 12), cer, f, 0, 0.47, 0.012).scale.set(1, 0.95, 1.05);
      put(new THREE.ConeGeometry(0.026, 0.075, 10), cer, f, 0, 0.455, 0.07, Math.PI / 2, 0, 0); put(sp(0.008, 6, 6), cerD, f, 0, 0.456, 0.108);
      for (const ex of [-1, 1]) { put(new THREE.ConeGeometry(0.018, 0.06, 4), cer, f, ex * 0.027, 0.525, 0, 0, Math.PI / 4, -ex * 0.12); put(bx(0.016, 0.004, 0.004), cerD, f, ex * 0.02, 0.48, 0.05, 0, 0, ex * 0.5); }
      put(tube([[0, 0.25, -0.06], [0, 0.34, -0.12], [0, 0.46, -0.11], [0, 0.53, -0.07]], 0.026, 14), cer, f); put(sp(0.03), cer, f, 0, 0.54, -0.065).scale.set(1, 1.4, 1);
      put(new THREE.TorusGeometry(0.04, 0.012, 6, 16, Math.PI), L(0xd0453a, 0.5), f, 0, 0.415, 0.03, Math.PI / 2 + 0.5, 0, Math.PI);
      put(bx(0.05, 0.045, 0.006), L(0xd0453a, 0.5), f, 0, 0.385, 0.062, -0.2);
    });
    // 새전함, 촛불 둘, 술잔
    put(bx(0.24, 0.1, 0.14), woodWarm, g, 0, 0.1, -0.6); for (let i = -2; i <= 2; i++) put(bx(0.012, 0.012, 0.14), L(0x3a2618), g, i * 0.045, 0.155, -0.6);
    const flames = [-1, 1].map((sx) => { put(cy(0.012, 0.012, 0.07, 8), B(0xf6efe0), g, sx * 0.17, 0.085, -0.58); const f = put(sp(0.016, 8, 8), B(0xffd27a), g, sx * 0.17, 0.14, -0.58); f.scale.set(0.8, 1.7, 0.8); return [f, halo(0xffb060, 0.3, g, sx * 0.17, 0.15, -0.56, 0.7)]; });
    put(cy(0.022, 0.014, 0.02, 12), B(0xfbf8f0), g, 0, 0.165, -0.6);
    for (let i = 0; i < 6; i++) put(new THREE.CircleGeometry(0.022, 5), B(i % 2 ? 0xd9682c : 0xc0392b), g, (Math.random() - 0.5) * 0.8, 0.056 + i * 0.001, -Math.random() * 0.9, -Math.PI / 2, 0, Math.random() * 3);   // 떨어진 단풍
    let pl = null; if (dark) { pl = new THREE.PointLight(0xffb060, 1.8, 3.4, 1.7); pl.position.set(0, 0.5, -0.35); g.add(pl); }
    let ring = 0;
    tick.push((dt, t, E, now) => {
      flames.forEach(([f, h], i) => { const k = 1 + Math.sin(t * 11 + i * 2) * 0.16 + Math.sin(t * 5.3 + i) * 0.1; f.scale.y = 1.7 * k; f.position.x += (Math.sin(t * 7 + i) * 0.0015); h.material.opacity = 0.55 + k * 0.15; });
      shide.forEach((s, i) => { s.rotation.z = Math.sin(t * 1.4 + i) * 0.12 + (now < ring ? Math.sin(t * 16) * 0.3 : 0); });
      if (pl) pl.intensity = 1.6 + Math.sin(t * 9) * 0.25 + Math.sin(t * 4.1) * 0.15;
    });
    onTap.shrine = (E, now) => { ring = now + 1.2; E.blip([[1568, 1568, 0.25], [2093, 2093, 0.4]], 0.035); if (E.state === "free" && E.me.bow) E.me.bow(); };
  }

  // ================================================================ ③ 자판기
  {
    const g = spot("vend", 4.35, -11.25, true, [1.5, 1.95, 1.1, 0.1]);
    put(bx(2.4, 2.6, 0.06), woodDark, g, 0, 1.3, -1.2);
    const W = 0.96, H = 1.83, D = 0.72, shell = L(0xf4f5f6, dark ? 0.2 : 0.1), trim = L(0xc8342c, dark ? 0.35 : 0.14), darkM = L(0x23272c, 0.15);
    put(bx(W, H, D), shell, g, 0, H / 2 + 0.06, 0); put(bx(W + 0.02, 0.06, D + 0.02), darkM, g, 0, 0.03, 0); put(bx(W + 0.02, 0.05, D + 0.02), trim, g, 0, H + 0.085, 0);
    for (const sx of [-1, 1]) put(bx(0.012, H - 0.1, 0.5), trim, g, sx * (W / 2 + 0.004), H / 2 + 0.06, 0);                        // 옆면 빨간 띠
    // 위쪽 광고판
    put(new THREE.PlaneGeometry(W - 0.08, 0.17), new THREE.MeshBasicMaterial({ map: canvasTex(256, 48, (x) => { x.fillStyle = "#c8342c"; x.fillRect(0, 0, 256, 48); x.fillStyle = "#fff"; x.font = "700 26px 'Noto Sans KR', sans-serif"; x.textAlign = "center"; x.textBaseline = "middle"; x.fillText("HOT & COLD  DRINK", 128, 25); }) }), g, 0, H - 0.06, D / 2 + 0.002);
    // 진열창: 뒤에서 비추는 밝은 판 + 선반 3단 + 캔·병
    put(bx(0.7, 1.02, 0.02), darkM, g, -0.09, 1.2, D / 2 - 0.005);
    put(new THREE.PlaneGeometry(0.66, 0.98), B(dark ? 0xf4fbff : 0xe2ecf0), g, -0.09, 1.2, D / 2 + 0.006);
    const drinks = [0xd64541, 0x2c82c9, 0xf5ab35, 0x27ae60, 0x8e44ad, 0xe67e22, 0x16a085, 0xc0392b, 0x34495e, 0xf1c40f, 0x2980b9, 0xd35400, 0x7f8c8d, 0xe74c3c, 0x1abc9c, 0x9b59b6, 0x2ecc71, 0xe84393];
    drinks.forEach((c, i) => {
      const row = Math.floor(i / 6), col = i % 6, x = -0.365 + col * 0.11, y = 1.555 - row * 0.33, bottle = (i + row) % 3 === 0, m = L(c, 0.55);
      if (bottle) { put(cy(0.03, 0.032, 0.13, 12), m, g, x, y, D / 2 + 0.03); put(cy(0.012, 0.028, 0.045, 10), L(0xe8f2f4, 0.6), g, x, y + 0.085, D / 2 + 0.03); put(cy(0.014, 0.014, 0.014, 10), L(0xffffff, 0.7), g, x, y + 0.112, D / 2 + 0.03); }
      else { put(cy(0.032, 0.032, 0.115, 14), m, g, x, y - 0.008, D / 2 + 0.03); put(cy(0.0325, 0.0325, 0.03, 14), L(0xf7f7f7, 0.6), g, x, y - 0.008, D / 2 + 0.03); put(cy(0.028, 0.032, 0.01, 14), L(0xcfd4d6, 0.5), g, x, y + 0.054, D / 2 + 0.03); }
      put(bx(0.07, 0.022, 0.006), B(0xffffff), g, x, y - 0.1, D / 2 + 0.012);                                                     // 가격표
      put(bx(0.045, 0.02, 0.012), B(row === 2 ? 0xff5a4a : 0x4aa8ff), g, x, y - 0.128, D / 2 + 0.014);                             // 버튼 (아래 줄은 따뜻한 음료)
    });
    for (let r = 0; r < 3; r++) put(bx(0.68, 0.012, 0.05), L(0xdfe5e8, 0.4), g, -0.09, 1.482 - r * 0.33, D / 2 + 0.03);
    put(bx(0.72, 1.04, 0.004), new THREE.MeshPhongMaterial({ color: 0xffffff, transparent: true, opacity: 0.1, shininess: 120, specular: 0xffffff, depthWrite: false }), g, -0.09, 1.2, D / 2 + 0.07);   // 유리
    // 오른쪽 조작부: 동전·지폐 투입구, 작은 화면, 반환 레버
    put(bx(0.17, 1.02, 0.015), L(0xdde1e4, 0.2), g, 0.375, 1.2, D / 2 + 0.004);
    const lcd = put(bx(0.11, 0.045, 0.01), B(0x7fe0a8), g, 0.375, 1.55, D / 2 + 0.016);
    put(bx(0.05, 0.012, 0.012), darkM, g, 0.375, 1.44, D / 2 + 0.016); put(bx(0.09, 0.016, 0.012), B(0x58c98a), g, 0.375, 1.36, D / 2 + 0.016);
    put(cy(0.02, 0.02, 0.02, 12), L(0xb9bfc4, 0.3), g, 0.375, 1.25, D / 2 + 0.02, Math.PI / 2); put(bx(0.06, 0.05, 0.01), darkM, g, 0.375, 1.13, D / 2 + 0.014);
    // 꺼내는 곳 + 굴러 나오는 캔
    put(bx(0.74, 0.2, 0.03), darkM, g, 0, 0.4, D / 2 + 0.002); put(bx(0.66, 0.13, 0.02), new THREE.MeshPhongMaterial({ color: 0x3a4046, shininess: 80, specular: 0x9aa4ac }), g, 0, 0.4, D / 2 + 0.02, 0.18);
    const can = put(cy(0.032, 0.032, 0.115, 14), L(0xc0392b, 0.6), g, 0, 0.33, D / 2 + 0.09, 0, 0, Math.PI / 2); can.visible = false;
    // 옆의 분리수거함
    put(cy(0.17, 0.15, 0.62, 16), L(0x6f7c86, dark ? 0.25 : 0.1), g, 0.78, 0.31, 0.05); put(cy(0.18, 0.18, 0.04, 16), L(0x4a545c, 0.2), g, 0.78, 0.64, 0.05);
    for (const sx of [-1, 1]) put(new THREE.CircleGeometry(0.04, 14), B(0x14181c), g, 0.78 + sx * 0.065, 0.5, 0.21 - Math.abs(sx) * 0.012, 0, sx * 0.4, 0);
    // 불빛: 앞바닥에 번지는 빛, 위쪽 등에 모이는 나방
    pool(0xcfeaff, 2.2, 1.9, g, -0.05, 0.95, dark ? 0.55 : 0.12); halo(0xdff4ff, 1.5, g, -0.09, 1.2, D / 2 + 0.1, dark ? 0.35 : 0.08);
    let pl = null; if (dark) { pl = new THREE.PointLight(0xd8eeff, 2.6, 5.5, 1.6); pl.position.set(0, 1.3, 1.0); g.add(pl); }
    const moths = [0, 1, 2, 3].map((i) => put(sp(0.012, 6, 6), B(0xfff6dc), g, 0, 1.9, 0.4));
    let drop = 0;
    tick.push((dt, t, E, now) => {
      moths.forEach((m, i) => { const a = t * (1.6 + i * 0.4) + i * 1.7, r = 0.16 + Math.sin(t * 0.9 + i) * 0.08; m.position.set(Math.cos(a) * r - 0.05, 1.93 + Math.sin(t * 2.3 + i * 2) * 0.07, D / 2 + 0.1 + Math.sin(a) * r * 0.6); m.visible = dark; });
      lcd.material.color.setHex((t % 2.4) < 1.2 ? 0x7fe0a8 : 0x58c98a);
      if (pl) pl.intensity = 2.5 + ((t % 7.3) < 0.08 ? -1.2 : 0);                                                                  // 가끔 형광등이 깜빡
      if (now < drop) { const k = 1 - (drop - now) / 1.6; can.visible = true; can.position.set(-0.2 + Math.min(1, k * 1.6) * 0.2, 0.33 + Math.max(0, 0.12 - k * 0.5), D / 2 + 0.09); can.rotation.x = k * 9; }
      else if (can.visible && now > drop + 4) can.visible = false;
    });
    onTap.vend = (E, now) => { drop = now + 1.6; E.blip([[190, 90, 0.12], [140, 70, 0.1], [300, 200, 0.06]], 0.12); E.me.gesture("sip", 3.6); };
  }

  // ================================================================ ④ 우산 도깨비
  {
    const g = spot("kasa", -3.75, 4.9, false, [1.0, 1.6, 1.0]); fence(g, 1.15);
    const k = new THREE.Group(); k.position.set(0, 0, -0.25); g.add(k);
    // 우산 종이: 붉은 기름종이에 살 자국과 흰 고리 무늬(자노메)
    const paper = canvasTex(256, 128, (x) => { x.fillStyle = "#a43a2c"; x.fillRect(0, 0, 256, 128); x.fillStyle = "#f3e8d0"; x.fillRect(0, 66, 256, 20); x.fillStyle = "#7a2a20"; x.fillRect(0, 118, 256, 10); x.strokeStyle = "rgba(60,20,14,.55)"; x.lineWidth = 2; for (let i = 0; i < 16; i++) { x.beginPath(); x.moveTo(i * 16, 0); x.lineTo(i * 16, 128); x.stroke(); } });
    const body = new THREE.Group(); body.position.y = 0.52; k.add(body);
    const canopy = put(new THREE.ConeGeometry(0.34, 0.82, 16, 1, true), new THREE.MeshLambertMaterial({ map: paper, side: THREE.DoubleSide, emissive: dark ? 0x4a1c16 : 0x1c0a08 }), body, 0, 0.41, 0);
    put(cy(0.02, 0.012, 0.1, 8), L(0x3a2a20), body, 0, 0.86, 0); put(sp(0.025, 8, 8), L(0x3a2a20), body, 0, 0.92, 0);
    for (let i = 0; i < 16; i++) { const a = (i / 16) * Math.PI * 2; put(sp(0.012, 6, 6), L(0xe8d9b0, 0.4), body, Math.cos(a) * 0.34, 0.0, Math.sin(a) * 0.34); }
    // 큰 외눈: 흰자, 호박색 홍채, 검은 눈동자, 반짝임 + 깜빡이는 눈꺼풀
    const eye = new THREE.Group(); eye.position.set(0, 0.36, 0.17); eye.rotation.x = -0.38; body.add(eye);
    put(sp(0.105, 20, 16), B(0xfbf8ee), eye).scale.set(1, 1, 0.55);
    const iris = put(sp(0.056, 16, 12), B(0xe8a23a), eye, 0, 0, 0.04); iris.scale.set(1, 1, 0.4);
    const pupil = put(sp(0.03, 12, 10), B(0x151515), eye, 0, 0, 0.058); pupil.scale.set(1, 1, 0.4);
    put(sp(0.012, 6, 6), B(0xffffff), eye, 0.022, 0.024, 0.07);
    const lid = put(new THREE.SphereGeometry(0.112, 16, 10, 0, Math.PI * 2, 0, Math.PI / 2), new THREE.MeshLambertMaterial({ color: 0x8a3024, emissive: dark ? 0x3a1612 : 0x140806, side: THREE.DoubleSide }), eye, 0, 0, 0.005); lid.scale.set(1, 1, 0.6);
    // 입과 긴 혀
    put(new THREE.TorusGeometry(0.085, 0.012, 6, 16, Math.PI), B(0x2a0f0c), body, 0, 0.17, 0.262, -0.38, 0, Math.PI);
    const tongue = new THREE.Group(); tongue.position.set(0.01, 0.1, 0.275); body.add(tongue);
    put(tube([[0, 0, 0], [0.005, -0.06, 0.03], [0.02, -0.13, 0.035], [0.04, -0.18, 0.015]], 0.022, 12), L(0xe8635a, 0.5), tongue).scale.set(1.25, 1, 0.6);
    // 두 팔 (살짝 흔든다)
    const arms = [-1, 1].map((sx) => { const a = new THREE.Group(); a.position.set(sx * 0.2, 0.22, 0.08); body.add(a); put(tube([[0, 0, 0], [sx * 0.1, -0.03, 0.03], [sx * 0.17, 0.04, 0.05]], 0.014, 10), L(0xe8cfa8, 0.3), a); put(sp(0.028, 8, 8), L(0xe8cfa8, 0.3), a, sx * 0.17, 0.04, 0.05); return a; });
    // 외다리와 나막신
    put(cy(0.034, 0.03, 0.44, 10), L(0xe8cfa8, 0.3), k, 0, 0.3, 0); put(sp(0.04, 10, 8), L(0xe8cfa8, 0.3), k, 0, 0.5, 0);
    put(sp(0.05, 10, 8), L(0xe8cfa8, 0.3), k, 0, 0.085, 0.03).scale.set(1, 0.6, 1.5);
    put(bx(0.13, 0.022, 0.22), woodWarm, k, 0, 0.055, 0.03); for (const dz of [-0.04, 0.09]) put(bx(0.12, 0.045, 0.025), woodWarm, k, 0, 0.022, dz);
    put(tube([[-0.045, 0.07, -0.01], [0, 0.1, 0.07], [0.045, 0.07, -0.01]], 0.008, 10), L(0xc0392b, 0.5), k);
    let hideUntil = 0, open = 1;
    tick.push((dt, t, E, now) => {
      const hidden = now < hideUntil, ph = (t % 3.6) / 0.55, hop = !hidden && ph < 1 ? Math.sin(ph * Math.PI) : 0;
      open += ((hidden ? 0.16 : 1) - open) * Math.min(1, dt * (hidden ? 9 : 4));
      canopy.scale.set(open, 1, open); eye.visible = open > 0.6; tongue.visible = open > 0.6; arms.forEach((a) => { a.visible = open > 0.6; });
      k.position.y = hop * 0.24 + (hidden ? -0.0 : 0); k.scale.set(1 + (ph < 1 ? -hop * 0.06 : 0), 1 + hop * 0.1 - (ph > 1 && ph < 1.25 ? Math.sin(((ph - 1) / 0.25) * Math.PI) * 0.1 : 0), 1);
      k.rotation.z = Math.sin(t * 1.9) * 0.05; k.rotation.y = Math.sin(t * 0.6) * 0.25;
      lid.rotation.x = -Math.PI / 2 + ((t % 3.1) < 0.14 || hidden ? 1.45 : 0.0) ;
      pupil.position.x = iris.position.x = Math.sin(t * 0.8) * 0.02; tongue.rotation.z = Math.sin(t * 4.2) * 0.25;
      arms.forEach((a, i) => { a.rotation.z = Math.sin(t * 3 + i * Math.PI) * 0.35; });
    });
    onTap.kasa = (E, now) => { hideUntil = now + 7; E.blip([[500, 1100, 0.1]], 0.06); };
  }

  // ================================================================ ⑤ 비밀 연구실
  {
    const g = spot("lab", -3.9, -1.62, false, [0.95, 1.9, 1.4]);
    put(bx(0.95, 2.4, 0.06), woodDark, g, 0, 1.2, -0.95);
    // 살짝 열린 문: 안쪽 따뜻한 빛, 바닥으로 번지는 빛
    put(new THREE.PlaneGeometry(0.58, 1.5), B(0xffdf9a), g, -0.06, 0.78, -0.915);
    const door = new THREE.Group(); door.position.set(-0.36, 0, -0.9); door.rotation.y = -0.5; g.add(door);
    put(bx(0.6, 1.52, 0.04), woodWarm, door, 0.3, 0.78, 0); for (const y of [0.42, 1.14]) put(bx(0.44, 0.5, 0.012), L(0x6e4a2a, dark ? 0.3 : 0.1), door, 0.3, y, 0.022);
    put(sp(0.028, 10, 8), L(0xd8b060, 0.6), door, 0.52, 0.8, 0.04);
    put(bx(0.7, 0.07, 0.07), L(0x2a1e16), g, -0.06, 1.57, -0.9); for (const sx of [-1, 1]) put(bx(0.06, 1.56, 0.07), L(0x2a1e16), g, -0.06 + sx * 0.33, 0.78, -0.9);
    const spill = pool(0xffcf80, 1.1, 1.3, g, -0.02, -0.35, dark ? 0.6 : 0.16);
    // 문패, 갓등
    put(new THREE.PlaneGeometry(0.46, 0.15), new THREE.MeshBasicMaterial({ map: textTexture("통합과학 lab", { w: 276, h: 90, fg: "#3a2a12", bg: "#e2c376", radius: 8, font: "700 36px 'Noto Sans KR', sans-serif" }) }), g, -0.06, 1.74, -0.905);
    put(new THREE.ConeGeometry(0.09, 0.07, 14, 1, true), new THREE.MeshLambertMaterial({ color: 0x2f4a42, side: THREE.DoubleSide, emissive: 0x0c1412 }), g, 0.28, 1.98, -0.8); put(sp(0.025, 8, 8), B(0xfff0c0), g, 0.28, 1.95, -0.8);
    const lampGlow = halo(0xffd58a, 0.5, g, 0.28, 1.93, -0.78, 0.7);
    // 작은 작업대 + 실험 기구: 삼각 플라스크, 둥근 플라스크, 시험관 꽂이 (빛나는 용액과 올라오는 방울)
    put(bx(0.44, 0.04, 0.26), woodWarm, g, 0.2, 0.52, -0.35); for (const [x, z] of [[0.02, -0.25], [0.38, -0.25], [0.02, -0.45], [0.38, -0.45]]) put(bx(0.03, 0.5, 0.03), L(0x5a3c22), g, x, 0.25, z);
    const glass = new THREE.MeshPhongMaterial({ color: 0xdff2f4, transparent: true, opacity: 0.32, shininess: 120, specular: 0xffffff, depthWrite: false, side: THREE.DoubleSide });
    const erl = [[0.012, 0], [0.058, 0.004], [0.06, 0.02], [0.02, 0.1], [0.018, 0.14], [0.022, 0.145]], rnd = [[0.01, 0], [0.04, 0.012], [0.052, 0.045], [0.04, 0.08], [0.014, 0.1], [0.014, 0.15], [0.018, 0.155]];
    const liquids = [];
    [[0.08, -0.33, erl, 0x6affb0, 0.55], [0.22, -0.4, rnd, 0x6ac8ff, 0.6], [0.34, -0.31, erl, 0xff8ad0, 0.45]].forEach(([x, z, prof, c, fill]) => {
      put(lathe(prof, 16), glass, g, x, 0.54, z);
      const inner = put(lathe(prof.slice(0, 4).map(([r, y]) => [r * 0.86, y * fill * 1.6 + 0.004]), 16), B(c), g, x, 0.542, z);
      const h = halo(c, 0.26, g, x, 0.6, z + 0.02, dark ? 0.6 : 0.25);
      const bub = [0, 1, 2].map(() => put(sp(0.006, 6, 6), B(0xffffff), g, x, 0.56, z));
      liquids.push({ x, z, inner, h, bub });
    });
    put(bx(0.16, 0.012, 0.05), L(0x5a3c22), g, 0.33, 0.6, -0.44); for (let i = 0; i < 3; i++) { put(cy(0.011, 0.011, 0.1, 8), glass, g, 0.285 + i * 0.045, 0.6, -0.44); put(cy(0.009, 0.009, 0.045, 8), B([0xffd24a, 0x9a7aff, 0x5affc0][i]), g, 0.285 + i * 0.045, 0.575, -0.44); }
    // 이젤 칠판 (공식과 원자 그림), 쌓아 둔 책
    const board = canvasTex(256, 200, (x) => { x.fillStyle = "#2f3b33"; x.fillRect(0, 0, 256, 200); for (let i = 0; i < 120; i++) { x.fillStyle = `rgba(255,255,255,${Math.random() * 0.04})`; x.fillRect(Math.random() * 256, Math.random() * 200, 2 + Math.random() * 26, 1 + Math.random() * 2); }
      x.fillStyle = "#f3f1e6"; x.font = "600 44px 'Noto Serif KR', serif"; x.textAlign = "center"; x.fillText("E = mc²", 128, 62); x.font = "500 26px 'Noto Serif KR', serif"; x.fillStyle = "#f2d98a"; x.fillText("H₂O   CO₂", 82, 176);
      x.strokeStyle = "#cfe8ff"; x.lineWidth = 2.5; for (let i = 0; i < 3; i++) { x.save(); x.translate(196, 130); x.rotate((i * Math.PI) / 3); x.beginPath(); x.ellipse(0, 0, 40, 14, 0, 0, Math.PI * 2); x.stroke(); x.restore(); } x.fillStyle = "#ffb07a"; x.beginPath(); x.arc(196, 130, 6, 0, Math.PI * 2); x.fill(); });
    const ez = new THREE.Group(); ez.position.set(-0.27, 0, -0.2); ez.rotation.y = 0.5; g.add(ez);
    put(bx(0.4, 0.31, 0.02), new THREE.MeshBasicMaterial({ map: board }), ez, 0, 0.52, 0, -0.16); put(bx(0.44, 0.35, 0.012), L(0x8a5e36, 0.2), ez, 0, 0.52, -0.012, -0.16); put(bx(0.4, 0.02, 0.04), L(0x8a5e36, 0.2), ez, 0, 0.35, 0.03);
    for (const sx of [-1, 1]) put(bx(0.022, 0.78, 0.022), L(0x8a5e36, 0.2), ez, sx * 0.17, 0.38, -0.03, -0.16, 0, sx * 0.06); put(bx(0.022, 0.72, 0.022), L(0x8a5e36, 0.2), ez, 0, 0.35, -0.16, 0.42);
    [[0x2c5f8c, 0.2, 0.15], [0xb5452f, 0.18, 0.13], [0x3d7a55, 0.17, 0.14]].forEach(([c, w, d], i) => { put(bx(w, 0.035, d), L(c, dark ? 0.4 : 0.14), g, -0.3 + i * 0.012, 0.02 + i * 0.037, 0.3, 0, i * 0.3 - 0.2, 0); put(bx(w - 0.01, 0.028, d - 0.006), B(0xf2ead8), g, -0.3 + i * 0.012 + 0.006, 0.02 + i * 0.037, 0.3, 0, i * 0.3 - 0.2, 0).scale.x = 0.98; });
    let pl = null; if (dark) { pl = new THREE.PointLight(0xffc878, 1.4, 3.2, 1.7); pl.position.set(0, 0.9, -0.3); g.add(pl); }
    let openUntil = 0;
    tick.push((dt, t, E, now) => {
      const flick = 0.86 + Math.sin(t * 13) * 0.07 + Math.sin(t * 7.1) * 0.06, wide = now < openUntil;
      door.rotation.y += ((wide ? -1.25 : -0.5) - door.rotation.y) * Math.min(1, dt * 4);
      spill.material.opacity = (dark ? 0.6 : 0.16) * flick * (wide ? 1.5 : 1); lampGlow.material.opacity = 0.6 * flick; if (pl) pl.intensity = (wide ? 2.4 : 1.4) * flick;
      liquids.forEach((q, i) => { q.h.material.opacity = (dark ? 0.55 : 0.22) + Math.sin(t * 2 + i * 2) * 0.1; q.bub.forEach((b, k) => { const p = (t * 0.5 + k * 0.33 + i * 0.2) % 1; b.position.set(q.x + Math.sin(p * 9 + k) * 0.012, 0.55 + p * 0.07, q.z); b.visible = p < 0.9; }); });
    });
    onTap.lab = (E, now) => { openUntil = now + 3; E.blip([[2400, 2100, 0.04], [2600, 2200, 0.04], [2300, 2000, 0.05]], 0.03); };
  }

  // ================================================================ ⑥ 오래된 우물과 도깨비불
  {
    const g = spot("wisp", -3.85, -14.1, false, [0.75, 1.9, 1.3]); fence(g, 0.75);
    // 돌 우물: 돌을 둘러 쌓은 벽, 이끼 낀 테, 검푸른 물
    for (let r = 0; r < 3; r++) for (let i = 0; i < 9; i++) { const a = ((i + r * 0.5) / 9) * Math.PI * 2; put(bx(0.19, 0.125, 0.09), i % 2 ? stone : stoneD, g, Math.cos(a) * 0.27, 0.065 + r * 0.13, -0.35 + Math.sin(a) * 0.27, 0, -a + Math.PI / 2, 0); }
    put(new THREE.TorusGeometry(0.275, 0.035, 8, 20), L(0x5f6a5a, dark ? 0.25 : 0.1), g, 0, 0.41, -0.35, Math.PI / 2);
    const water = put(new THREE.CircleGeometry(0.24, 20), B(0x0d2230), g, 0, 0.3, -0.35, -Math.PI / 2);
    const wellGlow = halo(0x6fd0ff, 0.7, g, 0, 0.36, -0.35, 0.35);
    // 나무 틀과 작은 지붕, 도르래 줄에 매달린 두레박
    for (const sx of [-1, 1]) put(bx(0.045, 1.2, 0.045), woodWarm, g, sx * 0.31, 0.6, -0.35); put(cy(0.02, 0.02, 0.68, 8), L(0x5a3c22), g, 0, 1.12, -0.35, 0, 0, Math.PI / 2);
    for (const sz of [-1, 1]) put(bx(0.76, 0.02, 0.26), L(0x3a3f44, 0.2), g, 0, 1.27, -0.35 + sz * 0.11, sz * 0.55);
    const rope = new THREE.Group(); rope.position.set(0.08, 1.12, -0.35); g.add(rope);
    put(cy(0.006, 0.006, 0.42, 6), L(0xd9c08a, 0.3), rope, 0, -0.21, 0);
    put(cy(0.07, 0.055, 0.11, 12, true), new THREE.MeshLambertMaterial({ map: woodWarm.map, side: THREE.DoubleSide, emissive: 0x140c06 }), rope, 0, -0.47, 0); put(cy(0.055, 0.055, 0.01, 12), L(0x5a3c22), rope, 0, -0.52, 0);
    put(new THREE.TorusGeometry(0.06, 0.005, 6, 14, Math.PI), L(0x2a2e33), rope, 0, -0.42, 0);
    // 도깨비불 셋: 밝은 심지, 푸른 번짐, 위로 흐르는 꼬리, 흩어지는 불티
    const flameGeo = lathe([[0, 0], [0.045, 0.02], [0.05, 0.06], [0.03, 0.13], [0.008, 0.2], [0, 0.22]], 12);
    const wisps = [0, 1, 2].map((i) => {
      const w = new THREE.Group(); g.add(w);
      const tail = put(flameGeo, new THREE.MeshBasicMaterial({ color: 0x4fb8ff, transparent: true, opacity: 0.55, depthWrite: false, blending: THREE.AdditiveBlending }), w, 0, -0.03, 0);
      const core = put(sp(0.032, 12, 10), new THREE.MeshBasicMaterial({ color: 0xeafcff, transparent: true }), w);
      const h = halo(0x5fc4ff, 0.42 + i * 0.05, w, 0, 0.02, 0, 0.75);
      const sparks = [0, 1, 2, 3].map(() => put(sp(0.007, 5, 5), new THREE.MeshBasicMaterial({ color: 0xbfeaff, transparent: true }), g));
      return { w, tail, core, h, sparks, a: 1 };
    });
    let pl = null; if (dark) { pl = new THREE.PointLight(0x6fc8ff, 1.4, 3.2, 1.7); pl.position.set(0, 1.0, -0.2); g.add(pl); }
    let goneUntil = 0;
    tick.push((dt, t, E, now) => {
      const gone = now < goneUntil; let lit = 0;
      wisps.forEach((q, i) => {
        q.a += ((gone ? 0 : 1) - q.a) * Math.min(1, dt * (gone ? 4 : 1.5)); lit += q.a;
        const ang = t * (0.5 + i * 0.12) + i * 2.1, r = 0.16 + Math.sin(t * 0.7 + i) * 0.06;
        const y = 0.62 + i * 0.3 + Math.sin(t * 1.3 + i * 1.7) * 0.1 - (1 - q.a) * (0.4 + i * 0.3);                               // 사라질 때는 우물 속으로 빨려 든다
        q.w.position.set(Math.cos(ang) * r, y, -0.35 + Math.sin(ang) * r * 0.8);
        q.tail.scale.set(1 + Math.sin(t * 9 + i) * 0.12, 1 + Math.sin(t * 6 + i * 2) * 0.2, 1); q.tail.rotation.z = Math.sin(t * 2 + i) * 0.2;
        q.tail.material.opacity = 0.55 * q.a; q.core.material.opacity = q.a; q.h.material.opacity = (0.6 + Math.sin(t * 7 + i * 3) * 0.15) * q.a;
        q.sparks.forEach((s, k) => { const p = (t * 0.6 + k * 0.25 + i * 0.13) % 1; s.position.set(q.w.position.x + Math.sin(p * 7 + k * 2) * 0.05, y + 0.12 + p * 0.3, q.w.position.z + Math.cos(p * 5 + k) * 0.04); s.material.opacity = (1 - p) * q.a; });
      });
      wellGlow.material.opacity = 0.25 + (1 - lit / 3) * 0.5 + Math.sin(t * 2) * 0.06; water.material.color.setHex(gone ? 0x1c4a66 : 0x0d2230);
      rope.rotation.z = Math.sin(t * 1.1) * 0.05 + (gone ? Math.sin(t * 14) * 0.08 * Math.max(0, (goneUntil - now - 5) / 2) : 0);
      if (pl) pl.intensity = (0.4 + lit * 0.4) + Math.sin(t * 3) * 0.2;
    });
    onTap.wisp = (E, now) => { goneUntil = now + 7; E.blip([[900, 300, 0.5]], 0.04); };
  }

  const TEXT = {
    cat: "야옹— 검은 고양이가 눈을 가늘게 떠요.",
    shrine: "작은 여우 사당이에요. 두 손을 모으고 오늘 목표 하나를 빌어요.",
    vend: "덜컹— 따뜻한 캔커피가 굴러 나왔어요.",
    kasa: "앗, 우산 도깨비가 깜짝 놀라 우산을 접었어요.",
    lab: "문이 살짝 더 열리고 분필 소리가 들려요. 누군가의 비밀 연구실인가 봐요.",
    wisp: "도깨비불이 우물 속으로 스르륵 숨었어요.",
  };
  function found(id) {
    let got = []; try { got = JSON.parse(localStorage.getItem("kissa-eggs") || "[]"); } catch (_) {}
    const first = !got.includes(id); if (first) { got.push(id); try { localStorage.setItem("kissa-eggs", JSON.stringify(got)); } catch (_) {} }
    const n = got.filter((k) => TEXT[k]).length, all = Object.keys(TEXT).length;
    return first ? (n === all ? ` 골목의 비밀 ${all}개를 모두 찾았어요!` : ` (골목의 비밀 ${n}/${all})`) : "";
  }
  return {
    picks,
    tap(E, o) { const id = o && o.userData.egg; if (!TEXT[id]) return; onTap[id](E, performance.now() / 1000); E.whisper(TEXT[id] + found(id), 4200); },
    update(dt, t, E) { const now = performance.now() / 1000; for (const f of tick) f(dt, t, E, now); },
  };
}
