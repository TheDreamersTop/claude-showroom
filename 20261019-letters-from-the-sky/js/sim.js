// Gravner–Griffeath snow-crystal lattice model (Physica D 237, 2008) on the GPU.
// Hexagonal lattice in axial coordinates on an N×N float texture.
// Texel: r = step at which the cell attached (0 = vapour/boundary), g = boundary mass b,
//        b = crystal mass c, a = diffusive (vapour) mass d.
import { program, target, pass } from './gl.js';

const HEAD = `#version 300 es
precision highp float; precision highp int;
uniform highp sampler2D S; uniform float N, rho, box;
in vec2 uv; out vec4 o;
const ivec2 NB[6] = ivec2[6](ivec2(1,0),ivec2(-1,0),ivec2(0,1),ivec2(0,-1),ivec2(1,-1),ivec2(-1,1));
vec4 at(ivec2 q){
  ivec2 c = q - ivec2(int(N)/2);
  if (abs(c.x) > int(box) || abs(c.y) > int(box) || abs(c.x+c.y) > int(box)) return vec4(0.,0.,0.,rho);
  return texelFetch(S, q, 0);
}
`;

export const DEFAULT = { rho: 0.635, beta: 1.6, alpha: 0.4, theta: 0.025, kappa: 0.0025, mu: 0.015, gamma: 0.0005, sigma: 0, supply: 0 };

export class SnowSim {
  constructor(gl, N = 512) {
    this.gl = gl; this.N = N;
    const opt = { internal: gl.RGBA32F, type: gl.FLOAT, filter: gl.NEAREST };
    this.A = target(gl, N, N, opt); this.B = target(gl, N, N, opt);
    this.init = program(gl, HEAD + `uniform float seedR;
      void main(){ ivec2 c = ivec2(gl_FragCoord.xy) - ivec2(int(N)/2);
        int h = max(max(abs(c.x),abs(c.y)),abs(c.x+c.y));
        o = float(h) <= seedR ? vec4(1.,0.,1.,0.) : vec4(0.,0.,0.,rho); }`);
    this.diff = program(gl, HEAD + `uniform float sigma, seed, supply;
      float hash(vec2 p){ vec3 p3 = fract(vec3(p.xyx)*.1031+seed); p3 += dot(p3, p3.yzx+33.33); return fract((p3.x+p3.y)*p3.z); }
      void main(){ ivec2 q = ivec2(gl_FragCoord.xy); vec4 s = at(q);
        if (s.r > 0.) { o = s; return; }
        float d = s.a; int n = 0;
        for (int k=0;k<6;k++){ vec4 m = at(q+NB[k]); if (m.r>0.) { d += s.a; n++; } else d += m.a; }
        d /= 7.;
        if (n == 0) d += supply*(rho - d);
        if (sigma > 0.) d *= 1. + sigma*(hash(vec2(q))*2.-1.);
        o = vec4(s.rgb, d); }`);
    this.grow = program(gl, HEAD + `uniform float beta, alpha, theta, kappa, mu, gamma, T;
      void main(){ ivec2 q = ivec2(gl_FragCoord.xy); vec4 s = at(q);
        if (s.r > 0.) { o = s; return; }
        int n = 0; float sd = s.a;
        for (int k=0;k<6;k++){ vec4 m = at(q+NB[k]); if (m.r>0.) n++; else sd += m.a; }
        if (n == 0) { o = s; return; }
        float b = s.g + (1.-kappa)*s.a, c = s.b + kappa*s.a;
        bool att = (n<=2 && b>=beta) || (n==3 && (b>=1. || (b>=alpha && sd<theta))) || n>=4;
        if (att) { o = vec4(T, 0., b + c, 0.); return; }
        float d = mu*b + gamma*c; b *= 1.-mu; c *= 1.-gamma;
        o = vec4(0., b, c, d); }`);
    // warm breath: weakly bound ice (few frozen neighbours) sublimates back into vapour, tips and thin branches first
    this.subl = program(gl, HEAD + `uniform float seed, rate, focusR; uniform vec2 focus;
      float hash(vec2 p){ vec3 p3 = fract(vec3(p.xyx)*.1031+seed); p3 += dot(p3, p3.yzx+33.33); return fract((p3.x+p3.y)*p3.z); }
      void main(){ ivec2 q = ivec2(gl_FragCoord.xy); vec4 s = at(q);
        if (s.r <= 0.) { o = s; return; }
        int n = 0; for (int k=0;k<6;k++) if (at(q+NB[k]).r > 0.) n++;
        vec2 c = vec2(q - ivec2(int(N)/2)); vec2 xy = vec2(c.x + c.y*.5, c.y*.8660254);
        float near = exp(-dot(xy - focus, xy - focus)/(focusR*focusR));
        float p = rate*near*(n <= 2 ? 1. : n == 3 ? .35 : n == 4 ? .06 : 0.);
        if (hash(vec2(q)) < p) { o = vec4(0., 0., 0., s.b); return; }
        o = s; }`);
    // radius: per lattice row, the largest hex distance of any frozen cell (GPU reduction, read back as one row)
    this.red = program(gl, HEAD + `void main(){ int j = int(gl_FragCoord.x); int c = int(N)/2; int dj = j - c; float r = 0.;
        if (abs(dj) <= int(box)) for (int i = 0; i < 2048; i++) { if (i >= int(N)) break; int di = i - c;
          if (abs(di) > int(box)) continue;
          if (texelFetch(S, ivec2(i, j), 0).r > 0.) r = max(r, float(max(max(abs(di), abs(dj)), abs(di + dj)))); }
        o = vec4(r, 0., 0., 1.); }`);
    this.redT = target(gl, N, 1, { internal: gl.RGBA32F, type: gl.FLOAT, filter: gl.NEAREST });
    // when the active region grows, cells entering it take the current ambient vapour density
    this.fill = program(gl, HEAD + `uniform float oldBox;
      void main(){ ivec2 q = ivec2(gl_FragCoord.xy); ivec2 c = q - ivec2(int(N)/2);
        int h = max(max(abs(c.x),abs(c.y)),abs(c.x+c.y));
        o = float(h) > oldBox ? vec4(0.,0.,0.,rho) : texelFetch(S, q, 0); }`);
    this.row = new Float32Array(N * 4);
    this.reset();
  }
  get tex() { return this.A; }
  reset(P = DEFAULT, seedR = 0) {
    this.T = 1; this.radius = seedR + 1; this.P = P; this.sinceM = 0; this.lastBox = 0;
    const box = this.N / 2 - 2;
    pass(this.gl, this.init, this.A, {}, { N: this.N, rho: P.rho, box, seedR });
    pass(this.gl, this.init, this.B, {}, { N: this.N, rho: P.rho, box, seedR });
  }
  // active region: the crystal can advance at most ~1 cell per step, so grow the margin with the steps run since the last measurement
  // quantised so the vapour boundary hardly depends on how often the radius is read back (keeps twins comparable)
  get box() { return Math.min(this.N / 2 - 3, 32 * Math.ceil((this.radius * 1.25 + 56 + 0.35 * (this.sinceM || 0)) / 32)); }
  step(n, P) {
    // re-measure at least every 128 steps so the active region (= the vapour boundary) depends on the crystal, not the frame rate
    while (n > 0) { const k = Math.min(n, 128 - (this.sinceM || 0)); if (k <= 0) { this.measure(); continue; } this._step(k, P); n -= k; }
  }
  _step(n, P) {
    this.sinceM = (this.sinceM || 0) + n;
    const gl = this.gl, N = this.N, box = this.box, c = N / 2;
    gl.enable(gl.SCISSOR_TEST);
    // axial hexagon of radius `box` fits in an axis-aligned square of half-size box (+1 for neighbour reads)
    gl.scissor(c - box - 1, c - box - 1, 2 * box + 3, 2 * box + 3);
    if (box > (this.lastBox || 0)) {
      for (let k = 0; k < 2; k++) { pass(gl, this.fill, this.B, { S: this.A }, { N, box: box + 1, rho: P.rho, oldBox: this.lastBox || 0 }); const t = this.A; this.A = this.B; this.B = t; }
      this.lastBox = box;
    }
    const u = Object.assign({ N, box }, P);
    for (let i = 0; i < n; i++) {
      u.seed = (this.T * 0.6180339 + (this.seedOff || 0)) % 1;
      pass(gl, this.diff, this.B, { S: this.A }, u);
      u.T = this.T++;
      pass(gl, this.grow, this.A, { S: this.B }, u);
    }
    gl.disable(gl.SCISSOR_TEST);
  }
  sublimate(n, rate, focus, focusR) {
    const gl = this.gl, N = this.N, box = this.box, c = N / 2;
    gl.enable(gl.SCISSOR_TEST); gl.scissor(c - box - 1, c - box - 1, 2 * box + 3, 2 * box + 3);
    for (let i = 0; i < n; i++) {
      pass(gl, this.subl, this.B, { S: this.A }, { N, box, rho: this.P.rho, seed: Math.random(), rate, focus, focusR });
      const t = this.A; this.A = this.B; this.B = t;
    }
    gl.disable(gl.SCISSOR_TEST);
  }
  // Measure the arm length along the six lattice axes (row through the centre covers ±i).
  measure() {
    const gl = this.gl, N = this.N;
    pass(gl, this.red, this.redT, { S: this.A }, { N, box: this.box, rho: this.P.rho });
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.redT.f);
    gl.readPixels(0, 0, N, 1, gl.RGBA, gl.FLOAT, this.row);
    let r = 0;
    for (let i = 0; i < N; i++) r = Math.max(r, this.row[i * 4]);
    this.radius = Math.max(this.radius, r);
    this.sinceM = 0;
    return this.radius;
  }
}
