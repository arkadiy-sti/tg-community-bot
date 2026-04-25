"""Лёгкая i18n: RU/EN словари + helper t(lang, key, **kwargs).

Тексты можно править здесь — без правок логики бота.
Если нужного перевода нет — fallback на RU, потом на ключ.
"""
from __future__ import annotations

from typing import Literal

Lang = Literal["ru", "en"]
DEFAULT_LANG: Lang = "ru"

# ---------------------------------------------------------------------------
# Словари. Структура: TEXTS[lang][key] = template (.format-friendly).
# ---------------------------------------------------------------------------
TEXTS: dict[str, dict[str, str]] = {
    "ru": {
        # --- Общее / онбординг ---
        "community_name": "Co-Workers Bay Area",
        "lang_choose": "Выбери язык / Choose language:",
        "lang_set_ru": "🇷🇺 Русский",
        "lang_set_en": "🇺🇸 English",
        "start_private": (
            "Привет, {name}! 👋\n\n"
            "Это бот сообщества <b>{community}</b> — площадка для русскоязычных "
            "хэндименов и заказчиков в Bay Area.\n\n"
            "Что ты можешь:\n"
            "• Зарегистрироваться как исполнитель, заказчик или компания\n"
            "• Размещать и находить работу\n"
            "• Оставлять и читать отзывы\n\n"
            "Команды:\n"
            "/register — регистрация\n"
            "/profile — мой профиль\n"
            "/post — разместить объявление\n"
            "/check — проверить контрагента\n"
            "/help — помощь"
        ),
        "help": (
            "<b>Команды</b>\n"
            "/register — регистрация / смена роли\n"
            "/profile — мой профиль и рейтинг\n"
            "/post — разместить объявление\n"
            "/check — карточка пользователя по @username\n"
            "/lang — сменить язык\n"
            "/rules — правила\n"
        ),
        "rules": (
            "<b>Правила {community}</b>\n\n"
            "1. Уважаем друг друга. Оскорбления, дискриминация → бан.\n"
            "2. Только реальные работы и реальные исполнители.\n"
            "3. Спам и реклама запрещены.\n"
            "4. Платные фичи — для подписчиков ($20 физлица / $200 компании в месяц).\n"
            "5. Все споры — в личку админа."
        ),

        # --- Welcome / Captcha ---
        "welcome_captcha": (
            "Привет, {name}! 👋\n\n"
            "Добро пожаловать в <b>{community}</b>.\n"
            "Подтверди, что ты не бот — нажми кнопку в течение {seconds} секунд."
        ),
        "captcha_button": "✅ Я не бот",
        "captcha_passed": (
            "Отлично, {name}! Ты в сообществе 🎉\n\n"
            "Чтобы начать пользоваться платформой — напиши боту в личку /register"
        ),
        "captcha_failed": "Время вышло — кикнул из чата. Зайди снова и пройди проверку.",

        # --- Регистрация ---
        "register_choose_role": "Выбери роль:",
        "role_handyman": "🔧 Исполнитель (handyman)",
        "role_individual": "🏠 Заказчик (физлицо)",
        "role_company": "🏢 Компания-заказчик",
        "register_ask_name": "Как тебя зовут? (имя или название компании)",
        "register_ask_area": "В каких районах Bay Area работаешь? (например: SF, Oakland, San Jose)",
        "register_ask_phone": "Телефон или способ связи (необязательно — пропусти, если не хочешь):",
        "register_ask_skip": "Пропустить",
        "register_ask_bio": (
            "Коротко о себе: специализация, опыт, что предлагаешь.\n"
            "Лимит: 500 символов."
        ),
        "register_done": (
            "✅ Готово! Профиль сохранён.\n"
            "Команды: /profile — посмотреть, /post — разместить объявление."
        ),

        # --- Профиль ---
        "profile_card": (
            "<b>{name}</b>\n"
            "Роль: {role}\n"
            "Район: {area}\n"
            "{bio}\n\n"
            "⭐ Рейтинг: {rating} ({deals} сделок)\n"
            "{subscription}"
        ),
        "profile_no_subscription": "Подписки нет — действуют только базовые функции.",
        "profile_subscription_active": "🟢 Подписка активна до {until}.",
        "profile_not_registered": "Ты ещё не зарегистрирован. Команда: /register",

        # --- Объявления ---
        "post_choose_kind": "Что публикуем?",
        "post_kind_offer": "💼 Предлагаю работу",
        "post_kind_seek": "🔎 Ищу работу",
        "post_ask_text": "Опиши работу/услугу. До 1000 символов.",
        "post_ask_tags": (
            "Выбери теги (можно несколько). Когда закончишь — нажми «Готово»."
        ),
        "post_tags_done": "Готово",
        "post_review": (
            "<b>Проверь объявление</b>\n\n"
            "Тип: {kind}\n"
            "Теги: {tags}\n\n"
            "{text}"
        ),
        "post_send": "📨 Отправить на модерацию",
        "post_cancel": "✖ Отменить",
        "post_sent": "✅ Отправлено на модерацию. Я напишу, когда админ проверит.",
        "post_canceled": "Отменено.",
        "post_approved_user": "✅ Твоё объявление опубликовано.",
        "post_rejected_user": "❌ Объявление отклонено модератором.\nПричина: {reason}",
        "post_too_long": "Слишком длинно ({n} символов, лимит {max}).",

        # --- Модерация ---
        "mod_new_listing": (
            "<b>На модерацию</b>\n"
            "От: {author}\n"
            "Тип: {kind}\n"
            "Теги: {tags}\n\n"
            "{text}"
        ),
        "mod_approve": "✅ Опубликовать",
        "mod_reject": "❌ Отклонить",
        "mod_done_approved": "Опубликовано в канал.",
        "mod_done_rejected": "Отклонено.",

        # --- Подписки ---
        "subscription_required": (
            "Эта функция доступна подписчикам.\n"
            "$20/мес для физлиц, $200/мес для компаний.\n"
            "Свяжись с админом, чтобы оформить."
        ),
        "subscription_granted": "Подписка выдана пользователю {user_id} до {until}.",
        "subscription_revoked": "Подписка отозвана у пользователя {user_id}.",
        "subscription_invalid_args": "Использование: /grant <user_id> <дней> или /revoke <user_id>",

        # --- Рейтинг / фидбэк ---
        "feedback_request": (
            "Сделка с {partner} завершена?\n"
            "Оставь короткий отзыв — это поможет сообществу."
        ),
        "feedback_rate": "Оцени от 1 до 5:",
        "feedback_tags": "Выбери подходящие теги (несколько):",
        "feedback_comment": "Комментарий (необязательно — нажми «Пропустить»):",
        "feedback_skip": "Пропустить",
        "feedback_thanks": "Спасибо за отзыв!",

        # --- Антиспам ---
        "antispam_link": "❌ {name}, ссылки разрешены только после 24 часов в сообществе.",
        "antispam_rate": "⏱ {name}, слишком много сообщений подряд. Сделай паузу.",
        "antispam_stopword": "❌ {name}, сообщение удалено — запрещённое содержимое.",

        # --- Админ ---
        "msg_banned": "🔨 Пользователь {name} забанен.",
        "msg_unbanned": "✅ Пользователь снят с бана.",
        "msg_warned": "⚠️ Предупреждение для {name} ({warnings}/{max_warnings}).",
        "msg_auto_ban": "🔨 {name} забанен автоматически — превышен лимит предупреждений.",
        "msg_muted": "🔇 {name} замьючен на {minutes} минут.",
        "msg_only_admin": "❌ Команда доступна только администраторам.",
        "msg_reply_required": "❌ Используй команду ответом на сообщение пользователя.",

        # --- Рассылка ---
        "broadcast_start": "📣 Начинаю рассылку для {count} пользователей…",
        "broadcast_done": (
            "✅ Рассылка завершена.\n"
            "Отправлено: {sent}\n"
            "Заблокировали бота: {blocked}\n"
            "Ошибок: {errors}"
        ),
        "broadcast_usage": (
            "Используй ответом на сообщение для рассылки.\n"
            "Опционально: /broadcast all|active_7d|new_users (по умолчанию all)."
        ),
        "stats_template": (
            "<b>Статистика {community}</b>\n\n"
            "👥 Всего пользователей: {total}\n"
            "🟢 Активных за 7 дней: {active_7d}\n"
            "🆕 Новых за 24 часа: {new_24h}\n"
            "🔨 Забанено: {banned}\n"
        ),
    },
    # ---------------------------------------------------------------------
    "en": {
        "community_name": "Co-Workers Bay Area",
        "lang_choose": "Выбери язык / Choose language:",
        "lang_set_ru": "🇷🇺 Русский",
        "lang_set_en": "🇺🇸 English",
        "start_private": (
            "Hi, {name}! 👋\n\n"
            "This is the bot for the <b>{community}</b> community — a marketplace "
            "for Russian-speaking handymen and clients in the Bay Area.\n\n"
            "What you can do:\n"
            "• Register as a contractor, individual client, or company\n"
            "• Post and find jobs\n"
            "• Leave and read reviews\n\n"
            "Commands:\n"
            "/register — register\n"
            "/profile — my profile\n"
            "/post — post a listing\n"
            "/check — look up another member\n"
            "/help — help"
        ),
        "help": (
            "<b>Commands</b>\n"
            "/register — register / change role\n"
            "/profile — my profile and rating\n"
            "/post — post a listing\n"
            "/check — member card by @username\n"
            "/lang — switch language\n"
            "/rules — rules\n"
        ),
        "rules": (
            "<b>{community} rules</b>\n\n"
            "1. Respect each other. Insults or discrimination → ban.\n"
            "2. Real jobs and real contractors only.\n"
            "3. No spam, no advertising.\n"
            "4. Paid features for subscribers ($20/mo individuals, $200/mo companies).\n"
            "5. Disputes — DM the admin."
        ),
        "welcome_captcha": (
            "Hi, {name}! 👋\n\n"
            "Welcome to <b>{community}</b>.\n"
            "Confirm you're not a bot — tap the button within {seconds} seconds."
        ),
        "captcha_button": "✅ I'm not a bot",
        "captcha_passed": (
            "Great, {name}! You're in 🎉\n\n"
            "DM the bot /register to start using the platform."
        ),
        "captcha_failed": "Time's up — you've been kicked. Rejoin and try again.",
        "register_choose_role": "Choose your role:",
        "role_handyman": "🔧 Contractor (handyman)",
        "role_individual": "🏠 Individual client",
        "role_company": "🏢 Company client",
        "register_ask_name": "What's your name? (your name or company name)",
        "register_ask_area": "Which Bay Area locations? (e.g. SF, Oakland, San Jose)",
        "register_ask_phone": "Phone or contact (optional — skip if you don't want to share):",
        "register_ask_skip": "Skip",
        "register_ask_bio": "Briefly: specialty, experience, what you offer.\nLimit: 500 chars.",
        "register_done": (
            "✅ Done! Profile saved.\n"
            "Commands: /profile — view, /post — create a listing."
        ),
        "profile_card": (
            "<b>{name}</b>\n"
            "Role: {role}\n"
            "Area: {area}\n"
            "{bio}\n\n"
            "⭐ Rating: {rating} ({deals} deals)\n"
            "{subscription}"
        ),
        "profile_no_subscription": "No subscription — basic features only.",
        "profile_subscription_active": "🟢 Subscription active until {until}.",
        "profile_not_registered": "You haven't registered yet. Use /register",
        "post_choose_kind": "What are we posting?",
        "post_kind_offer": "💼 Offering a job",
        "post_kind_seek": "🔎 Looking for work",
        "post_ask_text": "Describe the job/service. Up to 1000 characters.",
        "post_ask_tags": "Pick tags (multiple ok). Tap \u201cDone\u201d when finished.",
        "post_tags_done": "Done",
        "post_review": (
            "<b>Review the listing</b>\n\n"
            "Type: {kind}\n"
            "Tags: {tags}\n\n"
            "{text}"
        ),
        "post_send": "📨 Send for moderation",
        "post_cancel": "✖ Cancel",
        "post_sent": "✅ Sent for moderation. I'll DM you when reviewed.",
        "post_canceled": "Canceled.",
        "post_approved_user": "✅ Your listing has been published.",
        "post_rejected_user": "❌ Listing rejected by moderator.\nReason: {reason}",
        "post_too_long": "Too long ({n} chars, limit {max}).",
        "mod_new_listing": (
            "<b>For moderation</b>\n"
            "From: {author}\n"
            "Type: {kind}\n"
            "Tags: {tags}\n\n"
            "{text}"
        ),
        "mod_approve": "✅ Approve",
        "mod_reject": "❌ Reject",
        "mod_done_approved": "Published to channel.",
        "mod_done_rejected": "Rejected.",
        "subscription_required": (
            "This feature is for subscribers.\n"
            "$20/mo for individuals, $200/mo for companies.\n"
            "Contact the admin to subscribe."
        ),
        "subscription_granted": "Subscription granted to user {user_id} until {until}.",
        "subscription_revoked": "Subscription revoked from user {user_id}.",
        "subscription_invalid_args": "Usage: /grant <user_id> <days> or /revoke <user_id>",
        "feedback_request": (
            "Did the deal with {partner} complete?\n"
            "Leave a quick review — it helps the community."
        ),
        "feedback_rate": "Rate from 1 to 5:",
        "feedback_tags": "Pick the tags that fit (multiple):",
        "feedback_comment": "Comment (optional — tap \u201cSkip\u201d):",
        "feedback_skip": "Skip",
        "feedback_thanks": "Thanks for the review!",
        "antispam_link": "❌ {name}, links are allowed only after 24 hours in the community.",
        "antispam_rate": "⏱ {name}, too many messages in a row. Slow down.",
        "antispam_stopword": "❌ {name}, message removed — banned content.",
        "msg_banned": "🔨 User {name} banned.",
        "msg_unbanned": "✅ User unbanned.",
        "msg_warned": "⚠️ Warning for {name} ({warnings}/{max_warnings}).",
        "msg_auto_ban": "🔨 {name} auto-banned — too many warnings.",
        "msg_muted": "🔇 {name} muted for {minutes} minutes.",
        "msg_only_admin": "❌ Admins only.",
        "msg_reply_required": "❌ Reply to a user's message to use this command.",
        "broadcast_start": "📣 Broadcasting to {count} users…",
        "broadcast_done": (
            "✅ Broadcast complete.\n"
            "Sent: {sent}\n"
            "Bot blocked: {blocked}\n"
            "Errors: {errors}"
        ),
        "broadcast_usage": (
            "Reply to a message to broadcast it.\n"
            "Optional: /broadcast all|active_7d|new_users (default all)."
        ),
        "stats_template": (
            "<b>{community} stats</b>\n\n"
            "👥 Total users: {total}\n"
            "🟢 Active 7d: {active_7d}\n"
            "🆕 New 24h: {new_24h}\n"
            "🔨 Banned: {banned}\n"
        ),
    },
}


def t(lang: str | None, key: str, /, **kwargs) -> str:
    """Резолв перевода: lang → DEFAULT_LANG → key."""
    if lang not in TEXTS:
        lang = DEFAULT_LANG
    template = TEXTS[lang].get(key)
    if template is None:
        template = TEXTS[DEFAULT_LANG].get(key)
    if template is None:
        return key
    if not kwargs:
        return template
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template


def normalize_lang(value: str | None) -> Lang:
    """Привести произвольный ввод к 'ru'/'en'."""
    if not value:
        return DEFAULT_LANG
    v = value.lower().strip()
    if v in ("ru", "rus", "russian", "русский", "ру"):
        return "ru"
    if v in ("en", "eng", "english", "английский"):
        return "en"
    return DEFAULT_LANG
