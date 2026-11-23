"""Importa SRT, VTT ou transcrição pública tabulada, preservando o original."""

import argparse
import hashlib
import html
import json
import re
import tempfile
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


BASE = Path(__file__).resolve().parents[1] / 'data' / 'base.json'
TEMPO = r'(?:\d{2,}:)?[0-5]\d:[0-5]\d[.,]\d{3}'
INTERVALO = re.compile(rf'^({TEMPO})\s+-->\s+({TEMPO})(?:\s+.*)?$')
TEMPO_PUBLICO = re.compile(rf'^(?:\d{{1,2}}:[0-5]\d|\d{{1,}}:[0-5]\d:[0-5]\d|{TEMPO})$')
ID_VIDEO = re.compile(r'[A-Za-z0-9_-]{11}')
MARCA_VTT = re.compile(r'</?(?:c(?:\.[^>\s]+)*|v|lang|b|i|u|ruby|rt)(?: [^>]*)?>|<\d{2}:\d{2}(?::\d{2})?\.\d{3}>')


def milissegundos(marcacao):
    relogio, _, fracao = marcacao.replace(',', '.').partition('.')
    segundos = 0
    for parte in relogio.split(':'):
        segundos = segundos * 60 + int(parte)
    return segundos * 1000 + int(fracao or '0')


def ler_legenda(texto, extensao):
    if extensao == '.txt':
        return ler_transcricao_publica(texto)

    blocos = re.split(r'\n[ \t]*\n+', texto.strip())
    if extensao == '.vtt':
        if not re.fullmatch(r'WEBVTT(?:[ \t][^\n]*)?', blocos[0].split('\n', 1)[0]):
            raise ValueError('Cabeçalho WEBVTT ausente.')
        blocos = blocos[1:]

    trechos = []
    for numero, bloco in enumerate(blocos, start=1):
        linhas = bloco.splitlines()
        if extensao == '.vtt' and re.match(r'^(?:NOTE(?:\s|$)|STYLE$|REGION$)', linhas[0]):
            continue
        indice = 0 if '-->' in linhas[0] else 1
        intervalo = INTERVALO.fullmatch(linhas[indice].strip()) if len(linhas) > indice else None
        fala = '\n'.join(linhas[indice + 1:]).strip()
        if not intervalo or not fala:
            raise ValueError(f'Bloco {numero} sem intervalo ou texto válido.')
        inicio, fim = map(milissegundos, intervalo.groups())
        if fim <= inicio:
            raise ValueError(f'Bloco {numero} tem fim anterior ou igual ao início.')
        trechos.append((inicio, fim, fala))
    if not trechos:
        raise ValueError('O arquivo não contém trechos.')
    return trechos


def ler_transcricao_publica(texto):
    trechos = []
    for numero, linha in enumerate(texto.splitlines(), start=1):
        if not linha.strip():
            continue
        tempo, _, fala = linha.partition('\t')
        if not TEMPO_PUBLICO.fullmatch(tempo.strip()) or not fala.strip():
            raise ValueError(f'Linha {numero}: use `tempo<TAB>texto` a partir da transcrição pública.')
        trechos.append((milissegundos(tempo.strip()), None, fala.strip()))
    if not trechos:
        raise ValueError('O arquivo não contém trechos.')
    return trechos


def url_trecho(url, inicio):
    original = urlsplit(url)
    parametros = [(chave, valor) for chave, valor in parse_qsl(original.query) if chave != 't']
    parametros.append(('t', f'{inicio // 1000}s'))
    return urlunsplit(original._replace(query=urlencode(parametros)))


def gravar_atomicamente(destino, dados):
    with tempfile.NamedTemporaryFile(dir=destino.parent, delete=False) as arquivo:
        temporario = Path(arquivo.name)
        try:
            arquivo.write(dados)
            arquivo.close()
            temporario.replace(destino)
        finally:
            arquivo.close()
            temporario.unlink(missing_ok=True)


@contextmanager
def bloquear(caminho):
    bloqueio = caminho.with_suffix(caminho.suffix + '.lock')
    try:
        marcador = bloqueio.open('x', encoding='utf-8')
    except FileExistsError as erro:
        raise ValueError(f'A base está em uso. Aguarde a outra importação: {bloqueio}') from erro
    try:
        marcador.close()
        yield
    finally:
        bloqueio.unlink()


def importar(caminho_base, video_id, arquivo, idioma, origem):
    extensao = arquivo.suffix.lower()
    if extensao not in {'.srt', '.vtt', '.txt'}:
        raise ValueError('Use um arquivo .srt, .vtt ou .txt tabulado.')
    if not ID_VIDEO.fullmatch(video_id) or not idioma.strip() or not origem.strip():
        raise ValueError('Informe o ID do vídeo, o idioma e a procedência da transcrição.')
    dados = arquivo.read_bytes()
    texto = dados.decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n')
    trechos = ler_legenda(texto, extensao)
    sha256 = hashlib.sha256(dados).hexdigest()

    with bloquear(caminho_base):
        base = json.loads(caminho_base.read_text(encoding='utf-8-sig'))
        video = next((item for item in base['videos'] if item['id'] == video_id), None)
        if video is None:
            raise ValueError(f'Vídeo {video_id} ausente na base.')
        transcricoes = base.setdefault('transcricoes', [])
        if any(item['video_id'] == video_id and item['sha256'] == sha256 for item in transcricoes):
            return 0

        transcricao_id = f'transcricao-{video_id}-{sha256}'
        relativo = Path('acervo') / 'transcricoes' / video_id / f'{sha256}{extensao}'
        destino = caminho_base.parent / relativo
        transcricoes.append({
            'id': transcricao_id, 'video_id': video_id, 'idioma': idioma.strip(),
            'origem': origem.strip(), 'data_consulta': date.today().isoformat(),
            'arquivo_original': relativo.as_posix(), 'sha256': sha256,
            'status_revisao': 'pendente',
        })
        registros = base.setdefault('trechos', [])
        for numero, (inicio, fim, fala) in enumerate(trechos, start=1):
            registros.append({
                'id': f'{transcricao_id}-{numero:04}', 'video_id': video_id,
                'transcricao_id': transcricao_id, 'inicio_ms': inicio, 'fim_ms': fim,
                'texto_original': fala, 'texto_revisado': None,
                'texto_normalizado': ' '.join(html.unescape(MARCA_VTT.sub('', fala)).split()),
                'falante_id': None, 'status_revisao': 'pendente',
                'url': url_trecho(video['url'], inicio),
            })
        if video.get('status_transcricao') in {None, 'não obtida', 'listada pelo player; texto não obtido'}:
            video['status_transcricao'] = 'importada, aguardando revisão'

        destino.parent.mkdir(parents=True, exist_ok=True)
        novo_original = not destino.exists()
        if novo_original:
            gravar_atomicamente(destino, dados)
        elif destino.read_bytes() != dados:
            raise ValueError(f'O original existente foi alterado: {destino}')
        try:
            gravar_atomicamente(caminho_base, (json.dumps(base, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
        except OSError:
            if novo_original:
                destino.unlink()
            raise
    return len(trechos)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--base', type=Path, default=BASE)
    cli.add_argument('--video-id', required=True)
    cli.add_argument('--arquivo', required=True, type=Path)
    cli.add_argument('--idioma', required=True, help='Idioma da faixa, por exemplo pt-BR.')
    cli.add_argument('--origem', required=True, help='URL e método, ou identificação do arquivo fornecido pelo canal.')
    args = cli.parse_args()
    try:
        total = importar(args.base, args.video_id, args.arquivo, args.idioma, args.origem)
    except (OSError, ValueError) as erro:
        cli.exit(1, f'{erro}\n')
    print(f'{total} trechos importados.' if total else 'Esta transcrição já está cadastrada.')


if __name__ == '__main__':
    main()
