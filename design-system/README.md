# Design system Turismo Aqui

Abra [o guia interativo](index.html) no navegador. Ele reúne a marca, a paleta, exemplos de componentes e um carrossel de destinos que responde a deslize, botões e teclado. Ao abrir o HTML direto da pasta, os links da marca e dos tokens abrem os arquivos em outra aba. O servidor local descrito no [README do projeto](../README.md) habilita o download pelos botões do guia.

## Identidade visual

- [PNG transparente](assets/turismo-aqui.png), 545 × 589 px. Use em aplicações raster e preserve a proporção.
- [SVG vetorial](assets/turismo-aqui.svg), com contornos preenchidos e editáveis. Use em interfaces e em tamanhos maiores.
- O [avatar público arquivado](../data/acervo/avatar-canal-referencia.jpg), de 900 × 900 px, foi a referência da vetorização. A transparência substitui o fundo branco e o recorte reduz as margens do avatar. As duas cores da assinatura são os valores RGB mais recorrentes no interior de cada conjunto de formas. O arquivo mestre da marca segue sem confirmação no [registro de procedência](../data/PESQUISA_E_PROCEDENCIA.md).
- Aplique a assinatura completa em fundo branco ou claro uniforme. Preserve uma área livre de pelo menos um quarto da largura do marcador ao redor da assinatura. Comece com 96 px de largura para aplicações que precisam manter “Aqui” legível.

## Cores de interface

| Aplicação | Fundo | Texto |
| --- | --- | --- |
| Ação principal | Azul-petróleo #217484 | Branco #FFFFFF |
| Destaque | Verde-amarelado #ABB737 | Grafite #182F31 |
| Leitura | Papel #F8F9F4 ou branco #FFFFFF | Grafite #182F31 ou secundário #4C6262 |
| Conteúdo de apoio | Verde-claro #EAF2EF | Grafite #182F31 |

Use as cores semânticas de informação, sucesso, alerta e erro com texto e ícone. Os valores estão em [tokens.json](tokens.json) e [tokens.css](tokens.css), com estados de interação, escala tipográfica, espaçamento, raios e sombras.

## Componentes

No HTML da aplicação, carregue [tokens.css](tokens.css), depois [components.css](components.css). Use a classe `ta` no elemento que envolve os componentes. O [guia](index.html) traz a marcação de botões, campos, filtros, alertas, cartões, modal e carrossel. O [script do guia](demo.js) traz os comportamentos da demonstração.

O azul-petróleo identifica a ação principal. Reserve o verde-amarelado para uma ação de destaque ou um estado selecionado. Mantenha foco visível, alvos interativos de 44 px e rótulos nos botões que exibem apenas ícones. Informe os erros próximos do campo e associe a mensagem ao campo correspondente.

Use Georgia nos títulos editoriais e a fonte do sistema nos controles e textos. A escala de espaçamento parte de 4 px, com cantos de 12 px nos controles e de 20 px nos cartões.

## Movimento e deslize

| Padrão | Duração | Aplicação |
| --- | --- | --- |
| Resposta de controle | 140 ms | Mudança de cor, borda ou indicador |
| Entrada de painel | 280 ms | Opacidade de 0 a 1 e deslocamento de 12 px |
| Transição de cena | 380 ms | Mudança de vista em aplicações do sistema |

O carrossel usa rolagem horizontal nativa com encaixe, setas, indicadores e contador. O gesto no toque segue a física de rolagem do navegador. Com a faixa em foco, use as setas do teclado, Home e End. O padrão de movimento reduzido aplica o estado final sem animação nas ações programadas, preservando a rolagem direta pelo usuário.

## Créditos dos exemplos

- Alter do Chão, fotografia de Rosanetur. [Arquivo e autoria](https://commons.wikimedia.org/wiki/File:Alter_do_Ch%C3%A3o_IMG_0682_(49694178436).jpg) · [CC BY 2.0](https://creativecommons.org/licenses/by/2.0/)
- Ilha do Amor, quadro do vídeo do Turismo Aqui aos 9:33. [Vídeo original](https://www.youtube.com/watch?v=i3hok4syuZw&t=573s)
- Rio Tapajós, ilustração conceitual gerada por IA para o projeto. [Caderno visual do piloto](../docs/CADERNO_VISUAL_PROVISORIO.md)
