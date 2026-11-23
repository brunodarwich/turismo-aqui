// Reproduz o WebM inteiro no Chromium e valida a trilha, as cenas e as legendas.
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

const output = path.resolve(__dirname, '../entregaveis');
const chromePath = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const { video: scenes } = JSON.parse(fs.readFileSync(path.join(__dirname, 'materiais.json'), 'utf8'));
const notes = fs.readFileSync(path.join(__dirname, 'roteiro-video.md'), 'utf8');

function seconds(time) {
  const [hours, minutes, last] = time.split(':').map(Number);
  return hours * 3600 + minutes * 60 + last;
}

async function main() {
  const planned = [...notes.matchAll(/^\| (\d\d:\d\d:\d\d\.\d{3})–(\d\d:\d\d:\d\d\.\d{3}) \|/gm)]
    .map(row => [seconds(row[1]), seconds(row[2])]);
  if (planned.length !== scenes.length) throw new Error('Roteiro e manifesto divergentes.');
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.TURISMO_BROWSER_EXECUTABLE || (fs.existsSync(chromePath) ? chromePath : undefined),
    args: ['--autoplay-policy=no-user-gesture-required'],
  });
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
    await page.setContent('<video playsinline></video>');
    const result = await page.evaluate(async ({ movie, captions, planned }) => {
      const video = document.querySelector('video');
      const bytes = Uint8Array.from(atob(movie), letter => letter.charCodeAt(0));
      const track = document.createElement('track');
      track.kind = 'subtitles';
      track.srclang = 'pt-BR';
      track.label = 'Português (Brasil)';

      function expect(target, event, error, timeout) {
        return new Promise((resolve, reject) => {
          const timer = setTimeout(() => reject(new Error(error)), timeout);
          target.addEventListener(event, () => { clearTimeout(timer); resolve(); }, { once: true });
          target.addEventListener('error', () => { clearTimeout(timer); reject(new Error(error)); }, { once: true });
        });
      }

      const loaded = expect(video, 'loadeddata', 'Falha ao decodificar o vídeo.', 10000);
      const loadedTrack = expect(track, 'load', 'Falha ao ler as legendas.', 10000);
      track.src = URL.createObjectURL(new Blob([captions], { type: 'text/vtt' }));
      video.append(track);
      track.track.mode = 'hidden';
      video.src = URL.createObjectURL(new Blob([bytes], { type: 'video/webm' }));
      await Promise.all([loaded, loadedTrack]);
      const cues = [...track.track.cues];
      const validCues = cues.every((cue, index) => {
        const lines = cue.text.split('\n');
        return lines.length <= 2 && lines.every(line => line.length > 0 && line.length <= 46) &&
          cue.endTime - cue.startTime >= 1 && (!index || cues[index - 1].endTime <= cue.startTime);
      });
      const captionsPerScene = planned.map(([start, end]) => cues.filter(cue => cue.startTime >= start && cue.endTime <= end).length);

      const sheet = document.createElement('canvas');
      sheet.width = 1536;
      sheet.height = 432;
      const preview = sheet.getContext('2d');
      preview.fillStyle = '#eaf2ef';
      preview.fillRect(0, 0, sheet.width, sheet.height);
      const inspected = new Set();
      const cueFrames = new Set();
      function frame(now, metadata) {
        const time = metadata.mediaTime;
        planned.forEach(([start, end], index) => {
          if (!inspected.has(index) && time >= start + 2.1 && time < end) {
            preview.drawImage(video, (index % 4) * 384, Math.floor(index / 4) * 216, 384, 216);
            inspected.add(index);
          }
        });
        cues.forEach((cue, index) => {
          if (time >= cue.startTime && time <= cue.endTime) cueFrames.add(index);
        });
        if (!video.ended) video.requestVideoFrameCallback(frame);
      }
      video.requestVideoFrameCallback(frame);
      const captured = video.captureStream();
      const ended = expect(video, 'ended', 'Reprodução incompleta após 70 s.', 70000);
      video.playbackRate = 2;
      await video.play();
      const tracks = captured.getAudioTracks().length;
      const audio = new AudioContext();
      const analyser = audio.createAnalyser();
      const samples = new Float32Array(analyser.fftSize);
      let peak = 0;
      if (tracks) audio.createMediaStreamSource(captured).connect(analyser);
      await audio.resume();
      const meter = setInterval(() => {
        analyser.getFloatTimeDomainData(samples);
        peak = Math.max(peak, ...samples.map(Math.abs));
      }, 120);
      try { await ended; } finally { clearInterval(meter); await audio.close(); }
      return {
        width: video.videoWidth, height: video.videoHeight, duration: video.currentTime,
        cues: cues.length, captionsPerScene, validCues, scenesDecoded: inspected.size,
        captionsDecoded: cueFrames.size, frames: video.getVideoPlaybackQuality().totalVideoFrames,
        audioTracks: tracks, audioPeak: peak, sheet: sheet.toDataURL('image/webp', 0.93).split(',')[1],
      };
    }, {
      movie: fs.readFileSync(path.join(output, 'guia-alter.webm')).toString('base64'),
      captions: fs.readFileSync(path.join(output, 'guia-alter.vtt'), 'utf8'),
      planned,
    });
    const { sheet, ...metrics } = result;
    const expectedDuration = planned.at(-1)[1];
    const valid = metrics.width === 1920 && metrics.height === 1080 &&
      Math.abs(metrics.duration - expectedDuration) < 0.4 &&
      metrics.validCues && metrics.captionsPerScene.every(Boolean) &&
      metrics.captionsDecoded === metrics.cues && metrics.scenesDecoded === scenes.length &&
      metrics.frames >= expectedDuration * 15 && metrics.audioTracks === 1 && metrics.audioPeak > 0.01;
    if (!valid) throw new Error('A verificação do vídeo falhou: ' + JSON.stringify(metrics));
    if (process.env.TURISMO_VIDEO_REVIEW_PATH) {
      fs.writeFileSync(process.env.TURISMO_VIDEO_REVIEW_PATH, Buffer.from(sheet, 'base64'));
    }
    console.log(JSON.stringify(metrics));
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
