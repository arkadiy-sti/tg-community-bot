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
            "Это бот сообщества <b>{community}</b>.\n"
            "Здесь собираются хэндимены, контракторы, муверы и все, "
            "кто не ждёт идеального момента, а строит своё дело уже сейчас.\n\n"
            "<b>🎯 Зачем это всё</b>\n\n"
            "Co-Workers — не доска объявлений и не очередной шумный чат, "
            "где через три сообщения уже никто ничего не помнит.\n\n"
            "Это сообщество людей, которые растут вместе: кто-то давно "
            "в профессии, кто-то только начинает, кто-то ищет помощников, "
            "партнёров, проекты — или просто нормальных людей рядом.\n\n"
            "Здесь можно:\n"
            "• делиться опытом и учиться новому\n"
            "• находить общие проекты, единомышленников и друзей\n"
            "• получать помощь и помогать другим\n"
            "• строить репутацию внутри сообщества, а не просто мелькать в чате\n\n"
            "Тем, кто щедро делится знаниями — отдельный респект. "
            "На таких людях нормальные сообщества и держатся.\n\n"
            "<b>🛠 Что можно делать через бота</b>\n\n"
            "• зарегистрироваться как <b>Coworker</b> — с профилем, тегами, "
            "рейтингом и уведомлениями\n"
            "• зайти как <b>Гость</b> — читать группу без профиля\n"
            "• размещать объявления о работе через /post\n"
            "• откликаться на объявления других участников\n"
            "• оставлять отзывы после сделок\n"
            "• смотреть профили участников\n"
            "• связываться с администраторами и отправлять идеи через /suggest\n\n"
            "<b>📋 Команды</b> (всё в меню ☰)\n\n"
            "/register — регистрация\n"
            "/profile — мой профиль\n"
            "/post — разместить объявление\n"
            "/my_posts — мои объявления\n"
            "/my_deals — мои сделки\n"
            "/check @username — посмотреть участника\n"
            "/suggest — идея или обратная связь админам\n"
            "/help — все команды\n\n"
            "<i>Впереди появятся платные функции: AI-помощник, "
            "push-уведомления по подходящим проектам, онлайн-встречи и другие "
            "инструменты для тех, кто хочет не просто читать чат, "
            "а развивать своё дело.</i>\n\n"
            "Добро пожаловать в <b>Co-Workers</b>. Здесь ценят работу, "
            "опыт и людей, которые умеют быть полезными."
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
            "<b>Правила сообщества {community}</b>\n\n"
            "🎯 <b>Что это за группа</b>\n"
            "{community} — сообщество людей, которые развивают свой бизнес "
            "и растут вместе. Здесь и опытные профессионалы, и те, кто только "
            "начинает. Мы помогаем найти сотрудников и помощников "
            "<b>внутри сообщества</b> — это не платформа лидогенерации.\n\n"
            "📜 <b>Правила</b>\n\n"
            "<b>1. Уважение к каждому.</b> Оскорбления, дискриминация по "
            "любому признаку (религия, национальность, пол, возраст, статус), "
            "разжигание вражды, троллинг — мгновенный бан без предупреждений.\n\n"
            "<b>2. Реальные профили и реальные объявления.</b> Регистрируем "
            "только настоящие данные. Публикуем только реальные работы и услуги.\n\n"
            "<b>3. Никакого спама и рекламы в группе.</b> Если хочешь "
            "предложить продукт, услугу или сделать необычное объявление — "
            "напиши боту через /suggest или админу в личку. Мы рассмотрим.\n\n"
            "<b>4. Сложные вопросы и споры — в личку админу или через "
            "/suggest.</b> Не выясняем отношения в общем чате.\n\n"
            "<b>5. Не захламляем ленту.</b> Однотипные сообщения, повторы "
            "и флуд — уважаем чужое время.\n\n"
            "🔮 <b>Скоро (платные подписки)</b>\n"
            "AI-агент для подбора проектов · push по подходящим работам · "
            "онлайн-встречи и разборы кейсов · Verified-бейдж "
            "лицензированного контрактора · и другое.\n\n"
            "❓ Вопросы и обратная связь — /suggest"
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
            "💼 <b>Предлагаю работу</b> — у тебя есть проект, ищешь исполнителя.\n\n"
            "<i>Ветка «Ищу работу» появится когда в группе наберётся "
            "достаточно заказчиков.</i>"
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
            "<b>Первое отправленное фото будет главным в объявлении.</b>\n\n"
            "Пришли фото одно за другим. Если ошибся — «🗑 Убрать последнее».\n"
            "Когда закончил — «✅ Готово». Не нужно фото — «⏭ Пропустить»."
        ),
        "post_photos_done": "✅ Готово ({n})",
        "post_photos_undo": "🗑 Убрать последнее",
        "post_photo_added": "📸 Фото добавлено ({n}/{limit}). Пришли ещё или нажми «✅ Готово».",
        "post_photo_removed": "🗑 Удалил последнее. Сейчас {n}/{limit} фото.",
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
            "Когда кто-то откликнется — я тебе сразу напишу.\n"
            "Управление объявлениями: /my_posts"
        ),
        "post_rejected_user_with_reason": (
            "❌ Твоё объявление отклонено модератором.\n\n"
            "Причина: <i>{reason}</i>\n\n"
            "Ты можешь поправить и опубликовать снова через /post."
        ),
        "post_response_to_author": (
            "📩 <b>На твоё объявление #LST-{listing_id} откликнулся:</b>\n\n"
            "{card}\n\n"
            "📊 Отклики: <b>{count}</b> / нужно <b>{needed}</b>\n\n"
            "Кнопки ниже — связаться или отметить статус. "
            "Когда нанял всех — объявление закроется автоматически."
        ),
        "post_response_to_responder": (
            "✅ <b>Ты откликнулся на объявление #LST-{listing_id}.</b>\n\n"
            "Профиль автора:\n\n{card}\n\n"
            "Связаться с автором можно по кнопкам ниже. "
            "Если автор ответит — он напишет тебе сам."
        ),
        "btn_hire_this": "✅ Нанял этого",
        "btn_still_looking": "⏳ Ещё ищу",
        "btn_close_listing": "🔒 Закрыть",
        "hire_acked": (
            "✅ Отметил как нанятого. Создал запись о сделке — "
            "после её завершения сможешь оставить отзыв."
        ),
        "hire_acked_closed": (
            "✅ Отметил как нанятого. Все нужные люди найдены — "
            "объявление автоматически закрыто."
        ),
        "still_looking_acked": (
            "⏳ Окей, продолжаем. Объявление остаётся в ленте."
        ),
        "close_acked": (
            "🔒 Объявление закрыто. Спасибо!"
        ),
        "post_response_acked": (
            "✅ Твой отклик отправлен автору. Если он на связи — скоро ответит."
        ),
        "post_response_register_first": (
            "🔒 Сначала зарегистрируйся в боте.\n\n"
            "Открой @{bot_username}, нажми /start, заполни профиль — "
            "и возвращайся откликаться."
        ),
        "post_response_cap_reached": (
            "🔒 На это объявление уже достаточно откликов.\n"
            "Автор закрыл набор — попробуй другие объявления."
        ),
        "post_response_self": (
            "Нельзя откликнуться на своё объявление 🙂"
        ),
        "post_listing_closed_in_group": (
            "🔒 <b>Набор закрыт.</b> Спасибо за интерес — автор получил "
            "достаточно откликов."
        ),

        # --- /suggest — обратная связь админам ---
        "suggest_ask_text": (
            "💡 Что хочешь предложить или сказать админам?\n\n"
            "Напиши идею, замечание или вопрос одним сообщением "
            "(до 2000 символов). Я передам админам.\n\n"
            "Если передумал — /cancel"
        ),
        "suggest_too_short": (
            "Слишком коротко (минимум {min} символов). Попробуй ещё раз."
        ),
        "suggest_thanks": (
            "✅ Спасибо! Передал админам — они прочитают и учтут."
        ),
        "suggest_canceled": "Отменено.",
        "suggest_admin_notif": (
            "💡 <b>Новое предложение #{id}</b>\n"
            "От: {user}\n\n"
            "{text}\n\n"
            "<i>Пометить обработанным:</i> <code>/suggest_done {id}</code>"
        ),

        # --- Ban-list ---
        "banned_user_blocked": (
            "🚫 Доступ к боту ограничен администратором.\n\n"
            "Если считаешь это ошибкой — обратись к админу группы напрямую."
        ),
        "register_returning": (
            "👋 С возвращением! Я нашёл твой прошлый профиль и восстановил его. "
            "Можешь обновить данные, или они останутся прежними."
        ),
        "delete_count_badge": " 🔄 Re-registered {n}×",
        "admin_ban_usage": (
            "Использование: <code>/ban_user &lt;tg_id&gt; [причина]</code>\n"
            "Узнать tg_id юзера: ответом на его сообщение → <code>/whoami</code>"
        ),
        "admin_unban_usage": "Использование: <code>/unban_user &lt;tg_id&gt;</code>",
        "admin_banned_user": "🔨 Пользователь tg_id=<code>{tg_id}</code> забанен. Причина: {reason}",
        "admin_already_banned": "⚠️ tg_id=<code>{tg_id}</code> уже в ban-list.",
        "admin_unbanned_user": "✅ tg_id=<code>{tg_id}</code> разбанен.",
        "admin_not_banned": "❌ tg_id=<code>{tg_id}</code> не в ban-list.",
        "admin_banned_list_empty": "📭 Ban-list пуст.",
        "admin_banned_list_header": "🚫 <b>Ban-list (последние {n}):</b>",
        "admin_cant_ban_admin": (
            "⛔ Нельзя забанить админа (tg_id=<code>{tg_id}</code> в ADMIN_IDS).\n"
            "Если нужно — сначала убери его из .env и рестартни бота."
        ),

        # --- Сделки и фидбэк ---
        "deals_list_empty": (
            "📭 У тебя пока нет активных сделок.\n\n"
            "Сделка появится когда:\n"
            "• кто-то откликнется на твоё /post и ты нажмёшь «✅ Нанял этого»\n"
            "• ты откликнешься на чужое объявление и автор тебя выберет"
        ),
        "deals_list_header": "🤝 <b>Твои сделки:</b>\n",
        "deals_item_open": (
            "<b>#{id}</b> · с <b>{partner}</b> · {date}\n"
            "Статус: 🟢 в работе"
        ),
        "deals_item_closed_my_review": (
            "<b>#{id}</b> · с <b>{partner}</b> · {date}\n"
            "Статус: ✅ закрыта · ✓ ты оставил отзыв"
        ),
        "deals_item_closed_no_review": (
            "<b>#{id}</b> · с <b>{partner}</b> · {date}\n"
            "Статус: ✅ закрыта · ⏳ ждём твой отзыв"
        ),
        "deal_btn_close_review": "✅ Закрыть и оценить #{id}",
        "deal_btn_review": "📝 Оставить отзыв #{id}",
        "feedback_ask_rating": (
            "⭐ Оцени работу с <b>{partner}</b>:\n"
            "1 — плохо · 5 — отлично"
        ),
        "feedback_ask_tags": (
            "🏷 Отметь теги (можно несколько). Когда закончишь — «✅ Готово»."
        ),
        "feedback_ask_comment": (
            "💬 Комментарий (необязательно — нажми «⏭ Пропустить»):"
        ),
        "feedback_thanks": (
            "✅ Спасибо за отзыв! Облако и рейтинг в профиле обновлены."
        ),
        "feedback_partner_notified": (
            "📩 <b>{partner}</b> закрыл сделку #{id} и оставил отзыв.\n"
            "Оставь свой отзыв через /my_deals — это поможет рейтингу обоих."
        ),
        "feedback_already_left": (
            "✓ Ты уже оставил отзыв на эту сделку."
        ),
        "feedback_canceled": "Отменено.",
        "feedback_btn_done": "✅ Готово ({n})",
        "feedback_btn_skip": "⏭ Пропустить",
        "feedback_btn_cancel": "✖ Отмена",
        "feedback_need_rating": "Поставь оценку 1–5.",

        # --- /my_posts: управление своими объявлениями ---
        "my_posts_empty": (
            "📭 У тебя пока нет объявлений.\n"
            "Создать новое: /post"
        ),
        "my_posts_header": "📋 <b>Твои объявления</b> (последние 20):\n",
        "my_posts_btn_close": "🔒 Закрыть #LST-{id}",
        "my_posts_status_pending": "⏳ ждёт модерации",
        "my_posts_status_approved": "🟢 опубликовано",
        "my_posts_status_closed": "🔒 закрыто",
        "my_posts_status_rejected": "❌ отклонено",
        "my_posts_status_expired": "⌛ истекло",

        # --- Кнопка-инвайт в группу (используется в /start, register_done) ---
        "btn_join_group": "👥 Зайти в группу Co-Workers Bay Area",
        "btn_open_my_posts": "📋 Мои объявления",
        "btn_open_my_deals": "🤝 Мои сделки",
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
            "This is the bot for <b>{community}</b>.\n"
            "A place for handymen, contractors, movers and everyone who's "
            "not waiting for the perfect moment — they're building their thing now.\n\n"
            "<b>🎯 Why this exists</b>\n\n"
            "Co-Workers isn't a job board or another noisy chat where nothing's "
            "remembered after three messages.\n\n"
            "It's a community of people growing together: some are seasoned pros, "
            "some are just starting, some are looking for helpers, partners, "
            "projects — or just decent people nearby.\n\n"
            "Here you can:\n"
            "• share experience and learn new things\n"
            "• find joint projects, like-minded people and friends\n"
            "• get help and help others\n"
            "• build a reputation inside the community, not just appear in chat\n\n"
            "For those generously sharing knowledge — special respect. "
            "Healthy communities are built on people like that.\n\n"
            "<b>🛠 What you can do via the bot</b>\n\n"
            "• register as <b>Coworker</b> — with profile, tags, rating, and alerts\n"
            "• join as <b>Guest</b> — read the group without a profile\n"
            "• post jobs via /post\n"
            "• respond to others' listings\n"
            "• leave reviews after deals\n"
            "• view member profiles\n"
            "• reach admins and submit ideas via /suggest\n\n"
            "<b>📋 Commands</b> (all in menu ☰)\n\n"
            "/register — register\n"
            "/profile — my profile\n"
            "/post — post a listing\n"
            "/my_posts — my listings\n"
            "/my_deals — my deals\n"
            "/check @username — view member\n"
            "/suggest — idea or feedback to admins\n"
            "/help — all commands\n\n"
            "<i>Paid features coming: AI helper, push notifications for matching "
            "projects, online meetings, and other tools for those who want to grow "
            "their business — not just read chat.</i>\n\n"
            "Welcome to <b>Co-Workers</b>. Here we value work, experience, "
            "and people who know how to be useful."
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
            "<b>{community} community rules</b>\n\n"
            "🎯 <b>What this group is</b>\n"
            "A community for people growing their business together. "
            "Pros and beginners side by side. We help you find coworkers "
            "<b>within</b> the community — not a lead-gen platform.\n\n"
            "📜 <b>Rules</b>\n\n"
            "<b>1. Respect.</b> Insults, discrimination of any kind "
            "(religion, ethnicity, gender, age, status), inciting hostility, "
            "trolling — instant ban, no warnings.\n\n"
            "<b>2. Real profiles, real listings.</b> Only register with real "
            "data. Only post real work and services.\n\n"
            "<b>3. No spam or ads in the group.</b> Want to promote a product "
            "or post something unusual — message the bot via /suggest or "
            "admin DM. We'll review.\n\n"
            "<b>4. Disputes — DM admin or via /suggest.</b> Don't argue "
            "publicly.\n\n"
            "<b>5. Don't clutter the feed.</b> Same-type messages, repeats, "
            "flood — respect others' time.\n\n"
            "🔮 <b>Coming soon (paid subscriptions)</b>\n"
            "AI agent for project matching · push for matching jobs · "
            "online meetings · Verified contractor badge · and more.\n\n"
            "❓ Questions — /suggest"
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
            "I'll DM you the moment someone responds.\n"
            "Manage your listings: /my_posts"
        ),
        "post_rejected_user_with_reason": (
            "❌ Your listing was rejected by a moderator.\n\n"
            "Reason: <i>{reason}</i>\n\n"
            "You can fix and resubmit via /post."
        ),
        "post_response_to_author": (
            "📩 <b>New response to your listing #LST-{listing_id}:</b>\n\n"
            "{card}\n\n"
            "📊 Responses: <b>{count}</b> / needed <b>{needed}</b>\n\n"
            "Use the buttons below to connect or mark status. "
            "When everyone's hired — the listing closes automatically."
        ),
        "post_response_to_responder": (
            "✅ <b>You responded to listing #LST-{listing_id}.</b>\n\n"
            "Author's profile:\n\n{card}\n\n"
            "Use the buttons below to reach out. "
            "If the author wants to connect — they'll DM you."
        ),
        "btn_hire_this": "✅ Hire this one",
        "btn_still_looking": "⏳ Still looking",
        "btn_close_listing": "🔒 Close",
        "hire_acked": (
            "✅ Marked as hired. Created a deal record — "
            "you'll be able to leave a review when it's done."
        ),
        "hire_acked_closed": (
            "✅ Marked as hired. All needed people found — "
            "listing automatically closed."
        ),
        "still_looking_acked": (
            "⏳ OK, keeping it open."
        ),
        "close_acked": (
            "🔒 Listing closed. Thanks!"
        ),
        "post_response_acked": (
            "✅ Your response sent to the author. If they're around — they'll be in touch."
        ),
        "post_response_register_first": (
            "🔒 Register first.\n\n"
            "Open @{bot_username}, tap /start, fill out your profile — "
            "then come back and respond."
        ),
        "post_response_cap_reached": (
            "🔒 This listing already has enough responses.\n"
            "The author closed the slot — check other listings."
        ),
        "post_response_self": (
            "Can't respond to your own listing 🙂"
        ),
        "post_listing_closed_in_group": (
            "🔒 <b>Closed.</b> Thanks for the interest — the author has "
            "enough responses."
        ),

        # --- /suggest ---
        "suggest_ask_text": (
            "💡 What would you like to suggest or tell the admins?\n\n"
            "Type your idea, comment or question in one message "
            "(up to 2000 chars). I'll forward it to the admins.\n\n"
            "Changed your mind — /cancel"
        ),
        "suggest_too_short": (
            "Too short (min {min} chars). Try again."
        ),
        "suggest_thanks": (
            "✅ Thanks! Forwarded to admins — they'll read and take note."
        ),
        "suggest_canceled": "Canceled.",
        "suggest_admin_notif": (
            "💡 <b>New suggestion #{id}</b>\n"
            "From: {user}\n\n"
            "{text}\n\n"
            "<i>Mark resolved:</i> <code>/suggest_done {id}</code>"
        ),

        # --- Ban-list ---
        "banned_user_blocked": (
            "🚫 Access to the bot has been restricted by an administrator.\n\n"
            "If you believe this is a mistake, contact the group admin directly."
        ),
        "register_returning": (
            "👋 Welcome back! I found your previous profile and restored it. "
            "You can update fields or keep them as they were."
        ),
        "delete_count_badge": " 🔄 Re-registered {n}×",
        "admin_ban_usage": "Usage: <code>/ban_user &lt;tg_id&gt; [reason]</code>",
        "admin_unban_usage": "Usage: <code>/unban_user &lt;tg_id&gt;</code>",
        "admin_banned_user": "🔨 User tg_id=<code>{tg_id}</code> banned. Reason: {reason}",
        "admin_already_banned": "⚠️ tg_id=<code>{tg_id}</code> is already in ban-list.",
        "admin_unbanned_user": "✅ tg_id=<code>{tg_id}</code> unbanned.",
        "admin_not_banned": "❌ tg_id=<code>{tg_id}</code> is not in ban-list.",
        "admin_banned_list_empty": "📭 Ban-list is empty.",
        "admin_banned_list_header": "🚫 <b>Ban-list (last {n}):</b>",
        "admin_cant_ban_admin": (
            "⛔ Can't ban an admin (tg_id=<code>{tg_id}</code> is in ADMIN_IDS).\n"
            "If needed — remove from .env first and restart the bot."
        ),

        # --- Deals & feedback ---
        "deals_list_empty": (
            "📭 No active deals yet.\n\n"
            "A deal appears when:\n"
            "• someone responds to your /post and you tap «✅ Hire this one»\n"
            "• you respond to someone's listing and the author picks you"
        ),
        "deals_list_header": "🤝 <b>Your deals:</b>\n",
        "deals_item_open": (
            "<b>#{id}</b> · with <b>{partner}</b> · {date}\n"
            "Status: 🟢 in progress"
        ),
        "deals_item_closed_my_review": (
            "<b>#{id}</b> · with <b>{partner}</b> · {date}\n"
            "Status: ✅ closed · ✓ you left a review"
        ),
        "deals_item_closed_no_review": (
            "<b>#{id}</b> · with <b>{partner}</b> · {date}\n"
            "Status: ✅ closed · ⏳ waiting for your review"
        ),
        "deal_btn_close_review": "✅ Close and review #{id}",
        "deal_btn_review": "📝 Leave review #{id}",
        "feedback_ask_rating": (
            "⭐ Rate your experience with <b>{partner}</b>:\n"
            "1 — bad · 5 — excellent"
        ),
        "feedback_ask_tags": (
            "🏷 Pick tags (multiple ok). Tap «✅ Done» when finished."
        ),
        "feedback_ask_comment": (
            "💬 Comment (optional — tap «⏭ Skip»):"
        ),
        "feedback_thanks": (
            "✅ Thanks for the review! Cloud and rating updated in profile."
        ),
        "feedback_partner_notified": (
            "📩 <b>{partner}</b> closed deal #{id} and left a review.\n"
            "Leave your own via /my_deals — helps both ratings."
        ),
        "feedback_already_left": (
            "✓ You already reviewed this deal."
        ),
        "feedback_canceled": "Canceled.",
        "feedback_btn_done": "✅ Done ({n})",
        "feedback_btn_skip": "⏭ Skip",
        "feedback_btn_cancel": "✖ Cancel",
        "feedback_need_rating": "Pick a rating 1–5.",

        # --- /my_posts ---
        "my_posts_empty": (
            "📭 No listings yet.\n"
            "Create new: /post"
        ),
        "my_posts_header": "📋 <b>Your listings</b> (last 20):\n",
        "my_posts_btn_close": "🔒 Close #LST-{id}",
        "my_posts_status_pending": "⏳ pending moderation",
        "my_posts_status_approved": "🟢 published",
        "my_posts_status_closed": "🔒 closed",
        "my_posts_status_rejected": "❌ rejected",
        "my_posts_status_expired": "⌛ expired",

        # --- Group invite button ---
        "btn_join_group": "👥 Join Co-Workers Bay Area",
        "btn_open_my_posts": "📋 My listings",
        "btn_open_my_deals": "🤝 My deals",
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
