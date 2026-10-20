import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--disable-component-update'] });
const page = await browser.newPage({ viewport: { width: 400, height: 300 } });
page.on('pageerror', e => console.log('[pe]', e.message));
await page.goto('http://localhost:8080/20261019-letters-from-the-sky/tools/simprobe.html');
await page.waitForFunction('window.__done === true', null, { timeout: 1200000, polling: 1000 });
console.log(await page.evaluate('JSON.stringify(window.__out)'));
await browser.close();
