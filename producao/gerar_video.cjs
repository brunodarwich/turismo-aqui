// Renderiza o roteiro em WebM com imagens do catálogo visual e legendas WebVTT.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { createHash } = require('node:crypto');
const { spawnSync } = require('node:child_process');
const { chromium } = require('playwright');

const root = path.resolve(__dirname, '..');
const output = path.join(root, 'entregaveis');
const manifestPath = path.join(__dirname, 'materiais.json');
const chromePath = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const { video: scenes } = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
const base = JSON.parse(fs.readFileSync(path.join(root, 'data/base.json'), 'utf8'));
const sources = new Map([...base.videos, ...base.fontes].map(item => [item.id, item]));
const assets = new Map(base.ativos.map(item => [item.id, item]));
const tokens = JSON.parse(fs.readFileSync(path.join(root, 'design-system/tokens.json'), 'utf8'));
const usedImages = [...new Set(scenes.flatMap(scene => scene.imagens))];
const usedSources = [...new Set(scenes.flatMap(scene => scene.fontes))];

function picture(filename) {
  const type = path.extname(filename).toLowerCase() === '.png' ? 'image/png' : 'image/jpeg';
  return 'data:' + type + ';base64,' + fs.readFileSync(path.join(root, filename)).toString('base64');
}

function localNarration() {
  if (process.platform !== 'win32') return { clips: [], voice: '' };
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'turismo-aqui-voz-'));
  const files = scenes.map((_, index) => path.join(temporary, 'cena-' + index + '.wav'));
  try {
    const exe = path.join(process.env.SystemRoot, 'System32/WindowsPowerShell/v1.0/powershell.exe');
    const spawned = spawnSync(exe, [
      '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'RemoteSigned',
      '-File', path.join(__dirname, 'gerar_narracao.ps1'),
      '-Roteiro', manifestPath, '-Pasta', temporary,
    ], { encoding: 'utf8', windowsHide: true });
    if (spawned.error || spawned.status !== 0) {
      throw new Error(spawned.error?.message || spawned.stderr || 'SAPI indisponível');
    }
    return { clips: files.map(file => fs.readFileSync(file).toString('base64')), voice: spawned.stdout.trim() };
  } catch (error) {
    console.warn('Narração indisponível. O vídeo manterá texto em tela, legendas e trilha.', error.message);
    return { clips: [], voice: '' };
  } finally {
    for (const file of files) {
      if (fs.existsSync(file)) fs.unlinkSync(file);
    }
    fs.rmdirSync(temporary);
  }
}

function timecode(seconds) {
  const ms = Math.round(seconds * 1000);
  return [Math.floor(ms / 3600000), Math.floor(ms / 60000) % 60, Math.floor(ms / 1000) % 60]
    .map(value => String(value).padStart(2, '0')).join(':') + '.' + String(ms % 1000).padStart(3, '0');
}

function captionLines(text) {
  const lines = [];
  let line = '';
  for (const word of text.split(' ')) {
    const candidate = line ? line + ' ' + word : word;
    if (line && candidate.length > 46) {
      lines.push(line);
      line = word;
    } else {
      line = candidate;
    }
  }
  if (lines.length === 1 && line.length < 17) {
    const words = lines[0].split(' ');
    while (words.length > 1) {
      const shortened = words.slice(0, -1).join(' ');
      const continued = words.at(-1) + ' ' + line;
      if (shortened.length < continued.length) break;
      words.pop();
      line = continued;
    }
    lines[0] = words.join(' ');
  }
  return [...lines, line];
}

function captionBlocks(sentence) {
  const lines = captionLines(sentence);
  if (lines.length <= 2) return [lines];
  const words = sentence.split(' ');
  let split = Math.ceil(words.length / 2);
  let first = captionLines(words.slice(0, split).join(' '));
  while (first.length > 2) {
    first = captionLines(words.slice(0, --split).join(' '));
  }
  return [first, ...captionBlocks(words.slice(split).join(' '))];
}

function captionsAndNotes(times, voice) {
  const captions = ['WEBVTT', ''];
  const notes = [
    '# Roteiro e storyboard do vídeo', '',
    'Vídeo em 1920 × 1080 com a identidade Turismo Aqui, composição em Canvas e trilha instrumental sintetizada no Web Audio.',
    voice ? 'Narração sintética em português do Brasil. Voz ' + voice + '.' : 'Edição com texto em tela, legendas e trilha.',
    '', '| Tempo | Imagem e movimento | Texto em tela | Texto de narração |', '| --- | --- | --- | --- |',
  ];
  let cue = 0;
  for (const [index, scene] of scenes.entries()) {
    const { start, end, captionStart, captionEnd } = times[index];
    const blocks = scene.fala.split(/(?<=[.!?]) +/).flatMap(captionBlocks);
    const total = scene.fala.length;
    let begin = captionStart;
    let covered = 0;
    for (const [blockIndex, lines] of blocks.entries()) {
      covered += lines.join(' ').length + 1;
      const until = blockIndex === blocks.length - 1
        ? captionEnd
        : captionStart + (captionEnd - captionStart) * covered / total;
      captions.push(String(++cue), timecode(begin) + ' --> ' + timecode(until), lines.join('\n'), '');
      begin = until;
    }
    notes.push('| ' + timecode(start) + '–' + timecode(end) + ' | ' + scene.visual + ' | ' +
      scene.titulo.replaceAll('\n', ' ') + ' · ' + scene.tela + ' | ' + scene.fala + ' |');
  }
  notes.push('', '## Imagens e áudio', '');
  for (const id of usedImages) {
    const asset = assets.get(id);
    const minute = timecode(asset.inicio_ms / 1000).slice(3, 8);
    notes.push('- [' + asset.titulo + ' · ' + asset.autor + ' · ' + minute + '](' + asset.url + ')');
  }
  notes.push('- Quadros com recortes editoriais para esta edição local.', '- [Marca e tokens Turismo Aqui](../design-system/index.html).');
  notes.push('', '## Fontes editoriais', '');
  for (const id of usedSources) {
    const item = sources.get(id);
    notes.push('- [' + item.titulo + '](' + item.url + ')');
  }
  notes.push('', 'Fontes de produção em `materiais.json`, `motion_guia.js`, `gerar_video.cjs` e `gerar_narracao.ps1`.', '');
  return { captions: captions.join('\n'), notes: notes.join('\n') };
}

async function render(page, pictures, brand, clips) {
  await page.addScriptTag({ path: path.join(__dirname, 'motion_guia.js') });
  return page.evaluate(async ({ scenes, pictures, brand, clips, tokens }) => {
    const canvas = document.createElement('canvas');
    canvas.width = 1920;
    canvas.height = 1080;
    document.body.style.margin = '0';
    document.body.appendChild(canvas);
    await document.fonts.ready;
    const ctx = canvas.getContext('2d', { alpha: false });
    const narrationDelay = 0.76;
    const audio = new AudioContext();
    const destination = audio.createMediaStreamDestination();
    const mastered = audio.createDynamicsCompressor();
    mastered.connect(destination);
    const filter = audio.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.value = 1450;
    filter.connect(mastered);

    async function loadImage(url) {
      const image = new Image();
      image.src = url;
      await image.decode();
      return image;
    }

    const images = Object.fromEntries(await Promise.all(Object.entries(pictures).map(async ([id, url]) => [id, await loadImage(url)])));
    const drawMotion = createGuideMotion(ctx, canvas, images, await loadImage(brand), tokens);
    const voice = await Promise.all(clips.map(clip => {
      const bytes = Uint8Array.from(atob(clip), char => char.charCodeAt(0));
      return audio.decodeAudioData(bytes.buffer);
    }));
    let duration = 0;
    const times = scenes.map((scene, index) => {
      const speaking = voice[index]?.duration || 0;
      const start = duration;
      duration += Math.ceil(Math.max(7.0, (speaking || scene.fala.length / 14) + 1.85) * 10) / 10;
      return {
        start, end: duration,
        captionStart: start + (speaking ? narrationDelay : 0.9),
        captionEnd: speaking ? start + narrationDelay + speaking + 0.18 : duration - 0.3,
      };
    });

    function draw(seconds) {
      const index = times.findIndex(time => time.end > seconds);
      const sceneIndex = index < 0 ? scenes.length - 1 : index;
      const time = times[sceneIndex];
      drawMotion(scenes[sceneIndex], seconds - time.start, time.end - time.start, sceneIndex);
    }

    function score(begin) {
      const chords = [[130.81, 196.00, 261.63], [110.00, 164.81, 261.63], [87.31, 130.81, 220.00], [98.00, 146.83, 196.00]];
      for (let elapsed = 0; elapsed < duration - 0.4; elapsed += 4) {
        const notes = chords[Math.floor(elapsed / 4) % chords.length];
        const start = begin + elapsed;
        const length = Math.min(4.6, duration - elapsed);
        for (const [index, frequency] of notes.entries()) {
          const oscillator = audio.createOscillator();
          oscillator.type = index ? 'triangle' : 'sine';
          oscillator.frequency.value = frequency;
          const envelope = audio.createGain();
          envelope.gain.setValueAtTime(0, start);
          envelope.gain.linearRampToValueAtTime(index ? 0.018 : 0.044, start + 0.35);
          envelope.gain.linearRampToValueAtTime(0, start + length);
          oscillator.connect(envelope).connect(filter);
          oscillator.start(start);
          oscillator.stop(start + length);
        }
      }
    }

    draw(1.9);
    const poster = canvas.toDataURL('image/png').split(',')[1];
    const thumbnail = document.createElement('canvas');
    thumbnail.width = 640;
    thumbnail.height = 320;
    const thumb = thumbnail.getContext('2d');
    thumb.drawImage(canvas, 0, 60, 1920, 960, 0, 0, 640, 320);
    thumb.beginPath();
    thumb.arc(533, 195, 34, 0, 2 * Math.PI);
    thumb.fillStyle = tokens.color['teal-active'];
    thumb.fill();
    thumb.strokeStyle = tokens.color.white;
    thumb.lineWidth = 2;
    thumb.stroke();
    thumb.beginPath();
    thumb.moveTo(524, 181);
    thumb.lineTo(546, 195);
    thumb.lineTo(524, 209);
    thumb.closePath();
    thumb.fillStyle = tokens.color.white;
    thumb.fill();

    await audio.resume();
    draw(0);
    const stream = canvas.captureStream(25);
    for (const track of destination.stream.getAudioTracks()) stream.addTrack(track);
    const formats = ['video/webm;codecs=vp8,opus', 'video/webm;codecs=vp9,opus', 'video/webm'];
    const mimeType = formats.find(value => MediaRecorder.isTypeSupported(value));
    if (!mimeType) throw new Error('WebM não suportado pelo navegador.');
    const chunks = [];
    const recorder = new MediaRecorder(stream, { mimeType, videoBitsPerSecond: 4800000, audioBitsPerSecond: 128000 });
    const recorded = new Promise((resolve, reject) => {
      recorder.onstop = resolve;
      recorder.onerror = event => reject(event.error);
      recorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
    });
    recorder.start();
    const beginAudio = audio.currentTime;
    voice.forEach((clip, index) => {
      const track = audio.createBufferSource();
      track.buffer = clip;
      track.connect(mastered);
      track.start(beginAudio + times[index].start + narrationDelay);
    });
    score(beginAudio);
    const beginVideo = performance.now();
    await new Promise(resolve => {
      function frame(now) {
        const seconds = (now - beginVideo) / 1000;
        draw(Math.min(seconds, duration));
        if (seconds < duration) requestAnimationFrame(frame);
        else resolve();
      }
      requestAnimationFrame(frame);
    });
    recorder.stop();
    await recorded;
    await audio.close();

    const blob = new Blob(chunks, { type: 'video/webm' });
    if (blob.size < 10000) throw new Error('A captura do vídeo não produziu quadros e áudio suficientes.');
    const reader = new FileReader();
    const webm = await new Promise((resolve, reject) => {
      reader.onload = () => resolve(reader.result.split(',')[1]);
      reader.onerror = () => reject(reader.error);
      reader.readAsDataURL(blob);
    });
    return { times, webm, poster, thumbnail: thumbnail.toDataURL('image/webp', 0.93).split(',')[1] };
  }, { scenes, pictures, brand, clips, tokens });
}

function versionLinks(files) {
  const entries = ['index.html', 'app/index.html', 'site/blog.html'];
  for (const entry of entries) {
    const file = path.join(root, entry);
    const original = fs.readFileSync(file, 'utf8');
    const html = original.replace(/((?:src|href)="(?:\.\.\/)?entregaveis\/)(guia-alter\.webm|guia-alter\.vtt|video-preview\.png|central\/video\.webp)(?:\?v=[a-f0-9]+)?"/g,
      (_, prefix, name) => prefix + name + '?v=' + createHash('sha256').update(files[name]).digest('hex').slice(0, 12) + '"');
    if (html !== original) fs.writeFileSync(file, html, 'utf8');
  }
}

async function main() {
  const pictures = Object.fromEntries(usedImages.map(id => [id, picture(assets.get(id).caminho)]));
  for (const id of usedSources) {
    if (!sources.get(id)?.url) throw new Error('Fonte do roteiro indisponível: ' + id);
  }
  const narration = localNarration();
  const executablePath = process.env.TURISMO_BROWSER_EXECUTABLE || (fs.existsSync(chromePath) ? chromePath : undefined);
  const browser = await chromium.launch({
    executablePath, headless: true, args: ['--autoplay-policy=no-user-gesture-required'],
  });
  try {
    const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
    const result = await render(page, pictures, picture('design-system/assets/turismo-aqui.png'), narration.clips);
    const encoded = Buffer.from(result.webm, 'base64');
    if (encoded.length < 10000 || encoded.readUInt32BE(0) !== 0x1a45dfa3) {
      throw new Error('O navegador não retornou um arquivo WebM válido.');
    }
    const companions = captionsAndNotes(result.times, narration.voice);
    const files = {
      'guia-alter.webm': encoded,
      'guia-alter.vtt': Buffer.from(companions.captions, 'utf8'),
      'video-preview.png': Buffer.from(result.poster, 'base64'),
      'central/video.webp': Buffer.from(result.thumbnail, 'base64'),
    };
    for (const [name, data] of Object.entries(files)) fs.writeFileSync(path.join(output, name), data);
    fs.writeFileSync(path.join(__dirname, 'roteiro-video.md'), companions.notes, 'utf8');
    versionLinks(files);
    console.log('Vídeo de ' + result.times.at(-1).end.toFixed(1) + ' s, legendas, prévia e storyboard atualizados.');
    if (narration.voice) console.log('Narração: ' + narration.voice);
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
