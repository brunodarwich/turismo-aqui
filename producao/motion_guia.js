/* Desenha cenas em coordenadas de 1280 × 720, escaladas para a resolução do vídeo. */
function createGuideMotion(ctx, canvas, images, logo, tokens) {
  'use strict';
  const color = tokens.color;
  const WIDTH = 1280;
  const HEIGHT = 720;
  const display = tokens.font.display;
  const sans = tokens.font.ui;
  const crops = {
    'quadro-ilha-do-amor-cheia': [0, 0.12, 1, 0.70],
    'quadro-canoa-caranazal': [0, 0, 1, 0.80],
    'quadro-ponta-pedras': [0.10, 0.17, 0.82, 0.59],
  };
  const clamp = value => Math.max(0, Math.min(1, value));
  const ease = (time, delay, duration) => 1 - (1 - clamp((time - delay) / duration)) ** 3;
  const alpha = (hex, opacity) => hex + Math.round(255 * opacity).toString(16).padStart(2, '0');

  function box(x, y, w, h, fill, radius = 0) {
    ctx.fillStyle = fill;
    if (!radius) {
      ctx.fillRect(x, y, w, h);
      return;
    }
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, radius);
    ctx.fill();
  }

  function text(value, x, y, width, size, fill, { serif = false, emphasis = false, line = 1.08 } = {}) {
    ctx.fillStyle = fill;
    ctx.textBaseline = 'top';
    const font = serif ? display : sans;
    const weight = emphasis ? 650 : 400;
    ctx.font = weight + ' ' + size + 'px ' + font;
    const lines = value.split('\n').flatMap(paragraph => {
      const rows = [];
      let row = '';
      for (const word of paragraph.split(' ')) {
        const next = row ? row + ' ' + word : word;
        if (row && ctx.measureText(next).width > width) {
          rows.push(row);
          row = word;
        } else {
          row = next;
        }
      }
      rows.push(row);
      return rows;
    });
    lines.forEach((row, index) => ctx.fillText(row, x, y + index * size * line));
  }

  function appear(time, delay, draw, amount = 20) {
    const stage = ease(time, delay, 0.63);
    if (!stage) return;
    ctx.save();
    ctx.globalAlpha = stage;
    ctx.translate(0, (1 - stage) * amount);
    draw();
    ctx.restore();
  }

  function photo(id, x, y, width, height, options = {}) {
    const { radius = 0, xFocus = 0.5, yFocus = 0.5, zoom = 0, reveal = 1, edge = 'right' } = options;
    if (reveal <= 0) return;
    const image = images[id];
    const [cx, cy, cw, ch] = crops[id] || [0, 0, 1, 1];
    const aspect = (cw * image.width) / (ch * image.height);
    const fittedWidth = Math.max(width, height * aspect) * (1 + zoom);
    const fittedHeight = fittedWidth / aspect;
    ctx.save();
    ctx.beginPath();
    ctx.rect(edge === 'left' ? x + width * (1 - reveal) : x, y, width * reveal, height);
    ctx.clip();
    ctx.beginPath();
    ctx.roundRect(x, y, width, height, radius);
    ctx.clip();
    ctx.drawImage(image, cx * image.width, cy * image.height, cw * image.width, ch * image.height,
      x + (width - fittedWidth) * xFocus, y + (height - fittedHeight) * yFocus, fittedWidth, fittedHeight);
    ctx.restore();
  }

  function brand(x, y) {
    box(x, y, 106, 113, color.white, 14);
    ctx.drawImage(logo, x + 15, y + 15, 76, 76 * logo.height / logo.width);
  }

  function photoLabel(label, x, y, width, shade = color['teal-active'], ink = color.white) {
    box(x, y, width, 40, shade, 8);
    text(label, x + 12, y + 8, width - 24, 20, ink, { emphasis: true });
  }

  function opening(scene, t, progress) {
    photo(scene.imagens[0], 0, 0, WIDTH, HEIGHT, { yFocus: 0.56, zoom: 0.012 + progress * 0.045 });
    const gradient = ctx.createLinearGradient(0, 0, WIDTH, 0);
    gradient.addColorStop(0, alpha(color.ink, 0.95));
    gradient.addColorStop(0.45, alpha(color.ink, 0.73));
    gradient.addColorStop(0.8, alpha(color.ink, 0.12));
    gradient.addColorStop(1, alpha(color.ink, 0));
    box(0, 0, WIDTH, HEIGHT, gradient);
    appear(t, 0.10, () => box(65, 230, 78, 5, color.lime), 0);
    appear(t, 0.18, () => text(scene.rotulo.toUpperCase(), 65, 252, 720, 21, color.lime, { emphasis: true }));
    appear(t, 0.28, () => text(scene.titulo, 61, 303, 940, 112, color.white, { serif: true }));
    appear(t, 0.48, () => text(scene.tela, 69, 430, 620, 38, color.white, { serif: true }));
    appear(t, 0.44, () => brand(1108, 61), 9);
  }

  function waters(scene, t, progress) {
    box(0, 0, WIDTH, HEIGHT, color.canvas);
    box(0, 0, WIDTH, 164, color.tint);
    appear(t, 0.13, () => text(scene.tela.toUpperCase(), 64, 47, 920, 19, color['teal-active'], { emphasis: true }));
    appear(t, 0.20, () => text(scene.titulo, 62, 79, 1160, 66, color.ink, { serif: true }));
    for (const [index, id] of scene.imagens.entries()) {
      const x = 64 + 588 * index;
      const delay = 0.16 + index * 0.19;
      photo(id, x, 191, 564, 376, {
        radius: 19, zoom: progress * 0.035, yFocus: 0.56,
        reveal: ease(t, delay, 0.84), edge: index ? 'left' : 'right',
      });
      appear(t, delay + 0.4, () => photoLabel(scene.rotulos[index], x + 18, 507, index ? 214 : 154,
        index ? color['lime-tint'] : color['teal-active'], index ? color.ink : color.white), 8);
    }
  }

  function crossing(scene, t, progress) {
    box(0, 0, WIDTH, HEIGHT, color.tint);
    photo(scene.imagens[0], 480, 0, 800, HEIGHT, {
      xFocus: 0.38, yFocus: 0.55, zoom: 0.02 + progress * 0.035, reveal: ease(t, 0.07, 0.85), edge: 'left',
    });
    appear(t, 0.19, () => {
      box(32, 147, 576, 376, color.canvas, 24);
      box(65, 174, 57, 5, color.lime);
      text(scene.rotulo.toUpperCase(), 65, 201, 498, 20, color['teal-active'], { emphasis: true });
    }, 36);
    appear(t, 0.36, () => text(scene.titulo, 63, 252, 532, 63, color.ink, { serif: true, line: 1.05 }));
    appear(t, 0.54, () => text(scene.tela, 65, 414, 494, 26, color['teal-active'], { emphasis: true }), 12);
  }

  function landscapes(scene, t, progress) {
    box(0, 0, WIDTH, HEIGHT, color['teal-active']);
    appear(t, 0.17, () => text(scene.titulo, 62, 57, 1140, 71, color.white, { serif: true }));
    const panels = [[64, 711, 0.16], [796, 420, 0.43]];
    for (const [index, [x, width, delay]] of panels.entries()) {
      photo(scene.imagens[index], x, 153, width, 428, {
        radius: 20, reveal: ease(t, delay, 0.76), edge: index ? 'left' : 'right',
        xFocus: index ? 0.50 : 0.46, yFocus: 0.48, zoom: progress * 0.045,
      });
      appear(t, delay + 0.48, () => photoLabel(scene.rotulos[index], x + 17, 521, 224,
        color.canvas, color.ink), 8);
    }
  }

  function culture(scene, t, progress) {
    box(0, 0, WIDTH, HEIGHT, color.canvas);
    photo(scene.imagens[0], 0, 0, 696, HEIGHT, {
      xFocus: 0.55, zoom: 0.025 + 0.035 * progress, reveal: ease(t, 0.06, 0.70),
    });
    appear(t, 0.28, () => photoLabel('Busca dos mastros', 52, 551, 204), 10);
    appear(t, 0.30, () => text(scene.rotulo.toUpperCase(), 738, 80, 495, 19, color['teal-active'], { emphasis: true }));
    appear(t, 0.38, () => text(scene.titulo, 733, 122, 490, 61, color.ink, { serif: true }));
    appear(t, 0.55, () => text(scene.tela, 738, 210, 452, 28, color.muted));
    photo(scene.imagens[1], 738, 299, 478, 280, {
      radius: 18, reveal: ease(t, 0.52, 0.78), edge: 'left', zoom: 0.025 * progress,
    });
  }

  function itinerary(scene, t, progress) {
    box(0, 0, WIDTH, HEIGHT, color.canvas);
    box(0, 0, WIDTH, 253, color.tint);
    appear(t, 0.17, () => text(scene.titulo, 62, 63, 1136, 79, color.ink, { serif: true }));
    appear(t, 0.33, () => text(scene.tela, 67, 161, 930, 30, color['teal-active']));
    for (const [index, id] of scene.imagens.entries()) {
      const x = 64 + 392 * index;
      appear(t, 0.22 + index * 0.53, () => {
        box(x, 220, 368, 354, color.white, 20);
        photo(id, x, 220, 368, 243, { radius: 20, zoom: 0.03 * progress });
        text('DIA ' + (index + 1), x + 20, 476, 322, 17, color['teal-active'], { emphasis: true });
        text(scene.rotulos[index], x + 19, 505, 331, 32, color.ink, { serif: true });
      }, 39);
    }
  }

  function closing(scene, t, progress) {
    box(0, 0, WIDTH, HEIGHT, color['teal-active']);
    photo(scene.imagens[0], 0, 0, WIDTH, HEIGHT, { xFocus: 0.42, zoom: 0.03 + progress * 0.05 });
    appear(t, 0.16, () => {
      box(700, 58, 515, 548, color.canvas, 26);
      box(736, 212, 65, 5, color.lime);
      brand(732, 82);
    }, 43);
    appear(t, 0.38, () => text(scene.titulo, 733, 250, 453, 63, color.ink, { serif: true }));
    appear(t, 0.55, () => text(scene.tela, 736, 421, 410, 30, color['teal-active'], { line: 1.2 }));
  }

  const renderers = {
    abertura: opening, aguas: waters, catraia: crossing, paisagens: landscapes,
    saire: culture, roteiro: itinerary, fecho: closing,
  };

  return function draw(scene, time, length, index) {
    ctx.setTransform(canvas.width / WIDTH, 0, 0, canvas.height / HEIGHT, 0, 0);
    box(0, 0, WIDTH, HEIGHT, color['teal-active']);
    renderers[scene.layout](scene, time, clamp(time / length));
    if (index > 0 && time < 0.42) {
      const edge = WIDTH * ease(time, 0, 0.42);
      box(edge, 0, WIDTH - edge, HEIGHT, color['teal-active']);
      box(edge, 0, Math.min(7, WIDTH - edge), HEIGHT, color.lime);
    }
  };
}
