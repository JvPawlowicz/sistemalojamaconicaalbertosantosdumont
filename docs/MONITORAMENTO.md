# Monitoramento

## 1. Está no ar? — `/saude/`
`GET /saude/` responde `{"status":"ok"}` (HTTP 200) quando o sistema e o banco funcionam, ou HTTP 503 se o banco cair.
Não exige login nem mostra dados da Loja. O `Dockerfile` já usa esse endereço no `HEALTHCHECK`.

**Uptime Kuma** (gratuito, código aberto) — alerta por e-mail/Telegram quando cair:
```bash
docker run -d --restart=always -p 3001:3001 -v uptime-kuma:/app/data --name uptime-kuma louislam/uptime-kuma:1
```
Crie um monitor *HTTP(s)* para `https://SEU-DOMINIO/saude/` (intervalo de 60 s) e vincule o canal de notificação.

## 2. Erros do sistema — Sentry/GlitchTip (opcional)
```bash
pip install sentry-sdk          # ou adicione ao requirements.txt
export SENTRY_DSN="https://...@sentry.io/..."   # ou o DSN do seu GlitchTip
```
Sem a variável `SENTRY_DSN` nada é enviado. Dados pessoais não são enviados (`send_default_pii=False`).

## 3. Rotinas
- **Diária (cron):** `python manage.py enviar_lembretes` (lembretes de sessão, vencimentos, parabéns, cobrança).
- **Diária (cron):** `deploy/backup.sh` (backup criptografado). Teste a restauração a cada trimestre.
- **Após enviar PDFs antigos:** `python manage.py extrair_textos` (indexa a busca dentro dos PDFs).
