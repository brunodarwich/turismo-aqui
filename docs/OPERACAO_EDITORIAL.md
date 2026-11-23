# Operação editorial do Turismo Aqui

## Dos vídeos aos produtos

1. Confirme data, duração, canal e reprodução na página do vídeo. Registre a origem e a data da consulta. No YouTube, use **Mostrar transcrição** na descrição para acessar o painel público quando o vídeo oferecer legenda.
2. Preserve o material coletado antes de editar. Para arquivos de legenda, mantenha SRT ou VTT original. Se o painel mostrar apenas início e texto, guarde a captura da estrutura original e prepare um TXT UTF-8 com uma linha `tempo<TAB>texto` por segmento, sem completar tempos ausentes.
3. Importe a faixa e revise grafias, pontuação e autoria contra a reprodução. Preencha `texto_revisado` após a conferência e indique o estado de revisão. Registre nomes ou falas incertos como pendentes. O texto normalizado automaticamente não passa por revisão humana.
4. Relacione trechos e cenas observadas por ID. Verifique afirmações em fontes públicas pertinentes. Guarde data, autoria e URL e explicite se a informação é histórica, confirmada, divergente ou pendente. Para uma imagem, registre também origem, licença e alterações.
5. Atualize matérias, dicas e fichas de produção usando IDs da base. Revise as saídas, execute os testes e anote no quadro de retomada os arquivos produzidos, a evidência da entrega e as lacunas remanescentes.

## Estrutura da base

| Coleção | Identificadores e relações |
| --- | --- |
| Vídeos, lugares, pessoas, organizações e temas | IDs dos vídeos do YouTube, IDs estáveis para entidades e listas de temas controladas pelo catálogo. Lugares podem ter coordenadas e nota da fonte. |
| Transcrições e trechos | Cada faixa aponta ao vídeo e a um original com SHA-256. Os trechos apontam à faixa, guardam início e fim em milissegundos e incluem link temporal. `fim_ms` aceita `null` quando a fonte só exibe o início. |
| Cenas e afirmações | Cena guarda vídeo, intervalo observado e descrição. Um quadro observado tem apenas a marcação temporal de captura. Afirmação guarda classificação, `fonte_ids` e, quando aplicável, `video_id` e `trecho_id`. Uma evidência escrita pode sustentar uma afirmação sem vínculo temporal. |
| Artigos e dicas | Matérias ligam `video_id`, `fonte_ids` e `trecho_ids` quando há citação ou evidência temporal. Dicas podem apontar a um lugar e registrar data de verificação. |
| Fontes, ativos e produtos | Fontes ligam títulos a URLs ou arquivos locais. Ativos registram procedência e situação de uso. Produtos referenciam as fontes e ativos usados. |

Filtre os CSVs por `video_id`, `lugar_ids`, `temas` ou `trecho_id`. As colunas de IDs permitem cruzar arquivos e rastrear um texto até a origem. Em registros com múltiplos IDs, o CSV usa ` | ` como separador. A edição é feita na base JSON.

## Importação reproduzível

Use um vídeo já catalogado, um arquivo UTF-8 e uma descrição de procedência que permita reencontrar o material.

```powershell
python -B producao/importar_legendas.py --video-id LhfExbCSfQY --arquivo C:\caminho\legenda.vtt --idioma pt --origem "Faixa fornecida pelo Turismo Aqui"
python -B producao/validar_base.py
python -B producao/exportar_csv.py
```

O importador preserva os bytes em `data/acervo/transcricoes/`, calcula SHA-256 e atualiza a base de forma atômica. Importar novamente o mesmo vídeo e arquivo é uma operação sem efeito. Uma versão diferente da faixa fica separada e pode ser comparada antes de mover referências editoriais. Faça as importações separadas de edições manuais da base. Se o processo for interrompido abruptamente, confira se ainda está em execução antes de remover um eventual `data/base.json.lock` residual.

## Verificação e reprodução

- Execute o servidor pela raiz e teste `/site/` e `/app/`. O README de cada produto descreve suas rotas e os testes locais.
- Os scripts de produção leem a base e os arquivos editoriais em `producao/`. Para exportar PDF e PNG, use Python com Pillow e ReportLab. Para o vídeo, use Node, Playwright e Chrome. Consulte os próprios scripts e o quadro de retomada para a ordem de geração e revisão.
- Confira as páginas do PDF renderizadas, as dez imagens e a reprodução do vídeo até o final com as legendas. Ao usar foto, quadro de vídeo, música ou depoimento, mantenha seus créditos e a situação de uso associados à peça.

## Catálogo visual do canal

O catálogo visual usa o [inventário público](../data/acervo/canal-turismo-aqui/catalogo.md) e seus TXTs com horários. Cada vídeo pode ser preparado e revisado individualmente. Os candidatos ficam em cache temporário e os quadros aprovados são copiados para a [galeria local](../entregaveis/catalogo-visual/index.html).

Use Python com `av`, `numpy`, `Pillow` e `yt-dlp[default]`, além de Node.js para o extrator do YouTube. A partir da raiz do projeto:

```powershell
$cacheQuadros = Join-Path $env:TEMP 'turismo-aqui-quadros'
python -B producao/capturar_quadros.py F6ACewul5Z4 --cache $cacheQuadros
python -B producao/catalogar_quadros.py --candidatos $cacheQuadros
```

Para preparar um novo lote, use `python -B producao/capturar_quadros.py --pendentes --limite 12`. O comando percorre o inventário na ordem do catálogo e pula as publicações já revisadas ou preparadas. Para distribuir a captura em paralelo, passe IDs diferentes a cada processo.

Abra as folhas de contato em `<cache>/<video_id>/` e amplie os candidatos duvidosos. Compare cenas e elimine repetições. Consulte a fala e o que aparece na imagem perto de cada tempo. Só atribua uma localização precisa quando a evidência corresponder à cena.

Salve uma revisão por ID em `data/acervo/canal-turismo-aqui/revisoes-visuais/`. Cada quadro usa `tempo_ms` do manifesto, `descricao`, `local`, `confianca` (`confirmado`, `provável` ou `não identificado`), `contexto` e `marcas` com os tempos de início da legenda em segundos inteiros. Use `local` vazio quando a localização for desconhecida. Use `marcas` vazia se o contexto não citar um ponto da transcrição. Registre em `fontes` os links externos usados para confirmar detalhes do quadro. Quando a seleção ficar abaixo de 10, informe o `motivo`. Para uma publicação indisponível, use `indisponivel: true`, `motivo` e `quadros: []`.

Se faltarem imagens em um vídeo, amplie a amostragem com `--samples 72` ou use `--cenas` para buscar perto de mudanças de cena. Esses modos preservam a primeira seleção em cache. A publicação valida os horários, as marcas da transcrição e os arquivos e reaproveita quadros aprovados de lotes anteriores.
