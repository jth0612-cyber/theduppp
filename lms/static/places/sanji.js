// 같이 공부 · 신사(神社, 학문의 신). 주홍 도리이 → 데미즈야 → 돌길과 석등이 있는 마당 → 계단 → 법당(靜學堂, 방석 24개), 종각과 에마 걸이.
export default {
  build(K) {
    const { THREE, scene, camera, TIME, PAL, mat, box, cyl, roof, textTexture, rand, srand, cedar, bamboo } = K;
    for (let i = 0; i < 46; i++) {
      const a = srand() * Math.PI * 2, r = 25 + srand() * 22;
      const x = Math.cos(a) * r, z = Math.sin(a) * r - 4;
      if (Math.abs(x) < 4 && z > 18) continue;
      cedar(x, z, 0.9 + srand() * 0.9);
    }
    [[-17, 15], [-19, 8], [17, 16], [-16, -6], [16, -8], [-20, 0], [20, 2]].forEach(([x, z]) => bamboo(x, z));

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

    // ---------------------------------------------------------------- 도리이 (주홍 기둥, 검은 가사기)
    {
      const TZ = 24.5, ver = 0xd2452c, blk = 0x1f1c1c;
      for (const x of [-2.7, 2.7]) { cyl(0.3, 0.34, 5.2, 12, ver, x, 2.6, TZ); cyl(0.42, 0.42, 0.35, 12, blk, x, 0.17, TZ); }
      box(7.0, 0.32, 0.36, ver, 0, 4.2, TZ);                                    // 누키
      box(0.42, 0.7, 0.3, ver, 0, 4.7, TZ);                                     // 가쿠즈카
      box(8.6, 0.42, 0.62, ver, 0, 5.05, TZ);                                   // 시마키
      const k2 = new THREE.Mesh(new THREE.BoxGeometry(9.6, 0.32, 0.72), mat(blk)); k2.position.set(0, 5.42, TZ); scene.add(k2);
      for (const sd of [-1, 1]) { const tip = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.3, 0.72), mat(blk)); tip.position.set(sd * 5.05, 5.55, TZ); tip.rotation.z = sd * 0.22; scene.add(tip); }
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
      const board = new THREE.Mesh(new THREE.PlaneGeometry(3.4, 0.85), new THREE.MeshBasicMaterial({ map: textTexture("學問宮") }));
      board.position.set(0, 5.6, -2.42); g.add(board);
      // 제단: 낮은 단, 둥근 창의 빛, 촛불
      box(6, 0.7, 1.4, 0x4b2e22, 0, 1.35, -12.8, g);
      const glow = new THREE.Mesh(new THREE.CircleGeometry(1.7, 40), new THREE.MeshBasicMaterial({ color: 0xe9eef0, fog: false }));   // 신경(둥근 거울)
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

    // ---------------------------------------------------------------- 본전 앞: 금줄(시메나와)·흰 종이(시데)·방울 줄·새전함·고마이누
    let suzuRope, suzuBell;
    {
      const straw = mat(0xc9a35a), strawDark = mat(0xa8823e);
      const curve = new THREE.CatmullRomCurve3([-6.4, -3.2, 0, 3.2, 6.4].map((x) => new THREE.Vector3(x, 6.0 - Math.cos((x / 6.4) * Math.PI / 2) * 0.55, -2.25)));
      const rope = new THREE.Mesh(new THREE.TubeGeometry(curve, 48, 0.22, 10), straw); scene.add(rope);
      const rope2 = new THREE.Mesh(new THREE.TubeGeometry(curve, 48, 0.13, 8), strawDark); rope2.position.set(0, 0.12, 0.12); scene.add(rope2);
      for (const x of [-3.4, 0, 3.4]) {                                           // 늘어진 짚 술
        const p = curve.getPoint((x + 6.4) / 12.8);
        const tas = new THREE.Mesh(new THREE.ConeGeometry(0.16, 0.9, 8), straw); tas.rotation.x = Math.PI; tas.position.set(x, p.y - 0.55, -2.25); scene.add(tas);
      }
      const shideShape = new THREE.Shape();                                         // 번개 모양 흰 종이
      [[0, 0], [0.22, 0], [0.22, -0.28], [0.42, -0.28], [0.42, -0.6], [0.62, -0.6], [0.62, -0.95], [0.4, -0.95], [0.4, -0.63], [0.2, -0.63], [0.2, -0.31], [0, -0.31]].forEach(([x, y], i) => (i ? shideShape.lineTo(x, y) : shideShape.moveTo(x, y)));
      const shideM = new THREE.MeshLambertMaterial({ color: 0xfbfaf4, side: THREE.DoubleSide });
      for (const x of [-5, -1.7, 1.7, 5]) {
        const p = curve.getPoint((x + 6.4) / 12.8);
        const sh = new THREE.Mesh(new THREE.ShapeGeometry(shideShape), shideM); sh.position.set(x - 0.3, p.y - 0.12, -2.0); scene.add(sh);
      }
      // 방울 줄: 처마에서 내려온 금빛 방울 + 빨강·하양·보라 꼰 줄
      suzuRope = new THREE.Group(); suzuRope.position.set(0, 5.35, -2.05); scene.add(suzuRope);
      suzuBell = new THREE.Mesh(new THREE.SphereGeometry(0.32, 16, 12), new THREE.MeshPhongMaterial({ color: 0xd9a93a, shininess: 90, specular: 0xfff0c0 }));
      suzuBell.position.y = -0.3; suzuRope.add(suzuBell);
      const slit = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.04, 0.05), mat(0x3a2a10)); slit.position.set(0, -0.42, 0.29); suzuRope.add(slit);
      [0xc8323a, 0xf4f0e8, 0x6a3a8a].forEach((c, i) => {
        const r = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 3.3, 6), mat(c));
        r.position.set((i - 1) * 0.07, -2.25, Math.sin(i * 2) * 0.03); r.rotation.z = (i - 1) * 0.02; suzuRope.add(r);
      });
      // 새전함 (나무 상자, 위에 살)
      const sb = new THREE.Group(); sb.position.set(0, HALL.floor, -2.9); scene.add(sb);
      box(1.3, 0.7, 0.75, 0x6b4630, 0, 0.35, 0, sb);
      for (let i = 0; i < 6; i++) box(0.06, 0.06, 0.75, 0x3a2418, -0.5 + i * 0.2, 0.72, 0, sb);
      const sbText = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 0.3), new THREE.MeshBasicMaterial({ map: textTexture("奉納", { w: 256, h: 96, fg: "#f2e6c8", bg: "#4a2e1e", font: "600 60px 'Noto Serif KR', serif" }) }));
      sbText.position.set(0, 0.38, 0.38); sb.add(sbText);
      // 고마이누 한 쌍 (계단 아래 양쪽, 돌 사자개)
      const stoneM = mat(0x9a958c), stoneD = mat(0x7c776e);
      for (const sd of [-1, 1]) {
        const k = new THREE.Group(); k.position.set(sd * 4.2, 0, 1.8); k.rotation.y = sd * -0.35; scene.add(k);
        box(1.0, 0.9, 1.1, 0x8a857c, 0, 0.45, 0, k);
        const body = new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.72, 0.85), stoneM); body.position.set(0, 1.3, -0.05); body.rotation.x = -0.15; k.add(body);
        const head = new THREE.Mesh(new THREE.DodecahedronGeometry(0.36, 0), stoneM); head.position.set(0, 1.85, 0.22); k.add(head);
        const mane = new THREE.Mesh(new THREE.IcosahedronGeometry(0.42, 0), stoneD); mane.position.set(0, 1.82, 0.05); mane.scale.set(1.1, 1, 0.7); k.add(mane);
        for (const ex of [-0.18, 0.18]) { const e = new THREE.Mesh(new THREE.SphereGeometry(0.06, 8, 6), mat(0x4a4640)); e.position.set(ex, 1.92, 0.5); k.add(e); }
        const tail = new THREE.Mesh(new THREE.ConeGeometry(0.16, 0.6, 6), stoneD); tail.position.set(0, 1.75, -0.48); tail.rotation.x = -0.6; k.add(tail);
        for (const lx of [-0.2, 0.2]) { const l = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.5, 0.16), stoneD); l.position.set(lx, 1.05, 0.38); k.add(l); }
      }
    }

    // ---------------------------------------------------------------- 데미즈야 (손 씻는 곳)
    const TEMIZU = { x: 6.2, z: 17.6 };
    let ladle;
    {
      const g = new THREE.Group(); g.position.set(TEMIZU.x, 0, TEMIZU.z); scene.add(g);
      for (const dx of [-1.5, 1.5]) for (const dz of [-1, 1]) cyl(0.11, 0.13, 2.9, 8, 0x7a5440, dx, 1.45, dz, g);
      roof(4.4, 3.2, 0.9, 0.3, 0x33383f, 0, 3.2, 0, g);
      box(2.2, 0.75, 1.1, 0x8f8a82, 0, 0.38, 0, g);
      const w = new THREE.Mesh(new THREE.PlaneGeometry(1.9, 0.8), new THREE.MeshPhongMaterial({ color: 0x8cbfc4, shininess: 120, specular: 0xffffff }));
      w.rotation.x = -Math.PI / 2; w.position.set(0, 0.74, 0); g.add(w);
      const pipe = cyl(0.06, 0.06, 0.9, 8, 0x8c9a52, -0.9, 1.05, 0, g); pipe.rotation.z = 1.2;
      box(2.2, 0.05, 0.05, 0x8c9a52, 0, 0.83, 0.42, g);                            // 국자 걸이 대나무
      for (let i = 0; i < 4; i++) { cyl(0.07, 0.06, 0.1, 10, 0xc9a77a, -0.75 + i * 0.5, 0.9, 0.42, g); const h = box(0.03, 0.02, 0.55, 0xc9a77a, -0.75 + i * 0.5, 0.86, 0.15, g); h.rotation.x = 0.15; }
      ladle = new THREE.Group(); ladle.visible = false; scene.add(ladle);
      cyl(0.08, 0.07, 0.12, 10, 0xc9a77a, 0, 0, 0, ladle); box(0.03, 0.03, 0.6, 0xc9a77a, 0, 0, -0.3, ladle);
      ladle.userData.popY = 0.75; ladle.userData.popScale = 1.2;
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

    // ---------------------------------------------------------------- 오미쿠지 (운세 뽑기): 육각 나무통, 하얀 운세 종이를 묶어 두는 줄
    const BELL = { x: 12.5, z: 9 };
    let kujiBox, slip;
    {
      box(3.6, 0.3, 2.4, 0x8c8579, BELL.x, 0.15, BELL.z);
      for (const dx of [-1.3, 1.3]) cyl(0.1, 0.12, 2.6, 8, 0xc8452c, BELL.x + dx, 1.45, BELL.z - 0.7);
      roof(3.4, 1.6, 0.6, 0.3, 0x33383f, BELL.x, 2.9, BELL.z - 0.7);
      box(2.2, 0.9, 0.8, 0x6b4630, BELL.x, 0.75, BELL.z - 0.5);
      kujiBox = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.2, 0.62, 6), mat(0x8a5a36)); kujiBox.position.set(BELL.x - 0.5, 1.5, BELL.z - 0.5); scene.add(kujiBox);
      const kt = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 0.42), new THREE.MeshBasicMaterial({ map: textTexture("おみくじ", { w: 256, h: 112, fg: "#f6efe0", bg: "#a8321e", font: "600 52px 'Noto Serif KR', serif" }) }));
      kt.position.set(BELL.x + 0.4, 1.5, BELL.z - 0.08); scene.add(kt);
      // 묶어 둔 운세 종이
      for (const y of [1.1, 1.6]) {
        box(3.0, 0.03, 0.03, 0x4a3a2a, BELL.x, y, BELL.z + 0.9);
        for (let i = 0; i < 16; i++) { const k = box(0.07, 0.12, 0.04, 0xfbf8f0, BELL.x - 1.4 + i * 0.185 + Math.random() * 0.04, y - 0.05, BELL.z + 0.9); k.rotation.z = (Math.random() - 0.5) * 0.6; }
      }
      for (const dx of [-1.55, 1.55]) box(0.08, 1.8, 0.08, 0x4a3a2a, BELL.x + dx, 0.9, BELL.z + 0.9);
      slip = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.42, 0.02), mat(0xfbf8f0)); slip.visible = false; slip.userData.popY = 0.95; slip.userData.popScale = 1.4; scene.add(slip);
    }
    const bellMesh = kujiBox;

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


    // ---------------------------------------------------------------- 벚나무와 흩날리는 꽃잎 (봄의 경내)
    const blossomC = TIME === "night" ? [0x6e5a78, 0x7a6684, 0x5e4c6a] : TIME === "dusk" ? [0xe8b0bc, 0xdc9cac, 0xf0c4cc] : [0xf6cdd6, 0xeeb6c4, 0xfbe0e6];
    const sakuraSpots = [[-9, 13, 1.25], [10.5, 16.5, 1.1], [-15, 7, 1.0], [17.5, 3, 1.15], [-13, -4, 1.0], [-6.5, 17.5, 0.9]];
    const canopies = [];
    sakuraSpots.forEach(([x, z, sc]) => {
      const trunk = cyl(0.16 * sc, 0.3 * sc, 2.6 * sc, 7, 0x3c2e2a, x, 1.3 * sc, z); trunk.rotation.z = (srand() - 0.5) * 0.2;
      for (let i = 0; i < 4; i++) { const br = cyl(0.06 * sc, 0.1 * sc, 1.8 * sc, 5, 0x3c2e2a, x, 2.7 * sc, z); br.rotation.z = (srand() - 0.5) * 1.6; br.rotation.y = srand() * 6; }
      const cg = new THREE.Group(); cg.userData.at = [x, z]; scene.add(cg); canopies.push(cg);
      for (let i = 0; i < 16; i++) {
        const a = srand() * Math.PI * 2, r = (0.5 + srand() * 2.1) * sc;
        const b = new THREE.Mesh(new THREE.IcosahedronGeometry((0.6 + srand() * 0.55) * sc, 1), mat(blossomC[i % 3]));
        b.position.set(x + Math.cos(a) * r, (2.9 + srand() * 1.5) * sc, z + Math.sin(a) * r); b.scale.y = 0.75; cg.add(b);
      }
    });
    const petalTex = (() => {
      const c = document.createElement("canvas"); c.width = c.height = 32; const x = c.getContext("2d");
      x.fillStyle = TIME === "night" ? "#b8a4c4" : "#f8d2dc"; x.beginPath(); x.ellipse(16, 16, 12, 7, 0.4, 0, Math.PI * 2); x.fill();
      const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
    })();
    const petals = (() => {
      const n = 160, p = new Float32Array(n * 3), seed = [];
      for (let i = 0; i < n; i++) { const [sx, sz] = sakuraSpots[i % sakuraSpots.length]; p.set([sx + rand(-3, 3), rand(0, 5), sz + rand(-3, 3)], i * 3); seed.push({ x: sx, z: sz, v: rand(0.25, 0.55), ph: rand(0, 10) }); }
      const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(p, 3));
      const pts = new THREE.Points(g, new THREE.PointsMaterial({ map: petalTex, size: 0.16, transparent: true, depthWrite: false, alphaTest: 0.2 }));
      pts.userData.seed = seed; scene.add(pts); return pts;
    })();

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
      if (d < 2.2) { x = BELL.x + (dx / (d || 1)) * 2.2; z = BELL.z + (dz / (d || 1)) * 2.2; }
      const tx = x - TEMIZU.x, tz = z - TEMIZU.z, td = Math.hypot(tx, tz);
      if (td < 1.7) { x = TEMIZU.x + (tx / (td || 1)) * 1.7; z = TEMIZU.z + (tz / (td || 1)) * 1.7; }
      return [x, z];
    }
    // 마당 ↔ 법당은 계단을 거쳐 간다
    function route(fx, fz, tx, tz, toHall) {
      const fromHall = inHall(fx, fz);
      const [cx, cz] = clampWalk(tx, tz, toHall);
      const pts = [];
      if (fromHall !== toHall) {
        let sx = Math.max(-2, Math.min(2, fromHall ? fx : cx));
        if (Math.abs(sx) < 1.1) sx = sx < 0 ? -1.5 : 1.5;                            // 가운데 새전함을 비켜 간다
        if (fromHall) { pts.push([sx, -3.0], [sx, 0.9]); } else { pts.push([sx, 0.9], [sx, -3.0]); }
      }
      pts.push([cx, cz]);
      return pts;
    }


    // 동작: 참배(두 번 절, 두 번 손뼉, 한 번 절) · 방울 · 손 씻기 · 오미쿠지
    let suzuSwing = 0, kujiShake = 0, busy = false;
    bellMesh.userData.action = "omikuji";
    suzuBell.userData.action = "suzu"; suzuRope.children.forEach((c) => (c.userData.action = "suzu"));
    emaRack.traverse((o) => { if (o.isMesh) o.userData.notes = true; });
    const wait = (ms) => new Promise((ok) => setTimeout(ok, ms));
    const FORTUNES = [
      "대길(大吉) · 오늘 푼 문제가 시험에 그대로 나올 것 같은 날이에요.",
      "대길(大吉) · 자료 해석에 강한 하루. 그래프 문제부터 풀어 보세요.",
      "길(吉) · 틀린 문제 하나가 큰 깨달음이 돼요. 오답 노트를 펼쳐 보세요.",
      "길(吉) · 모르는 건 질답 게시판에 물으면 길이 열려요.",
      "중길(中吉) · 한 단원만 끝까지. 작은 완주가 큰 힘이 돼요.",
      "소길(小吉) · 25분만 집중해도 오늘은 충분히 잘한 날이에요.",
      "말길(末吉) · 천천히 가도 멈추지만 않으면 돼요. 내일은 더 좋아요.",
    ];
    const restPose = (E) => (E.me.seat !== null ? "sit" : "stand");
    async function sanpai(E) {
      if (busy) return; busy = true;
      E.whisper("두 번, 깊이 절해요.", 3200);
      E.me.bow(); E.sync(true); await wait(1700); E.me.bow(); E.sync(true); await wait(1800);
      E.whisper("두 번 손뼉을 쳐요.", 2000);
      for (let i = 0; i < 2; i++) { E.me.pose = restPose(E); await wait(160); E.me.pose = "gassho"; E.sfx("clap"); await wait(380); }
      E.sync(true); await wait(500);
      E.whisper("마지막으로 한 번 절하며, 오늘의 목표를 마음속으로 말해요.", 3400);
      E.me.bow(); E.sync(true); await wait(1800);
      E.me.pose = restPose(E); E.sync(true); busy = false;
    }
    return {
      seats: SEATS, seatNoun: "방석", heightAt,
      spawn: { x: 0, z: 11.5, yaw: Math.PI },
      picks: [...pickSeats, bellMesh, suzuBell, ...suzuRope.children, ...emaRack.children, ...pickHall, ...pickGround],
      indoor: (x, z) => inHall(x, z),
      planWalk(from, p, obj) { return route(from.x, from.z, p.x, p.z, pickHall.includes(obj) || inHall(p.x, p.z)); },
      planTo(from, x, z) { return route(from.x, from.z, x, z, inHall(x, z)); },
      planSeat(from, id) { const s = SEATS[id]; return route(from.x, from.z, s.x, s.z + 0.9, true).concat([[s.x, s.z]]); },
      step(x, z, nx, nz) { const onSteps = Math.abs(nx) < 2.6 && nz > -3.2 && nz < 1.0; return onSteps ? [nx, nz] : clampWalk(nx, nz, inHall(x, z)); },
      welcome: "학문의 신을 모신 신사예요. 손을 씻고 참배한 뒤, 본전 방석에 앉아 집중해 보세요.",
      sitText: "방석에 앉았어요. 시간을 고르고 집중을 시작해 보세요.",
      spaceAction: "sanpai",
      actions: { free: ["sit", "sanpai", "suzu", "temizu", "omikuji"], sitting: ["focus", "breathe", "sanpai", "stand"], focus: ["breathe", "stop"] },
      labels: { sanpai: "참배", suzu: "방울", temizu: "손 씻기", omikuji: "오미쿠지" },
      icons: {
        sanpai: '<svg viewBox="0 0 24 24"><path d="M9 21v-6l-2-4 1-7 2 6M15 21v-6l2-4-1-7-2 6M5 6l-2-1M19 6l2-1M12 3v2"/></svg>',
        suzu: '<svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="4.5"/><path d="M8 8h8M12 12.5V22M10 22h4"/></svg>',
        temizu: '<svg viewBox="0 0 24 24"><path d="M4 12h9v2a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4zM13 13l7-6M17 3c1 2 2 3 2 4.5a2 2 0 0 1-4 0C15 6 16 5 17 3z"/></svg>',
        omikuji: '<svg viewBox="0 0 24 24"><path d="M8 3h8v18l-4-2-4 2zM10 8h4M10 11h4M10 14h2"/></svg>',
      },
      custom: {
        sanpai(E) { if (E.state === "focus") return E.whisper("집중이 끝나면 참배해 보세요."); sanpai(E); },
        suzu(E) {
          if (E.state === "focus") return E.whisper("집중이 끝나면 방울을 흔들어 보세요.");
          E.walk(route(E.me.pos.x, E.me.pos.z, 0, 1.2, false).concat([[0, -0.9]]), () => {
            E.face(0, -4); E.look(0, 6.5, 0.32); suzuSwing = 1; E.sfx("suzu"); E.whisper("딸랑딸랑— 방울 소리로 왔다고 알려요. 이어서 참배해 보세요.", 3800);
          });
        },
        temizu(E) {
          if (E.state === "focus") return E.whisper("집중 중이에요. 먼저 '그만하기'를 누르세요.");
          E.walk(route(E.me.pos.x, E.me.pos.z, TEMIZU.x, TEMIZU.z - 1.8, false), () => {
            E.face(TEMIZU.x, TEMIZU.z); E.look(Math.PI, 4.2, 0.2); E.pop(ladle, 2.2); E.sfx("water");
            E.whisper("왼손, 오른손, 그리고 입을 차례로 헹궈 마음을 맑게 해요.", 4000);
          });
        },
        omikuji(E) {
          if (E.state === "focus") return E.whisper("집중이 끝나면 오미쿠지를 뽑아 보세요.");
          E.walk(route(E.me.pos.x, E.me.pos.z, BELL.x - 2.4, BELL.z - 0.4, false), () => {
            E.face(BELL.x, BELL.z - 0.5); E.look(-Math.PI / 2, 5.5, 0.3); kujiShake = 1; E.sfx("kuji");
            setTimeout(() => { E.pop(slip, 3.2); E.whisper(FORTUNES[Math.floor(Math.random() * FORTUNES.length)], 6500); }, 1300);
          });
        },
      },
      sounds: {
        loops: [{ f: "sanji/wind", g: 0.85 }, { f: "sanji/birds", g: 0.55, when: "day" }, { f: "common/crickets", g: 0.5, when: "night" }],
        gusts: [{ f: "sanji/chimes", max: 0.42, every: [14, 30] }],
        sfx: { suzu: { f: "sanji/suzu", g: 0.75, jitter: true }, clap: { f: "sanji/clap", g: 0.8, jitter: true }, kuji: { f: "sanji/kuji", g: 0.8 },
               water: { f: "sento/splash", g: 0.35, rate: 1.15, lp: 2600 } },
      },
      update(dt, t) {
        // 카메라가 벚나무 속으로 들어가면 그 나무의 꽃만 잠깐 숨긴다
        canopies.forEach((c) => { const [cx, cz] = c.userData.at; c.visible = Math.hypot(camera.position.x - cx, camera.position.z - cz) > 3.4 || camera.position.y < 2; });
        const pp = petals.geometry.attributes.position, sd = petals.userData.seed;
        for (let i = 0; i < sd.length; i++) {
          const q = sd[i]; let y = pp.getY(i) - q.v * dt;
          let x = pp.getX(i) + (Math.sin(t * 0.9 + q.ph) * 0.35 + 0.25) * dt, z = pp.getZ(i) + Math.cos(t * 0.7 + q.ph) * 0.25 * dt;
          if (y < 0.02) { y = rand(3.2, 5.2); x = q.x + rand(-2.5, 2.5); z = q.z + rand(-2.5, 2.5); }
          pp.setXYZ(i, x, y, z);
        }
        pp.needsUpdate = true;
        if (suzuSwing > 0) { suzuSwing = Math.max(0, suzuSwing - dt * 0.45); suzuRope.rotation.x = Math.sin((1 - suzuSwing) * 18) * 0.16 * suzuSwing; suzuRope.rotation.z = Math.sin((1 - suzuSwing) * 13) * 0.08 * suzuSwing; }
        if (kujiShake > 0) { kujiShake = Math.max(0, kujiShake - dt * 0.8); kujiBox.rotation.z = Math.sin((1 - kujiShake) * 40) * 0.5 * kujiShake; kujiBox.position.y = 1.5 + Math.abs(Math.sin((1 - kujiShake) * 40)) * 0.12 * kujiShake; }
      },
    };
  },
};
