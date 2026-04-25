#!/usr/bin/env bash
# Первоначальная установка tg-community-bot на чистой Ubuntu 22+ (VPS Hostinger).
# Запускать от root: bash bootstrap.sh
#
# Что делает:
#  1. Ставит python3.11, git, sqlite, build-essential.
#  2. Клонирует репозиторий в /opt/tg-community-bot (если ещё не клонирован).
#  3. Создаёт venv и ставит requirements.
#  4. Запрашивает у тебя prod- и dev-токены, ID канала, твой Telegram ID
#     и записывает в /opt/tg-community-bot/.env.prod и /opt/tg-community-bot/.env.dev.
#  5. Кладёт systemd-юниты, включает оба сервиса.
#  6. Прописывает cron на ежедневный бэкап SQLite.
#
# Перезапускать безопасно: пропустит шаги, которые уже сделаны.

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/arkadiy-sti/tg-community-bot.git}"
APP_DIR="/opt/tg-community-bot"
DATA_DIR="$APP_DIR/data"
BACKUP_DIR="/root/tg-bot-backups"
PY="python3.11"

log() { echo -e "\033[1;32m[bootstrap]\033[0m $*"; }
ask() {
  local prompt="$1" var="$2" default="${3:-}"
  if [[ -n "$default" ]]; then
    read -rp "$prompt [$default]: " val
    val="${val:-$default}"
  else
    read -rp "$prompt: " val
  fi
  printf -v "$var" "%s" "$val"
}
ask_secret() {
  local prompt="$1" var="$2"
  read -rsp "$prompt: " val; echo
  printf -v "$var" "%s" "$val"
}

if [[ $EUID -ne 0 ]]; then
  echo "Запусти от root: sudo bash $0" >&2
  exit 1
fi

# 1. Пакеты
log "Устанавливаю apt-пакеты"
apt-get update -qq
apt-get install -y -qq software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa >/dev/null 2>&1 || true
apt-get update -qq
apt-get install -y -qq \
  python3.11 python3.11-venv python3.11-dev \
  git sqlite3 build-essential libjpeg-dev zlib1g-dev curl

# 2. Репозиторий
if [[ ! -d "$APP_DIR/.git" ]]; then
  log "Клонирую репо в $APP_DIR"
  git clone "$REPO_URL" "$APP_DIR"
else
  log "Репо уже на месте — git pull"
  git -C "$APP_DIR" pull --ff-only
fi

mkdir -p "$DATA_DIR" "$BACKUP_DIR"

# 3. Виртуальное окружение
if [[ ! -d "$APP_DIR/.venv" ]]; then
  log "Создаю venv"
  $PY -m venv "$APP_DIR/.venv"
fi
log "Ставлю зависимости"
"$APP_DIR/.venv/bin/pip" install -q --upgrade pip wheel
"$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

# 4. .env файлы
write_env() {
  local file="$1" token="$2" profile="$3"
  cat > "$file" <<EOF
BOT_TOKEN=$token
BOT_PROFILE=$profile
ADMIN_IDS=$ADMIN_IDS
CHANNEL_ID=$CHANNEL_ID
MAIN_CHAT_ID=$CHANNEL_ID
DEFAULT_LANG=ru
DB_URL=sqlite+aiosqlite:///$DATA_DIR/bot${profile_suffix}.db
CAPTCHA_TIMEOUT_SEC=60
RATE_LIMIT_MSGS=5
RATE_LIMIT_WINDOW_SEC=10
NEW_USER_HOURS=24
MAX_WARNINGS=3
LOG_LEVEL=INFO
EOF
  chmod 600 "$file"
}

if [[ ! -f "$APP_DIR/.env.prod" || ! -f "$APP_DIR/.env.dev" ]]; then
  log "Заполни .env (.env.prod и .env.dev)"
  ask "Твой Telegram user ID (ADMIN_IDS)" ADMIN_IDS "125293998"
  ask "ID канала/группы для публикаций (CHANNEL_ID, формат -100...)" CHANNEL_ID "-1002186030111"
  ask_secret "PROD BOT_TOKEN (от @BotFather, для C0w0rker_bot)" BOT_TOKEN_PROD
  ask_secret "DEV  BOT_TOKEN (для C0w0rker1_bot)"               BOT_TOKEN_DEV

  profile_suffix="" ; write_env "$APP_DIR/.env.prod" "$BOT_TOKEN_PROD" "prod"
  profile_suffix="-dev" ; write_env "$APP_DIR/.env.dev"  "$BOT_TOKEN_DEV"  "dev"
  log ".env.prod и .env.dev записаны (chmod 600)"
else
  log ".env-файлы уже существуют — пропускаю"
fi

# 5. systemd
log "Кладу systemd-юниты"
install -m 644 "$APP_DIR/deploy/tg-community-bot.service"     /etc/systemd/system/tg-community-bot.service
install -m 644 "$APP_DIR/deploy/tg-community-bot-dev.service" /etc/systemd/system/tg-community-bot-dev.service
systemctl daemon-reload
systemctl enable --now tg-community-bot.service tg-community-bot-dev.service

# 6. Cron бэкап
if ! crontab -l 2>/dev/null | grep -q "tg-bot-backup"; then
  log "Добавляю cron-бэкап в 03:00"
  ( crontab -l 2>/dev/null; echo "0 3 * * * $APP_DIR/deploy/backup.sh # tg-bot-backup" ) | crontab -
fi

log "Готово!"
echo
echo "Статус сервисов:"
systemctl --no-pager status tg-community-bot.service     | head -n 5
echo
systemctl --no-pager status tg-community-bot-dev.service | head -n 5
echo
echo "Логи:    journalctl -u tg-community-bot.service -f"
echo "Деплой:  $APP_DIR/deploy/deploy.sh"
