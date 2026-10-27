# Sistema da Loja — Loja Maçônica Alberto Santos Dumont

Sistema de gestão e administração para a Loja (Rito Schröder, GLESP): irmãos, cargos e gestão por **ano maçônico**
(julho–junho), sessões e presença, **atas com assinatura eletrônica avançada** (hash, desenho, IP, geolocalização,
verificação pública), tesouraria, visitação (certificados em lote), biblioteca com visualizador embutido,
candidatos, comissões, expediente, patrimônio e relatórios (PDF, XLSX, CSV).

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
`apps/expediente` · `apps/comissoes` · `apps/relatorios`.

## Fora do escopo atual

Votação/escrutínio no sistema, sessão online (Jitsi) e integração bancária (PIX/boleto com baixa automática).
