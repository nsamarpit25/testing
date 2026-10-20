// Isometric drawing kit in SVG. World units are px; x runs right-down, y runs left-down, z is up.
// Boxes are shaded on three faces with neon edges; any flat 2D drawing can be mapped onto a face with an affine matrix.
import React from 'react';
import { COL, clamp } from './core';

export const C30 = Math.cos(Math.PI / 6);
export const P = (x: number, y: number, z = 0): [number, number] => [(x - y) * C30, (x + y) * 0.5 - z];
const pts = (a: [number, number, number][]) => a.map(([x, y, z]) => P(x, y, z).map((v) => v.toFixed(1)).join(',')).join(' ');

/** content drawn in local (u, v) px onto the top face starting at world (x, y, z): u along +x, v along +y */
export const onTop = (x: number, y: number, z: number, k = 1) => `matrix(${C30 * k},${0.5 * k},${-C30 * k},${0.5 * k},${(x - y) * C30},${(x + y) * 0.5 - z})`;
/** onto the front-left face (plane y = const): u along +x, v downward; (x, y, z) is the face's top-left corner */
export const onFront = (x: number, y: number, z: number, k = 1) => `matrix(${C30 * k},${0.5 * k},0,${k},${(x - y) * C30},${(x + y) * 0.5 - z})`;
/** onto the front-right face (plane x = const): u along -y, v downward; (x, y, z) is the face's top-left corner (largest y) */
export const onSide = (x: number, y: number, z: number, k = 1) => `matrix(${C30 * k},${-0.5 * k},0,${k},${(x - y) * C30},${(x + y) * 0.5 - z})`;

export const Defs: React.FC = () => (
  <defs>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="5" result="b" />
      <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
    </filter>
    <filter id="halo" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="16" /></filter>
    <filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="22" /></filter>
    <linearGradient id="topSheen" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stopColor="#FFFFFF" stopOpacity="0.07" /><stop offset="0.6" stopColor="#FFFFFF" stopOpacity="0" />
    </linearGradient>
  </defs>
);

/** soft contact shadow under a footprint */
export const Shadow: React.FC<{ x: number; y: number; w: number; d: number; o?: number; grow?: number }> = ({ x, y, w, d, o = 0.6, grow = 18 }) => (
  <polygon points={pts([[x - grow, y - grow, 0], [x + w + grow, y - grow, 0], [x + w + grow, y + d + grow, 0], [x - grow, y + d + grow, 0]])}
    fill="#000" opacity={o} filter="url(#soft)" />
);

type BoxP = { x: number; y: number; z?: number; w: number; d: number; h: number; col?: string; glow?: number; op?: number;
  top?: string; left?: string; right?: string; draw?: number; edge?: number; shadow?: boolean; children?: React.ReactNode };
/** shaded box; `draw` 0→1 draws the edges in; children are drawn on the top face (use onTop with the same x, y, z + h) */
export const Box: React.FC<BoxP> = ({ x, y, z = 0, w, d, h, col = COL.cyan, glow = 1, op = 1, top = COL.top, left = COL.left, right = COL.right, draw = 1, edge = 2.2, shadow = true, children }) => {
  const t = z + h;
  const T = pts([[x, y, t], [x + w, y, t], [x + w, y + d, t], [x, y + d, t]]);
  const R = pts([[x + w, y, z], [x + w, y + d, z], [x + w, y + d, t], [x + w, y, t]]);
  const Lf = pts([[x, y + d, z], [x + w, y + d, z], [x + w, y + d, t], [x, y + d, t]]);
  const sil = pts([[x, y, t], [x + w, y, t], [x + w, y, z], [x + w, y + d, z], [x, y + d, z], [x, y + d, t]]);
  const ridge = `M${P(x, y + d, t).join(',')} L${P(x + w, y + d, t).join(',')} L${P(x + w, y, t).join(',')} M${P(x + w, y + d, t).join(',')} L${P(x + w, y + d, z).join(',')}`;
  const fo = clamp(draw * 1.6 - 0.3);
  const dash = { pathLength: 1, strokeDasharray: 1, strokeDashoffset: 1 - clamp(draw) } as const;
  return (
    <g opacity={op}>
      {shadow && z < 40 && <Shadow x={x} y={y} w={w} d={d} o={0.55 * fo} />}
      <g opacity={fo}>
        <polygon points={R} fill={right} />
        <polygon points={Lf} fill={left} />
        <polygon points={T} fill={top} />
        <polygon points={T} fill="url(#topSheen)" />
      </g>
      {glow > 0 && <polygon points={sil} fill="none" stroke={col} strokeWidth={edge * 3} opacity={0.35 * glow} filter="url(#halo)" />}
      <path d={ridge} fill="none" stroke={col} strokeWidth={edge * 0.6} opacity={0.55} {...dash} />
      <polygon points={sil} fill="none" stroke={col} strokeWidth={edge} strokeLinejoin="round" {...dash} />
      <g opacity={fo}>{children}</g>
    </g>
  );
};

/** database cylinder centred at (cx, cy) */
export const Cyl: React.FC<{ cx: number; cy: number; z?: number; r: number; h: number; col?: string; glow?: number; op?: number; bands?: number; fill?: number }> = ({ cx, cy, z = 0, r, h, col = COL.cyan, glow = 1, op = 1, bands = 2, fill = 0 }) => {
  const [X, Yb] = P(cx, cy, z), Yt = Yb - h, rx = r * 1.2247, ry = r * 0.7071;
  const body = `M${X - rx},${Yt} L${X - rx},${Yb} A${rx},${ry} 0 0 0 ${X + rx},${Yb} L${X + rx},${Yt} Z`;
  return (
    <g opacity={op}>
      <ellipse cx={X} cy={Yb + 6} rx={rx * 1.25} ry={ry * 1.25} fill="#000" opacity={0.55} filter="url(#soft)" />
      <path d={body} fill={COL.left} />
      <path d={`M${X},${Yt} L${X + rx},${Yt} L${X + rx},${Yb} A${rx},${ry} 0 0 1 ${X},${Yb + ry} Z`} fill={COL.right} />
      {fill > 0 && <path d={`M${X - rx},${Yb - (h - 8) * fill} L${X - rx},${Yb} A${rx},${ry} 0 0 0 ${X + rx},${Yb} L${X + rx},${Yb - (h - 8) * fill} A${rx},${ry} 0 0 1 ${X - rx},${Yb - (h - 8) * fill}`} fill={col} opacity={0.16} />}
      <ellipse cx={X} cy={Yt} rx={rx} ry={ry} fill={COL.top} />
      {glow > 0 && <path d={body} fill="none" stroke={col} strokeWidth={7} opacity={0.3 * glow} filter="url(#halo)" />}
      {Array.from({ length: bands }, (_, i) => {
        const yy = Yt + (h * (i + 1)) / (bands + 1);
        return <path key={i} d={`M${X - rx},${yy} A${rx},${ry} 0 0 0 ${X + rx},${yy}`} fill="none" stroke={col} strokeWidth={1.6} opacity={0.6} />;
      })}
      <path d={body} fill="none" stroke={col} strokeWidth={2.2} />
      <ellipse cx={X} cy={Yt} rx={rx} ry={ry} fill="none" stroke={col} strokeWidth={2.2} />
    </g>
  );
};

/** a world-space line between two points; `flow` animates dashes along it, `draw` draws it in */
export const Wire: React.FC<{ a: [number, number, number]; b: [number, number, number]; col?: string; op?: number; draw?: number; flow?: number; w?: number; mid?: number }> = ({ a, b, col = COL.cyan, op = 1, draw = 1, flow, w = 2, mid }) => {
  const A = P(...a), B = P(...b);
  // elbow through a mid z so wires run like cables
  const pa = mid !== undefined ? [A, P(a[0], a[1], mid), P(b[0], b[1], mid), B] : [A, B];
  const d = 'M' + pa.map((p) => p.join(',')).join(' L');
  return (
    <g opacity={op}>
      <path d={d} fill="none" stroke={col} strokeWidth={w * 4} opacity={0.18} filter="url(#halo)" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - clamp(draw)} />
      <path d={d} fill="none" stroke={col} strokeWidth={w} opacity={0.45} pathLength={1} strokeDasharray={1} strokeDashoffset={1 - clamp(draw)} />
      {flow !== undefined && draw >= 1 && <path d={d} fill="none" stroke={col} strokeWidth={w + 0.6} strokeDasharray="10 26" strokeDashoffset={-flow * 60} strokeLinecap="round" />}
    </g>
  );
};
/** point along the same elbow path as Wire, k in 0..1 */
export const along = (a: [number, number, number], b: [number, number, number], k: number, mid?: number): [number, number] => {
  const ps = mid !== undefined ? [P(...a), P(a[0], a[1], mid), P(b[0], b[1], mid), P(...b)] : [P(...a), P(...b)];
  const seg = ps.slice(1).map((p, i) => Math.hypot(p[0] - ps[i][0], p[1] - ps[i][1]));
  let L = seg.reduce((s, v) => s + v, 0) * clamp(k);
  for (let i = 0; i < seg.length; i++) {
    if (L <= seg[i] || i === seg.length - 1) { const f = seg[i] ? clamp(L / seg[i]) : 0; return [ps[i][0] + (ps[i + 1][0] - ps[i][0]) * f, ps[i][1] + (ps[i + 1][1] - ps[i][1]) * f]; }
    L -= seg[i];
  }
  return ps[ps.length - 1];
};

/** flat line icons in a 100 x 100 box */
export const ICON: Record<string, string> = {
  plane: 'M50 8 C55 8 56 16 56 22 L56 40 L90 60 L90 68 L56 58 L55 80 L66 88 L66 94 L50 89 L34 94 L34 88 L45 80 L44 58 L10 68 L10 60 L44 40 L44 22 C44 16 45 8 50 8 Z',
  bed: 'M10 74 L10 30 M10 58 L90 58 L90 74 M10 66 L90 66 M42 58 L42 44 Q42 40 46 40 L84 40 Q90 40 90 46 L90 58 M16 50 Q16 42 24 42 L30 42 Q36 42 36 50 Q36 56 30 56 L22 56 Q16 56 16 50 Z',
  lock: 'M28 46 L72 46 Q76 46 76 50 L76 82 Q76 86 72 86 L28 86 Q24 86 24 82 L24 50 Q24 46 28 46 Z M36 46 L36 32 Q36 16 50 16 Q64 16 64 32 L64 46 M50 60 L50 72',
  unlock: 'M28 46 L72 46 Q76 46 76 50 L76 82 Q76 86 72 86 L28 86 Q24 86 24 82 L24 50 Q24 46 28 46 Z M36 46 L36 26 Q36 10 50 10 Q64 10 64 26 L64 30 M50 60 L50 72',
  check: 'M24 52 L42 70 L78 32',
  cross: 'M30 30 L70 70 M70 30 L30 70',
  hub: 'M50 50 m-14 0 a14 14 0 1 0 28 0 a14 14 0 1 0 -28 0 M50 36 L50 12 M50 64 L50 88 M36 50 L12 50 M64 50 L88 50 M40 40 L22 22 M60 60 L78 78 M60 40 L78 22 M40 60 L22 78',
  hourglass: 'M30 14 L70 14 M30 86 L70 86 M34 14 Q34 40 50 50 Q66 40 66 14 M34 86 Q34 60 50 50 Q66 60 66 86',
  doc: 'M24 8 L64 8 L80 24 L80 92 L24 92 Z M64 8 L64 24 L80 24',
  cart: 'M8 16 L22 16 L32 64 L80 64 L88 30 L26 30 M38 80 m-6 0 a6 6 0 1 0 12 0 a6 6 0 1 0 -12 0 M74 80 m-6 0 a6 6 0 1 0 12 0 a6 6 0 1 0 -12 0',
};
export const Icon: React.FC<{ n: keyof typeof ICON | string; x: number; y: number; s: number; col: string; w?: number; draw?: number; fill?: boolean; op?: number }> = ({ n, x, y, s, col, w = 6, draw = 1, fill = false, op = 1 }) => (
  <g transform={`translate(${x - s / 2},${y - s / 2}) scale(${s / 100})`} opacity={op}>
    <path d={ICON[n]} fill={fill ? col : 'none'} fillOpacity={fill ? 0.18 : 0} stroke={col} strokeWidth={w} strokeLinecap="round" strokeLinejoin="round"
      pathLength={1} strokeDasharray={1} strokeDashoffset={1 - clamp(draw)} />
  </g>
);
