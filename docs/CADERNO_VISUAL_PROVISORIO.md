# Caderno de identidade visual do Turismo Aqui

## Marca do canal

![Logotipo Turismo Aqui publicado como avatar do canal](../data/acervo/avatar-canal-referencia.jpg)

O avatar público de 900 × 900 px reúne o contorno de uma câmera, um marcador azul-petróleo e a assinatura verde-amarelada “Aqui”. Essa é a versão usada como referência no protótipo local. A versão vetorial e as demais assinaturas da marca permanecem pendentes de confirmação. Consulta em 21 de novembro de 2026. [Canal Turismo Aqui](https://www.youtube.com/@TurismoAqui)

- Preserve as proporções, as cores e a assinatura do avatar. Use o fundo branco presente no arquivo de origem.
- Mantenha espaço livre ao redor da marca. No protótipo, use a assinatura completa em tamanho suficiente para ler “Aqui” e deixe as miniaturas representarem o vídeo ou o lugar.
- A abertura do ebook e o vídeo usam o avatar. Nos cards, a assinatura editorial em texto acompanha a peça e mantém o foco no assunto.

## Cores e tipografia

| Cor | Referência | Uso no piloto |
| --- | --- | --- |
| Azul-petróleo | #206E7D | Aproximação visual do marcador e do nome no avatar |
| Verde-amarelado | #A6B637 | Aproximação visual da assinatura “Aqui” |
| Verde profundo | #123C39 | Fundo de capa, títulos e destaque editorial |
| Areia | #E3C68F | Acentos e linhas sobre fundo escuro |
| Papel | #FBF6E9 | Fundo claro de leitura e texto sobre verde |

Os dois primeiros valores são aproximações da imagem digital pública. O verde profundo, a areia e o papel formam a paleta editorial de apoio. Use serifas de peso forte nos títulos do ebook e das peças, com Georgia ou DejaVu Serif nas imagens e Times no PDF. Use Arial, Helvetica ou outra fonte de sistema nas legendas e textos.

## Imagens e voz editorial

- A fotografia de Alter do Chão é de Rosanetur, tem enquadramento preservado nas aplicações e é creditada como registro documental externo. [Arquivo e autoria](https://commons.wikimedia.org/wiki/File:Alter_do_Ch%C3%A3o_IMG_0682_(49694178436).jpg) · [Licença CC BY 2.0](https://creativecommons.org/licenses/by/2.0/)
- O ebook apresenta Emanuel Júlio em um quadro do vídeo publicado pelo Turismo Aqui em 17 de novembro de 2019, aos 0:12. A imagem foi enquadrada para a página do guia local. [Quadro no vídeo de origem](https://www.youtube.com/watch?v=pcdSgCIfEUw&t=12s)
- A seção sobre o nível do Tapajós reúne dois quadros da Ilha do Amor. Um deles é a tomada aérea publicada pelo Turismo Aqui em 20 de setembro de 2019, aos 9:33. [Quadro no vídeo de origem](https://www.youtube.com/watch?v=i3hok4syuZw&t=573s)
- As ilustrações da canoa e do banco de areia são composições conceituais geradas por IA. Indique esse crédito junto de cada aplicação.
- Mostre cada quadro do acervo com vídeo de origem, tempo e crédito. Use os registros de procedência para confirmar o escopo de reutilização. [Procedência do acervo](../data/PESQUISA_E_PROCEDENCIA.md)
- Escreva em português brasileiro, com frases diretas e nomes locais conferidos. Oriente a consulta de horários, acesso e valores nas fontes responsáveis pela data da visita.

## Aplicações e reprodução

| Aplicação | Material | Arquivo de edição ou geração |
| --- | --- | --- |
| Identidade | Avatar do canal | [Referência raster](../data/acervo/avatar-canal-referencia.jpg) |
| Redes sociais | [Dez imagens quadradas](../entregaveis/redes-sociais) e [legendas](../producao/legendas-redes.md) | [Pautas](../producao/materiais.json) e [gerador das peças](../producao/gerar_materiais.py) |
| Ebook | [Guia de Alter do Chão](../entregaveis/guia-alter-do-chao-prototipo.pdf) | [Pauta e referências](../producao/guia_alter.json) e [diagramação](../producao/gerar_guia_alter.py) |
| Vídeo | [Guia em vídeo](../entregaveis/guia-alter.webm) e [legendas](../entregaveis/guia-alter.vtt) | [Roteiro e storyboard](../producao/roteiro-video.md), [composição e movimento](../producao/motion_guia.js) e [gerador](../producao/gerar_video.cjs) |

Execute os comandos na raiz do projeto:

```text
python producao/gerar_materiais.py
node producao/gerar_video.cjs
node producao/verificar_video.cjs
```

O gerador de imagens e PDF usa Pillow e ReportLab. A geração e a verificação do vídeo usam Node, Playwright e Chromium ou Chrome. Para escolher um navegador instalado, defina `TURISMO_BROWSER_EXECUTABLE` com o caminho do executável. A edição entregue usa a voz Microsoft Maria em português do Brasil e trilha instrumental sintetizada no código. Em máquinas sem uma voz brasileira SAPI disponível, o gerador produz a edição com texto em tela, legendas e trilha.

Para regenerar apenas o guia, execute `python producao/gerar_materiais.py --ebook-only`.

Para regenerar as peças quadradas, a galeria, a miniatura da Central e as legendas, execute `python producao/gerar_materiais.py --social-only`.

## Origem das ilustrações

**Canoa e margem do rio.** [Arquivo original do piloto](../producao/ilustracao.png)

> Create an editorial illustration for a Brazilian Amazon tourism guide, inspired generally by the Tapajós river landscape: wide calm river, pale sandy riverbank, lush forest in distance, small traditional wooden canoe, warm late afternoon light. Sophisticated contemporary gouache and subtle paper texture, rich teal, deep forest green and warm sand palette. Landscape composition with generous empty sky for later typography. This is a conceptual illustration, not an exact depiction of any real location. No people, no logos, no text, no watermark.

**Banco de areia.** [Arquivo gerado com a ferramenta integrada de imagem](../producao/ilustracao-banco-de-areia.png)

> Wide landscape editorial gouache illustration for Turismo Aqui, a Brazilian Amazon travel guide. A conceptual view over a sweeping pale sandbar and crystalline blue-green river beside lush riverside forest, viewed from an elevated viewpoint, late morning with soft clouds. Palette of deep forest #123c39, blue-green and warm sand #e3c68f. Sophisticated painterly travel editorial with delicate paper texture and distinct composition. Suggested by the Tapajós region while remaining deliberately non-documentary and without identifiable real landmarks. No people, no buildings, no text, no logos, no watermark.

