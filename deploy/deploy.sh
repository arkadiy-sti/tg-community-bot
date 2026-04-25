#!/usr/bin/env bash
# Раскатывает свежий main: git pull → pip install → restart обоих сервисов.
# Запускать на VPS: bash /opt/tg-community-bot/deploy/deploy.sh
set -euo pipefail

APP_DIR="/opt/tg-community-bot"

cd "$APP_DIR"
echo "[deploy] git pull"
git pull --ff-only

echo "[deploy] pip install"
"$APP_DIR/.venv/bin/pip" install -q --upgrade pip wheel
"$APP_DIR/.venv/bin/pip" install -q -r requirements.txt

echo "[deploy] restart services"
systemctl restart tg-community-bot.service tg-community-bot-dev.service

sleep 2
systemctl --no-pager status tg-community-bot.service     | head -n 5
echo
systemctl --no-pager status tg-community-bot-dev.service | head -n 5
echo
echo "[deploy] done. Logs:"
echo "  journalctl -u tg-community-bot.service -n 30 --no-pager"
echo "  journalctl -u tg-community-bot-dev.service -n 30 --no-pager"
