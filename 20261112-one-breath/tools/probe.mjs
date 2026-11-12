import puppeteer from 'puppeteer-core';
const browser = await puppeteer.launch({ executablePath: '/usr/bin/chromium', headless: true, protocolTimeout: 3600000, args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage(); page.setDefaultTimeout(600000);
page.on('pageerror', (e) => console.log('ERR', e));
await page.setViewport({ width: 640, height: 400 });
await page.goto(`http://localhost:${process.env.PORT || 8765}/?warm=0`);
await page.waitForFunction(() => window.__ob);
await page.evaluate(() => window.__ob.pause(true));
for (const s of [0.1, 1, 3]) { await page.evaluate((d) => window.__ob.skip(d), s); console.log(s, JSON.stringify(await page.evaluate(() => window.__ob.probe()))); }
await browser.close();
