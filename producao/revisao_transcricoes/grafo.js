'use strict';

const graphColors = { Local:'#72d4ad', Comida:'#f8b777', Pessoa:'#dabeff', Tema:'#99caff' };

class TagGraph {
  constructor(canvas, tooltip, onSelect) {
    this.canvas = canvas;
    this.context = canvas.getContext('2d');
    this.tooltip = tooltip;
    this.onSelect = onSelect;
    this.nodes = [];
    this.edges = [];
    this.byId = new Map();
    this.visible = { nodes:[], edges:[], bands:[[], [], [], []], degrees:new Map(), maxDegree:1 };
    this.videos = [];
    this.focus = '';
    this.minimum = 1;
    this.mode = 'all';
    this.width = this.height = 0;
    this.stretch = 1;
    this.camera = { x:0, y:0, scale:1 };
    this.autoFit = true;
    this.points = new Map();
    this.gesture = null;
    this.hover = null;
    this.frame = 0;
    this.steps = 0;
    this.reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
    new ResizeObserver(() => this.resize()).observe(canvas);
    this.resize();

    canvas.addEventListener('wheel', (event) => {
      event.preventDefault();
      const point = this.point(event);
      const delta = event.deltaY * (event.deltaMode === 1 ? 16 : 1);
      this.zoom(Math.exp(-Math.max(-140, Math.min(140, delta)) * .0028), point);
    }, { passive:false });
    canvas.addEventListener('pointerdown', (event) => this.pointerDown(event));
    canvas.addEventListener('pointermove', (event) => this.pointerMove(event));
    canvas.addEventListener('pointerup', (event) => this.pointerEnd(event));
    canvas.addEventListener('pointercancel', (event) => this.pointerEnd(event, true));
    canvas.addEventListener('lostpointercapture', (event) => this.pointerEnd(event, true));
    canvas.addEventListener('pointerleave', () => this.clearHover());
    canvas.addEventListener('keydown', (event) => this.key(event));
  }

  setData(videos, tags) {
    if (videos.length === this.videos.length && videos.every((video, index) => video === this.videos[index])) return false;
    this.videos = videos;
    const previous = this.byId;
    this.nodes = tags.map((tag, index) => {
      const last = previous.get(tag.id);
      const angle = index * Math.PI * (3 - Math.sqrt(5));
      const distance = 44 * Math.sqrt(index);
      return {
        ...tag, index, x:last?.x ?? distance * Math.cos(angle), y:last?.y ?? distance * Math.sin(angle),
        vx:0, vy:0, pinned:last?.pinned ?? false,
        neighbors:[],
      };
    });
    this.byId = new Map(this.nodes.map((node) => [node.id, node]));
    const edges = new Map();
    const size = this.nodes.length;
    for (const video of videos) {
      const indices = Array.from(video.lookup, (id) => this.byId.get(id).index).sort((a, b) => a - b);
      for (let i = 0; i < indices.length; i++) {
        for (let j = i + 1; j < indices.length; j++) {
          const pair = indices[i] * size + indices[j];
          edges.set(pair, (edges.get(pair) || 0) + 1);
        }
      }
    }
    this.edges = Array.from(edges, ([pair, count]) => {
      const a = this.nodes[Math.floor(pair / size)];
      const b = this.nodes[pair % size];
      const edge = { a, b, count, band:count >= 15 ? 3 : count >= 5 ? 2 : count >= 2 ? 1 : 0 };
      a.neighbors.push({ node:b, count, edge });
      b.neighbors.push({ node:a, count, edge });
      return edge;
    });
    for (const edge of this.edges) {
      const strength = Math.log1p(edge.count);
      edge.pull = (.033 + .026 * strength) / Math.sqrt(Math.max(edge.a.neighbors.length, edge.b.neighbors.length));
      edge.length = 98 + 37 / strength;
    }
    this.clearHover();
    return true;
  }

  setView(focus, mode, minimum, changedData, center) {
    const changedScope = this.mode !== mode || (mode === 'near' && (this.focus !== focus || this.minimum !== minimum));
    this.focus = focus;
    this.mode = mode;
    this.minimum = minimum;
    this.clearHover();
    const central = this.byId.get(focus);
    const neighborhood = this.connections(focus);
    const subset = mode === 'near' && central ? new Set([central, ...neighborhood.map(({ node }) => node)]) : null;
    const nodes = subset ? this.nodes.filter((node) => subset.has(node)) : this.nodes;
    const edges = this.edges.filter((edge) => edge.count >= minimum && (!subset || (subset.has(edge.a) && subset.has(edge.b))));
    const bands = [[], [], [], []];
    const degrees = new Map();
    for (const edge of edges) {
      bands[edge.band].push(edge);
      degrees.set(edge.a, (degrees.get(edge.a) || 0) + 1);
      degrees.set(edge.b, (degrees.get(edge.b) || 0) + 1);
    }
    this.visible = { nodes, edges, bands, degrees, maxDegree:Math.max(1, ...degrees.values()) };
    if (changedData) {
      const warmup = this.reducedMotion.matches ? 80 : 27;
      for (let i = 0; i < warmup; i++) this.step();
      this.steps = this.reducedMotion.matches ? 0 : 68;
    }
    if (changedData || changedScope) this.fit();
    if (center && central && mode === 'all') this.locate(central);
    this.schedule();
  }

  connections(id) {
    return this.byId.get(id)?.neighbors.filter(({ count }) => count >= this.minimum) ?? [];
  }

  resize() {
    const { width, height } = this.canvas.getBoundingClientRect();
    if (!width || !height) return;
    this.dpr = Math.min(devicePixelRatio || 1, 2);
    this.canvas.width = Math.round(width * this.dpr);
    this.canvas.height = Math.round(height * this.dpr);
    const stretch = Math.max(1, Math.min(1.55, width / height * .94));
    this.camera.x = width / 2 - (this.width / 2 - this.camera.x) * stretch / this.stretch;
    this.camera.y += (height - this.height) / 2;
    this.stretch = stretch;
    this.width = width;
    this.height = height;
    if (this.autoFit) this.fit();
    this.schedule();
  }

  fit() {
    const { nodes } = this.visible;
    const pad = Math.min(165, Math.max(84, this.width * .135));
    const left = nodes.length ? Math.min(...nodes.map((node) => node.x)) : 0;
    const right = nodes.length ? Math.max(...nodes.map((node) => node.x)) : 0;
    const top = nodes.length ? Math.min(...nodes.map((node) => node.y)) : 0;
    const bottom = nodes.length ? Math.max(...nodes.map((node) => node.y)) : 0;
    const maximum = nodes.length > 1 ? 1.8 : 1.15;
    const scale = Math.max(.025, Math.min(maximum,
      (this.width - pad) / Math.max(1, (right - left) * this.stretch), (this.height - 93) / Math.max(1, bottom - top)));
    this.camera = { x:this.width / 2 - (left + right) * this.stretch * scale / 2,
      y:(this.height - 25) / 2 - (top + bottom) * scale / 2, scale };
    this.autoFit = true;
    this.clearHover();
    this.schedule();
  }

  locate(node) {
    this.autoFit = false;
    const scale = Math.max(this.camera.scale, 1.05);
    this.camera = { x:this.width / 2 - node.x * this.stretch * scale, y:this.height / 2 - node.y * scale, scale };
    this.schedule();
  }

  zoom(factor, point = { x:this.width / 2, y:this.height / 2 }, origin = point) {
    const camera = this.camera;
    const scale = Math.max(.025, Math.min(7, camera.scale * factor));
    const ratio = scale / camera.scale;
    this.camera = { x:point.x - (origin.x - camera.x) * ratio, y:point.y - (origin.y - camera.y) * ratio, scale };
    this.autoFit = false;
    this.clearHover();
    this.schedule();
  }

  step() {
    const nodes = this.nodes;
    for (let i = 0; i < nodes.length; i++) {
      const a = nodes[i];
      for (let j = i + 1; j < nodes.length; j++) {
        const b = nodes[j];
        const dx = b.x - a.x || .01;
        const dy = b.y - a.y || .01;
        const distance = dx * dx + dy * dy;
        const force = 5900 / ((distance + 170) * Math.sqrt(distance));
        a.vx -= dx * force;
        a.vy -= dy * force;
        b.vx += dx * force;
        b.vy += dy * force;
      }
    }
    for (const { a, b, length, pull } of this.edges) {
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const distance = Math.hypot(dx, dy) || 1;
      const force = (distance - length) * pull / distance;
      a.vx += dx * force;
      a.vy += dy * force;
      b.vx -= dx * force;
      b.vy -= dy * force;
    }
    for (const node of nodes) {
      if (node.pinned) {
        node.vx = node.vy = 0;
        continue;
      }
      node.vx = Math.max(-21, Math.min(21, (node.vx - node.x * .008) * .72));
      node.vy = Math.max(-21, Math.min(21, (node.vy - node.y * .008) * .72));
      node.x += node.vx;
      node.y += node.vy;
    }
  }

  schedule() {
    if (this.frame) return;
    this.frame = requestAnimationFrame(() => {
      this.frame = 0;
      if (this.steps > 0) {
        this.steps--;
        this.step();
        if (!this.steps && this.autoFit) this.fit();
        if (this.steps) this.schedule();
      }
      this.draw();
    });
  }

  screen(node) {
    const { x, y, scale } = this.camera;
    return { x:x + node.x * scale * this.stretch, y:y + node.y * scale };
  }

  radius(node) {
    const fraction = (this.visible.degrees.get(node) || 0) / this.visible.maxDegree;
    const zoom = Math.max(.75, Math.min(2.1, Math.sqrt(this.camera.scale)));
    return (3.6 + 10.4 * Math.sqrt(fraction)) * zoom;
  }

  draw() {
    const ctx = this.context;
    if (!ctx || !this.width) return;
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.clearRect(0, 0, this.width, this.height);
    const positions = new Map(this.visible.nodes.map((node) => [node, this.screen(node)]));
    const emphasis = this.hover?.node || this.byId.get(this.focus);
    const bright = emphasis ? new Set([emphasis, ...this.connections(emphasis.id).map(({ node }) => node)]) : null;
    const opacity = Math.max(.035, Math.min(.44, 130 / Math.max(1, this.visible.edges.length)));
    const edgeIsBright = (edge) => edge.a === emphasis || edge.b === emphasis || edge === this.hover?.edge;
    const segment = ({ a, b }) => {
      const from = positions.get(a), to = positions.get(b);
      ctx.moveTo(from.x, from.y);
      ctx.lineTo(to.x, to.y);
    };
    this.visible.bands.forEach((edges, band) => {
      ctx.beginPath();
      for (const edge of edges) if (!edgeIsBright(edge)) segment(edge);
      ctx.strokeStyle = 'rgba(151,196,179,' + Math.min(.62, opacity * (bright ? .46 : 1) * (1 + band * .65)) + ')';
      ctx.lineWidth = .55 + band * .27;
      ctx.stroke();
      if (!bright && !this.hover?.edge) return;
      ctx.beginPath();
      for (const edge of edges) if (edgeIsBright(edge)) segment(edge);
      ctx.strokeStyle = 'rgba(174,236,208,' + (.33 + band * .16) + ')';
      ctx.lineWidth = 1 + band * .44;
      ctx.stroke();
    });

    for (const [node, point] of positions) {
      const radius = this.radius(node);
      ctx.beginPath();
      ctx.arc(point.x, point.y, radius, 0, 2 * Math.PI);
      ctx.fillStyle = graphColors[node.grupo];
      ctx.globalAlpha = bright && !bright.has(node) ? .38 : .96;
      ctx.fill();
      if (node === emphasis || node.id === this.focus) {
        ctx.strokeStyle = '#fff4d1';
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    }
    ctx.globalAlpha = 1;
    this.drawLabels(positions, emphasis, bright);
  }

  drawLabels(positions, emphasis, bright) {
    const ctx = this.context;
    const boxes = [];
    const scale = this.camera.scale;
    const total = positions.size;
    const limit = total <= 30 || scale >= 1.45 ? total : Math.min(total, this.width > 580 ? 15 : 8);
    const candidates = new Set([emphasis, this.byId.get(this.focus), ...positions.keys()]);
    ctx.font = '600 13px system-ui, sans-serif';
    ctx.lineJoin = 'round';
    ctx.lineWidth = 3;
    ctx.strokeStyle = '#0c302a';
    for (const node of candidates) {
      if (boxes.length >= limit) break;
      const point = positions.get(node);
      if (!point || (bright && !bright.has(node) && scale < 1.45)) continue;
      const width = ctx.measureText(node.nome).width;
      if (point.x < 0 || point.x > this.width || point.y < 0 || point.y > this.height || width > this.width - 10) continue;
      const r = this.radius(node);
      const centered = Math.max(5, Math.min(this.width - width - 5, point.x - width / 2));
      const position = [
        { x:centered, y:point.y - r - 6 },
        { x:centered, y:point.y + r + 15 },
        { x:point.x + r + 6, y:point.y + 4 },
        { x:point.x - r - width - 6, y:point.y + 4 },
      ].find(({ x, y }) => x >= 5 && x + width <= this.width - 5 && y >= 16 && y <= this.height - 8 &&
        !boxes.some((box) => x < box.x + box.width + 8 && x + width + 8 > box.x && Math.abs(y - box.y) < 18));
      if (!position) continue;
      const { x, y } = position;
      boxes.push({ x, y, width });
      ctx.fillStyle = node === emphasis || node.id === this.focus ? '#fff7de' : '#dff1e8';
      ctx.strokeText(node.nome, x, y);
      ctx.fillText(node.nome, x, y);
    }
  }

  point(event) {
    const rect = this.canvas.getBoundingClientRect();
    return { x:event.clientX - rect.left, y:event.clientY - rect.top };
  }

  findNode(point) {
    let nearest = null;
    let best = Infinity;
    for (const node of this.visible.nodes) {
      const position = this.screen(node);
      const distance = Math.hypot(position.x - point.x, position.y - point.y);
      if (distance <= this.radius(node) + 5 && distance < best) {
        nearest = node;
        best = distance;
      }
    }
    return nearest;
  }

  findEdge(point) {
    const active = this.byId.get(this.focus);
    const candidates = active ? this.connections(active.id).map(({ edge }) => edge) : this.visible.edges;
    if (!active && candidates.length > 900 && this.camera.scale < 1.45) return null;
    let nearest = null;
    let best = 5;
    for (const edge of candidates) {
      const a = this.screen(edge.a), b = this.screen(edge.b);
      const dx = b.x - a.x, dy = b.y - a.y;
      const t = ((point.x - a.x) * dx + (point.y - a.y) * dy) / (dx * dx + dy * dy);
      if (!(t > 0 && t < 1)) continue;
      const distance = Math.hypot(point.x - a.x - t * dx, point.y - a.y - t * dy);
      if (distance < best) {
        nearest = edge;
        best = distance;
      }
    }
    return nearest;
  }

  showHover(point) {
    const node = this.findNode(point);
    const edge = node ? null : this.findEdge(point);
    if (!node && !edge) {
      this.clearHover();
      return;
    }
    this.hover = { node, edge };
    this.canvas.dataset.cursor = node ? 'node' : '';
    const degree = node ? this.visible.degrees.get(node) || 0 : 0;
    this.tooltip.textContent = node
      ? node.nome + ' · ' + degree + (degree === 1 ? ' conexão' : ' conexões') +
        ' · ' + node.count + (node.count === 1 ? ' publicação' : ' publicações')
      : edge.a.nome + ' + ' + edge.b.nome + ' · ' + edge.count + (edge.count === 1 ? ' publicação em comum' : ' publicações em comum');
    this.tooltip.hidden = false;
    this.tooltip.style.left = Math.max(5, Math.min(this.width - this.tooltip.offsetWidth - 5, point.x + 14)) + 'px';
    this.tooltip.style.top = Math.max(5, Math.min(this.height - this.tooltip.offsetHeight - 5, point.y + 14)) + 'px';
    this.schedule();
  }

  clearHover() {
    this.tooltip.hidden = true;
    this.canvas.dataset.cursor = this.points.size ? 'drag' : '';
    if (this.hover) {
      this.hover = null;
      this.schedule();
    }
  }

  pointerDown(event) {
    if (event.button !== 0) return;
    this.canvas.focus({ preventScroll:true });
    this.canvas.setPointerCapture(event.pointerId);
    const point = this.point(event);
    this.points.set(event.pointerId, point);
    const node = this.findNode(point);
    if (this.points.size === 1) {
      const screen = node ? this.screen(node) : point;
      this.gesture = { node, start:point, moved:false, dx:screen.x - point.x, dy:screen.y - point.y };
    } else {
      this.gesture = null;
    }
    this.clearHover();
  }

  pointerMove(event) {
    const point = this.point(event);
    const previous = this.points.get(event.pointerId);
    if (!previous) {
      if (!this.points.size && event.pointerType !== 'touch') this.showHover(point);
      return;
    }
    const other = Array.from(this.points).find(([id]) => id !== event.pointerId)?.[1];
    this.points.set(event.pointerId, point);
    if (other) {
      const center = { x:(point.x + other.x) / 2, y:(point.y + other.y) / 2 };
      const origin = { x:(previous.x + other.x) / 2, y:(previous.y + other.y) / 2 };
      const factor = Math.hypot(point.x - other.x, point.y - other.y) /
        Math.max(1, Math.hypot(previous.x - other.x, previous.y - other.y));
      this.zoom(factor || 1, center, origin);
      return;
    }
    const drag = this.gesture;
    if (!drag) return;
    if (!drag.moved && Math.hypot(point.x - drag.start.x, point.y - drag.start.y) < 4) return;
    const { x, y, scale } = this.camera;
    if (drag.node) {
      drag.node.pinned = true;
      drag.node.x = (point.x + drag.dx - x) / (scale * this.stretch);
      drag.node.y = (point.y + drag.dy - y) / scale;
    } else {
      const origin = drag.moved ? previous : drag.start;
      this.camera.x += point.x - origin.x;
      this.camera.y += point.y - origin.y;
    }
    drag.moved = true;
    this.autoFit = false;
    this.schedule();
  }

  pointerEnd(event, cancelled = false) {
    if (!this.points.delete(event.pointerId)) return;
    const drag = this.gesture;
    this.gesture = null;
    this.clearHover();
    if (cancelled || !drag) return;
    if (!drag.moved) {
      this.onSelect(drag.node?.id || '');
    } else if (drag.node && !this.reducedMotion.matches) {
      this.steps = Math.max(26, this.steps);
      this.schedule();
    }
  }

  key(event) {
    const moves = { ArrowLeft:[55, 0], ArrowRight:[-55, 0], ArrowUp:[0, 55], ArrowDown:[0, -55] };
    const move = moves[event.key];
    if (move) {
      this.camera.x += move[0];
      this.camera.y += move[1];
      this.autoFit = false;
      this.schedule();
    } else if (event.key === '+' || event.key === '=') this.zoom(1.22);
    else if (event.key === '-') this.zoom(1 / 1.22);
    else if (event.key === 'Home') this.fit();
    else if (event.key === 'Escape') this.onSelect('');
    else return;
    event.preventDefault();
  }
}
