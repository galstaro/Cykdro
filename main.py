"""
Cykdro — Telegram AI Nutrition & Fitness Tracker
Entry point: registers all handlers and starts the bot.
"""
from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from bot.commands import help_command, status_command
from bot.meal_logging import (
    build_meal_handler,
    cancel_meal,
    confirm_meal,
    handle_photo,
    handle_text_meal,
)
from bot.onboarding import build_onboarding_handler
from database.models import init_db

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    # ── Database ──────────────────────────────────────────────────────────────
    init_db()
    logger.info("Database initialised.")

    # ── Telegram application ──────────────────────────────────────────────────
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()

    # Shared OpenAI client stored in bot_data so all handlers can access it
    app.bot_data["openai_client"] = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

    # ── Handlers — order matters ──────────────────────────────────────────────

    # 1. Onboarding conversation (/start … /cancel)
    app.add_handler(build_onboarding_handler())

    # 2. Meal-edit sub-conversation (captures free-text corrections after Edit btn)
    app.add_handler(build_meal_handler())

    # 3. Confirm / Cancel callbacks (outside any conversation — fire immediately)
    app.add_handler(CallbackQueryHandler(confirm_meal, pattern="^meal_confirm$"))
    app.add_handler(CallbackQueryHandler(cancel_meal,  pattern="^meal_cancel$"))

    # 4. Standalone commands
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("help",   help_command))

    # 5. Media / text meal entry (lowest priority — catch-all for non-command messages)
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_meal)
    )

    # ── Start polling ─────────────────────────────────────────────────────────
    logger.info("Cykdro bot started. Polling for updates…")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
