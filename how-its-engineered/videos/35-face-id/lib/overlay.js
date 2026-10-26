// 35 Face ID fork: calm fades (calmIn), karaoke captions in a quiet box, a top-left state widget, news receipt cards.
// Shared overlays for the ember remakes (same look as 21): code card, tool card, serif slams, captions, profile card,
// dim/flash/grain. The page defines its world first, then a REEL config, then loads this file. This file builds the DOM
// and window.render / window.ready.
//
// REEL = {
//   shots, kicks, shakes,            camera (see world.js camAt)
//   world(t), tags(t),               the page's own 3D world and world-anchored labels
//   code: [[from, to, file, kind, chips, lines, cues, mode]...]   (same shape as 21's CODE)
//   tools: [{a, b, svg, name, sub, src}],
//   slams: [{a, b, text, sub, size, top}],
//   bad: [...words], good: [...words],   caption colours
//   tiles: [[icon, 'TITLE<br>LINE'], x3],   end: time the profile card comes in, follow: time of "follow"
//   flash(t) → opacity of the red flash, hl: extra keyword regex for the code card
// }
function buildOverlays(R) {
  const st = $('stage');
  const add = (html) => { const w = document.createElement('div'); w.innerHTML = html.trim(); const n = w.firstChild; st.appendChild(n); return n; };
  add('<div id="vig"></div>'); add('<div id="dim"></div>');
  add(`<div id="ed"><div class="tb"><i></i><i></i><i></i><span class="fn" id="edfn"></span><span class="st" id="edst"></span></div><div id="code">${
    [1, 2, 3, 4, 5].map((i) => `<div class="ln" id="l${i}"><span class="n">${i}</span><span id="l${i}t"></span><span class="r" id="l${i}r"></span></div>`).join('')}</div></div>`);
  (R.tools || []).forEach((tl, i) => {
    tl.el = add(`<div class="tool" id="tool${i}" style="position:absolute;left:26px;right:26px;top:${tl.top || 150}px;display:none;padding:16px 18px;border-radius:12px;background:rgba(19,17,15,0.95);border:1px solid rgba(255,106,31,0.4);box-shadow:0 14px 34px rgba(8,6,4,0.6),0 0 40px rgba(255,106,31,0.08)">
      <div style="display:flex;align-items:center;gap:16px">${tl.svg || ''}<div><div style="font:800 25px/1 Inter;letter-spacing:-0.5px">${tl.name}</div><div style="font:600 11px/1 Mono;letter-spacing:1.2px;color:#ffb070;margin-top:8px">${tl.sub}</div></div></div>
      ${tl.src ? `<div style="font:600 9px/1 Mono;letter-spacing:1px;color:#6e6965;margin-top:12px;border-top:1px solid rgba(255,255,255,0.06);padding-top:10px">${tl.src}</div>` : ''}</div>`);
  });
  (R.slams || []).forEach((s, i) => {
    s.el = add(`<div class="slam" style="top:${s.top || 236}px"><div class="t" style="font-size:${s.size || 66}px">${s.text}</div>${s.sub ? `<div class="sub">${s.sub}</div>` : ''}</div>`);
  });
  const tiles = R.tiles.map(([ic, tt], i) => `<div class="tile" ${i ? '' : 'id="t0"'}><div class="ic" ${i ? '' : 'id="t0i"'}>${ic}</div><div class="t">${tt}</div></div>`).join('');
  add(`<div id="prof"><div class="top"><div class="ring"><div>{ }</div></div><div style="flex:1;min-width:0"><div style="font-weight:800;font-size:16px">@how.its.engineered</div><div style="color:#9e9995;font-size:11.5px;margin-top:3px">System design, one picture at a time</div></div><div id="fb">Follow</div></div><div class="tiles">${tiles}</div></div>`);
  add('<div id="cap"></div>');
  add('<svg id="cursor" viewBox="0 0 22 28"><path d="M2 2 L2 22 L7.5 17 L11 25 L14.5 23.5 L11 15.5 L18.5 15.5 Z" fill="#fff" stroke="#0b0a09" stroke-width="1.6" stroke-linejoin="round"/></svg>');
  add('<div id="flash"></div>'); add('<div id="grain"></div>');
  // the Face ID badge: the glyph (four corners, eyes, nose, smile) and one status word
  if (R.state) R.state.el = add(`<div id="state"><svg viewBox="0 0 40 40" width="26" height="26" fill="none" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12V8a4 4 0 0 1 4-4h4M28 4h4a4 4 0 0 1 4 4v4M36 28v4a4 4 0 0 1-4 4h-4M12 36H8a4 4 0 0 1-4-4v-4"/><path id="stf" d="M14 14v3M26 14v3M20 14v8h-2M15 27c3 2.4 7 2.4 10 0"/></svg><span id="stw"></span></div>`);
}

/* ---------------- code card */
const setH = (id, h) => { const e = $(id); if (e._h !== h) { e._h = h; e.innerHTML = h; } };
const esc = (x) => x.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
function hl(line) {
  let h = esc(line);
  if (/^\s*(\/\/|--|#)/.test(line)) return `<span class="c">${h}</span>`;
  h = h.replace(/('[^']*'|"[^"]*")/g, '<span class="s">$1</span>');
  h = h.replace(REEL.hl || /\b(if|else|return|await|FROM|RUN|COPY|CMD|WORKDIR|kind|image|replicas|location|proxy_pass|upstream|server|limit_req|GET|POST|PUT|HTTP)\b/g, '<span class="oc">$1</span>');
  h = h.replace(/\b(true|OK|200|healthy|Running)\b/g, '<span class="okc">$1</span>');
  h = h.replace(/(\.?[A-Za-z_]\w*)(?=\()/g, '<span style="color:#fff">$1</span>');
  return h;
}
const TYPE_CPS = 54;
function card(t) {
  const seg_ = (REEL.code || []).find((c) => t >= c[0] && t < c[1]), ed = $('ed');
  if (!seg_) { ed.style.display = 'none'; return; }
  const [a, b, file, kind, chips, lines, cues, mode] = seg_;
  const k = ep(t, a, a + 0.25) * (1 - ep(t, b - 0.2, b));
  ed.style.display = 'block'; ed.style.opacity = k; ed.style.transform = `translateY(${(1 - ep(t, a, a + 0.3, ease.out)) * -14}px)`;
  let chip = chips[0]; for (const c of chips) if (t >= c[0]) chip = c;
  setH('edfn', `<b>${file}</b> <span style="color:#6e6965">· ${kind}</span>`);
  setH('edst', '● ' + chip[1]); $('edst').style.color = chip[2];
  ed.style.borderColor = chip[2] === RED ? 'rgba(255,77,94,0.5)' : chip[2] === OK ? 'rgba(255,106,31,0.4)' : 'rgba(255,181,71,0.45)';
  const res = {}; let act = 0, acls = '';
  for (const [ct, ln, r, cl] of cues) if (t >= ct - 0.05) { res[ln] = r === '' ? null : [typeof r === 'function' ? r(t) : r, cl]; act = r === '' ? act : ln; acls = r === '' ? acls : cl; }
  let chars = mode === 'type' ? Math.max(0, (t - a - 0.15) * TYPE_CPS) : 1e9;
  for (let i = 1; i <= 5; i++) {
    const L = lines[i - 1], showL = L !== undefined && (L[1] === undefined || t >= L[1]);
    $(`l${i}`).style.display = L !== undefined ? 'flex' : 'none';
    if (L === undefined) continue;
    let txt = showL ? L[0] : '', caret = '';
    if (mode === 'type') { const n = Math.floor(clamp(chars, 0, txt.length)); if (n > 0 && n < txt.length) caret = '<span class="caret"></span>'; chars -= txt.length + 2; txt = txt.slice(0, n); }
    setH(`l${i}t`, hl(txt) + caret);
    const r = res[i], col = r ? (r[1] === 'bad' ? RED : r[1] === 'good' ? OK : r[1] === 'amb' ? AMB : O2) : '';
    setH(`l${i}r`, r && r[0] ? `<span style="color:${col}">${esc(r[0])}</span>` : '');
    $(`l${i}r`).style.opacity = r ? (i === act ? 1 : 0.55) : 0;
    $(`l${i}`).className = 'ln' + (i === act && r ? ' ' + (acls || 'run') : '');
  }
}
function tools(t) {
  for (const tl of REEL.tools || []) { const p = calmIn(t, tl.a, tl.b); vis(tl.el, p.a, `translateY(${p.y}px)`); tl.el.style.display = p.a > 0.001 ? 'block' : 'none'; }
}

/* ---------------- captions (same chunking as 21) */
let CHUNKS = [];
function buildCaptions() {
  const BADW = new Set(REEL.bad || []), GOODW = new Set(REEL.good || []);
  const norm = (s) => s.toLowerCase().replace(/[^a-z0-9-]/g, '');
  const CAPW = [];
  TIMINGS.forEach((p) => {
    let star = false, pill = false;
    const toks = p.show.split(/\s+/).filter(Boolean).map((r) => {
      if (r.startsWith('*')) star = true; if (r.startsWith('[')) pill = true;
      const tk = { s: r.replace(/[*[\]]/g, ''), star, pill };
      if (/\*[.,?!:]*$/.test(r)) star = false; if (/\][.,?!:]*$/.test(r)) pill = false;
      return tk;
    });
    for (let j = 0; j < toks.length;) {
      if (!toks[j].pill) { j++; continue; }
      let e = j; while (e < toks.length && toks[e].pill) e++;
      const run = toks.slice(j, e).map((x) => norm(x.s));
      const pc = run.some((x) => BADW.has(x)) ? RED : run.some((x) => GOODW.has(x)) ? OK : O;
      for (let q = j; q < e; q++) toks[q].col = pc; j = e;
    }
    toks.forEach((k) => { if (!k.col && k.star) k.col = BADW.has(norm(k.s)) ? RED : GOODW.has(norm(k.s)) ? OK : O; });
    const ws = WORDS.filter(([, a]) => a >= p.start - 0.02 && a < p.end - 0.01);
    if (ws.length === toks.length) toks.forEach((k, j) => { k.a = ws[j][1]; k.b = ws[j][2]; });
    else {
      const a = ws.length ? ws[0][1] : p.start, b = ws.length ? ws[ws.length - 1][2] : p.end;
      const tot = toks.reduce((n, k) => n + k.s.length + 1, 0); let acc = 0;
      toks.forEach((k) => { k.a = a + (b - a) * (acc / tot); acc += k.s.length + 1; k.b = a + (b - a) * (acc / tot); });
    }
    CAPW.push(...toks);
  });
  const WEAK = new Set(['a', 'an', 'the', 'are', 'on', 'in', 'it', 'and', 'at', 'is', 'of', 'to', 'for', 'with', 'by', 'its', 'has', 'that', 'so', 'but', 'or', 'if', 'your', 'you']);
  let cur = [];
  const flushC = () => {
    if (!cur.length) return;
    const carry = [];
    while (carry.length < 2 && cur.length >= 2 && !/[.,?:!]$/.test(cur[cur.length - 1].s) && WEAK.has(cur[cur.length - 1].s.toLowerCase())) carry.unshift(cur.pop());
    CHUNKS.push(cur); cur = carry;
  };
  CAPW.forEach((w) => {
    const prev = cur[cur.length - 1];
    const len = cur.reduce((n, x) => n + x.s.length + 1, 0);
    if (prev && (/[.?:!]$/.test(prev.s) || (/,$/.test(prev.s) && cur.length >= 3) || cur.length >= 4 || len + w.s.length > 24 || w.a - prev.b > 0.6)) flushC();
    cur.push(w);
  });
  flushC();
  for (let i = CHUNKS.length - 1; i > 0; i--) {
    const c = CHUNKS[i], p = CHUNKS[i - 1], len = [...p, ...c].reduce((n, x) => n + x.s.length + 1, 0);
    if (c.length <= 2 && p.length + c.length <= 5 && !/[.?!]$/.test(p[p.length - 1].s) && len <= 30) { p.push(...c); CHUNKS.splice(i, 1); }
  }
  CHUNKS.forEach((c, ci) => {
    const bx = div($('cap'), 'box'); c.box = bx;
    c.els = c.map((w) => { const s = document.createElement('span'); s.className = 'w'; s.textContent = w.s.replace(/[.,:;]+$/, ''); if (w.col) s.style.color = w.col; bx.appendChild(s); return s; });
    c.t0 = c[0].a - 0.04; c.t1 = CHUNKS[ci + 1] ? Math.min(CHUNKS[ci + 1][0].a - 0.04, c[c.length - 1].b + 0.9) : DURATION;
  });
}
function caps(t) {
  for (const c of CHUNKS) {
    const on = t >= c.t0 && t < c.t1;
    c.box.style.display = on ? 'flex' : 'none';
    if (!on) continue;
    // the whole line sits there quietly; each word brightens as it is spoken
    c.els.forEach((s, i) => { s.style.opacity = 0.55 + 0.45 * prog(t, c[i].a - 0.04, c[i].a + 0.1); });
  }
}

/* ---------------- state widget, receipts */
// REEL.state = { a, b, at(t) → [word, colour] }: the badge's status word and glyph colour
function state(t) {
  const S = REEL.state; if (!S) return;
  const p = calmIn(t, S.a, S.b); S.el.style.display = p.a > 0.001 ? 'flex' : 'none'; S.el.style.opacity = p.a;
  if (p.a <= 0.001) return;
  const [w, col] = S.at(t), sv = S.el.firstChild;
  if (S._w !== w) { S._w = w; $('stw').textContent = w; }
  sv.style.stroke = col; $('stw').style.color = col === '#9e9995' ? '#d9d5d1' : col;
}

/* ---------------- slams, profile */
function slamEl(e, t, a, b) {
  const on = t > a && t < b;
  e.style.display = on ? 'block' : 'none';
  if (!on) return;
  const i = ease.outExpo(prog(t, a, a + 0.35)), o = ep(t, b - 0.25, b, ease.in);
  e.style.opacity = Math.min(1, prog(t, a, a + 0.08)) * (1 - o);
  e.style.transform = `scale(${lerp(1.5, 1, i) + 0.03 * o}) translateY(${o * -10}px)`;
  e.style.filter = i < 0.98 ? `blur(${(1 - i) * 6}px)` : 'none';
}
function cursorAt(x, y, a, press) { const CUR = $('cursor'); CUR.style.display = a > 0.01 ? 'block' : 'none'; CUR.style.opacity = a; CUR.style.left = x + 'px'; CUR.style.top = y + 'px'; CUR.style.transform = `scale(${1 - 0.18 * press})`; }
function profile(t) {
  const END = REEL.end, TAP_F = REEL.follow + 0.35;
  const p = calmIn(t, END + 0.1, DURATION + 1), pr = $('prof');
  vis(pr, p.a, `translateY(${p.y}px)`); pr.style.display = p.a > 0.001 ? 'block' : 'none';
  if (p.a <= 0.001) { cursorAt(0, 0, 0, 0); return; }
  const fb = $('fb'), done = t > TAP_F + 0.08;
  if (fb._d !== done) { fb._d = done; fb.textContent = done ? 'Following ✓' : 'Follow'; fb.style.background = done ? '#2c2927' : ''; fb.style.color = done ? '#f4f3f2' : ''; fb.style.fontSize = done ? '12.5px' : ''; }
  fb.style.transform = `scale(${1 - 0.06 * window01(t, TAP_F, TAP_F + 0.16, 0.06)})`;
  const hi = ep(t, END + 0.4, END + 0.9), tk = $('t0'), ic = $('t0i');
  tk.style.borderColor = `rgba(255,106,31,${hi})`; tk.style.boxShadow = `0 0 ${24 * hi}px rgba(255,106,31,${0.4 * hi})`;
  ic.style.borderColor = hi > 0.3 ? '#ff6a1f' : ''; ic.style.color = hi > 0.3 ? '#ff6a1f' : '';
  const m = ep(t, TAP_F - 0.9, TAP_F - 0.1, ease.inOut);
  cursorAt(lerp(500, 432, m), lerp(560, 316, m), ep(t, TAP_F - 1.0, TAP_F - 0.8), window01(t, TAP_F, TAP_F + 0.16, 0.05));
}

/* ---------------- render */
buildOverlays(REEL);
buildCaptions();
window.render = (t) => {
  camAt(t, REEL.shots, REEL.kicks || [], REEL.shakes || []);
  orbsReset(); sparksReset(); ringsReset();
  REEL.world(t);
  sparksFlush(); updateEmbers(t);
  renderer.render(scene, camera);
  REEL.tags && REEL.tags(t);
  card(t); tools(t);
  (REEL.slams || []).forEach((s) => slamEl(s.el, t, s.a, s.b));
  $('dim').style.opacity = 0.55 * ep(t, REEL.end, REEL.end + 0.6);
  $('flash').style.opacity = REEL.flash ? REEL.flash(t) : 0;
  caps(t);
  state(t);
  profile(t);
};
window.ready = async () => { $('grain').style.background = `url(${grainURL(256, 0.06, 5)})`; await Promise.all([...document.fonts].map((f) => f.load().catch(() => {}))); };

/* ---------------- cover mode: video.html#cover renders a clean frame with the title block (REEL.cover = {k, t, s?, at}; covers are topic-only, so s is normally left out) */
if (/cover/.test(location.hash) && REEL.cover) {
  const css = document.createElement('style');
  css.textContent = `#ed, .tool, #prof, #cap, #cursor, #flash, #lbls, #dim, .slam { display: none !important; }
#ct { position: absolute; inset: 0; text-align: center; background: linear-gradient(180deg, rgba(16,14,13,0.96) 0%, rgba(16,14,13,0.9) 38%, rgba(16,14,13,0) 52%); }
#ct .k { position: absolute; top: 150px; left: 0; right: 0; font-family: Mono; font-weight: 800; font-size: 13px; letter-spacing: 3.5px; color: #ffb070; }
#ct .t { position: absolute; top: 176px; left: 0; right: 0; font-weight: 900; font-size: 58px; letter-spacing: -2.4px; line-height: 0.95; background: linear-gradient(180deg,#ffb070,#ff6a1f 70%); -webkit-background-clip: text; background-clip: text; color: transparent; filter: drop-shadow(0 0 22px rgba(255,106,31,0.45)); }
#ct .s { position: absolute; top: ${REEL.cover.sTop || 256}px; left: 30px; right: 30px; font-family: Instrument; font-size: 34px; line-height: 38px; color: #f4f3f2; }
#ct .s i { color: #ff4d5e; }
#ct .h { position: absolute; bottom: 82px; left: 0; right: 0; font-family: Mono; font-size: 11px; letter-spacing: 2px; color: #9e9995; }
#world { transform: translateY(${REEL.cover.dy ?? 150}px) scale(${REEL.cover.zoom ?? 0.88}); transform-origin: 50% 50%; }`;
  document.head.appendChild(css);
  const c = REEL.cover, d = document.createElement('div'); d.id = 'ct';
  d.innerHTML = `<div class="k">${c.k || 'SYSTEM DESIGN'}</div><div class="t">${c.t}</div>${c.s ? `<div class="s">${c.s}</div>` : ''}<div class="h">@HOW.ITS.ENGINEERED</div>`;
  $('vig').after(d);
}
