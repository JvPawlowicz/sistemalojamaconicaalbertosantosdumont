# Escopo do Sistema — Loja Maçônica Alberto Santos Dumont

**Rito:** Schröder (alemão, quadro de cargos reduzido) · **Potência:** Grande Loja Maçônica do Estado de São Paulo (GLESP) · **Ano maçônico:** julho a julho
**Status:** rascunho v0.2 — base para desenho dos fluxos

## Premissas gerais

- Tudo integrado em uma única aplicação: agenda, sessão, ata, tesouraria, biblioteca, visitação.
- Visualização de PDF e imagens dentro do sistema (viewer embutido, sem sair da página).
- Acesso controlado por **grau** (Aprendiz, Companheiro, Mestre) e por **cargo/perfil**.
- Dados sensíveis (LGPD): trilha de auditoria, 2FA para cargos administrativos, backups criptografados.
- Tudo é associado a um **Ano Maçônico** (jul–jun), que serve de eixo para gestões, presença, orçamento e relatórios.
- Fora de escopo por ora: **Hospitalaria / Tronco de Beneficência**.

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
- Exportação em PDF com cabeçalho da loja, assinaturas e hash no rodapé.

> Nota: essa assinatura é uma assinatura eletrônica simples/avançada interna. Tem valor para uso da loja, mas não equivale a ICP-Brasil/gov.br; se a GLESP exigir isso para algum documento, tratamos como exceção.

## 5. Tesouraria

- Funciona como um **ERP financeiro** da loja.
- **Categorias de irmão** com regras de cobrança: integral, remido (isento) e outras que a loja definir; valor por categoria e por ano maçônico.
- Mensalidades e contribuições: geração automática, baixa, quitação, inadimplência.
- **Cobrança enviada pelo Tesoureiro dentro do sistema** (e-mail, e WhatsApp na integração), com segunda via, lembretes e histórico por irmão.
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
| Companheiro | Aprendiz e Companheiro *(a confirmar, ver questões em aberto)* |
| Mestre | todos os graus |
- 2FA para cargos administrativos; auditoria de acesso e alterações.

## 7. Candidatos (Propostas)

- Painel de acompanhamento: quem foi proposto, **por quem**, data, etapa atual.
- Etapas: proposta → sindicância (comissão e pareceres) → escrutínio → iniciação.
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

**Visitas realizadas**
- Registro de visitas feitas pelos irmãos a outras lojas.

## 11. Comunicação

- Avisos e convocações por e-mail; atas por e-mail.
- WhatsApp via API (certificados e avisos).

## 12. Relatórios

- Frequência por irmão/ano; quadro de obreiros; financeiro e orçamento; visitas recebidas/realizadas; candidatos; inventário.
- Exportação em PDF/planilha.

---

## Questões em aberto

### Decididas
- Potência: GLESP. Assinatura de ata: eletrônica interna com hash, canvas, IP, geolocalização e integridade; foto opcional. Mensalidade por categoria, com remidos e integral. Visibilidade de atas por grau.

### Ainda abertas
1. **Cargos do Rito Schröder:** qual a lista oficial de cargos da loja (para já cadastrar)?
2. **Companheiro:** você escreveu que ele vê "aprendiz e mestre". Imagino que seja Aprendiz e Companheiro (seu próprio grau e o inferior), certo? Um Companheiro não deveria ver atas de Mestre.
3. **Outros conteúdos por grau:** a regra "ver o próprio grau e os inferiores" vale também para biblioteca, documentos e presença?
4. **Cobrança:** o Tesoureiro só envia o aviso/cobrança, ou o sistema também deve gerar PIX/boleto com baixa automática (exige integração com banco ou gateway)?
5. **Ata por e-mail:** quem recebe a ata para aprovação, todos os irmãos do grau ou uma lista escolhida pelo Secretário? E o e-mail leva o texto no corpo, PDF anexo ou link para ler no sistema (recomendo o link, por segurança)?
6. **"Portaria" da assinatura digital:** entendi como um termo de aceite exibido no sistema. Se for um documento formal da loja (portaria/decreto do Venerável autorizando a assinatura digital), podemos anexá-lo e linkar no termo. Qual dos dois?
7. **Usuários:** quantos irmãos e quantas sessões por mês, aproximadamente?
8. **WhatsApp:** já há provedor de API em mente (Meta Cloud API, Twilio, Z-API etc.)?
9. **Stack:** confirmar Django + PostgreSQL.
