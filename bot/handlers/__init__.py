from aiogram import Router

from bot.handlers import admin, broadcast, common, welcome


def get_main_router() -> Router:
    """Собирает все роутеры в один — порядок важен."""
    root = Router(name="root")
    root.include_router(welcome.router)
    root.include_router(admin.router)
    root.include_router(broadcast.router)
    root.include_router(common.router)
    return root
