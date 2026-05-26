#!/usr/bin/env bash
# backup_db.sh — ежедневный бэкап PostgreSQL для tg-community-bot
#
# Хранит последние 7 дней. Запускается через cron.
# Установка: см. README внизу файла.
#
# Структура файлов:
#   /opt/tg-community-bot/backups/tgbot_prod_YYYY-MM-DD.sql.gz

set -euo pipefail

# ── Настройки ────────────────────────────────────────────────────────────────
DB_HOST="localhost"
DB_PORT="5433"
DB_NAME="tgbot_prod"
DB_USER="bot_user"
DB_PASS="***REMOVED***"
BACKUP_DIR="/opt/backups/tg-community-bot"
KEEP_DAYS=7
# ─────────────────────────────────────────────────────────────────────────────

DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_FILE="${BACKUP_DIR}/tgbot_prod_${DATE}.sql.gz"
LOG_FILE="${BACKUP_DIR}/backup.log"

# Структура файлов:
#   /opt/backups/tg-community-bot/tgbot_prod_YYYY-MM-DD.sql.gz
#   /opt/backups/tg-community-bot/backup.log

mkdir -p "$BACKUP_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "=== Бэкап начат ==="

# pg_dump с паролем через переменную окружения (не через .pgpass)
if PGPASSWORD="$DB_PASS" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --format=plain \
    --no-password \
    | gzip -9 > "$BACKUP_FILE"; then

    SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
    log "OK: ${BACKUP_FILE} (${SIZE})"
else
    log "ОШИБКА: pg_dump завершился с кодом $?"
    exit 1
fi

# Удаляем бэкапы старше KEEP_DAYS дней
DELETED=$(find "$BACKUP_DIR" -name "tgbot_prod_*.sql.gz" -mtime +"$KEEP_DAYS" -print)
if [ -n "$DELETED" ]; then
    echo "$DELETED" | xargs rm -f
    log "Удалено старых бэкапов: $(echo "$DELETED" | wc -l)"
fi

# Показываем что хранится
log "Текущие бэкапы:"
ls -lh "${BACKUP_DIR}"/tgbot_prod_*.sql.gz 2>/dev/null | awk '{print "  " $5, $9}' | tee -a "$LOG_FILE"

log "=== Бэкап завершён ==="

# ── Установка cron (выполнить один раз вручную) ───────────────────────────
# chmod +x /opt/tg-community-bot/scripts/backup_db.sh
# (crontab -l 2>/dev/null; echo "0 3 * * * /opt/tg-community-bot/scripts/backup_db.sh") | crontab -
#
# Проверить: crontab -l
# Тест (запуск вручную): bash /opt/tg-community-bot/scripts/backup_db.sh
# Лог: tail -f /opt/backups/tg-community-bot/backup.log
# Список бэкапов: ls -lh /opt/backups/tg-community-bot/
#
# Восстановление из бэкапа:
#   gunzip -c /opt/backups/tg-community-bot/tgbot_prod_YYYY-MM-DD.sql.gz \
#   | PGPASSWORD=***REMOVED*** psql -h localhost -p 5433 -U bot_user -d tgbot_prod
