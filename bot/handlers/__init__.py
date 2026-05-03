from aiogram import Router

from bot.handlers import (
    admin, broadcast, common, deals, edit, post, post_moderation, profile,
    register, suggest, welcome,
)


def get_main_router() -> Router:
    """Собирает все роутеры в один — порядок важен.

    Роутеры с FSM (register, edit, post, suggest, deals) ставим до common,
    иначе FSM-сообщения могут уйти в catch-all хэндлеры.
    """
    root = Router(name="root")
    root.include_router(welcome.router)
    root.include_router(register.router)
    root.include_router(edit.router)
    root.include_router(post.router)
    root.include_router(post_moderation.router)
    root.include_router(deals.router)
    root.include_router(suggest.router)
    root.include_router(profile.router)
    root.include_router(admin.router)
    root.include_router(broadcast.router)
    root.include_router(common.router)
    return root
