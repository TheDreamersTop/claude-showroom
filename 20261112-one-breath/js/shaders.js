// GLSL for the film simulation and the renderer.
//
// The bubble's surface is stored as two disks side by side in one texture: the front
// hemisphere on the left, the back hemisphere on the right. A texel's disk position (x, y)
// is the sphere point seen straight on, so z = +-sqrt(1 - x^2 - y^2).

export const VS = `#version 300 es
in vec2 aPos; out vec2 vUv;
void main(){ vUv = aPos*0.5+0.5; gl_Position = vec4(aPos,0.,1.); }`;

const HEAD = `#version 300 es
precision highp float; precision highp sampler2D;
in vec2 vUv; out vec4 o;
uniform float uN;   // disk size in texels
uniform float uDt;
float hemiOf(vec2 uv){ return step(0.5, uv.x); }
vec2 xyOf(vec2 uv){ return vec2(fract(uv.x*2.)*2.-1., uv.y*2.-1.); }
vec2 uvOf(vec2 xy, float hemi){ return vec2((hemi + xy.x*.5+.5)*.5, xy.y*.5+.5); }
vec2 clampDisk(vec2 xy){ float r = length(xy); return r > .985 ? xy*(.985/r) : xy; }
vec2 xyOfTexel(ivec2 c){ return vec2((float(c.x % int(uN)) + .5)/uN*2.-1., (float(c.y)+.5)/uN*2.-1.); }
bool inDisk(ivec2 c){ return c.y >= 0 && c.y < int(uN) && c.x >= 0 && c.x < 2*int(uN) && length(xyOfTexel(c)) < .985; }
`;

// Surface flow forces: buoyancy of thin film, a slow churning breeze, vorticity confinement
// (keeps the swirls crisp), and the finger.
export const FS_FORCE = HEAD + `
uniform sampler2D U, H, C;
uniform float uTime, uBuoy, uNoise, uVort, uDamp;
uniform vec4 uSplat;      // xy = disk pos, z = radius^2, w = hemisphere
uniform vec2 uSplatV;
vec2 churn(vec2 p, float t){
  vec2 u = vec2(0.);
  // stream function made of drifting waves; velocity is its curl
  const int K = 6;
  vec3 W[K] = vec3[K](vec3(2.1,1.3,.21), vec3(-1.7,2.6,.17), vec3(3.3,-.9,.27), vec3(-2.8,-3.1,.13), vec3(4.6,2.2,.33), vec3(.7,-4.9,.23));
  for(int i=0;i<K;i++){
    vec2 k = W[i].xy; float a = 1./length(k);
    float c = cos(dot(k,p) + W[i].z*t*6.2831 + float(i)*1.7);
    u += a*c*vec2(k.y, -k.x);
  }
  return u;
}
void main(){
  vec2 xy = xyOf(vUv); float hemi = hemiOf(vUv);
  if(length(xy) > .985){ o = vec4(0.); return; }
  ivec2 c = ivec2(gl_FragCoord.xy);
  vec2 u = texelFetch(U, c, 0).xy;
  float h = texelFetch(H, c, 0).x;
  float hl = textureLod(H, vUv, 3.5).x;
  vec2 up = vec2(-xy.x*xy.y, 1.-xy.y*xy.y);          // "up" along the sphere, seen in the disk
  vec2 f = uBuoy*clamp((hl-h)/max(hl,30.), -1., 1.)*up;
  f += uNoise*churn(xy*1.6 + hemi*3.1, uTime);
  float cL = abs(texelFetch(C,c-ivec2(1,0),0).x), cR = abs(texelFetch(C,c+ivec2(1,0),0).x);
  float cB = abs(texelFetch(C,c-ivec2(0,1),0).x), cT = abs(texelFetch(C,c+ivec2(0,1),0).x);
  vec2 g = vec2(cR-cL, cT-cB); g /= length(g)+1e-5;
  float w = texelFetch(C,c,0).x;
  f += uVort*vec2(g.y, -g.x)*w;
  u += uDt*f;
  if(hemi == uSplat.w){ vec2 d = xy-uSplat.xy; u += uSplatV*exp(-dot(d,d)/uSplat.z); }
  u *= exp(-uDt*uDamp);
  o = vec4(u, 0., 1.);
}`;

export const FS_CURL = HEAD + `
uniform sampler2D U;
void main(){
  ivec2 c = ivec2(gl_FragCoord.xy); float dx = 2./uN;
  float L = texelFetch(U,c-ivec2(1,0),0).y, R = texelFetch(U,c+ivec2(1,0),0).y;
  float B = texelFetch(U,c-ivec2(0,1),0).x, T = texelFetch(U,c+ivec2(0,1),0).x;
  o = vec4((R-L-(T-B))/(2.*dx), 0., 0., 1.);
}`;

export const FS_ADVECT = HEAD + `
uniform sampler2D U, S;
void main(){
  vec2 xy = xyOf(vUv); float hemi = hemiOf(vUv);
  if(length(xy) > .985){ o = texture(S, vUv); return; }
  vec2 src = clampDisk(xy - uDt*texture(U, vUv).xy);
  o = texture(S, uvOf(src, hemi));
}`;

export const FS_DIV = HEAD + `
uniform sampler2D U;
vec2 vel(ivec2 c){ return inDisk(c) ? texelFetch(U,c,0).xy : vec2(0.); }
void main(){
  ivec2 c = ivec2(gl_FragCoord.xy); float dx = 2./uN;
  float d = (vel(c+ivec2(1,0)).x - vel(c-ivec2(1,0)).x + vel(c+ivec2(0,1)).y - vel(c-ivec2(0,1)).y)/(2.*dx);
  o = vec4(d,0.,0.,1.);
}`;

export const FS_JACOBI = HEAD + `
uniform sampler2D P, D;
void main(){
  ivec2 c = ivec2(gl_FragCoord.xy); float dx = 2./uN;
  float p0 = texelFetch(P,c,0).x;
  ivec2 n[4] = ivec2[4](c+ivec2(1,0), c-ivec2(1,0), c+ivec2(0,1), c-ivec2(0,1));
  float s = 0.;
  for(int i=0;i<4;i++) s += inDisk(n[i]) ? texelFetch(P,n[i],0).x : p0;
  o = vec4((s - dx*dx*texelFetch(D,c,0).x)*.25, 0., 0., 1.);
}`;

export const FS_GRAD = HEAD + `
uniform sampler2D P, U;
void main(){
  ivec2 c = ivec2(gl_FragCoord.xy); float dx = 2./uN;
  if(!inDisk(c)){ o = vec4(0.); return; }
  float p0 = texelFetch(P,c,0).x;
  float pR = inDisk(c+ivec2(1,0)) ? texelFetch(P,c+ivec2(1,0),0).x : p0;
  float pL = inDisk(c-ivec2(1,0)) ? texelFetch(P,c-ivec2(1,0),0).x : p0;
  float pT = inDisk(c+ivec2(0,1)) ? texelFetch(P,c+ivec2(0,1),0).x : p0;
  float pB = inDisk(c-ivec2(0,1)) ? texelFetch(P,c-ivec2(0,1),0).x : p0;
  o = vec4(texelFetch(U,c,0).xy - vec2(pR-pL, pT-pB)/(2.*dx), 0., 1.);
}`;

// Thickness: carried by the flow, drained by gravity, thinned by evaporation.
// Gravity pulls the film down the sphere; seen in the disk that flow is (x*y, y*y-1),
// whose divergence is 3y: film thins on top and piles up at the bottom. Drainage of a
// thin sheet goes as h^2.
export const FS_THICK = HEAD + `
uniform sampler2D U, H;
uniform float uDrain, uEvap, uStir, uVol;
uniform vec4 uSplat;
uniform vec4 uPlume[4];   // xy = disk pos, z = hemisphere, w = strength
float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7)))*43758.5453); }
float vnoise(vec2 p){
  vec2 i = floor(p), f = fract(p); f = f*f*(3.-2.*f);
  return mix(mix(hash(i), hash(i+vec2(1,0)), f.x), mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), f.x), f.y);
}

void main(){
  vec2 xy = xyOf(vUv); float hemi = hemiOf(vUv);
  float r = length(xy);
  // outside the disk: copy the film just inside, so edge sampling never mixes in stale film
  if(r > .985){ o = textureLod(H, uvOf(xy*(.97/r), hemi), 0.); return; }
  vec2 src = clampDisk(xy - uDt*texture(U, vUv).xy);
  float h = textureLod(H, uvOf(src, hemi), 0.).x;
  float hk = h*1e-3;
  float hd = min(hk, 1.2);                               // drainage speed stops growing past the full-size range
  if(xy.y > 0.) h *= exp(-uDt*uDrain*hd*hd*3.*xy.y);   // top drains
  else h += uDt*uDrain*60.*(-xy.y)*smoothstep(4000.,2500.,h); // bottom collects, up to a limit
  // black film nucleates in patches: where the film may snap varies from place to place (25 to 70 nm)
  float thr = 25. + 45.*vnoise(xy*7. + hemi*13.);
  float black = 1. - smoothstep(thr - 6., thr + 6., h);
  h -= (1.-black)*uDt*uEvap*(.5 + 2.4*smoothstep(.25, .85, xy.y));   // the top cap loses most: drained and drying
  // marginal regeneration: near the bottom, thinner film is pulled out of the thick rim
  // region and rises as plumes (buoyancy in the force pass does the lifting)
  for(int i=0;i<4;i++){
    if(uPlume[i].z != hemi) continue;
    vec2 d = xy - uPlume[i].xy;
    h = mix(h, h*.55, uDt*uPlume[i].w*exp(-dot(d,d)/.006));
  }
  // below ~100 nm van der Waals attraction between the two faces pulls the film thinner, faster
  // until the film snaps to a stable common black film about 12 nm thick
  h -= (1.-black)*uDt*uEvap*.5*pow(80./max(h, 12.), 2.);
  h += black*(12. - h)*min(1., uDt*1.5);
  h *= mix(uVol, 1., black);                      // global soap correction (see README), not applied to black film
  if(hemi == uSplat.w){ vec2 d = xy-uSplat.xy; h *= 1. - uStir*exp(-dot(d,d)/uSplat.z); }
  o = vec4(clamp(h, 0., 4000.), 0., 0., 1.);
}`;

// Hole opening: arrival time (ms) of the rim at each point, by repeated relaxation.
// The rim runs at the Taylor-Culick speed sqrt(2 sigma / (rho h)), so it races through thin film
// and crawls through thick film.
export const FS_RIM = HEAD + `
uniform sampler2D T, H;
uniform float uRphys;     // bubble radius in metres
vec3 sph(vec2 xy, float hemi){ return vec3(xy, (hemi < .5 ? 1. : -1.)*sqrt(max(0., 1.-dot(xy,xy)))); }
void main(){
  ivec2 c = ivec2(gl_FragCoord.xy);
  if(!inDisk(c)){                                   // ring outside the disk follows the film just inside it
    vec2 xy = xyOfTexel(c); float r = length(xy);
    float hm = float(c.x >= int(uN));
    o = (r > .5 && r < 1.2) ? textureLod(T, vec2((hm + xy.x*(.97/r)*.5+.5)*.5, xy.y*(.97/r)*.5+.5), 0.) : vec4(6e4);
    return;
  }
  float hemi = float(c.x >= int(uN));
  vec3 p = sph(xyOfTexel(c), hemi);
  float t = texelFetch(T,c,0).x;
  float h = max(texelFetch(H,c,0).x, 4.);
  float v = sqrt(2.*.025/(1000.*h*1e-9));
  // small texel-to-texel variation in the film makes the front ragged, as real rims are
  float k = 1000.*uRphys/v*(.8 + .4*fract(sin(dot(vec2(c), vec2(12.9898,78.233)))*43758.5));
  const ivec2 NB[16] = ivec2[16](ivec2(1,0),ivec2(-1,0),ivec2(0,1),ivec2(0,-1),ivec2(1,1),ivec2(1,-1),ivec2(-1,1),ivec2(-1,-1),
    ivec2(2,1),ivec2(2,-1),ivec2(-2,1),ivec2(-2,-1),ivec2(1,2),ivec2(1,-2),ivec2(-1,2),ivec2(-1,-2));
  for(int q=0;q<16;q++){                      // 16 neighbours: less grid bias in the hole's shape
    ivec2 n = c+NB[q];
    if(!inDisk(n) || (n.x >= int(uN)) != (hemi > .5)) continue;
    t = min(t, texelFetch(T,n,0).x + k*length(p - sph(xyOfTexel(n), hemi)));
  }
  vec2 xy = xyOfTexel(c);
  if(length(xy) > .985 - 3./uN){                         // the two hemispheres meet at the rim
    ivec2 n = c + ivec2(hemi > .5 ? -int(uN) : int(uN), 0);
    t = min(t, texelFetch(T,n,0).x + k*length(p - sph(xy, 1.-hemi)));
  }
  o = vec4(t, 0., 0., 1.);
}`;

// Coarse stats for the CPU: thinnest film in each block, mean thickness, and rim arrival time.
export const FS_DOWN = HEAD + `
uniform sampler2D H, T;
uniform float uM;          // output disk size
void main(){
  ivec2 o2 = ivec2(gl_FragCoord.xy);
  int b = int(uN/uM);
  float mn = 1e5, sum = 0., cnt = 0.;
  for(int j=0;j<b;j++) for(int i=0;i<b;i++){
    ivec2 c = o2*b + ivec2(i,j);
    if(!inDisk(c)) continue;
    float h = texelFetch(H,c,0).x; mn = min(mn,h); sum += h; cnt += 1.;
  }
  float tl = 0.;                            // latest rim arrival in the block: torn once uTpop passes it
  for(int j=0;j<b;j++) for(int i=0;i<b;i++){ ivec2 c = o2*b + ivec2(i,j); if(inDisk(c)) tl = max(tl, texelFetch(T,c,0).x); }
  o = vec4(mn, cnt > 0. ? sum/cnt : 0., tl, cnt/float(b*b));
}`;

export const FS_RENDER = `#version 300 es
precision highp float; precision highp sampler2D;
in vec2 vUv; out vec4 o;
uniform sampler2D H, T, LUT;
uniform vec2 uRes; uniform vec3 uC, uCam; uniform float uR, uCamZ, uTan, uScale, uTpop, uPopping, uTime, uLutN, uHmax, uFade;
uniform float uLutC, uTend;

// The room the bubble reflects: a tall daylight window with mullions, a warm lamp, a dark floor.
vec3 env(vec3 d){
  // a big soft light behind the camera, the way bubbles are photographed against black
  vec3 col = vec3(.004,.004,.006);
  float front = smoothstep(-.55, .65, d.z);
  col += front*mix(vec3(.55,.57,.62), vec3(1.15,1.10,1.02), smoothstep(-.6,.7,d.y))*(.75+.25*sin(d.x*3.1+1.3));
  col = mix(col, vec3(.018,.012,.009), smoothstep(-.1,-.45,d.y));            // floor
  // window, up and to the left, facing the bubble
  vec3 wc = normalize(vec3(-.55,.42,.72));
  vec3 wx = normalize(cross(vec3(0,1,0), wc)), wy = cross(wc, wx);
  float pu = dot(d,wx)/max(dot(d,wc),1e-3), pv = dot(d,wy)/max(dot(d,wc),1e-3);
  if(dot(d,wc) > 0.){
    float win = smoothstep(.36,.33,abs(pu))*smoothstep(.52,.49,abs(pv));
    float bars = smoothstep(.012,.02,abs(pu))*smoothstep(.012,.02,abs(pv-.12))*smoothstep(.012,.02,abs(pv+.2));
    vec3 sky = mix(vec3(5.2,5.6,6.4), vec3(7.5,7.1,6.4), smoothstep(-.5,.5,pv));
    col += win*bars*sky;
  }
  // warm lamp, right
  vec3 lc = normalize(vec3(.75,.12,.55));
  float l = dot(d,lc);
  col += vec3(4.,2.4,1.1)*smoothstep(.9975,.9990,l) + vec3(.16,.08,.03)*pow(max(l,0.),40.);
  return col;
}

// What the camera sees behind the bubble: soft out-of-focus room, a few dim bokeh discs.
vec3 backdrop(vec2 p){
  vec3 col = mix(vec3(.003,.003,.005), vec3(.010,.010,.013), smoothstep(-1.,1.2,p.y));
  for(int i=0;i<7;i++){
    float fi = float(i);
    vec2 c = vec2(fract(sin(fi*12.9)*437.5)*3.4-1.7, fract(sin(fi*78.2)*913.1)*2.-1.);
    float r = .08+.1*fract(sin(fi*3.3)*55.);
    float d = length(p - c);
    col += mix(vec3(.016,.011,.006), vec3(.006,.009,.016), fract(fi*.37))*smoothstep(r, r*.6, d);
  }
  return col;
}

vec3 film(float h, float cosI){
  float u = (clamp(h/uHmax,0.,1.)*(uLutN-1.)+.5)/uLutN;
  float v = (clamp(cosI,0.,1.)*(uLutC-1.)+.5)/uLutC;
  return texture(LUT, vec2(u,v)).rgb;
}
vec2 uvOf(vec2 xy, float hemi){ return vec2((hemi + xy.x*.5+.5)*.5, xy.y*.5+.5); }

// One wall of the bubble: light reflected by the film over light passing through.
vec3 layer(vec3 under, vec3 p, vec3 n, vec3 rd, float hemi){
  float pr = length(p.xy);
  vec2 uv = uvOf(p.xy*min(1., .975/max(pr, 1e-4)), hemi);
  float t = texture(T, uv).x;
  if(pr > .9) t = min(t, texture(T, uvOf(p.xy*min(1., .975/max(pr, 1e-4)), 1.-hemi)).x);   // near and far wall tear together at the edge
  if(uPopping > .5 && t < uTpop) return under;                               // already torn open
  float h = texture(H, uv).x*uScale;
  vec3 F = film(h, abs(dot(n, rd)));
  vec3 r = reflect(rd, n);
  float cover = uPopping > .5 ? smoothstep(.04, .2, abs(dot(n, rd)))*(1. - smoothstep(.75*uTend, uTend, uTpop)) : 1.;   // while tearing, edge-on film and the last scraps fade out
  F *= cover;
  vec3 col = under*(1.-F) + F*env(r);
  if(uPopping > .5){                                                         // liquid gathered in the rim
    float rim = smoothstep(.12, 0., t - uTpop);
    col += cover*rim*(.12 + .9*env(r))*.6;
  }
  return col;
}

void main(){
  vec2 p = (gl_FragCoord.xy - .5*uRes)/uRes.y*2.;
  // the camera looks slightly down on the bubble, so the drained top faces us
  vec3 ro = uCam;
  vec3 f = normalize(-ro), rt = normalize(cross(f, vec3(0,1,0))), up = cross(rt, f);
  vec3 rd = normalize(f + uTan*(p.x*rt + p.y*up));
  vec3 col = backdrop(p*1.1 + vec2(0., .1));
  vec3 oc = ro - uC;
  float b = dot(oc, rd), c = dot(oc,oc) - uR*uR, disc = b*b - c;
  if(disc > 0. && uFade > 0.){
    float s = sqrt(disc);
    float t0 = -b - s, t1 = -b + s;
    vec3 p1 = (ro + rd*t1 - uC)/uR, p0 = (ro + rd*t0 - uC)/uR;
    vec3 inside = layer(col, p1, -p1, rd, step(p1.z, 0.));   // far wall, seen from inside
    inside = layer(inside, p0, p0, rd, step(p0.z, 0.));       // near wall
    col = mix(col, inside, uFade);
  }
  col *= 1.0 - .35*dot(p*.5,p*.5);                // vignette
  col *= 1.6;                                     // filmic curve with a real black (Narkowicz ACES fit)
  col = clamp((col*(2.51*col+.03))/(col*(2.43*col+.59)+.14), 0., 1.);
  col = pow(col, vec3(1./2.2));
  col += (fract(sin(dot(gl_FragCoord.xy + uTime, vec2(12.9898,78.233)))*43758.5) - .5)/255.;
  o = vec4(col, 1.);
}`;

// Droplets thrown off the rim: tiny bright beads.
export const VS_DROP = `#version 300 es
in vec3 aP; in float aA;
uniform vec2 uRes; uniform vec3 uCam; uniform float uTan;
out float vA;
void main(){
  vec3 f = normalize(-uCam), rt = normalize(cross(f, vec3(0,1,0))), up = cross(rt, f);
  vec3 q = aP - uCam;
  float z = dot(q, f);
  vec2 s = vec2(dot(q, rt), dot(q, up))/(z*uTan);
  gl_Position = vec4(s.x*uRes.y/uRes.x, s.y, 0., 1.);
  gl_PointSize = max(1.5, 5.*uRes.y/1000./(z*.25));
  vA = aA;
}`;
export const FS_DROP = `#version 300 es
precision highp float;
in float vA; out vec4 o;
uniform float uLine;
void main(){
  if(uLine > .5){ o = vec4(vec3(.85,.9,1.)*vA*vA*1.4, 1.); return; }
  vec2 d = gl_PointCoord*2.-1.;
  float r = dot(d,d);
  if(r > 1.) discard;
  float glint = exp(-r*3.) + .8*exp(-dot(d-vec2(-.35,.35), d-vec2(-.35,.35))*30.);
  o = vec4(vec3(.85,.9,1.)*glint*vA, 1.);
}`;
