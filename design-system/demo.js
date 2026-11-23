if (location.protocol === 'file:') {
  document.querySelectorAll('[data-local-label]').forEach(label => {
    const link = label.closest('a');
    label.textContent = label.dataset.localLabel;
    link.removeAttribute('download');
    link.target = '_blank';
    link.rel = 'noopener';
  });
}

const destinationDialog = document.querySelector('#destination-dialog');
document.querySelector('[data-open-destination]').addEventListener('click', () => {
  destinationDialog.showModal();
});

const favoriteButtons = [...document.querySelectorAll('[data-favorite]')];
const favorites = new Set();
const favoritesKey = 'turismo-aqui:design-system:favorites';

try {
  const saved = JSON.parse(localStorage.getItem(favoritesKey) ?? '[]');
  if (Array.isArray(saved)) saved.forEach(name => favorites.add(name));
} catch {
  // O exemplo mantém a seleção durante a sessão se o armazenamento estiver indisponível.
}

function updateFavorites() {
  favoriteButtons.forEach(button => {
    button.setAttribute('aria-pressed', String(favorites.has(button.dataset.name)));
  });
}

favoriteButtons.forEach(button => {
  button.addEventListener('click', () => {
    const { name } = button.dataset;
    if (favorites.has(name)) favorites.delete(name);
    else favorites.add(name);
    updateFavorites();
    try {
      localStorage.setItem(favoritesKey, JSON.stringify([...favorites]));
    } catch {
      // A seleção continua visível nesta página.
    }
  });
});
updateFavorites();

const catalog = [
  { name: 'Alter do Chão', type: 'passeio' },
  { name: 'Ilha do Amor', type: 'praia' },
  { name: 'Rio Tapajós', type: 'passeio' },
];
const searchForm = document.querySelector('#filter-demo');
const searchInput = document.querySelector('#destination-search');
const searchError = document.querySelector('#search-error');
const searchHint = document.querySelector('#search-hint');
const searchResult = document.querySelector('#search-result');
const filters = [...searchForm.querySelectorAll('[data-filter]')];
let activeFilter = 'todos';
let submittedQuery = '';

function normalize(value) {
  return value.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase().trim();
}

function showSearchResult() {
  const matches = catalog.filter(place =>
    (activeFilter === 'todos' || place.type === activeFilter) &&
    normalize(place.name).includes(submittedQuery)
  );
  if (matches.length === 0) {
    searchResult.textContent = 'Nenhum lugar encontrado. Ajuste a busca ou o filtro.';
    return;
  }
  const count = matches.length === 1 ? '1 lugar' : matches.length + ' lugares';
  searchResult.textContent = count + ' · ' + matches.map(place => place.name).join(', ');
}

function showSearchError(invalid) {
  searchError.hidden = !invalid;
  searchHint.hidden = invalid;
  searchInput.setAttribute('aria-describedby', invalid ? 'search-error' : 'search-hint');
  if (invalid) searchInput.setAttribute('aria-invalid', 'true');
  else searchInput.removeAttribute('aria-invalid');
}

searchForm.addEventListener('submit', event => {
  event.preventDefault();
  const query = normalize(searchInput.value);
  const invalid = query.length === 1;
  showSearchError(invalid);
  if (invalid) {
    searchInput.focus();
    return;
  }
  submittedQuery = query;
  showSearchResult();
});

searchInput.addEventListener('input', () => {
  const query = normalize(searchInput.value);
  if (query.length !== 1) showSearchError(false);
  if (!query && submittedQuery) {
    submittedQuery = '';
    showSearchResult();
  }
});

filters.forEach(button => button.addEventListener('click', () => {
  activeFilter = button.dataset.filter;
  filters.forEach(filter => filter.setAttribute('aria-pressed', String(filter === button)));
  showSearchResult();
}));

const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
const motionCard = document.querySelector('.motion-card');
const motionResult = document.querySelector('#motion-result');
let motionPreview;
function syncMotionPreference() {
  motionPreview?.cancel();
  motionResult.textContent = reducedMotion.matches ? 'Movimento reduzido ativo' : 'Entrada: 280 ms';
}
reducedMotion.addEventListener('change', syncMotionPreference);
syncMotionPreference();

document.querySelector('#play-motion').addEventListener('click', () => {
  motionPreview?.cancel();
  if (reducedMotion.matches) return;
  const styles = getComputedStyle(motionCard);
  const duration = Number.parseFloat(styles.getPropertyValue('--ta-motion-enter'));
  const distance = styles.getPropertyValue('--ta-motion-distance').trim();
  const easing = styles.getPropertyValue('--ta-motion-ease').trim();
  motionPreview = motionCard.animate([
    { opacity: 0, transform: 'translateY(' + distance + ')' },
    { opacity: 1, transform: 'translateY(0)' },
  ], { duration, easing });
});

const track = document.querySelector('#destination-track');
const cards = [...track.querySelectorAll('.ta-card')];
const cardNames = cards.map(card => card.querySelector('h4').textContent);
const dots = [...document.querySelectorAll('[data-slide]')];
const galleryStatus = document.querySelector('#gallery-status');
const prev = document.querySelector('#prev-card');
const next = document.querySelector('#next-card');
let current = -1;
let requested = null;
let settleTimer;
prev.disabled = false;

function selectSlide(index) {
  if (index === current) return;
  current = index;
  dots.forEach((dot, dotIndex) => {
    if (dotIndex === index) dot.setAttribute('aria-current', 'true');
    else dot.removeAttribute('aria-current');
  });
  prev.setAttribute('aria-disabled', String(index === 0));
  next.setAttribute('aria-disabled', String(index === cards.length - 1));
  galleryStatus.textContent = (index + 1) + ' de ' + cards.length + ' · ' + cardNames[index];
}

function slidePosition(index) {
  return cards[index].offsetLeft - cards[0].offsetLeft;
}

function syncFromScroll() {
  let closest = 0;
  for (let i = 1; i < cards.length; i += 1) {
    if (Math.abs(track.scrollLeft - slidePosition(i)) < Math.abs(track.scrollLeft - slidePosition(closest))) closest = i;
  }
  requested = null;
  selectSlide(closest);
}

function scrollToSlide(index) {
  const target = Math.max(0, Math.min(cards.length - 1, index));
  const left = slidePosition(target);
  if (Math.abs(track.scrollLeft - left) < 2) {
    syncFromScroll();
    return;
  }
  requested = target;
  track.scrollTo({ left, behavior: reducedMotion.matches ? 'instant' : 'smooth' });
}

prev.addEventListener('click', () => {
  if (prev.getAttribute('aria-disabled') !== 'true') scrollToSlide((requested ?? current) - 1);
});
next.addEventListener('click', () => {
  if (next.getAttribute('aria-disabled') !== 'true') scrollToSlide((requested ?? current) + 1);
});
dots.forEach(dot => dot.addEventListener('click', () => scrollToSlide(Number(dot.dataset.slide))));

track.addEventListener('keydown', event => {
  if (event.target !== track || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
  const base = requested ?? current;
  const targets = { ArrowLeft: base - 1, ArrowRight: base + 1, Home: 0, End: cards.length - 1 };
  const target = targets[event.key];
  if (typeof target !== 'number') return;
  event.preventDefault();
  scrollToSlide(target);
});

if ('onscrollend' in track) {
  track.addEventListener('scrollend', syncFromScroll);
} else {
  track.addEventListener('scroll', () => {
    clearTimeout(settleTimer);
    settleTimer = setTimeout(syncFromScroll, 120);
  }, { passive: true });
}

selectSlide(0);
