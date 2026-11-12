// Words shown after a bubble pops. Numbers come straight from the simulation.

const HAIR_NM = 70000; // a human hair is about 70 microns across

function twoSig(x) {
  const p = Math.pow(10, Math.floor(Math.log10(x)) - 1);
  return Math.round(x / p) * p;
}

export function hairFraction(hNm) {
  return '1/' + twoSig(HAIR_NM / hNm).toLocaleString('en-US');
}

export function epitaph({ ageS, thinnestNm, diameterCm }) {
  const s = Math.round(ageS);
  const size = diameterCm ? { zh: `${Math.round(diameterCm)} 公分寬，`, en: ` ${Math.round(diameterCm)} cm across.` } : { zh: '', en: '' };
  if (!Number.isFinite(thinnestNm)) return { zh: `${size.zh}活了 ${s} 秒。`, en: `Lived ${s} s.${size.en}` };
  const h = Math.round(thinnestNm);
  const frac = hairFraction(Math.max(1, thinnestNm));
  return {
    zh: `${size.zh}活了 ${s} 秒。最薄的地方 ${h} 奈米，是頭髮的 ${frac}。`,
    en: `Lived ${s} s.${size.en} Thinnest spot: ${h} nm, ${frac} of a hair.`,
  };
}
