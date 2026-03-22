"""
Standalone bot commands: /status, /help, /reset_day, /delete_me.
"""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.helpers import format_status
from bot.keyboards import delete_me_confirm_keyboard, delete_me_warn_keyboard, reset_day_keyboard
from database.crud import delete_today_meals, delete_user, get_today_totals, get_user

logger = logging.getLogger(__name__)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = get_user(update.effective_user.id)
    if user is None:
        await update.message.reply_text("Please run /start first to set up your profile.")
        return

    totals = get_today_totals(user.id)
    await update.message.reply_text(
        format_status(totals, user), parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "*Cykdro Commands*\n\n"
        "/start      — Set up or update your profile\n"
        "/status     — View today's macro progress\n"
        "/reset\_day — Clear all meals logged today\n"
        "/delete\_me — Permanently delete your account\n"
        "/help       — Show this message\n\n"
        "Just send a 📸 *photo* or type a *meal description* to log food!",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# /reset_day — clear today's meal log
# ---------------------------------------------------------------------------

async def reset_day_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = get_user(update.effective_user.id)
    if user is None:
        await update.message.reply_text("Please run /start first to set up your profile.")
        return
    await update.message.reply_text(
        "🔄 *Reset Today's Log?*\n\n"
        "This will delete all meals you've logged today. "
        "Your profile and history from other days will stay intact.",
        parse_mode="Markdown",
        reply_markup=reset_day_keyboard(),
    )


async def reset_day_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    user = get_user(user_id)
    if user is None:
        await query.edit_message_text("No profile found. Use /start to set one up.")
        return
    count = delete_today_meals(user_id)
    if count:
        text = (
            f"✅ Done! Cleared {count} meal{'s' if count != 1 else ''} from today. "
            "Fresh start — go get it! 💪"
        )
    else:
        text = "ℹ️ No meals were logged today yet — nothing to clear!"
    await query.edit_message_text(text)


async def reset_day_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Reset cancelled. Your today's log is safe.")


# ---------------------------------------------------------------------------
# /delete_me — full account deletion (double confirmation)
# ---------------------------------------------------------------------------

async def delete_me_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = get_user(update.effective_user.id)
    if user is None:
        await update.message.reply_text("No profile found. Use /start to create one.")
        return
    await update.message.reply_text(
        "⚠️ *Delete Your Account?*\n\n"
        "This will permanently erase:\n"
        "• Your profile (goals, targets, settings)\n"
        "• Your entire meal history\n\n"
        "This action *cannot be undone*.",
        parse_mode="Markdown",
        reply_markup=delete_me_warn_keyboard(),
    )


async def delete_me_warn_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """First confirmation — escalate to final confirmation prompt."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🚨 *Last chance — are you absolutely sure?*\n\n"
        "All your data will be gone forever. There is no undo.",
        parse_mode="Markdown",
        reply_markup=delete_me_confirm_keyboard(),
    )


async def delete_me_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Second (final) confirmation — perform the deletion."""
    query = update.callback_query
    await query.answer()
    delete_user(update.effective_user.id)
    await query.edit_message_text(
        "👋 *Account deleted.*\n\n"
        "All your data has been removed. We're sorry to see you go!\n\n"
        "Whenever you're ready to start fresh, just send /start.",
        parse_mode="Markdown",
    )


async def delete_me_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ Deletion cancelled. Your account is safe!")
