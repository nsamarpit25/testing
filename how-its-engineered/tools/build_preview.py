import base64, re, sys
from pathlib import Path
# usage: python3 tools/build_preview.py videos/<slug> voice.m4a ["Page title"]
vid = Path(sys.argv[1]).resolve()
src = (vid / 'video.html').read_text()
b64 = lambda p: base64.b64encode(Path(p).read_bytes()).decode()
style = re.search(r'<style>(.*?)</style>', src, re.S).group(1)
style = re.sub(r'url\((\.\./\.\./node_modules/[^)]+\.woff2)\)', lambda m: f"url(data:font/woff2;base64,{b64(vid / m.group(1))})", style)
style = style.replace('html, body { margin: 0; background: #000; }', '')
body = re.search(r'<body>(.*)</body>', src, re.S).group(1)
def inline(m):
    p = m.group(1)
    return '<script>\n' + (vid / p).read_text() + '\n</script>'
body = re.sub(r'<script src="([^"]+)"></script>', inline, body)
audio = b64(sys.argv[2])
title = sys.argv[3] if len(sys.argv) > 3 else vid.name + ' preview'
page = f'''<title>{title}</title>
<style>
:root {{ --bg:#0b0b0c; --panel:#141416; --line:#2a2a2e; --fg:#ededee; --mute:#8b8b91; --go:#32D74B; color-scheme: dark; }}
html, body {{ height: 100%; }}
body {{ margin: 0; background: var(--bg); color: var(--fg); font: 13px/1.4 ui-monospace, "SF Mono", Menlo, monospace; display: flex; flex-direction: column; align-items: center; padding-inline: 16px; box-sizing: border-box; }}
#wrap {{ flex: 1; min-height: 0; width: 100%; display: flex; align-items: center; justify-content: center; padding-block: 12px 4px; }}
#frame {{ position: relative; border-radius: 14px; overflow: hidden; box-shadow: 0 0 0 1px var(--line); cursor: pointer; }}
#frame > #stage {{ transform-origin: 0 0; position: absolute; left: 0; top: 0; }}
#big {{ position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.35); }}
#big span {{ width: 72px; height: 72px; border-radius: 50%; background: var(--fg); color: var(--bg); display: flex; align-items: center; justify-content: center; font-size: 26px; padding-left: 5px; box-sizing: border-box; }}
#ctl {{ width: 100%; max-width: 560px; display: flex; gap: 12px; align-items: center; padding-block: 8px 16px; }}
#ctl button {{ background: var(--panel); color: var(--fg); border: 1px solid var(--line); border-radius: 8px; height: 34px; min-width: 64px; font: inherit; cursor: pointer; }}
#ctl button:focus-visible, #seek:focus-visible {{ outline: 2px solid var(--go); outline-offset: 2px; }}
#seek {{ flex: 1; min-width: 0; accent-color: var(--go); }}
#tm {{ color: var(--mute); font-variant-numeric: tabular-nums; white-space: nowrap; }}
{style}
</style>
<div id="wrap"><div id="frame">{body}<div id="big"><span>▶</span></div></div></div>
<div id="ctl"><button id="pp" type="button">Play</button><input id="seek" type="range" min="0" max="1000" value="0" aria-label="Seek"><span id="tm">0.0 / 0.0s</span></div>
<audio id="au" preload="auto" src="data:audio/mp4;base64,{audio}"></audio>
<script>
(() => {{
  const st = document.getElementById('stage'), fr = document.getElementById('frame'), wrap = document.getElementById('wrap');
  const au = document.getElementById('au'), pp = document.getElementById('pp'), seek = document.getElementById('seek'), tm = document.getElementById('tm'), big = document.getElementById('big');
  const D = window.DURATION;
  function fit() {{
    const s = Math.min((wrap.clientHeight - 16) / 960, (wrap.clientWidth) / 540);
    st.style.transform = `scale(${{s}})`; fr.style.width = 540 * s + 'px'; fr.style.height = 960 * s + 'px';
  }}
  addEventListener('resize', fit); fit();
  let playing = false, last = -1;
  const draw = (t) => {{ t = Math.min(t, D); if (t === last) return; last = t; window.render(t); seek.value = Math.round(t / D * 1000); tm.textContent = t.toFixed(1) + ' / ' + D.toFixed(1) + 's'; }};
  function loop() {{ if (!playing) return; draw(au.currentTime); if (au.currentTime >= D || au.ended) {{ stop(); }} else requestAnimationFrame(loop); }}
  function play() {{ if (au.currentTime >= D - 0.05) au.currentTime = 0; au.play().then(() => {{ playing = true; pp.textContent = 'Pause'; big.hidden = true; loop(); }}).catch(() => {{}}); }}
  function stop() {{ playing = false; au.pause(); pp.textContent = 'Play'; big.hidden = false; }}
  pp.onclick = () => (playing ? stop() : play());
  fr.onclick = () => (playing ? stop() : play());
  seek.oninput = () => {{ const t = seek.value / 1000 * D; au.currentTime = t; draw(t); }};
  addEventListener('keydown', (e) => {{ if (e.code === 'Space' && e.target === document.body) {{ e.preventDefault(); playing ? stop() : play(); }} }});
  document.fonts && document.fonts.ready.then(() => draw(0.3));
  draw(0.3);
}})();
</script>
'''
out = vid / 'preview.html'
out.write_text(page)
print(out, round(len(page) / 1e6, 2), 'MB')
