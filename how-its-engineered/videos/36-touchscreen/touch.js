// 36 Touchscreen props, built from kit.js: a phone lying on a plinth with a passcode keypad on its screen, its display
// stack that lifts apart (cover glass, the see-through sensor grid of rows and columns), the field at every crossing
// (soft points), the signal at each crossing (thin bars), and the things that tap it: a ceramic finger with a nail, a
// knitted glove, a snack sausage, a drop of water. Units: the phone is sc = 10 (about 10 units per real cm). z up.

const sstep = (a, b, x) => { const k = clamp((x - a) / (b - a)); return k * k * (3 - 2 * k); };
const PSC = 10, PLINTH_H = 70;

/* ------------------------------------------------------------------ the phone, flat on its plinth */
function buildRig(x, y) {
  const g = grp(null, x, y, 0);
  mesh(rb(150, 228, PLINTH_H, 4.5, 3), mat('#161514', { r: 0.55 }), g, 0, 0, 0);
  const ph = phone3(g, 0, 0, PLINTH_H + 0.39 * PSC, PSC, '#3a3734');
  const sw = ph.W - 2 * 0.42 * PSC, sh = ph.H - 2 * 0.42 * PSC, top = PLINTH_H + 0.78 * PSC;
  return { g, ph, s: ph.s, sw, sh, top };
}

/* ------------------------------------------------------------------ the display stack: glass, grid, nodes, bars */
const NC = 8, NR = 16;
function buildStack(R) {
  const g = grp(R.g, 0, 0, R.top + 0.2);
  const node = (i, j) => [((i + 0.5) / NC) * R.sw - R.sw / 2, ((j + 0.5) / NR) * R.sh - R.sh / 2];
  // the sensor grid: rows (along x) in one layer, columns (along y) just above it, each line its own fade
  const grid = grp(g, 0, 0, 0), lm = (c) => new TH.MeshBasicMaterial({ color: C(c), transparent: true, opacity: 0, depthWrite: false, toneMapped: false });
  const rows = [], cols = [];
  for (let j = 0; j < NR; j++) { const m = mesh(new TH.PlaneGeometry(R.sw + 4, 0.38), lm('#cfc8c1'), grid, 0, node(0, j)[1], 0, { cast: false }); m.renderOrder = 2; rows.push(m); }
  for (let i = 0; i < NC; i++) { const m = mesh(new TH.PlaneGeometry(0.38, R.sh + 4), lm('#a59d96'), grid, node(i, 0)[0], 0, 0.15, { cast: false }); m.renderOrder = 2; cols.push(m); }
  // a faint sheet the grid sits on (the sensor film), and the touch controller chip at its bottom edge
  const film = mesh(rrg(R.sw + 6, R.sh + 6, 4), new TH.MeshBasicMaterial({ color: C('#d9d5d1'), transparent: true, opacity: 0, depthWrite: false, toneMapped: false }), grid, 0, 0, -0.2, { cast: false });
  const chip = mesh(rbc(16, 6, 1.6, 0.6), pmat('#1a1918', { r: 0.4, m: 0.4 }), grid, 0, -R.sh / 2 - 7, 1.0);
  chip.visible = false;
  // the cover glass: a clear slab with soft reflections
  const glassM = new TH.MeshPhysicalMaterial({ color: C('#e9eef0'), roughness: 0.04, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.03, envMap: STUDIO_ENV, envMapIntensity: 0.45, transparent: true, opacity: 0, depthWrite: false });
  const glass = mesh(slab(R.sw + 6, R.sh + 6, 1.4, 4.5, 0.5, 4), glassM, g, 0, 0, 0, { cast: false }); glass.renderOrder = 6;
  // the field at each crossing: soft orange points whose brightness the scene sets every frame (aI)
  const N = NC * NR, P = new Float32Array(N * 3), I = new Float32Array(N);
  for (let j = 0; j < NR; j++) for (let i = 0; i < NC; i++) { const [x, y] = node(i, j); P.set([x, y, 0.4], (j * NC + i) * 3); }
  const geo = new TH.BufferGeometry(); geo.setAttribute('position', new TH.Float32BufferAttribute(P, 3)); geo.setAttribute('aI', new TH.Float32BufferAttribute(I, 1));
  const nm = new TH.ShaderMaterial({
    uniforms: { uSize: { value: 26 }, uCol: { value: C(O) }, uA: { value: 0 } },
    vertexShader: 'attribute float aI; uniform float uSize; varying float vI; void main() { vI = aI; vec4 mv = modelViewMatrix * vec4(position, 1.0); gl_Position = projectionMatrix * mv; gl_PointSize = uSize * (0.55 + 0.45 * aI); }',
    fragmentShader: 'uniform vec3 uCol; uniform float uA; varying float vI; void main() { float r = length(gl_PointCoord - 0.5) * 2.0; float a = (smoothstep(1.0, 0.0, r) * 0.55 + smoothstep(0.28, 0.0, r) * 0.6) * vI * uA; if (a < 0.01) discard; gl_FragColor = vec4(uCol * (0.9 + 0.6 * smoothstep(0.3, 0.0, r)), a); }',
    transparent: true, depthWrite: false, toneMapped: false, blending: TH.AdditiveBlending,
  });
  const nodes = new TH.Points(geo, nm); nodes.renderOrder = 4; nodes.frustumCulled = false; grid.add(nodes);
  // the signal at each crossing: thin bars standing on the grid
  const bg = new TH.BoxGeometry(1.6, 1.6, 1); bg.translate(0, 0, 0.5);
  const bm = new TH.MeshStandardMaterial({ color: C(O), emissive: C(O), emissiveIntensity: 0.4, roughness: 0.5, transparent: true, opacity: 0.95 });
  const bars = new TH.InstancedMesh(bg, bm, N); bars.frustumCulled = false; bars.renderOrder = 5; grid.add(bars);
  const M4 = new TH.Matrix4();
  return {
    g, grid, rows, cols, film, chip, glass, glassM, nodes, nm, bars, bm, node,
    // lift: 0 = assembled, 1 = exploded (glass above the grid, the grid above the screen)
    lift(k) { grid.position.z = 16 * k; glass.position.z = 0.6 + 40 * k; },
    setNodes(fn) { const a = geo.attributes.aI; for (let j = 0; j < NR; j++) for (let i = 0; i < NC; i++) a.setX(j * NC + i, fn(i, j)); a.needsUpdate = true; },
    setBars(fn) {
      for (let j = 0; j < NR; j++) for (let i = 0; i < NC; i++) { const [x, y] = node(i, j), h = fn(i, j); const v = h > 0.08 ? 1 : 0; M4.makeScale(v, v, Math.max(0.001, h)); M4.setPosition(x, y, 0.3); bars.setMatrixAt(j * NC + i, M4); }
      bars.instanceMatrix.needsUpdate = true;
    },
  };
}

/* ------------------------------------------------------------------ things that touch */
// a finger-like lathe along +z, tip at the origin: R radius, L length, slight swell
function tipGeo(R, L, flat = 0.88, swell = 0.1, joints = 0, rib = 0, taper = 0) {
  const pts = [];
  for (let k = 0; k <= 12; k++) { const a = (k / 12) * (Math.PI / 2); pts.push([Math.max(0.001, R * Math.sin(a)), R * (1 - Math.cos(a))]); }
  const n = rib ? 160 : 40;
  for (let k = 1; k <= n; k++) {
    const z = R + (k / n) * (L - R);
    // a gentle swell, two soft knuckles (finger), or knitted rows (glove)
    const j = joints * (0.06 * Math.exp(-(((z - 27) / 6) ** 2)) + 0.09 * Math.exp(-(((z - 64) / 9) ** 2)) - 0.03 * Math.exp(-(((z - 44) / 8) ** 2)));
    const r = 0.035 * rib * Math.abs(Math.sin((z * Math.PI) / 2.6));
    pts.push([R * (1 + swell * Math.sin(Math.min(1, (k / n) * 2.2) * Math.PI * 0.5) + j + r + taper * Math.min(1, z / 120)), z]);
  }
  const g = lathe(pts, 64); g.scale(1, flat, 1); g.computeVertexNormals(); return g;
}
const KNIT = ctex(256, 256, (g, w, h) => {
  g.fillStyle = '#6f6862'; g.fillRect(0, 0, w, h);
  for (let x = 0; x < w; x += 16) for (let y = 0; y < h; y += 12) {
    g.fillStyle = `rgba(255,255,255,${0.16 + 0.08 * rnd(x * 7 + y, 3)})`; g.beginPath(); g.ellipse(x + 4, y + 6, 3.6, 6, 0.35, 0, 7); g.fill();
    g.fillStyle = `rgba(255,255,255,${0.16 + 0.08 * rnd(x + y * 5, 4)})`; g.beginPath(); g.ellipse(x + 12, y + 6, 3.6, 6, -0.35, 0, 7); g.fill();
  }
}, [3, 10]);
const CERAMIC = () => new TH.MeshPhysicalMaterial({ color: C('#ece6de'), roughness: 0.5, clearcoat: 0.25, clearcoatRoughness: 0.4, envMap: STUDIO_ENV, envMapIntensity: 1.1 });
function buildToucher(kind) {
  const g = new TH.Group(); scene.add(g); g.visible = false;
  const inner = new TH.Group(); g.add(inner);
  let lift = 0;  // how far the touching surface sits from the tip origin (a nail tap touches with the nail, not the pad)
  if (kind === 'finger' || kind === 'nail') {
    const m = CERAMIC(), R = 8;
    mesh(tipGeo(R, 230, 0.84, 0.06, 1, 0, 0.16), m, inner);
    // the nail: a thin glossy plate on the back of the tip, curving with the finger
    const nail = new TH.CylinderGeometry(R * 0.86, R * 0.86, 13, 32, 1, true, -0.95, 1.9); nail.rotateX(Math.PI / 2); nail.rotateZ(Math.PI / 2); nail.translate(0, 0.35, 0);
    nail.scale(1, 1.02, 1);
    const nm = new TH.MeshPhysicalMaterial({ color: C('#e6dfd7'), roughness: 0.22, clearcoat: 0.9, clearcoatRoughness: 0.12, envMap: STUDIO_ENV, envMapIntensity: 0.9, side: TH.DoubleSide });
    const n = mesh(nail, nm, inner, 0, 0, kind === 'nail' ? 4.6 : 9.6); n.scale.y = 0.9;
    if (kind === 'nail') { mesh(nail.clone(), nm, inner, 0, 0, -1.5).scale.set(1, 0.9, 1); }
    return { g, inner, m, kind };
  }
  if (kind === 'glove') {
    const m = new TH.MeshPhysicalMaterial({ color: C('#ffffff'), map: KNIT, bumpMap: KNIT, bumpScale: 1.4, roughness: 1, sheen: 1, sheenRoughness: 0.6, sheenColor: C('#c9c0b6'), envMap: STUDIO_ENV, envMapIntensity: 0.5 });
    mesh(tipGeo(10.2, 230, 0.9, 0.14, 0, 1), m, inner);
    return { g, inner, m, kind };
  }
  if (kind === 'sausage') {
    const m = new TH.MeshPhysicalMaterial({ color: C('#a85a37'), roughness: 0.4, clearcoat: 0.55, clearcoatRoughness: 0.3, envMap: STUDIO_ENV, envMapIntensity: 0.6, sheen: 0.3 });
    const R = 6.4, L = 92, pts = [];
    for (let k = 0; k <= 12; k++) { const a = (k / 12) * (Math.PI / 2); pts.push([Math.max(0.001, R * Math.sin(a)), R * (1 - Math.cos(a))]); }
    for (let k = 1; k < 40; k++) pts.push([R, R + (k / 40) * (L - 2 * R)]);
    for (let k = 0; k <= 12; k++) { const a = (k / 12) * (Math.PI / 2); pts.push([Math.max(0.001, R * Math.cos(a)), L - R + R * Math.sin(a)]); }
    // faint casing wrinkles along the body
    for (const q of pts) if (q[1] > R && q[1] < L - R) q[0] *= 1 + 0.018 * Math.sin(q[1] * 0.83) + 0.012 * Math.sin(q[1] * 2.1 + 1);
    mesh(lathe(pts, 48), m, inner);
    // the casing gathered at the far end, closed by a flat crimped band
    mesh(cy(1.0, 2.6, 3.2, 20), m, inner, 0, 0, L - 0.6);
    mesh(cy(1.1, 1.1, 1.6, 20), pmat('#77716b', { r: 0.5, m: 1 }), inner, 0, 0, L + 2.4).scale.set(1.7, 0.42, 1);
    return { g, inner, m, kind };
  }
}
// put a toucher's tip at p (world), its body leaning back along dir (world, normalised), back of the finger up
const _Z = new TH.Vector3(0, 0, 1);
function placeToucher(Tc, p, dir) {
  const z = new TH.Vector3(...dir).normalize(), y = _Z.clone().addScaledVector(z, -z.dot(_Z)).normalize(), x = new TH.Vector3().crossVectors(y, z);
  Tc.g.quaternion.setFromRotationMatrix(new TH.Matrix4().makeBasis(x, y, z)); Tc.g.position.set(...p);
}
// a drop of water: a flattened clear dome
function buildDrop() {
  const geo = new TH.SphereGeometry(1, 48, 24, 0, Math.PI * 2, 0, Math.PI / 2); geo.rotateX(Math.PI / 2); geo.scale(5.2, 5.2, 2.6);
  const m = new TH.MeshPhysicalMaterial({ color: C('#f2f6f7'), roughness: 0.0, transmission: 0.55, thickness: 3, ior: 1.33, clearcoat: 1, clearcoatRoughness: 0.0, envMap: STUDIO_ENV, envMapIntensity: 3.2, transparent: true, opacity: 0.5, depthWrite: false });
  const d = new TH.Mesh(geo, m); d.renderOrder = 7; d.visible = false; scene.add(d); return { d, m };
}
// snow: slow soft flakes falling through a box around the rig (story)
function buildSnow(n, box) {
  const geo = new TH.BufferGeometry(), P = new Float32Array(n * 3), S = new Float32Array(n);
  for (let i = 0; i < n; i++) { P.set([box[0] + (rnd(i, 1) - 0.5) * box[3], box[1] + (rnd(i, 2) - 0.5) * box[4], box[2] + rnd(i, 3) * box[5]], i * 3); S[i] = 0.5 + rnd(i, 4); }
  geo.setAttribute('position', new TH.Float32BufferAttribute(P, 3)); geo.setAttribute('aS', new TH.Float32BufferAttribute(S, 1));
  const m = new TH.ShaderMaterial({
    uniforms: { uT: { value: 0 }, uA: { value: 0 }, uH: { value: box[5] }, uZ0: { value: box[2] } },
    vertexShader: 'attribute float aS; uniform float uT, uH, uZ0; varying float vS; void main() { vec3 p = position; p.z = uZ0 + mod(p.z - uZ0 - uT * (14.0 + 10.0 * aS), uH); p.x += sin(uT * 0.6 + aS * 9.0) * 4.0; vS = aS; vec4 mv = modelViewMatrix * vec4(p, 1.0); gl_Position = projectionMatrix * mv; gl_PointSize = (5.0 + 6.0 * aS) * 300.0 / -mv.z; }',
    fragmentShader: 'uniform float uA; varying float vS; void main() { float r = length(gl_PointCoord - 0.5) * 2.0; float a = smoothstep(1.0, 0.2, r) * uA * (0.35 + 0.4 * vS); if (a < 0.01) discard; gl_FragColor = vec4(vec3(0.92, 0.91, 0.9), a); }',
    transparent: true, depthWrite: false, toneMapped: false,
  });
  const pts = new TH.Points(geo, m); pts.frustumCulled = false; pts.renderOrder = 8; pts.visible = false; scene.add(pts); return { pts, m };
}

/* ------------------------------------------------------------------ the keypad screen */
// key centres as fractions of the screen (x right, y down) for the passcode keypad
const KEYS = { 1: [0.25, 0.5], 2: [0.5, 0.5], 3: [0.75, 0.5], 4: [0.25, 0.625], 5: [0.5, 0.625], 6: [0.75, 0.625], 7: [0.25, 0.75], 8: [0.5, 0.75], 9: [0.75, 0.75], 0: [0.5, 0.875] };
function keypad(g, W0, H0, o) {
  const k = W0 / 600; g.scale(k, k); const W = 600, H = H0 / k;
  const bg = g.createLinearGradient(0, 0, 0, H); bg.addColorStop(0, '#26221f'); bg.addColorStop(0.55, '#161412'); bg.addColorStop(1, '#0d0c0b'); g.fillStyle = bg; g.fillRect(0, 0, W, H);
  g.textAlign = 'center'; g.fillStyle = '#e9e6e3'; g.font = '500 34px Inter'; g.fillText('Enter Passcode', W / 2, H * 0.27);
  for (let i = 0; i < 6; i++) { const x = W / 2 + (i - 2.5) * 42, y = H * 0.32; g.beginPath(); g.arc(x, y, 9, 0, 7); if (i < o.n) { g.fillStyle = '#f4f3f2'; g.fill(); } else { g.strokeStyle = '#bdb7b1'; g.lineWidth = 2.2; g.stroke(); } }
  const sub = { 2: 'A B C', 3: 'D E F', 4: 'G H I', 5: 'J K L', 6: 'M N O', 7: 'P Q R S', 8: 'T U V', 9: 'W X Y Z' };
  for (const [key, [fx, fy]] of Object.entries(KEYS)) {
    const x = fx * W, y = fy * H, hi = o.hi?.[key] || 0;
    g.beginPath(); g.arc(x, y, 64, 0, 7); g.fillStyle = `rgba(${Math.round(70 + 185 * hi)},${Math.round(66 + 40 * hi)},${Math.round(63 - 30 * hi)},${0.55 + 0.4 * hi})`; g.fill();
    g.fillStyle = '#f4f3f2'; g.font = '400 58px Inter'; g.fillText(key, x, y + (sub[key] ? 8 : 20));
    if (sub[key]) { g.font = '600 15px Inter'; g.fillStyle = 'rgba(244,243,242,0.75)'; g.fillText(sub[key], x, y + 34); }
  }
  // touch ripples: [fx, fy, age 0..1]
  for (const [fx, fy, a] of o.rip || []) { if (a <= 0 || a >= 1) continue; g.beginPath(); g.arc(fx * W, fy * H, 20 + 90 * a, 0, 7); g.strokeStyle = `rgba(255,176,112,${0.75 * (1 - a)})`; g.lineWidth = 4; g.stroke(); }
  g.fillStyle = 'rgba(244,243,242,0.85)'; g.beginPath(); g.roundRect(W / 2 - 110, H - 40, 220, 9, 5); g.fill();
}
