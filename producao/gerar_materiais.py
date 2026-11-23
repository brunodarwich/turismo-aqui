"""Gera as peças sociais e o ebook a partir do catálogo."""

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "entregaveis"
MANIFEST = ROOT / "producao" / "materiais.json"
BASE = ROOT / "data" / "base.json"


def load_catalog():
    data = json.loads(BASE.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    sources = {record["id"]: record for record in data["videos"] + data["fontes"]}
    assets = {record["id"]: record for record in data["ativos"]}
    return manifest, sources, assets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--ebook-only", action="store_true", help="Gera somente o PDF do guia.")
    modes.add_argument("--social-only", action="store_true", help="Gera somente as peças sociais e suas legendas.")
    args = parser.parse_args()
    manifest, sources, assets = load_catalog()
    if not args.ebook_only:
        from gerar_redes import generate_cards

        generate_cards(manifest, sources, assets)
        print(f"Geradas {len(manifest['pecas'])} peças sociais e suas legendas em {OUT}")
    if not args.social_only:
        from gerar_guia_alter import generate_ebook

        generate_ebook(manifest, sources)
        print(f"Guia em PDF gerado em {OUT}")


if __name__ == "__main__":
    main()
