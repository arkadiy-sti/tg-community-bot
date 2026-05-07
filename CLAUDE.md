# Co-Workers Bay Area — Claude project context

> **Прочти этот файл ПЕРВЫМ перед любой работой.**
> Если нужна история чата сверх того что здесь — спроси у Аркадия.
> Этот файл обновляется в конце каждого значимого блока работы.

_Последнее обновление: 2026-05-07 (Customer-роль вместо Guest: 3-шаговая регистрация, упрощённый /post 7 шагов, гейтинг; **109 тестов зелёных**)_

---

## Что строим

Telegram-бот **маркетплейс** для русскоязычных хэндименов и заказчиков в **Bay Area + Sacramento**. Заказчики постят работу → исполнители (Coworker-ы) откликаются → автор нанимает.

- **Группа** (где публикуются объявления): `Co-Worker'ы` (`MAIN_CHAT_ID = -1002186030111`)
- **Dev-бот:** `@C0w0rker1_bot`
- **Prod-бот:** будет создан перед запуском
- **Инвайт-ссылка:** `https://t.me/+pJqeSGuX005kNThi` (в `bot/i18n.py` константа `COMMUNITY_INVITE_URL`)

## Заказчик / контекст

- **Аркадий Березынец** (`arkadiybrsv@gmail.com`)
- **Запуск:** май 2026 (онбординг + реклама в TG-каналах)
- **Цель монетизации:** $5K/мес за 2 месяца после запуска (фазированный план — см. ниже)

## Stack

- Python 3.11, aiogram 3.13.1
- SQLAlchemy 2.0 async + asyncpg (prod) / aiosqlite (tests)
- pydantic-settings для конфига
- phonenumbers для E.164, email-validator
- pytest, **94 теста зелёные** (запуск из корня: `python -m pytest tests/`)

## Деплой workflow

```bash
# 1) Mac
cd ~/Coworkers/tg-community-bot
git add -A && git commit -m "..." && git push origin main
# username для PAT: arkadiy-sti
```
```bash
# 2) VPS (Hetzner srv1054603, обычно уже залогинен как root)
cd /opt/tg-community-bot && git pull
sudo systemctl restart tg-community-bot-dev.service
sleep 5
sudo journalctl -u tg-community-bot-dev.service --since "30 seconds ago" --no-pager | tail -15
```

- **Dev сервис:** `tg-community-bot-dev.service`
- **Prod сервис:** `tg-community-bot.service` (НЕ трогать пока dev не подтверждён)
- **ENV файл:** `/opt/tg-community-bot/.env.dev` (читается через `ENV_FILE` в systemd unit). Критичные переменные: `BOT_TOKEN`, `ADMIN_IDS` (csv), `MAIN_CHAT_ID`, `DB_URL`. Coolify-панель env-vars **НЕ** прокидываются в systemd — править нужно именно файл.
- Миграции в `bot/db/migrations.py` запускаются на каждом старте — для нового поля просто добавь в `_USER_COLUMNS`/`_LISTING_COLUMNS`/etc, для новой таблицы — `_ensure_table` с DDL для PG и SQLite.

## Структура файлов (что где)

```
bot/
  main.py                — entry point, set_my_commands при старте
  config.py              — Settings из .env, admin_ids, main_chat_id
  i18n.py                — ВСЕ user-facing тексты RU+EN, COMMUNITY_INVITE_URL
  db/
    models.py            — все SQLAlchemy модели
    database.py          — engine, sessionmaker, get_session
    migrations.py        — idempotent миграции (запускаются на каждом старте)
    seed_tags.py         — словарь тегов + sync labels + OBSOLETE_SLUGS deletion
  services/
    users.py             — User CRUD, save_registration_v2, soft delete, ban_tg_id, list_banned
    tags.py              — normalize_custom_tag, create_custom_tag (rate-limit 3/user),
                           replace_user_tags, render_tag_cloud
    listings.py          — Listing CRUD, label-словари (KIND/HELPER/etc),
                           render_listing(mask_contact), RESPONSE_CAP_BONUS=3
    phones.py            — normalize_phone (E.164), validate_email
  handlers/
    __init__.py          — get_main_router, ВАЖЕН ПОРЯДОК (FSM до catch-all)
    welcome.py           — captcha при входе в группу
    register.py          — FSM v2: lang→role→name→area→primary→sec_tags→
                           contact_type→contact_value→bio→licensed→consent
    edit.py              — /edit точечная правка + /delete_me (soft)
    profile.py           — /profile, /check (gated к coworker, бейдж re-register)
    post.py              — FSM /post (13 шагов; seek-ветка ЗАКОММЕНТИРОВАНА)
    post_moderation.py   — DM админам, approve→publish, hire-flow, контакт-кнопки
    suggest.py           — /suggest юзер→админ, /suggestions, /suggest_done
    admin.py             — /ban /unban /warn /mute /stats + /ban_user /unban_user /banned_list
    common.py            — /start /help /rules /whichchat
tests/
  test_*.py              — 94 теста, conftest с in-memory SQLite
```

## Доменная модель (кратко)

| Модель | Что | Особенности |
|---|---|---|
| `User` | юзер бота | role: coworker/customer/guest (guest — legacy, новые не создаём), contact_phone/whatsapp/email (E.164), is_deleted/deleted_at/delete_count для soft-delete, primary_tag_id |
| `BannedTgId` | постоянный бан | переживает delete+re-register, проверяется в /start и /register |
| `Tag` | skill/location/feedback_pos/feedback_neg | is_predefined+is_approved (custom от юзеров с rate-limit) |
| `UserTag` | M2M юзер↔тег | is_primary флаг, лимит 6 на профиль |
| `Listing` | объявление | offer (seek **paused**), num_people/helper_kind/language_req/duration/urgency/budget/location_freetext/contact_override; status: pending→approved→closed/expired |
| `ListingPhoto` | фото к объявлению | хранится `file_id` Telegram (не байты), до 5 шт |
| `ListingTag` | M2M listing↔tag | locations + skills в одной таблице (различаются по category) |
| `Response` | отклик | is_hired+hired_at; UNIQUE(listing_id, responder_id) — нельзя дважды |
| `Deal` | сделка | создаётся при «Нанял этого», базис для будущих рейтингов |
| `Feedback` + `FeedbackTag` | модели готовы, **flow ещё не реализован** | для будущего рейтинг-flow |
| `Suggestion` | фидбек о боте от юзера админу | /suggest |
| `Subscription` | платная подписка | модель есть, **gating ещё не подключён** |

## Ключевые конвенции и гочи

1. **i18n всегда** — каждая строка для юзера через `t(lang, key, **kwargs)`. RU + EN копия.
2. **HTML-escape** для user-controlled полей: `html.escape(...)` для description, contact_override, location_freetext. Был баг с `<$500` который ломал парсер — НЕ делать `<` в predefined labels.
3. **Не затенять `t`** в list-comprehensions: использовать `tg`, не `t`.
4. **Helpers из callback требуют explicit `tg_id`**: сигнатура `_go_to_X(target_message, state, lang, *, tg_id=...)`. `callback.message.from_user` — это БОТ, а не юзер.
5. **Snapshot полей User до закрытия сессии** — иначе `DetachedInstanceError`. Паттерн в `_render_preview_safe`.
6. **HTML parse_mode** в `DefaultBotProperties` — допустимы `<b><i><a><code>`. User content всегда escape.
7. **`disable_web_page_preview=True`** для сообщений с t.me-ссылками.
8. **Telegram album не поддерживает inline_keyboard** — паттерн: send_media_group + send_message с reply_to_message_id.
9. **Tags seed-as-truth**: меняешь `label_ru`/`label_en` в `TAGS` — sync на следующем рестарте. Удаление через `OBSOLETE_SLUGS` (только если 0 usages).
10. **Privacy маска**: `mask_contact=True` в `render_listing` при публикации в группу. `_classify_override()` определяет тип override (phone/email/@username) — реальный номер автору приходит только в DM responder-у после клика.
11. **Cap откликов**: `num_people + RESPONSE_CAP_BONUS` (=3). Превышение → status='expired' + edit group msg для удаления кнопки.
12. **Hire**: каждый клик «Нанял» инкрементит `hired_count` (через подсчёт `Response.is_hired=True`). `hired_count >= num_people` → status='closed'.
13. **Phone format**: в БД E.164 (`+12125551234`), на ввод просим 10 цифр.
14. **Soft-delete**: `/delete_me` чистит личные поля но row остаётся. Re-register реюзит row, `delete_count++` сохраняется как след для модератора.

## Стиль работы (предпочтения Аркадия)

- **Русский**, прямо, без воды.
- **Решения принимаешь сам** — не over-discuss. Краткое обсуждение → код одним коммитом → деплой-команды.
- **Шипишь инкрементально** — маленькие коммиты, быстрый цикл.
- После каждого изменения — **готовые copy-paste команды для деплоя** (Mac block + VPS block).
- Сначала **код**, потом краткое объяснение что и зачем.
- **Тесты держать зелёными**. Добавлять при новой логике, не отдельной cleanup-пачкой.
- Если есть risk/неоднозначность — **спроси перед кодом** (особенно если влияет на монетизацию или публичный чат).

## Что готово / статус

**MVP marketplace pipeline закрыт целиком и проверен живьём:**

- ✅ Регистрация (Coworker/Guest) с language, role, name, area, primary tag, secondary tags (до 5), contact type+value (с phonenumbers валидацией), bio, licensed contractor, consent
- ✅ `/edit` точечная правка всех полей включая теги
- ✅ `/delete_me` soft-delete (с подтверждением и каскадом по объявлениям → closed)
- ✅ `/profile` с тегами, primary, бейджем Verified, фидбэк-облаком (пока пусто)
- ✅ `/check @username` (только Coworker), бейдж re-registered
- ✅ `/post` 13-шаговый FSM с фото (до 5, undo-кнопка), custom locations/skills, маскировка контакта, preview→submit
- ✅ Модерация в DM админам с approve/reject + причина
- ✅ Публикация в группу: альбом + текст-reply с кнопкой Откликнуться
- ✅ Отклик с богатыми DM обоим сторонам + контакт-кнопки (Telegram/WhatsApp/Phone/Email + fallback `tg://user?id`)
- ✅ Hire-flow с Нанял/Ещё ищу/Закрыть, создание Deal, авто-закрытие при `hired_count >= num_people`
- ✅ Cap откликов `num_people + 3` с авто-expire и удалением кнопки в группе
- ✅ Welcome-сообщения с инвайтом в группу
- ✅ Меню команд через `set_my_commands`, `/whichchat` для админа
- ✅ Soft-delete + ban-list (`/ban_user /unban_user /banned_list`); ban_user также кикает из MAIN_CHAT_ID, unban_user возвращает доступ
- ✅ Re-registered бейдж в /check виден **только админам** (`viewer_is_admin` параметр в `_build_card`); в /profile никогда
- ✅ `/suggest` обратная связь юзеры→админы
- ✅ `/my_deals` + фидбэк-flow: rating ⭐1-5 → multi-select feedback-теги → опц. комментарий. Запись в Feedback+FeedbackTag. Облако и рейтинг в /profile **живые** — наполняются автоматически. При закрытии сделки одной стороной — DM второй с приглашением оставить отзыв.
- ✅ `/my_posts` — список своих объявлений (последние 20) с кнопкой `🔒 Закрыть`. Можно закрывать pending/approved/expired. Pending → 'closed' без редактирования группы (объявление ещё не публиковалось). Approved → закрытие в группе с пометкой «Набор закрыт».
- ✅ `/lang` команда осталась (работает), но **скрыта из меню** — до полной локализации EN-веток.
- ✅ INFO-лог `Notify author OK: listing=N author_tg_id=X responder_tg_id=Y count=K/N` — для дебага «получил/не получил отклик».
- ✅ **Welcome (`/start`) и правила (`/rules`) переписаны** — описание сообщества, ценности, развёрнутые правила (5 пунктов с пояснениями), упоминание будущих платных подписок (AI-агент, push-уведомления, онлайн-встречи, Verified). Тон — простой, тёплый, без пафоса.
- ✅ **Inline-кнопка «👥 Зайти в группу»** под `/start`, `register_done`, `register_guest_done` — клик одной кнопкой, без поиска ссылки в тексте.
- ✅ **Админские команды для исправления отзывов**: `/feedback_view @username` — список всех отзывов на юзера с ID; `/feedback_remove <id>` — удалить ошибочный отзыв (cascade убирает FeedbackTag, облако и рейтинг автоматически пересчитываются при следующем рендере).
- ✅ **Защита админов от self-ban**: `/ban_user` отказывается банить юзера если его tg_id в `ADMIN_IDS`. И в `/start`/`/register` ban-check игнорирует админов (даже если они каким-то образом попали в `banned_tg_ids`).
- ✅ **Auto-expire 14 дней** через фоновую asyncio-задачу `auto_expire_loop` в `bot/main.py`. Запускается через 60 сек после старта, далее каждые 24 часа. Помечает approved-объявления старше 14 дней как `expired`, редактирует сообщение в группе (убирает кнопку «Откликнуться», добавляет reply-сообщение «⌛ Срок истёк»). Параметр `LISTING_AUTO_EXPIRE_DAYS=14` в `bot/services/listings.py`.
- ✅ **Welcome в группе после captcha** — расширенное приветствие (i18n `captcha_passed`) с описанием сообщества, списком команд бота в DM, упоминанием будущих платных фич + inline-кнопка «🤖 Открыть бота» с deep-link `https://t.me/{bot_username}?start=welcome` (имя бота берётся через `bot.me()` динамически). Реализация в `bot/handlers/welcome.py` (`on_user_passed_captcha`).
- ✅ **Подписки + community-бейджи**:
  - Поля `User.badge_verified/badge_trusted/badge_top` (admin-assigned). Бейджи рендерятся в `/profile` и `/check` рядом с именем: ✅ Verified · 💎 Trusted Pro · 🏆 Top Coworker. Существующий 🛠 Verified contractor (auto, по `is_licensed_contractor`) остался.
  - Сервис `users.grant_subscription/revoke_subscription/get_active_subscription` — продление существующей подписки если она активна. `users.set_user_badge(tg_id, badge, value)` для бейджей. `users.KNOWN_BADGES` = ('verified', 'trusted', 'top').
  - Админ-команды: `/grant <tg_id> <дней> [pro|business]` (default pro), `/revoke <tg_id>`, `/grant_badge <tg_id> <verified|trusted|top>`, `/revoke_badge <tg_id> <badge>`.
  - Команда юзеру: `/my_subscription` — статус активной подписки или предложение оформить (через /suggest).
  - `bot/services/subscriptions.py` — декоратор `@subscription_required(plan="any" | "pro" | "business")` готов к использованию, но **никуда не подключён** (лимиты публикаций отложены до набора 100-200 чел в группе).
  - `Subscription` модель уже была в БД, миграции не нужны (только User badge_*).

- ✅ **Customer-роль** (заменила Guest): упрощённая регистрация (3 шага: имя→контакт→согласие), упрощённый `/post` (7 шагов: район→навыки→описание→срочность→бюджет→фото→контакт), гейтинг: customer не видит /check, /edit только имя+контакт, `/profile` показывает упрощённую карточку. Legacy guest-записи в БД сохранены.

**Seek-ветка `/post` (Ищу работу) — закомментирована** в `_kb_kind`, ждёт набора аудитории заказчиков.

## Pending блоки (по приоритету)

**MVP функционал закрыт.** Что осталось — пост-MVP, по мере роста аудитории:

1. **Подключить декоратор `@subscription_required` к платным фичам** — после набора 100-200 чел в группе. Кандидаты: лимит публикаций (free 2/мес vs Pro безлимит), Featured Listing $50, push-уведомления по тегам, AI-агент.
2. **Stripe** или Telegram Stars для self-service подписки (сейчас выдача только через админ /grant).
3. **Контент-рубрики**: проект месяца, голосовалки, фоновые истории — заведутся с ростом аудитории.


## Стратегия монетизации $5K/мес (для подписок)

| Фаза | Месяц | Что | $/мес |
|---|---|---|---|
| 1 | Май | Всё бесплатно. Цель: 150-200 Coworker-ов | $0 |
| 2 | Июнь | Pro $20 (Verified бейдж + безлимит публикаций), Business $200 | $400-600 |
| 3 | Июль | + Featured Listing $50 (объявление в топе 7 дней), реклама $300/нед от поставщиков/insurance | $2-3K |
| 4 | Авг | Pro 30+, Business 5+, 50 Featured, 4 ads | **$5K+** |

**Не делать:**
- Жёсткий gating в Фазе 1 — убьёт рост.
- Платные отклики — убивают marketplace.

**Делать:**
- Verified бейдж → драйвер Pro (доверие в US).
- Реклама от смежных бизнесов — самое маржинальное.

## Процесс в новой сессии

1. Прочитай этот файл.
2. Если нужен дополнительный контекст из чата — **спроси Аркадия**.
3. Перед кодом — короткое подтверждение что собираешься делать (1-2 предложения).
4. Кодишь → тесты → деплой-команды copy-paste готовые.
5. Если добавил/изменил что-то крупное — **обнови этот файл** в разделах «Что готово / статус» и «Pending блоки».
