import { featuredArticles, loadBase, projectFile } from './catalogo.js';

const postList = document.querySelector('#post-list');
const journalNotice = document.querySelector('#journal-status');
const dialog = document.querySelector('#article-dialog');
const articleContent = document.querySelector('#article-content');
const closeArticle = document.querySelector('#close-article');
const siteTitle = document.title;
const dateFormatter = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'long', timeZone: 'UTC' });

let articles = [];
let videos = [];
let sources = [];
let excerpts = [];
let scenes = [];
let assets = [];
let renderedArticleId;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

function externalLink(text, value) {
  try {
    const url = new URL(value);
    if (!['https:', 'http:'].includes(url.protocol)) return null;
    const link = element('a', null, text);
    link.href = url.href;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    return link;
  } catch {
    return null;
  }
}

function picture(className, src, alt, dimensions, eager = false) {
  const frame = element('div', className);
  const fallback = element('span', 'thumbnail-fallback', 'Imagem indisponível');
  frame.append(fallback);
  if (!src) return frame;

  const image = element('img');
  image.alt = alt;
  if (dimensions?.largura && dimensions?.altura) {
    image.width = dimensions.largura;
    image.height = dimensions.altura;
  }
  image.loading = eager ? 'eager' : 'lazy';
  image.decoding = 'async';
  image.addEventListener('load', () => { fallback.hidden = true; });
  image.addEventListener('error', () => image.remove());
  image.src = src;
  frame.append(image);
  return frame;
}

function thumbnail(video, className) {
  const validId = /^[\w-]{11}$/.test(video?.id ?? '');
  const src = validId ? 'https://i.ytimg.com/vi/' + video.id + '/hqdefault.jpg' : null;
  return picture(className, src, '');
}

function articleLocation(id) {
  const url = new URL(location.href);
  if (id) {
    url.searchParams.set('artigo', id);
    url.hash = '';
  } else {
    url.searchParams.delete('artigo');
  }
  return url;
}

function estimateReadingTime(article) {
  const copy = [article.resumo, ...(article.secoes ?? []).map(section => section.texto)].join(' ').trim();
  return Math.max(1, Math.ceil(copy.split(/\s+/).length / 200)) + ' min de leitura';
}

function articleMeta(article, className) {
  const meta = element('div', className);
  meta.append(element('span', 'ta-badge', article.categoria));
  if (article.local) meta.append(element('span', null, article.local));
  if (article.data_publicacao) meta.append(element('span', null, estimateReadingTime(article)));
  return meta;
}

function renderCard(article, eager = false) {
  const video = videos.find(item => item.id === article.video_id);
  const asset = assets.find(item => item.id === article.ativo_ids?.[0]);
  const imagePath = projectFile(asset?.caminho);
  const card = element('a', 'ta-card hub-card card');
  card.href = articleLocation(article.id).href;
  card.dataset.post = article.id;
  const image = imagePath
    ? picture('card-image', imagePath, '', asset, eager)
    : thumbnail(video, 'card-image');
  card.append(image, element('h3', null, article.titulo), element('span', 'hub-card-meta', article.categoria));
  return card;
}

function renderPostList() {
  const featured = featuredArticles(articles);
  const archive = articles.filter(article => !featured.includes(article));
  document.querySelector('#featured-posts').append(...featured.map(article => renderCard(article, true)));
  if (archive.length) {
    document.querySelector('#journal-archive').hidden = false;
    document.querySelector('#archive-posts').append(...archive.map(article => renderCard(article)));
  }
}

function dateLine(value, prefix = '') {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value ?? '')) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  const line = element('p', 'article-date', prefix);
  const dateLabel = element('time', null, dateFormatter.format(date));
  dateLabel.dateTime = value;
  line.append(dateLabel);
  return line;
}

function timeLabel(milliseconds) {
  const seconds = Math.floor(milliseconds / 1000);
  return Math.floor(seconds / 60) + ':' + String(seconds % 60).padStart(2, '0');
}

function excerptLink(excerpt) {
  const video = videos.find(item => item.id === excerpt.video_id);
  if (!video || !Number.isFinite(excerpt.inicio_ms) || excerpt.inicio_ms < 0) return null;
  const link = externalLink(video.titulo + ' (' + timeLabel(excerpt.inicio_ms) + ')', video.url);
  if (link) {
    const url = new URL(link.href);
    url.searchParams.set('t', String(Math.floor(excerpt.inicio_ms / 1000)));
    link.href = url.href;
  }
  return link;
}

function sourceLink(source) {
  const link = externalLink(source.titulo, source.url);
  if (link) return link;
  const path = projectFile(source.caminho);
  if (!path) return null;
  const local = element('a', null, source.titulo);
  local.href = path;
  return local;
}

function appendReferences(parent, article, video) {
  const links = [];
  if (video) links.push(externalLink(video.titulo, video.url));
  for (const sourceId of article.fonte_ids ?? []) {
    const source = sources.find(item => item.id === sourceId);
    if (source && (!video || source.url !== video.url)) links.push(sourceLink(source));
  }
  for (const excerptId of article.trecho_ids ?? []) {
    const excerpt = excerpts.find(item => item.id === excerptId);
    if (excerpt) links.push(excerptLink(excerpt));
  }
  for (const sceneId of article.cena_ids ?? []) {
    const scene = scenes.find(item => item.id === sceneId);
    if (scene?.tipo === 'trecho do episódio') {
      links.push(externalLink(scene.descricao + ' (' + timeLabel(scene.inicio_ms) + ')', scene.url));
    }
  }

  const list = element('ul');
  for (const link of links.filter(Boolean)) {
    const item = element('li');
    item.append(link);
    list.append(item);
  }
  if (list.childElementCount) {
    const section = element('section', 'article-references');
    section.append(element('h3', null, 'Fontes consultadas'), list);
    parent.append(section);
  }
}

function articleFigure(assetsForArticle, assetId, eager = false) {
  const asset = assetsForArticle.find(item => item.id === assetId);
  const imagePath = projectFile(asset?.caminho);
  if (!imagePath) return null;
  const figure = element('figure', 'article-figure');
  const caption = element('figcaption', null, asset.titulo + ' ');
  const credit = 'Quadro do ' + asset.autor + ', ' + timeLabel(asset.inicio_ms);
  caption.append(externalLink(credit, asset.url) ?? credit);
  figure.append(picture('article-image', imagePath, asset.descricao_alt, asset, eager), caption);
  return figure;
}

function renderArticle(article) {
  const video = videos.find(item => item.id === article.video_id);
  const assetsForArticle = assets.filter(item => article.ativo_ids?.includes(item.id));
  articleContent.replaceChildren();
  const title = element('h2', null, article.titulo);
  title.id = 'article-title';
  articleContent.append(
    articleMeta(article, 'article-meta'),
    title,
    element('p', 'article-deck', article.resumo)
  );

  if (article.autor) articleContent.append(element('p', 'article-byline', 'Por ' + article.autor));

  const date = article.data_publicacao
    ? dateLine(article.data_publicacao, 'Publicado em ')
    : dateLine(article.data_verificacao, 'Verificado em ');
  if (date) {
    date.classList.add('article-date-spaced');
    articleContent.append(date);
  }
  if (article.status_revisao !== 'revisado') {
    articleContent.append(element('p', 'ta-notice ta-notice--warning', 'Matéria em revisão editorial.'));
  }
  const cover = articleFigure(assetsForArticle, article.ativo_ids?.[0], true);
  if (cover) {
    articleContent.append(cover);
  } else if (video) {
    const frame = element('div', 'article-figure');
    frame.append(thumbnail(video, 'article-image'));
    articleContent.append(frame);
  }

  const prose = element('div', 'article-prose');
  for (const section of article.secoes ?? []) {
    const body = element('section');
    body.append(element('h3', null, section.titulo));
    for (const paragraph of (section.texto ?? '').split(/\n\s*\n/)) {
      if (paragraph.trim()) body.append(element('p', null, paragraph.trim()));
    }
    if (section.ativo_id) {
      const figure = articleFigure(assetsForArticle, section.ativo_id);
      if (figure) body.append(figure);
    }
    prose.append(body);
  }
  appendReferences(prose, article, video);
  articleContent.append(prose);
  renderedArticleId = article.id;
}

function syncArticle() {
  const activeId = new URL(location.href).searchParams.get('artigo');
  const article = articles.find(item => item.id === activeId);
  document.title = article ? article.titulo + ' | Turismo Aqui' : siteTitle;
  if (!article) {
    if (dialog.open) dialog.close();
    journalNotice.textContent = activeId ? 'Matéria não encontrada. Consulte a lista abaixo.' : '';
    if (!activeId && !articles.length) journalNotice.textContent = 'Nenhuma matéria cadastrada.';
    return;
  }
  journalNotice.textContent = '';
  if (renderedArticleId !== article.id) renderArticle(article);
  if (!dialog.open) {
    dialog.scrollTop = 0;
    dialog.showModal();
  }
}

postList.addEventListener('click', event => {
  const link = event.target.closest('[data-post]');
  if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
  event.preventDefault();
  history.pushState({ turismoArtigo: link.dataset.post }, '', link.href);
  syncArticle();
});

closeArticle.addEventListener('click', () => dialog.close());
dialog.addEventListener('close', () => {
  const activeId = new URL(location.href).searchParams.get('artigo');
  if (dialog.open || !activeId || activeId !== renderedArticleId) return;
  if (history.state?.turismoArtigo === activeId) {
    history.back();
  } else {
    history.replaceState(null, '', articleLocation());
    syncArticle();
  }
});

async function loadCatalog() {
  try {
    const data = await loadBase();
    articles = data.artigos ?? [];
    videos = data.videos ?? [];
    sources = data.fontes ?? [];
    excerpts = data.trechos ?? [];
    scenes = data.cenas ?? [];
    assets = data.ativos ?? [];
    renderPostList();
    window.addEventListener('popstate', syncArticle);
    syncArticle();
  } catch {
    journalNotice.textContent = 'Não foi possível carregar as matérias. Confira se o servidor local foi iniciado na pasta raiz do projeto.';
  }
}

loadCatalog();
