// 37 QR code props, built from kit.js: a cafe menu card on a dark oak table with a real QR code (window.QR from
// qrgen.py: version 3-M, it scans to the channel) made of one printed cell per module so cells can lift, glow and
// fade, a coffee stain, a ceramic cup, the phone, and the story set (a Go board, a flyer, a magazine, a box).
// Units: about 10 per real cm. z up. The menu lies flat at z = 0 .. CARD_T.

const MOD = 2.0, QN = QR.n, CARD_W = 150, CARD_H = 212, CARD_T = 1.0;
const QR_Y = -50;                                   // the code's centre on the card (card-local y)
const INK = '#1c1a18', PAPER = '#cdc5b8';

/* ------------------------------------------------------------------ the table */
const OAK = ctex(1024, 1024, (g, w, h) => {
  g.fillStyle = '#1b1612'; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 260; i++) {
    const y = rnd(i, 1) * h, a = 0.025 + 0.05 * rnd(i, 2), lw = 0.6 + 3 * rnd(i, 3);
    g.strokeStyle = `rgba(${rnd(i, 4) > 0.5 ? '120,92,66' : '8,6,4'},${a})`; g.lineWidth = lw; g.beginPath();
    for (let x = 0; x <= w; x += 16) g.lineTo(x, y + 10 * Math.sin(x / 140 + i) + 4 * Math.sin(x / 37 + i * 3));
    g.stroke();
  }
}, [3, 3]);
const TABLE_M = new TH.MeshPhysicalMaterial({ map: OAK, color: C('#ffffff'), roughness: 0.55, clearcoat: 0.35, clearcoatRoughness: 0.35, envMap: STUDIO_ENV, envMapIntensity: 0.35 });

/* ------------------------------------------------------------------ the menu card */
// the printed menu (everything but the QR, which is 3D): paper fibre, type, a hairline frame, "Scan to order"
const MENU_TEX = ctex(1050, 1484, (g, w, h) => {
  const k = w / CARD_W, Y = (y) => (CARD_H / 2 - y) * k, X = (x) => (x + CARD_W / 2) * k;
  g.fillStyle = PAPER; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 9000; i++) { g.fillStyle = `rgba(${rnd(i, 5) > 0.5 ? '255,255,255' : '90,80,70'},${0.03 + 0.04 * rnd(i, 6)})`; g.fillRect(rnd(i, 7) * w, rnd(i, 8) * h, 1 + 2 * rnd(i, 9), 1); }
  g.strokeStyle = 'rgba(40,36,32,0.55)'; g.lineWidth = 1.4; g.strokeRect(X(-66), Y(97), 132 * k, 194 * k);
  g.fillStyle = INK; g.textAlign = 'center';
  g.font = `500 ${4.2 * k}px Mono`; g.fillText('E S T .   2 0 1 9', X(0), Y(83));
  g.font = `600 ${11 * k}px Inter`; g.fillText('Morning', X(0), Y(68));
  g.font = `500 ${3.4 * k}px Mono`; g.fillStyle = 'rgba(28,26,24,0.7)'; g.fillText('C O F F E E   ·   B A K E R Y', X(0), Y(60));
  const item = (y, a, p) => {
    g.textAlign = 'left'; g.fillStyle = INK; g.font = `500 ${4.6 * k}px Inter`; g.fillText(a, X(-52), Y(y));
    g.textAlign = 'right'; g.fillText(p, X(52), Y(y));
    g.fillStyle = 'rgba(28,26,24,0.35)'; const x0 = X(-52) + g.measureText(a).width + 0 * k;
    g.textAlign = 'left'; g.font = `500 ${4.6 * k}px Inter`; const aw = g.measureText(a).width, pw = g.measureText(p).width;
    for (let x = X(-52) + aw + 2 * k; x < X(52) - pw - 2 * k; x += 1.6 * k) g.fillRect(x, Y(y) - 0.4 * k, 0.45 * k, 0.45 * k);
  };
  g.textAlign = 'left'; g.font = `600 ${3.6 * k}px Mono`; g.fillStyle = 'rgba(28,26,24,0.75)'; g.fillText('COFFEE', X(-52), Y(46));
  item(38, 'Espresso', '2.80'); item(31, 'Flat white', '3.60'); item(24, 'Cortado', '3.40'); item(17, 'Filter', '3.00');
  g.textAlign = 'left'; g.font = `600 ${3.6 * k}px Mono`; g.fillStyle = 'rgba(28,26,24,0.75)'; g.fillText('BAKERY', X(-52), Y(5));
  item(-3, 'Croissant', '3.20'); item(-10, 'Banana bread', '3.50');
  g.textAlign = 'center'; g.fillStyle = 'rgba(28,26,24,0.8)'; g.font = `500 ${3.6 * k}px Mono`; g.fillText('S C A N   T O   O R D E R', X(0), Y(QR_Y - QN * MOD / 2 - 9));
});
function buildMenu(x, y, rz) {
  const g = grp(null, x, y, 0, rz);
  const paper = new TH.MeshPhysicalMaterial({ color: C('#d9d9d9'), map: MENU_TEX, roughness: 0.82, sheen: 0.4, sheenRoughness: 0.8, sheenColor: C('#ffffff'), envMap: STUDIO_ENV, envMapIntensity: 0.25 });
  const edge = pmat('#cfc7ba', { r: 0.85, env: 0.3 });
  const card = mesh(slab(CARD_W, CARD_H, CARD_T, 1.6, 0.25, 3), [edge, edge], g, 0, 0, CARD_T / 2);
  const top = mesh(rrg(CARD_W - 0.5, CARD_H - 0.5, 1.4), paper, g, 0, 0, CARD_T + 0.01, { cast: false });
  g.updateMatrixWorld(true);
  return { g, card, top, paper };
}

/* ------------------------------------------------------------------ the QR code, one cell per module */
// role per module: f finder, t timing, a alignment, m format, d data, e error correction (backup), r remainder
const QROLE = (i, j) => QR.role[j][i], QBIT = (i, j) => QR.bits[j][i] === '1';
function buildQR(par, z) {
  const g = grp(par, 0, QR_Y, z);
  const N = QN * QN, geo = new TH.BoxGeometry(MOD * 0.96, MOD * 0.96, 1); geo.translate(0, 0, 0.5);
  const m = new TH.MeshPhysicalMaterial({ color: C('#ffffff'), roughness: 0.62, clearcoat: 0.15, clearcoatRoughness: 0.6, envMap: STUDIO_ENV, envMapIntensity: 0.3 });
  const cells = new TH.InstancedMesh(geo, m, N); cells.castShadow = true; cells.receiveShadow = true; cells.frustumCulled = false; g.add(cells);
  const loc = (i, j) => [(i - (QN - 1) / 2) * MOD, ((QN - 1) / 2 - j) * MOD];
  const M4 = new TH.Matrix4(), Q = new TH.Quaternion(), V = new TH.Vector3(), Sv = new TH.Vector3(), col = new TH.Color();
  // per cell: h (height), up (lift above the paper), k (0 = gone, 1 = full), c (colour hex or Color), s (xy scale)
  const st = []; for (let j = 0; j < QN; j++) for (let i = 0; i < QN; i++) st.push({ i, j, dark: QBIT(i, j), role: QROLE(i, j) });
  function set(fn) {
    for (let n = 0; n < N; n++) {
      const c = st[n], o = fn(c); const [x, y] = loc(c.i, c.j);
      const s = (o.s ?? 1) * (o.k ?? 1), h = Math.max(0.001, o.h ?? 0.06);
      V.set(x, y, o.up ?? 0); Sv.set(Math.max(0.001, s), Math.max(0.001, s), h); M4.compose(V, Q, Sv); cells.setMatrixAt(n, M4);
      col.set(o.c ?? (c.dark ? INK : PAPER)); cells.setColorAt(n, col);
    }
    cells.instanceMatrix.needsUpdate = true; cells.instanceColor.needsUpdate = true;
  }
  return { g, cells, m, loc, set, st };
}

/* ------------------------------------------------------------------ the coffee stain (a soft ring and wash) */
function stainTex(seed, dark) {
  return ctex(512, 512, (g, w, h) => {
    g.clearRect(0, 0, w, h);
    const blob = (r0, a, wob, lw) => {
      g.beginPath();
      for (let k = 0; k <= 96; k++) { const t = (k / 96) * Math.PI * 2, r = r0 * (1 + wob * (0.5 * Math.sin(3 * t + seed) + 0.3 * Math.sin(7 * t + seed * 2) + 0.2 * Math.sin(13 * t + seed * 3))); g.lineTo(w / 2 + r * Math.cos(t), h / 2 + r * Math.sin(t)); }
      g.closePath(); return g;
    };
    const gr = g.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w * 0.45);
    gr.addColorStop(0, `rgba(92,58,32,${dark ? 0.92 : 0.38})`); gr.addColorStop(0.8, `rgba(110,70,38,${dark ? 0.9 : 0.42})`); gr.addColorStop(1, 'rgba(110,70,38,0)');
    g.filter = 'blur(5px)'; blob(w * 0.4, 1, 0.08); g.fillStyle = gr; g.fill();
    // soaked-in mottling: a few faint darker patches inside, like coffee drying into paper fibres
    for (let k = 0; k < 9; k++) { const a = rnd(k, seed) * 7, d = w * 0.22 * rnd(k + 9, seed), rr = w * (0.05 + 0.08 * rnd(k + 3, seed));
      g.beginPath(); g.arc(w / 2 + d * Math.cos(a), h / 2 + d * Math.sin(a), rr, 0, 7); g.fillStyle = `rgba(70,40,20,${dark ? 0.18 : 0.08})`; g.fill(); }
    g.filter = 'blur(2.5px)'; blob(w * 0.405, 1, 0.08); g.strokeStyle = `rgba(74,44,22,${dark ? 0.55 : 0.4})`; g.lineWidth = 4; g.stroke(); g.filter = 'none';
  });
}
function buildStain(par, x, y, z, r, seed, dark = false) {
  const m = new TH.MeshStandardMaterial({ map: stainTex(seed, dark), transparent: true, opacity: 0, depthWrite: false, roughness: 0.4, polygonOffset: true, polygonOffsetFactor: -4 });
  const me = mesh(new TH.PlaneGeometry(1, 1), m, par, x, y, z, { cast: false }); me.scale.set(r * 2, r * 2, 1); me.renderOrder = 3;
  return { me, m, r };
}

/* ------------------------------------------------------------------ a ceramic cup and saucer */
function buildCup(x, y) {
  const g = grp(null, x, y, 0), glaze = pmat('#e6e1da', { r: 0.18, cc: 0.8, ccr: 0.1, env: 0.9 });
  const sau = []; for (let k = 0; k <= 16; k++) { const u = k / 16; sau.push([Math.max(0.01, 70 * u), 1.2 + 4.2 * Math.pow(u, 3) + (u > 0.95 ? -1 : 0)]); }
  sau.push([68, 6.4], [62, 6], [26, 2.4], [0.01, 2.4]);
  mesh(lathe(sau, 96), glaze, g);
  const cup = []; for (let k = 0; k <= 20; k++) { const u = k / 20; cup.push([Math.max(0.01, 26 + 18 * Math.sin(u * Math.PI * 0.55)), 3 + 60 * u]); }
  cup.push([41.6, 63.3], [39, 62], [24, 20], [0.01, 18]);
  mesh(lathe(cup, 96), glaze, g);
  mesh(new TH.CircleGeometry(39.5, 64), pmat('#2a170c', { r: 0.12, cc: 1, ccr: 0.05, env: 0.6 }), g, 0, 0, 55);
  const hd = new TH.TorusGeometry(12, 3.6, 16, 48, Math.PI * 1.25); hd.rotateX(Math.PI / 2); hd.rotateY(-Math.PI * 0.12);
  mesh(hd, glaze, g, 40, 0, 36);
  return g;
}

/* ------------------------------------------------------------------ story: a Go board and a few printed things */
const GO_TEX = ctex(1024, 1024, (g, w, h) => {
  g.fillStyle = '#7f6c55'; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 160; i++) { const y = rnd(i, 11) * h; g.strokeStyle = `rgba(${rnd(i, 12) > 0.5 ? '200,170,120' : '110,80,48'},${0.05 + 0.08 * rnd(i, 13)})`; g.lineWidth = 1 + 4 * rnd(i, 14); g.beginPath(); for (let x = 0; x <= w; x += 20) g.lineTo(x, y + 6 * Math.sin(x / 90 + i)); g.stroke(); }
  const m = 70, s = (w - 2 * m) / 18; g.strokeStyle = 'rgba(30,22,14,0.85)'; g.lineWidth = 2.2;
  for (let k = 0; k < 19; k++) { g.beginPath(); g.moveTo(m, m + k * s); g.lineTo(w - m, m + k * s); g.stroke(); g.beginPath(); g.moveTo(m + k * s, m); g.lineTo(m + k * s, h - m); g.stroke(); }
  g.fillStyle = 'rgba(30,22,14,0.9)'; for (const a of [3, 9, 15]) for (const b of [3, 9, 15]) { g.beginPath(); g.arc(m + a * s, m + b * s, 6, 0, 7); g.fill(); }
});
const GO_STONES = [[3, 3, 1], [4, 3, 0], [15, 3, 0], [15, 4, 1], [16, 5, 1], [3, 15, 0], [4, 16, 1], [2, 13, 1], [9, 9, 1], [10, 9, 0], [10, 10, 1], [8, 10, 0], [13, 15, 0], [14, 14, 1], [16, 14, 0], [6, 2, 1], [5, 5, 0], [12, 3, 1], [11, 4, 0], [15, 10, 1], [16, 11, 0], [3, 9, 0], [4, 10, 1]];
function buildGo(x, y) {
  const g = grp(null, x, y, 0), W = 130, H = 14;
  mesh(slab(W, W, H, 2, 1.2, 4), pmat('#6f5d48', { r: 0.5, cc: 0.3, env: 0.5 }), g, 0, 0, H / 2);
  mesh(new TH.PlaneGeometry(W - 2.4, W - 2.4), new TH.MeshPhysicalMaterial({ map: GO_TEX, color: C('#ffffff'), roughness: 0.45, clearcoat: 0.4, clearcoatRoughness: 0.3, envMap: STUDIO_ENV, envMapIntensity: 0.5 }), g, 0, 0, H + 0.02, { cast: false });
  const sg = new TH.SphereGeometry(3.05, 32, 16); sg.scale(1, 1, 0.42);
  const bk = pmat('#121212', { r: 0.18, cc: 1, ccr: 0.15, env: 0.9 }), wh = pmat('#ece8e1', { r: 0.25, cc: 1, ccr: 0.15, env: 0.9 });
  const m = W * (70 / 1024), s = (W - 2 * m) / 18, stones = [];
  for (const [a, b, c] of GO_STONES) stones.push(mesh(sg, c ? bk : wh, g, -W / 2 + m + a * s, W / 2 - m - b * s, H + 1.2));
  return { g, stones, cell: s, m, W, H };
}
// a printed sheet with a texture painted by fn (flyer, magazine page, the side of a box)
function printed(par, x, y, z, w, h, rz, fn, o = {}) {
  const t = ctex(Math.round(w * 6), Math.round(h * 6), fn);
  const m = new TH.MeshPhysicalMaterial({ map: t, color: C('#ffffff'), roughness: o.r ?? 0.7, clearcoat: o.cc ?? 0, clearcoatRoughness: 0.3, envMap: STUDIO_ENV, envMapIntensity: 0.35 });
  const g = grp(par, x, y, z, rz);
  mesh(slab(w, h, o.t ?? 0.5, 0.6, 0.15, 2), pmat(o.edge ?? '#d7d0c4', { r: 0.8, env: 0.3 }), g, 0, 0, (o.t ?? 0.5) / 2);
  mesh(new TH.PlaneGeometry(w - 0.3, h - 0.3), m, g, 0, 0, (o.t ?? 0.5) + 0.02, { cast: false });
  return g;
}
const FLYER = (g, w, h) => {
  g.fillStyle = '#d8d1c4'; g.fillRect(0, 0, w, h); g.fillStyle = '#1c1a18';
  g.font = `700 ${w * 0.14}px Inter`; g.fillText('SALE', w * 0.08, h * 0.2); g.font = `600 ${w * 0.06}px Inter`; g.fillText('This weekend only', w * 0.08, h * 0.28);
  g.fillStyle = '#3a3633'; g.fillRect(w * 0.08, h * 0.34, w * 0.84, h * 0.36);
  for (let k = 0; k < 6; k++) { g.fillStyle = 'rgba(28,26,24,0.7)'; g.fillRect(w * 0.08, h * (0.76 + k * 0.035), w * (0.5 + 0.34 * rnd(k, 20)), h * 0.012); }
};
const MAG = (g, w, h) => {
  g.fillStyle = '#d6cfc3'; g.fillRect(0, 0, w, h);
  g.fillStyle = '#2b2826'; g.fillRect(w * 0.07, h * 0.06, w * 0.86, h * 0.42);
  g.fillStyle = '#1c1a18'; g.font = `700 ${w * 0.075}px Inter`; g.fillText('The quiet', w * 0.07, h * 0.56); g.fillText('revolution', w * 0.07, h * 0.62);
  for (let c = 0; c < 2; c++) for (let k = 0; k < 14; k++) { g.fillStyle = 'rgba(28,26,24,0.55)'; g.fillRect(w * (0.07 + c * 0.45), h * (0.67 + k * 0.022), w * (0.36 + 0.05 * rnd(k + c * 20, 21)), h * 0.008); }
};
const BOX = (g, w, h) => {
  g.fillStyle = '#8f7558'; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 4000; i++) { g.fillStyle = `rgba(${rnd(i, 22) > 0.5 ? '160,130,96' : '90,70,50'},0.15)`; g.fillRect(rnd(i, 23) * w, rnd(i, 24) * h, 2, 1); }
  g.strokeStyle = 'rgba(30,24,18,0.85)'; g.lineWidth = w * 0.012; g.strokeRect(w * 0.1, h * 0.12, w * 0.8, h * 0.3);
  g.fillStyle = 'rgba(30,24,18,0.9)'; g.font = `700 ${w * 0.1}px Inter`; g.fillText('FRAGILE', w * 0.17, h * 0.32);
  for (let k = 0; k < 18; k++) g.fillRect(w * (0.1 + k * 0.045), h * 0.6, w * (k % 3 ? 0.012 : 0.028), h * 0.22);
  g.font = `600 ${w * 0.045}px Mono`; g.fillText('THIS SIDE UP  ↑↑', w * 0.1, h * 0.92);
};

/* ------------------------------------------------------------------ thin lines and points over the code */
const lineM = (c, op = 0) => new TH.MeshBasicMaterial({ color: C(c), transparent: true, opacity: op, depthWrite: false, toneMapped: false });
function buildSampler(Q, z) {
  // a fine sampling grid that sits on the code, and one point at every module centre
  const g = grp(Q.g, 0, 0, z), L = QN * MOD, lm = lineM(O), rows = [], cols = [];
  for (let k = 0; k <= QN; k++) {
    const p = (k - QN / 2) * MOD;
    const r = mesh(new TH.PlaneGeometry(L, 0.16), lm, g, 0, p, 0, { cast: false }); r.renderOrder = 6; rows.push(r);
    const c = mesh(new TH.PlaneGeometry(0.16, L), lm, g, p, 0, 0, { cast: false }); c.renderOrder = 6; cols.push(c);
  }
  const N = QN * QN, P = new Float32Array(N * 3), A = new Float32Array(N);
  for (let j = 0; j < QN; j++) for (let i = 0; i < QN; i++) { const [x, y] = Q.loc(i, j); P.set([x, y, 0.3], (j * QN + i) * 3); }
  const geo = new TH.BufferGeometry(); geo.setAttribute('position', new TH.Float32BufferAttribute(P, 3)); geo.setAttribute('aI', new TH.Float32BufferAttribute(A, 1));
  const pm = new TH.ShaderMaterial({
    uniforms: { uSize: { value: 7 }, uCol: { value: C(O) } },
    vertexShader: 'attribute float aI; uniform float uSize; varying float vI; void main() { vI = aI; vec4 mv = modelViewMatrix * vec4(position, 1.0); gl_Position = projectionMatrix * mv; gl_PointSize = uSize; }',
    fragmentShader: 'uniform vec3 uCol; varying float vI; void main() { float r = length(gl_PointCoord - 0.5) * 2.0; float a = smoothstep(1.0, 0.55, r) * vI; if (a < 0.01) discard; gl_FragColor = vec4(uCol, a); }',
    transparent: true, depthWrite: false, depthTest: false, toneMapped: false,
  });
  const pts = new TH.Points(geo, pm); pts.renderOrder = 8; pts.frustumCulled = false; g.add(pts);
  return { g, lm, pm, setDots(fn) { const a = geo.attributes.aI; for (let j = 0; j < QN; j++) for (let i = 0; i < QN; i++) a.setX(j * QN + i, fn(i, j)); a.needsUpdate = true; } };
}
// a scan line: a thin glowing bar with a soft halo, drawn on top
function buildScan(par, len) {
  const g = grp(par, 0, 0, 0);
  const core = mesh(new TH.PlaneGeometry(len, 0.35), lineM(O), g, 0, 0, 0, { cast: false }); core.renderOrder = 9; core.material.depthTest = false;
  const halo = mesh(new TH.PlaneGeometry(len, 4), new TH.MeshBasicMaterial({ color: C(O), transparent: true, opacity: 0, depthWrite: false, depthTest: false, toneMapped: false, blending: TH.AdditiveBlending, map: (() => { const c = document.createElement('canvas'); c.width = 4; c.height = 64; const x = c.getContext('2d'); const gr = x.createLinearGradient(0, 0, 0, 64); gr.addColorStop(0, 'rgba(255,255,255,0)'); gr.addColorStop(0.5, 'rgba(255,255,255,1)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); x.fillStyle = gr; x.fillRect(0, 0, 4, 64); return new TH.CanvasTexture(c); })() }), g, 0, 0, 0, { cast: false }); halo.renderOrder = 9;
  return { g, set(a) { g.visible = a > 0.01; core.material.opacity = 0.95 * a; halo.material.opacity = 0.35 * a; } };
}

/* ------------------------------------------------------------------ the phone's camera screen */
// paper, the code (drawn straight), corner brackets that close in and turn orange, then the link banner
function viewfinder(g, W, H, o) {
  const gr = g.createLinearGradient(0, 0, 0, H); gr.addColorStop(0, '#2d2a27'); gr.addColorStop(1, '#171514'); g.fillStyle = gr; g.fillRect(0, 0, W, H);
  const cx = W / 2, cy = H * 0.52, S = W * 0.62, m = S / (QN + 8);
  g.fillStyle = '#bdb6aa'; g.fillRect(cx - S / 2 - W * 0.3, cy - S / 2 - W * 0.25, S + W * 0.6, S + W * 0.7);
  g.fillStyle = '#2a2826'; for (let j = 0; j < QN; j++) for (let i = 0; i < QN; i++) if (QBIT(i, j)) g.fillRect(cx - S / 2 + (i + 4) * m, cy - S / 2 + (j + 4) * m, m + 0.5, m + 0.5);
  if (o.stain) { const sg = g.createRadialGradient(cx + S * 0.08, cy + S * 0.1, 0, cx + S * 0.08, cy + S * 0.1, S * 0.22); sg.addColorStop(0, 'rgba(110,70,38,0.55)'); sg.addColorStop(1, 'rgba(110,70,38,0)'); g.fillStyle = sg; g.fillRect(0, 0, W, H); }
  const lk = o.lock ?? 0, br = S * (0.62 - 0.1 * lk), L = W * 0.07;
  g.strokeStyle = lk > 0.5 ? '#ff6a1f' : 'rgba(255,255,255,0.9)'; g.lineWidth = W * 0.012; g.lineCap = 'round';
  for (const [sx, sy] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) { g.beginPath(); g.moveTo(cx + sx * br, cy + sy * br - sy * L); g.lineTo(cx + sx * br, cy + sy * br); g.lineTo(cx + sx * br - sx * L, cy + sy * br); g.stroke(); }
  if (o.link > 0.01) {
    g.globalAlpha = o.link; const bw = W * 0.8, bh = W * 0.16, bx = cx - bw / 2, by = H * 0.13;
    g.fillStyle = 'rgba(30,28,27,0.92)'; g.beginPath(); g.roundRect(bx, by, bw, bh, bh / 2); g.fill();
    g.fillStyle = '#ff6a1f'; g.beginPath(); g.arc(bx + bh * 0.55, by + bh / 2, bh * 0.22, 0, 7); g.fill();
    g.fillStyle = '#f2f0ee'; g.font = `600 ${W * 0.045}px Inter`; g.textAlign = 'left'; g.fillText('instagram.com', bx + bh * 1.0, by + bh * 0.46);
    g.fillStyle = '#a49d97'; g.font = `500 ${W * 0.034}px Inter`; g.fillText('Open in Safari', bx + bh * 1.0, by + bh * 0.78);
    g.globalAlpha = 1;
  }
  g.fillStyle = 'rgba(255,255,255,0.85)'; g.beginPath(); g.arc(cx, H * 0.9, W * 0.07, 0, 7); g.fill();
}
