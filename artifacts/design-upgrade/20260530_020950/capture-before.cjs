const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const url = process.argv[2];
  const out = path.resolve(process.argv[3]);
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 }, deviceScaleFactor: 1 });
  await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
  await page.screenshot({ path: out, fullPage: true });
  await browser.close();
})();
