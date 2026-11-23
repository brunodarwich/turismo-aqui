const assert = require('node:assert/strict');
const { chromium } = require(process.env.TURISMO_AQUI_PLAYWRIGHT || 'playwright');

const origin = process.env.TURISMO_AQUI_TEST_ORIGIN || 'http://127.0.0.1:8000';

async function verify() {
  const browser = await chromium.launch({
    executablePath: process.env.TURISMO_AQUI_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: true,
  });
  try {
    for (const width of [320, 390]) {
      const page = await browser.newPage({ viewport: { width, height: 844 }, deviceScaleFactor: 1 });
      await page.route('https://**', route => route.abort());
      const pages = [
        ['/', '#produtos .hub-card'], ['/site/', '#spotlight .spotlight-card'],
        ['/site/blog.html', '#post-list .card'], ['/app/', '#places .place'],
        ['/entregaveis/redes-sociais/', '.social-card'],
      ];
      for (const [path, firstItem] of pages) {
        await page.goto(origin + path);
        await page.locator(firstItem).first().waitFor();
        const contentWidth = await page.evaluate(() => document.documentElement.scrollWidth);
        assert.ok(contentWidth <= width, path + ' ultrapassa a viewport de ' + width + ' px');
      }

      await page.goto(origin + '/site/blog.html');
      await page.locator('[data-post]').first().click();
      await page.locator('#article-dialog[open]').waitFor();
      await page.getByRole('button', { name: 'Fechar artigo' }).click();
      await page.locator('#article-dialog').waitFor({ state: 'hidden' });
      await page.waitForURL(url => !url.searchParams.has('artigo'));
      await page.close();
    }
    console.log('Verificação móvel concluída em 320 e 390 px.');
  } finally {
    await browser.close();
  }
}

verify().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
