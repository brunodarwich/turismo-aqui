"""Renderiza as peças quadradas, a galeria e os créditos do Turismo Aqui."""

import json
from functools import lru_cache
from hashlib import sha256
from html import escape
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "entregaveis" / "redes-sociais"
DESIGN = ROOT / "design-system"
SIZE = 1080
PAD = 64
COLOR = json.loads((DESIGN / "tokens.json").read_text(encoding="utf-8"))["color"]
CROPS = {
    "quadro-ilha-do-amor-cheia": (0, 0.12, 1, 0.82),
    "quadro-canoa-caranazal": (0, 0, 1, 0.80),
    "quadro-ponta-pedras": (0.10, 0.17, 0.92, 0.76),
    "quadro-emanuel-alter-0012": (0, 0, 1, 0.90),
}


@lru_cache(maxsize=None)
def font(size, role):
    names = {
        "title": ("georgia.ttf", "DejaVuSerif.ttf"),
        "italic": ("georgiai.ttf", "DejaVuSerif-Italic.ttf"),
        "text": ("segoeui.ttf", "DejaVuSans.ttf"),
        "label": ("segoeuib.ttf", "DejaVuSans-Bold.ttf"),
    }
    native, fallback = names[role]
    for candidate in (str(Path("C:/Windows/Fonts") / native), fallback):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    raise OSError(f"Fonte indisponível: {native} ou {fallback}.")


def rounded_mask(size, radius):
    mask = Image.new("L", size)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius, fill=255)
    return mask


class Artwork:
    def __init__(self, record, assets):
        self.record = record
        self.assets = [assets[key] for key in record["imagens"]]
        self.canvas = Image.new("RGB", (SIZE, SIZE), COLOR["canvas"])
        self.draw = ImageDraw.Draw(self.canvas)

    def rect(self, x, y, w, h, color, radius=0):
        box = (x, y, x + w - 1, y + h - 1)
        if radius:
            self.draw.rounded_rectangle(box, radius, fill=COLOR[color])
        else:
            self.draw.rectangle(box, fill=COLOR[color])

    def line(self, x, y, w, color="line"):
        self.draw.line((x, y, x + w, y), fill=COLOR[color], width=2)

    def text(self, value, x, y, w, size, *, role="text", color="ink", leading=None, bottom=SIZE):
        face = font(size, role)
        gap = leading or round(size * 1.16)
        lines = []
        for paragraph in value.splitlines():
            line = ""
            for word in paragraph.split():
                proposed = f"{line} {word}".strip()
                if line and self.draw.textlength(proposed, font=face) > w:
                    lines.append(line)
                    line = word
                else:
                    line = proposed
            lines.append(line)
        for index, line in enumerate(lines):
            position = (x, y + index * gap)
            bounds = self.draw.textbbox(position, line, font=face, anchor="lt")
            if bounds[0] < 0 or bounds[2] > min(x + w + 2, SIZE) or bounds[3] > bottom:
                raise ValueError(f"Texto fora da área de {self.record['layout']}: {line}")
            self.draw.text(position, line, font=face, fill=COLOR[color], anchor="lt")
        return y + len(lines) * gap

    def label(self, value, x, y, w, color="teal-active", size=27, bottom=SIZE):
        return self.text(value.upper(), x, y, w, size, role="label", color=color, bottom=bottom)

    def photo(self, index, x, y, w, h, *, center=(0.5, 0.5), radius=0):
        asset = self.assets[index]
        with Image.open(ROOT / asset["caminho"]) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            if crop := CROPS.get(asset["id"]):
                left, top, right, bottom = crop
                image = image.crop((round(left * image.width), round(top * image.height),
                                    round(right * image.width), round(bottom * image.height)))
            image = ImageOps.fit(image, (w, h), Image.Resampling.LANCZOS, centering=center)
        self.canvas.paste(image, (x, y), rounded_mask(image.size, radius) if radius else None)

    def brand(self, x, y, *, badge=False):
        logo = brand_logo()
        if badge:
            self.rect(x - 17, y - 13, 131, 132, "white", 16)
        self.canvas.paste(logo, (x, y), logo)

    def credit(self, x=PAD, y=1017, *, light=False):
        self.text("Acervo Turismo Aqui", x, y, SIZE - x - 48, 23,
                  color="tint" if light else "muted")

    def abertura(self):
        self.photo(0, 0, 0, SIZE, 657, center=(0.5, 0.57))
        self.rect(0, 657, SIZE, 423, "teal-active")
        self.rect(64, 657, 124, 7, "lime")
        self.brand(904, 66, badge=True)
        self.label(self.record["categoria"], PAD, 710, 760, "lime")
        self.text(self.record["titulo"], PAD, 765, 950, 130, role="title", color="white", bottom=884)
        self.text(self.record["texto"], PAD, 920, 920, 45, role="italic", color="white", bottom=972)
        self.credit(light=True)

    def comparacao(self):
        self.rect(0, 0, SIZE, 355, "tint")
        self.brand(896, 62)
        self.text(self.record["titulo"], PAD, 66, 800, 93, role="title", leading=99, bottom=260)
        self.text(self.record["texto"], PAD, 290, 935, 37, bottom=336)
        for index, label in enumerate(self.record["rotulos"]):
            x = PAD + index * 486
            self.photo(index, x, 383, 466, 501, radius=22,
                       center=(0.52, 0.54) if index else (0.44, 0.44))
            self.rect(x, 900, 466, 63, "teal-active" if index == 0 else "lime-tint", 12)
            self.label(label, x + 23, 916, 421, "white" if index == 0 else "teal-active")
        self.credit()

    def travessia(self):
        self.rect(0, 0, SIZE, SIZE, "tint")
        self.photo(0, 258, 180, 822, 660, center=(0.40, 0.66), radius=27)
        self.brand(64, 50)
        self.rect(32, 289, 628, 310, "canvas", 24)
        self.rect(64, 326, 67, 6, "lime")
        self.label(self.record["categoria"], 64, 362, 520)
        self.text(self.record["titulo"], 64, 430, 565, 71, role="title", leading=79, bottom=583)
        self.text(self.record["texto"], PAD, 895, 920, 39, bottom=995)
        self.credit()

    def checklist(self):
        self.label(self.record["categoria"], PAD, 63, 750)
        self.brand(900, 50)
        self.text(self.record["titulo"], PAD, 121, 820, 78, role="title", bottom=211)
        self.photo(0, PAD, 236, 952, 340, center=(0.52, 0.61), radius=20)
        for index, item in enumerate(self.record["itens"]):
            y = 613 + 86 * index
            self.line(PAD, y, 952)
            self.rect(68, y + 22, 42, 42, "lime-tint", 10)
            self.draw.line((79, y + 43, 87, y + 51, 101, y + 33), fill=COLOR["teal-active"], width=4)
            self.text(item, 134, y + 21, 865, 36, role="label", bottom=y + 73)
        self.credit()

    def coluna(self):
        self.rect(0, 0, SIZE, SIZE, "teal-active")
        self.photo(0, 547, 0, 533, SIZE, center=(0.50, 0.5))
        self.brand(64, 67, badge=True)
        self.rect(64, 308, 73, 7, "lime")
        self.label(self.record["categoria"], PAD, 354, 450, "lime")
        self.text(self.record["titulo"], PAD, 420, 460, 69, role="title",
                  color="white", leading=79, bottom=610)
        self.text(self.record["texto"], PAD, 651, 420, 42, color="white", leading=56, bottom=900)
        self.credit(light=True)

    def imersao(self):
        self.photo(0, 0, 0, SIZE, SIZE, center=(0.46, 0.5))
        ramp = Image.linear_gradient("L").resize((SIZE, 625))
        ramp = ramp.point(lambda value: round(247 * (value / 255) ** 0.78))
        self.canvas.paste(COLOR["ink"], (0, SIZE - ramp.height, SIZE, SIZE), ramp)
        self.brand(903, 65, badge=True)
        self.rect(PAD, 527, 233, 45, "teal-active", 8)
        self.label(self.record["categoria"], PAD + 13, 536, 205, "lime", size=25)
        self.text(self.record["titulo"], PAD, 598, 940, 112, role="title", leading=111,
                  color="white", bottom=817)
        self.text(self.record["texto"], PAD, 871, 945, 39, color="white", bottom=967)
        self.credit(light=True)

    def paisagem(self):
        self.rect(0, 0, SIZE, 144, "tint")
        self.label(self.record["categoria"], PAD, 72, 750)
        self.brand(903, 31, badge=True)
        self.photo(0, 0, 159, SIZE, 541)
        self.rect(0, 700, 14, 380, "lime")
        self.text(self.record["titulo"], PAD, 756, 945, 103, role="title", bottom=855)
        self.text(self.record["texto"], PAD, 909, 945, 38, bottom=970)
        self.credit()

    def diptico(self):
        self.rect(0, 0, SIZE, SIZE, "teal-active")
        self.brand(899, 63, badge=True)
        self.label(self.record["categoria"], PAD, 68, 730, "lime")
        self.text(self.record["titulo"], PAD, 127, 810, 94, role="title", color="white", bottom=220)
        self.text(self.record["texto"], PAD, 263, 945, 38, color="white", bottom=322)
        for index, (x, y, width, height) in enumerate(((64, 372, 512, 494), (596, 432, 420, 434))):
            self.photo(index, x, y, width, height, radius=20, center=(0.55, 0.5))
            self.label(self.record["rotulos"][index], x, 890, width, "lime", size=26)
        self.credit(light=True)

    def linha_do_tempo(self):
        self.photo(0, 0, 0, SIZE, 492, center=(0.50, 0.37))
        self.rect(0, 492, SIZE, 588, "tint")
        self.brand(900, 553)
        self.label(self.record["categoria"], PAD, 531, 765)
        self.text(self.record["titulo"], PAD, 578, 810, 86, role="title", bottom=669)
        for index, (year, copy) in enumerate(self.record["itens"]):
            y = 706 + index * 134
            self.line(PAD, y, 952)
            self.text(year, PAD, y + 20, 140, 51, role="title", color="teal-active", bottom=y + 88)
            self.text(copy, 232, y + 25, 775, 35, leading=45, bottom=y + 104)
        self.credit()

    def roteiro(self):
        self.rect(0, 0, SIZE, 264, "tint")
        self.brand(898, 61)
        self.text(self.record["titulo"], PAD, 70, 814, 84, role="title", bottom=168)
        self.text(self.record["texto"], PAD, 191, 940, 37, bottom=237)
        for index, (title, detail) in enumerate(self.record["itens"]):
            y = 292 + index * 227
            self.rect(64, y, 952, 204, "white", 22)
            self.photo(index, 64, y, 284, 204, radius=22)
            self.label(f"Dia {index + 1}", 382, y + 22, 600, size=25, bottom=y + 55)
            self.text(title, 382, y + 67, 614, 48, role="title", bottom=y + 125)
            self.text(detail, 382, y + 139, 614, 33, bottom=y + 178)
        self.credit()

    def render(self):
        layouts = {
            "abertura": self.abertura, "comparacao": self.comparacao, "travessia": self.travessia,
            "checklist": self.checklist, "coluna": self.coluna, "imersao": self.imersao,
            "paisagem": self.paisagem, "diptico": self.diptico,
            "linha-do-tempo": self.linha_do_tempo, "roteiro": self.roteiro,
        }
        layouts[self.record["layout"]]()
        return self.canvas


@lru_cache(maxsize=1)
def brand_logo():
    with Image.open(DESIGN / "assets" / "turismo-aqui.png") as logo:
        return ImageOps.contain(logo.convert("RGBA"), (98, 106), Image.Resampling.LANCZOS)


def plain_title(record):
    return " ".join(record["titulo"].splitlines())


def image_credit(asset, sources):
    seconds = asset["inicio_ms"] // 1000
    minute, second = divmod(seconds, 60)
    url = asset.get("url")
    if not url:
        url = f"{sources[asset['video_id']]['url']}&t={seconds}s"
    return f"- [{asset['titulo']} · {asset['autor']} · {minute}:{second:02}]({url})"


def gallery_markup(records, assets, directory):
    start, end = '<!-- pecas: inicio -->', '<!-- pecas: fim -->'
    gallery = (OUT / "index.html").read_text(encoding="utf-8")
    intro, after = gallery.split(start, 1)
    _, footer = after.split(end, 1)
    items = []
    for number, record in enumerate(records, 1):
        filename = f"{number:02}.png"
        revision = sha256((directory / filename).read_bytes()).hexdigest()[:12]
        image_url = f"{filename}?v={revision}"
        title = escape(plain_title(record))
        heading = f"peca-{number:02}"
        details = [record.get("texto"), *record.get("rotulos", [])]
        details.extend(" — ".join(item) if isinstance(item, list) else item for item in record.get("itens", []))
        for asset_id in record["imagens"]:
            asset = assets[asset_id]
            details.append(asset.get("descricao_alt") or asset["titulo"])
        description = escape(" ".join(detail.rstrip(".") + "." for detail in details if detail))
        items.append(
            f'      <a class="ta-card social-card" href="{image_url}" aria-labelledby="{heading}">\n'
            f'        <img src="{image_url}" alt="{description}" width="1080" height="1080" loading="lazy" decoding="async">\n'
            f'        <h2 id="{heading}">{title}</h2>\n'
            '      </a>'
        )
    return f"{intro}{start}\n" + "\n".join(items) + f"\n      {end}{footer}"


def thumbnail(directory):
    canvas = Image.new("RGB", (640, 320), COLOR["tint"])
    for number, x, y, side in ((2, 24, 72, 176), (10, 440, 72, 176), (6, 208, 48, 224)):
        with Image.open(directory / f"{number:02}.png") as image:
            card = image.resize((side, side), Image.Resampling.LANCZOS)
        mask = rounded_mask(card.size, 9)
        canvas.paste(COLOR["line"], (x + 6, y + 7, x + 6 + side, y + 7 + side), mask)
        canvas.paste(card, (x, y), mask)
    return canvas


def generate_cards(manifest, sources, assets):
    records = manifest["pecas"]
    legends = [
        "# Legendas das peças sociais", "",
        "Edição local do Turismo Aqui. As imagens têm recortes editoriais.", "",
    ]
    with TemporaryDirectory(prefix="redes-", dir=OUT.parent) as working:
        folder = Path(working)
        for number, record in enumerate(records, 1):
            artwork = Artwork(record, assets)
            artwork.render().save(folder / f"{number:02}.png", optimize=True)
            legends.extend((f"## {number:02} · {plain_title(record)}", "", record["legenda"], ""))
            legends.extend(image_credit(asset, sources) for asset in artwork.assets)
            legends.extend(f"- [{sources[key]['titulo']}]({sources[key]['url']})" for key in record["fontes"])
            legends.append("")

        thumbnail(folder).save(folder / "redes.webp", quality=90, method=6)
        (folder / "legendas-redes.md").write_text("\n".join(legends), encoding="utf-8")
        gallery = gallery_markup(records, assets, folder)
        (folder / "index.html").write_text(gallery, encoding="utf-8")
        for number in range(1, len(records) + 1):
            filename = f"{number:02}.png"
            (folder / filename).replace(OUT / filename)
        (folder / "redes.webp").replace(OUT.parent / "central" / "redes.webp")
        (folder / "legendas-redes.md").replace(ROOT / "producao" / "legendas-redes.md")
        (folder / "index.html").replace(OUT / "index.html")
