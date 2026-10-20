// Hook C, first 10 s. Same beats and timing in every style variant.
// Word times are a stand-in until the real voice exists (then they come from voice/words.json).
const DURATION = 10;
window.DURATION = DURATION;
const WORDS = [
  ['Your', 0.25, 0.45], ['service', 0.45, 0.85], ['restarted.', 0.85, 1.45],
  ['Same', 1.85, 2.1], ['code.', 2.1, 2.5],
  ['New', 2.85, 3.1], ['address.', 3.1, 3.7],
  ['And', 4.2, 4.35], ['every', 4.35, 4.65], ['call', 4.65, 4.95], ['to', 4.95, 5.05], ['it', 5.05, 5.3],
  ['just', 5.55, 5.8], ['failed.', 5.8, 6.4],
  ['So', 7.1, 7.3], ['how', 7.3, 7.5], ['does', 7.5, 7.65], ['anything', 7.65, 8.1], ['ever', 8.15, 8.4], ['find', 8.45, 8.75], ['it?', 8.75, 9.2],
];
// beats
const B = {
  crash: 0.95,      // service goes red and dies
  gone: 1.55,       // removed
  respawn: 2.0,     // lands on another machine
  same: 2.1,        // "same code" check
  newip: 3.1,       // address scrambles to the new one
  ipDone: 3.65,
  calls: 4.25,      // callers keep firing at the old address
  hits: [4.75, 5.15, 5.6],
  failed: 5.85,     // FAILED slam
  q: 7.1,           // the open question
  find: 8.45,
};
const OLD_IP = '10.0.0.7', NEW_IP = '10.0.4.23';
// address text while it scrambles from OLD to NEW between a and b
function ipAt(t, a = B.newip, b = B.ipDone) {
  if (t < a) return OLD_IP;
  if (t >= b) return NEW_IP;
  const k = Math.floor(t * 30);
  return OLD_IP.split('').map((c, i) => (c === '.' ? '.' : String(Math.floor(rndH(i, k) * 10)))).join('').slice(0, NEW_IP.length) || NEW_IP;
}
function rndH(i, s) { const x = Math.sin(i * 127.1 + s * 311.7) * 43758.5453; return x - Math.floor(x); }

// Caption chunks: at most 3 words, break on punctuation or a pause.
function buildChunks(fix = (s) => s) {
  const out = []; let cur = [];
  const flush = () => { if (cur.length) out.push(cur); cur = []; };
  WORDS.forEach(([w, a, b]) => {
    const prev = cur[cur.length - 1];
    const len = cur.reduce((n, x) => n + x.s.length + 1, 0);
    if (prev && (/[.,?:!]$/.test(prev.s) || cur.length >= 3 || len + w.length > 19 || a - prev.b > 0.3)) flush();
    cur.push({ s: fix(w), a, b });
  });
  flush();
  out.forEach((c, i) => { c.t0 = c[0].a - 0.04; c.t1 = out[i + 1] ? Math.min(out[i + 1][0].a - 0.04, c[c.length - 1].b + 0.9) : DURATION; });
  return out;
}
// Bold outlined pop-in captions (house style). colOf(word, t) -> colour or null.
function popCaptions(container, colOf, opt = {}) {
  const chunks = buildChunks();
  chunks.forEach((c) => {
    const box = document.createElement('div'); box.className = 'box'; container.appendChild(box); c.box = box;
    c.els = c.map((w) => {
      const s = document.createElement('span'); s.className = 'w';
      s.textContent = opt.keepPunct ? w.s : w.s.replace(/[.,:;]+$/, '');
      const col = colOf(w.s.toLowerCase().replace(/[.,?:!]/g, ''), w.a);
      if (col) { s.style.color = col; if (opt.glow !== false) s.style.textShadow = (opt.shadow || '0 4px 0 #04060f, ') + `0 0 22px ${col}88`; }
      box.appendChild(s); return s;
    });
  });
  return (t) => {
    for (const c of chunks) {
      const on = t >= c.t0 && t < c.t1;
      c.box.style.display = on ? 'flex' : 'none';
      if (!on) continue;
      const out = c.t1 - c.t0 > 0.3 ? ep(t, c.t1 - 0.1, c.t1, ease.in) : 0;
      c.box.style.opacity = 1 - out;
      c.box.style.transform = `translateY(${-out * 8}px)`;
      c.els.forEach((s, i) => {
        const { a, b } = c[i];
        const p = ep(t, a - 0.04, a + 0.12, ease.back);
        const live = window01(t, a - 0.04, b + 0.08, 0.08);
        s.style.opacity = prog(t, a - 0.04, a + 0.03);
        s.style.transform = `translateY(${(1 - p) * 14 - live * 3}px) scale(${(0.6 + 0.4 * p) * (1 + 0.04 * live)})`;
      });
    }
  };
}
