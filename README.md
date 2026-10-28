# Sistema da Loja — Loja Maçônica Alberto Santos Dumont

Sistema de gestão e administração para a Loja (Rito Schröder, GLESP): irmãos, cargos e gestão por **ano maçônico**
(julho–junho), sessões e presença, **atas com assinatura eletrônica avançada** (hash, desenho, IP, geolocalização,
verificação pública), tesouraria, visitação (certificados em lote), biblioteca com visualizador embutido,
candidatos, comissões, expediente, patrimônio e relatórios (PDF, XLSX, CSV).

Também inclui: cerimônias (iniciação, promoção e elevação atualizam grau e datas, com interstício configurável),
iniciação direta a partir do candidato aprovado, agenda unificada (+ exportação .ics) e agenda social com confirmação
de presença, livro de atas em PDF, importação do quadro por planilha, painel de indicadores, direitos LGPD
(exportação dos próprios dados e solicitações) e lembretes automáticos.

Código aberto sob licença **MIT**. Escopo completo: [`docs/ESCOPO.md`](docs/ESCOPO.md).

## Stack

Django 5 · PostgreSQL (SQLite em desenvolvimento) · HTML/CSS/JS sem build (acessível, claro/escuro/alto contraste) ·
ícones Lucide (ISC) · WeasyPrint (PDF) · django-otp (2FA) · django-axes (bloqueio de força bruta) ·
django-simple-history (auditoria) · WhiteNoise.

## Rodando localmente

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # DJANGO_DEBUG=1 para desenvolvimento
python manage.py migrate
python manage.py seed_inicial   # cargos, categorias, modelos de texto, termo (use --demo para dados fictícios)
python manage.py createsuperuser   # cria o primeiro usuário (perfil Desenvolvedor)
python manage.py runserver
python -m pytest                # testes
```

PDFs (WeasyPrint) exigem as bibliotecas do sistema `pango` e `harfbuzz` (no Debian/Ubuntu: `libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0`).

Primeiros passos pelo navegador: entre como o usuário criado → **Configurações** (dados da Loja, termo, texto legal) →
**Categorias de irmão** (valor das mensalidades) → **Catálogo de cargos** → cadastre os irmãos (convite de senha por e-mail).

## Navegação (menos cliques e menos rolagem)

- **8 seções no menu** (antes eram 22 itens): Início, Agenda, Atas, Irmãos, Acervo, Financeiro, Relatórios e Administração.
  Cada seção tem **abas** (ex.: Irmãos → Quadro · Cargos e gestão · Candidatos · Comissões · Visitação). A definição fica
  em um só lugar: `apps/core/navegacao.py` (um teste garante que nenhuma tela fique "órfã").
- **Início = central de pendências**: o que precisa da sua atenção (assinar ata, redigir ata, cobrar, enviar convocação…)
  com botão direto para a ação, mais atalhos conforme o perfil.
- **Sessão como área de trabalho**: Resumo · Escala · Presença · Visitantes · Cerimônias · Ata em uma só página (abas).
- **Busca rápida** (`Ctrl+K` ou `/`): irmãos, atas, sessões, documentos, visitantes e páginas, respeitando grau e perfil.
- Formulários longos em **abas** (cadastro do irmão), **barra de salvar fixa**, filtros que aplicam sozinhos,
  "marcar todos presentes", "salvar e continuar editando" na ata, cabeçalho de tabela fixo. Conta (cadastro, LGPD, senha, sair) no menu do usuário.

## Rotinas automáticas

Agende diariamente (cron/systemd) para lembretes de sessão, marcação de mensalidades vencidas e cobrança semanal opcional:

```bash
0 8 * * *  cd /app && python manage.py enviar_lembretes      # em Docker: docker compose exec -T web python manage.py enviar_lembretes
```

Importação inicial do quadro: **Irmãos → Importar planilha** (modelo CSV disponível na própria tela; use "Apenas validar" antes).

## Qualidade e validações

- **Testes automatizados** (`python -m pytest`, ~80): regras, fluxos, permissões, 2FA de ponta a ponta, backup/restauração,
  integrações. Rodam em **SQLite e PostgreSQL 16** (`--ds=config.settings_pg_test`, ver CI).
- **Integrações exercitadas com servidores reais**: SMTP (aiosmtpd) e Evolution API (servidor HTTP simulado, formato do
  `sendMedia`). Em *Configurações* há botões para **testar o e-mail e o WhatsApp** antes de usar em produção
  (`python manage.py testar_email destino@x.org` também funciona).
- **Acessibilidade**: `tools/a11y_audit.js` roda o axe-core (WCAG 2.0/2.1/2.2 A/AA) em 32 telas × 3 temas — sem violações.
- **Produção verificada** com gunicorn + PostgreSQL + WhiteNoise + SMTP real (cadastro de 2FA, assinatura de ata, PDF).
- **Backup/restauração**: `python manage.py backup_dados DESTINO` (dados + arquivos, criptografado com `BACKUP_PASSPHRASE`) e
  `python manage.py restaurar_dados ARQUIVO --confirmar`; as assinaturas continuam íntegras após restaurar. Veja `deploy/backup.sh`.

## Regras do regimento (opcionais)

Em *Configurações*: limite de faltas consecutivas, frequência mínima, quórum mínimo, multa e juros de atraso, interstício
entre graus. Com `0` a regra fica desligada. Alertas aparecem no Início da Secretaria e em *Relatórios → Alertas do regimento*.

## Perfis e graus

| Perfil | Acesso |
|---|---|
| Irmão | cadastro próprio, conteúdo do seu grau (ou inferior), mensalidades próprias |
| Tesoureiro | tesouraria |
| Secretário | secretaria (cadastros, sessões, atas, visitas, documentos…) **e** funções de Administrador |
| Venerável | tudo de Secretário, Tesoureiro e Administrador |
| Desenvolvedor | acesso técnico total (painel `/admin/`), auditado |

Conteúdo de grau X é visível a irmãos de grau **igual ou superior** a X (Aprendiz < Companheiro < Mestre).
Perfis administrativos exigem **2FA (TOTP)**; todos aceitam o **termo de assinatura eletrônica** no primeiro acesso.

## Assinatura eletrônica das atas

Base legal impressa em toda ata/certificado: MP 2.200-2/2001 (art. 10, §2º) e Lei 14.063/2020 (art. 4º, II) — texto editável em
Configurações. Cada assinatura registra: usuário (com 2FA), desenho ou foto da assinatura, IP, dispositivo, data/hora,
geolocalização (se autorizada), hash SHA-256 do texto da ata e hash de integridade do próprio registro.
Qualquer alteração cria nova versão e invalida as assinaturas anteriores. A página pública `/verificar/<código>/`
confirma a autenticidade sem expor o conteúdo. **Recomenda-se validar o termo com um advogado.**

## Produção

`docker compose up -d` (PostgreSQL + app + Caddy com HTTPS automático). Veja [`docker-compose.yml`](docker-compose.yml),
[`deploy/Caddyfile`](deploy/Caddyfile) e [`deploy/backup.sh`](deploy/backup.sh) (backup criptografado). Em produção:
`DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY` forte, `PROXY_COUNT=1` atrás de proxy, SMTP configurado (`EMAIL_*`).
WhatsApp (certificados) é opcional via Evolution API (`EVOLUTION_*`); o canal principal é SMTP.

## Estrutura

`apps/core` (Loja, ano maçônico, termo, assinatura, e-mail) · `apps/irmaos` · `apps/cargos` · `apps/sessoes` ·
`apps/atas` · `apps/tesouraria` · `apps/visitas` · `apps/documentos` · `apps/candidatos` · `apps/patrimonio` ·
`apps/expediente` · `apps/comissoes` · `apps/relatorios` · `apps/votacoes` · `apps/hospitalaria` · `apps/agape`.

## Fora do escopo atual

Integração bancária automática (PIX/boleto com baixa automática).
