"""Gera o acervo de leitura do canal a partir das legendas arquivadas."""

import argparse
import json
import re
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACERVO = ROOT / "data/acervo/canal-turismo-aqui"
SAIDA = ROOT / "entregaveis/transcricoes-revisadas"
RECURSOS = ROOT / "producao/revisao_transcricoes"
LINHA = re.compile(
    r"^\| (Vídeo|Live) \| (\d\d/\d\d/\d{4}) \| ([\d:]+) \| "
    r"\[(.*?)\]\(<https://www\.youtube\.com/watch\?v=([\w-]{11})>\) \| "
    r"\[(.*?)\]\(<transcricoes/([^>]+)>\) \|"
)
LEGENDA = re.compile(r"^(\d+(?::\d\d){1,2})[ \t]+(.*)$")
SOM = re.compile(
    r"\[(?:música(?: e canto(?: até o fim da gravação)?)?|music|aplausos?|applause|risos?|risadas?|"
    r"laughter|silêncio|sons? ambientes?|roncando|limpando a garganta|"
    r"apresentação do festribal com música, canto e som ambiente)\.?\]", re.I,
)
INCERTO = re.compile(
    r"\[(?:trecho incerto|nome incerto|inaudível|ininteligível|fala indistinta|"
    r"trecho sem áudio audível|[^\]\n]+\btrecho indistinto)\.?\]", re.I,
)
FRASE = re.compile(r"(?<=[.!?…])\s+(?=[«“\"(—]*[A-ZÀ-Ü0-9])")
PALAVRA = re.compile(r"[^\W_]+(?:[-’'][^\W_]+)*", re.UNICODE)
CATEGORIAS = ("Local", "Comida", "Pessoa", "Tema")
TAGS_CONTEXTUAIS = {"local/para", "local/amazonas", "local/ana", "local/tucuma", "pessoa/joao-fona"}
DIAS_UTEIS = {"segunda", "terca", "quarta", "quinta", "sexta", "segundas", "tercas", "quartas", "quintas", "sextas"}
ESTADOS = {
    "lote": "Revisão em lote",
    "editorial": "Revisão editorial",
    "audio": "Transcrição recuperada do áudio",
    "silencio": "Áudio silencioso",
    "sem-fala": "Fala ausente na legenda",
    "pendente": "Legenda indisponível para revisão",
}


def normalizar(texto):
    """Chave de busca com acentos, caixa e hífens neutralizados."""
    letras = unicodedata.normalize("NFKD", texto.casefold())
    letras = "".join(letra for letra in letras if not unicodedata.combining(letra))
    return " ".join(re.findall(r"[a-z0-9]+", letras))


def catalogo():
    videos = []
    for linha in (ACERVO / "catalogo.md").read_text(encoding="utf-8-sig").splitlines():
        if not linha.startswith(("| Vídeo |", "| Live |")):
            continue
        capturas = LINHA.match(linha)
        if not capturas:
            raise ValueError(f"Linha de catálogo não reconhecida: {linha}")
        tipo, data, duracao, titulo, video, fonte, nome = capturas.groups()
        if not nome.startswith(video + "."):
            raise ValueError(f"Legenda divergente para {video}: {nome}")
        videos.append({
            "id": video, "titulo": re.sub(r"\\([|\[\]\\])", r"\1", titulo),
            "tipo": tipo, "data": datetime.strptime(data, "%d/%m/%Y").date().isoformat(),
            "duracao": duracao, "fonte": fonte, "arquivoOriginal": nome,
        })
    originais = {arquivo.name for arquivo in (ACERVO / "transcricoes").glob("*.txt")}
    if len({v["id"] for v in videos}) != len(videos) or originais != {v["arquivoOriginal"] for v in videos}:
        raise ValueError("Catálogo e pasta de legendas não correspondem um a um.")
    return videos


def segundos(marca):
    total = 0
    for campo in marca.split(":"):
        total = total * 60 + int(campo)
    return total


def blocos_da_legenda(caminho):
    """Agrupa a fala pelos intervalos das legendas e conserva mudanças de cena."""
    blocos, atual = [], []
    anterior = "", None
    for linha in caminho.read_text(encoding="utf-8-sig").splitlines():
        if not linha.strip():
            continue
        item = LEGENDA.fullmatch(linha.strip())
        if not item:
            raise ValueError(f"Legenda sem formato esperado em {caminho.name}: {linha[:90]}")
        marca, falado = item.groups()
        tempo = segundos(marca)
        falado = SOM.sub(" ", falado)
        falado = re.sub(r"[♪♫\u200b\ufeff]", " ", falado)
        falado = " ".join(falado.split())
        if not falado or (not atual and falado.casefold() in {"a", "e", "o", "ah", "é", "uh", "um"}):
            continue
        ultima_fala, ultimo_tempo = anterior
        if falado.casefold() == ultima_fala.casefold() and tempo - ultimo_tempo <= 3:
            continue
        if atual and tempo - ultimo_tempo >= 17:
            blocos.append(" ".join(atual))
            atual = []
        atual.append(falado)
        anterior = falado, tempo
    if atual:
        blocos.append(" ".join(atual))
    return blocos


def fracionar(texto, limite=132):
    palavras = texto.split()
    enquanto = 0
    while len(palavras) - enquanto > limite + 35:
        fim = enquanto + limite
        cortes = [i for i in range(fim - 35, fim + 1) if palavras[i - 1].endswith((".", "?", "!", "…"))]
        if cortes:
            fim = cortes[-1]
        else:
            conectores = ("agora", "aqui", "ali", "então", "olha", "bom", "enfim", "mas", "depois")
            cortes = [i for i in range(fim - 25, fim) if palavras[i].lower() in conectores]
            if cortes:
                fim = cortes[-1]
        yield " ".join(palavras[enquanto:fim])
        enquanto = fim
    if enquanto < len(palavras):
        yield " ".join(palavras[enquanto:])


def precisa_pontuacao(texto):
    palavras = len(texto.split())
    sinais = len(re.findall(r"[.!?…](?=\s|$)", texto))
    return palavras > 10 and sinais < max(1, palavras / 53)


def paragrafos(texto):
    frases = FRASE.split(texto.strip())
    partes, atual, n = [], [], 0
    for frase in frases:
        tamanho = len(frase.split())
        if atual and (n >= 85 or (n >= 42 and n + tamanho > 123)):
            partes.append(" ".join(atual))
            atual, n = [], 0
        atual.append(frase)
        n += tamanho
    if atual:
        partes.append(" ".join(atual))
    return partes


def pontuar_basico(texto):
    """Pontuação de apoio quando o modelo local está indisponível."""
    texto = re.sub(r"\b(olha só|bom|agora|então|pois é)(?=\s+(?:eu|a gente|aqui|vou|vamos|nós|hoje)\b)",
                   r"\1,", texto, flags=re.I)
    texto = re.sub(r"(?<![.!?…,])\s+(?=(?:olha só,|eu sou (?:Emanuel|Manoel)|nesse vídeo,|"
                   r"nesse canal,|é isso (?:aí|gente)\b|vamos (?:lá|comigo)\b))", ". ", texto, flags=re.I)
    texto = re.sub(r"(?<![.!?…,])\s+né(?=\s|$)", ", né?", texto, flags=re.I)
    return finalizar_pontuacao(texto)


def finalizar_pontuacao(texto):
    texto = re.sub(r"\s+([,.!?…])", r"\1", texto).strip(" ,;:")
    texto = re.sub(r"([.!?…]\s+)([a-zà-ü])", lambda m: m[1] + m[2].upper(), texto)
    if texto:
        texto = texto[0].upper() + texto[1:]
        if texto[-1] not in ".!?…]”\"":
            texto += "."
    return texto


def preservar_palavras(original, previsao):
    """Usa o modelo apenas para caixa e sinais; conserva a ortografia de entrada."""
    # O modelo pode separar um termo hifenizado ou perder um fragmento de
    # legenda. Alinhe palavras para aproveitar a pontuação nas regiões estáveis.
    atomo = r"[^\W_]+"
    originais = list(re.finditer(atomo, original))
    previstos = list(re.finditer(atomo, previsao))
    alinhamento = SequenceMatcher(
        None, [m[0].casefold() for m in originais], [m[0].casefold() for m in previstos],
        autojunk=False,
    )
    correspondencias = {a + i: b + i for a, b, tamanho in alinhamento.get_matching_blocks()
                       for i in range(tamanho)}
    if len(correspondencias) < len(originais) * .85:
        return pontuar_basico(original)
    saida = []
    for i, palavra in enumerate(originais):
        fim = originais[i + 1].start() if i + 1 < len(originais) else len(original)
        separador = original[palavra.end():fim]
        termo = palavra[0]
        if (j := correspondencias.get(i)) is not None:
            anterior = original[max(0, palavra.start() - 1):palavra.start()]
            if previstos[j][0][0].isupper() and termo[0].islower() and anterior not in {"-", "’", "'"}:
                termo = termo[0].upper() + termo[1:]
            if separador.isspace() and correspondencias.get(i + 1) == j + 1:
                proposto = previsao[previstos[j].end():previstos[j + 1].start()].strip()
                if proposto in {".", ",", "?", "!", ":"}:
                    separador = proposto + separador
        saida.extend((termo, separador))
    prefixo = original[:originais[0].start()] if originais else original
    return finalizar_pontuacao(prefixo + "".join(saida))


def preparar_modelo():
    from punctuators.models import PunctCapSegModelONNX

    return PunctCapSegModelONNX.from_pretrained("pcs_romance", ort_providers=["CPUExecutionProvider"])


def restaurar_pontuacao(videos, cache):
    cache.mkdir(parents=True, exist_ok=True)
    pendentes = [v for v in videos if v["arquivoOriginal"].endswith(".pt.txt")
                 and not (cache / (v["id"] + ".json")).is_file()]
    if not pendentes:
        return
    modelo = preparar_modelo()
    for indice, video in enumerate(pendentes, 1):
        publicado = ACERVO / "transcricoes" / video["arquivoOriginal"]
        blocos = [parte for bloco in blocos_da_legenda(publicado) for parte in fracionar(bloco)]
        indices = [i for i, bloco in enumerate(blocos) if precisa_pontuacao(bloco)]
        for offset in range(0, len(indices), 8):
            lote = indices[offset:offset + 8]
            previsoes = modelo.infer([blocos[i].lower() for i in lote], apply_sbd=False)
            for i, previsao in zip(lote, previsoes, strict=True):
                blocos[i] = preservar_palavras(blocos[i], previsao)
        destino = cache / (video["id"] + ".json")
        temporario = destino.with_suffix(".part")
        temporario.write_text(json.dumps(blocos, ensure_ascii=False), encoding="utf-8")
        temporario.replace(destino)
        if indice % 10 == 0 or indice in {1, len(pendentes)}:
            print(f"Pontuação: {indice}/{len(pendentes)} ({video['id']})", flush=True)


def revisar_pontuacao_residual(videos, cache):
    """Repontua blocos longos que ficaram sem divisões na primeira passagem."""
    corte = re.compile(r"[.!?…]\s")
    modelo = preparar_modelo()
    examinados = corrigidos = arquivos = 0
    for video in videos:
        video_id = video["id"]
        destino = cache / (video_id + ".json")
        if not destino.is_file() or (RECURSOS / "edicoes" / (video_id + ".txt")).is_file():
            continue
        blocos = json.loads(destino.read_text(encoding="utf-8"))
        indices = [i for i, bloco in enumerate(blocos)
                   if len(bloco.split()) >= 59 and not corte.search(bloco)]
        mudou = False
        for offset in range(0, len(indices), 10):
            lote = indices[offset:offset + 10]
            previsoes = modelo.infer([blocos[i].lower() for i in lote], apply_sbd=False)
            for i, previsao in zip(lote, previsoes, strict=True):
                proposta = preservar_palavras(blocos[i], previsao)
                examinados += 1
                if not corte.search(proposta):
                    proposta = re.sub(r", (?=(?:Vamos (?:em frente|devagar)|Vai ficar difícil|Mas é isso aí)\b)",
                                      ". ", proposta)
                if corte.search(proposta):
                    blocos[i] = proposta
                    corrigidos += 1
                    mudou = True
        if mudou:
            temporario = destino.with_suffix(".part")
            temporario.write_text(json.dumps(blocos, ensure_ascii=False), encoding="utf-8")
            temporario.replace(destino)
            arquivos += 1
            if arquivos % 25 == 0:
                print(f"Pontuação adicional: {corrigidos} blocos em {arquivos} vídeos.", flush=True)
    print(f"Pontuação adicional: {corrigidos}/{examinados} blocos em {arquivos} vídeos.", flush=True)


def linhas_dados(nome):
    for linha in (RECURSOS / nome).read_text(encoding="utf-8-sig").splitlines():
        if linha.strip() and not linha.lstrip().startswith("#"):
            yield [campo.strip() for campo in linha.split("|")]


class Vocabulario:
    def __init__(self):
        self.tags = {}
        self.por_termo = defaultdict(set)
        for grupo, nome, outros in linhas_dados("tags.txt"):
            chave = grupo.lower() + "/" + normalizar(nome).replace(" ", "-")
            if grupo not in CATEGORIAS or chave in self.tags:
                raise ValueError(f"Tag duplicada ou inválida: {grupo} / {nome}")
            self.tags[chave] = {"id": chave, "nome": nome, "grupo": grupo}
            nomes = [] if chave in TAGS_CONTEXTUAIS else [nome]
            termos = {normalizar(termo) for termo in (*nomes, *outros.split(",")) if termo.strip()}
            for termo in termos:
                self.por_termo[tuple(termo.split())].add(chave)
        self.tamanhos = sorted({len(termo) for termo in self.por_termo}, reverse=True)

    def ocorrencias(self, texto):
        chaves = Counter()
        palavras = normalizar(texto).split()
        proximos = {}
        for inicio in range(len(palavras)):
            for tamanho in self.tamanhos:
                fim = inicio + tamanho
                if fim > len(palavras):
                    continue
                termo = tuple(palavras[inicio:fim])
                for chave in self.por_termo.get(termo, ()):
                    if inicio < proximos.get(chave, 0):
                        continue
                    if (chave == "tema/feiras-e-mercados" and termo[0] in {"feira", "feiras"}
                            and inicio and palavras[inicio - 1] in DIAS_UTEIS):
                        continue
                    if chave == "comida/cafe" and termo in {("cafe",), ("cafes",)} and palavras[fim:fim + 2] == ["da", "manha"]:
                        continue
                    chaves[chave] += 1
                    proximos[chave] = fim
        if matches := len(re.findall(r"\bPará\b", texto, re.I)):
            chaves["local/para"] = max(chaves["local/para"], matches)
        return chaves

    def atribuir(self, video, corpo):
        titulo = self.ocorrencias(video["titulo"])
        fala_sem_vinheta = re.sub(
            r"\b(?:eu lembro )?(?:(?:que |[eo]sse |o )?(?:nosso )?canal )nasceu na amaz[oô]nia\b",
            "", corpo, flags=re.I,
        )
        fala = self.ocorrencias(fala_sem_vinheta)
        vinculos = {chave: "Título" for chave in titulo}
        exclusivos_do_titulo = {"tema/canal-turismo-aqui", "tema/transmissoes-ao-vivo"}
        for chave, total in fala.items():
            grupo = self.tags[chave]["grupo"]
            nome = self.tags[chave]["nome"]
            especifico = grupo == "Local" and len(nome.split()) >= 3 and chave != "local/regiao-norte-do-brasil"
            minimo = 2 if (grupo in {"Local", "Tema"} and not especifico) or chave == "comida/pescado" else 1
            if chave not in exclusivos_do_titulo and total >= minimo:
                vinculos[chave] = "Título e transcrição" if chave in vinculos else "Transcrição"
        for chave in titulo.keys() & fala.keys():
            vinculos[chave] = "Título e transcrição"
        if video["tipo"] == "Live":
            vinculos.setdefault("tema/transmissoes-ao-vivo", "Tipo de publicação")
        if "local/ponta-de-pedras-marajo" in vinculos and "local/santarem" not in titulo:
            vinculos.pop("local/ponta-de-pedras", None)
        if "local/guiana-francesa" in vinculos:
            contexto = normalizar(video["titulo"] + " " + fala_sem_vinheta).replace("guiana francesa", "")
            if not re.search(r"\bguiana\b", contexto):
                vinculos.pop("local/guiana", None)
        ordem = sorted(vinculos, key=lambda chave: (
            CATEGORIAS.index(self.tags[chave]["grupo"]), normalizar(self.tags[chave]["nome"]),
        ))
        return [{"id": chave, "evidencia": vinculos[chave]} for chave in ordem]


def carregar_grafias(vocabulario):
    grafias = {}
    ambiguas = {"Acre", "Amazonas", "Anã", "Breves", "Colares", "Guiana", "Pará", "Portel",
                "Soure", "São Marcos", "Amapá", "Carajás", "Porto Novo"}
    for tag in vocabulario.tags.values():
        nome = tag["nome"]
        if tag["grupo"] in {"Local", "Pessoa"} and "(" not in nome and nome not in ambiguas:
            grafias[nome.lower()] = nome
    for certo, outros in linhas_dados("grafias.txt"):
        for termo in (certo, *outros.split(",")):
            if termo.strip():
                grafias[termo.strip().casefold()] = certo
    termos = sorted(grafias, key=len, reverse=True)
    padrao = re.compile(r"(?<![\w/-])(?:" + "|".join(map(re.escape, termos)) + r")(?![\w/-])", re.I)
    return padrao, grafias


def editar_bloco(bloco, grafias):
    padrao, valores = grafias
    bloco = " ".join(SOM.sub(" ", bloco).split())
    bloco = padrao.sub(lambda m: valores.get(m[0].casefold(), m[0]), bloco)
    bloco = re.sub(r"\b(canal|site|marca)\s+(?:do\s+)?turismo[,.]?\s+aqui\b",
                   r"\1 Turismo Aqui", bloco, flags=re.I)
    bloco = re.sub(r"\b(meu nome é|eu sou)\s+(?:mano|humano|emano)\s+j[uú]nior"
                   r"(?=[,.]?\s+e\s+es[st]e\s+é\s+o\s+canal\b)",
                   r"\1 Emanuel Júlio", bloco, flags=re.I)
    bloco = re.sub(r"\b(meu nome é|eu sou)\s+(?:e mano|o mano|a manu|hermano|irmão do|irmã do)"
                   r"\s+(?:Emanuel )?j[uú]lio(?=[,.]?\s+e\s+es[st]e\s+é\s+o\s+canal\b)",
                   r"\1 Emanuel Júlio", bloco, flags=re.I)
    bloco = re.sub(r"\b(?:se\s+)?inscreva(?:-se)?\s+n(?:e|o)s?se canal\b",
                   "se inscreva neste canal", bloco, flags=re.I)
    bloco = re.sub(r"\b(santarém|belém|manaus),?\s+(pará|amazonas)\b",
                   lambda m: m[1].capitalize() + ", " + m[2].capitalize(), bloco, flags=re.I)
    bloco = re.sub(r"(?<![\d:])((?:[01]?\d|2[0-3])):([0-5]\d)(?![\d:])",
                   lambda m: f"{int(m[1])}h{m[2]}", bloco)
    bloco = re.sub(r"\b(\d{1,2}h[0-5]\d)\s+\1\b", r"\1", bloco)
    bloco = re.sub(r"\bpr(?:[,\s]+pr)*[,\s]+(?=pra\b|pro\b|pros\b|para\b)", "", bloco, flags=re.I)
    bloco = re.sub(r"\bpr(?=\s+gente\b)", "para a", bloco, flags=re.I)
    bloco = re.sub(r"\bpr(?=\s+(?:as?|os?|u(?:m|ma)|aqui|ali|lá|cá|frente|trás|direita|esquerda|"
                   r"você[s]?|nós|mim|te|fazer|ver|mostrar|chegar|passar|pegar|dar|ir|voltar|conhecer)\b)",
                   "para", bloco, flags=re.I)
    bloco = re.sub(r"\b(e aí)(?:[,.]?\s+\1){2,}\b", r"\1", bloco, flags=re.I)
    bloco = re.sub(r"\b(eh|é)(?:[,\s]+\1){2,}\b", r"\1", bloco, flags=re.I)
    bloco = re.sub(r"\b((?:a|de|do|da|o|os|as|que|no|na|um|uma|para|pra|com|e)\b)\s+\1\b",
                   r"\1", bloco, flags=re.I)
    bloco = INCERTO.sub("[trecho incerto]", bloco)
    bloco = re.sub(r"\[\s*_+\s*\]", "[palavra omitida na legenda]", bloco)
    return finalizar_pontuacao(bloco)


def ler_texto(video, cache, grafias):
    video_id = video["id"]
    original = ACERVO / "transcricoes" / video["arquivoOriginal"]
    editorial = RECURSOS / "edicoes" / (video_id + ".txt")
    recuperado = cache.parent / (video_id + ".pt-audio.txt")
    processado = cache / (video_id + ".json")
    if original.name.endswith(".sem-audio.txt"):
        return ("A gravação tem a faixa de áudio silenciosa durante toda a transmissão.", "silencio", "")
    if editorial.is_file():
        corpo = editorial.read_text(encoding="utf-8-sig").strip()
        estado = "editorial"
        nota = "Texto revisto a partir das legendas e referências do acervo."
        if original.name.endswith(".en.txt"):
            estado = "audio"
            nota = "Fala recuperada em português por reconhecimento do áudio, com revisão posterior do texto."
        if INCERTO.search(corpo):
            nota += " Os trechos assinalados como incertos precisam de conferência no áudio."
        return corpo, estado, nota
    if recuperado.is_file():
        blocos = blocos_da_legenda(recuperado)
        estado = "audio"
        nota = "A transcrição foi reconstituída em português a partir do áudio, com reconhecimento automático."
    elif original.name.endswith(".en.txt"):
        return ("A legenda disponível está corrompida. O conteúdo falado ainda precisa ser recuperado do áudio.",
                "pendente", "")
    else:
        estado = "lote"
        nota = ""
        if processado.is_file():
            blocos = json.loads(processado.read_text(encoding="utf-8"))
        else:
            blocos = [pontuar_basico(parte) for bloco in blocos_da_legenda(original) for parte in fracionar(bloco)]
    blocos = [editar_bloco(bloco, grafias) for bloco in blocos]
    if not blocos or not PALAVRA.search(INCERTO.sub("", " ".join(blocos))):
        return "A legenda disponível não contém falas identificáveis.", "sem-fala", ""
    corpo = "\n\n".join(paragrafo for bloco in blocos if PALAVRA.search(bloco) for paragrafo in paragrafos(bloco))
    if "[trecho incerto]" in corpo and not nota:
        nota = "Os trechos assinalados como incertos precisam de conferência no áudio."
    return corpo, estado, nota


def escrever_txt(video, corpo, vocabulario, nota):
    pasta = SAIDA / "txt"
    pasta.mkdir(parents=True, exist_ok=True)
    slug = normalizar(video["titulo"]).replace(" ", "-")[:76].rstrip("-")
    nome = f"{slug}--{video['id']}.txt"
    linhas = [video["titulo"], "", corpo, "", "Tags"]
    tags = [(vocabulario.tags[vinculo["id"]]["grupo"], vocabulario.tags[vinculo["id"]]["nome"])
            for vinculo in video["tags"]]
    for grupo in CATEGORIAS:
        nomes = [nome_tag for categoria, nome_tag in tags if categoria == grupo]
        if nomes:
            linhas.append(f"{grupo} — " + " · ".join(nomes))
    if not tags:
        linhas.append("Sem tags identificadas pelo vocabulário.")
    if nota:
        linhas.extend(("", "Nota editorial", nota))
    linhas.extend(("", "Vídeo de origem", "https://www.youtube.com/watch?v=" + video["id"], ""))
    gravar_texto(pasta / nome, "\n".join(linhas))
    return nome


def gravar_texto(caminho, conteudo):
    if caminho.is_file() and caminho.read_text(encoding="utf-8") == conteudo:
        return
    temporario = caminho.with_suffix(caminho.suffix + ".part")
    temporario.write_text(conteudo, encoding="utf-8")
    temporario.replace(caminho)


def publicar(videos, cache, exigir_modelo=False):
    if exigir_modelo:
        pendentes = [v["id"] for v in videos if v["arquivoOriginal"].endswith(".pt.txt")
                     and not (cache / (v["id"] + ".json")).is_file()]
        if pendentes:
            raise ValueError(f"Faltam {len(pendentes)} arquivos no cache de pontuação.")
    vocabulario = Vocabulario()
    grafias = carregar_grafias(vocabulario)
    notas_de_edicao = dict(linhas_dados("notas_edicoes.txt"))
    usadas = set()
    for video in videos:
        corpo, estado, nota = ler_texto(video, cache, grafias)
        nota = " ".join(filter(None, (nota, notas_de_edicao.get(video["id"]))))
        video["estado"] = estado
        video["trechosIncertos"] = len(INCERTO.findall(corpo))
        texto_para_tags = corpo if estado in {"lote", "editorial", "audio"} else ""
        video["tags"] = vocabulario.atribuir(video, texto_para_tags)
        video["txt"] = escrever_txt(video, corpo, vocabulario, nota)
        usadas.update(vinculo["id"] for vinculo in video["tags"])
    dados = {"videos": videos, "tags": [vocabulario.tags[chave] for chave in sorted(usadas)], "estados": ESTADOS}
    base = json.dumps(dados, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    gravar_texto(SAIDA / "painel.html", renderizar_painel(base))
    print(f"{len(videos)} TXTs, {len(usadas)} tags, "
          f"{sum(len(v['tags']) for v in videos)} associações.", flush=True)
    print(dict(Counter(v["estado"] for v in videos)), flush=True)
    print("Sem tags:", [(v["id"], v["titulo"]) for v in videos if not v["tags"]], flush=True)


def renderizar_painel(base):
    modelo = (RECURSOS / "painel.html").read_text(encoding="utf-8-sig")
    grafo = (RECURSOS / "grafo.js").read_text(encoding="utf-8-sig")
    for marcador, conteudo in (("<!-- BASE DO ACERVO -->", base), ("/* CÓDIGO DO GRAFO */", grafo)):
        if modelo.count(marcador) != 1:
            raise ValueError(f"Ponto de inserção do painel não encontrado: {marcador}")
        modelo = modelo.replace(marcador, conteudo)
    return modelo


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--pontuar", action="store_true")
    parser.add_argument("--revisar-pontuacao", action="store_true")
    parser.add_argument("--publicar", action="store_true")
    parser.add_argument("--exigir-modelo", action="store_true")
    args = parser.parse_args()
    registros = catalogo()
    if args.pontuar:
        restaurar_pontuacao(registros, args.cache)
    if args.revisar_pontuacao:
        revisar_pontuacao_residual(registros, args.cache)
    if args.publicar:
        publicar(registros, args.cache, args.exigir_modelo)
