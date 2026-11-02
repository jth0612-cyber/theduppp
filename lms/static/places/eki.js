// 같이 공부 · 바닷가 역. 하치노헤 쪽 바닷가의 작은 무인역 느낌:
// 자갈 마당, 노란 난간 계단, 높은 승강장 하나, 선로 한 줄, 큰 삼나무, 그리고 승강장 너머 태평양.
// 가끔 두 칸짜리 디젤 열차가 들어왔다가 떠난다.
export default {
  palette(PAL, TIME) {
    Object.assign(PAL, {
      // 맑은 여름 아침의 투명한 파랑
      day:   { top: 0x3f7fc4, horizon: 0xd8e8f2, fog: 0xcfe0ec, hemiSky: 0xfdf6e6, hemiGround: 0x5f7a4a, hemi: 1.05, sun: 0xfff2d8, sunI: 1.7, ground: 0x8d8a86, grass: 0x6f9a48, lamp: 0.4 },
      // 짙은 구름 아래 수평선만 주황색으로 타는 저녁
      dusk:  { top: 0x2a2e3a, horizon: 0xe8823a, fog: 0x4c4a54, hemiSky: 0xb0a8b8, hemiGround: 0x3a383e, hemi: 0.8, sun: 0xff9a5a, sunI: 0.75, ground: 0x6a6668, grass: 0x44523a, lamp: 1.6 },
      // 푸른 시간
      night: { top: 0x141f55, horizon: 0x6a5aa0, fog: 0x2a3168, hemiSky: 0x9aa0e8, hemiGround: 0x2a2a3a, hemi: 0.95, sun: 0xa8b4f0, sunI: 0.35, ground: 0x4a4a5a, grass: 0x2a3a34, lamp: 2.2 },
    }[TIME]);
  },
  build(K) {
    const { THREE, scene, TIME, PAL, mat, box, cyl, roof, textTexture, rand, srand } = K;
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
      const slope = new THREE.Mesh(new THREE.PlaneGeometry(160, 26), mat(PAL.grass)); slope.rotation.x = -Math.PI / 2 + 0.12; slope.position.set(0, -1.4, -15.5); scene.add(slope);
      const beach = new THREE.Mesh(new THREE.PlaneGeometry(160, 8), mat(TIME === "day" ? 0xd9ccb0 : 0x6a6260)); beach.rotation.x = -Math.PI / 2; beach.position.set(0, -2.95, -31); scene.add(beach);
      // 풀 덤불
      const bushC = TIME === "day" ? [0x5f8f3e, 0x7aa64a, 0x4d7a36] : [0x34442e, 0x3c4e34, 0x2a3828];
      for (let i = 0; i < 70; i++) {
        const x = rand(-40, 40), z = srand() > 0.5 ? rand(-14, -3) : rand(16, 30);
        const b = new THREE.Mesh(new THREE.IcosahedronGeometry(rand(0.4, 1.1), 0), mat(bushC[i % 3]));
        b.position.set(x, z < 0 ? -0.2 - (Math.abs(z) - 3) * 0.12 : 0.2, z); b.scale.y = 0.6; scene.add(b);
      }
      // 선로 옆 키 큰 풀
      for (let i = 0; i < 50; i++) {
        const b = new THREE.Mesh(new THREE.ConeGeometry(0.18, rand(0.6, 1.2), 4), mat(bushC[(i + 1) % 3]));
        b.position.set(rand(-40, 40), 0.3, TRACK_Z - rand(1.4, 2.6)); scene.add(b);
      }
    }

    // ---------------------------------------------------------------- 바다
    const sea = new THREE.Mesh(new THREE.PlaneGeometry(500, 220, 60, 24),
      new THREE.MeshPhongMaterial({ color: TIME === "day" ? 0x2f6fa8 : dusk ? 0x3a3a48 : 0x26306e, shininess: 70, specular: dusk ? 0xffa060 : 0x99bbdd, flatShading: true }));
    sea.rotation.x = -Math.PI / 2; sea.position.set(0, -3.1, -140); scene.add(sea);
    const seaBase = sea.geometry.attributes.position.array.slice();
    // 수평선의 빛 띠 (저녁엔 주황, 밤엔 분홍)
    if (TIME !== "day") {
      const band = new THREE.Mesh(new THREE.PlaneGeometry(500, 6), new THREE.MeshBasicMaterial({ color: dusk ? 0xffa050 : 0xd890c8, transparent: true, opacity: dusk ? 0.75 : 0.45, fog: false }));
      band.position.set(0, 3, -215); scene.add(band);
      const glow = new THREE.Mesh(new THREE.PlaneGeometry(260, 70), new THREE.MeshBasicMaterial({ color: dusk ? 0xff8a3a : 0xc890d0, transparent: true, opacity: 0.18, fog: false, depthWrite: false }));
      glow.rotation.x = -Math.PI / 2; glow.position.set(0, -3.0, -170); scene.add(glow);
      // 낮게 깔린 짙은 구름
      for (let i = 0; i < 14; i++) {
        const c = new THREE.Mesh(new THREE.SphereGeometry(rand(10, 22), 10, 6), new THREE.MeshBasicMaterial({ color: dusk ? 0x2c2e38 : 0x1e2658, fog: false }));
        c.scale.y = 0.22; c.position.set(rand(-180, 180), rand(16, 30), -205 + rand(-6, 6)); scene.add(c);
      }
    }
    // 오른쪽 곶(숲 실루엣)과 등대
    {
      const capeC = TIME === "day" ? 0x3d5e3a : 0x14181c;
      const cape = new THREE.Mesh(new THREE.SphereGeometry(30, 16, 10, 0, Math.PI * 2, 0, Math.PI / 2), mat(capeC)); cape.scale.set(1.6, 0.4, 0.8); cape.position.set(95, -3, -150); scene.add(cape);
      const cape2 = new THREE.Mesh(new THREE.SphereGeometry(20, 14, 8, 0, Math.PI * 2, 0, Math.PI / 2), mat(capeC)); cape2.scale.set(2.2, 0.35, 0.9); cape2.position.set(-110, -3, -120); scene.add(cape2);
      cyl(0.9, 1.2, 7, 10, 0xf2efe8, 62, 4, -142);
      cyl(1.0, 1.0, 1.2, 10, 0xb84a3a, 62, 8.1, -142);
    }
    const beam = new THREE.Mesh(new THREE.ConeGeometry(4, 60, 16, 1, true), new THREE.MeshBasicMaterial({ color: 0xfff2c0, transparent: true, opacity: 0.12, depthWrite: false, side: THREE.DoubleSide, fog: false }));
    beam.geometry.translate(0, -30, 0); beam.geometry.rotateZ(Math.PI / 2); beam.position.set(62, 8.2, -142); beam.visible = TIME !== "day"; scene.add(beam);
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
      box(0.62, 0.5, 0.06, chairC[i % 4], x, PLAT.h + 0.74, z + 0.28);
      SEATS.push({ x, z, yaw: Math.PI, y: PLAT.h + 0.28, lift: 0.12, kind: "bench" });
    });
    // 마당 끝 나무 벤치 둘 (바다 쪽)
    [[-12.5, 4.4], [-10.6, 4.4], [12, 4.4], [13.9, 4.4]].forEach(([x, z]) => {
      const id = SEATS.length;
      const c = box(1.5, 0.1, 0.5, 0x8a6a4a, x, 0.45, z); c.userData.seat = id; pickSeats.push(c);
      box(0.1, 0.45, 0.4, 0x5a4636, x - 0.6, 0.22, z); box(0.1, 0.45, 0.4, 0x5a4636, x + 0.6, 0.22, z);
      SEATS.push({ x, z, yaw: Math.PI, y: 0.28, lift: 0.12, kind: "lot" });
    });

    // ---------------------------------------------------------------- 큰 삼나무와 소나무, 전봇대와 전선, 표지판, 거울
    function bigCedar(x, z, s) {
      cyl(0.35 * s, 0.5 * s, 4 * s, 7, 0x4a3628, x, 2 * s, z);
      const g = TIME === "day" ? [0x2f5a32, 0x3a6a3a, 0x2a4e2e] : [0x18261c, 0x1e2e22, 0x15201a];
      for (let i = 0; i < 6; i++) {
        const c = new THREE.Mesh(new THREE.IcosahedronGeometry((3.2 - i * 0.35) * s, 0), mat(g[i % 3]));
        c.position.set(x + rand(-0.8, 0.8) * s, (3.2 + i * 1.6) * s, z + rand(-0.8, 0.8) * s); c.scale.y = 0.75; scene.add(c);
      }
    }
    bigCedar(-20, 2, 1.25); bigCedar(-25, -1, 1.05); bigCedar(-21, 9, 1.0); bigCedar(26, 16, 0.9);
    function pine(x, z, s) {
      const gy = z < -3 ? -0.2 - (-z - 3) * 0.12 : 0;
      const t = cyl(0.12 * s, 0.2 * s, 3.5 * s, 6, 0x5a4232, x, gy + 1.75 * s, z); t.rotation.z = rand(-0.15, 0.15);
      for (let i = 0; i < 3; i++) { const c = new THREE.Mesh(new THREE.SphereGeometry(1.2 * s, 8, 5), mat(TIME === "day" ? 0x3a5a36 : 0x18241c)); c.scale.y = 0.35; c.position.set(x + rand(-1, 1) * s, gy + (3.2 + i * 0.6) * s, z + rand(-1, 1) * s); scene.add(c); }
    }
    for (let i = 0; i < 12; i++) { const x = rand(-60, 60); if (Math.abs(x) < 14) continue; pine(x, rand(-26, -10), rand(1.1, 1.8)); }
    for (let i = 0; i < 8; i++) pine(rand(-40, 40), rand(20, 34), rand(1.2, 2));
    // 집들 (작은 함석지붕)
    const roofC = [0xc87a8e, 0x4a6e9a, 0x6a4a3a, 0x3e6a5a];
    [[22, 9, 0.3], [27, 3, -0.2], [-30, 14, 0.5], [18, 20, 0.1]].forEach(([x, z, r], i) => {
      const g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = r; scene.add(g);
      box(5, 3, 4, 0xece6da, 0, 1.5, 0, g); roof(5.8, 4.8, 1.2, 0.1, roofC[i], 0, 3.6, 0, g);
      const w = new THREE.Mesh(new THREE.PlaneGeometry(1.4, 0.9), new THREE.MeshBasicMaterial({ color: TIME === "day" ? 0x8aa2b0 : 0xffd394 })); w.position.set(0, 1.8, 2.02); g.add(w);
    });
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
      box(0.3, 0.9, 0.3, 0xb4b0a8, -3.6, 0.45, 6.4); box(0.3, 0.9, 0.3, 0xb4b0a8, -1.6, 0.45, 6.4);
      const board = new THREE.Mesh(new THREE.BoxGeometry(2.1, 0.9, 0.08), mat(0xe8ecee)); board.position.set(-2.6, 1.2, 6.4); board.rotation.x = -0.35; scene.add(board);
      const bt = new THREE.Mesh(new THREE.PlaneGeometry(1.9, 0.7), new THREE.MeshBasicMaterial({ map: textTexture("역 노트", { w: 512, h: 192, fg: "#1f6a4a", bg: "#f4f2ea", font: "600 60px 'Noto Sans KR', sans-serif" }) }));
      bt.position.set(-2.6, 1.22, 6.46); bt.rotation.x = -0.35; scene.add(bt);
      board.userData.notes = true; bt.userData.notes = true; pickSeats.push(board, bt);
    }

    // ---------------------------------------------------------------- 열차 (흰 몸체에 바다색 띠, 두 칸)
    const train = new THREE.Group(); scene.add(train);
    {
      const body = 0xf2f1ec, stripe = 0x2a8ab0, stripe2 = 0x7ac8d8, winC = TIME === "day" ? 0x3a4a58 : 0xffe8b0;
      for (let c = 0; c < 2; c++) {
        const g = new THREE.Group(); g.position.x = c * 20.6; train.add(g);
        box(20, 2.9, 2.8, body, 0, 2.15, 0, g);
        box(20.02, 0.32, 2.82, stripe, 0, 1.3, 0, g); box(20.02, 0.12, 2.82, stripe2, 0, 1.55, 0, g);
        box(20, 0.25, 2.6, 0xd8d6d0, 0, 3.7, 0, g);
        for (let i = 0; i < 7; i++) {
          const wm = new THREE.MeshBasicMaterial({ color: winC });
          for (const sd of [-1, 1]) { const w = new THREE.Mesh(new THREE.PlaneGeometry(1.6, 0.9), wm); w.position.set(-8 + i * 2.6, 2.5, sd * 1.41); if (sd < 0) w.rotation.y = Math.PI; g.add(w); }
        }
        box(1.2, 2.0, 2.84, 0xc8c6c0, -6, 2.0, 0, g); box(1.2, 2.0, 2.84, 0xc8c6c0, 6, 2.0, 0, g);
        box(16, 0.6, 2.2, 0x2a2a2a, 0, 0.75, 0, g);
      }
      for (const end of [-10.02, 30.62]) {
        const f = new THREE.Mesh(new THREE.PlaneGeometry(2.4, 1.1), new THREE.MeshBasicMaterial({ color: 0x2a3440 })); f.position.set(end, 2.6, 0); f.rotation.y = end < 0 ? -Math.PI / 2 : Math.PI / 2; train.add(f);
        if (TIME !== "day") for (const sd of [-0.8, 0.8]) { const h = new THREE.Mesh(new THREE.CircleGeometry(0.16, 10), new THREE.MeshBasicMaterial({ color: 0xfff6d8 })); h.position.set(end + (end < 0 ? -0.01 : 0.01), 1.6, sd); h.rotation.y = end < 0 ? -Math.PI / 2 : Math.PI / 2; train.add(h); }
      }
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
      sounds: {
        loops: [{ f: "eki/waves", g: 0.8 }, { f: "eki/wind", g: 0.35 }, { f: "common/crickets", g: 0.35, when: "night" }],
        gusts: [{ f: "eki/gulls", max: 0.4, every: [16, 32], when: "day" }],
        sfx: { train: { f: "eki/train", g: 0.85 } },
        steps: { f: "common/steps", out: 0.5, in: 0.3 },
      },
      update(dt, t, E) {
        // 파도
        const pos = sea.geometry.attributes.position;
        for (let i = 0; i < pos.count; i++) { const bx = seaBase[i * 3], by = seaBase[i * 3 + 1]; pos.setZ(i, Math.sin(bx * 0.08 + t * 0.9) * 0.25 + Math.cos(by * 0.12 + t * 0.6) * 0.2); }
        pos.needsUpdate = true;
        beam.rotation.y = t * 0.6;
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
