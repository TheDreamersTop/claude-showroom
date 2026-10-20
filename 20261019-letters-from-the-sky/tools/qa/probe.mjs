import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--disable-component-update'] });
const page = await browser.newPage({ viewport: { width: 800, height: 450 } });
page.on('console', m => console.log('[c]', m.text())); page.on('pageerror', e => console.log('[pe]', e.message));
await page.goto(process.argv[2]); await page.waitForTimeout(+process.argv[3] || 3000);
console.log(await page.evaluate(process.argv[4]));
await browser.close();
