# Roteiro de teste do sistema

## 1. Subir o sistema no seu computador (≈5 minutos)

Requisitos: Python 3.11+ e, para gerar PDFs, as bibliotecas `pango`/`harfbuzz`
(Ubuntu/Debian: `sudo apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0`;
macOS: `brew install pango`; Windows: use o WSL).

```bash
git clone https://github.com/JvPawlowicz/sistemalojamaconicaalbertosantosdumont.git
cd sistemalojamaconicaalbertosantosdumont
git checkout claude/loving-dirac-ot2k5c
python3 -m venv .venv && . .venv/bin/activate        # Windows/WSL: igual
pip install -r requirements-dev.txt
printf 'DJANGO_DEBUG=1\nEXIGIR_2FA=0\n' > .env          # modo de teste (sem 2FA)
python manage.py migrate
python manage.py seed_inicial --demo                    # cria usuários e dados fictícios
python manage.py runserver
```

Abra <http://127.0.0.1:8000/> e entre com um dos usuários abaixo (senha de todos: `demo-senha-123`).

| Usuário | Perfil | Grau |
|---|---|---|
| `veneravel` | Venerável (todas as funções administrativas) | Mestre |
| `secretario` | Secretário (+ Administrador) | Mestre |
| `tesoureiro` | Tesoureiro | Mestre |
| `mestre` | Irmão | Mestre |
| `companheiro` | Irmão | Companheiro |
| `aprendiz` | Irmão | Aprendiz |

No primeiro acesso de cada usuário aparece o **termo de assinatura eletrônica** (aceite obrigatório).
Para testar o 2FA, apague `EXIGIR_2FA=0` do `.env` e entre como `tesoureiro`.
E-mails não saem de verdade: aparecem no terminal onde o servidor está rodando (configure `EMAIL_*` no `.env` para SMTP real).

Os testes automáticos rodam com `python -m pytest`.

## 2. Roteiro sugerido

**A. Cadastro e gestão** (como `secretario`)
1. *Irmãos → Novo irmão*: preencha dados, família, plano de saúde; confira a máscara de telefone/CPF.
2. *Cargos e gestão*: defina titulares do ano 2026/2027. Em *Configurações* ajuste dados da Loja e o catálogo de cargos.
3. *Irmãos → Importar planilha*: baixe o modelo, edite e use "Apenas validar" e depois "Importar".

**B. Sessão, presença e ata** (como `secretario`, depois `veneravel`)
1. *Sessões → Nova sessão* (grau Aprendiz). A escala é preenchida com os titulares; troque um cargo para testar a **substituição**.
2. *Presença*: marque presentes/ausentes; *Marcar como realizada* e veja *Sessões → Frequência*.
3. *Redigir ata*: digite `@` e escolha "Abertura dos trabalhos" (variáveis já preenchidas). Salve.
4. *Colocar em circulação* (e-mail aparece no terminal) → *Aprovar* escolhendo os signatários.
5. Entre como `veneravel` → *Assinar*: desenhe a assinatura (mouse/dedo), permita a localização, assine. Repita com `secretario`.
6. Abra o **PDF** da ata (cabeçalho, assinaturas, base legal, hash, QR Code) e a página pública `/verificar/<código>/`.
7. Tente editar a ata assinada (bloqueado) e use *Nova versão* (assinaturas anteriores deixam de valer).

**C. Visibilidade por grau**
1. Crie uma sessão de grau Mestre com ata. Entre como `aprendiz` e `companheiro`: a ata **não** aparece. Como `mestre`: aparece.
2. Em *Biblioteca*, envie um documento com "grau mínimo: Mestre" e confira o acesso de cada usuário. Abra um PDF no visualizador embutido.

**D. Tesouraria** (como `tesoureiro`)
1. *Categorias de irmão* (Integral R$ 150, Remido isento) e atribua aos irmãos.
2. *Mensalidades → Gerar mensalidades do mês*; dê **baixa** em uma (a receita entra no caixa) e **estorne**.
3. Teste **E-mail** e **WhatsApp** (abre `wa.me` com a mensagem pronta) na cobrança; lance uma *cobrança avulsa*.
4. *Caixa* (receita/despesa), *Orçamento* (previsto × realizado) e *Minhas mensalidades* como irmão comum.

**E. Visitação**
1. Na sessão: *Visitantes* → cadastre um visitante (com e-mail) → *Gerar certificados*.
2. *Assinar em lote* como `secretario` e como `veneravel` → *Enviar em lote* (PDF anexado no e-mail do terminal).
3. *Visitação → Registrar visita*: envie um PDF/imagem de certificado de outra loja e abra-o no visualizador.

**F. Cerimônias e candidatos**
1. *Candidatos → Nova proposta*; mova até **Aprovado** e use *Iniciar candidato* (cria o irmão Aprendiz).
2. Na sessão: *Cerimônias* → promover o Aprendiz a Companheiro; em Configurações defina um interstício e veja o bloqueio.

**G. Outros**
*Agenda* (+ exportar .ics), *Agenda social* (confirmar presença), *Expediente*, *Comissões*, *Patrimônio*,
*Relatórios* (PDF/XLSX/CSV), *Meus dados (LGPD)*, tema escuro / alto contraste / fonte maior (botões no topo) e a tela no celular.

## 3. O que reportar

Anote qualquer tela confusa, texto errado, regra que não bate com o regimento da Loja ou campo que falta.
