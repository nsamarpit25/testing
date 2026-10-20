// Shared 3D canvas engine for the 10 opening variants (lifted from 09-kubernetes). Needs tools/lib.js.
const $ = (id) => document.getElementById(id);
const hex = (h) => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
const rgba = (c, k = 1, a = 1) => `rgba(${Math.min(255, c[0] * k) | 0},${Math.min(255, c[1] * k) | 0},${Math.min(255, c[2] * k) | 0},${a})`;
const mixc = (a, b, t) => [lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)];
const HX = { cy: '#22D3EE', vi: '#A78BFA', or: '#FF8A3D', gr: '#4ADE80', rd: '#FF3B5C', ye: '#FACC15', pk: '#F472B6', bl: '#4F8CFF', sl: '#8A9BC4' };
const K = {}; for (const k in HX) K[k] = hex(HX[k]);
const SLATE = hex('#252D4F'), DARK = hex('#161C36'), STEEL = hex('#39446E'), ICE = [196, 236, 255];
// deterministic random
const rnd = (i, s = 1) => { const x = Math.sin(i * 127.1 + s * 311.7) * 43758.5453; return x - Math.floor(x); };
const cv = $('cv'), g = cv.getContext('2d');
const cam = { f: [0, 0, 0], s: 1, a: 0.9, e: 0.62, sx: 270, sy: 500 };
let ca, sa, ce, se, toCam;
function camApply() { ca = Math.cos(cam.a); sa = Math.sin(cam.a); ce = Math.cos(cam.e); se = Math.sin(cam.e); toCam = [-sa * ce, -ca * ce, se]; }
function P(x, y, z) {
  const dx = x - cam.f[0], dy = y - cam.f[1], dz = z - cam.f[2];
  const r = dx * ca - dy * sa, f = dx * sa + dy * ca;
  return [cam.sx + r * cam.s, cam.sy - (dz * ce + f * se) * cam.s];
}
const D = (x, y, z) => (x * sa + y * ca) * ce - z * se;
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
  cam.f = cur.f; cam.s = cur.s * (1 + kick); cam.a = cur.a + 0.035 * Math.sin(t * 0.21); cam.e = cur.e; cam.sx = 270 + shx; cam.sy = cur.sy + shy;
  camApply();
  return { shx, shy };
}
/* ------------------------------------------------------------------ draw list */
let DL = [];
const add = (layer, depth, fn) => DL.push({ layer, depth, fn });
function flush() { DL.sort((a, b) => a.layer - b.layer || b.depth - a.depth); for (const d of DL) d.fn(); DL = []; }
const LIGHT = (() => { const l = [-0.35, -0.6, 1]; const n = Math.hypot(...l); return l.map((v) => v / n); })();
function poly(pts, fill, stroke, lw = 1) {
  g.beginPath(); pts.forEach((p, i) => (i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1]))); g.closePath();
  if (fill) { g.fillStyle = fill; g.fill(); }
  if (stroke) { g.strokeStyle = stroke; g.lineWidth = lw; g.stroke(); }
}
function glow(col, blur) { g.shadowColor = col; g.shadowBlur = blur * 2; }
function noGlow() { g.shadowBlur = 0; g.shadowColor = 'transparent'; }

// face frame helpers (u right, v up, units = world)
const fpt = (F, u, v) => P(F.o[0] + F.u[0] * u + F.v[0] * v, F.o[1] + F.u[1] * u + F.v[1] * v, F.o[2] + F.u[2] * u + F.v[2] * v);
function fquad(F, u0, v0, u1, v1, fill, gl) {
  if (gl) glow(gl[0], gl[1]);
  poly([fpt(F, u0, v0), fpt(F, u1, v0), fpt(F, u1, v1), fpt(F, u0, v1)], fill);
  if (gl) noGlow();
}
function ftext(F, u, v, str, size, fill, font = 'Mono', weight = 700, align = 'center', gl) {
  const p0 = fpt(F, u, v), pu = fpt(F, u + 1, v), pv = fpt(F, u, v + 1);
  g.save();
  g.setTransform(2 * (pu[0] - p0[0]), 2 * (pu[1] - p0[1]), -2 * (pv[0] - p0[0]), -2 * (pv[1] - p0[1]), 2 * p0[0], 2 * p0[1]);
  g.font = `${weight} ${size}px ${font}`; g.textAlign = align; g.textBaseline = 'middle'; g.fillStyle = fill;
  if (gl) { g.shadowColor = gl; g.shadowBlur = 14; }
  g.fillText(str, 0, 0);
  g.restore();
}
function fpath(F, pts, col, lw, gl) {
  g.save(); if (gl) glow(gl, 8);
  g.strokeStyle = col; g.lineWidth = lw * cam.s; g.lineCap = 'round'; g.lineJoin = 'round';
  g.beginPath(); pts.forEach(([u, v], i) => { const p = fpt(F, u, v); i ? g.lineTo(...p) : g.moveTo(...p); }); g.stroke();
  noGlow(); g.restore();
}
// box: x,y centre, z bottom. o: {layer, op, edge, lw, gl:[col,blur], front(F), side(F), top(F), dz}
function box(x, y, z, w, d, h, col, o = {}) {
  add(o.layer ?? 1, D(x, y, z + h / 2) + (o.dz || 0), () => drawBox(x, y, z, w, d, h, col, o));
}
function drawBox(x, y, z, w, d, h, col, o) {
  const x0 = x - w / 2, x1 = x + w / 2, y0 = y - d / 2, y1 = y + d / 2, z1 = z + h;
  const faces = [
    { n: [0, -1, 0], p: [[x0, y0, z], [x1, y0, z], [x1, y0, z1], [x0, y0, z1]], F: { o: [x0, y0, z], u: [1, 0, 0], v: [0, 0, 1] }, cb: o.front, nm: 'front' },
    { n: [0, 1, 0], p: [[x1, y1, z], [x0, y1, z], [x0, y1, z1], [x1, y1, z1]] },
    { n: [-1, 0, 0], p: [[x0, y1, z], [x0, y0, z], [x0, y0, z1], [x0, y1, z1]], F: { o: [x0, y1, z], u: [0, -1, 0], v: [0, 0, 1] }, cb: o.side, nm: 'side' },
    { n: [1, 0, 0], p: [[x1, y0, z], [x1, y1, z], [x1, y1, z1], [x1, y0, z1]] },
    { n: [0, 0, 1], p: [[x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], F: { o: [x0, y0, z1], u: [1, 0, 0], v: [0, 1, 0] }, cb: o.top, nm: 'top' },
  ];
  const op = o.op ?? 1;
  if (op <= 0.002) return;
  g.globalAlpha = op;
  if (o.gl) glow(o.gl[0], o.gl[1]);
  for (const f of faces) {
    const vis = f.n[0] * toCam[0] + f.n[1] * toCam[1] + f.n[2] * toCam[2];
    if (vis <= 0) continue;
    const lam = Math.max(0, f.n[0] * LIGHT[0] + f.n[1] * LIGHT[1] + f.n[2] * LIGHT[2]);
    const k = 0.42 + 0.72 * lam;
    const pts = f.p.map((q) => P(...q));
    poly(pts, rgba(col, k, 1));
    if (o.edge) { g.save(); noGlow(); poly(pts, null, o.edge, o.lw || 0.8); g.restore(); if (o.gl) glow(o.gl[0], o.gl[1]); }
  }
  noGlow();
  for (const f of faces) {
    if (!f.cb) continue;
    const vis = f.n[0] * toCam[0] + f.n[1] * toCam[1] + f.n[2] * toCam[2];
    if (vis > 0) f.cb(f.F, f.nm === 'front' ? w : f.nm === 'side' ? d : w, f.nm === 'top' ? d : h);
  }
  g.globalAlpha = 1;
}
function ell(c, rx, ry, fill, stroke, lw = 1) {
  g.beginPath(); g.ellipse(c[0], c[1], Math.max(0.1, rx), Math.max(0.1, ry), 0, 0, Math.PI * 2);
  if (fill) { g.fillStyle = fill; g.fill(); }
  if (stroke) { g.strokeStyle = stroke; g.lineWidth = lw; g.stroke(); }
}
// floor light pool
function pool(x, y, r, col, a) {
  if (a <= 0.003) return;
  add(0, 1e6 - 1, () => {
    const c = P(x, y, 0);
    g.save(); g.translate(c[0], c[1]); g.scale(1, se); g.globalCompositeOperation = 'lighter';
    const R = r * cam.s, gr = g.createRadialGradient(0, 0, 0, 0, 0, R);
    gr.addColorStop(0, rgba(col, 1, 0.5 * a)); gr.addColorStop(0.4, rgba(col, 1, 0.16 * a)); gr.addColorStop(1, rgba(col, 1, 0));
    g.fillStyle = gr; g.beginPath(); g.arc(0, 0, R, 0, Math.PI * 2); g.fill(); g.restore();
  });
}
function ripple(t, t0, x, y, z, col, maxR, dur, lw = 2) {
  const p = prog(t, t0, t0 + dur); if (p <= 0 || p >= 1) return;
  add(0, 1e6 - 2, () => {
    const c = P(x, y, z), r = (12 + maxR * ease.out(p)) * cam.s;
    g.save(); g.globalCompositeOperation = 'lighter'; glow(rgba(col), 10);
    ell(c, r, r * se, null, rgba(col, 1, (1 - p) * 0.9), lw * (1 - p * 0.5)); g.restore();
  });
}
function sparks(t, t0, x, y, z, col, n, seed, spd = 160, life = 0.7, size = 2.4, grav = 260) {
  const dt = t - t0; if (dt <= 0 || dt > life) return;
  add(3, 0, () => {
    g.save(); g.globalCompositeOperation = 'lighter';
    for (let i = 0; i < n; i++) {
      const th = rnd(i, seed) * Math.PI * 2, up = 0.3 + rnd(i, seed + 1) * 0.9, v = spd * (0.4 + rnd(i, seed + 2) * 0.8);
      const px = x + Math.cos(th) * v * dt, py = y + Math.sin(th) * v * dt, pz = z + up * v * dt - grav * dt * dt;
      const q = P(px, py, Math.max(0, pz)), k = 1 - dt / life;
      g.fillStyle = rgba(col, 1.2, k); const s = size * (0.5 + k * 0.7) * Math.min(1.4, cam.s + 0.3);
      g.fillRect(q[0] - s / 2, q[1] - s / 2, s, s);
    }
    g.restore();
  });
}
// dashed wireframe box (blueprints, empty slots)
function wireBox(x, y, z, w, d, h, col, a, layer = 2, dash = [4, 3]) {
  if (a <= 0.01) return;
  add(layer, D(x, y, z + h / 2), () => {
    const X = [x - w / 2, x + w / 2], Y = [y - d / 2, y + d / 2], Z = [z, z + h];
    const c = (i, j, k) => P(X[i], Y[j], Z[k]);
    const E = [[[0, 0, 0], [1, 0, 0]], [[0, 1, 0], [1, 1, 0]], [[0, 0, 1], [1, 0, 1]], [[0, 1, 1], [1, 1, 1]], [[0, 0, 0], [0, 1, 0]], [[1, 0, 0], [1, 1, 0]], [[0, 0, 1], [0, 1, 1]], [[1, 0, 1], [1, 1, 1]], [[0, 0, 0], [0, 0, 1]], [[1, 0, 0], [1, 0, 1]], [[0, 1, 0], [0, 1, 1]], [[1, 1, 0], [1, 1, 1]]];
    g.save(); g.setLineDash(dash.map((v) => v * Math.max(0.6, cam.s))); g.lineDashOffset = -performance.now() * 0; glow(rgba(col), 8);
    g.strokeStyle = rgba(col, 1.1, a); g.lineWidth = 1.4;
    g.beginPath(); for (const [p0, p1] of E) { g.moveTo(...c(...p0)); g.lineTo(...c(...p1)); } g.stroke();
    g.setLineDash([]); noGlow(); g.restore();
  });
}
function person(x, y, col, lit, o = {}) {
  const op = o.op ?? 1;
  if (op <= 0.01) return;
  add(1, D(x, y, 14), () => {
    g.globalAlpha = op;
    const b = P(x, y, 0), s = cam.s, hz = 30 + (o.jump || 0);
    const tp = P(x, y, 21 + (o.jump || 0)), h = P(x, y, hz);
    ell(b, 9 * s, 9 * s * se, 'rgba(0,0,0,0.35)');
    if (lit > 0.05) glow(rgba(col, 1, lit), 12);
    const bw = 13 * s, gr = g.createLinearGradient(b[0] - bw / 2, 0, b[0] + bw / 2, 0);
    gr.addColorStop(0, rgba(col, 0.55)); gr.addColorStop(0.6, rgba(col, 0.95)); gr.addColorStop(1, rgba(col, 0.7));
    g.fillStyle = gr; g.beginPath(); g.roundRect(b[0] - bw / 2, tp[1], bw, b[1] - tp[1] + 1, [bw / 2, bw / 2, 3 * s, 3 * s]); g.fill();
    const hg = g.createRadialGradient(h[0] - 2 * s, h[1] - 2 * s, 0, h[0], h[1], 6.5 * s);
    hg.addColorStop(0, rgba(col, 1.35)); hg.addColorStop(1, rgba(col, 0.75));
    g.fillStyle = hg; g.beginPath(); g.arc(h[0], h[1], 6.3 * s, 0, Math.PI * 2); g.fill();
    // hood slit
    g.fillStyle = 'rgba(5,8,22,0.85)'; g.fillRect(h[0] - 3.6 * s, h[1] - 0.6 * s, 7.2 * s, 2.2 * s);
    noGlow(); g.globalAlpha = 1;
  });
}
// labelled cube (app code, environment tiles)
function cube(x, y, z, sz, col, o = {}) {
  const base = o.base || hex('#1E2654');
  box(x, y, z, sz, sz, sz, mixc(base, col, o.fill ?? 0.25), { layer: o.layer ?? 1, op: o.op, edge: rgba(col, 1.2, 0.95), lw: 1.3, gl: [rgba(col, 1, 0.9 * (o.op ?? 1)), o.blur ?? 12], dz: o.dz ?? -4,
    front: o.label ? (F, w, h) => ftext(F, w / 2, h / 2, o.label, o.lsz || sz * 0.26, rgba(col, 1.45), 'Mono', 800) : null,
    top: o.code ? (F, w, d) => { for (let i = 0; i < 3; i++) fquad(F, w * 0.18, d * (0.72 - i * 0.22), w * (0.18 + [0.6, 0.4, 0.7][i]), d * (0.62 - i * 0.22), rgba([K.pk, K.cy, K.ye][i], 1, 0.95)); } : null });
}
function orb(p, col, a = 1, r = 5) {
  if (a <= 0.01) return;
  add(1, D(...p) - 6, () => {
    const c = P(...p), R = r * cam.s;
    g.save(); g.globalCompositeOperation = 'lighter';
    const rg = g.createRadialGradient(c[0], c[1], 0, c[0], c[1], R * 2.4);
    rg.addColorStop(0, rgba(col, 1.4, a)); rg.addColorStop(0.35, rgba(col, 1, 0.6 * a)); rg.addColorStop(1, rgba(col, 1, 0));
    g.fillStyle = rg; g.beginPath(); g.arc(c[0], c[1], R * 2.4, 0, Math.PI * 2); g.fill();
    g.fillStyle = `rgba(255,255,255,${a})`; g.beginPath(); g.arc(c[0], c[1], R * 0.55, 0, Math.PI * 2); g.fill();
    g.restore();
  });
}
// glowing floor road with flowing dashes
function roadLine(pts, col, a) {
  if (a <= 0.01 || pts.length < 2) return;
  add(0, 1e6 - 3, () => {
    const q = pts.map((p) => P(p[0], p[1], 0.5));
    const path = () => { g.beginPath(); q.forEach((p, i) => (i ? g.lineTo(...p) : g.moveTo(...p))); g.stroke(); };
    g.save(); g.globalCompositeOperation = 'lighter'; g.lineCap = 'round'; g.lineJoin = 'round';
    g.strokeStyle = rgba(col, 1, 0.16 * a); g.lineWidth = 7 * cam.s; path();
    g.strokeStyle = rgba(col, 1, 0.5 * a); g.lineWidth = 1.3 * cam.s; path();
    g.setLineDash([4 * cam.s, 10 * cam.s]); g.lineDashOffset = -t_ * 36 * cam.s; g.strokeStyle = rgba(col, 1.3, 0.8 * a); g.lineWidth = 2 * cam.s; path();
    g.restore();
  });
}
let t_ = 0;

/* ------------------------------------------------------------------ paths */
const lerp3 = (a, b, q) => [lerp(a[0], b[0], q), lerp(a[1], b[1], q), lerp(a[2], b[2], q)];
const segs = (pts) => { const L = []; let tot = 0; for (let i = 0; i < pts.length - 1; i++) { const d = Math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1], pts[i + 1][2] - pts[i][2]); L.push(d); tot += d; } return [L, tot]; };
function along(pts, q) {
  const [L, tot] = segs(pts); let s = clamp(q) * tot;
  for (let i = 0; i < L.length; i++) { if (s <= L[i] || i === L.length - 1) return lerp3(pts[i], pts[i + 1], L[i] ? clamp(s / L[i]) : 0); s -= L[i]; }
  return pts[pts.length - 1];
}
function sub(pts, q) {
  if (q >= 1) return pts;
  const [L, tot] = segs(pts); let s = Math.max(0, q) * tot; const out = [pts[0]];
  for (let i = 0; i < L.length; i++) { if (s <= L[i]) { out.push(lerp3(pts[i], pts[i + 1], L[i] ? s / L[i] : 0)); return out; } out.push(pts[i + 1]); s -= L[i]; }
  return out;
}
const pulse = (t, t0, k = 3) => (t > t0 ? Math.exp(-(t - t0) * k) : 0);
function key1(t, keys, fn = ease.inOut) {
  if (t <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) if (t < keys[i][0]) return lerp(keys[i - 1][1], keys[i][1], fn(prog(t, keys[i - 1][0], keys[i][0])));
  return keys[keys.length - 1][1];
}
function arc(a, b, q, hgt) { return [lerp(a[0], b[0], q), lerp(a[1], b[1], q), lerp(a[2], b[2], q) + Math.sin(q * Math.PI) * hgt]; }
/* ------------------------------------------------------------------ DOM helpers */
const cards = $('cards'), kin = $('kin'), lbls = $('lbls'), fx = $('fx');
function div(parent, cls, html, style) { const d = document.createElement('div'); if (cls) d.className = cls; if (html != null) d.innerHTML = html; if (style) d.style.cssText = style; parent.appendChild(d); return d; }
function vis(elm, a, extra = '') { elm.style.display = a > 0.001 ? '' : 'none'; elm.style.opacity = a; if (extra !== null) elm.style.transform = extra; }
const popIn = (t, a, b, d = 0.3) => { const i = ease.back(prog(t, a, a + d)), o = ep(t, b - 0.22, b, ease.in); return { a: t < a ? 0 : Math.min(1, prog(t, a, a + 0.12)) * (1 - o), s: t < a ? 0.8 : lerp(0.8, 1, i) - o * 0.06, y: (1 - Math.min(1, i)) * 12 + o * -8 }; };
function cardAnim(elm, t, a, b, ox = 0) { const p = popIn(t, a, b); vis(elm, p.a, `translate(${ox}px, ${p.y}px) scale(${p.s})`); return p.a; }
const LB = {};
function lbl(key, html, cls, style) { if (!LB[key]) LB[key] = div(lbls, cls, html, style); return LB[key]; }
// world-anchored pill that pops in at a and out at b
function tag(key, html, style, wp, t, a, b, dy = 0) {
  const e = lbl(key, html, 'lbl', style);
  if (e._h !== html) { e._h = html; e.innerHTML = html; }
  if (e._st !== style) { e._st = style; e.style.cssText = style; }
  const pp = popIn(t, a, b);
  if (pp.a <= 0.001) { e.style.display = 'none'; return e; }
  const p = P(...wp); e.style.left = p[0] + 'px'; e.style.top = p[1] + dy + 'px';
  vis(e, pp.a, `translate(-50%,-50%) scale(${pp.s})`);
  return e;
}
const SV_ = 'http://www.w3.org/2000/svg';
const LN = {};
function cline(key, p0, p1, a, col = '#fff') { if (!LN[key]) { LN[key] = document.createElementNS(SV_, 'g'); LN[key].innerHTML = '<line stroke-width="1" /><circle r="2.6" />'; fx.appendChild(LN[key]); } const gN = LN[key]; gN.style.display = a > 0.01 ? '' : 'none'; gN.style.opacity = a; const [l, c] = gN.children; l.setAttribute('x1', p0[0]); l.setAttribute('y1', p0[1]); l.setAttribute('x2', p1[0]); l.setAttribute('y2', p1[1]); l.setAttribute('stroke', col); c.setAttribute('cx', p0[0]); c.setAttribute('cy', p0[1]); c.setAttribute('fill', col); }
function callout(key, text, wp, dx, dy, a, col = '#fff') {
  const e = lbl(key, text, 'co');
  if (e._h !== text) { e._h = text; e.innerHTML = text; }
  const p = P(...wp), q = [p[0] + dx, p[1] + dy];
  cline(key, p, q, a, col);
  e.style.left = q[0] + (dx >= 0 ? 4 : -4) + 'px'; e.style.top = q[1] - 8 + 'px';
  e.style.transform = dx >= 0 ? '' : 'translateX(-100%)';
  e.style.display = a > 0.01 ? '' : 'none'; e.style.opacity = a;
}

