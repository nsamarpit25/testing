// 35 Face ID props, built from kit.js: a sculpted ceramic head on a plinth (closed eyes, gallery bust), the phone held
// in front of it with its TrueDepth parts (infrared camera, flood light, selfie camera, dot projector), the dot pattern
// ray-marched onto the face, a printed photo on a stand and the 3D-printed mask. One shader on the face-like surfaces
// can show them as the infrared picture (uIR) or as a depth map with contour lines (uDepth), measured from the phone.
// Units: the head is 100 tall (about 4.3 units per real cm). z up. Load after kit.js.

const wpos = (o) => { const v = new TH.Vector3(); o.getWorldPosition(v); return [v.x, v.y, v.z]; };
const sstep = (a, b, x) => { const k = clamp((x - a) / (b - a)); return k * k * (3 - 2 * k); };
const gs = (x, y, cx, cy, sx, sy) => Math.exp(-(((x - cx) / sx) ** 2) - (((y - cy) / sy) ** 2));

/* ------------------------------------------------------------------ the head (headR, headHit, HR, HS: head.js) */
function headGeo(seg = 220, o = {}) {
  const g = new TH.SphereGeometry(1, seg, Math.round(seg * 0.75), o.p0 ?? -Math.PI / 2, o.pl ?? Math.PI * 2, o.t0 ?? 0, o.tl ?? Math.PI);
  const P = g.attributes.position;
  for (let i = 0; i < P.count; i++) { const x = P.getX(i), y = P.getY(i), z = P.getZ(i), r = HR * headR(x, y, z) * (o.k ?? 1); P.setXYZ(i, x * r, y * r, z * r); }
  g.computeVertexNormals(); return g;
}

/* ------------------------------------------------------------------ the real head: Lee Perry-Smith scan (leehead.js) */
// baked into head-local units: x right, y up (eyes at 0), z forward (the face looks along +z); ~97 units crown to chin.
// o.mask keeps only the front of the face (the 3D-printed mask); o.cut drops the shoulders below that y (scan units).
const LEE_S = 20.6, LEE_EYE = 1.85, LEE_Z = 0.3;
const _b64 = (s, T) => { const b = atob(s), u = new Uint8Array(b.length); for (let i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); return new T(u.buffer); };
function leeGeo(o = {}) {
  const P = _b64(LEE.p, Float32Array), N = _b64(LEE.n, Float32Array), UV = _b64(LEE.uv, Float32Array), I = _b64(LEE.i, Uint16Array);
  const keep = (k) => { const x = P[3 * k], y = P[3 * k + 1], z = P[3 * k + 2];
    return o.mask ? (z > -0.3 && y > -1.3 && y < 3.7 && Math.abs(x) < 2.05) : y > (o.cut ?? -9); };
  const idx = []; for (let i = 0; i < I.length; i += 3) if (keep(I[i]) && keep(I[i + 1]) && keep(I[i + 2])) idx.push(I[i], I[i + 1], I[i + 2]);
  const Q = new Float32Array(P.length); for (let k = 0; k < P.length; k += 3) { Q[k] = P[k] * LEE_S; Q[k + 1] = (P[k + 1] - LEE_EYE) * LEE_S; Q[k + 2] = (P[k + 2] - LEE_Z) * LEE_S; }
  const g = new TH.BufferGeometry();
  g.setAttribute('position', new TH.BufferAttribute(Q, 3)); g.setAttribute('normal', new TH.BufferAttribute(N, 3)); g.setAttribute('uv', new TH.BufferAttribute(UV, 2));
  if (o.mask) { const A = new Float32Array((Q.length / 3) * 2); for (let k = 0; k < Q.length / 3; k++) { A[2 * k] = Q[3 * k]; A[2 * k + 1] = Q[3 * k + 1]; } g.setAttribute('aL', new TH.BufferAttribute(A, 2)); }
  g.setIndex(idx); if (!o.mask) g.computeTangents(); return g;
}
const LEE_NM = new TH.TextureLoader().load('assets/Infinite-Level_02_Tangent_SmoothUV.jpg', () => (LEE_NM.ready = true));

/* ------------------------------------------------------------------ the face shader: ceramic / infrared / depth map */
const ORIGIN = new TH.Vector3();   // the phone's TrueDepth window, set once the phone is built
function faceMat(col, o = {}) {
  const m = new TH.MeshPhysicalMaterial({ color: C(col), roughness: o.r ?? 0.55, metalness: 0, clearcoat: o.cc ?? 0.18, clearcoatRoughness: 0.5, envMap: STUDIO_ENV, envMapIntensity: 0.55 });
  if (o.map) m.map = o.map;
  if (o.vc) m.vertexColors = true;
  m.userData.u = { uIR: { value: 0 }, uDepth: { value: 0 }, uOrigin: { value: ORIGIN }, uNear: { value: 100 }, uFar: { value: 190 }, uFlat: { value: o.flat ? 1 : 0 }, uIRk: { value: 1 }, uOv: { value: new TH.Vector3(...(o.oval || [0, 0, 0])) } };
  m.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, m.userData.u);
    sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nvarying vec3 vWP; varying vec3 vWN;' + (o.oval ? '\nattribute vec2 aL; varying vec2 vL;' : ''))
      .replace('#include <project_vertex>', '#include <project_vertex>\nvWP = (modelMatrix * vec4(transformed, 1.0)).xyz; vWN = normalize(mat3(modelMatrix) * objectNormal);' + (o.oval ? '\nvL = aL;' : ''));
    if (o.oval) sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying vec2 vL; uniform vec3 uOv;').replace('#include <clipping_planes_fragment>', '#include <clipping_planes_fragment>\nvec2 qo = vec2(vL.x / uOv.x, (vL.y - uOv.z) / uOv.y); if (dot(qo, qo) > 1.0) discard;');
    sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying vec3 vWP; varying vec3 vWN; uniform float uIR, uDepth, uNear, uFar, uFlat, uIRk; uniform vec3 uOrigin;')
      .replace('#include <dithering_fragment>', `#include <dithering_fragment>
      vec3 L = uOrigin - vWP; float dd = length(L);
      // infrared picture: lit only by the flood light at the phone, falling off with distance, in grey
      float ir = clamp((dot(normalize(vWN), L / dd) + 0.3) / 1.3, 0.0, 1.0); ir = pow(ir, 1.1) * 0.62 * (120.0 * 120.0) / (dd * dd);
      vec3 irc = vec3(0.74, 0.73, 0.72) * clamp(ir, 0.0, 1.0) * uIRk + 0.012;
      gl_FragColor.rgb = mix(gl_FragColor.rgb, irc, uIR);
      // depth map: near = bright orange, far = dark, with thin contour lines every 6 units
      float k = clamp((dd - uNear) / (uFar - uNear), 0.0, 1.0);
      float lum = dot(gl_FragColor.rgb, vec3(0.3, 0.55, 0.15)); vec3 dc = mix(vec3(1.0, 0.56, 0.26) * (0.45 + 0.75 * lum), vec3(0.05, 0.04, 0.035) + 0.25 * lum, pow(k, 0.85));
      float cl = abs(fract(dd / 8.0) - 0.5); float line = 1.0 - smoothstep(0.0, fwidth(dd / 6.0) * 1.2, cl - 0.0);
      line = (1.0 - smoothstep(0.012, 0.012 + fwidth(dd / 8.0) * 1.2, 0.5 - cl)) * (1.0 - uFlat * 0.85);
      dc += vec3(1.0, 0.62, 0.36) * line * 0.34 * (1.0 - k * 0.5);
      gl_FragColor.rgb = mix(gl_FragColor.rgb, dc, uDepth);`);
  };
  return m;
}
const setFace = (m, ir, depth) => { m.userData.u.uIR.value = ir; m.userData.u.uDepth.value = depth; };

/* ------------------------------------------------------------------ the bust */
// head group: local x right, y up, z forward; placed so world z is up and the face looks along world -y (rz turns it)
function buildBust(par, x, y, rz = 0) {
  const g = grp(par, x, y, 0, rz);
  const hm = faceMat('#d8d4cf', { r: 0.6 });
  const plinth = mat('#1d1b1a', { r: 0.7 });
  mesh(rb(150, 150, 70, 3, 3), plinth, g, 0, 0, 0);
  const torso = new TH.SphereGeometry(1, 96, 48, 0, Math.PI * 2, 0, Math.PI * 0.5); torso.scale(64, 42, 40); torso.rotateX(Math.PI / 2);
  const tm = mesh(torso, hm, g, 0, -2, 72);
  const head = new TH.Group(); head.rotation.set(Math.PI / 2, 0, 0); head.position.set(0, -4, 150); g.add(head);
  // local y → world z, local z (the face) → world -y; tilt the chin a touch down
  const hg = new TH.Group(); hg.rotation.x = 0.1; head.add(hg);
  const hmesh = mesh(leeGeo({ cut: -1.25 }), hm, hg); hmesh.castShadow = true;
  return { g, head: hg, mesh: hmesh, m: hm, torso: tm };
}
// head-local ↔ world for one bust
const toWorld = (B, p) => { B.head.updateWorldMatrix(true, false); const v = new TH.Vector3(...p).applyMatrix4(B.head.matrixWorld); return [v.x, v.y, v.z]; };
function toLocal(B, p, dir) {
  B.head.updateWorldMatrix(true, false); const inv = B.head.matrixWorld.clone().invert();
  const o = new TH.Vector3(...p).applyMatrix4(inv), d = new TH.Vector3(...dir).transformDirection(inv);
  return [[o.x, o.y, o.z], [d.x, d.y, d.z]];
}

/* ------------------------------------------------------------------ the phone and its TrueDepth parts */
// parts along the top of the screen, in phone-local x (units of sc): IR camera, flood light, selfie camera, dot projector
const TD = [{ k: 'ir', x: -0.62, r: 0.2, lab: 'Infrared camera' }, { k: 'flood', x: -0.25, r: 0.13, lab: 'Flood light' },
  { k: 'selfie', x: 0.3, r: 0.19, lab: 'Selfie camera' }, { k: 'dots', x: 0.66, r: 0.2, lab: 'Dot projector' }];
function buildPhone(par, x, y, z, sc, rz, lean = 0.05) {
  const g = grp(par, x, y, z, rz);
  const tilt = new TH.Group(); tilt.rotation.x = Math.PI / 2 - lean; g.add(tilt);     // stand it up: screen towards -y (rz = PI turns it to +y)
  const ph = phone3(tilt, 0, 0, 0, sc, '#3a3734', 'plain');
  const top = ph.H / 2 - 0.42 * sc - 0.62 * sc, zf = ph.T / 2;
  // the parts sit inside the island; each is a tiny lens on a dark mount that can slide out along +z (the exploded view)
  const lensM = pmat('#0c0b0d', { r: 0.04, cc: 1, env: 1.5 }), mountM = mat('#141312', { r: 0.6 });
  const em = { ir: pmat('#1a1220', { r: 0.1, cc: 1, env: 1.2 }), flood: pmat('#2a1e26', { r: 0.25, cc: 0.6, env: 1 }), selfie: lensM, dots: pmat('#1d1420', { r: 0.08, cc: 1, env: 1.3 }) };
  const parts = TD.map((p) => {
    const pg = grp(tilt, p.x * sc, top, zf + 0.06 * sc);
    const body = mesh(p.k === 'flood' ? rbc(p.r * 2.1 * sc, p.r * 2.1 * sc, 0.5 * sc, 0.05 * sc) : cy(p.r * 1.25 * sc, p.r * 1.25 * sc, 0.5 * sc, 40), mountM, pg, 0, 0, p.k === "flood" ? -0.25 * sc : -0.5 * sc, { cast: false });
    const lens = mesh(p.k === 'flood' ? rbc(p.r * 1.5 * sc, p.r * 1.5 * sc, 0.06 * sc, 0.02 * sc) : cy(p.r * sc, p.r * sc, 0.06 * sc, 40), em[p.k], pg, 0, 0, 0.0, { cast: false });
    return { ...p, g: pg, lens, z0: zf + 0.06 * sc };
  });
  const at = (k) => parts.find((p) => p.k === k);
  return { g, tilt, ph, parts, at, sc, s: ph.s };
}
// a part's world position (front face of its lens)
const partW = (PH, k) => wpos(PH.at(k).g);

/* ------------------------------------------------------------------ dots */
// a soft round point sprite with per-point reveal: aT in [0,1] is when the point lands as uP sweeps 0 → 1
function dotCloud(n, col, size) {
  const geo = new TH.BufferGeometry();
  geo.setAttribute('position', new TH.Float32BufferAttribute(new Float32Array(n * 3), 3));
  geo.setAttribute('aT', new TH.Float32BufferAttribute(new Float32Array(n), 1));
  geo.setAttribute('aS', new TH.Float32BufferAttribute(new Float32Array(n).fill(1), 1));
  const m = new TH.ShaderMaterial({
    uniforms: { uP: { value: 0 }, uA: { value: 1 }, uSize: { value: size }, uCol: { value: C(col) }, uHot: { value: 0 } },
    vertexShader: `attribute float aT; attribute float aS; uniform float uP, uSize, uHot; varying float vA;
      void main() { float k = clamp((uP - aT) / 0.06, 0.0, 1.0); vA = k; vec4 mv = modelViewMatrix * vec4(position, 1.0); gl_Position = projectionMatrix * mv;
        gl_PointSize = uSize * aS * (1.0 + 1.6 * (1.0 - k) * step(0.001, k) + uHot); }`,
    fragmentShader: `uniform vec3 uCol; uniform float uA; varying float vA;
      void main() { float r = length(gl_PointCoord - 0.5) * 2.0; float a = smoothstep(1.0, 0.35, r) * vA * uA; if (a < 0.01) discard; gl_FragColor = vec4(uCol * (0.95 + 0.7 * smoothstep(0.55, 0.0, r)), a); }`,
    transparent: true, depthWrite: false, toneMapped: false,
  });
  const pts = new TH.Points(geo, m); pts.frustumCulled = false; pts.renderOrder = 4; scene.add(pts);
  return { pts, geo, m, n };
}
// fire n rays from the projector in a jittered pattern across the face and keep the hits (world positions, with the
// normal offset so they sit on the skin); also returns for each hit the depth from the projector
const _rc = new TH.Raycaster(); _rc.near = 20; _rc.far = 600;
function projectDots(B, from, n, spread, aimAt, seed = 1) {
  (B.mesh || B.frame).updateWorldMatrix(true, false);
  const f = new TH.Vector3(...from), aim = new TH.Vector3(...aimAt), fw = aim.clone().sub(f).normalize();
  const rt = new TH.Vector3().crossVectors(fw, new TH.Vector3(0, 0, 1)).normalize(), up = new TH.Vector3().crossVectors(rt, fw).normalize();
  const out = [];
  for (let i = 0; i < n; i++) {
    // a jittered grid in angle space (the real projector uses a pseudo-random pattern)
    const gx = Math.floor(Math.sqrt(n * 0.8)), u = ((i % gx) + rnd(i, seed) * 0.9) / gx - 0.5, v = (Math.floor(i / gx) + rnd(i, seed + 7) * 0.9) / Math.ceil(n / gx) - 0.5;
    const d = fw.clone().addScaledVector(rt, u * spread * 0.8).addScaledVector(up, v * spread).normalize();
    _rc.set(f, d); const hit = _rc.intersectObject(B.mesh || B.frame, false)[0];
    if (!hit) continue;
    const nw = hit.face.normal.clone().transformDirection(hit.object.matrixWorld), q = hit.point.clone().addScaledVector(nw, 0.6);
    out.push({ p: [q.x, q.y, q.z], t: hit.distance, u, v, dir: [d.x, d.y, d.z] });
  }
  return out;
}

/* ------------------------------------------------------------------ volumes: the flood light's cone, ray streaks */
const CONE_TX = ctex(64, 256, (g, w, h) => { const gr = g.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, 'rgba(255,255,255,0.75)'); gr.addColorStop(0.35, 'rgba(255,255,255,0.22)'); gr.addColorStop(1, 'rgba(255,255,255,0.04)'); g.fillStyle = gr; g.fillRect(0, 0, w, h); });
// a soft additive cone; cone.aim(a, b, R) puts the apex at a and the base (radius R) at b
function cone(col) {
  const geo = new TH.CylinderGeometry(0.004, 1, 1, 64, 1, true); geo.translate(0, -0.5, 0);
  const m = new TH.MeshBasicMaterial({ map: CONE_TX, color: C(col), transparent: true, opacity: 0, blending: TH.AdditiveBlending, depthWrite: false, side: TH.DoubleSide, toneMapped: false });
  m.onBeforeCompile = (sh) => {
    sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nvarying float vF;').replace('#include <project_vertex>', '#include <project_vertex>\nvec3 nv = normalize(normalMatrix * normal); vF = abs(dot(nv, normalize(-mvPosition.xyz)));');
    sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying float vF;').replace('#include <dithering_fragment>', '#include <dithering_fragment>\ngl_FragColor.a *= smoothstep(0.0, 0.6, vF);');
  };
  const me = new TH.Mesh(geo, m); me.renderOrder = 3; me.frustumCulled = false; me.visible = false; scene.add(me);
  me.aim = (a, b, R, op) => {
    me.visible = op > 0.004; if (!me.visible) return; m.opacity = op;
    const d = new TH.Vector3(b[0] - a[0], b[1] - a[1], b[2] - a[2]), L = d.length();
    me.position.set(...a); me.quaternion.setFromUnitVectors(new TH.Vector3(0, -1, 0), d.normalize()); me.scale.set(R, L, R);
  };
  return me;
}
// thin line segments with per-segment alpha (rays from the projector, the camera's sight lines)
function segs3(n, col, w = 1.3) {
  const L = []; for (let i = 0; i < n; i++) { const geo = new TH.LineGeometry(); geo.setPositions([0, 0, 0, 0, 0, 1]); const l = new TH.Line2(geo, lineMat(col, w, { add: true, op: 0 })); l.visible = false; l.frustumCulled = false; l.renderOrder = 5; scene.add(l); L.push(l); }
  let k = 0;
  return {
    begin() { k = 0; },
    add(a, b, op, col2) { if (k >= L.length || op <= 0.005) return; const l = L[k++]; l.geometry.setPositions([...a, ...b]); l.material.opacity = op; if (col2) l.material.color.set(col2); l.visible = true; },
    end() { for (let i = k; i < L.length; i++) L[i].visible = false; },
  };
}

/* ------------------------------------------------------------------ photo and mask */
// the head drawn from the front into a texture (the photo print), using a throwaway camera
function headPhotoTex(B, w = 512, h = 640) {
  const rt = new TH.WebGLRenderTarget(w, h, { samples: 4 });
  const c = new TH.PerspectiveCamera(22, w / h, 10, 4000), hp = toWorld(B, [0, -24, 0]), fwd = toWorld(B, [0, -24, 470]);
  c.up.set(0, 0, 1); c.position.set(...fwd); c.lookAt(...hp);
  const vis = scene.children.map((o) => [o, o.visible]); scene.children.forEach((o) => { if (o !== B.g) o.visible = false; });
  // its own soft portrait light: a large key from the front left, a warm fill, a faint rim from behind
  const key = new TH.DirectionalLight(0xfff4ea, 2.4), fill = new TH.HemisphereLight(0xf2ece6, 0x4a423c, 1.1), rim = new TH.DirectionalLight(0xffe2cc, 0.9);
  key.position.set(...toWorld(B, [-260, 160, 420])); key.target.position.set(...hp); rim.position.set(...toWorld(B, [200, 120, -300])); rim.target.position.set(...hp);
  [key, key.target, fill, rim, rim.target].forEach((o) => scene.add(o));
  const bg = scene.background; scene.background = C('#6f665f');
  const sh = renderer.shadowMap.enabled; renderer.shadowMap.enabled = false;
  renderer.setRenderTarget(rt); _rawRender(scene, c); renderer.setRenderTarget(null); renderer.shadowMap.enabled = sh;
  [key, key.target, fill, rim, rim.target].forEach((o) => scene.remove(o));
  scene.background = bg; vis.forEach(([o, v]) => (o.visible = v));
  return rt.texture;
}
function buildPhoto(par, x, y, rz, tex) {
  const g = grp(par, x, y, 0, rz);
  const base = mat('#1d1b1a', { r: 0.7 }), rod = pmat('#8d8780', { r: 0.3, m: 1 });
  mesh(cy(26, 30, 6, 64), base, g); mesh(cy(1.6, 1.6, 150, 16), rod, g, 0, 2, 0);
  const card = grp(g, 0, 0, 175); card.rotation.x = Math.PI / 2;
  mesh(rbc(84, 108, 1.2, 0.6), mat('#efebe5', { r: 0.6 }), card, 0, 0, 0);
  const fm = faceMat('#ffffff', { map: tex, r: 0.65, cc: 0, flat: true });
  fm.emissiveMap = tex; fm.emissive = C('#ffffff'); fm.emissiveIntensity = 0.5;   // a print stays readable in the dark studio
  const img = mesh(new TH.PlaneGeometry(76, 95), fm, card, 0, 4, 0.66, { cast: false });
  return { g, card, img, m: fm, W: 76, H: 95 };
}
// the 3D-printed frame (front half of a face, a little coarse, printed-layer lines), a handmade nose, printed eyes
const LAYERS = ctex(64, 512, (g, w, h) => { g.fillStyle = '#ffffff'; g.fillRect(0, 0, w, h); for (let y = 0; y < h; y += 4) { g.fillStyle = `rgba(0,0,0,${0.045 + 0.02 * rnd(y, 2)})`; g.fillRect(0, y, w, 1.6); } }, [1, 0.6]);
// the mask's outline: an oval in head-local units (half-width, half-height, centre y): forehead to chin, cheek to cheek
const MASK_OVAL = [33, 50, -12];
const inOval = (x, y) => (x / MASK_OVAL[0]) ** 2 + ((y - MASK_OVAL[2]) / MASK_OVAL[1]) ** 2 <= 1;
function buildMask(par, x, y, rz) {
  const g = grp(par, x, y, 0, rz);
  const base = mat('#1d1b1a', { r: 0.7 }), rod = pmat('#8d8780', { r: 0.3, m: 1 });
  mesh(cy(30, 34, 6, 64), base, g); mesh(cy(2, 2, 150, 16), rod, g, 0, 10, 0);
  const head = new TH.Group(); head.rotation.set(Math.PI / 2, 0, 0); head.position.set(0, 0, 175); g.add(head);
  const frameM = faceMat('#ffffff', { map: LAYERS, r: 0.8, cc: 0, vc: true, oval: MASK_OVAL });
  const fg = leeGeo({ mask: true });
  // the handmade nose: the nose region in a muted skin tone, the rest the printer's grey
  const PP = fg.attributes.position, VC = [], gry = C('#c9c4be'), skin = C('#b8907a');
  for (let i = 0; i < PP.count; i++) {
    const x = PP.getX(i), y = PP.getY(i), z = PP.getZ(i), n = Math.hypot(x, y, z);
    const k = sstep(2.4 * HS, 1.6 * HS, Math.abs(x)) * sstep(-6 * HS, -5 * HS, y) * sstep(1.6 * HS, 0.8 * HS, y) * sstep(8.3 * HS, 9 * HS, z);
    const c = gry.clone().lerp(skin, k); VC.push(c.r, c.g, c.b);
  }
  fg.setAttribute('color', new TH.Float32BufferAttribute(VC, 3));
  const frame = mesh(fg, frameM, head); frameM.side = TH.DoubleSide;
  const noseM = frameM;
  // printed eyes: flat paper patches with a drawn eye, stuck into the sockets
  const EYE = ctex(256, 128, (gx, w, h) => {
    gx.fillStyle = '#e9e4dd'; gx.beginPath(); gx.ellipse(w / 2, h / 2, w / 2 - 6, h / 2 - 8, 0, 0, 7); gx.fill();
    gx.strokeStyle = '#3b2f28'; gx.lineWidth = 6; gx.beginPath(); gx.moveTo(30, 70); gx.quadraticCurveTo(128, 10, 226, 70); gx.quadraticCurveTo(128, 112, 30, 70); gx.stroke();
    gx.fillStyle = '#5a463a'; gx.beginPath(); gx.arc(128, 64, 26, 0, 7); gx.fill(); gx.fillStyle = '#1a1310'; gx.beginPath(); gx.arc(128, 64, 11, 0, 7); gx.fill();
  });
  const eyeM = faceMat('#ffffff', { map: EYE, r: 0.85, cc: 0, flat: true }); eyeM.transparent = true; eyeM.alphaTest = 0.5;
  const eyes = [-1, 1].map((s) => { const e = mesh(new TH.PlaneGeometry(14, 7), eyeM, head, 3.15 * s * HS, 0, 8.25 * HS); e.rotation.y = 0.3 * s; e.castShadow = false; return e; });
  return { g, head, frame, frameM, noseM, eyeM, eyes, mats: [frameM, noseM, eyeM] };
}

/* ------------------------------------------------------------------ the phone's two pictures, as small images */
// the head seen straight on, computed on the CPU once: a depth map (near = bright orange, contour lines) and an
// infrared picture (grey, lit from the viewer). Returns data URLs for the HUD cards.
function faceThumbs(w = 96, h = 120) {
  const X0 = -46, X1 = 46, Y0 = -64, Y1 = 52, Z = new Float32Array(w * h).fill(NaN);
  for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) {
    const x = lerp(X0, X1, (i + 0.5) / w), y = lerp(Y1, Y0, (j + 0.5) / h), t = headHit([x, y, 200], [0, 0, -1], 100, 300);
    if (t > 0) Z[j * w + i] = 200 - t;
  }
  const mk = (fn) => { const c = document.createElement('canvas'); c.width = w; c.height = h; const g = c.getContext('2d'), im = g.createImageData(w, h);
    for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) { const z = Z[j * w + i], k = (j * w + i) * 4; const [r, gg, b, a] = isNaN(z) ? [0, 0, 0, 0] : fn(z, i, j); im.data.set([r, gg, b, a], k); }
    g.putImageData(im, 0, 0); return c.toDataURL(); };
  const dz = (i, j) => { const a = Z[j * w + Math.max(0, i - 1)], b = Z[j * w + Math.min(w - 1, i + 1)], c = Z[Math.max(0, j - 1) * w + i], d = Z[Math.min(h - 1, j + 1) * w + i]; return [isNaN(a) || isNaN(b) ? 0 : (b - a) / 2, isNaN(c) || isNaN(d) ? 0 : (d - c) / 2]; };
  const px = (X1 - X0) / w;
  const depth = mk((z, i, j) => {
    const k = clamp((z - 0) / 56), c = [lerp(16, 255, k ** 1.2), lerp(8, 140, k ** 1.4), lerp(4, 56, k ** 1.6)];
    const f = Math.abs(((z / 5) % 1) - 0.5), line = f > 0.43 ? 0.5 : 0;
    return [c[0] + (255 - c[0]) * line * 0.6, c[1] + (200 - c[1]) * line * 0.6, c[2] + (150 - c[2]) * line * 0.6, 255];
  });
  const ir = mk((z, i, j) => {
    const [gx, gy] = dz(i, j), n = [-gx / px, gy / px, 1], L = Math.hypot(...n), d = Math.max(0, n[2] / L), v = 30 + 215 * Math.pow(d, 1.3) * (0.75 + 0.25 * clamp(z / 50));
    return [v, v * 0.98, v * 0.96, 255];
  });
  return { depth, ir };
}
// dots on a flat card: rays from the projector against the plane y = py (world), kept inside the card
function projectFlat(from, n, spread, aimAt, py, box, seed = 3) {
  const f = new TH.Vector3(...from), aim = new TH.Vector3(...aimAt), fw = aim.clone().sub(f).normalize();
  const rt = new TH.Vector3().crossVectors(fw, new TH.Vector3(0, 0, 1)).normalize(), up = new TH.Vector3().crossVectors(rt, fw).normalize();
  const out = [], gx = Math.floor(Math.sqrt(n * 0.8));
  for (let i = 0; i < n; i++) {
    const u = ((i % gx) + rnd(i, seed) * 0.9) / gx - 0.5, v = (Math.floor(i / gx) + rnd(i, seed + 7) * 0.9) / Math.ceil(n / gx) - 0.5;
    const d = fw.clone().addScaledVector(rt, u * spread * 0.8).addScaledVector(up, v * spread).normalize();
    const t = (py - f.y) / d.y, p = [f.x + d.x * t, py, f.z + d.z * t];
    if (Math.abs(p[0] - box[0]) > box[2] || Math.abs(p[2] - box[1]) > box[3]) continue;
    out.push({ p, t, u, v, dir: [d.x, d.y, d.z] });
  }
  return out;
}
// fill a dot cloud from hits: reveal time per dot (aT) scattered so the pattern rains on, not wipes on
function fillDots(D, hits, seed = 1) {
  const P = D.geo.attributes.position, A = D.geo.attributes.aT, S = D.geo.attributes.aS;
  hits.forEach((h, i) => { P.setXYZ(i, ...h.p); A.setX(i, 0.05 + 0.85 * rnd(i, seed + 11)); S.setX(i, 0.9 + 0.2 * rnd(i, seed + 5)); });
  D.geo.setDrawRange(0, hits.length); P.needsUpdate = A.needsUpdate = S.needsUpdate = true; D.hits = hits;
}
