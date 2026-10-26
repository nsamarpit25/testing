// Shared constants and helpers for the ember remakes. Load after world.js, before the page's own script.
const WORDS = window.WORDS, TIMINGS = window.TIMINGS;
const DURATION = TIMINGS[TIMINGS.length - 1].end + 1.8;
window.DURATION = DURATION;
const O = '#ff6a1f', O2 = '#ffb070', OK = '#ff6a1f', RED = '#ff4d5e', AMB = '#ffb547', DIM = '#4b4743', WH = '#f4f3f2', GR = '#9e9995';
const pulse = (t, t0, k = 3) => (t > t0 ? Math.exp(-(t - t0) * k) : 0);
function colAt(keys, t, d = 0.3) {
  let i = 0; keys.forEach(([a], j) => { if (a <= t) i = j; });
  if (i === 0 || t < keys[0][0]) return keys[0][1];
  return mixHex(keys[i - 1][1], keys[i][1], (t - keys[i][0]) / d);
}
const lastKey = (keys, t) => { let i = 0; keys.forEach(([a], j) => { if (a <= t) i = j; }); return keys[i][0]; };

// at('crashed') → start time of the first spoken "crashed"; at('image', 2) → the second one. Throws if missing.
const _wn = (s) => s.toLowerCase().replace(/[^a-z0-9]/g, '');
function at(word, n = 1, end = false) {
  let k = 0;
  for (const w of WORDS) if (_wn(w[0]) === _wn(word) && ++k === n) return end ? w[2] : w[1];
  throw new Error('no word ' + word + ' #' + n);
}
// line li, part pi start/end from timings
const line = (li, pi = 0) => TIMINGS.find((x) => x.li === li && x.pi === pi);
