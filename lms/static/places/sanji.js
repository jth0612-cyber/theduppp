// 같이 공부 · 산사. 일주문 → 돌길과 석등이 있는 마당 → 계단 → 법당(靜學堂, 방석 24개), 종각과 에마 걸이.
export default {
  build(K) {
    const { THREE, scene, TIME, PAL, mat, box, cyl, roof, textTexture, rand, srand, cedar, bamboo } = K;
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


    // 종 흔들림·목탁
    let bellSwing = 0;
    const moktakObj = new THREE.Mesh(new THREE.SphereGeometry(0.22, 12, 8), mat(0x9a5a2e));
    moktakObj.scale.set(1.2, 0.85, 1); moktakObj.visible = false; moktakObj.userData.popScale = 1; scene.add(moktakObj);
    bellMesh.userData.action = "bell";
    emaRack.traverse((o) => { if (o.isMesh) o.userData.notes = true; });
    return {
      seats: SEATS, seatNoun: "방석", heightAt,
      spawn: { x: 0, z: 11.5, yaw: Math.PI },
      picks: [...pickSeats, bellMesh, ...emaRack.children, ...pickHall, ...pickGround],
      indoor: (x, z) => inHall(x, z),
      planWalk(from, p, obj) { return route(from.x, from.z, p.x, p.z, pickHall.includes(obj) || inHall(p.x, p.z)); },
      planTo(from, x, z) { return route(from.x, from.z, x, z, inHall(x, z)); },
      planSeat(from, id) { const s = SEATS[id]; return route(from.x, from.z, s.x, s.z + 0.9, true).concat([[s.x, s.z]]); },
      step(x, z, nx, nz) { const onSteps = Math.abs(nx) < 2.6 && nz > -3.2 && nz < 1.0; return onSteps ? [nx, nz] : clampWalk(nx, nz, inHall(x, z)); },
      welcome: "고요한 산사예요. 법당 방석에 앉아 집중을 시작해 보세요.",
      sitText: "방석에 앉았어요. 시간을 고르고 집중을 시작해 보세요.",
      actions: { free: ["sit", "gassho", "bow", "moktak", "bell"], sitting: ["focus", "breathe", "moktak", "gassho", "stand"], focus: ["breathe", "moktak", "stop"] },
      labels: { moktak: "목탁", bell: "종 치기" },
      custom: {
        moktak(E) { E.sfx("moktak"); E.pop(moktakObj, 0.9); },
        bell(E) {
          if (E.state === "focus") return E.whisper("집중이 끝나면 종을 쳐 보세요.");
          E.walk(route(E.me.pos.x, E.me.pos.z, BELL.x - 3.0, BELL.z, false), () => {
            E.face(BELL.x, BELL.z); bellSwing = 1; E.sfx("bell"); E.whisper("데엥— 종소리가 산을 건너가요.");
          });
        },
      },
      sounds: {
        loops: [{ f: "sanji/wind", g: 0.85 }, { f: "sanji/birds", g: 0.55, when: "day" }, { f: "common/crickets", g: 0.5, when: "night" }],
        gusts: [{ f: "sanji/chimes", max: 0.42, every: [14, 30] }],
        sfx: { moktak: { f: "sanji/moktak", g: 0.9, jitter: true }, bell: { f: "common/bowl", g: 1.0, rate: 0.42, lp: 1400 } },
      },
      update(dt) { if (bellSwing > 0) { bellSwing -= dt * 0.35; bellMesh.rotation.x = Math.sin((1 - bellSwing) * 14) * 0.12 * bellSwing; } },
    };
  },
};
