#!/bin/sh
# Inicialização do contêiner: migra, cria dados iniciais (e de demonstração se DEMO=1) e sobe o servidor.
set -e
python manage.py migrate --noinput
python manage.py seed_inicial
if [ "${DEMO:-0}" = "1" ]; then python manage.py seed_inicial --demo; fi
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers "${WEB_CONCURRENCY:-2}" --timeout 60
