"""Exporta o catálogo editorial em CSVs UTF-8 com colunas estáveis."""

import argparse
import csv
import json
from pathlib import Path

from validar_base import BASE, validar


COLUNAS = {
    'videos': 'id titulo url data_publicacao duracao_segundos descricao status_transcricao fonte_ids',
    'lugares': 'id nome categoria descricao latitude longitude fonte_ids',
    'pessoas': 'id nome papel fonte_ids',
    'organizacoes': 'id nome papel video_ids fonte_ids',
    'temas': 'tema',
    'fontes': 'id titulo url tipo data_publicacao data_consulta',
    'transcricoes': 'id video_id idioma origem data_consulta arquivo_original sha256 status_revisao',
    'trechos': 'id video_id transcricao_id inicio_ms fim_ms texto_original texto_normalizado texto_revisado falante_id status_revisao url',
    'afirmacoes': 'id texto tipo status_verificacao video_id trecho_id fonte_ids',
    'cenas': 'id video_id inicio_ms fim_ms descricao status_revisao fonte_ids',
    'artigos': 'id categoria titulo resumo video_id secoes fonte_ids data_verificacao status_revisao',
    'dicas': 'id titulo texto lugar_id fonte_ids data_verificacao status_revisao',
    'ativos': 'id titulo tipo caminho autor licenca status_uso fonte_ids',
    'produtos': 'id titulo tipo caminho fonte_ids ativo_ids status',
}


def celula(valor):
    if isinstance(valor, list) and all(isinstance(item, str) for item in valor):
        return ' | '.join(valor)
    if isinstance(valor, (dict, list)):
        return json.dumps(valor, ensure_ascii=False)
    return valor


def exportar(caminho_base, destino):
    erros = validar(caminho_base)
    if erros:
        raise ValueError('\n'.join(erros))
    dados = json.loads(caminho_base.read_text(encoding='utf-8-sig'))
    destino.mkdir(parents=True, exist_ok=True)
    for colecao, colunas in COLUNAS.items():
        registros = dados.get(colecao, [])
        if colecao == 'temas':
            registros = [{'tema': tema} for tema in registros]
        campos = list(dict.fromkeys([*colunas.split(), *(campo for item in registros for campo in item)]))
        with (destino / f'{colecao}.csv').open('w', encoding='utf-8-sig', newline='') as arquivo:
            tabela = csv.DictWriter(arquivo, fieldnames=campos)
            tabela.writeheader()
            for item in registros:
                tabela.writerow({campo: celula(valor) for campo, valor in item.items()})


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--base', type=Path, default=BASE)
    cli.add_argument('--destino', type=Path)
    args = cli.parse_args()
    destino = args.destino or args.base.parent / 'tabelas'
    try:
        exportar(args.base, destino)
    except (OSError, ValueError) as erro:
        cli.exit(1, f'{erro}\n')
    print(f'Tabelas exportadas em {destino}')


if __name__ == '__main__':
    main()
