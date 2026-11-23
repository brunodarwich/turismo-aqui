import { applyCatalogFigure, loadBase, projectFile, setCatalogImage } from '../site/catalogo.js';

const placeList = document.querySelector('#places');
const videoList = document.querySelector('#videos-list');
const tipList = document.querySelector('#tips-list');
const loadStatus = document.querySelector('#load-status');
const emptySearch = document.querySelector('#empty');
const search = document.querySelector('#search');

const mapFrame = document.querySelector('#map-frame');
const mapLink = document.querySelector('#map-link');
const markerNote = document.querySelector('#map-marker');
const mapStatus = document.querySelector('#map-status');
const mapSelector = document.querySelector('#map-place');
const mapControls = document.querySelector('#map-controls');
const dateFormatter = new Intl.DateTimeFormat('pt-BR', { timeZone: 'UTC' });

let places = [];
let sources = [];
let mapPlaces = [];
let assets = new Map();

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

function appendDate(target, value, label) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value ?? '')) return;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return;
  const time = element('time', null, dateFormatter.format(date));
  time.dateTime = value;
  const line = element('p', 'record-date', label);
  line.append(time);
  target.append(line);
}

function sourceList(ids) {
  const list = element('ul', 'record-sources');
  for (const sourceId of ids ?? []) {
    const source = sources.find(item => item.id === sourceId);
    if (!source) continue;
    const link = externalLink(source.titulo, source.url);
    if (!link) continue;
    const item = element('li');
    item.append(link);
    appendDate(item, source.data_consulta, 'Fonte consultada em ');
    list.append(item);
  }
  return list;
}

function mapLinks(place) {
  const { latitude, longitude } = place;
  const embed = new URL('https://www.openstreetmap.org/export/embed.html');
  const viewport = [longitude - 0.06, latitude - 0.035, longitude + 0.06, latitude + 0.035];
  embed.searchParams.set('bbox', viewport.map(coordinate => coordinate.toFixed(4)).join(','));
  embed.searchParams.set('layer', 'mapnik');
  embed.searchParams.set('marker', latitude + ',' + longitude);

  const full = new URL('https://www.openstreetmap.org/');
  full.searchParams.set('mlat', String(latitude));
  full.searchParams.set('mlon', String(longitude));
  full.hash = 'map=13/' + latitude + '/' + longitude;
  return { embed, full };
}

function selectMapPlace(place) {
  const links = mapLinks(place);
  mapSelector.value = place.id;
  mapLink.href = links.full.href;
  mapLink.textContent = 'Ver ' + place.nome + ' no OpenStreetMap';
  mapFrame.title = 'Mapa com marcador de ' + place.nome;
  markerNote.textContent = place.localizacao_nota || 'Marcador: ' + place.nome + '.';
  mapStatus.hidden = navigator.onLine;
  mapFrame.hidden = !navigator.onLine;
  if (navigator.onLine && mapFrame.src !== links.embed.href) mapFrame.src = links.embed.href;
}

function renderMap() {
  mapPlaces = places.filter(place =>
    Number.isFinite(place.latitude) && Math.abs(place.latitude) <= 90
    && Number.isFinite(place.longitude) && Math.abs(place.longitude) <= 180
    && (place.fonte_ids ?? []).some(id => sources.some(source => source.id === id))
  );
  for (const place of mapPlaces) {
    const option = element('option', null, place.nome);
    option.value = place.id;
    mapSelector.append(option);
  }
  const initialPlace = mapPlaces.find(place => place.id === 'alter-do-chao') ?? mapPlaces[0];
  if (initialPlace) {
    mapControls.hidden = false;
    selectMapPlace(initialPlace);
  }
}

function renderPlace(place) {
  const card = element('article', 'ta-card place');
  const asset = assets.get(place.ativo_ids?.[0]);
  const photo = catalogPhoto(asset);
  const art = element('div', photo ? 'place-visual' : 'place-visual place-visual--marker');
  const body = element('div', 'place-content');
  const details = element('details', 'place-details');
  card.id = 'lugar-' + place.id;
  if (photo) {
    art.append(photo);
  } else {
    const marker = element('img');
    marker.src = '../design-system/assets/icone-turismo-aqui.png';
    marker.alt = '';
    marker.width = 44;
    marker.height = 44;
    art.append(marker);
  }

  body.append(
    element('h3', null, place.nome),
    element('p', 'place-category', place.categoria || 'Lugar')
  );
  details.append(element('summary', null, 'Sobre o lugar'), element('p', null, place.descricao));
  if (place.localizacao_nota) details.append(element('p', null, place.localizacao_nota));

  if (mapPlaces.includes(place)) {
    const showMap = element('a', 'ta-button ta-button--secondary', 'Ver no mapa');
    showMap.href = '#mapa';
    showMap.addEventListener('click', () => selectMapPlace(place));
    body.append(showMap);
  } else {
    details.append(element('p', null, 'Ainda sem coordenadas verificadas no catálogo.'));
  }

  const credit = externalLink('Quadro do Turismo Aqui', asset?.url);
  if (credit) details.append(credit);
  const references = sourceList(place.fonte_ids);
  if (references.childElementCount) details.append(references);
  card.append(art, body, details);
  return card;
}

function searchText(value) {
  return String(value ?? '').normalize('NFD').replace(/\p{Diacritic}/gu, '').toLocaleLowerCase('pt-BR');
}

function renderPlaces() {
  const term = searchText(search.value.trim());
  const matches = places.filter(place =>
    [place.nome, place.categoria, place.descricao, ...(place.temas ?? [])]
      .some(part => searchText(part).includes(term))
  );
  emptySearch.hidden = matches.length > 0 || places.length === 0;
  placeList.replaceChildren(...matches.map(renderPlace));
}

function catalogPhoto(asset, alt = asset?.descricao_alt ?? '') {
  const path = projectFile(asset?.caminho);
  if (!path) return null;
  const image = element('img');
  setCatalogImage(image, asset, path, alt);
  image.loading = 'lazy';
  image.decoding = 'async';
  return image;
}

function renderVideos(videos, articles) {
  for (const video of videos) {
    const card = externalLink('', video.url);
    if (!card) continue;
    const article = articles.find(item => item.video_id === video.id && item.ativo_ids?.length);
    const photo = catalogPhoto(assets.get(article?.ativo_ids[0]), '');
    card.className = 'ta-card hub-card video-card';
    if (photo) card.append(photo);
    card.append(element('h3', null, video.titulo));
    videoList.append(card);
  }
}

function renderTips(tips) {
  for (const tip of tips) {
    const card = element('article', 'ta-card tip');
    card.append(element('h3', null, tip.titulo), element('p', null, tip.texto));
    if (tip.status_revisao !== 'revisado') card.append(element('p', 'record-date', 'Em revisão editorial'));
    appendDate(card, tip.data_verificacao, 'Verificado em ');
    const place = places.find(item => item.id === tip.lugar_id);
    if (place) {
      const link = element('a', 'text-link', 'Explorar ' + place.nome);
      link.href = '#lugar-' + place.id;
      link.addEventListener('click', () => {
        if (search.value) {
          search.value = '';
          renderPlaces();
        }
      });
      card.append(link);
    }
    const references = sourceList(tip.fonte_ids);
    if (references.childElementCount) {
      const details = element('details', 'tip-sources');
      details.append(element('summary', null, 'Fontes'), references);
      card.append(details);
    }
    tipList.append(card);
  }
  if (!tips.length) tipList.append(element('p', null, 'Ainda não há dicas no catálogo.'));
}

search.addEventListener('input', renderPlaces);
mapSelector.addEventListener('change', () => {
  const place = mapPlaces.find(item => item.id === mapSelector.value);
  if (place) selectMapPlace(place);
});
mapFrame.addEventListener('error', () => {
  mapFrame.hidden = true;
  mapStatus.hidden = false;
});
window.addEventListener('offline', () => {
  mapFrame.hidden = true;
  mapStatus.hidden = false;
});
window.addEventListener('online', () => {
  const place = mapPlaces.find(item => item.id === mapSelector.value);
  if (place) {
    mapFrame.removeAttribute('src');
    selectMapPlace(place);
  }
});

async function loadCatalog() {
  try {
    const data = await loadBase();
    places = data.lugares ?? [];
    sources = data.fontes ?? [];
    assets = new Map((data.ativos ?? []).map(asset => [asset.id, asset]));
    const cover = document.querySelector('[data-asset]');
    applyCatalogFigure(cover, assets.get(cover.dataset.asset));
    renderMap();
    renderPlaces();
    renderVideos(data.videos ?? [], data.artigos ?? []);
    renderTips(data.dicas ?? []);
    loadStatus.textContent = places.length ? '' : 'Ainda não há lugares no catálogo.';
  } catch {
    loadStatus.textContent = 'Não foi possível carregar a base. Confira se o servidor local foi iniciado na pasta raiz do projeto.';
  }
}

loadCatalog();
