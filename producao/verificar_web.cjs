const assert = require('node:assert/strict');
const { chromium } = require(process.env.TURISMO_AQUI_PLAYWRIGHT || 'playwright');

const origin = process.env.TURISMO_AQUI_TEST_ORIGIN || 'http://127.0.0.1:8000';

async function verify() {
  const browser = await chromium.launch({
    executablePath: process.env.TURISMO_AQUI_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: true,
  });
  try {
    const page = await browser.newPage();
    await page.route('https://**', route => route.abort());
    await page.goto(origin + '/');
    await page.getByRole('heading', { name: 'Central Turismo Aqui' }).waitFor();
    const localLinks = await page.locator('main a[href]').evaluateAll(links => {
      return [...new Set(links.map(link => link.href).filter(href => new URL(href).origin === location.origin))];
    });
    for (const link of localLinks) {
      assert.ok((await page.request.head(link)).ok(), link);
    }
    await page.getByRole('link', { name: 'Peças para redes sociais', exact: false }).first().click();
    assert.equal(await page.locator('.social-card').count(), 10);

    await page.goto(origin + '/site/');
    await page.locator('#spotlight .spotlight-card').first().waitFor();
    assert.equal(await page.locator('#spotlight .spotlight-card').count(), 3);
    for (const image of await page.locator('#spotlight img, [data-asset] img').all()) {
      await image.scrollIntoViewIfNeeded();
      await image.evaluate(node => node.decode());
      assert.match(await image.getAttribute('src'), /^\.\.\/entregaveis\/catalogo-visual\/imagens\//);
    }
    await page.locator('#spotlight a.spotlight-card').first().click();
    await page.locator('#article-dialog[open] #article-title').waitFor();
    assert.match(page.url(), /\/site\/blog\.html\?artigo=/);
    await page.goto(origin + '/site/?artigo=caminhos');
    await page.locator('#article-dialog[open] #article-title').waitFor();
    assert.match(page.url(), /\/site\/blog\.html\?artigo=caminhos$/);

    await page.goto(origin + '/site/blog.html');
    const posts = page.locator('#post-list [data-post]');
    await posts.first().waitFor();
    assert.equal(await posts.count(), 8);
    const articleLinks = await posts.evaluateAll(links => links.map(link => link.href));
    assert.equal(new Set(articleLinks).size, 8);
    assert.equal(await page.locator('#featured-posts .card').count(), 3);
    assert.equal(await page.locator('#archive-posts .card').count(), 5);
    const coverImages = page.locator('#post-list .card-image img');
    assert.equal(await coverImages.count(), 8);
    for (const image of await coverImages.all()) {
      await image.scrollIntoViewIfNeeded();
      await image.evaluate(node => node.decode());
      assert.match(await image.getAttribute('src'), /^\.\.\/entregaveis\/catalogo-visual\/imagens\//);
    }

    await posts.first().click();
    await page.waitForURL(url => url.searchParams.has('artigo'));
    await page.locator('#article-dialog[open]').waitFor();
    await page.goBack();
    await page.locator('#article-dialog').waitFor({ state: 'hidden' });
    assert.equal(new URL(page.url()).searchParams.has('artigo'), false);

    for (const href of articleLinks) {
      await page.goto(href);
      await page.locator('#article-dialog[open] #article-title').waitFor();
      assert.ok(await page.locator('#article-content ul a[href^="http"]').count() >= 1);
      assert.ok(await page.locator('#article-content a[href*="youtube.com/watch"][href*="&t="]').count() >= 1);
      await page.keyboard.press('Escape');
      await page.waitForURL(url => !url.searchParams.has('artigo'));
    }

    for (const href of articleLinks.slice(0, 3)) {
      await page.goto(href);
      const article = page.locator('#article-dialog[open] #article-content');
      await article.waitFor();
      assert.equal(await article.locator('.article-prose > section:not(.article-references)').count(), 4);
      const figures = article.locator('figure');
      assert.equal(await figures.count(), 2);
      for (const figure of await figures.all()) {
        const image = figure.locator('img[alt]:not([alt=""])');
        await image.scrollIntoViewIfNeeded();
        await image.evaluate(node => node.decode());
        assert.match(await figure.locator('figcaption a').getAttribute('href'), /youtube\.com\/watch.*&t=\d+s$/);
      }
      await page.keyboard.press('Escape');
      await page.waitForURL(url => !url.searchParams.has('artigo'));
    }

    const ebook = await page.locator('footer a[href$=".pdf"]').getAttribute('href');
    const video = await page.locator('footer a[href$=".webm"]').getAttribute('href');
    for (const asset of [ebook, video]) {
      assert.equal((await page.request.head(new URL(asset, page.url()).href)).ok(), true);
    }

    await page.getByRole('navigation', { name: 'Navegação principal' }).getByRole('link', { name: 'Destinos' }).click();
    const places = page.locator('#places .place');
    await places.first().waitFor();
    assert.ok(await places.count() > 1);
    assert.equal(await page.locator('#places .place-visual img[src*="catalogo-visual"]').count(), 4);
    assert.equal(await page.locator('#videos-list .video-card img[src*="catalogo-visual"]').count(), 6);
    await page.locator('#search').fill('chao');
    assert.ok(await places.count() >= 1);
    await page.locator('#search').fill('Ilha');
    await page.locator('#places h3').getByText('Ilha do Amor').waitFor();
    await page.locator('#search').fill('termo-sem-resultado-xyz');
    await page.locator('#empty').waitFor();
    assert.equal(await places.count(), 0);

    await page.locator('#search').fill('');
    const firstPlace = places.first();
    await page.locator('#lugar-ilha-do-amor').getByRole('link', { name: 'Ver no mapa' }).click();
    await page.waitForURL(url => url.hash === '#mapa');
    assert.equal(await page.locator('#map-place').inputValue(), 'ilha-do-amor');
    await firstPlace.locator('summary').click();
    assert.ok(await firstPlace.locator('details[open] a[href^="http"]').count() >= 1);
    assert.ok(await page.locator('#tips-list .record-sources a[href^="http"]').count() >= 1);
    assert.ok(await page.locator('#tips-list .record-sources time').count() >= 1);
    assert.match(await page.locator('#map-frame').getAttribute('src'), /marker=/);
    await page.locator('#map-place').selectOption('ilha-do-amor');
    assert.match(await page.locator('#map-marker').textContent(), /P2\.5/);
    assert.match(await page.locator('#map-frame').getAttribute('title'), /Ilha do Amor/);
    assert.equal(await page.locator('#mapa a[href="#lugares"]').first().isVisible(), true);
    assert.ok(await places.count() > 1);

    await page.route('**/data/base.json', async route => {
      const response = await route.fetch();
      const data = await response.json();
      const videoId = data.artigos[0].video_id;
      data.trechos = [...(data.trechos ?? []), { id: 'trecho-validacao', inicio_ms: 12000, video_id: videoId }];
      data.artigos[0].trecho_ids = ['trecho-validacao'];
      await route.fulfill({ response, json: data });
    });
    const legacyLink = articleLinks.find(href => new URL(href).searchParams.get('artigo') === 'caminhos');
    await page.goto(legacyLink);
    await page.locator('#article-dialog[open] #article-title').waitFor();
    const excerpt = page.locator('#article-content a[href*="t=12"]');
    await excerpt.waitFor();
    assert.match(await excerpt.textContent(), /0:12/);
    await page.unroute('**/data/base.json');

    await page.route('**/data/base.json', route => route.abort());
    await page.goto(origin + '/site/blog.html');
    await page.getByText('Não foi possível carregar as matérias.', { exact: false }).waitFor();
    await page.goto(origin + '/app/');
    await page.getByText('Não foi possível carregar a base.', { exact: false }).waitFor();
    console.log('Verificação desktop concluída. Central, site, revista, materiais e aplicativo testados.');
  } finally {
    await browser.close();
  }
}

verify().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
