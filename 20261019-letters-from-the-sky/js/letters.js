// Turning a crystal's journey into words, and into a link that regrows the same crystal.
import { habitName, tempC } from './weather.js';
const deg = t => tempC(t).toFixed(1).replace('-', '−');

const NAMES = {
  plate: ['六角板', 'hexagonal plate'],
  sector: ['扇形板', 'sectored plate'],
  stellar: ['星狀板', 'stellar plate'],
  fern: ['羊齒狀枝晶', 'fern dendrite'],
  needle: ['細密枝晶', 'fernlike stellar dendrite'],
  open: ['星狀樹枝', 'stellar dendrite'],
};
const MOOD = {
  plate: ['乾冷的空氣讓它長成一塊安靜的六角板。', 'Dry, cold air kept it a quiet hexagonal plate.'],
  sector: ['寒冷把它的六條手臂壓成了寬寬的扇。', 'The cold pressed its six arms into broad sectors.'],
  stellar: ['它在雲裡伸出六道星芒。', 'It reached out six stellar arms inside the cloud.'],
  fern: ['在飽和的雲中，它長出了羽毛般的枝。', 'In a saturated cloud it grew feathers.'],
  needle: ['過飽和的水氣讓它長出細密的枝葉。', 'Supersaturated vapour gave it dense, fine branches.'],
  open: ['接近冰點的濕氣讓它長出纖細的樹枝。', 'Damp air near freezing grew it slender branches.'],
};

// trail: [[t, h, step], ...]  ->  segments of constant habit
export function segments(trail) {
  if (!trail.length) return [];
  const segs = [];
  for (const [t, h, T] of trail) {
    const hb = habitName(t, h);
    const last = segs[segs.length - 1];
    if (last && last.habit === hb) { last.n++; last.t += t; last.h += h; last.T1 = T; }
    else segs.push({ habit: hb, n: 1, t, h, T0: T, T1: T });
  }
  // merge segments that are too short to have left a mark
  const total = trail.length, out = [];
  for (const s of segs) {
    if (s.n < total * 0.08 && out.length) { const l = out[out.length - 1]; l.n += s.n; l.t += s.t; l.h += s.h; l.T1 = s.T1; }
    else out.push(s);
  }
  for (const s of out) { s.t /= s.n; s.h /= s.n; }
  // merge neighbours that ended up with the same habit
  const m = [];
  for (const s of out) { const l = m[m.length - 1]; if (l && l.habit === s.habit) { l.t = (l.t * l.n + s.t * s.n) / (l.n + s.n); l.h = (l.h * l.n + s.h * s.n) / (l.n + s.n); l.n += s.n; l.T1 = s.T1; } else m.push(s); }
  return m;
}

// air, in words
const tempZh = t => t < 0.2 ? '接近冰點' : t < 0.45 ? '微寒' : t < 0.72 ? '零下十五度上下' : '酷寒';
const tempEn = t => t < 0.2 ? 'near freezing' : t < 0.45 ? 'gently cold' : t < 0.72 ? 'around −15 °C' : 'bitterly cold';
const humZh = h => h < 0.3 ? '乾燥' : h < 0.65 ? '濕潤' : '飽和';
const humEn = h => h < 0.3 ? 'dry' : h < 0.65 ? 'damp' : 'saturated';
const airEn = (t, h) => t < 0.2 ? `near-freezing ${humEn(h)} air` : t < 0.45 ? `cool, ${humEn(h)} air` : t < 0.72 ? `${humEn(h)} air at about −15 °C` : `bitterly cold, ${humEn(h)} air`;
// what each habit does, as a verb phrase
const GREW = {
  plate: ['收斂成一片平整的六角板', 'closed into a flat hexagonal plate'],
  sector: ['把六條手臂壓成寬寬的扇', 'pressed its arms into broad sectors'],
  stellar: ['伸出六道星芒', 'reached out six stellar arms'],
  fern: ['長出羽毛般的枝', 'grew feathers'],
  needle: ['長出細密的枝葉', 'grew dense, fine branches'],
  open: ['長出纖細的樹枝', 'grew slender branches'],
};
const BORN = {
  plate: ['一片小小的六角板', 'a small hexagonal plate'], sector: ['一顆寬臂的小星', 'a small broad-armed star'],
  stellar: ['一顆小小的星', 'a small star'], fern: ['一株細小的羽枝', 'a tiny feathered star'],
  needle: ['一叢細枝', 'a tuft of fine branches'], open: ['一顆纖細的小星', 'a slender little star'],
};
const used = new Set();
// what the finished crystal looks like, for its specimen label: a dendrite that ended in dry air is plate-tipped
const DENDRITIC = new Set(['fern', 'needle', 'open', 'stellar']);
function shapeOf(segs) {
  if (!segs.length) return 'plate';
  const dend = segs.filter(s => DENDRITIC.has(s.habit)), last = segs[segs.length - 1].habit;
  if (dend.length && (last === 'plate' || last === 'sector') && segs.length > 1) return 'tipped';
  const pool = dend.length ? dend : segs; let best = pool[0]; for (const s of pool) if (s.n > best.n) best = s;
  return best.habit;
}

export function describe(letter) {
  const segs = segments(letter.trail);
  const lines = segs.slice(0, 4).map((s, i) => ({
    zh: `${i === 0 ? '誕生於' : '飄進'} ${deg(s.t)} °C、濕度 ${(s.h * 100) | 0}% 的空氣 — ${NAMES[s.habit][0]}`,
    en: `${i === 0 ? 'born in' : 'then'} ${deg(s.t)} °C air at ${(s.h * 100) | 0}% humidity — ${NAMES[s.habit][1]}`,
  }));
  if (letter.breathed) lines.push({ zh: '途中有人對它呵了一口氣，枝尖化回水氣', en: 'on the way, someone breathed on it and its tips turned back to vapour' });
  // the headline tells *this* crystal's path: where it was born, what it became, how it ended
  let zh, en;
  if (!segs.length) { zh = '它還來不及長大，就落了下來。'; en = 'It fell before it had time to grow.'; }
  else if (segs.length === 1) {
    const s0 = segs[0];
    zh = `它一路都在${tempZh(s0.t)}、${humZh(s0.h)}的空氣裡，${GREW[s0.habit][0]}。`;
    en = `It fell the whole way through ${airEn(s0.t, s0.h)} and ${GREW[s0.habit][1]}.`;
  } else {
    const s0 = segs[0], last = segs[segs.length - 1];
    zh = `它生於${tempZh(s0.t)}的${humZh(s0.h)}空氣，起初是${BORN[s0.habit][0]}；`;
    en = `Born in ${airEn(s0.t, s0.h)}, it began as ${BORN[s0.habit][1]}; `;
    // every middle stretch of the journey gets its own clause
    // temperature is only mentioned when it changes; humidity always (it is what the pointer's height means)
    let prevT = tempZh(s0.t);
    const zhAir = (m, noun) => { const t = tempZh(m.t), w = t === prevT ? `${humZh(m.h)}的${noun}` : `${t}、${humZh(m.h)}的${noun}`; prevT = t; return w; };
    let prevTe = tempEn(s0.t);
    const enAir = (m, noun) => { const t = tempEn(m.t), w = t === prevTe ? `${humEn(m.h)} ${noun}` : airEn(m.t, m.h).replace(/ air/, ' ' + noun); prevTe = t; return w; };
    segs.slice(1, -1).forEach((m, i) => {
      zh += `${i ? '又' : ''}飄進${zhAir(m, '雲')}，${GREW[m.habit][0]}，`;
      en += `${i ? 'then ' : ''}in ${enAir(m, 'cloud')} it ${GREW[m.habit][1]}, `;
    });
    zh += `${segs.length > 2 ? '最後在' : '然後在'}${zhAir(last, '空氣')}裡${GREW[last.habit][0]}。`;
    en += `${segs.length > 2 ? 'and at the end' : 'then'}, in ${enAir(last, 'air')}, it ${GREW[last.habit][1]}.`;
  }
  if (letter.breathed) { zh += '有人對它呵過氣。'; en += ' Someone breathed on it.'; }
  if (used.has(zh) && !letter.twinOf) { zh = zh.replace(/。$/, '——又一封，卻不是同一封。'); en = en.replace(/\.$/, ' — another letter, never the same one.'); }
  used.add(zh);
  return { lines, mood: [zh, en], habit: shapeOf(segs) };
}

// Compact journey code: one (t,h) byte pair per 250 simulation steps.
const STEP = 250;
export function encode(trail, totalSteps) {
  const bytes = [];
  let k = 0;
  for (let T = 0; T < totalSteps; T += STEP) {
    while (k < trail.length - 1 && trail[k + 1][2] <= T) k++;
    const p = trail[k] || [0.5, 0.5, 0];
    bytes.push(Math.round(p[0] * 255), Math.round(p[1] * 255));
  }
  let bin = ''; for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
export function decode(code) {
  try {
    const bin = atob(code.replace(/-/g, '+').replace(/_/g, '/'));
    const pts = [];
    for (let i = 0; i + 1 < bin.length; i += 2) pts.push([bin.charCodeAt(i) / 255, bin.charCodeAt(i + 1) / 255, (i / 2) * STEP]);
    return pts.length ? pts : null;
  } catch (e) { return null; }
}
export const JOURNEY_STEP = STEP;
