"""Prepara a Central e o acervo estático para o GitHub Pages."""

from argparse import ArgumentParser
from html import escape
from pathlib import Path
import shutil
import subprocess
from urllib.parse import quote


RAIZ = Path(__file__).resolve().parents[1]
PASTAS = {"app", "data", "design-system", "docs", "entregaveis", "producao", "site"}
ARQUIVOS = {"index.html", "README.md", "PLANO_TURISMO_AQUI_PROTOTIPO.md"}
INDICES = {
    "data/acervo/canal-turismo-aqui/transcricoes": "Transcrições originais do canal",
    "data/tabelas": "Tabelas da base editorial",
    "entregaveis/revisao-pdf": "Páginas de revisão do ebook",
    "entregaveis/transcricoes-revisadas/txt": "Transcrições revisadas",
    "producao/revisao_transcricoes": "Arquivos de revisão das transcrições",
    "producao/revisao_transcricoes/edicoes": "Edições das transcrições",
}


def criar_indice(destino, pasta, titulo):
    diretorio = destino / pasta
    central = "../" * len(diretorio.relative_to(destino).parts)
    arquivos = sorted(diretorio.iterdir(), key=lambda caminho: caminho.name.casefold())
    links = []
    for arquivo in arquivos:
        nome = arquivo.name + ("/" if arquivo.is_dir() else "")
        links.append(f'    <li><a href="{quote(nome)}">{escape(nome)}</a></li>')
    lista = "\n".join(links)
    (diretorio / "index.html").write_text(
        f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(titulo)} · Turismo Aqui</title>
  <link rel="stylesheet" href="{central}design-system/tokens.css">
  <link rel="stylesheet" href="{central}design-system/components.css">
  <link rel="stylesheet" href="{central}site/style.css">
</head>
<body class="ta">
<main class="wrap">
  <p><a href="{central}">Central Turismo Aqui</a></p>
  <h1>{escape(titulo)}</h1>
  <ul>
{lista}
  </ul>
</main>
</body>
</html>
""",
        encoding="utf-8",
    )


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("destino", type=Path, help="Pasta de saída que ainda não existe")
    destino = parser.parse_args().destino.resolve()
    arquivos = subprocess.check_output(["git", "ls-files", "-z"], cwd=RAIZ)
    caminhos = [Path(nome) for nome in arquivos.decode("utf-8").split("\0") if nome]
    destino.mkdir(parents=True)
    for caminho in caminhos:
        if caminho.parts[0] in PASTAS or caminho.as_posix() in ARQUIVOS:
            alvo = destino / caminho
            alvo.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(RAIZ / caminho, alvo)
    for pasta, titulo in INDICES.items():
        criar_indice(destino, pasta, titulo)


if __name__ == "__main__":
    main()
