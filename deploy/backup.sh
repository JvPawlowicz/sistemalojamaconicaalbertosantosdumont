#!/usr/bin/env bash
# Backup do banco e dos arquivos enviados, criptografado com GPG (chave simétrica) ou restic.
# Uso: BACKUP_PASSPHRASE=... ./deploy/backup.sh /caminho/destino
set -euo pipefail
destino="${1:?informe o diretório de destino}"
data=$(date +%Y%m%d-%H%M)
mkdir -p "$destino"
docker compose exec -T db pg_dump -U "${DB_USER:-loja}" "${DB_NAME:-loja}" | gzip > "/tmp/loja-$data.sql.gz"
docker compose cp web:/app/media - | gzip > "/tmp/loja-media-$data.tar.gz"
for f in "/tmp/loja-$data.sql.gz" "/tmp/loja-media-$data.tar.gz"; do
  gpg --batch --yes --pinentry-mode loopback --passphrase "${BACKUP_PASSPHRASE:?defina BACKUP_PASSPHRASE}" -c -o "$destino/$(basename "$f").gpg" "$f"
  rm -f "$f"
done
find "$destino" -name 'loja-*.gpg' -mtime +60 -delete
echo "Backup concluído em $destino"
