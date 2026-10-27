#!/usr/bin/env bash
# Backup completo (dados + arquivos enviados), independente do banco, criptografado com BACKUP_PASSPHRASE.
# Uso (na pasta do projeto):  BACKUP_PASSPHRASE='senha-longa' ./deploy/backup.sh /caminho/destino
# Restaurar:  docker compose exec -T web python manage.py restaurar_dados /backup/ARQUIVO.tar.gz.enc --confirmar
# Agende no cron (ex.: todo dia 2h) e copie o resultado para FORA do servidor (outro disco/nuvem).
set -euo pipefail
destino="${1:?informe o diretório de destino}"
: "${BACKUP_PASSPHRASE:?defina BACKUP_PASSPHRASE}"
mkdir -p "$destino"
if command -v docker >/dev/null && [ -f docker-compose.yml ]; then
  docker compose exec -T -e BACKUP_PASSPHRASE="$BACKUP_PASSPHRASE" web python manage.py backup_dados /tmp/bk
  docker compose cp web:/tmp/bk/. "$destino/"
  docker compose exec -T web sh -c 'rm -rf /tmp/bk'
else
  python manage.py backup_dados "$destino"
fi
find "$destino" -name 'loja-backup-*' -mtime +60 -delete
echo "Backup concluído em $destino"
