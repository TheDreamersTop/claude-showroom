// Headless check: loads the page, drives the bubble through its life, saves screenshots,
// and fails on any console error. Usage: node tools/shot.mjs <outdir> [w h]
import puppeteer from 'puppeteer-core';
const [out = 'shots', w = 1280, h = 800] = process.argv.slice(2);
const browser = await puppeteer.launch({ executablePath: process.env.CHROME || '/usr/bin/chromium', headless: true, protocolTimeout: 3600000, args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage();
await page.setViewport({ width: +w, height: +h, deviceScaleFactor: 1 });
const errors = [];
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
page.setDefaultTimeout(600000);
page.on('pageerror', (e) => errors.push(String(e)));
await page.goto(`http://localhost:${process.env.PORT || 8765}/?shot&warm=0`);
await page.waitForFunction(() => window.__ob, { timeout: 120000 });
await page.evaluate(() => window.__ob.pause(true));
const snap = async (name) => { await new Promise((r) => setTimeout(r, 150)); await page.screenshot({ path: `${out}/${name}.jpg`, quality: 88 }); };
const info = () => page.evaluate(() => { const s = window.__ob.st; return { phase: s.phase, age: +s.age.toFixed(1), min: s.stats && +s.stats.min.toFixed(1), mean: s.stats && +s.stats.mean.toFixed(0), thinnest: +s.thinnest.toFixed?.(1), drops: window.__ob.drops.length }; });
const plan = (process.env.PLAN || '0,5,15,30,45,60').split(',').map(Number);
let t = 0;
for (const at of plan) {
  await page.evaluate((d) => window.__ob.skip(d), at - t); t = at;
  await snap(`life-${String(at).padStart(3, '0')}s`);
  console.log('t', at, JSON.stringify(await info()));
}
if (!process.env.NOPOP) {
  await page.evaluate(() => window.__ob.pop());
  for (const k of [0.15, 0.3, 0.3, 0.5, 1.0]) {
    await page.evaluate((d) => window.__ob.skip(d), k);
    t += k; await snap(`pop-${t.toFixed(2)}`);
    console.log('pop', JSON.stringify(await info()));
  }
  await page.evaluate(() => window.__ob.skip(8));
  await snap('after');
  console.log('after', JSON.stringify(await info()), await page.evaluate(() => document.getElementById('ep-en').textContent));
  // a quick real tap (pointer down, up) after the pop must still give a full, coloured bubble
  const ph = await info();
  if (ph.phase !== 'gone') errors.push('pop did not reach the gone phase: ' + ph.phase);
  await page.mouse.move(640, 400); await page.mouse.down(); await page.mouse.up();
  await page.evaluate(() => window.__ob.skip(1.2));
  await snap('blowing');
  await page.evaluate(() => window.__ob.skip(6));
  await snap('reborn');
  const rb = await info();
  console.log('reborn', JSON.stringify(rb));
  if (rb.phase !== 'alive' || !(rb.mean > 300) || !(rb.min > 100)) errors.push('quick tap did not give a healthy bubble: ' + JSON.stringify(rb));
  const R = await page.evaluate(() => window.__ob.st.R);
  if (!(R >= 0.65 && R < 0.75)) errors.push('a quick tap should give a small bubble, got R=' + R);
  if (process.env.SMALL_LIFE) {                      // the small, thick bubble must still die within 90 s
    let t = 0;
    while (t < 90 && (await info()).phase === 'alive') { await page.evaluate(() => window.__ob.skip(10)); t += 10; }
    const end = await info();
    console.log('small bubble after', t, 's:', JSON.stringify(end));
    if (end.phase === 'alive') errors.push('small bubble still alive after 90 s');
  }
}
console.log(errors.length ? 'ERRORS:\n' + errors.join('\n') : 'no console errors');
await browser.close();
process.exit(errors.length ? 1 : 0);
