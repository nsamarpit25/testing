// Isometric line-art engine for the black style. Needs tools/lib.js loaded first.
// All drawing goes into ISO.layer (an <svg>), cleared by the page each frame.
const ISO = { layer: null };
// pitch: camera elevation in radians (0.6155 = true isometric; higher = more top-down)
const CAM = { yaw: 0, pitch: 0.6155, scale: 1, ox: 270, oy: 520 };

function raw(x, y, z) {
  const c = Math.cos(CAM.yaw), s = Math.sin(CAM.yaw);
  const rx = x * c - y * s, ry = x * s + y * c;
  return [(rx - ry) * 0.866, ((rx + ry) * 0.7071 * Math.sin(CAM.pitch) - z * Math.cos(CAM.pitch)) * 1.2247];
}
function P(x, y, z) { const r = raw(x, y, z); return [CAM.ox + r[0] * CAM.scale, CAM.oy + r[1] * CAM.scale]; }
const depth = (x, y) => { const c = Math.cos(CAM.yaw), s = Math.sin(CAM.yaw); return (x * c - y * s) + (x * s + y * c); };
// point the camera so world point `focus` lands on screen (sx, sy)
function aim(focus, sx, sy) { const r = raw(...focus); CAM.ox = sx - r[0] * CAM.scale; CAM.oy = sy - r[1] * CAM.scale; }
const path2 = (pts, close = true) => 'M' + pts.map((p) => p[0].toFixed(2) + ' ' + p[1].toFixed(2)).join('L') + (close ? 'Z' : '');
const add3 = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const mul3 = (a, k) => [a[0] * k, a[1] * k, a[2] * k];
const len3 = (a) => Math.hypot(a[0], a[1], a[2]);

// ---- primitives collected per object, then emitted with a staggered draw-in ----
function Obj() { return { items: [], texts: [] }; }
function push(o, d, opt = {}) { o.items.push({ d, ...opt }); }
const fp = (F, a, b) => P(...add3(add3(F.o, mul3(F.u, a)), mul3(F.v, b)));
function fpoly(o, F, a, b, wa, hb, opt = {}) {
  push(o, path2([fp(F, a, b), fp(F, a + wa, b), fp(F, a + wa, b + hb), fp(F, a, b + hb)]), { w: 0.7, ...opt });
}
function fline(o, F, a1, b1, a2, b2, opt = {}) { push(o, path2([fp(F, a1, b1), fp(F, a2, b2)], false), { w: 0.7, fill: 'none', ...opt }); }
function fdot(o, F, a, b, r = 0.9, opt = {}) {
  const p = fp(F, a, b); const R = r * Math.min(1.4, CAM.scale + 0.2);
  push(o, `M${p[0] - R} ${p[1]}a${R} ${R} 0 1 0 ${2 * R} 0a${R} ${R} 0 1 0 ${-2 * R} 0`, { fill: '#fff', stroke: 'none', ...opt });
}
// text lying on a face; a,b = position (0..1), size in world units
function ftext(o, F, a, b, str, size, opt = {}) { o.texts.push({ F, a, b, str, size, ...opt }); }

function box(o, x, y, z, w, d, h, opt = {}) {
  const c = Math.cos(CAM.yaw), s = Math.sin(CAM.yaw);
  const vis = (nx, ny) => (nx * c - ny * s) + (nx * s + ny * c) > 0.001;
  const F = {};
  const sides = [
    ['px', [x + w, y, z], [0, d, 0], [0, 0, h], 1, 0],
    ['nx', [x, y, z], [0, d, 0], [0, 0, h], -1, 0],
    ['py', [x, y + d, z], [w, 0, 0], [0, 0, h], 0, 1],
    ['ny', [x, y, z], [w, 0, 0], [0, 0, h], 0, -1],
  ];
  for (const [k, oo, u, v, nx, ny] of sides) {
    if (!vis(nx, ny)) continue;
    F[k] = { o: oo, u, v };
    fpoly(o, F[k], 0, 0, 1, 1, { fill: '#000', w: 1, ...opt });
  }
  F.top = { o: [x, y, z + h], u: [w, 0, 0], v: [0, d, 0] };
  fpoly(o, F.top, 0, 0, 1, 1, { fill: '#000', w: 1, ...opt });
  return F;
}
function cylinder(o, cx, cy, z, r, h, bands = 2) {
  const N = 48;
  const ring = (zz) => Array.from({ length: N + 1 }, (_, i) => { const a = (i / N) * Math.PI * 2; return P(cx + r * Math.cos(a), cy + r * Math.sin(a), zz); });
  const bot = ring(z), top = ring(z + h);
  let L = 0, R = 0;
  bot.forEach((p, i) => { if (p[0] < bot[L][0]) L = i; if (p[0] > bot[R][0]) R = i; });
  const walk = (pts, dir) => { const a = []; let i = L; for (let k = 0; k <= N; k++) { a.push(pts[i]); if (i === R) break; i = (i + dir + N) % N; } return a; };
  const probe = walk(bot, 1);
  const dir = probe[Math.floor(probe.length / 2)][1] > (bot[L][1] + bot[R][1]) / 2 ? 1 : -1;
  const fb = walk(bot, dir), ft = walk(top, dir);
  push(o, path2([...fb, ...ft.slice().reverse()]), { fill: '#000', w: 1 });
  for (let b = 1; b <= bands; b++) push(o, path2(walk(ring(z + (h * b) / (bands + 1)), dir), false), { fill: 'none', w: 0.7 });
  push(o, path2(top), { fill: '#000', w: 1 });
}

// D: 0..1 draw progress (lines draw in, staggered). op: overall opacity.
function emit(o, D, op = 1) {
  if (D <= 0 || op <= 0) return;
  const layer = ISO.layer;
  const n = o.items.length;
  o.items.forEach((it, i) => {
    const f = n > 1 ? (i / (n - 1)) * 0.6 : 0;
    const dp = ease.out(prog(D, f, f + 0.4));
    if (dp <= 0) return;
    const p = el('path', {
      d: it.d, fill: it.fill ?? '#000', 'fill-opacity': it.fill === 'none' ? 0 : clamp(dp * 1.6) * (it.fillOp ?? 1),
      stroke: it.stroke ?? '#fff', 'stroke-width': it.w ?? 1, 'stroke-opacity': (it.op ?? 1) * op,
      'stroke-linejoin': 'round', 'stroke-linecap': 'round',
    }, layer);
    if (op < 1) p.setAttribute('opacity', op);
    if (it.dash) p.setAttribute('stroke-dasharray', it.dash);
    else if (dp < 1 && it.stroke !== 'none') { p.setAttribute('pathLength', '1'); p.setAttribute('stroke-dasharray', '1 1'); p.setAttribute('stroke-dashoffset', 1 - dp); }
  });
  const tp = ease.out(prog(D, 0.55, 1));
  for (const t of o.texts) {
    if (tp <= 0) continue;
    const U = [fp(t.F, 1, 0)[0] - fp(t.F, 0, 0)[0], fp(t.F, 1, 0)[1] - fp(t.F, 0, 0)[1]];
    const V = [fp(t.F, 0, 1)[0] - fp(t.F, 0, 0)[0], fp(t.F, 0, 1)[1] - fp(t.F, 0, 0)[1]];
    const lu = len3(t.F.u), lv = len3(t.F.v), O = fp(t.F, 0, 0);
    const g = el('g', { transform: `matrix(${U[0] / lu} ${U[1] / lu} ${V[0] / lv} ${V[1] / lv} ${O[0]} ${O[1]})` }, layer);
    const tx = el('text', {
      x: t.a * lu, y: t.b * lv, 'font-size': t.size, fill: t.fill ?? '#fff', 'font-family': t.font ?? 'Inter',
      'font-weight': t.weight ?? 700, 'text-anchor': t.anchor ?? 'middle', 'dominant-baseline': 'middle', 'letter-spacing': t.ls ?? 0,
      opacity: tp * op * (t.op ?? 1),
    }, g);
    tx.textContent = t.str;
  }
}

// ---- reusable objects ----
function tileDots(o, F, nx, ny) {
  for (let i = 1; i < nx; i++) for (let j = 1; j < ny; j++) fdot(o, F, i / nx, j / ny, 0.55, { fillOp: 0.55 });
}
function rack(o, x, y, z, w, d, h) {
  const F = box(o, x, y, z, w, d, h);
  if (F.py) {
    const R = F.py;
    fpoly(o, R, 0.07, 0.03, 0.86, 0.94, { fill: 'none', w: 0.6 });
    for (let k = 0; k < 12; k++) {
      const b = 0.06 + k * 0.074;
      fline(o, R, 0.1, b, 0.9, b, { w: 0.55, op: 0.8 });
      fpoly(o, R, 0.15, b + 0.016, 0.32, 0.04, { fill: 'none', w: 0.55 });
      fpoly(o, R, 0.5, b + 0.016, 0.18, 0.04, { fill: 'none', w: 0.55, op: 0.7 });
      fdot(o, R, 0.8, b + 0.036, 0.75);
    }
  }
  if (F.px) {
    for (let k = 0; k < 9; k++) fline(o, F.px, 0.15 + k * 0.085, 0.62, 0.15 + k * 0.085, 0.92, { w: 0.55, op: 0.7 });
    for (let k = 0; k < 9; k++) fline(o, F.px, 0.15 + k * 0.085, 0.08, 0.15 + k * 0.085, 0.38, { w: 0.55, op: 0.7 });
  }
  fpoly(o, F.top, 0.1, 0.12, 0.8, 0.76, { fill: 'none', w: 0.6 });
  fline(o, F.top, 0.2, 0.3, 0.8, 0.3, { w: 0.6 });
  fline(o, F.top, 0.2, 0.5, 0.8, 0.5, { w: 0.6 });
  return F;
}
function packet(o, x, y, z, solid = true) {
  const F = box(o, x - 6, y - 6, z, 12, 12, 12);
  if (solid) fpoly(o, F.top, 0.25, 0.25, 0.5, 0.5, { fill: '#fff', stroke: 'none' });
}
