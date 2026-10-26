// Render an HTML page that exposes window.DURATION and window.render(t) to an MP4.
// usage: node tools/render.mjs page.html out.mp4 [--audio voice.wav] [--from 0 --to 25.5] [--stills 1,5.5,12 --outdir dir]
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';

const args = process.argv.slice(2);
const opt = (name) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : null; };
const [html, out] = args;
const FPS = 30;

// CHROMIUM_PATH: use a preinstalled browser (cloud sessions) instead of Playwright's own download
// RENDER_GPU=vulkan: real GPU WebGL through ANGLE/Vulkan (the home PC's RX 6600) instead of headless SwiftShader
const gpu = process.env.RENDER_GPU === 'vulkan'
  ? { args: ['--use-angle=vulkan', '--enable-features=Vulkan', '--ignore-gpu-blocklist', '--enable-gpu'], ignoreDefaultArgs: ['--use-angle=swiftshader-webgl', '--enable-unsafe-swiftshader'] } : {};
const browser = await chromium.launch({ ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}), ...gpu });
const page = await browser.newPage({ viewport: { width: 540, height: 960 }, deviceScaleFactor: 2 });
page.on('pageerror', (e) => console.error('page error:', e.message));
await page.goto('file://' + path.resolve(html));
await page.evaluate(() => document.fonts.ready);
await page.evaluate(() => window.ready && window.ready());
const duration = await page.evaluate(() => window.DURATION);

const stills = opt('--stills');
if (stills) {
  const dir = opt('--outdir') || '.';
  fs.mkdirSync(dir, { recursive: true });
  for (const s of stills.split(',').map(Number)) {
    await page.evaluate((t) => window.render(t), s);
    await page.screenshot({ path: path.join(dir, `still_${s.toFixed(2)}.png`) });
  }
  await browser.close();
  process.exit(0);
}

const audio = opt('--audio');
const from = Number(opt('--from') ?? 0);
const to = Math.min(Number(opt('--to') ?? duration), duration);
const ff = spawn('ffmpeg', [
  '-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
  ...(audio ? ['-ss', String(from), '-i', audio, '-c:a', 'aac', '-b:a', '192k', '-shortest'] : []),
  '-c:v', 'libx264', '-crf', '15', '-preset', 'slow', '-x264-params', 'aq-mode=3', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out,
], { stdio: ['pipe', 'inherit', 'inherit'] });

const first = Math.round(from * FPS), total = Math.round(to * FPS);
const t0 = Date.now();
for (let i = first; i < total; i++) {
  await page.evaluate((t) => window.render(t), i / FPS);
  const buf = await page.screenshot({ type: 'png' });
  if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
  if (i % 60 === 0) process.stdout.write(`\rframe ${i}/${total}`);
}
ff.stdin.end();
await new Promise((r) => ff.on('close', r));
await browser.close();
console.log(`\rdone ${total - first} frames in ${((Date.now() - t0) / 1000).toFixed(1)}s -> ${out}`);
