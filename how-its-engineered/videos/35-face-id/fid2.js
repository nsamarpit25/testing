// 35 Face ID v2: the interactive layer. A live "infrared camera" picture-in-picture (a second render of the scene
// from the phone's IR camera, faces in their infrared look, dots in white), point clouds that lift off a face and turn
// in space (coloured by depth), the phone's lock screen states, and a match meter. Load after faceid.js.

/* ------------------------------------------------------------------ picture-in-picture: what the IR camera sees */
const pipCam = new TH.PerspectiveCamera(24, 1, 5, 4000); pipCam.up.set(0, 0, 1);
const pipEl = div($('world'), 'pip', '<div class="pk"><i></i><span>Infrared camera</span></div><div class="pn"></div>');
// o: { a (0..1, opens as a top-down wipe), box: {x, y, w, h} in 540x960 px, from, at, fov, show: [objects],
//      ir (flood brightness), depth (0..1 depth-map look), dots: [dot clouds], note, hot (orange frame) }
let PIP_O = null;
function pipSet(o) {
  PIP_O = o && o.a > 0.01 ? o : null;
  if (!PIP_O) { pipEl.style.display = 'none'; return; }
  const b = o.box, h = b.h * ease.inOut(clamp(o.a));
  pipEl.style.display = 'block'; pipEl.style.left = b.x + 'px'; pipEl.style.top = b.y + 'px'; pipEl.style.width = b.w + 'px'; pipEl.style.height = h + 'px';
  pipEl.classList.toggle('hot', !!o.hot);
  const n = pipEl.querySelector('.pn'); if (n._h !== (o.note || '')) { n._h = o.note || ''; n.innerHTML = n._h; }
  n.style.opacity = clamp((o.a - 0.6) / 0.4);
  pipEl.querySelector('.pk span').textContent = o.label || 'Infrared camera';
}
function pipRender() {
  const o = PIP_O; if (!o) return;
  const b = o.box, h = b.h * ease.inOut(clamp(o.a));
  if (h < 2) return;
  const vis = scene.children.map((c) => [c, c.visible]);
  scene.children.forEach((c) => (c.visible = false));
  o.show.forEach((g) => (g.visible = true));
  const fs = FACES.map((m) => [m, m.userData.u.uIR.value, m.userData.u.uDepth.value, m.userData.u.uIRk.value]);
  FACES.forEach((m) => { m.userData.u.uIR.value = o.mix && o.mix.has(m) ? o.mix.get(m) : 1; m.userData.u.uDepth.value = o.depth || 0; m.userData.u.uIRk.value = o.ir ?? 1; });
  const ds = (o.dots || []).map((D) => [D, D.m.uniforms.uCol.value.clone(), D.m.uniforms.uSize.value]);
  (o.dots || []).forEach((D) => { D.pts.visible = D.m.uniforms.uA.value > 0.005; D.m.uniforms.uCol.value.set('#ffffff'); D.m.uniforms.uSize.value *= 1.1; });
  const fog = scene.fog, bg = scene.background; scene.fog = null; scene.background = C('#040404');
  pipCam.aspect = b.w / b.h; pipCam.fov = o.fov || 24; pipCam.position.set(...o.from); pipCam.lookAt(...o.at); pipCam.updateProjectionMatrix();
  const X = Math.round(b.x * 2), Y = Math.round((960 - b.y - b.h) * 2), W = Math.round(b.w * 2), H = Math.round(b.h * 2), HV = Math.round(h * 2);
  renderer.setScissorTest(true); renderer.setScissor(X + 2, Y + H - HV + 2, W - 4, HV - 4); renderer.setViewport(X, Y, W, H);
  const sh = renderer.shadowMap.enabled; renderer.shadowMap.enabled = false;
  _rawRender(scene, pipCam);
  renderer.shadowMap.enabled = sh; renderer.setScissorTest(false); renderer.setViewport(0, 0, 1080, 1920);
  scene.fog = fog; scene.background = bg;
  fs.forEach(([m, a, d, k]) => { m.userData.u.uIR.value = a; m.userData.u.uDepth.value = d; m.userData.u.uIRk.value = k; });
  ds.forEach(([D, c, s]) => { D.m.uniforms.uCol.value.copy(c); D.m.uniforms.uSize.value = s; });
  vis.forEach(([c, v]) => (c.visible = v));
}

/* ------------------------------------------------------------------ point clouds that lift off a face */
// pts in world space; the cloud sits in a group at the pivot so it can turn about the vertical axis.
// colour by depth from the projector: near = warm white, far = deep orange (cool = the saved data, all one grey-white)
function liftCloud(hits, pivot, o = {}) {
  const n = hits.length, P = new Float32Array(n * 3), Cc = new Float32Array(n * 3), A = new Float32Array(n);
  let t0 = 1e9, t1 = -1e9; hits.forEach((h) => { t0 = Math.min(t0, h.t); t1 = Math.max(t1, h.t); });
  const near = C(o.near || '#ffe1c4'), far = C(o.far || '#8a3208'), c = new TH.Color();
  hits.forEach((h, i) => {
    const j = o.jit || 0;
    P.set([h.p[0] - pivot[0] + j * (rnd(i, 41) - 0.5), h.p[1] - pivot[1] + j * (rnd(i, 43) - 0.5), h.p[2] - pivot[2] + j * (rnd(i, 47) - 0.5)], i * 3);
    const k = o.flatCol ? 0.15 : Math.pow(clamp((h.t - t0) / Math.max(1e-6, t1 - t0)), 0.8);
    c.copy(near).lerp(far, k); Cc.set([c.r, c.g, c.b], i * 3); A[i] = rnd(i, 53);
  });
  const geo = new TH.BufferGeometry();
  geo.setAttribute('position', new TH.Float32BufferAttribute(P, 3)); geo.setAttribute('color', new TH.Float32BufferAttribute(Cc, 3)); geo.setAttribute('aR', new TH.Float32BufferAttribute(A, 1));
  const m = new TH.ShaderMaterial({
    uniforms: { uA: { value: 0 }, uSize: { value: o.size || 2.6 }, uHot: { value: 0 }, uShow: { value: 1 } },
    vertexShader: `attribute vec3 color; attribute float aR; uniform float uSize, uShow; varying vec3 vC; varying float vS;
      void main() { vC = color; vS = step(aR, uShow); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); gl_PointSize = uSize; }`,
    fragmentShader: `uniform float uA, uHot; varying vec3 vC; varying float vS;
      void main() { float r = length(gl_PointCoord - 0.5) * 2.0; float a = smoothstep(1.0, 0.3, r) * uA * vS; if (a < 0.01) discard;
        gl_FragColor = vec4(mix(vC, vec3(1.0, 0.55, 0.22), uHot) * (1.35 + 0.7 * smoothstep(0.5, 0.0, r)), a); }`,
    transparent: true, depthWrite: false, toneMapped: false, blending: TH.AdditiveBlending,
  });
  const g = new TH.Group(); g.position.set(...pivot); scene.add(g);
  const pts = new TH.Points(geo, m); pts.frustumCulled = false; pts.renderOrder = 6; g.add(pts);
  g.visible = false;
  return { g, pts, m, set(a, rz = 0, off = [0, 0, 0], hot = 0, show = 1) { g.visible = a > 0.005; m.uniforms.uA.value = a; m.uniforms.uHot.value = hot; m.uniforms.uShow.value = show; g.rotation.z = rz; g.position.set(pivot[0] + off[0], pivot[1] + off[1], pivot[2] + off[2]); } };
}

/* ------------------------------------------------------------------ the phone's lock screen */
const FACE_GLYPH = new Path2D('M4 12V8a4 4 0 0 1 4-4h4M28 4h4a4 4 0 0 1 4 4v4M36 28v4a4 4 0 0 1-4 4h-4M12 36H8a4 4 0 0 1-4-4v-4M14 14v3M26 14v3M20 14v8h-2M15 27c3 2.4 7 2.4 10 0');
// st: 'lock' | 'scan' (ph = 0..1 spins the ring) | 'ok' | 'fail'
function lockScreen2(g, W0, H0, st, ph = 0) {
  const k = W0 / 600; g.scale(k, k); const W = 600, H = H0 / k;
  const bg = g.createLinearGradient(0, 0, 0, H); bg.addColorStop(0, '#24201d'); bg.addColorStop(0.6, '#141210'); bg.addColorStop(1, '#0b0a09'); g.fillStyle = bg; g.fillRect(0, 0, W, H);
  g.textAlign = 'center';
  // padlock above the time: shut while locked, open (shackle lifted) once it knows you
  const open = st === 'ok';
  g.save(); g.translate(W / 2, 168); g.strokeStyle = open ? O : '#d9d5d1'; g.fillStyle = open ? O : '#d9d5d1'; g.lineWidth = 5; g.lineCap = 'round';
  g.beginPath(); g.roundRect(-17, -6, 34, 28, 6); g.fill();
  g.beginPath(); if (open) { g.moveTo(-10, -6); g.lineTo(-10, -18); g.arc(0, -18, 10, Math.PI, 0); g.lineTo(10, -24); } else { g.moveTo(-10, -6); g.lineTo(-10, -16); g.arc(0, -16, 10, Math.PI, 0); g.lineTo(10, -6); } g.stroke(); g.restore();
  g.fillStyle = '#d9d5d1'; g.font = '500 30px Inter'; g.fillText('Friday 23 October', W / 2, 262);
  g.fillStyle = '#f4f3f2'; g.font = '600 168px Inter'; g.fillText('9:41', W / 2, 430);
  // the Face ID glyph in the middle, with the scanning ring while it looks
  const cy = H * 0.66;
  g.save(); g.translate(W / 2 - 51, cy - 51); g.scale(2.55, 2.55);
  g.strokeStyle = st === 'ok' ? O : st === 'fail' ? RED : '#e6e2de'; g.lineWidth = 2; g.lineCap = 'round'; g.lineJoin = 'round';
  if (st === 'fail') g.translate(4 * Math.sin(ph * 40) * (1 - ph), 0);
  g.stroke(FACE_GLYPH); g.restore();
  if (st === 'scan') {
    g.save(); g.translate(W / 2, cy); g.rotate(ph * Math.PI * 4); g.strokeStyle = 'rgba(255,176,112,0.9)'; g.lineWidth = 3.5; g.lineCap = 'round';
    for (let i = 0; i < 3; i++) { g.beginPath(); g.arc(0, 0, 82, i * 2.09, i * 2.09 + 0.9); g.stroke(); } g.restore();
  }
  g.fillStyle = st === 'ok' ? O : st === 'fail' ? RED : '#9e9995'; g.font = '500 28px Inter';
  g.fillText(st === 'ok' ? 'Unlocked' : st === 'fail' ? 'Try again' : st === 'scan' ? 'Looking for you…' : 'Face ID', W / 2, cy + 132);
  g.fillStyle = 'rgba(244,243,242,0.85)'; g.beginPath(); g.roundRect(W / 2 - 110, H - 40, 220, 9, 5); g.fill();
}

/* ------------------------------------------------------------------ HUD bits */
const fmtN = (n) => Math.round(n).toLocaleString('en-US');
// a quiet meter: label, a thin bar, a number, and the verdict on the right
const meter = (q, col, verdict) => `<div class="mt"><div class="mb"><i style="width:${(100 * clamp(q)).toFixed(1)}%;background:${col}"></i></div>`
  + `<b style="color:${col}">${verdict}</b></div>`;
