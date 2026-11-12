import * as S from './shaders.js';
import { buildLUT, filmRGB } from './film.js';
import { epitaph } from './story.js';
import { Sound } from './audio.js';

const N = 256;               // film texels across one hemisphere
const M = 32;                // stats grid across one hemisphere
const SLOW = 200;            // the pop is shown this many times slower than real
const R_PHYS = 0.04;         // a full breath makes a 4 cm bubble
const R_MIN = 0.65;          // a quick puff makes one about two thirds that size
const H_MAX = 4000, LUT_N = 640, LUT_C = 24;
const P = { buoy: 2.2, noise: 0.04, vort: 0.1, damp: 0.3, drain: 0.075, evap: 3.2 };

const qs = new URLSearchParams(location.search);
const canvas = document.getElementById('c');
const gl = canvas.getContext('webgl2', { antialias: false, alpha: false, preserveDrawingBuffer: qs.has('shot') });
const ui = (id) => document.getElementById(id);
if (!gl || !gl.getExtension('EXT_color_buffer_float')) {
  ui('nogl').hidden = false;
  throw new Error('WebGL2 with float render targets is required');
}

// ---------- GL plumbing ----------
function compile(type, src) {
  const s = gl.createShader(type);
  gl.shaderSource(s, src); gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s) + '\n' + src.slice(0, 200));
  return s;
}
function program(fs, vs = S.VS) {
  const p = gl.createProgram();
  gl.attachShader(p, compile(gl.VERTEX_SHADER, vs));
  gl.attachShader(p, compile(gl.FRAGMENT_SHADER, fs));
  gl.bindAttribLocation(p, 0, 'aPos');
  gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
  const u = {};
  const n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
  for (let i = 0; i < n; i++) { const a = gl.getActiveUniform(p, i); u[a.name] = gl.getUniformLocation(p, a.name); }
  return { p, u };
}
function texture(w, h, fmt, data = null, filter = gl.LINEAR, mips = false) {
  const t = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, t);
  const [ifmt] = fmt;
  gl.texImage2D(gl.TEXTURE_2D, 0, ifmt, w, h, 0, gl.RGBA, gl.FLOAT, data);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, mips ? gl.LINEAR_MIPMAP_LINEAR : filter);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, filter);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  if (mips) gl.generateMipmap(gl.TEXTURE_2D);
  return t;
}
function target(w, h, fmt, data, mips) {
  const tex = texture(w, h, fmt, data, gl.LINEAR, mips);
  const fb = gl.createFramebuffer();
  gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
  return { tex, fb, w, h, mips };
}
function pingpong(w, h, fmt, data, mips) {
  const a = target(w, h, fmt, data, mips), b = target(w, h, fmt, data, mips);
  return { get r() { return a.swap ? b : a; }, get w() { return a.swap ? a : b; }, swap() { a.swap = !a.swap; }, a, b };
}
const F16 = [gl.RGBA16F], F32 = [gl.RGBA32F];

const quad = gl.createVertexArray();
gl.bindVertexArray(quad);
const qb = gl.createBuffer();
gl.bindBuffer(gl.ARRAY_BUFFER, qb);
gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
gl.enableVertexAttribArray(0);
gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);

const prog = {
  force: program(S.FS_FORCE), curl: program(S.FS_CURL), advect: program(S.FS_ADVECT),
  div: program(S.FS_DIV), jacobi: program(S.FS_JACOBI), grad: program(S.FS_GRAD),
  thick: program(S.FS_THICK), rim: program(S.FS_RIM), down: program(S.FS_DOWN),
  render: program(S.FS_RENDER),
  scale: program(`#version 300 es
precision highp float; in vec2 vUv; out vec4 o; uniform sampler2D H; uniform float uK;
void main(){ o = vec4(min(texture(H, vUv).x*uK, 4000.), 0., 0., 1.); }`),
};

const W2 = 2 * N;
const U = pingpong(W2, N, F16), Pr = pingpong(W2, N, F16), T = pingpong(W2, N, F16);
const Hf = pingpong(W2, N, F16, null, true);
const Cu = target(W2, N, F16), Dv = target(W2, N, F16), Ut = target(W2, N, F16);
const Down = target(2 * M, M, F32);
const lut = texture(LUT_N, LUT_C, F16, buildLUT(LUT_N, LUT_C, H_MAX));

function run(pr, out, uniforms) {
  gl.useProgram(pr.p);
  let unit = 0;
  for (let [k, v] of Object.entries(uniforms)) {
    const loc = pr.u[k];
    if (loc == null) continue;
    if (v && v.tex !== undefined) v = v.tex;
    if (v instanceof WebGLTexture) { gl.activeTexture(gl.TEXTURE0 + unit); gl.bindTexture(gl.TEXTURE_2D, v); gl.uniform1i(loc, unit++); }
    else if (typeof v === 'number') gl.uniform1f(loc, v);
    else if (v.length === 16) gl.uniform4fv(loc, v);
    else if (v.length === 2) gl.uniform2fv(loc, v);
    else if (v.length === 3) gl.uniform3fv(loc, v);
    else gl.uniform4fv(loc, v);
  }
  if (out) { gl.bindFramebuffer(gl.FRAMEBUFFER, out.fb); gl.viewport(0, 0, out.w, out.h); }
  else { gl.bindFramebuffer(gl.FRAMEBUFFER, null); gl.viewport(0, 0, canvas.width, canvas.height); }
  gl.bindVertexArray(quad);
  gl.drawArrays(gl.TRIANGLES, 0, 3);
}

// ---------- the film's starting state ----------
function rng(seed) { let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }
function freshFilm(seed) {
  const r = rng(seed);
  const waves = Array.from({ length: 10 }, (_, i) => [(r() - 0.5) * (3 + i * 1.8), (r() - 0.5) * (3 + i * 1.8), r() * 6.28, 1 / (1 + i * 0.6)]);
  const d = new Float32Array(W2 * N * 4);
  for (let j = 0; j < N; j++) for (let i = 0; i < W2; i++) {
    const x = ((i % N) + 0.5) / N * 2 - 1, y = (j + 0.5) / N * 2 - 1, hemi = i >= N ? 1 : 0;
    let n = 0;
    for (const [kx, ky, ph, a] of waves) n += a * Math.sin(kx * x + ky * y + ph + hemi * 2.1);
    const h = 760 * (1 + 0.16 * n) * (1 + 0.35 * Math.max(0, -y)) * (1 - 0.12 * Math.max(0, y));
    d[(j * W2 + i) * 4] = h;
  }
  return d;
}
function upload(pp, data) {
  for (const t of [pp.a, pp.b]) {
    gl.bindTexture(gl.TEXTURE_2D, t.tex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA16F, W2, N, 0, gl.RGBA, gl.FLOAT, data);
    if (t.mips) gl.generateMipmap(gl.TEXTURE_2D);
  }
}
const zeros = new Float32Array(W2 * N * 4);
function seedHole(x, y, hemi) {
  const d = new Float32Array(W2 * N * 4).fill(6e4);
  const ci = Math.floor((x * 0.5 + 0.5) * N) + hemi * N, cj = Math.floor((y * 0.5 + 0.5) * N);
  for (let j = -1; j <= 1; j++) for (let i = -1; i <= 1; i++) {
    const ii = Math.min(W2 - 1, Math.max(0, ci + i)), jj = Math.min(N - 1, Math.max(0, cj + j));
    d[(jj * W2 + ii) * 4] = 0;
  }
  upload(T, d);
}

// ---------- state ----------
const st = {
  phase: 'alive', age: 0, R: 1, C: [0, 0.03, 0], fade: 1, scale: 1,
  thinnest: Infinity, blackSeen: false, tPop: 0, popAt: 0, popWall: 0, popEnd: Infinity, timescale: 1,
  seed: Number(qs.get('seed') || 7), time: 0, stats: null, statsAge: 99, hover: null,
};
const drops = [];
const sound = new Sound();
let splat = [0, 0, 1e-3, -1], splatV = [0, 0];

function newBubble(seed) {
  upload(Hf, freshFilm(seed));
  upload(U, zeros); upload(Pr, zeros);
  upload(T, new Float32Array(W2 * N * 4).fill(6e4));
  Object.assign(st, { mean0: null, blackFor: 0, blackLife: 7 + Math.random() * 6, age: 0, thinnest: Infinity, blackSeen: false, tPop: 0, popEnd: Infinity, timescale: 1, stats: null, statsAge: 99 });
  drops.length = 0;
}

// ---------- plumes: four wandering sources of thin film low on the bubble ----------
const plumes = Array.from({ length: 4 }, (_, i) => ({ a: -Math.PI / 2 + (i - 1.5) * 0.7, hemi: i % 2, w: 0, phase: i * 1.7 }));
function plumeData() {
  const d = new Float32Array(16);
  plumes.forEach((p, i) => {
    p.a += (Math.random() - 0.5) * 0.02;
    p.a = Math.max(-Math.PI + 0.4, Math.min(-0.4, p.a));
    const pulse = Math.max(0, Math.sin(st.time * 0.35 + p.phase));
    d.set([0.86 * Math.cos(p.a), 0.86 * Math.sin(p.a), p.hemi, 1.6 * pulse * pulse], i * 4);
  });
  return d;
}

// ---------- volume: drainage only moves soap around; evaporation is the only loss ----------
const EVAP_MEAN = 1.6; // nm/s of mean thickness lost to drying
function volumeFix(dt, blowing) {
  if (blowing || !st.stats || st.mean0 == null) return 1;
  const target = Math.max(120, st.mean0 - EVAP_MEAN * st.age);
  const err = (target - st.stats.mean) / st.stats.mean;
  return 1 + Math.max(-0.03, Math.min(0.03, err)) * dt * 2;
}

// ---------- simulation step ----------
function simulate(dt) {
  const common = { uN: N, uDt: dt };
  run(prog.curl, Cu, { ...common, U: U.r });
  run(prog.force, Ut, { ...common, U: U.r, H: Hf.r, C: Cu, uTime: st.time, uBuoy: P.buoy, uNoise: P.noise, uVort: P.vort, uDamp: P.damp, uSplat: splat, uSplatV: splatV });
  run(prog.advect, U.w, { ...common, U: Ut, S: Ut }); U.swap();
  run(prog.div, Dv, { ...common, U: U.r });
  for (let i = 0; i < 24; i++) { run(prog.jacobi, Pr.w, { ...common, P: Pr.r, D: Dv }); Pr.swap(); }
  run(prog.grad, U.w, { ...common, P: Pr.r, U: U.r }); U.swap();
  const blowing = st.phase === 'blowing';
  run(prog.thick, Hf.w, { ...common, U: U.r, H: Hf.r, uDrain: blowing ? 0 : P.drain, uEvap: blowing ? 0 : P.evap, uStir: 0.0, uSplat: splat, 'uPlume[0]': plumeData(), uVol: volumeFix(dt, blowing) });
  Hf.swap();
  gl.bindTexture(gl.TEXTURE_2D, Hf.r.tex); gl.generateMipmap(gl.TEXTURE_2D);
  splat = [0, 0, 1e-3, -1]; splatV = [0, 0];
}

// The film is always stepped at 30 Hz, whatever the screen's refresh rate: thickness is stored as
// half floats, and the smaller per-frame changes of a 120 Hz step would round away to nothing.
const SIM_DT = 1 / 30;
let simAcc = 0;
function simulateFixed(dt) {
  simAcc += dt;
  while (simAcc >= SIM_DT) { simAcc -= SIM_DT; simulate(SIM_DT); }
}

const statsBuf = new Float32Array(2 * M * M * 4);
function readStats() {
  run(prog.down, Down, { uN: N, uM: M, H: Hf.r, T: T.r });
  gl.bindFramebuffer(gl.FRAMEBUFFER, Down.fb);
  gl.readPixels(0, 0, 2 * M, M, gl.RGBA, gl.FLOAT, statsBuf);
  let mn = Infinity, at = null, sum = 0, cnt = 0, tMax = 0, seenBlack = 0;
  const cp = camPos(), cl = Math.hypot(...cp);
  for (let j = 0; j < M; j++) for (let i = 0; i < 2 * M; i++) {
    const k = (j * 2 * M + i) * 4, cov = statsBuf[k + 3];
    if (cov < 0.15) continue;
    const h = statsBuf[k];
    const x = ((i % M) + 0.5) / M * 2 - 1, y = (j + 0.5) / M * 2 - 1, hemi = i >= M ? 1 : 0;
    if (h < mn) { mn = h; at = [x, y, hemi]; }
    if (h < 20) {                                       // black film the viewer can actually see
      const z = (hemi ? -1 : 1) * Math.sqrt(Math.max(0, 1 - x * x - y * y));
      if ((x * cp[0] + y * cp[1] + z * cp[2]) / cl > 0.35) seenBlack++;
    }
    sum += statsBuf[k + 1]; cnt++;
    tMax = Math.max(tMax, statsBuf[k + 2]);
  }
  st.stats = { min: mn, at, mean: sum / cnt, tMax, seenBlack };
  st.statsAge = 0;
}

function sphPoint(x, y, hemi) {
  const z = (hemi ? -1 : 1) * Math.sqrt(Math.max(0, 1 - x * x - y * y));
  return [st.C[0] + st.R * x, st.C[1] + st.R * y, st.C[2] + st.R * z];
}

function startPop(x, y, hemi) {
  if (st.phase !== 'alive') return;
  seedHole(x, y, hemi);
  st.phase = 'popping';
  st.tPop = 0; st.timescale = 1 / SLOW; st.popWall = 0; st.popAt = sphPoint(x, y, hemi); st.popEndT = null;
  st.popEnd = Infinity;
  if (!st.stats) readStats();
  if (st.thinnest === Infinity && st.stats) st.thinnest = st.stats.min;
  sound.pop(true);
  ui('slow').classList.add('on');
  ui('black').classList.remove('on');
  hideHint();
}

function spawnDrops(prevT, nowT) {
  for (let j = 0; j < M; j++) for (let i = 0; i < 2 * M; i++) {
    const k = (j * 2 * M + i) * 4;
    const t = statsBuf[k + 2];
    if (statsBuf[k + 3] < 0.3 || !(t > prevT && t <= nowT) || statsBuf[k + 1] < 100 || drops.length > 70) continue;
    const x = ((i % M) + 0.5) / M * 2 - 1, y = (j + 0.5) / M * 2 - 1, hemi = i >= M ? 1 : 0;
    const p = sphPoint(x, y, hemi);
    const nrm = [(p[0] - st.C[0]) / st.R, (p[1] - st.C[1]) / st.R, (p[2] - st.C[2]) / st.R];
    let a = [p[0] - st.popAt[0], p[1] - st.popAt[1], p[2] - st.popAt[2]];
    const dn = a[0] * nrm[0] + a[1] * nrm[1] + a[2] * nrm[2];
    a = a.map((v, q) => v - dn * nrm[q]);
    const al = Math.hypot(...a) || 1;
    const h = Math.max(4, statsBuf[k]);
    // spray leaves the rim at the rim's own speed (Taylor-Culick), shown 200x slower, in bubble radii per second
    const speed = Math.sqrt(0.05 / (1000 * h * 1e-9)) / SLOW / (R_PHYS * st.R);
    if (Math.random() > 0.45) continue;
    for (let n = 0; n < 1; n++) {
      const s = speed * (0.6 + Math.random() * 0.8);
      drops.push({
        p: p.slice(), life: 1,
        v: a.map((v, q) => (v / al) * s + nrm[q] * s * (Math.random() * 0.6 - 0.1) + (Math.random() - 0.5) * 0.05),
      });
    }
    if (Math.random() < 0.08) sound.drip(x * (hemi ? -1 : 1));
  }
}

// ---------- camera and pointer ----------
const TAN = Math.tan((15 * Math.PI) / 180);
const TILT = (28 * Math.PI) / 180;   // looking down a little, so the drained top of the bubble faces us
function camZ() {
  const aspect = canvas.width / canvas.height;
  return 1.0 / (TAN * Math.min(1, aspect) * 0.8);
}
function camPos() { const d = camZ(); return [0, d * Math.sin(TILT), d * Math.cos(TILT)]; }
function hit(px, py) {
  const r = canvas.getBoundingClientRect();
  const h = r.height, w = r.width;
  const sx = ((px - r.left) - w / 2) / h * 2 * TAN, sy = (h / 2 - (py - r.top)) / h * 2 * TAN;
  const ro = camPos();
  const norm = (v) => { const l = Math.hypot(...v); return v.map((x) => x / l); };
  const f = norm(ro.map((v) => -v));
  const rt = norm([-f[2], 0, f[0]]);                       // cross(f, up)
  const up = [rt[1] * f[2] - rt[2] * f[1], rt[2] * f[0] - rt[0] * f[2], rt[0] * f[1] - rt[1] * f[0]];
  const rd = norm(f.map((v, i) => v + sx * rt[i] + sy * up[i]));
  const oc = ro.map((v, i) => v - st.C[i]);
  const b = oc[0] * rd[0] + oc[1] * rd[1] + oc[2] * rd[2];
  const c = oc[0] ** 2 + oc[1] ** 2 + oc[2] ** 2 - st.R * st.R;
  const disc = b * b - c;
  if (disc < 0) return null;
  const t = -b - Math.sqrt(disc);
  const q = ro.map((v, i) => (v + rd[i] * t - st.C[i]) / st.R);
  return { x: q[0], y: q[1], z: q[2], hemi: q[2] >= 0 ? 0 : 1 };
}

let down = null, holding = false;
function onDown(e) {
  sound.start();
  canvas.setPointerCapture?.(e.pointerId);
  down = { phase: st.phase, x: e.clientX, y: e.clientY, t: performance.now(), moved: false, last: hit(e.clientX, e.clientY), lt: performance.now() };
  if (st.phase === 'gone' && st.time - st.goneAt > 1.5) beginBlow();
}
function onMove(e) {
  const hp = hit(e.clientX, e.clientY);
  st.hover = hp;
  st.hoverTouch = e.pointerType !== 'mouse';
  st.hoverPx = [e.clientX, e.clientY];
  if (!down) return;
  if (Math.hypot(e.clientX - down.x, e.clientY - down.y) > 8) down.moved = true;
  if (st.phase === 'alive' && down.moved && hp && down.last) {
    const now = performance.now(), dt = Math.max(8, now - down.lt) / 1000;
    const vx = (hp.x - down.last.x) / dt, vy = (hp.y - down.last.y) / dt;
    splat = [hp.x, hp.y, 0.012, hp.hemi];
    splatV = [vx * 0.55, vy * 0.55];
    sound.stirring(Math.hypot(vx, vy) * 0.08);
    down.lt = now;
  }
  down.last = hp;
}
function onUp(e) {
  holding = false;                     // the breath ends; the bubble keeps what it has (at least a small one)
  if (down && down.phase === 'alive' && st.phase === 'alive' && !down.moved && performance.now() - down.t < 400) {
    const hp = hit(e.clientX, e.clientY);
    if (hp) startPop(hp.x, hp.y, hp.hemi);
  }
  if (e.pointerType !== 'mouse') st.hover = null;
  down = null;
  sound.stirring(0);
}
canvas.addEventListener('pointerdown', onDown);
addEventListener('pointermove', onMove);
addEventListener('pointerup', onUp);
addEventListener('pointercancel', onUp);
document.addEventListener('pointerout', (e) => { if (!e.relatedTarget) st.hover = null; });
addEventListener('keydown', (e) => {
  if (e.repeat) return;
  if (e.code === 'Space') { e.preventDefault(); sound.start(); if (st.phase === 'gone' && st.time - st.goneAt > 1.5) beginBlow(); }
  if (e.code === 'KeyP' && st.phase === 'alive' && st.stats) startPop(...st.stats.at);
});
addEventListener('keyup', (e) => { if (e.code === 'Space') holding = false; });
addEventListener('blur', () => { holding = false; });

function beginBlow() {
  st.seed++;
  newBubble(st.seed);
  st.phase = 'blowing'; st.R = 0.06; st.fade = 1; holding = true;
  ui('epitaph').classList.remove('on');
  ui('again').classList.remove('on');
}
function endBlow() {
  holding = false;
  if (st.phase !== 'blowing') return;
  // bake the stretch into the film: a bigger bubble is a thinner bubble (same soap, more area)
  run(prog.scale, Hf.w, { H: Hf.r, uK: 1 / (st.R * st.R) });
  Hf.swap();
  gl.bindTexture(gl.TEXTURE_2D, Hf.r.tex); gl.generateMipmap(gl.TEXTURE_2D);
  st.scale = 1;
  st.phase = 'alive';
  st.age = 0;
  sound.blowing(0);
}

// ---------- drops (GPU points) ----------
const dropProg = program(S.FS_DROP, S.VS_DROP);
const dropVao = gl.createVertexArray(), dropBuf = gl.createBuffer();
gl.bindVertexArray(dropVao);
gl.bindBuffer(gl.ARRAY_BUFFER, dropBuf);
gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 16, 0);
gl.enableVertexAttribArray(1); gl.vertexAttribPointer(1, 1, gl.FLOAT, false, 16, 12);
gl.bindAttribLocation(dropProg.p, 0, 'aP'); gl.bindAttribLocation(dropProg.p, 1, 'aA'); gl.linkProgram(dropProg.p);
dropProg.u = { uRes: gl.getUniformLocation(dropProg.p, 'uRes'), uCam: gl.getUniformLocation(dropProg.p, 'uCam'), uTan: gl.getUniformLocation(dropProg.p, 'uTan'), uLine: gl.getUniformLocation(dropProg.p, 'uLine') };
function drawDrops() {
  if (!drops.length) return;
  // each drop is a short streak: a bright head and a tail along where it came from
  const a = new Float32Array(drops.length * 8);
  drops.forEach((d, i) => a.set([d.p[0], d.p[1], d.p[2], d.life, d.p[0] - d.v[0] * 0.07, d.p[1] - d.v[1] * 0.07, d.p[2] - d.v[2] * 0.07, 0], i * 8));
  gl.bindVertexArray(dropVao);
  gl.bindBuffer(gl.ARRAY_BUFFER, dropBuf);
  gl.bufferData(gl.ARRAY_BUFFER, a, gl.DYNAMIC_DRAW);
  gl.useProgram(dropProg.p);
  gl.uniform2f(dropProg.u.uRes, canvas.width, canvas.height);
  gl.uniform3fv(dropProg.u.uCam, camPos()); gl.uniform1f(dropProg.u.uTan, TAN);
  gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE);
  gl.uniform1f(dropProg.u.uLine, 1);
  gl.drawArrays(gl.LINES, 0, drops.length * 2);
  gl.disable(gl.BLEND);
}

// ---------- UI: thickness ruler ----------
const ruler = ui('ruler'), rctx = ruler.getContext('2d');
const RULER_MAX = 1200;
function drawRuler() {
  const h = 512;
  ruler.width = 1; ruler.height = h;
  const img = rctx.createImageData(1, h);
  for (let j = 0; j < h; j++) {
    const nm = (1 - j / (h - 1)) * RULER_MAX;
    // same tone curve as the bubble itself, as if the film reflected a bright white light
    const c = filmRGB(nm, 1).map((v) => { const x = v * 6.4; return 255 * Math.pow(Math.min(1, (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)), 1 / 2.2); });
    img.data.set([c[0], c[1], c[2], 255], j * 4);
  }
  rctx.putImageData(img, 0, 0);
}
drawRuler();

const px1 = new Float32Array(4);
function hoverThickness() {
  if (!st.hover || st.phase !== 'alive') return null;
  const i = Math.min(N - 1, Math.max(0, Math.floor((st.hover.x * 0.5 + 0.5) * N))) + st.hover.hemi * N;
  const j = Math.min(N - 1, Math.max(0, Math.floor((st.hover.y * 0.5 + 0.5) * N)));
  gl.bindFramebuffer(gl.FRAMEBUFFER, Hf.r.fb);
  gl.readPixels(i, j, 1, 1, gl.RGBA, gl.FLOAT, px1);
  return px1[0];
}
let hoverNm = null, hoverTick = 0;
function updateUI() {
  document.body.classList.toggle('nobubble', st.phase === 'gone');
  if (++hoverTick % 3 === 0) hoverNm = hoverThickness();
  const tag = ui('tag'), mark = ui('mark');
  if (hoverNm != null) {
    tag.textContent = `${Math.round(hoverNm)} nm`;
    tag.style.transform = st.hoverTouch ? `translate(${st.hoverPx[0] - 24}px, ${st.hoverPx[1] - 64}px)` : `translate(${st.hoverPx[0] + 16}px, ${st.hoverPx[1] - 10}px)`;
    tag.classList.add('on');
    mark.style.top = `${(1 - Math.min(hoverNm, RULER_MAX) / RULER_MAX) * 100}%`;
    mark.classList.add('on');
  } else { tag.classList.remove('on'); mark.classList.remove('on'); }
  if (st.phase === 'alive' && !st.blackSeen && st.stats && st.stats.seenBlack >= 3) {
    st.blackSeen = true;
    ui('black').classList.add('on');                  // stays up until the pop
  }
}
function flash(id, ms = 5200) { const el = ui(id); el.classList.add('on'); setTimeout(() => el.classList.remove('on'), ms); }
let hintHidden = false;
function hideHint() { if (!hintHidden) { hintHidden = true; ui('hint').classList.remove('on'); } }
setTimeout(() => { if (!hintHidden) ui('hint').classList.add('on'); }, 1200);
setTimeout(hideHint, 14000);

// ---------- frame loop ----------
function resize() {
  const dpr = Math.min(devicePixelRatio || 1, 2);
  const w = Math.round(innerWidth * dpr), h = Math.round(innerHeight * dpr);
  if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
}

function step(dtReal) {
  st.time += dtReal;
  if (st.phase === 'blowing') {
    // it grows while you keep blowing; a quick puff still makes a small bubble
    if (holding || st.R < R_MIN) st.R = Math.min(1, st.R + dtReal * (0.08 + 0.55 * (1 - st.R)));
    st.C = [0, -1 + st.R, 0];
    st.scale = 1 / (st.R * st.R);
    sound.blowing(holding ? 0.4 + 0.6 * (1 - st.R) : 0);
    if (st.R >= 0.995 || (!holding && st.R >= R_MIN)) endBlow();
    simulateFixed(dtReal);
  } else if (st.phase === 'alive') {
    st.age += dtReal;
    const t = st.time;
    st.C = [st.C[0] + (0.05 * Math.sin(t * 0.13) - st.C[0]) * dtReal, st.C[1] + (0.03 + 0.03 * Math.sin(t * 0.21) - st.C[1]) * dtReal * 0.8, 0];
    simulateFixed(dtReal);
    if (++st.statsAge > 5) readStats();
    if (st.stats) {
      if (st.mean0 == null) st.mean0 = st.stats.mean + EVAP_MEAN * st.age;   // age is ~0 here after a blow
      st.thinnest = Math.min(st.thinnest, st.stats.min);
      // black film is metastable: it holds for a while, then a black spot gives way
      if (st.stats.seenBlack >= 3) st.blackFor = (st.blackFor || 0) + dtReal;
      else if (st.stats.min < 20) st.blackFor = (st.blackFor || 0) + dtReal * 0.3;   // black out of sight still ages it
      if (st.blackFor > st.blackLife) startPop(...st.stats.at);
    }
    sound.mood(1, Math.min(1, Math.max(0, (1100 - (st.stats?.mean ?? 1100)) / 900)));
  } else if (st.phase === 'popping') {
    const prev = st.tPop;
    st.popWall += dtReal;
    st.tPop += dtReal * 1000 * st.timescale;
    for (let i = 0; i < 32; i++) { run(prog.rim, T.w, { uN: N, T: T.r, H: Hf.r, uRphys: R_PHYS * st.R }); T.swap(); }
    readStats();
    if (st.stats.tMax < 5e4) st.popEndT = st.stats.tMax;   // when the last of the film will be torn
    spawnDrops(prev, st.tPop);
    if (st.popEnd === Infinity && st.popWall > 0.3 && (st.tPop > st.stats.tMax + 0.2 || st.popWall > 9)) st.popEnd = st.popWall;
    if (st.popWall > st.popEnd + 0.4) {
      st.phase = 'gone'; st.goneAt = st.time;
      ui('slow').classList.remove('on');
      const e = epitaph({ ageS: st.age, thinnestNm: st.thinnest, diameterCm: 2 * R_PHYS * st.R * 100 });
      ui('ep-zh').textContent = e.zh; ui('ep-en').textContent = e.en;
      setTimeout(() => { if (st.phase === 'gone') ui('epitaph').classList.add('on'); }, 700);
      setTimeout(() => { if (st.phase === 'gone') ui('again').classList.add('on'); }, 2600);
    }
  } else if (st.phase === 'gone') {
    st.fade = Math.max(0, st.fade - dtReal / 0.3);
    st.timescale = Math.min(1 / 25, st.timescale * Math.pow(6, dtReal));
  }
  // drops: thrown outward, slowed by air, then falling
  const ts = st.phase === 'popping' ? 1 : SLOW * st.timescale;
  for (const d of drops) {
    const k = Math.exp(-dtReal * 0.9);
    d.v = d.v.map((v) => v * k);
    d.v[1] -= dtReal * 9.8 / R_PHYS * (st.timescale * st.timescale) * 40 * ts / SLOW;
    for (let q = 0; q < 3; q++) d.p[q] += d.v[q] * dtReal * ts;
    d.life -= dtReal * 2;                       // a streak lasts about half a second
  }
  for (let i = drops.length - 1; i >= 0; i--) {
    const d = drops[i], far = Math.hypot(d.p[0] - st.C[0], d.p[1] - st.C[1], d.p[2] - st.C[2]) > 1.2 * st.R;
    if (d.life <= 0 || far) drops.splice(i, 1);
  }
}

function render() {
  run(prog.render, null, {
    H: Hf.r, T: T.r, LUT: lut, uRes: [canvas.width, canvas.height], uC: st.C, uR: st.R, uCam: camPos(), uTan: TAN,
    uScale: st.phase === 'blowing' ? st.scale : 1, uTpop: st.tPop, uPopping: st.phase === 'popping' || st.phase === 'gone' ? 1 : 0,
    uTime: st.time, uLutN: LUT_N, uLutC: LUT_C, uHmax: H_MAX, uFade: st.fade, uTend: Math.max(1, st.popEndT || 1e9),
  });
  drawDrops();
}

let last = performance.now(), paused = false;
function frame(now) {
  const dt = Math.max(0, Math.min(1 / 30, (now - last) / 1000));
  last = now;
  resize();
  if (!paused) step(dt);
  render();
  updateUI();
  requestAnimationFrame(frame);
}

// A first bubble is already floating when the page opens, a few seconds into its life.
newBubble(st.seed);
for (let i = 0; i < Number(qs.get('warm') ?? 150); i++) { st.time += 1 / 30; simulate(1 / 30); }
st.age = 5;
requestAnimationFrame(frame);
document.addEventListener('visibilitychange', () => { last = performance.now(); });

// Hooks for the headless checks in tools/.
window.__ob = {
  st, drops,
  skip(sec, dt = 1 / 30) { for (let t = 0; t < sec; t += dt) step(dt); render(); },
  pause(v) { paused = v; },
  pop() { if (st.stats) startPop(...st.stats.at); else startPop(0, 0.5, 0); },
  pokeAt(x, y) { startPop(x, y, 0); },
  blow(sec) { beginBlow(); this.skip(sec); },
  release() { holding = false; },
  readStats,
  probe() {
    const out = {};
    for (const [name, pp] of [['U', U.r], ['H', Hf.r]]) {
      const b = new Float32Array(W2 * N * 4);
      gl.bindFramebuffer(gl.FRAMEBUFFER, pp.fb); gl.readPixels(0, 0, W2, N, gl.RGBA, gl.FLOAT, b);
      let mx = 0, sum = 0, n = 0;
      for (let i = 0; i < W2 * N; i++) { const m = Math.hypot(b[i * 4], b[i * 4 + 1]); mx = Math.max(mx, m); sum += m; n++; }
      out[name] = { max: mx, mean: sum / n, sample: Array.from(b.slice((128 * W2 + 128) * 4, (128 * W2 + 128) * 4 + 2)) };
    }
    return out;
  },
};
