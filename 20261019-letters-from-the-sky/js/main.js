import { createGL } from './gl.js';
import { SnowSim } from './sim.js';
import { Renderer } from './render.js';
import { params, habit, habitName, tempC } from './weather.js';
import { describe, encode, decode, JOURNEY_STEP } from './letters.js';

const Q = new URLSearchParams(location.search);
const N = +(Q.get('n') || 768);
const canvas = document.getElementById('gl');
const gl = createGL(canvas);
const sim = new SnowSim(gl, N);
const ren = new Renderer(gl, N);

const lerp = (a, b, k) => a + (b - a) * k;
const clamp01 = x => Math.min(1, Math.max(0, x));
const ease = x => { x = clamp01(x); return x * x * (3 - 2 * x); };
const easeOut = x => 1 - Math.pow(1 - clamp01(x), 3);
const mix3 = (a, b, k) => [lerp(a[0], b[0], k), lerp(a[1], b[1], k), lerp(a[2], b[2], k)];
const norm = v => { const l = Math.hypot(...v); return v.map(x => x / l); };

// ---------------------------------------------------------------- state
const S = {
  time: +(Q.get('t0') || 0), fall: 0,
  wT: 0.58, wH: 0.62, tT: 0.58, tH: 0.62,       // weather: current (smoothed) and target (pointer)
  zoom: 300, speed: Q.get('speed') != null ? +Q.get('speed') : (Q.get('steps') ? 0 : 7),
  maxSteps: 30, drdT: 0.01, boost: 1,
  phase: 'intro', phaseT: 0,
  trail: [], letters: [], live: null,
  pan: [0, 0], hover: -1, focus: -1,
  script: null,                                   // a journey from a shared link
};

// ---------------------------------------------------------------- timeline (birth weather of every cell)
const STRIDE = 16, TL = new Float32Array(4096 * 4 * 4);
let tlDirtyRow = -1, tlLast = null;
function record(fromT, toT) {
  const w = [S.wT, S.wH];
  const ch = tlLast ? Math.hypot(w[0] - tlLast[0], w[1] - tlLast[1]) : 0;
  for (let slot = Math.floor(fromT / STRIDE); slot <= Math.floor(toT / STRIDE) && slot < 16384; slot++) {
    TL[slot * 4] = w[0]; TL[slot * 4 + 1] = w[1]; TL[slot * 4 + 2] = ch; tlDirtyRow = Math.max(tlDirtyRow, slot >> 12);
  }
  tlLast = w;
}

// ---------------------------------------------------------------- crystals
const NUCLEUS = Object.assign(params(0.2, 0.0), { rho: 0.5 });   // every crystal is born a tiny hexagonal prism
function currentParams() { return params(S.wT, S.wH); }
function zoomFor(r) { return Math.max(r * 2.7, (innerHeight || 900) * 0.36); }
function newCrystal(seedOff = 0) {
  sim.seedOff = seedOff;
  // the seed is a small hexagonal prism, as real snow crystals begin
  sim.reset(Object.assign({}, NUCLEUS, { rho: params(S.wT, S.wH).rho }), 4);
  TL.fill(0); tlLast = null; tlDirtyRow = 3;
  sim.measure();
  S.trail = []; S.drdT = 0.01; S.lastMT = 0; S.zoom = zoomFor(sim.radius); S.growT = 0; S.breathedAt = null;
}

// table slots: a loose hexagonal spiral of letters on the wool
const SPACING = 150;   // spiral step; actual spacing is radius-aware
function slotPos(i) {
  if (i === 0) return [0, 0];
  let ring = 1, k = i - 1;
  while (k >= ring * 6) { k -= ring * 6; ring++; }
  const side = Math.floor(k / ring), off = k % ring;
  const a0 = side * Math.PI / 3 + Math.PI / 6, a1 = a0 + Math.PI / 3;
  const p0 = [Math.cos(a0) * ring, Math.sin(a0) * ring], p1 = [Math.cos(a1) * ring, Math.sin(a1) * ring];
  const u = off / ring, j = Math.abs(Math.sin(i * 12.9898) * 43758.5453) % 1;
  return [(lerp(p0[0], p1[0], u) + j * 0.12) * SPACING, (lerp(p0[1], p1[1], u) - j * 0.1) * SPACING];
}

// ---------------------------------------------------------------- phases
function setPhase(p) { S.phase = p; S.phaseT = 0; document.body.dataset.phase = p; }
// the opening crystal: a plate that met humid air (fern arms) and then dry air again (plate tips)
const INTRO_J = [[0.58, 0.1, 500], [0.58, 0.9, 2600], [0.62, 0.1, 9000]], INTRO_STEPS = +(Q.get('introSteps') || 4300);
function introWeather() { let a = 0; for (const [t, h, n] of INTRO_J) { if (sim.T < a + n) return [t, h]; a += n; } return INTRO_J[INTRO_J.length - 1]; }
function begin() {
  if (S.phase !== 'intro') return;
  audioStart();
  if (S.script) { newCrystal(); setPhase('grow'); return; }
  S.rewZoom0 = S.zoom; setPhase('rewind'); chime(0.8, 0);
}
function land() {
  if (S.phase !== 'grow') return;
  const idx = S.letters.length;
  // twins lie next to their original; everything else takes the first free place on the spiral
  // display scale: small crystals are shown up to 1.6× larger so the collection has even visual weight (labels keep the true size)
  const kNew = Math.min(2.0, Math.max(1, N * 0.26 / Math.max(sim.radius, 1)));
  const live = S.letters.slice(-ren.maxLetters + 1), rNew = sim.radius * kNew;
  const free = p => live.every(l => Math.hypot(l.pos[0] - p[0], l.pos[1] - p[1]) > (l.r * l.k + rNew) * 1.12);
  let pos = null;
  if (S.twinOf) {
    const o = S.letters[S.twinOf - 1];
    for (let k = 0; k < 12 && !pos; k++) { const a = k * Math.PI / 3, d = (o.r * o.k + rNew) * (k < 6 ? 1.15 : 1.6); const c = [o.pos[0] + Math.cos(a) * d, o.pos[1] + Math.sin(a) * d]; if (free(c)) pos = c; }
  }
  for (let k = 0; !pos; k++) { const c = slotPos(k); if (free(c)) pos = c; }
  const L = {
    n: idx + 1, layer: idx % ren.maxLetters, pos, rot: S.twinOf ? S.letters[S.twinOf - 1].rot : (idx * 1.7) % (Math.PI / 3),
    r: sim.radius, k: kNew, steps: sim.T, trail: S.trail.slice(), fallSeconds: S.growT,
    size: sim.radius * 2 * 0.0042, breathed: !!S.breathedAt, twinOf: S.twinOf,
  };
  L.text = describe(L);
  L.code = encode(L.trail, L.steps);
  L.tl = TL.slice(0, (Math.floor(sim.T / STRIDE) + 1) * 4);
  S.letters.push(L); S.live = L; S.focus = -1;
  S.pan = L.pos.slice(); S.landZoom = S.zoom;
  setPhase('land');
  document.body.classList.remove('gift', 'twin');
  showCard(L, true);
  chime(1.0, 0.5);
}
function rise() {
  if (S.phase !== 'gallery' && S.phase !== 'land') return;
  // the live crystal becomes a stored letter; a new one is born in the sky
  ren.pack(S.live.layer, params(S.wT, S.wH).beta);
  hideCard();
  setPhase('rise');
  S.riseFrom = { zoom: S.zoom, pan: S.pan.slice() };
  S.script = null; S.twinOf = null; document.body.classList.remove('gift', 'twin');
  newCrystal();
}
function twin(L) {
  rise();
  newCrystal(0.137 + Math.random() * 0.7);   // exactly the same journey, different molecular noise
  S.script = { tl: L.tl, end: L.steps }; S.twinOf = L.n; document.body.classList.add('gift', 'twin');
  scriptWeather(); S.wT = S.tT; S.wH = S.tH;
}

// ---------------------------------------------------------------- input
const ptr = { x: innerWidth / 2, y: innerHeight / 2 };
addEventListener('pointermove', e => {
  ptr.x = e.clientX; ptr.y = e.clientY; S.lastMove = S.time;
  if (!S.script && S.phase !== 'intro') { S.tT = clamp01(e.clientX / innerWidth); S.tH = clamp01(1 - e.clientY / innerHeight); }
  S.px = e.clientX / innerWidth - .5; S.py = e.clientY / innerHeight - .5;
});
canvas.addEventListener('contextmenu', e => e.preventDefault());
canvas.addEventListener('pointerdown', e => {
  if (e.button === 2) { S.breathing = true; return; }
  if (S.phase === 'intro') return begin();
  if (S.phase === 'grow') S.boost = 4;
  if (S.phase === 'gallery' && S.hover >= 0) { S.focus = S.hover; showCard(S.letters[S.hover], false); }
  else if (S.phase === 'gallery' && S.focus >= 0) { S.focus = -1; hideCard(); }
});
addEventListener('pointerup', e => { if (e.button === 2) S.breathing = false; else S.boost = 1; });
addEventListener('keydown', e => {
  if (e.code === 'Space') {
    e.preventDefault();
    if (S.phase === 'intro') begin(); else if (S.phase === 'grow') land(); else if (S.phase === 'gallery' || S.phase === 'land') rise();
  }
  if (e.code === 'KeyV') S.vapourOn = !S.vapourOn;
  if (e.code === 'KeyB') S.breathing = true;
});
addEventListener('keyup', e => { if (e.code === 'KeyB') S.breathing = false; });

// ---------------------------------------------------------------- HUD
const $ = id => document.getElementById(id);
const CURSOR_NAME = { plate: ['板', 'plate'], sector: ['扇', 'sectored'], stellar: ['星', 'stellar'], fern: ['羊齒', 'fern'], needle: ['細枝', 'fine dendrite'], open: ['樹枝', 'dendrite'] };
const hud = { hint: $('hint'), cursor: $('cursor'), temp: $('temp'), hum: $('hum'), habit: $('habit'), size: $('size'), nk: $('nakaya'), card: $('card'), count: $('count') };
const nkx = hud.nk.getContext('2d');
const HABIT_LABEL = { plate: '六角板 · hexagonal plate', sector: '扇形板 · sectored plate', stellar: '星狀板 · stellar plate', fern: '羊齒狀 · fern dendrite', needle: '細密枝晶 · fernlike stellar', open: '星狀樹枝 · stellar dendrite' };
const HABIT_RGB = { plate: [120, 160, 225], sector: [150, 140, 235], stellar: [140, 205, 240], fern: [240, 225, 185], needle: [205, 180, 240], open: [120, 225, 200] };
// precomputed habit map with labels
const nkMap = (() => {
  // faint region contours, not a filled box: where the habit changes, draw a hairline
  const W = hud.nk.width, H = hud.nk.height, c = document.createElement('canvas'); c.width = W; c.height = H;
  const x = c.getContext('2d'), img = x.createImageData(W, H);
  const name = (i, j) => habitName(i / (W - 1), 1 - j / (H - 1));
  for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
    const k = name(i, j), edge = (i > 0 && name(i - 1, j) !== k) || (j > 0 && name(i, j - 1) !== k);
    const o = (j * W + i) * 4, cl = HABIT_RGB[k];
    img.data[o] = cl[0]; img.data[o + 1] = cl[1]; img.data[o + 2] = cl[2]; img.data[o + 3] = edge ? 90 : 14;
  }
  x.putImageData(img, 0, 0);
  // labels live on their own layer, drawn above the path with a dark halo
  const lc = document.createElement('canvas'); lc.width = W; lc.height = H; const lx = lc.getContext('2d');
  lx.font = '10px Inter, sans-serif'; lx.textAlign = 'center'; lx.lineWidth = 3; lx.strokeStyle = 'rgba(3,5,12,.85)'; lx.fillStyle = 'rgba(220,232,255,.6)';
  const acc = {};
  for (let j = 0; j < H; j += 4) for (let i = 0; i < W; i += 4) { const k = name(i, j); (acc[k] ||= [0, 0, 0]); acc[k][0] += i; acc[k][1] += j; acc[k][2]++; }
  const short = { plate: '板', sector: '扇', stellar: '星', fern: '羊齒', needle: '細枝', open: '樹枝' };
  for (const k in acc) if (acc[k][2] > 30) { const px2 = acc[k][0] / acc[k][2] + 12, py2 = acc[k][1] / acc[k][2] + 3; lx.strokeText(short[k], px2, py2); lx.fillText(short[k], px2, py2); }
  c.labels = lc;
  return c;
})();
// the same map, full screen: the renderer tints the sky with it and colours ice by the habit it froze in
(() => {
  const W = 256, H = 160, d = new Uint8Array(W * H * 4);
  const name = (i, j) => habitName(i / (W - 1), j / (H - 1));
  for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
    const k = name(i, j), cl = HABIT_RGB[k], o = (j * W + i) * 4;
    const edge = (i > 0 && name(i - 1, j) !== k) || (j > 0 && name(i, j - 1) !== k) || (i < W - 1 && name(i + 1, j) !== k) || (j < H - 1 && name(i, j + 1) !== k);
    d[o] = cl[0]; d[o + 1] = cl[1]; d[o + 2] = cl[2]; d[o + 3] = edge ? 255 : 0;
  }
  ren.habitMap(d, W, H);
})();
function drawNakaya(trail, upto = 1, live = true) {
  const W = hud.nk.width, H = hud.nk.height, x = nkx;
  x.clearRect(0, 0, W, H); x.drawImage(nkMap, 0, 0);
  const n = Math.floor(trail.length * upto);
  x.lineWidth = 2.6; x.lineCap = 'round'; x.lineJoin = 'round';
  for (let i = 1; i < n; i++) {
    const cl = HABIT_RGB[habitName(trail[i][0], trail[i][1])];
    x.strokeStyle = `rgba(${cl[0] + 40},${cl[1] + 25},${cl[2]},${0.25 + 0.75 * i / n})`;
    x.beginPath(); x.moveTo(trail[i - 1][0] * W, (1 - trail[i - 1][1]) * H); x.lineTo(trail[i][0] * W, (1 - trail[i][1]) * H); x.stroke();
  }
  x.drawImage(nkMap.labels, 0, 0);
  const p = live ? [S.wT, S.wH] : (n > 0 ? trail[n - 1] : [0.5, 0.5]);
  const cx = p[0] * W, cy = (1 - p[1]) * H;
  x.fillStyle = '#fff'; x.beginPath(); x.arc(cx, cy, 3.2, 0, 7); x.fill();
  x.strokeStyle = 'rgba(255,255,255,.35)'; x.lineWidth = 1; x.beginPath(); x.arc(cx, cy, 8 + 2 * Math.sin(S.time * 3), 0, 7); x.stroke();
}
function showCard(L, typing) {
  const c = hud.card;
  c.innerHTML = `<div class="no"><b>第 ${L.n} 封信</b>Letter № ${L.n}${L.twinOf ? ` · twin of № ${L.twinOf}` : ''}</div>
    <div class="mood"><span class="zh">${L.text.mood[0]}</span><span class="en">${L.text.mood[1]}</span></div>
    <div class="lines">${L.text.lines.map(l => `<p title="${l.en}"><span class="zh">${l.zh}</span></p>`).join('')}</div>
    <div class="meta">${L.size.toFixed(2)} mm · ${Math.round(L.fallSeconds)} s · ${L.steps.toLocaleString()} steps</div>
    <div class="btns"><button id="next">再接一片雪 · catch another<kbd>space</kbd></button><button id="twin">長出它的雙胞胎 · grow its twin</button><button id="copy">複製這封信 · copy letter link</button><button id="card-save">存成明信片 · save as postcard</button></div>`;
  c.classList.remove('show'); void c.offsetWidth;
  c.classList.toggle('typing', typing); c.classList.add('show');
  c.querySelectorAll('.lines p').forEach((p, i) => p.style.transitionDelay = typing ? (2.9 + i * 1.0) + 's' : (i * 0.12) + 's');
  c.querySelector('.mood').style.transitionDelay = typing ? '6.6s' : '.1s';
  c.querySelector('#next').onclick = () => rise();
  c.querySelector('#twin').onclick = () => twin(L);
  c.querySelector('#card-save').onclick = () => { S.wantPostcard = L; };
  c.querySelector('#copy').onclick = e => {
    const url = location.origin + location.pathname + '#letter=' + L.code;
    (navigator.clipboard ? navigator.clipboard.writeText(url) : Promise.reject()).then(() => { e.target.textContent = '已複製 · copied'; }, () => { prompt('Letter link', url); });
  };
}
// a postcard: the frame as it is now (crystal on wool) + the letter, saved as a PNG
function postcard(L) {
  const W = 1800, H = 1100, c = document.createElement('canvas'); c.width = W; c.height = H;
  const x = c.getContext('2d');
  x.fillStyle = '#04050b'; x.fillRect(0, 0, W, H);
  // the crystal bleeds across the left; the frame fades into the paper on the right
  const cw = canvas.width, ch = canvas.height, s = Math.min(ch, cw * 0.62);
  const cx = cw / 2 - (S.phase === 'gallery' && S.focus < 0 ? (S.letters.length > 1 ? 0 : 0.26) : 0.28) * ch;
  const sx = Math.max(0, Math.min(cw - s, cx - s / 2)), sy = (ch - s) / 2;
  x.drawImage(canvas, sx, sy, s, s, -40, 0, H, H);
  const fade = x.createLinearGradient(H * 0.55, 0, H - 70, 0); fade.addColorStop(0, 'rgba(4,5,11,0)'); fade.addColorStop(1, 'rgba(4,5,11,1)');
  x.fillStyle = fade; x.fillRect(H * 0.62, 0, W, H);
  const serif = '"Iowan Old Style", Palatino, "Noto Serif TC", "Songti TC", serif', sans = 'Inter, "Helvetica Neue", sans-serif';
  const tx = H + 10, maxW = W - tx - 80;
  // CJK line breaking: punctuation never starts a line
  const wrap = (t, y, lh) => {
    // CJK breaks between characters (punctuation never starts a line); Latin text breaks between words
    const units = /[\u3000-\u9fff]/.test(t) ? [...t] : t.split(/(?<= )/);
    let line = '';
    for (const u of units) { if (x.measureText(line + u).width > maxW && line && !/^[，。、；：！？）」』,.;:!?)]/.test(u)) { x.fillText(line.trimEnd(), tx, y); y += lh; line = ''; } line += u; }
    x.fillText(line, tx, y); return y + lh; };
  // postmark: the journey on the Nakaya diagram, inside a stamp ring
  const pmx = W - 250, pmy = 70;
  x.save(); x.globalAlpha = 0.9; x.drawImage(hud.nk, pmx, pmy, 180, 116); x.restore();
  x.font = `11px ${sans}`; x.fillStyle = 'rgba(214,224,255,.55)'; x.textAlign = 'center';
  x.fillText(`${new Date().toISOString().slice(0, 10)} · № ${L.n}`, pmx + 90, pmy + 168); x.textAlign = 'left';
  // the letter, anchored low
  let y = 360;
  x.fillStyle = 'rgba(214,224,255,.6)'; x.font = `500 16px ${sans}`; x.fillText(`第 ${L.n} 封信 · LETTER № ${L.n}`, tx, y);
  x.fillStyle = '#e9eefc'; x.font = `30px ${serif}`; y = wrap(L.text.mood[0], y + 56, 44);
  x.font = `italic 20px ${serif}`; x.fillStyle = 'rgba(225,232,255,.75)'; y = wrap(L.text.mood[1], y - 6, 30) + 22;
  for (const l of L.text.lines) { x.font = `16px ${serif}`; x.fillStyle = 'rgba(233,238,252,.88)'; y = wrap(l.zh, y, 25); x.font = `12px ${sans}`; x.fillStyle = 'rgba(214,224,255,.58)'; y = wrap(l.en, y - 5, 18) + 12; }
  x.font = `13px ${sans}`; x.fillStyle = 'rgba(214,224,255,.5)'; x.fillText(`${L.size.toFixed(2)} mm · ${L.steps.toLocaleString()} steps`, tx, H - 110);
  x.font = `24px ${serif}`; x.fillStyle = '#e9eefc'; x.fillText('天空寄來的信', tx, H - 64);
  x.font = `12px ${sans}`; x.fillStyle = 'rgba(214,224,255,.5)'; x.fillText('LETTERS FROM THE SKY', tx + 168, H - 66);
  const a = document.createElement('a'); a.download = `letter-from-the-sky-${L.n}.png`; a.href = c.toDataURL('image/png'); a.click();
}
const labelBox = document.getElementById('labels');
function labels(alpha) {
  labelBox.style.opacity = alpha;
  if (alpha <= 0.01) return;
  while (labelBox.children.length < S.letters.length) labelBox.appendChild(document.createElement('div'));
  S.letters.forEach((l, i) => {
    const d = labelBox.children[i];
    const x = innerWidth / 2 + ((l.pos[0] + l.r * l.k * 0.78) - S.pan[0]) / S.zoom * innerHeight;
    const y = innerHeight / 2 - ((l.pos[1] - l.r * l.k * 0.78) - S.pan[1]) / S.zoom * innerHeight;
    if (d.dataset.n !== String(l.n)) { d.dataset.n = l.n; d.innerHTML = `№ ${l.n}<span>${NAMES_SHORT[l.text.habit] || ''}${l.twinOf ? ' · twin' : ''}</span>`; }
    d.style.transform = `translate(${x}px, ${y}px)`;
    d.classList.toggle('hot', S.hover === i);
  });
}
const NAMES_SHORT = { tipped: '端板樹枝 plate-tipped', plate: '六角板 plate', sector: '扇形板 sector', stellar: '星狀板 stellar', fern: '羊齒 fern', needle: '細枝 fine', open: '樹枝 dendrite' };
function hideCard() { hud.card.classList.remove('show'); }

// ---------------------------------------------------------------- audio (gentle, synthesised; starts on first click)
let AC = null, master = null;
function audioStart() {
  if (AC || Q.get('mute')) return;
  try {
    AC = new AudioContext(); master = AC.createGain(); master.gain.value = 0.0; master.connect(AC.destination);
    master.gain.linearRampToValueAtTime(0.5, AC.currentTime + 3);
    const buf = AC.createBuffer(1, AC.sampleRate * 4, AC.sampleRate), d = buf.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    const src = AC.createBufferSource(); src.buffer = buf; src.loop = true;
    const bp = AC.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 420; bp.Q.value = 0.6;
    const g = AC.createGain(); g.gain.value = 0.05; src.connect(bp).connect(g).connect(master); src.start();
    S.wind = { bp, g };
  } catch (e) { AC = null; }
}
const PENTA = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21];
function chime(level, pan = 0) {
  if (!AC) return;
  const t = AC.currentTime, f = 880 * Math.pow(2, PENTA[(Math.random() * PENTA.length) | 0] / 12) * (S.wT > 0.5 ? 1 : 0.75);
  const o = AC.createOscillator(), o2 = AC.createOscillator(), g = AC.createGain(), p = AC.createStereoPanner();
  o.type = 'sine'; o.frequency.value = f; o2.type = 'sine'; o2.frequency.value = f * 2.76;
  g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(0.05 * level, t + 0.005); g.gain.exponentialRampToValueAtTime(0.0001, t + 2.2);
  p.pan.value = Math.max(-1, Math.min(1, pan));
  o.connect(g); o2.connect(g); g.connect(p).connect(master); o.start(t); o2.start(t); o.stop(t + 2.3); o2.stop(t + 2.3);
}

// ---------------------------------------------------------------- palette by weather
const PAL = {
  cold: { cA: [0.42, 0.52, 0.95], cB: [0.012, 0.012, 0.05], cC: [0.004, 0.004, 0.016], warm: [1.0, 0.45, 0.30] },
  mid: { cA: [0.40, 0.75, 0.95], cB: [0.004, 0.018, 0.045], cC: [0.002, 0.006, 0.014], warm: [1.0, 0.55, 0.25] },
  mild: { cA: [0.45, 0.85, 0.80], cB: [0.010, 0.026, 0.040], cC: [0.004, 0.008, 0.012], warm: [1.0, 0.62, 0.35] },
};
const blendPal = (a, b, k) => { const o = {}; for (const key in a) o[key] = mix3(a[key], b[key], k); return o; };
const palette = t => t < .45 ? blendPal(PAL.mild, PAL.mid, t / .45) : blendPal(PAL.mid, PAL.cold, (t - .45) / .55);

function rotMat(ax, ay, az) {
  const cx = Math.cos(ax), sx = Math.sin(ax), cy = Math.cos(ay), sy = Math.sin(ay), cz = Math.cos(az), sz = Math.sin(az);
  const Rz = [cz, sz, 0, -sz, cz, 0, 0, 0, 1], Rx = [1, 0, 0, 0, cx, sx, 0, -sx, cx], Ry = [cy, 0, -sy, 0, 1, 0, sy, 0, cy];
  return mul(Ry, mul(Rx, Rz));
}
function mul(a, b) { const o = new Array(9); for (let c = 0; c < 3; c++) for (let r = 0; r < 3; r++) { let s = 0; for (let k = 0; k < 3; k++) s += a[k * 3 + r] * b[c * 3 + k]; o[c * 3 + r] = s; } return o; }

// ---------------------------------------------------------------- shared letter link
const hashCode = (location.hash.match(/letter=([\w-]+)/) || [])[1];
if (hashCode) {
  const pts = decode(hashCode);
  if (pts) { S.script = pts; document.body.classList.add('gift'); S.wT = S.tT = pts[0][0]; S.wH = S.tH = pts[0][1]; }
}
function scriptWeather() {
  if (S.script.tl) {   // a twin: the original's exact timeline
    const i = Math.min(S.script.tl.length / 4 - 1, Math.floor(sim.T / STRIDE));
    S.tT = S.script.tl[i * 4]; S.tH = S.script.tl[i * 4 + 1];
    return sim.T >= S.script.end;
  }
  const i = Math.min(S.script.length - 1, Math.floor(sim.T / JOURNEY_STEP));
  S.tT = S.script[i][0]; S.tH = S.script[i][1];
  return sim.T >= S.script.length * JOURNEY_STEP;
}

// ---------------------------------------------------------------- loop
newCrystal();
setPhase('intro');
let last = performance.now(), acc = 0, frameN = 0, glowPulse = 0;
const maxScale = +(Q.get('scale') || Math.min(devicePixelRatio || 1, 1.5));
let scale = Math.min(maxScale, 1), ftAvg = 1 / 60, scaleCool = 0;
const stats = Q.get('stats') ? Object.assign(document.body.appendChild(document.createElement('div')), { style: 'position:fixed;right:8px;bottom:8px;font:11px monospace;color:#8af;z-index:9' }) : null;
function frame(now) {
  const realDt = (now - last) / 1000;
  const dt = Q.get('fixdt') ? +Q.get('fixdt') : Math.min(0.05, realDt); last = now; frameN++;
  S.time += dt; S.phaseT += dt;
  // dynamic resolution: keep the frame near 60 fps on weaker GPUs
  if (!Q.get('fixdt') && realDt < 0.25) {
    ftAvg = lerp(ftAvg, realDt, 0.05); scaleCool -= realDt;
    if (scaleCool < 0 && !Q.get('scale')) {
      if (ftAvg > 1 / 45 && scale > 0.55) { scale = Math.max(0.55, scale * 0.88); scaleCool = 1.2; }
      else if (ftAvg < 1 / 58 && scale < maxScale) { scale = Math.min(maxScale, scale * 1.06); scaleCool = 2.5; }
    }
  }
  if (stats && frameN % 15 === 0) stats.textContent = `${(ftAvg * 1000).toFixed(1)} ms · scale ${scale.toFixed(2)} · steps/frame ${S.maxSteps | 0} · T ${sim.T} · R ${sim.radius}`;
  const W = Math.round(innerWidth * scale), H = Math.round(innerHeight * scale);
  if (canvas.width !== W || canvas.height !== H) { canvas.width = W; canvas.height = H; }
  ren.resize(W, H);

  // weather follows the pointer with inertia (air masses do not jump); a shared letter replays its journey
  if (S.script && S.phase === 'grow' && scriptWeather()) land();
  if (S.script && S.phase === 'grow') scriptWeather();
  const wk = S.script && S.script.tl ? 1 : 1 - Math.exp(-dt * (S.script ? 6 : 1.5));
  S.wT = lerp(S.wT, S.tT, wk); S.wH = lerp(S.wH, S.tH, wk);

  let woolMix = 0, focusBlur = 1, replay = 2, ofs = [0, 0], tableZoom = S.zoom, landK = 0, fade = 1;
  glowPulse = 0;
  if (S.phase === 'grow') {
    S.growT += dt;
    if (!S.hinted && S.growT > 8 && !S.script) { S.hinted = true; hud.hint.classList.add('show'); setTimeout(() => hud.hint.classList.remove('show'), 3800); }
    const want = S.speed * dt * S.boost / Math.max(S.drdT, 0.0015);
    S.maxSteps = Q.get('nocap') ? +Q.get('nocap') : realDt > 0.03 ? Math.max(4, S.maxSteps * 0.97) : Math.min(90, S.maxSteps + 0.5);
    acc += Math.min(want, S.maxSteps);
    let n = Math.floor(acc); acc -= n;
    S.breath = lerp(S.breath || 0, S.breathing ? 1 : 0, 1 - Math.exp(-dt * (S.breathing ? 4 : 2)));
    if (S.breath > 0.05) {
      // warm breath: no growth, the ice under the pointer sublimates
      const spin = S.time * 0.03, sx = (ptr.x - innerWidth / 2) / innerHeight, sy = (innerHeight / 2 - ptr.y) / innerHeight;
      const lx = sx * S.zoom, ly = sy * S.zoom, c = Math.cos(-spin), s2 = Math.sin(-spin);
      sim.sublimate(3, 0.09 * S.breath, [c * lx - s2 * ly, s2 * lx + c * ly], 0.2 * S.zoom);
      if (!S.breathedAt) S.breathedAt = [S.wT, S.wH];
      n = 0; acc = 0;
    }
    if (n > 0 && S.speed > 0) { const t0 = sim.T; sim.step(n, currentParams()); record(t0, sim.T); }
    if (frameN % 5 === 0) {
      const rOld = sim.radius;
      sim.measure();
      if (S.lastMT && sim.T > S.lastMT) {
        if (sim.radius > S.lastMR || sim.T - S.lastMT > 400) { S.drdT = lerp(S.drdT, Math.max((sim.radius - S.lastMR) / (sim.T - S.lastMT), 0.0015), 0.35); S.lastMR = sim.radius; S.lastMT = sim.T; }
      } else { S.lastMR = sim.radius; S.lastMT = sim.T; }
      S.trail.push([S.wT, S.wH, sim.T]);
      if (sim.radius > rOld && S.time - (S.lastChime || 0) > 0.35 + Math.random() * 0.5) { S.lastChime = S.time; chime(0.25 + Math.random() * 0.3, (Math.random() - .5) * 1.2); }
      if (sim.radius > N / 2 - 70) land();
    }
    S.fall += dt * (0.6 + S.boost * 0.4);
    S.zoom = lerp(S.zoom, zoomFor(sim.radius), 1 - Math.exp(-dt * 2.0));
    tableZoom = S.zoom;
    if (S.phaseT < 1.5 && S.riseFrom) fade = ease(S.phaseT / 0.6 + 0.5);
  } else if (S.phase === 'land' || S.phase === 'gallery') {
    const L = S.phaseT, live = S.live;
    if (S.phase === 'land' && L > 9.5) { setPhase('gallery'); if (S.letters.length > 1) hideCard(); }
    const LL = S.phase === 'gallery' ? 99 : L;
    landK = ease(LL / 2.0);
    const woolMix0 = easeOut(LL / 1.8);
    woolMix = woolMix0;
    focusBlur = lerp(1, 0.12, ease((LL - 0.3) / 1.6));          // rack focus onto the wool
    S.fall += dt * 0.6 * (1 - landK);
    // read the letter: the crystal regrows in 4 s, in step with its journey
    if (S.phase === 'land') replay = L < 2.7 ? 2 : L < 6.9 ? Math.max(0.02, easeOut((L - 2.7) / 4.2)) : 2;
    if (S.phase === 'land' && L > 2.7 && L < 6.9 && S.time - (S.lastChime || 0) > 0.22) { S.lastChime = S.time; chime(0.35, (Math.random() - .5)); }
    glowPulse = S.phase === 'land' ? 0.3 * Math.exp(-Math.pow((L - 1.9) / 0.3, 2)) : 0;
    S.sweep = S.phase === 'land' && L > 1.3 && L < 2.5 ? [lerp(-0.9, 0.6, (L - 1.3) / 1.2), 0.5 * Math.sin(Math.PI * clamp01((L - 1.3) / 1.2))] : [0, 0];
    // pull back to the whole collection
    const pts = S.letters.map(l => l.pos);
    const cen = pts.reduce((a, p) => [a[0] + p[0] / pts.length, a[1] + p[1] / pts.length], [0, 0]);
    // fit every letter: vertically within ±0.42 of the screen height, horizontally within ±0.5 (left of the card)
    const cen0 = cen.slice();
    const cardUp = !(S.phase === 'gallery' && S.focus < 0 && S.letters.length > 1);
    let need = 0; S.letters.forEach(l => { need = Math.max(need, (Math.abs(l.pos[1] - cen[1]) + l.r * l.k) / 0.42, (Math.abs(l.pos[0] - cen[0]) + l.r * l.k) / (cardUp ? 0.42 : 0.7)); });
    const galleryZoom = Math.max(S.landZoom * 1.35, need);
    if (cardUp) cen[0] += 0.26 * galleryZoom;   // the collection sits left of the letter card
    const focusL = S.focus >= 0 ? S.letters[S.focus] : null;
    const pk = S.phase === 'gallery' ? 1 : ease((L - 7.0) / 2.5);
    const lp0 = [live.pos[0] + 0.28 * S.landZoom * ease(LL / 2.5), live.pos[1]];   // slide left of the letter card
    let zT = lerp(S.landZoom, galleryZoom, pk), pT = [lerp(lp0[0], cen[0], pk), lerp(lp0[1], cen[1], pk)];
    if (S.phase === 'gallery' && focusL) { zT = zoomFor(focusL.r * focusL.k) * 1.15; pT = [focusL.pos[0] + 0.28 * zT, focusL.pos[1]]; }
    if (S.phase === 'gallery') {
      // slow drift, as if the camera were breathing
      pT = [pT[0] + Math.sin(S.time * 0.11) * zT * 0.012, pT[1] + Math.sin(S.time * 0.083 + 1) * zT * 0.009]; zT *= 1 + 0.01 * Math.sin(S.time * 0.07);
      const k2 = 1 - Math.exp(-dt * 2.5); S.zoom = lerp(S.zoom, zT, k2); S.pan = [lerp(S.pan[0], pT[0], k2), lerp(S.pan[1], pT[1], k2)]; }
    else { S.zoom = zT; S.pan = pT; }
    tableZoom = S.zoom;
    S.liveK = S.phase === 'gallery' ? live.k : lerp(1, live.k, pk);
    ofs = [(live.pos[0] - S.pan[0]) / S.zoom, (live.pos[1] - S.pan[1]) / S.zoom];
    focusBlur = lerp(focusBlur, 0.2, pk * (focusL ? 0 : 1));
    // hover: which letter is under the pointer
    if (S.phase === 'gallery') {
      const sx = (ptr.x - innerWidth / 2) / innerHeight, sy = (innerHeight / 2 - ptr.y) / innerHeight;
      const q = [sx * S.zoom + S.pan[0], sy * S.zoom + S.pan[1]];
      S.hover = -1;
      S.letters.forEach((l, i) => { if (i >= S.letters.length - ren.maxLetters && Math.hypot(q[0] - l.pos[0], q[1] - l.pos[1]) < l.r * l.k * 1.05) S.hover = i; });
      canvas.style.cursor = S.hover >= 0 ? 'pointer' : 'default';
    }
    // light pool centred on the collection; specimen labels beside each letter
    const cs = [lerp(live.pos[0], cen0[0], pk) - S.pan[0], lerp(live.pos[1], cen0[1], pk) - S.pan[1]].map(v => v / S.zoom);
    S.spot = [cs[0], cs[1], lerp(0.9, Math.max(0.5, (need || 1) / S.zoom * 0.75), pk)];
    labels(pk * (S.focus >= 0 ? 0 : 1));
  } else if (S.phase === 'rise') {
    labels(0);
    const L = S.phaseT;
    woolMix = 1 - easeOut(L / 1.2); focusBlur = lerp(0.2, 1, ease(L / 1.0));
    S.pan = S.riseFrom.pan; tableZoom = S.riseFrom.zoom * (1 + L * 0.8);
    S.fall += dt * 0.8 * ease(L);
    S.zoom = zoomFor(sim.radius);
    if (L > 1.4) { setPhase('grow'); canvas.style.cursor = 'crosshair'; S.hover = -1; }
  } else if (S.phase === 'rewind') {
    // time runs backwards: the opening crystal shrinks back into its seed, then yours begins
    replay = Math.max(0.001, 1 - ease(S.phaseT / 1.6));
    S.zoom = lerp(S.rewZoom0, zoomFor(6), ease(S.phaseT / 1.6));
    tableZoom = S.zoom; ofs = [0, 0.075 * (1 - ease(S.phaseT / 1.6))];
    S.fall -= dt * 0.8;
    if (S.phaseT > 1.75) { newCrystal(); setPhase('grow'); }
  } else {
    S.fall += dt * 0.3;
    fade = Math.min(1, S.time / 1.5);
    if (!S.script && sim.T < INTRO_STEPS && !Q.get('steps')) {
      S.maxSteps = realDt > 0.03 ? Math.max(8, S.maxSteps * 0.95) : Math.min(140, S.maxSteps + 2);
      const n = Math.min(INTRO_STEPS - sim.T, Q.get('fixdt') ? 400 : Math.round(S.maxSteps));
      const w = introWeather(); S.wT = S.tT = w[0]; S.wH = S.tH = w[1];
      const t0 = sim.T; sim.step(n, currentParams()); record(t0, sim.T);
      if (frameN % 5 === 0) sim.measure();
    }
    S.zoom = lerp(S.zoom, zoomFor(sim.radius) * 1.22, 1 - Math.exp(-dt * 2.0));
    tableZoom = S.zoom; ofs = [0, 0.075];
  }

  if (Q.get('steps') && !S.preDone) { // test hook: pre-grow along an optional journey
    S.preDone = true; setPhase('grow');
    const tgt = +Q.get('steps'); const J = JSON.parse(Q.get('j') || '[]'); let acc2 = 0, ji = 0;
    while (sim.T < tgt) {
      if (J.length) { while (ji < J.length - 1 && sim.T >= acc2 + J[ji][2]) { acc2 += J[ji][2]; ji++; } S.wT = S.tT = J[ji][0]; S.wH = S.tH = J[ji][1]; }
      const t0 = sim.T; sim.step(Math.min(50, tgt - sim.T), currentParams()); record(t0, sim.T);
      if (sim.T % 250 < 50) { sim.measure(); S.trail.push([S.wT, S.wH, sim.T]); }
    }
    sim.measure(); S.zoom = zoomFor(sim.radius); S.growT = tgt / 200;
    if (Q.get('land')) land();
  }

  if (window.__replay != null) replay = window.__replay;
  const pal = palette(S.wT);
  const px = S.px || 0, py = S.py || 0;
  const growPose = [0.22 * Math.sin(S.time * 0.21) + py * 0.15, 0.28 * Math.sin(S.time * 0.17 + 1.3) + px * 0.2, S.time * 0.03];
  const tablePose = [-0.05, 0.03, S.live ? S.live.rot : 0];
  const k = S.phase === 'land' || S.phase === 'gallery' ? landK : 0;
  const rot = rotMat(lerp(growPose[0], tablePose[0], k), lerp(growPose[1], tablePose[1], k), lerp(growPose[2], tablePose[2], k));
  const onTable = S.phase === 'land' || S.phase === 'gallery';
  const stored = S.letters.slice(0, S.letters.length - (onTable ? 1 : 0)).slice(-ren.maxLetters);
  const nLetters = stored.length;
  const slots = new Float32Array(64);
  for (const l of stored) slots.set([l.pos[0], l.pos[1], l.rot, N / ren.NL * l.k], l.layer * 4);

  if (tlDirtyRow >= 0) { ren.timeline(TL, tlDirtyRow + 1); tlDirtyRow = -1; }
  ren.frame(sim, {
    stride: STRIDE, ringK: +(Q.get('ring') || 3), terrace: +(Q.get('terr') || 1.5),
    time: S.time, fall: S.fall, zoom: S.phase === 'rise' ? S.zoom : tableZoom / (onTable && S.liveK ? S.liveK : 1), rot, tau: 50 * S.boost, ofs, replay,
    cA: pal.cA, cB: pal.cB, cC: pal.cC, cWarm: pal.warm, warm: 0.6 + 0.4 * S.wH,
    keyCol: [1.0, 0.95, 0.88], rimCol: [0.55, 0.75, 1.0], iceCol: [0.45, 0.65, 1.0], glowCol: HABIT_RGB[habitName(S.wT, S.wH)].map(v => 0.35 + v / 255 * 0.75),
    sweepPos: S.sweep ? S.sweep[0] : 0, sweepAmt: (S.phase === 'land' && S.sweep) ? S.sweep[1] : 0,
    glow: 0.5 + glowPulse * 1.5, thick: lerp(2 + sim.radius * 0.02, 1.2, k),
    slope: +(Q.get('slope') || 1.6), bevel: +(Q.get('bevel') || 0.6), edgeGain: +(Q.get('eg') || 0.9) * (1 + glowPulse * .8 + (S.hover >= 0 && S.letters[S.hover] === S.live ? .35 : 0)),
    lampA: [0.5, 0.9, 1.4], dirA: norm([-0.6, 0.8, 0]), lampB: pal.warm.map(v => v * 1.2), dirB: norm([0.75, -0.55, 0]), lampC: [0.6, 0.2, 0.8], dirC: norm([-0.3, -0.95, 0]),
    beta: params(S.wT, S.wH).beta, rho0: params(S.wT, S.wH).rho, vapour: S.vapourOn ? 1 : 0,
    bokehTint: mix3(pal.cA, [1, 1, 1], .3).map(v => v * .35 * (1 - woolMix)),
    mapK: S.phase === 'grow' && !S.script ? 1 : 0, cursor: [ptr.x / innerWidth, 1 - ptr.y / innerHeight],
    shadowK: (S.phase === 'land' || S.phase === 'gallery') ? landK : 0, livePos: S.live ? S.live.pos : [0, 0], liveRot: S.live ? S.live.rot : 0, liveK: onTable && S.liveK ? S.liveK : 1,
    spot: S.spot || [0, 0, 9],
    woolMix, focusBlur, tilt: 0.55, sparkle: 1, pan: S.pan, tableZoom,
    woolCol: [0.020, 0.025, 0.040], woolCol2: [0.042, 0.030, 0.046],
    galleryAlpha: S.phase === 'land' ? ease((S.phaseT - 6.8) / 2.0) : 1,
    letters: nLetters, slots, hoverId: S.hover >= 0 && S.letters[S.hover] !== S.live ? S.letters[S.hover].layer : -1,
    breath: [ptr.x / innerWidth, 1 - ptr.y / innerHeight, (S.breath || 0) * (S.phase === 'grow' ? 1 : 0)],
    bloom: Q.get('bloom') != null ? +Q.get('bloom') : 0.3, dbg: +(Q.get('dbg') || 0), bloomThr: 0.9, expo: +(Q.get('expo') || 1.0), fade,
  });

  if (S.wantPostcard) { postcard(S.wantPostcard); S.wantPostcard = null; }
  // HUD
  hud.temp.textContent = tempC(S.wT).toFixed(1).replace('-', '−') + ' °C';
  hud.hum.textContent = (S.wH * 100 | 0) + ' %';
  hud.habit.textContent = HABIT_LABEL[habitName(S.wT, S.wH)];
  if (S.phase === 'rewind' || S.phase === 'intro') S.trail.length = 0;
  hud.size.textContent = (sim.radius * 2 * 0.0042).toFixed(2) + ' mm';
  if (S.phase === 'grow' && !S.script) {
    const hb = habitName(S.tT, S.tH);
    if (hud.cursor.dataset.h !== hb) { hud.cursor.dataset.h = hb; hud.cursor.innerHTML = `<b>${CURSOR_NAME[hb][0]}</b>${CURSOR_NAME[hb][1]}`; }
    hud.cursor.style.transform = `translate(${ptr.x + 18}px, ${ptr.y + 14}px)`;
    hud.cursor.style.opacity = S.time - (S.lastMove || 0) < 2.5 ? 1 : 0.25;
  } else hud.cursor.style.opacity = 0;
  hud.count.textContent = S.letters.length ? `${S.letters.length} 封信 · letters` : '';
  if (frameN % 2 === 0) {
    if (onTable && S.live) drawNakaya((S.focus >= 0 ? S.letters[S.focus] : S.live).trail, S.phase === 'land' ? clamp01((S.phaseT - 2.7) / 4.2) : 1, false);
    else drawNakaya(S.trail);
  }
  if (S.wind && AC) { S.wind.bp.frequency.value = 300 + S.wT * 500 - (S.breath || 0) * 150; S.wind.g.gain.value = 0.02 + 0.05 * S.wH * (S.phase === 'grow' ? 1 : 0.4) + (S.breath || 0) * 0.12; }
  window.__T = sim.T; window.__R = sim.radius; window.__phase = S.phase; window.__ready = true;
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
window.__S = S; window.__sim = sim; window.__land = land; window.__rise = rise;
// test hook: grow a crystal synchronously along a journey [[t, h, steps], ...] and land it
window.__autoLetter = (J, total) => {
  if (S.phase === 'land' || S.phase === 'gallery') rise();
  if (S.phase === 'intro' || S.phase === 'rewind') newCrystal();
  if (S.phase !== 'grow') setPhase('grow');
  let acc2 = 0, ji = 0;
  while (sim.T < total && sim.radius < N / 2 - 70) {
    while (ji < J.length - 1 && sim.T >= acc2 + J[ji][2]) { acc2 += J[ji][2]; ji++; }
    S.wT = S.tT = J[ji][0]; S.wH = S.tH = J[ji][1];
    const t0 = sim.T; sim.step(Math.min(50, total - sim.T), currentParams()); record(t0, sim.T);
    if (sim.T % 250 < 50) { sim.measure(); S.trail.push([S.wT, S.wH, sim.T]); }
  }
  sim.measure(); S.zoom = zoomFor(sim.radius); S.growT = total / 180;
  land();
};
