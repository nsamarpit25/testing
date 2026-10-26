// Three.js version of our ember world, for render(t) pages. Z is up and the camera is an orthographic iso view
// driven by the same shot list as the 2D engine. The world is matte black blocks with glowing edges, real occlusion,
// warm light pools, floor roads with flowing dashes, orbs, sparks and drifting embers. Needs lib/three.js and tools/lib.js.
const TH = window.THREE;
const $ = (id) => document.getElementById(id);
const C = (h) => new TH.Color(h);
const RES = new TH.Vector2(1080, 1920);
const rnd = (i, s = 1) => { const x = Math.sin(i * 127.1 + s * 311.7) * 43758.5453; return x - Math.floor(x); };
const mixHex = (a, b, k) => '#' + new TH.Color(a).lerp(new TH.Color(b), clamp(k)).getHexString();

/* ------------------------------------------------------------------ renderer, scene, camera */
const renderer = new TH.WebGLRenderer({ canvas: $('cv'), antialias: true, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(1); renderer.setSize(1080, 1920, false);
renderer.outputColorSpace = TH.SRGBColorSpace; renderer.toneMapping = TH.NoToneMapping;
renderer.setClearColor(0x0b0a09, 1);
const scene = new TH.Scene();
scene.fog = new TH.Fog(0x0b0a09, 3500, 4700);
const camera = new TH.OrthographicCamera(-1, 1, 1, -1, 10, 6000);
camera.up.set(0, 0, 1);
scene.add(new TH.HemisphereLight(0xb8aca2, 0x0b0a09, 0.75));
const keyL = new TH.DirectionalLight(0xffe2c8, 1.1); keyL.position.set(-400, -700, 1100); scene.add(keyL);
const rimL = new TH.DirectionalLight(0xff8a3d, 0.35); rimL.position.set(600, 500, 300); scene.add(rimL);

const cam = { f: [0, 0, 0], s: 1, a: -0.42, e: 0.6, sy: 480, sx: 270 };
let toCam = [0, 0, 1], camRight = [1, 0, 0];
function camApply() {
  const ca = Math.cos(cam.a), sa = Math.sin(cam.a), ce = Math.cos(cam.e), se = Math.sin(cam.e);
  toCam = [-sa * ce, -ca * ce, se]; camRight = [ca, -sa, 0];
  const R = 3000;
  camera.position.set(cam.f[0] + toCam[0] * R, cam.f[1] + toCam[1] * R, cam.f[2] + toCam[2] * R);
  camera.lookAt(cam.f[0], cam.f[1], cam.f[2]);
  const s = cam.s;
  camera.left = -cam.sx / s; camera.right = (540 - cam.sx) / s; camera.top = cam.sy / s; camera.bottom = -(960 - cam.sy) / s;
  camera.updateProjectionMatrix(); camera.updateMatrixWorld();
}
// shots: [{t,d,f,s,a,e,sy}], kicks: [[t,amp]], shakes: [[t,amp,dur]]
function camAt(t, SHOTS, KICKS = [], SHAKES = []) {
  let cur = { ...SHOTS[0] };
  for (let i = 1; i < SHOTS.length; i++) {
    const k = SHOTS[i];
    if (t < k.t) break;
    const p = k.d ? ease.inOut(prog(t, k.t, k.t + k.d)) : 1;
    const tg = { ...cur, ...k };
    cur = { f: [0, 1, 2].map((j) => lerp(cur.f[j], tg.f[j], p)), s: lerp(cur.s, tg.s, p), a: lerp(cur.a, tg.a, p), e: lerp(cur.e, tg.e, p), sy: lerp(cur.sy, tg.sy, p) };
  }
  let kick = 0;
  for (const [t0, amp] of KICKS) { const dt = t - t0; if (dt > 0 && dt < 1.2) kick += amp * (dt < 0.05 ? dt / 0.05 : Math.exp(-(dt - 0.05) * 6)); }
  let shx = 0, shy = 0;
  for (const [t0, amp, dur] of SHAKES) { const dt = t - t0; if (dt > 0 && dt < dur) { const k = amp * (1 - dt / dur); shx += k * Math.sin(t * 91); shy += k * Math.cos(t * 67); } }
  // a slow breathing drift so no shot is ever fully still
  cam.f = [cur.f[0] + 2 * Math.sin(t * 0.37), cur.f[1] + 2 * Math.cos(t * 0.29), cur.f[2]];
  cam.s = cur.s * (1 + kick); cam.a = cur.a + 0.03 * Math.sin(t * 0.21); cam.e = cur.e; cam.sx = 270 + shx; cam.sy = cur.sy + shy;
  camApply();
}
// world point → stage CSS px (540×960)
const _v = new TH.Vector3();
function P(x, y, z) { _v.set(x, y, z).project(camera); return [(_v.x + 1) * 270, (1 - _v.y) * 480]; }

/* ------------------------------------------------------------------ materials */
const lineMats = [];
function lineMat(col, w, o = {}) {
  const m = new TH.LineMaterial({ color: C(col), linewidth: w, transparent: true, opacity: o.op ?? 1, depthWrite: !o.add, dashed: !!o.dashed,
    dashSize: o.dash || 6, gapSize: o.gap || 10, blending: o.add ? TH.AdditiveBlending : TH.NormalBlending, worldUnits: false, toneMapped: false, fog: true });
  m.resolution.copy(RES); lineMats.push(m); return m;
}
const bodyMat = (col = 0x131110) => new TH.MeshStandardMaterial({ color: col, roughness: 0.62, metalness: 0.15, polygonOffset: true, polygonOffsetFactor: 1.5, polygonOffsetUnits: 2 });
function radialTex(size = 128, stops = [[0, 1], [0.35, 0.45], [1, 0]]) {
  const c = document.createElement('canvas'); c.width = c.height = size; const g = c.getContext('2d');
  const gr = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  for (const [o, a] of stops) gr.addColorStop(o, `rgba(255,255,255,${a})`);
  g.fillStyle = gr; g.fillRect(0, 0, size, size);
  const tx = new TH.CanvasTexture(c); tx.colorSpace = TH.SRGBColorSpace; return tx;
}
const TX_ORB = radialTex(128, [[0, 1], [0.12, 0.9], [0.3, 0.35], [1, 0]]);
const TX_POOL = radialTex(256, [[0, 0.55], [0.4, 0.18], [1, 0]]);
const TX_SOFT = radialTex(128, [[0, 0.75], [0.5, 0.25], [1, 0]]);
const TX_BLOB = radialTex(128, [[0, 0.75], [0.6, 0.3], [1, 0]]);

/* ------------------------------------------------------------------ ember objects */
// a group whose edges glow: core line + soft additive halo. setLook(col, glow, op) recolours everything.
function edgeLines(geo, col, w = 2.6, thresh = 25) {
  const eg = new TH.LineSegmentsGeometry().fromEdgesGeometry(new TH.EdgesGeometry(geo, thresh));
  const core = new TH.LineSegments2(eg, lineMat(col, w));
  const halo = new TH.LineSegments2(eg, lineMat(col, w * 4.2, { add: true, op: 0.16 }));
  halo.renderOrder = 2;
  return { core, halo };
}
function ember(geo, col, o = {}) {
  const g = new TH.Group();
  const mesh = new TH.Mesh(geo, o.mat || bodyMat(o.body));
  g.add(mesh);
  const { core, halo } = edgeLines(geo, col, o.lw || 2.6, o.thresh || 25);
  g.add(core, halo);
  const obj = { g, mesh, core, halo, col, glow: 1, op: 1 };
  obj.setLook = (c, glow = 1, op = 1) => {
    if (c !== obj._c) { obj._c = c; core.material.color.set(c); halo.material.color.set(c); }
    core.material.opacity = op; halo.material.opacity = 0.17 * glow * op;
    mesh.material.transparent = op < 0.999; mesh.material.opacity = op; mesh.visible = op > 0.01; core.visible = halo.visible = op > 0.01;
  };
  (o.parent || scene).add(g);
  return obj;
}
// box with its base at z=0, centred on x/y
function boxGeo(w, d, h) { const geo = new TH.BoxGeometry(w, d, h); geo.translate(0, 0, h / 2); return geo; }
function emberBox(x, y, w, d, h, col, o = {}) { const b = ember(boxGeo(w, d, h), col, o); b.g.position.set(x, y, o.z || 0); b.w = w; b.d = d; b.h = h; return b; }
// a cylinder whose silhouette lines follow the camera (rings at the caps plus two side lines)
function emberCyl(x, y, r, h, col, o = {}) {
  const g = new TH.Group(); g.position.set(x, y, o.z || 0); scene.add(g);
  const geo = new TH.CylinderGeometry(r, r, h, 48, 1); geo.rotateX(Math.PI / 2); geo.translate(0, 0, h / 2);
  const mesh = new TH.Mesh(geo, bodyMat()); g.add(mesh);
  const ring = (z) => { const pts = []; for (let i = 0; i <= 64; i++) { const a = (i / 64) * Math.PI * 2; pts.push(Math.cos(a) * r, Math.sin(a) * r, z); } return pts; };
  const lines = [];
  const mk = (pts, w, add) => { const lg = new TH.LineGeometry(); lg.setPositions(pts); const l = new TH.Line2(lg, lineMat(col, w, add ? { add: true, op: 0.16 } : {})); g.add(l); lines.push(l); return l; };
  const zs = o.bands || [0, h];
  zs.forEach((z) => { mk(ring(z), z === 0 || z === h ? 2.6 : 1.6); mk(ring(z), 10, true); });
  const sideG = new TH.LineSegmentsGeometry(); sideG.setPositions([0, 0, 0, 0, 0, h, 0, 0, 0, 0, 0, h]);
  const side = new TH.LineSegments2(sideG, lineMat(col, 2.6)), sideH = new TH.LineSegments2(sideG, lineMat(col, 10, { add: true, op: 0.16 }));
  g.add(side, sideH); lines.push(side, sideH);
  const obj = { g, mesh, r, h };
  obj.update = () => { const rx = camRight[0] * r, ry = camRight[1] * r; sideG.setPositions([rx, ry, 0, rx, ry, h, -rx, -ry, 0, -rx, -ry, h]); };
  obj.setLook = (c, glow = 1, op = 1) => {
    for (const l of lines) { l.material.color.set(c); l.material.opacity = (l.material.blending === TH.AdditiveBlending ? 0.17 * glow : 1) * op; l.visible = op > 0.01; }
    mesh.visible = op > 0.01; mesh.material.transparent = op < 0.999; mesh.material.opacity = op;
  };
  return obj;
}

/* ------------------------------------------------------------------ face decals (canvas textures) */
// a flat canvas on a face. face: 'front' (-y), 'right' (+x), 'top' (+z). k = canvas px per world unit.
function decal(w, h, face, k = 6, parent = scene) {
  const c = document.createElement('canvas'); c.width = Math.round(w * k); c.height = Math.round(h * k);
  const g = c.getContext('2d');
  const tex = new TH.CanvasTexture(c); tex.colorSpace = TH.SRGBColorSpace; tex.anisotropy = 8;
  const mat = new TH.MeshBasicMaterial({ map: tex, transparent: true, toneMapped: false, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -4 });
  const m = new TH.Mesh(new TH.PlaneGeometry(w, h), mat);
  m.rotation.order = 'ZYX';
  if (face === 'front') m.rotation.set(Math.PI / 2, 0, 0);
  if (face === 'right') m.rotation.set(Math.PI / 2, 0, Math.PI / 2);
  parent.add(m);
  const d = { m, c, g, tex, k, w: c.width, h: c.height };
  d.draw = (fn) => { g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, c.width, c.height); fn(g, c.width, c.height); tex.needsUpdate = true; };
  return d;
}
const ICON = {
  plane: 'M50 8 C55 8 56 16 56 22 L56 40 L90 60 L90 68 L56 58 L55 80 L66 88 L66 94 L50 89 L34 94 L34 88 L45 80 L44 58 L10 68 L10 60 L44 40 L44 22 C44 16 45 8 50 8 Z',
  bed: 'M10 74 L10 30 M10 58 L90 58 L90 74 M10 66 L90 66 M42 58 L42 44 Q42 40 46 40 L84 40 Q90 40 90 46 L90 58 M16 50 Q16 42 24 42 L30 42 Q36 42 36 50 Q36 56 30 56 L22 56 Q16 56 16 50 Z',
  check: 'M24 52 L42 70 L78 32', cross: 'M30 30 L70 70 M70 30 L30 70',
};
const P2 = {}; for (const k in ICON) P2[k] = new Path2D(ICON[k]);
function icon(g, n, x, y, s, col, lw = 7, glow = 0) {
  g.save(); g.translate(x - s / 2, y - s / 2); g.scale(s / 100, s / 100);
  g.strokeStyle = col; g.lineWidth = lw; g.lineCap = 'round'; g.lineJoin = 'round';
  if (glow) { g.shadowColor = col; g.shadowBlur = glow; }
  g.stroke(P2[n]); g.restore();
}
function rrect(g, x, y, w, h, r) { g.beginPath(); g.roundRect(x, y, w, h, r); }

/* ------------------------------------------------------------------ floor, grid, embers */
const floor = new TH.Mesh(new TH.PlaneGeometry(8000, 8000), new TH.MeshStandardMaterial({ color: 0x0c0b0a, roughness: 0.92, metalness: 0 }));
floor.position.z = -0.5; scene.add(floor);
(() => {
  const pts = [], N = 40, S = 60;
  for (let i = -N; i <= N; i++) { pts.push(i * S, -N * S, 0, i * S, N * S, 0, -N * S, i * S, 0, N * S, i * S, 0); }
  const geo = new TH.BufferGeometry(); geo.setAttribute('position', new TH.Float32BufferAttribute(pts, 3));
  const m = new TH.LineSegments(geo, new TH.LineBasicMaterial({ color: 0x2a221c, transparent: true, opacity: 0.55, fog: true }));
  m.position.z = 0.05; scene.add(m);
})();
// light pools: an additive floor glow plus a real point light, so nearby faces pick up the colour too
function pool(x, y, r, col) {
  const m = new TH.Mesh(new TH.PlaneGeometry(r * 2, r * 2), new TH.MeshBasicMaterial({ map: TX_POOL, color: C(col), transparent: true, blending: TH.AdditiveBlending, depthWrite: false, toneMapped: false }));
  m.position.set(x, y, 0.3); scene.add(m);
  const L = new TH.PointLight(C(col), 0, r * 2.2, 1.2); L.position.set(x, y, 40); scene.add(L);
  return { m, L, set(col, a) { m.material.color.set(col); m.material.opacity = a; L.color.set(col); L.intensity = a * 2600; } };
}
// soft contact shadow under an object
function blob(x, y, w, d) {
  const m = new TH.Mesh(new TH.PlaneGeometry(w * 1.5, d * 1.5), new TH.MeshBasicMaterial({ map: TX_BLOB, color: 0x000000, transparent: true, opacity: 0.8, depthWrite: false }));
  m.position.set(x, y, 0.2); scene.add(m); return m;
}
const EMB_N = 160;
const embGeo = new TH.BufferGeometry(); embGeo.setAttribute('position', new TH.Float32BufferAttribute(new Float32Array(EMB_N * 3), 3));
const embers = new TH.Points(embGeo, new TH.PointsMaterial({ map: TX_SOFT, color: C('#FFB070'), size: 5, sizeAttenuation: false, transparent: true, opacity: 0.5, blending: TH.AdditiveBlending, depthWrite: false, toneMapped: false }));
scene.add(embers);
function updateEmbers(t) {
  const a = embGeo.attributes.position.array;
  for (let i = 0; i < EMB_N; i++) {
    const life = 7 + rnd(i, 3) * 5, ph = ((t + rnd(i, 4) * life) % life) / life;
    a[i * 3] = cam.f[0] + (rnd(i, 1) - 0.5) * 900 + Math.sin(t * 0.6 + i) * 10;
    a[i * 3 + 1] = cam.f[1] + (rnd(i, 2) - 0.5) * 900;
    a[i * 3 + 2] = ph * 260;
  }
  embGeo.attributes.position.needsUpdate = true;
}

/* ------------------------------------------------------------------ roads, orbs, sparks */
const lerp3 = (a, b, q) => [lerp(a[0], b[0], q), lerp(a[1], b[1], q), lerp(a[2], b[2], q)];
const segs = (pts) => { const L = []; let tot = 0; for (let i = 0; i < pts.length - 1; i++) { const d = Math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1], pts[i + 1][2] - pts[i][2]); L.push(d); tot += d; } return [L, tot]; };
function along(pts, q) {
  const [L, tot] = segs(pts); let s = clamp(q) * tot;
  for (let i = 0; i < L.length; i++) { if (s <= L[i] || i === L.length - 1) return lerp3(pts[i], pts[i + 1], L[i] ? clamp(s / L[i]) : 0); s -= L[i]; }
  return pts[pts.length - 1];
}
function sub(pts, q) {
  if (q >= 1) return pts;
  const [L, tot] = segs(pts); let s = Math.max(0.001, q) * tot; const out = [pts[0]];
  for (let i = 0; i < L.length; i++) { if (s <= L[i]) { out.push(lerp3(pts[i], pts[i + 1], L[i] ? s / L[i] : 0)); return out; } out.push(pts[i + 1]); s -= L[i]; }
  return out;
}
// a glowing floor road: wide soft glow, thin base line and bright dashes that flow along it
function road(pts, col) {
  const mk = (w, o) => { const l = new TH.Line2(new TH.LineGeometry(), lineMat(col, w, o)); l.renderOrder = 1; scene.add(l); return l; };
  const r = { pts, glow: mk(14, { add: true, op: 0.12 }), base: mk(1.6, { op: 0.5 }), dash: mk(3.2, { dashed: true, dash: 5, gap: 9 }), _q: -1 };
  r.set = (q, col, a, t) => {
    const on = a > 0.01 && q > 0.002;
    for (const l of [r.glow, r.base, r.dash]) l.visible = on;
    if (!on) return;
    if (Math.abs(q - r._q) > 1e-4) {
      r._q = q; const flat = sub(r.pts, q).flatMap((p) => [p[0], p[1], p[2] + 0.8]);
      for (const l of [r.glow, r.base, r.dash]) { l.geometry.dispose(); l.geometry = new TH.LineGeometry(); l.geometry.setPositions(flat); l.computeLineDistances(); }
    }
    for (const l of [r.glow, r.base, r.dash]) l.material.color.set(col);
    r.glow.material.opacity = 0.13 * a; r.base.material.opacity = 0.5 * a; r.dash.material.opacity = 0.95 * a;
    r.dash.material.dashOffset = -t * 30;
  };
  return r;
}
// orb pool: a bright core sprite, a wide glow sprite, and a short trail
const ORBS = [];
function orbSprite(scale) { const s = new TH.Sprite(new TH.SpriteMaterial({ map: TX_ORB, color: 0xffffff, transparent: true, blending: TH.AdditiveBlending, depthWrite: false, toneMapped: false })); s.scale.set(scale, scale, 1); s.visible = false; scene.add(s); return s; }
for (let i = 0; i < 10; i++) ORBS.push({ core: orbSprite(9), glow: orbSprite(34), trail: [0, 1, 2, 3, 4].map(() => orbSprite(10)) });
let orbI = 0;
function orbsReset() { orbI = 0; for (const o of ORBS) { o.core.visible = o.glow.visible = false; o.trail.forEach((s) => (s.visible = false)); } }
function orb(pts, q, col, a = 1, size = 1) {
  if (a <= 0.01 || orbI >= ORBS.length) return null;
  const o = ORBS[orbI++], p = along(pts, q);
  o.core.visible = o.glow.visible = true;
  o.core.position.set(...p); o.glow.position.set(...p);
  o.core.material.color.set(mixHex(col, '#ffffff', 0.65)); o.core.material.opacity = a; o.core.scale.set(10 * size, 10 * size, 1);
  o.glow.material.color.set(col); o.glow.material.opacity = 0.85 * a; o.glow.scale.set(40 * size, 40 * size, 1);
  o.trail.forEach((s, k) => {
    const qq = q - (k + 1) * 0.022; s.visible = qq > 0;
    if (!s.visible) return;
    s.position.set(...along(pts, qq)); s.material.color.set(col); s.material.opacity = a * 0.6 * (1 - k / 5); const z = (9 - k) * size; s.scale.set(z, z, 1);
  });
  return p;
}
const SPK_N = 240;
const spkGeo = new TH.BufferGeometry();
spkGeo.setAttribute('position', new TH.Float32BufferAttribute(new Float32Array(SPK_N * 3), 3));
spkGeo.setAttribute('color', new TH.Float32BufferAttribute(new Float32Array(SPK_N * 3), 3));
const sparksPts = new TH.Points(spkGeo, new TH.PointsMaterial({ map: TX_SOFT, size: 7, sizeAttenuation: false, vertexColors: true, transparent: true, blending: TH.AdditiveBlending, depthWrite: false, toneMapped: false }));
scene.add(sparksPts);
let spkI = 0;
const _sc = new TH.Color();
function sparksReset() { spkI = 0; }
function sparks(t, t0, x, y, z, col, n, seed, spd = 150, life = 0.8, grav = 240) {
  const dt = t - t0; if (dt <= 0 || dt > life) return;
  const a = spkGeo.attributes.position.array, c = spkGeo.attributes.color.array; _sc.set(col);
  for (let i = 0; i < n && spkI < SPK_N; i++, spkI++) {
    const th = rnd(i, seed) * Math.PI * 2, up = 0.4 + rnd(i, seed + 1) * 1.0, v = spd * (0.4 + rnd(i, seed + 2) * 0.8), k = 1 - dt / life;
    a[spkI * 3] = x + Math.cos(th) * v * dt; a[spkI * 3 + 1] = y + Math.sin(th) * v * dt; a[spkI * 3 + 2] = Math.max(0, z + up * v * dt - grav * dt * dt);
    c[spkI * 3] = _sc.r * k * 1.4; c[spkI * 3 + 1] = _sc.g * k * 1.4; c[spkI * 3 + 2] = _sc.b * k * 1.4;
  }
}
function sparksFlush() {
  const a = spkGeo.attributes.position.array;
  for (let i = spkI; i < SPK_N; i++) a[i * 3 + 2] = -9999;
  spkGeo.attributes.position.needsUpdate = true; spkGeo.attributes.color.needsUpdate = true;
}
// expanding floor ring (taps, arrivals)
const RINGS = [];
for (let i = 0; i < 6; i++) { const m = new TH.Mesh(new TH.RingGeometry(0.86, 1, 64), new TH.MeshBasicMaterial({ color: 0xffffff, transparent: true, blending: TH.AdditiveBlending, depthWrite: false, toneMapped: false, side: TH.DoubleSide })); m.visible = false; scene.add(m); RINGS.push(m); }
let ringI = 0;
function ringsReset() { ringI = 0; RINGS.forEach((m) => (m.visible = false)); }
function ripple(t, t0, x, y, z, col, maxR, dur = 0.7) {
  const p = prog(t, t0, t0 + dur); if (p <= 0 || p >= 1 || ringI >= RINGS.length) return;
  const m = RINGS[ringI++], r = 6 + maxR * ease.out(p);
  m.visible = true; m.position.set(x, y, z); m.scale.set(r, r, 1); m.material.color.set(col); m.material.opacity = (1 - p) * 0.9;
}

/* ------------------------------------------------------------------ DOM helpers (same as the 2D pages) */
function div(parent, cls, html, style) { const d = document.createElement('div'); if (cls) d.className = cls; if (html != null) d.innerHTML = html; if (style) d.style.cssText = style; parent.appendChild(d); return d; }
function vis(elm, a, extra = '') { elm.style.display = a > 0.001 ? '' : 'none'; elm.style.opacity = a; if (extra !== null) elm.style.transform = extra; }
const popIn = (t, a, b, d = 0.3) => { const i = ease.back(prog(t, a, a + d)), o = ep(t, b - 0.22, b, ease.in); return { a: t < a ? 0 : Math.min(1, prog(t, a, a + 0.12)) * (1 - o), s: t < a ? 0.8 : lerp(0.8, 1, i) - o * 0.06, y: (1 - Math.min(1, i)) * 12 + o * -8 }; };
const LB = {};
function tag(key, html, style, wp, t, a, b, dy = 0) {
  if (!LB[key]) LB[key] = div($('lbls'), 'lbl');
  const e = LB[key];
  if (e._h !== html) { e._h = html; e.innerHTML = html; }
  if (e._st !== style) { e._st = style; e.style.cssText = style; }
  const pp = popIn(t, a, b);
  if (pp.a <= 0.001) { e.style.display = 'none'; return e; }
  const p = P(...wp); e.style.left = p[0] + 'px'; e.style.top = p[1] + dy + 'px';
  vis(e, pp.a, `translate(-50%,-50%) scale(${pp.s})`);
  return e;
}
