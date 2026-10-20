import { createGL } from './gl.js';
import { SnowSim } from './sim.js';
import { Renderer } from './render.js';
import { params, habit, habitName, tempC } from './weather.js';

const Q = new URLSearchParams(location.search);
const N = +(Q.get('n') || 768);
const canvas = document.getElementById('gl');
const gl = createGL(canvas);
const sim = new SnowSim(gl, N);
const ren = new Renderer(gl, N);

// ---------------------------------------------------------------- state
const S = {
  time: +(Q.get('t0') || 0), fall: 0,
  wT: 0.58, wH: 0.55,          // current weather (smoothed)
  tT: 0.58, tH: 0.55,          // target weather (mouse)
  zoom: 300, speed: +(Q.get('speed') || 7), maxSteps: 30, drdT: 0.01, boost: 1,
  phase: 'intro', fade: 0, landT: 0,
  trail: [], letters: [],
};
const lerp = (a, b, k) => a + (b - a) * k;
const mix3 = (a, b, k) => [lerp(a[0], b[0], k), lerp(a[1], b[1], k), lerp(a[2], b[2], k)];

// ---------------------------------------------------------------- input
addEventListener('pointermove', e => {
  S.tT = Math.min(1, Math.max(0, e.clientX / innerWidth));
  S.tH = Math.min(1, Math.max(0, 1 - e.clientY / innerHeight));
  S.px = e.clientX / innerWidth - .5; S.py = e.clientY / innerHeight - .5;
});
addEventListener('pointerdown', () => { S.boost = 4; if (S.phase === 'intro') begin(); });
addEventListener('pointerup', () => { S.boost = 1; });
addEventListener('keydown', e => {
  if (e.code === 'Space') { e.preventDefault(); if (S.phase === 'grow') land(); else if (S.phase === 'intro') begin(); }
  if (e.code === 'KeyV') S.vapourOn = !S.vapourOn;
});

function begin() {
  S.phase = 'grow'; document.body.classList.add('growing');
}
// every crystal is born as a tiny hexagonal prism (plate habit) before the weather takes over
const NUCLEUS = params(0.2, 0.0);
function currentParams() { return sim.radius < 7 ? NUCLEUS : params(S.wT, S.wH); }
function newCrystal() {
  sim.reset(NUCLEUS, 1);
  while (sim.T < 4000 && sim.measure() < 6) sim.step(40, NUCLEUS);
  S.trail = []; S.landT = 0; S.born = performance.now();
  S.drdT = 0.01; S.lastMT = 0; S.zoom = zoomFor(sim.radius);
}
function zoomFor(r) { return Math.max(r * 2.7, (canvas.height || 900) * 0.36); }
function land() {
  if (S.phase !== 'grow') return;
  S.phase = 'land'; S.landT = 0;
  S.wantSnap = true;
}
function snapshot() {
  // keep a thumbnail of the current frame's crystal and its journey
  const c = document.createElement('canvas'); c.width = 180; c.height = 180;
  const x = c.getContext('2d');
  const s = Math.min(canvas.width, canvas.height);
  x.drawImage(canvas, (canvas.width - s) / 2, (canvas.height - s) / 2, s, s, 0, 0, 180, 180);
  const letter = { img: c, trail: S.trail.slice(), r: sim.radius, steps: sim.T, habit: habitName(S.wT, S.wH) };
  S.letters.push(letter);
  addLetterCard(letter);
}

// ---------------------------------------------------------------- HUD
const hud = {
  temp: document.getElementById('temp'), hum: document.getElementById('hum'), habit: document.getElementById('habit'),
  size: document.getElementById('size'), nk: document.getElementById('nakaya'), letters: document.getElementById('letters'),
};
const nkx = hud.nk.getContext('2d');
const HABIT_LABEL = { plate: 'hexagonal plate · 六角板', sector: 'sectored plate · 扇形板', stellar: 'stellar plate · 星狀板', fern: 'fern dendrite · 羊齒狀', needle: 'fernlike stellar · 細枝星' };
function drawNakaya() {
  const W = hud.nk.width, H = hud.nk.height, x = nkx;
  x.clearRect(0, 0, W, H);
  // habit map (coarse)
  const cols = { plate: [90, 120, 170], sector: [110, 160, 210], stellar: [150, 200, 240], fern: [220, 240, 255], needle: [200, 220, 255] };
  const cw = 6, ch = 6;
  for (let i = 0; i < W; i += cw) for (let j = 0; j < H; j += ch) {
    const w = habit(i / W, 1 - j / H); let r = 0, g = 0, b = 0;
    for (const k in w) { r += w[k] * cols[k][0]; g += w[k] * cols[k][1]; b += w[k] * cols[k][2]; }
    x.fillStyle = `rgba(${r | 0},${g | 0},${b | 0},0.10)`; x.fillRect(i, j, cw, ch);
  }
  x.strokeStyle = 'rgba(200,215,255,.18)'; x.lineWidth = 1; x.strokeRect(.5, .5, W - 1, H - 1);
  // trail
  const tr = S.trail;
  if (tr.length > 1) {
    x.lineWidth = 1.5; x.lineCap = 'round'; x.lineJoin = 'round';
    for (let i = 1; i < tr.length; i++) {
      x.strokeStyle = `rgba(230,240,255,${0.15 + 0.7 * i / tr.length})`;
      x.beginPath(); x.moveTo(tr[i - 1][0] * W, (1 - tr[i - 1][1]) * H); x.lineTo(tr[i][0] * W, (1 - tr[i][1]) * H); x.stroke();
    }
  }
  const cx = S.wT * W, cy = (1 - S.wH) * H;
  x.fillStyle = '#fff'; x.beginPath(); x.arc(cx, cy, 3, 0, 7); x.fill();
  x.strokeStyle = 'rgba(255,255,255,.35)'; x.beginPath(); x.arc(cx, cy, 8 + 2 * Math.sin(S.time * 3), 0, 7); x.stroke();
}
function addLetterCard(l) {
  const d = document.createElement('div'); d.className = 'letter';
  d.appendChild(l.img);
  const n = document.createElement('span'); n.textContent = '№ ' + S.letters.length; d.appendChild(n);
  hud.letters.appendChild(d);
  requestAnimationFrame(() => d.classList.add('in'));
}

// ---------------------------------------------------------------- palette by weather
const PAL = {
  cold: { cA: [0.42, 0.52, 0.95], cB: [0.012, 0.012, 0.06], cC: [0.015, 0.015, 0.06], warm: [1.0, 0.45, 0.30] },
  mid: { cA: [0.40, 0.75, 0.95], cB: [0.006, 0.022, 0.06], cC: [0.01, 0.025, 0.06], warm: [1.0, 0.55, 0.25] },
  mild: { cA: [0.55, 0.80, 0.85], cB: [0.014, 0.03, 0.05], cC: [0.02, 0.03, 0.05], warm: [1.0, 0.62, 0.35] },
};
function palette(t) {
  return t < .45 ? blendPal(PAL.mild, PAL.mid, t / .45) : blendPal(PAL.mid, PAL.cold, (t - .45) / .55);
}
function blendPal(a, b, k) { const o = {}; for (const key in a) o[key] = mix3(a[key], b[key], k); return o; }

function norm(v) { const l = Math.hypot(...v); return v.map(x => x / l); }
function rotMat(ax, ay, az) {
  const cx = Math.cos(ax), sx = Math.sin(ax), cy = Math.cos(ay), sy = Math.sin(ay), cz = Math.cos(az), sz = Math.sin(az);
  // R = Ry * Rx * Rz (column-major)
  const Rz = [cz, sz, 0, -sz, cz, 0, 0, 0, 1];
  const Rx = [1, 0, 0, 0, cx, sx, 0, -sx, cx];
  const Ry = [cy, 0, -sy, 0, 1, 0, sy, 0, cy];
  return mul(Ry, mul(Rx, Rz));
}
function mul(a, b) { const o = new Array(9); for (let c = 0; c < 3; c++) for (let r = 0; r < 3; r++) { let s = 0; for (let k = 0; k < 3; k++) s += a[k * 3 + r] * b[c * 3 + k]; o[c * 3 + r] = s; } return o; }

// ---------------------------------------------------------------- loop
newCrystal();
let last = performance.now(), acc = 0, frameN = 0;
const scale = +(Q.get('scale') || Math.min(devicePixelRatio || 1, 1.5));
function frame(now) {
  const dt = Q.get('fixdt') ? +Q.get('fixdt') : Math.min(0.05, (now - last) / 1000); last = now; frameN++;
  S.time += dt;
  const W = Math.round(innerWidth * scale), H = Math.round(innerHeight * scale);
  if (canvas.width !== W || canvas.height !== H) { canvas.width = W; canvas.height = H; }
  ren.resize(W, H);

  // weather follows the pointer, with inertia (air masses do not jump)
  S.wT = lerp(S.wT, S.tT, 1 - Math.exp(-dt * 1.5));
  S.wH = lerp(S.wH, S.tH, 1 - Math.exp(-dt * 1.5));

  if (S.phase === 'grow') {
    // adaptive pace: keep the visible growth speed roughly constant whatever the habit
    const want = S.speed * dt * S.boost / Math.max(S.drdT, 0.0015);
    S.maxSteps = dt > 0.03 ? Math.max(4, S.maxSteps * 0.97) : Math.min(90, S.maxSteps + 0.5);
    acc += Math.min(want, S.maxSteps);
    let n = Math.floor(acc); acc -= n;
    if (n > 0) sim.step(n, currentParams());
    if (frameN % 5 === 0) {
      const r0 = sim.radius, t0 = sim.T;
      sim.measure();
      if (S.lastMT && t0 > S.lastMT) {
        const est = (sim.radius - S.lastMR) / (sim.T - S.lastMT);
        if (sim.radius > S.lastMR || sim.T - S.lastMT > 400) { S.drdT = lerp(S.drdT, Math.max(est, 0.0015), 0.35); S.lastMR = sim.radius; S.lastMT = sim.T; }
      } else { S.lastMR = sim.radius; S.lastMT = sim.T; }
      S.trail.push([S.wT, S.wH]);
      if (sim.radius > N / 2 - 70) land();
    }
    S.fall += dt * (0.6 + S.boost * 0.4);
  } else if (S.phase === 'land') {
    S.landT += dt;
    S.fall += dt * 0.2;
    if (S.landT > 2.2) { newCrystal(); S.phase = 'grow'; }
  } else if (S.phase === 'intro') { S.fall += dt * 0.3;
  }
  if (Q.get('steps') && !S.preDone) { // test hook: pre-grow
    S.preDone = true; S.phase = 'grow'; document.body.classList.add('growing');
    const tgt = +Q.get('steps'); while (sim.T < tgt) { sim.step(Math.min(200, tgt - sim.T), params(S.wT, S.wH)); }
    sim.measure();
  }

  const targetZoom = zoomFor(sim.radius);
  S.zoom = lerp(S.zoom, targetZoom, 1 - Math.exp(-dt * 2.0));
  if (Q.get('steps')) S.zoom = targetZoom;

  const pal = palette(S.wT);
  const px = S.px || 0, py = S.py || 0;
  const landK = S.phase === 'land' ? Math.min(1, S.landT / 1.6) : 0;
  const rot = rotMat(0.22 * Math.sin(S.time * 0.21) + py * 0.15 - landK * 0.9, 0.28 * Math.sin(S.time * 0.17 + 1.3) + px * 0.2, S.time * 0.03);
  const fade = S.phase === 'land' ? 1 - Math.max(0, (S.landT - 1.4) / 0.8) : Math.min(1, (S.time) / 1.5);

  ren.frame(sim, {
    time: S.time, fall: S.fall, zoom: S.zoom, rot, tau: 50 * S.boost,
    cA: pal.cA, cB: pal.cB, cC: pal.cC, cWarm: pal.warm, warm: 0.6 + 0.4 * S.wH,
    keyCol: [1.0, 0.95, 0.88], rimCol: [0.55, 0.75, 1.0], iceCol: [0.45, 0.65, 1.0], glowCol: [1.0, 0.92, 0.8],
    glow: 0.5, thick: 2 + sim.radius * 0.02, slope: +(Q.get('slope') || 1.6), bevel: +(Q.get('bevel') || 1.5), edgeGain: +(Q.get('eg') || 0.9),
    lampA: [0.5, 0.9, 1.4], dirA: norm([-0.6, 0.8, 0]), lampB: pal.warm.map(v => v * 1.2), dirB: norm([0.75, -0.55, 0]), lampC: [0.6, 0.2, 0.8], dirC: norm([-0.3, -0.95, 0]), beta: params(S.wT, S.wH).beta, vapour: S.vapourOn ? 1 : 0,
    bokehTint: mix3(pal.cA, [1, 1, 1], .3).map(v => v * .5),
    bloom: Q.get('bloom') != null ? +Q.get('bloom') : 0.3, dbg: +(Q.get('dbg') || 0), bloomThr: 0.9, expo: +(Q.get('expo') || 1.0), fade,
  });

  if (S.wantSnap) { S.wantSnap = false; snapshot(); }
  // HUD
  hud.temp.textContent = tempC(S.wT).toFixed(1) + ' °C';
  hud.hum.textContent = (S.wH * 100 | 0) + ' %';
  hud.habit.textContent = HABIT_LABEL[habitName(S.wT, S.wH)];
  hud.size.textContent = (sim.radius * 2 * 0.0042).toFixed(2) + ' mm';
  if (frameN % 2 === 0) drawNakaya();
  window.__T = sim.T; window.__R = sim.radius; window.__ready = true;
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
window.__S = S; window.__sim = sim; window.__land = land;
