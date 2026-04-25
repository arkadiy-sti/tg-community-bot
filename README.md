# tg-community-bot

Telegram-бот для сообщества **Co-Workers Bay Area** — площадки русскоязычных
handyman-исполнителей и заказчиков в Bay Area.

## Стек

- Python 3.11
- aiogram 3
- SQLAlchemy 2 (async) + SQLite (на старте), Alembic
- pydantic-settings
- wordcloud + Pillow — генерация PNG-облаков тегов

## Структура

```
bot/
  main.py            — точка входа
  config.py          — Settings (ENV_FILE → .env.prod / .env.dev)
  i18n.py            — RU/EN тексты + helper t(lang, key, **kwargs)
  texts.py           — старая шинель (плоские строки), оставлено для обратной совместимости
  db/                — модели и подключение
  handlers/          — common / welcome / admin / broadcast (+ скоро: register, post, feedback, subscription)
  services/          — captcha, antispam, broadcast (+ скоро: listings, ratings, tagcloud, subscriptions)
  keyboards/         — inline-клавиатуры
  middlewares/       — activity, antispam
deploy/
  bootstrap.sh                    — первичная установка на VPS
  deploy.sh                       — git pull + restart
  backup.sh                       — ежедневный SQLite-бэкап
  tg-community-bot.service        — systemd для prod
  tg-community-bot-dev.service    — systemd для dev
tests/                — pytest (capcha, antispam, broadcast, users, config)
```

## Деплой на VPS

Один раз:

```bash
ssh root@185.28.22.204
curl -fsSL https://raw.githubusercontent.com/arkadiy-sti/tg-community-bot/main/deploy/bootstrap.sh -o /tmp/bootstrap.sh
bash /tmp/bootstrap.sh
```

Скрипт спросит токены и ID, всё подключит и запустит оба сервиса (prod + dev).

Каждое обновление:

```bash
ssh root@185.28.22.204 'bash /opt/tg-community-bot/deploy/deploy.sh'
```

Логи:

```bash
journalctl -u tg-community-bot.service -f          # prod
journalctl -u tg-community-bot-dev.service -f      # dev
```

## Локальный запуск

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
# заполни BOT_TOKEN, ADMIN_IDS, CHANNEL_ID
ENV_FILE=.env python -m bot.main
```

## Тесты

```bash
pytest -q
```

## Лицензия

Внутренний проект.
