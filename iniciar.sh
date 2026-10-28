#!/usr/bin/env bash
# Prepara e inicia o sistema para TESTE local (macOS, Linux, WSL). Uso: ./iniciar.sh
set -e
cd "$(dirname "$0")"
PORTA="${PORTA:-8000}"
PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null || { echo "Python 3.11+ não encontrado. Instale em https://www.python.org/downloads/"; exit 1; }
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' || { echo "Precisa de Python 3.11 ou mais novo."; exit 1; }

if [ ! -d .venv ]; then echo "→ Criando ambiente virtual…"; "$PY" -m venv .venv; fi
# shellcheck disable=SC1091
. .venv/bin/activate
echo "→ Instalando dependências (só na primeira vez demora)…"
pip install -q --disable-pip-version-check -r requirements.txt

# modo de teste: sem 2FA, e-mails aparecem neste terminal
[ -f .env ] || printf 'DJANGO_DEBUG=1\nEXIGIR_2FA=0\n' > .env

echo "→ Preparando o banco de dados e os dados de demonstração…"
python manage.py migrate -v0
python manage.py seed_inicial --demo -v0

cat <<MSG

======================================================================
  Sistema da Loja pronto para teste
  Endereço:  http://127.0.0.1:${PORTA}/
  Usuários:  veneravel · secretario · tesoureiro · mestre · companheiro · aprendiz
  Senha de todos:  demo-senha-123
  (Pare o sistema com Ctrl+C. Roteiro de testes: docs/TESTE.md)
======================================================================

MSG
[ "${NAO_INICIAR:-0}" = "1" ] && exit 0
(sleep 3; (command -v xdg-open >/dev/null && xdg-open "http://127.0.0.1:${PORTA}/") || (command -v open >/dev/null && open "http://127.0.0.1:${PORTA}/") || true) >/dev/null 2>&1 &
exec python manage.py runserver "127.0.0.1:${PORTA}"
