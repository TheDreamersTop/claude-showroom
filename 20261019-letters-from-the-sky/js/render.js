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

// birth record per cell: weather at the step it froze (from the timeline), normalised attach time
const VIEW2 = P + `uniform highp sampler2D S, TL; uniform float T, stride;
void main(){ vec4 s = texelFetch(S, ivec2(gl_FragCoord.xy), 0);
  if (s.r <= 0.) { o = vec4(0.); return; }
  int slot = int(s.r/stride); ivec2 a = ivec2(slot % 4096, slot / 4096);
  vec4 w = texelFetch(TL, a, 0);
  o = vec4(w.x, w.y, s.r/T, w.z); }`;

// 7-tap hex blur in axial space (keeps 6-fold symmetry of the field)
const HBLUR = P + `uniform sampler2D V; uniform float N;
void main(){ ivec2 q = ivec2(gl_FragCoord.xy);
  vec4 s = texelFetch(V, q, 0)*2.;
  s += texelFetch(V, q+ivec2(1,0),0) + texelFetch(V, q+ivec2(-1,0),0) + texelFetch(V, q+ivec2(0,1),0)
     + texelFetch(V, q+ivec2(0,-1),0) + texelFetch(V, q+ivec2(1,-1),0) + texelFetch(V, q+ivec2(-1,1),0);
  vec4 c = texelFetch(V, q, 0);
  o = vec4(s.rg/8., max(c.b, s.b/8.), c.a); }`;

// ---- sky -------------------------------------------------------------------------------------
const SKY = P + NOISE + `uniform vec2 R; uniform float time, fall, mapK; uniform vec3 cA, cB, cC, cWarm; uniform float warm; uniform sampler2D HAB; uniform vec2 cursor;
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
  // the screen is the Nakaya diagram: faint habit tints and hairline borders, brightest around the cursor
  if (mapK > 0.) {
    vec2 su = gl_FragCoord.xy/R; vec4 hm = texture(HAB, su);
    vec2 dc = (su - cursor)*vec2(R.x/R.y, 1.);
    float near = exp(-dot(dc, dc)*16.);

  }
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
void main(){ float r = length(lp);
  float m = smoothstep(1., .82, r);
  float ring = smoothstep(.6, 1., r)*m;
  o = vec4(tint*(m*.18 + ring*.22)*a, 1.); }`;

// ---- knitted wool (the landing surface), band-limited for depth of field ----------------------
const WOOL = P + NOISE + `uniform vec3 spot; uniform vec2 R, pan, livePos; uniform float zoom, time, focusBlur, tilt, mixK, sparkle, shadowK, liveRot, NV, liveK; uniform vec3 woolCol, woolCol2, keyCol; uniform sampler2D LV;
uniform sampler2D SKYT;
// one knit leg: an ellipse slanted by ang, returns height (0..1) and local coords
float leg(vec2 p, vec2 c, float ang, out vec2 lc){ vec2 d = p - c; float ca = cos(ang), sa = sin(ang);
  lc = vec2(ca*d.x + sa*d.y, -sa*d.x + ca*d.y) / vec2(.2, .74);
  float r = length(lc); return sqrt(max(0., 1. - r*r)); }
void main(){
  vec2 sp = (gl_FragCoord.xy - .5*R)/R.y;
  // tilted table: depth varies along y; blur grows away from the focus line
  float depth = sp.y*tilt;
  float b = clamp(focusBlur + abs(depth)*1.8, 0., 1.);
  vec2 q = (sp*(1. + depth*.35))*zoom + pan;       // lattice units on the table
  vec2 st = q / vec2(320., 250.);                  // stitch grid (a fine knit, ~1.3 mm)
  st += (vec2(fbm(q*.0014), fbm(q*.0014 + 5.2)) - .5)*.35;   // hand-knit irregularity
  vec2 id = floor(st), f = fract(st);
  float hBest = 0.; vec2 lcB = vec2(0.); float side = 0.;
  for (int dy=-1; dy<=1; dy++){
    vec2 ff = f - vec2(0., float(dy));
    vec2 lc; float hL = leg(ff, vec2(.3, .5), .5, lc);
    if (hL > hBest) { hBest = hL; lcB = lc; side = -1.; }
    hL = leg(ff, vec2(.7, .5), -.5, lc);
    if (hL > hBest) { hBest = hL; lcB = lc; side = 1.; }
  }
  float detail = 1. - b;
  float h = smoothstep(0., .3 + b*.7, hBest);
  // fibres: many thin, rim-lit strands running along the yarn leg, each with its own brightness and wobble
  float fib = 0.;
  for (int k=0;k<3;k++){ float fk = float(k);
    float x = lcB.x*(22. + fk*13.) + fbm(vec2(lcB.y*(1.2 + fk*.4), fk*3.1) + id*1.7)*(3. + fk);
    float line = pow(1. - abs(sin(x*3.14159)), 18. + fk*10.);
    fib += line*(.35 + .65*h21(vec2(floor(x), fk) + id*7.))*(1. - fk*.2); }
  fib *= smoothstep(0., .25, hBest);   // fibres fade at the yarn edge instead of stopping at the cell border
  // raking key light from the upper left across the round yarn
  vec2 nrm2 = lcB*vec2(1., .35); float lit = clamp(.55 + .6*dot(normalize(vec3(nrm2, .8)), normalize(vec3(-.7, .5, .6))), 0., 1.2);
  vec3 base = mix(woolCol, woolCol2, smoothstep(.25, .75, fbm(st*.35 + 3.7)));   // continuous dye variation (no per-stitch steps)
  base *= .85 + .3*fbm(q*.004);                     // heather
  vec3 col = base*(.16 + .6*pow(h, 1.3)*lit);
  col += mix(base*3.2, keyCol*.35, .35)*fib*h*lit*detail*.55;
  // stray hairs crossing the gaps: short straight segments, thin and rim-lit
  vec2 hc = q/260.; vec2 hid = floor(hc); float hair = 0.;
  for (int j=-1;j<=1;j++) for (int i=-1;i<=1;i++){ vec2 cid = hid + vec2(i,j); float rh = h21(cid*1.3);
    if (rh < .55) continue;
    vec2 p0 = (cid + vec2(h21(cid+.7), h21(cid+2.3)))*260.; float an = h21(cid+5.1)*6.283;
    vec2 dir = vec2(cos(an), sin(an)); vec2 dq = q - p0; float along = dot(dq, dir);
    float d = abs(dot(dq, vec2(-dir.y, dir.x)) + .0035*along*along*(rh - .78) + 6.*sin(along*.02 + rh*9.));
    hair += smoothstep(2. + b*40., 0., d)*smoothstep(200., 40., abs(along))*(.3 + rh)*(1. - b*.8); }
  col += keyCol*.05*hair*(1. - h*.7);
  col *= mix(1., .4 + .6*h, .85);                   // occlusion between the legs
  col = mix(col, base*.16, b*.55);                  // defocus flattens contrast
  // shadow (and focused light at its rim) of the crystal lying on the fibres
  if (shadowK > 0.) {
    vec2 d0 = q - livePos - vec2(7., -9.);
    float ca2 = cos(liveRot), sa2 = sin(liveRot); vec2 lq = vec2(ca2*d0.x + sa2*d0.y, -sa2*d0.x + ca2*d0.y) / liveK;
    float jj = lq.y*1.1547005; vec2 ax = vec2(lq.x - jj*.5, jj) + NV*.5;
    float sh = textureLod(LV, (ax + .5)/NV, 2.5).r;
    col *= 1. - .34*shadowK*smoothstep(.1, .7, sh);
  }
  // frost sparkles on the fibres (out of focus they become soft hexagonal bokeh)
  vec2 sq = q/90.; vec2 sid = floor(sq); vec2 sf = fract(sq) - .5;
  float hs = h21(sid);
  if (hs > .94 && h > .3) { vec2 o2 = vec2(h21(sid+1.3), h21(sid+2.7)) - .5; vec2 d = abs(sf - o2*.6);
    float rad = .03 + b*.12; float rr = length(d);
    float tw = .5 + .5*sin(time*(1.5 + hs*3.) + hs*40.);
    col += keyCol*smoothstep(rad, 0., rr)*tw*sparkle*(1. - b)*.5; }
  // a soft pool of light around the collection, falling off into the dark cloth
  col *= mix(.5, 1.18, exp(-dot(sp - spot.xy, sp - spot.xy)/(spot.z*spot.z)));
  vec3 sky = texture(SKYT, gl_FragCoord.xy/R).rgb;
  o = vec4(mix(sky, col, mixK), 1.); }`;

// ---- gallery: earlier letters lying on the wool (texture array, one layer per letter) --------
const GALLERY = `#version 300 es
precision highp float; precision highp int; precision highp sampler2DArray;
in vec2 uv; out vec4 o;
uniform highp sampler2DArray LT; uniform sampler2D BG; uniform vec2 R, pan; uniform float zoom, count, time, hoverId, NL, alpha;
uniform vec4 slots[16];      // xy = table position (lattice units), z = rotation, w = scale (letter lattice per texel)
uniform vec3 lampA, lampB, lampC, dirA, dirB, dirC, iceCol, keyCol; uniform float edgeGain, bevel, slope, terrace, ringK; uniform sampler2D HAB;
vec2 toAx(vec2 p){ float j = p.y*1.1547005; return vec2(p.x - j*.5, j) + NL*.5; }
// triangle interpolation on the hex lattice (straight facets), from the full-resolution layer
vec4 triA(float L, vec2 a){ vec2 i = floor(a); vec2 f = a - i; ivec3 q = ivec3(ivec2(i), int(L));
  vec4 v10 = texelFetch(LT, q+ivec3(1,0,0), 0), v01 = texelFetch(LT, q+ivec3(0,1,0), 0);
  if (f.x + f.y < 1.) { vec4 v00 = texelFetch(LT, q, 0); return v00 + f.x*(v10 - v00) + f.y*(v01 - v00); }
  vec4 v11 = texelFetch(LT, q+ivec3(1,1,0), 0); return v11 - (1.-f.x)*(v11 - v01) - (1.-f.y)*(v11 - v10); }
vec4 LS(float L, vec2 lpp, float lod){ vec2 a = toAx(lpp); return lod < .6 ? triA(L, a - .5) : textureLod(LT, vec3(a/NL, L), lod); }
void main(){ vec2 sp = (gl_FragCoord.xy - .5*R)/R.y;
  vec3 col = texture(BG, gl_FragCoord.xy/R).rgb;
  vec2 q = sp*zoom + pan;
  float px = zoom/R.y;
  for (int i=0;i<16;i++){ if (float(i) >= count) break;
    vec4 sl = slots[i]; vec2 d = q - sl.xy; float ca = cos(sl.z), sa = sin(sl.z);
    vec2 lpp = vec2(ca*d.x + sa*d.y, -sa*d.x + ca*d.y) / sl.w;   // texel units
    float hovI = hoverId == float(i) ? 1. : 0.;
    // one soft shadow, cast slightly down-right; it separates when the letter is lifted (hover)
    { vec2 ds = d - vec2(7., -9.)*(1. + hovI*2.5); vec2 ls = vec2(ca*ds.x + sa*ds.y, -sa*ds.x + ca*ds.y) / sl.w; vec2 as2 = toAx(ls);
      if (as2.x > 1. && as2.y > 1. && as2.x < NL-2. && as2.y < NL-2.) {
        float sh = textureLod(LT, vec3(as2/NL, float(i)), log2(max(px/sl.w, 1.)) + 1.5).r;
        vec2 eb = min(as2, NL - as2); float edgeF = smoothstep(4., 40., min(eb.x, eb.y));
        col *= 1. - (.34 - hovI*.12)*alpha*smoothstep(.1, .7, sh)*edgeF; } }
    if (abs(lpp.x) > NL*.5 || abs(lpp.y) > NL*.5) continue;
    vec2 a = toAx(lpp); if (a.x < 2. || a.y < 2. || a.x > NL-3. || a.y > NL-3.) continue;
    float lod = log2(max(px/sl.w, 1.));
    float fi = float(i);
    vec4 f = LS(fi, lpp, lod);
    float e = max(px/sl.w, .8);
    vec4 fx1 = LS(fi, lpp+vec2(e,0), lod), fx0 = LS(fi, lpp-vec2(e,0), lod), fy1 = LS(fi, lpp+vec2(0,e), lod), fy0 = LS(fi, lpp-vec2(0,e), lod);
    float pw = max(px/sl.w, .08)*.6;
    float m = smoothstep(.5 - pw, .5 + pw, f.r);
    if (m <= 0.) continue;
    // the live crystal's material: outline bevel + mass relief, edge orientation picks a coloured lamp
    vec2 gm = vec2(fx1.r - fx0.r, fy1.r - fy0.r)/(2.*e), gc = vec2(fx1.g - fx0.g, fy1.g - fy0.g)/(2.*e);
    vec2 gH = vec2(fx1.a - fx0.a, fy1.a - fy0.a)/(2.*e), gT = vec2(fx1.b - fx0.b, fy1.b - fy0.b)/(2.*e);
    float inner = smoothstep(.97, 1., f.r);
    vec2 g = gm*bevel + (gc - gH*terrace*inner)*slope;
    float sl2 = length(g); vec2 gd = sl2 > 1e-4 ? -g/sl2 : vec2(0.);
    vec2 gs = vec2(ca*gd.x - sa*gd.y, sa*gd.x + ca*gd.y);
    float ew = smoothstep(.03, .7, sl2);
    float small = clamp(px/sl.w, 1., 1.8);   // small on screen: edges carry the ice, so light them harder
    vec3 tr = (lampA*(.05 + pow(max(dot(gs, dirA.xy), 0.), 2.5)) + lampB*(.03 + pow(max(dot(gs, dirB.xy), 0.), 2.5)) + lampC*pow(max(dot(gs, dirC.xy), 0.), 3.))*ew*edgeGain*small*1.15;
    float ring = clamp((length(gT) + length(gH))*inner*ringK, 0., 1.);
    vec3 birthTint = pow(texture(HAB, vec2(f.b, f.a)).rgb, vec3(2.2))*2.2;
    vec3 ice = col*.9 + iceCol*(.06 + .11*f.g)*mix(vec3(1.), birthTint, .5/small) + tr + (lampA*.6 + lampB*.3)*ring*edgeGain*.8;
    vec3 n = normalize(vec3(-g, 1.));
    ice += iceCol*.22*pow(max(dot(n, normalize(vec3(-.5, .65, .6))), 0.), 3.)*clamp(f.g, 0., 1.5);
    vec2 cell = floor(lpp*.5); float hsh = fract(sin(dot(cell + fi*17., vec2(12.9898, 78.233)))*43758.5453);
    ice += keyCol*step(.965, hsh)*pow(.5 + .5*sin(time*(1.2 + hsh*2.) + hsh*30.), 24.)*1.5;   // twinkling glints
    ice *= 1. + hovI*.25;
    col = mix(col, ice, m*alpha);
  }
  o = vec4(col, 1.); }`;

// packs a finished crystal into one layer of the letters array: mask, mass, birth temperature, birth humidity
const PACK = P + `uniform sampler2D V, VT; uniform float N, NL, beta;
void main(){ vec2 a = gl_FragCoord.xy/NL; vec4 v = texture(V, a); vec4 t = texture(VT, a);
  o = vec4(v.r, v.g/max(v.r,1e-3)/beta, t.x, t.y); }`;

// ---- crystal ----------------------------------------------------------------------------------
const FLAKE = P + NOISE + `
uniform sampler2D V, V0, VT, SKYT, HAB; uniform highp sampler2D SIM; uniform float replay; uniform vec2 ofs; uniform vec2 R; uniform float N, zoom, time, glowAmt, beta, vapour;
uniform mat3 rot; uniform vec3 keyCol, rimCol, iceCol, glowCol, lampA, lampB, lampC, dirA, dirB, dirC; uniform float slope, bevel, dbg, edgeGain, thick, ringK, terrace, simBox, rho0, sweepPos, sweepAmt;
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
// replay visibility: hidden if any cell around p froze after the replay time
float shown(vec2 p){ if (replay > 1.5) return 1.; ivec2 q = ivec2(floor(toAx(p) + .5)); float z = texelFetch(VT, q, 0).z;
  z = max(z, max(texelFetch(VT, q+ivec2(1,0), 0).z, texelFetch(VT, q+ivec2(-1,0), 0).z));
  z = max(z, max(texelFetch(VT, q+ivec2(0,1), 0).z, texelFetch(VT, q+ivec2(0,-1), 0).z));
  z = max(z, max(texelFetch(VT, q+ivec2(1,-1), 0).z, texelFetch(VT, q+ivec2(-1,1), 0).z));
  return 1. - step(replay, z); }
void main(){
  vec2 sp = (gl_FragCoord.xy - .5*R)/R.y;
  // camera ray onto the tilted plane of the crystal
  vec3 ro = vec3(0., 0., 2.4), rd = normalize(vec3(sp, -2.4));
  vec3 pn = rot*vec3(0,0,1), pu = rot*vec3(1,0,0), pv = rot*vec3(0,1,0);
  // the crystal is a slab: near face at +thick/2 (towards the camera), far face at -thick/2
  vec3 C = vec3(ofs, 0.);
  float sgn = sign(dot(ro - C, pn));
  float hz = .5*thick/zoom*sgn;
  float t = (hz - dot(ro - C, pn))/dot(rd, pn);
  vec3 hit = ro + rd*t - C;
  vec2 lp = vec2(dot(hit, pu), dot(hit, pv)) * zoom;     // lattice units, near face
  float tb = (-hz - dot(ro - C, pn))/dot(rd, pn);
  vec3 hitb = ro + rd*tb - C;
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
  float e2 = max(px, 1.7);
  vec2 gc = vec2(F(lp+vec2(e2,0)).g - F(lp-vec2(e2,0)).g, F(lp+vec2(0,e2)).g - F(lp-vec2(0,e2)).g)/(2.*e2*beta);
  float m = smoothstep(.5 - max(px,.28)*.7, .5 + max(px,.28)*.7, mix(f0.r, f.r, .5));
  float magK = mix(.55, 1., smoothstep(.25, .9, px));   // magnified (small) crystals: thinner light on their edges
  // birth record: weather (temperature x, humidity y) when each cell froze, z = attach time / now
  vec4 bgx, bgy; vec4 bw = tri(VT, lp, bgx, bgy);
  float inner = smoothstep(.97, 1., f0.r);
  vec2 gT = vec2(bgx.x, bgy.x)*inner, gH = vec2(bgx.y, bgy.y)*inner;
  float ring = clamp((length(gT) + length(gH))*ringK, 0., 1.);
  // dry growth builds thicker plate faces than humid growth: humidity changes leave terraces
  gc += -gH*terrace;
  float rmask = shown(lp);
  m *= rmask;
  vec3 col = sky;
  float aura = smoothstep(.0, .5, f.r) * (1. - m) * rmask;
  col += iceCol * aura * .05;
  if (vapour > 0.) {
    // the invisible made visible: vapour is consumed near the ice; show the depleted halo and its isolines
    vec2 ax0 = toAx(lp) - N*.5; float hd = max(max(abs(ax0.x), abs(ax0.y)), abs(ax0.x + ax0.y));
    float inside = smoothstep(simBox, simBox*.8, hd);
    vec4 a1, a2; float d = tri(SIM, lp, a1, a2).a / max(rho0, 1e-3);
    float dep = clamp(1. - d, 0., 1.);
    float iso = abs(fract(d*12.) - .5);
    vec3 vc = vec3(.02, .08, .24)*pow(dep, .7) + vec3(.35, .65, 1.)*smoothstep(.04, .0, iso)*.16*(.3 + dep);
    col = mix(col, col*.35 + vc, vapour*inside*(1. - m)); }
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
    vec3 tr = lampA*(.05 + pow(max(dot(gs, dirA.xy), 0.), 2.5))
            + lampB*(.03 + pow(max(dot(gs, dirB.xy), 0.), 2.5))
            + lampC*pow(max(dot(gs, dirC.xy), 0.), 3.);
    tr *= ew*edgeGain*magK;
    // body tint remembers the temperature it grew in: mild = green-cyan, cold = violet-blue
    vec3 birthTint = pow(texture(HAB, vec2(bw.x, bw.y)).rgb, vec3(2.2))*2.2;
    vec3 ice = behind*.9 + iceCol*(.05 + .10*cN)*mix(vec3(1.), birthTint, .5*step(.001, bw.z)) + tr;
    // growth contours: thin ridges every 1/14 of the crystal's life (hexagons inside plates, bands across arms)
    { float zz = bw.z*14.; float dz = min(fract(zz), 1. - fract(zz)); float fw = fwidth(zz);
      float gl2 = (1. - smoothstep(0., fw*1.3, dz))*inner*smoothstep(.35, .12, fw)*step(.001, bw.z);
      ice += (lampA*.5 + lampB*.25)*gl2*.09*edgeGain; }
    // growth rings where the weather changed: a thin ridge that catches the lamps
    ice += (lampA*.6 + lampB*.3) * smoothstep(0., 1., ring) * edgeGain * .45 * magK;
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
    // landing: a narrow beam of light sweeps across and catches every ridge
    if (sweepAmt > 0.) { float sw = exp(-pow((dot(sp - ofs, normalize(vec2(1., .55))) - sweepPos)/.035, 2.));
      ice += (keyCol*.25 + tr*2.2 + iceCol*ring)*sw*sweepAmt; }
    if (dbg > 2.5) ice = vec3(sl*.5, cN*.5, f.b);
    if (dbg > 3.5) ice = vec3(gs*.5+.5, ew);
    if (dbg > 4.5) ice = tr;
    if (dbg > 5.5) ice = vec3(bw.z, bw.x, bw.y);
    col = mix(col, ice, m);
  }
  // side walls: the ray misses the near face but the far face is under it -> we look through a facet edge
  vec4 fb = F(lpb);
  float rb = shown(lpb);
  float mb = smoothstep(.35, .65, fb.r) * (1. - m) * rb;
  if (mb > 0.) {
    vec2 gb = vec2(F(lpb+vec2(1.,0)).r - F(lpb-vec2(1.,0)).r, F(lpb+vec2(0,1.)).r - F(lpb-vec2(0,1.)).r);
    vec2 gs2 = (rot*vec3(-normalize(gb+1e-5), 0.)).xy;
    vec3 wall = lampA*(.25 + pow(max(dot(gs2, dirA.xy), 0.), 2.)) + lampB*(.15 + pow(max(dot(gs2, dirB.xy), 0.), 2.)) + lampC*.2;
    col = mix(col, sky*.6 + wall*edgeGain*.55 + glowCol*fb.b*glowAmt, mb);
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
const FINAL = P + NOISE + `uniform sampler2D A, BL; uniform vec2 R; uniform float time, bloom, expo, fade; uniform vec3 breath;
vec3 aces(vec3 x){ return clamp((x*(2.51*x+.03))/(x*(2.43*x+.59)+.14), 0., 1.); }
void main(){ vec2 c = uv - .5;
  float ca = dot(c,c)*.006;
  vec3 col = vec3(texture(A, uv - c*ca).r, texture(A, uv).g, texture(A, uv + c*ca).b);
  col += texture(BL, uv).rgb * bloom;
  // warm breath fogging the lens around the pointer
  vec2 bd = (uv - breath.xy)*vec2(R.x/R.y, 1.);
  float fog = breath.z*exp(-dot(bd, bd)*38.)*(.6 + .4*fbm(uv*9. + time*.4));
  col = mix(col, col*.6 + vec3(.20, .14, .10), fog*.5);
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
      view: program(gl, VIEW), view2: program(gl, VIEW2), hblur: program(gl, HBLUR), sky: program(gl, SKY),
      bokeh: program(gl, BOKEH_FS, BOKEH_VS), flake: program(gl, FLAKE),
      wool: program(gl, WOOL), copy: program(gl, P + `uniform sampler2D A; void main(){ o = texelFetch(A, ivec2(gl_FragCoord.xy), 0); }`), gallery: program(gl, GALLERY), pack: program(gl, PACK),
      bright: program(gl, BRIGHT), down: program(gl, DOWN), up: program(gl, UP), final: program(gl, FINAL),
    };
    const half = { internal: gl.RGBA16F, type: gl.HALF_FLOAT, filter: gl.LINEAR };
    this.V0 = target(gl, N, N, half);
    this.V1 = target(gl, N, N, half);
    this.V1m = target(gl, N, N, { internal: gl.RGBA16F, type: gl.HALF_FLOAT, filter: gl.LINEAR });
    gl.bindTexture(gl.TEXTURE_2D, this.V1m.t); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR); gl.generateMipmap(gl.TEXTURE_2D);
    this.VT = target(gl, N, N, { internal: gl.RGBA16F, type: gl.HALF_FLOAT, filter: gl.NEAREST });
    this.TL = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, this.TL);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA32F, 4096, 4, 0, gl.RGBA, gl.FLOAT, null);
    for (const k of [gl.TEXTURE_MIN_FILTER, gl.TEXTURE_MAG_FILTER]) gl.texParameteri(gl.TEXTURE_2D, k, gl.NEAREST);
    this.half = half; this.w = 0; this.h = 0;
    // letters: one RGBA16F layer per finished crystal, mipmapped for the zoomed-out gallery
    this.NL = 512; this.maxLetters = 16;
    this.LT = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D_ARRAY, this.LT);
    gl.texStorage3D(gl.TEXTURE_2D_ARRAY, 6, gl.RGBA16F, this.NL, this.NL, this.maxLetters);
    gl.texParameteri(gl.TEXTURE_2D_ARRAY, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
    gl.texParameteri(gl.TEXTURE_2D_ARRAY, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D_ARRAY, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D_ARRAY, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    this.packFB = gl.createFramebuffer();
    this.quad = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, this.quad);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]), gl.STATIC_DRAW);
    this.bvao = gl.createVertexArray(); gl.bindVertexArray(this.bvao);
    gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
    gl.bindVertexArray(gl.__vao);
  }
  resize(w, h) {
    if (w === this.w && h === this.h) return;
    const gl = this.gl; this.w = w; this.h = h;
    for (const k of ['sky', 'scene', 'bg2']) if (this[k]) { gl.deleteTexture(this[k].t); gl.deleteFramebuffer(this[k].f); }
    this.sky = target(gl, w, h, this.half); this.scene = target(gl, w, h, this.half); this.bg2 = target(gl, w, h, this.half);
    this.mips = [];
    let mw = w >> 1, mh = h >> 1;
    for (let i = 0; i < 6 && mw > 8; i++) { this.mips.push([target(gl, mw, mh, this.half), target(gl, mw, mh, this.half)]); mw >>= 1; mh >>= 1; }
  }
  frame(sim, s) {
    const gl = this.gl, N = this.N, R = [this.w, this.h];
    // 1. lattice -> filterable view
    pass(gl, this.p.view, this.V0, { S: sim.tex }, { N, T: sim.T, tau: s.tau });
    pass(gl, this.p.hblur, this.V1, { V: this.V0 }, { N });
    pass(gl, this.p.view2, this.VT, { S: sim.tex, TL: this.TL }, { T: Math.max(sim.T, 1), stride: s.stride });
    // 2. sky + bokeh behind
    pass(gl, this.p.sky, this.sky, { HAB: this.HAB }, { R, mapK: s.mapK || 0, cursor: s.cursor || [.5, .5], time: s.time, fall: s.fall, cA: s.cA, cB: s.cB, cC: s.cC, cWarm: s.cWarm, warm: s.warm });
    this.bokeh(this.sky, 0, s, 9);
    
    // 2b. wool table and the earlier letters on it
    let bg = this.sky;
    if (s.woolMix > 0) {
      if (s.shadowK > 0) { pass(gl, this.p.copy, this.V1m, { A: this.V1 }, {}); gl.bindTexture(gl.TEXTURE_2D, this.V1m.t); gl.generateMipmap(gl.TEXTURE_2D); }
      pass(gl, this.p.wool, this.bg2, { SKYT: this.sky, LV: this.V1m }, { R, pan: s.pan, zoom: s.tableZoom, time: s.time, focusBlur: s.focusBlur, tilt: s.tilt, mixK: s.woolMix,
        sparkle: s.sparkle, woolCol: s.woolCol, woolCol2: s.woolCol2, keyCol: s.keyCol, spot: s.spot || [0, 0, 9], shadowK: s.shadowK || 0, livePos: s.livePos || [0, 0], liveRot: s.liveRot || 0, NV: this.N, liveK: s.liveK || 1 });
      bg = this.bg2;
      if (s.letters > 0) {
        pass(gl, this.p.gallery, this.sky, { BG: this.bg2, LT: { arr: this.LT }, HAB: this.HAB }, { R, pan: s.pan, zoom: s.tableZoom, count: s.letters, time: s.time, hoverId: s.hoverId, NL: this.NL, alpha: s.woolMix * (s.galleryAlpha ?? 1),
          slots: s.slots, lampA: s.lampA, lampB: s.lampB, lampC: s.lampC, dirA: s.dirA, dirB: s.dirB, dirC: s.dirC, iceCol: s.iceCol, keyCol: s.keyCol,
          edgeGain: s.edgeGain, bevel: s.bevel, slope: s.slope, terrace: s.terrace ?? 1.5, ringK: s.ringK ?? 3 });
        bg = this.sky;
      }
    }
    // 3. crystal
    pass(gl, this.p.flake, this.scene, { V: this.V1, V0: this.V0, VT: this.VT, SIM: sim.tex, SKYT: bg, HAB: this.HAB }, {
      R, N, zoom: s.zoom, time: s.time, glowAmt: s.glow, beta: s.beta, vapour: s.vapour,
      keyCol: s.keyCol, rimCol: s.rimCol, iceCol: s.iceCol, glowCol: s.glowCol, rot: s.rot, replay: s.replay ?? 2, ofs: s.ofs || [0, 0],
      lampA: s.lampA, lampB: s.lampB, lampC: s.lampC, dirA: s.dirA, dirB: s.dirB, dirC: s.dirC, slope: s.slope, bevel: s.bevel, dbg: s.dbg || 0, edgeGain: s.edgeGain, thick: s.thick, ringK: s.ringK ?? 3, terrace: s.terrace ?? 1.5, simBox: sim.box, rho0: s.rho0 || 0.6, sweepPos: s.sweepPos || 0, sweepAmt: s.sweepAmt || 0 });
    // 4. bloom
    const m = this.mips;
    pass(gl, this.p.bright, m[0][0], { A: this.scene }, { thr: s.bloomThr });
    for (let i = 1; i < m.length; i++) pass(gl, this.p.down, m[i][0], { A: m[i - 1][0] }, { texel: [1 / m[i - 1][0].w, 1 / m[i - 1][0].h] });
    for (let i = m.length - 1; i > 0; i--) {
      const src = i === m.length - 1 ? m[i][0] : m[i][1];
      pass(gl, this.p.up, m[i - 1][1], { A: src, B: m[i - 1][0] }, { texel: [1 / src.w, 1 / src.h], k: 1 });
    }
    // 5. finish
    pass(gl, this.p.final, null, { A: s.dbg === 1 ? this.sky : s.dbg === 2 ? this.V1 : this.scene, BL: m[0][1] }, { R, time: s.time, bloom: s.bloom, expo: s.expo, fade: s.fade, breath: s.breath || [0, 0, 0] });
  }
  // copy the current crystal into letters layer i
  pack(i, beta) {
    const gl = this.gl;
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.packFB);
    gl.framebufferTextureLayer(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, this.LT, 0, i);
    pass(gl, this.p.pack, { f: this.packFB, w: this.NL, h: this.NL }, { V: this.V1, VT: this.VT }, { N: this.N, NL: this.NL, beta });
    gl.bindTexture(gl.TEXTURE_2D_ARRAY, this.LT); gl.generateMipmap(gl.TEXTURE_2D_ARRAY);
  }
  habitMap(data, w, h) {
    const gl = this.gl; this.HAB = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, this.HAB);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, data);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  }
  timeline(data, rows) { // data: Float32Array(4096*4*4)
    const gl = this.gl; gl.bindTexture(gl.TEXTURE_2D, this.TL);
    gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, 4096, rows, gl.RGBA, gl.FLOAT, data.subarray(0, 4096 * 4 * rows));
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
