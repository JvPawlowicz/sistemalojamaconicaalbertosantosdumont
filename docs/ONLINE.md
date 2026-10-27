# Testar online (Render) — ≈10 minutos

> Ambiente **de teste**, com dados fictícios. Não cadastre dados reais dos irmãos nele.

1. Crie uma conta em <https://render.com> e conecte o GitHub (autorize o repositório `sistemalojamaconicaalbertosantosdumont`).
2. **New + → Blueprint**, escolha o repositório e a branch `claude/loving-dirac-ot2k5c` (ou a que estiver em uso). O Render lê o `render.yaml`
   e cria o banco PostgreSQL e o serviço web. O primeiro build leva alguns minutos.
3. Quando ficar "Live", abra a URL `https://sistema-da-loja-xxxx.onrender.com`.
4. A **senha** dos usuários de demonstração está em *sistema-da-loja → Environment → `DEMO_PASSWORD`*.
   Usuários: `veneravel`, `secretario`, `tesoureiro`, `mestre`, `companheiro`, `aprendiz` (roteiro em [`TESTE.md`](TESTE.md)).
5. HTTPS já vem ligado, então a **geolocalização da assinatura** funciona. E-mail: sem SMTP configurado as mensagens são
   apenas registradas; para receber de verdade, adicione `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` em *Environment*.

Observações do plano gratuito: o serviço "dorme" após ~15 min sem acesso (o primeiro acesso demora ~1 min), o banco gratuito expira
em ~30 dias e fotos/documentos enviados somem a cada novo deploy.

## Alternativas
- **No seu computador** (mais simples): [`TESTE.md`](TESTE.md).
- **VPS próprio** (uso real): `docker compose up -d` com HTTPS automático (Caddy) — ver `README.md`.
