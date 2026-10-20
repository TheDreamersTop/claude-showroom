// usage: node shot.mjs <url> <out.png> [waitMs]  env: VW VH EVAL EVALWAIT STEPS(json [{eval,wait,shot}])
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
const [url, out, wait] = [process.argv[2], process.argv[3], +(process.argv[4] || 3000)];
const W = +(process.env.VW || 1600), H = +(process.env.VH || 900);
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--enable-webgl','--disable-component-update','--no-first-run','--disable-background-networking'] });
const page = await browser.newPage({ viewport: { width: W, height: H } });
const logs = [];
page.on('console', m => logs.push(`[${m.type()}] ${m.text()}`));
page.on('pageerror', e => logs.push(`[pageerror] ${e.message}`));
page.on('requestfailed', r => logs.push(`[reqfail] ${r.url()}`));
const t0 = Date.now();
await page.goto(url, { waitUntil: 'load', timeout: 120000 });
try { await page.waitForFunction('window.__ready === true', null, { timeout: 300000 }); } catch (e) {}
await page.waitForTimeout(wait);
if (process.env.WAITFOR) await page.waitForFunction(process.env.WAITFOR, null, { timeout: 900000, polling: 500 });
if (process.env.STEPS) {
  for (const s of JSON.parse(process.env.STEPS)) {
    if (s.eval) await page.evaluate(s.eval);
    if (s.mouse) { for (const [x, y] of s.mouse) { await page.mouse.move(x, y); await page.waitForTimeout(s.mdelay || 16); } }
    if (s.down) await page.mouse.down(); if (s.up) await page.mouse.up();
    if (s.key) await page.keyboard.press(s.key);
    if (s.wait) await page.waitForTimeout(s.wait);
    if (s.shot) await page.screenshot({ path: s.shot });
  }
} else await page.screenshot({ path: out, fullPage: !!process.env.FULL });
console.log(logs.slice(0, 40).join('\n')); console.log('done', ((Date.now() - t0) / 1000).toFixed(1) + 's');
await browser.close();
