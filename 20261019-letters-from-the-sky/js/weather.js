// Weather -> Gravner–Griffeath parameters.
// temp ∈ [0,1] maps −1 °C … −25 °C; hum ∈ [0,1] is vapour supersaturation.
// Anchor parameter sets were chosen by sweeping the model (tools/explore.html) and labelled by the
// form they actually grow. Weights follow the Nakaya diagram: compact plates when the air is dry,
// broad sectored plates near −2 °C and below −20 °C, stellar plates around −10 … −20 °C, and fern-like
// dendrites in the humid band around −15 °C.
export const ANCHORS = {
  plate:   { rho: 0.80, beta: 2.60, alpha: 0.006, theta: 0.005, kappa: 0.05,   mu: 0.015, gamma: 0.0001 },
  sector:  { rho: 0.50, beta: 1.40, alpha: 0.10,  theta: 0.005, kappa: 0.001,  mu: 0.07,  gamma: 0.0001 },
  stellar: { rho: 0.40, beta: 1.30, alpha: 0.08,  theta: 0.025, kappa: 0.003,  mu: 0.07,  gamma: 0.00005 },
  fern:    { rho: 0.635, beta: 1.60, alpha: 0.40, theta: 0.025, kappa: 0.0025, mu: 0.015, gamma: 0.0005 },
  needle:  { rho: 0.45, beta: 1.20, alpha: 0.15,  theta: 0.04,  kappa: 0.005,  mu: 0.05,  gamma: 0.0001 },
  open:    { rho: 0.38, beta: 1.06, alpha: 0.35,  theta: 0.112, kappa: 0.001,  mu: 0.14,  gamma: 0.0006 },
};
const KEYS = ['rho', 'beta', 'alpha', 'theta', 'kappa', 'mu', 'gamma'];
const LOG = new Set(['alpha', 'theta', 'kappa', 'gamma']);   // interpolate small rates in log space

export const tempC = t => -1 - 24 * t;
const bell = (x, c, w) => Math.exp(-(((x - c) / w) ** 2));
const sstep = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };

export function habit(t, h) {
  const T = tempC(t);
  const dendr = bell(T, -15, 3.5);             // dendritic window
  const wet = sstep(0.25, 0.75, h), dry = 1 - sstep(0.1, 0.45, h);
  const w = {
    plate: dry * 1.2 + bell(T, -5.5, 2) * 0.6 * (1 - wet) + 0.02,
    sector: (1 - dry) * (1 - dendr) * sstep(-17, -22, T) * 1.2,
    stellar: (1 - dry) * (bell(T, -10, 2.5) + dendr * (1 - wet)) * 1.3,
    open: (1 - dry) * sstep(-4.5, -2, T) * 1.4 + (1 - dry) * wet * bell(T, -6.5, 1.6) * 1.2,
    fern: wet * dendr * 1.8 * (1 - sstep(0.85, 1, h)),
    needle: wet * dendr * sstep(0.8, 1, h) * 2.2,
  };
  // sharpen so each region is mostly one habit (blends of very different sets grow mush)
  let s = 0; for (const k in w) { w[k] = w[k] ** 2.2; s += w[k]; }
  for (const k in w) w[k] /= s;
  return w;
}

export function params(t, h) {
  const w = habit(t, h), P = {};
  for (const key of KEYS) {
    let v = 0;
    for (const a in w) v += w[a] * (LOG.has(key) ? Math.log(ANCHORS[a][key]) : ANCHORS[a][key]);
    P[key] = LOG.has(key) ? Math.exp(v) : v;
  }
  P.sigma = 0.00002;
  P.supply = 0.0;
  return P;
}

export function habitName(t, h) {
  const w = habit(t, h); let best = 'plate', bv = -1;
  for (const k in w) if (w[k] > bv) { bv = w[k]; best = k; }
  return best;
}
