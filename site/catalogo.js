export function projectFile(value) {
  const parts = value?.split('/');
  if (!parts || !['data', 'entregaveis'].includes(parts[0])) return null;
  if (parts.some(part => !/^[\w.-]+$/.test(part) || part === '.' || part === '..')) return null;
  return '../' + value;
}

export function setCatalogImage(image, asset, path, alt = asset.descricao_alt ?? '') {
  image.src = path;
  image.alt = alt;
  if (asset.largura && asset.altura) {
    image.width = asset.largura;
    image.height = asset.altura;
  }
}

export function applyCatalogFigure(figure, asset) {
  const path = projectFile(asset?.caminho);
  if (!path) return;
  setCatalogImage(figure.querySelector('img'), asset, path);
  if (!asset.url?.startsWith('https://')) return;
  figure.querySelector('[data-photo-title]').textContent = asset.titulo;
  figure.querySelector('figcaption a').href = asset.url;
  const seconds = Math.floor(asset.inicio_ms / 1000);
  const time = Math.floor(seconds / 60) + ':' + String(seconds % 60).padStart(2, '0');
  figure.querySelector('[data-photo-credit]').textContent = asset.autor + ', ' + time;
}

export function featuredArticles(articles) {
  return articles
    .filter(article => article.data_publicacao && article.status_revisao === 'revisado')
    .sort((first, second) => second.data_publicacao.localeCompare(first.data_publicacao))
    .slice(0, 3);
}

export async function loadBase() {
  const response = await fetch('../data/base.json');
  if (!response.ok) throw new Error('Base indisponível');
  return response.json();
}
