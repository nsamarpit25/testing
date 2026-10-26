// 34 Shazam: the pieces this reel adds to the AirTag kit. A noisy café with a wall speaker, a hero phone with a
// listening screen, a spectrogram wall (time across, pitch up) made of glowing bars that thin out to star peaks, a
// fingerprint strip, a hall of fingerprints with a sliding match panel, a 2002 pub with an old candy-bar phone held up
// to a speaker, and the humming twist (two star panels that don't line up). Load after scenes.js.
Z.CAFE = [0, 0]; Z.LAB = [0, 30000]; Z.DB = [30000, 0]; Z.OLD = [-30000, 0]; Z.HUM = [0, -30000];

ICO.mail = (g, S, col) => {
  g.strokeStyle = col; g.fillStyle = col; g.lineWidth = S * 0.06; g.lineJoin = 'round'; g.shadowColor = col; g.shadowBlur = 8;
  g.beginPath(); g.roundRect(S * 0.2, S * 0.3, S * 0.6, S * 0.42, S * 0.05); g.stroke();
  g.beginPath(); g.moveTo(S * 0.22, S * 0.33); g.lineTo(S / 2, S * 0.54); g.lineTo(S * 0.78, S * 0.33); g.stroke();
};
ICO.note = (g, S, col) => {
  g.fillStyle = col; g.strokeStyle = col; g.lineWidth = S * 0.06; g.shadowColor = col; g.shadowBlur = 8;
  g.beginPath(); g.ellipse(S * 0.38, S * 0.7, S * 0.12, S * 0.09, -0.4, 0, 7); g.fill();
  g.beginPath(); g.moveTo(S * 0.49, S * 0.68); g.lineTo(S * 0.49, S * 0.2); g.lineTo(S * 0.7, S * 0.3); g.stroke();
};

/* ------------------------------------------------------------------ the music: a spectrogram and its peaks */
// NX time columns × NY pitch rows. A melody, a harmony a fifth up, a bass line, drum hits across the band, a noise floor.
const NX = 40, NY = 32, CW = 24, Z0 = 40;
const MEL = [14, 16, 18, 16, 21, 19, 18, 14, 13, 16, 18, 21], BASS = [3, 3, 5, 4, 3, 6];
const g1 = (x, s) => Math.exp(-x * x / (s * s));
const AMP = [];
for (let i = 0; i < NX; i++) {
  const m = MEL[Math.floor(i / 4) % MEL.length], b = BASS[Math.floor(i / 7) % BASS.length], onm = 1 - 0.35 * ((i % 4) / 3), drum = i % 4 === 0 ? 1 : 0;
  for (let j = 0; j < NY; j++) {
    let a = 0.06 + 0.12 * rnd(i * 61 + j, 3);
    a += 0.95 * onm * g1(j - m, 0.75) + 0.5 * onm * g1(j - m - 7, 0.7) + 0.3 * g1(j - m - 12, 0.6);
    a += 0.8 * g1(j - b, 0.8) * (0.75 + 0.25 * Math.sin(i));
    a += drum * 0.32 * (0.6 + 0.4 * rnd(i + j * 7, 5)) * (j > 22 ? 1.2 : 0.7);
    AMP.push(clamp(a, 0, 1));
  }
}
const amp = (i, j) => AMP[i * NY + j];
// keep the brightest cell of each 4 × 4 patch (if it is loud enough): those are the stars
const PATCH = 4, PEAKS = [];
for (let pi = 0; pi < NX / PATCH; pi++) for (let pj = 0; pj < NY / PATCH; pj++) {
  let best = null;
  for (let i = pi * PATCH; i < (pi + 1) * PATCH; i++) for (let j = pj * PATCH; j < (pj + 1) * PATCH; j++) if (!best || amp(i, j) > amp(best[0], best[1])) best = [i, j];
  if (amp(best[0], best[1]) > 0.42) PEAKS.push({ i: best[0], j: best[1], a: amp(best[0], best[1]) });
}
const ISPEAK = new Set(PEAKS.map((p) => p.i * NY + p.j));
// the café adds a few stars that aren't in the song, and buries some that are
const NOISE = Array.from({ length: 11 }, (_, k) => ({ i: 2 + Math.floor(rnd(k, 41) * (NX - 4)), j: 1 + Math.floor(rnd(k, 42) * (NY - 2)) }));
const HIDDEN = new Set(PEAKS.map((_, k) => k).filter((k) => k % 6 === 3));
// pairs of stars that become codes: an anchor and a later star close in time
const PAIRS = (() => {
  const out = [], used = new Set();
  const cand = PEAKS.map((p, k) => ({ ...p, k })).filter((p) => p.i >= 8 && p.i <= 28 && !HIDDEN.has(p.k)).sort((a, b) => a.i - b.i || a.j - b.j);
  for (const a of cand) {
    if (out.length >= 6 || used.has(a.k)) continue;
    const b = cand.filter((q) => q.i > a.i + 1 && q.i <= a.i + 8 && !used.has(q.k) && q.k !== a.k).sort((p, q) => Math.abs(p.j - a.j) - Math.abs(q.j - a.j))[0];
    if (!b) continue;
    used.add(a.k); out.push([a.k, b.k]);
  }
  return out;
})();
const ampCol = (a) => (a < 0.5 ? mixHex('#3a1406', '#ff6a1f', a / 0.5) : mixHex('#ff6a1f', '#ffe9d2', (a - 0.5) / 0.5));

/* ------------------------------------------------------------------ star points */
// a pool of glowing points (pixel size), set per frame
function starPool(n, size = 26) {
  const pos = new Float32Array(n * 3), col = new Float32Array(n * 3), g = new TH.BufferGeometry();
  g.setAttribute('position', new TH.BufferAttribute(pos, 3)); g.setAttribute('color', new TH.BufferAttribute(col, 3));
  const pts = new TH.Points(g, new TH.PointsMaterial({ map: TX_ORB, size, sizeAttenuation: false, vertexColors: true, transparent: true, blending: TH.AdditiveBlending, depthWrite: false, toneMapped: false }));
  pts.frustumCulled = false; pts.renderOrder = 7; scene.add(pts);
  let k = 0;
  return {
    pts, begin() { k = 0; },
    add(x, y, z, hex, a) { if (k >= n || a <= 0.005) return; const c = C(hex); pos.set([x, y, z], k * 3); col.set([c.r * a * 2.2, c.g * a * 2.2, c.b * a * 2.2], k * 3); k++; },
    end() { for (let q = k; q < n; q++) pos.set([0, 0, -1e6], q * 3); g.attributes.position.needsUpdate = true; g.attributes.color.needsUpdate = true; },
  };
}

/* ------------------------------------------------------------------ CAFE */
function chair(par, x, y, rz) {
  const g = grp(par, x, y, 0, rz), w = mat('#3a3431', { r: 0.7 }), leg = mat('#1d1b1a', { r: 0.5, m: 0.4 });
  mesh(rb(42, 42, 4, 2), w, g, 0, 0, 44); mesh(rb(4, 40, 42, 2), w, g, -19, 0, 48);
  for (const [sx, sy] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) mesh(cy(1.6, 1.6, 44, 6), leg, g, sx * 17, sy * 17, 0);
  return g;
}
function roundTable(par, x, y) {
  const g = grp(par, x, y), top = mat('#4a423c', { r: 0.45 }), metal = mat('#1d1b1a', { r: 0.4, m: 0.6 });
  mesh(cy(42, 42, 4, 32), top, g, 0, 0, 72); mesh(cy(3, 3, 72, 10), metal, g); mesh(cy(22, 24, 3, 24), metal, g);
  return g;
}
function cup(par, x, y, z) { const g = grp(par, x, y, z); mesh(cy(4.6, 3.8, 9, 16), mat('#e3ddd8', { r: 0.35 }), g); mesh(cy(7.5, 7.5, 0.8, 20), mat('#d6d0cb', { r: 0.35 }), g); return g; }
function wallSpeaker(par, x, y, z, sc = 1) {
  const g = grp(par, x, y, z); g.scale.setScalar(sc);
  mesh(rb(46, 32, 70, 4), mat('#1a1817', { r: 0.6 }), g, 0, 0, 0);
  const cone = mat('#0b0a0a', { r: 0.9 }), rim = mat('#3b3734', { r: 0.4, m: 0.6 });
  for (const [z_, r] of [[48, 9], [22, 16]]) { const m = mesh(cy(r, r * 0.6, 3, 24), cone, g, 0, -16, z_, { rx: Math.PI / 2 }); mesh(tor(r, 1.2, 32), rim, g, 0, -17, z_, { rx: Math.PI / 2 }); }
  const led = glowM(O, 2); mesh(sph(1.4, 8, 6), led, g, 16, -16.5, 6);
  return { g, mouth: [x, y - 20 * sc, z + 35 * sc], led };
}
function buildCafe() {
  const g = grp(scene, ...Z.CAFE), W = 1240, D = 900, WH = 330, F = { g };
  mesh(rb(W + 16, D + 16, 30), mat('#151413'), g, -8, 8, -30.2);
  plane(g, W, D, texM(planksTex(), { r: 0.7, c: '#cfc6bf' }), 0, 0, 0.05);
  const wall = mat('#2f2a27', { r: 0.95 }), trim = mat('#1d1c1b', { r: 0.8 });
  mesh(rb(W + 16, 16, WH), wall, g, -8, D / 2 + 8, 0);
  mesh(rb(16, D, WH), wall, g, -W / 2 - 8, 0, 0);
  // tiled lower half on the back wall, a chalk menu board, a window to the street
  plane(g, W, 110, texM(tilesTex('#3a3330', '#2a2523', 10), { r: 0.5 }), 0, D / 2 - 0.5, 55, '-y');
  const menu = ctex(320, 220, (x, w, h) => {
    x.fillStyle = '#161514'; x.fillRect(0, 0, w, h); x.strokeStyle = '#5a524c'; x.lineWidth = 6; x.strokeRect(3, 3, w - 6, h - 6);
    x.fillStyle = '#d8d0c8'; x.font = '700 26px Inter'; x.fillText('MENU', 24, 44);
    [['Espresso', '2.4'], ['Flat white', '3.2'], ['Chai', '3.0'], ['Croissant', '2.8']].forEach(([a, b], k) => { x.font = '500 20px Inter'; x.fillStyle = '#b9b0a8'; x.fillText(a, 24, 86 + k * 34); x.textAlign = 'right'; x.fillText(b, w - 24, 86 + k * 34); x.textAlign = 'left'; });
  });
  plane(g, 150, 103, texM(menu, { r: 0.8 }), -330, D / 2 - 0.6, 230, '-y');
  plane(g, 260, 150, screenM(skylineTex(), 0.8), 110, D / 2 - 0.6, 215, '-y');
  for (const [w, h, x, z] of [[276, 8, 110, 136], [276, 8, 110, 290], [8, 162, -24, 136], [8, 162, 244, 136], [5, 150, 110, 140]]) mesh(rb(w, 10, h), trim, g, x, D / 2 - 5, z);
  // the counter along the left wall with an espresso machine
  mesh(rb(90, 420, 100, 4), mat('#2a2523', { r: 0.6 }), g, -W / 2 + 60, 120, 0);
  mesh(rb(96, 426, 5, 2), mat('#5d544d', { r: 0.35 }), g, -W / 2 + 60, 120, 100);
  mesh(rb(46, 60, 46, 6), pmat('#8e8883', { r: 0.25, m: 1, env: 0.9 }), g, -W / 2 + 60, 210, 105);
  for (let k = 0; k < 4; k++) cup(g, -W / 2 + 50, 40 + k * 22, 105);
  // the speaker high on the back wall, right of the window: the music
  F.spk = wallSpeaker(g, 400, D / 2 - 18, 210, 1.3);
  F.spk2 = wallSpeaker(g, -W / 2 + 22, -260, 220, 1.1); F.spk2.g.rotation.z = Math.PI / 2;
  // pendant lights
  F.lamps = [];
  for (const [x, y] of [[-160, -120], [210, -60], [-60, 230], [380, 210]]) {
    mesh(cy(0.7, 0.7, 120, 6), mat('#111'), g, x, y, WH - 120);
    const sh = mesh(cy(4, 22, 20, 24), glowM('#ffd8b0', 1.2, '#2e2a27'), g, x, y, WH - 140);
    const L = new TH.PointLight(C('#ffc89a'), 120, 520, 1.2); L.position.set(x, y, WH - 150); g.add(L); F.lamps.push(L);
  }
  // tables of people talking; their cups clink
  F.talk = []; F.cups = [];
  const TB = [[-160, -120], [210, -60], [-60, 230]];
  TB.forEach(([x, y], n) => {
    roundTable(g, x, y);
    for (const [dx, rz] of [[-62, 0], [62, Math.PI]]) {
      chair(g, x + dx, y, rz);
      const p = person(g, x + dx - (dx < 0 ? 4 : -4), y, rz, { seed: 3 + n * 2 + (dx > 0 ? 1 : 0), long: (n + (dx > 0)) % 2 === 1 });
      F.talk.push({ p, ph: n * 1.7 + (dx > 0 ? 2.3 : 0) });
      F.cups.push(cup(g, x + dx * 0.35, y + (dx < 0 ? -8 : 10), 76));
    }
  });
  // you, alone at the window table, holding your phone up toward the speaker
  roundTable(g, 380, 210); chair(g, 318, 210, 0);
  F.you = person(g, 314, 210, 0, { seed: 1, phone: true, shirt: '#5a5551' });
  F.cups.push(cup(g, 392, 196, 76));
  plant(g, -560, 400, 1.3); plant(g, 560, 400, 1.1);
  F.youPhone = () => wpos(F.you.phone);
  return F;
}

/* ------------------------------------------------------------------ STUDIO: the hero phones */
// an old candy-bar phone: a rounded slab, a small greenish screen, a 4 × 3 keypad and a nav key. Front faces +z.
function oldPhone(par, sc = 8) {
  const g = grp(par); g.up.set(0, 0, 1);
  const W = 4.6 * sc, H = 11.2 * sc, T = 1.9 * sc;
  const body = pmat('#3a3d42', { r: 0.35, m: 0.5, env: 1.0 }), face = pmat('#24262a', { r: 0.4, m: 0.2, env: 0.8 }), key = pmat('#cfd2d6', { r: 0.4, env: 0.7 });
  mesh(slab(W, H, T, 1.4 * sc, 0.5 * sc), body, g);
  mesh(slab(W - 0.5 * sc, H - 0.5 * sc, 0.2 * sc, 1.2 * sc, 0.08 * sc, 4), face, g, 0, 0, T / 2 - 0.05 * sc);
  const sw = 3.2 * sc, sh = 2.7 * sc;
  mesh(slab(sw + 0.5 * sc, sh + 0.5 * sc, 0.12 * sc, 0.3 * sc, 0.05 * sc, 3), mat('#0c0d0e', { r: 0.2 }), g, 0, 2.6 * sc, T / 2 + 0.06 * sc);
  const s = scr(sw, sh, (sc > 3 ? 640 : 256) / sw, g, 1.0, 0.15 * sc); s.m.position.set(0, 2.6 * sc, T / 2 + 0.14 * sc);
  mesh(rrg(0.9 * sc, 0.12 * sc, 0.06 * sc), mat('#0c0d0e'), g, 0, 4.7 * sc, T / 2 + 0.1 * sc, { cast: false });
  mesh(slab(1.7 * sc, 0.75 * sc, 0.2 * sc, 0.35 * sc, 0.06 * sc, 3), key, g, 0, 0.55 * sc, T / 2 + 0.08 * sc);
  const keys = [];
  for (let r = 0; r < 4; r++) for (let c = 0; c < 3; c++) {
    const k = mesh(slab(1.0 * sc, 0.62 * sc, 0.18 * sc, 0.22 * sc, 0.06 * sc, 3), key, g, (c - 1) * 1.25 * sc, (-0.65 - r * 0.85) * sc, T / 2 + 0.08 * sc);
    keys.push(k);
  }
  // digits on the keys
  const lab = ctex(512, 512, (x, w, h) => {
    x.clearRect(0, 0, w, h); x.fillStyle = '#26282b'; x.font = '700 64px Inter'; x.textAlign = 'center'; x.textBaseline = 'middle';
    '123456789*0#'.split('').forEach((d, n) => x.fillText(d, (n % 3 + 0.5) * w / 3, (Math.floor(n / 3) + 0.5) * h / 4));
  });
  const lp = new TH.Mesh(new TH.PlaneGeometry(3 * 1.25 * sc, 4 * 0.85 * sc), new TH.MeshBasicMaterial({ map: lab, transparent: true, toneMapped: false, depthWrite: false }));
  lp.position.set(0, (-0.65 - 1.5 * 0.85) * sc, T / 2 + 0.2 * sc); g.add(lp);
  mesh(cy(0.25 * sc, 0.25 * sc, 1.2 * sc, 10), body, g, W / 2 - 0.8 * sc, H / 2, -0.2 * sc); // stub antenna
  return { g, s, keys, W, H, T };
}
function oldStand(par, x, y, sc = 8) {
  const g = grp(par, x, y);
  mesh(rb(250, 210, 34, 10, 4), pmat('#1c1a19', { r: 0.55, env: 0.35 }), g);
  mesh(rb(238, 198, 1, 8), pmat('#262422', { r: 0.4, env: 0.5 }), g, 0, 0, 34);
  const ph = oldPhone(g, sc);
  ph.g.rotation.order = 'ZXY'; ph.g.rotation.set(Math.PI / 2 - 0.28, 0, 0.7);
  ph.g.position.set(Math.sin(0.7) * 14, Math.cos(0.7) * 14, 36 + 46);
  const alu = pmat('#4a4744', { r: 0.42, m: 1, env: 0.55 }), st = grp(g, 0, 0, 35, 0.7);
  mesh(cy(34, 36, 3, 64), alu, st, 0, 22, 0);
  mesh(rb(26, 2.4, 80, 1.2, 3), alu, st, 0, 40, 2, { rx: -0.28 });
  mesh(rb(46, 9, 2.4, 1.1, 3), alu, st, 0, 6, 2);
  return { g, ph, s: ph.s, top: wpos(ph.g) };
}
function buildPhones() {
  const g = grp(scene, ...Z.STU), S = { g };
  mesh(cy(2800, 2800, 20, 96), mat('#161514', { r: 0.9 }), g, 0, 0, -20);
  const fl = ctex(1024, 1024, (x, w, h) => { x.fillStyle = '#000'; x.fillRect(0, 0, w, h); x.strokeStyle = 'rgba(206,186,169,0.05)'; x.lineWidth = 2; for (let i = 0; i <= 32; i++) { x.beginPath(); x.moveTo(i * 32, 0); x.lineTo(i * 32, h); x.moveTo(0, i * 32); x.lineTo(w, i * 32); x.stroke(); } });
  plane(g, 5600, 5600, new TH.MeshBasicMaterial({ map: fl, transparent: true, blending: TH.AdditiveBlending, depthWrite: false, toneMapped: false }), 0, 0, 0.2);
  S.yours = phoneStand(g, 0, 0, '#2d2b29', 'ios');
  S.old = oldStand(g, -1600, 0);
  S.under = glowSpot(g, 0, 0, 0.5, 260, O, 0.06);
  S.under2 = glowSpot(g, -1600, 0, 0.5, 260, '#b9d08a', 0.04);
  return S;
}

/* ------------------------------------------------------------------ LAB: the spectrogram wall */
function buildLab() {
  const g = grp(scene, ...Z.LAB), L = { g }, X0 = -NX * CW / 2;
  mesh(cy(2600, 2600, 20, 96), mat('#121110', { r: 0.95 }), g, 0, 300, -20);
  // the backing slab, a thin frame
  mesh(rb(NX * CW + 60, 40, NY * CW + 70, 6), mat('#141312', { r: 0.7 }), g, 0, 22, Z0 - 35);
  const fr = mat('#2f2b28', { r: 0.4, m: 0.5 });
  mesh(rb(NX * CW + 70, 10, 8, 2), fr, g, 0, -2, Z0 - 38); mesh(rb(NX * CW + 70, 10, 8, 2), fr, g, 0, -2, Z0 + NY * CW + 30);
  // bars: dark lit sides (instanced boxes) + glowing front caps (instanced planes), one per cell
  const N = NX * NY, bx = new TH.BoxGeometry(CW - 4, 1, CW - 4); bx.translate(0, -0.5, 0);
  L.bars = new TH.InstancedMesh(bx, new TH.MeshStandardMaterial({ color: C('#ffffff'), roughness: 0.55, metalness: 0.1 }), N);
  const cp = new TH.PlaneGeometry(CW - 4, CW - 4); cp.rotateX(Math.PI / 2);
  L.caps = new TH.InstancedMesh(cp, new TH.MeshBasicMaterial({ color: C('#ffffff'), toneMapped: false }), N);
  for (const m of [L.bars, L.caps]) { m.frustumCulled = false; m.instanceMatrix.setUsage(TH.DynamicDrawUsage); m.setColorAt(0, C('#000')); g.add(m); }
  L.bars.castShadow = true;
  const M4 = new TH.Matrix4(), cc = new TH.Color();
  L.cell = (i, j) => [X0 + (i + 0.5) * CW, Z0 + (j + 0.5) * CW];
  // set(i, j, depth, hex, glow): one cell
  L.set = (i, j, d, hex, k) => {
    const n = i * NY + j, [x, z] = L.cell(i, j), dd = Math.max(0.5, d);
    M4.makeScale(1, dd, 1); M4.setPosition(x, 0, z); L.bars.setMatrixAt(n, M4);
    M4.makeTranslation(x, -dd - 0.3, z); L.caps.setMatrixAt(n, M4);
    cc.set(hex); L.bars.setColorAt(n, cc.clone().multiplyScalar(0.25 + 0.35 * Math.min(1, k)));
    L.caps.setColorAt(n, cc.multiplyScalar(k));
  };
  L.flush = () => { for (const m of [L.bars, L.caps]) { m.instanceMatrix.needsUpdate = true; m.instanceColor.needsUpdate = true; } };
  // the patch grid (4 × 4 cells), drawn as a transparent overlay in front of the bars
  const pg = ctex(1024, 820, (x, w, h) => {
    x.clearRect(0, 0, w, h); x.strokeStyle = 'rgba(255,176,112,0.9)'; x.lineWidth = 3;
    for (let i = 0; i <= NX / PATCH; i++) { x.beginPath(); x.moveTo(i * w / (NX / PATCH), 0); x.lineTo(i * w / (NX / PATCH), h); x.stroke(); }
    for (let j = 0; j <= NY / PATCH; j++) { x.beginPath(); x.moveTo(0, j * h / (NY / PATCH)); x.lineTo(w, j * h / (NY / PATCH)); x.stroke(); }
  });
  L.gridM = new TH.MeshBasicMaterial({ map: pg, transparent: true, opacity: 0, depthWrite: false, toneMapped: false });
  const gp = plane(g, NX * CW, NY * CW, L.gridM, 0, -75, Z0 + NY * CW / 2, '-y'); gp.renderOrder = 6;
  // the play head that sweeps across while the sound is mapped
  L.headM = new TH.MeshBasicMaterial({ color: C(O2), transparent: true, opacity: 0, depthWrite: false, toneMapped: false, blending: TH.AdditiveBlending });
  L.head = plane(g, 5, NY * CW + 40, L.headM, 0, -80, Z0 + NY * CW / 2, '-y');
  // the fingerprint strip above the wall: one tick per code, drawn on as the codes land
  L.fpz = Z0 + NY * CW + 95;
  const fpT = ctex(1024, 96, (x, w, h) => {
    x.fillStyle = '#120f0d'; x.fillRect(0, 0, w, h);
    for (let k = 0; k < 96; k++) { const xx = 14 + k * 10.5, hh = 20 + 56 * rnd(k, 77); x.fillStyle = rnd(k, 78) < 0.25 ? '#ffe9d2' : '#ff6a1f'; x.fillRect(xx, (h - hh) / 2, 5, hh); }
  });
  L.fpM = new TH.MeshBasicMaterial({ map: fpT, transparent: true, opacity: 0, toneMapped: false });
  L.fp = plane(g, NX * CW, 72, L.fpM, 0, -60, L.fpz, '-y'); L.fp.renderOrder = 6;
  L.fpBack = mesh(rb(NX * CW + 24, 14, 90, 4), mat('#1a1817', { r: 0.6 }), g, 0, -48, L.fpz - 45);
  mesh(rb(16, 10, L.fpz - 45 - (Z0 + NY * CW + 34), 2), mat('#2f2b28', { r: 0.4, m: 0.5 }), g, -NX * CW / 2 + 60, -40, Z0 + NY * CW + 34);
  mesh(rb(16, 10, L.fpz - 45 - (Z0 + NY * CW + 34), 2), mat('#2f2b28', { r: 0.4, m: 0.5 }), g, NX * CW / 2 - 60, -40, Z0 + NY * CW + 34);
  L.stars = starPool(PEAKS.length + NOISE.length + 4, 30);
  return L;
}

/* ------------------------------------------------------------------ DB: a hall of fingerprints + the match panel */
function buildDB() {
  const g = grp(scene, ...Z.DB), B = { g };
  mesh(cy(4200, 4200, 20, 96), mat('#121110', { r: 0.9 }), g, 0, 1500, -20);
  plane(g, 8000, 8000, texM(tilesTex('#151413', '#1d1b1a', 16), { r: 0.6 }), 0, 1500, 0.1);
  const T_ = ctex(1024, 512, (x, w, h) => {
    x.fillStyle = '#0e0c0b'; x.fillRect(0, 0, w, h);
    for (let r = 0; r < 16; r++) {
      x.fillStyle = '#1c1917'; x.fillRect(8, r * 32 + 6, w - 16, 22);
      for (let k = 0; k < 92; k++) { const v = rnd(r * 97 + k, 21); if (v < 0.35) continue; const hh = 6 + 12 * rnd(r * 97 + k, 22); x.fillStyle = v > 0.93 ? '#ffd2a8' : v > 0.6 ? '#ff6a1f' : '#7a3a1c'; x.fillRect(16 + k * 10.9, r * 32 + 17 - hh / 2, 4, hh); }
    }
  }, [3, 1]);
  const wm = new TH.MeshStandardMaterial({ map: T_, emissiveMap: T_, emissive: C('#ffffff'), emissiveIntensity: 0.9, roughness: 0.7 });
  B.walls = [];
  for (let r = 0; r < 6; r++) {
    const y = 300 + r * 520;
    mesh(rb(3600, 40, 420, 4), mat('#141312', { r: 0.7 }), g, 0, y + 22, 0);
    const p = plane(g, 3560, 400, wm, 0, y, 210, '-y'); B.walls.push(p);
  }
  // a scan bar running along the nearest walls
  B.scanM = new TH.MeshBasicMaterial({ color: C(O2), transparent: true, opacity: 0, blending: TH.AdditiveBlending, depthWrite: false, toneMapped: false });
  B.scan = [0, 1, 2].map((r) => plane(g, 14, 420, B.scanM, 0, 300 + r * 520 - 4, 210, '-y'));
  // the match panel standing in front: a song's stars (grey) three clips long; your clip's window slides along it
  const CS = 15, PW = NX * CS * 3, PH = NY * CS;
  B.cs = CS; B.pw = PW; B.ph = PH; B.py = -380; B.pz = 80;
  mesh(rb(PW + 50, 30, PH + 60, 6), mat('#161412', { r: 0.6 }), g, 0, B.py + 18, B.pz - 30);
  const fr = mat('#35302c', { r: 0.4, m: 0.5 });
  for (const zz of [B.pz - 34, B.pz + PH + 22]) mesh(rb(PW + 60, 8, 8, 2), fr, g, 0, B.py, zz);
  // the song's own stars: random either side, your clip's true peaks in the middle third
  B.song = [];
  for (let s = 0; s < 3; s++) {
    if (s === 1) PEAKS.forEach((p) => B.song.push({ i: p.i + NX, j: p.j, mine: true }));
    else for (let k = 0; k < PEAKS.length; k++) B.song.push({ i: s * NX + Math.floor(rnd(k + s * 99, 31) * NX), j: Math.floor(rnd(k + s * 99, 32) * NY), mine: false });
  }
  B.at = (i, j) => [-PW / 2 + (i + 0.5) * CS, B.py - 20, B.pz + (j + 0.5) * CS];
  B.stars = starPool(B.song.length + PEAKS.length + NOISE.length, 20);
  // the window frame (four thin glowing bars) that carries your clip's stars
  B.winM = new TH.MeshBasicMaterial({ color: C(O), transparent: true, opacity: 0, toneMapped: false });
  B.win = grp(g, 0, B.py - 26, B.pz);
  const WW = NX * CS;
  for (const [w, h, x, z] of [[WW + 8, 4, 0, -4], [WW + 8, 4, 0, PH], [4, PH + 8, -WW / 2 - 2, -4], [4, PH + 8, WW / 2 + 2, -4]]) { const m = new TH.Mesh(new TH.BoxGeometry(w, 3, h), B.winM); m.position.set(x, 0, z + h / 2); B.win.add(m); }
  return B;
}

/* ------------------------------------------------------------------ OLD: a pub in 2002 */
function buildPub() {
  const g = grp(scene, ...Z.OLD), P_ = { g }, W = 1000, D = 760, WH = 320;
  mesh(rb(W + 16, D + 16, 30), mat('#141312'), g, -8, 8, -30.2);
  plane(g, W, D, texM(planksTex(), { r: 0.75, c: '#a8968a' }), 0, 0, 0.05);
  const wall = mat('#2b2420', { r: 0.95 });
  mesh(rb(W + 16, 16, WH), wall, g, -8, D / 2 + 8, 0); mesh(rb(16, D, WH), wall, g, -W / 2 - 8, 0, 0);
  plane(g, W, 120, texM(planksTex(), { r: 0.8, c: '#6d5546' }), 0, D / 2 - 0.5, 60, '-y');
  // the bar: counter, taps, a shelf of bottles
  mesh(rb(520, 70, 108, 4), mat('#3a2a20', { r: 0.6 }), g, -120, D / 2 - 160, 0);
  mesh(rb(530, 80, 6, 2), mat('#5a4234', { r: 0.35 }), g, -120, D / 2 - 160, 108);
  for (let k = 0; k < 4; k++) mesh(cy(2.2, 2.2, 34, 8), pmat('#c9b48a', { r: 0.25, m: 1 }), g, -260 + k * 40, D / 2 - 170, 114);
  mesh(rb(500, 26, 4, 1), mat('#3a2a20'), g, -120, D / 2 - 14, 190);
  for (let k = 0; k < 18; k++) mesh(cy(4, 4, 26 + 10 * rnd(k, 5), 10), mat(['#3d5a3a', '#6a4a2a', '#2f3d4a', '#7a6a3a'][k % 4], { r: 0.2, op: 0.9 }), g, -350 + k * 26, D / 2 - 14, 194);
  // a chunky 2002 TV on a bracket and the pub speaker the phone is held up to
  mesh(rb(80, 60, 64, 6), mat('#2a2826', { r: 0.6 }), g, 300, D / 2 - 40, 210);
  plane(g, 62, 46, screenM(ctex(128, 96, (x, w, h) => { x.fillStyle = '#26323a'; x.fillRect(0, 0, w, h); x.fillStyle = '#4c6a3a'; x.fillRect(0, h * 0.6, w, h); x.fillStyle = '#e8e8e8'; x.fillRect(w * 0.45, h * 0.62, 6, 6); }), 0.7), 300, D / 2 - 71, 244, '-y');
  P_.spk = wallSpeaker(g, 40, D / 2 - 18, 210, 1.4);
  // tables
  for (const [x, y] of [[280, -120], [-260, -200]]) { roundTable(g, x, y); chair(g, x - 62, y, 0); chair(g, x + 62, y, Math.PI); }
  P_.mates = [person(g, 214, -120, 0, { seed: 9 }), person(g, 346, -120, Math.PI, { seed: 12, long: true })];
  P_.mates.forEach((m) => m.pose('sit'));
  P_.lamps = [];
  for (const [x, y] of [[280, -120], [-120, D / 2 - 160], [-260, -200]]) { const L = new TH.PointLight(C('#ffbf86'), 140, 520, 1.2); L.position.set(x, y, WH - 120); g.add(L); mesh(cy(4, 20, 18, 20), glowM('#ffcf9a', 1.1, '#2a2522'), g, x, y, WH - 110); P_.lamps.push(L); }
  // you, standing under the speaker, holding the old phone up to it
  P_.you = person(g, 40, D / 2 - 120, Math.PI / 2, { seed: 2, shirt: '#4a4f57', coat: true });
  P_.you.pose('stand');
  const hand = grp(P_.you.elR, 2, 0, -36), mini = oldPhone(hand, 1.4);
  mini.g.rotation.set(Math.PI, 0, Math.PI / 2);
  P_.mini = mini; P_.hand = hand;
  return P_;
}

/* ------------------------------------------------------------------ HUM: the twist */
function starPanel(par, x, y, w, h) {
  const g = grp(par, x, y);
  mesh(rb(w + 40, 30, h + 50, 6), mat('#161412', { r: 0.6 }), g, 0, 18, 0);
  const fr = mat('#35302c', { r: 0.4, m: 0.5 });
  for (const zz of [-4, h + 42]) mesh(rb(w + 50, 8, 8, 2), fr, g, 0, 0, zz);
  return g;
}
function buildHum() {
  const g = grp(scene, ...Z.HUM), H = { g }, CS = 16;
  mesh(cy(2600, 2600, 20, 96), mat('#121110', { r: 0.9 }), g, 0, 200, -20);
  H.cs = CS; H.w = NX * CS; H.h = NY * CS; H.z = 70;
  H.ax = -390; H.bx = 390;
  starPanel(g, H.ax, 0, H.w, H.h).position.z = H.z - 20;
  starPanel(g, H.bx, 0, H.w, H.h).position.z = H.z - 20;
  H.at = (px, i, j) => [Z.HUM[0] + px - H.w / 2 + (i + 0.5) * CS, Z.HUM[1] - 22, H.z + (j + 0.5) * CS];
  // a hummed tune: one smooth pitch line (the melody, roughly), no harmony, no drums, a few faint overtones
  H.hum = [];
  for (let i = 1; i < NX; i += 3) { const m = MEL[Math.floor(i / 4) % MEL.length]; H.hum.push({ i, j: Math.round(m * 0.62 + 2 + Math.sin(i * 0.7)) }); if (i % 6 === 1) H.hum.push({ i, j: Math.round(m * 0.62 + 2) + 9 }); }
  H.stars = starPool(PEAKS.length + H.hum.length + 4, 24);
  H.guy = person(g, H.bx + H.w / 2 + 130, -150, Math.PI, { seed: 5, shirt: '#5c5650' });
  H.guy.pose('stand');
  const L = new TH.PointLight(C('#ffd8b0'), 160, 1400, 1.0); L.position.set(0, -500, 600); g.add(L);
  return H;
}
