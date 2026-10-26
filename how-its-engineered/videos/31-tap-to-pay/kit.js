// Solid low-poly 3D kit for the scene reels (29 AirTag first). Upgrades the ember renderer to real lighting (soft
// shadows that follow the camera, ACES tone mapping, a dim room environment for reflections, bloom) and builds props
// from rounded boxes, cylinders and capsules: rooms, furniture, posable people, phones with live canvas screens,
// suitcases, an AirTag that can explode into its parts, city blocks with lit windows, server racks, an airport carousel.
// Units are centimetres, z is up. Load after world.js and base.js.

/* ------------------------------------------------------------------ renderer upgrade */
renderer.shadowMap.enabled = true; renderer.shadowMap.type = TH.PCFSoftShadowMap;
renderer.toneMapping = TH.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.0;
scene.fog = null;
// an explicit background makes three clear in the composer's linear target every frame; without it RenderPass clears
// with the colour left over from the last screen pass (already sRGB-encoded), which lifts the blacks to grey after frame 0
scene.background = new TH.Color(0x0b0a09); renderer.setClearColor(0x0b0a09, 1);
scene.children.filter((o) => o.isLineSegments && !o.isLineSegments2).forEach((o) => scene.remove(o));
floor.visible = false; embers.visible = false;
scene.environment = new TH.PMREMGenerator(renderer).fromScene(new TH.RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.3;
// product-shot reflections for the hero props: soft white boxes and one warm strip on black, so gloss and metal
// pick up clean highlights instead of the dim room. Applied per material (envMap), never to the whole city.
const STUDIO_ENV = (() => {
  const s = new TH.Scene(); s.background = new TH.Color(0x030303);
  const box = (w, h, x, y, z, r, g, b) => { const m = new TH.Mesh(new TH.PlaneGeometry(w, h), new TH.MeshBasicMaterial({ color: new TH.Color(r, g, b), side: TH.DoubleSide })); m.position.set(x, y, z); m.lookAt(0, 0, 0); s.add(m); };
  // a graded dome: bright overhead falling off to a dark horizon, a thin bright horizon band for chrome edges, black below
  const dome = new TH.SphereGeometry(20, 64, 32), P = dome.attributes.position, col = [];
  for (let i = 0; i < P.count; i++) { const z = P.getY(i) / 20, k = z > 0 ? 0.05 + 0.55 * Math.pow(z, 1.3) : 0.012; const band = Math.exp(-Math.pow((z - 0.06) / 0.035, 2)) * 0.9; col.push(k + band, k + band, k + band); }
  dome.setAttribute('color', new TH.Float32BufferAttribute(col, 3)); dome.rotateX(Math.PI / 2);
  s.add(new TH.Mesh(dome, new TH.MeshBasicMaterial({ vertexColors: true, side: TH.BackSide })));
  box(6, 3.5, -6, -7, 8, 2.4, 2.4, 2.4);      // key softbox, front left, high
  box(10, 0.9, 8, 1, 4, 1.6, 1.6, 1.6);       // strip, right
  box(14, 0.6, -2, 10, 2.2, 2.6, 1.05, 0.38);  // warm rim strip behind
  return new TH.PMREMGenerator(renderer).fromScene(s, 0.02).texture;
})();
// a physical material lit by the studio environment (gloss plastic, glass, polished or brushed metal)
const _pm = {};
function pmat(col, o = {}) {
  const k = col + JSON.stringify(o);
  if (_pm[k]) return _pm[k];
  const m = new TH.MeshPhysicalMaterial({ color: C(col), roughness: o.r ?? 0.3, metalness: o.m ?? 0, clearcoat: o.cc ?? 0, clearcoatRoughness: o.ccr ?? 0.08, envMap: STUDIO_ENV, envMapIntensity: o.env ?? 1 });
  if (o.e) { m.emissive = C(o.e); m.emissiveIntensity = o.ei ?? 1; }
  return (_pm[k] = m);
}
scene.children.forEach((o) => { if (o.isHemisphereLight) { o.color.set('#a8a4a0'); o.groundColor.set('#141313'); o.intensity = 1.1; } });
keyL.color.set('#f5f1ee'); keyL.intensity = 1.75; keyL.castShadow = true;
keyL.shadow.mapSize.set(4096, 4096); keyL.shadow.bias = -0.0002; keyL.shadow.normalBias = 1.5; keyL.shadow.radius = 4;
scene.add(keyL.target);
rimL.color.set('#a28e7d'); rimL.intensity = 0.65;
const KEYDIR = new TH.Vector3(-0.45, -0.7, 1).normalize();
// the shadow camera's screen axes (lookAt with the default +y up), for snapping its box to whole texels
const SH_X = new TH.Vector3(0, 1, 0).cross(KEYDIR).normalize(), SH_Y = KEYDIR.clone().cross(SH_X).normalize();

const COMP_RT = new TH.WebGLRenderTarget(1080, 1920, { type: TH.HalfFloatType, samples: 4 });
const composer = new TH.EffectComposer(renderer, COMP_RT);
composer.addPass(new TH.RenderPass(scene, camera));
const bloom = new TH.UnrealBloomPass(new TH.Vector2(540, 960), 0.5, 0.32, 1.0);
composer.addPass(bloom);
composer.addPass(new TH.OutputPass());
const _rawRender = renderer.render.bind(renderer);
let _inComp = false;
renderer.render = (s, c) => { if (_inComp || s !== scene) return _rawRender(s, c); _inComp = true; composer.render(); _inComp = false; };

// camera: like camAt, but the scale eases in log space (big zoom-outs feel even) and the eye sits far back so a whole
// city fits between the near and far planes. Shot fields: t, d (0 = cut), f, s, a, e, sy, ez (easing).
function cam3(t, SHOTS, KICKS = [], SHAKES = []) {
  let cur = { ...SHOTS[0] }, cs = SHOTS[0].s;
  for (let i = 1; i < SHOTS.length; i++) {
    const k = SHOTS[i];
    if (t < k.t) break;
    if (!k.d || k.g) cs = k.s;
    const p = k.d ? (k.ez || ease.inOut)(prog(t, k.t, k.t + k.d)) : 1;
    const tg = { ...cur, ...k };
    cur = { f: [0, 1, 2].map((j) => lerp(cur.f[j], tg.f[j], p)), s: Math.exp(lerp(Math.log(cur.s), Math.log(tg.s), p)), a: lerp(cur.a, tg.a, p), e: lerp(cur.e, tg.e, p), sy: lerp(cur.sy, tg.sy, p) };
  }
  let kick = 0;
  for (const [t0, amp] of KICKS) { const dt = t - t0; if (dt > 0 && dt < 1.2) kick += amp * (dt < 0.05 ? dt / 0.05 : Math.exp(-(dt - 0.05) * 6)); }
  let shx = 0, shy = 0;
  for (const [t0, amp, dur] of SHAKES) { const dt = t - t0; if (dt > 0 && dt < dur) { const k = amp * (1 - dt / dur); shx += k * Math.sin(t * 91); shy += k * Math.cos(t * 67); } }
  cam.f = cur.f; cam.s = cur.s * (1 + kick); cam.a = cur.a + 0.015 * Math.sin(t * 0.23); cam.e = cur.e; cam.sx = 270 + shx; cam.sy = cur.sy + shy;
  camApply();
  const R = 30000;
  camera.position.set(cam.f[0] + toCam[0] * R, cam.f[1] + toCam[1] * R, cam.f[2] + toCam[2] * R);
  camera.near = 1; camera.far = 60000; camera.updateProjectionMatrix(); camera.updateMatrixWorld();
  // the key light and its shadow box follow the focus. The box keeps one size per shot (stepped only while a shot
  // zooms out) and moves in whole shadow-map texels, so shadow edges hold still instead of shimmering.
  const sq = Math.min(cs, cur.s), qs = sq < cs ? Math.pow(2, Math.floor(Math.log2(sq) * 3) / 3) : cs;
  const half = clamp(720 / qs, 120, 9000), tx = (2 * half) / keyL.shadow.mapSize.x;
  const fx = cur.f[0] * SH_X.x + cur.f[1] * SH_X.y + cur.f[2] * SH_X.z, fy = cur.f[0] * SH_Y.x + cur.f[1] * SH_Y.y + cur.f[2] * SH_Y.z;
  const ex = fx - Math.round(fx / tx) * tx, ey = fy - Math.round(fy / tx) * tx;
  const f = [0, 1, 2].map((j) => cur.f[j] - SH_X.getComponent(j) * ex - SH_Y.getComponent(j) * ey);
  keyL.target.position.set(f[0], f[1], f[2]); keyL.target.updateMatrixWorld();
  keyL.position.set(f[0] + KEYDIR.x * 9000, f[1] + KEYDIR.y * 9000, f[2] + KEYDIR.z * 9000);
  const sc = keyL.shadow.camera; sc.left = -half; sc.right = half; sc.top = half; sc.bottom = -half; sc.near = 100; sc.far = 20000; sc.updateProjectionMatrix();
}

/* ------------------------------------------------------------------ materials and geometry */
const _mats = {};
function mat(col, o = {}) {
  const k = col + JSON.stringify(o);
  if (_mats[k]) return _mats[k];
  const m = new TH.MeshStandardMaterial({ color: C(col), roughness: o.r ?? 0.82, metalness: o.m ?? 0, flatShading: !!o.flat });
  if (o.e) { m.emissive = C(o.e); m.emissiveIntensity = o.ei ?? 2; }
  if (o.op != null) { m.transparent = true; m.opacity = o.op; m.depthWrite = false; }
  if (o.map) m.map = o.map;
  return (_mats[k] = m);
}
// a glowing material of its own (animated per frame)
const glowM = (col, ei = 3, base = '#141313') => new TH.MeshStandardMaterial({ color: C(base), emissive: C(col), emissiveIntensity: ei, roughness: 0.6 });
function mesh(geo, m, par, x = 0, y = 0, z = 0, o = {}) {
  const me = new TH.Mesh(geo, m); me.position.set(x, y, z);
  me.castShadow = o.cast ?? true; me.receiveShadow = o.recv ?? true;
  if (o.rz) me.rotation.z = o.rz; if (o.rx) me.rotation.x = o.rx; if (o.ry) me.rotation.y = o.ry;
  (par || scene).add(me); return me;
}
function grp(par, x = 0, y = 0, z = 0, rz = 0) { const g = new TH.Group(); g.position.set(x, y, z); g.rotation.z = rz; (par || scene).add(g); return g; }
const _geos = {};
const gk = (k, f) => _geos[k] || (_geos[k] = f());
// rounded box, base at z=0
const rb = (w, d, h, r = 0, seg = 2) => gk(`rb${w},${d},${h},${r},${seg}`, () => {
  const rr = Math.min(r, w / 2 - 0.01, d / 2 - 0.01, h / 2 - 0.01);
  const g = rr > 0.05 ? new TH.RoundedBoxGeometry(w, d, h, seg, rr) : new TH.BoxGeometry(w, d, h); g.translate(0, 0, h / 2); return g;
});
// rounded box, centred
const rbc = (w, d, h, r = 0, seg = 2) => gk(`rbc${w},${d},${h},${r},${seg}`, () => { const g = rb(w, d, h, r, seg).clone(); g.translate(0, 0, -h / 2); return g; });
// flat rounded rectangle in xy (centred), uvs 0..1 across it: screens with real corner radii
const rrg = (w, h, r) => gk(`rr${w},${h},${r}`, () => {
  const p = new TH.Shape(), x = -w / 2, y = -h / 2;
  p.moveTo(x + r, y); p.lineTo(x + w - r, y); p.quadraticCurveTo(x + w, y, x + w, y + r); p.lineTo(x + w, y + h - r); p.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  p.lineTo(x + r, y + h); p.quadraticCurveTo(x, y + h, x, y + h - r); p.lineTo(x, y + r); p.quadraticCurveTo(x, y, x + r, y);
  const g = new TH.ShapeGeometry(p, 10), P = g.attributes.position, uv = g.attributes.uv;
  for (let i = 0; i < P.count; i++) uv.setXY(i, (P.getX(i) - x) / w, (P.getY(i) - y) / h);
  return g;
});
// cylinder along z, base at z=0
const cy = (rt, rbt, h, seg = 24) => gk(`cy${rt},${rbt},${h},${seg}`, () => { const g = new TH.CylinderGeometry(rt, rbt, h, seg); g.rotateX(Math.PI / 2); g.translate(0, 0, h / 2); return g; });
// capsule hanging down from z=0 (limbs)
const capd = (r, len) => gk(`cd${r},${len}`, () => { const g = new TH.CapsuleGeometry(r, len, 4, 12); g.rotateX(Math.PI / 2); g.translate(0, 0, -(len / 2 + r)); return g; });
const sph = (r, ws = 20, hs = 14) => gk(`sp${r},${ws}`, () => new TH.SphereGeometry(r, ws, hs));
const ico = (r, d = 1) => gk(`ic${r},${d}`, () => new TH.IcosahedronGeometry(r, d));
const tor = (R, r, seg = 48) => gk(`to${R},${r}`, () => new TH.TorusGeometry(R, r, 10, seg));
function lathe(pts, seg = 48) { const g = new TH.LatheGeometry(pts.map(([r, z]) => new TH.Vector2(r, z)), seg); g.rotateX(Math.PI / 2); return g; }

// merge every static mesh under root into one mesh per material (far fewer draw calls for a whole city)
function bake(root) {
  root.updateMatrixWorld(true);
  const by = new Map();
  root.traverse((o) => {
    if (!o.isMesh) return;
    const k = o.material.uuid;
    if (!by.has(k)) by.set(k, { m: o.material, gs: [], cast: o.castShadow });
    const g = o.geometry.index ? o.geometry.toNonIndexed() : o.geometry.clone();
    g.applyMatrix4(o.matrixWorld);
    for (const n of Object.keys(g.attributes)) if (!['position', 'normal', 'uv'].includes(n)) g.deleteAttribute(n);
    if (!g.attributes.uv) g.setAttribute('uv', new TH.Float32BufferAttribute(new Float32Array(g.attributes.position.count * 2), 2));
    g.clearGroups(); by.get(k).gs.push(g);
  });
  const out = new TH.Group();
  for (const { m, gs, cast } of by.values()) { const me = new TH.Mesh(TH.mergeGeometries(gs), m); me.castShadow = cast; me.receiveShadow = true; out.add(me); }
  root.parent.remove(root); scene.add(out); return out;
}

/* ------------------------------------------------------------------ canvas screens and holograms */
// a flat canvas screen in the parent's xy plane facing +z. draw(key, fn) only repaints when the key changes.
function scr(w, h, k, par, glow = 1.3, rad = 0) {
  const c = document.createElement('canvas'); c.width = Math.round(w * k); c.height = Math.round(h * k);
  const g = c.getContext('2d');
  const tex = new TH.CanvasTexture(c); tex.colorSpace = TH.SRGBColorSpace; tex.anisotropy = 8;
  const m = new TH.MeshBasicMaterial({ map: tex, toneMapped: false }); m.color.setScalar(glow);
  const me = new TH.Mesh(rad > 0 ? rrg(w, h, rad) : new TH.PlaneGeometry(w, h), m); par.add(me);
  const d = { m: me, mat: m, c, g, tex, W: c.width, H: c.height, _k: null };
  d.draw = (key, fn) => { if (key != null && key === d._k) return; d._k = key; g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, c.width, c.height); fn(g, c.width, c.height); tex.needsUpdate = true; };
  return d;
}
// a camera-facing glowing icon (pin, lock, key...) drawn once on a canvas
function holo(draw, size, col) {
  const c = document.createElement('canvas'); c.width = c.height = 256; draw(c.getContext('2d'), 256, col);
  const tex = new TH.CanvasTexture(c); tex.colorSpace = TH.SRGBColorSpace;
  const m = new TH.SpriteMaterial({ map: tex, transparent: true, depthWrite: false, depthTest: false, toneMapped: false }); m.color.setScalar(1.15);
  const s = new TH.Sprite(m); s.scale.set(size, size, 1); s.visible = false; s.renderOrder = 5; scene.add(s);
  s.show = (p, a, k = 1) => { s.visible = a > 0.01; if (!s.visible) return; s.position.set(...p); m.opacity = a; s.scale.set(size * k, size * k, 1); };
  return s;
}
const ICO = {
  pin(g, S, col) { g.fillStyle = col; g.shadowColor = col; g.shadowBlur = 8; g.beginPath(); g.arc(S / 2, S * 0.4, S * 0.24, Math.PI * 0.82, Math.PI * 0.18); g.lineTo(S / 2, S * 0.9); g.closePath(); g.fill(); g.shadowBlur = 0; g.fillStyle = '#0b0a09'; g.beginPath(); g.arc(S / 2, S * 0.4, S * 0.09, 0, 7); g.fill(); },
  lock(g, S, col) { g.strokeStyle = col; g.fillStyle = col; g.lineWidth = S * 0.08; g.shadowColor = col; g.shadowBlur = 8; g.beginPath(); g.arc(S / 2, S * 0.42, S * 0.17, Math.PI, 0); g.stroke(); g.beginPath(); g.roundRect(S * 0.26, S * 0.42, S * 0.48, S * 0.38, S * 0.06); g.fill(); g.shadowBlur = 0; g.fillStyle = '#0b0a09'; g.beginPath(); g.arc(S / 2, S * 0.58, S * 0.05, 0, 7); g.fill(); g.fillRect(S * 0.48, S * 0.58, S * 0.04, S * 0.1); },
  unlock(g, S, col) { g.strokeStyle = col; g.fillStyle = col; g.lineWidth = S * 0.08; g.shadowColor = col; g.shadowBlur = 8; g.beginPath(); g.arc(S * 0.66, S * 0.36, S * 0.17, Math.PI, 0); g.stroke(); g.beginPath(); g.roundRect(S * 0.2, S * 0.42, S * 0.48, S * 0.38, S * 0.06); g.fill(); g.shadowBlur = 0; },
  key(g, S, col) { g.strokeStyle = col; g.lineWidth = S * 0.08; g.lineCap = 'round'; g.shadowColor = col; g.shadowBlur = 8; g.beginPath(); g.arc(S * 0.32, S / 2, S * 0.14, 0, 7); g.moveTo(S * 0.46, S / 2); g.lineTo(S * 0.84, S / 2); g.moveTo(S * 0.72, S / 2); g.lineTo(S * 0.72, S * 0.64); g.moveTo(S * 0.82, S / 2); g.lineTo(S * 0.82, S * 0.6); g.stroke(); },
  wave(g, S, col) { g.strokeStyle = col; g.lineWidth = S * 0.06; g.lineCap = 'round'; g.shadowColor = col; g.shadowBlur = 8; g.fillStyle = col; g.beginPath(); g.arc(S / 2, S * 0.62, S * 0.06, 0, 7); g.fill(); for (let i = 1; i <= 3; i++) { g.globalAlpha = 1 - i * 0.2; g.beginPath(); g.arc(S / 2, S * 0.62, S * 0.12 * i + S * 0.04, Math.PI * 1.2, Math.PI * 1.8); g.stroke(); } g.globalAlpha = 1; },
  x(g, S, col) { g.strokeStyle = col; g.lineWidth = S * 0.1; g.lineCap = 'round'; g.shadowColor = col; g.shadowBlur = 8; g.beginPath(); g.moveTo(S * 0.3, S * 0.3); g.lineTo(S * 0.7, S * 0.7); g.moveTo(S * 0.7, S * 0.3); g.lineTo(S * 0.3, S * 0.7); g.stroke(); },
};

/* ------------------------------------------------------------------ props */
const SKIN = ['#c99f84', '#a87a5e', '#e0bba0', '#7d563f'], HAIR = ['#211a16', '#3b2a1f', '#5c4434', '#15110f'];
const SHIRT = ['#5a5551', '#564f4a', '#474441', '#57534f', '#6f6863', '#3f3b38', '#564f49'], PANTS = ['#282625', '#3f3b38', '#3a3735', '#282624'];
// a person facing +x. Joints: hip/knee/shoulder/elbow pivots and a head pivot. pose(name, ph) sets them.
function person(par, x, y, rz, o = {}) {
  const i = o.seed ?? 0;
  const skin = mat(o.skin || SKIN[i % 4]), hair = mat(o.hair || HAIR[(i >> 1) % 4], { r: 0.9 });
  const shirt = mat(o.shirt || SHIRT[i % 7]), pants = mat(o.pants || PANTS[(i >> 2) % 4]), shoe = mat('#171615', { r: 0.6 });
  const root = grp(par, x, y, 0, rz), body = grp(root);
  const P_ = { root, body };
  const leg = (sy) => {
    const hip = grp(body, 0, sy * 10, 92);
    mesh(capd(7.2, 30), pants, hip);
    const knee = grp(hip, 0, 0, -44);
    mesh(capd(6.2, 28), pants, knee);
    mesh(rbc(25, 11, 8, 3), shoe, knee, 5, 0, -44);
    return [hip, knee];
  };
  [P_.hipL, P_.kneeL] = leg(1); [P_.hipR, P_.kneeR] = leg(-1);
  mesh(rbc(23, 35, 18, 7), pants, body, 0, 0, 94);
  mesh(rb(o.coat ? 28 : 24, 38, o.coat ? 70 : 54, 9), shirt, body, 0, 0, o.coat ? 76 : 92);
  if (o.pack) { mesh(rb(14, 30, 40, 5), mat(o.pack, { r: 0.7 }), body, -18, 0, 98); P_.pocket = [-26, 0, 112]; }
  const arm = (sy) => {
    const sh = grp(body, 0, sy * 22, 138);
    mesh(capd(5.4, 20), shirt, sh);
    const el = grp(sh, 0, 0, -31);
    mesh(capd(4.6, 18), o.short ? skin : shirt, el);
    mesh(sph(4.8, 12, 8), skin, el, 0, 0, -30);
    return [sh, el];
  };
  [P_.shL, P_.elL] = arm(1); [P_.shR, P_.elR] = arm(-1);
  mesh(cy(5, 5, 9, 12), skin, body, 0, 0, 144);
  const head = grp(body, 0, 0, 150); P_.head = head;
  mesh(sph(11.5), skin, head, 1, 0, 11);
  const hs = mesh(sph(12.3), hair, head, -2.5, 0, 13.5); hs.scale.set(1, 1, 0.86);
  if (o.long) mesh(rb(8, 22, 26, 4), hair, head, -9, 0, -8);
  if (o.bun) mesh(sph(6, 12, 8), hair, head, -9, 0, 24);
  // a phone in the right hand (screen faces the eyes); its screen material is shared so the page can light it
  if (o.phone) {
    const pg = grp(body, 40, -8, 112); pg.rotation.set(0, -0.6, 0);
    mesh(rbc(7.4, 15, 0.9, 1), mat('#171615', { r: 0.4, m: 0.3 }), pg);
    P_.screen = new TH.MeshBasicMaterial({ color: C(O2), toneMapped: false });
    const sm = new TH.Mesh(new TH.PlaneGeometry(6.6, 14), P_.screen); sm.position.z = 0.5; sm.rotation.z = Math.PI / 2; pg.add(sm);
    P_.phone = pg;
  }
  P_.pose = (name, ph = 0) => {
    const J = [P_.hipL, P_.hipR, P_.kneeL, P_.kneeR, P_.shL, P_.shR, P_.elL, P_.elR, head];
    J.forEach((j) => j.rotation.set(0, 0, 0)); body.position.z = 0;
    if (name === 'walk' || name === 'walkphone') {
      const s = Math.sin(ph), c = Math.cos(ph);
      P_.hipL.rotation.y = -0.42 * s; P_.hipR.rotation.y = 0.42 * s;
      P_.kneeL.rotation.y = 0.55 * Math.max(0, c); P_.kneeR.rotation.y = 0.55 * Math.max(0, -c);
      P_.shL.rotation.y = 0.32 * s; P_.shR.rotation.y = -0.32 * s; P_.elL.rotation.y = -0.25; P_.elR.rotation.y = -0.25;
      body.position.z = 1.6 * Math.abs(c);
    }
    if (name === 'sit') { P_.hipL.rotation.y = P_.hipR.rotation.y = -1.5; P_.kneeL.rotation.y = P_.kneeR.rotation.y = 1.45; body.position.z = -40; }
    if (name === 'phone' || name === 'walkphone' || (name === 'sit' && o.phone)) {
      P_.shR.rotation.set(0.28, -0.55, 0); P_.elR.rotation.y = -1.15; head.rotation.y = 0.32;
      if (name === 'sit') { P_.shL.rotation.set(-0.28, -0.5, 0); P_.elL.rotation.y = -1.1; }
    }
    if (name === 'talk') { P_.shR.rotation.y = -0.4 - 0.2 * Math.sin(ph); P_.elR.rotation.y = -1.2; P_.shL.rotation.y = -0.2; P_.elL.rotation.y = -0.9; }
    if (P_.phone) P_.phone.visible = name === 'phone' || name === 'walkphone' || name === 'sit';
  };
  P_.pose(o.pose || 'stand');
  return P_;
}

// a hard-shell checked suitcase: two shell halves with a zip seam, soft vertical ribs, aluminium telescoping handle,
// rubber top grip, corner guards and four double spinner wheels. Base at z = 0, top of the shell at 71 * sc.
function suitcase(par, x, y, rz, col, sc = 1) {
  const g = grp(par, x, y, 0, rz); g.scale.setScalar(sc);
  const shell = pmat(col, { r: 0.38, cc: 0.55, ccr: 0.25, env: 0.7 }), rub = mat('#141312', { r: 0.7 }), seam = mat('#0f0e0e', { r: 0.6 });
  const alu = pmat('#b9b6b3', { r: 0.28, m: 1, env: 1.1 }), alud = pmat('#5c5956', { r: 0.35, m: 1, env: 0.9 });
  mesh(rb(46, 27, 64, 6.5, 4), shell, g, 0, 0, 7);
  // zip seam: a thin dark band around the sides and top, two thirds of the way back
  mesh(rb(46.5, 0.9, 64.5, 6.6, 4), seam, g, 0, 3.5, 6.75);
  // soft ribs, barely raised
  for (const xx of [-15, -5, 5, 15]) mesh(rb(2.4, 27.5, 50, 1.2, 3), shell, g, xx, 0, 14);
  // corner guards and wheel housings
  for (const [xx, yy] of [[-19.5, -9.5], [19.5, -9.5], [-19.5, 9.5], [19.5, 9.5]]) {
    mesh(rb(8, 8, 6, 2.5, 3), rub, g, xx, yy, 5.5);
    for (const d of [-1.6, 1.6]) mesh(cy(3, 3, 1.7, 20), rub, g, xx + d - 0.85, yy, 3, { ry: Math.PI / 2 }).position.z = 3;
    mesh(cy(1.1, 1.1, 5, 12), alud, g, xx - 2.5, yy, 3, { ry: Math.PI / 2 });
  }
  // telescoping handle: housing on the top, two tubes, grip bar
  mesh(rb(26, 5, 1.2, 1.5, 3), rub, g, 0, 9, 70.6);
  for (const xx of [-9, 9]) { mesh(cy(0.95, 0.95, 13, 16), alu, g, xx, 9, 71); mesh(cy(1.25, 1.25, 1.2, 16), alud, g, xx, 9, 71); }
  mesh(rbc(22, 3.2, 3, 1.4, 3), rub, g, 0, 9, 85);
  // top carry handle on two mounts
  mesh(rbc(15, 3.2, 2.6, 1.3, 3), rub, g, 0, -3.5, 74.4);
  for (const xx of [-7.5, 7.5]) mesh(rb(3.4, 4, 3.6, 1.2, 3), rub, g, xx, -3.5, 70.6);
  return { g, top: 71 * sc };
}

// an AirTag of radius R (real one: 32 mm across, 8 mm thick): a glossy white domed face over a mirror-polished steel
// back with a fine seam between them; inside, the board with the Bluetooth chip, the speaker coil and a coin cell.
// Parts can be pulled apart (explode 0..1). A thin light ring on the surface under it pulses when it pings.
// textures for the AirTag insides: a circuit board (gold traces and pads on a dark board) and a CR2032 cell face
let _atPcb, _atCell; // made on first use: ctex lives further down this file
const AT_PCB = () => _atPcb || (_atPcb = ctex(1024, 1024, (x, w) => {
  const c = w / 2; x.fillStyle = '#1b1a17'; x.beginPath(); x.arc(c, c, c, 0, 7); x.fill();
  x.strokeStyle = 'rgba(214,170,80,0.55)'; x.lineWidth = 5; x.lineCap = 'round';
  for (let k = 0; k < 26; k++) { const a0 = k * 0.2417 + 0.3, r0 = c * (0.42 + 0.04 * (k % 4)), r1 = c * (0.78 - 0.03 * (k % 3)), a1 = a0 + 0.12 * ((k % 2) ? 1 : -1);
    x.beginPath(); x.moveTo(c + Math.cos(a0) * r0, c + Math.sin(a0) * r0); x.lineTo(c + Math.cos(a0) * (r0 + r1) / 2, c + Math.sin(a0) * (r0 + r1) / 2); x.lineTo(c + Math.cos(a1) * r1, c + Math.sin(a1) * r1); x.stroke();
    x.fillStyle = '#d9b25a'; x.beginPath(); x.arc(c + Math.cos(a1) * r1, c + Math.sin(a1) * r1, 9, 0, 7); x.fill(); }
  x.strokeStyle = 'rgba(214,170,80,0.7)'; x.lineWidth = 7; x.beginPath(); x.arc(c, c, c * 0.9, 0.2, 2.6); x.stroke(); // antenna
  x.strokeStyle = 'rgba(235,232,226,0.35)'; x.lineWidth = 3; x.beginPath(); x.arc(c, c, c * 0.4, 0, 7); x.stroke();
  x.fillStyle = 'rgba(235,232,226,0.5)'; x.font = '600 30px Inter'; x.textAlign = 'center'; x.fillText('U1', c - c * 0.5, c + c * 0.52); x.fillText('BT', c + c * 0.52, c - c * 0.36);
  x.strokeStyle = '#d9b25a'; x.lineWidth = 10; x.beginPath(); x.arc(c, c, c * 0.985, 0, 7); x.stroke();
}));
const AT_CELL = () => _atCell || (_atCell = ctex(1024, 1024, (x, w) => {
  const c = w / 2; x.fillStyle = '#c9c6c2'; x.beginPath(); x.arc(c, c, c, 0, 7); x.fill();
  for (let r = 8; r < c; r += 6) { x.strokeStyle = `rgba(${r % 12 ? 255 : 90},${r % 12 ? 255 : 90},${r % 12 ? 255 : 90},0.05)`; x.lineWidth = 3; x.beginPath(); x.arc(c, c, r, 0, 7); x.stroke(); }
  x.fillStyle = 'rgba(60,58,56,0.72)'; x.textAlign = 'center'; x.textBaseline = 'middle';
  x.font = '700 200px Inter'; x.fillText('+', c, c - 190); x.font = '700 132px Inter'; x.fillText('CR2032', c, c + 30); x.font = '600 84px Inter'; x.fillText('3V', c, c + 190);
}));
const discG = () => gk('atdisc', () => new TH.CircleGeometry(1, 96));
// an Apple AirTag: a glossy white pillow face on a mirror-polished steel back. explode(k) lifts the face, the board
// (speaker coil, magnet, Bluetooth and U1 chips) and the CR2032 cell up out of the steel cup.
function airtag3(par, R, o = {}) {
  const g = grp(par);
  const white = pmat('#f6f5f3', { r: 0.2, cc: 1, ccr: 0.03, env: 1.25 }), steel = pmat('#f2f0ee', { r: 0.05, m: 1, env: 1.9 });
  const brushed = pmat('#c9c6c2', { r: 0.3, m: 1, env: 1.3 }), dark = mat('#0b0a09', { r: 0.6 });
  const cap = grp(g), back = grp(g), pcb = grp(g), bat = grp(g);
  // white face: a soft pillow, flat-ish crown rolling over a generous shoulder to the seam
  const face = [], z0 = 0.27 * R, crown = 0.5 * R;
  for (let i = 0; i <= 40; i++) { const u = i / 40, r = 0.78 * R * u; face.push([Math.max(0.001, r), crown - 0.06 * R * u * u]); }
  for (let i = 1; i <= 16; i++) { const a = (i / 16) * Math.PI / 2, rr = 0.2 * R; face.push([0.78 * R + Math.sin(a) * rr, crown - 0.06 * R - (1 - Math.cos(a)) * (crown - 0.06 * R - z0 - 0.02 * R) / 1]); }
  face.push([0.985 * R, z0 + 0.004 * R], [0.001, z0]);
  mesh(lathe(face.reverse(), 160), white, cap);
  // the seam: a thin dark groove between face and back
  mesh(cy(0.982 * R, 0.982 * R, 0.022 * R, 128), dark, back, 0, 0, 0.255 * R, { cast: false });
  // polished steel back: a dome curving away under the seam
  const bk = []; for (let i = 0; i <= 24; i++) { const u = i / 24, a = u * Math.PI / 2; bk.push([Math.max(0.001, R * Math.sin(a) * (0.86 + 0.14 * u)), 0.26 * R * (1 - Math.cos(a)) * 0.9 + 0.006 * R * u]); }
  bk.push([0.99 * R, 0.256 * R], [0.94 * R, 0.262 * R], [0.001, 0.262 * R]);
  mesh(lathe(bk, 128), steel, back);
  // inside the cup (seen once the parts lift out): a brushed recess, three bayonet tabs, the spring contact
  const cupM = pmat('#8a8581', { r: 0.38, m: 0.55, env: 1.5 });
  mesh(cy(0.9 * R, 0.9 * R, 0.004 * R, 96), cupM, back, 0, 0, 0.262 * R, { cast: false });
  for (const [r, w] of [[0.7, 0.006], [0.5, 0.005], [0.3, 0.005]]) mesh(tor(r * R, w * R, 96), pmat('#a6a19c', { r: 0.3, m: 0.8, env: 1.4 }), back, 0, 0, 0.266 * R, { cast: false });
  mesh(tor(0.9 * R, 0.018 * R, 96), steel, back, 0, 0, 0.266 * R, { cast: false });
  for (let k = 0; k < 3; k++) { const a = k * 2.094 + 0.4; mesh(rbc(0.2 * R, 0.07 * R, 0.03 * R, 0.01 * R), steel, back, Math.cos(a) * 0.86 * R, Math.sin(a) * 0.86 * R, 0.275 * R, { rz: a + Math.PI / 2, cast: false }); }
  mesh(cy(0.08 * R, 0.1 * R, 0.035 * R, 32), pmat('#d8b56a', { r: 0.25, m: 1, env: 1.2 }), back, 0, 0, 0.264 * R, { cast: false });
  // the board: dark PCB with gold traces, a copper speaker coil around a chrome magnet, black chip packages
  mesh(cy(0.86 * R, 0.86 * R, 0.035 * R, 96), mat('#1b1a17', { r: 0.5 }), pcb);
  const top = new TH.Mesh(discG(), new TH.MeshStandardMaterial({ map: AT_PCB(), roughness: 0.42, metalness: 0.25 })); top.scale.setScalar(0.86 * R); top.position.z = 0.0355 * R; pcb.add(top);
  const copper = pmat('#c47a45', { r: 0.28, m: 1, env: 1.2 });
  for (let k = 0; k < 6; k++) mesh(tor(0.24 * R + k * 0.024 * R, 0.013 * R, 72), copper, pcb, 0, 0, 0.05 * R);
  mesh(cy(0.2 * R, 0.2 * R, 0.06 * R, 64), steel, pcb, 0, 0, 0.035 * R);
  mesh(cy(0.12 * R, 0.12 * R, 0.065 * R, 48), dark, pcb, 0, 0, 0.035 * R, { cast: false });
  const chipM = glowM(O, 0, '#171615');
  mesh(rb(0.24 * R, 0.24 * R, 0.045 * R, 0.012 * R), chipM, pcb, 0.52 * R, 0.2 * R, 0.035 * R);
  const pkg = pmat('#1d1c1b', { r: 0.35, cc: 0.6 });
  for (const [xx, yy, w, h] of [[-0.5, -0.24, 0.22, 0.2], [-0.2, -0.62, 0.16, 0.12], [0.24, -0.6, 0.12, 0.1], [0.62, -0.2, 0.1, 0.14], [-0.62, 0.22, 0.12, 0.12]]) mesh(rb(w * R, h * R, 0.035 * R, 0.006 * R), pkg, pcb, xx * R, yy * R, 0.035 * R);
  const smd = pmat('#9a8f80', { r: 0.4, m: 0.6 });
  for (let k = 0; k < 14; k++) { const a = k * 0.449 + 1.1, r = (0.44 + 0.05 * (k % 3)) * R; mesh(rbc(0.05 * R, 0.025 * R, 0.02 * R), smd, pcb, Math.cos(a) * r, Math.sin(a) * r, 0.045 * R, { rz: a, cast: false }); }
  // CR2032 coin cell: stainless can with the printed face
  mesh(cy(0.66 * R, 0.66 * R, 0.1 * R, 96), brushed, bat);
  mesh(tor(0.655 * R, 0.012 * R, 96), steel, bat, 0, 0, 0.1 * R, { cast: false });
  const cf = new TH.Mesh(discG(), new TH.MeshPhysicalMaterial({ map: AT_CELL(), metalness: 1, roughness: 0.26, envMap: STUDIO_ENV, envMapIntensity: 1.35 })); cf.scale.setScalar(0.64 * R); cf.position.z = 0.1015 * R; bat.add(cf);
  const ringM = glowM(O, 0, '#0b0a09');
  const ring = mesh(gk('agr', () => new TH.RingGeometry(1.06, 1.1, 96)), ringM, g, 0, 0, 0.004 * R, { cast: false }); ring.scale.setScalar(R);
  g.traverse((m) => { if (m.isMesh && m !== ring && m.castShadow !== false) m.castShadow = true; });
  const A = { g, cap, back, pcb, bat, chipM, ringM, R, chip: [0.52 * R, 0.2 * R] };
  A.explode = (k) => {
    cap.position.z = k * 2.9 * R; pcb.position.z = 0.06 * R + k * 1.85 * R; bat.position.z = 0.05 * R + k * 0.95 * R;
    cap.rotation.z = k * 0.25; pcb.rotation.z = -k * 0.15; ring.visible = k < 0.05;
    // tilt the lifted parts a little toward the camera so their faces read
    for (const p of [cap, pcb, bat]) p.rotation.x = -0.18 * k;
  };
  A.explode(0);
  return A;
}

// a hero phone (product-shot scale) with a live screen. kind 'ios' | 'android'. A metal frame with real corner radii,
// a black glass front with a thin even bezel, a rounded screen, the island (iOS) or punch-hole camera (Android), side
// buttons, a camera module on the back, and a faint glass sheen across the screen.
const SHEEN = (() => { const c = document.createElement('canvas'); c.width = 256; c.height = 512; const x = c.getContext('2d');
  const gr = x.createLinearGradient(0, 0, 256, 512); gr.addColorStop(0, 'rgba(255,255,255,0.10)'); gr.addColorStop(0.38, 'rgba(255,255,255,0.025)'); gr.addColorStop(0.42, 'rgba(255,255,255,0)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
  x.fillStyle = gr; x.fillRect(0, 0, 256, 512); const t = new TH.CanvasTexture(c); t.colorSpace = TH.SRGBColorSpace; return t; })();
// a slab with real plan-view corner radius r and softly rounded edges (bevel bev), centred on z = 0
const slab = (w, h, d, r, bev, seg = 10) => gk(`sl${w},${h},${d},${r},${bev}`, () => {
  const ri = Math.max(0.01, r - bev), x = w / 2 - bev, y = h / 2 - bev, p = new TH.Shape();
  p.moveTo(-x + ri, -y); p.lineTo(x - ri, -y); p.absarc(x - ri, -y + ri, ri, -Math.PI / 2, 0); p.lineTo(x, y - ri); p.absarc(x - ri, y - ri, ri, 0, Math.PI / 2);
  p.lineTo(-x + ri, y); p.absarc(-x + ri, y - ri, ri, Math.PI / 2, Math.PI); p.lineTo(-x, -y + ri); p.absarc(-x + ri, -y + ri, ri, Math.PI, Math.PI * 1.5);
  const g = new TH.ExtrudeGeometry(p, { depth: Math.max(0.001, d - 2 * bev), bevelEnabled: true, bevelThickness: bev, bevelSize: bev, bevelSegments: seg, curveSegments: 32 });
  g.translate(0, 0, -(d - 2 * bev) / 2); return g;
});
function phone3(par, x, y, z, sc, body, kind = 'ios') {
  const g = grp(par, x, y, z); g.up.set(0, 0, 1);
  const W = 7.15 * sc, H = 14.7 * sc, T = 0.78 * sc, rad = 1.05 * sc, bz = 0.42 * sc, bev = 0.2 * sc;
  const frame = pmat(body, { r: 0.26, m: 1, env: 1.2 }), glass = pmat('#050505', { r: 0.05, cc: 1, ccr: 0.02, env: 1.3 });
  mesh(slab(W, H, T, rad, bev), frame, g); // the rounded metal band shows around the glass
  mesh(rrg(W - 2 * bev, H - 2 * bev, rad - bev), glass, g, 0, 0, T / 2 + 0.008 * sc, { cast: false });
  const sw = W - 2 * bz, sh = H - 2 * bz;
  const s = scr(sw, sh, 760 / sw, g, 0.97, rad - bz * 0.8); s.m.position.z = T / 2 + 0.02 * sc;
  const sheen = new TH.Mesh(rrg(sw, sh, rad - bz * 0.8), new TH.MeshBasicMaterial({ map: SHEEN, transparent: true, depthWrite: false, toneMapped: false, blending: TH.AdditiveBlending }));
  sheen.position.z = T / 2 + 0.035 * sc; g.add(sheen);
  const blk = mat('#020202', { r: 0.2 });
  if (kind === 'ios') mesh(rrg(2.15 * sc, 0.62 * sc, 0.31 * sc), blk, g, 0, sh / 2 - 0.62 * sc, T / 2 + 0.04 * sc, { cast: false });
  else mesh(gk('pch', () => new TH.CircleGeometry(1, 24)), blk, g, 0, sh / 2 - 0.55 * sc, T / 2 + 0.04 * sc, { cast: false }).scale.setScalar(0.2 * sc);
  // side buttons
  for (const [yy, l] of [[2.6, 1.1], [1.1, 1.1], [3.9, 0.55]]) mesh(slab(0.24 * sc, l * sc, 0.3 * sc, 0.1 * sc, 0.05 * sc, 4), frame, g, -W / 2 + 0.02 * sc, yy * sc, 0);
  mesh(slab(0.24 * sc, 1.9 * sc, 0.3 * sc, 0.1 * sc, 0.05 * sc, 4), frame, g, W / 2 - 0.02 * sc, 2.4 * sc, 0);
  // camera module on the back
  const lens = pmat('#0b0b0d', { r: 0.05, cc: 1, env: 1.4 }), ringm = pmat(body, { r: 0.2, m: 1, env: 1.3 });
  if (kind === 'ios') {
    const cx = -W / 2 + 1.75 * sc, cy_ = H / 2 - 1.75 * sc, bk = -T / 2;
    mesh(slab(2.9 * sc, 2.9 * sc, 0.18 * sc, 0.75 * sc, 0.06 * sc, 4), glass, g, cx, cy_, bk - 0.09 * sc);
    for (const [dx, dy] of [[-0.62, 0.62], [-0.62, -0.62], [0.62, 0]]) { const l = mesh(cy(0.52 * sc, 0.52 * sc, 0.22 * sc, 32), ringm, g, cx + dx * sc, cy_ + dy * sc, bk - 0.4 * sc); mesh(cy(0.38 * sc, 0.38 * sc, 0.05 * sc, 32), lens, g, cx + dx * sc, cy_ + dy * sc, bk - 0.42 * sc); }
  } else {
    mesh(slab(W - 1.2 * sc, 1.7 * sc, 0.26 * sc, 0.85 * sc, 0.08 * sc, 4), glass, g, 0, H / 2 - 2 * sc, -T / 2 - 0.13 * sc);
    for (const dx of [-1.6, -0.4, 0.8]) mesh(cy(0.45 * sc, 0.45 * sc, 0.06 * sc, 32), lens, g, dx * sc, H / 2 - 2 * sc, -T / 2 - 0.3 * sc);
  }
  return { g, s, W, H, T };
}

/* ------------------------------------------------------------------ furniture */
function sofa(par, x, y, rz, col) {
  const g = grp(par, x, y, 0, rz), m = mat(col, { r: 0.95 }), leg = mat('#1b1a19', { r: 0.6 });
  mesh(rb(210, 92, 30, 6), m, g, 0, 0, 10);
  for (const xx of [-49, 49]) mesh(rb(96, 74, 15, 6), m, g, xx, -6, 40);
  mesh(rb(210, 22, 46, 8), m, g, 0, 36, 38);
  for (const xx of [-98, 98]) mesh(rb(22, 92, 58, 8), m, g, xx, 0, 10);
  for (const xx of [-35, 35]) mesh(rb(40, 14, 34, 6), mat(mixHex(col, '#ff6a1f', 0.25), { r: 0.95 }), g, xx * 2.2, 22, 52, { rz: 0.1 });
  for (const [xx, yy] of [[-95, -38], [95, -38], [-95, 38], [95, 38]]) mesh(cy(2.4, 2, 10, 8), leg, g, xx, yy, 0);
  return g;
}
function table(par, x, y, w, d, h, col) {
  const g = grp(par, x, y), m = mat(col, { r: 0.6 });
  mesh(rb(w, d, 4, 1.5), m, g, 0, 0, h - 4);
  for (const [sx, sy] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) mesh(cy(1.8, 1.8, h - 4, 8), mat('#1b1a19'), g, sx * (w / 2 - 6), sy * (d / 2 - 6), 0);
  return g;
}
function floorLamp(par, x, y, col = '#ded9d5') {
  const g = grp(par, x, y), metal = mat('#2c2a28', { r: 0.4, m: 0.6 });
  mesh(cy(15, 15, 3, 24), metal, g); mesh(cy(1.3, 1.3, 150, 8), metal, g, 0, 0, 3);
  const shade = mesh(cy(16, 22, 30, 24), glowM(col, 1.4, '#332f2c'), g, 0, 0, 148);
  const L = new TH.PointLight(C(col), 260, 900, 1); L.position.set(0, 0, 150); g.add(L);
  return { g, L, shade };
}
function plant(par, x, y, s = 1) {
  const g = grp(par, x, y); g.scale.setScalar(s);
  mesh(cy(15, 11, 30, 18), mat('#393634', { r: 0.8 }), g);
  const leaf = mat('#3d3a37', { r: 0.9, flat: true });
  [[0, 0, 62, 26], [12, 8, 82, 18], [-10, -6, 88, 16], [4, -10, 104, 12]].forEach(([xx, yy, z, r]) => mesh(ico(r, 0), leaf, g, xx, yy, z));
  mesh(cy(2, 2, 50, 6), mat('#332f2c'), g, 0, 0, 28);
  return g;
}
function tree(par, x, y, s = 1, seed = 0) {
  const g = grp(par, x, y, 0, seed); g.scale.setScalar(s);
  mesh(cy(9, 13, 160, 8), mat('#2b2825', { r: 0.9 }), g);
  const leaf = mat(['#383532', '#3c3936', '#322f2d'][seed % 3], { r: 0.95, flat: true });
  mesh(ico(95, 1), leaf, g, 0, 0, 250); mesh(ico(70, 1), leaf, g, 45, 20, 320); mesh(ico(60, 1), leaf, g, -40, -25, 300);
  return g;
}
function car(par, x, y, rz, col, lit = false) {
  const g = grp(par, x, y, 0, rz), paint = mat(col, { r: 0.35, m: 0.45 }), glass = mat('#111010', { r: 0.12, m: 0.3 }), tire = mat('#161514', { r: 0.8 });
  mesh(rb(430, 180, 62, 16), paint, g, 0, 0, 24);
  mesh(rb(240, 160, 56, 22), glass, g, -25, 0, 74);
  mesh(rb(230, 166, 6, 3), paint, g, -25, 0, 126);
  for (const [xx, yy] of [[-140, -82], [140, -82], [-140, 82], [140, 82]]) mesh(cy(33, 33, 22, 16), tire, g, xx, yy, 0, { rx: Math.PI / 2 }).position.z = 33;
  const hl = lit ? glowM('#f6f2ef', 4) : mat('#56524f', { r: 0.3 }), tl = lit ? glowM('#ff3a1a', 4) : mat('#4a1e14', { r: 0.4 });
  for (const yy of [-62, 62]) { mesh(rbc(6, 34, 12, 3), hl, g, 214, yy, 66, { cast: false }); mesh(rbc(6, 30, 10, 3), tl, g, -214, yy, 68, { cast: false }); }
  return g;
}
function streetLamp(par, x, y, rz, headM) {
  const g = grp(par, x, y, 0, rz), metal = mat('#292725', { r: 0.5, m: 0.6 });
  mesh(cy(7, 9, 20, 10), metal, g); mesh(cy(4, 4, 560, 8), metal, g, 0, 0, 20);
  mesh(rb(110, 6, 6, 2), metal, g, 52, 0, 570);
  mesh(rb(46, 22, 10, 4), metal, g, 100, 0, 562);
  mesh(rbc(40, 16, 3, 1.4), headM, g, 100, 0, 561, { cast: false });
  return g;
}
function bench(par, x, y, rz, w = 180) {
  const g = grp(par, x, y, 0, rz), wood = mat('#3d3834', { r: 0.8 }), metal = mat('#211f1e', { r: 0.5, m: 0.5 });
  mesh(rb(w, 44, 5, 1.5), wood, g, 0, 0, 42); mesh(rb(w, 5, 34, 1.5), wood, g, 0, 22, 54);
  for (const xx of [-w / 2 + 14, w / 2 - 14]) mesh(rb(5, 44, 42, 1), metal, g, xx, 0, 0);
  return g;
}
// a cat curled up on the floor, facing +x
function cat(par, x, y, rz) {
  const g = grp(par, x, y, 0, rz), fur = mat('#7f7873', { r: 0.95 }), dk = mat('#56524e', { r: 0.95 });
  mesh(gk('catb', () => new TH.CapsuleGeometry(10, 26, 4, 12).rotateZ(Math.PI / 2)), fur, g, -4, 0, 10);
  mesh(sph(8.5, 14, 10), fur, g, 19, 2, 12);
  for (const yy of [-2, 6]) mesh(gk('ear', () => new TH.ConeGeometry(3, 6, 4).rotateX(Math.PI / 2)), dk, g, 21, yy, 21);
  mesh(gk('catt', () => new TH.CapsuleGeometry(2.6, 26, 3, 8).rotateZ(Math.PI / 2)), dk, g, -8, -11, 3, { rz: 0.35 });
  return g;
}

/* ------------------------------------------------------------------ city */
// a facade texture: 8×8 bays of windows, some lit; map + emissive mask
function facadeTex(seed, lit, wall = '#2b2826') {
  const mk = () => { const c = document.createElement('canvas'); c.width = c.height = 512; return c; };
  const c = mk(), e = mk(), g = c.getContext('2d'), ge = e.getContext('2d');
  g.fillStyle = wall; g.fillRect(0, 0, 512, 512); ge.fillStyle = '#000'; ge.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 8; i++) for (let j = 0; j < 8; j++) {
    const x = i * 64, y = j * 64, r = rnd(i * 8 + j, seed);
    g.fillStyle = mixHex(wall, '#030404', 0.45); g.fillRect(x, y + 54, 64, 10);
    g.fillStyle = '#161514'; g.fillRect(x + 12, y + 12, 40, 34);
    if (r < lit * 0.55) {
      // a few windows lit, cool and dim, so the facades stay matte and the signals read first
      const col = r < lit * 0.25 ? '#d7c5b7' : r < lit * 0.7 ? '#cbc4bf' : '#ece6e2';
      ge.globalAlpha = 0.18 + 0.4 * rnd(i * 8 + j, seed + 1); ge.fillStyle = col; ge.fillRect(x + 12, y + 12, 40, 34); ge.globalAlpha = 1;
      g.fillStyle = col; g.fillRect(x + 12, y + 12, 40, 34);
      ge.fillStyle = 'rgba(8,6,4,0.5)'; ge.fillRect(x + 12 + 40 * rnd(i, seed + 3), y + 12, 6, 34);
    }
  }
  const T = (cv) => { const t = new TH.CanvasTexture(cv); t.colorSpace = TH.SRGBColorSpace; t.wrapS = t.wrapT = TH.RepeatWrapping; t.anisotropy = 8; return t; };
  const m = new TH.MeshStandardMaterial({ map: T(c), emissiveMap: T(e), emissive: C('#ffffff'), emissiveIntensity: 1.5, roughness: 0.85 });
  return m;
}
// a building box whose sides tile the facade (bay 300 wide, floor 320 tall), base at z
function bldgGeo(w, d, h, u0, v0) {
  const g = new TH.BoxGeometry(w, h, d), uv = g.attributes.uv;
  for (let f = 0; f < 6; f++) for (let k = 0; k < 4; k++) {
    const i = f * 4 + k;
    if (f === 2 || f === 3) { uv.setXY(i, 0.001, 0.001); continue; }
    const span = f < 2 ? d : w;
    uv.setXY(i, u0 + uv.getX(i) * span / 2400, v0 + uv.getY(i) * h / 2560);
  }
  g.rotateX(Math.PI / 2); g.translate(0, 0, h / 2);
  return g;
}
function building(par, x, y, w, d, h, fm, seed, roofCol = '#242220') {
  const g = grp(par, x, y);
  mesh(bldgGeo(w, d, h, Math.floor(rnd(seed, 1) * 8) / 8, Math.floor(rnd(seed, 2) * 8) / 8), fm, g);
  const roof = mat(roofCol, { r: 0.9 });
  mesh(rb(w + 8, d + 8, 30), roof, g, 0, 0, h);
  mesh(rb(w - 30, d - 30, 10), mat('#1a1817', { r: 0.95 }), g, 0, 0, h + 22);
  for (let k = 0; k < 3; k++) if (rnd(seed, k + 5) < 0.7) mesh(rb(80 + 60 * rnd(seed, k + 9), 70, 60 + 40 * rnd(seed, k + 2), 4), mat('#3a3735', { r: 0.7, m: 0.2 }), g, (rnd(seed, k + 11) - 0.5) * (w - 160), (rnd(seed, k + 13) - 0.5) * (d - 160), h + 30);
  return g;
}

/* ------------------------------------------------------------------ small helpers */
const hexA = (h, a) => `rgba(${parseInt(h.slice(1, 3), 16)},${parseInt(h.slice(3, 5), 16)},${parseInt(h.slice(5, 7), 16)},${a})`;
// a canvas texture painted once; rep = [u, v] repeats
// (all of them are painted again once the web fonts have loaded: ctexRedraw)
const CTEX = [];
function ctex(w, h, fn, rep) {
  const c = document.createElement('canvas'); c.width = w; c.height = h; fn(c.getContext('2d'), w, h);
  const t = new TH.CanvasTexture(c); t.colorSpace = TH.SRGBColorSpace; t.anisotropy = 8;
  if (rep) { t.wrapS = t.wrapT = TH.RepeatWrapping; t.repeat.set(rep[0], rep[1]); }
  t.cv = c; CTEX.push([c, fn, t]); return t;
}
function ctexRedraw() { for (const [c, fn, t] of CTEX) { const g = c.getContext('2d'); g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, c.width, c.height); fn(g, c.width, c.height); t.needsUpdate = true; } }
const texM = (map, o = {}) => new TH.MeshStandardMaterial({ map, color: C(o.c || '#ffffff'), roughness: o.r ?? 0.85, metalness: o.m ?? 0 });
const screenM = (map, k = 1) => { const m = new TH.MeshBasicMaterial({ map, toneMapped: false }); m.color.setScalar(k); return m; };
// a flat plane: face 'up' (default), '-y' (faces the camera side) or '+x'
function plane(par, w, h, m, x, y, z, face) {
  const me = new TH.Mesh(new TH.PlaneGeometry(w, h), m); me.position.set(x, y, z); me.receiveShadow = true;
  if (face === '-y') me.rotation.x = Math.PI / 2;
  if (face === '+x') { me.rotation.order = 'ZXY'; me.rotation.set(Math.PI / 2, 0, Math.PI / 2); }
  (par || scene).add(me); return me;
}
// additive floor glow (no light cost)
const GP2 = new TH.PlaneGeometry(2, 2);
function glowSpot(par, x, y, z, r, col, a) {
  const m = new TH.Mesh(GP2, new TH.MeshBasicMaterial({ map: TX_POOL, color: C(col), transparent: true, opacity: a, blending: TH.AdditiveBlending, depthWrite: false, toneMapped: false }));
  m.position.set(x, y, z); m.scale.set(r, r, 1); m.renderOrder = 1; (par || scene).add(m); return m;
}
// a stadium (rounded-end rectangle) shape, straight length L, radius R; with a hole of radius Rh
function stadium(L, R, Rh) {
  const mk = (S, r, rev) => {
    S.moveTo(-L / 2, -r); S.lineTo(L / 2, -r); S.absarc(L / 2, 0, r, -Math.PI / 2, Math.PI / 2, false);
    S.lineTo(-L / 2, r); S.absarc(-L / 2, 0, r, Math.PI / 2, Math.PI * 1.5, false); return S;
  };
  const s = mk(new TH.Shape(), R);
  if (Rh) s.holes.push(mk(new TH.Path(), Rh));
  return s;
}
const extr = (shape, h, bev = 2) => new TH.ExtrudeGeometry(shape, { depth: h, bevelEnabled: bev > 0, bevelThickness: bev, bevelSize: bev, bevelSegments: 2, curveSegments: 32 });
// point at distance u along a stadium centreline (L, R), and its heading
function stadiumAt(L, R, u) {
  const per = 2 * L + 2 * Math.PI * R; u = ((u % per) + per) % per;
  if (u < L) return [-L / 2 + u, -R, 0];
  u -= L; if (u < Math.PI * R) { const a = -Math.PI / 2 + u / R; return [L / 2 + Math.cos(a) * R, Math.sin(a) * R, a + Math.PI / 2]; }
  u -= Math.PI * R; if (u < L) return [L / 2 - u, R, Math.PI];
  u -= L; const a = Math.PI / 2 + u / R; return [-L / 2 + Math.cos(a) * R, Math.sin(a) * R, a + Math.PI / 2];
}

/* ------------------------------------------------------------------ HUD */
// Glass cards: an accent bar, a small coloured caps label over a bold white value, and an elbow leader with a pulsing
// dot on the object it names. Call hud.begin() each frame, then hud.card / hud.chip, then hud.end().
const hud = (() => {
  const lay = div($('world'), 'layer'); lay.id = 'hud';
  const svg = document.createElementNS(SVGNS, 'svg'); svg.setAttribute('width', 540); svg.setAttribute('height', 960);
  svg.style.cssText = 'position:absolute;left:0;top:0;overflow:visible'; lay.appendChild(svg);
  const E = {}, LP = []; let li = 0, seen = new Set();
  const ldr = () => {
    if (!LP[li]) {
      const g = document.createElementNS(SVGNS, 'g');
      g.innerHTML = '<polyline fill="none" stroke-width="1.25" stroke-linejoin="round" stroke-linecap="round"/><circle r="2.4"/><circle fill="none" stroke-width="1"/>';
      svg.appendChild(g); LP.push(g);
    }
    return LP[li++];
  };
  function place(key, cls, html, o, t) {
    let e = E[key];
    if (!e) { e = E[key] = div(lay, cls); e._h = null; }
    seen.add(key);
    const p = popIn(t, o.a, o.b ?? 1e9);
    if (p.a <= 0.001) { e.style.display = 'none'; return; }
    if (e._h !== html) { e._h = html; e.innerHTML = html; }
    const col = o.c || O;
    if (e._c !== col) { e._c = col; e.style.setProperty('--c', col); e.style.setProperty('--cg', hexA(col, 0.32)); e.style.setProperty('--cb', hexA(col, 0.09)); }
    e.style.display = 'block';
    const w = e.offsetWidth, h = e.offsetHeight;
    const an = o.w ? P(...o.w) : null;
    let x = o.x ?? 0, y = o.y ?? 0;
    if (o.rel && an) { x += an[0]; y += an[1]; }
    if (o.cx) x -= w / 2;
    x = clamp(x, 14, 526 - w); y = clamp(y, 118, 724 - h);
    e.style.left = x + 'px'; e.style.top = y + 'px'; e.style.opacity = p.a;
    e.style.transform = `translateY(${p.y}px) scale(${p.s})`;
    if (an && o.lead !== false) {
      // an elbow: a 45-degree run off the object, then level into the card's nearest side; it draws itself on
      const ins = an[0] > x - 6 && an[0] < x + w + 6;
      const sx = an[0] < x ? -1 : 1, qx = ins ? clamp(an[0], x + 14, x + w - 14) : (sx < 0 ? x : x + w), qy = ins ? (an[1] < y ? y : y + h) : clamp(an[1], y + h / 2, y + h / 2);
      const dx = Math.abs(qx - an[0]), dy = Math.abs(qy - an[1]);
      if (Math.hypot(dx, dy) > 10) {
        const g = ldr(), [ln, d1, d2] = g.children;
        const run = ins ? 0 : Math.max(0, dx - Math.min(dy, Math.max(0, dx - 16))), kx = qx + (an[0] < qx ? -run : run);
        const pts = ins ? [[an[0], an[1]], [qx, qy]] : [[an[0], an[1]], [kx, qy], [qx, qy]];
        let L = 0; for (let i = 1; i < pts.length; i++) L += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
        const dr = ease.out(prog(t, o.a, o.a + 0.32));
        g.style.display = ''; g.style.opacity = Math.min(1, p.a * 1.2);
        ln.setAttribute('points', pts.map((q) => q.join(',')).join(' ')); ln.setAttribute('stroke', hexA(col, 0.85));
        ln.setAttribute('stroke-dasharray', L); ln.setAttribute('stroke-dashoffset', L * (1 - dr));
        const pr = (t * 0.9) % 1;
        d1.setAttribute('fill', col); d2.setAttribute('stroke', hexA(col, 0.7 * (1 - pr))); d2.setAttribute('r', 3 + 7 * pr);
        for (const d of [d1, d2]) { d.setAttribute('cx', an[0]); d.setAttribute('cy', an[1]); }
      }
    }
  }
  return {
    begin() { li = 0; seen = new Set(); },
    end() { for (let i = li; i < LP.length; i++) LP[i].style.display = 'none'; for (const k in E) if (!seen.has(k)) E[k].style.display = 'none'; },
    // o: { k: label, v: value, c: colour, w: world anchor, x, y (top-left px; rel → offset from the anchor), a, b, big }
    card(key, o, t) { place(key, 'hc' + (o.big ? ' big' : ''), `<div class="k">${o.k}</div><div class="v">${o.v}</div>`, o, t); },
    // a small pill label ("Lens", "Board")
    chip(key, o, t) { place(key, 'hp' + (o.hot ? ' hot' : ''), o.s, o, t); },
  };
})();
