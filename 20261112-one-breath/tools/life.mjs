// Fast lifetime check without screenshots: prints thinnest and mean film every 10 s of sim time.
import puppeteer from 'puppeteer-core';
const browser = await puppeteer.launch({ executablePath: '/usr/bin/chromium', headless: true, protocolTimeout: 3600000, args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage(); page.setDefaultTimeout(1200000);
page.on('pageerror', (e) => console.log('ERR', e));
await page.setViewport({ width: 320, height: 200 });
await page.goto(`http://localhost:${process.env.PORT || 8765}/?warm=0`);
await page.waitForFunction(() => window.__ob);
await page.evaluate(() => window.__ob.pause(true));
for (let t = 10; t <= Number(process.argv[2] || 120); t += 10) {
  await page.evaluate(() => window.__ob.skip(10));
  const s = await page.evaluate(() => { const s = window.__ob.st; return `${s.phase} age=${s.age.toFixed(0)} min=${s.stats?.min.toFixed(0)} mean=${s.stats?.mean.toFixed(0)}`; });
  console.log('t', t, s);
  if (!s.startsWith('alive')) break;
}
await browser.close();
