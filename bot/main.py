"""Точка входа бота."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import get_settings
from bot.db.database import dispose as db_dispose
from bot.db.database import init_db
from bot.handlers import get_main_router
from bot.middlewares.activity import ActivityMiddleware
from bot.middlewares.antispam import AntispamMiddleware


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

    try:
        me = await bot.get_me()
        log.info("Бот запущен как @%s (id=%s)", me.username, me.id)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        await db_dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.getLogger("bot.main").info("Остановлен")
