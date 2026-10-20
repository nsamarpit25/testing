// The two-phase commit board: a coordinator above two services (flights, hotels), floor cables, and message chips
// travelling between them. Colours and icons follow keyframe lists so the same board plays the happy path, the abort and the slow case.
import React from 'react';
import { COL, MONO, cmix, clamp, pop, pr, eo } from '../lib/core';
import { P, Box, Wire, along, Icon, onTop, onFront } from '../lib/iso';

export type Key<T> = [number, T];
/** colour at t from keyframes, blending over `d` seconds into each new key */
export const colAt = (keys: Key<string>[], t: number, d = 0.3) => {
  let i = -1; keys.forEach(([a], j) => { if (a <= t) i = j; });
  if (i < 0) return keys[0][1];
  if (i === 0) return keys[0][1];
  return cmix(keys[i - 1][1], keys[i][1], clamp((t - keys[i][0]) / d));
};
export const keyAt = <T,>(keys: Key<T>[], t: number): [T, number] => {
  let i = 0; keys.forEach(([a], j) => { if (a <= t) i = j; }); return [keys[i][1], keys[i][0]];
};
export type Packet = { from: 'c' | 'f' | 'h'; to: 'c' | 'f' | 'h'; t0: number; dur: number; label: string; col: string };
export type Board = {
  cC: Key<string>[]; cF: Key<string>[]; cH: Key<string>[];
  iF: Key<[string, string]>[]; iH: Key<[string, string]>[]; packets: Packet[];
  appear: number; spinH?: [number, number]; timer?: number; dimF?: Key<number>[]; dimH?: Key<number>[];
};

const POS = { c: [-200, -200], f: [-30, 300], h: [300, -30] } as const;

const Chip: React.FC<{ x: number; y: number; label: string; col: string; k: number }> = ({ x, y, label, col, k }) => {
  const w = label.length * 14 + 34;
  return (
    <g transform={`translate(${x},${y}) scale(${0.6 + 0.4 * k})`} opacity={k}>
      <rect x={-w / 2} y={-22} width={w} height={44} rx={13} fill={col} opacity={0.22} filter="url(#halo)" />
      <rect x={-w / 2} y={-22} width={w} height={44} rx={13} fill="#0A111B" stroke={col} strokeWidth={2.4} />
      <text x={0} y={8} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={22} letterSpacing={1.5} fill={col}>{label}</text>
    </g>
  );
};

const Service: React.FC<{ cx: number; cy: number; col: string; icon: string; label: string; k: number; t: number; mark: [string, string]; markT: number; spin?: number; op?: number }> = ({ cx, cy, col, icon, label, k, t, mark, markT, spin = 0, op = 1 }) => {
  const x = cx - 70, y = cy - 70, h = 140;
  const [mx, my] = P(cx, cy, h + 95 + Math.sin(t * 2.4 + cx) * 6);
  const bl = P(cx + 70, cy + 70, 0);
  const mk = pop(t, markT, 0.45);
  return (
    <g opacity={op}>
      <Box x={x} y={y} w={140} d={140} h={h} col={col} draw={k}>
        <g transform={onTop(x, y, h)}><Icon n={icon} x={70} y={70} s={78} col={col} w={6} /></g>
        <g transform={onFront(x, y + 140, h)}>
          {[0, 1, 2, 3].map((i) => <g key={i}>
            <rect x={16} y={18 + i * 30} width={108} height={18} rx={4} fill="none" stroke={col} strokeOpacity={0.5} strokeWidth={1.6} />
            <circle cx={110} cy={27 + i * 30} r={3.5} fill={col} opacity={0.4 + 0.6 * ((Math.floor(t * 4 + i * 1.7 + cx) % 3) === 0 ? 1 : 0.3)} />
          </g>)}
        </g>
      </Box>
      <text x={bl[0] - 70} y={bl[1] + 18} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={24} letterSpacing={4} fill={col} opacity={0.9 * k}>{label}</text>
      {mark[0] && <g opacity={mk}>
        <circle cx={mx} cy={my} r={44 * (0.7 + 0.3 * mk)} fill={mark[1]} opacity={0.14} />
        <circle cx={mx} cy={my} r={44 * (0.7 + 0.3 * mk)} fill="none" stroke={mark[1]} strokeWidth={2.4} />
        <Icon n={mark[0]} x={mx} y={my - 2} s={50} col={mark[1]} w={8} draw={eo((t - markT) / 0.4)} />
      </g>}
      {spin > 0 && <g opacity={spin} transform={`translate(${mx},${my})`}>
        <circle r={44} fill="none" stroke={COL.dim} strokeWidth={4} />
        <circle r={44} fill="none" stroke={COL.amber} strokeWidth={5} strokeDasharray="70 210" strokeLinecap="round" transform={`rotate(${t * 220})`} />
        <text y={9} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={24} fill={COL.amber}>…</text>
      </g>}
    </g>
  );
};

export const TwoPC: React.FC<{ t: number; b: Board; op?: number }> = ({ t, b, op = 1 }) => {
  const k = pr(t, b.appear, 0.8), kc = pr(t, b.appear + 0.15, 0.8);
  const cc = colAt(b.cC, t), cf = colAt(b.cF, t), ch = colAt(b.cH, t);
  const [iF, tF] = keyAt(b.iF, t), [iH, tH] = keyAt(b.iH, t);
  const pt = (n: 'c' | 'f' | 'h', z = 0): [number, number, number] => [POS[n][0], POS[n][1], z];
  const top = P(-280, -280, 120);
  const dF = b.dimF ? keyAt(b.dimF, t)[0] : 1, dH = b.dimH ? keyAt(b.dimH, t)[0] : 1;
  return (
    <g opacity={op}>
      <Wire a={pt('c')} b={pt('f')} col={cmix(cc, cf, 0.5)} draw={pr(t, b.appear + 0.3, 0.8)} flow={t} w={2.5} />
      <Wire a={pt('c')} b={pt('h')} col={cmix(cc, ch, 0.5)} draw={pr(t, b.appear + 0.3, 0.8)} flow={t} w={2.5} />
      <Box x={-280} y={-280} w={160} d={160} h={120} col={cc} draw={kc}>
        <g transform={onTop(-280, -280, 120)}>
          <Icon n={b.timer !== undefined && t > b.timer ? 'hourglass' : 'hub'} x={80} y={80} s={86} col={cc} w={5} />
        </g>
      </Box>
      <text x={top[0]} y={top[1] - 40} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={24} letterSpacing={4} fill={cc} opacity={kc}>COORDINATOR</text>
      {b.timer !== undefined && t > b.timer && (
        <text x={top[0]} y={top[1] - 78} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={30} fill={COL.amber}>
          WAITING {(t - b.timer).toFixed(1)}s
        </text>
      )}
      <Service cx={POS.f[0]} cy={POS.f[1]} col={cf} icon="plane" label="FLIGHTS" k={k} t={t} mark={iF} markT={tF} op={dF} />
      <Service cx={POS.h[0]} cy={POS.h[1]} col={ch} icon="bed" label="HOTELS" k={k} t={t} mark={iH} markT={tH} op={dH}
        spin={b.spinH ? clamp((t - b.spinH[0]) / 0.3) * (1 - clamp((t - b.spinH[1]) / 0.3)) : 0} />
      {b.packets.map((p, i) => {
        const u = (t - p.t0) / p.dur;
        if (u < -0.05 || u > 1.25) return null;
        const zA = p.from === 'c' ? 120 : 140, zB = p.to === 'c' ? 120 : 140;
        const [x, y] = along(pt(p.from, zA), pt(p.to, zB), eo(u));
        const vis = clamp(u / 0.12) * (1 - clamp((u - 1) / 0.2));
        const off = p.to === 'c' ? (p.from === 'f' ? -70 : 70) * eo(u) : 0;
        return <Chip key={i} x={x + off} y={y - 46} label={p.label} col={p.col} k={vis} />;
      })}
    </g>
  );
};
