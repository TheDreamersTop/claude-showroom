// What the README promises about the breath: a long breath makes a big bubble with thinner film,
// a quick puff a smaller one with thicker film, and both live about 50 s. Usage: node tools/breath.mjs
import puppeteer from 'puppeteer-core';
const browser = await puppeteer.launch({ executablePath: process.env.CHROME || '/usr/bin/chromium', headless: true, protocolTimeout: 3600000, args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage(); page.setDefaultTimeout(3600000);
const errors = [];
page.on('pageerror', (e) => errors.push(String(e)));
await page.setViewport({ width: 640, height: 400 });
await page.goto(`http://localhost:${process.env.PORT || 8765}/?warm=0`);
await page.waitForFunction(() => window.__ob);
await page.evaluate(() => window.__ob.pause(true));
const st = () => page.evaluate(() => { const s = window.__ob.st; return { phase: s.phase, age: s.age, R: s.R, black: s.blackSeen, mean0: s.mean0 }; });
async function lifeOf(label, blow) {
  await page.evaluate(() => { window.__ob.pop(); window.__ob.skip(8); });   // end the current bubble
  await blow();
  await page.evaluate(() => window.__ob.skip(1));
  let s = await st(), blackAt = null;
  const R = s.R, mean0 = s.mean0;
  while (s.phase !== 'gone' && s.age < 150) {
    await page.evaluate(() => window.__ob.skip(2));
    s = await st();
    if (s.black && blackAt === null) blackAt = s.age;
  }
  const r = { label, R: +R.toFixed(2), mean0: Math.round(mean0), blackAt: blackAt && +blackAt.toFixed(1), diedAt: +s.age.toFixed(1), phase: s.phase };
  console.log(JSON.stringify(r));
  return r;
}
const big = await lifeOf('long breath', async () => {
  await page.keyboard.down('Space'); await page.evaluate(() => window.__ob.skip(6)); await page.keyboard.up('Space');
  await page.evaluate(() => window.__ob.skip(0.5));
});
const small = await lifeOf('quick puff', async () => {
  await page.mouse.move(320, 200); await page.mouse.down(); await page.mouse.up();
  await page.evaluate(() => window.__ob.skip(2));
});
if (!(big.R > 0.95)) errors.push('long breath should give a full-size bubble');
if (!(small.R < 0.75)) errors.push('quick puff should give a small bubble');
if (!(small.mean0 > 1.8 * big.mean0)) errors.push('quick puff should have much thicker film (1/R^2)');
for (const b of [big, small]) if (!(b.diedAt > 35 && b.diedAt < 70)) errors.push(`${b.label} should live about 50 s, lived ${b.diedAt}`);
await browser.close();
console.log(errors.length ? 'ERRORS:\n' + errors.join('\n') : 'breath promise holds');
process.exit(errors.length ? 1 : 0);
