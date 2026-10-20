// Frame furniture: fonts, background, captions, the transaction HUD and the cross-fading scene wrapper.
import React, { useEffect, useState } from 'react';
import { continueRender, delayRender, staticFile, useCurrentFrame } from 'remotion';
import { COL, FONT, MONO, W, H, FPS, clamp, eo, pop, TL } from './core';
import { P, Defs } from './iso';

export const Fonts: React.FC = () => {
  const [h] = useState(() => delayRender('fonts'));
  useEffect(() => {
    const fs = [new FontFace('Inter', `url(${staticFile('fonts/inter.woff2')})`, { weight: '100 900' }),
      new FontFace('JB Mono', `url(${staticFile('fonts/mono500.woff2')})`, { weight: '500' }),
      new FontFace('JB Mono', `url(${staticFile('fonts/mono700.woff2')})`, { weight: '700' })];
    Promise.all(fs.map((f) => f.load())).then((ls) => { ls.forEach((f) => document.fonts.add(f)); continueRender(h); });
  }, [h]);
  return null;
};

/** dark navy floor with an isometric grid that fades out, a slow parallax drift, film grain and a vignette */
export const Background: React.FC<{ t: number; cx?: number; cy?: number; tint?: string }> = ({ t, cx = 0, cy = 0, tint = COL.cyan }) => {
  const frame = useCurrentFrame();
  const lines: string[] = [];
  const G = 120, N = 16, ox = cx + (t * 6) % G, oy = cy + (t * 3) % G;
  for (let i = -N; i <= N; i++) {
    const a = P(i * G + ox, -N * G + oy), b = P(i * G + ox, N * G + oy);
    const c = P(-N * G + ox, i * G + oy), d = P(N * G + ox, i * G + oy);
    lines.push(`M${a[0]},${a[1]}L${b[0]},${b[1]}M${c[0]},${c[1]}L${d[0]},${d[1]}`);
  }
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ position: 'absolute', inset: 0 }}>
      <defs>
        <radialGradient id="bgG" cx="50%" cy="46%" r="75%">
          <stop offset="0" stopColor={COL.bg1} /><stop offset="1" stopColor={COL.bg0} />
        </radialGradient>
        <radialGradient id="gridM" cx="50%" cy="50%" r="50%">
          <stop offset="0" stopColor="#fff" stopOpacity="1" /><stop offset="0.7" stopColor="#fff" stopOpacity="0.35" /><stop offset="1" stopColor="#fff" stopOpacity="0" />
        </radialGradient>
        <mask id="gridMask"><rect x="-200" y="200" width={W + 400} height={H - 300} fill="url(#gridM)" /></mask>
        <radialGradient id="vig" cx="50%" cy="48%" r="72%">
          <stop offset="0.55" stopColor="#000" stopOpacity="0" /><stop offset="1" stopColor="#000" stopOpacity="0.75" />
        </radialGradient>
        <radialGradient id="pool" cx="50%" cy="50%" r="50%">
          <stop offset="0" stopColor={tint} stopOpacity="0.13" /><stop offset="1" stopColor={tint} stopOpacity="0" />
        </radialGradient>
      </defs>
      <rect width={W} height={H} fill="url(#bgG)" />
      <ellipse cx={W / 2} cy={H * 0.5} rx={620} ry={520} fill="url(#pool)" />
      <g mask="url(#gridMask)"><g transform={`translate(${W / 2},${H * 0.52})`}>
        <path d={lines.join('')} stroke={COL.grid} strokeWidth={1.3} opacity={0.42} fill="none" />
      </g></g>
      <rect width={W} height={H} fill="url(#vig)" />
      <g style={{ mixBlendMode: 'overlay' }} opacity={0.5}>
        <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed={frame % 24} /><feColorMatrix values="0 0 0 0 0.5  0 0 0 0 0.5  0 0 0 0 0.5  0 0 0 0.55 0" /></filter>
        <rect width={W} height={H} filter="url(#grain)" />
      </g>
    </svg>
  );
};

/** a full-frame SVG layer in world space: origin at (W/2, oy), with a camera zoom and pan */
export const Stage: React.FC<{ oy?: number; zoom?: number; px?: number; py?: number; children: React.ReactNode }> = ({ oy = 980, zoom = 1, px = 0, py = 0, children }) => (
  <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ position: 'absolute', inset: 0 }}>
    <Defs />
    <g transform={`translate(${W / 2 + px},${oy + py}) scale(${zoom})`}>{children}</g>
  </svg>
);

/** shows a scene between a and b with a cross-fade, a small push-in, and a slow drift */
export const Shot: React.FC<{ t: number; a: number; b: number; children: (lt: number, k: number) => React.ReactNode }> = ({ t, a, b, children }) => {
  if (t < a - 0.35 || t > b + 0.35) return null;
  const kin = eo((t - a + 0.35) / 0.5), kout = clamp((b + 0.35 - t) / 0.35);
  const op = Math.min(kin, kout), s = 0.965 + 0.035 * kin + 0.012 * clamp((t - a) / Math.max(1, b - a)) + 0.02 * (1 - kout);
  return (
    <div style={{ position: 'absolute', inset: 0, opacity: op, transform: `scale(${s})`, filter: kout < 1 ? `blur(${(1 - kout) * 6}px)` : undefined }}>
      {children(t - a, kin)}
    </div>
  );
};

// ---------- captions: chunks of up to 4 words in a dark pill; spoken words light up, keywords coloured ----------
const RED = new Set(['failed', 'nowhere', 'sleep', 'neither', 'should', 'nothing', 'happens', 'cancels', 'half', 'slowest', 'no']);
const GREEN = new Set(['commit', 'yes', 'both']);
type Tok = { s: string; t: number; star: boolean; pill: boolean; pc?: string };
const chunksFor = (tl: TL) => {
  const out: { a: number; b: number; toks: Tok[] }[] = [];
  tl.T.forEach((p, i) => {
    let star = false, pill = false;
    const raw = p.show.split(/\s+/).filter(Boolean);
    const toks: Tok[] = raw.map((r) => {
      const s0 = r.startsWith('*') || r.startsWith('['); if (r.startsWith('*')) star = true; if (r.startsWith('[')) pill = true;
      const tok = { s: r.replace(/[*[\]]/g, ''), t: 0, star, pill };
      if (/\*[.,?!:]*$/.test(r) && (!s0 || r.length > 1)) star = false;
      if (/\][.,?!:]*$/.test(r)) pill = false;
      return tok;
    });
    // one colour per [pill] run: red if it holds a failure word, green if a success word, else amber
    const base = (x: string) => x.toLowerCase().replace(/[^a-z%0-9]/g, '');
    for (let j = 0; j < toks.length; ) {
      if (!toks[j].pill) { j++; continue; }
      let e = j; while (e < toks.length && toks[e].pill) e++;
      const run = toks.slice(j, e).map((x) => base(x.s));
      const pc = run.some((x) => RED.has(x)) ? COL.red : run.some((x) => GREEN.has(x)) ? COL.green : COL.amber;
      for (let q = j; q < e; q++) toks[q].pc = pc;
      j = e;
    }
    const ws = tl.WORDS.filter(([, a]) => a >= p.start - 0.02 && a < p.end - 0.01);
    if (ws.length === toks.length) toks.forEach((k, j) => (k.t = ws[j][1]));
    else {
      const tot = toks.reduce((s, k) => s + k.s.length + 1, 0); let acc = 0;
      const a = ws.length ? ws[0][1] : p.start, b = ws.length ? ws[ws.length - 1][1] : p.end;
      toks.forEach((k) => { k.t = a + (b - a) * (acc / Math.max(1, tot - toks[toks.length - 1].s.length - 1)); acc += k.s.length + 1; });
    }
    const groups: Tok[][] = []; let g: Tok[] = [];
    toks.forEach((k, j) => {
      g.push(k);
      const len = g.reduce((s, x) => s + x.s.length + 1, 0);
      const left = toks.length - 1 - j, endP = /[.,?!:]$/.test(k.s);
      if (endP || j === toks.length - 1 || ((g.length >= 4 || len > 20) && left !== 1) || g.length >= 5) { groups.push(g); g = []; }
    });
    const next = tl.T[i + 1]?.start ?? p.end + 1.2;
    groups.forEach((gr, j) => {
      const a = gr[0].t - 0.1, b = j < groups.length - 1 ? groups[j + 1][0].t - 0.1 : Math.min(next - 0.12, p.end + 0.7);
      out.push({ a, b, toks: gr });
    });
  });
  return out;
};
let CH: ReturnType<typeof chunksFor> | null = null;
export const Captions: React.FC<{ t: number; tl: TL; y?: number }> = ({ t, tl, y = 1500 }) => {
  CH = CH || chunksFor(tl);
  const c = CH.find((x) => t >= x.a && t < x.b);
  if (!c) return null;
  const k = eo((t - c.a) / 0.16), out = clamp((c.b - t) / 0.1);
  return (
    <div style={{ position: 'absolute', left: 0, right: 0, top: y, display: 'flex', justifyContent: 'center', opacity: Math.min(k, out) }}>
      <div style={{ transform: `translateY(${(1 - k) * 14}px) scale(${0.94 + 0.06 * k})`, padding: '18px 32px 20px', borderRadius: 26,
        background: 'rgba(9,14,24,0.86)', border: '1.5px solid rgba(255,255,255,0.07)', boxShadow: '0 18px 50px rgba(0,0,0,0.55)',
        fontFamily: FONT, fontWeight: 800, fontSize: 54, letterSpacing: -1, color: COL.white, whiteSpace: 'nowrap', display: 'flex', gap: 15 }}>
        {c.toks.map((w, i) => {
          const on = t >= w.t - 0.04, kk = eo((t - w.t + 0.04) / 0.14);
          const col = w.pill ? w.pc! : w.star ? COL.cyan : COL.white;
          return (
            <span key={i} style={{ position: 'relative', color: col, opacity: on ? 0.32 + 0.68 * kk : 0.32 }}>
              {w.pill && <span style={{ position: 'absolute', inset: '-4px -10px', borderRadius: 12, background: col, opacity: 0.16 * (on ? kk : 0) }} />}
              <span style={{ position: 'relative', textShadow: on && (w.pill || w.star) ? `0 0 22px ${col}66` : undefined }}>{w.s}</span>
            </span>
          );
        })}
      </div>
    </div>
  );
};

// ---------- HUD: transaction status with the two legs, plus a segmented progress strip ----------
export type Leg = 'idle' | 'wait' | 'held' | 'ok' | 'fail' | 'cancel' | 'yes' | 'no';
const LEG: Record<Leg, [string, string]> = {
  idle: ['—', COL.dim], wait: ['ASKING', COL.mute], held: ['HELD', COL.amber], ok: ['BOOKED', COL.green], fail: ['FAILED', COL.red],
  cancel: ['CANCELLED', COL.mute], yes: ['YES', COL.green], no: ['NO', COL.red],
};
const Chip: React.FC<{ icon: string; label: string; st: Leg; since: number; t: number }> = ({ icon, label, st, since, t }) => {
  const [txt, col] = LEG[st]; const k = pop(t, since, 0.4);
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '12px 20px', borderRadius: 16, border: `1.5px solid ${col}55`,
      background: `linear-gradient(180deg, ${col}1c, ${col}08)`, boxShadow: st === 'idle' ? undefined : `0 0 24px ${col}33` }}>
      <svg width={38} height={38} viewBox="0 0 100 100"><path d={icon} fill="none" stroke={col} strokeWidth={7} strokeLinecap="round" strokeLinejoin="round" /></svg>
      <div style={{ fontFamily: MONO, fontSize: 21, lineHeight: 1.15 }}>
        <div style={{ color: COL.mute, fontWeight: 500, letterSpacing: 2 }}>{label}</div>
        <div style={{ color: col, fontWeight: 700, letterSpacing: 1.5, transform: `scale(${0.85 + 0.15 * k})`, transformOrigin: 'left center' }}>{txt}</div>
      </div>
    </div>
  );
};
export const Hud: React.FC<{ t: number; tl: TL; legs: { f: Leg; h: Leg; fs: number; hs: number }; op: number; icons: [string, string] }> = ({ t, tl, legs, op, icons }) => {
  const seg = tl.nLines;
  return (
    <div style={{ position: 'absolute', left: 60, right: 60, top: 150, opacity: op }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ fontFamily: MONO, fontWeight: 700, fontSize: 26, letterSpacing: 4, color: COL.white, lineHeight: 1.25 }}>
          TRANSACTION<br /><span style={{ color: COL.mute, fontWeight: 500, letterSpacing: 2, fontSize: 21 }}>#TRIP-4821</span>
        </div>
        <div style={{ display: 'flex', gap: 14 }}>
          <Chip icon={icons[0]} label="FLIGHT" st={legs.f} since={legs.fs} t={t} />
          <Chip icon={icons[1]} label="HOTEL" st={legs.h} since={legs.hs} t={t} />
        </div>
      </div>
      <div style={{ display: 'flex', gap: 6, marginTop: 22 }}>
        {Array.from({ length: seg }, (_, i) => {
          const a = tl.L(i), b = i + 1 < seg ? tl.L(i + 1) : tl.END - 1.5;
          const f = clamp((t - a) / (b - a));
          return <div key={i} style={{ flex: 1, height: 6, borderRadius: 3, background: '#1A2636', overflow: 'hidden' }}>
            <div style={{ width: `${f * 100}%`, height: '100%', background: COL.cyan, boxShadow: `0 0 10px ${COL.cyan}` }} /></div>;
        })}
      </div>
    </div>
  );
};

export const useT = () => useCurrentFrame() / FPS;
