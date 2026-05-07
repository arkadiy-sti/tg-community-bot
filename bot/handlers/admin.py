"""Админ-команды: /ban /unban /warn /mute /stats /ban_user /unban_user /banned_list."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.types import ChatPermissions, Message

from bot import texts
from bot.config import get_settings
from bot.db.database import get_session
from bot.i18n import t
from bot.services import users

log = logging.getLogger(__name__)

router = Router(name="admin")


def _is_admin(user_id: int | None) -> bool:
    if user_id is None:
        return False
    return user_id in get_settings().admin_ids


@router.message(Command("ban"))
async def cmd_ban(message: Message, bot: Bot) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        await message.answer(texts.MSG_ONLY_ADMIN)
        return
    target = message.reply_to_message.from_user if message.reply_to_message else None
    if target is None:
        await message.answer(texts.MSG_REPLY_REQUIRED)
        return
    try:
        await bot.ban_chat_member(message.chat.id, target.id)
    except TelegramBadRequest as ex:
        log.warning("ban_chat_member failed: %s", ex)
    async with get_session() as session:
        await users.ban_user(session, target.id)
    await message.answer(texts.MSG_BANNED.format(name=target.full_name))


@router.message(Command("unban"))
async def cmd_unban(message: Message, bot: Bot, command: CommandObject) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        await message.answer(texts.MSG_ONLY_ADMIN)
        return
    target_id: int | None = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
    elif command.args:
        try:
            target_id = int(command.args.strip())
        except ValueError:
            await message.answer("Используй: /unban <user_id> или ответом.")
            return
    if target_id is None:
        await message.answer(texts.MSG_REPLY_REQUIRED)
        return
    try:
        await bot.unban_chat_member(message.chat.id, target_id, only_if_banned=True)
    except TelegramBadRequest as ex:
        log.warning("unban_chat_member failed: %s", ex)
    async with get_session() as session:
        await users.unban_user(session, target_id)
    await message.answer(texts.MSG_UNBANNED)


@router.message(Command("warn"))
async def cmd_warn(message: Message, bot: Bot) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        await message.answer(texts.MSG_ONLY_ADMIN)
        return
    target = message.reply_to_message.from_user if message.reply_to_message else None
    if target is None:
        await message.answer(texts.MSG_REPLY_REQUIRED)
        return

    async with get_session() as session:
        warns = await users.add_warning(session, target.id)

    max_warnings = get_settings().max_warnings
    if warns >= max_warnings:
        async with get_session() as session:
            await users.ban_user(session, target.id)
        try:
            await bot.ban_chat_member(message.chat.id, target.id)
        except TelegramBadRequest as ex:
            log.warning("auto-ban failed: %s", ex)
        await message.answer(texts.MSG_AUTO_BAN.format(name=target.full_name))
    else:
        await message.answer(
            texts.MSG_WARNED.format(
                name=target.full_name, warnings=warns, max_warnings=max_warnings
            )
        )


@router.message(Command("mute"))
async def cmd_mute(message: Message, bot: Bot, command: CommandObject) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        await message.answer(texts.MSG_ONLY_ADMIN)
        return
    target = message.reply_to_message.from_user if message.reply_to_message else None
    if target is None:
        await message.answer(texts.MSG_REPLY_REQUIRED)
        return
    try:
        minutes = int(command.args.strip()) if command.args else 60
    except ValueError:
        await message.answer("Используй: /mute <минуты> ответом.")
        return
    until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    try:
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until,
        )
    except TelegramBadRequest as ex:
        log.warning("restrict_chat_member failed: %s", ex)
        await message.answer(f"Не смог замьютить: {ex.message}")
        return
    await message.answer(texts.MSG_MUTED.format(name=target.full_name, minutes=minutes))


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        await message.answer(texts.MSG_ONLY_ADMIN)
        return
    async with get_session() as session:
        stats = await users.get_stats(session)
    await message.answer(
        texts.STATS_TEMPLATE.format(community=texts.COMMUNITY_NAME, **stats)
    )


# ---------------------------------------------------------------------------
# Постоянный бан по tg_id (переживает /delete_me + re-register)
# ---------------------------------------------------------------------------


@router.message(Command("ban_user"))
async def cmd_ban_user(message: Message, command: CommandObject, bot: Bot) -> None:
    """/ban_user <tg_id> [reason] — постоянный бан + кик из группы."""
    if not _is_admin(message.from_user.id if message.from_user else None):
        return
    args = (command.args or "").strip().split(maxsplit=1)
    if not args:
        await message.answer(t("ru", "admin_ban_usage"))
        return
    try:
        tg_id = int(args[0])
    except ValueError:
        await message.answer(t("ru", "admin_ban_usage"))
        return
    # Защита: нельзя банить админа (защита от self-ban при тестах)
    if tg_id in get_settings().admin_ids:
        await message.answer(t("ru", "admin_cant_ban_admin", tg_id=tg_id))
        return
    reason = args[1] if len(args) > 1 else None
    async with get_session() as session:
        entry = await users.ban_tg_id(
            session, tg_id,
            by_admin=message.from_user.id, reason=reason,
        )
    if entry is None:
        await message.answer(t("ru", "admin_already_banned", tg_id=tg_id))
        return

    # Кик из группы — best-effort
    settings = get_settings()
    group_kicked = False
    group_err: str | None = None
    if settings.main_chat_id:
        try:
            await bot.ban_chat_member(
                chat_id=settings.main_chat_id, user_id=tg_id,
            )
            group_kicked = True
            log.info("Banned tg_id=%s in group %s",
                     tg_id, settings.main_chat_id)
        except TelegramBadRequest as e:
            group_err = str(e)
            log.warning("Group ban failed for tg_id=%s: %s", tg_id, e)
        except Exception as e:
            group_err = str(e)
            log.warning("Group ban exception for tg_id=%s: %s", tg_id, e)

    extra = ""
    if settings.main_chat_id:
        extra = (
            "\n👮 Кикнут из группы." if group_kicked
            else f"\n⚠️ Из группы выкинуть не удалось: {group_err}"
        )
    await message.answer(
        t("ru", "admin_banned_user", tg_id=tg_id, reason=(reason or "—"))
        + extra
    )
    log.info("Admin %s banned tg_id=%s reason=%r group_kicked=%s",
             message.from_user.id, tg_id, reason, group_kicked)


@router.message(Command("unban_user"))
async def cmd_unban_user(
    message: Message, command: CommandObject, bot: Bot
) -> None:
    """/unban_user <tg_id> — снять с ban-list + разбанить в группе."""
    if not _is_admin(message.from_user.id if message.from_user else None):
        return
    arg = (command.args or "").strip()
    try:
        tg_id = int(arg)
    except ValueError:
        await message.answer(t("ru", "admin_unban_usage"))
        return
    async with get_session() as session:
        ok = await users.unban_tg_id(session, tg_id)
    if not ok:
        await message.answer(t("ru", "admin_not_banned", tg_id=tg_id))
        return

    # Разбан в группе — best-effort
    settings = get_settings()
    group_msg = ""
    if settings.main_chat_id:
        try:
            await bot.unban_chat_member(
                chat_id=settings.main_chat_id, user_id=tg_id,
                only_if_banned=True,
            )
            group_msg = "\n👤 Разбанен в группе (может вернуться сам)."
        except Exception as e:
            log.warning("Group unban exception for tg_id=%s: %s", tg_id, e)

    await message.answer(t("ru", "admin_unbanned_user", tg_id=tg_id) + group_msg)
    log.info("Admin %s unbanned tg_id=%s", message.from_user.id, tg_id)


# ---------------------------------------------------------------------------
# Редактирование отзывов (админ может убрать ошибочный негатив/спам-отзыв)
# ---------------------------------------------------------------------------


@router.message(Command("feedback_view"))
async def cmd_feedback_view(message: Message, command: CommandObject) -> None:
    """/feedback_view @username — список всех отзывов НА юзера с ID для удаления."""
    if not _is_admin(message.from_user.id if message.from_user else None):
        return
    arg = (command.args or "").strip().lstrip("@").lower()
    if not arg:
        await message.answer(
            "Использование: <code>/feedback_view @username</code>"
        )
        return

    from sqlalchemy import select, func as sa_func
    from bot.db.models import Feedback, User

    async with get_session() as session:
        rs = await session.execute(
            select(User).where(sa_func.lower(User.username) == arg)
        )
        target = rs.scalar_one_or_none()
        if target is None:
            await message.answer(f"❌ Юзер @{arg} не найден.")
            return
        rs2 = await session.execute(
            select(Feedback)
            .where(Feedback.to_user_id == target.id)
            .order_by(Feedback.created_at.desc())
            .limit(50)
        )
        feedbacks = list(rs2.scalars().all())
        if not feedbacks:
            await message.answer(f"📭 На @{arg} нет отзывов.")
            return

        lines = [f"💬 <b>Отзывы на @{arg}</b> (последние {len(feedbacks)}):\n"]
        for fb in feedbacks:
            from_rs = await session.execute(
                select(User).where(User.id == fb.from_user_id)
            )
            from_user = from_rs.scalar_one_or_none()
            from_label = (
                f"@{from_user.username}" if from_user and from_user.username
                else (from_user.display_name if from_user else "—")
            )
            date = fb.created_at.strftime("%Y-%m-%d") if fb.created_at else "—"
            stars = "⭐" * fb.rating
            comment = (fb.comment or "—")[:120]
            lines.append(
                f"<b>#{fb.id}</b> · {stars} · {date} · от {from_label}\n"
                f"💬 {comment}\n"
                f"Удалить: <code>/feedback_remove {fb.id}</code>"
            )
        await message.answer("\n\n".join(lines))


@router.message(Command("feedback_remove"))
async def cmd_feedback_remove(message: Message, command: CommandObject) -> None:
    """/feedback_remove <id> — удалить отзыв (cascade убирает FeedbackTag)."""
    if not _is_admin(message.from_user.id if message.from_user else None):
        return
    arg = (command.args or "").strip()
    try:
        fid = int(arg)
    except ValueError:
        await message.answer("Использование: <code>/feedback_remove &lt;id&gt;</code>")
        return
    from bot.db.models import Feedback
    async with get_session() as session:
        fb = await session.get(Feedback, fid)
        if fb is None:
            await message.answer(f"❌ Отзыв #{fid} не найден.")
            return
        to_user_id = fb.to_user_id
        await session.delete(fb)
        await session.commit()
    log.info(
        "Admin %s removed feedback #%s (target user_id=%s)",
        message.from_user.id, fid, to_user_id,
    )
    await message.answer(
        f"✅ Отзыв #{fid} удалён. Облако и рейтинг обновятся при следующем "
        "просмотре /profile или /check."
    )


@router.message(Command("banned_list"))
async def cmd_banned_list(message: Message) -> None:
    """/banned_list — последние 50 забаненных."""
    if not _is_admin(message.from_user.id if message.from_user else None):
        return
    async with get_session() as session:
        items = await users.list_banned(session, limit=50)
    if not items:
        await message.answer(t("ru", "admin_banned_list_empty"))
        return
    lines = [t("ru", "admin_banned_list_header", n=len(items))]
    for b in items:
        when = b.banned_at.strftime("%Y-%m-%d") if b.banned_at else "—"
        reason = b.reason or "—"
        lines.append(f"• <code>{b.tg_id}</code> · {when} · {reason}")
    await message.answer("\n".join(lines))


# ---------------------------------------------------------------------------
# Подписки: ручная выдача/отзыв админом
# ---------------------------------------------------------------------------


@router.message(Command("grant"))
async def cmd_grant(message: Message, command: CommandObject) -> None:
    """/grant <tg_id> <дней> [pro|business] — выдать подписку."""
    if not _is_admin(message.from_user.id if message.from_user else None):
        return
    args = (command.args or "").strip().split()
    if len(args) < 2:
        await message.answer(t("ru", "admin_grant_usage"))
        return
    try:
        tg_id = int(args[0])
        days = int(args[1])
    except ValueError:
        await message.answer(t("ru", "admin_grant_usage"))
        return
    kind = args[2].lower() if len(args) > 2 else "pro"
    if kind not in ("pro", "business", "individual", "company"):
        kind = "pro"
    async with get_session() as session:
        sub = await users.grant_subscription(
            session, tg_id=tg_id, kind=kind, days=days,
            granted_by_tg_id=message.from_user.id,
        )
    if sub is None:
        await message.answer(t("ru", "admin_grant_user_not_found", tg_id=tg_id))
        return
    until = sub.expires_at.strftime("%Y-%m-%d")
    await message.answer(
        t("ru", "admin_grant_done", kind=kind, tg_id=tg_id, until=until)
    )
    log.info("Admin %s granted sub %s to tg_id=%s for %s days",
             message.from_user.id, kind, tg_id, days)


@router.message(Command("revoke"))
async def cmd_revoke(message: Message, command: CommandObject) -> None:
    """/revoke <tg_id> — отозвать активную подписку."""
    if not _is_admin(message.from_user.id if message.from_user else None):
        return
    arg = (command.args or "").strip()
    try:
        tg_id = int(arg)
    except ValueError:
        await message.answer(t("ru", "admin_revoke_usage"))
        return
    async with get_session() as session:
        ok = await users.revoke_subscription(session, tg_id)
    if not ok:
        await message.answer(t("ru", "admin_revoke_no_active", tg_id=tg_id))
        return
    await message.answer(t("ru", "admin_revoke_done", tg_id=tg_id))
    log.info("Admin %s revoked sub from tg_id=%s",
             message.from_user.id, tg_id)


# ---------------------------------------------------------------------------
# Community badges (admin-assigned: verified / trusted / top)
# ---------------------------------------------------------------------------


@router.message(Command("grant_badge"))
async def cmd_grant_badge(message: Message, command: CommandObject) -> None:
    """/grant_badge <tg_id> <verified|trusted|top> — выдать бейдж."""
    if not _is_admin(message.from_user.id if message.from_user else None):
        return
    args = (command.args or "").strip().split()
    if len(args) < 2:
        await message.answer(t("ru", "admin_grant_badge_usage"))
        return
    try:
        tg_id = int(args[0])
    except ValueError:
        await message.answer(t("ru", "admin_grant_badge_usage"))
        return
    badge = args[1].lower()
    if badge not in users.KNOWN_BADGES:
        await message.answer(t("ru", "admin_badge_unknown", badge=badge))
        return
    async with get_session() as session:
        ok, changed = await users.set_user_badge(
            session, tg_id=tg_id, badge=badge, value=True,
        )
    if not ok:
        await message.answer(t("ru", "admin_grant_user_not_found", tg_id=tg_id))
        return
    if not changed:
        await message.answer(t("ru", "admin_badge_already",
                               badge=badge, tg_id=tg_id))
        return
    await message.answer(t("ru", "admin_badge_granted",
                           badge=badge, tg_id=tg_id))
    log.info("Admin %s granted badge=%s to tg_id=%s",
             message.from_user.id, badge, tg_id)


@router.message(Command("revoke_badge"))
async def cmd_revoke_badge(message: Message, command: CommandObject) -> None:
    """/revoke_badge <tg_id> <verified|trusted|top> — снять бейдж."""
    if not _is_admin(message.from_user.id if message.from_user else None):
        return
    args = (command.args or "").strip().split()
    if len(args) < 2:
        await message.answer(t("ru", "admin_revoke_badge_usage"))
        return
    try:
        tg_id = int(args[0])
    except ValueError:
        await message.answer(t("ru", "admin_revoke_badge_usage"))
        return
    badge = args[1].lower()
    if badge not in users.KNOWN_BADGES:
        await message.answer(t("ru", "admin_badge_unknown", badge=badge))
        return
    async with get_session() as session:
        ok, changed = await users.set_user_badge(
            session, tg_id=tg_id, badge=badge, value=False,
        )
    if not ok:
        await message.answer(t("ru", "admin_grant_user_not_found", tg_id=tg_id))
        return
    if not changed:
        await message.answer(t("ru", "admin_badge_not_set",
                               badge=badge, tg_id=tg_id))
        return
    await message.answer(t("ru", "admin_badge_revoked",
                           badge=badge, tg_id=tg_id))
    log.info("Admin %s revoked badge=%s from tg_id=%s",
             message.from_user.id, badge, tg_id)
