#!/usr/bin/env bash
# Ежедневный pg_dump prod- и dev-баз. Хранит последние 30 файлов на каждую базу.
# DB_URL берётся из /opt/tg-community-bot/.env.prod и /opt/tg-community-bot/.env.dev.
set -euo pipefail

APP_DIR="/opt/tg-community-bot"
BACKUP_DIR="/root/tg-bot-backups"
mkdir -p "$BACKUP_DIR"

stamp="$(date +%Y%m%d-%H%M%S)"

dump_one() {
  local env_file="$1" name="$2"
  [[ -f "$env_file" ]] || { echo "[backup] нет $env_file — пропускаю"; return; }

  # Достаём DB_URL (формат postgresql+asyncpg://user:pass@host/dbname)
  local db_url
  db_url="$(grep -E '^DB_URL=' "$env_file" | head -n1 | cut -d= -f2-)"
  [[ -n "$db_url" ]] || { echo "[backup] DB_URL пуст в $env_file"; return; }

  # pg_dump хочет URL без +asyncpg
  local pg_url="${db_url/postgresql+asyncpg:\/\//postgresql:\/\/}"
  local out="$BACKUP_DIR/${name}-${stamp}.sql.gz"

  pg_dump --no-owner --no-privileges "$pg_url" | gzip -c > "$out"
  echo "[backup] $out"

  # Оставить только 30 последних
  ls -1t "$BACKUP_DIR/${name}-"*.sql.gz 2>/dev/null | tail -n +31 | xargs -r rm -f
}

dump_one "$APP_DIR/.env.prod" "prod"
dump_one "$APP_DIR/.env.dev"  "dev"
