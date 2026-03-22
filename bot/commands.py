"""
Standalone bot commands: /status, /help, /reset.
"""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.helpers import format_status
from database.crud import get_today_totals, get_user, upsert_user

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
        "/start  — Set up or update your profile\n"
        "/status — View today's macro progress\n"
        "/help   — Show this message\n\n"
        "Just send a 📸 *photo* or type a *meal description* to log food!",
        parse_mode="Markdown",
    )
