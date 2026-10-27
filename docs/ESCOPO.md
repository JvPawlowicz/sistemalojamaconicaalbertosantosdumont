# Escopo do Sistema — Loja Maçônica Alberto Santos Dumont

**Rito:** Schröder (alemão, quadro de cargos reduzido) · **Potência:** Grande Loja Maçônica do Estado de São Paulo (GLESP) · **Ano maçônico:** julho a julho
**Status:** versão 1.0 candidata (escopo fechado, pendente de revisão final) — base para desenho dos fluxos

## Premissas gerais

- Tudo integrado em uma única aplicação: agenda, sessão, ata, tesouraria, biblioteca, visitação.
- Visualização de PDF e imagens dentro do sistema (viewer embutido, sem sair da página).
- Acesso controlado por **grau** (Aprendiz, Companheiro, Mestre) e por **cargo/perfil**.
- Dados sensíveis (LGPD): trilha de auditoria, 2FA para cargos administrativos, backups criptografados.
- Tudo é associado a um **Ano Maçônico** (jul–jun), que serve de eixo para gestões, presença, orçamento e relatórios.
- Fora de escopo por ora: **Hospitalaria / Tronco de Beneficência** e **votação/escrutínio no sistema**.
- A GLESP já tem sistema próprio de presença. Este sistema **não substitui nem integra** o da Potência: serve como **registro interno** da loja (a presença aqui é espelho para consulta, relatórios e frequência; pode-se exportar planilha para facilitar o lançamento na Potência).
- Escala: quadro de ~20 irmãos e ~4 sessões por mês.
- Licença do projeto: **MIT**. Só usar dependências com licença permissiva compatível (MIT, BSD, Apache-2.0, ISC); evitar GPL/AGPL.

---

## 1. Cadastro de Irmãos

| Bloco | Campos |
|---|---|
| Maçônicos | nome, nº de matrícula, grau, data de iniciação, data de promoção (elevação), data de exaltação, situação (ativo, licenciado, remido, falecido), histórico de cargos |
| Pessoais | endereço, telefones, e-mail, data de nascimento, contato de emergência |
| Família | nome da cunhada (esposa), filhos/filhas (nome, nascimento) |
| Profissionais | formação acadêmica, profissão, empresa/atuação |
| Saúde e previdência | plano de saúde, plano funeral (se houver) |
| Anexos | foto, documentos (PDF/imagem) |

Observação: campos de saúde/família têm visibilidade restrita (Venerável, Secretário e o próprio irmão).

## 2. Quadro de Oficiais e Cargos

- **Ano maçônico** como entidade: cria-se o ano (jul–jun) e dentro dele a gestão.
- **Gestão (titulares):** cada cargo é atribuído a um irmão para o ano. O **catálogo de cargos é configurável** (o Rito Schröder tem menos cargos que o quadro padrão); a lista oficial da loja será cadastrada no início, sem alterar código.
- **Escalação por sessão (substituição):** para cada sessão do calendário, o Venerável confirma quem ocupa cada cargo. Por padrão, o sistema pré-preenche com os titulares; se um titular faltar, o Venerável designa substituto apenas para aquela sessão.
- Histórico completo de quem exerceu cada cargo em cada sessão (alimenta currículo maçônico e relatórios).

## 3. Agenda e Sessões

**Fluxo da sessão:**
1. Agendamento no calendário (tipo: ordinária, magna, econômica, instrução, outras; grau da sessão).
2. Definição da **pauta** e do **expediente** do dia.
3. Convocação (e-mail; WhatsApp na fase de integração).
4. Escalação de cargos da sessão (item 2).
5. Realização: registro de presença (irmãos + visitantes).
6. Redação da ata (item 4).
7. Fechamento da sessão e cálculo de frequência.

**Presença:** por irmão, por sessão, por grau, com justificativa de ausência; percentuais por ano maçônico, por período e por tipo de sessão.

**Agenda da loja / social:** calendário único com sessões, ágapes, eventos e datas importantes.

## 4. Atas

- O Secretário redige a ata **dentro do sistema**; ela já é gerada com **cabeçalho da loja**.
- Estados: rascunho → **em circulação para aprovação** → aprovada na sessão → pendente de assinaturas → assinada (imutável, com versionamento).
- **Circulação para aprovação:** o Secretário envia a ata (por e-mail via SMTP ou apenas dentro do sistema) aos irmãos autorizados, para que ela possa ser lida e aprovada na sessão.
- Lista de signatários configurável (Secretário, Venerável e demais necessários).
- **Assinatura eletrônica no sistema**, com evidências:
  - desenho da assinatura em canvas (mouse/toque);
  - **hash** (SHA-256) do conteúdo da ata no momento da assinatura, para provar integridade;
  - IP, data/hora do servidor, user-agent e **geolocalização** (com consentimento do navegador);
  - registro vinculado ao usuário autenticado (login + 2FA);
  - **foto da assinatura opcional** (upload de imagem de assinatura de próprio punho);
  - página de verificação: qualquer pessoa autorizada confere se o PDF corresponde ao hash registrado.
- **Termo de aceite claramente exibido** antes de assinar, informando que a assinatura digital pelo sistema é válida para a loja e quais dados serão coletados (LGPD).
- Qualquer alteração depois de assinada gera nova versão e invalida as assinaturas anteriores.
- **Base legal:** MP 2.200-2/2001, art. 10, §2º, e Lei 14.063/2020, art. 4º, que admitem assinatura eletrônica **avançada** por meio diferente do certificado ICP-Brasil, desde que **aceita pelas partes**. O sistema coleta o **aceite expresso de cada irmão** (data, IP e hash do termo) no primeiro acesso.
- **Toda ata assinada pelo sistema sai com a fundamentação legal impressa** na página/bloco de assinaturas do PDF (texto configurável pelo administrador, com a MP 2.200-2/2001 e a Lei 14.063/2020 como padrão), junto com hash, QR Code de verificação e evidências de cada assinatura, para dar segurança jurídica ao ato. Recomenda-se validar o texto final com advogado.

**Biblioteca de modelos de texto (digitação rápida):**
- O Secretário pré-cadastra **cabeçalhos, abertura, encerramento, fórmulas e trechos padrão**, organizados por categoria e por tipo de sessão.
- Na digitação da ata, ao escrever `@` abre uma lista pesquisável; escolher o modelo insere o texto no ponto do cursor.
- Modelos aceitam **variáveis** preenchidas automaticamente: `{{data}}`, `{{grau}}`, `{{venerável}}`, `{{local}}`, `{{ano_maçônico}}`, `{{presentes}}`, `{{visitantes}}` etc.
- Cabeçalho oficial da loja (nome, número, oriente, brasão) é um modelo fixo aplicado a toda ata.

**Quem recebe a ata (por grau da sessão):** a ata de uma sessão de grau X é visível apenas para irmãos de grau **igual ou superior** a X. Como o Mestre é o último grau, ele acessa todas as atas.

| Ata da sessão de grau | Aprendiz | Companheiro | Mestre |
|---|---|---|---|
| Aprendiz | sim | sim | sim |
| Companheiro | não | sim | sim |
| Mestre | não | não | sim |

O envio por SMTP e a visibilidade dentro do sistema obedecem à mesma regra.
- Exportação em PDF com cabeçalho da loja, assinaturas e hash no rodapé.

> Nota: essa assinatura é uma assinatura eletrônica simples/avançada interna. Tem valor para uso da loja, mas não equivale a ICP-Brasil/gov.br; se a GLESP exigir isso para algum documento, tratamos como exceção.

## 5. Tesouraria

- Funciona como um **ERP financeiro** da loja.
- **Categorias de irmão** com regras de cobrança: integral, remido (isento) e outras que a loja definir; valor por categoria e por ano maçônico.
- Mensalidades e contribuições: geração automática, baixa, quitação, inadimplência.
- **Cobrança disparada pelo Tesoureiro dentro do sistema:** por e-mail (SMTP) e por **link `wa.me`** com a mensagem já preenchida (o Tesoureiro apenas clica e envia pelo próprio WhatsApp, sem API). Boleto: anexado ao lançamento (emitido fora do sistema). **Baixa sempre manual** pelo Tesoureiro; sem integração bancária.
- Status do lançamento: previsto, pago, pendente, vencido, isento, dispensado; recibo e **extrato por irmão** em PDF.
- Livro-caixa, despesas, contas a pagar e receber; relatório mensal e **pacote para a comissão de auditoria/Conselho Fiscal** no fim do ano maçônico.
- Caixa em tempo real (entradas e saídas).
- Despesas, contas a pagar/receber.
- **Orçamento (budget) por ano maçônico** com supervisão orçamentária: previsto × realizado por categoria.
- Relatórios mensais e prestação de contas.

## 6. Controle de Acesso

- Perfis: Administrador, Venerável, Secretário, Tesoureiro, Orador, Irmão (e outros a definir).
- Restrição de conteúdo **por grau** (documentos, atas, biblioteca, sessões).
- **Regra de visualização de atas:**

| Grau do irmão | Atas que pode ver |
|---|---|
| Aprendiz | somente do grau de Aprendiz |
| Companheiro | Aprendiz e Companheiro |
| Mestre | todos os graus |
- 2FA para cargos administrativos; auditoria de acesso e alterações.

## 7. Candidatos (Propostas)

- Painel de acompanhamento: quem foi proposto, **por quem**, data, etapa atual.
- Etapas: proposta → sindicância (comissão e pareceres) → resultado do escrutínio (apenas registrado) → iniciação.
- Documentos do candidato (anexos).

## 8. Biblioteca e Documentos

- Biblioteca digital organizada por categoria e **restrita por grau**.
- Visualizador embutido (PDF e imagens) sem sair da página.
- Regimento interno, pranchas/trabalhos, certificados e diplomas.

## 9. Patrimônio

- Inventário da loja (velas, livros, alfaias etc.): item, quantidade, estado, localização, responsável.
- Movimentações e baixas.

## 10. Visitação

**Visitantes recebidos**
- Cadastro do visitante na sessão, feito pelo irmão designado ou pelo Secretário.
- Alimenta um **banco de dados de visitantes** (reaproveitado em visitas futuras).
- **Certificado de visita** emitido e enviado por e-mail e WhatsApp (API).

**Visitas realizadas (certificados de outras lojas)**
- O certificado é emitido por **outra loja**. O Secretário **escaneia** (PDF ou imagem), envia ao sistema e **vincula ao irmão**, informando loja visitada, oriente, potência, data da sessão e grau da sessão.
- O arquivo abre dentro do sistema (visualizador embutido).
- Histórico de visitas por irmão e por período; contagem para relatórios e currículo maçônico.

## 11. Comunicação

- Avisos e convocações por e-mail; atas por e-mail.
- WhatsApp via API (certificados e avisos).

## 12. Relatórios

Todos exportáveis em **PDF e planilha (XLSX/CSV)**, com filtros por ano maçônico, período, grau e irmão, e com cabeçalho da loja.

**Secretaria**
- Frequência por irmão (percentual, faltas justificadas e não justificadas) e por sessão; ranking de assiduidade por ano maçônico.
- Quadro de obreiros (lista de irmãos por grau e situação) e quadro de oficiais por gestão.
- Atas: situação (rascunho, circulação, aprovada, assinadas/pendentes) e quem ainda não assinou.
- Aniversariantes do mês e aniversários maçônicos.
- Candidatos: propostos por quem, etapa atual, tempo em cada etapa.
- Cerimônias realizadas por ano (iniciações, promoções, elevações).
- Visitas realizadas e visitantes recebidos (por loja, por período).

**Tesouraria**
- Mensalidades: pagas, pendentes, vencidas, isentas; inadimplência por irmão e por mês; extrato individual.
- Fluxo de caixa; receitas e despesas por categoria; orçamento previsto × realizado.
- Prestação de contas e **pacote da comissão de auditoria** do ano maçônico.

**Patrimônio e biblioteca**
- Inventário por categoria, estado e responsável; empréstimos em aberto.

**Administração e segurança**
- Acessos e alterações (trilha de auditoria); usuários por perfil e último acesso; relatório de aceites do termo de assinatura.

**Painel de indicadores (dashboard)** com os principais números do ano maçônico: frequência média, inadimplência, saldo de caixa, pendências de assinatura e próximas sessões.

---

## 13. Graus e Cerimônias

Sequência fixa de graus: **Aprendiz → Companheiro → Mestre**.

| Cerimônia | Passagem de grau | Data registrada no cadastro |
|---|---|---|
| Iniciação | ingresso como Aprendiz | data de iniciação |
| Promoção | Aprendiz → Companheiro | data de promoção |
| Elevação | Companheiro → Mestre | data de elevação |

- A cerimônia é registrada **na sessão** em que ocorre e, ao ser concluída, atualiza o grau e a data do irmão automaticamente.
- Interstício mínimo entre graus configurável (a loja define; pode ficar vazio).
- Linha do tempo maçônica do irmão e aniversários maçônicos (iniciação, promoção, elevação).

## 14. Extras sugeridos

**Incluídos no escopo para fechar o sistema:**
- **Expediente (correspondências):** registro de documentos recebidos e enviados pela loja (com anexo e leitura no sistema), que alimenta o "expediente do dia" na pauta.
- **Numeração e livro de atas:** numeração sequencial e controle de livro/folha, com impressão para o livro físico, se a loja mantiver.
- **Comissões e Conselho Fiscal:** cadastro de comissões (sindicância, auditoria, eventos) com membros, prazo e parecer.
- **Configurações da loja:** nome, número, oriente, potência, brasão, cores, cabeçalho de documentos, categorias de irmão, catálogo de cargos, modelos de texto.
- **Termos e privacidade (LGPD):** política de privacidade, consentimento por irmão, solicitação de acesso/correção/exclusão de dados e registro de incidentes.
- **Trilha de auditoria** visível ao administrador.
- **Onboarding guiado:** primeiro acesso com troca de senha, 2FA, aceite do termo de assinatura e conferência dos dados pessoais.

**Opcionais (podem ficar para depois):**

- **Painel inicial** por perfil (também listado em Relatórios): próximas sessões, pendências de assinatura, mensalidades em aberto, aniversariantes.
- **Aniversariantes e datas maçônicas** com aviso automático.
- **Busca global** (irmãos, atas, documentos, visitantes).
- **Importação inicial** por planilha (CSV/XLSX) para migrar o quadro atual.
- **Sessão online/híbrida (futuro, fora do MVP):** link de videoconferência por sessão (Jitsi Meet, open source) e presença remota registrada. Módulo desativável, pois nem toda loja admite sessão remota.
- **Escrutínio/votação** de propostas (futuro; por ora fora do escopo, apenas registro do resultado).
- **Diretório de lojas** (nome, número, oriente, potência) para alimentar visitação.
- **Backup e exportação** completos dos dados (portabilidade e LGPD).
- **PWA:** instalável no celular, usado principalmente para presença e leitura de atas.

## 15. Requisitos técnicos e de experiência

- **Open source e extensível:** só componentes de código aberto; arquitetura em apps/plugins Django por módulo, ativáveis/desativáveis.
- **Localização pt-BR completa:** idioma, datas (dd/mm/aaaa), moeda (R$), fuso de São Paulo, máscaras e validação de CPF, CNPJ, CEP, telefone e RG.
- **Acessibilidade (WCAG 2.2 AA):** contraste alto, fonte ajustável, navegação por teclado, leitor de tela, modo escuro e modo alto contraste; pensado para público de idade variada.
- **Visual:** interface limpa, ícones consistentes (biblioteca Lucide), tema com identidade da loja (cores e brasão configuráveis).
- **E-mail:** envio preferencialmente por **SMTP** (configurável); fila de envio com registro de entregas e falhas.
- **WhatsApp:** via **Evolution API** (instância própria, número do Secretário conectado por QR); uso restrito a certificados e avisos pontuais, com SMTP sempre como canal principal e fallback. Observação: é uma integração não oficial baseada no WhatsApp Web, adequada para baixo volume.
- **Escala:** ~4 sessões/mês e quadro pequeno; basta uma instância simples (Docker Compose) com backup diário.
- **Visualizador embutido** de PDF e imagem (pdf.js) dentro da página, sem download obrigatório.

## 16. Análise de mercado (referência)

Levantamento web (informações de fabricantes e lojas de aplicativos, **não verificadas de forma independente**; vale pedir demonstração antes de copiar qualquer ideia):

| Sistema | O que declara oferecer |
|---|---|
| [Architect](https://apps.apple.com/br/app/architect/id6476198100) | ERP web e mobile para lojas e potências: membros e cargos, financeiro (mensalidades, fluxo de caixa), eventos, presenças e atas |
| [Maçonaria Virtual](https://apps.apple.com/py/app/ma%C3%A7onaria-virtual-mobile/id736701203) | chancelaria com frequência, extratos por membro, receitas e despesas, geração de boletos |
| [LIF](https://apps.apple.com/au/app/lif/id1529007170) | tesouraria, boletos, presenças, votação, ingressos; QR Code no certificado de presença |
| [The Working Tools](https://www.capterra.co.nz/software/1106688/The-Working-Tools) (Reino Unido) | membros, presença, geração de convocações e atas, livro-caixa, despesas, candidatos, backups em nuvem |
| [masonicfind](https://masonicfind.com/ai-masonic-lodge-management-software) (EUA) | mensalidade automática por membro, status (pago, pendente, vencido, isento, dispensado), recibos, ata em PDF |

**Funcionalidades que adotamos a partir dessa análise:**
- Extrato por irmão e recibos em PDF (tesouraria).
- Status financeiros detalhados, incluindo isento e dispensado.
- **QR Code de verificação** nos certificados de visita e em PDFs de ata (leva à página de conferência de autenticidade).
- Geração de **convocação** (summons) em PDF a partir da pauta.
- Acompanhamento de candidatos em painel.
- Backups automáticos.
- Pacote de documentos para a **comissão de auditoria** no fim do ano.

**Nossos diferenciais** (não aparecem de forma clara nos concorrentes encontrados): assinatura de ata com hash, evidências e verificação pública; modelos de texto com `@` na digitação; escalação de cargos por sessão com substituições; Rito Schröder e GLESP como padrão; visualizador embutido; código aberto (MIT).

## Stack proposta

Django 5 + PostgreSQL; HTMX + Alpine.js; Tailwind CSS (com DaisyUI); Lucide Icons; django-allauth + django-otp (login e 2FA); django-simple-history (auditoria); WeasyPrint (PDFs com cabeçalho); django-q2 ou Celery (envios agendados); pdf.js (viewer); Evolution API (WhatsApp); Jitsi Meet (opcional); Docker Compose.

---

## Questões em aberto

### Decididas
- Potência: GLESP (com sistema próprio de presença; o nosso é registro interno). Rito Schröder, cargos configuráveis. Graus: Aprendiz, Companheiro, Mestre (iniciação, promoção, elevação). Assinatura de ata eletrônica avançada com hash, canvas, IP, geolocalização e aceite expresso; foto opcional.
- Atas visíveis a irmãos de grau igual ou superior ao da sessão. Companheiro vê Aprendiz e Companheiro.
- Cobrança por e-mail e link `wa.me`, boleto externo, baixa manual. SMTP como canal principal; Evolution API só para certificados pelo WhatsApp do Secretário.
- Sem votação no sistema por ora. Sem sessão online por ora. Licença MIT. Django. ~20 irmãos, ~4 sessões/mês.

### Ainda abertas
1. **Texto da fundamentação legal:** aceita o texto padrão (MP 2.200-2/2001, art. 10, §2º, e Lei 14.063/2020, art. 4º) ou a loja já tem um texto/portaria própria a transcrever? Recomenda-se validação por advogado antes do uso oficial.
2. **Certificado de visita recebido (nosso para visitantes):** além de arquivar os certificados de outras lojas, vamos também **emitir** certificado para os visitantes que recebemos? Se sim: texto, assinante e se leva assinatura desenhada.
3. **Perfis de usuário:** além dos três graus, quais cargos terão poder administrativo (Venerável, Secretário, Tesoureiro, Chanceler, Orador)? Proposta: Secretário (atas, cadastros, visitas, documentos), Tesoureiro (financeiro), Venerável (escalação, leitura geral, assinatura), Administrador (configurações e usuários).
