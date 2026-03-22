"""
Admin dashboard — /admin command.
Only accessible by ADMIN_ID (set via ADMIN_TELEGRAM_ID env var).
"""
from __future__ import annotations

import logging
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from database.crud import (
    get_all_user_ids,
    get_all_users,
    get_stats,
    get_user,
    get_user_by_username,
    set_user_active,
)

logger = logging.getLogger(__name__)

def _get_admin_id() -> int:
    return int(os.environ.get("ADMIN_TELEGRAM_ID", "0"))

# ---------------------------------------------------------------------------
# Conversation states
# ---------------------------------------------------------------------------
(
    ADMIN_DASHBOARD,
    ADMIN_MANAGE_INPUT,
    ADMIN_BAN_INPUT,
    ADMIN_BROADCAST_INPUT,
    ADMIN_BROADCAST_CONFIRM,
    ADMIN_SEARCH_INPUT,
) = range(6)


# ---------------------------------------------------------------------------
# Keyboards
# ---------------------------------------------------------------------------

def _dashboard_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 View Stats",          callback_data="adm_stats")],
        [InlineKeyboardButton("👥 List All Users",      callback_data="adm_list_users")],
        [InlineKeyboardButton("👤 Manage User",         callback_data="adm_manage")],
        [InlineKeyboardButton("🚫 Ban / Unban User",    callback_data="adm_ban")],
        [InlineKeyboardButton("📢 Broadcast Message",   callback_data="adm_broadcast")],
        [InlineKeyboardButton("🔍 Search User",         callback_data="adm_search")],
    ])


def _back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Dashboard", callback_data="adm_back")]
    ])


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user.id != _get_admin_id():
        await update.message.reply_text("Command not found.")
        return ConversationHandler.END

    await update.message.reply_text(
        "🛠 *Cykdro Admin Panel*\n\nChoose an action:",
        parse_mode="Markdown",
        reply_markup=_dashboard_kb(),
    )
    return ADMIN_DASHBOARD


# ---------------------------------------------------------------------------
# Dashboard callbacks
# ---------------------------------------------------------------------------

async def admin_back_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🛠 *Cykdro Admin Panel*\n\nChoose an action:",
        parse_mode="Markdown",
        reply_markup=_dashboard_kb(),
    )
    return ADMIN_DASHBOARD


async def admin_stats_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    s = get_stats()
    await query.edit_message_text(
        "📊 *System Stats*\n\n"
        f"👥 Total users:       *{s['total_users']}*\n"
        f"🆕 Joined today:      *{s['users_today']}*\n"
        f"🍽 Meals today:       *{s['meals_today']}*\n"
        f"🚫 Banned users:      *{s['banned_users']}*",
        parse_mode="Markdown",
        reply_markup=_back_kb(),
    )
    return ADMIN_DASHBOARD


async def admin_list_users_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    users = get_all_users()
    if not users:
        await query.edit_message_text("No users yet.", reply_markup=_back_kb())
        return ADMIN_DASHBOARD

    lines = []
    for u in users:
        status = "🚫" if not u.is_active else "✅"
        username = f"@{u.username}" if u.username else "no username"
        lines.append(f"{status} `{u.id}` — {username} — {u.goal}")

    await query.edit_message_text(
        f"👥 *All Users ({len(users)})*\n\n" + "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=_back_kb(),
    )
    return ADMIN_DASHBOARD


async def admin_manage_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "👤 *Manage User*\n\nSend the Telegram user ID:",
        parse_mode="Markdown",
    )
    return ADMIN_MANAGE_INPUT


async def admin_ban_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🚫 *Ban / Unban User*\n\nSend the Telegram user ID to toggle their status:",
        parse_mode="Markdown",
    )
    return ADMIN_BAN_INPUT


async def admin_broadcast_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📢 *Broadcast Message*\n\nType the message to send to all active users:",
        parse_mode="Markdown",
    )
    return ADMIN_BROADCAST_INPUT


async def admin_search_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🔍 *Search User*\n\nSend a Telegram ID or @username:",
        parse_mode="Markdown",
    )
    return ADMIN_SEARCH_INPUT


# ---------------------------------------------------------------------------
# Text-input handlers
# ---------------------------------------------------------------------------

def _user_profile_text(user) -> str:
    status = "✅ Active" if user.is_active else "🚫 Banned"
    pro = " ⭐ Pro" if user.is_pro else ""
    return (
        f"👤 *User {user.id}*{pro}\n\n"
        f"Username: @{user.username or 'N/A'}\n"
        f"Status:   {status}\n"
        f"Age:      {user.age}\n"
        f"Gender:   {user.gender.capitalize()}\n"
        f"Weight:   {user.weight_kg} kg\n"
        f"Height:   {user.height_cm} cm\n"
        f"Activity: {user.activity_level}/5\n"
        f"Goal:     {user.goal.capitalize()}\n\n"
        f"Targets:  {user.daily_calories} kcal | "
        f"P {user.daily_protein_g} g | "
        f"C {user.daily_carbs_g} g | "
        f"F {user.daily_fat_g} g"
    )


async def admin_manage_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("❌ Invalid ID. Please send a numeric Telegram user ID.")
        return ADMIN_MANAGE_INPUT

    user = get_user(int(text))
    if user is None:
        await update.message.reply_text("❌ User not found.", reply_markup=_back_kb())
    else:
        await update.message.reply_text(
            _user_profile_text(user),
            parse_mode="Markdown",
            reply_markup=_back_kb(),
        )
    return ADMIN_DASHBOARD


async def admin_ban_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("❌ Invalid ID. Please send a numeric Telegram user ID.")
        return ADMIN_BAN_INPUT

    uid = int(text)
    user = get_user(uid)
    if user is None:
        await update.message.reply_text("❌ User not found.", reply_markup=_back_kb())
        return ADMIN_DASHBOARD

    new_state = not user.is_active
    set_user_active(uid, new_state)
    label = "✅ Unbanned" if new_state else "🚫 Banned"
    await update.message.reply_text(
        f"{label} user *{uid}* (@{user.username or 'N/A'}).",
        parse_mode="Markdown",
        reply_markup=_back_kb(),
    )
    return ADMIN_DASHBOARD


async def admin_broadcast_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["_broadcast_msg"] = update.message.text
    confirm_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Send to All", callback_data="adm_broadcast_do"),
            InlineKeyboardButton("❌ Cancel",      callback_data="adm_back"),
        ]
    ])
    await update.message.reply_text(
        f"📢 *Preview:*\n\n{update.message.text}\n\n"
        "Send this to all active users?",
        parse_mode="Markdown",
        reply_markup=confirm_kb,
    )
    return ADMIN_BROADCAST_CONFIRM


async def admin_broadcast_do_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    msg = context.user_data.pop("_broadcast_msg", None)
    if not msg:
        await query.edit_message_text("❌ No message found. Please start over.")
        return ADMIN_DASHBOARD

    user_ids = get_all_user_ids()
    sent, failed = 0, 0
    for uid in user_ids:
        try:
            await context.bot.send_message(
                uid,
                f"📢 *Announcement*\n\n{msg}",
                parse_mode="Markdown",
            )
            sent += 1
        except Exception:
            failed += 1

    await query.edit_message_text(
        f"✅ Broadcast complete.\n\nSent: {sent}  |  Failed: {failed}",
        reply_markup=_back_kb(),
    )
    return ADMIN_DASHBOARD


async def admin_search_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text.startswith("@") or not text.isdigit():
        user = get_user_by_username(text)
    else:
        user = get_user(int(text))

    if user is None:
        await update.message.reply_text("❌ User not found.", reply_markup=_back_kb())
    else:
        await update.message.reply_text(
            _user_profile_text(user),
            parse_mode="Markdown",
            reply_markup=_back_kb(),
        )
    return ADMIN_DASHBOARD


# ---------------------------------------------------------------------------
# Handler factory
# ---------------------------------------------------------------------------

def build_admin_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("admin", admin_command)],
        states={
            ADMIN_DASHBOARD: [
                CallbackQueryHandler(admin_stats_cb,       pattern="^adm_stats$"),
                CallbackQueryHandler(admin_list_users_cb,  pattern="^adm_list_users$"),
                CallbackQueryHandler(admin_manage_cb,      pattern="^adm_manage$"),
                CallbackQueryHandler(admin_ban_cb,       pattern="^adm_ban$"),
                CallbackQueryHandler(admin_broadcast_cb, pattern="^adm_broadcast$"),
                CallbackQueryHandler(admin_search_cb,    pattern="^adm_search$"),
                CallbackQueryHandler(admin_back_cb,      pattern="^adm_back$"),
            ],
            ADMIN_MANAGE_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_manage_input),
            ],
            ADMIN_BAN_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_ban_input),
            ],
            ADMIN_BROADCAST_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast_input),
            ],
            ADMIN_BROADCAST_CONFIRM: [
                CallbackQueryHandler(admin_broadcast_do_cb, pattern="^adm_broadcast_do$"),
                CallbackQueryHandler(admin_back_cb,         pattern="^adm_back$"),
            ],
            ADMIN_SEARCH_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_search_input),
            ],
        },
        fallbacks=[CallbackQueryHandler(admin_back_cb, pattern="^adm_back$")],
        per_message=False,
        name="admin",
        persistent=False,
    )
