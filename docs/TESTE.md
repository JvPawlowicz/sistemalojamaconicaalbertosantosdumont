# Roteiro de teste do sistema

## 1. Subir o sistema no seu computador (≈5 minutos)

**Passo 1 — baixar.** No GitHub, abra o repositório, escolha a branch `claude/loving-dirac-ot2k5c`, clique em **Code → Download ZIP** e
extraia a pasta. (Quem usa git: `git clone -b claude/loving-dirac-ot2k5c https://github.com/JvPawlowicz/sistemalojamaconicaalbertosantosdumont.git`.)

**Passo 2 — instalar o Python** (só uma vez), versão 3.11 ou mais nova: <https://www.python.org/downloads/>
(no Windows, marque **"Add python.exe to PATH"**).

**Passo 3 — iniciar** (o script cria tudo sozinho: ambiente, dependências, banco e dados de demonstração):

| Sistema | Como |
|---|---|
| **Windows** | dê **duplo clique** em `iniciar.bat` |
| **macOS / Linux / WSL** | no terminal, dentro da pasta: `bash iniciar.sh` |
| **Com Docker** (sem instalar Python) | `docker compose -f docker-compose.demo.yml up --build` (senha: `demo-teste-local`) |

Na primeira vez leva cerca de 1 minuto (instala as dependências). O navegador abre sozinho; se não abrir, acesse o endereço abaixo.
Para parar: `Ctrl+C` (ou feche a janela).

> **PDFs no Windows:** precisam do *GTK for Windows Runtime*. Sem ele, todo o resto funciona e as telas de PDF mostram um aviso explicando.
> No macOS: `brew install pango`. No Ubuntu/Debian: `sudo apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0`.

<details><summary>Instalação manual (sem o script)</summary>

```bash
python3 -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
printf 'DJANGO_DEBUG=1\nEXIGIR_2FA=0\n' > .env          # modo de teste (sem 2FA)
python manage.py migrate
python manage.py seed_inicial --demo                    # cria usuários e dados fictícios
python manage.py runserver
```
</details>

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
1. *Início → Nova sessão* (grau Aprendiz). A sessão abre como área de trabalho com abas. Em **Escala**, troque um cargo para testar a **substituição**.
2. Aba **Presença** (use "Marcar todos presentes"); *Concluir sessão* e veja *Agenda → Frequência*.
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
1. Na sessão, aba **Visitantes** → cadastre um visitante (com e-mail) → *Gerar certificados*.
2. *Assinar em lote* como `secretario` e como `veneravel` → *Enviar em lote* (PDF anexado no e-mail do terminal).
3. *Visitação → Registrar visita*: envie um PDF/imagem de certificado de outra loja e abra-o no visualizador.

**F. Cerimônias e candidatos**
1. *Candidatos → Nova proposta*; mova até **Aprovado** e use *Iniciar candidato* (cria o irmão Aprendiz).
2. Na sessão, aba **Cerimônias** → promover o Aprendiz a Companheiro; em Configurações defina um interstício e veja o bloqueio.

**F2. Novidades para conferir**
1. *Administração → Configurações*: preencha as **regras do regimento** (ex.: quórum 5, 3 faltas, multa 2%, juros 1%) e use **Enviar e-mail de teste** / **Testar WhatsApp**.
2. Aprove uma ata: os signatários recebem e-mail com o link para assinar. Crie uma **nova versão** e veja *Ata → Versões* (comparação).
3. Aba **Visitantes** → *Pré-autorizar assinatura*: assine antes e veja os certificados já saírem assinados ao gerar.
4. *Relatórios → Pacote do Conselho Fiscal* (como `tesoureiro`) e *Alertas do regimento*.
5. Foto do irmão (*Meu cadastro*) e brasão da Loja (*Configurações*) aparecem normalmente.
6. Faça um **backup** e **restaure** num banco vazio: `BACKUP_PASSPHRASE=x python manage.py backup_dados /tmp/bk`.

**G. Navegação** (confira os atalhos)
O **Início** lista o que precisa da sua atenção, cada item com botão direto. Pressione `Ctrl+K` (ou `/`) e busque um irmão, ata ou página.
O menu é uma **barra superior** com 8 seções (no celular vira botão ☰) e abas; conta e sair ficam em *Conta* (canto superior direito).

**G2. Ágape** (*Financeiro › Ágape*, perfil Tesoureiro)
1. *Novo Ágape* (ligue à sessão): todos os irmãos entram como "vai"; cada irmão pode marcar *Vou / Não vou* na própria tela. *Sincronizar* usa a presença da sessão.
2. Adicione **visitantes**: o custo é da loja. *Repassar* lança a despesa no caixa da loja e a entrada no **caixa do Ágape** (separado).
3. *Dar baixa* no rateio de cada irmão que vai; confira *Caixa do Ágape* e o *Inventário* (refrigerantes: estoque mínimo, compra com custo, consumo, ajuste).

**G3. Numeração das atas** — em *Configurações*, informe o **nº da primeira ata** (loja que já existe) e se a numeração reinicia por gestão. A ata aparece como `1287/2025-2026`.

**G4. Identidade visual e textos padrão**
*Configurações*: envie o **brasão/logo** (cabeçalho dos PDFs), a **marca d'água** (fundo de atas, certificados e convocações; ajuste a intensidade) e a **imagem de identidade** (ex.: busto de Santos Dumont, usada na entrada e na página inicial). Em *Atas › Modelos de texto* use **Carregar textos padrão** (28 textos prontos para o Secretário; digite `@` na ata).

**G5. PIX, conciliação, aniversários, busca em PDF e ajuda**
1. *Configurações*: informe a chave PIX. Em *Financeiro › Minhas mensalidades* clique em **PIX** (QR Code e copia e cola).
2. *Financeiro › Conciliação*: envie um extrato **OFX**; confira as sugestões e dê baixa nas marcadas (repetir o arquivo não duplica).
3. Ative o e-mail de parabéns em *Configurações* e rode `python manage.py enviar_lembretes`; o painel e a agenda mostram aniversários de vida e maçônicos.
4. *Biblioteca*: envie um PDF e busque por uma palavra do texto (o trecho aparece no cartão). `python manage.py extrair_textos` indexa PDFs antigos.
5. `GET /saude/` deve responder `{"status":"ok"}`. Menu da conta › **Ajuda e manuais** mostra o guia do seu perfil.

**H. Outros**
*Agenda* (+ exportar .ics), *Agenda social* (confirmar presença), *Expediente*, *Comissões*, *Patrimônio*,
*Relatórios* (PDF/XLSX/CSV), *Meus dados (LGPD)*, tema escuro / alto contraste / fonte maior (botões no topo) e a tela no celular.

## 3. O que reportar

Anote qualquer tela confusa, texto errado, regra que não bate com o regimento da Loja ou campo que falta.
