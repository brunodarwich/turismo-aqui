import csv
import json
import tempfile
import unittest
from pathlib import Path

from exportar_csv import exportar
from importar_legendas import importar
from validar_base import validar


class TesteAcervo(unittest.TestCase):
    video_id = 'pcdSgCIfEUw'

    def setUp(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        self.raiz = Path(pasta.name)
        self.base = self.raiz / 'base.json'
        url = f'https://www.youtube.com/watch?v={self.video_id}'
        self.gravar_base({
            'videos': [{'id': self.video_id, 'url': url, 'fonte_ids': ['video']}],
            'fontes': [{'id': 'video', 'url': url}],
        })

    def gravar_base(self, dados):
        self.base.write_text(json.dumps(dados), encoding='utf-8')

    def importar_arquivo(self, nome, dados):
        arquivo = self.raiz / nome
        arquivo.write_bytes(dados)
        return importar(self.base, self.video_id, arquivo, 'pt-BR', 'Arquivo sintético de teste')

    def ler_base(self):
        return json.loads(self.base.read_text(encoding='utf-8'))

    def test_srt_preserva_original_tempos_e_revisao(self):
        dados = '1\r\n00:00:01,250 --> 00:00:03,500\r\nUma fala sintética.\r\n'.encode('utf-8-sig')
        self.assertEqual(self.importar_arquivo('teste.srt', dados), 1)
        base = self.ler_base()
        original = self.raiz / base['transcricoes'][0]['arquivo_original']
        self.assertEqual(original.read_bytes(), dados)
        trecho = base['trechos'][0]
        self.assertEqual((trecho['inicio_ms'], trecho['fim_ms']), (1250, 3500))
        self.assertTrue(trecho['url'].endswith('&t=1s'))
        trecho['texto_revisado'] = 'Correção humana.'
        self.gravar_base(base)
        self.assertEqual(self.importar_arquivo('novo-nome.srt', dados), 0)
        self.assertEqual(self.ler_base()['trechos'][0]['texto_revisado'], 'Correção humana.')
        self.assertEqual(validar(self.base), [])
        original.write_bytes(b'texto substituido')
        self.assertTrue(any('original alterado' in erro for erro in validar(self.base)))

    def test_vtt_com_notas_identificador_e_configuracao(self):
        dados = b'WEBVTT\n\nNOTE teste\n\ncue-1\n00:01.250 --> 00:03.000 align:start\n<c>Rios &amp; praias</c>\n'
        self.assertEqual(self.importar_arquivo('teste.vtt', dados), 1)
        trecho = self.ler_base()['trechos'][0]
        self.assertEqual(trecho['texto_normalizado'], 'Rios & praias')
        self.assertIsNone(trecho['texto_revisado'])
        self.assertEqual(validar(self.base), [])

    def test_transcricao_publica_sem_fim_e_exportacao(self):
        self.assertEqual(self.importar_arquivo('teste.txt', b'0:05\tTeste\n1:02:03\tOutro teste'), 2)
        dados = self.ler_base()
        self.assertEqual([(t['inicio_ms'], t['fim_ms']) for t in dados['trechos']], [(5000, None), (3723000, None)])
        destino = self.raiz / 'tabelas'
        exportar(self.base, destino)
        with (destino / 'trechos.csv').open(encoding='utf-8-sig', newline='') as arquivo:
            self.assertEqual(len(list(csv.DictReader(arquivo))), 2)
        self.assertIn('inicio_ms', (destino / 'cenas.csv').read_text(encoding='utf-8-sig'))

    def test_entrada_invalida_mantem_base(self):
        anterior = self.base.read_bytes()
        with self.assertRaisesRegex(ValueError, 'fim anterior'):
            self.importar_arquivo('teste.srt', b'1\n00:00:05,000 --> 00:00:03,000\nTeste')
        self.assertEqual(self.base.read_bytes(), anterior)
        self.assertFalse((self.raiz / 'acervo').exists())

    def test_bloqueio_evitar_importacao_concorrente(self):
        self.base.with_suffix('.json.lock').touch()
        with self.assertRaisesRegex(ValueError, 'base está em uso'):
            self.importar_arquivo('teste.txt', b'0:05\tTeste')


if __name__ == '__main__':
    unittest.main()
