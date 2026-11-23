"""Verifica as referências e os registros de evidência do piloto."""

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit


BASE = Path(__file__).resolve().parents[1] / 'data' / 'base.json'
COLECOES = (
    'videos', 'fontes', 'pessoas', 'organizacoes', 'lugares', 'transcricoes', 'trechos',
    'afirmacoes', 'cenas', 'artigos', 'dicas', 'ativos', 'produtos',
)
REFERENCIAS = {
    'video_id': 'videos', 'video_ids': 'videos', 'fonte_ids': 'fontes',
    'transcricao_id': 'transcricoes', 'trecho_id': 'trechos', 'trecho_ids': 'trechos',
    'falante_id': 'pessoas', 'pessoa_ids': 'pessoas', 'lugar_id': 'lugares',
    'lugar_ids': 'lugares', 'cena_ids': 'cenas', 'afirmacao_ids': 'afirmacoes',
    'ativo_id': 'ativos', 'ativo_ids': 'ativos', 'artigo_ids': 'artigos', 'dica_ids': 'dicas',
    'organizacao_id': 'organizacoes',
}
COM_FONTES = ('videos', 'lugares', 'pessoas', 'organizacoes', 'afirmacoes', 'artigos', 'dicas', 'ativos', 'produtos')


def url_valida(url):
    if not isinstance(url, str):
        return False
    try:
        partes = urlsplit(url)
        return partes.scheme in {'http', 'https'} and bool(partes.hostname)
    except ValueError:
        return False


def validar(caminho):
    base = json.loads(caminho.read_text(encoding='utf-8-sig'))
    erros = []
    temas = base.get('temas', [])
    if not isinstance(temas, list) or any(not isinstance(tema, str) or not tema.strip() for tema in temas):
        erros.append('temas: esperada uma lista de nomes não vazios.')
        temas = []
    indices = {nome: {} for nome in COLECOES}
    for nome, indice in indices.items():
        registros = base.get(nome, [])
        if not isinstance(registros, list):
            erros.append(f'{nome}: esperada uma lista.')
            continue
        for item in registros:
            id_item = item.get('id') if isinstance(item, dict) else None
            if not isinstance(id_item, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', id_item):
                erros.append(f'{nome}: registro sem identificador válido.')
            elif id_item in indice:
                erros.append(f'{nome}: identificador duplicado {id_item}.')
            else:
                indice[id_item] = item

    for nome, indice in indices.items():
        for id_item, item in indice.items():
            chave = f'{nome}/{id_item}'
            if nome in COM_FONTES and not item.get('fonte_ids'):
                erros.append(f'{chave}: indique pelo menos uma fonte.')
            temas_item = item.get('temas', [])
            if not isinstance(temas_item, list) or any(tema not in temas for tema in temas_item):
                erros.append(f'{chave}: use temas definidos na base.')
            for campo, destino in REFERENCIAS.items():
                valor = item.get(campo)
                if valor is None:
                    continue
                valores = valor if campo.endswith('_ids') else [valor]
                if not isinstance(valores, list):
                    erros.append(f'{chave}: {campo} deve ser uma lista.')
                    continue
                for valor_id in valores:
                    if not isinstance(valor_id, str) or valor_id not in indices[destino]:
                        erros.append(f'{chave}: {campo} aponta para {valor_id!r} ausente em {destino}.')

            if nome in {'videos', 'trechos'} and not url_valida(item.get('url')):
                erros.append(f'{chave}: URL inválida.')
            if nome == 'fontes' and not url_valida(item.get('url')):
                raiz = caminho.parent.parent.resolve()
                local = item.get('caminho')
                destino = (raiz / local).resolve() if isinstance(local, str) else raiz
                if not destino.is_relative_to(raiz) or not destino.is_file():
                    erros.append(f'{chave}: informe URL válida ou arquivo local existente.')
            if nome in {'trechos', 'cenas'}:
                inicio, fim = item.get('inicio_ms'), item.get('fim_ms')
                if type(inicio) is not int or inicio < 0 or (
                    fim is not None and (type(fim) is not int or fim <= inicio)
                ) or (nome == 'cenas' and fim is None and item.get('tipo') != 'quadro observado'):
                    erros.append(f'{chave}: intervalo inválido.')
                if not item.get('video_id'):
                    erros.append(f'{chave}: vídeo ausente.')

            if nome == 'trechos':
                transcricao_id = item.get('transcricao_id')
                transcricao = indices['transcricoes'].get(transcricao_id) if isinstance(transcricao_id, str) else None
                if not transcricao or transcricao.get('video_id') != item.get('video_id'):
                    erros.append(f'{chave}: transcrição ausente ou de outro vídeo.')
            if nome == 'afirmacoes' and isinstance(item.get('trecho_id'), str):
                trecho = indices['trechos'].get(item['trecho_id'])
                if trecho and trecho.get('video_id') != item.get('video_id'):
                    erros.append(f'{chave}: trecho pertence a outro vídeo.')

    for item in indices['transcricoes'].values():
        relativo = item.get('arquivo_original')
        original = (caminho.parent / relativo).resolve() if isinstance(relativo, str) else caminho.parent.resolve()
        if not original.is_relative_to(caminho.parent.resolve()) or not original.is_file():
            erros.append(f"transcricoes/{item['id']}: arquivo original indisponível.")
        elif hashlib.sha256(original.read_bytes()).hexdigest() != item.get('sha256'):
            erros.append(f"transcricoes/{item['id']}: arquivo original alterado.")
    return erros


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--base', type=Path, default=BASE)
    args = cli.parse_args()
    try:
        erros = validar(args.base)
    except (OSError, ValueError) as erro:
        cli.exit(1, f'{erro}\n')
    if erros:
        cli.exit(1, '\n'.join(erros) + '\n')
    print('Referências e evidências da base verificadas.')


if __name__ == '__main__':
    main()
