"""Обратная совместимость с плоскими константами.

Новый код пишется через bot.i18n.t(lang, key, **kwargs).
Старые модули (handlers/welcome.py, handlers/common.py, handlers/admin.py,
middlewares/antispam.py, services/broadcast handler) продолжают работать
со ссылками типа texts.WELCOME_CAPTCHA — здесь они резолвятся в RU-строки
из bot.i18n.TEXTS (DEFAULT_LANG).

Постепенно handlers переезжают на t(lang, ...) — в момент, когда у
пользователя есть User.language. Тогда этот файл можно удалить.
"""
from __future__ import annotations

from bot.i18n import DEFAULT_LANG, TEXTS

_RU = TEXTS[DEFAULT_LANG]

COMMUNITY_NAME = _RU["community_name"]

WELCOME_CAPTCHA = _RU["welcome_captcha"]
CAPTCHA_BUTTON = _RU["captcha_button"]
CAPTCHA_PASSED = _RU["captcha_passed"]
CAPTCHA_FAILED = _RU["captcha_failed"]

START_PRIVATE = _RU["start_private"]
HELP_TEXT = _RU["help"]

ADMIN_HELP = (
    "<b>Команды администратора</b>\n\n"
    "/ban — забанить (ответом на сообщение)\n"
    "/unban — разбанить (ответом или с user_id)\n"
    "/warn — выдать предупреждение (ответом)\n"
    "/mute &lt;минуты&gt; — замьютить (ответом)\n"
    "/stats — статистика сообщества\n"
    "/ghost_stats — сколько незарегистрированных «призраков»\n"
    "/welcome_unreg — напомнить призракам о регистрации (в группу)\n"
    "/broadcast — рассылка (ответом на сообщение)\n"
    "/grant &lt;user_id&gt; &lt;дней&gt; — выдать подписку\n"
    "/revoke &lt;user_id&gt; — отозвать подписку\n"
)

RULES = _RU["rules"]

MSG_BANNED = _RU["msg_banned"]
MSG_UNBANNED = _RU["msg_unbanned"]
MSG_WARNED = _RU["msg_warned"]
MSG_AUTO_BAN = _RU["msg_auto_ban"]
MSG_MUTED = _RU["msg_muted"]
MSG_ONLY_ADMIN = _RU["msg_only_admin"]
MSG_REPLY_REQUIRED = _RU["msg_reply_required"]

MSG_ANTISPAM_LINK = _RU["antispam_link"]
MSG_ANTISPAM_RATE = _RU["antispam_rate"]
MSG_ANTISPAM_STOPWORD = _RU["antispam_stopword"]

BROADCAST_START = _RU["broadcast_start"]
BROADCAST_DONE = _RU["broadcast_done"]
BROADCAST_USAGE = _RU["broadcast_usage"]

STATS_TEMPLATE = _RU["stats_template"]
