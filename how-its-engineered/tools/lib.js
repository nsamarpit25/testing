// Shared helpers for render(t) video pages. Loaded with a plain <script>.
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, t) => a + (b - a) * t;
const prog = (t, a, b) => clamp((t - a) / (b - a));
const ease = {
  out: (t) => 1 - Math.pow(1 - t, 3),
  in: (t) => t * t * t,
  inOut: (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
  outExpo: (t) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t)),
  back: (t) => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); },
};
// eased progress between a and b
const ep = (t, a, b, fn = ease.out) => fn(prog(t, a, b));
// value that rises in [a, a+d] and falls in [b-d, b]
const window01 = (t, a, b, d = 0.3) => Math.min(ep(t, a, a + d), 1 - ep(t, b - d, b));

const SVGNS = 'http://www.w3.org/2000/svg';
function el(tag, attrs = {}, parent) {
  const n = document.createElementNS(SVGNS, tag);
  for (const k in attrs) n.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(n);
  return n;
}

/*
 Captions. Each cue: { t, end, text } where text uses
   "|"     line break
   *word*  key word (styled .key)
   [word]  key word in a pill (styled .key.pill)
 Words are revealed one by one starting at cue.t, `gap` seconds apart.
 Returns { cues, wordTimes } so other things (lip flaps) can sync to the same times.
*/
function makeCaptions(container, cues, gap = 0.26) {
  const built = cues.map((c) => {
    const box = document.createElement('div');
    box.className = 'cap';
    const words = [];
    c.text.split('|').forEach((line, li) => {
      const row = document.createElement('div');
      row.className = 'cap-line';
      // tokens: *multi word key*  [pill group]  _emphasis words_  plain
      for (const m of line.trim().matchAll(/\*[^*]+\*[.,!?]*|\[[^\]]+\][.,!?]*|_[^_]+_[.,!?]*|\S+/g)) {
        const tok = m[0];
        const mk = (text, cls) => { const s = document.createElement('span'); s.className = 'w ' + cls; s.textContent = text; row.appendChild(s); words.push(s); };
        if (tok[0] === '[') mk(tok.replace(/[\[\]]/g, ''), 'key pill');
        else if (tok[0] === '*' || tok[0] === '_') {
          const cls = tok[0] === '*' ? 'key' : 'em';
          tok.replace(/[*_]/g, '').split(/\s+/).forEach((w) => mk(w, cls));
        } else mk(tok, '');
      }
      box.appendChild(row);
    });
    box.style.display = 'none';
    container.appendChild(box);
    // gaps[i] = pause after word i (defaults to `gap`); or `dur` = spread words over the spoken phrase by length
    const times = [];
    if (c.dur) {
      const L = words.map((w) => w.textContent.length + 2), tot = L.reduce((a, b) => a + b, 0);
      words.reduce((acc, _, i) => { times.push(acc); return acc + (L[i] / tot) * c.dur * 0.85; }, c.t);
    } else words.reduce((acc, _, i) => { times.push(acc); return acc + ((c.gaps && c.gaps[i]) ?? gap); }, c.t);
    return { ...c, box, words, times };
  });
  const allTimes = built.flatMap((b) => b.times);
  return {
    wordTimes: allTimes,
    render(t) {
      for (const c of built) {
        const on = t >= c.t - 0.05 && t < c.end;
        c.box.style.display = on ? '' : 'none';
        if (!on) continue;
        const out = ep(t, c.end - 0.22, c.end, ease.in);
        c.box.style.opacity = 1 - out;
        c.box.style.transform = `translateY(${-out * 8}px)`;
        c.words.forEach((w, i) => {
          const p = ep(t, c.times[i], c.times[i] + 0.2);
          w.style.opacity = 0.0 + p;
          w.style.filter = p < 1 ? `blur(${(1 - p) * 6}px)` : 'none';
          w.style.transform = `translateY(${(1 - p) * 6}px)`;
        });
      }
    },
  };
}

// 0..1 mouth openness from word times (simple lip flap)
function mouthOpen(t, times, wordLen = 0.24) {
  let v = 0;
  for (const wt of times) {
    if (t < wt || t > wt + wordLen) continue;
    const p = (t - wt) / wordLen;
    v = Math.max(v, Math.sin(p * Math.PI) * (0.65 + 0.35 * Math.sin(wt * 37)));
  }
  return v;
}

// Deterministic noise texture (data URL) for paper grain.
function grainURL(size = 256, alpha = 0.06, seed = 7) {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const g = c.getContext('2d');
  const img = g.createImageData(size, size);
  let s = seed;
  const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < img.data.length; i += 4) {
    const v = rnd() * 255;
    img.data[i] = img.data[i + 1] = img.data[i + 2] = v;
    img.data[i + 3] = rnd() * 255 * alpha;
  }
  g.putImageData(img, 0, 0);
  return c.toDataURL();
}
