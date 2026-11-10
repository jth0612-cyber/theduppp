// 소도시 명상 · 바닷가 역. 하치노헤 쪽 바닷가의 작은 무인역 느낌:
// 자갈 마당, 노란 난간 계단, 높은 승강장 하나, 선로 한 줄, 큰 삼나무, 그리고 승강장 너머 태평양.
// 가끔 두 칸짜리 디젤 열차가 들어왔다가 떠난다.
export default {
  palette(PAL, TIME) {
    Object.assign(PAL, {
      // 맑은 여름 아침의 투명한 파랑
      day:   { top: 0x3f7fc4, horizon: 0xd8e8f2, fog: 0xcfe0ec, hemiSky: 0xfdf6e6, hemiGround: 0x5f7a4a, hemi: 1.05, sun: 0xfff2d8, sunI: 1.7, ground: 0x8d8a86, grass: 0x6f9a48, lamp: 0.4 },
      // 해가 넘어간 뒤의 파스텔 하늘: 위는 옅은 하늘색, 수평선은 크림·복숭아빛 (참고 영상)
      dusk:  { top: 0x7f9fc8, horizon: 0xf4d6b0, fog: 0xdccab8, hemiSky: 0xece6e4, hemiGround: 0x5a5650, hemi: 0.95, sun: 0xffc890, sunI: 0.85, ground: 0x8a8480, grass: 0x66784a, lamp: 1.3 },
      // 푸른 시간
      night: { top: 0x141f55, horizon: 0x6a5aa0, fog: 0x2a3168, hemiSky: 0x9aa0e8, hemiGround: 0x2a2a3a, hemi: 0.95, sun: 0xa8b4f0, sunI: 0.35, ground: 0x4a4a5a, grass: 0x2a3a34, lamp: 2.2 },
    }[TIME]);
  },
  build(K) {
    const { THREE, scene, camera, TIME, PAL, mat, box, cyl, roof, textTexture, rand, srand, trees } = K;
    const night = TIME === "night", dusk = TIME === "dusk";
    const pickGround = [];
    const PLAT = { x0: -15, x1: 15, z0: 0.2, z1: 3.0, h: 1.0 };
    const TRACK_Z = -1.3;
    const STAIR = { x0: 6.3, x1: 7.9, z0: 3.0, z1: 5.6 };
    const LOT = { x0: -17, x1: 17, z0: 3.3, z1: 15 };

    // ---------------------------------------------------------------- 땅: 자갈 마당, 풀, 바다로 내려가는 비탈
    {
      const lot = new THREE.Mesh(new THREE.PlaneGeometry(LOT.x1 - LOT.x0, LOT.z1 - LOT.z0 + 2), mat(PAL.ground));
      lot.rotation.x = -Math.PI / 2; lot.position.set(0, 0.01, (LOT.z0 + LOT.z1) / 2 + 1); scene.add(lot); pickGround.push(lot);
      // 자갈 얼룩
      for (let i = 0; i < 60; i++) {
        const s = new THREE.Mesh(new THREE.CircleGeometry(rand(0.03, 0.07), 5), mat(srand() > 0.5 ? 0x6f6c69 : 0xa8a49e));
        s.rotation.x = -Math.PI / 2; s.position.set(rand(LOT.x0, LOT.x1), 0.015, rand(LOT.z0, LOT.z1)); scene.add(s);
      }
      const grass = new THREE.Mesh(new THREE.PlaneGeometry(160, 60), mat(PAL.grass)); grass.rotation.x = -Math.PI / 2; grass.position.set(0, -0.01, 30); scene.add(grass);
      // 선로 너머: 풀 비탈이 바다 쪽으로 내려간다
      const slope = new THREE.Mesh(new THREE.PlaneGeometry(160, 26), mat(PAL.grass)); slope.rotation.x = -Math.PI / 2 - 0.12; slope.position.set(0, -1.4, -15.5); scene.add(slope);   // 선로 쪽이 높고 바다 쪽으로 내려간다
      const beach = new THREE.Mesh(new THREE.PlaneGeometry(160, 8), mat(TIME === "day" ? 0xd9ccb0 : 0x6a6260)); beach.rotation.x = -Math.PI / 2; beach.position.set(0, -2.95, -31); scene.add(beach);
      // 풀숲과 덤불 (잎 뭉치 카드)
      const slopeY = (z) => (z < -3 ? -0.2 - (Math.abs(z) - 3) * 0.12 : 0);
      for (let i = 0; i < 46; i++) { const x = rand(-40, 40), z = srand() > 0.5 ? rand(-14, -3) : rand(16, 30); trees.bush(x, z, rand(0.7, 1.3), { y: slopeY(z) - 0.1 }); }
      for (let i = 0; i < 160; i++) { const x = rand(-40, 40), z = srand() > 0.35 ? TRACK_Z - rand(1.4, 3.2) : rand(-14, -3); trees.grass(x, z, rand(0.6, 1.2), { y: slopeY(z) }); }
    }

    // ---------------------------------------------------------------- 바다 (가까울수록 옥빛, 멀수록 짙은 파랑)
    const SHORE_Z = -31, SEA_Y = -3.05;
    const seaG = new THREE.PlaneGeometry(500, 230, 90, 46);
    {
      const near = new THREE.Color(TIME === "day" ? 0x6aa9ac : dusk ? 0xa8bcc4 : 0x2c3a6e);
      const far = new THREE.Color(TIME === "day" ? 0x2c5f8c : dusk ? 0x8ea0bc : 0x1c2456);
      const cols = [], pa = seaG.attributes.position;
      for (let i = 0; i < pa.count; i++) { const k = Math.min(1, Math.max(0, (pa.getY(i) + 115) / 230)); const c = far.clone().lerp(near, Math.pow(k, 2.2)); cols.push(c.r, c.g, c.b); }
      seaG.setAttribute("color", new THREE.Float32BufferAttribute(cols, 3));
    }
    const sea = new THREE.Mesh(seaG, new THREE.MeshPhongMaterial({ vertexColors: true, shininess: 90, specular: dusk ? 0xffd2a0 : TIME === "day" ? 0xcfe4f0 : 0x8890d0 }));
    sea.rotation.x = -Math.PI / 2; sea.position.set(0, SEA_Y, SHORE_Z - 115); scene.add(sea);
    const seaBase = seaG.attributes.position.array.slice();
    // 젖은 모래 띠
    { const wet = new THREE.Mesh(new THREE.PlaneGeometry(160, 2.2), mat(TIME === "day" ? 0xb9ab90 : dusk ? 0x9a8c80 : 0x4a4652)); wet.rotation.x = -Math.PI / 2; wet.position.set(0, -2.94, SHORE_Z - 0.6); scene.add(wet); }
    // 밀려와 부서지는 흰 파도: 거품 띠가 바다 쪽에서 모래까지 밀려왔다 스며든다
    const foamTex = (() => {
      const c = document.createElement("canvas"); c.width = 512; c.height = 64; const x = c.getContext("2d");
      for (let i = 0; i < 900; i++) { const y = 8 + Math.pow(Math.random(), 1.6) * 52; x.fillStyle = `rgba(255,255,255,${0.15 + Math.random() * 0.5})`; x.beginPath(); x.ellipse(Math.random() * 512, y, 2 + Math.random() * 10, 1 + Math.random() * 2.5, 0, 0, Math.PI * 2); x.fill(); }
      const gr = x.createLinearGradient(0, 0, 0, 64); gr.addColorStop(0, "rgba(255,255,255,0.95)"); gr.addColorStop(0.18, "rgba(255,255,255,0.75)"); gr.addColorStop(1, "rgba(255,255,255,0)");
      x.globalCompositeOperation = "destination-in"; x.fillStyle = gr; x.fillRect(0, 0, 512, 64);
      const t = new THREE.CanvasTexture(c); t.wrapS = THREE.RepeatWrapping; t.repeat.set(10, 1); t.colorSpace = THREE.SRGBColorSpace; return t;
    })();
    const foams = [];
    for (let i = 0; i < 3; i++) {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(170, 3.2), new THREE.MeshBasicMaterial({ map: foamTex.clone(), transparent: true, depthWrite: false, opacity: 0, color: dusk ? 0xfff0e0 : TIME === "day" ? 0xffffff : 0xb8c0e8 }));
      m.material.map.needsUpdate = true; m.material.map.offset.x = Math.random();
      m.rotation.x = -Math.PI / 2; scene.add(m);
      const lip = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.32, 170, 8, 1, true), new THREE.MeshPhongMaterial({ color: TIME === "day" ? 0x8cc6c2 : dusk ? 0xb0c0c4 : 0x3a4a80, transparent: true, opacity: 0, shininess: 60, depthWrite: false }));
      lip.rotation.z = Math.PI / 2; scene.add(lip);
      foams.push({ m, lip, ph: i / 3 });
    }
    // 방파 블록(테트라포드) 줄
    {
      const tM = mat(TIME === "day" ? 0xa9a6a0 : dusk ? 0x8e8a88 : 0x3a3a44);
      for (const [x0, x1, z] of [[-70, -22, -58], [14, 58, -62]]) for (let x = x0; x < x1; x += 1.3) {
        const tp = new THREE.Mesh(new THREE.TetrahedronGeometry(0.9 + Math.random() * 0.3, 0), tM);
        tp.position.set(x, SEA_Y + 0.25, z + (Math.random() - 0.5) * 1.2); tp.rotation.set(Math.random() * 3, Math.random() * 3, Math.random() * 3); scene.add(tp);
      }
    }
    // 구름: 낮엔 몽글한 뭉게구름, 저녁엔 길게 늘어진 새털구름(복숭아빛), 밤엔 낮게 깔린 짙은 구름
    const cloudTex = (() => {           // 뭉게구름: 가장자리가 그림 밖으로 잘리지 않게 안쪽에만 그리고, 둥근 가림으로 한 번 더 부드럽게
      const c = document.createElement("canvas"); c.width = c.height = 256; const x = c.getContext("2d");
      for (let i = 0; i < 18; i++) { const cx = 80 + Math.random() * 96, cy = 108 + Math.random() * 40, r = 22 + Math.random() * 30;
        const gr = x.createRadialGradient(cx, cy, 0, cx, cy, r); gr.addColorStop(0, "rgba(255,255,255,.5)"); gr.addColorStop(1, "rgba(255,255,255,0)"); x.fillStyle = gr; x.fillRect(0, 0, 256, 256); }
      x.globalCompositeOperation = "destination-in";
      const m = x.createRadialGradient(128, 128, 40, 128, 128, 126); m.addColorStop(0, "rgba(0,0,0,1)"); m.addColorStop(1, "rgba(0,0,0,0)"); x.fillStyle = m; x.fillRect(0, 0, 256, 256);
      const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
    })();
    const clouds = [];
    for (let i = 0; i < (TIME === "day" ? 10 : 14); i++) {
      const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: cloudTex, transparent: true, depthWrite: false, fog: false,
        color: TIME === "day" ? 0xffffff : dusk ? (i % 3 ? 0xffe2c8 : 0xf6c8b8) : 0x2a3266, opacity: TIME === "day" ? 0.85 : dusk ? 0.6 : 0.8 }));
      const w = TIME === "day" ? rand(30, 60) : dusk ? rand(70, 140) : rand(40, 90);
      s.scale.set(w, TIME === "day" ? w * 0.45 : dusk ? w * 0.09 : w * 0.18, 1);
      s.position.set(rand(-200, 200), TIME === "day" ? rand(30, 70) : dusk ? rand(28, 90) : rand(14, 32), rand(-205, -150));
      s.userData.v = rand(0.3, 0.9); scene.add(s); clouds.push(s);
    }
    // ---------------------------------------------------------------- 도호쿠 바닷가 마을 집 (참고 사진): 2층, 밝은 사이딩 벽,
    // 낮은 경사의 함석 모임지붕(짙은 초록·남색·밤색, 세로 골), 넓은 처마와 물받이, 큰 알루미늄 미닫이창, 옆에 작은 헛간, TV 안테나
    function texOf(w, h, draw, rx, ry) { const c = document.createElement("canvas"); c.width = w; c.height = h; draw(c.getContext("2d")); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(rx, ry); t.anisotropy = 4; return t; }
    const sidingTex = (base) => texOf(64, 64, (x) => { x.fillStyle = base; x.fillRect(0, 0, 64, 64); x.fillStyle = "rgba(0,0,0,.07)"; for (let y = 0; y < 64; y += 16) x.fillRect(0, y, 64, 1.5); x.fillStyle = "rgba(255,255,255,.18)"; for (let y = 1; y < 64; y += 16) x.fillRect(0, y + 1, 64, 1); }, 3, 3);
    const tinTex = (base) => texOf(64, 64, (x) => { x.fillStyle = base; x.fillRect(0, 0, 64, 64); for (let i = 0; i < 64; i += 8) { x.fillStyle = "rgba(255,255,255,.12)"; x.fillRect(i, 0, 1.5, 64); x.fillStyle = "rgba(0,0,0,.18)"; x.fillRect(i + 2, 0, 1, 64); } }, 6, 2);
    const WALLS = ["#e6e5df", "#d9d6cc", "#eceae4", "#cfd2cf"].map((c) => new THREE.MeshLambertMaterial({ map: sidingTex(c) }));
    const ROOFS = ["#2f4a42", "#2c3a52", "#5a3a2e", "#3a4448"].map((c) => new THREE.MeshLambertMaterial({ map: tinTex(c) }));
    const sash = 0x8f969a, glassC = TIME === "day" ? 0x6e8592 : 0xffd394;
    function tinRoof(w, d, h, m, x, y, z, g) {            // 낮은 모임지붕 + 처마 끝 물받이
      const r = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 1, h, 4, 1), m); r.geometry.rotateY(Math.PI / 4);
      r.scale.set(w / Math.SQRT2, 1, d / Math.SQRT2); r.position.set(x, y + h / 2, z); g.add(r);
      for (const sz of [-1, 1]) box(w * 0.98, 0.08, 0.1, 0x6a6e70, x, y + 0.02, z + sz * d / 2 * 0.98, g);
      return r;
    }
    function windowAt(g, x, y, z, w, h, rotY = 0) {
      const f = new THREE.Group(); f.position.set(x, y, z); f.rotation.y = rotY; g.add(f);
      const gl = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshPhongMaterial({ color: glassC, shininess: 80, specular: 0x9aa8b0, emissive: TIME === "day" ? 0x000000 : 0x3a2a10 })); gl.position.z = 0.01; f.add(gl);
      box(w + 0.1, 0.07, 0.08, sash, 0, h / 2, 0.03, f); box(w + 0.1, 0.07, 0.08, sash, 0, -h / 2, 0.03, f);
      box(0.07, h, 0.08, sash, -w / 2, 0, 0.03, f); box(0.07, h, 0.08, sash, w / 2, 0, 0.03, f); box(0.05, h, 0.06, sash, 0, 0, 0.04, f);   // 두 짝 미닫이
      if (TIME === "day") { const cur = new THREE.Mesh(new THREE.PlaneGeometry(w * 0.35, h * 0.9), mat(0xe8e2d4)); cur.position.set(-w * 0.3, 0, 0.015); f.add(cur); }
    }
    function jpHouse(x, y, z, r, sc = 1, two = true, seed = 0) {
      const g = new THREE.Group(); g.position.set(x, y, z); g.rotation.y = r; g.scale.setScalar(sc); scene.add(g);
      const wm = WALLS[seed % WALLS.length], rm = ROOFS[(seed + 1) % ROOFS.length];
      const W = 6.4, D = 5, H1 = 2.7, H2 = 2.5;
      box(W + 0.3, 0.35, D + 0.3, 0x9a9690, 0, 0.17, 0, g);                                        // 콘크리트 기초
      const m1 = new THREE.Mesh(new THREE.BoxGeometry(W, H1, D), wm); m1.position.y = 0.35 + H1 / 2; g.add(m1);
      windowAt(g, -1.2, 0.35 + 1.4, D / 2, 2.6, 1.7); windowAt(g, 1.9, 0.35 + 1.55, D / 2, 1.2, 1.0);
      box(1.0, 2.0, 0.06, 0x6a5a48, 1.9, 0.35 + 1.0 - 0.3, D / 2 + 0.02, g);                       // 현관 문
      if (two) {
        tinRoof(W + 1.0, D + 1.0, 0.45, rm, 0, 0.35 + H1, 0, g);                                    // 1층 처마 지붕
        const m2 = new THREE.Mesh(new THREE.BoxGeometry(W - 0.6, H2, D - 0.8), wm); m2.position.y = 0.35 + H1 + 0.25 + H2 / 2; g.add(m2);
        windowAt(g, -1.3, 0.35 + H1 + 1.45, (D - 0.8) / 2, 2.2, 1.3); windowAt(g, 1.4, 0.35 + H1 + 1.45, (D - 0.8) / 2, 1.6, 1.3);
        box(2.4, 0.5, 0.5, wm.color ? 0xe0ddd4 : 0xe0ddd4, -1.3, 0.35 + H1 + 0.75, (D - 0.8) / 2 + 0.25, g);   // 2층 창 아래 화분대
        const top = 0.35 + H1 + 0.25 + H2;
        tinRoof(W + 0.6, D + 0.2, 1.0, rm, 0, top, 0, g);
        cyl(0.025, 0.025, 1.6, 4, 0x8a8a8a, 0.8, top + 1.5, -0.6, g); box(1.2, 0.03, 0.03, 0x8a8a8a, 0.8, top + 2.1, -0.6, g); box(0.8, 0.03, 0.03, 0x8a8a8a, 0.8, top + 1.9, -0.6, g);   // 안테나
      } else {
        tinRoof(W + 1.0, D + 1.0, 1.1, rm, 0, 0.35 + H1, 0, g);
      }
      cyl(0.04, 0.04, H1 + (two ? H2 : 0), 6, 0x6a6e70, W / 2 + 0.05, 0.35 + (H1 + (two ? H2 : 0)) / 2, D / 2 + 0.05, g);   // 물받이 홈통
      // 옆의 작은 헛간 (외쪽 경사 지붕)
      const sh = new THREE.Group(); sh.position.set(W / 2 + 1.6, 0, 0.6); g.add(sh);
      const shm = new THREE.Mesh(new THREE.BoxGeometry(2.0, 2.0, 2.4), WALLS[(seed + 2) % WALLS.length]); shm.position.y = 1.0; sh.add(shm);
      const sr = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.08, 2.8), ROOFS[(seed + 2) % ROOFS.length]); sr.position.y = 2.15; sr.rotation.x = 0.18; sh.add(sr);
      return g;
    }
    // 승강장 아래 비탈의 마을: 기와지붕 목조집, 가지 늘어진 벚나무
    {
      [[-19, -14, 0.2, 0.9, true], [-6, -16.5, -0.1, 0.85, false], [12, -15, 0.15, 0.9, true], [24, -13, -0.2, 0.85, false], [-31, -12, 0.3, 0.9, true], [35, -11, 0, 0.85, true]].forEach(([x, z, r, sc, two], i) =>
        jpHouse(x, -0.2 - (-z - 3) * 0.12 - 0.05, z, r, sc, two, i));
      const blossom = TIME === "day" ? 0xfad2dc : dusk ? 0xe6aab4 : 0x6a5070;
      [[-14, -9, 0.85, true], [17, -10, 0.8, true], [-24, -13, 1.0, false], [27, -12, 0.9, true], [3, -26, 0.8, false]].forEach(([x, z, sc, w]) =>
        trees.broad(x, z, sc, { y: z < -3 ? -0.2 - (-z - 3) * 0.12 : 0, kind: "petal", leaf: blossom, bark: 0x3c2e2a, weeping: w }));
    }
    // 오른쪽 곶(숲 실루엣)과 등대
    {
      const capeC = TIME === "day" ? 0x3d5e3a : 0x14181c;
      const cape = new THREE.Mesh(new THREE.SphereGeometry(30, 16, 10, 0, Math.PI * 2, 0, Math.PI / 2), mat(capeC)); cape.scale.set(1.6, 0.4, 0.8); cape.position.set(95, -3, -150); scene.add(cape);
      const cape2 = new THREE.Mesh(new THREE.SphereGeometry(20, 14, 8, 0, Math.PI * 2, 0, Math.PI / 2), mat(capeC)); cape2.scale.set(2.2, 0.35, 0.9); cape2.position.set(-110, -3, -120); scene.add(cape2);
      // 등대: 흰 탑, 붉은 띠, 난간, 유리 등실, 둥근 지붕
      cyl(0.9, 1.25, 7, 16, 0xf2efe8, 62, 4, -142); cyl(0.98, 1.0, 0.5, 16, 0xb84a3a, 62, 6.2, -142);
      cyl(1.35, 1.35, 0.12, 16, 0x3a3c40, 62, 7.55, -142);
      const lamp = new THREE.Mesh(new THREE.CylinderGeometry(0.62, 0.62, 0.9, 12), new THREE.MeshBasicMaterial({ color: TIME === "day" ? 0xa8c4d0 : 0xfff2c8 })); lamp.position.set(62, 8.05, -142); scene.add(lamp);
      const dome = new THREE.Mesh(new THREE.SphereGeometry(0.72, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2), mat(0xb84a3a)); dome.position.set(62, 8.5, -142); scene.add(dome);
    }
    // 등대 빛 (밤·저녁): 빛줄기는 늘 카메라 쪽을 향한 부드러운 띠로 그려(어느 각도에서 봐도 판자처럼 보이지 않게),
    // 끝으로 갈수록 옅어진다. 빛이 이쪽을 비추는 순간 등실이 반짝 밝아진다.
    const LH = new THREE.Vector3(62, 8.05, -142), lit = TIME !== "day";
    const beamTex = (() => {
      const c = document.createElement("canvas"); c.width = 256; c.height = 64; const x = c.getContext("2d"), img = x.createImageData(256, 64);
      for (let i = 0; i < 256; i++) for (let j = 0; j < 64; j++) {
        const u = i / 255, v = (j - 31.5) / 32, along = Math.pow(1 - u, 1.6) * Math.min(1, u * 30), across = Math.exp(-v * v * (3 + u * 2));
        const a = along * across, k = (j * 256 + i) * 4; img.data[k] = 255; img.data[k + 1] = 242; img.data[k + 2] = 210; img.data[k + 3] = Math.round(a * 255);
      }
      x.putImageData(img, 0, 0); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
    })();
    const beams = [0, Math.PI].map((off) => {
      const g = new THREE.PlaneGeometry(1, 1); g.translate(0.5, 0, 0);
      const m = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ map: beamTex, transparent: true, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, fog: false, opacity: dusk ? 0.22 : 0.38 }));
      m.matrixAutoUpdate = false; m.visible = lit; m.userData.off = off; m.userData.noOcclude = true; scene.add(m); return m;
    });
    const haloTex = (() => {
      const c = document.createElement("canvas"); c.width = c.height = 128; const x = c.getContext("2d");
      const rg = x.createRadialGradient(64, 64, 0, 64, 64, 64); rg.addColorStop(0, "rgba(255,248,226,1)"); rg.addColorStop(0.12, "rgba(255,240,205,.7)"); rg.addColorStop(0.4, "rgba(255,230,190,.16)"); rg.addColorStop(1, "rgba(255,230,190,0)");
      x.fillStyle = rg; x.fillRect(0, 0, 128, 128); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
    })();
    const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: haloTex, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, fog: false }));
    halo.position.copy(LH); halo.scale.setScalar(6); halo.visible = lit; scene.add(halo);
    const _d = new THREE.Vector3(), _c = new THREE.Vector3(), _s = new THREE.Vector3(), _n = new THREE.Vector3(), _m = new THREE.Matrix4();
    function updateBeam(t) {
      if (!lit) return;
      _c.subVectors(camera.position, LH); const dist = _c.length(); _c.normalize();
      let flash = 0;
      beams.forEach((b) => {
        const a = t * 0.45 + b.userData.off; _d.set(Math.cos(a), -0.04, Math.sin(a)).normalize();
        _s.crossVectors(_d, _c).normalize(); _n.crossVectors(_d, _s);
        const L = 90, Wd = 5;
        _m.makeBasis(_d.clone().multiplyScalar(L), _s.clone().multiplyScalar(Wd), _n); _m.setPosition(LH); b.matrix.copy(_m); b.matrixWorldNeedsUpdate = true;
        const face = Math.max(0, _d.dot(_c)); flash = Math.max(flash, Math.pow(face, 24));
        b.material.opacity = (dusk ? 0.22 : 0.38) * (1 - face * 0.7);            // 정면으로 올 때는 띠 대신 반짝임으로
      });
      halo.scale.setScalar(6 + flash * 26 * Math.min(1, dist / 120)); halo.material.opacity = 0.75 + flash * 0.25;
    }
    // 고기잡이배 불빛
    const boat = new THREE.Group(); boat.position.set(-50, -2.9, -120); scene.add(boat);
    box(3, 0.6, 1, TIME === "day" ? 0xf2f0ea : 0x22242c, 0, 0, 0, boat); box(1, 0.8, 0.8, TIME === "day" ? 0xe8e4dc : 0x22242c, -0.5, 0.6, 0, boat);
    if (TIME !== "day") { const l = new THREE.Mesh(new THREE.SphereGeometry(0.3, 8, 6), new THREE.MeshBasicMaterial({ color: 0xb8ffd8, fog: false })); l.position.set(-0.5, 1.3, 0); boat.add(l); }

    // ---------------------------------------------------------------- 선로
    {
      const ballast = new THREE.Mesh(new THREE.BoxGeometry(260, 0.35, 3.2), mat(TIME === "day" ? 0x55524f : 0x3a3838)); ballast.position.set(0, 0.17, TRACK_Z); scene.add(ballast);
      const tieM = mat(TIME === "day" ? 0xb9b4aa : 0x6a6662);
      const ties = new THREE.InstancedMesh(new THREE.BoxGeometry(0.22, 0.1, 2.3), tieM, 260);
      const m4 = new THREE.Matrix4();
      for (let i = 0; i < 260; i++) { m4.makeTranslation(-130 + i, 0.38, TRACK_Z); ties.setMatrixAt(i, m4); }
      scene.add(ties);
      for (const dz of [-0.72, 0.72]) box(260, 0.12, 0.09, 0x8a6a52, 0, 0.48, TRACK_Z + dz);
    }

    // ---------------------------------------------------------------- 승강장 (높은 철골 위 콘크리트 판)
    const pickPlat = [];
    {
      const deck = box(PLAT.x1 - PLAT.x0, 0.2, PLAT.z1 - PLAT.z0, 0x9c9894, (PLAT.x0 + PLAT.x1) / 2, PLAT.h - 0.1, (PLAT.z0 + PLAT.z1) / 2); pickPlat.push(deck);
      box(PLAT.x1 - PLAT.x0, 0.03, 0.12, 0xf0f0ea, (PLAT.x0 + PLAT.x1) / 2, PLAT.h + 0.01, PLAT.z0 + 0.2);       // 흰 경계선
      box(PLAT.x1 - PLAT.x0, 0.03, 0.3, 0xe8c23a, (PLAT.x0 + PLAT.x1) / 2, PLAT.h + 0.01, PLAT.z0 + 0.75);     // 점자 블록
      for (let x = PLAT.x0 + 1; x < PLAT.x1; x += 2.5) for (const z of [PLAT.z0 + 0.3, PLAT.z1 - 0.3]) box(0.12, PLAT.h - 0.2, 0.12, 0x6a6e72, x, (PLAT.h - 0.2) / 2, z);
      // 노란 난간: 마당 쪽 앞면 (계단 자리만 비운다), 양 끝
      const Y = 0xe6b92a;
      const rail = (x0, x1, z) => { box(x1 - x0, 0.07, 0.07, Y, (x0 + x1) / 2, PLAT.h + 1.0, z); box(x1 - x0, 0.06, 0.06, Y, (x0 + x1) / 2, PLAT.h + 0.55, z); for (let x = x0; x <= x1 + 0.01; x += Math.max(0.5, (x1 - x0) / Math.ceil((x1 - x0) / 2.2))) box(0.08, 1.0, 0.08, Y, x, PLAT.h + 0.5, z); };
      rail(PLAT.x0, STAIR.x0, PLAT.z1 - 0.05); rail(STAIR.x1, PLAT.x1, PLAT.z1 - 0.05);
      for (const x of [PLAT.x0, PLAT.x1]) { box(0.07, 0.07, PLAT.z1 - PLAT.z0, Y, x, PLAT.h + 1.0, (PLAT.z0 + PLAT.z1) / 2); box(0.08, 1.0, 0.08, Y, x, PLAT.h + 0.5, PLAT.z0 + 0.4); }
      // 계단
      const n = 5, sw = STAIR.x1 - STAIR.x0;
      for (let i = 0; i < n; i++) {
        const z = STAIR.z0 + (i + 0.5) * (STAIR.z1 - STAIR.z0) / n, y = PLAT.h - (i + 1) * (PLAT.h / (n + 0.5));
        const st = box(sw, 0.12, (STAIR.z1 - STAIR.z0) / n + 0.02, 0x8e8a86, (STAIR.x0 + STAIR.x1) / 2, y, z); pickPlat.push(st);
      }
      const ang = Math.atan2(PLAT.h, STAIR.z1 - STAIR.z0), len = Math.hypot(PLAT.h, STAIR.z1 - STAIR.z0);
      for (const x of [STAIR.x0, STAIR.x1]) {
        const r = box(0.08, 0.08, len, Y, x, PLAT.h / 2 + 0.95, (STAIR.z0 + STAIR.z1) / 2); r.rotation.x = ang;
        box(0.08, 1.0, 0.08, Y, x, 0.5, STAIR.z1); box(0.08, 1.0, 0.08, Y, x, PLAT.h + 0.5, STAIR.z0);
      }
    }

    // 역 이름판 (지어낸 역 이름)
    {
      const c = document.createElement("canvas"); c.width = 1024; c.height = 256; const x = c.getContext("2d");
      x.fillStyle = "#f6f6f2"; x.fillRect(0, 0, 1024, 256); x.strokeStyle = "#5a5a5a"; x.lineWidth = 8; x.strokeRect(4, 4, 1016, 248);
      x.fillStyle = "#2f9e5a"; x.fillRect(24, 40, 150, 176);
      x.fillStyle = "#fff"; x.font = "700 92px 'Noto Sans KR', sans-serif"; x.textAlign = "center"; x.textBaseline = "middle"; x.fillText("潮", 99, 130);
      x.fillStyle = "#222"; x.font = "600 104px 'Noto Serif KR', serif"; x.fillText("汐見浜駅", 600, 110);
      x.font = "500 44px 'Noto Sans KR', sans-serif"; x.fillText("Shiomihama Station", 600, 205);
      const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
      const sign = new THREE.Mesh(new THREE.PlaneGeometry(3.2, 0.8), new THREE.MeshLambertMaterial({ map: t }));
      sign.position.set(1.5, PLAT.h + 0.78, PLAT.z1 + 0.02); scene.add(sign);
      const back = new THREE.Mesh(new THREE.PlaneGeometry(3.2, 0.8), new THREE.MeshLambertMaterial({ map: t })); back.rotation.y = Math.PI; back.position.set(1.5, PLAT.h + 0.78, PLAT.z1 - 0.1); scene.add(back);
    }
    // 작은 대합실(나무)과 벤치
    const SEATS = [], pickSeats = [];
    const SHED = { x: -7, z: 1.6 };
    {
      box(4.2, 0.12, 2.2, 0x4f3b2c, SHED.x, PLAT.h + 2.5, SHED.z);
      box(4.0, 2.4, 0.1, 0xb59a74, SHED.x, PLAT.h + 1.2, SHED.z + 1.0);
      box(0.1, 2.4, 2.0, 0xb59a74, SHED.x - 2.0, PLAT.h + 1.2, SHED.z);
      box(0.1, 2.4, 2.0, 0xb59a74, SHED.x + 2.0, PLAT.h + 1.2, SHED.z);
      const win = new THREE.Mesh(new THREE.PlaneGeometry(1.2, 0.8), new THREE.MeshBasicMaterial({ color: night ? 0xffd89a : 0x9ab8c8 }));
      win.position.set(SHED.x + 1.0, PLAT.h + 1.6, SHED.z + 0.94); win.rotation.y = Math.PI; scene.add(win);
      box(3.6, 0.08, 0.5, 0x8a6a4a, SHED.x, PLAT.h + 0.45, SHED.z + 0.6);
      for (const dx of [-1.6, 1.6]) box(0.08, 0.45, 0.4, 0x5a4636, SHED.x + dx, PLAT.h + 0.22, SHED.z + 0.6);
      if (TIME !== "day") { const pl = new THREE.PointLight(0xffe0b0, PAL.lamp * 1.4, 7, 1.6); pl.position.set(SHED.x, PLAT.h + 2.3, SHED.z); scene.add(pl);
        const bulb = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.06, 0.12), new THREE.MeshBasicMaterial({ color: 0xfff4dc })); bulb.position.set(SHED.x, PLAT.h + 2.42, SHED.z); scene.add(bulb); }
      for (let i = 0; i < 3; i++) {
        const x = SHED.x - 1.1 + i * 1.1, z = SHED.z + 0.55, id = SEATS.length;
        const hit = new THREE.Mesh(new THREE.BoxGeometry(0.95, 0.12, 0.5), mat(0x9a7a56)); hit.position.set(x, PLAT.h + 0.5, z); hit.userData.seat = id; scene.add(hit); pickSeats.push(hit);
        SEATS.push({ x, z, yaw: Math.PI, y: PLAT.h + 0.3, lift: 0.12, kind: "shed" });
      }
    }
    // 승강장 벤치(바다를 바라본다) — 플라스틱 의자
    const chairC = [0x3d7fb0, 0x3d7fb0, 0xd8d4c8, 0x3d7fb0];
    [-1.5, -0.6, 3.8, 4.7, 10.5, 11.4].forEach((x, i) => {
      const z = 2.3, id = SEATS.length;
      box(0.1, 0.42, 0.1, 0x6a6e72, x, PLAT.h + 0.21, z);
      const c = new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.08, 0.55), mat(chairC[i % 4])); c.position.set(x, PLAT.h + 0.46, z); c.userData.seat = id; scene.add(c); pickSeats.push(c);
      const backrest = box(0.62, 0.5, 0.06, chairC[i % 4], x, PLAT.h + 0.74, z + 0.28);
      backrest.userData.seat = id; pickSeats.push(backrest);              // 뒤에서 등받이를 눌러도 앉는다
      SEATS.push({ x, z, yaw: Math.PI, y: PLAT.h + 0.28, lift: 0.12, kind: "bench" });
    });
    // 마당 끝 나무 벤치 둘 (바다 쪽)
    [[-12.5, 4.4], [-10.6, 4.4], [12, 4.4], [13.9, 4.4]].forEach(([x, z]) => {
      const id = SEATS.length;
      const c = box(1.5, 0.1, 0.5, 0x8a6a4a, x, 0.45, z); c.userData.seat = id; pickSeats.push(c);
      box(0.1, 0.45, 0.4, 0x5a4636, x - 0.6, 0.22, z); box(0.1, 0.45, 0.4, 0x5a4636, x + 0.6, 0.22, z);
      SEATS.push({ x, z, yaw: Math.PI, y: 0.28, lift: 0.12, kind: "lot" });
    });

    // 역 노트 판: 학생들이 남긴 최근 글 다섯 줄 (줄 공책 모양)
    const noteCanvas = document.createElement("canvas"); noteCanvas.width = 768; noteCanvas.height = 414;
    let noteTex = null;
    // 글씨를 maxW 안에서 띄어쓰기 기준으로 줄바꿈 (최대 max줄, 넘치면 마지막 줄 끝에 …)
    function wrapText(x, text, maxW, max) {
      const src = String(text || "").trim(), out = []; let cur = "", rest = "";
      const words = src.split(/(\s+)/);
      for (let wi = 0; wi < words.length; wi++) {
        const w = words[wi];
        if (x.measureText(cur + w).width <= maxW) { cur += w; continue; }
        if (!w.trim()) continue;
        if (cur.trim()) { out.push(cur.trim()); cur = ""; }
        let piece = w;                                   // 한 단어가 한 줄보다 길면 글자 단위로 자른다
        while (x.measureText(piece).width > maxW) { let k = piece.length; while (k > 1 && x.measureText(piece.slice(0, k)).width > maxW) k--; out.push(piece.slice(0, k)); piece = piece.slice(k); if (out.length >= max) break; }
        cur = piece;
        if (out.length >= max) { rest = cur + words.slice(wi + 1).join(""); break; }
      }
      if (out.length < max) { if (cur.trim()) out.push(cur.trim()); }
      else if (cur.trim() || rest.trim()) rest = rest || cur;
      if (out.length > max) out.length = max;
      if (rest.trim() || (out.length === max && out.join(" ").length < src.replace(/\s+/g, " ").length)) {
        let t = out[max - 1]; while (x.measureText(t + "…").width > maxW && t.length > 1) t = t.slice(0, -1); out[max - 1] = t + "…";
      }
      return out;
    }
    // 최근 글 3개는 꼭 보이게: 먼저 모두 한 줄, 남는 줄(spare)은 최근 글부터 두 줄로
    function pickLines(x, list, maxW, spare) {
      const last = (list || []).slice(-3);
      const out = last.map((l) => ({ l, body: wrapText(x, l.body, maxW, 1) }));
      for (let i = out.length - 1; i >= 0 && spare > 0; i--) {
        const two = wrapText(x, out[i].l.body, maxW, 2);
        if (two.length > 1) { out[i].body = two; spare--; }
      }
      return out;
    }
    function drawNotes(lines) {
      const x = noteCanvas.getContext("2d");
      x.fillStyle = "#f6f2e6"; x.fillRect(0, 0, 768, 414);
      x.fillStyle = "#1f8a5c"; x.fillRect(0, 0, 768, 64);
      x.fillStyle = "#fff"; x.font = "700 32px 'Noto Sans KR', sans-serif"; x.textBaseline = "middle"; x.fillText("역 노트", 28, 33);
      x.font = "500 22px 'Noto Serif KR', serif"; x.textAlign = "right"; x.fillText("汐見浜駅", 740, 34); x.textAlign = "left";
      const ROW = 62, TOP = 72;     // 줄 공책 한 줄 높이 (큰 글씨)
      x.strokeStyle = "rgba(90,120,160,.28)"; x.lineWidth = 2;
      for (let yy = TOP + ROW; yy < 414; yy += ROW) { x.beginPath(); x.moveTo(24, yy); x.lineTo(744, yy); x.stroke(); }
      x.strokeStyle = "rgba(200,80,80,.35)"; x.beginPath(); x.moveTo(170, 70); x.lineTo(170, 414); x.stroke();
      if (!lines || !lines.length) { x.fillStyle = "#8a8276"; x.font = "400 32px 'Noto Sans KR', sans-serif"; x.fillText("기차를 기다리며 한 줄 남겨 보세요", 190, TOP + ROW / 2); }
      else {
        // 최근 글 3개 (아래가 최근). 남는 줄은 최근 글부터 두 줄로
        const rows = Math.floor((414 - TOP) / ROW);
        x.font = "500 38px 'Noto Sans KR', sans-serif";
        const picked = pickLines(x, lines, 550, rows - Math.min(3, lines.length)).map((it) => [it.l, it.body]);
        const used = picked.reduce((t, [, b]) => t + b.length, 0);
        let r = rows - used;
        for (const [l, body] of picked) {
          const y = TOP + r * ROW + ROW / 2;
          x.fillStyle = "#2c6852"; x.font = "600 22px 'Noto Sans KR', sans-serif";
          let n = l.nick; if (x.measureText(n).width > 140) { while (x.measureText(n + "…").width > 140 && n.length > 1) n = n.slice(0, -1); n += "…"; }
          x.fillText(n, 24, y);
          x.fillStyle = "#2a2622"; x.font = "500 38px 'Noto Sans KR', sans-serif";
          body.forEach((t, k) => x.fillText(t, 188, y + k * ROW));
          r += body.length;
        }
      }
      if (noteTex) noteTex.needsUpdate = true;
    }

    // ---------------------------------------------------------------- 큰 삼나무와 소나무, 전봇대와 전선, 표지판, 거울
    [[-20, 2, 1.35], [-25, -1, 1.15], [-21, 9, 1.1], [26, 16, 1.0]].forEach(([x, z, sc]) => trees.cedar(x, z, sc));
    for (let i = 0; i < 12; i++) { const x = rand(-60, 60); if (Math.abs(x) < 14) continue; const z = rand(-26, -10); trees.pine(x, z, rand(1.0, 1.5), { y: -0.2 - (-z - 3) * 0.12 }); }
    for (let i = 0; i < 8; i++) trees.pine(rand(-40, 40), rand(20, 34), rand(1.1, 1.7));
    // 역 앞 마을 집들
    [[22, 9, 0.3, true], [27, 3, -0.2, false], [-30, 14, 0.5, true], [18, 20, 0.1, true]].forEach(([x, z, r, two], i) => jpHouse(x, 0, z, r + Math.PI, 0.9, two, i + 3));
    // 마당 가로등
    {
      cyl(0.07, 0.09, 4.2, 6, 0x9a9a9a, -6, 2.1, 6.2); box(0.9, 0.08, 0.08, 0x9a9a9a, -5.6, 4.15, 6.2);
      const lampHead = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.12, 0.25), new THREE.MeshBasicMaterial({ color: TIME === "day" ? 0xdcdcd4 : 0xfff2d0 })); lampHead.position.set(-5.2, 4.08, 6.2); scene.add(lampHead);
      if (TIME !== "day") { const pl = new THREE.PointLight(0xfff0d0, PAL.lamp * 2.2, 16, 1.4); pl.position.set(-5.2, 3.9, 6.2); scene.add(pl); }
    }
    // 전봇대와 전선
    const poles = [[-14, 5.2], [-1, 5.2], [12, 5.2], [26, 5.2]];
    poles.forEach(([x, z]) => { cyl(0.11, 0.15, 7.5, 6, 0x8a8680, x, 3.75, z); box(1.4, 0.08, 0.08, 0x6a6660, x, 7.0, z); });
    const wireM = new THREE.LineBasicMaterial({ color: 0x2a2a2a });
    for (const dy of [7.0, 6.6]) for (let i = 0; i < poles.length - 1; i++) {
      const [ax, az] = poles[i], [bx, bz] = poles[i + 1], pts = [];
      for (let k = 0; k <= 12; k++) { const t = k / 12; pts.push(new THREE.Vector3(ax + (bx - ax) * t + 0.5, dy - Math.sin(t * Math.PI) * 0.45, az + (bz - az) * t)); }
      scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), wireM));
    }
    // 거리 표지(초록 22), 엑스 표지, 반사 거울, 안내판
    {
      const km = textTexture("22", { w: 128, h: 192, fg: "#ffffff", bg: "#1f8a5c", radius: 6, font: "700 96px 'Noto Sans KR', sans-serif" });
      cyl(0.04, 0.04, 2.6, 6, 0x9a9a9a, 15.8, PLAT.h + 1.3, 2.2);
      const kp = new THREE.Mesh(new THREE.PlaneGeometry(0.5, 0.75), new THREE.MeshLambertMaterial({ map: km })); kp.position.set(15.8, PLAT.h + 2.4, 2.25); scene.add(kp);
      const xc = document.createElement("canvas"); xc.width = xc.height = 128; const x = xc.getContext("2d");
      x.translate(64, 64); x.rotate(Math.PI / 4); x.fillStyle = "#e8784a"; x.fillRect(-44, -44, 88, 88); x.fillStyle = "#fff"; x.fillRect(-38, -38, 76, 76);
      x.rotate(-Math.PI / 4); x.strokeStyle = "#111"; x.lineWidth = 12; x.beginPath(); x.moveTo(-22, -22); x.lineTo(22, 22); x.moveTo(22, -22); x.lineTo(-22, 22); x.stroke();
      const xt = new THREE.CanvasTexture(xc); xt.colorSpace = THREE.SRGBColorSpace;
      cyl(0.04, 0.04, 2.2, 6, 0x9a9a9a, 17.6, 1.1, 2.4);
      const xs = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 0.9), new THREE.MeshLambertMaterial({ map: xt, transparent: true })); xs.position.set(17.6, 2.1, 2.45); scene.add(xs);
      // 반사 거울(주황 테두리)
      cyl(0.06, 0.06, 4.2, 6, 0xb0b0b0, 9.2, 2.1, 5.6);
      const mf = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.55, 0.12, 20), mat(0xd86a3a)); mf.rotation.x = Math.PI / 2; mf.position.set(9.2, 4.3, 5.68); scene.add(mf);
      const mg = new THREE.Mesh(new THREE.CircleGeometry(0.46, 20), new THREE.MeshBasicMaterial({ color: TIME === "day" ? 0x6ea8d8 : 0x3a4268 })); mg.position.set(9.2, 4.3, 5.75); scene.add(mg);
      // 돌 받침 안내판 (남기는 글)
      box(0.3, 1.0, 0.3, 0xb4b0a8, -3.7, 0.5, 6.35); box(0.3, 1.0, 0.3, 0xb4b0a8, -1.5, 0.5, 6.35);
      const board = new THREE.Mesh(new THREE.BoxGeometry(2.7, 1.5, 0.08), mat(0x6a6e72)); board.position.set(-2.6, 1.45, 6.4); board.rotation.x = -0.3; scene.add(board);
      noteTex = new THREE.CanvasTexture(noteCanvas); noteTex.colorSpace = THREE.SRGBColorSpace; noteTex.anisotropy = 4; drawNotes([]);
      const bt = new THREE.Mesh(new THREE.PlaneGeometry(2.56, 1.38), new THREE.MeshBasicMaterial({ map: noteTex }));
      bt.position.set(-2.6, 1.46, 6.455); bt.rotation.x = -0.3; scene.add(bt);
      board.userData.notes = true; bt.userData.notes = true; pickSeats.push(board, bt);
    }

    // ---------------------------------------------------------------- 열차: JR 313계 모양 (스테인리스 은색 차체, 주황 띠, 검은 앞창, 두 칸)
    const train = new THREE.Group(); scene.add(train);
    {
      const L = 20, W = 2.95, H = 3.0, FLOOR = 0.95;          // 한 칸 길이·폭·높이, 차체 밑면 높이
      const lit = TIME !== "day";
      // 차체 단면: 아래는 곧고 지붕 어깨가 둥근 모양을 길이 방향으로 밀어낸다
      const sec = new THREE.Shape(), r = 0.45;
      sec.moveTo(-W / 2, 0); sec.lineTo(W / 2, 0); sec.lineTo(W / 2, H - r); sec.quadraticCurveTo(W / 2, H, W / 2 - r, H);
      sec.lineTo(-W / 2 + r, H); sec.quadraticCurveTo(-W / 2, H, -W / 2, H - r); sec.lineTo(-W / 2, 0);
      const bodyGeo = new THREE.ExtrudeGeometry(sec, { depth: L, bevelEnabled: false, curveSegments: 8 });
      bodyGeo.translate(0, 0, -L / 2); bodyGeo.rotateY(Math.PI / 2);
      const steel = new THREE.MeshPhongMaterial({ color: 0xc9cdd2, shininess: 90, specular: 0x9aa0a8 });
      // 옆면 그림 (창, 문 세 짝, 주황 띠, 스테인리스 결)
      function sideTex(carNo) {
        const c = document.createElement("canvas"); c.width = 2048; c.height = 300; const x = c.getContext("2d");
        const gr = x.createLinearGradient(0, 0, 0, 300); gr.addColorStop(0, "#d9dde1"); gr.addColorStop(0.5, "#c6cace"); gr.addColorStop(1, "#b4b8bd");
        x.fillStyle = gr; x.fillRect(0, 0, 2048, 300);
        for (let i = 0; i < 2048; i += 3) { x.fillStyle = `rgba(255,255,255,${Math.random() * 0.06})`; x.fillRect(i, 0, 1, 300); }
        for (let y of [40, 262]) { x.fillStyle = "rgba(120,126,132,.5)"; x.fillRect(0, y, 2048, 2); }
        const m = 2048 / L, doors = [3.6, 10, 16.4];
        // 창 (문 사이에 두 장씩)
        const winY = 88, winH = 86;
        const winCol = lit ? "#ffe4ad" : "#2b3137";
        const bays = [[0.6, 2.7], [4.5, 9.1], [10.9, 15.5], [17.3, 19.4]];
        bays.forEach(([a, b]) => {
          const n = b - a > 3 ? 2 : 1, gap = 0.18, w = (b - a - gap * (n - 1)) / n;
          for (let k = 0; k < n; k++) {
            const x0 = (a + k * (w + gap)) * m;
            x.fillStyle = "#6a7076"; x.fillRect(x0 - 3, winY - 3, w * m + 6, winH + 6);
            const wg = x.createLinearGradient(0, winY, 0, winY + winH); wg.addColorStop(0, lit ? "#ffeec8" : "#3c444c"); wg.addColorStop(1, winCol);
            x.fillStyle = wg; x.fillRect(x0, winY, w * m, winH);
            x.fillStyle = "rgba(255,255,255,.16)"; x.fillRect(x0 + 6, winY + 4, w * m * 0.35, 6);
          }
        });
        // 주황 띠 (창 아래)
        x.fillStyle = "#e3642b"; x.fillRect(0, 186, 2048, 26);
        x.fillStyle = "#f08a50"; x.fillRect(0, 186, 2048, 4);
        // 문
        doors.forEach((d) => {
          const x0 = (d - 0.65) * m, w = 1.3 * m;
          x.fillStyle = "#7d838a"; x.fillRect(x0 - 3, 46, w + 6, 254);
          x.fillStyle = "#cfd3d7"; x.fillRect(x0, 50, w / 2 - 2, 250); x.fillRect(x0 + w / 2 + 2, 50, w / 2 - 2, 250);
          x.fillStyle = winCol; x.fillRect(x0 + 10, 82, w / 2 - 22, 84); x.fillRect(x0 + w / 2 + 12, 82, w / 2 - 22, 84);
          x.fillStyle = "#e3642b"; x.fillRect(x0, 186, w, 26);
        });
        x.fillStyle = "#3a3f44"; x.font = "600 20px sans-serif"; x.fillText("クハ313-" + carNo, 30, 245);
        const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
      }
      // 앞면 그림 (검은 앞창, 가운데 통로문, 행선 표시, 주황 띠, 전조등)
      function rr(x, l, t, w, h, r) { x.beginPath(); x.moveTo(l + r, t); x.arcTo(l + w, t, l + w, t + h, r); x.arcTo(l + w, t + h, l, t + h, r); x.arcTo(l, t + h, l, t, r); x.arcTo(l, t, l + w, t, r); x.closePath(); }
      function frontTex() {
        const c = document.createElement("canvas"); c.width = 512; c.height = 520; const x = c.getContext("2d");
        x.fillStyle = "#d3d7db"; x.fillRect(0, 0, 512, 520);
        x.fillStyle = "#1b1f24"; rr(x, 26, 60, 460, 200, 26); x.fill();
        x.fillStyle = "rgba(120,150,180,.22)"; x.beginPath(); x.moveTo(40, 70); x.lineTo(200, 70); x.lineTo(120, 250); x.lineTo(40, 250); x.fill();
        x.fillStyle = "#c9cdd1"; x.fillRect(196, 48, 120, 330);                    // 통로문
        x.fillStyle = "#1b1f24"; x.fillRect(214, 90, 84, 150);
        x.fillStyle = "#2a2e33"; x.fillRect(206, 18, 100, 24); x.fillStyle = "#ffb43a"; x.font = "700 18px sans-serif"; x.textAlign = "center"; x.fillText("普通 八戸", 256, 37);
        x.fillStyle = "#2a2e33"; x.fillRect(60, 20, 110, 30); x.fillRect(342, 20, 110, 30);
        x.fillStyle = "#ffb43a"; x.fillText("普通", 115, 42); x.fillText("2両", 397, 42);
        x.fillStyle = "#e3642b"; x.fillRect(0, 300, 196, 40); x.fillRect(316, 300, 196, 40);
        x.fillStyle = "#e3642b"; x.fillRect(196, 300, 120, 40);
        for (const hx of [70, 442]) { x.fillStyle = "#3a3f44"; rr(x, hx - 44, 352, 88, 40, 10); x.fill(); x.fillStyle = lit ? "#fff6dc" : "#f2f0e8"; rr(x, hx - 36, 358, 72, 28, 8); x.fill(); }
        x.fillStyle = "#8d9399"; x.fillRect(0, 430, 512, 90);
        const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
      }
      const fTex = frontTex();
      for (let ci = 0; ci < 2; ci++) {
        const g = new THREE.Group(); g.position.x = ci * (L + 0.6); train.add(g);
        const body = new THREE.Mesh(bodyGeo, steel); body.position.y = FLOOR; g.add(body);
        const st = sideTex(ci === 0 ? 5001 : 5301), sm = new THREE.MeshPhongMaterial({ map: st, shininess: 70, specular: 0x777c82 });
        for (const sd of [-1, 1]) {
          const side = new THREE.Mesh(new THREE.PlaneGeometry(L, H - 0.45), sm);
          side.position.set(0, FLOOR + (H - 0.45) / 2, sd * (W / 2 + 0.006)); if (sd < 0) { side.rotation.y = Math.PI; } g.add(side);
        }
        // 지붕 위 냉방 장치, 바닥 밑 기기와 대차(바퀴)
        for (const ax of [-5.5, 5.5]) box(2.6, 0.32, 1.7, 0xb5b9be, ax, FLOOR + H + 0.12, 0, g);
        box(L - 5, 0.55, 2.3, 0x3a3d42, 0, FLOOR - 0.25, 0, g);
        for (const bx of [-7, 7]) {
          box(2.6, 0.45, 2.2, 0x2a2c30, bx, 0.45, 0, g);
          for (const wx of [-0.9, 0.9]) for (const sd of [-1, 1]) { const wh = cyl(0.42, 0.42, 0.12, 14, 0x1c1d20, bx + wx, 0.42, sd * 0.78, g); wh.rotation.x = Math.PI / 2; }
        }
        // 앞머리 (두 칸 모두 바깥쪽 끝이 운전석)
        const endX = ci === 0 ? -L / 2 : L / 2, dir = ci === 0 ? -1 : 1;
        const nose = new THREE.Mesh(new THREE.ExtrudeGeometry(sec, { depth: 0.35, bevelEnabled: true, bevelThickness: 0.14, bevelSize: 0.12, bevelSegments: 4, curveSegments: 8 }), steel);
        nose.rotation.y = dir < 0 ? -Math.PI / 2 : Math.PI / 2; nose.position.set(endX, FLOOR, 0); g.add(nose);
        const face = new THREE.Mesh(new THREE.PlaneGeometry(W - 0.1, H - 0.1), new THREE.MeshPhongMaterial({ map: fTex, shininess: 60 }));
        face.position.set(endX + dir * 0.5, FLOOR + H / 2 - 0.02, 0); face.rotation.y = dir < 0 ? -Math.PI / 2 : Math.PI / 2; g.add(face);
        box(0.3, 0.5, 2.4, 0x2a2c30, endX + dir * 0.45, FLOOR - 0.2, 0, g);        // 연결기·스커트
        if (lit) { const pl = new THREE.PointLight(0xfff0d0, 2.2, 14, 1.6); pl.position.set(endX + dir * 1.2, 1.4, 0); g.add(pl); }
      }
      box(0.6, 2.4, 2.2, 0x3a3d42, L / 2 + 0.3, FLOOR + 1.3, 0, train);            // 칸 사이 통로막
      train.position.set(400, 0.48, TRACK_Z);
    }
    // 모두가 같은 시간에 같은 열차를 보도록 시계에 맞춘 주기(3분)
    const CYCLE = 180, ARRIVE = 9, STOP = 14, LEAVE = 10;
    let lastPhase = -1;
    function trainX(c) {
      const stopX = -10;
      if (c < ARRIVE) { const k = c / ARRIVE; return stopX + 200 * Math.pow(1 - k, 2); }
      if (c < ARRIVE + STOP) return stopX;
      const k = (c - ARRIVE - STOP) / LEAVE; return k < 1 ? stopX - 200 * k * k : -400;
    }
    const clockSec = () => (Date.now() / 1000) % CYCLE;

    // ---------------------------------------------------------------- 걷기 (마당 ↔ 계단 ↔ 승강장)
    function region(x, z) {
      if (x > STAIR.x0 && x < STAIR.x1 && z >= PLAT.z1 - 0.2 && z < STAIR.z1) return "S";
      if (x > PLAT.x0 + 0.3 && x < PLAT.x1 - 0.3 && z > PLAT.z0 + 0.25 && z < PLAT.z1 - 0.15) return "P";
      if (x > LOT.x0 && x < LOT.x1 && z > LOT.z0 && z < LOT.z1) return "L";
      return null;
    }
    function heightAt(x, z) {
      const r = region(x, z);
      if (r === "P") return PLAT.h;
      if (r === "S") return Math.max(0, Math.min(PLAT.h, PLAT.h * (1 - (z - STAIR.z0) / (STAIR.z1 - STAIR.z0))));
      if (z < TRACK_Z - 2) return -0.2 - Math.max(0, -z - 3) * 0.12;
      return 0;
    }
    const clampP = (x, z) => [Math.max(PLAT.x0 + 0.4, Math.min(PLAT.x1 - 0.4, x)), Math.max(PLAT.z0 + 0.35, Math.min(PLAT.z1 - 0.25, z))];
    const clampL = (x, z) => [Math.max(LOT.x0 + 0.2, Math.min(LOT.x1 - 0.2, x)), Math.max(LOT.z0 + 0.2, Math.min(LOT.z1 - 0.2, z))];
    const SX = (STAIR.x0 + STAIR.x1) / 2;
    function route(fx, fz, tx, tz) {
      const a = region(fx, fz) || (fz < PLAT.z1 ? "P" : "L"), b = region(tx, tz) || (tz < PLAT.z1 ? "P" : "L");
      const T = b === "P" ? clampP(tx, tz) : b === "L" ? clampL(tx, tz) : [tx, tz];
      if (a === b || a === "S" || b === "S") {
        if (a === "S" && b !== "S") return b === "P" ? [[SX, PLAT.z1 - 0.4], T] : [[SX, STAIR.z1 + 0.3], T];
        if (b === "S" && a !== "S") return a === "P" ? [[SX, PLAT.z1 - 0.4], T] : [[SX, STAIR.z1 + 0.3], T];
        return [T];
      }
      return a === "L" ? [[SX, STAIR.z1 + 0.3], [SX, PLAT.z1 - 0.4], T] : [[SX, PLAT.z1 - 0.4], [SX, STAIR.z1 + 0.3], T];
    }
    const OK = { P: ["P", "S"], S: ["S", "P", "L"], L: ["L", "S"] };
    const seaSpot = () => [rand(-4, 4), PLAT.z0 + 0.6];

    return {
      seats: SEATS, seatNoun: "자리", heightAt,
      spawn: { x: 2, z: 8.5, yaw: Math.PI },
      cam: { pitch: 0.38, seatPitch: 0.2, focusPitch: 0.17 },
      fog: { near: 60, far: 260, fnear: 6, ffar: 40 },
      fireflies: false,
      picks: [...pickSeats, ...pickPlat, ...pickGround],
      indoor: () => false,
      planWalk(from, p) { return route(from.x, from.z, p.x, p.z); },
      planTo(from, x, z) { return route(from.x, from.z, x, z); },
      planSeat(from, id) { const s = SEATS[id]; return route(from.x, from.z, s.x, s.z - 0.65).concat([[s.x, s.z]]); },
      leaveSeat(s) { return [s.x, s.z - 0.65]; },
      step(x, z, nx, nz) { const a = region(x, z), b = region(nx, nz); if (!b || (a && !OK[a].includes(b))) return [x, z]; return [nx, nz]; },
      welcome: "작은 바닷가 역이에요. 승강장 의자에 앉아 바다를 보며 집중해 보세요. 기차는 3분마다 지나가요.",
      sitText: "자리에 앉았어요. 파도 소리를 들으며 시작해 볼까요?",
      focusText: (m) => `${m}분, 다음 기차가 몇 번 지나갈 때까지.`,
      spaceAction: "sea",
      actions: { free: ["sit", "sea", "wait", "breathe"], sitting: ["focus", "wait", "breathe", "stand"], focus: ["breathe", "stop"] },
      labels: { sea: "바다 보기", wait: "기차 언제?" },
      icons: {
        sea: '<svg viewBox="0 0 24 24"><path d="M3 15c2 1.5 4 1.5 6 0s4-1.5 6 0 4 1.5 6 0M3 19c2 1.5 4 1.5 6 0s4-1.5 6 0 4 1.5 6 0M7 10a5 5 0 0 1 10 0"/></svg>',
        wait: '<svg viewBox="0 0 24 24"><rect x="5" y="4" width="14" height="13" rx="3"/><path d="M5 11h14M8 21l2-4M16 21l-2-4"/><circle cx="9" cy="14" r=".5"/><circle cx="15" cy="14" r=".5"/></svg>',
      },
      custom: {
        sea(E) {
          if (E.state !== "free") { E.look(0, 9, 0.18); return E.whisper("멀리 수평선이 보여요."); }
          const [tx, tz] = seaSpot();
          E.walk(route(E.me.pos.x, E.me.pos.z, tx, tz), () => { E.face(tx, -40); E.look(0, 7, 0.16); E.whisper("선로 너머로 바다가 넓게 펼쳐져요."); });
        },
        wait(E) {
          const c = clockSec(); const left = c < ARRIVE + STOP ? 0 : CYCLE - c;
          if (left === 0) return E.whisper("지금 기차가 서 있어요.");
          const m = Math.floor(left / 60), s = Math.floor(left % 60);
          E.whisper(`다음 기차까지 ${m ? m + "분 " : ""}${s}초 남았어요.`);
        },
      },
      board(lines) { drawNotes(lines); },
      chat: { can: (seat, st) => st !== "focus", placeholder: "역 노트에 한 줄 (하루 5줄)", done: "역 노트에 적었어요.", hint: "아래 칸에 한 줄 적으면 역 노트에 붙어요." },
      sounds: {
        // 바닷가: 파도가 주인공(먼 파도 + 가까이 부서지는 파도), 바람은 넓게, 저녁 마을 소리는 작게, 갈매기는 아주 가끔
        loops: [{ f: "eki/waves", g: 0.9 }, { f: "eki/shore", g: 0.28 }, { f: "eki/wind", g: 0.28 }, { f: "eki/evening", g: 0.28 }],
        gusts: [{ f: "eki/gulls", max: 0.28, every: [30, 60], when: "day" }],
        sfx: { train: { f: "eki/train", g: 0.85 } },
        steps: { f: "common/steps", out: 0.32, in: 0.22 },
      },
      update(dt, t, E) {
        // 파도
        const pos = sea.geometry.attributes.position;
        for (let i = 0; i < pos.count; i++) { const bx = seaBase[i * 3], by = seaBase[i * 3 + 1]; pos.setZ(i, Math.sin(bx * 0.05 + by * 0.11 + t * 0.8) * 0.22 + Math.sin(bx * 0.13 - by * 0.07 + t * 1.3) * 0.12 + Math.sin(bx * 0.31 + by * 0.27 + t * 2.1) * 0.05); }
        pos.needsUpdate = true; seaG.computeVertexNormals();
        // 부서지는 파도: 9초마다 한 줄씩, 바다 쪽에서 밀려와 모래 위로 얇게 퍼진다
        foams.forEach((f, i) => {
          const k = ((t / 9) + f.ph) % 1, z = SHORE_Z - 12 + k * 12.4;
          f.lip.position.set(0, SEA_Y + 0.12 + Math.sin(Math.min(1, k * 1.4) * Math.PI) * 0.25, z - 1.4);
          f.lip.material.opacity = k < 0.75 ? Math.sin(Math.min(1, k / 0.75) * Math.PI) * 0.7 : 0;
          f.m.position.set(0, SEA_Y + 0.14 + (k > 0.85 ? (k - 0.85) * 0.8 : 0), z);
          f.m.scale.y = 0.7 + k * 1.2;
          f.m.material.opacity = k < 0.55 ? k / 0.55 * 0.4 : k < 0.85 ? 0.4 + (k - 0.55) * 1.6 : Math.max(0, 0.88 - (k - 0.85) * 6);
          f.m.material.map.offset.x += dt * 0.004 * (i % 2 ? 1 : -1);
        });
        clouds.forEach((c) => { c.position.x += c.userData.v * dt; if (c.position.x > 230) c.position.x = -230; });
        updateBeam(t);
        boat.position.x = -50 + Math.sin(t * 0.02) * 20;
        // 열차
        const c = clockSec();
        train.position.x = trainX(c);
        const phase = c < 2 ? 0 : 1;
        if (phase === 0 && lastPhase !== 0 && E.audioOn) E.sfx("train");
        if (phase === 0 && lastPhase === 1) E.whisper("멀리서 기차가 들어와요.", 3000);
        lastPhase = phase;
      },
    };
  },
};
