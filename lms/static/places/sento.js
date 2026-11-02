// 같이 공부 · 노천탕. 눈 내리는 산골 마을(갓쇼 지붕)을 내려다보는 바위 온천,
// 대나무 홈통에서 떨어지는 물, 김, 그리고 화로(이로리)가 있는 휴게소의 둥근 펠트 방석.
export default {
  moon: false,
  palette(PAL, TIME) {
    // 눈 오는 날의 흐린 흰 하늘 → 해 질 녘 푸른 시간 → 밤
    Object.assign(PAL, {
      day:   { top: 0xb9c3cc, horizon: 0xeceef0, fog: 0xe4e7ea, hemiSky: 0xf4f6f8, hemiGround: 0x9aa0a6, hemi: 1.15, sun: 0xfff6ea, sunI: 0.9, ground: 0xeef0f2, lamp: 0.6 },
      dusk:  { top: 0x2e3b5e, horizon: 0x8f9cc0, fog: 0x7d88a8, hemiSky: 0xb8c4e8, hemiGround: 0x4a4e60, hemi: 0.9, sun: 0xc8d2f0, sunI: 0.5, ground: 0xc9d0e0, lamp: 1.6 },
      night: { top: 0x0d1428, horizon: 0x34405e, fog: 0x2a3350, hemiSky: 0x8394c8, hemiGround: 0x22242e, hemi: 0.7, sun: 0x9db0e6, sunI: 0.3, ground: 0x9aa3b8, lamp: 2.4 },
    }[TIME]);
  },
  build(K) {
    const { THREE, scene, TIME, PAL, mat, box, cyl, roof, textTexture, rand, srand } = K;
    const night = TIME !== "day";
    const SNOW = PAL.ground;
    const pickGround = [];

    // ---------------------------------------------------------------- 땅(눈)과 먼 산
    {
      const g = new THREE.Mesh(new THREE.CircleGeometry(90, 48), mat(SNOW));
      g.rotation.x = -Math.PI / 2; scene.add(g); pickGround.push(g);
      // 눈 둔덕
      for (let i = 0; i < 26; i++) {
        const a = srand() * Math.PI * 2, r = 16 + srand() * 18;
        const m = new THREE.Mesh(new THREE.SphereGeometry(1.5 + srand() * 2.5, 10, 6, 0, Math.PI * 2, 0, Math.PI / 2), mat(SNOW));
        m.scale.y = 0.35; m.position.set(Math.cos(a) * r, 0, Math.sin(a) * r - 4); scene.add(m);
      }
      const far = night ? 0x56607a : 0xc9cfd6, mid = night ? 0x3d4660 : 0xa9b1ba;
      for (let i = 0; i < 9; i++) {
        const a = (i / 9) * Math.PI * 2 + 0.3, r = 70 + srand() * 18;
        const m = new THREE.Mesh(new THREE.ConeGeometry(18 + srand() * 14, 18 + srand() * 14, 6), mat(i % 2 ? far : mid));
        m.position.set(Math.cos(a) * r, 6, Math.sin(a) * r - 10); m.rotation.y = srand() * 3; scene.add(m);
      }
    }

    // ---------------------------------------------------------------- 눈 덮인 삼나무
    function snowCedar(x, z, s = 1) {
      cyl(0.16 * s, 0.24 * s, 1.6 * s, 6, 0x3e2f25, x, 0.8 * s, z);
      for (let i = 0; i < 3; i++) {
        const r = (1.6 - i * 0.4) * s, h = (2.1 - i * 0.3) * s, y = (1.9 + i * 1.1) * s;
        const c = new THREE.Mesh(new THREE.ConeGeometry(r, h, 7), mat(night ? 0x1d2a26 : 0x2c4036)); c.position.set(x, y, z); scene.add(c);
        const cap = new THREE.Mesh(new THREE.ConeGeometry(r * 0.72, h * 0.5, 7), mat(SNOW)); cap.position.set(x, y + h * 0.26, z); scene.add(cap);
      }
    }
    for (let i = 0; i < 40; i++) {
      const a = srand() * Math.PI * 2, r = 24 + srand() * 26;
      const x = Math.cos(a) * r, z = Math.sin(a) * r - 6;
      if (z > 12 && Math.abs(x) < 10) continue;
      snowCedar(x, z, 0.9 + srand() * 0.8);
    }

    // ---------------------------------------------------------------- 갓쇼 지붕 집 (눈이 두껍게 쌓인 초가)
    const windows = [];
    function gassho(x, z, w, len, h, rotY) {
      const g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = rotY; scene.add(g);
      box(w * 0.92, 1.6, len * 0.92, 0x3b2c22, 0, 0.8, 0, g);
      // 지붕 몸통(삼각기둥)
      const tri = new THREE.Shape(); tri.moveTo(-w / 2 - 0.4, 0); tri.lineTo(w / 2 + 0.4, 0); tri.lineTo(0, h); tri.lineTo(-w / 2 - 0.4, 0);
      const geo = new THREE.ExtrudeGeometry(tri, { depth: len, bevelEnabled: false }); geo.translate(0, 0, -len / 2);
      const body = new THREE.Mesh(geo, mat(0x4a3b2e)); body.position.y = 1.5; g.add(body);
      // 눈 두 장
      const sl = Math.hypot(w / 2 + 0.4, h), ang = Math.atan2(h, w / 2 + 0.4);
      for (const sd of [-1, 1]) {
        const slab = new THREE.Mesh(new THREE.BoxGeometry(sl + 0.3, 0.55, len + 0.5), mat(SNOW));
        slab.position.set(sd * (w / 4 + 0.2) + sd * 0.12, 1.5 + h / 2 + 0.2, 0); slab.rotation.z = -sd * ang; g.add(slab);
      }
      const ridge = new THREE.Mesh(new THREE.CylinderGeometry(0.45, 0.45, len + 0.6, 10), mat(SNOW)); ridge.rotation.x = Math.PI / 2; ridge.position.set(0, 1.5 + h + 0.15, 0); g.add(ridge);
      // 박공 면의 창 (밤엔 따뜻하게 켜진다)
      const winC = night ? 0xffcf8a : 0xe6e2d6;
      const rows = [[0.7, [-0.9, 0.9]], [2.0, [-0.6, 0.6]], [3.1, [0]]];
      rows.forEach(([y, xs]) => xs.forEach((wx) => {
        if (y + 1.5 > 1.5 + h - 0.8) return;
        for (const sd of [-1, 1]) {
          const win = new THREE.Mesh(new THREE.PlaneGeometry(0.75, 0.8), new THREE.MeshBasicMaterial({ color: winC }));
          win.position.set(wx, 1.5 + y, sd * (len / 2 + 0.02)); if (sd < 0) win.rotation.y = Math.PI; g.add(win); windows.push(win);
        }
      }));
      return g;
    }
    gassho(-17, -34, 7, 9, 6.5, 0.15);
    gassho(-5, -40, 6.5, 8, 6, -0.1);
    gassho(9, -37, 7.5, 9.5, 7, 0.08);
    gassho(24, -30, 6, 8, 5.6, -0.4);
    gassho(-30, -22, 6, 8, 5.6, 0.6);

    // ---------------------------------------------------------------- 바위 온천
    const POOL = { x: -2, z: -3, r: 5.2 };
    const poolR = (a) => POOL.r + Math.sin(a * 3) * 0.5 + Math.cos(a * 5) * 0.3;
    const WATER_Y = 0.22, FLOOR_Y = -0.5;
    {
      const sh = new THREE.Shape();
      for (let i = 0; i <= 48; i++) { const a = (i / 48) * Math.PI * 2, r = poolR(a); const px = Math.cos(a) * r, pz = -Math.sin(a) * r; i ? sh.lineTo(px, pz) : sh.moveTo(px, pz); }
      const bottom = new THREE.Mesh(new THREE.ShapeGeometry(sh), mat(0x5d6a66)); bottom.rotation.x = -Math.PI / 2; bottom.position.set(POOL.x, FLOOR_Y, POOL.z); scene.add(bottom);
      const waterM = new THREE.MeshPhongMaterial({ color: night ? 0x3f7f86 : 0x86c4c0, transparent: true, opacity: 0.88, shininess: 90, specular: 0xffffff, emissive: night ? 0x0d2a2e : 0x0a1f1f });
      const water = new THREE.Mesh(new THREE.ShapeGeometry(sh, 24), waterM); water.rotation.x = -Math.PI / 2; water.position.set(POOL.x, WATER_Y, POOL.z); scene.add(water); pickGround.push(water);
      // 테두리 바위(눈 모자)
      for (let i = 0; i < 30; i++) {
        const a = (i / 30) * Math.PI * 2 + srand() * 0.1, r = poolR(a) + 0.35;
        const s = 0.42 + srand() * 0.4;
        const rock = new THREE.Mesh(new THREE.DodecahedronGeometry(s, 0), mat(i % 3 ? 0x5a5f63 : 0x6c7074));
        rock.position.set(POOL.x + Math.cos(a) * r, s * 0.35, POOL.z + Math.sin(a) * r); rock.rotation.set(srand() * 3, srand() * 3, 0); rock.scale.y = 0.55; scene.add(rock);
        if (i % 2 === 0 && a > Math.PI * 0.9 && a < Math.PI * 2.1) {
          const cap = new THREE.Mesh(new THREE.SphereGeometry(s * 0.75, 8, 5, 0, Math.PI * 2, 0, Math.PI / 2), mat(SNOW));
          cap.position.copy(rock.position); cap.position.y += s * 0.25; cap.scale.y = 0.45; scene.add(cap);
        }
      }
    }

    // 대나무 홈통 (뒤쪽 바위에서 물이 떨어진다)
    const SPOUT = { x: POOL.x + 1.2, z: POOL.z - poolR(-Math.PI / 2 + 0.25) - 0.2 };
    {
      const big = new THREE.Mesh(new THREE.DodecahedronGeometry(1.4, 0), mat(0x55595d)); big.position.set(SPOUT.x, 0.7, SPOUT.z - 1.2); big.scale.y = 0.9; scene.add(big);
      const pipe = cyl(0.09, 0.09, 2.2, 8, 0x8c9a52, SPOUT.x, 1.6, SPOUT.z - 0.2); pipe.rotation.x = Math.PI / 2 - 0.25;
      cyl(0.05, 0.05, 1.6, 6, 0x6f5a3d, SPOUT.x - 0.3, 0.8, SPOUT.z - 0.9).rotation.z = 0.3;
      cyl(0.05, 0.05, 1.6, 6, 0x6f5a3d, SPOUT.x + 0.3, 0.8, SPOUT.z - 0.9).rotation.z = -0.3;
    }
    const stream = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.08, 1.3, 6, 1, true),
      new THREE.MeshBasicMaterial({ color: 0xe8f6f4, transparent: true, opacity: 0.55, depthWrite: false }));
    stream.position.set(SPOUT.x, 0.9, SPOUT.z + 0.85); scene.add(stream);
    const ripple = new THREE.Mesh(new THREE.RingGeometry(0.2, 0.28, 24), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.5, depthWrite: false }));
    ripple.rotation.x = -Math.PI / 2; ripple.position.set(SPOUT.x, WATER_Y + 0.02, SPOUT.z + 0.85); scene.add(ripple);

    // ---------------------------------------------------------------- 김 (부드러운 구름 조각)
    const steamTex = (() => {
      const c = document.createElement("canvas"); c.width = c.height = 64; const x = c.getContext("2d");
      const gr = x.createRadialGradient(32, 32, 0, 32, 32, 32); gr.addColorStop(0, "rgba(255,255,255,0.9)"); gr.addColorStop(1, "rgba(255,255,255,0)");
      x.fillStyle = gr; x.fillRect(0, 0, 64, 64); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
    })();
    const steam = [];
    for (let i = 0; i < 22; i++) {
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: steamTex, transparent: true, depthWrite: false, opacity: 0, color: night ? 0xc8d4e8 : 0xffffff }));
      sp.userData = { a: srand() * Math.PI * 2, r: srand() * 0.85, t: srand() * 6, life: 5 + srand() * 3 };
      scene.add(sp); steam.push(sp);
    }

    // ---------------------------------------------------------------- 탕 속 자리 (가장자리를 따라 8개, 가운데를 바라본다)
    const SEATS = [], pickSeats = [];
    for (let i = 0; i < 8; i++) {
      const a = (i / 8) * Math.PI * 2 + Math.PI / 8, r = poolR(a) - 0.9;
      const x = POOL.x + Math.cos(a) * r, z = POOL.z + Math.sin(a) * r;
      const id = SEATS.length;
      SEATS.push({ x, z, yaw: Math.atan2(POOL.x - x, POOL.z - z), y: FLOOR_Y + 0.12, lift: 0, kind: "water" });
      // 앉을 수 있는 자리는 물 위에 옅은 고리로 보인다
      const m = new THREE.Mesh(new THREE.CircleGeometry(0.55, 20), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.12, depthWrite: false }));
      m.rotation.x = -Math.PI / 2; m.position.set(x, WATER_Y + 0.015, z); m.userData.seat = id; scene.add(m); pickSeats.push(m);
    }

    // ---------------------------------------------------------------- 휴게소: 이로리(화로)와 둥근 펠트 방석
    const HUT = { x: 9.5, z: 0.5, w: 7, d: 6, floor: 0.45 };
    const inHut = (x, z) => Math.abs(x - HUT.x) < HUT.w / 2 - 0.3 && Math.abs(z - HUT.z) < HUT.d / 2 - 0.3;
    const pickHut = [];
    let hutRoof, board;
    {
      const fl = box(HUT.w, HUT.floor, HUT.d, 0xe9e4da, HUT.x, HUT.floor / 2, HUT.z); pickHut.push(fl);
      box(HUT.w + 0.2, 0.12, HUT.d + 0.2, 0x5a4232, HUT.x, HUT.floor - 0.1, HUT.z);
      // 기둥
      for (const [dx, dz] of [[-1, -1], [1, -1], [-1, 1], [1, 1], [0, -1]]) box(0.22, 3.0, 0.22, 0x4a3426, HUT.x + dx * (HUT.w / 2 - 0.15), HUT.floor + 1.5, HUT.z + dz * (HUT.d / 2 - 0.15));
      // 뒷벽(흰 회벽 + 검은 나무)
      box(HUT.w, 2.2, 0.15, 0xf1ece2, HUT.x, HUT.floor + 1.1, HUT.z - HUT.d / 2 + 0.08);
      box(HUT.w, 0.6, 0.17, 0x3b2c22, HUT.x, HUT.floor + 0.3, HUT.z - HUT.d / 2 + 0.08);
      box(0.15, 2.2, HUT.d, 0xf1ece2, HUT.x + HUT.w / 2 - 0.08, HUT.floor + 1.1, HUT.z);
      // 지붕(눈) — 안에 들어가면 걷힌다
      hutRoof = new THREE.Group(); scene.add(hutRoof);
      roof(HUT.w + 1.6, HUT.d + 1.6, 1.4, 0.35, 0x3a2e26, HUT.x, HUT.floor + 3.6, HUT.z, hutRoof);
      roof(HUT.w + 1.4, HUT.d + 1.4, 0.7, 0.3, SNOW, HUT.x, HUT.floor + 4.25, HUT.z, hutRoof);
      // 이로리: 나뭇결 테두리, 재, 쇠 받침, 숯불
      const IR = { x: HUT.x, z: HUT.z };
      const frame = 0x9a6235;
      box(1.9, 0.08, 0.28, frame, IR.x, HUT.floor + 0.04, IR.z - 0.81); box(1.9, 0.08, 0.28, frame, IR.x, HUT.floor + 0.04, IR.z + 0.81);
      box(0.28, 0.08, 1.9, frame, IR.x - 0.81, HUT.floor + 0.04, IR.z); box(0.28, 0.08, 1.9, frame, IR.x + 0.81, HUT.floor + 0.04, IR.z);
      box(1.36, 0.04, 1.36, 0xb8b2a6, IR.x, HUT.floor + 0.01, IR.z);
      const tri = 0x3a2a22;
      for (const [dx, dz] of [[-0.3, -0.18], [0.3, -0.18], [-0.3, 0.18], [0.3, 0.18]]) box(0.03, 0.22, 0.03, tri, IR.x + dx, HUT.floor + 0.12, IR.z + dz);
      box(0.64, 0.03, 0.03, tri, IR.x, HUT.floor + 0.23, IR.z - 0.18); box(0.64, 0.03, 0.03, tri, IR.x, HUT.floor + 0.23, IR.z + 0.18);
      const ember = new THREE.Mesh(new THREE.DodecahedronGeometry(0.16, 0), new THREE.MeshBasicMaterial({ color: night ? 0xff7a3a : 0x6b4a3a }));
      ember.position.set(IR.x, HUT.floor + 0.06, IR.z); ember.scale.set(1.6, 0.5, 1); scene.add(ember);
      if (night) { const pl = new THREE.PointLight(0xff9a50, 2.4, 7, 1.6); pl.position.set(IR.x, HUT.floor + 0.6, IR.z); scene.add(pl); }
      // 방석 4장: 테라코타, 슬레이트 블루, 남색, 녹슨 빨강
      const felt = [0xb5582f, 0x5f7688, 0x2c3446, 0x8c3a2e];
      [[0, -1.55, 0], [1.55, 0, -Math.PI / 2], [0, 1.55, Math.PI], [-1.55, 0, Math.PI / 2]].forEach(([dx, dz, yaw], i) => {
        const x = IR.x + dx, z = IR.z + dz, id = SEATS.length;
        const c = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.52, 0.1, 28), mat(felt[i], { flatShading: false }));
        c.position.set(x, HUT.floor + 0.05, z); c.userData.seat = id; scene.add(c); pickSeats.push(c);
        SEATS.push({ x, z, yaw, y: HUT.floor, lift: 0.1, kind: "hearth" });
      });
      // 칠판(남기는 글)
      board = box(1.6, 1.0, 0.06, 0x2f3b33, HUT.x - 1.6, HUT.floor + 1.5, HUT.z - HUT.d / 2 + 0.2);
      box(1.7, 0.08, 0.1, 0x8a6a4a, HUT.x - 1.6, HUT.floor + 0.98, HUT.z - HUT.d / 2 + 0.24);
      const chalk = new THREE.Mesh(new THREE.PlaneGeometry(1.4, 0.35), new THREE.MeshBasicMaterial({ map: textTexture("오늘의 한 줄", { w: 512, h: 128, fg: "#e8efe6", bg: null, font: "500 54px 'Noto Sans KR', sans-serif" }), transparent: true }));
      chalk.position.set(HUT.x - 1.6, HUT.floor + 1.72, HUT.z - HUT.d / 2 + 0.24); scene.add(chalk);
      board.userData.notes = true; chalk.userData.notes = true; pickHut.push(board, chalk);
      // 노렌(湯) 걸린 입구 쪽 기둥 사이
      const noren = new THREE.Mesh(new THREE.PlaneGeometry(1.6, 0.9), new THREE.MeshLambertMaterial({ map: textTexture("ゆ", { w: 256, h: 160, fg: "#f4efe4", bg: "#2b3a55", radius: 0, font: "500 96px 'Noto Serif KR', serif" }), side: THREE.DoubleSide }));
      noren.position.set(HUT.x - HUT.w / 2 + 0.15, HUT.floor + 2.5, HUT.z + 1.2); noren.rotation.y = Math.PI / 2; hutRoof.add(noren);
    }

    // ---------------------------------------------------------------- 디딤돌과 석등
    const path = [[-2, 6.5], [0.5, 4.2], [3.2, 2.6], [5.6, 1.2]];
    path.forEach(([x, z]) => { const s = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.6, 0.12, 9), mat(0x8a8d90)); s.position.set(x, 0.06, z); scene.add(s); });
    const lampFires = [];
    function lantern(x, z) {
      cyl(0.18, 0.24, 1.1, 6, 0x7d7a74, x, 0.55, z); box(0.6, 0.45, 0.6, 0x8a8780, x, 1.32, z);
      const f = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.3, 0.62), new THREE.MeshBasicMaterial({ color: night ? 0xffd08a : 0xd8d0be }));
      f.position.set(x, 1.32, z); scene.add(f); lampFires.push(f);
      roof(0.9, 0.9, 0.35, 0.2, 0x6f6c66, x, 1.72, z); roof(0.8, 0.8, 0.25, 0.2, SNOW, x, 1.92, z);
      if (night) { const pl = new THREE.PointLight(0xffb867, PAL.lamp, 8, 1.8); pl.position.set(x, 1.5, z); scene.add(pl); }
    }
    lantern(-8.6, 1.5); lantern(4.2, -6.5); lantern(-0.5, 7.6);

    // ---------------------------------------------------------------- 내리는 눈
    const flakes = (() => {
      const n = 900, p = new Float32Array(n * 3), v = [];
      for (let i = 0; i < n; i++) { p[i * 3] = rand(-30, 30); p[i * 3 + 1] = rand(0, 18); p[i * 3 + 2] = rand(-30, 22); v.push(rand(0.6, 1.3)); }
      const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(p, 3));
      const pts = new THREE.Points(g, new THREE.PointsMaterial({ color: 0xffffff, size: 0.09, transparent: true, opacity: 0.9, depthWrite: false }));
      pts.userData.v = v; scene.add(pts); return pts;
    })();

    // ---------------------------------------------------------------- 걷기
    const inPool = (x, z) => { const a = Math.atan2(z - POOL.z, x - POOL.x); return Math.hypot(x - POOL.x, z - POOL.z) < poolR(a) - 0.2; };
    function heightAt(x, z) {
      if (inHut(x, z)) return HUT.floor;
      if (inPool(x, z)) return FLOOR_Y + 0.05;
      return 0;
    }
    const AREA = 18;
    function clampWalk(x, z) {
      x = Math.max(-AREA, Math.min(AREA - 4, x)); z = Math.max(-14, Math.min(12, z));
      // 휴게소 벽(뒤·오른쪽)은 막고, 앞과 왼쪽으로만 드나든다
      const lx = x - HUT.x, lz = z - HUT.z;
      if (Math.abs(lx) < HUT.w / 2 + 0.2 && Math.abs(lz) < HUT.d / 2 + 0.2 && !inHut(x, z)) {
        if (lz < -HUT.d / 2 + 0.3 || lx > HUT.w / 2 - 0.3) return null;
      }
      return [x, z];
    }
    // 휴게소 입구는 왼쪽 면(노렌 아래)
    const DOOR = [HUT.x - HUT.w / 2 - 0.6, HUT.z + 1.2];
    function route(fx, fz, tx, tz) {
      const a = inHut(fx, fz), b = inHut(tx, tz);
      if (a === b) return [[tx, tz]];
      if (b) return [DOOR, [HUT.x - HUT.w / 2 + 0.8, HUT.z + 1.2], [tx, tz]];
      return [[HUT.x - HUT.w / 2 + 0.8, HUT.z + 1.2], DOOR, [tx, tz]];
    }

    // ---------------------------------------------------------------- 물 튕기기
    const drops = [];
    for (let i = 0; i < 10; i++) {
      const d = new THREE.Mesh(new THREE.SphereGeometry(0.05, 6, 4), new THREE.MeshBasicMaterial({ color: 0xe8fbff, transparent: true, opacity: 0.9 }));
      d.visible = false; scene.add(d); drops.push(d);
    }
    let splashT = 0;
    function splash(E) {
      const p = E.me.g.position, f = [Math.sin(E.me.yaw), Math.cos(E.me.yaw)];
      drops.forEach((d) => { d.visible = true; d.position.set(p.x + f[0] * 0.6, WATER_Y + 0.1, p.z + f[1] * 0.6); d.userData.v = new THREE.Vector3(f[0] * rand(0.6, 1.8) + rand(-0.6, 0.6), rand(2, 3.4), f[1] * rand(0.6, 1.8) + rand(-0.6, 0.6)); });
      splashT = 1.2; E.sfx("splash");
    }
    const waterSeat = (s) => s.kind === "water";
    const hearthSeat = (s) => s.kind === "hearth";

    return {
      seats: SEATS, seatNoun: "자리", heightAt,
      spawn: { x: -2, z: 9.5, yaw: Math.PI },
      cam: { pitch: 0.4, seatPitch: 0.5, focusPitch: 0.46 },
      fog: { near: 16, far: 70, fnear: 4, ffar: 20 },
      fireflies: false,
      picks: [...pickSeats, ...pickHut, ...pickGround],
      indoor: inHut,
      planWalk(from, p) { const c = clampWalk(p.x, p.z); return c ? route(from.x, from.z, c[0], c[1]) : null; },
      planTo(from, x, z) { return route(from.x, from.z, x, z); },
      planSeat(from, id) {
        const s = SEATS[id];
        if (s.kind === "hearth") return route(from.x, from.z, s.x, s.z);
        const a = Math.atan2(s.z - POOL.z, s.x - POOL.x), r = poolR(a) + 0.9;
        const edge = [POOL.x + Math.cos(a) * r, POOL.z + Math.sin(a) * r];
        return route(from.x, from.z, edge[0], edge[1]).concat([[s.x, s.z]]);
      },
      leaveSeat(s) {
        if (s.kind === "hearth") return [s.x - Math.sin(s.yaw) * 0.8, s.z - Math.cos(s.yaw) * 0.8];
        const a = Math.atan2(s.z - POOL.z, s.x - POOL.x), r = poolR(a) + 0.9; return [POOL.x + Math.cos(a) * r, POOL.z + Math.sin(a) * r];
      },
      step(x, z, nx, nz) {
        const c = clampWalk(nx, nz); if (!c) return [x, z];
        // 휴게소는 입구로만 드나든다
        if (inHut(x, z) !== inHut(c[0], c[1]) && Math.abs(nz - DOOR[1]) > 1.1) return [x, z];
        return c;
      },
      welcome: "눈 내리는 노천탕이에요. 탕에 몸을 담그거나 화롯가 방석에 앉아 보세요.",
      sitText: (s) => s.kind === "water" ? "따뜻한 물에 몸을 담갔어요. 시간을 고르고 집중을 시작해 보세요." : "화롯가 방석에 앉았어요. 숯불 소리를 들으며 시작해 볼까요?",
      sitSound: (s) => s.kind === "water" ? "soak" : "cushion",
      focusText: (m) => `${m}분, 김이 오르는 동안 한 가지에만.`,
      spaceAction: "splash",
      actions: { free: ["soak", "hearth", "splash", "breathe"], sitting: ["focus", "breathe", "splash", "stand"], focus: ["breathe", "stop"] },
      labels: { soak: "탕에 들어가기", hearth: "화롯가로", splash: "물 튕기기" },
      icons: {
        soak: '<svg viewBox="0 0 24 24"><path d="M3 15c2 1.5 4 1.5 6 0s4-1.5 6 0 4 1.5 6 0M3 19c2 1.5 4 1.5 6 0s4-1.5 6 0 4 1.5 6 0M8 11c0-2 2-2 2-4M13 11c0-2 2-2 2-4"/></svg>',
        hearth: '<svg viewBox="0 0 24 24"><rect x="4" y="9" width="16" height="11" rx="1"/><path d="M12 17c-2 0-3-1.5-2-3.5.5 1 1.5 1 1.5 0 0-1.5 1-2.5 2-3 0 1.5 1.5 2 1.5 4a2.5 2.5 0 0 1-3 2.5z"/></svg>',
        splash: '<svg viewBox="0 0 24 24"><path d="M12 4c3 4 5 6.5 5 9a5 5 0 0 1-10 0c0-2.5 2-5 5-9z"/></svg>',
      },
      custom: {
        soak(E) { if (E.state === "focus") return E.whisper("집중 중이에요. 먼저 '그만하기'를 누르세요."); const s = E.nearestSeat(waterSeat); s === null ? E.whisper("탕 자리가 꽉 찼어요. 화롯가는 어때요?") : E.sit(s); },
        hearth(E) { if (E.state === "focus") return E.whisper("집중 중이에요. 먼저 '그만하기'를 누르세요."); const s = E.nearestSeat(hearthSeat); s === null ? E.whisper("화롯가 방석이 다 찼어요.") : E.sit(s); },
        splash(E) {
          if (!inPool(E.me.pos.x, E.me.pos.z) && E.me.seat === null) {
            const a = Math.atan2(E.me.pos.z - POOL.z, E.me.pos.x - POOL.x), r = poolR(a) + 0.6;
            if (!E.walk(route(E.me.pos.x, E.me.pos.z, POOL.x + Math.cos(a) * r, POOL.z + Math.sin(a) * r), () => { E.face(POOL.x, POOL.z); setTimeout(() => splash(E), 250); })) return;
            return;
          }
          splash(E); E.whisper("찰방— 물방울이 김 속으로 흩어져요.");
        },
      },
      sounds: {
        loops: [{ f: "sento/water", g: 0.75 }, { f: "sento/spout", g: 0.45 }, { f: "sanji/wind", g: 0.22 }],
        gusts: [{ f: "sento/drips", max: 0.5, every: [10, 22] }, { f: "sento/bamboo", max: 0.35, every: [18, 34] }],
        sfx: { splash: { f: "sento/splash", g: 0.8, jitter: true }, soak: { f: "sento/splash", g: 0.45, rate: 0.8, lp: 2000 } },
        steps: { f: "common/steps", out: 0.4, in: 0.15 },
      },
      update(dt, t, E) {
        hutRoof.visible = !inHut(E.me.pos.x, E.me.pos.z);
        // 김: 물 위에서 천천히 올라가며 퍼졌다 사라진다
        steam.forEach((sp) => {
          const u = sp.userData; u.t += dt;
          if (u.t > u.life) { u.t = 0; u.a = Math.random() * Math.PI * 2; u.r = Math.random() * 0.85; }
          const k = u.t / u.life, rr = poolR(u.a) * u.r;
          sp.position.set(POOL.x + Math.cos(u.a) * rr + Math.sin(t * 0.3 + u.a) * 0.4 * k, WATER_Y + 0.2 + k * 3.2, POOL.z + Math.sin(u.a) * rr);
          sp.scale.setScalar(1.2 + k * 2.6); sp.material.opacity = Math.sin(k * Math.PI) * (state(E) ? 0.22 : 0.32);
        });
        // 홈통 물줄기 물결
        const rk = (t * 0.8) % 1; ripple.scale.setScalar(1 + rk * 3); ripple.material.opacity = 0.5 * (1 - rk);
        // 눈
        const p = flakes.geometry.attributes.position, v = flakes.userData.v;
        for (let i = 0; i < v.length; i++) {
          let y = p.getY(i) - v[i] * dt; let x = p.getX(i) + Math.sin(t * 0.6 + i) * 0.006;
          if (y < 0) { y = 18; x = rand(-30, 30); p.setZ(i, rand(-30, 22)); }
          p.setY(i, y); p.setX(i, x);
        }
        p.needsUpdate = true;
        // 물방울
        if (splashT > 0) {
          splashT -= dt;
          drops.forEach((d) => { if (!d.visible) return; d.userData.v.y -= 9.8 * dt; d.position.addScaledVector(d.userData.v, dt); if (d.position.y < WATER_Y) d.visible = false; });
        }
        if (night) lampFires.forEach((f, i) => f.material.color.setHSL(0.09, 1, 0.72 + Math.sin(t * 6 + i * 2) * 0.03));
      },
    };
    function state(E) { return E.state === "focus"; }
  },
};
