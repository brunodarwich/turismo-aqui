"""Diagrama a edição fotográfica do guia de Alter do Chão."""

import csv
import json
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from PIL import Image, ImageOps
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "entregaveis" / "catalogo-visual"
DESIGN = ROOT / "design-system"
OUTPUT = ROOT / "entregaveis" / "guia-alter-do-chao-prototipo.pdf"
WIDTH, HEIGHT = A4


def register_fonts():
    for role, names, fallback in (
        ("display", ("georgia.ttf", "DejaVuSerif.ttf"), "Times-Roman"),
        ("text", ("segoeui.ttf", "DejaVuSans.ttf"), "Helvetica"),
        ("bold", ("segoeuib.ttf", "DejaVuSans-Bold.ttf"), "Helvetica-Bold"),
    ):
        for path in (
            Path("C:/Windows/Fonts") / names[0],
            Path("/usr/share/fonts/truetype/dejavu") / names[1],
        ):
            if path.is_file():
                pdfmetrics.registerFont(TTFont(role, str(path)))
                break
        else:
            role = fallback
        yield role


class Guide:
    def __init__(self, path):
        self.doc = canvas.Canvas(str(path), pagesize=A4, pageCompression=1, invariant=1, lang="pt-BR")
        self.doc.setTitle("Alter do Chão | Guia Turismo Aqui")
        self.doc.setAuthor("Turismo Aqui")
        self.doc.setSubject("Guia de viagem com praias, floresta, cultura e roteiro de três dias")
        self.doc.showOutline()
        tokens = json.loads((DESIGN / "tokens.json").read_text(encoding="utf-8"))
        self.colors = {key: HexColor(value) for key, value in tokens["color"].items()}
        self.margin = self.points(tokens["space"]["16"])
        self.gap = self.points(tokens["space"]["6"])
        self.radius = self.points(tokens["radius"]["card"])
        self.inner = WIDTH - 2 * self.margin
        self.half = (self.inner - self.gap) / 2
        self.faces = dict(zip(("display", "text", "bold"), register_fonts()))
        self.number = 0
        self.id = ""
        self.photos_used = {}

    @staticmethod
    def points(rem):
        return float(rem.removesuffix("rem")) * 12

    def rectangle(self, x, top, width, height, color, radius=0):
        self.doc.setFillColor(self.colors[color])
        if radius:
            self.doc.roundRect(x, HEIGHT - top - height, width, height, radius, fill=1, stroke=0)
        else:
            self.doc.rect(x, HEIGHT - top - height, width, height, fill=1, stroke=0)

    def line(self, x, top, end, color="line"):
        self.doc.setStrokeColor(self.colors[color])
        self.doc.setLineWidth(0.8)
        self.doc.line(x, HEIGHT - top, end, HEIGHT - top)

    def text(self, value, top, *, x=None, width=None, size=12, leading=None,
             face="text", color="ink", limit=None):
        x = self.margin if x is None else x
        width = self.inner if width is None else width
        leading = size * 1.4 if leading is None else leading
        font = self.faces[face]
        lines = simpleSplit(value, font, size, width)
        end = top + leading * len(lines)
        if (limit is not None and end > limit) or any(
            pdfmetrics.stringWidth(line, font, size) > width + 0.1 for line in lines
        ):
            raise ValueError(f"Texto excede a área prevista em {self.id}: {value}")
        self.doc.setFillColor(self.colors[color])
        self.doc.setFont(font, size)
        for index, line in enumerate(lines):
            self.doc.drawString(x, HEIGHT - top - size - index * leading, line)
        return end

    def link(self, x, top, width, height, *, url=None, page=None):
        box = (x, HEIGHT - top - height, x + width, HEIGHT - top)
        if url:
            self.doc.linkURL(url, box)
        else:
            self.doc.linkRect("", page, box, relative=0)

    def named_link(self, label, url, x, top, width, *, size=10):
        end = self.text(label, top, x=x, width=width, size=size, face="bold", color="teal-active")
        self.link(x, top, width, end - top, url=url)
        return end

    def start(self, page_id, title):
        self.number += 1
        self.id = page_id
        self.rectangle(0, 0, WIDTH, HEIGHT, "canvas")
        self.doc.bookmarkPage(page_id)
        self.doc.addOutlineEntry(title, page_id, level=0)

    def heading(self, title, summary, eyebrow="GUIA DE ALTER DO CHÃO"):
        self.text(eyebrow, 43, size=10, face="bold", color="teal-active")
        self.rectangle(self.margin, 69, 29, 4, "lime")
        self.text(title, 80, size=37, leading=44, face="display", limit=124)
        self.text(summary, 137, width=466, size=13, leading=18, color="muted", limit=175)

    def footer(self):
        self.line(self.margin, 784, WIDTH - self.margin)
        self.text("T U R I S M O   A Q U I", 799, size=8, face="bold", color="teal-active")
        if self.id not in {"sumario", "capa"}:
            self.text("Voltar ao sumário", 798, x=WIDTH / 2 - 40, width=90, size=9, color="teal-active")
            self.link(WIDTH / 2 - 40, 795, 84, 20, page="sumario")
        self.text(f"{self.number:02d}", 794, x=WIDTH - self.margin - 24, width=24, size=13, face="display")
        self.doc.showPage()

    def photo(self, photo, x, top, width, height, *, caption=True, focus=(0.5, 0.5)):
        with Image.open(photo["path"]) as source:
            image = source.convert("RGB")
            pixels = (round(width * 2.4), round(height * 2.4))
            if crop := photo.get("crop"):
                left, top_edge, right, bottom = crop
                image = image.crop((round(left * image.width), round(top_edge * image.height),
                                    round(right * image.width), round(bottom * image.height)))
            if photo.get("preserve"):
                image = ImageOps.contain(image, pixels, Image.Resampling.LANCZOS)
                scale = min(width / image.width, height / image.height)
                photo_width, photo_height = image.width * scale, image.height * scale
            else:
                image = ImageOps.fit(image, pixels, Image.Resampling.LANCZOS, centering=focus)
                photo_width, photo_height = width, height
        buffer = BytesIO()
        image.save(buffer, "JPEG", quality=89, optimize=True)
        buffer.seek(0)
        self.doc.saveState()
        if caption:
            mask = self.doc.beginPath()
            mask.roundRect(x, HEIGHT - top - height, width, height, self.radius)
            self.doc.clipPath(mask, stroke=0, fill=0)
        self.doc.drawImage(
            ImageReader(buffer), x + (width - photo_width) / 2,
            HEIGHT - top - (height + photo_height) / 2, width=photo_width, height=photo_height,
        )
        self.doc.restoreState()
        self.photos_used[photo["id"]] = photo
        if caption:
            self.named_link(photo["caption"], photo["url"], x, top + height + 5, width, size=8.25)

    def block(self, entry, x, top, width, limit, *, title_size=18):
        title, body = entry
        start = self.text(title, top, x=x, width=width, size=title_size, leading=title_size + 5,
                          face="display", color="teal-active", limit=limit)
        return self.text(body, start + 5, x=x, width=width, size=11.25, leading=16, limit=limit)

    def panel(self, entry, top, height, color="tint"):
        self.rectangle(self.margin, top, self.inner, height, color, self.radius)
        self.block(entry, self.margin + 17, top + 12, self.inner - 34, top + height - 6, title_size=17)

    def source_note(self, chapter, references, top=743):
        sources = [references[key] for key in chapter["fontes"]]
        x = self.margin
        for label, url in sources:
            width = pdfmetrics.stringWidth(label, self.faces["bold"], 8.5)
            if x + width > WIDTH - self.margin:
                x = self.margin
                top += 14
            self.named_link(label, url, x, top, width + 1, size=8.5)
            x += width + 14

    def cover(self, copy, photo):
        self.start("capa", "Capa")
        self.rectangle(0, 0, WIDTH, 9, "teal")
        self.text(copy["local"].upper(), 61, width=340, size=11, face="bold", color="teal-active")
        self.rectangle(self.margin, 92, 41, 5, "lime")
        logo = ImageReader(str(DESIGN / "assets" / "turismo-aqui.png"))
        logo_width = 75
        original_width, original_height = logo.getSize()
        logo_height = logo_width * original_height / original_width
        self.doc.drawImage(logo, WIDTH - self.margin - logo_width, HEIGHT - 46 - logo_height,
                           width=logo_width, height=logo_height, mask="auto")
        self.text(copy["titulo"], 126, size=64, leading=76, face="display", limit=202)
        self.text(copy["subtitulo"], 209, size=20, leading=25, face="display", limit=234)
        self.text(copy["resumo"], 248, size=12.5, color="muted", limit=268)
        self.photo(photo, 0, 295, WIDTH, 474, caption=False, focus=(0.52, 0.48))
        self.rectangle(0, 769, WIDTH, HEIGHT - 769, "teal-active")
        self.text(photo["caption"], 787, size=9, color="white")
        self.link(self.margin, 784, 290, 24, url=photo["url"])
        self.text("Ver sumário", 787, x=WIDTH - self.margin - 65, width=65,
                  size=9, face="bold", color="white")
        self.link(WIDTH - self.margin - 65, 784, 65, 24, page="sumario")
        self.doc.showPage()

    def contents(self, chapters, photo):
        self.start("sumario", "Sumário")
        self.heading("Sumário", "Escolha por onde começar ou vá direto ao roteiro de três dias.")
        self.photo(photo, self.margin, 181, self.inner, 148, focus=(0.5, 0.62))
        entries = [(item["id"], item["titulo"]) for item in chapters] + [("fontes", "Fontes e créditos")]
        for idx, (page_id, title) in enumerate(entries, start=3):
            top = 352 + (idx - 3) * 45
            self.line(self.margin, top, WIDTH - self.margin)
            self.text(title, top + 7, width=self.inner - 48, size=17, face="display")
            self.text(f"{idx:02d}", top + 9, x=WIDTH - self.margin - 25, width=25,
                      size=12, face="bold", color="teal-active")
            self.link(self.margin, top + 2, self.inner, 41, page=page_id)
        self.footer()

    def chapter(self, chapter, photos, references):
        self.start(chapter["id"], chapter["titulo"])
        self.heading(chapter["titulo"], chapter["resumo"])
        pictures = [photos[key] for key in chapter.get("imagens", [])]
        blocks = chapter["blocos"]
        left, right = self.margin, self.margin + self.half + self.gap
        if self.id in {"vila", "floresta"}:
            if self.id == "vila":
                self.photo(pictures[0], left, 202, self.half, 181)
                self.photo(pictures[1], right, 202, self.half, 181)
                text_top = 438
            else:
                self.photo(pictures[0], left, 202, self.inner, 267)
                text_top = 512
            self.block(blocks[0], left, text_top, self.half, 642)
            self.block(blocks[1], right, text_top, self.half, 642)
            self.panel(blocks[2], 646, 80)
        elif self.id == "aguas":
            for idx, (picture, block) in enumerate(zip(pictures, blocks)):
                top = 200 + idx * 220
                self.photo(picture, left, top, 293, 183)
                self.block(block, left + 315, top + 30, self.inner - 315, top + 177)
            self.panel(blocks[2], 639, 96, "lime-tint")
        elif self.id == "travessia":
            self.photo(pictures[0], left, 202, self.inner, 268)
            self.block(blocks[0], left, 522, self.half, 644)
            self.photo(pictures[1], right, 507, self.half, 127)
            self.panel(blocks[1], 657, 80, "lime-tint")
        elif self.id in {"praias", "saire"}:
            self.photo(pictures[0], left, 205, self.half, 182)
            self.photo(pictures[1], right, 205, self.half, 182)
            self.block(blocks[0], left, 436, self.half, 613)
            self.block(blocks[1], right, 436, self.half, 613)
            self.panel(blocks[2], 601, 104)
        elif self.id == "roteiro":
            for idx, (title, body) in enumerate(blocks[:3], start=1):
                top = 193 + (idx - 1) * 139
                self.rectangle(left, top, self.inner, 123, "white", self.radius)
                self.rectangle(left + 17, top + 19, 52, 36, "lime-tint", 8)
                self.text(f"Dia {idx}", top + 27, x=left + 28, width=42, size=11, face="bold")
                self.block((title, body), left + 89, top + 17, self.inner - 110, top + 115, title_size=21)
            self.panel(blocks[3], 628, 85, "lime-tint")
        elif self.id == "turismo-aqui":
            self.photo(pictures[0], left, 198, self.inner, 282)
            for idx, (year, body) in enumerate(blocks):
                top = 522 + idx * 92
                self.line(left, top, WIDTH - left)
                self.text(year, top + 12, width=76, size=28, face="display", color="teal-active")
                self.text(body, top + 16, x=left + 98, width=self.inner - 98, size=12, limit=top + 78)
        else:
            raise ValueError(f"Diagramação ausente para o capítulo {self.id}")
        self.source_note(chapter, references)
        self.footer()

    def credits(self, references, license_url):
        self.start("fontes", "Fontes e créditos")
        self.heading("Fontes e créditos", "Consulte os vídeos de origem, as referências da Prefeitura e os créditos das imagens.", "ACERVO E REFERÊNCIAS")
        left, right = self.margin, self.margin + self.half + self.gap
        self.line(left, 193, WIDTH - self.margin)
        self.text("Para ler e assistir", 206, x=left, width=self.half, size=19, face="display")
        self.text("Para ver os quadros", 206, x=right, width=self.half, size=19, face="display")
        top = 246
        for label, url in references.values():
            top = self.named_link(label, url, left, top, self.half, size=10) + 10
        top += 12
        self.text("Fotografia documental", top, x=left, width=self.half, face="display", size=16)
        top = self.named_link("Alter do Chão · Rosanetur", self.photos_used["rosanetur"]["url"],
                              left, top + 27, self.half)
        self.named_link("Licença CC BY 2.0 · enquadramento original", license_url, left, top + 4,
                        self.half, size=9)
        top = 246
        for key, photo in self.photos_used.items():
            if key == "rosanetur":
                continue
            top = self.named_link(photo["caption"], photo["url"], right, top, self.half, size=8.5) + 8
        self.rectangle(left, 679, self.inner, 69, "tint", self.radius)
        self.text("Quadros do Turismo Aqui com recortes editoriais. A seleção de imagens do canal é para esta edição local.",
                  695, x=left + 17, width=self.inner - 34, size=10.5, leading=15, limit=735)
        self.footer()
        self.doc.save()


def load_photos(copy, assets):
    with (CATALOG / "quadros.csv").open(encoding="utf-8-sig", newline="") as source:
        frames = {(row["video_id"], int(row["tempo_ms"])): row for row in csv.DictReader(source)}
    photos = {}
    for key, (video_id, ms, scene) in copy["quadros"].items():
        frame = frames[video_id, ms]
        minute, second = divmod(ms // 1000, 60)
        photos[key] = {
            "id": key, "path": CATALOG / frame["imagem"], "url": frame["url_instante"],
            "caption": f"{scene} · Turismo Aqui · {minute}:{second:02d}",
        }
    photos["pedras"]["crop"] = (0.10, 0.17, 0.92, 0.76)
    for key, asset, caption, preserve in (
        ("ilha-0933", "quadro-ilha-do-amor", "Ilha do Amor · Turismo Aqui · 9:33", False),
        ("emanuel", "quadro-emanuel", "Emanuel Júlio em Alter do Chão · Turismo Aqui · 0:12", False),
        ("rosanetur", "foto-alter", "Alter do Chão · Rosanetur · CC BY 2.0", True),
    ):
        photo = assets[asset]
        photos[key] = {
            "id": key, "path": ROOT / photo["arquivo"], "url": photo["url"],
            "caption": caption, "preserve": preserve,
        }
    for photo in photos.values():
        if not photo["path"].is_file():
            raise FileNotFoundError(photo["path"])
    return photos


def generate_ebook(manifest, sources):
    copy = json.loads((ROOT / "producao" / "guia_alter.json").read_text(encoding="utf-8"))
    references = {
        key: (label, sources[source]["url"])
        for key, (label, source) in copy["referencias"].items()
    }
    photos = load_photos(copy, manifest["imagens"])
    with NamedTemporaryFile(dir=OUTPUT.parent, prefix="guia-alter-", suffix=".tmp", delete=False) as stream:
        temporary = Path(stream.name)
    try:
        guide = Guide(temporary)
        guide.cover(copy["capa"], photos[copy["capa"]["imagem"]])
        guide.contents(copy["capitulos"], photos["vila"])
        for chapter in copy["capitulos"]:
            guide.chapter(chapter, photos, references)
        guide.credits(references, manifest["imagens"]["foto-alter"]["licenca"])
        temporary.replace(OUTPUT)
    finally:
        temporary.unlink(missing_ok=True)
