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
    this.row = new Float32Array(N * 4);
    this.reset();
  }
  get tex() { return this.A; }
  reset(P = DEFAULT, seedR = 0) {
    this.T = 1; this.radius = seedR + 1; this.P = P;
    const box = this.N / 2 - 2;
    pass(this.gl, this.init, this.A, {}, { N: this.N, rho: P.rho, box, seedR });
    pass(this.gl, this.init, this.B, {}, { N: this.N, rho: P.rho, box, seedR });
  }
  get box() { return Math.min(this.N / 2 - 3, Math.ceil(this.radius + 48)); }
  step(n, P) {
    const gl = this.gl, N = this.N, box = this.box, c = N / 2;
    gl.enable(gl.SCISSOR_TEST);
    // axial hexagon of radius `box` fits in an axis-aligned square of half-size box (+1 for neighbour reads)
    gl.scissor(c - box - 1, c - box - 1, 2 * box + 3, 2 * box + 3);
    const u = Object.assign({ N, box }, P);
    for (let i = 0; i < n; i++) {
      u.seed = (this.T * 0.6180339) % 1;
      pass(gl, this.diff, this.B, { S: this.A }, u);
      u.T = this.T++;
      pass(gl, this.grow, this.A, { S: this.B }, u);
    }
    gl.disable(gl.SCISSOR_TEST);
  }
  // Measure the arm length along the six lattice axes (row through the centre covers ±i).
  measure() {
    const gl = this.gl, N = this.N, c = N / 2;
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.A.f);
    gl.readPixels(0, c, N, 1, gl.RGBA, gl.FLOAT, this.row);
    let r = 0;
    for (let i = 0; i < N; i++) if (this.row[i * 4] > 0) r = Math.max(r, Math.abs(i - c));
    this.radius = Math.max(this.radius, r);
    return this.radius;
  }
}
