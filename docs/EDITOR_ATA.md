# Editor de atas — escolhas em código aberto

A ata é escrita dentro do sistema, com formatação, estrutura e textos prontos, e depois segue para aprovação e assinatura
(o hash da assinatura cobre exatamente o texto aprovado). Este documento registra o que foi escolhido, por quê, e o que
ainda pode ser acrescentado.

## Comparativo de editores (só licenças compatíveis com o projeto MIT)

| Opção | Licença | Pontos fortes | Pontos fracos | Decisão |
|---|---|---|---|---|
| **Tiptap 2** (sobre ProseMirror) | **MIT** | modular, acessível, extensões prontas (listas, alinhamento, contador, menções), saída HTML limpa | extensões "Pro" são pagas (não usamos) | **Escolhido** |
| ProseMirror (puro) | MIT | base de tudo, controle total | muito baixo nível, mais código | usado indiretamente |
| Lexical (Meta) | MIT | rápido, bom suporte a acessibilidade | ecossistema menor, menos extensões | alternativa |
| Quill 2 | BSD-3 | simples, estável | modelo "Delta" próprio, menos flexível para estrutura | alternativa |
| Trix (Basecamp) | MIT | minúsculo | poucas opções, sem menções | descartado |
| Editor.js | Apache-2.0 | edição por blocos | saída JSON, menos natural para texto corrido | descartado |
| CKEditor 5 / TinyMCE 7 | GPL-2+ ou comercial | muito completos | licença incompatível com o MIT do projeto (ou paga) | **evitar** |

O editor é empacotado em **um único arquivo** (`static/vendor/editor-ata.js`, ~300 KB) gerado com esbuild a partir de
`tools/editor-ata/` — não depende de CDN nem de Node em produção. Para atualizar: `cd tools/editor-ata && npm install && npm run build`.
As licenças dos componentes estão em `static/vendor/editor-ata.LICENSES.txt`.

## O que já está implementado

- **Formatação**: título de seção, subtítulo, negrito, itálico, sublinhado, alinhamento (inclui justificado), listas, citação, linha, desfazer/refazer.
- **Estrutura da ata**: menu *Inserir seção* (Cabeçalho, Abertura, Leitura da ata anterior, Expediente, Ordem do dia, Palavra a bem da Ordem, Tronco de Beneficência, Encerramento) e painel lateral **Estrutura** para navegar pelos títulos.
- **`@` para inserir**: textos prontos cadastrados (com variáveis da sessão: data, Venerável, Secretário, presentes…) e **nomes de irmãos** (`Ir∴ Nome`).
- **Ditado por voz** em português (Web Speech API do navegador), tela cheia (foco), contador de palavras e verificação ortográfica do navegador (pt-BR).
- **Rascunho automático** neste computador (recupera se a aba fechar ou a energia cair) e `Ctrl+S` para salvar.
- **Segurança**: o HTML é sanitizado no servidor com **nh3** (MIT) — só tags de redação e alinhamento passam; nenhum script, evento ou estilo arbitrário chega ao banco, às telas ou aos PDFs. Atas antigas (texto simples) abrem no editor e continuam com o mesmo hash enquanto não forem editadas.
- **Versões**: cada ata aprovada é arquivada; há comparação entre versões linha a linha.
- **PDF** com o texto formatado, assinaturas, hash e QR Code.

## Complementos recomendados (código aberto) — próximos passos

| Recurso | Ferramenta | Licença | Observação |
|---|---|---|---|
| Correção gramatical em pt-BR | **LanguageTool** (servidor próprio) | LGPL-2.1+ | roda em Java/Docker; integra via API; os textos ficam na infraestrutura da Loja |
| Corretor ortográfico offline | **nspell** + dicionário Hunspell pt-BR | MIT / LGPL | alternativa leve ao corretor do navegador |
| Transcrição de voz sem enviar áudio a terceiros | **faster-whisper** / **whisper.cpp** | MIT | o ditado atual usa o serviço do navegador (Chrome/Edge enviam o áudio ao Google); esta opção mantém tudo local |
| Redação a várias mãos e comentários | **Yjs** + **y-prosemirror** + **Hocuspocus** | MIT | exige servidor WebSocket (Django Channels, BSD) |
| Sugestões/"controle de alterações" | **prosemirror-changeset** | MIT | útil para revisão pelo Orador/Venerável antes da aprovação |
| Tabelas (ex.: presença nominal, balancete) | `@tiptap/extension-table` | MIT | basta incluir no `build.mjs` e liberar `table/tr/td` no sanitizador |
| Comparação visual de versões (palavra a palavra) | **jsdiff** | BSD-3 | hoje a comparação é por linha (Python `difflib`) |
| Modelos de ata por tipo de sessão (magna, econômica, iniciação…) | recurso próprio | — | cadastrar modelos por categoria e pré-carregar ao criar a ata |

Sugestão de ordem: modelos por tipo de sessão → LanguageTool → transcrição local → redação colaborativa.
