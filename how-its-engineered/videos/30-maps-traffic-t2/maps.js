// 30 Maps traffic: the pieces this reel adds to the AirTag kit. A traffic model on the hero road (cars bunch up in a
// jam zone and slow down), a phone marker over every car, city-wide moving dots on every road, glowing road overlays
// that can turn red, your own car with a detour route, and the artist's little red wagon full of phones.

// a phone glyph for holo sprites
ICO.phone = (g, S, col) => {
  g.strokeStyle = col; g.lineWidth = S * 0.07; g.shadowColor = col; g.shadowBlur = 8;
  g.beginPath(); g.roundRect(S * 0.32, S * 0.14, S * 0.36, S * 0.72, S * 0.07); g.stroke();
  g.shadowBlur = 0; g.fillStyle = col; g.globalAlpha = 0.35; g.fillRect(S * 0.37, S * 0.22, S * 0.26, S * 0.5); g.globalAlpha = 1;
  g.beginPath(); g.arc(S / 2, S * 0.79, S * 0.025, 0, 7); g.fill();
};
ICO.cam = (g, S, col) => {
  g.strokeStyle = col; g.fillStyle = col; g.lineWidth = S * 0.06; g.shadowColor = col; g.shadowBlur = 8;
  g.beginPath(); g.roundRect(S * 0.2, S * 0.36, S * 0.42, S * 0.3, S * 0.05); g.stroke();
  g.beginPath(); g.moveTo(S * 0.62, S * 0.46); g.lineTo(S * 0.8, S * 0.38); g.lineTo(S * 0.8, S * 0.64); g.lineTo(S * 0.62, S * 0.56); g.closePath(); g.stroke();
  g.lineWidth = S * 0.08; g.beginPath(); g.moveTo(S * 0.16, S * 0.16); g.lineTo(S * 0.84, S * 0.84); g.stroke();
};

// the road grid: roads run between blocks at (k + 0.5) * PITCH; each has a lane each way, 140 off the centre line
const ROADS = []; for (let k = -4; k <= 3; k++) { ROADS.push({ ax: 'x', c: (k + 0.5) * PITCH }); ROADS.push({ ax: 'y', c: (k + 0.5) * PITCH }); }
const HERO_Y = -1000, LANE_E = -860, LANE_W = -1140;   // the hero road and its eastbound / westbound lanes
const JAM0 = 600, JAM1 = 2900, JK = 0.3;               // the jam zone on the eastbound lane, and how much it squeezes
// free-flow coordinate s → road x: outside the jam 1:1, inside it squeezed by JK (so cars bunch up and slow down there)
function jamX(s) {
  if (s < JAM0) return s;
  const L = (JAM1 - JAM0) / JK;
  return s < JAM0 + L ? JAM0 + (s - JAM0) * JK : JAM1 + (s - JAM0 - L);
}

function buildMaps(CI) {
  const M = { cars: [], marks: [], dots: null, ov: [], jamOv: null };
  const cols = ['#45423f', '#47413d', '#3b3836', '#484542', '#5b544f', '#282625', '#7a2e1c', '#b3b0ae', '#3f3c3a'];
  // traffic on the eastbound lane: evenly spaced in free-flow s, squeezed in the jam
  const GAP = 1500, V = 1150;
  for (let k = 0; k < 14; k++) {
    const g = car(scene, 0, 0, 0, cols[k % cols.length], true);
    M.cars.push({ g, s0: -9000 + k * GAP });
  }
  // a few westbound cars, free-flowing (the other side of the road is clear)
  for (let k = 0; k < 4; k++) M.cars.push({ g: car(scene, 0, 0, Math.PI, cols[(k + 4) % cols.length], true), w: true, s0: k * 4500 });
  M.carX = (c, t) => {
    if (c.w) { const u = ((c.s0 - 1300 * t) % 18000 + 18000) % 18000 - 9000; return u; }
    const s = ((c.s0 + V * t + 9000) % 18000 + 18000) % 18000 - 9000;
    return jamX(s);
  };
  // a phone marker over every car (sprite) + its soft halo
  const holoPh = () => holo(ICO.phone, 120, O);
  M.cars.forEach((c) => { c.ph = holoPh(); });
  // your car: white, lit, takes the detour
  M.you = car(scene, 0, 0, 0, '#d8d4d0', true);
  M.youPh = holo(ICO.phone, 150, '#ffffff');
  // road overlays: a soft strip down every road, and a red strip over the jam
  const ovM = new TH.MeshBasicMaterial({ color: C('#e9e3dd'), transparent: true, opacity: 0, depthWrite: false, toneMapped: false });
  M.ovM = ovM;
  for (const r of ROADS) {
    const m = new TH.Mesh(new TH.PlaneGeometry(r.ax === 'x' ? 18000 : 36, r.ax === 'x' ? 36 : 18000), ovM);
    m.position.set(r.ax === 'x' ? 0 : r.c, r.ax === 'x' ? r.c : 0, 2); m.renderOrder = 2; scene.add(m); M.ov.push(m);
  }
  M.jamM = new TH.MeshBasicMaterial({ color: C(RED), transparent: true, opacity: 0, depthWrite: false, toneMapped: false });
  M.jamOv = new TH.Mesh(new TH.PlaneGeometry(1, 200), M.jamM); M.jamOv.position.set(0, LANE_E, 2.5); M.jamOv.renderOrder = 3; scene.add(M.jamOv);
  M.setJam = (x0, x1, y, a) => { M.jamOv.scale.x = Math.max(1, x1 - x0); M.jamOv.position.set((x0 + x1) / 2, y, 2.5); M.jamM.opacity = a; };
  // a second red strip for the Berlin street
  M.berM = new TH.MeshBasicMaterial({ color: C(RED), transparent: true, opacity: 0, depthWrite: false, toneMapped: false });
  M.berOv = new TH.Mesh(new TH.PlaneGeometry(1, 120), M.berM); M.berOv.renderOrder = 3; scene.add(M.berOv);
  // city-wide dots: one per phone on the road, moving along its lane (the hero eastbound lane jams like the cars)
  const ND = 420, pos = new Float32Array(ND * 3), col = new Float32Array(ND * 3), meta = [];
  for (let n = 0; n < ND; n++) {
    const r = ROADS[Math.floor(rnd(n, 11) * ROADS.length)], dir = rnd(n, 12) < 0.5 ? 1 : -1;
    meta.push({ r, dir, s0: (rnd(n, 13) - 0.5) * 18000, v: 700 + rnd(n, 14) * 600, b: 0.7 + 0.3 * rnd(n, 15) });
  }
  // extra dots crowded on the hero eastbound lane, so the jam reads as many slow dots
  for (let n = 0; n < 60; n++) meta[n] = { r: { ax: 'x', c: HERO_Y }, dir: 1, hero: true, s0: -9000 + n * 300, v: 1150, b: 0.9 };
  const pg = new TH.BufferGeometry(); pg.setAttribute('position', new TH.BufferAttribute(pos, 3)); pg.setAttribute('color', new TH.BufferAttribute(col, 3));
  M.dots = new TH.Points(pg, new TH.PointsMaterial({ map: TX_SOFT, size: 13, sizeAttenuation: false, vertexColors: true, transparent: true, blending: TH.AdditiveBlending, depthWrite: false, toneMapped: false }));
  M.dots.frustumCulled = false; M.dots.visible = false; scene.add(M.dots);
  // dots: a = brightness 0..1, red = how far the jam dots shift to red, t0 = draw-on start (dots appear outward from the focus)
  M.updDots = (t, a, red = 0, f = [0, 0]) => {
    M.dots.visible = a > 0.01; if (!M.dots.visible) return;
    const p = pos, c = col;
    meta.forEach((m, n) => {
      const s = ((m.s0 + m.dir * m.v * t + 9000) % 18000 + 18000) % 18000 - 9000;
      let x, y;
      if (m.hero) { x = jamX(((m.s0 + 1150 * t + 9000) % 18000 + 18000) % 18000 - 9000); y = LANE_E; }
      else if (m.r.ax === 'x') { x = s; y = m.r.c + (m.dir > 0 ? 140 : -140); }
      else { x = m.r.c + (m.dir > 0 ? -140 : 140); y = s; }
      p[n * 3] = x; p[n * 3 + 1] = y; p[n * 3 + 2] = 120;
      const inJam = m.hero && x > JAM0 && x < JAM1, k = a * m.b, rr = inJam ? red : 0;
      c[n * 3] = k * lerp(2.2, 2.4, rr); c[n * 3 + 1] = k * lerp(1.0, 0.3, rr); c[n * 3 + 2] = k * lerp(0.4, 0.38, rr);
    });
    M.dots.geometry.attributes.position.needsUpdate = true; M.dots.geometry.attributes.color.needsUpdate = true;
  };
  // the artist's little red wagon: a bed full of glowing phones, pulled on a long handle
  const wg = grp(scene), paint = pmat('#b5332a', { r: 0.35, cc: 0.6, env: 0.6 }), dk = mat('#141312', { r: 0.6 });
  mesh(rb(140, 82, 34, 6), paint, wg, 0, 0, 26);
  const phT = ctex(512, 300, (x, w, h) => {
    x.fillStyle = '#100e0d'; x.fillRect(0, 0, w, h);
    for (let i = 0; i < 11; i++) for (let j = 0; j < 9; j++) {
      const px = 14 + i * 44.5, py = 12 + j * 31.5;
      x.fillStyle = '#2a2725'; x.beginPath(); x.roundRect(px, py, 38, 27, 4); x.fill();
      const gr = x.createLinearGradient(px, py, px + 38, py + 27); gr.addColorStop(0, '#ffd0a6'); gr.addColorStop(1, '#ff8a3c');
      x.fillStyle = gr; x.beginPath(); x.roundRect(px + 3, py + 3, 32, 21, 3); x.fill();
      x.fillStyle = 'rgba(255,77,94,0.9)'; x.fillRect(px + 7, py + 12, 24, 4);
    }
  });
  const top = new TH.Mesh(new TH.PlaneGeometry(130, 72), new TH.MeshBasicMaterial({ map: phT, toneMapped: false })); top.position.z = 61; wg.add(top);
  for (const [xx, yy] of [[-48, -44], [48, -44], [-48, 44], [48, 44]]) mesh(cy(13, 13, 8, 16), dk, wg, xx, yy, 13, { rx: Math.PI / 2 });
  const handle = mesh(cy(2.2, 2.2, 150, 8), dk, wg, 0, 0, 0); handle.rotation.set(0, Math.PI / 2 - 0.42, 0); handle.position.set(70, 0, 34);
  M.wagon = wg; M.wagonGlow = new TH.PointLight(C('#ffae6e'), 0, 600, 1.6); scene.add(M.wagonGlow);
  M.artist = person(scene, 0, 0, 0, { seed: 6, shirt: '#3f3b38', coat: true });
  return M;
}
