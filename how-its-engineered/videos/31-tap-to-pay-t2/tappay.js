// 31 Tap to pay: the pieces this reel adds to the AirTag kit. A card machine (keypad, printer hump, live screen with the
// four contactless lights), a bank card that comes apart into its layers to show the copper coil round its edge and the
// chip, the field loops a reader makes, a café counter, and a row of London Underground ticket gates with paddles.
// Zones: CAFE at 0,0, the hero STUDIO and DC (the bank) from scenes.js, TUBE to the east. Load after scenes.js.
Z.CAFE = [0, 0]; Z.TUBE = [40000, 0];
const CU = '#d9894a';   // copper

/* ------------------------------------------------------------------ the card machine */
// k = scale (1 = real size, cm). Long axis along y: keypad nearest the camera (-y), screen beyond it, printer at +y.
// Its top face is at z = 4.6k; screen centre at TM.scr (local).
function terminal3(par, x, y, k, rz = 0) {
  const g = grp(par, x, y, 0, rz), W = 7.8 * k, L = 17 * k, H = 3.4 * k;
  const shell = pmat('#1d1b1a', { r: 0.42, cc: 0.4, env: 0.7 }), dark = pmat('#0c0b0b', { r: 0.3, env: 0.5 });
  mesh(slab(W, L, H, 1.4 * k, 0.5 * k), shell, g, 0, 0, H / 2 + 0.6 * k);
  mesh(rb(W * 0.94, L * 0.94, 0.6 * k, 0.4 * k), dark, g, 0, 0, 0);               // rubber foot
  mesh(slab(W * 0.98, 4.4 * k, 1.6 * k, 1.2 * k, 0.5 * k), shell, g, 0, L / 2 - 2.6 * k, H + 0.8 * k);   // printer hump
  mesh(rb(W * 0.7, 0.25 * k, 0.12 * k, 0.05 * k), dark, g, 0, L / 2 - 0.6 * k, H + 1.4 * k, { cast: false }); // paper slot
  // the screen (glass inset) on the top, beyond the keypad
  const sw = W * 0.82, sh = 6.0 * k, sy = 1.6 * k, top = H + 0.62 * k;
  mesh(rrg(sw + 0.5 * k, sh + 0.5 * k, 0.5 * k), pmat('#040404', { r: 0.05, cc: 1, env: 1.2 }), g, 0, sy, top, { cast: false });
  const s = scr(sw, sh, 600 / sw, g, 1.05, 0.35 * k); s.m.position.set(0, sy, top + 0.03 * k);
  // keypad: 4 × 3 keys and the red / yellow / green row
  const key = pmat('#2c2a28', { r: 0.5, env: 0.5 }), keys = [];
  for (let r = 0; r < 4; r++) for (let c = 0; c < 3; c++) keys.push(mesh(rbc(1.7 * k, 0.95 * k, 0.35 * k, 0.25 * k), key, g, (c - 1) * 2.1 * k, -2.2 * k - r * 1.25 * k, top + 0.15 * k));
  ['#b8323a', '#c99b2c', '#3d8a52'].forEach((col, c) => mesh(rbc(1.7 * k, 0.95 * k, 0.35 * k, 0.25 * k), pmat(col, { r: 0.4, env: 0.5 }), g, (c - 1) * 2.1 * k, -7.2 * k, top + 0.15 * k));
  const glyph = ctex(256, 256, (x, w) => { x.fillStyle = '#000'; x.fillRect(0, 0, w, w); x.fillStyle = '#9e9995'; x.font = '700 120px Inter'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText('·', w / 2, w / 2); });
  void glyph;
  // the reader's antenna: a faint ring under the screen glass (lights when the field is on)
  const ant = new TH.Mesh(tor(2.2 * k, 0.05 * k, 64), new TH.MeshBasicMaterial({ color: C(O), transparent: true, opacity: 0, toneMapped: false, depthWrite: false, blending: TH.AdditiveBlending }));
  ant.position.set(0, sy, top + 0.06 * k); g.add(ant);
  return { g, s, k, top, scr: [0, sy, top], ant, W, L, keys };
}

/* ------------------------------------------------------------------ the bank card */
// A card lying flat, long side along x, face up. Three layers: back, the inlay (copper coil + chip), the printed front.
// explode(e): the layers part and the front turns see-through. Coil points (local) in C.coil, chip at C.chip.
function cardFace(w, h) {
  return ctex(1024, Math.round(1024 * h / w), (x, W, H) => {
    const gr = x.createLinearGradient(0, 0, W, H); gr.addColorStop(0, '#2b2622'); gr.addColorStop(0.55, '#1a1715'); gr.addColorStop(1, '#100e0d'); x.fillStyle = gr; x.fillRect(0, 0, W, H);
    const r = x.createRadialGradient(W * 0.86, H * 0.12, 10, W * 0.86, H * 0.12, W * 0.6); r.addColorStop(0, 'rgba(255,106,31,0.5)'); r.addColorStop(1, 'rgba(255,106,31,0)'); x.fillStyle = r; x.fillRect(0, 0, W, H);
    x.strokeStyle = 'rgba(255,176,112,0.12)'; x.lineWidth = 3; for (let i = 0; i < 7; i++) { x.beginPath(); x.arc(W * 1.05, H * 1.2, W * (0.35 + i * 0.07), Math.PI, Math.PI * 1.5); x.stroke(); }
    // chip contacts (gold)
    const cx = W * 0.175, cy_ = H * 0.46, cw = W * 0.13, ch = H * 0.2;
    const gg = x.createLinearGradient(cx - cw / 2, cy_ - ch / 2, cx + cw / 2, cy_ + ch / 2); gg.addColorStop(0, '#e9cf8a'); gg.addColorStop(0.5, '#b8924a'); gg.addColorStop(1, '#e0c27a');
    x.fillStyle = gg; x.beginPath(); x.roundRect(cx - cw / 2, cy_ - ch / 2, cw, ch, 14); x.fill();
    x.strokeStyle = 'rgba(80,58,24,0.75)'; x.lineWidth = 3; x.beginPath();
    x.moveTo(cx - cw / 2, cy_); x.lineTo(cx - cw * 0.12, cy_); x.moveTo(cx + cw * 0.12, cy_); x.lineTo(cx + cw / 2, cy_);
    x.moveTo(cx - cw * 0.12, cy_ - ch / 2); x.lineTo(cx - cw * 0.12, cy_ + ch / 2); x.moveTo(cx + cw * 0.12, cy_ - ch / 2); x.lineTo(cx + cw * 0.12, cy_ + ch / 2);
    x.moveTo(cx - cw / 2, cy_ - ch * 0.2); x.lineTo(cx - cw * 0.12, cy_ - ch * 0.2); x.moveTo(cx + cw * 0.12, cy_ + ch * 0.2); x.lineTo(cx + cw / 2, cy_ + ch * 0.2); x.stroke();
    // contactless mark
    x.strokeStyle = '#e8e2dd'; x.lineWidth = 9; x.lineCap = 'round';
    for (let i = 0; i < 4; i++) { x.beginPath(); x.arc(W * 0.3 + i * 22, H * 0.46, 22 + i * 22, -0.75, 0.75); x.stroke(); }
    x.fillStyle = '#e8e2dd'; x.font = '600 58px Mono'; x.textBaseline = 'alphabetic';
    x.fillText('••••  ••••  ••••  4821', W * 0.08, H * 0.78);
    x.fillStyle = '#a39e99'; x.font = '600 30px Mono'; x.fillText('VALID THRU 09/29', W * 0.08, H * 0.9);
    x.fillStyle = '#f4f3f2'; x.font = '800 54px Inter'; x.textAlign = 'right'; x.fillText('debit', W * 0.93, H * 0.9);
  });
}
function card3(par, k) {
  const g = grp(par), w = 8.56 * k, h = 5.4 * k, th = 0.08 * k, r = 0.32 * k, C_ = { g, k, w, h };
  const back = grp(g), inlay = grp(g), front = grp(g);
  mesh(rbc(w, h, th, r, 3), pmat('#151312', { r: 0.4, cc: 0.5, env: 0.6 }), back);
  const stripe = mesh(rbc(w, 1.0 * k, th * 0.3, 0.05 * k), mat('#0a0909', { r: 0.3 }), back, 0, h / 2 - 1.1 * k, -th * 0.55, { cast: false });
  void stripe;
  // inlay: a pale sheet you can see the coil through
  C_.sheetM = new TH.MeshPhysicalMaterial({ color: C('#d8d0c8'), roughness: 0.5, transparent: true, opacity: 0.16, depthWrite: false, side: TH.DoubleSide, envMap: STUDIO_ENV, envMapIntensity: 0.6 });
  mesh(rbc(w * 0.995, h * 0.995, th * 0.3, r, 3), C_.sheetM, inlay, 0, 0, 0, { cast: false });
  // the coil: four turns just inside the edge, its inner end running to the chip
  const pts = [], turns = 4, in0 = 0.32 * k, step = 0.17 * k, z = th * 0.4;
  for (let i = 0; i < turns; i++) {
    const d = in0 + i * step, x0 = -w / 2 + d, x1 = w / 2 - d, y0 = -h / 2 + d, y1 = h / 2 - d;
    pts.push([x0, y1 - (i ? 0 : 0), z], [x1, y1, z], [x1, y0, z], [x0, y0, z], [x0, y1 - step, z]);
  }
  const chip = [-w / 2 + 0.175 * w, h / 2 - 0.46 * h, z];
  pts.push([chip[0] - 0.5 * k, pts[pts.length - 1][1], z], [chip[0] - 0.5 * k, chip[1], z], [chip[0], chip[1], z]);
  C_.coil = pts; C_.chip = chip;
  const lg = new TH.LineGeometry(); lg.setPositions(pts.flat());
  C_.coilCore = new TH.Line2(lg, lineMat(CU, 2.2)); C_.coilHalo = new TH.Line2(lg, lineMat(O, 12, { add: true, op: 0 }));
  for (const l of [C_.coilCore, C_.coilHalo]) { l.frustumCulled = false; inlay.add(l); }
  C_.coilHalo.renderOrder = 4;
  // chip module: a gold pad and the tiny silicon die under it (glows when awake)
  mesh(rbc(1.1 * k, 0.95 * k, th * 0.5, 0.12 * k), pmat('#c9a45a', { r: 0.25, m: 1, env: 1.2 }), inlay, chip[0], chip[1], z);
  C_.dieM = glowM(O, 0, '#151313');
  mesh(rbc(0.42 * k, 0.42 * k, th * 1.2, 0.05 * k), C_.dieM, inlay, chip[0], chip[1], z + th * 0.5);
  // the printed front
  C_.faceM = new TH.MeshPhysicalMaterial({ map: cardFace(w, h), roughness: 0.35, clearcoat: 0.6, clearcoatRoughness: 0.12, envMap: STUDIO_ENV, envMapIntensity: 0.7, transparent: true });
  C_.faceM.map.colorSpace = TH.SRGBColorSpace;
  C_.edgeM = new TH.MeshPhysicalMaterial({ color: C('#1a1716'), roughness: 0.4, envMap: STUDIO_ENV, envMapIntensity: 0.6, transparent: true });
  mesh(rbc(w, h, th, r, 3), C_.edgeM, front);
  C_.face = new TH.Mesh(rrg(w * 0.996, h * 0.996, r), C_.faceM); C_.face.position.z = th / 2 + 0.01 * k; front.add(C_.face);
  C_.layers = { back, inlay, front };
  C_.explode = (e, see = e) => {
    back.position.z = -th - e * 2.2 * k; front.position.z = th + e * 2.4 * k; inlay.position.z = 0;
    const op = 1 - 0.82 * see; C_.faceM.opacity = op; C_.edgeM.opacity = op; C_.faceM.depthWrite = C_.edgeM.depthWrite = op > 0.98;
  };
  // power: 0..1 lights the coil; awake: 0..1 lights the die
  C_.power = (p, awake) => { C_.coilHalo.material.opacity = 0.75 * p; C_.coilCore.material.color.set(mixHex(CU, '#ffd2b0', p)); C_.dieM.emissiveIntensity = 3.5 * awake; };
  C_.explode(0); C_.power(0, 0);
  C_.at = (p) => { g.updateMatrixWorld(true); const v = new TH.Vector3(...p); inlay.localToWorld(v); return [v.x, v.y, v.z]; };
  return C_;
}

/* ------------------------------------------------------------------ field loops */
// Field lines over a reader: arches that rise out of the centre and fall back outside it, in 8 directions, two sizes.
// They flow (dashes) one way, then the other: the field keeps changing.
function fieldLoops(cx, cy_, cz, R, Hh) {
  const F = { lines: [] };
  for (let a = 0; a < 8; a++) for (const rk of [0.55, 1]) {
    const ang = (a / 8) * Math.PI * 2 + (rk < 1 ? Math.PI / 8 : 0), pts = [];
    for (let i = 0; i <= 28; i++) { const th = Math.PI * (1 - i / 28), r0 = R * rk / 2; const u = r0 + r0 * Math.cos(th), zz = Hh * rk * Math.sin(th); pts.push(cx + Math.cos(ang) * u, cy_ + Math.sin(ang) * u, cz + zz); }
    const lg = new TH.LineGeometry(); lg.setPositions(pts);
    const core = new TH.Line2(lg, lineMat(O, 2.4, { dashed: true, dash: 7, gap: 7 })), halo = new TH.Line2(lg, lineMat(O, 9, { add: true, op: 0.1 }));
    for (const l of [core, halo]) { l.computeLineDistances(); l.frustumCulled = false; l.visible = false; scene.add(l); }
    core.renderOrder = 5; halo.renderOrder = 4; F.lines.push({ core, halo });
  }
  // a: strength 0..1; ph: field phase (radians); flips direction and colour each half cycle
  F.set = (t, a, ph) => {
    const s = Math.sin(ph), dir = s >= 0 ? 1 : -1, k = a * (0.35 + 0.65 * Math.abs(s)), col = s >= 0 ? O : AMB;
    for (const L of F.lines) {
      L.core.visible = L.halo.visible = a > 0.01; if (!L.core.visible) continue;
      L.core.material.color.set(col); L.halo.material.color.set(col);
      L.core.material.opacity = k; L.halo.material.opacity = 0.16 * k; L.core.material.dashOffset = -dir * t * 40;
    }
    return { k, s };
  };
  return F;
}

/* ------------------------------------------------------------------ STUDIO: the hero machine and card on a plinth */
function buildTapStudio() {
  const g = grp(scene, ...Z.STU), S = { g };
  mesh(cy(2800, 2800, 20, 96), mat('#161514', { r: 0.9 }), g, 0, 0, -20);
  const fl = ctex(1024, 1024, (x, w, h) => { x.fillStyle = '#000'; x.fillRect(0, 0, w, h); x.strokeStyle = 'rgba(206,186,169,0.05)'; x.lineWidth = 2; for (let i = 0; i <= 32; i++) { x.beginPath(); x.moveTo(i * 32, 0); x.lineTo(i * 32, h); x.moveTo(0, i * 32); x.lineTo(w, i * 32); x.stroke(); } });
  plane(g, 5600, 5600, new TH.MeshBasicMaterial({ map: fl, transparent: true, blending: TH.AdditiveBlending, depthWrite: false, toneMapped: false }), 0, 0, 0.2);
  mesh(cy(150, 160, 64, 64), mat('#22201e', { r: 0.55, m: 0.2 }), g);
  mesh(cy(144, 144, 2, 64), mat('#2c2927', { r: 0.4, m: 0.3 }), g, 0, 0, 64);
  S.rimM = glowM(O, 1.0); mesh(tor(151, 0.8, 96), S.rimM, g, 0, 0, 64, { cast: false });
  S.under = glowSpot(g, 0, 0, 0.5, 360, O, 0.05);
  S.term = terminal3(g, 0, 0, 7.5); S.term.g.position.z = 66;
  const ts = S.term.scr; S.scrW = wz('STU', ts[0], ts[1], 66 + ts[2]);
  S.card = card3(scene, 7.5);
  S.field = fieldLoops(S.scrW[0], S.scrW[1], S.scrW[2] + 1, 150, 120);
  S.cardL = new TH.PointLight(C(O), 0, 260, 1.4); scene.add(S.cardL);
  return S;
}

/* ------------------------------------------------------------------ CAFE: a counter, a barista, you tapping */
function buildCafe() {
  const g = grp(scene, ...Z.CAFE), F = { g };
  mesh(rb(1400, 1000, 30), mat('#171615'), g, 0, 150, -30.2);
  plane(g, 1400, 1000, texM(planksTex(), { r: 0.75 }), 0, 150, 0.05);
  const wall = mat('#2b2826', { r: 0.95 });
  mesh(rb(1400, 16, 320), wall, g, 0, 658, 0); mesh(rb(16, 1000, 320), wall, g, -708, 150, 0);
  // menu board on the back wall
  const menu = ctex(640, 300, (x, w, h) => {
    x.fillStyle = '#141312'; x.fillRect(0, 0, w, h); x.strokeStyle = '#3a3633'; x.lineWidth = 6; x.strokeRect(8, 8, w - 16, h - 16);
    x.fillStyle = '#ffb070'; x.font = '800 34px Inter'; x.fillText('COFFEE', 34, 58);
    [['Flat white', '3.60'], ['Latte', '3.80'], ['Cappuccino', '3.70'], ['Croissant', '2.40'], ['Banana bread', '3.10']].forEach(([a, b], i) => { x.fillStyle = '#d3cfcb'; x.font = '600 26px Inter'; x.fillText(a, 34, 104 + i * 38); x.textAlign = 'right'; x.fillText('£' + b, w - 34, 104 + i * 38); x.textAlign = 'left'; });
  });
  plane(g, 320, 150, screenM(menu, 0.75), 120, 649, 215, '-y');
  // counter
  const wood = mat('#3d3834', { r: 0.6 }), front = mat('#232120', { r: 0.85 });
  mesh(rb(420, 70, 100, 3), front, g, 0, 60, 0);
  for (let i = 0; i < 9; i++) mesh(rb(2, 2, 96), mat('#1a1918'), g, -200 + i * 50, 24.5, 2, { cast: false });
  mesh(rb(432, 80, 5, 1.5), wood, g, 0, 60, 100);
  // espresso machine
  const steel = pmat('#9c9894', { r: 0.25, m: 1, env: 0.9 }), blk = mat('#121110', { r: 0.4 });
  mesh(rb(80, 50, 46, 4), steel, g, -140, 72, 105); mesh(rb(76, 46, 6, 2), blk, g, -140, 72, 151);
  for (const dx of [-20, 20]) { mesh(cy(4, 4, 10, 12), blk, g, -140 + dx, 46, 128); mesh(cy(4.5, 3.5, 7, 14), mat('#e9e3dd', { r: 0.4 }), g, -140 + dx, 46, 105); }
  for (let i = 0; i < 4; i++) mesh(cy(4.5, 3.5, 8, 14), mat('#e9e3dd', { r: 0.4 }), g, -140 + i * 10 - 15, 76, 157);
  // pastry case
  mesh(rb(90, 46, 6, 2), blk, g, 140, 72, 105);
  const glass = new TH.MeshPhysicalMaterial({ color: C('#bfc5c4'), roughness: 0.05, transparent: true, opacity: 0.18, depthWrite: false, envMap: STUDIO_ENV, envMapIntensity: 1 });
  mesh(rb(90, 46, 36, 2), glass, g, 140, 72, 111, { cast: false });
  for (let i = 0; i < 4; i++) mesh(gk('crois', () => new TH.CapsuleGeometry(4, 9, 3, 8).rotateZ(Math.PI / 2)), mat('#b9844e', { r: 0.7 }), g, 116 + i * 16, 72, 117);
  // pendant lamps
  F.lamps = [];
  for (const lx of [-160, 0, 160]) {
    mesh(cy(0.6, 0.6, 120, 6), blk, g, lx, 60, 230);
    mesh(cy(6, 20, 20, 24), mat('#2a2725', { r: 0.5 }), g, lx, 60, 212);
    mesh(cy(14, 14, 1, 24), glowM('#ffd9b8', 3), g, lx, 60, 211.5, { cast: false });
    const L = new TH.PointLight(C('#ffcfa6'), 900, 520, 1.3); L.position.set(lx, 60, 200); g.add(L); F.lamps.push(L);
  }
  plant(g, -480, 560, 1.5); plant(g, 520, 520, 1.2);
  // the card machine on the counter, the barista behind it, you in front
  F.term = terminal3(g, 34, 46, 1, 0.25); F.term.g.position.z = 105;
  F.barista = person(g, 60, 128, -Math.PI / 2, { seed: 4, shirt: '#3f3b38', coat: false }); F.barista.pose('talk');
  F.you = person(g, -6, -40, Math.PI / 2 - 0.25, { seed: 2, shirt: '#6f6863', coat: true });
  F.you.pose('stand');
  F.card = mesh(rbc(5.4, 8.56, 0.3, 0.3), pmat('#2b2622', { r: 0.35, cc: 0.5, env: 0.7 }), F.you.elR, 2, 0, -33);
  F.card.rotation.set(0, Math.PI / 2 - 0.1, 0);
  F.cardEdge = glowM(O, 0); mesh(rbc(5.6, 8.7, 0.12, 0.3), F.cardEdge, F.card, 0, 0, 0.2, { cast: false });
  F.queue = person(g, -150, -120, Math.PI / 2 + 0.2, { seed: 9, phone: true }); F.queue.pose('phone');
  const ts = F.term.scr; F.scrW = [ts[0], ts[1], 105 + ts[2]];
  F.term.g.updateMatrixWorld(true); { const v = new TH.Vector3(...ts); F.term.g.localToWorld(v); F.scrW = [v.x, v.y, v.z]; }
  return F;
}
// your arm reaching out over the machine: r = 0 (by your side) .. 1 (card held over the screen); dip = 0..1
function reach(P_, r, dip = 0) {
  P_.pose('stand');
  P_.shR.rotation.y = lerp(0, -0.95, r) - 0.12 * dip; P_.elR.rotation.y = lerp(-0.1, -0.62, r) + 0.18 * dip; P_.head.rotation.y = 0.25 * r;
}

/* ------------------------------------------------------------------ TUBE: a row of ticket gates */
function buildTube() {
  const g = grp(scene, ...Z.TUBE), T_ = { g, lanes: [-90, 0, 90], gates: [] };
  mesh(rb(2400, 1400, 30), mat('#141312'), g, 0, 100, -30.2);
  plane(g, 2400, 1400, texM(tilesTex('#2a2725', '#1a1817', 8), { r: 0.55, m: 0.1 }), 0, 100, 0.05);
  const wallT = tilesTex('#3a3633', '#262321', 12);
  const wallM = texM(wallT, { r: 0.5, m: 0.05 });
  mesh(rb(2400, 16, 380), wallM, g, 0, 420, 0);
  // the roundel and a way-out sign on the wall
  const rnd_ = ctex(512, 512, (x, w) => {
    x.fillStyle = 'rgba(0,0,0,0)'; x.clearRect(0, 0, w, w);
    x.strokeStyle = '#d9333f'; x.lineWidth = 64; x.beginPath(); x.arc(w / 2, w / 2, 170, 0, 7); x.stroke();
    x.fillStyle = '#1e3a8a'; x.fillRect(20, w / 2 - 44, w - 40, 88);
    x.fillStyle = '#fff'; x.font = '800 54px Inter'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText('UNDERGROUND', w / 2, w / 2 + 3);
  });
  const rm = new TH.MeshBasicMaterial({ map: rnd_, transparent: true, toneMapped: false }); rm.color.setScalar(0.85);
  plane(g, 170, 170, rm, -260, 410, 250, '-y');
  const way = ctex(512, 128, (x, w, h) => { x.fillStyle = '#f2c230'; x.fillRect(0, 0, w, h); x.fillStyle = '#111'; x.font = '800 64px Inter'; x.textBaseline = 'middle'; x.fillText('Way out  →', 34, h / 2 + 2); });
  plane(g, 200, 50, screenM(way, 0.8), 260, 410, 300, '-y');
  // gate cabinets (long along x), with a yellow reader at the entry end and a pair of paddles in each lane
  const body = pmat('#26292b', { r: 0.4, m: 0.6, env: 0.5 }), topM = pmat('#3a3d3f', { r: 0.35, m: 0.7, env: 0.6 });
  T_.readerM = [];
  for (const cyy of [-135, -45, 45, 135]) {
    mesh(rb(150, 26, 96, 4), body, g, 0, cyy, 0);
    mesh(rb(152, 28, 4, 2), topM, g, 0, cyy, 96);
    const rm_ = glowM('#f2c230', 0.6, '#3a3016'); T_.readerM.push(rm_);
    mesh(cy(9, 9, 1.6, 32), rm_, g, -48, cyy, 100);
    mesh(rbc(10, 8, 0.4, 1), glowM(O, 1.2), g, -26, cyy, 100.4, { cast: false });
    // the arrow / cross light on the entry face
    mesh(rbc(0.6, 10, 8, 1), glowM('#f4f3f2', 0.8), g, -75.4, cyy, 80, { cast: false });
  }
  const glassM = new TH.MeshPhysicalMaterial({ color: C('#e06a5f'), roughness: 0.15, transparent: true, opacity: 0.5, depthWrite: false, envMap: STUDIO_ENV, envMapIntensity: 0.8 });
  const edgeM = glowM(RED, 0.8);
  T_.lanes.forEach((ly, li) => {
    const gate = { y: ly, paddles: [] };
    for (const side of [-1, 1]) {
      const piv = grp(g, 20, ly + side * 32, 34);
      mesh(rb(3, 30, 52, 2), glassM, piv, 0, -side * 15, 0, { cast: false });
      mesh(rb(3.4, 1.2, 52, 0.5), edgeM, piv, 0, -side * 30, 0, { cast: false });
      gate.paddles.push({ piv, side });
    }
    gate.reader = wz('TUBE', -48, ly - 45, 101.6);
    gate.open = (o) => gate.paddles.forEach((p) => { p.piv.rotation.z = p.side * o * Math.PI / 2 * 0.98; });
    gate.open(0); T_.gates.push(gate);
  });
  T_.readerAt = (li) => T_.gates[li].reader;
  // commuters: each carries a card in the right hand
  T_.ppl = [];
  const mk = (seed, o = {}) => {
    const p = person(g, 0, 0, 0, { seed, coat: seed % 2 === 0, ...o });
    p.card = mesh(rbc(5.4, 8.56, 0.3, 0.3), pmat('#2b2622', { r: 0.35, env: 0.6 }), p.elR, 2, 0, -33); p.card.rotation.set(0, Math.PI / 2, 0);
    return p;
  };
  T_.hero = mk(2, { shirt: '#6f6863', coat: true });
  // phases chosen so nobody walks right beside the hero commuter while they tap
  [[0, 3, 0], [1, 5, 0.37], [2, 7, 1.24], [0, 8, 1.11], [2, 10, 1.48], [1, 12, 1.85], [0, 13, 2.22]].forEach(([li, s, ph], k) => T_.ppl.push({ li, p: mk(s), ph, v: 125 + 15 * rnd(k, 3) }));
  T_.lamp = new TH.PointLight(C('#ffe2c8'), 2600, 1600, 1.2); T_.lamp.position.set(...wz('TUBE', 0, -100, 420)); scene.add(T_.lamp);
  return T_;
}
// a commuter's pose at gate-relative x: walking, tapping the card on the reader as they pass it
function commuterPose(P_, x, tapK) {
  P_.pose('walk', x / 140 * Math.PI * 2);
  if (tapK > 0) { P_.shR.rotation.y = lerp(P_.shR.rotation.y, -0.85, tapK); P_.elR.rotation.y = lerp(P_.elR.rotation.y, -0.75, tapK); }
}
