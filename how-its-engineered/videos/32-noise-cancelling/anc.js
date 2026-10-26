// 32 Noise cancelling: the props this reel adds to the AirTag kit. Over-ear headphones with two tiny mics on each cup,
// a jet engine with a spinning fan, an airliner cabin cutaway (wing and engine outside the windows), a big ear cross
// section where a column of air particles bunches and spreads as the wave passes and an eardrum moves in and out, a
// studio with a phone and hero headphones, a flight map (Zurich → Boston) with an airliner on it, and a notepad.
// Units are centimetres, z up. Load after scenes.js.

Object.assign(Z, { CAB: [0, 0], EAR: [30000, 0], STU2: [-30000, 0], FLY: [0, 40000], C78: [0, -30000] });

ICO.note = (g, S, col) => { g.fillStyle = col; g.shadowColor = col; g.shadowBlur = 10; g.font = `700 ${S * 0.62}px Inter, sans-serif`; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('♪', S / 2, S / 2); };

// a studio floor: dark disc with a faint additive grid (same as 29's studio)
function studioFloor(g, R = 2800) {
  mesh(cy(R, R, 20, 96), mat('#161514', { r: 0.9 }), g, 0, 0, -20);
  const fl = ctex(1024, 1024, (x, w, h) => { x.fillStyle = '#000'; x.fillRect(0, 0, w, h); x.strokeStyle = 'rgba(206,186,169,0.05)'; x.lineWidth = 2; for (let i = 0; i <= 32; i++) { x.beginPath(); x.moveTo(i * 32, 0); x.lineTo(i * 32, h); x.moveTo(0, i * 32); x.lineTo(w, i * 32); x.stroke(); } });
  plane(g, 2 * R, 2 * R, new TH.MeshBasicMaterial({ map: fl, transparent: true, blending: TH.AdditiveBlending, depthWrite: false, toneMapped: false }), 0, 0, 0.2);
}

/* ------------------------------------------------------------------ headphones */
// one ear cup: local z points out from the head. Cushion ring, shell, metal cap, two tiny mics on the outside, and
// (x-ray) a speaker driver and a chip inside. o.glass makes the shell see-through.
function earCup(par, o = {}) {
  const c = grp(par), M = { g: c };
  let shell = pmat(o.col || '#2a2826', { r: 0.35, cc: 0.5, env: 0.8 });
  if (o.glass) { shell = shell.clone(); shell.transparent = true; shell.opacity = 0.2; shell.depthWrite = false; }
  const pad = mat('#151413', { r: 0.9 }), metal = pmat('#8d8985', { r: 0.3, m: 1, env: 1 });
  mesh(tor(5.4, 1.5, 40), pad, c, 0, 0, 1.2);
  mesh(cy(6.4, 6.8, 4.2, 40), shell, c, 0, 0, 1.4, { cast: !o.glass });
  if (!o.glass) mesh(cy(5.0, 5.0, 0.35, 40), metal, c, 0, 0, 5.6);
  M.rimM = glowM(O, 0, '#1a1918'); mesh(tor(6.45, 0.12, 64), M.rimM, c, 0, 0, 5.6, { cast: false });
  M.micM = glowM(O, 0, '#1a1918');
  M.mics = [[2.8, 2.2], [-2.6, -2.4]].map(([x, y]) => { mesh(cy(0.75, 0.75, 0.3, 16), mat('#0b0a09'), c, x, y, 5.6, { cast: false }); return mesh(sph(0.5, 10, 8), M.micM, c, x, y, 5.9, { cast: false }); });
  if (o.glass) {
    // the driver: a cone facing the ear, on a magnet; the chip on a little board behind it
    M.drv = grp(c, 0, 0, 2.2);
    const cone = lathe([[0.3, 0], [4.6, 1.2], [5.0, 1.3]], 48); M.coneM = pmat('#3a3734', { r: 0.5, env: 0.6 });
    const cm = mesh(cone, M.coneM, M.drv); cm.material = M.coneM; cm.material.side = TH.DoubleSide;
    mesh(cy(1.6, 1.6, 1.4, 24), pmat('#9a9590', { r: 0.3, m: 1 }), M.drv, 0, 0, 1.2);
    M.drvGlow = glowM(O, 0, '#141313'); mesh(cy(0.9, 0.9, 0.2, 24), M.drvGlow, M.drv, 0, 0, -0.05, { cast: false });
    mesh(rb(5.4, 3.2, 0.25, 0.1), mat('#1b2a1f', { r: 0.6 }), c, 0, 0, 4.4);
    M.chipM = glowM(O, 0, '#171615'); mesh(rb(1.6, 1.6, 0.4, 0.1), M.chipM, c, 0, 0, 4.65);
  }
  return M;
}
// over-ear headphones for a person's head group (head sphere at 1,0,11 r 11.5)
function headphones(par, o = {}) {
  const g = grp(par, 1, 0, 11), H = { g, cups: [] };
  const shell = pmat(o.col || '#2a2826', { r: 0.35, cc: 0.5, env: 0.8 });
  const band = new TH.TorusGeometry(14.5, o.thin ? 0.6 : 1.5, 10, 40, Math.PI); band.rotateX(Math.PI / 2); band.rotateZ(Math.PI / 2);
  mesh(band, shell, g, 0, 0, 0);
  for (const s of [1, -1]) {
    const cg = grp(g, 0, s * 11.2, -1); cg.rotation.x = -s * Math.PI / 2;
    if (o.thin) { mesh(cy(3.6, 3.6, 2.4, 24), shell, cg); mesh(cy(3.2, 3.2, 0.3, 24), mat('#c9a35a', { r: 0.4, m: 0.6 }), cg, 0, 0, 2.4); H.cups.push({ g: cg }); continue; }
    H.cups.push(earCup(cg, o));
  }
  H.out = (k = 0) => { const v = new TH.Vector3(0, 0, 6.2); H.cups[k].g.localToWorld(v); return [v.x, v.y, v.z]; };
  return H;
}

/* ------------------------------------------------------------------ jet engine */
// a turbofan pointing +x: nacelle (open lathe), a fan of 20 blades that spins, spinner, core and exhaust cone
function engine3(par, x, y, z, sc = 1) {
  const g = grp(par, x, y, z); g.scale.setScalar(sc);
  const skin = pmat('#cfcbc7', { r: 0.35, m: 0.3, cc: 0.3, env: 0.9 }).clone(); skin.side = TH.DoubleSide;
  const metal = pmat('#6d6965', { r: 0.3, m: 1, env: 1.1 }), dark = mat('#0d0c0b', { r: 0.7 });
  const prof = [[84, 6], [92, 0], [100, 22], [102, 120], [96, 240], [80, 320], [72, 345]];
  const nac = lathe(prof.map(([r, xx]) => [r, -xx]), 64); nac.rotateY(Math.PI / 2); mesh(nac, skin, g);
  const lip = mesh(tor(88, 6, 64), metal, g, -3, 0, 0, { ry: Math.PI / 2 });
  mesh(cy(84, 84, 4, 48), dark, g, -70, 0, 0, { ry: Math.PI / 2, cast: false });
  const fan = grp(g, -40, 0, 0); E_FANS.push(fan);
  for (let k = 0; k < 20; k++) { const b = grp(fan); b.rotation.x = (k / 20) * Math.PI * 2; mesh(rb(5, 74, 10, 1), metal, b, 0, 44, -5, { rx: 0.5 }); }
  const sp = lathe([[0.1, 30], [14, 22], [24, 6], [26, 0]], 32); sp.rotateY(Math.PI / 2); mesh(sp, pmat('#e8e5e2', { r: 0.2, m: 0.4, cc: 1 }), g, -40, 0, 0);
  mesh(cy(56, 46, 140, 40), mat('#2f2c2a', { r: 0.5, m: 0.4 }), g, -330, 0, 0, { ry: Math.PI / 2 });
  const ex = lathe([[44, 0], [30, 40], [0.1, 90]], 32); ex.rotateY(-Math.PI / 2); mesh(ex, metal, g, -330, 0, 0);
  const glow = glowSpot(g, -360, 0, 0, 90, O, 0.0);
  mesh(rb(200, 24, 90, 6), skin, g, -160, 0, 90);   // pylon
  return { g, glow, intake: () => wpos(g) };
}
const E_FANS = [];

/* ------------------------------------------------------------------ airliner cabin cutaway */
function airSeat(par, x, y, col, o = {}) {
  const g = grp(par, x, y), fab = mat(col, { r: 0.92 }), frame = mat('#2a2826', { r: 0.5, m: 0.4 });
  mesh(rb(30, 34, 34, 3), frame, g, 0, 0, 0);
  mesh(rb(50, 46, 14, 5), fab, g, 2, 0, 34);
  const back = grp(g, -22, 0, 44); back.rotation.y = -0.16;
  mesh(rb(12, 46, 74, 5), fab, back);
  mesh(rb(5, 32, 18, 3), mat(o.cover || '#d8d4d0', { r: 0.9 }), back, -6.5, 0, 52);
  mesh(rb(3, 30, 12, 1), mat('#121110', { r: 0.4 }), back, -7.5, 0, 22);  // seat-back pocket / screen
  for (const yy of [-24, 24]) mesh(rb(42, 5, 5, 2), frame, g, 0, yy, 60);
  return g;
}
function buildCabin(zn, o = {}) {
  const g = grp(scene, ...Z[zn]), C_ = { g, pax: [] };
  const fab = o.old ? '#6b4a35' : '#3a3f4a';
  mesh(rb(1700, 600, 30, 4), mat('#1a1918', { r: 0.8 }), g, 0, 0, -30);
  const carpet = ctex(256, 256, (x, w, h) => { x.fillStyle = o.old ? '#3a2a22' : '#25262b'; x.fillRect(0, 0, w, h); for (let i = 0; i < 900; i++) { x.fillStyle = `rgba(255,255,255,${0.02 + 0.03 * rnd(i, 2)})`; x.fillRect(rnd(i, 3) * w, rnd(i, 4) * h, 2, 2); } }, [6, 2]);
  plane(g, 1700, 600, texM(carpet, { r: 1 }), 0, 0, 0.1);
  // side wall (+y): low panel, window posts, glass, overhead bins with a soft light strip
  const panel = mat(o.old ? '#cfc6b8' : '#d9d6d2', { r: 0.7 });
  mesh(rb(1700, 14, 64, 3), panel, g, 0, 300, 0);
  const glassM = new TH.MeshStandardMaterial({ color: C('#1a2230'), roughness: 0.1, metalness: 0.2, transparent: true, opacity: 0.18, depthWrite: false });
  for (let k = -4; k <= 4; k++) {
    const x = k * 190;
    mesh(rb(26, 18, 140, 4), panel, g, x + 95, 300, 64);
    plane(g, 70, 96, glassM, x, 304, 130, '-y');
    mesh(rb(80, 6, 104, 22, 4), mat('#2c2a28', { r: 0.4 }), g, x, 310, 78).visible = false;
  }
  mesh(rb(1700, 18, 14, 3), panel, g, 0, 300, 204);
  mesh(rb(1700, 86, 46, 8), mat(o.old ? '#bfb5a6' : '#cfccc8', { r: 0.6 }), g, 0, 252, 214);
  C_.binL = glowM('#ffe7cf', 0.9, '#2a2826'); mesh(rb(1700, 3, 3, 1), C_.binL, g, 0, 208, 212, { cast: false });
  // seats: five rows × three on the window side; the near side is cut away for the view
  const rows = [-380, -190, 0, 190, 380];
  rows.forEach((x, ri) => [200, 145, 90].forEach((y, si) => airSeat(g, x, y, fab, { cover: o.old ? '#e7dccb' : '#d8d4d0' })));
  // passengers (a few seats taken), each facing +x
  const taken = [[-380, 145, 3], [-190, 90, 8], [190, 200, 5], [380, 145, 11], [190, 90, 2]];
  taken.forEach(([x, y, sd]) => { const p = person(g, x + 6, y, 0, { seed: sd }); p.pose('sit'); C_.pax.push(p); });
  C_.hero = person(g, 6, 200, 0, { seed: o.old ? 4 : 1, shirt: o.old ? '#5c4a3a' : '#4a4642', pants: '#282625', hair: o.old ? '#1d1714' : undefined });
  C_.hero.pose('sit');
  C_.hp = headphones(C_.hero.head, { thin: !!o.old, col: o.old ? '#3a3632' : '#2a2826' });
  // wing and engine outside the windows (+y), under the cabin floor line
  const wingS = new TH.Shape(); wingS.moveTo(-260, 0); wingS.lineTo(240, 0); wingS.lineTo(-180, 1500); wingS.lineTo(-420, 1500); wingS.closePath();
  const wing = mesh(new TH.ExtrudeGeometry(wingS, { depth: 18, bevelEnabled: true, bevelSize: 6, bevelThickness: 6, bevelSegments: 2 }), pmat('#c7c3bf', { r: 0.4, m: 0.3, env: 0.7 }), g, 0, 330, -70);
  C_.eng = engine3(g, 140, 820, -200, 1.0);
  // a tray table on the seat in front of the hero (deployed only in 1978)
  if (o.old) {
    const tray = grp(g, 62, 200, 70); mesh(rb(34, 40, 2.4, 1), mat('#bfb5a6', { r: 0.6 }), tray);
    mesh(rb(23, 30, 0.6, 0.3), mat('#efe8da', { r: 0.95 }), tray, -1, 0, 2.4);
    C_.pad = scr(22, 29, 34, tray, 1.0); C_.pad.m.position.set(-1, 0, 3.1);
    C_.pen = mesh(cy(0.45, 0.45, 13, 8), mat('#1d1b19', { r: 0.4 }), tray, 0, 0, 4, { ry: 1.2 });
    C_.tray = tray;
  }
  return C_;
}

/* ------------------------------------------------------------------ the ear, in cross-section */
// Along +x: the engine far left, a column of air (particles) to the ear, the hero ear cup (x-ray) against the side
// of the head, the ear canal and the eardrum at x = 330. HC is the height of the column's axis.
const HC = 170, DRUM_X = 330, CUP_X = 150;
function buildEar() {
  const g = grp(scene, ...Z.EAR), E = { g };
  studioFloor(g, 3200);
  E.eng = engine3(g, -1250, 0, HC, 0.9);
  mesh(rb(80, 50, HC - 90, 6), mat('#24221f', { r: 0.7 }), g, -1420, 0, 0);
  // the head: a soft translucent block, the canal inside it, the eardrum
  const skin = pmat('#c99f84', { r: 0.6, env: 0.4 }).clone(); skin.transparent = true; skin.opacity = 0.16; skin.depthWrite = false;
  mesh(rb(360, 520, 420, 120, 6), skin, g, CUP_X + 180, 0, 0, { cast: false });
  const canalM = pmat('#d79a86', { r: 0.6, env: 0.4 }).clone(); canalM.transparent = true; canalM.opacity = 0.3; canalM.side = TH.DoubleSide; canalM.depthWrite = false;
  mesh(cy(36, 32, DRUM_X - CUP_X, 40), canalM, g, CUP_X, 0, HC, { ry: Math.PI / 2, cast: false });
  E.drum = grp(g, DRUM_X, 0, HC);
  const dm = new TH.SphereGeometry(40, 32, 12, 0, Math.PI * 2, 0, 0.5); dm.rotateZ(-Math.PI / 2); dm.translate(-35, 0, 0);
  E.drumM = pmat('#e9b7a0', { r: 0.45, cc: 0.4, env: 0.7 }).clone(); E.drumM.side = TH.DoubleSide;
  mesh(dm, E.drumM, E.drum, 0, 0, 0, { cast: false });
  mesh(tor(37, 3, 48), pmat('#b97a66', { r: 0.6 }), g, DRUM_X, 0, HC, { ry: Math.PI / 2 });
  E.drumRing = glowM(O, 0, '#1a1918'); mesh(tor(41, 0.8, 64), E.drumRing, g, DRUM_X, 0, HC, { ry: Math.PI / 2, cast: false });
  // the hero ear cup, x-ray, pressed against the head (outward = -x); it lowers into place for the mic beat
  E.cupG = grp(g, CUP_X, 0, HC); E.cupR = grp(E.cupG); E.cupR.rotation.y = -Math.PI / 2; E.cupR.scale.setScalar(13);
  E.cup = earCup(E.cupR, { glass: true });
  E.mic = (k) => { const v = new TH.Vector3(); E.cup.mics[k].getWorldPosition(v); return [v.x, v.y, v.z]; };
  E.chip = () => { const v = new TH.Vector3(0, 0, 4.85); E.cupR.localToWorld(v); return [v.x, v.y, v.z]; };
  E.drv = () => { const v = new TH.Vector3(0, 0, 2.0); E.cupR.localToWorld(v); return [v.x, v.y, v.z]; };
  // the air: particles in a column, displaced along x by the wave (bunched = push, spread = pull)
  const N = 1500, pos = new Float32Array(N * 3), col = new Float32Array(N * 3), meta = [];
  for (let n = 0; n < N; n++) { const x0 = -1080 + rnd(n, 21) * (DRUM_X - 4 + 1080), r0 = Math.sqrt(rnd(n, 22)), th = rnd(n, 23) * Math.PI * 2; meta.push({ x0, r0, th, b: 0.55 + 0.45 * rnd(n, 24) }); }
  const pg = new TH.BufferGeometry(); pg.setAttribute('position', new TH.BufferAttribute(pos, 3)); pg.setAttribute('color', new TH.BufferAttribute(col, 3));
  E.air = new TH.Points(pg, new TH.PointsMaterial({ map: TX_SOFT, size: 9, sizeAttenuation: false, vertexColors: true, transparent: true, blending: TH.AdditiveBlending, depthWrite: false, toneMapped: false }));
  E.air.frustumCulled = false; scene.add(E.air);
  // disp(x) → displacement in -1..1 at that x; dens(x) → compression; a = brightness
  E.updAir = (disp, dens, a, D = 22) => {
    E.air.visible = a > 0.01; if (!E.air.visible) return;
    meta.forEach((m, n) => {
      const R = m.x0 > CUP_X - 20 ? 30 : 75, x = m.x0 + D * disp(m.x0);
      pos[n * 3] = Z.EAR[0] + x; pos[n * 3 + 1] = Z.EAR[1] + Math.cos(m.th) * m.r0 * R; pos[n * 3 + 2] = HC + Math.sin(m.th) * m.r0 * R;
      const k = a * m.b * (0.55 + 0.6 * clamp(0.5 + 0.5 * dens(m.x0), 0, 1.2));
      col[n * 3] = k * 1.5; col[n * 3 + 1] = k * 1.05; col[n * 3 + 2] = k * 0.8;
    });
    pg.attributes.position.needsUpdate = true; pg.attributes.color.needsUpdate = true;
  };
  return E;
}

/* ------------------------------------------------------------------ studio: phone + hero headphones */
function buildStu2() {
  const g = grp(scene, ...Z.STU2), S = { g };
  studioFloor(g);
  S.ph = phoneStand(g, 170, 0, '#2d2b29', 'ios');
  // hero headphones on a stand
  const st = grp(g, -190, 40), alu = pmat('#4a4744', { r: 0.42, m: 1, env: 0.55 });
  mesh(cy(46, 50, 4, 64), alu, st); mesh(cy(2.4, 2.4, 160, 12), alu, st, 0, 0, 4);
  const hd = grp(st, 0, 0, 164); hd.scale.setScalar(4.2); hd.rotation.z = 0.9;
  S.hp = headphones(hd, {}); S.hp.g.position.set(0, 0, 12);
  S.hd = hd;
  return S;
}

/* ------------------------------------------------------------------ flight map: Zurich → Boston */
const MAPW = 14000, MAPH = 8000;
function buildFly() {
  const g = grp(scene, ...Z.FLY), F = { g };
  const tex = ctex(2048, 1170, (x, w, h) => {
    x.fillStyle = '#0d1114'; x.fillRect(0, 0, w, h);
    // faint graticule
    x.strokeStyle = 'rgba(160,170,180,0.06)'; x.lineWidth = 2;
    for (let i = 0; i <= 16; i++) { x.beginPath(); x.moveTo(i * w / 16, 0); x.lineTo(i * w / 16, h); x.stroke(); }
    for (let j = 0; j <= 9; j++) { x.beginPath(); x.moveTo(0, j * h / 9); x.lineTo(w, j * h / 9); x.stroke(); }
    const land = (pts, fill) => { x.fillStyle = fill; x.beginPath(); pts.forEach(([a, b], i) => (i ? x.lineTo(a * w, b * h) : x.moveTo(a * w, b * h))); x.closePath(); x.fill(); x.strokeStyle = 'rgba(255,176,112,0.18)'; x.lineWidth = 3; x.stroke(); };
    // North America (left), Greenland, the British Isles and Europe (right): rough silhouettes
    land([[0, 0.12], [0.1, 0.1], [0.2, 0.2], [0.24, 0.34], [0.28, 0.4], [0.25, 0.47], [0.21, 0.52], [0.17, 0.6], [0.14, 0.72], [0.1, 0.8], [0.04, 0.85], [0, 0.86]], '#1e2124');
    land([[0.3, 0.02], [0.42, 0.0], [0.45, 0.1], [0.4, 0.22], [0.35, 0.25], [0.31, 0.15]], '#1c1f22');
    land([[0.72, 0.26], [0.76, 0.22], [0.78, 0.3], [0.76, 0.4], [0.73, 0.42], [0.71, 0.34]], '#1e2124');
    land([[0.8, 0.12], [0.88, 0.08], [1, 0.1], [1, 0.95], [0.9, 0.9], [0.86, 0.78], [0.8, 0.74], [0.78, 0.62], [0.82, 0.5], [0.8, 0.42], [0.84, 0.32], [0.8, 0.22]], '#1e2124');
  });
  plane(g, MAPW, MAPH, texM(tex, { r: 0.95 }), 0, 0, 0.5);
  // cities on the map (x, y in cm, zone-local)
  F.zrh = [0.87 * MAPW - MAPW / 2, MAPH / 2 - 0.58 * MAPH, 2]; F.bos = [0.19 * MAPW - MAPW / 2, MAPH / 2 - 0.47 * MAPH, 2];
  for (const p of [F.zrh, F.bos]) { mesh(cy(40, 40, 6, 24), glowM(O, 2.2), g, p[0], p[1], 0); }
  // the route: a great-circle-ish arc bowing north
  F.route = []; for (let i = 0; i <= 40; i++) { const u = i / 40; F.route.push([lerp(F.zrh[0], F.bos[0], u) + Z.FLY[0], lerp(F.zrh[1], F.bos[1], u) + Math.sin(u * Math.PI) * 1500 + Z.FLY[1], 8]); }
  // an airliner: white fuselage, swept wings, tail, three engines (two under the wings, one in the tail)
  const pl = grp(scene), white = pmat('#eceae7', { r: 0.3, cc: 0.6, env: 1 }), grey = pmat('#9d9994', { r: 0.4, m: 0.4 });
  const fus = new TH.CapsuleGeometry(55, 760, 6, 24); fus.rotateZ(Math.PI / 2); mesh(fus, white, pl, 0, 0, 0);
  const ws = new TH.Shape(); ws.moveTo(-60, 0); ws.lineTo(140, 0); ws.lineTo(-200, 620); ws.lineTo(-290, 620); ws.closePath();
  for (const s of [1, -1]) { const wg = new TH.ExtrudeGeometry(ws, { depth: 10, bevelEnabled: false }); if (s < 0) wg.scale(1, -1, 1); mesh(wg, white, pl, 0, 0, -20); const e = mesh(cy(26, 22, 120, 20), grey, pl, -60, s * 260, -40, { ry: -Math.PI / 2 }); }
  const ts = new TH.Shape(); ts.moveTo(-360, 0); ts.lineTo(-450, 0); ts.lineTo(-500, 260); ts.lineTo(-440, 260); ts.closePath();
  const tg = new TH.ExtrudeGeometry(ts, { depth: 10, bevelEnabled: false }); tg.rotateX(Math.PI / 2); mesh(tg, white, pl, 0, 5, 40);
  mesh(cy(26, 22, 110, 20), grey, pl, -380, 0, 90, { ry: -Math.PI / 2 });
  const hs = new TH.Shape(); hs.moveTo(-400, 0); hs.lineTo(-460, 0); hs.lineTo(-500, 200); hs.lineTo(-470, 200); hs.closePath();
  for (const s of [1, -1]) { const hg = new TH.ExtrudeGeometry(hs, { depth: 6, bevelEnabled: false }); if (s < 0) hg.scale(1, -1, 1); mesh(hg, white, pl, 0, 0, 10); }
  pl.scale.setScalar(1.6); F.plane = pl;
  F.at = (u) => along(F.route, u);
  return F;
}
