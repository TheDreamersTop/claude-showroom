// Soap-film optics and rim physics. Pure functions, no DOM: runs in the browser and in node tests.
//
// Colour: light reflects off the front and back of the film. The two reflections interfere,
// and which wavelengths survive depends on the film's thickness (Airy formula for a single
// layer). We integrate the reflected spectrum against the CIE 1931 colour-matching functions
// and convert to linear sRGB, white-balanced so a perfect mirror reads (1, 1, 1).

const N_FILM = 1.33; // soapy water

// CIE 1931 2-degree observer, multi-lobe Gaussian fit (Wyman, Sloan & Shirley 2013).
function g(x, mu, s1, s2) {
  const t = (x - mu) / (x < mu ? s1 : s2);
  return Math.exp(-0.5 * t * t);
}
function cmf(l) {
  return [
    1.056 * g(l, 599.8, 37.9, 31.0) + 0.362 * g(l, 442.0, 16.0, 26.7) - 0.065 * g(l, 501.1, 20.4, 26.2),
    0.821 * g(l, 568.8, 46.9, 40.5) + 0.286 * g(l, 530.9, 16.3, 31.1),
    1.217 * g(l, 437.0, 11.8, 36.0) + 0.681 * g(l, 459.0, 26.0, 13.8),
  ];
}
function xyzToLinearSRGB([x, y, z]) {
  return [
    3.2406 * x - 1.5372 * y - 0.4986 * z,
    -0.9689 * x + 1.8758 * y + 0.0415 * z,
    0.0557 * x - 0.204 * y + 1.057 * z,
  ];
}

const LAMBDAS = [];
for (let l = 380; l <= 780; l += 2) LAMBDAS.push(l);
const CMF = LAMBDAS.map(cmf);
const WHITE = (() => {
  const xyz = [0, 0, 0];
  for (const c of CMF) for (let k = 0; k < 3; k++) xyz[k] += c[k];
  return xyzToLinearSRGB(xyz);
})();

// Reflectance of a single film for one polarisation, from its interface amplitude r.
function airy(r, delta) {
  const r2 = r * r, cd = Math.cos(delta);
  return (2 * r2 * (1 - cd)) / (1 - 2 * r2 * cd + r2 * r2);
}

// Reflected colour of a film hNm nanometres thick, viewed at cos(angle) cosI to its normal.
export function filmRGB(hNm, cosI) {
  const sinI = Math.sqrt(Math.max(0, 1 - cosI * cosI));
  const cosT = Math.sqrt(1 - (sinI / N_FILM) ** 2);
  const rs = (cosI - N_FILM * cosT) / (cosI + N_FILM * cosT);
  const rp = (N_FILM * cosI - cosT) / (N_FILM * cosI + cosT);
  const xyz = [0, 0, 0];
  for (let i = 0; i < LAMBDAS.length; i++) {
    const delta = (4 * Math.PI * N_FILM * hNm * cosT) / LAMBDAS[i];
    const R = 0.5 * (airy(rs, delta) + airy(rp, delta));
    for (let k = 0; k < 3; k++) xyz[k] += R * CMF[i][k];
  }
  const rgb = xyzToLinearSRGB(xyz);
  return rgb.map((v, k) => Math.max(0, v / WHITE[k]));
}

// Lookup table for the GPU: rows are view angle (cos from 0 to 1), columns thickness 0..hMax nm.
export function buildLUT(nH, nCos, hMax) {
  const out = new Float32Array(nH * nCos * 4);
  for (let j = 0; j < nCos; j++) {
    const cosI = Math.max(0.02, j / (nCos - 1));
    for (let i = 0; i < nH; i++) {
      const c = filmRGB((i / (nH - 1)) * hMax, cosI);
      out.set([c[0], c[1], c[2], 1], (j * nH + i) * 4);
    }
  }
  return out;
}

// Taylor-Culick speed (m/s) at which the rim of a hole runs through a film hNm thick:
// v = sqrt(2 * surface tension / (density * thickness)).
const SURFACE_TENSION = 0.025; // N/m, soapy water
const DENSITY = 1000; // kg/m^3
export function rimSpeed(hNm) {
  return Math.sqrt((2 * SURFACE_TENSION) / (DENSITY * hNm * 1e-9));
}
