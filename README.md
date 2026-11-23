# Turismo Aqui — piloto de Alter do Chão

Vídeos do canal alimentam uma base editorial compartilhada pela Revista Turismo Aqui, pelo aplicativo de destinos e pelos materiais para redes sociais, leitura e vídeo. O blog reúne cinco artigos originais sobre turismo na região de Santarém, ilustrados pelo acervo do canal.

## Acessar a publicação

A [Central Turismo Aqui](https://brunodarwich.github.io/turismo-aqui/) reúne site, blog, aplicativo, acervo editorial, vídeos, peças sociais, ebook e documentação. Cada atualização da branch `main` gera uma publicação pelo GitHub Actions.

Os dois vídeos originais acima de 100 MiB estão na [Release Acervo original](https://github.com/brunodarwich/turismo-aqui/releases/tag/acervo-original), com links na seção **Materiais** da Central. Após baixar os arquivos, coloque o MP4 em `entregaveis/corte-turismo-aqui/` e o MOV em `entregaveis/terra-a-noite/` para recompor o acervo local.

## Abrir localmente

No Windows, abra o atalho **Turismo Aqui** da Área de Trabalho. Ele inicia o serviço em segundo plano e abre a **Central Turismo Aqui** no navegador padrão. Se o serviço já estiver aberto, o mesmo atalho reutiliza o endereço.

Para iniciar pelo terminal com Python 3.10 ou superior, execute na pasta raiz.

```powershell
python -m http.server 8000 --bind 127.0.0.1
```

- Central em [localhost:8000](http://localhost:8000/), com acesso aos produtos, ao acervo e aos materiais.
- Site institucional em [localhost:8000/site/](http://localhost:8000/site/) e revista em [localhost:8000/site/blog.html](http://localhost:8000/site/blog.html).
- App com mapa, busca e dicas em [localhost:8000/app/](http://localhost:8000/app/).
- [Ebook em PDF](entregaveis/guia-alter-do-chao-prototipo.pdf), [vídeo explicativo](entregaveis/guia-alter.webm) e [dez peças sociais](entregaveis/redes-sociais/).
- [Caderno de identidade](docs/CADERNO_VISUAL_PROVISORIO.md), [pesquisa e procedência](data/PESQUISA_E_PROCEDENCIA.md) e [guia de retomada](docs/PROJETO_E_RETOMADA.md).
- [Design system](design-system/index.html), com [logo em PNG transparente](design-system/assets/turismo-aqui.png), [logo em SVG](design-system/assets/turismo-aqui.svg), tokens e exemplos interativos.

Abra o site e o app pelo servidor da pasta raiz para que os dois encontrem a base. O mapa externo e os links do YouTube usam internet. A busca e o catálogo de lugares funcionam com o mapa indisponível.

## Consultar e atualizar o catálogo

O [catálogo completo do canal](data/acervo/canal-turismo-aqui/catalogo.md) reúne as publicações públicas com seus links, transcrições em TXT, playlists e links das descrições.

O [painel de transcrições](entregaveis/transcricoes-revisadas/painel.html) abre localmente no navegador e reúne os TXTs em texto corrido, a busca por tags, os gráficos de frequência e o grafo de coocorrência. No painel, cada publicação tem um link para o TXT e para o vídeo de origem.

O [catálogo visual](entregaveis/catalogo-visual/index.html) reúne os quadros aprovados com descrição, link para o instante do vídeo e contexto da transcrição. A galeria oferece busca por vídeo e lugar, exportação dos quadros em CSV e situação de revisão para cada publicação.

[A base JSON](data/base.json) é a fonte dos artigos, das dicas e das relações entre os vídeos e suas evidências. [As tabelas CSV](data/tabelas/) são geradas a partir dela. O [guia de operação editorial](docs/OPERACAO_EDITORIAL.md) explica importação, revisão e geração de materiais.

```powershell
python -B producao/validar_base.py
python -B producao/exportar_csv.py
python -B -m unittest discover -s producao -p test_acervo.py
```

O conteúdo com revisão pendente está identificado no catálogo. Preços de 2019 são históricos. Confira fontes, condições locais e direitos dos ativos antes de reutilizar os materiais em outra publicação.
