// 35 Face ID: the sculpted head as a signed distance field, in real proportions (cm, eyes at y = 0, chin at -11.8,
// crown at +11.4): cranium, face and jaw masses blended together, then brow, closed eyes, nose, lips and chin.
// Head-local units are cm * HS. x right, y up, z forward (the face looks along +z). Self-contained: also runs in node.

const HR = 50, HS = 4.2;
const _cl = (v) => Math.min(1, Math.max(0, v));
function _el(x, y, z, cx, cy, cz, rx, ry, rz) {
  x -= cx; y -= cy; z -= cz;
  const k0 = Math.hypot(x / rx, y / ry, z / rz), k1 = Math.hypot(x / (rx * rx), y / (ry * ry), z / (rz * rz));
  return k1 < 1e-9 ? -Math.min(rx, ry, rz) : (k0 * (k0 - 1)) / k1;
}
const _smin = (a, b, k) => { const h = _cl(0.5 + (0.5 * (b - a)) / k); return b + (a - b) * h - k * h * (1 - h); };
const _smax = (a, b, k) => -_smin(-a, -b, k);
// a capsule whose radius goes from r1 at a to r2 at b
function _cap(x, y, z, ax, ay, az, bx, by, bz, r1, r2) {
  const px = x - ax, py = y - ay, pz = z - az, ux = bx - ax, uy = by - ay, uz = bz - az;
  const h = _cl((px * ux + py * uy + pz * uz) / (ux * ux + uy * uy + uz * uz));
  return Math.hypot(px - ux * h, py - uy * h, pz - uz * h) - (r1 + (r2 - r1) * h);
}
function headSDF(x, y, z) {
  const X = Math.abs(x);
  let d = _el(x, y, z, 0, 2.4, -0.9, 7.2, 9.0, 9.0);                                   // cranium
  d = _smin(d, _el(x, y, z, 0, 0.5, 3.2, 6.4, 7.0, 6.0), 2.0);                         // face mass
  d = _smin(d, _el(x, y, z, 0, 4.6, 3.0, 6.0, 5.4, 5.7), 2.0);                         // forehead
  d = _smin(d, _el(x, y, z, 0, -6.4, 6.1, 3.3, 2.7, 3.4), 1.6);                        // muzzle (mouth area)
  const jq = _cl((-y - 4) / 7.5), jw = 1 - 0.36 * jq * jq * (3 - 2 * jq);                                            // the jaw narrows to the chin
  d = _smin(d, _el(x / jw, y, z, 0, -6.0, 2.6, 5.5, 5.4, 6.3) * jw, 2.2);              // jaw and lower face
  d = _smin(d, _el(x, y, z, 0, -9.9, 7.9, 2.3, 1.75, 1.9), 1.5);                       // chin
  d = _smin(d, _el(X, y, z, 4.4, -1.6, 5.2, 2.6, 2.0, 2.6), 1.5);                      // cheekbones
  d = _smin(d, _el(X, y, z, 3.6, -4.5, 5.2, 2.3, 2.6, 2.4), 2.0);                      // cheeks
  d = _smax(d, -(Math.hypot(X - 3.15, y - 0.25, z - 9.3) - 1.95), 1.3);                 // eye sockets
  d = _smin(d, _el(X, y, z, 3.15, 0.0, 6.95, 1.55, 1.1, 1.3), 0.45);                  // closed eyes
  d = _smin(d, _el(X, y, z, 2.85, 2.0, 7.6, 2.3, 0.8, 1.0), 1.9);                     // brow
  let n = _cap(x, y, z, 0, 1.0, 8.6, 0, -4.0, 10.6, 0.72, 0.92);                       // nose bridge
  n = _smin(n, Math.hypot(x, y + 4.2, z - 10.3) - 1.05, 0.5);                          // nose tip
  n = _smin(n, _el(X, y, z, 1.15, -4.5, 9.5, 0.85, 0.75, 0.9), 0.4);                   // nostril wings
  d = _smin(d, n, 0.7);
  d = _smin(d, _el(x, y, z, 0, -6.55, 9.25, 2.1, 0.5, 0.6), 0.5);                       // upper lip
  d = _smin(d, _el(x, y, z, 0, -7.55, 9.1, 1.8, 0.55, 0.65), 0.5);                       // lower lip
  d = _smax(d, -_el(x, y, z, 0, -7.08, 9.8, 2.0, 0.1, 0.9), 0.2);                    // mouth line
  d = _smin(d, _el(X, y, z, 6.75, -1.0, -0.4, 0.75, 2.7, 1.5), 0.8);                     // ears
  return d;
}
const headD = (x, y, z) => headSDF(x / HS, y / HS, z / HS) * HS;   // in head-local units
// distance from the centre to the surface along a direction, / HR (the outermost surface, traced inwards)
function headR(x, y, z) {
  const n = Math.hypot(x, y, z); x /= n; y /= n; z /= n;
  let t = 16;
  for (let i = 0; i < 120; i++) { const s = headSDF(x * t, y * t, z * t); if (s < 1e-4) break; t -= Math.max(s * 0.8, 1e-4); }
  return (t * HS) / HR;
}
// ray against the head in head-local space (sphere tracing). Returns t or -1.
function headHit(o, d, t0 = 0, t1 = 400) {
  let t = t0;
  for (let i = 0; i < 240 && t < t1; i++) {
    const s = headD(o[0] + d[0] * t, o[1] + d[1] * t, o[2] + d[2] * t);
    if (s < 0.02) return t;
    t += Math.max(s * 0.8, 0.02);
  }
  return -1;
}
if (typeof module !== 'undefined') module.exports = { headSDF, headD, headR, headHit, HR, HS };
