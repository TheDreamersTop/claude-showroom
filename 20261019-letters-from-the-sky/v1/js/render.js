// Renderer: sky (backlight, cloud, hexagonal bokeh), the crystal (backlit ice, refraction,
// dispersion, fresh-ice glow, glints), bloom and a filmic finish.
import { program, target, pass } from './gl.js';

const P = `#version 300 es
precision highp float; precision highp int;
in vec2 uv; out vec4 o;
`;

const NOISE = `
float h21(vec2 p){ vec3 p3 = fract(vec3(p.xyx)*.1031); p3 += dot(p3, p3.yzx+33.33); return fract((p3.x+p3.y)*p3.z); }
float vnoise(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.-2.*f);
  return mix(mix(h21(i),h21(i+vec2(1,0)),f.x), mix(h21(i+vec2(0,1)),h21(i+vec2(1,1)),f.x), f.y); }
float fbm(vec2 p){ float s = 0., a = .5; for (int i=0;i<5;i++){ s += a*vnoise(p); p = p*2.03 + vec2(1.7,9.2); a *= .5; } return s; }
`;

// ---- view field: lattice state -> smooth, filterable fields --------------------------------
const VIEW = P + `uniform highp sampler2D S; uniform float N, T, tau;
void main(){ vec4 s = texelFetch(S, ivec2(gl_FragCoord.xy), 0);
  float solid = s.r > 0. ? 1. : 0.;
  float age = solid > 0. ? (T - s.r) : 1e5;
  o = vec4(solid, solid*s.b, exp(-age/tau), s.a); }`;

// 7-tap hex blur in axial space (keeps 6-fold symmetry of the field)
const HBLUR = P + `uniform sampler2D V; uniform float N;
void main(){ ivec2 q = ivec2(gl_FragCoord.xy);
  vec4 s = texelFetch(V, q, 0)*2.;
  s += texelFetch(V, q+ivec2(1,0),0) + texelFetch(V, q+ivec2(-1,0),0) + texelFetch(V, q+ivec2(0,1),0)
     + texelFetch(V, q+ivec2(0,-1),0) + texelFetch(V, q+ivec2(1,-1),0) + texelFetch(V, q+ivec2(-1,1),0);
  vec4 c = texelFetch(V, q, 0);
  o = vec4(s.rg/8., max(c.b, s.b/8.), c.a); }`;

// ---- sky -------------------------------------------------------------------------------------
const SKY = P + NOISE + `uniform vec2 R; uniform float time, fall; uniform vec3 cA, cB, cC, cWarm; uniform float warm;
void main(){ vec2 p = (gl_FragCoord.xy - .5*R)/R.y;
  float r = length(p);
  vec3 col = mix(cC, cB, smoothstep(1.1, .1, r));
  col += cA * (.05*exp(-r*r*3.) + .02*exp(-r*r*1.));
  // warm accent light on one side, gives refraction colour in the ridges
  col += cWarm * warm * smoothstep(.9, .0, length(p - vec2(.75, -.35))) * .06;
  // drifting cloud (we fall, so it rises)
  vec2 q = p*1.6 + vec2(0., -fall*.18);
  float cl = fbm(q + vec2(fbm(q*.7 + time*.02), fbm(q*.7 - time*.015)));
  col *= .78 + .55*cl;
  vec2 q2 = p*3.2 + vec2(0., -fall*.45);
  col += cA*.05*smoothstep(.55,.95,fbm(q2));
  o = vec4(col, 1.); }`;

// hexagonal bokeh sprites (other snow crystals, out of focus)
const BOKEH_VS = `#version 300 es
precision highp float;
in vec2 p; uniform vec2 R; uniform float time, fall, layer, count;
out vec2 lp; out float a; flat out float id;
float h(float n){ return fract(sin(n*127.1)*43758.5453); }
void main(){ int i = gl_InstanceID; float f = float(i) + layer*1000.;
  float z = mix(.6, 1.0, h(f+3.)) * (layer > .5 ? 1. : .45);
  float size = (layer > .5 ? mix(.05, .16, h(f+7.)) : mix(.012, .035, h(f+7.)));
  float spd = (layer > .5 ? .22 : .08) * mix(.7, 1.3, h(f+9.));
  vec2 c = vec2(h(f)*2.-1., h(f+1.)*2.-1.);
  c.x *= R.x/R.y;
  c.y = mod(c.y + fall*spd + 1.2, 2.4) - 1.2;
  c.x += .05*sin(time*.3 + f);
  float ang = h(f+11.)*1.0472;
  mat2 rot = mat2(cos(ang), -sin(ang), sin(ang), cos(ang));
  lp = p; a = mix(.25, 1., h(f+5.)) * (layer > .5 ? .35 : .5); id = f;
  vec2 w = c + rot*p*size;
  gl_Position = vec4(w.x*R.y/R.x, w.y, 0., 1.); }`;
const BOKEH_FS = P.replace('in vec2 uv;', '') + `in vec2 lp; in float a; flat in float id; uniform vec3 tint;
void main(){ vec2 q = abs(lp);
  float hexd = max(q.x*.866 + q.y*.5, q.y);
  float m = smoothstep(1., .9, hexd);
  float ring = smoothstep(.75, 1., hexd)*m;
  o = vec4(tint*(m*.25 + ring*.35)*a, 1.); }`;

// ---- crystal ----------------------------------------------------------------------------------
const FLAKE = P + NOISE + `
uniform sampler2D V, V0, SKYT; uniform vec2 R; uniform float N, zoom, time, glowAmt, beta, vapour;
uniform mat3 rot; uniform vec3 keyCol, rimCol, iceCol, glowCol, lampA, lampB, lampC, dirA, dirB, dirC; uniform float slope, bevel, dbg, edgeGain, thick;
vec2 toAx(vec2 p){ float j = p.y*1.1547005; return vec2(p.x - j*.5, j) + N*.5; }
// Linear interpolation on the triangles of the hexagonal lattice (respects all three crystal axes,
// so facets along any of them stay straight). Returns value; grad (cartesian) via out param.
vec4 tri(sampler2D T, vec2 p, out vec4 gx, out vec4 gy){
  vec2 a = toAx(p); vec2 i = floor(a); vec2 f = a - i; ivec2 q = ivec2(i);
  vec4 v10 = texelFetch(T, q+ivec2(1,0), 0), v01 = texelFetch(T, q+ivec2(0,1), 0), v;
  vec4 di, dj;
  if (f.x + f.y < 1.) { vec4 v00 = texelFetch(T, q, 0); di = v10 - v00; dj = v01 - v00; v = v00 + f.x*di + f.y*dj; }
  else { vec4 v11 = texelFetch(T, q+ivec2(1,1), 0); di = v11 - v01; dj = v11 - v10; v = v11 - (1.-f.x)*di - (1.-f.y)*dj; }
  gx = di; gy = (-di + 2.*dj)*.57735027;
  return v; }
vec4 F(vec2 p){ vec4 a, b; return tri(V, p, a, b); }
void main(){
  vec2 sp = (gl_FragCoord.xy - .5*R)/R.y;
  // camera ray onto the tilted plane of the crystal
  vec3 ro = vec3(0., 0., 2.4), rd = normalize(vec3(sp, -2.4));
  vec3 pn = rot*vec3(0,0,1), pu = rot*vec3(1,0,0), pv = rot*vec3(0,1,0);
  // the crystal is a slab: near face at +thick/2 (towards the camera), far face at -thick/2
  float sgn = sign(dot(ro, pn));
  float hz = .5*thick/zoom*sgn;
  float t = (hz - dot(ro, pn))/dot(rd, pn);
  vec3 hit = ro + rd*t;
  vec2 lp = vec2(dot(hit, pu), dot(hit, pv)) * zoom;     // lattice units, near face
  float tb = (-hz - dot(ro, pn))/dot(rd, pn);
  vec3 hitb = ro + rd*tb;
  vec2 lpb = vec2(dot(hitb, pu), dot(hitb, pv)) * zoom;  // far face
  float px = zoom/R.y * t/2.4;                           // lattice units per pixel
  vec4 f = F(lp);
  vec3 sky = texture(SKYT, gl_FragCoord.xy/R).rgb;
  vec4 gxV, gyV, gx0, gy0;
  f = tri(V, lp, gxV, gyV);
  vec4 f0 = tri(V0, lp, gx0, gy0);
  // smooth gradients by central differences over ~1 cell (piecewise-linear gradients look tiled)
  float e = max(px, .8);
  vec4 fx1 = F(lp+vec2(e,0)), fx0 = F(lp-vec2(e,0)), fy1 = F(lp+vec2(0,e)), fy0 = F(lp-vec2(0,e));
  vec2 gm = vec2(fx1.r - fx0.r, fy1.r - fy0.r)/(2.*e);
  float cN = f.g/max(f.r,1e-3)/beta;
  vec2 gc = vec2(fx1.g - fx0.g, fy1.g - fy0.g)/(2.*e*beta);
  float m = smoothstep(.5 - max(px,.05)*.7, .5 + max(px,.05)*.7, mix(f0.r, f.r, .5));
  vec3 col = sky;
  float aura = smoothstep(.0, .5, f.r) * (1. - m);
  col += iceCol * aura * .05;
  if (vapour > 0.) col = mix(col, vec3(.1,.35,.9)*f.a*1.8 + vec3(.9,.95,1.)*m, vapour*.9);
  if (m > 0.) {
    vec3 v = -rd;
    vec2 suv = gl_FragCoord.xy/R;
    // relief normal (outline bevel + mass terraces)
    vec2 g = gm*bevel + gc*slope;
    vec3 nL = normalize(vec3(-g, 1.));
    vec3 n = rot*nL;
    // transmitted background, slightly displaced by the relief, per channel (dispersion)
    vec2 off = (rot*vec3(nL.xy,0.)).xy*.012;
    vec3 behind = vec3(texture(SKYT, suv - off).r, texture(SKYT, suv - off*1.25).g, texture(SKYT, suv - off*1.5).b);
    // dark-field: steep facets bend the off-axis lamps into the eye -> bright edges & ribs with colour fringes
    float sl = length(g);
    // edge orientation picks which coloured lamp it catches
    vec2 gd = sl > 1e-4 ? -g/sl : vec2(0.);
    vec2 gs = (rot*vec3(gd, 0.)).xy;
    float ew = smoothstep(.03, .7, sl);
    vec3 tr = lampA*(.12 + pow(max(dot(gs, dirA.xy), 0.), 2.5))
            + lampB*(.06 + pow(max(dot(gs, dirB.xy), 0.), 2.5))
            + lampC*pow(max(dot(gs, dirC.xy), 0.), 3.);
    tr *= ew*edgeGain;
    vec3 ice = behind*.9 + iceCol*(.07 + .12*cN) + tr;
    // soft top light on the terraces
    vec3 L = normalize(vec3(-.5, .65, .6));
    ice += iceCol*.22*pow(max(dot(n, L), 0.), 3.)*clamp(cN, 0., 1.5);
    float spec = pow(max(dot(reflect(-v, n), L), 0.), 60.);
    float fr = pow(1. - max(dot(n, v), 0.), 5.);
    // micro-facet glints, a few cells at a time, twinkling as the crystal turns
    vec2 cell = floor(lp*.5);
    float hsh = h21(cell);
    vec3 mn = normalize(n + .5*vec3(h21(cell+3.1)-.5, h21(cell+7.7)-.5, 0.));
    float glint = pow(max(dot(reflect(-v, mn), L), 0.), 250.) * step(.93, hsh);
    ice += keyCol*(spec*.5 + glint*4.) + rimCol*fr*.3;
    // freshly frozen ice glows as it crystallises
    ice += glowCol * f.b * glowAmt;
    if (dbg > 2.5) ice = vec3(sl*.5, cN*.5, f.b);
    if (dbg > 3.5) ice = vec3(gs*.5+.5, ew);
    if (dbg > 4.5) ice = tr;
    col = mix(col, ice, m);
  }
  // side walls: the ray misses the near face but the far face is under it -> we look through a facet edge
  vec4 fb = F(lpb);
  float mb = smoothstep(.35, .65, fb.r) * (1. - m);
  if (mb > 0.) {
    vec2 gb = vec2(F(lpb+vec2(1.,0)).r - F(lpb-vec2(1.,0)).r, F(lpb+vec2(0,1.)).r - F(lpb-vec2(0,1.)).r);
    vec2 gs2 = (rot*vec3(-normalize(gb+1e-5), 0.)).xy;
    vec3 wall = lampA*(.25 + pow(max(dot(gs2, dirA.xy), 0.), 2.)) + lampB*(.15 + pow(max(dot(gs2, dirB.xy), 0.), 2.)) + lampC*.2;
    col = mix(col, sky*.6 + wall*edgeGain*.9 + glowCol*fb.b*glowAmt, mb);
  }
  o = vec4(col, 1.);
}`;

// ---- post ----------------------------------------------------------------------------------
const BRIGHT = P + `uniform sampler2D A; uniform float thr; void main(){ vec3 c = texture(A, uv).rgb; float l = max(c.r, max(c.g, c.b)); o = vec4(c*smoothstep(thr, thr+.6, l), 1.); }`;
const DOWN = P + `uniform sampler2D A; uniform vec2 texel; void main(){ vec3 c = vec3(0.);
  c += texture(A, uv + texel*vec2(-1,-1)).rgb + texture(A, uv + texel*vec2(1,-1)).rgb + texture(A, uv + texel*vec2(-1,1)).rgb + texture(A, uv + texel*vec2(1,1)).rgb;
  o = vec4(c*.25, 1.); }`;
const UP = P + `uniform sampler2D A, B; uniform vec2 texel; uniform float k; void main(){
  vec3 c = texture(A, uv + texel*vec2(-1,0)).rgb + texture(A, uv + texel*vec2(1,0)).rgb + texture(A, uv + texel*vec2(0,1)).rgb + texture(A, uv + texel*vec2(0,-1)).rgb;
  o = vec4(c*.25*k + texture(B, uv).rgb, 1.); }`;
const FINAL = P + NOISE + `uniform sampler2D A, BL; uniform vec2 R; uniform float time, bloom, expo, fade;
vec3 aces(vec3 x){ return clamp((x*(2.51*x+.03))/(x*(2.43*x+.59)+.14), 0., 1.); }
void main(){ vec2 c = uv - .5;
  float ca = dot(c,c)*.006;
  vec3 col = vec3(texture(A, uv - c*ca).r, texture(A, uv).g, texture(A, uv + c*ca).b);
  col += texture(BL, uv).rgb * bloom;
  col *= expo;
  col *= 1. - .55*smoothstep(.25, 1.1, length(c*vec2(R.x/R.y, 1.)));
  col = aces(col);
  col = pow(col, vec3(1./2.2));
  col += (h21(gl_FragCoord.xy + fract(time)*91.) - .5)*.035;
  o = vec4(col*fade, 1.); }`;

export class Renderer {
  constructor(gl, N) {
    this.gl = gl; this.N = N;
    this.p = {
      view: program(gl, VIEW), hblur: program(gl, HBLUR), sky: program(gl, SKY),
      bokeh: program(gl, BOKEH_FS, BOKEH_VS), flake: program(gl, FLAKE),
      bright: program(gl, BRIGHT), down: program(gl, DOWN), up: program(gl, UP), final: program(gl, FINAL),
    };
    const half = { internal: gl.RGBA16F, type: gl.HALF_FLOAT, filter: gl.LINEAR };
    this.V0 = target(gl, N, N, half);
    this.V1 = target(gl, N, N, half);
    this.half = half; this.w = 0; this.h = 0;
    this.quad = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, this.quad);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]), gl.STATIC_DRAW);
    this.bvao = gl.createVertexArray(); gl.bindVertexArray(this.bvao);
    gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
    gl.bindVertexArray(gl.__vao);
  }
  resize(w, h) {
    if (w === this.w && h === this.h) return;
    const gl = this.gl; this.w = w; this.h = h;
    for (const k of ['sky', 'scene', 'bl0']) if (this[k]) { gl.deleteTexture(this[k].t); gl.deleteFramebuffer(this[k].f); }
    this.sky = target(gl, w, h, this.half); this.scene = target(gl, w, h, this.half);
    this.mips = [];
    let mw = w >> 1, mh = h >> 1;
    for (let i = 0; i < 6 && mw > 8; i++) { this.mips.push([target(gl, mw, mh, this.half), target(gl, mw, mh, this.half)]); mw >>= 1; mh >>= 1; }
  }
  frame(sim, s) {
    const gl = this.gl, N = this.N, R = [this.w, this.h];
    // 1. lattice -> filterable view
    pass(gl, this.p.view, this.V0, { S: sim.tex }, { N, T: sim.T, tau: s.tau });
    pass(gl, this.p.hblur, this.V1, { V: this.V0 }, { N });
    // 2. sky + bokeh behind
    pass(gl, this.p.sky, this.sky, {}, { R, time: s.time, fall: s.fall, cA: s.cA, cB: s.cB, cC: s.cC, cWarm: s.cWarm, warm: s.warm });
    this.bokeh(this.sky, 0, s, 70);
    this.bokeh(this.sky, 1, s, 10);
    // 3. crystal
    pass(gl, this.p.flake, this.scene, { V: this.V1, V0: this.V0, SKYT: this.sky }, {
      R, N, zoom: s.zoom, time: s.time, glowAmt: s.glow, beta: s.beta, vapour: s.vapour,
      keyCol: s.keyCol, rimCol: s.rimCol, iceCol: s.iceCol, glowCol: s.glowCol, rot: s.rot,
      lampA: s.lampA, lampB: s.lampB, lampC: s.lampC, dirA: s.dirA, dirB: s.dirB, dirC: s.dirC, slope: s.slope, bevel: s.bevel, dbg: s.dbg || 0, edgeGain: s.edgeGain, thick: s.thick });
    // 4. bloom
    const m = this.mips;
    pass(gl, this.p.bright, m[0][0], { A: this.scene }, { thr: s.bloomThr });
    for (let i = 1; i < m.length; i++) pass(gl, this.p.down, m[i][0], { A: m[i - 1][0] }, { texel: [1 / m[i - 1][0].w, 1 / m[i - 1][0].h] });
    for (let i = m.length - 1; i > 0; i--) {
      const src = i === m.length - 1 ? m[i][0] : m[i][1];
      pass(gl, this.p.up, m[i - 1][1], { A: src, B: m[i - 1][0] }, { texel: [1 / src.w, 1 / src.h], k: 1 });
    }
    // 5. finish
    pass(gl, this.p.final, null, { A: s.dbg === 1 ? this.sky : s.dbg === 2 ? this.V1 : this.scene, BL: m[0][1] }, { R, time: s.time, bloom: s.bloom, expo: s.expo, fade: s.fade });
  }
  bokeh(dst, layer, s, count) {
    const gl = this.gl;
    gl.useProgram(this.p.bokeh.p); gl.bindFramebuffer(gl.FRAMEBUFFER, dst.f); gl.viewport(0, 0, dst.w, dst.h);
    const u = this.p.bokeh.u;
    gl.uniform2f(u.R, this.w, this.h); gl.uniform1f(u.time, s.time); gl.uniform1f(u.fall, s.fall); gl.uniform1f(u.layer, layer);
    gl.uniform3fv(u.tint, s.bokehTint);
    gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE);
    gl.bindVertexArray(this.bvao); gl.drawArraysInstanced(gl.TRIANGLES, 0, 6, count); gl.bindVertexArray(gl.__vao);
    gl.disable(gl.BLEND);
  }
}
