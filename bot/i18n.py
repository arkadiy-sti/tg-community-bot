"""Лёгкая i18n: RU/EN словари + helper t(lang, key, **kwargs).

Тексты можно править здесь — без правок логики бота.
Если нужного перевода нет — fallback на RU, потом на ключ.
"""
from __future__ import annotations

from typing import Literal

Lang = Literal["ru", "en"]
DEFAULT_LANG: Lang = "ru"

# Инвайт-ссылка на группу — выводится в welcome-сообщениях.
# При смене группы — менять здесь, везде подтянется.
COMMUNITY_INVITE_URL = "https://t.me/+pJqeSGuX005kNThi"

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
            "• Зарегистрироваться как <b>Coworker</b> — профиль с тегами, "
            "рейтингом и уведомлениями о подходящих проектах\n"
            "• Или зайти как <b>Гость</b> — просто читать группу\n"
            "• Размещать и находить работу\n"
            "• Оставлять и читать отзывы\n\n"
            "👥 Группа: <a href=\"{invite}\">Co-Workers Bay Area</a>\n\n"
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
        "register_choose_role": (
            "Выбери, как ты будешь участвовать:\n\n"
            "🛠 <b>Coworker</b> — заполняешь профиль, получаешь предложения, "
            "можешь публиковать и откликаться.\n"
            "👀 <b>Гость</b> — только читаешь группу, профиль не нужен."
        ),
        "role_coworker": "🛠 Coworker",
        "role_guest": "👀 Гость",
        "role_handyman": "🔧 Исполнитель (handyman)",  # legacy
        "role_individual": "🏠 Заказчик (физлицо)",      # legacy
        "role_company": "🏢 Компания-заказчик",          # legacy
        "register_guest_done": (
            "👀 <b>Добро пожаловать в Co-Workers Bay Area!</b>\n\n"
            "Ты в группе как гость — можешь читать чат, общаться, "
            "наблюдать за проектами. Профиль не создан, поэтому "
            "тебя не видно в директории и нет уведомлений о работе.\n\n"
            "👥 Заходи в группу: <a href=\"{invite}\">Co-Workers Bay Area</a>\n\n"
            "Когда захочешь стать активным участником и получать "
            "предложения о проектах — напиши /register снова и выбери "
            "<b>Coworker</b>."
        ),
        "register_ask_name": "Как тебя зовут? (имя или название компании)",
        "register_ask_area": (
            "В каких районах North CA работаешь? "
            "(например: SF, Oakland, San Jose, Sacramento…)"
        ),
        "register_ask_primary_tag": (
            "Выбери <b>основной вид работ</b> — это твоя ключевая компетенция.\n"
            "По нему мы будем подбирать самые подходящие проекты."
        ),
        "register_ask_more_tags": (
            "Выбери до 5 дополнительных навыков (всего {limit} тегов на профиль).\n"
            "Можно тапнуть «✏️ Свой вариант» или «✅ Готово».\n\n"
            "Выбрано: {selected}/{max}"
        ),
        "register_ask_custom_tag": (
            "Введи свой тег одним сообщением.\n"
            "От 2 до 30 символов, только буквы (рус/англ), цифры, пробелы и дефисы."
        ),
        "register_custom_tag_invalid": (
            "❌ Тег невалидный. Только буквы, цифры, пробел и дефис, длина 2–30."
        ),
        "register_custom_tag_limit": (
            "Лимит твоих собственных тегов исчерпан ({limit}). "
            "Выбери из готовых вариантов."
        ),
        "register_tag_limit_reached": (
            "Достигнут лимит {limit} тегов. Нажми «✅ Готово»."
        ),
        "register_ask_contact_type": (
            "📞 На какой контакт прислать <b>срочные предложения</b> по подходящим "
            "проектам?\n\n"
            "Без него уведомления приходят только в Telegram — это медленнее.\n"
            "Заказчики часто уходят к тому, кто ответил первым."
        ),
        "contact_type_phone": "📱 Телефон (SMS)",
        "contact_type_whatsapp": "💬 WhatsApp",
        "contact_type_email": "✉️ Email",
        "register_ask_phone": (
            "Введи 10 цифр без пробелов и знаков.\n"
            "Пример: <code>2125551234</code>"
        ),
        "register_ask_whatsapp": (
            "Введи WhatsApp-номер: 10 цифр без пробелов.\n"
            "Пример: <code>2125551234</code>"
        ),
        "register_ask_email": (
            "Введи email одним сообщением.\n"
            "Пример: <code>name@example.com</code>"
        ),
        "register_phone_invalid": "❌ Не похоже на номер. Введи 10 цифр (US).",
        "register_email_invalid": "❌ Email не прошёл проверку. Попробуй ещё раз.",
        "register_ask_skip": "Пропустить",
        "register_ask_bio": (
            "Коротко о себе: опыт, что умеешь, что предлагаешь.\n"
            "Лимит: 500 символов."
        ),
        "register_ask_licensed": (
            "У тебя есть лицензия contractor (CSLB / state license)?\n"
            "Это будет показано в профиле бейджем «Verified»."
        ),
        "licensed_yes": "✅ Да, есть лицензия",
        "licensed_no": "❌ Нет",
        "licensed_skip": "⏭ Пропустить",
        "register_ask_license_number": (
            "Введи номер лицензии (необязательно — нажми «Пропустить»)."
        ),
        "register_consent_intro": (
            "📋 Последний шаг — согласие.\n\n"
            "Без согласия на обработку данных мы не можем сохранить профиль. "
            "Согласие на уведомления — опционально, но без него мы не сможем "
            "слать тебе предложения о проектах."
        ),
        "consent_data": "☑ Согласен на обработку данных",
        "consent_data_off": "☐ Согласен на обработку данных",
        "consent_notif": "☑ Согласен получать уведомления",
        "consent_notif_off": "☐ Согласен получать уведомления",
        "consent_finish": "✅ Завершить регистрацию",
        "consent_data_required": (
            "Без галки «Согласен на обработку данных» завершить нельзя.\n"
            "Если не согласен — напиши /cancel."
        ),
        "register_canceled": "Регистрация отменена. Можно начать снова через /register.",
        "register_done": (
            "🎉 <b>Добро пожаловать в Co-Workers Bay Area!</b>\n\n"
            "Профиль создан. Теперь ты в комьюнити русскоязычных "
            "хэндименов и заказчиков Bay Area.\n\n"
            "👥 Заходи в группу: <a href=\"{invite}\">Co-Workers Bay Area</a>\n"
            "Там обсуждаем проекты, делимся опытом, ищем подрядчиков "
            "и заказчиков.\n\n"
            "Что дальше:\n"
            "• /profile — посмотреть свою карточку\n"
            "• /edit — поправить профиль\n"
            "• /post — разместить объявление о работе\n"
            "• /check @username — карточка другого участника\n\n"
            "Удачи в проектах! 🛠"
        ),
        "register_already_registered": (
            "У тебя уже есть профиль. Если хочешь перезаписать — нажми «Перезаписать».\n"
            "Для точечных правок используй /edit."
        ),
        "register_overwrite": "🔄 Перезаписать",
        "register_keep": "Оставить как есть",

        # --- /edit — редактирование профиля ---
        "edit_menu": "Что хочешь изменить?",
        "edit_field_name": "✏️ Имя",
        "edit_field_area": "📍 Район",
        "edit_field_bio": "📝 О себе",
        "edit_field_contact": "📞 Контакт",
        "edit_field_tags": "🏷 Теги",
        "edit_field_license": "📜 Лицензия",
        "edit_field_lang": "🌐 Язык",
        "edit_cancel": "✖ Отмена",
        "edit_done": "✅ Сохранено.",
        "edit_not_registered": "Сначала зарегистрируйся: /register",

        # --- /delete_me ---
        "delete_me_confirm": (
            "⚠️ Это удалит твой профиль, теги, отклики и подписки.\n"
            "Сообщения и история останутся — но без привязки к тебе.\n\n"
            "Подтвердить?"
        ),
        "delete_me_yes": "🗑 Да, удалить",
        "delete_me_no": "Отмена",
        "delete_me_done": "✅ Профиль удалён. Свяжись снова через /start.",
        "delete_me_canceled": "Удаление отменено.",

        # --- Профиль ---
        "profile_card": (
            "<b>{name}</b>{licensed_badge}\n"
            "Роль: {role}\n"
            "Район: {area}\n"
            "Основной навык: {primary_tag}\n"
            "Доп. навыки: {tags}\n"
            "Приоритетный способ связи: {contact_pref}\n"
            "{bio}\n\n"
            "⭐ Рейтинг: {rating} ({deals} сделок)\n"
            "💬 Что говорят: {cloud}\n"
            "{subscription}"
        ),
        "profile_licensed_badge": " ✅ Verified contractor",
        "profile_contact_phone": "📱 Телефон (SMS)",
        "profile_contact_whatsapp": "💬 WhatsApp",
        "profile_contact_email": "✉️ Email",
        "profile_contact_none": "только Telegram",
        "check_only_coworkers": (
            "🔒 Просмотр профилей участников — только для зарегистрированных Coworker-ов.\n\n"
            "Сначала зарегистрируйся как Coworker: /register\n"
            "После этого ты сможешь смотреть карточки других участников и "
            "получать предложения о подходящих проектах."
        ),

        # --- /post — создание объявления ---
        "post_only_coworkers": (
            "🔒 Публиковать объявления могут только зарегистрированные Coworker-ы.\n\n"
            "Сначала зарегистрируйся: /register"
        ),
        "post_kind_choose": (
            "Что публикуем?\n\n"
            "💼 <b>Предлагаю работу</b> — у тебя есть проект, ищешь исполнителя.\n"
            "🔎 <b>Ищу работу</b> — ты исполнитель, ищешь клиентов или подработку."
        ),
        "post_kind_offer_btn": "💼 Предлагаю работу",
        "post_kind_seek_btn": "🔎 Ищу работу",
        "post_ask_locations": (
            "📍 В каком районе работа? (выбери до {limit} или укажи свой адрес)\n\n"
            "Выбрано: {selected}/{limit}"
        ),
        "post_ask_custom_location": (
            "Введи город или ZIP-код одним сообщением.\n"
            "Пример: <code>94103</code> или <code>Walnut Creek</code>"
        ),
        "post_ask_skills": (
            "🏷 Какие виды работ? (выбери до {limit})\n\n"
            "Выбрано: {selected}/{limit}"
        ),
        "post_ask_num_people": "👥 Сколько нужно человек?",
        "post_ask_engagement": "📋 Тип занятости?",
        "post_ask_helper_kind": (
            "👷 Кто нужен?\n\n"
            "🔧 <b>Профессионал</b> — закроет работу под ключ, ведёт процесс сам. Ставка выше.\n"
            "🛠 <b>Помощник</b> — работает под вашим руководством, заказчик ведёт процесс. Ставка ниже.\n"
            "👤 <b>Любой</b> — рассмотрите оба варианта."
        ),
        "post_ask_language_offer": "🗣 Нужно ли общаться с клиентом?",
        "post_ask_language_seek": (
            "🗣 На каких языках можешь общаться? (выбери все подходящие)"
        ),
        "post_ask_duration": "⏱ Сколько времени займёт работа?",
        "post_ask_urgency": "⚡ Срочность?",
        "post_ask_budget": (
            "💵 Бюджет (опционально — можно пропустить):"
        ),
        "post_ask_description": (
            "📝 Опиши работу подробнее. До 1000 символов.\n\n"
            "Что важно: что нужно сделать, какие материалы, особенности объекта, "
            "пожелания по графику. Чем конкретнее — тем лучше отклик."
        ),
        "post_ask_photos": (
            "📷 Хочешь приложить фото? До {limit} штук.\n"
            "Пришли фото одно за другим, потом нажми «✅ Готово».\n"
            "Если не нужно — нажми «⏭ Пропустить»."
        ),
        "post_photos_done": "✅ Готово ({n})",
        "post_photo_added": "📸 Фото добавлено ({n}/{limit}). Пришли ещё или нажми «✅ Готово».",
        "post_photo_limit": "❌ Достигнут лимит {limit} фото. Нажми «✅ Готово».",
        "post_ask_contact": (
            "📞 На какой контакт принимать отклики?\n\n"
            "По умолчанию используется твой приоритетный из профиля:\n<b>{contact}</b>"
        ),
        "post_contact_keep": "✅ Использовать этот",
        "post_contact_other": "🔄 Указать другой",
        "post_ask_contact_other": (
            "Введи контакт для этого объявления одним сообщением.\n"
            "Может быть телефон, WhatsApp, email или @username."
        ),
        "post_preview_title": "📋 <b>Проверь объявление перед отправкой</b>",
        "post_send": "📨 Отправить",
        "post_cancel": "✖ Отменить",
        "post_skip": "⏭ Пропустить",
        "post_back": "← Назад",
        "post_done": "✅ Готово",
        "post_sent": (
            "✅ Готово! Отправил админу на модерацию — это не займёт много времени, "
            "скоро вернусь с публикацией. 📨"
        ),
        "post_approved_user": (
            "🎉 Твоё объявление опубликовано в группе <b>Co-Workers Bay Area</b>!\n\n"
            "Когда кто-то откликнется — я тебе сразу напишу."
        ),
        "post_rejected_user_with_reason": (
            "❌ Твоё объявление отклонено модератором.\n\n"
            "Причина: <i>{reason}</i>\n\n"
            "Ты можешь поправить и опубликовать снова через /post."
        ),
        "post_response_to_author": (
            "📩 На твоё объявление откликнулся <b>{responder}</b>.\n\n"
            "Контакт: {contact}\n\n"
            "Свяжись с ним напрямую — Telegram-бот посредником не работает."
        ),
        "post_response_acked": (
            "✅ Твой отклик отправлен автору. Если он на связи — скоро ответит."
        ),
        # Модерация — для админов
        "mod_new_listing": (
            "🆕 <b>Новое объявление #LST-{id}</b> на модерацию\n\n"
            "От: {author}\n\n"
            "{body}"
        ),
        "mod_btn_approve": "✅ Опубликовать",
        "mod_btn_reject": "❌ Отклонить",
        "mod_already_handled": "Уже обработано: <b>{status}</b> модератором {who}.",
        "mod_ask_reject_reason": (
            "Введи причину отказа одним сообщением (≤ 200 символов).\n"
            "Эта причина будет показана автору."
        ),
        "mod_done_approved": "✅ Опубликовано в группу.",
        "mod_done_rejected": "❌ Отклонено. Автор уведомлён.",
        "mod_no_group_chat": (
            "⚠️ GROUP_CHAT_ID не настроен в .env — публикация в группу пропущена. "
            "Объявление помечено как approved, но в группу не отправлено."
        ),
        "post_respond_btn": "📩 Откликнуться",
        "post_canceled": "Создание объявления отменено.",
        "post_too_long": "Слишком длинно ({n} символов, лимит {max}).",
        "post_need_locations": "Выбери хотя бы один район.",
        "post_need_skills": "Выбери хотя бы один вид работ.",
        "post_need_languages": "Выбери хотя бы один язык.",
        "post_limit_reached": (
            "Лимит публикаций достигнут (≤{limit} в 30 дней). "
            "Подожди или оформи подписку у админа."
        ),

        # Лейблы кнопок для /post
        "post_num_5_plus": "5+",
        "post_engagement_one_time": "На один проект",
        "post_engagement_part_time": "Подработка",
        "post_helper_pro": "🔧 Профессионал",
        "post_helper_helper": "🛠 Помощник",
        "post_helper_any": "Любой",
        "post_lang_offer_none": "Общение не требуется",
        "post_lang_offer_ru": "Русский",
        "post_lang_offer_en": "Английский",
        "post_lang_seek_ru": "Русский",
        "post_lang_seek_en": "Английский",
        "post_duration_hours": "Несколько часов",
        "post_duration_day": "1 день",
        "post_duration_few_days": "2–5 дней",
        "post_duration_week_plus": "Неделя+",
        "post_duration_longterm": "Долгосрочно",
        "post_urgency_urgent": "🔥 Срочно",
        "post_urgency_this_week": "📅 На этой неделе",
        "post_urgency_this_month": "🗓 В этом месяце",
        "post_urgency_flexible": "⏳ Не горит",
        "post_budget_under_500": "до $500",
        "post_budget_500_2k": "$500–2K",
        "post_budget_2k_10k": "$2K–10K",
        "post_budget_over_10k": "$10K+",
        "post_budget_discuss": "Обсуждаем",
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
        "post_too_long": "Слишком длинно ({n} символов, лимит {max}).",

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
            "• Register as a <b>Coworker</b> — profile with tags, rating, "
            "and project notifications\n"
            "• Or join as a <b>Guest</b> — just read the group\n"
            "• Post and find jobs\n"
            "• Leave and read reviews\n\n"
            "👥 Group: <a href=\"{invite}\">Co-Workers Bay Area</a>\n\n"
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
        "register_choose_role": (
            "How do you want to participate?\n\n"
            "🛠 <b>Coworker</b> — fill profile, get matched to projects, "
            "post and reply to listings.\n"
            "👀 <b>Guest</b> — just read the group, no profile."
        ),
        "role_coworker": "🛠 Coworker",
        "role_guest": "👀 Guest",
        "role_handyman": "🔧 Contractor (handyman)",
        "role_individual": "🏠 Individual client",
        "role_company": "🏢 Company client",
        "register_guest_done": (
            "👀 <b>Welcome to Co-Workers Bay Area!</b>\n\n"
            "You're in as a guest — you can read the chat, post, and "
            "follow projects. No profile is created, so you're not in "
            "the directory and won't receive project alerts.\n\n"
            "👥 Join the group: <a href=\"{invite}\">Co-Workers Bay Area</a>\n\n"
            "When you want to become an active member and receive "
            "project offers — type /register again and pick <b>Coworker</b>."
        ),
        "register_ask_name": "What's your name? (your name or company name)",
        "register_ask_area": (
            "Which Northern California locations? "
            "(e.g. SF, Oakland, San Jose, Sacramento…)"
        ),
        "register_ask_primary_tag": (
            "Pick your <b>main work category</b> — your key skill.\n"
            "We'll match you to the most relevant projects by it."
        ),
        "register_ask_more_tags": (
            "Pick up to 5 additional skills ({limit} tags total per profile).\n"
            "Tap «✏️ Custom» or «✅ Done» when finished.\n\n"
            "Selected: {selected}/{max}"
        ),
        "register_ask_custom_tag": (
            "Type your tag in one message.\n"
            "2 to 30 characters: letters (EN/RU), digits, spaces, hyphens only."
        ),
        "register_custom_tag_invalid": (
            "❌ Invalid tag. Letters, digits, space, hyphen only; length 2–30."
        ),
        "register_custom_tag_limit": (
            "Custom tag limit reached ({limit}). Pick from preset options."
        ),
        "register_tag_limit_reached": (
            "Tag limit reached ({limit}). Tap «✅ Done»."
        ),
        "register_ask_contact_type": (
            "📞 Where should we send <b>urgent project offers</b> matching your "
            "profile?\n\n"
            "Without it, alerts go only to Telegram — slower.\n"
            "Clients often go with whoever replies first."
        ),
        "contact_type_phone": "📱 Phone (SMS)",
        "contact_type_whatsapp": "💬 WhatsApp",
        "contact_type_email": "✉️ Email",
        "register_ask_phone": (
            "Type 10 digits, no spaces or symbols.\n"
            "Example: <code>2125551234</code>"
        ),
        "register_ask_whatsapp": (
            "WhatsApp number, 10 digits no spaces.\n"
            "Example: <code>2125551234</code>"
        ),
        "register_ask_email": (
            "Type your email in one message.\n"
            "Example: <code>name@example.com</code>"
        ),
        "register_phone_invalid": "❌ Doesn't look like a phone. Type 10 digits (US).",
        "register_email_invalid": "❌ Email failed validation. Try again.",
        "register_ask_skip": "Skip",
        "register_ask_bio": "Briefly: specialty, experience, what you offer.\nLimit: 500 chars.",
        "register_ask_licensed": (
            "Do you have a contractor license (CSLB / state)?\n"
            "We'll show a Verified badge on your profile."
        ),
        "licensed_yes": "✅ Yes, I'm licensed",
        "licensed_no": "❌ No",
        "licensed_skip": "⏭ Skip",
        "register_ask_license_number": (
            "Type your license number (optional — tap Skip)."
        ),
        "register_consent_intro": (
            "📋 Last step — consent.\n\n"
            "Without data-processing consent we can't save the profile. "
            "Notification consent is optional, but without it we can't send "
            "you project offers."
        ),
        "consent_data": "☑ I agree to data processing",
        "consent_data_off": "☐ I agree to data processing",
        "consent_notif": "☑ I agree to receive notifications",
        "consent_notif_off": "☐ I agree to receive notifications",
        "consent_finish": "✅ Finish registration",
        "consent_data_required": (
            "Can't finish without «I agree to data processing».\n"
            "If you disagree — type /cancel."
        ),
        "register_canceled": "Registration canceled. Run /register again to retry.",
        "register_done": (
            "🎉 <b>Welcome to Co-Workers Bay Area!</b>\n\n"
            "Your profile is set up. You're now in the community of "
            "Russian-speaking handymen and clients in the Bay Area.\n\n"
            "👥 Join the group: <a href=\"{invite}\">Co-Workers Bay Area</a>\n"
            "We discuss projects, share experience, find contractors "
            "and clients there.\n\n"
            "What's next:\n"
            "• /profile — view your card\n"
            "• /edit — update profile\n"
            "• /post — post a job listing\n"
            "• /check @username — view another member's card\n\n"
            "Good luck on your projects! 🛠"
        ),
        "register_already_registered": (
            "You already have a profile. Tap «Overwrite» to start over.\n"
            "For small edits use /edit."
        ),
        "register_overwrite": "🔄 Overwrite",
        "register_keep": "Keep as is",

        # --- /edit ---
        "edit_menu": "What do you want to change?",
        "edit_field_name": "✏️ Name",
        "edit_field_area": "📍 Area",
        "edit_field_bio": "📝 Bio",
        "edit_field_contact": "📞 Contact",
        "edit_field_tags": "🏷 Tags",
        "edit_field_license": "📜 License",
        "edit_field_lang": "🌐 Language",
        "edit_cancel": "✖ Cancel",
        "edit_done": "✅ Saved.",
        "edit_not_registered": "Register first: /register",

        # --- /delete_me ---
        "delete_me_confirm": (
            "⚠️ This deletes your profile, tags, responses, subscriptions.\n"
            "Messages and history stay — without your link.\n\n"
            "Confirm?"
        ),
        "delete_me_yes": "🗑 Yes, delete",
        "delete_me_no": "Cancel",
        "delete_me_done": "✅ Profile deleted. /start to come back.",
        "delete_me_canceled": "Deletion canceled.",
        "profile_card": (
            "<b>{name}</b>{licensed_badge}\n"
            "Role: {role}\n"
            "Area: {area}\n"
            "Main skill: {primary_tag}\n"
            "Other skills: {tags}\n"
            "Preferred contact: {contact_pref}\n"
            "{bio}\n\n"
            "⭐ Rating: {rating} ({deals} deals)\n"
            "💬 Reviews say: {cloud}\n"
            "{subscription}"
        ),
        "profile_licensed_badge": " ✅ Verified contractor",
        "profile_contact_phone": "📱 Phone (SMS)",
        "profile_contact_whatsapp": "💬 WhatsApp",
        "profile_contact_email": "✉️ Email",
        "profile_contact_none": "Telegram only",
        "check_only_coworkers": (
            "🔒 Viewing member profiles is for registered Coworkers only.\n\n"
            "Register as a Coworker first: /register\n"
            "After that you'll be able to view other members' cards and "
            "receive offers for matching projects."
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
        "post_sent": (
            "✅ Done! Sent to admin for moderation — won't take long, "
            "I'll be back with the publication soon. 📨"
        ),
        "post_approved_user": (
            "🎉 Your listing is published in <b>Co-Workers Bay Area</b>!\n\n"
            "I'll DM you the moment someone responds."
        ),
        "post_rejected_user_with_reason": (
            "❌ Your listing was rejected by a moderator.\n\n"
            "Reason: <i>{reason}</i>\n\n"
            "You can fix and resubmit via /post."
        ),
        "post_response_to_author": (
            "📩 <b>{responder}</b> responded to your listing.\n\n"
            "Contact: {contact}\n\n"
            "Reach out directly — the bot doesn't relay messages."
        ),
        "post_response_acked": (
            "✅ Your response sent to the author. If they're around — they'll be in touch."
        ),
        "mod_new_listing": (
            "🆕 <b>New listing #LST-{id}</b> for moderation\n\n"
            "From: {author}\n\n"
            "{body}"
        ),
        "mod_btn_approve": "✅ Publish",
        "mod_btn_reject": "❌ Reject",
        "mod_already_handled": "Already handled: <b>{status}</b> by {who}.",
        "mod_ask_reject_reason": (
            "Type rejection reason in one message (≤ 200 chars).\n"
            "This will be shown to the author."
        ),
        "mod_done_approved": "✅ Published to group.",
        "mod_done_rejected": "❌ Rejected. Author notified.",
        "mod_no_group_chat": (
            "⚠️ GROUP_CHAT_ID not configured in .env — group publication skipped. "
            "Listing marked as approved but not sent to the group."
        ),
        "post_respond_btn": "📩 Respond",
        "post_too_long": "Too long ({n} chars, limit {max}).",
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
