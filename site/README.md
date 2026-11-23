# Site e blog — Turismo Aqui

Abra o atalho **Turismo Aqui** na Área de Trabalho ou inicie o servidor pela raiz conforme o [README do projeto](../README.md). A central fica em `/`, o site institucional em `/site/`, a revista em `/site/blog.html` e o aplicativo em `/app/`.

O site institucional e a revista usam `../data/base.json` para exibir as três matérias revisadas com data de publicação mais recente. O blog reúne as outras em **Mais do blog**. Abra uma matéria por endereço direto, como `/site/blog.html?artigo=roteiro-santarem`. Os endereços anteriores com `/site/?artigo=` redirecionam para a revista. O botão de voltar e a tecla Esc fecham o artigo.

A interface usa a marca, os tokens e os componentes de `../design-system/`. O site e a revista usam quadros locais do [catálogo visual](../entregaveis/catalogo-visual/index.html), com crédito e link temporal nas legendas. Em `ativo_ids`, o primeiro quadro é a capa. Uma seção pode usar `ativo_id` para exibir outro quadro da mesma matéria.

Rode `node producao/verificar_web.cjs` e `node producao/verificar_mobile.cjs` na pasta raiz com o servidor iniciado, Playwright e Chrome instalados. Para outros caminhos ou portas, use `TURISMO_AQUI_CHROME`, `TURISMO_AQUI_PLAYWRIGHT` e `TURISMO_AQUI_TEST_ORIGIN`.
