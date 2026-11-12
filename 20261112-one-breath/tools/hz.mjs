// The bubble must age the same on any screen: at 120 frames per second the film must thin as it
// does at 30 (half-float storage once swallowed small per-frame changes). Usage: node tools/hz.mjs [hz]
import puppeteer from 'puppeteer-core';
const hz = Number(process.argv[2] || 120);
const browser = await puppeteer.launch({ executablePath: process.env.CHROME || '/usr/bin/chromium', headless: true, protocolTimeout: 3600000, args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage(); page.setDefaultTimeout(3600000);
await page.setViewport({ width: 320, height: 200 });
await page.goto(`http://localhost:${process.env.PORT || 8765}/?warm=0`);
await page.waitForFunction(() => window.__ob);
await page.evaluate(() => window.__ob.pause(true));
for (let i = 0; i < 4; i++) await page.evaluate((dt) => window.__ob.skip(4, dt), 1 / hz);
const s = await page.evaluate(() => { window.__ob.readStats(); const s = window.__ob.st; return { age: s.age, min: s.stats.min, mean: s.stats.mean }; });
console.log(hz, 'Hz', JSON.stringify(s));
await browser.close();
// at 30 Hz the thinnest film is about 270 nm at age ~21 s; a frozen film stays above 340
const ok = s.min < 310;
console.log(ok ? 'film thins at ' + hz + ' Hz' : 'FAIL: film froze at ' + hz + ' Hz');
process.exit(ok ? 0 : 1);
