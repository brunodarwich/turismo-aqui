import { applyCatalogFigure, featuredArticles, loadBase, projectFile, setCatalogImage } from './catalogo.js';

function renderSpotlight(articles, assets) {
  const template = document.querySelector('#spotlight-card');
  const cards = featuredArticles(articles).map(article => {
    const card = template.content.firstElementChild.cloneNode(true);
    const asset = assets.get(article.ativo_ids?.[0]);
    const path = projectFile(asset?.caminho);
    const image = card.querySelector('img');
    if (path) setCatalogImage(image, asset, path, '');
    else image.remove();
    card.href = 'blog.html?artigo=' + encodeURIComponent(article.id);
    card.querySelector('h3').textContent = article.titulo;
    card.querySelector('.hub-card-meta').textContent = article.categoria;
    return card;
  });
  document.querySelector('#spotlight').append(...cards);
}

async function renderHome() {
  try {
    const data = await loadBase();
    const assets = new Map((data.ativos ?? []).map(asset => [asset.id, asset]));
    renderSpotlight(data.artigos ?? [], assets);
    document.querySelectorAll('[data-asset]').forEach(figure => {
      applyCatalogFigure(figure, assets.get(figure.dataset.asset));
    });
  } catch {
    document.querySelector('#spotlight-status').textContent = 'Não foi possível carregar as matérias em destaque.';
  }
}

const current = new URL(location.href);
if (current.searchParams.has('artigo')) {
  const blog = new URL('blog.html', current);
  blog.search = current.search;
  blog.hash = current.hash;
  location.replace(blog);
} else {
  renderHome();
  if ('IntersectionObserver' in window && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08 });
    document.documentElement.classList.add('motion-ready');
    document.querySelectorAll('.reveal').forEach(element => observer.observe(element));
  }
}
