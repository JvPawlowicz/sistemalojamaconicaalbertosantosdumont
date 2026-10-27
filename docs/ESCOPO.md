# Escopo do Sistema — Loja Maçônica Alberto Santos Dumont

**Rito:** Schröder (alemão) · **Ano maçônico:** julho a julho
**Status:** rascunho v0.1 — base para desenho dos fluxos

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
- **Gestão (titulares):** cada cargo (Venerável, 1º/2º Vigilante, Orador, Secretário, Tesoureiro, Chanceler, Mestre de Cerimônias, Cobridor etc.) é atribuído a um irmão para o ano.
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
- Estados: rascunho → pendente de assinatura → assinada/aprovada (imutável, com versionamento).
- Lista de signatários configurável (Secretário, Venerável e demais necessários); cada um assina no sistema.
- Envio da ata por e-mail aos irmãos; exportação em PDF.

## 5. Tesouraria

- Mensalidades e contribuições: geração, baixa, quitação, inadimplência.
- Caixa em tempo real (entradas e saídas).
- Despesas, contas a pagar/receber.
- **Orçamento (budget) por ano maçônico** com supervisão orçamentária: previsto × realizado por categoria.
- Relatórios mensais e prestação de contas.

## 6. Controle de Acesso

- Perfis: Administrador, Venerável, Secretário, Tesoureiro, Orador, Irmão (e outros a definir).
- Restrição de conteúdo **por grau** (documentos, atas, biblioteca, sessões).
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

1. **Potência/jurisdição:** a loja é filiada a qual (GOB, CMSB, Grande Loja estadual)? Define relatórios e nomenclatura.
2. **Particularidades do Rito Schröder:** quais cargos, nomes de sessões, graus e rituais diferem do quadro padrão que usei acima? Lista oficial de cargos?
3. **Assinatura da ata:** assinatura simples (login + registro) basta, ou precisa de assinatura digital (ICP-Brasil / gov.br)?
4. **Mensalidade:** valor único ou por categoria de irmão? Há remidos/isenções? Cobrança via boleto/PIX integrada ou só controle manual?
5. **Visibilidade entre graus:** Aprendiz vê a presença/ata de sessões de outros graus? Regras exatas por tipo de conteúdo.
6. **Usuários:** aproximadamente quantos irmãos e quantas sessões por mês (dimensiona infraestrutura)?
7. **WhatsApp:** já há provedor de API em mente (Meta Cloud API, Twilio, Z-API etc.)?
8. **Stack:** confirmar a escolha (sugestão: Django + PostgreSQL).
