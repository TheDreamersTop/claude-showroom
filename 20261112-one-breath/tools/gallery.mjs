// Renders the poster, the showroom thumbnail and a few state shots into shots/.
// Usage: node tools/gallery.mjs   (needs tools/serve.mjs running on 8765)
import puppeteer from 'puppeteer-core';
const browser = await puppeteer.launch({ executablePath: process.env.CHROME || '/usr/bin/chromium', headless: true, protocolTimeout: 3600000, args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const errors = [];
async function open(w, h, warm = 0) {
  const page = await browser.newPage(); page.setDefaultTimeout(1800000);
  page.on('pageerror', (e) => errors.push(String(e)));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  await page.setViewport({ width: w, height: h, deviceScaleFactor: 1 });
  await page.goto(`http://localhost:${process.env.PORT || 8765}/?shot&warm=${warm}`);
  await page.waitForFunction(() => window.__ob);
  await page.evaluate(() => window.__ob.pause(true));
  return page;
}
const shot = (page, path, clean = true) => page.evaluate((q) => { document.body.classList.toggle('clean', q); window.__ob.skip(0.05); }, clean)
  .then(() => new Promise((r) => setTimeout(r, 1500))).then(() => page.screenshot({ path, type: 'jpeg', quality: 90 }));
const at = Number(process.env.AT || 40);

const p1 = await open(1200, 630);
await p1.evaluate(() => { window.__ob.st.blackLife = 1e9; });   // stills only: hold the rupture so the frame shows black film
// poster and thumb: a freshly stirred film, the way a visitor sees it after a swirl of the finger
await p1.evaluate(() => window.__ob.skip(14));
await p1.mouse.move(600 + 140, 315); await p1.mouse.down();
for (let i = 0; i <= 60; i++) {
  const a = (i / 60) * Math.PI * 4;
  await p1.mouse.move(600 + 140 * Math.cos(a), 300 + 110 * Math.sin(a));
  await p1.evaluate(() => window.__ob.skip(1 / 30));
}
await p1.mouse.up(); await p1.mouse.move(5, 5);
await p1.evaluate(() => window.__ob.skip(1.8));
await shot(p1, 'poster.jpg');
await p1.setViewport({ width: 800, height: 450 });
await shot(p1, 'shots/thumb.jpg');
await p1.setViewport({ width: 1280, height: 800 });
// life: left alone until the black film shows at the top
await p1.evaluate((s) => window.__ob.skip(s), at - 16);
await shot(p1, 'shots/life.jpg', false);
await p1.evaluate(() => window.__ob.pop());
await p1.evaluate(() => window.__ob.skip(0.6));
await shot(p1, 'shots/pop.jpg', false);
await p1.evaluate(() => window.__ob.skip(6));
await shot(p1, 'shots/after.jpg', false);
await p1.close();

const p2 = await open(390, 844);
await p2.evaluate((s) => window.__ob.skip(s), 20);
await shot(p2, 'shots/phone.jpg', false);
await p2.close();

await browser.close();
console.log(errors.length ? 'ERRORS:\n' + errors.join('\n') : 'no console errors');
process.exit(errors.length ? 1 : 0);
