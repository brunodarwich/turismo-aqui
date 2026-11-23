"""Prepara candidatos a partir de vídeos do acervo para revisão visual."""

import argparse
import hashlib
import json
import math
import re
import sys
import tempfile
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError


VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}")
CHANNEL_ID = "UC-ZHb_OxZfMI33dMiOSUneQ"
SOURCE_EXTENSIONS = (".mp4", ".webm", ".mkv", ".mov", ".m4v")
SHEET_PAGE_SIZE = 12
DEFAULT_SAMPLES = 36
SCHEMA_VERSION = 1


def load_ready(directory, requested_samples):
    manifest = directory / "candidatos.json"
    if not manifest.is_file():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        files = [frame["file"] for frame in data["frames"]] + data["contact_sheets"]
        if (
            data["schema"] == SCHEMA_VERSION
            and data["requested_samples"] >= requested_samples
            and data["frames"]
            and all((directory / name).is_file() for name in files)
        ):
            return data
    except (KeyError, TypeError, ValueError, OSError):
        pass
    return None


def source_path(cache, video_id, media_directory):
    sources = cache / "sources"
    fallback = sources / "720p"
    for directory in (media_directory, sources, fallback):
        if directory is None:
            continue
        for extension in SOURCE_EXTENSIONS:
            path = directory / (video_id + extension)
            if path.is_file() and path.stat().st_size:
                return path, directory != media_directory

    def check_channel(info, *, incomplete):
        if info.get("id") and info["id"] != video_id:
            return "o ID retornado não coincide com o vídeo solicitado"
        channel_id = info.get("channel_id")
        if channel_id != CHANNEL_ID and (channel_id or not incomplete):
            return "o vídeo retornado não pertence ao canal Turismo Aqui"
        return None

    options = {
        "format": (
            "bv[vcodec^=avc][height=1080][fps<=30]/bv[vcodec^=avc][height=1080]"
            "/bv[height<=1080]/b[height<=1080]/bv/b"
        ),
        "noplaylist": True,
        "match_filter": check_channel,
        "js_runtimes": {"node": {}},
        "socket_timeout": 20,
        "retries": 2,
        "fragment_retries": 2,
        "concurrent_fragment_downloads": 2,
        "noprogress": True,
        "overwrites": False,
        "updatetime": False,
    }
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        path = download_source(url, sources, options)
    except DownloadError as error:
        if "HTTP Error 403" not in str(error):
            raise
        # The public video can remain accessible through a separate encoded format.
        path = download_source(url, fallback, options | {"format": "bv[height<=720]/b[height<=720]"})
    return path, True


def download_source(url, directory, options):
    directory.mkdir(parents=True, exist_ok=True)
    with YoutubeDL(options | {"outtmpl": str(directory / "%(id)s.%(ext)s")}) as downloader:
        info = downloader.extract_info(url, download=True)
        if not info:
            raise ValueError("a fonte não confirmou o vídeo e o canal solicitados")
        path = Path(downloader.prepare_filename(info))
    if not path.is_file() or not path.stat().st_size:
        raise ValueError("o download não produziu um arquivo de vídeo")
    return path


def measure(frame):
    width = min(frame.width, 320)
    height = max(8, round(frame.height * width / frame.width))
    gray = frame.reformat(width=width, height=height, format="gray").to_ndarray()
    gray = gray.astype(np.float32)
    center = gray[1:-1, 1:-1]
    laplacian = gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:] - 4 * center
    sharpness = float(laplacian.var())
    brightness = float(gray.mean())
    contrast = float(gray.std())
    tiny = Image.fromarray(gray.astype(np.uint8)).resize((9, 8), Image.Resampling.BILINEAR)
    values = np.asarray(tiny)
    signature = int.from_bytes(np.packbits(values[:, 1:] > values[:, :-1]).tobytes(), "big")
    near_black = float((gray < 18).mean())
    near_white = float((gray > 242).mean())
    score = math.log1p(sharpness) + 0.018 * min(contrast, 60) - 3 * max(near_black, near_white)
    return score, signature, sharpness, brightness, contrast


def cut_positions(source, duration, origin, slots):
    strongest = {}
    previous = None
    with av.open(str(source)) as container:
        stream = container.streams.video[0]
        stream.codec_context.skip_frame = "NONKEY"
        for frame in container.decode(stream):
            if frame.pts is None:
                continue
            time = float(frame.pts * frame.time_base) - origin
            gray = frame.reformat(width=96, height=54, format="gray").to_ndarray().astype(np.int16)
            if previous is not None and 0 < time < duration and gray.std() >= 12:
                change = float(np.abs(gray - previous).mean()) / 255
                slot = min(slots - 1, int(slots * time / duration))
                if change >= 0.13 and change > strongest.get(slot, (0, 0))[0]:
                    strongest[slot] = (change, time)
            previous = gray
    return [time for _, time in sorted(strongest.values(), reverse=True)]


def sample_positions(source, duration, origin, samples, scene_scan):
    # Leave a small margin around the first and last frames.
    margin = min(1.0, duration * 0.03)
    span = duration - 2 * margin
    uniform = [margin + span * (index + 0.5) / samples for index in range(samples)]
    if not scene_scan:
        return uniform
    cuts = cut_positions(source, duration, origin, samples // 3)
    anchors = samples - len(cuts)
    positions = [margin + span * (index + 0.5) / anchors for index in range(anchors)]
    min_gap = min(0.5, span / (2 * samples))
    for time in cuts + uniform:
        if len(positions) >= samples:
            break
        if all(abs(time - existing) >= min_gap for existing in positions):
            positions.append(time)
    return sorted(positions)


def windows(container, stream, duration, origin, positions):
    half_width = min(0.4, duration / len(positions) * 0.42)
    time_base = float(stream.time_base)
    cadence = half_width / 2
    for index, target in enumerate(positions):
        start = max(0, target - half_width)
        end = min(duration, target + half_width)
        container.seek(int((origin + start) / time_base), stream=stream, backward=True)
        next_sample = start
        for frame in container.decode(stream):
            if frame.pts is None:
                continue
            timestamp = float(frame.pts * frame.time_base) - origin
            if timestamp < start:
                continue
            if timestamp > end:
                # Very short clips may not have an exact match in narrow windows.
                if next_sample == start and timestamp < duration:
                    yield index, timestamp, frame
                break
            if timestamp >= next_sample:
                yield index, timestamp, frame
                next_sample = timestamp + cadence


def timestamp_label(milliseconds):
    seconds, fraction = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}.{fraction:03}"


def save_frame(directory, number, candidate):
    _, signature, sharpness, brightness, contrast, timestamp, frame = candidate
    picture = frame.to_image()
    rotation = getattr(frame, "rotation", 0) or 0
    if rotation:
        picture = picture.rotate(rotation, expand=True)
    candidate_id = f"C{number:02}"
    filename = candidate_id + ".jpg"
    path = directory / filename
    picture.save(path, quality=91)
    with path.open("rb") as contents:
        checksum = hashlib.file_digest(contents, "sha256").hexdigest()
    return {
        "candidate_id": candidate_id,
        "file": filename,
        "timestamp_ms": round(timestamp * 1000),
        "width": picture.width,
        "height": picture.height,
        "sha256": checksum,
        "sharpness": round(sharpness, 2),
        "brightness": round(brightness, 2),
        "contrast": round(contrast, 2),
        "visual_hash": f"{signature:016x}",
    }


def make_contact_sheets(directory, frames):
    columns = 3
    cell_width, cell_height = 360, 234
    font = ImageFont.load_default(size=16)
    sheets = []
    for page, offset in enumerate(range(0, len(frames), SHEET_PAGE_SIZE), start=1):
        group = frames[offset:offset + SHEET_PAGE_SIZE]
        rows = math.ceil(len(group) / columns)
        sheet = Image.new("RGB", (columns * cell_width, rows * cell_height), "#20252a")
        draw = ImageDraw.Draw(sheet)
        for index, frame in enumerate(group):
            row, column = divmod(index, columns)
            x, y = column * cell_width, row * cell_height
            with Image.open(directory / frame["file"]) as picture:
                picture.thumbnail((cell_width - 12, cell_height - 33))
                sheet.paste(picture, (x + (cell_width - picture.width) // 2, y + 4))
            label = f'{frame["candidate_id"]}   {timestamp_label(frame["timestamp_ms"])}'
            draw.text((x + 8, y + cell_height - 25), label, fill="#ffffff", font=font)
        name = f"folha-{page:02}.jpg"
        sheet.save(directory / name, quality=88)
        sheets.append(name)
    return sheets


def extract(source, directory, samples, scene_scan):
    frames = []
    signatures = []
    timestamps = set()
    best = None
    current_index = None
    with av.open(str(source)) as container:
        if not container.streams.video:
            raise ValueError("arquivo sem faixa de vídeo")
        stream = container.streams.video[0]
        time_base = float(stream.time_base)
        stream.codec_context.thread_count = 2
        origin = float(stream.start_time or 0) * time_base
        duration = stream.duration * time_base if stream.duration else (
            (container.duration or 0) / av.time_base
        )
        if duration <= 0:
            raise ValueError("não foi possível determinar a duração do vídeo")
        positions = sample_positions(source, duration, origin, samples, scene_scan)
        for index, timestamp, frame in windows(container, stream, duration, origin, positions):
            if index != current_index and best is not None:
                saved = save_frame(directory, len(frames) + 1, best)
                frames.append(saved)
                signatures.append(best[1])
                timestamps.add(saved["timestamp_ms"])
                best = None
            current_index = index
            if round(timestamp * 1000) in timestamps:
                continue
            score, signature, sharpness, brightness, contrast = measure(frame)
            if any((signature ^ previous).bit_count() <= 4 for previous in signatures):
                score -= 2
            if best is None or score > best[0]:
                best = (score, signature, sharpness, brightness, contrast, timestamp, frame)
        if best is not None:
            frames.append(save_frame(directory, len(frames) + 1, best))
    if not frames:
        raise ValueError("nenhum quadro decodificado")
    return round(duration * 1000), frames


def capture(cache, video_id, samples, keep_source, media_directory, scene_scan):
    directory = cache / video_id
    if existing := load_ready(directory, samples):
        return len(existing["frames"]), "já preparado"
    source, managed = source_path(cache, video_id, media_directory)
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="etapa-", dir=directory) as workspace:
        stage = Path(workspace)
        duration, frames = extract(source, stage, samples, scene_scan)
        data = {
            "schema": SCHEMA_VERSION,
            "video_id": video_id,
            "video_url": f"https://www.youtube.com/watch?v={video_id}",
            "duration_ms": duration,
            "source": source.name,
            "strategy": "uniforme e mudanças de cena" if scene_scan else "uniforme",
            "requested_samples": samples,
            "contact_sheets": make_contact_sheets(stage, frames),
            "frames": frames,
        }
        manifest = stage / "candidatos.json"
        manifest.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        for path in stage.iterdir():
            if path != manifest:
                path.replace(directory / path.name)
        manifest.replace(directory / manifest.name)
    if managed and not keep_source:
        source.unlink()
    return len(frames), "preparado"


def pendentes(cache, amostras):
    from revisar_transcricoes import ACERVO, catalogo

    revisoes = ACERVO / "revisoes-visuais"
    ids = []
    for video in catalogo():
        video_id = video["id"]
        if not (revisoes / f"{video_id}.json").is_file() and not load_ready(cache / video_id, amostras):
            ids.append(video_id)
    return ids


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video_ids", nargs="*", help="IDs do YouTube")
    parser.add_argument("--ids-file", type=Path, help="IDs do YouTube separados por espaço ou linha")
    parser.add_argument("--pendentes", action="store_true", help="prepara publicações ainda sem revisão nem candidatos")
    parser.add_argument("--limite", type=int, help="limita a quantidade de publicações de --pendentes")
    parser.add_argument(
        "--cache", type=Path, default=Path(tempfile.gettempdir()) / "turismo-aqui-quadros"
    )
    parser.add_argument("--media-dir", type=Path, help="arquivos locais nomeados pelo ID do YouTube")
    parser.add_argument("--samples", type=int, default=DEFAULT_SAMPLES, help="janelas de amostragem por vídeo")
    parser.add_argument(
        "--cenas", action="store_true", help="acrescenta varredura de cenas em um cache separado"
    )
    parser.add_argument("--keep-source", action="store_true", help="preserva os vídeos no cache")
    args = parser.parse_args()
    ids = list(args.video_ids)
    if args.ids_file:
        ids.extend(args.ids_file.read_text(encoding="utf-8-sig").split())
    if not 10 <= args.samples <= 240:
        parser.error("--samples deve estar entre 10 e 240")
    cache = args.cache / "cenas" if args.cenas else args.cache
    if args.samples != DEFAULT_SAMPLES:
        cache /= f"amostras-{args.samples}"
    if args.limite is not None and (not args.pendentes or args.limite < 1):
        parser.error("--limite exige --pendentes e um número positivo")
    if args.pendentes:
        if ids:
            parser.error("use --pendentes ou informe IDs explicitamente")
        ids = pendentes(cache, args.samples)[:args.limite]
        if not ids:
            print("Nenhuma publicação pendente de preparo.")
            return 0
    if not ids or any(not VIDEO_ID.fullmatch(video_id) for video_id in ids):
        parser.error("informe IDs do YouTube com onze caracteres")
    errors = 0
    for video_id in dict.fromkeys(ids):
        try:
            count, status = capture(cache, video_id, args.samples, args.keep_source, args.media_dir, args.cenas)
            print(f"{video_id}\t{status}\t{count}\t{cache / video_id}", flush=True)
        except (OSError, ValueError, av.error.FFmpegError, DownloadError) as error:
            errors += 1
            print(f"{video_id}\tfalha\t{type(error).__name__}: {error}", file=sys.stderr, flush=True)
    return min(errors, 1)


if __name__ == "__main__":
    sys.exit(main())
