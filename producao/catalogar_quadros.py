"""Valida os quadros revisados e publica o catálogo visual local."""

import argparse
import csv
import hashlib
import html
import io
import json
import os
import re
import tempfile
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image

from revisar_transcricoes import ACERVO, LEGENDA, ROOT, catalogo, segundos


SAIDA = ROOT / "entregaveis/catalogo-visual"
QUOTA = 10
CREDITO = "Turismo Aqui — quadro de vídeo publicado no YouTube"
CONFIANCA = {"confirmado", "provável", "não identificado"}
COLUNAS = (
    "video_id", "titulo", "tipo", "data", "tempo_ms", "tempo", "url_video",
    "url_instante", "imagem", "largura", "altura", "descricao", "local",
    "confianca", "contexto", "marcas_transcricao", "arquivo_transcricao",
    "fontes", "credito", "sha256",
)


def ler_json(caminho):
    return json.loads(caminho.read_text(encoding="utf-8-sig"))


def salvar(caminho, dados):
    if caminho.is_file() and caminho.read_bytes() == dados:
        return
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=caminho.parent, delete=False) as arquivo:
        temporario = Path(arquivo.name)
        arquivo.write(dados)
    try:
        os.replace(temporario, caminho)
    finally:
        temporario.unlink(missing_ok=True)


def salvar_texto(caminho, texto):
    salvar(caminho, texto.encode("utf-8"))


def youtube(video_id, tempo_ms=None):
    url = f"https://www.youtube.com/watch?v={video_id}"
    return url if tempo_ms is None else f"{url}&t={tempo_ms // 1000}s"


def tempo(ms, exato=False):
    horas, resto = divmod(ms // 1000, 3600)
    minutos, seg = divmod(resto, 60)
    marca = f"{horas:02d}:{minutos:02d}:{seg:02d}"
    return f"{marca}.{ms % 1000:03d}" if exato else marca


def marcas_originais(original):
    return {
        segundos(item[1]) for linha in original.read_text(encoding="utf-8-sig").splitlines()
        if (item := LEGENDA.fullmatch(linha.strip()))
    }


def carregar_candidatos(raizes, video_id):
    por_tempo = {}
    for raiz in raizes:
        pasta = raiz / video_id
        manifesto = pasta / "candidatos.json"
        if not manifesto.is_file():
            continue
        dados = ler_json(manifesto)
        if dados["video_id"] != video_id:
            raise ValueError(f"ID divergente em {manifesto}")
        for quadro in dados["frames"]:
            caminho = pasta / quadro["file"]
            if caminho.is_file():
                por_tempo.setdefault(quadro["timestamp_ms"], (quadro, caminho))
    return por_tempo


def validar_revisao(video, arquivo, candidatos, saida):
    revisao = ler_json(arquivo)
    video_id = video["id"]
    if revisao["video_id"] != video_id:
        raise ValueError(f"ID divergente em {arquivo}")
    quadros = revisao["quadros"]
    motivo = revisao.get("motivo", "").strip()
    indisponivel = revisao.get("indisponivel", False)
    if (len(quadros) < QUOTA and not motivo) or (indisponivel and quadros):
        raise ValueError(f"Contagem e justificativa incompatíveis em {arquivo}")
    candidatos_por_tempo = carregar_candidatos(candidatos, video_id)
    origem_transcricao = ACERVO / "transcricoes" / video["arquivoOriginal"]
    if nome := revisao.get("transcricao"):
        if nome != f"{video_id}.pt.txt":
            raise ValueError(f"Nome de transcrição suplementar inválido em {arquivo}")
        origem_transcricao = arquivo.parent / "transcricoes" / nome
    marcas_validas = marcas_originais(origem_transcricao)
    link_transcricao = Path(os.path.relpath(origem_transcricao, saida)).as_posix()
    registros = []
    imagens = {}
    hashes = set()
    for quadro in sorted(quadros, key=lambda quadro: quadro["tempo_ms"]):
        ms = quadro["tempo_ms"]
        if type(ms) is not int or not 0 <= ms < (segundos(video["duracao"]) + 1) * 1000:
            raise ValueError(f"Tempo fora do vídeo {video_id}: {ms}")
        marcas = quadro["marcas"]
        if sorted(set(marcas)) != marcas or any(type(m) is not int or m not in marcas_validas for m in marcas):
            raise ValueError(f"Marcas de transcrição inválidas em {video_id}, {ms}: {marcas}")
        confianca = quadro["confianca"]
        local = quadro["local"].strip()
        descricao = quadro["descricao"].strip()
        contexto = quadro["contexto"].strip()
        if confianca not in CONFIANCA or bool(local) == (confianca == "não identificado") or not (descricao and contexto):
            raise ValueError(f"Descrição, contexto ou localização inválidos em {video_id}, {ms}")
        fontes = quadro.get("fontes", [])
        if not isinstance(fontes, list) or any(
            not isinstance(url, str) or not url.startswith("https://") or not urlsplit(url).hostname for url in fontes
        ):
            raise ValueError(f"Fonte externa inválida em {video_id}, {ms}")

        nome = f"{ms:09d}.jpg"
        imagem = f"imagens/{video_id}/{nome}"
        candidato, caminho = candidatos_por_tempo.get(ms, (None, saida / imagem))
        if not caminho.is_file():
            raise ValueError(f"Quadro de {video_id} aos {ms} ms ausente do cache e da galeria")
        dados = caminho.read_bytes()
        with Image.open(io.BytesIO(dados)) as foto:
            if foto.format != "JPEG":
                raise ValueError(f"Imagem não é JPEG: {caminho}")
            largura, altura = foto.size
            foto.load()
        digest = hashlib.sha256(dados).hexdigest()
        if candidato and (digest != candidato["sha256"] or (largura, altura) != (candidato["width"], candidato["height"])):
            raise ValueError(f"Imagem divergente do manifesto em {video_id}, {ms}")
        if imagem in imagens or digest in hashes:
            raise ValueError(f"Quadro duplicado em {video_id}, {ms}")
        hashes.add(digest)
        imagens[imagem] = (caminho, digest)
        registros.append(dict(
            video_id=video_id, titulo=video["titulo"], tipo=video["tipo"], data=video["data"],
            tempo_ms=ms, tempo=tempo(ms, True), url_video=youtube(video_id),
            url_instante=youtube(video_id, ms), imagem=imagem, largura=largura, altura=altura,
            descricao=descricao, local=local, confianca=confianca, contexto=contexto,
            marcas_transcricao=" | ".join(tempo(m * 1000) for m in marcas),
            arquivo_transcricao=link_transcricao, fontes=" | ".join(fontes),
            credito=CREDITO, sha256=digest,
        ))
    estado = "Completo" if len(registros) >= QUOTA else "Seleção abaixo de 10"
    return registros, imagens, "Indisponível" if indisponivel else estado, motivo


def pagina(titulo, conteudo, prefixo="", script=""):
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(titulo)}</title><link rel="stylesheet" href="{prefixo}estilo.css">
{script}</head><body><main>{conteudo}</main></body></html>\n"""


def ficha(video, registros):
    titulo = html.escape(video["titulo"])
    data = "/".join(reversed(video["data"].split("-")))
    motivo = f'<p class="nota">{html.escape(video["motivo"])}</p>' if video["motivo"] else ""
    cartoes = []
    for quadro in registros:
        q = {campo: html.escape(str(valor)) for campo, valor in quadro.items()}
        local = f'{q["local"]} · {q["confianca"]}' if quadro["local"] else "Local não identificado"
        marcas = q["marcas_transcricao"] or "Sem marca de fala aplicável"
        fontes = " · ".join(
            f'<a href="{url}">Referência {n}</a>' for n, url in enumerate(q["fontes"].split(" | "), 1) if url
        )
        links = f"<br>{fontes}" if fontes else ""
        cartoes.append(f"""<article class="cena" id="q{q['tempo_ms']}">
<a class="imagem" href="../{q['imagem']}" aria-label="Abrir quadro em {q['tempo']}">
<img src="../miniaturas/{q['imagem'].removeprefix('imagens/')}" alt="{q['descricao']}" loading="lazy"></a>
<div class="cena-texto"><a class="tempo" href="{q['url_instante']}">{q['tempo']}</a>
<h2>{q['descricao']}</h2><p class="local">{local}</p>
<p>{q['contexto']}</p><p class="origem">Transcrição · {marcas}<br>{q['credito']}{links}</p></div></article>""")
    return pagina(titulo, f"""<nav><a href="../index.html">Voltar ao catálogo</a></nav>
<header><p class="origem">{html.escape(video['tipo'])} · {data} · {len(registros)} quadros</p>
<h1>{titulo}</h1><p><a href="{youtube(video['id'])}">Vídeo de origem</a> ·
<a href="../{html.escape(registros[0]['arquivo_transcricao'])}">Transcrição com horários</a></p>{motivo}</header>
<section class="cenas" aria-label="Quadros revisados">{''.join(cartoes)}</section>""", "../")


def exportar_csv(saida, nome, colunas, linhas):
    texto = io.StringIO(newline="")
    escritor = csv.DictWriter(texto, fieldnames=colunas, extrasaction="ignore")
    escritor.writeheader()
    escritor.writerows(linhas)
    salvar(saida / nome, texto.getvalue().encode("utf-8-sig"))


def miniatura(imagem):
    with Image.open(imagem) as foto:
        foto.thumbnail((520, 380), Image.Resampling.LANCZOS)
        dados = io.BytesIO()
        foto.save(dados, format="JPEG", quality=85, optimize=True)
        return dados.getvalue()


def imagens_publicadas(saida):
    caminho = saida / "quadros.csv"
    if not caminho.is_file():
        return {}
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return {linha["imagem"]: linha["sha256"] for linha in csv.DictReader(arquivo)}


def remover_substituidas(saida, anteriores, atuais):
    raiz = saida.resolve()
    for imagem in anteriores.keys() - atuais.keys():
        if not re.fullmatch(r"imagens/[\w-]{11}/\d{9}\.jpg", imagem, re.ASCII):
            continue
        caminho = saida / imagem
        if not caminho.resolve().is_relative_to(raiz):
            continue
        if caminho.is_file() and hashlib.sha256(caminho.read_bytes()).hexdigest() == anteriores[imagem]:
            caminho.unlink()
            pequena = saida / imagem.replace("imagens/", "miniaturas/", 1)
            if pequena.resolve().is_relative_to(raiz):
                pequena.unlink(missing_ok=True)


def publicar(candidatos, revisoes, saida):
    videos = catalogo()
    publicadas = imagens_publicadas(saida)
    ids = {video["id"] for video in videos}
    arquivos = {p.stem: p for p in revisoes.glob("*.json")}
    if extras := arquivos.keys() - ids:
        raise ValueError(f"Revisões sem registro no inventário: {', '.join(sorted(extras))}")
    todos_quadros = []
    todas_imagens = {}
    fichas = {}
    indice = []
    cenas = candidatos / "cenas"
    caches = [candidatos, cenas, *sorted(candidatos.glob("amostras-*")), *sorted(cenas.glob("amostras-*"))]
    for video in videos:
        video_id = video["id"]
        registros, imagens, estado, motivo = [], {}, "Pendente", ""
        if video_id in arquivos:
            registros, imagens, estado, motivo = validar_revisao(video, arquivos[video_id], caches, saida)
        item = dict(video, estado=estado, motivo=motivo, quantidade=len(registros), url=youtube(video_id))
        if registros:
            item.update(ficha=f"videos/{video_id}.html", capa=registros[0]["imagem"].replace("imagens/", "miniaturas/", 1),
                        locais=sorted({q["local"] for q in registros if q["local"]}))
            fichas[video_id] = ficha(item, registros)
        indice.append(item)
        todas_imagens.update(imagens)
        todos_quadros.extend(registros)

    for imagem, (origem, checksum) in todas_imagens.items():
        destino = saida / imagem
        if destino != origem:
            dados = origem.read_bytes()
            if hashlib.sha256(dados).hexdigest() != checksum:
                raise ValueError(f"O quadro mudou durante a publicação: {origem}")
            salvar(destino, dados)
        pequena = saida / imagem.replace("imagens/", "miniaturas/", 1)
        if not pequena.exists() or pequena.stat().st_mtime_ns < destino.stat().st_mtime_ns:
            salvar(pequena, miniatura(destino))
    for video_id, conteudo in fichas.items():
        salvar_texto(saida / "videos" / f"{video_id}.html", conteudo)
    exportar_csv(saida, "quadros.csv", COLUNAS, todos_quadros)
    exportar_csv(saida, "cobertura.csv", ("id", "titulo", "tipo", "data", "duracao", "estado", "quantidade", "motivo", "url"), indice)
    salvar_texto(saida / "catalogo.js", "window.catalogoVisual = " + json.dumps(indice, ensure_ascii=False, separators=(",", ":")) + ";\n")
    remover_substituidas(saida, publicadas, todas_imagens)
    print(f"{len(todos_quadros)} quadros, {len(videos)} publicações: {dict(Counter(v['estado'] for v in indice))}")


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--candidatos", type=Path, default=Path(tempfile.gettempdir()) / "turismo-aqui-quadros",
                     help="Pasta com os candidatos por ID")
    cli.add_argument("--revisoes", type=Path, default=ACERVO / "revisoes-visuais")
    args = cli.parse_args()
    publicar(args.candidatos, args.revisoes, SAIDA)


if __name__ == "__main__":
    main()
