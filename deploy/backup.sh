#!/usr/bin/env bash
# Ежедневный бэкап SQLite-баз. Кладёт сжатые копии в /root/tg-bot-backups.
# Хранит последние 30 файлов на каждую базу.
set -euo pipefail

DATA_DIR="/opt/tg-community-bot/data"
BACKUP_DIR="/root/tg-bot-backups"
mkdir -p "$BACKUP_DIR"

stamp="$(date +%Y%m%d-%H%M%S)"

for db in "$DATA_DIR"/*.db; do
  [[ -f "$db" ]] || continue
  name="$(basename "$db" .db)"
  out="$BACKUP_DIR/${name}-${stamp}.db.gz"
  # .backup корректно копирует БД даже под нагрузкой (без блокировок)
  sqlite3 "$db" ".backup '/tmp/${name}.backup'"
  gzip -c "/tmp/${name}.backup" > "$out"
  rm -f "/tmp/${name}.backup"
  echo "[backup] $out"
  # Оставить только 30 последних
  ls -1t "$BACKUP_DIR/${name}-"*.db.gz 2>/dev/null | tail -n +31 | xargs -r rm -f
done
