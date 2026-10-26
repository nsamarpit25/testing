// The zones of 29 AirTag, built from kit.js props. Origins are far apart so each shot only sees its own diorama:
// CITY at 0,0 (the bus stop with the lost bag, the stranger, the apartment complex, a few thousand glowing phones),
// HOME, STUDIO (hero AirTag and hero phones) and DC (Find My racks) to the west, AIRPORT to the east.
// Units are centimetres, z up. Load after kit.js.
const Z = { HOME: [-40000, 0], STU: [-40000, 10000], DC: [-40000, -10000], AIR: [40000, 0] };
const wz = (zn, x = 0, y = 0, z = 0) => [Z[zn][0] + x, Z[zn][1] + y, z];
const wpos = (o) => { const v = new TH.Vector3(); o.getWorldPosition(v); return [v.x, v.y, v.z]; };

/* ------------------------------------------------------------------ canvases */
function planksTex() {
  return ctex(512, 512, (g, w, h) => {
    g.fillStyle = '#171615'; g.fillRect(0, 0, w, h);
    for (let r = 0; r < 8; r++) {
      let x = -rnd(r, 3) * 200;
      for (let k = 0; x < w; k++) {
        const len = 150 + rnd(r * 9 + k, 4) * 180;
        g.fillStyle = mixHex('#2b2825', rnd(r * 9 + k, 5) < 0.5 ? '#36322f' : '#1f1d1b', rnd(r * 9 + k, 6) * 0.9);
        g.fillRect(x + 1.5, r * 64 + 1.5, len - 3, 61);
        g.fillStyle = 'rgba(8,6,4,0.12)'; g.fillRect(x + 1.5, r * 64 + 40, len - 3, 3);
        x += len;
      }
    }
  }, [2, 2]);
}
function tilesTex(base, line, n = 8, glow) {
  return ctex(512, 512, (g, w, h) => {
    g.fillStyle = base; g.fillRect(0, 0, w, h);
    const s = w / n;
    for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) { g.fillStyle = mixHex(base, '#030404', rnd(i * n + j, 2) * 0.18); g.fillRect(i * s + 1, j * s + 1, s - 2, s - 2); }
    g.strokeStyle = line; g.lineWidth = 2;
    for (let i = 0; i <= n; i++) { g.beginPath(); g.moveTo(i * s, 0); g.lineTo(i * s, h); g.moveTo(0, i * s); g.lineTo(w, i * s); g.stroke(); }
    if (glow) for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) if (rnd(i * n + j, 7) < 0.15) { g.fillStyle = glow; for (let k = 0; k < 4; k++) g.fillRect(i * s + 8 + k * 10, j * s + s / 2, 5, 5); }
  }, [3, 3]);
}
// night skyline seen through a window
function skylineTex(w = 512, h = 340) {
  return ctex(w, h, (g) => {
    const gr = g.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, '#100f0e'); gr.addColorStop(0.7, '#221f1d'); gr.addColorStop(1, '#322c28');
    g.fillStyle = gr; g.fillRect(0, 0, w, h);
    let x = 0;
    for (let k = 0; x < w; k++) {
      const bw = 40 + rnd(k, 1) * 70, bh = h * (0.25 + rnd(k, 2) * 0.55);
      g.fillStyle = '#0f0e0d'; g.fillRect(x, h - bh, bw, bh);
      for (let yy = h - bh + 10; yy < h - 8; yy += 14) for (let xx = x + 6; xx < x + bw - 6; xx += 11) if (rnd(xx * 3 + yy, k) < 0.14) { g.fillStyle = rnd(xx + yy, 9) < 0.5 ? '#9b9087' : '#d5cec8'; g.fillRect(xx, yy, 4, 6); }
      x += bw + 4;
    }
  });
}

/* ------------------------------------------------------------------ HOME: a living-room cutaway */
function buildHome() {
  const g = grp(scene, ...Z.HOME), W = 760, D = 640, WH = 290, TW = 16, H = { g };
  const wall = mat('#2b2826', { r: 0.95 }), trim = mat('#1d1c1b', { r: 0.8 }), wood = mat('#373431', { r: 0.7 });
  mesh(rb(W + TW, D + TW, 30), mat('#171615'), g, -TW / 2, TW / 2, -30.2);
  plane(g, W, D, texM(planksTex(), { r: 0.75 }), 0, 0, 0.05);
  // walls: left (-x) and back (+y) with a window
  mesh(rb(TW, D + TW, WH), wall, g, -W / 2 - TW / 2, TW / 2, 0);
  const by = D / 2 + TW / 2, wx0 = 30, wx1 = 270, wz0 = 95, wz1 = 240;
  mesh(rb(wx0 + W / 2 + TW, TW, WH), wall, g, (wx0 - W / 2 - TW) / 2, by, 0);
  mesh(rb(W / 2 - wx1, TW, WH), wall, g, (wx1 + W / 2) / 2, by, 0);
  mesh(rb(wx1 - wx0, TW, wz0), wall, g, (wx0 + wx1) / 2, by, 0);
  mesh(rb(wx1 - wx0, TW, WH - wz1), wall, g, (wx0 + wx1) / 2, by, wz1);
  plane(g, wx1 - wx0, wz1 - wz0, screenM(skylineTex(), 0.9), (wx0 + wx1) / 2, by + 4, (wz0 + wz1) / 2, '-y');
  for (const [w, h, x, z] of [[wx1 - wx0 + 12, 6, (wx0 + wx1) / 2, wz0 - 6], [wx1 - wx0 + 12, 6, (wx0 + wx1) / 2, wz1], [6, wz1 - wz0, wx0 - 3, wz0], [6, wz1 - wz0, wx1 - 3, wz0], [4, wz1 - wz0, (wx0 + wx1) / 2 - 2, wz0]])
    mesh(rb(w, 10, h), trim, g, x, by - 6, z);
  mesh(rb(wx1 - wx0 + 20, 22, 4), trim, g, (wx0 + wx1) / 2, by - 12, wz0 - 4);
  H.window = [(wx0 + wx1) / 2, by, (wz0 + wz1) / 2];
  // skirting
  mesh(rb(W, 3, 10), trim, g, 0, D / 2 - 1.5, 0); mesh(rb(3, D, 10), trim, g, -W / 2 + 1.5, 0, 0);
  // rug, sofa, table
  const rugT = ctex(256, 192, (x, w, h) => { x.fillStyle = '#2e2c2a'; x.fillRect(0, 0, w, h); x.strokeStyle = '#524c48'; x.lineWidth = 5; x.strokeRect(14, 14, w - 28, h - 28); x.strokeStyle = '#3e3a37'; x.lineWidth = 2; x.strokeRect(26, 26, w - 52, h - 52); });
  mesh(rb(330, 240, 1.4, 0.6), texM(rugT, { r: 1 }), g, -40, 70, 0.1, { cast: false });
  sofa(g, -60, 238, 0, '#3b3835');
  table(g, -50, 80, 130, 64, 40, '#383532');
  mesh(cy(4.5, 4, 10, 14), mat('#d0cecc', { r: 0.4 }), g, -80, 75, 40);
  mesh(rb(26, 18, 3, 1), mat('#625c58'), g, -25, 90, 40, { rz: 0.2 });
  H.lamp = floorLamp(g, -310, 262); H.lamp.L.intensity = 130; H.lamp.L.distance = 1100;
  plant(g, 320, 250, 1.35); plant(g, -330, -250, 1.0);
  // bookshelf on the left wall
  const sx = -W / 2 + 19, syc = -150, shf = mat('#2e2b29', { r: 0.8 });
  mesh(rb(36, 4, 190), shf, g, sx, syc - 83, 0); mesh(rb(36, 4, 190), shf, g, sx, syc + 83, 0); mesh(rb(3, 170, 190), shf, g, -W / 2 + 1.5, syc, 0);
  const BK = ['#47413d', '#44413f', '#5b544f', '#3b3836', '#625c58', '#484542', '#77706b', '#5f5a56'];
  for (let s = 0; s < 4; s++) {
    const z = s * 47; mesh(rb(36, 170, 3), shf, g, sx, syc, z);
    for (let yy = syc - 78, k = 0; yy < syc + 70; k++) {
      const bw = 4 + rnd(s * 40 + k, 1) * 4, bh = 26 + rnd(s * 40 + k, 2) * 14;
      if (rnd(s * 40 + k, 3) < 0.12) { yy += 10; continue; }
      mesh(rb(24, bw, bh, 0.5), mat(BK[Math.floor(rnd(s * 40 + k, 4) * BK.length)], { r: 0.85 }), g, sx + 2, yy + bw / 2, z + 3);
      yy += bw + 0.6;
    }
  }
  mesh(rb(36, 170, 3), shf, g, sx, syc, 187);
  // media console + TV on the left wall
  mesh(rb(46, 190, 48, 3), mat('#2b2826', { r: 0.7 }), g, -W / 2 + 23, 80, 0);
  mesh(rb(5, 150, 86, 2), mat('#0f0e0d', { r: 0.2, m: 0.3 }), g, -W / 2 + 10, 80, 62);
  mesh(rb(12, 30, 14, 2), mat('#1d1c1b'), g, -W / 2 + 14, 80, 48);
  // wall art above the sofa
  const art = ctex(240, 160, (x, w, h) => { x.fillStyle = '#1f1d1c'; x.fillRect(0, 0, w, h); const gr = x.createRadialGradient(w * 0.62, h * 0.45, 4, w * 0.62, h * 0.45, 60); gr.addColorStop(0, '#8c7d71'); gr.addColorStop(1, 'rgba(255,106,31,0)'); x.fillStyle = gr; x.fillRect(0, 0, w, h); x.fillStyle = '#141312'; x.fillRect(0, h * 0.68, w, h); });
  mesh(rb(124, 4, 84, 1), trim, g, -60, D / 2 - 2, 160);
  plane(g, 116, 76, texM(art, { r: 0.6 }), -60, D / 2 - 4.2, 202, '-y');
  cat(g, 120, 40, 2.6);
  // you, on the sofa, with your phone
  H.you = person(g, -60, 248, -Math.PI / 2, { phone: true, seed: 1, shirt: '#5a5551', pants: '#282625' }); H.you.pose('sit');
  H.phoneL = new TH.PointLight(C(O), 0, 220, 1.4); scene.add(H.phoneL);
  H.phoneAt = () => wpos(H.you.phone);
  return H;
}

/* ------------------------------------------------------------------ STUDIO: hero AirTag on a plinth, hero phones */
function phoneStand(par, x, y, body, kind, sc = 8) {
  const g = grp(par, x, y);
  mesh(rb(250, 210, 34, 10, 4), pmat('#1c1a19', { r: 0.55, env: 0.35 }), g);
  mesh(rb(238, 198, 1, 8), pmat('#262422', { r: 0.4, env: 0.5 }), g, 0, 0, 34);
  mesh(rb(240, 200, 1, 0), glowM(O, 0.0, '#1f1d1c'), g, 0, 0, 34.2).visible = false;
  const ph = phone3(g, 0, 0, 36 + 59, sc, body, kind);
  ph.g.rotation.order = 'ZXY'; ph.g.rotation.set(Math.PI / 2 - 0.28, 0, 0.7);
  ph.g.position.set(Math.sin(0.7) * 12, Math.cos(0.7) * 12, 36 + 59);
  // stand: weighted round base, a slim leaning arm behind the phone and a front lip it rests on
  const alu = pmat('#4a4744', { r: 0.42, m: 1, env: 0.55 }), st = grp(g, 0, 0, 35, 0.7);
  mesh(cy(34, 36, 3, 64), alu, st, 0, 20, 0);
  mesh(rb(26, 2.4, 92, 1.2, 3), alu, st, 0, 38, 2, { rx: -0.28 });
  mesh(rb(46, 7, 2.4, 1.1, 3), alu, st, 0, 8, 2);
  mesh(rb(46, 1.6, 5, 0.7, 3), alu, st, 0, 4.5, 2);
  return { g, ph, s: ph.s, top: wpos(ph.g) };
}
function buildStudio() {
  const g = grp(scene, ...Z.STU), S = { g };
  mesh(cy(2800, 2800, 20, 96), mat('#161514', { r: 0.9 }), g, 0, 0, -20);
  const fl = ctex(1024, 1024, (x, w, h) => { x.fillStyle = '#000'; x.fillRect(0, 0, w, h); x.strokeStyle = 'rgba(206,186,169,0.05)'; x.lineWidth = 2; for (let i = 0; i <= 32; i++) { x.beginPath(); x.moveTo(i * 32, 0); x.lineTo(i * 32, h); x.moveTo(0, i * 32); x.lineTo(w, i * 32); x.stroke(); } });
  const flm = new TH.MeshBasicMaterial({ map: fl, transparent: true, blending: TH.AdditiveBlending, depthWrite: false, toneMapped: false });
  plane(g, 5600, 5600, flm, 0, 0, 0.2);
  // plinth with a glowing rim
  mesh(cy(118, 128, 64, 64), mat('#22201e', { r: 0.55, m: 0.2 }), g);
  mesh(cy(112, 112, 2, 64), mat('#2c2927', { r: 0.4, m: 0.3 }), g, 0, 0, 64);
  S.rimM = glowM(O, 1.0); mesh(tor(119, 0.7, 96), S.rimM, g, 0, 0, 64, { cast: false });
  S.under = glowSpot(g, 0, 0, 0.5, 300, O, 0.05);
  S.tag = airtag3(g, 40); S.tag.g.position.z = 66;
  S.tagTop = wz('STU', 0, 0, 66);
  S.yours = phoneStand(g, 1600, 0, '#2d2b29', 'ios');
  S.str = phoneStand(g, -1600, 0, '#c2c0be', 'ios');
  S.and = phoneStand(g, 1600 + 180 * 0.765, 180 * 0.644, '#5f6e62', 'android');
  S.and.g.visible = false;
  return S;
}

/* ------------------------------------------------------------------ DC: the Find My servers */
// server face art (4 px per cm): a rack of 1U/2U servers and storage shelves behind a perforated steel door.
// The static art is painted once; LEDs are painted on top every frame (hot rack: all lit when a report lands).
function rackFaceArt(seed) {
  const c = document.createElement('canvas'); c.width = 232; c.height = 800; const x = c.getContext('2d'), leds = [];
  x.fillStyle = '#0a0a0a'; x.fillRect(0, 0, 232, 800);
  const U = 17.8, plan = [2, 1, 1, 2, 0, 2, 2, 1, 1, 1, 4, 2, 0, 1, 1, 2, 2, 1, 1, 4, 2, 0, 1, 1, 2];
  let y = 22;
  plan.forEach((n, i) => {
    const h = (n || 1) * U - 1.5, r = rnd(seed * 31 + i, 5);
    if (y + h > 778) return;
    if (!n) { x.fillStyle = '#121211'; x.fillRect(14, y, 204, h); x.fillStyle = '#0c0c0c'; for (let k = 3; k < h; k += 4) x.fillRect(16, y + k, 200, 1); y += h + 1.5; return; }
    x.fillStyle = n >= 4 ? '#1b1a19' : '#201f1e'; x.fillRect(14, y, 204, h);
    x.fillStyle = '#363331'; x.fillRect(14, y, 204, 1); x.fillStyle = '#0b0b0a'; x.fillRect(14, y + h - 1, 204, 1);
    // ears with handles
    for (const ex of [14, 206]) { x.fillStyle = '#2b2927'; x.fillRect(ex, y + 1, 12, h - 2); x.fillStyle = '#4a4643'; x.fillRect(ex + 4, y + 3, 3, h - 6); }
    if (n === 1) {
      for (let k = 0; k < 10; k++) { const bx = 32 + k * 15; x.fillStyle = '#121110'; x.fillRect(bx, y + 3, 12, h - 6); x.fillStyle = '#2c2a28'; x.fillRect(bx, y + 3, 12, 1); leds.push([bx + 9, y + h - 6, 2, 2, 'a']); }
      x.fillStyle = '#151413'; for (let k = 0; k < 7; k++) x.fillRect(184 + (k % 2) * 0, y + 3 + k * 2, 18, 1);
      leds.push([196, y + 5, 3, 3, 's']);
    } else if (n === 2) {
      for (let k = 0; k < 4; k++) for (let j = 0; j < 2; j++) { const bx = 32 + k * 36, by = y + 3 + j * (h / 2 - 1); x.fillStyle = '#121110'; x.fillRect(bx, by, 33, h / 2 - 4); x.fillStyle = '#2d2b29'; x.fillRect(bx, by, 33, 1); x.fillStyle = '#1a1918'; for (let v = 0; v < 6; v++) x.fillRect(bx + 3 + v * 4, by + 4, 2, h / 2 - 10); leds.push([bx + 28, by + 3, 2, 2, 'a']); }
      x.fillStyle = '#121110'; x.fillRect(180, y + 4, 22, h - 8); leds.push([186, y + 8, 3, 3, 's'], [193, y + 8, 3, 3, 'p']);
    } else {
      for (let k = 0; k < 4; k++) for (let j = 0; j < 3; j++) { const bx = 30 + k * 40, by = y + 4 + j * (h - 8) / 3; x.fillStyle = '#111010'; x.fillRect(bx, by, 37, (h - 8) / 3 - 3); x.fillStyle = '#2a2826'; x.fillRect(bx, by, 37, 1); leds.push([bx + 31, by + 4, 3, 2, 'a']); }
      leds.push([196, y + 8, 3, 3, 's']);
    }
    y += h + 1.5;
  });
  // perforated door over it all
  x.fillStyle = 'rgba(0,0,0,0.42)';
  for (let j = 0; j < 800; j += 4) for (let i = (j / 4) % 2 ? 2 : 0; i < 232; i += 4) x.fillRect(i, j, 2, 2);
  // door frame and handle
  x.strokeStyle = '#2a2826'; x.lineWidth = 10; x.strokeRect(5, 5, 222, 790);
  x.strokeStyle = '#3d3a37'; x.lineWidth = 1; x.strokeRect(10.5, 10.5, 211, 779);
  x.fillStyle = '#1a1918'; x.fillRect(216, 330, 8, 120); x.fillStyle = '#5d5955'; x.fillRect(218, 336, 3, 108);
  return { c, leds };
}
function buildDC() {
  const g = grp(scene, ...Z.DC), W = 1500, D = 1000, WH = 330, TW = 16, Dc = { g, racks: [] };
  mesh(rb(W + TW, D + TW, 30), mat('#121110'), g, -TW / 2, TW / 2, -30.2);
  plane(g, W, D, texM(tilesTex('#211f1e', '#141312', 8), { r: 0.6, m: 0.15 }), 0, 0, 0.05);
  // perforated tiles down the cold aisle
  const perf = ctex(256, 256, (x, w, h) => { x.fillStyle = '#2a2826'; x.fillRect(0, 0, w, h); x.fillStyle = '#121110'; for (let j = 14; j < h - 10; j += 9) for (let i = 14; i < w - 10; i += 9) x.fillRect(i, j, 5, 5); x.strokeStyle = '#141312'; x.lineWidth = 4; x.strokeRect(0, 0, w, h); }, [12, 2]);
  plane(g, 744, 124, texM(perf, { r: 0.55, m: 0.3 }), -152, 30, 0.12);
  const wall = mat('#1d1b1a', { r: 0.9 }), seamM = mat('#141312', { r: 0.9 });
  mesh(rb(TW, D + TW, WH), wall, g, -W / 2 - TW / 2, TW / 2, 0);
  mesh(rb(W + TW, TW, WH), wall, g, -TW / 2, D / 2 + TW / 2, 0);
  for (let k = 1; k < 12; k++) mesh(rb(1.5, 1, WH), seamM, g, -W / 2 + k * 125, D / 2 - 0.4, 0, { cast: false });
  for (let k = 1; k < 8; k++) mesh(rb(1, 1.5, WH), seamM, g, -W / 2 + 0.4, -D / 2 + k * 125, 0, { cast: false });
  // a warm-white cove light along the top of both walls
  const cove = glowM('#f2e6da', 0.45);
  mesh(rb(W, 3, 2.5), cove, g, 0, D / 2 - 2, WH - 30, { cast: false }); mesh(rb(3, D, 2.5), cove, g, -W / 2 + 2, 0, WH - 30, { cast: false });
  const mkLed = (seed) => { const art = rackFaceArt(seed), c = document.createElement('canvas'); c.width = 232; c.height = 800; const t = new TH.CanvasTexture(c); t.colorSpace = TH.SRGBColorSpace; t.anisotropy = 8; return { art, c, g: c.getContext('2d'), t }; };
  Dc.led = mkLed(3); Dc.hot = mkLed(5);
  const ledM = screenM(Dc.led.t, 1.45), hotM = screenM(Dc.hot.t, 1.45);
  const body = pmat('#1a1918', { r: 0.42, m: 0.55, env: 0.35 }), cap = pmat('#232120', { r: 0.5, m: 0.4, env: 0.35 }), trim = pmat('#36332f', { r: 0.35, m: 0.8, env: 0.6 });
  const vent = ctex(128, 192, (x, w, h) => { x.fillStyle = '#211f1e'; x.fillRect(0, 0, w, h); x.fillStyle = '#121110'; for (let j = 12; j < h - 12; j += 6) x.fillRect(14, j, w - 28, 3); }, null);
  const ventM = texM(vent, { r: 0.6, m: 0.4 }), cable = mat('#0e0d0d', { r: 0.7 }), strip = glowM(O, 0.7), hotStrip = glowM(O, 0.7);
  Dc.hotStrip = hotStrip;
  for (const [ry, n] of [[-170, 9], [230, 9]]) {
    for (let k = 0; k < n; k++) {
      const x = -440 + k * 72, hot = ry === -170 && k === 5;
      mesh(rb(70, 100, 212, 1.2, 2), body, g, x, ry, 0);
      mesh(rb(70.4, 100.4, 2, 1, 2), cap, g, x, ry, 212);
      plane(g, 48, 76, ventM, x, ry + 6, 214.2);
      for (const ex of [-34, 34]) mesh(rb(2.2, 2, 212), trim, g, x + ex, ry - 49.6, 0);
      plane(g, 62, 204, hot ? hotM : ledM, x, ry - 50.15, 106, '-y');
      mesh(rb(54, 0.8, 1.1), hot ? hotStrip : strip, g, x, ry - 50.6, 206.5, { cast: false });
      // cables dropping from the tray into the top of the rack
      for (const cx of [-14, -8, 10]) mesh(cy(0.9, 0.9, 46, 8), cable, g, x + cx, ry + 30, 214);
      Dc.racks.push(wz('DC', x, ry, 214));
      if (hot) Dc.hotTop = wz('DC', x, ry, 214);
    }
    // end panels and the ladder cable tray over the row
    for (const ex of [-440 - 37, -440 + (n - 1) * 72 + 37]) mesh(rb(4, 102, 214, 1, 2), trim, g, ex, ry, 0);
    const tray = pmat('#3a3734', { r: 0.4, m: 0.8, env: 0.5 });
    for (const dy of [12, 48]) mesh(rb(680, 1.6, 6), tray, g, -152, ry + dy, 258);
    for (let k = 0; k < 23; k++) mesh(rb(1.6, 36, 1.6), tray, g, -480 + k * 30, ry + 30, 258);
    mesh(rb(660, 28, 4, 2), cable, g, -152, ry + 30, 260);
    for (const xx of [-470, -152, 166]) mesh(cy(0.8, 0.8, 70, 8), tray, g, xx, ry + 30, 264);
  }
  Dc.aisle = mesh(rb(700, 6, 0.6), glowM(O, 0), g, -150, 30, 0.1, { cast: false }); Dc.aisle.visible = false;
  Dc.draw = (t, hotK) => {
    const k = Math.floor(t * 8);
    const paint = (L, hotk) => {
      const x = L.g; x.drawImage(L.art.c, 0, 0);
      L.art.leds.forEach(([lx, ly, lw, lh, kind], i) => {
        const r = rnd(i * 7 + k * 13 + (kind === 'a' ? 0 : 5), 3);
        x.fillStyle = hotk > 0.3 ? (r < 0.5 ? '#ffd2b0' : '#ff6a1f')
          : kind === 'p' ? '#cfc7bf' : kind === 's' ? (r < 0.92 ? '#ff6a1f' : '#ffb547') : r < 0.55 ? '#e8e0d6' : r < 0.62 ? '#ff6a1f' : '#2a2725';
        x.fillRect(lx, ly, lw, lh);
      });
      L.t.needsUpdate = true;
    };
    paint(Dc.led, 0); paint(Dc.hot, hotK);
    hotStrip.emissiveIntensity = 0.7 + 3 * hotK;
  };
  Dc.draw(0, 0);
  return Dc;
}

/* ------------------------------------------------------------------ AIRPORT: baggage claim */
function buildAirport() {
  const g = grp(scene, ...Z.AIR), W = 2600, D = 1800, WH = 470, TW = 18, A = { g, bags: [] };
  mesh(rb(W + TW, D + TW, 30), mat('#161514'), g, -TW / 2, TW / 2, -30.2);
  plane(g, W, D, texM(tilesTex('#2c2a28', '#1d1b1a', 10), { r: 0.42, m: 0.05 }), 0, 0, 0.05);
  const wall = mat('#272524', { r: 0.95 });
  mesh(rb(TW, D + TW, WH), wall, g, -W / 2 - TW / 2, TW / 2, 0);
  // back wall with tall windows onto the night apron
  const by = D / 2 + TW / 2, sky = screenM(ctex(512, 360, (x, w, h) => {
    const gr = x.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, '#0f0e0e'); gr.addColorStop(1, '#23201e'); x.fillStyle = gr; x.fillRect(0, 0, w, h);
    x.fillStyle = '#121110'; x.fillRect(0, h * 0.78, w, h); for (let i = 0; i < 26; i++) { x.fillStyle = i % 3 ? '#9b9087' : '#d5cec8'; x.fillRect(i * 20 + 4, h * 0.8, 5, 3); }
    x.fillStyle = '#0d0c0c'; x.beginPath(); x.moveTo(w * 0.55, h * 0.66); x.lineTo(w * 0.95, h * 0.62); x.lineTo(w * 0.95, h * 0.7); x.lineTo(w * 0.55, h * 0.72); x.fill();
  }), 0.9);
  for (let k = 0; k < 5; k++) {
    const x0 = -W / 2 + k * (W / 5);
    mesh(rb(W / 5, TW, 70), wall, g, x0 + W / 10, by, 0); mesh(rb(W / 5, TW, 90), wall, g, x0 + W / 10, by, WH - 90);
    mesh(rb(40, TW, WH), wall, g, x0 + 20, by, 0);
    plane(g, W / 5 - 40, WH - 160, sky, x0 + W / 10 + 20, by + 2, 70 + (WH - 160) / 2, '-y');
  }
  mesh(rb(W, 8, 8), mat('#1d1c1b'), g, 0, by - 12, 70);
  // pillars
  for (const [x, y] of [[-1000, -500], [1050, 350], [-1000, 520]]) { mesh(cy(42, 42, WH, 24), mat('#302d2b', { r: 0.6 }), g, x, y, 0); mesh(cy(50, 50, 12, 24), mat('#1f1e1d'), g, x, y, 0); }
  // the carousel: base, belt ring, steel island; bags ride the belt
  const cg = grp(g, -250, 230), L = 620, R = 175;
  A.c = [Z.AIR[0] - 250, Z.AIR[1] + 230];
  mesh(extr(stadium(L, R + 70), 30, 3), mat('#2d2a28', { r: 0.6, m: 0.3 }), cg);
  mesh(extr(stadium(L, R + 62, R - 58), 6, 2), mat('#181717', { r: 0.9 }), cg, 0, 0, 32);
  mesh(extr(stadium(L, R - 52), 46, 3), mat('#3c3936', { r: 0.35, m: 0.7 }), cg, 0, 0, 30);
  mesh(extr(stadium(L, R - 64), 4, 1), glowM(O, 0.7), cg, 0, 0, 78, { cast: false });
  const BAGC = ['#44413f', '#47413d', '#3b3836', '#5b544f', '#282625', '#484542', '#46403b', '#45423f', '#65615d'];
  // each bag lies on its back inside a holder group that rides the belt
  for (let k = 0; k < 9; k++) { const h = grp(cg), s = suitcase(h, 0, 30, 0, BAGC[k], 0.85); s.g.position.z = 12; s.g.rotation.x = Math.PI / 2; s.g.rotation.order = 'ZXY'; s.g.rotation.z = (k % 2) * 0.3; A.bags.push(h); }
  A.belt = (t) => A.bags.forEach((h, k) => { const [x, y, a] = stadiumAt(L, R, k * (2 * L + 2 * Math.PI * R) / 9 + t * 40); h.position.set(x, y, 38); h.rotation.z = a + Math.PI / 2; });
  A.belt(0);
  // the hanging "BAGGAGE CLAIM" sign
  // text sized to fit beside the belt number, so the two never overlap
  const sign = ctex(768, 128, (x, w, h) => {
    x.fillStyle = '#171615'; x.fillRect(0, 0, w, h); x.textBaseline = 'middle';
    x.fillStyle = '#ff6a1f'; x.beginPath(); x.roundRect(w - 112, 18, 88, 92, 10); x.fill();
    x.fillStyle = '#181513'; x.font = '800 70px Inter'; x.textAlign = 'center'; x.fillText('3', w - 68, h / 2 + 3);
    x.textAlign = 'left'; x.fillStyle = '#f4f3f2'; let fs = 58; x.font = `700 ${fs}px Inter`;
    while (x.measureText('BAGGAGE CLAIM').width > w - 170 && fs > 30) x.font = `700 ${--fs}px Inter`;
    x.fillText('BAGGAGE CLAIM', 30, h / 2 + 2);
  });
  mesh(rb(470, 14, 84, 3), mat('#1d1c1b'), g, -250, 230, 340);
  plane(g, 460, 77, screenM(sign, 1.1), -250, 222.5, 382, '-y');
  for (const x of [-440, -60]) mesh(cy(1.5, 1.5, 46), mat('#2c2a28'), g, x, 230, 424);
  // departures board on the back wall
  const board = ctex(600, 260, (x, w, h) => {
    x.fillStyle = '#100f0f'; x.fillRect(0, 0, w, h); x.font = '700 22px Mono'; x.fillStyle = '#9e9995'; x.fillText('ARRIVALS', 20, 34);
    [['UA 1142', 'DENVER', 'BELT 3'], ['DL 0871', 'ATLANTA', 'BELT 1'], ['AA 2209', 'CHICAGO', 'BELT 3'], ['UA 0567', 'NEWARK', 'DELAYED'], ['B6 0414', 'BOSTON', 'BELT 2']].forEach((r, i) => {
      x.fillStyle = r[2] === 'DELAYED' ? '#ff4d5e' : '#ffb547'; x.fillText(r[0], 20, 78 + i * 38); x.fillText(r[1], 190, 78 + i * 38); x.fillText(r[2], 430, 78 + i * 38);
    });
  });
  mesh(rb(330, 12, 150, 3), mat('#1d1c1b'), g, 650, D / 2 - 6, 230);
  plane(g, 316, 137, screenM(board, 1.2), 650, D / 2 - 12.5, 305, '-y');
  // baggage services desk
  const dg = grp(g, 700, -380);
  mesh(rb(380, 90, 102, 4), mat('#312e2c', { r: 0.6 }), dg);
  mesh(rb(394, 100, 6, 2), mat('#3e3b39', { r: 0.4, m: 0.2 }), dg, 0, 0, 102);
  mesh(rb(380, 2, 30, 1), glowM(O, 0.8), dg, 0, -46, 60, { cast: false });
  const ds = ctex(512, 96, (x, w, h) => { x.fillStyle = '#171615'; x.fillRect(0, 0, w, h); x.fillStyle = '#f4f3f2'; x.font = '800 44px Inter'; x.textBaseline = 'middle'; x.fillText('BAGGAGE SERVICES', 22, h / 2 + 2); });
  mesh(rb(330, 10, 64, 3), mat('#1d1c1b'), dg, 0, 70, 220); plane(dg, 318, 58, screenM(ds, 1.2), 0, 64.5, 252, '-y');
  for (const x of [-140, 140]) mesh(cy(2, 2, 120), mat('#2c2a28'), dg, x, 70, 102);
  mesh(rb(44, 34, 30, 3), mat('#161514'), dg, 90, 10, 108, { rz: -0.4 });
  A.agent = person(dg, 30, 95, -Math.PI / 2, { seed: 4, shirt: '#3f3b38', pants: '#282624', short: true }); A.agent.pose('talk', 0);
  A.her = person(dg, -40, -150, Math.PI / 2, { seed: 2, shirt: '#564f49', long: true, phone: true }); A.her.pose('phone');
  // a few people waiting at the belt
  A.wait = [[-640, -60, 0.5, 3], [-300, -60, 1.3, 6], [120, 40, 2.4, 7], [-520, 470, -1.2, 9]].map(([x, y, rz, s]) => { const p = person(g, x, y, rz, { seed: s }); p.pose(s % 2 ? 'phone' : 'stand'); return p; });
  return A;
}

/* ------------------------------------------------------------------ CITY */
const PITCH = 2000, BLK = 1400, SWK = 260, NCELL = 4, BAG = [175, -565], SLANE = -695;
const isPark = (i, j) => j === -1 && Math.abs(i) <= 1;
const isApt = (i, j) => i === 2 && j === 1;
// a loop around a block at distance r from its centre: point + heading at distance u
// a checked bag lying open on the ground, lid flipped back, clothes spilling out (other people's bags at the dumpsters)
function openCase(par, x, y, rz, col) {
  const g = grp(par, x, y, 16, rz), shell = mat(col, { r: 0.55 }), cloth = ['#625c58', '#867f7a', '#3e3a37'];
  mesh(rb(64, 44, 14, 3), shell, g); mesh(rb(58, 38, 3, 1.2), mat('#322f2c', { r: 0.95 }), g, 0, 0, 11);
  mesh(rb(64, 44, 12, 3), shell, g, 0, 48, 0, { rx: 0.22 });
  [[-12, -30, 0.6, 30, 20], [14, -40, -0.3, 24, 16], [4, 6, 0.2, 34, 22]].forEach(([dx, dy, r, w, d], k) => mesh(rb(w, d, 6, 3), mat(cloth[k], { r: 1 }), g, dx, dy, k === 2 ? 12 : 0, { rz: r }));
  return g;
}
function loopAt(cx, cy_, r, u) {
  const L = 2 * r; u = ((u % (4 * L)) + 4 * L) % (4 * L);
  const s = Math.floor(u / L), q = u - s * L;
  if (s === 0) return [cx - r + q, cy_ - r, 0];
  if (s === 1) return [cx + r, cy_ - r + q, Math.PI / 2];
  if (s === 2) return [cx + r - q, cy_ + r, Math.PI];
  return [cx - r, cy_ + r - q, -Math.PI / 2];
}
function buildCity() {
  const root = grp(scene), Ci = { bld: [], walkers: [], movers: [] };
  const asphalt = mat('#161514', { r: 0.92 }), conc = mat('#2e2c2a', { r: 0.92 }), inner = mat('#1e1c1b', { r: 0.95 });
  const grass = mat('#201e1c', { r: 1 }), pathM = mat('#312e2c', { r: 0.95 }), paintM = mat('#4c4946', { r: 0.8 });
  mesh(rb(19000, 19000, 6), asphalt, root, 0, 0, -6, { cast: false });
  for (let k = -5; k <= 4; k++) {
    const c = (k + 0.5) * PITCH;
    for (let s = -9000; s <= 9000; s += 450) {
      const m = (((s - 1000) % PITCH) + PITCH) % PITCH; if (m < 360 || m > PITCH - 360) continue;
      mesh(rb(200, 10, 0.8), paintM, root, s, c, 0, { cast: false }); mesh(rb(10, 200, 0.8), paintM, root, c, s, 0, { cast: false });
    }
  }
  // zebra crossings around the hero corner
  for (const [x, y, rz] of [[-1000, -1000, 0], [1000, -1000, 0], [3000, -1000, 0], [1000, 1000, 0]]) for (let k = -4; k <= 4; k++) {
    mesh(rb(60, 300, 0.8), paintM, root, x + k * 0 + 0, y, 0, { cast: false }).position.set(x + k * 70, y - 520, 0);
    mesh(rb(300, 60, 0.8), paintM, root, x, y, 0, { cast: false }).position.set(x - 520, y + k * 70, 0);
  }
  const FAC = [facadeTex(1, 0.42), facadeTex(2, 0.3, '#2e2c2a'), facadeTex(3, 0.52, '#262423'), facadeTex(4, 0.22, '#322f2c')];
  const shopM = mat('#262320', { e: '#b6aca4', ei: 0.35 }), awnM = mat('#3c3834', { r: 0.8 }), shopF = mat('#191817', { r: 0.6 });
  const lampHead = mat('#ffffff', { e: '#f3efeb', ei: 2.2 });
  const lampAt = (x, y, rz) => { streetLamp(root, x, y, rz, lampHead); const c = [Math.cos(rz) * 100, Math.sin(rz) * 100]; glowSpot(root, x + c[0], y + c[1], 17, 300, '#a89a8f', 0.12); };
  const cars = ['#45423f', '#47413d', '#3b3836', '#484542', '#5b544f', '#282625', '#7a2e1c', '#b3b0ae'];
  for (let i = -NCELL; i <= NCELL; i++) for (let j = -NCELL; j <= NCELL; j++) {
    const cx = i * PITCH, cy_ = j * PITCH, s = (i + 9) * 31 + j + 9, hero = j === 0 && Math.abs(i) <= 1;
    mesh(rb(BLK, BLK, 16, 5), conc, root, cx, cy_, 0);
    if (isPark(i, j)) {
      mesh(rb(880, 880, 6), grass, root, cx, cy_, 16);
      mesh(rb(880, 90, 1.2), pathM, root, cx, cy_, 22); mesh(rb(90, 880, 1.2), pathM, root, cx, cy_, 22);
      for (let k = 0, n = 0; k < 40 && n < 7; k++) {
        const x = (rnd(s * 50 + k, 1) - 0.5) * 760, y = (rnd(s * 50 + k, 2) - 0.5) * 760;
        if (Math.abs(x) < 110 || Math.abs(y) < 110 || y > -60) continue;
        tree(root, cx + x, cy_ + y, 0.8 + rnd(k, s) * 0.4, k + s); n++;
      }
      bench(root, cx + 220, cy_ - 75, 0); bench(root, cx - 75, cy_ - 240, -Math.PI / 2);
    } else if (isApt(i, j)) {
      // the apartment complex: four wings round a courtyard, with the dumpsters in the middle. Two versions, not baked:
      // solid for the city shots, and a glass cutaway for the airline story, so her bag reads as inside the complex
      mesh(rb(880, 880, 2), mat('#1f1e1d', { r: 0.95 }), root, cx, cy_, 16);
      mesh(rb(440, 440, 1), mat('#2c2a28', { r: 0.9 }), root, cx, cy_, 18, { cast: false });
      const am = facadeTex(7, 0.55, '#373330'), FH = 300, NF = 3, HH = NF * FH + 30;
      // back wings (north, west) stay solid; the front wings (south, east) are solid in the city shots and an open
      // glass frame in the airline story, so the camera sees into the courtyard
      const WINGS = [[0, 330, 880, 220], [-330, 0, 220, 440], [0, -330, 880, 220], [330, 0, 220, 440]];
      Ci.aptSolid = grp(scene); Ci.aptGlass = grp(scene); Ci.aptGlass.visible = false;
      WINGS.forEach(([dx, dy, w, d], k) => building(k < 2 ? root : Ci.aptSolid, cx + dx, cy_ + dy, w - 4, d - 4, HH, am, 71 + k, '#292725'));
      const glassM = new TH.MeshStandardMaterial({ color: C('#ffc08a'), roughness: 0.1, transparent: true, opacity: 0.035, depthWrite: false, side: TH.DoubleSide });
      const slabM = new TH.MeshStandardMaterial({ color: C('#383533'), roughness: 0.9, transparent: true, opacity: 0.16, depthWrite: false });
      const frameM = mat('#413d3a', { r: 0.6, m: 0.3 });
      WINGS.slice(2).forEach(([dx, dy, w, d]) => {
        const x = cx + dx, y = cy_ + dy;
        mesh(rb(w - 4, d - 4, HH), glassM, Ci.aptGlass, x, y, 16, { cast: false, recv: false });
        for (let f = 1; f <= NF; f++) {
          const z = 16 + f * FH; mesh(rb(w, d, 4), slabM, Ci.aptGlass, x, y, z - 4, { cast: false, recv: false });
          mesh(rb(w, 8, 8), frameM, Ci.aptGlass, x, y - d / 2, z, { cast: false }); mesh(rb(w, 8, 8), frameM, Ci.aptGlass, x, y + d / 2, z, { cast: false });
          mesh(rb(8, d, 8), frameM, Ci.aptGlass, x - w / 2, y, z, { cast: false }); mesh(rb(8, d, 8), frameM, Ci.aptGlass, x + w / 2, y, z, { cast: false });
        }
        for (const [sx, sy] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) mesh(rb(10, 10, HH), frameM, Ci.aptGlass, x + sx * (w / 2 - 5), y + sy * (d / 2 - 5), 16, { cast: false });
      });
      // the complex's sign by the gate on the street side
      // even letter spacing, sized to fit; sits by the gate, near the middle of the street side so it stays in frame
      const signT = ctex(1024, 160, (g, W, H) => {
        g.fillStyle = '#141211'; g.fillRect(0, 0, W, H); g.fillStyle = '#f4f3f2'; g.textAlign = 'center'; g.textBaseline = 'middle';
        let fs = 92; g.letterSpacing = '10px'; g.font = `700 ${fs}px Inter`; while (g.measureText('APARTMENTS').width > W * 0.86) g.font = `700 ${--fs}px Inter`;
        g.fillText('APARTMENTS', W / 2, H / 2 + 4);
      });
      Ci.signG = grp(scene); // outside root, so bake() leaves it separate and the page can hide it
      mesh(rb(330, 24, 110, 4), mat('#292725', { r: 0.8 }), Ci.signG, cx + 120, cy_ - 470, 16);
      plane(Ci.signG, 304, 47, screenM(signT, 1.1), cx + 120, cy_ - 483, 72, '-y');
      Ci.aptSign = [cx + 120, cy_ - 483, 110]; Ci.aptWing = [cx - 330, cy_ - 60, HH * 0.6];
      // the dumpsters in the courtyard, in a three-sided fence
      Ci.dumpster = [cx + 90, cy_ + 110, 17]; Ci.aptC = [cx, cy_];
      const dg = grp(root, Ci.dumpster[0], Ci.dumpster[1], 17), fenceM = mat('#373330', { r: 0.85 });
      mesh(rb(170, 100, 110, 4), mat('#4e4a46', { r: 0.6, m: 0.2 }), dg); mesh(rb(176, 106, 8, 3), mat('#403c38', { r: 0.5 }), dg, 0, 0, 110, { rx: -0.08 });
      mesh(rb(260, 8, 150), fenceM, dg, 0, 70, 0); mesh(rb(8, 150, 150), fenceM, dg, -130, 0, 0); mesh(rb(8, 150, 150), fenceM, dg, 130, 0, 0);
      // other people's bags, opened and dumped in front of the bins: this is where her tag's location report pointed
      const DX = Ci.dumpster[0], DY = Ci.dumpster[1];
      // B: no dumped bags here (the story only says her tag pointed to the complex)
      Ci.otherBags = [DX + 72, DY - 96, 26]; Ci.herTag = [DX + 5, DY - 98];
      lampAt(cx + 100, cy_ - 660, -Math.PI / 2); lampAt(cx + 660, cy_ + 200, 0);
    } else {
      mesh(rb(880, 880, 2), inner, root, cx, cy_, 16);
      const kind = rnd(s, 1), I = 440, gap = 22;
      const parts = kind < 0.28 ? [[0, 0, 2 * I, 2 * I]] : kind < 0.55 ? [[0, -I / 2, 2 * I, I], [0, I / 2, 2 * I, I]] : kind < 0.72 ? [[-I / 2, 0, I, 2 * I], [I / 2, 0, I, 2 * I]] : [[-I / 2, -I / 2, I, I], [I / 2, -I / 2, I, I], [-I / 2, I / 2, I, I], [I / 2, I / 2, I, I]];
      const far = Math.max(Math.abs(i), Math.abs(j)), minF = hero ? 3 : 2, maxF = hero ? 6 : far > 2 ? 12 : 8;
      parts.forEach(([dx, dy, w, d], k) => {
        const fl = minF + Math.floor(rnd(s, k + 3) * (maxF - minF + 1)), h = fl * 320 + 40, bw = w - 2 * gap, bd = d - 2 * gap;
        building(root, cx + dx, cy_ + dy, bw, bd, h, FAC[(s + k) % 4], s * 7 + k);
        Ci.bld.push([cx + dx, cy_ + dy, bw, bd, h]);
        if (hero && dy <= 0) {
          const y0 = cy_ + dy - bd / 2;
          mesh(rb(bw - 60, 4, 230), shopM, root, cx + dx, y0 - 2, 16, { cast: false });
          for (let m = 0; m < 4; m++) mesh(rb(8, 8, 230), shopF, root, cx + dx - (bw - 60) / 2 + m * (bw - 60) / 3, y0 - 5, 16);
          if ((k + i) % 2 === 0) mesh(rb(bw - 40, 90, 8, 2), awnM, root, cx + dx, y0 - 45, 258, { rx: 0.18 });
        }
      });
    }
    // sidewalk lamps and trees
    if (!isApt(i, j)) {
      const R = 668;
      for (const [side, rz] of [[0, -Math.PI / 2], [1, 0], [2, Math.PI / 2], [3, Math.PI]]) {
        const hs = i === 0 && j === 0 && side === 0, along = hs ? [-420, 640] : [-380, 380], Rr = hs ? 690 : R;
        for (const a of along) {
          const [x, y] = side === 0 ? [cx + a, cy_ - Rr] : side === 1 ? [cx + Rr, cy_ + a] : side === 2 ? [cx - a, cy_ + Rr] : [cx - Rr, cy_ - a];
          lampAt(x, y, rz);
        }
        if (!(i === 0 && j === 0 && side === 0) && rnd(s, side + 20) < 0.6) {
          const a = 0, [x, y] = side === 0 ? [cx + a, cy_ - R] : side === 1 ? [cx + R, cy_ + a] : side === 2 ? [cx - a, cy_ + R] : [cx - R, cy_ - a];
          tree(root, x, y, 0.75, s + side);
        }
      }
    }
    // parked cars on the quiet streets
    if (!(j === 0 || j === -1) || Math.abs(i) > 2) for (let side = 0; side < 4; side++) if (rnd(s, side + 40) < 0.45 && side !== 0) {
      const R = 790, a = (rnd(s, side + 50) - 0.5) * 900, rz = [0, Math.PI / 2, Math.PI, -Math.PI / 2][side];
      const [x, y] = side === 0 ? [cx + a, cy_ - R] : side === 1 ? [cx + R, cy_ + a] : side === 2 ? [cx - a, cy_ + R] : [cx - R, cy_ - a];
      car(root, x, y, rz, cars[(s + side) % cars.length]);
    }
  }
  // the bus stop on the south sidewalk of cell (0,0), the lost bag beside its bench
  const bs = grp(root, 90, -500), steel = mat('#2c2a28', { r: 0.4, m: 0.6 });
  mesh(rb(400, 150, 8, 3), mat('#211f1e', { r: 0.6 }), bs, 0, -40, 250);
  for (const x of [-190, 190]) mesh(rb(8, 8, 250), steel, bs, x, 25, 0);
  mesh(rb(380, 4, 200), mat('#867f7a', { op: 0.16, r: 0.1 }), bs, 0, 30, 30);
  const ad = ctex(256, 384, (x, w, h) => { x.fillStyle = '#191716'; x.fillRect(0, 0, w, h); const gr = x.createRadialGradient(w / 2, h * 0.42, 10, w / 2, h * 0.42, 130); gr.addColorStop(0, '#ffb070'); gr.addColorStop(0.5, '#ff6a1f'); gr.addColorStop(1, 'rgba(255,106,31,0)'); x.fillStyle = gr; x.fillRect(0, 0, w, h); x.fillStyle = '#f4f3f2'; x.font = '900 34px Inter'; x.fillText('NIGHT', 26, h - 70); x.fillText('LINES', 26, h - 34); });
  mesh(rb(10, 130, 210, 2), mat('#211f1e'), bs, 205, -40, 20);
  plane(bs, 120, 196, screenM(ad, 0.35), 211, -40, 125, '+x');
  bench(root, 30, -505, 0, 200);
  const sp = grp(root, -170, -640); mesh(cy(3, 3, 260, 8), steel, sp); mesh(cy(26, 26, 3, 24), mat('#c2c0be', { r: 0.5 }), sp, 0, 0, 262, { rx: Math.PI / 2 });
  Ci.busL = new TH.PointLight(C('#e3ddd8'), 650, 1500, 1.2); Ci.busL.position.set(90, -560, 240); scene.add(Ci.busL);
  Ci.baked = bake(root);
  // --- dynamic things (not baked)
  Ci.bag = suitcase(scene, BAG[0], BAG[1], 0.35, '#dedbd9');
  Ci.bag.g.position.z = 16;
  Ci.tag = airtag3(Ci.bag.g, 5); Ci.tag.g.position.set(-16, -4, 71.5); Ci.tag.g.rotation.x = 0;
  // a leather holder around the tag, looped onto the carry handle
  { const lea = pmat('#2a1d17', { r: 0.55, cc: 0.3, env: 0.5 }); mesh(cy(5.9, 5.9, 1.4, 48), lea, Ci.bag.g, -16, -4, 71); mesh(rb(7, 3, 1.2, 0.6, 2), lea, Ci.bag.g, -10.5, -3.8, 71); }
  Ci.tagAt = () => wpos(Ci.tag.g);
  // her bag, standing upright in front of the dumped cases with her AirTag on the handle (not baked, so it stays lit)
  Ci.herTag = [Ci.dumpster[0] + 5, Ci.dumpster[1] - 165];
  Ci.herBag = suitcase(scene, Ci.herTag[0], Ci.herTag[1], -0.5, '#e4dccf'); Ci.herBag.g.position.z = 17;
  Ci.herTagO = airtag3(Ci.herBag.g, 5); Ci.herTagO.g.position.set(-16, -4, 71.5);
  { const lea = pmat('#2a1d17', { r: 0.55, cc: 0.3, env: 0.5 }); mesh(cy(5.9, 5.9, 1.4, 48), lea, Ci.herBag.g, -16, -4, 71); mesh(rb(7, 3, 1.2, 0.6, 2), lea, Ci.herBag.g, -10.5, -3.8, 71); }
  // walkers on the sidewalks (none on the hero corner)
  for (let n = 0, k = 0; n < 26 && k < 200; k++) {
    const i = Math.floor(rnd(k, 61) * 7) - 3, j = Math.floor(rnd(k, 62) * 7) - 3;
    if ((i === 0 || i === 1) && (j === 0 || j === -1)) continue;
    const p = person(scene, 0, 0, 0, { seed: k + 3, phone: rnd(k, 63) < 0.5, long: rnd(k, 64) < 0.3, pack: rnd(k, 65) < 0.2 ? '#3a3735' : null });
    Ci.walkers.push({ p, cx: i * PITCH, cy: j * PITCH, r: 560 + rnd(k, 66) * 60, u0: rnd(k, 67) * 4800, v: (rnd(k, 68) < 0.5 ? -1 : 1) * (110 + rnd(k, 69) * 40), ph: rnd(k, 70) * 6 }); n++;
  }
  // moving cars: two lanes on the hero road, one on a cross street
  for (let k = 0; k < 7; k++) {
    const lane = k % 3, g = car(scene, 0, 0, 0, cars[(k * 3) % cars.length], true);
    Ci.movers.push({ g, lane, u0: rnd(k, 80) * 18000, v: 700 + rnd(k, 81) * 300 });
  }
  // the people in the story
  Ci.stranger = person(scene, 0, -650, 0, { seed: 5, phone: true, shirt: '#57534f', coat: true });
  Ci.you = person(scene, 0, 0, 0, { seed: 11, pack: '#3a3735', shirt: '#3f3b38' });
  Ci.hider = person(scene, 0, 0, 0, { seed: 9, shirt: '#282625', pants: '#282624', coat: true });
  Ci.redTag = airtag3(scene, 4); Ci.redTag.ringM.emissive.set(RED);
  // phones everywhere: points on lit facades and sidewalks; each lights once as the wave reaches it and then holds
  const NP = 1700, pos = new Float32Array(NP * 3), col = new Float32Array(NP * 3), meta = [];
  for (let n = 0; n < NP; n++) {
    let x, y, z;
    if (n < 900) {
      const b = Ci.bld[Math.floor(rnd(n, 91) * Ci.bld.length)], f = Math.floor(rnd(n, 92) * 4);
      const fl = Math.floor(rnd(n, 93) * (b[4] - 40) / 320);
      z = fl * 320 + 100 + rnd(n, 94) * 120;
      const t = rnd(n, 95) - 0.5;
      [x, y] = f === 0 ? [b[0] + t * b[2], b[1] - b[3] / 2 - 8] : f === 1 ? [b[0] + b[2] / 2 + 8, b[1] + t * b[3]] : f === 2 ? [b[0] + t * b[2], b[1] + b[3] / 2 + 8] : [b[0] - b[2] / 2 - 8, b[1] + t * b[3]];
    } else {
      const i = Math.floor(rnd(n, 96) * 9) - 4, j = Math.floor(rnd(n, 97) * 9) - 4;
      [x, y] = loopAt(i * PITCH, j * PITCH, 560 + rnd(n, 98) * 100, rnd(n, 99) * 4800); z = 125;
    }
    pos.set([x, y, z], n * 3);
    meta.push({ d: Math.hypot(x - BAG[0], y - BAG[1]), r: rnd(n, 100), b: n < 900 ? 0.55 + 0.25 * rnd(n, 101) : 0.9 + 0.2 * rnd(n, 101) });
  }
  const pg = new TH.BufferGeometry(); pg.setAttribute('position', new TH.BufferAttribute(pos, 3)); pg.setAttribute('color', new TH.BufferAttribute(col, 3));
  Ci.dots = new TH.Points(pg, new TH.PointsMaterial({ map: TX_SOFT, size: 11, sizeAttenuation: false, vertexColors: true, transparent: true, blending: TH.AdditiveBlending, depthWrite: false, toneMapped: false }));
  Ci.dots.frustumCulled = false; scene.add(Ci.dots); Ci.dotMeta = meta;
  // per frame: walkers, cars, phone dots (on = 0..1 brightness, t0 = when the wave starts)
  Ci.update = (t, o = {}) => {
    for (const w of Ci.walkers) {
      const u = w.u0 + w.v * t, [x, y, a] = loopAt(w.cx, w.cy, w.r, u);
      w.p.root.position.set(x, y, 16); w.p.root.rotation.z = a + (w.v < 0 ? Math.PI : 0);
      w.p.pose(w.p.phone ? 'walkphone' : 'walk', Math.abs(u) / 140 * Math.PI * 2 + w.ph);
    }
    for (const m of Ci.movers) {
      const u = ((m.u0 + m.v * t) % 18000 + 18000) % 18000 - 9000;
      if (m.lane === 0) { m.g.position.set(u, -860, 0); m.g.rotation.z = 0; }
      else if (m.lane === 1) { m.g.position.set(-u, -1140, 0); m.g.rotation.z = Math.PI; }
      else { m.g.position.set(1000, u, 0); m.g.rotation.z = Math.PI / 2; }
    }
    const c = Ci.dots.geometry.attributes.color.array, on = o.on || 0, t0 = o.t0 ?? 1e9;
    for (let n = 0; n < NP; n++) {
      const M = meta[n], k0 = t0 + (M.d / 9000) * 2.4 + M.r * 0.25, dt = t - k0;
      // a short bright pop as the wave reaches the phone, then a steady glow (no twinkle)
      const v = dt <= 0 ? 0 : on * M.b * (ease.out(Math.min(1, dt / 0.3)) + 0.9 * Math.exp(-dt * 4) * Math.min(1, dt / 0.08));
      c[n * 3] = 2.2 * v; c[n * 3 + 1] = 1.0 * v; c[n * 3 + 2] = 0.4 * v;
    }
    Ci.dots.geometry.attributes.color.needsUpdate = true; Ci.dots.visible = on > 0;
  };
  return Ci;
}
