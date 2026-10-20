// usage: node phases.mjs <url> <prefix> <json [[phase, t, name, evalBefore?], ...]>
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
const [url, prefix, plan] = [process.argv[2], process.argv[3], JSON.parse(process.argv[4])];
const W = +(process.env.VW || 1600), H = +(process.env.VH || 900);
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-component-update', '--no-first-run', '--disable-background-networking'] });
const page = await browser.newPage({ viewport: { width: W, height: H }, acceptDownloads: true });
page.on('download', d => d.saveAs(prefix + 'download.png').then(() => console.log('download saved')));
const logs = [];
page.on('console', m => { if (m.type() !== 'log' || /error|warn/i.test(m.text())) logs.push(`[${m.type()}] ${m.text()}`); });
page.on('pageerror', e => logs.push(`[pageerror] ${e.message}`));
await page.addInitScript(() => { window.__mv = (x, y) => window.dispatchEvent(new PointerEvent('pointermove', { clientX: x, clientY: y })); window.__pd = () => document.getElementById('gl').dispatchEvent(new PointerEvent('pointerdown', { bubbles: true })); window.__pu = () => window.dispatchEvent(new PointerEvent('pointerup')); window.__sp = () => window.dispatchEvent(new KeyboardEvent('keydown', { code: 'Space' })); });
await page.goto(url, { waitUntil: 'load' });
await page.waitForFunction('window.__ready === true', null, { timeout: 120000 });
for (const [phase, t, name, ev] of plan) {
  if (ev) await page.evaluate(ev);
  if (phase) await page.waitForFunction(([p, tt]) => window.__S && window.__S.phase === p && window.__S.phaseT >= tt, [phase, t], { timeout: 600000, polling: 100 });
  else await page.waitForTimeout(t);
  if (name) { await page.screenshot({ path: `${prefix}${name}.png` }); console.log('shot', name, await page.evaluate('JSON.stringify({p:__S.phase,t:+__S.phaseT.toFixed(2),T:__T,R:__R,v:window.__printv})')); }
}
console.log(logs.filter(l => !/404/.test(l)).slice(0, 30).join('\n'));
await browser.close();
