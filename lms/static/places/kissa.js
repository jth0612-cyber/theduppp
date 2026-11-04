// 소도시 명상 · 골목 찻집. 마쓰야마 성 아래 비 오는 좁은 골목:
// 검은 판자벽과 흰 회벽 집들, 골목을 따라 흐르는 돌 물길, 처마 끝 둥근 등, 골목 끝을 지나는 옛 노면전차.
// 찻집 안은 나무 쟁반과 나무 컵, 창가 자리, 바 자리, 보라색 방석이 놓인 다다미방.
export default {
  moon: false,
  palette(PAL, TIME) {
    Object.assign(PAL, {
      day:   { top: 0x7d8a96, horizon: 0xc6cbcd, fog: 0xa9b1b6, hemiSky: 0xf0ece4, hemiGround: 0x5a5048, hemi: 1.25, sun: 0xf2f0ea, sunI: 0.55, ground: 0x5f6164, lamp: 1.1 },
      dusk:  { top: 0x232c46, horizon: 0x66749a, fog: 0x46506c, hemiSky: 0x8e9cc6, hemiGround: 0x2c2a2c, hemi: 0.8, sun: 0xa8b4dc, sunI: 0.35, ground: 0x3c4048, lamp: 2.2 },
      night: { top: 0x0b0f1e, horizon: 0x262c44, fog: 0x1b2032, hemiSky: 0x6a76a6, hemiGround: 0x1e1c20, hemi: 0.62, sun: 0x8a98c8, sunI: 0.25, ground: 0x2c2e34, lamp: 2.8 },
    }[TIME]);
  },
  build(K) {
    const { THREE, scene, TIME, PAL, mat, box, cyl, roof, textTexture, rand, srand } = K;
    const dark = TIME !== "day";
    const warm = dark ? 0xffc477 : 0xf3dcb4;
    const CAFE = { x0: 3.2, x1: 13, z0: -10, z1: 4 };
    const DOOR = { z0: -0.5, z1: 0.9 };
    const ALLEY = { x0: -1.6, x1: 3.2, z0: -25, z1: 14 };
    const STREET = { z0: -29, z1: -25, x0: -18, x1: 18 };
    const TATAMI = { x0: 8.2, z1: -3.6, h: 0.35 };
    const pickGround = [];
    const wet = (c, sh = 60) => new THREE.MeshPhongMaterial({ color: c, shininess: sh, specular: dark ? 0x8a8070 : 0x9aa0a6, flatShading: true });

    // ---------------------------------------------------------------- 젖은 돌길, 물길
    {
      const ground = new THREE.Mesh(new THREE.PlaneGeometry(120, 120), wet(PAL.ground, 30)); ground.rotation.x = -Math.PI / 2; scene.add(ground);
      const alley = new THREE.Mesh(new THREE.PlaneGeometry(ALLEY.x1 - ALLEY.x0 + 0.2, ALLEY.z1 - ALLEY.z0), wet(dark ? 0x34363c : 0x6a6a6a, 80));
      alley.rotation.x = -Math.PI / 2; alley.position.set((ALLEY.x0 + ALLEY.x1) / 2, 0.01, (ALLEY.z0 + ALLEY.z1) / 2); scene.add(alley); pickGround.push(alley);
      // 돌 포장 줄눈
      for (let z = ALLEY.z0; z < ALLEY.z1; z += 1.1) box(ALLEY.x1 - ALLEY.x0, 0.012, 0.04, dark ? 0x23252a : 0x4a4a4c, (ALLEY.x0 + ALLEY.x1) / 2, 0.015, z);
      const street = new THREE.Mesh(new THREE.PlaneGeometry(STREET.x1 - STREET.x0, STREET.z1 - STREET.z0), wet(dark ? 0x2a2c32 : 0x55575a, 70));
      street.rotation.x = -Math.PI / 2; street.position.set(0, 0.012, (STREET.z0 + STREET.z1) / 2); scene.add(street); pickGround.push(street);
      // 물길 (골목 왼쪽)
      box(0.18, 0.25, ALLEY.z1 - ALLEY.z0, 0x55585c, -1.75, 0.06, (ALLEY.z0 + ALLEY.z1) / 2);
      box(0.18, 0.25, ALLEY.z1 - ALLEY.z0, 0x55585c, -2.75, 0.06, (ALLEY.z0 + ALLEY.z1) / 2);
      const water = new THREE.Mesh(new THREE.PlaneGeometry(0.82, ALLEY.z1 - ALLEY.z0), new THREE.MeshPhongMaterial({ color: dark ? 0x1a2430 : 0x3a4a50, shininess: 120, specular: 0xffffff }));
      water.rotation.x = -Math.PI / 2; water.position.set(-2.25, -0.04, (ALLEY.z0 + ALLEY.z1) / 2); scene.add(water);
    }

    // ---------------------------------------------------------------- 골목 집들 (검은 판자 + 흰 회벽, 따뜻한 격자창)
    const lanterns = [];
    function machiya(x, z, w, d, h, side) {
      const g = new THREE.Group(); g.position.set(x, 0, z); scene.add(g);
      box(d, h * 0.45, w, 0x4a3628, 0, h * 0.225, 0, g);
      box(d, h * 0.55, w, 0xeeeae0, 0, h * 0.725, 0, g);
      // 회벽 위 검은 기둥·보
      const face = side * (d / 2 + 0.01);
      for (let i = 0; i <= Math.floor(w / 1.6); i++) box(0.06, h * 0.55, 0.12, 0x2a2420, face, h * 0.725, -w / 2 + i * (w / Math.floor(w / 1.6)), g);
      box(0.06, 0.12, w, 0x2a2420, face, h * 0.72, 0, g);
      // 격자창
      const win = new THREE.Mesh(new THREE.PlaneGeometry(w * 0.5, h * 0.25), new THREE.MeshBasicMaterial({ color: dark ? warm : 0xd8d2c4 }));
      win.position.set(face + side * 0.02, h * 0.25, 0); win.rotation.y = side > 0 ? Math.PI / 2 : -Math.PI / 2; g.add(win);
      for (let i = 0; i < 7; i++) box(0.05, h * 0.27, 0.05, 0x2a2420, face + side * 0.04, h * 0.25, -w * 0.25 + (i / 6) * w * 0.5, g);
      // 기와 처마 (골목 쪽으로 나온다)
      const r = box(0.7, 0.06, w, 0x50545a, side * (d / 2 + 0.3), h * 0.47, 0, g); r.rotation.z = side * 0.3;
      roof(d + 1.2, w + 0.6, 1.6, 0.25, 0x34363a, 0, h + 0.7, 0, g);
      // 처마 끝 둥근 등
      const lan = new THREE.Mesh(new THREE.SphereGeometry(0.2, 12, 10), new THREE.MeshBasicMaterial({ color: warm }));
      lan.position.set(side * (d / 2 + 0.8), h * 0.42 - 0.35, rand(-w / 3, w / 3)); g.add(lan); lanterns.push(lan);
      return g;
    }
    // 왼쪽 줄 (물길 건너)
    [[-24, 5, 3.4], [-17.5, 6, 3.8], [-11, 5.5, 3.4], [-4.6, 5, 3.9], [1.6, 5.5, 3.3], [8, 5, 3.8], [14, 5, 3.4]].forEach(([z, w, h]) => machiya(-5, z, w, 4, h, 1));
    // 오른쪽 줄 (찻집 앞뒤)
    [[-22, 5.5, 4], [-15.5, 6, 3.6], [13.5, 4, 3.6]].forEach(([z, w, h]) => machiya(7.7, z, w, 9, h, -1));
    // 비가 와서 몇 개만 진짜 불빛
    if (dark) [[-2.9, 2.4, -6], [3.1, 2.4, 8], [-2.9, 2.4, -18]].forEach(([x, y, z]) => { const pl = new THREE.PointLight(0xffb867, PAL.lamp, 9, 1.6); pl.position.set(x, y, z); scene.add(pl); });

    // ---------------------------------------------------------------- 골목 끝: 성이 있는 언덕
    {
      const hill = new THREE.Mesh(new THREE.ConeGeometry(34, 26, 12), mat(dark ? 0x1c2620 : 0x4a5e4a)); hill.position.set(4, 4, -92); scene.add(hill);
      const wallC = dark ? 0xd8dce4 : 0xf2f0ea, roofC = dark ? 0x2a2e38 : 0x3e4450;
      const C = { x: 4, y: 17, z: -92 };
      box(9, 2.2, 7, 0x8a8478, C.x, C.y, C.z);
      [[7, 2.2, 5.6, 2.6], [5.4, 2, 4.2, 5.4], [3.6, 1.8, 3, 7.9]].forEach(([w, h, d, y]) => {
        box(w, h, d, wallC, C.x, C.y + y, C.z); roof(w + 1.6, d + 1.4, 1.0, 0.55, roofC, C.x, C.y + y + h / 2 + 0.4, C.z);
      });
      if (dark) { const pl = new THREE.PointLight(0xe8eeff, 6, 30, 1.2); pl.position.set(C.x, C.y + 6, C.z + 10); scene.add(pl); }
    }
    // 노면전차 선로 + 전차 (짙은 초록·크림)
    {
      for (const dz of [-0.6, 0.6]) box(STREET.x1 - STREET.x0 + 40, 0.04, 0.08, 0x8a8a8a, 0, 0.03, -27 + dz);
      box(80, 0.04, 0.04, 0x222222, 0, 4.6, -27);
    }
    const tram = new THREE.Group(); scene.add(tram);
    {
      box(7.5, 2.4, 2.3, 0x2e5a44, 0, 1.6, 0, tram); box(7.5, 0.8, 2.32, 0xe8dcb8, 0, 2.3, 0, tram);
      roof(7.8, 2.6, 0.5, 0.6, 0x3a2e28, 0, 3.05, 0, tram);
      for (let i = 0; i < 5; i++) for (const sd of [-1, 1]) {
        const w = new THREE.Mesh(new THREE.PlaneGeometry(1.0, 0.65), new THREE.MeshBasicMaterial({ color: dark ? 0xffd28a : 0x5a6a70 }));
        w.position.set(-2.8 + i * 1.4, 2.3, sd * 1.17); if (sd < 0) w.rotation.y = Math.PI; tram.add(w);
      }
      box(0.06, 1.4, 0.06, 0x222222, 1.5, 3.9, 0, tram);
      tram.position.set(-80, 0, -27);
    }
    const TRAM_CYCLE = 70, TRAM_RUN = 14;
    let tramWas = false;

    // ---------------------------------------------------------------- 찻집
    const SEATS = [], pickSeats = [], pickCafe = [];
    const cutaway = new THREE.Group(); scene.add(cutaway);     // 안에 들어가면 낮아지는 벽
    const cafeRoof = new THREE.Group(); scene.add(cafeRoof);
    {
      const cx = (CAFE.x0 + CAFE.x1) / 2, cz = (CAFE.z0 + CAFE.z1) / 2, W = CAFE.x1 - CAFE.x0, D = CAFE.z1 - CAFE.z0, H = 3.4;
      // 바닥: 짙은 숯빛 나무 (참고 사진의 복도 바닥)
      const floor = box(W, 0.1, D, 0x4a423b, cx, 0.05, cz); pickCafe.push(floor);
      for (let x = CAFE.x0 + 0.45; x < CAFE.x1; x += 0.45) { const l = box(0.015, 0.004, D, 0x3a332d, x, 0.102, cz); l.userData.noOcclude = true; }
      // 벽: 따뜻한 올리브빛 흙벽 (미세한 얼룩 질감) + 나무 기둥·인방
      const plaster = (() => {
        const c = document.createElement("canvas"); c.width = c.height = 256; const x = c.getContext("2d");
        x.fillStyle = "#a39a6e"; x.fillRect(0, 0, 256, 256);
        for (let i = 0; i < 2600; i++) { x.fillStyle = `rgba(${Math.random() < 0.5 ? "70,60,30" : "235,225,180"},${Math.random() * 0.07})`; x.fillRect(Math.random() * 256, Math.random() * 256, 1 + Math.random() * 3, 1 + Math.random() * 3); }
        const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(4, 2); return t;
      })();
      const wallM = new THREE.MeshLambertMaterial({ map: plaster });
      const wall = (w, h, d, x, y, z) => { const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), wallM); m.position.set(x, y, z); cutaway.add(m); return m; };
      wall(0.2, H, D, CAFE.x1, H / 2, cz); wall(W, H, 0.2, cx, H / 2, CAFE.z0); wall(W, H, 0.2, cx, H / 2, CAFE.z1);
      const woodL = 0xc89a64, woodD = 0x8a5e36;
      for (const z of [CAFE.z0 + 0.12, CAFE.z1 - 0.12]) for (let x = CAFE.x0 + 2.4; x < CAFE.x1; x += 2.4) box(0.14, H, 0.14, woodL, x, H / 2, z, cutaway);
      for (let z = CAFE.z0 + 2.3; z < CAFE.z1; z += 2.3) box(0.14, H, 0.14, woodL, CAFE.x1 - 0.12, H / 2, z, cutaway);
      box(W, 0.1, 0.06, woodL, cx, 2.15, CAFE.z0 + 0.13, cutaway); box(W, 0.1, 0.06, woodL, cx, 2.15, CAFE.z1 - 0.13, cutaway);   // 인방(가모이)
      box(0.06, 0.1, D, woodL, CAFE.x1 - 0.13, 2.15, cz, cutaway);
      box(W, 0.12, 0.05, woodD, cx, 0.06, CAFE.z0 + 0.13, cutaway); box(W, 0.12, 0.05, woodD, cx, 0.06, CAFE.z1 - 0.13, cutaway);  // 걸레받이
      // 미닫이 맹장지(후스마) 두 짝: 은회색 종이 + 동그란 손잡이 (앞 벽)
      const fusuma = new THREE.MeshLambertMaterial({ color: 0xa8acb0 });
      [9.2, 10.6].forEach((fx, i) => {
        const f = new THREE.Mesh(new THREE.BoxGeometry(1.36, 2.05, 0.04), fusuma); f.position.set(fx, 1.04, CAFE.z1 - 0.16); cutaway.add(f);
        box(1.4, 0.05, 0.05, woodL, fx, 2.08, CAFE.z1 - 0.18, cutaway); box(0.04, 2.05, 0.05, woodL, fx - 0.68, 1.04, CAFE.z1 - 0.18, cutaway);
        const knob = new THREE.Mesh(new THREE.CircleGeometry(0.04, 16), new THREE.MeshBasicMaterial({ color: 0x2a2420 })); knob.rotation.y = Math.PI; knob.position.set(fx + (i ? -0.5 : 0.5), 1.0, CAFE.z1 - 0.19); cutaway.add(knob);
      });
      // 작은 장지창(쇼지) 네 칸 (뒷벽), 뒤에서 빛이 비친다
      { const sx = 6.6, sy = 1.55, sz = CAFE.z0 + 0.12;
        const pane = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 0.9), new THREE.MeshBasicMaterial({ color: dark ? 0xf6e7c6 : 0xf3efe4 })); pane.position.set(sx, sy, sz + 0.02); cutaway.add(pane);
        box(0.98, 0.05, 0.05, woodL, sx, sy + 0.47, sz + 0.03, cutaway); box(0.98, 0.05, 0.05, woodL, sx, sy - 0.47, sz + 0.03, cutaway);
        box(0.05, 0.98, 0.05, woodL, sx - 0.47, sy, sz + 0.03, cutaway); box(0.05, 0.98, 0.05, woodL, sx + 0.47, sy, sz + 0.03, cutaway);
        box(0.025, 0.9, 0.03, woodL, sx, sy, sz + 0.04, cutaway); box(0.9, 0.025, 0.03, woodL, sx, sy, sz + 0.04, cutaway); }
      box(0.22, 0.3, D, 0x2a2420, CAFE.x0, 0.15, cz);
      // 앞면 유리와 검은 창살, 위쪽 대나무 발(스다레)
      const glass = new THREE.MeshPhongMaterial({ color: 0xbcd0d8, transparent: true, opacity: dark ? 0.12 : 0.2, shininess: 100, depthWrite: false });
      for (const [z0, z1] of [[CAFE.z0, DOOR.z0], [DOOR.z1, CAFE.z1]]) {
        const g = new THREE.Mesh(new THREE.PlaneGeometry(z1 - z0, H - 0.3), glass); g.rotation.y = Math.PI / 2; g.position.set(CAFE.x0, H / 2 + 0.15, (z0 + z1) / 2); scene.add(g);
        for (let z = z0; z <= z1 + 0.01; z += (z1 - z0) / Math.max(1, Math.round((z1 - z0) / 1.8))) box(0.1, H, 0.1, 0x2a2420, CAFE.x0, H / 2, z);
      }
      box(0.12, 0.12, D, 0x2a2420, CAFE.x0, H, cz);
      const sc = document.createElement("canvas"); sc.width = 64; sc.height = 256; const x = sc.getContext("2d");
      x.fillStyle = dark ? "#d8a560" : "#b89a6a"; x.fillRect(0, 0, 64, 256);
      x.fillStyle = dark ? "#6a4a28" : "#5a4630"; for (let y = 0; y < 256; y += 8) x.fillRect(0, y, 64, 3);
      const st = new THREE.CanvasTexture(sc); st.colorSpace = THREE.SRGBColorSpace; st.wrapS = st.wrapT = THREE.RepeatWrapping; st.repeat.set(D / 1.2, 1);
      const sudare = new THREE.Mesh(new THREE.PlaneGeometry(D, 0.9), new THREE.MeshBasicMaterial({ map: st, transparent: true, opacity: 0.92, side: THREE.DoubleSide }));
      sudare.rotation.y = Math.PI / 2; sudare.position.set(CAFE.x0 + 0.06, H - 0.5, cz); scene.add(sudare);
      // 노렌과 간판
      const noren = new THREE.Mesh(new THREE.PlaneGeometry(1.4, 0.8), new THREE.MeshLambertMaterial({ map: textTexture("喫茶", { w: 256, h: 150, fg: "#f2ebdc", bg: "#3b4a3a", radius: 0, font: "500 80px 'Noto Serif KR', serif" }), side: THREE.DoubleSide }));
      noren.rotation.y = -Math.PI / 2; noren.position.set(CAFE.x0 - 0.12, 2.35, (DOOR.z0 + DOOR.z1) / 2); scene.add(noren);
      const sign = new THREE.Mesh(new THREE.PlaneGeometry(0.5, 1.6), new THREE.MeshBasicMaterial({ map: textTexture("雨音", { w: 96, h: 320, fg: "#2a2420", bg: dark ? "#f6e6c4" : "#efe6d4", radius: 4, font: "600 64px 'Noto Serif KR', serif" }) }));
      sign.rotation.y = -Math.PI / 2; sign.position.set(CAFE.x0 - 0.45, 1.6, DOOR.z1 + 0.9); scene.add(sign);
      // 지붕
      roof(W + 1.6, D + 1.2, 1.4, 0.3, 0x34363a, cx, H + 0.7, cz, cafeRoof);
      box(1.4, 0.12, D + 0.4, 0x3a3c40, CAFE.x0 - 0.5, H - 0.1, cz, cafeRoof).rotation.z = -0.3;

      // 바 자리: 뒷벽을 따라 카운터, 높은 의자 4개 (카운터를 바라본다)
      box(0.8, 1.05, 5.2, 0xc8a47a, 11.6, 0.52, 0.8); box(1.0, 0.08, 5.4, 0x3a2a20, 11.6, 1.08, 0.8);
      for (let i = 0; i < 4; i++) {
        const z = -1.1 + i * 1.3, id = SEATS.length;
        cyl(0.05, 0.08, 0.7, 8, 0x3a2a20, 10.6, 0.35, z);
        const top = new THREE.Mesh(new THREE.CylinderGeometry(0.26, 0.26, 0.08, 16), mat(0x7a5a3e, { flatShading: false })); top.position.set(10.6, 0.74, z); top.userData.seat = id; scene.add(top); pickSeats.push(top);
        SEATS.push({ x: 10.6, z, yaw: Math.PI / 2, y: 0.62, lift: 0.1, kind: "bar" });
      }
      // 선반의 나무 컵들, 주전자
      box(0.3, 0.06, 4.6, 0x6a4a32, 12.75, 1.9, 0.8); box(0.3, 0.06, 4.6, 0x6a4a32, 12.75, 2.5, 0.8);
      for (let i = 0; i < 9; i++) cyl(0.08, 0.065, 0.16, 10, i % 3 ? 0xd4b48a : 0xf0ece2, 12.75, 2.01 + (i % 2) * 0.6, -1.1 + i * 0.5);
      const kettle = new THREE.Mesh(new THREE.SphereGeometry(0.22, 12, 10), mat(0x8a8c90)); kettle.position.set(11.6, 1.3, 2.6); kettle.scale.y = 0.8; scene.add(kettle);
      // ---------- 천장 (참고 사진): 연한 노송나무 살대 천장 + 가운데 빛나는 격자 조명 띠 + 세로살 큰 보 + 육각 나무 등 ----------
      const CY = H - 0.02;
      const ceil = box(W, 0.05, D, 0xcaa77a, cx, CY + 0.03, cz);                          // 천장 판 (카메라가 이 아래에 머문다)
      for (let z = CAFE.z0 + 0.2; z < CAFE.z1; z += 0.3) { const b = box(W, 0.07, 0.07, 0xb98d5c, cx, CY - 0.04, z); b.userData.noOcclude = true; }   // 살대
      const latticeTex = (() => {                                                           // 장지 격자 조명 (빛이 새어 나오는 흰 종이 + 나무 살)
        const c = document.createElement("canvas"); c.width = 256; c.height = 64; const x = c.getContext("2d");
        x.fillStyle = "#fff6e0"; x.fillRect(0, 0, 256, 64); x.fillStyle = "#c99a62";
        for (let i = 0; i <= 256; i += 16) x.fillRect(i, 0, 3, 64); x.fillRect(0, 0, 256, 3); x.fillRect(0, 30, 256, 3); x.fillRect(0, 61, 256, 3);
        const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.wrapS = THREE.RepeatWrapping; t.repeat.set(D / 4, 1); return t;
      })();
      const lightBand = new THREE.Mesh(new THREE.PlaneGeometry(D - 1.2, 1.1), new THREE.MeshBasicMaterial({ map: latticeTex }));
      lightBand.rotation.x = Math.PI / 2; lightBand.rotation.z = Math.PI / 2; lightBand.position.set(6.2, CY - 0.085, cz); scene.add(lightBand);
      box(0.08, 0.14, D - 1.1, woodL, 6.2 - 0.6, CY - 0.1, cz); box(0.08, 0.14, D - 1.1, woodL, 6.2 + 0.6, CY - 0.1, cz);
      const louverTex = (() => {                                                            // 큰 보 옆면의 가는 세로살
        const c = document.createElement("canvas"); c.width = 128; c.height = 64; const x = c.getContext("2d");
        x.fillStyle = "#d4ac78"; x.fillRect(0, 0, 128, 64); x.fillStyle = "#a87a48"; for (let i = 0; i < 128; i += 4) x.fillRect(i, 0, 1.5, 64);
        const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.wrapS = THREE.RepeatWrapping; t.repeat.set(D / 1.2, 1); return t;
      })();
      const beam = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.62, D), [new THREE.MeshLambertMaterial({ map: louverTex }), new THREE.MeshLambertMaterial({ map: louverTex }),
        new THREE.MeshLambertMaterial({ color: 0xcaa77a }), new THREE.MeshLambertMaterial({ color: 0xb08050 }), new THREE.MeshLambertMaterial({ color: 0xcaa77a }), new THREE.MeshLambertMaterial({ color: 0xcaa77a })]);
      beam.position.set(TATAMI.x0, CY - 0.31, cz); cutaway.add(beam);
      const glowStrip = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.05, D - 0.4), new THREE.MeshBasicMaterial({ color: 0xffd896 }));       // 창 위 간접 조명
      glowStrip.position.set(CAFE.x0 + 0.22, CY - 0.14, cz); scene.add(glowStrip);
      // 육각 나무 등: 나뭇결이 비치는 육각 기둥 + 빛나는 육각 밑면
      const hexWood = new THREE.MeshLambertMaterial({ color: 0xe7c48e, emissive: 0x6a4214, emissiveIntensity: dark ? 0.9 : 0.5 });
      const hexGlow = new THREE.MeshBasicMaterial({ color: 0xfff4d8 });
      [[8.6, -1.0], [8.6, 2.2], [10.5, -5.4], [10.5, -8.0], [4.6, -3.2], [4.6, -6.4], [4.6, 2.2]].forEach(([px, pz], i) => {
        const hex = new THREE.Mesh(new THREE.CylinderGeometry(0.13, 0.13, 0.34, 6), hexWood); hex.position.set(px, CY - 0.25, pz); scene.add(hex);
        const bot = new THREE.Mesh(new THREE.CircleGeometry(0.13, 6), hexGlow); bot.rotation.x = Math.PI / 2; bot.position.set(px, CY - 0.425, pz); scene.add(bot);
        const ring = new THREE.Mesh(new THREE.CylinderGeometry(0.19, 0.19, 0.02, 6), mat(0x2a2420)); ring.position.set(px, CY - 0.07, pz); scene.add(ring);
        if (i < 4) { const pl = new THREE.PointLight(0xffcf8e, dark ? 2.4 : 1.3, 8, 1.5); pl.position.set(px, CY - 0.6, pz); scene.add(pl); }
      });

      // 창가 자리: 유리 앞 긴 나무판 + 쟁반과 나무 컵, 등받이 살 의자 (밖을 본다)
      box(0.6, 0.08, 5.6, 0x9a6a42, 3.75, 0.95, -4.8);
      for (const z of [-2.6, -7.0]) box(0.08, 0.9, 0.08, 0x5a3e2a, 3.75, 0.46, z);
      for (let i = 0; i < 4; i++) {
        const z = -2.6 - i * 1.45, id = SEATS.length;
        const tray = new THREE.Mesh(new THREE.CylinderGeometry(0.24, 0.24, 0.03, 20), mat(0xd8b088, { flatShading: false })); tray.scale.z = 0.7; tray.position.set(3.78, 1.0, z); scene.add(tray);
        cyl(0.06, 0.05, 0.1, 12, 0xc89a6a, 3.82, 1.07, z + 0.06);
        const seat = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.06, 0.5), mat(0x4a3022)); seat.position.set(4.7, 0.55, z); seat.userData.seat = id; scene.add(seat); pickSeats.push(seat);
        for (const dz of [-0.2, 0.2]) for (const dx of [-0.2, 0.2]) box(0.04, 0.55, 0.04, 0x3a2418, 4.7 + dx, 0.27, z + dz);
        for (let k = 0; k < 6; k++) box(0.03, 0.7, 0.03, 0x3a2418, 4.97, 0.92, z - 0.2 + k * 0.08);
        box(0.05, 0.08, 0.5, 0x3a2418, 4.97, 1.28, z);
        SEATS.push({ x: 4.7, z, yaw: -Math.PI / 2, y: 0.5, lift: 0.1, kind: "window" });
      }

      // 다다미방: 짙은 칠기 낮은 상 + 보라색 방석과 나무 좌식 의자
      const tx0 = TATAMI.x0, tx1 = CAFE.x1 - 0.1, tz0 = CAFE.z0 + 0.1, tz1 = TATAMI.z1;
      const tat = box(tx1 - tx0, TATAMI.h, tz1 - tz0, 0xd9cc9a, (tx0 + tx1) / 2, TATAMI.h / 2, (tz0 + tz1) / 2); pickCafe.push(tat);
      for (let z = tz0 + 1.8; z < tz1; z += 1.8) box(tx1 - tx0, 0.01, 0.05, 0x2a2420, (tx0 + tx1) / 2, TATAMI.h + 0.005, z);
      box(0.05, 0.01, tz1 - tz0, 0x2a2420, (tx0 + tx1) / 2, TATAMI.h + 0.005, (tz0 + tz1) / 2);
      box(0.12, TATAMI.h + 0.02, tz1 - tz0, 0x6a4a32, tx0, TATAMI.h / 2, (tz0 + tz1) / 2);
      const T = { x: 10.6, z: -6.7 };
      const table = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.08, 4.2), new THREE.MeshPhongMaterial({ color: 0x2a1c16, shininess: 90, specular: 0x6a5040 }));
      table.position.set(T.x, TATAMI.h + 0.42, T.z); scene.add(table);
      box(1.1, 0.38, 3.6, 0x1c1410, T.x, TATAMI.h + 0.19, T.z);
      [-1.3, 0, 1.3].forEach((dz) => [[-1, Math.PI / 2], [1, -Math.PI / 2]].forEach(([sd, yaw]) => {
        const x = T.x + sd * 1.15, z = T.z + dz, id = SEATS.length;
        const cush = new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.14, 0.62), mat(0x4a2a6a, { flatShading: false })); cush.position.set(x, TATAMI.h + 0.08, z); cush.userData.seat = id; scene.add(cush); pickSeats.push(cush);
        const back = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.55, 0.5), mat(0xe2c8a0)); back.position.set(x + sd * 0.34, TATAMI.h + 0.35, z); back.rotation.z = sd * 0.25; scene.add(back);
        SEATS.push({ x, z, yaw, y: TATAMI.h + 0.02, lift: 0.12, kind: "tatami" });
      }));
      // 주황 산 그림 (뒷벽) → 남기는 글(냅킨 메모)
      const pc = document.createElement("canvas"); pc.width = 384; pc.height = 256; const p = pc.getContext("2d");
      p.fillStyle = "#f1ece2"; p.fillRect(0, 0, 384, 256);
      [["#e8a070", 170], ["#e07a4a", 195], ["#c85a3a", 220]].forEach(([c, base], i) => { p.fillStyle = c; p.beginPath(); p.moveTo(0, 256); for (let xx = 0; xx <= 384; xx += 16) p.lineTo(xx, base - Math.sin(xx / 50 + i) * 30 - (xx > 180 && xx < 260 ? 30 : 0)); p.lineTo(384, 256); p.fill(); });
      p.fillStyle = "#3a2e28"; p.font = "500 22px 'Noto Serif KR', serif"; ["오늘의", "한 줄을", "남겨요"].forEach((t, i) => p.fillText(t, 290, 50 + i * 30));
      const pt = new THREE.CanvasTexture(pc); pt.colorSpace = THREE.SRGBColorSpace;
      const painting = new THREE.Mesh(new THREE.PlaneGeometry(2.2, 1.45), new THREE.MeshLambertMaterial({ map: pt }));
      painting.rotation.y = -Math.PI / 2; painting.position.set(CAFE.x1 - 0.12, 2.0, -6.7); cutaway.add(painting);
      painting.userData.notes = true; pickCafe.push(painting);
      // 귤 상자 (문 옆)
      for (let i = 0; i < 3; i++) {
        box(0.7, 0.4, 0.5, 0xb88a52, CAFE.x0 - 0.6, 0.2 + i * 0.42, DOOR.z1 + 1.8 + (i === 2 ? 0.05 : 0));
        if (i === 2) for (let k = 0; k < 6; k++) { const o = new THREE.Mesh(new THREE.SphereGeometry(0.1, 8, 6), mat(0xf08a1c)); o.position.set(CAFE.x0 - 0.8 + (k % 3) * 0.2, 1.1, DOOR.z1 + 1.7 + Math.floor(k / 3) * 0.2); scene.add(o); }
      }
      // 찻집 앞 화분
      [[CAFE.x0 + 0.6, 5.2], [CAFE.x0 + 1.6, 5.6], [CAFE.x0 + 0.9, 6.6]].forEach(([x, z], i) => { cyl(0.28, 0.22, 0.5, 10, 0x6a5a4a, x, 0.25, z); const b = new THREE.Mesh(new THREE.IcosahedronGeometry(0.45 + i * 0.1, 0), mat(dark ? 0x2a3a2c : 0x4e6e44)); b.position.set(x, 0.85 + i * 0.1, z); scene.add(b); });
      // 자전거 (왼쪽 벽 아래)
      const bike = new THREE.Group(); bike.position.set(-3.0 + 0.1, 0, 5); bike.rotation.y = Math.PI / 2; scene.add(bike);
      for (const dx of [-0.55, 0.55]) { const w = new THREE.Mesh(new THREE.TorusGeometry(0.33, 0.03, 6, 20), mat(0x222222)); w.position.set(dx, 0.34, 0); bike.add(w); }
      const fr = box(1.1, 0.05, 0.05, 0x6a8aa0, 0, 0.6, 0, bike); fr.rotation.z = 0.1;
      box(0.05, 0.45, 0.05, 0x6a8aa0, -0.15, 0.55, 0, bike); box(0.25, 0.05, 0.1, 0x222222, -0.15, 0.8, 0, bike); box(0.05, 0.05, 0.5, 0x444444, 0.5, 0.9, 0, bike);
    }

    // 나무 컵 (커피 한 모금) + 김

    // ---------------------------------------------------------------- 비
    const rain = (() => {
      const n = 900, p = new Float32Array(n * 6), v = [];
      const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(p, 3));
      const ls = new THREE.LineSegments(g, new THREE.LineBasicMaterial({ color: dark ? 0x9aa8c8 : 0xd8e0e8, transparent: true, opacity: dark ? 0.45 : 0.5 }));
      for (let i = 0; i < n; i++) { v.push(rand(14, 20)); reset(p, i, rand(0, 14)); }
      ls.userData.v = v; scene.add(ls); return ls;
      function reset(p, i, y) {
        let x, z; do { x = rand(-12, 16); z = rand(-30, 16); } while (x > CAFE.x0 - 0.4 && x < CAFE.x1 + 0.4 && z > CAFE.z0 - 0.4 && z < CAFE.z1 + 0.4);
        p.set([x, y, z, x + 0.02, y + 0.45, z], i * 6);
      }
    })();
    const ripples = [];
    for (let i = 0; i < 14; i++) {
      const r = new THREE.Mesh(new THREE.RingGeometry(0.06, 0.09, 16), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0, depthWrite: false }));
      r.rotation.x = -Math.PI / 2; r.userData.t = Math.random(); r.scale.setScalar(0.6); scene.add(r); ripples.push(r);
    }

    // ---------------------------------------------------------------- 걷기
    const inCafe = (x, z) => x > CAFE.x0 + 0.15 && x < CAFE.x1 - 0.3 && z > CAFE.z0 + 0.3 && z < CAFE.z1 - 0.3;
    const inAlley = (x, z) => (x > ALLEY.x0 && x < CAFE.x0 + 0.15 && z > ALLEY.z0 - 0.1 && z < ALLEY.z1) || (z > STREET.z0 + 0.3 && z <= ALLEY.z0 && x > STREET.x0 && x < STREET.x1);
    const region = (x, z) => inCafe(x, z) ? "C" : inAlley(x, z) ? "A" : null;
    const onTatami = (x, z) => inCafe(x, z) && x > TATAMI.x0 && z < TATAMI.z1;
    function heightAt(x, z) { return onTatami(x, z) ? TATAMI.h : inCafe(x, z) ? 0.1 : 0; }
    const DZ = (DOOR.z0 + DOOR.z1) / 2;
    const clampA = (x, z) => z <= ALLEY.z0 ? [Math.max(STREET.x0 + 0.5, Math.min(STREET.x1 - 0.5, x)), Math.max(STREET.z0 + 0.5, z)] : [Math.max(ALLEY.x0 + 0.2, Math.min(CAFE.x0 - 0.1, x)), Math.min(ALLEY.z1 - 0.3, z)];
    const clampC = (x, z) => [Math.max(CAFE.x0 + 0.4, Math.min(CAFE.x1 - 0.5, x)), Math.max(CAFE.z0 + 0.5, Math.min(CAFE.z1 - 0.5, z))];
    function route(fx, fz, tx, tz) {
      const a = region(fx, fz) || "A";
      const b = region(tx, tz) || (tx > CAFE.x0 && tz > CAFE.z0 && tz < CAFE.z1 ? "C" : "A");
      const T = b === "C" ? clampC(tx, tz) : clampA(tx, tz);
      const pre = [];
      if (a === "A" && fz <= ALLEY.z0 && !(b === "A" && T[1] <= ALLEY.z0)) pre.push([1, ALLEY.z0 + 0.5]);
      if (a === b) { if (b === "A" && T[1] <= ALLEY.z0 && fz > ALLEY.z0) pre.push([1, ALLEY.z0 + 0.3]); return pre.concat([T]); }
      if (b === "C") return pre.concat([[CAFE.x0 - 0.7, DZ], [CAFE.x0 + 0.9, DZ], T]);
      return [[CAFE.x0 + 0.9, DZ], [CAFE.x0 - 0.7, DZ], ...(T[1] <= ALLEY.z0 ? [[1, ALLEY.z0 + 0.3]] : []), T];
    }
    const windowSeat = (s) => s.kind === "window";
    let cut = 1;

    return {
      seats: SEATS, seatNoun: "자리", heightAt,
      spawn: { x: 0.8, z: 11, yaw: Math.PI },
      cam: { pitch: 0.44, seatPitch: 0.5, focusPitch: 0.42 },
      fog: { near: 14, far: 110, fnear: 4, ffar: 18 },
      fireflies: false,
      picks: [...pickSeats, ...pickCafe, ...pickGround],
      indoor: inCafe,
      planWalk(from, p) { return route(from.x, from.z, p.x, p.z); },
      planTo(from, x, z) { return route(from.x, from.z, x, z); },
      planSeat(from, id) {
        const s = SEATS[id], bx = s.x - Math.sin(s.yaw) * 0.7, bz = s.z - Math.cos(s.yaw) * 0.7;
        return route(from.x, from.z, bx, bz).concat([[s.x, s.z]]);
      },
      leaveSeat(s) { return [s.x - Math.sin(s.yaw) * 0.7, s.z - Math.cos(s.yaw) * 0.7]; },
      step(x, z, nx, nz) {
        const a = region(x, z), b = region(nx, nz);
        if (!b) return [x, z];
        if (a && a !== b && (nz < DOOR.z0 || nz > DOOR.z1)) return [x, z];
        return [nx, nz];
      },
      welcome: "비 오는 골목 찻집이에요. 창가 자리에 앉아 빗소리를 들으며 집중해 보세요.",
      sitText: (s) => s.kind === "window" ? "창가 자리예요. 유리창에 빗방울이 맺혀요." : s.kind === "tatami" ? "보라색 방석에 앉았어요. 상 위에 책을 펼쳐요." : "바 자리에 앉았어요. 주전자에서 김이 올라와요.",
      sitSound: "cushion",
      focusText: (m) => `${m}분, 비가 그칠 때까지는 여기서.`,
      spaceAction: "coffee",
      actions: { free: ["sit", "window", "coffee", "breathe"], sitting: ["focus", "coffee", "page", "stand"], focus: ["coffee", "page", "stop"] },
      labels: { window: "창가 자리", coffee: "커피 한 모금", page: "책장 넘기기" },
      icons: {
        window: '<svg viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="1"/><path d="M12 4v16M4 12h16M7 7l1 2M15 14l1 2"/></svg>',
        coffee: '<svg viewBox="0 0 24 24"><path d="M5 10h11v4a5 5 0 0 1-5 5h-1a5 5 0 0 1-5-5zM16 11h2a2 2 0 0 1 0 4h-2M9 3c0 2 2 2 2 4M13 3c0 2 2 2 2 4"/></svg>',
        page: '<svg viewBox="0 0 24 24"><path d="M4 5c3-1 6-1 8 1 2-2 5-2 8-1v14c-3-1-6-1-8 1-2-2-5-2-8-1zM12 6v14"/></svg>',
      },
      custom: {
        window(E) { if (E.state === "focus") return E.whisper("집중 중이에요. 먼저 '그만하기'를 누르세요."); const s = E.nearestSeat(windowSeat); s === null ? E.whisper("창가 자리가 다 찼어요. 바 자리는 어때요?") : E.sit(s); },
        coffee(E) { E.me.gesture("sip", 3.6); E.share("coffee"); E.sfx("sip"); E.whisper(E.state === "free" ? "따뜻한 커피를 후- 불어 한 모금." : "커피 한 모금. 다시 한 줄만 더."); },
        page(E) { E.sfx("page"); E.share("page"); E.whisper("사락— 다음 장으로."); },
      },
      remote: { coffee: (E, av) => av.gesture("sip", 3.6), page: (E) => E.sfx("pageFar") },
      sounds: {
        loops: [{ f: "kissa/rain", g: 0.62 }, { f: "kissa/rain2", g: 0.28 }, { f: "kissa/cafe", g: 0.28 }, { f: "kissa/clock", g: 0.14 }],
        gusts: [],
        sfx: { kettle: { f: "kissa/kettle", g: 0.55 }, sip: { f: "kissa/kettle", g: 0.22, rate: 1.3, lp: 1800 }, page: { f: "kissa/page", g: 0.8, jitter: true }, pageFar: { f: "kissa/page", g: 0.3, lp: 2500 }, tram: { f: "common/bowl", g: 0.32, rate: 2.6 } },
        steps: { f: "common/steps", out: 0.45, in: 0.2 },
      },
      update(dt, t, E) {
        const inside = inCafe(E.me.pos.x, E.me.pos.z);
        cafeRoof.visible = !inside;
        // 천장이 생겨서 벽을 낮추지 않는다 (카메라는 벽·천장 안쪽에 머문다)
        // 비
        const p = rain.geometry.attributes.position, v = rain.userData.v, a = p.array;
        for (let i = 0; i < v.length; i++) {
          const o = i * 6; const d = v[i] * dt; a[o + 1] -= d; a[o + 4] -= d;
          if (a[o + 1] < 0) {
            let x, z; do { x = rand(-12, 16); z = rand(-30, 16); } while (x > CAFE.x0 - 0.4 && x < CAFE.x1 + 0.4 && z > CAFE.z0 - 0.4 && z < CAFE.z1 + 0.4);
            a[o] = x; a[o + 1] = 14; a[o + 2] = z; a[o + 3] = x + 0.02; a[o + 4] = 14.45; a[o + 5] = z;
          }
        }
        p.needsUpdate = true;
        ripples.forEach((r) => {
          r.userData.t += dt * 1.4;
          if (r.userData.t > 1) { r.userData.t = 0; r.position.set(rand(ALLEY.x0 + 0.2, CAFE.x0 - 0.2), 0.03, rand(E.me.pos.z - 8, E.me.pos.z + 6)); }
          const k = r.userData.t; r.scale.setScalar(0.6 + k * 1.8); r.material.opacity = 0.2 * (1 - k);
        });
        lanterns.forEach((l, i) => { l.position.y += Math.sin(t * 1.3 + i) * 0.0008; });
        // 노면전차: 70초마다 골목 끝을 지나간다
        const c = (Date.now() / 1000) % TRAM_CYCLE, run = c < TRAM_RUN;
        tram.position.x = run ? -60 + (c / TRAM_RUN) * 120 : -80;
        if (run && !tramWas && E.audioOn) E.sfx("tram");
        tramWas = run;
      },
    };
  },
};
