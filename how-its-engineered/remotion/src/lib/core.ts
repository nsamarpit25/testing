// Shared look and timing for the Remotion reels: palette, easing, and the voice timeline (phrase starts + whisper words).
export const W = 1080, H = 1920, FPS = 30;

export const COL = {
  bg0: '#04070C', bg1: '#0A1424', grid: '#2A5F80',
  cyan: '#46E3FF', cyanD: '#1B7FA0', amber: '#FFB547', green: '#3CF2A0', red: '#FF4D5E',
  white: '#EEF4FF', mute: '#7E8CA3', dim: '#3A4A60',
  top: '#16212F', left: '#0F1824', right: '#0A111A',
};
export const FONT = "'Inter', system-ui, sans-serif", MONO = "'JB Mono', ui-monospace, monospace";

export const clamp = (x: number, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const mix = (a: number, b: number, k: number) => a + (b - a) * k;
export const eio = (x: number) => { x = clamp(x); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
export const eo = (x: number) => 1 - Math.pow(1 - clamp(x), 3);
export const back = (x: number) => { x = clamp(x); const c1 = 1.5, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };
/** 0→1 from time a over d seconds (ease out) */
export const pr = (t: number, a: number, d = 0.45) => eo((t - a) / d);
/** pop with overshoot */
export const pop = (t: number, a: number, d = 0.5) => back((t - a) / d);
/** on between a and b with soft edges */
export const win = (t: number, a: number, b: number, f = 0.3) => clamp((t - a) / f) * (1 - clamp((t - b) / f));

const hex = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
export const cmix = (a: string, b: string, k: number) => {
  const A = hex(a), B = hex(b); k = clamp(k);
  return '#' + A.map((v, i) => Math.round(v + (B[i] - v) * k).toString(16).padStart(2, '0')).join('');
};

export type Phrase = { li: number; pi: number; say: string; show: string; start: number; end: number };
export type Word = [string, number, number];

export const makeTimeline = (T: Phrase[], WORDS: Word[]) => {
  const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, '');
  const L = (li: number, pi = 0) => T.find((x) => x.li === li && x.pi === pi)!.start;
  const LE = (li: number, pi = 0) => T.find((x) => x.li === li && x.pi === pi)!.end;
  /** start time of the first spoken word `tok` at or after `after` */
  const Wd = (tok: string, after = 0) => {
    const w = WORDS.find(([s, a]) => a >= after - 1e-6 && norm(s) === norm(tok));
    if (!w) throw new Error(`word ${tok} after ${after} not found`);
    return w[1];
  };
  const END = T[T.length - 1].end + 1.8;
  const nLines = Math.max(...T.map((x) => x.li)) + 1;
  return { T, WORDS, L, LE, Wd, END, nLines, norm };
};
export type TL = ReturnType<typeof makeTimeline>;
