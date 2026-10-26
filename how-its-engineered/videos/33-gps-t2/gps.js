// 33 GPS: the pieces this reel adds to the AirTag kit. A space zone far east of the city: a night Earth with
// procedural continents and warm city lights, 30 GPS satellites on six inclined orbits (gold-foil body, two solar
// wings, an antenna that faces the Earth, a clock light), a star backdrop, distance spheres around four hero
// satellites and the circles where those spheres cut the Earth's surface. Plus a small studio with the hero phone.
// The spot Q (where "you" are) turns with the Earth; the four hero satellites sit around it at TREF.
Z.SPC = [70000, 0];
const EC = [70000, 0, 0], ER = 2200, ORB = 6200, INC = 55 * Math.PI / 180, W_SAT = 0.012, W_EARTH = 0.008, TREF = 23;
const v3 = {
  add: (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]], sub: (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]],
  mul: (a, k) => [a[0] * k, a[1] * k, a[2] * k], dot: (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2],
  cross: (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]],
  len: (a) => Math.hypot(a[0], a[1], a[2]), norm: (a) => { const l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; },
  rotZ: (a, r) => [a[0] * Math.cos(r) - a[1] * Math.sin(r), a[0] * Math.sin(r) + a[1] * Math.cos(r), a[2]],
};
// where you are, as a direction from the Earth's centre at TREF; Q(t) turns with the Earth
const QD = v3.norm([0.5, -0.62, 0.62]);
const QAt = (t, lift = 0) => v3.add(EC, v3.mul(v3.rotZ(QD, W_EARTH * (t - TREF)), ER + lift));

/* ---------------- Earth */
function earthTex() {
  const W = 1024, H = 512, h3 = (x, y, z) => { const s = Math.sin(x * 127.1 + y * 311.7 + z * 74.7) * 43758.5453; return s - Math.floor(s); };
  const sm = (u) => u * u * (3 - 2 * u);
  const vn = (x, y, z) => {
    const xi = Math.floor(x), yi = Math.floor(y), zi = Math.floor(z), u = sm(x - xi), v = sm(y - yi), w = sm(z - zi);
    const L = (a, b, k) => a + (b - a) * k;
    return L(L(L(h3(xi, yi, zi), h3(xi + 1, yi, zi), u), L(h3(xi, yi + 1, zi), h3(xi + 1, yi + 1, zi), u), v),
      L(L(h3(xi, yi, zi + 1), h3(xi + 1, yi, zi + 1), u), L(h3(xi, yi + 1, zi + 1), h3(xi + 1, yi + 1, zi + 1), u), v), w);
  };
  const fbm = (x, y, z) => { let a = 0.5, s = 0; for (let o = 0; o < 4; o++) { s += a * vn(x, y, z); x *= 2.03; y *= 2.03; z *= 2.03; a *= 0.5; } return s; };
  const mk = () => { const c = document.createElement('canvas'); c.width = W; c.height = H; return c; };
  const c = mk(), e = mk(), g = c.getContext('2d'), ge = e.getContext('2d'), im = g.createImageData(W, H), ie = ge.createImageData(W, H);
  for (let y = 0; y < H; y++) {
    const lat = (0.5 - (y + 0.5) / H) * Math.PI, cl = Math.cos(lat), sl = Math.sin(lat);
    for (let x = 0; x < W; x++) {
      const lon = ((x + 0.5) / W) * Math.PI * 2 - Math.PI, px = cl * Math.cos(lon), py = cl * Math.sin(lon), pz = sl;
      const n = fbm(px * 2.1 + 7, py * 2.1 + 3, pz * 2.1 + 11), land = n > 0.52, i = (y * W + x) * 4, ice = Math.abs(lat) > 1.25;
      let r, gg, b;
      if (ice) { r = 70; gg = 68; b = 66; }
      else if (land) { const k = Math.min(1, (n - 0.52) * 6); r = 52 + 22 * k; gg = 46 + 18 * k; b = 40 + 12 * k; if (n < 0.535) { r += 14; gg += 10; b += 6; } }
      else { const k = n / 0.52; r = 14 + 8 * k; gg = 17 + 8 * k; b = 21 + 8 * k; }
      im.data[i] = r; im.data[i + 1] = gg; im.data[i + 2] = b; im.data[i + 3] = 255;
      const lit = land && !ice && h3(x, y, 5) < 0.05 + 0.12 * Math.max(0, 0.6 - n) ? 1 : 0;
      ie.data[i] = 255 * lit; ie.data[i + 1] = 140 * lit; ie.data[i + 2] = 60 * lit; ie.data[i + 3] = 255;
    }
  }
  g.putImageData(im, 0, 0); ge.putImageData(ie, 0, 0);
  g.strokeStyle = 'rgba(255,196,160,0.07)'; g.lineWidth = 1.2;
  for (let k = 1; k < 12; k++) { g.beginPath(); g.moveTo(0, k * H / 12); g.lineTo(W, k * H / 12); g.stroke(); }
  for (let k = 0; k < 24; k++) { g.beginPath(); g.moveTo(k * W / 24, 0); g.lineTo(k * W / 24, H); g.stroke(); }
  const T = (cv) => { const t = new TH.CanvasTexture(cv); t.colorSpace = TH.SRGBColorSpace; t.anisotropy = 8; return t; };
  return { map: T(c), lights: T(e) };
}

/* ---------------- a GPS satellite: +z faces the Earth */
const PANEL_TX = ctex(256, 512, (x, w, h) => {
  x.fillStyle = '#16191c'; x.fillRect(0, 0, w, h);
  for (let i = 0; i < 4; i++) for (let j = 0; j < 8; j++) { x.fillStyle = (i + j) % 3 ? '#1f2328' : '#23282e'; x.fillRect(i * 64 + 4, j * 64 + 4, 56, 56); }
  x.strokeStyle = 'rgba(214,170,110,0.55)'; x.lineWidth = 3; x.strokeRect(2, 2, w - 4, h - 4);
});
function gpsSat() {
  const g = new TH.Group(); scene.add(g);
  const foil = pmat('#c08a3e', { r: 0.34, m: 1, env: 1.1 }), dark = pmat('#232120', { r: 0.45, m: 0.5, env: 0.8 }), white = pmat('#cfcac5', { r: 0.5, env: 0.6 });
  mesh(rbc(170, 150, 210, 14, 3), foil, g);
  mesh(rbc(176, 156, 14, 4), white, g, 0, 0, -100);
  mesh(cy(58, 70, 50, 32), dark, g, 0, 0, 104);
  for (let k = 0; k < 8; k++) { const a = k / 8 * Math.PI * 2; mesh(cy(9, 13, 34, 12), white, g, Math.cos(a) * 40, Math.sin(a) * 40, 150); }
  mesh(cy(12, 16, 40, 12), white, g, 0, 0, 150);
  const pm = texM(PANEL_TX, { r: 0.3, m: 0.4 });
  for (const s of [-1, 1]) {
    mesh(rbc(80, 8, 8, 2), dark, g, s * 125, 0, 0);
    mesh(rbc(170, 5, 360, 3), pm, g, s * 255, 0, 0);
    mesh(rbc(170, 5, 360, 3), pm, g, s * 435, 0, 0);
  }
  const clockM = glowM(AMB, 2.5); mesh(rbc(90, 4, 16, 3), clockM, g, 0, -76, -40, { cast: false });
  const glow = new TH.Sprite(new TH.SpriteMaterial({ map: TX_ORB, color: C(O), transparent: true, blending: TH.AdditiveBlending, depthWrite: false, toneMapped: false }));
  glow.renderOrder = 4; scene.add(glow);
  return { g, glow, clockM };
}

function buildSpace() {
  const S = { sats: [], planes: [] };
  const tx = earthTex();
  S.earthM = new TH.MeshStandardMaterial({ map: tx.map, emissiveMap: tx.lights, emissive: C('#ffffff'), emissiveIntensity: 1.3, roughness: 0.9 });
  const eg = new TH.SphereGeometry(ER, 128, 80); eg.rotateX(Math.PI / 2);
  S.earth = new TH.Mesh(eg, S.earthM); S.earth.position.set(...EC); S.earth.receiveShadow = true; scene.add(S.earth);
  // a thin warm rim of atmosphere (camera-facing sprite)
  const atm = ctex(512, 512, (x, w) => {
    const gr = x.createRadialGradient(w / 2, w / 2, 0, w / 2, w / 2, w / 2);
    gr.addColorStop(0, 'rgba(255,150,90,0)'); gr.addColorStop(0.84, 'rgba(255,150,90,0)'); gr.addColorStop(0.885, 'rgba(255,170,110,0.32)'); gr.addColorStop(0.9, 'rgba(255,150,90,0.16)'); gr.addColorStop(1, 'rgba(255,150,90,0)');
    x.fillStyle = gr; x.fillRect(0, 0, w, w);
  });
  S.atm = new TH.Sprite(new TH.SpriteMaterial({ map: atm, transparent: true, blending: TH.AdditiveBlending, depthWrite: false, toneMapped: false }));
  S.atm.scale.set(ER * 2 / 0.892, ER * 2 / 0.892, 1); S.atm.position.set(...EC); S.atm.renderOrder = 3; scene.add(S.atm);
  // stars: a backdrop behind the Earth, as seen from the space shots' camera
  const toC = v3.norm([0.57, -0.67, 0.48]), right = v3.norm(v3.cross([0, 0, 1], toC)), up = v3.cross(toC, right);
  const NS = 1400, sp = new Float32Array(NS * 3), sc = new Float32Array(NS * 3);
  for (let n = 0; n < NS; n++) {
    const p = v3.add(v3.add(v3.add(EC, v3.mul(toC, -16000 - 4000 * rnd(n, 3))), v3.mul(right, (rnd(n, 1) - 0.5) * 70000)), v3.mul(up, (rnd(n, 2) - 0.5) * 90000));
    sp.set(p, n * 3); const k = 0.25 + 0.75 * Math.pow(rnd(n, 4), 3); sc.set([k * 1.1, k, k * 0.92], n * 3);
  }
  const sg = new TH.BufferGeometry(); sg.setAttribute('position', new TH.BufferAttribute(sp, 3)); sg.setAttribute('color', new TH.BufferAttribute(sc, 3));
  S.stars = new TH.Points(sg, new TH.PointsMaterial({ map: TX_SOFT, size: 5, sizeAttenuation: false, vertexColors: true, transparent: true, blending: TH.AdditiveBlending, depthWrite: false, toneMapped: false }));
  S.stars.frustumCulled = false; scene.add(S.stars);
  // four hero satellites sit around Q at TREF; each gets its own orbital plane (inclination 55°), two more planes fill in
  const t1 = v3.norm(v3.cross([0, 0, 1], QD)), t2 = v3.cross(QD, t1), B = 38 * Math.PI / 180;
  const HERO = [130, 40, 310, 220].map((d) => { const f = d * Math.PI / 180; return v3.norm(v3.add(v3.mul(QD, Math.cos(B)), v3.mul(v3.add(v3.mul(t1, Math.cos(f)), v3.mul(t2, Math.sin(f))), Math.sin(B)))); });
  const basis = (Om) => [[Math.cos(Om), Math.sin(Om), 0], [-Math.sin(Om) * Math.cos(INC), Math.cos(Om) * Math.cos(INC), Math.sin(INC)]];
  const planes = HERO.map((D) => {
    const A = Math.hypot(D[0], D[1]), psi = Math.atan2(D[1], D[0]), c = clamp(-D[2] / Math.tan(INC) / A, -1, 1), Om = psi + Math.asin(c);
    const [n, m] = basis(Om); return { Om, n, m, th: Math.atan2(v3.dot(D, m), v3.dot(D, n)) };
  });
  for (const k of [0, 1]) { const Om = planes[k].Om + Math.PI, [n, m] = basis(Om); planes.push({ Om, n, m, th: 0.6 * k + 0.3 }); }
  planes.forEach((p, pi) => {
    for (let j = 0; j < 5; j++) {
      const s = gpsSat(); s.plane = p; s.th0 = p.th + j * Math.PI * 2 / 5 + (pi >= 4 ? Math.PI / 5 : 0) - W_SAT * TREF; s.hero = pi < 4 && j === 0 ? pi : -1;
      S.sats.push(s);
    }
    const pts = []; for (let k = 0; k <= 128; k++) { const a = k / 128 * Math.PI * 2; pts.push(...v3.add(EC, v3.add(v3.mul(p.n, ORB * Math.cos(a)), v3.mul(p.m, ORB * Math.sin(a))))); }
    const geo = new TH.LineGeometry(); geo.setPositions(pts);
    const L = new TH.Line2(geo, lineMat('#a69a90', 1.3, { op: 0.32 })); L.frustumCulled = false; scene.add(L); S.planes.push(L);
  });
  S.hero = [0, 1, 2, 3].map((k) => S.sats.find((s) => s.hero === k));
  S.satPos = (s, t) => { const a = s.th0 + W_SAT * t; return v3.add(EC, v3.add(v3.mul(s.plane.n, ORB * Math.cos(a)), v3.mul(s.plane.m, ORB * Math.sin(a)))); };
  S.heroAt = (k, t) => S.satPos(S.hero[k], t);
  // distance spheres (latitude / longitude lines only) and their circles on the Earth's surface
  const sphLines = (() => {
    const v = [];
    for (let i = 1; i < 12; i++) { const la = -Math.PI / 2 + i * Math.PI / 12, z = Math.sin(la), r = Math.cos(la); for (let k = 0; k < 64; k++) { const a0 = k / 64 * Math.PI * 2, a1 = (k + 1) / 64 * Math.PI * 2; v.push(r * Math.cos(a0), r * Math.sin(a0), z, r * Math.cos(a1), r * Math.sin(a1), z); } }
    for (let i = 0; i < 16; i++) { const lo = i / 16 * Math.PI * 2; for (let k = 0; k < 32; k++) { const b0 = -Math.PI / 2 + k / 32 * Math.PI, b1 = b0 + Math.PI / 32; v.push(Math.cos(b0) * Math.cos(lo), Math.cos(b0) * Math.sin(lo), Math.sin(b0), Math.cos(b1) * Math.cos(lo), Math.cos(b1) * Math.sin(lo), Math.sin(b1)); } }
    const g = new TH.BufferGeometry(); g.setAttribute('position', new TH.Float32BufferAttribute(v, 3)); return g;
  })();
  const sphFill = new TH.SphereGeometry(1, 64, 40);
  const CN = 96;
  S.spheres = [0, 1, 2, 3].map(() => {
    const wm = new TH.LineBasicMaterial({ color: C(O), transparent: true, opacity: 0, blending: TH.AdditiveBlending, depthWrite: false, toneMapped: false });
    const fm = new TH.MeshBasicMaterial({ color: C(O), transparent: true, opacity: 0, blending: TH.AdditiveBlending, depthWrite: false, toneMapped: false });
    const w = new TH.LineSegments(sphLines, wm), f = new TH.Mesh(sphFill, fm); w.frustumCulled = f.frustumCulled = false; w.renderOrder = f.renderOrder = 2;
    scene.add(w); scene.add(f);
    const geo = new TH.LineGeometry(); geo.setPositions(new Array((CN + 1) * 3).fill(0).map((_, k) => k));
    const core = new TH.Line2(geo, lineMat(O, 3.2)), halo = new TH.Line2(geo, lineMat(O, 10, { add: true, op: 0.18 }));
    for (const l of [core, halo]) { l.frustumCulled = false; l.visible = false; l.renderOrder = 6; scene.add(l); }
    return { w, f, wm, fm, geo, core, halo };
  });
  // sphere k: around satellite position Sp with radius |Sp - Q|; r = 0..1 grown, a = opacity; circle drawn to fraction c
  S.sphere = (k, Sp, Q, r, a, c, ca = 1) => {
    const o = S.spheres[k], d = v3.len(v3.sub(Sp, Q)), R = Math.max(1, d * r);
    o.w.visible = o.f.visible = a > 0.01 && r > 0.001;
    o.w.position.set(...Sp); o.f.position.set(...Sp); o.w.scale.setScalar(R); o.f.scale.setScalar(R); o.wm.opacity = 0.16 * a; o.fm.opacity = 0.035 * a;
    o.core.visible = o.halo.visible = c > 0.001 && ca > 0.01;
    if (!o.core.visible) return;
    const s = v3.sub(Sp, EC), rs = v3.len(s), sh = v3.norm(s), q = v3.sub(Q, EC), h = (ER * ER + rs * rs - d * d) / (2 * rs), rho = Math.sqrt(Math.max(0, ER * ER - h * h));
    const a1 = v3.norm(v3.sub(q, v3.mul(sh, v3.dot(q, sh)))), a2 = v3.cross(sh, a1), arr = o.geo.attributes.instanceStart.data.array, n = Math.max(1, Math.round(CN * c));
    const pt = (u) => { const p = v3.add(v3.mul(sh, h), v3.add(v3.mul(a1, rho * Math.cos(u)), v3.mul(a2, rho * Math.sin(u)))); return v3.add(EC, v3.mul(v3.norm(p), ER + 12)); };
    // drawn on both ways from the point opposite Q, so it closes on Q
    let prev = pt(Math.PI - c * Math.PI);
    for (let i = 1; i <= n; i++) { const u = Math.PI - c * Math.PI + (i / n) * 2 * Math.PI * c, p = pt(u); arr.set([...prev, ...p], (i - 1) * 6); prev = p; }
    o.geo.attributes.instanceStart.data.needsUpdate = true; o.geo.instanceCount = n;
    o.core.material.opacity = ca; o.halo.material.opacity = 0.18 * ca;
  };
  S.update = (t, o) => {
    const px = 1 / cam.s;
    S.sats.forEach((s, k) => {
      const p = S.satPos(s, t); s.g.position.set(...p); s.g.lookAt(EC[0], EC[1], EC[2]);
      s.glow.position.set(...p); const gk_ = (o.glow ?? 1) * (0.7 + 0.3 * Math.sin(t * 2.2 + k * 1.7)) * (s.pop ?? 1);
      s.glow.visible = gk_ > 0.01; s.glow.material.opacity = gk_; s.glow.scale.set(30 * px * (o.glowK ?? 1), 30 * px * (o.glowK ?? 1), 1);
      s.g.visible = (s.pop ?? 1) > 0.01; s.g.scale.setScalar(Math.max(0.01, s.pop ?? 1));
      s.clockM.emissiveIntensity = 1.5 + 2.5 * Math.exp(-((t % 1) * 6));
    });
    S.earth.rotation.z = W_EARTH * (t - TREF);
  };
  return S;
}

/* ---------------- the phone studio */
function buildPhoneStudio() {
  const g = grp(scene, ...Z.STU);
  mesh(cy(2800, 2800, 20, 96), mat('#161514', { r: 0.9 }), g, 0, 0, -20);
  const fl = ctex(1024, 1024, (x, w, h) => { x.fillStyle = '#000'; x.fillRect(0, 0, w, h); x.strokeStyle = 'rgba(206,186,169,0.05)'; x.lineWidth = 2; for (let i = 0; i <= 32; i++) { x.beginPath(); x.moveTo(i * 32, 0); x.lineTo(i * 32, h); x.moveTo(0, i * 32); x.lineTo(w, i * 32); x.stroke(); } });
  plane(g, 5600, 5600, new TH.MeshBasicMaterial({ map: fl, transparent: true, blending: TH.AdditiveBlending, depthWrite: false, toneMapped: false }), 0, 0, 0.2);
  glowSpot(g, 0, 0, 0.5, 420, O, 0.08);
  return phoneStand(g, 0, 0, '#2d2b29', 'ios');
}
