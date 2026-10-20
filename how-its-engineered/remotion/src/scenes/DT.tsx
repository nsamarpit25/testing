// Reel 21: Distributed Transactions. Every scene is timed off the voiceover (phrase starts and whisper words).
import React from 'react';
import { AbsoluteFill, Audio, Sequence, staticFile } from 'remotion';
import T from '../data/timings.json';
import WORDS from '../data/words.json';
import { COL, FONT, MONO, FPS, clamp, eo, pr, pop, win, cmix, mix, makeTimeline, Phrase, Word } from '../lib/core';
import { P, Box, Cyl, Wire, Icon, ICON, onTop, onFront } from '../lib/iso';
import { Background, Stage, Shot, Captions, Hud, Fonts, useT, Leg } from '../lib/ui';
import { TwoPC, Board, Key } from './TwoPC';

const tl = makeTimeline(T as Phrase[], WORDS as unknown as Word[]);
const { L, LE, Wd, END } = tl;
export const DT_FRAMES = Math.ceil(END * FPS);

const tt = {
  checkout: Wd('checkout'), through: Wd('through'), failed: Wd('failed'), nowhere: Wd('nowhere'),
  succeed: Wd('succeed'), neither: Wd('neither'), distributed: Wd('distributed'),
  contract: Wd('contract'), bothSides: Wd('both', L(4)), signature: Wd('signature'), nothing: Wd('nothing'),
  steps: Wd('two', L(5)), phase: Wd('phase'),
  coord: Wd('coordinator'), asks: Wd('asks'), holds: Wd('holds'), yes1: Wd('yes', L(6, 1)),
  commit: Wd('commit', L(7)), anyone: L(7, 1), no2: Wd('no', L(7, 1)), cancels: Wd('cancels'),
  both8: Wd('both', L(8)), neither8: Wd('neither', L(8)), half: Wd('half'),
  slowest: Wd('slowest'), google: Wd('google'), pg: Wd('postgresql'), follow: Wd('follow'),
};

const Txt: React.FC<{ x: number; y: number; s?: number; col?: string; w?: number; ls?: number; op?: number; children: React.ReactNode }> = ({ x, y, s = 24, col = COL.mute, w = 700, ls = 4, op = 1, children }) => (
  <text x={x} y={y} textAnchor="middle" fontFamily={MONO} fontWeight={w} fontSize={s} letterSpacing={ls} fill={col} opacity={op}>{children}</text>
);

// ---------- 1. one checkout: flight ✓, hotel ✗ ----------
const Row: React.FC<{ y: number; icon: string; col: string; ok: number; bad: number; dx?: number }> = ({ y, icon, col, ok, bad, dx = 0 }) => (
  <g transform={`translate(${dx},0)`}>
    <rect x={16} y={y} width={272} height={116} rx={20} fill={col} fillOpacity={0.06 + 0.12 * (ok + bad)} stroke={col} strokeWidth={2.5} />
    <Icon n={icon} x={72} y={y + 58} s={64} col={col} w={6} />
    <rect x={124} y={y + 36} width={96} height={13} rx={6} fill={COL.white} opacity={0.75} />
    <rect x={124} y={y + 62} width={62} height={10} rx={5} fill={COL.mute} opacity={0.6} />
    <circle cx={252} cy={y + 58} r={21} fill={col} fillOpacity={0.15} stroke={col} strokeWidth={2.5} />
    {ok > 0 && <Icon n="check" x={252} y={y + 58} s={36} col={COL.green} w={11} draw={ok} />}
    {bad > 0 && <Icon n="cross" x={252} y={y + 58} s={28} col={COL.red} w={13} draw={bad} />}
  </g>
);
const Checkout: React.FC<{ t: number }> = ({ t }) => {
  const fOk = pr(t, tt.through, 0.35), hBad = pr(t, tt.failed, 0.3);
  const shake = Math.sin((t - tt.failed) * 70) * 9 * win(t, tt.failed, tt.failed + 0.45, 0.05);
  const press = win(t, tt.checkout - 0.05, tt.checkout + 0.3, 0.08);
  const x0 = -170, y0 = -300, h = 26;
  const fc = cmix(COL.cyan, COL.green, fOk), hc = cmix(COL.cyan, COL.red, hBad);
  return (
    <Stage oy={940} zoom={1.1 + 0.05 * clamp(t / 5)}>
      <Box x={x0} y={y0} w={340} d={600} h={h} col={hBad > 0.5 ? cmix(COL.cyan, COL.red, 0.35 * win(t, tt.failed, tt.failed + 0.6, 0.1)) : COL.cyan} draw={pr(t, -0.3, 0.7)} top="#0B121C">
        <g transform={onTop(x0 + 18, y0 + 18, h)}>
          <rect x={0} y={0} width={304} height={564} rx={26} fill="#060B12" stroke={COL.cyan} strokeOpacity={0.35} strokeWidth={2} />
          <rect x={24} y={30} width={130} height={15} rx={7} fill={COL.white} opacity={0.8} />
          <rect x={24} y={56} width={74} height={10} rx={5} fill={COL.mute} opacity={0.6} />
          <Icon n="cart" x={260} y={48} s={42} col={COL.cyan} w={7} />
          <Row y={96} icon="plane" col={fc} ok={fOk} bad={0} />
          <Row y={232} icon="bed" col={hc} ok={0} bad={hBad} dx={shake} />
          <rect x={24} y={384} width={90} height={12} rx={6} fill={COL.mute} opacity={0.6} />
          <rect x={196} y={380} width={84} height={20} rx={10} fill={COL.white} opacity={0.85} />
          <rect x={20} y={450} width={264} height={80} rx={22} fill={COL.cyan} fillOpacity={0.14 + 0.45 * press} stroke={COL.cyan} strokeWidth={2.5} />
          <rect x={112} y={483} width={80} height={14} rx={7} fill={COL.cyan} />
        </g>
      </Box>
      {/* tap ripple on Pay */}
      {(() => { const [x, y] = P(x0 + 18 + 152, y0 + 18 + 490, h); const u = clamp((t - tt.checkout + 0.05) / 0.6);
        return u > 0 && u < 1 ? <ellipse cx={x} cy={y} rx={30 + 90 * u} ry={(30 + 90 * u) * 0.58} fill="none" stroke={COL.cyan} strokeWidth={3} opacity={1 - u} /> : null; })()}
    </Stage>
  );
};

// ---------- 2. a boarding pass, and no bed ----------
const Stranded: React.FC<{ t: number }> = ({ t }) => {
  const a = L(1), k1 = pr(t, a - 0.25, 0.7), k2 = pr(t, a + 0.1, 0.7), fl = Math.sin(t * 2.2) * 7;
  const flick = 0.45 + 0.55 * Math.abs(Math.sin(t * 6.1) * Math.sin(t * 2.3 + 1));
  const tx = -259, ty = -46, bx = 30, by = -320;
  const [cx, cy] = P(bx + 100, by + 150, 190 + fl);
  const xk = pr(t, tt.nowhere, 0.45);
  return (
    <Stage oy={960} zoom={1.0} px={-40}>
      <Box x={tx} y={ty} z={26 + fl} w={150} d={300} h={8} col={COL.green} draw={k1} top="#0D1A17">
        <g transform={onTop(tx, ty, 34 + fl)}>
          <Icon n="plane" x={75} y={62} s={70} col={COL.green} w={6} />
          <line x1={10} y1={124} x2={140} y2={124} stroke={COL.green} strokeWidth={2} strokeDasharray="6 7" opacity={0.7} />
          <rect x={22} y={146} width={70} height={11} rx={5} fill={COL.white} opacity={0.75} />
          <rect x={22} y={168} width={46} height={9} rx={4} fill={COL.mute} opacity={0.6} />
          {Array.from({ length: 16 }, (_, i) => <rect key={i} x={22 + i * 6.8} y={222} width={i % 3 ? 2.4 : 4.4} height={52} fill={COL.green} opacity={0.8} />)}
        </g>
      </Box>
      <g opacity={flick * k2}>
        <Box x={bx} y={by - 4} w={200} d={20} h={120} col={COL.red} draw={k2} glow={0.5} />
        <Box x={bx} y={by} w={200} d={300} h={36} col={COL.red} draw={k2} glow={0.6} />
        <Box x={bx + 12} y={by + 12} z={36} w={176} d={276} h={20} col={COL.red} draw={k2} glow={0.4} shadow={false} />
        <Box x={bx + 26} y={by + 22} z={56} w={148} d={60} h={14} col={COL.red} draw={k2} glow={0.4} shadow={false} />
      </g>
      <g opacity={xk}>
        <circle cx={cx} cy={cy} r={58 * (0.7 + 0.3 * pop(t, tt.nowhere))} fill={COL.red} opacity={0.14} />
        <circle cx={cx} cy={cy} r={58 * (0.7 + 0.3 * pop(t, tt.nowhere))} fill="none" stroke={COL.red} strokeWidth={3} />
        <Icon n="cross" x={cx} y={cy} s={60} col={COL.red} w={11} draw={xk} />
      </g>
      {(() => { const [x, y] = P(tx + 150, ty + 300, 0); return <Txt x={x - 40} y={y + 70} col={COL.green} op={k1}>PAID</Txt>; })()}
      {(() => { const [x, y] = P(bx + 200, by + 300, 0); return <Txt x={x - 50} y={y + 70} col={COL.red} op={k2}>NO ROOM</Txt>; })()}
    </Stage>
  );
};

// ---------- 3–4. two services, two databases → one distributed transaction ----------
const Group: React.FC<{ cx: number; cy: number; icon: string; label: string; col: string; k: number; t: number }> = ({ cx, cy, icon, label, col, k, t }) => {
  const rx = cx - 95, ry = cy - 70, [lx, ly] = P(cx + 120, cy + 120, 0);
  return (
    <g>
      <Box x={cx - 120} y={cy - 120} w={240} d={240} h={14} col={col} draw={k} glow={0.5} />
      <Box x={rx} y={ry} z={14} w={100} d={120} h={210} col={col} draw={k} shadow={false}>
        <g transform={onTop(rx, ry, 224)}><Icon n={icon} x={50} y={60} s={70} col={col} w={6} /></g>
        <g transform={onFront(rx, ry + 120, 224)}>
          {Array.from({ length: 6 }, (_, i) => <g key={i}>
            <rect x={12} y={16 + i * 31} width={76} height={17} rx={3} fill="none" stroke={col} strokeOpacity={0.5} strokeWidth={1.5} />
            <circle cx={78} cy={24.5 + i * 31} r={3.2} fill={col} opacity={(Math.floor(t * 5 + i * 2.3 + cx) % 4) === 0 ? 1 : 0.35} />
          </g>)}
        </g>
      </Box>
      <Cyl cx={cx + 58} cy={cy + 52} z={14} r={40} h={104} col={col} fill={0.6} />
      <Txt x={lx - 120} y={ly + 64} col={col} op={k} s={26}>{label}</Txt>
    </g>
  );
};
const Services: React.FC<{ t: number }> = ({ t }) => {
  const a = L(2), k1 = pr(t, a - 0.2, 0.8), k2 = pr(t, Wd('two', a + 0.6) - 0.2, 0.8);
  const back = pr(t, L(3) - 0.1, 0.9);
  let col = t < tt.neither ? cmix(COL.cyan, COL.green, win(t, tt.succeed, tt.neither - 0.05, 0.25)) : cmix(COL.cyan, COL.dim, pr(t, tt.neither, 0.3));
  col = cmix(col, COL.cyan, back);
  const ring = pr(t, tt.distributed - 0.1, 1.0);
  const pts = [[-280, -280], [320, -280], [320, 320], [-280, 320]].map(([x, y]) => P(x, y, 0).join(',')).join(' ');
  const [chx, chy] = P(-280, -280, 0);
  return (
    <>
      <Stage oy={960} zoom={1.06 - 0.2 * back} py={150 * back}>
        <Wire a={[-175, 160, 224]} b={[125, -140, 224]} mid={330} col={col} draw={pr(t, tt.succeed - 0.6, 0.8)} flow={t} w={2.5} />
        <Group cx={-130} cy={170} icon="plane" label="FLIGHTS" col={col} k={k1} t={t} />
        <Group cx={170} cy={-130} icon="bed" label="HOTELS" col={col} k={k2} t={t} />
        {ring > 0 && <g>
          <polygon points={pts} fill={COL.cyan} fillOpacity={0.04 * ring} stroke={COL.cyan} strokeWidth={3} strokeDasharray="14 12" opacity={ring} />
          <polygon points={pts} fill="none" stroke={COL.cyan} strokeWidth={10} opacity={0.25 * ring} filter="url(#halo)" />
          <g transform={`translate(${chx},${chy - 36}) scale(${0.7 + 0.3 * pop(t, tt.distributed + 0.3)})`} opacity={pr(t, tt.distributed + 0.3, 0.3)}>
            <rect x={-150} y={-26} width={300} height={52} rx={14} fill="#0A111B" stroke={COL.cyan} strokeWidth={2.4} />
            <text y={9} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={22} letterSpacing={3} fill={COL.cyan}>ONE TRANSACTION</text>
          </g>
        </g>}
      </Stage>
      <BigTitle t={t} at={tt.distributed - 0.15} lines={['distributed', 'transaction']} />
    </>
  );
};

const BigTitle: React.FC<{ t: number; at: number; lines: string[]; y?: number; col?: string }> = ({ t, at, lines, y = 300, col = COL.cyan }) => (
  <div style={{ position: 'absolute', left: 70, top: y, fontFamily: FONT, fontWeight: 900, fontSize: 124, lineHeight: 0.98, letterSpacing: -5 }}>
    {lines.map((s, i) => {
      const k = eo((t - at - i * 0.14) / 0.5);
      return <div key={i} style={{ overflow: 'hidden', paddingBottom: 8 }}>
        <div style={{ transform: `translateY(${(1 - k) * 110}%)`, color: i ? col : COL.white, textShadow: i ? `0 0 40px ${col}55` : undefined }}>{s}</div>
      </div>;
    })}
  </div>
);

// ---------- 5. a contract needs both signatures ----------
const SIG_A = 'M50 492 C60 452 78 450 74 476 C70 502 94 472 106 462 C114 456 110 488 122 482 C134 476 142 462 164 472';
const SIG_B = 'M236 490 C246 456 264 452 260 476 C256 498 278 470 292 462 C302 458 300 484 314 480 C328 476 336 464 356 470';
const Contract: React.FC<{ t: number }> = ({ t }) => {
  const k = pr(t, L(4) - 0.25, 0.8), slot = win(t, tt.bothSides - 0.1, tt.signature, 0.2);
  const sA = pr(t, tt.signature - 0.1, 0.9), bad = win(t, tt.nothing - 0.05, LE(4, 1) + 0.15, 0.15);
  const sB = pr(t, LE(4, 1) + 0.02, 0.5), ok = pop(t, LE(4, 1) + 0.45, 0.45);
  const x0 = -200, y0 = -290, h = 6;
  const sealCol = ok > 0 ? COL.green : bad > 0 ? COL.red : COL.dim;
  return (
    <Stage oy={940} zoom={1.04 + 0.04 * clamp((t - L(4)) / 6)}>
      <Box x={x0} y={y0} w={400} d={580} h={h} col={ok > 0 ? cmix(COL.cyan, COL.green, ok) : COL.cyan} draw={k} top="#141E2C">
        <g transform={onTop(x0, y0, h)}>
          <rect x={40} y={40} width={210} height={22} rx={6} fill={COL.white} opacity={0.85} />
          <rect x={40} y={74} width={120} height={12} rx={6} fill={COL.mute} opacity={0.7} />
          {Array.from({ length: 8 }, (_, i) => <rect key={i} x={40} y={124 + i * 30} width={320 - (i % 3) * 46} height={9} rx={4.5} fill={COL.mute} opacity={0.42} />)}
          {[[40, 175, 'plane'], [225, 360, 'bed']].map(([a, b, ic], i) => (
            <g key={i}>
              <line x1={a as number} y1={500} x2={b as number} y2={500} stroke={cmix(COL.mute, COL.amber, slot)} strokeWidth={2.5 + 2 * slot} />
              <Icon n={ic as string} x={((a as number) + (b as number)) / 2} y={534} s={30} col={COL.mute} w={7} />
            </g>
          ))}
          <path d={SIG_A} fill="none" stroke={COL.cyan} strokeWidth={4.5} strokeLinecap="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - sA} />
          <path d={SIG_B} fill="none" stroke={COL.cyan} strokeWidth={4.5} strokeLinecap="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - sB} />
          <g transform="translate(320,96)">
            <circle r={50} fill={sealCol} fillOpacity={0.1 + 0.1 * ok} stroke={sealCol} strokeWidth={3} strokeDasharray={ok > 0 ? undefined : '8 7'} />
            {bad > 0 && ok <= 0 && <Icon n="cross" x={0} y={0} s={46} col={COL.red} w={10} op={bad} />}
            {ok > 0 && <Icon n="check" x={0} y={0} s={56} col={COL.green} w={11} draw={ok} />}
          </g>
        </g>
      </Box>
      {(() => { const [x, y] = P(x0 + 400, y0 + 580, 0); return <Txt x={x - 20} y={y + 72} col={ok > 0 ? COL.green : bad > 0 ? COL.red : COL.mute} op={k} s={26}>{ok > 0 ? 'SIGNED · VALID' : bad > 0 ? '1 OF 2 · NOT VALID' : 'CONTRACT'}</Txt>; })()}
    </Stage>
  );
};

// ---------- 6. two-phase commit: two steps ----------
const Steps: React.FC<{ t: number }> = ({ t }) => {
  const cards = [['01', 'PREPARE', 'Can you do it?', COL.amber, tt.steps - 0.1], ['02', 'COMMIT', 'Then everyone does.', COL.green, tt.steps + 0.25]] as const;
  return (
    <>
      <BigTitle t={t} at={tt.phase - 0.35} lines={['two-phase', 'commit']} y={330} col={COL.amber} />
      <div style={{ position: 'absolute', left: 70, right: 70, top: 690, display: 'flex', flexDirection: 'column', gap: 30 }}>
        {cards.map(([n, h, s, c, at], i) => {
          const k = pop(t, at, 0.55);
          return <div key={i} style={{ opacity: clamp(k), transform: `translateX(${(1 - k) * -80}px)`, display: 'flex', alignItems: 'center', gap: 34, padding: '34px 40px',
            borderRadius: 30, background: `linear-gradient(135deg, ${c}1f, #0B121C 60%)`, border: `2px solid ${c}66`, boxShadow: `0 0 50px ${c}22, 0 30px 60px rgba(0,0,0,0.5)` }}>
            <div style={{ fontFamily: MONO, fontWeight: 700, fontSize: 64, color: c, textShadow: `0 0 26px ${c}88` }}>{n}</div>
            <div>
              <div style={{ fontFamily: MONO, fontWeight: 700, fontSize: 46, letterSpacing: 6, color: COL.white }}>{h}</div>
              <div style={{ fontFamily: FONT, fontWeight: 600, fontSize: 34, color: COL.mute, marginTop: 6 }}>{s}</div>
            </div>
          </div>;
        })}
      </div>
    </>
  );
};

// ---------- 7–8. the board: prepare → hold → yes → commit; then a NO → abort ----------
const A = COL.amber, G = COL.green, R = COL.red, Cn = COL.cyan, D = COL.dim;
const boardMain: Board = {
  appear: L(6) - 0.3,
  cC: [[0, Cn], [tt.yes1 + 0.95, G], [tt.anyone, Cn], [tt.no2 + 0.45, R], [tt.cancels + 0.5, D]],
  cF: [[0, Cn], [tt.holds, A], [tt.commit + 0.6, G], [tt.anyone, A], [tt.cancels + 0.5, D]],
  cH: [[0, Cn], [tt.holds + 0.12, A], [tt.commit + 0.6, G], [tt.anyone, A], [tt.no2, R], [tt.cancels + 0.5, D]],
  iF: [[0, ['', '']], [tt.holds, ['lock', A]], [tt.commit + 0.6, ['check', G]], [tt.anyone, ['lock', A]], [tt.cancels + 0.5, ['unlock', COL.mute]]],
  iH: [[0, ['', '']], [tt.holds + 0.12, ['lock', A]], [tt.commit + 0.6, ['check', G]], [tt.anyone, ['lock', A]], [tt.no2, ['cross', R]], [tt.cancels + 0.5, ['unlock', COL.mute]]],
  packets: [
    { from: 'c', to: 'f', t0: tt.asks, dur: 0.9, label: 'PREPARE?', col: A }, { from: 'c', to: 'h', t0: tt.asks + 0.1, dur: 0.9, label: 'PREPARE?', col: A },
    { from: 'f', to: 'c', t0: tt.yes1 - 0.1, dur: 0.8, label: 'YES', col: G }, { from: 'h', to: 'c', t0: tt.yes1 + 0.08, dur: 0.8, label: 'YES', col: G },
    { from: 'c', to: 'f', t0: tt.commit - 0.15, dur: 0.7, label: 'COMMIT', col: G }, { from: 'c', to: 'h', t0: tt.commit - 0.05, dur: 0.7, label: 'COMMIT', col: G },
    { from: 'f', to: 'c', t0: tt.no2 - 0.5, dur: 0.7, label: 'YES', col: G }, { from: 'h', to: 'c', t0: tt.no2 - 0.25, dur: 0.7, label: 'NO', col: R },
    { from: 'c', to: 'f', t0: tt.cancels - 0.2, dur: 0.65, label: 'ABORT', col: R }, { from: 'c', to: 'h', t0: tt.cancels - 0.1, dur: 0.65, label: 'ABORT', col: R },
  ],
};
const Board1: React.FC<{ t: number }> = ({ t }) => {
  const rw = win(t, tt.anyone - 0.15, tt.anyone + 0.2, 0.12);   // quick "rewind" flash between the two endings
  return (
    <Stage oy={1010} zoom={1.1 + 0.04 * clamp((t - L(6)) / 14)}>
      <g opacity={1 - 0.55 * rw}><TwoPC t={t} b={boardMain} /></g>
      {rw > 0 && <text x={0} y={-470} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={30} letterSpacing={6} fill={COL.mute} opacity={rw}>◀◀ REPLAY</text>}
    </Stage>
  );
};

// ---------- 9. both, neither — never half ----------
const Outcomes: React.FC<{ t: number }> = ({ t }) => {
  const items = [
    { at: tt.both8 - 0.1, col: G, marks: ['check', 'check'], mc: [G, G], label: 'BOTH', tag: 'OK' },
    { at: tt.neither8 - 0.1, col: COL.mute, marks: ['cross', 'cross'], mc: [COL.mute, COL.mute], label: 'NEITHER', tag: 'OK' },
    { at: tt.half - 0.1, col: R, marks: ['check', 'cross'], mc: [G, R], label: 'HALF', tag: 'NEVER' },
  ];
  return (
    <Stage oy={1000} zoom={1.05}>
      {items.map((it, i) => {
        const X = (i - 1) * 345, cx = X / (2 * 0.8660254), cy = -cx;
        const k = pr(t, it.at, 0.6), p = pop(t, it.at, 0.55);
        const sh = i === 2 ? Math.sin((t - it.at) * 60) * 8 * win(t, it.at + 0.35, it.at + 0.8, 0.05) : 0;
        const fl = Math.sin(t * 2 + i) * 5;
        const [tx, ty] = P(cx, cy, 120 + fl);
        const strike = pr(t, it.at + 0.35, 0.3);
        return <g key={i} opacity={clamp(k * 1.5)} transform={`translate(${sh},0)`}>
          <Box x={cx - 85} y={cy - 85} w={170} d={170} h={18} col={it.col} draw={k} glow={0.8} />
          {it.marks.map((m, j) => {
            const ix = tx + (j ? 52 : -52), iy = ty - 30 + (1 - p) * 30;
            return <g key={j} opacity={clamp(p)}>
              <Icon n={j ? 'bed' : 'plane'} x={ix} y={iy - 40} s={62} col={it.col} w={6} />
              <circle cx={ix} cy={iy + 36} r={20} fill={it.mc[j]} fillOpacity={0.15} stroke={it.mc[j]} strokeWidth={2.4} />
              <Icon n={m} x={ix} y={iy + 36} s={26} col={it.mc[j]} w={13} draw={pr(t, it.at + 0.15 + j * 0.1, 0.3)} />
            </g>;
          })}
          {(() => { const [lx, ly] = P(cx + 85, cy + 85, 0); return <g>
            <Txt x={lx} y={ly + 64} col={it.col} s={30} op={k}>{it.label}</Txt>
            <Txt x={lx} y={ly + 104} col={i === 2 ? R : COL.mute} s={20} op={k * 0.9}>{it.tag}</Txt>
            {i === 2 && <line x1={lx - 80} y1={ly + 54} x2={lx - 80 + 160 * strike} y2={ly + 54} stroke={R} strokeWidth={5} strokeLinecap="round" />}
          </g>; })()}
        </g>;
      })}
    </Stage>
  );
};

// ---------- 10. the catch: everyone waits for the slowest ----------
const a9 = L(9);
const boardSlow: Board = {
  appear: a9 - 0.6, timer: a9 + 0.2, spinH: [a9 + 0.3, END],
  cC: [[0, Cn], [a9 + 0.2, A]], cF: [[0, A]], cH: [[0, A], [tt.slowest - 0.1, cmix(A, R, 0.6)]],
  iF: [[0, ['lock', A]]], iH: [[0, ['', '']]],
  packets: [{ from: 'f', to: 'c', t0: a9 - 0.1, dur: 0.6, label: 'YES', col: G }],
};
const Catch: React.FC<{ t: number }> = ({ t }) => (
  <Stage oy={1030} zoom={1.08 + 0.05 * clamp((t - a9) / 3)}><TwoPC t={t} b={boardSlow} /></Stage>
);

// ---------- 11. in the real world ----------
const PG = ["BEGIN;", "UPDATE seats SET held = true;", "PREPARE TRANSACTION 'trip_4821';", "COMMIT PREPARED 'trip_4821';"];
const RealWorld: React.FC<{ t: number }> = ({ t }) => {
  const k1 = pop(t, tt.google - 0.2, 0.6), k2 = pop(t, tt.pg - 0.25, 0.6);
  let chars = Math.max(0, (t - tt.pg) * 34);
  return (
    <div style={{ position: 'absolute', left: 70, right: 70, top: 470, display: 'flex', flexDirection: 'column', gap: 40 }}>
      <div style={{ opacity: clamp(k1), transform: `translateY(${(1 - k1) * 60}px)`, display: 'flex', alignItems: 'center', gap: 36, padding: '40px 44px', borderRadius: 32,
        background: 'linear-gradient(135deg, #12223A, #0A111B 70%)', border: `2px solid ${COL.cyan}55`, boxShadow: `0 0 60px ${COL.cyan}1f, 0 30px 70px rgba(0,0,0,0.55)` }}>
        <svg width={130} height={130} viewBox="0 0 100 100">
          <circle cx={50} cy={50} r={40} fill="none" stroke={COL.cyan} strokeWidth={3.5} />
          <ellipse cx={50} cy={50} rx={17} ry={40} fill="none" stroke={COL.cyan} strokeWidth={2.5} transform={`rotate(${t * 20} 50 50)`} opacity={0.8} />
          <path d="M12 38 H88 M12 62 H88" stroke={COL.cyan} strokeWidth={2.5} opacity={0.7} />
          {[[30, 30], [70, 36], [44, 70], [66, 64]].map(([x, y], i) => <circle key={i} cx={x} cy={y} r={5} fill={COL.amber} opacity={0.5 + 0.5 * Math.abs(Math.sin(t * 3 + i))} />)}
        </svg>
        <div>
          <div style={{ fontFamily: FONT, fontWeight: 800, fontSize: 60, letterSpacing: -1.5, color: COL.white }}>Google Spanner</div>
          <div style={{ fontFamily: MONO, fontWeight: 500, fontSize: 26, color: COL.cyan, marginTop: 8, letterSpacing: 1 }}>2-phase commit across shards</div>
        </div>
      </div>
      <div style={{ opacity: clamp(k2), transform: `translateY(${(1 - k2) * 60}px)`, borderRadius: 32, overflow: 'hidden', background: '#070C14',
        border: `2px solid ${COL.amber}55`, boxShadow: `0 0 60px ${COL.amber}1a, 0 30px 70px rgba(0,0,0,0.55)` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '22px 30px', background: '#0E1622', borderBottom: '1.5px solid #1C2A3C' }}>
          {[COL.red, COL.amber, COL.green].map((c, i) => <div key={i} style={{ width: 16, height: 16, borderRadius: 8, background: c, opacity: 0.8 }} />)}
          <div style={{ fontFamily: MONO, fontWeight: 700, fontSize: 24, color: COL.mute, marginLeft: 16, letterSpacing: 2 }}>PostgreSQL · psql</div>
        </div>
        <div style={{ padding: '30px 34px 36px', fontFamily: MONO, fontWeight: 500, fontSize: 29, lineHeight: 1.7, minHeight: 230 }}>
          {PG.map((ln, i) => {
            const n = clamp(chars, 0, ln.length); chars -= ln.length + 3;
            const hot = /PREPARE/.test(ln);
            return <div key={i} style={{ color: hot ? COL.amber : '#B9C6D8', whiteSpace: 'pre' }}>
              <span style={{ color: COL.dim }}>{'> '}</span>{ln.slice(0, Math.floor(n))}
              {n > 0 && n < ln.length && <span style={{ background: COL.amber, color: '#000' }}> </span>}
            </div>;
          })}
        </div>
      </div>
    </div>
  );
};

// ---------- 12. follow card ----------
const Follow: React.FC<{ t: number }> = ({ t }) => {
  const a = L(11), k = pop(t, a - 0.2, 0.7), clicked = t >= tt.follow + 0.05;
  const cur = eo((t - (tt.follow - 0.75)) / 0.6), press = win(t, tt.follow - 0.05, tt.follow + 0.12, 0.05);
  const tiles = [['CANARY', 'RELEASES', COL.amber], ['EVENT', 'DRIVEN', COL.cyan], ['PUB', 'SUB', COL.green]];
  return (
    <div style={{ position: 'absolute', left: 70, right: 70, top: 520, opacity: clamp(k), transform: `scale(${0.9 + 0.1 * k})` }}>
      <div style={{ padding: 44, borderRadius: 36, background: 'linear-gradient(160deg, #13203A, #0A111B 65%)', border: '2px solid #22324A', boxShadow: '0 40px 90px rgba(0,0,0,0.6)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 30 }}>
          <div style={{ width: 132, height: 132, borderRadius: 66, background: 'radial-gradient(circle at 35% 30%, #1E3A5C, #0A111B)', border: `3px solid ${COL.cyan}`, boxShadow: `0 0 34px ${COL.cyan}55`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg width={76} height={76} viewBox="-50 -50 100 100"><path d="M0 -38 L33 -19 L33 19 L0 38 L-33 19 L-33 -19 Z M0 -38 L0 0 M0 0 L33 19 M0 0 L-33 19" fill="none" stroke={COL.cyan} strokeWidth={5} strokeLinejoin="round" /></svg>
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontFamily: FONT, fontWeight: 800, fontSize: 48, color: COL.white, letterSpacing: -1 }}>how.its.engineered</div>
            <div style={{ fontFamily: FONT, fontWeight: 500, fontSize: 30, color: COL.mute, marginTop: 6 }}>System design your AI skipped</div>
          </div>
        </div>
        <div style={{ marginTop: 36, height: 92, borderRadius: 22, display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `scale(${1 - 0.05 * press})`,
          background: clicked ? '#1C2A3C' : COL.cyan, color: clicked ? COL.white : '#04121A', fontFamily: FONT, fontWeight: 800, fontSize: 38,
          boxShadow: clicked ? undefined : `0 0 40px ${COL.cyan}66` }}>{clicked ? 'Following ✓' : 'Follow'}</div>
        <div style={{ display: 'flex', gap: 18, marginTop: 34 }}>
          {tiles.map(([a1, b1, c], i) => <div key={i} style={{ flex: 1, height: 190, borderRadius: 20, border: `2px solid ${c}55`, background: `linear-gradient(180deg, ${c}18, #0A111B)`,
            display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', padding: 18, opacity: clamp(pop(t, a + 0.3 + i * 0.12, 0.5)) }}>
            <div style={{ fontFamily: MONO, fontWeight: 700, fontSize: 22, letterSpacing: 2, color: c, lineHeight: 1.3 }}>{a1}<br />{b1}</div>
          </div>)}
        </div>
      </div>
      <svg width={70} height={70} viewBox="0 0 24 24" style={{ position: 'absolute', left: 640 - 260 * cur, top: 700 - 330 * cur + 0, opacity: clamp(cur * 3), transform: `scale(${1 - 0.15 * press})` }}>
        <path d="M4 2 L4 19 L8.5 15 L11.5 22 L14.5 20.7 L11.5 14 L17.5 14 Z" fill="#fff" stroke="#000" strokeWidth={1.2} strokeLinejoin="round" />
      </svg>
    </div>
  );
};

// ---------- HUD legs ----------
const legKeys: { f: Key<Leg>[]; h: Key<Leg>[] } = {
  f: [[0, 'idle'], [tt.checkout, 'wait'], [tt.through, 'ok'], [L(3), 'idle'], [tt.asks + 0.6, 'wait'], [tt.holds, 'held'], [tt.yes1 + 0.1, 'yes'], [tt.commit + 0.6, 'ok'],
    [tt.anyone, 'held'], [tt.no2 - 0.3, 'yes'], [tt.cancels + 0.5, 'cancel'], [tt.both8, 'ok'], [tt.neither8, 'idle'], [tt.half, 'ok'], [L(9), 'held'], [L(9) + 0.1, 'yes']],
  h: [[0, 'idle'], [tt.checkout, 'wait'], [tt.failed, 'fail'], [L(3), 'idle'], [tt.asks + 0.6, 'wait'], [tt.holds + 0.12, 'held'], [tt.yes1 + 0.3, 'yes'], [tt.commit + 0.6, 'ok'],
    [tt.anyone, 'held'], [tt.no2, 'no'], [tt.cancels + 0.5, 'cancel'], [tt.both8, 'ok'], [tt.neither8, 'idle'], [tt.half, 'fail'], [L(9), 'wait']],
};
const leg = (k: Key<Leg>[], t: number): [Leg, number] => { let i = 0; k.forEach(([a], j) => { if (a <= t) i = j; }); return [k[i][1], k[i][0]]; };

// ---------- sound design: synthesized UI cues under the voice ----------
const CUES: [number, string, number][] = (() => {
  const c: [number, string, number][] = [];
  [L(1), L(2), L(4), L(5) + 0.3, L(6), L(8), L(9), L(10), L(11)].forEach((a) => c.push([a - 0.3, 'whoosh', 0.35]));
  c.push([tt.checkout, 'tap', 0.6], [tt.through, 'ok', 0.5], [tt.failed, 'err', 0.55], [tt.nowhere, 'err', 0.3]);
  c.push([Wd('two', L(2) + 0.6) - 0.2, 'pop', 0.4], [tt.succeed, 'ok3', 0.4], [tt.neither, 'tick', 0.5], [tt.distributed - 1.0, 'rise', 0.5], [tt.distributed + 0.3, 'pop', 0.5]);
  c.push([tt.bothSides, 'tick', 0.5], [tt.nothing, 'err', 0.4], [LE(4, 1) + 0.45, 'ok3', 0.5]);
  c.push([tt.steps - 0.1, 'pop', 0.5], [tt.steps + 0.25, 'pop', 0.5]);
  c.push([tt.coord, 'pop', 0.45], [tt.asks, 'tick', 0.5], [tt.asks + 0.1, 'tick', 0.4], [tt.holds, 'lock', 0.55], [tt.holds + 0.12, 'lock', 0.45]);
  c.push([tt.yes1 + 0.6, 'tick', 0.4], [tt.yes1 + 0.95, 'ok', 0.45], [tt.commit - 0.15, 'tick', 0.45], [tt.commit + 0.6, 'ok3', 0.55]);
  c.push([tt.anyone - 0.15, 'whoosh', 0.3], [tt.no2 - 0.25, 'tick', 0.4], [tt.no2 + 0.45, 'err', 0.5], [tt.cancels + 0.5, 'err', 0.4], [tt.cancels + 0.5, 'lock', 0.4]);
  c.push([tt.both8, 'pop', 0.45], [tt.both8 + 0.2, 'ok', 0.4], [tt.neither8, 'pop', 0.45], [tt.half, 'pop', 0.45], [tt.half + 0.35, 'err', 0.5]);
  c.push([a9 - 0.1, 'tick', 0.4], [a9 + 0.5, 'tick', 0.4], [tt.slowest - 0.1, 'err', 0.3]);
  c.push([tt.google - 0.2, 'pop', 0.45], [tt.pg - 0.25, 'pop', 0.45]);
  const total = PG.reduce((s, l) => s + l.length, 0);
  for (let i = 0; i < total; i += 3) c.push([tt.pg + i / 34, `key${(i / 3) % 4}`, 0.55]);
  c.push([tt.follow, 'tap', 0.6], [tt.follow + 0.1, 'ok', 0.45]);
  return c.filter(([a]) => a > 0);
})();
const Sfx: React.FC = () => <>{CUES.map(([a, n, v], i) => (
  <Sequence key={i} from={Math.round(a * FPS)} durationInFrames={Math.round(1.6 * FPS)} layout="none"><Audio src={staticFile(`sfx/${n}.wav`)} volume={v} /></Sequence>
))}</>;

export const DT: React.FC = () => {
  const t = useT();
  const [f, fs] = leg(legKeys.f, t), [h, hs] = leg(legKeys.h, t);
  const S = (a: number, b: number, el: (lt: number) => React.ReactNode) => <Shot t={t} a={a} b={b}>{() => el(t)}</Shot>;
  return (
    <AbsoluteFill style={{ background: COL.bg0 }}>
      <Fonts />
      <Background t={t} tint={t > tt.failed && t < L(2) ? COL.red : COL.cyan} />
      {S(-0.5, L(1), (x) => <Checkout t={x} />)}
      {S(L(1), L(2), (x) => <Stranded t={x} />)}
      {S(L(2), L(4), (x) => <Services t={x} />)}
      {S(L(4), L(5) + 0.3, (x) => <Contract t={x} />)}
      {S(L(5) + 0.3, L(6), (x) => <Steps t={x} />)}
      {S(L(6), L(8), (x) => <Board1 t={x} />)}
      {S(L(8), L(9), (x) => <Outcomes t={x} />)}
      {S(L(9), L(10), (x) => <Catch t={x} />)}
      {S(L(10), L(11), (x) => <RealWorld t={x} />)}
      {S(L(11), END + 1, (x) => <Follow t={x} />)}
      <Hud t={t} tl={tl} legs={{ f, h, fs, hs }} op={1 - clamp((t - L(10) + 0.3) / 0.4)} icons={[ICON.plane, ICON.bed]} />
      <Captions t={t} tl={tl} y={1440} />
      <Audio src={staticFile('dt/voice.wav')} />
      <Sfx />
    </AbsoluteFill>
  );
};
