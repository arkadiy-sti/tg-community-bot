"""Точка входа бота."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
)

from bot.config import get_settings
from bot.db.database import dispose as db_dispose
from bot.db.database import get_session, init_db
from bot.handlers import get_main_router
from bot.middlewares.activity import ActivityMiddleware
from bot.middlewares.antispam import AntispamMiddleware
from bot.services import listings as listings_svc

# Раз в сутки — auto-expire старых объявлений
AUTO_EXPIRE_INTERVAL_SEC = 24 * 60 * 60
AUTO_EXPIRE_INITIAL_DELAY_SEC = 60


PRIVATE_COMMANDS = [
    BotCommand(command="start", description="🚀 Начать / Restart"),
    BotCommand(command="register", description="✍️ Регистрация / Register"),
    BotCommand(command="profile", description="👤 Мой профиль / My profile"),
    BotCommand(command="edit", description="✏️ Изменить профиль / Edit"),
    BotCommand(command="check", description="🔍 Карточка @username / Check"),
    BotCommand(command="post", description="📢 Объявление / Post a listing"),
    BotCommand(command="my_posts", description="📋 Мои объявления / My posts"),
    BotCommand(command="my_deals", description="🤝 Мои сделки / My deals"),
    BotCommand(command="my_subscription", description="🟢 Моя подписка / My sub"),
    BotCommand(command="suggest", description="💡 Идея для бота / Suggest"),
    # /lang команда работает, но скрыта из меню до полной локализации EN-веток
    BotCommand(command="rules", description="📜 Правила / Rules"),
    BotCommand(command="help", description="ℹ️ Помощь / Help"),
    BotCommand(command="delete_me", description="🗑 Удалить профиль / Delete"),
]


GROUP_COMMANDS = [
    BotCommand(command="rules", description="📜 Правила группы / Rules"),
    BotCommand(command="report", description="🚨 Пожаловаться / Report"),
    BotCommand(command="help", description="ℹ️ Помощь / Help"),
]


async def setup_bot_commands(bot: Bot) -> None:
    """Зарегистрировать меню команд для приватных и групповых чатов."""
    await bot.set_my_commands(
        PRIVATE_COMMANDS, scope=BotCommandScopeAllPrivateChats()
    )
    await bot.set_my_commands(
        GROUP_COMMANDS, scope=BotCommandScopeAllGroupChats()
    )


async def auto_expire_loop(bot: Bot) -> None:
    """Фоновая задача: раз в сутки помечает approved-объявления старше
    14 дней как expired и редактирует сообщения в группе.

    Первый прогон — через минуту после старта (catch-up если бот лежал),
    далее — каждые 24 часа.
    """
    log = logging.getLogger("bot.auto_expire")
    settings = get_settings()
    await asyncio.sleep(AUTO_EXPIRE_INITIAL_DELAY_SEC)
    while True:
        try:
            async with get_session() as session:
                count = await listings_svc.auto_expire_old_listings(
                    session,
                    bot=bot,
                    group_chat_id=settings.main_chat_id,
                )
            if count:
                log.info("Auto-expire: marked %s listings as expired", count)
            else:
                log.debug("Auto-expire: nothing to mark")
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.exception("auto_expire_loop error: %s", e)
        await asyncio.sleep(AUTO_EXPIRE_INTERVAL_SEC)


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    log = logging.getLogger("bot.main")
    log.info("Запуск бота…")

    await init_db(settings.db_url)
    log.info("БД инициализирована (%s)", settings.db_url)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Порядок важен: сначала activity (обновить БД), потом antispam
    dp.message.middleware(ActivityMiddleware())
    dp.message.middleware(AntispamMiddleware())

    dp.include_router(get_main_router())

    expire_task: asyncio.Task | None = None
    try:
        me = await bot.get_me()
        log.info("Бот запущен как @%s (id=%s)", me.username, me.id)
        try:
            await setup_bot_commands(bot)
            log.info("Меню команд зарегистрировано")
        except Exception as e:
            log.warning("Не удалось зарегистрировать меню: %s", e)
        # Фоновая задача auto-expire
        expire_task = asyncio.create_task(auto_expire_loop(bot))
        log.info("Auto-expire loop запущен (раз в %sч, expire через %s дней)",
                 AUTO_EXPIRE_INTERVAL_SEC // 3600,
                 listings_svc.LISTING_AUTO_EXPIRE_DAYS)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        if expire_task is not None:
            expire_task.cancel()
            try:
                await expire_task
            except (asyncio.CancelledError, Exception):
                pass
        await bot.session.close()
        await db_dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.getLogger("bot.main").info("Остановлен")
