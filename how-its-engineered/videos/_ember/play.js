// Live player for render(t) pages: plays in a normal browser, stays out of the way when the renderer drives the page.
// Space = play/pause, ←/→ = step 0.5 s, M = sound on/off (muted by default), drag the bar to scrub. Loops.
(function () {
  if (navigator.webdriver && !/play/.test(location.hash)) return;
  // #embed: inside the gallery page, which owns the clock (parent.__T) and the controls.
  const embed = /embed/.test(location.hash) && window.parent !== window;
  const stage = document.getElementById('stage');
  const css = document.createElement('style');
  css.textContent = `
html, body { height: 100%; background: #050505; overflow: hidden; }
#pl-wrap { position: fixed; left: 50%; top: 12px; transform-origin: 50% 0; }
#pl-bar { position: fixed; left: 50%; transform: translateX(-50%); bottom: 10px; display: flex; align-items: center; gap: 10px; font: 600 11px/1 ui-monospace, Menlo, monospace; color: #bbb; background: rgba(20,20,20,0.9); border: 1px solid #333; border-radius: 10px; padding: 7px 10px; }
#pl-bar button { all: unset; cursor: pointer; width: 22px; text-align: center; color: #FF6A1F; font-size: 14px; }
#pl-bar input { width: 260px; accent-color: #FF6A1F; }`;
  document.head.appendChild(css);
  const wrap = document.createElement('div'); wrap.id = 'pl-wrap';
  stage.parentNode.insertBefore(wrap, stage); wrap.appendChild(stage);
  // #safe: shade where Instagram's own UI sits on a reel (header, side buttons, caption + audio bar)
  if (/safe/.test(location.hash)) {
    const z = document.createElement('div');
    z.style.cssText = 'position:absolute;inset:0;pointer-events:none;z-index:99;font:700 10px/1 Mono,monospace;letter-spacing:1px;color:#fff';
    z.innerHTML = '<div style="position:absolute;left:0;right:0;top:0;height:110px;background:rgba(0,140,255,0.28);border-bottom:1px dashed #4cf;padding:8px">INSTAGRAM HEADER</div>'
      + '<div style="position:absolute;right:0;top:470px;width:62px;bottom:170px;background:rgba(0,140,255,0.22);border-left:1px dashed #4cf"></div>'
      + '<div style="position:absolute;left:0;right:0;bottom:0;height:170px;background:rgba(0,140,255,0.28);border-top:1px dashed #4cf;padding:8px">CAPTION · AUDIO</div>';
    stage.appendChild(z);
  }
  const bar = document.createElement('div'); bar.id = 'pl-bar';
  bar.innerHTML = '<button id="pl-pp">❚❚</button><button id="pl-mu" title="Sound on/off (M)"></button><input id="pl-sc" type="range" min="0" max="1000" value="0"><span id="pl-t">0.00</span>';
  document.body.appendChild(bar);
  if (embed) { bar.style.display = 'none'; wrap.style.top = '0'; }
  const fit = () => { const k = embed ? Math.min(innerHeight / 960, innerWidth / 540) : Math.min((innerHeight - 70) / 960, (innerWidth - 20) / 540); wrap.style.transform = `translateX(-50%) scale(${k})`; };
  addEventListener('resize', fit); fit();
  let playing = true, t = 0, last = performance.now();
  const D = window.DURATION, pp = document.getElementById('pl-pp'), sc = document.getElementById('pl-sc'), tl = document.getElementById('pl-t');
  // voice track: when it is playing it drives the clock, so picture and sound stay in sync
  const au = embed ? null : new Audio((window.VOICE || 'voice/voice.wav') + '?v=' + Date.now());
  const seek = (v) => { t = Math.max(0, Math.min(D, v)); if (au) au.currentTime = Math.min(t, au.duration || t); };
  const setPlay = (v) => {
    playing = v; pp.textContent = v ? '❚❚' : '▶';
    if (au) { if (v) { au.currentTime = t; au.play().catch(() => setPlay(false)); } else au.pause(); }
  };
  pp.onclick = () => setPlay(!playing);
  // sound: off unless the viewer turned it on (remembered per browser)
  const mu = document.getElementById('pl-mu');
  let muted = true; try { muted = localStorage.getItem('pl-sound') !== 'on'; } catch (e) {}
  const setMute = (v) => { muted = v; if (au) au.muted = v; mu.textContent = v ? '🔇' : '🔊'; try { localStorage.setItem('pl-sound', v ? 'off' : 'on'); } catch (e) {} };
  mu.onclick = () => setMute(!muted); setMute(muted);
  if (!au) mu.style.display = 'none';
  sc.oninput = () => { seek((sc.value / 1000) * D); setPlay(false); };
  addEventListener('keydown', (e) => {
    if (e.code === 'Space') { e.preventDefault(); setPlay(!playing); }
    if (e.code === 'ArrowRight') seek(t + 0.5);
    if (e.code === 'ArrowLeft') seek(t - 0.5);
    if (e.code === 'KeyM') setMute(!muted);
  });
  if (au) setPlay(true); // autoplay with sound if the browser allows it, else waits for ▶
  const start = () => {
    window.ready && window.ready();
    const tick = (now) => {
      const dt = Math.min(0.1, (now - last) / 1000); last = now;
      if (embed) t = Math.min(D, parent.__T || 0);
      else if (playing) {
        if (au && !au.paused && !au.ended) t = au.currentTime; else t += dt;
        if (t >= D) { t = 0; if (au) { au.currentTime = 0; au.play().catch(() => {}); } }
      }
      window.render(t);
      sc.value = Math.round((t / D) * 1000); tl.textContent = t.toFixed(2) + 's';
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };
  (document.fonts ? document.fonts.ready : Promise.resolve()).then(start);
})();
