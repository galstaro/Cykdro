"""
Meal logging handlers.

Flow:
  User sends photo or text
    → OpenAI analyses it
    → Bot shows result + Confirm / Edit / Cancel keyboard
    → Confirm → save to DB, show remaining macros
    → Edit   → ask for corrected values (manual override)
    → Cancel → discard
"""
from __future__ import annotations

import io
import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.helpers import format_analysis, format_status, macro_bar
from bot.keyboards import meal_confirmation_keyboard
from database.crud import add_meal, get_today_totals, get_user, is_user_active
from services.openai_vision import analyse_food_image, analyse_food_text

logger = logging.getLogger(__name__)

# ConversationHandler states
AWAITING_EDIT = 1

# user_data key where we stash the pending meal analysis
PENDING_KEY = "pending_meal"


# ---------------------------------------------------------------------------
# Guard — require onboarding
# ---------------------------------------------------------------------------

async def _require_user(update: Update) -> bool:
    """Return True if user is registered and not banned, else handle appropriately."""
    user_id = update.effective_user.id
    if not is_user_active(user_id):
        return False  # silently ignore banned users
    user = get_user(user_id)
    if user is None:
        await update.effective_message.reply_text(
            "Please run /start first to set up your profile."
        )
        return False
    return True


# ---------------------------------------------------------------------------
# Photo handler
# ---------------------------------------------------------------------------

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_user(update):
        return

    await update.message.reply_chat_action(ChatAction.TYPING)

    # Download highest-resolution photo
    photo = update.message.photo[-1]
    file = await photo.get_file()
    buf = io.BytesIO()
    await file.download_to_memory(buf)
    image_bytes = buf.getvalue()

    ai_client = context.bot_data["openai_client"]
    result = await analyse_food_image(ai_client, image_bytes)

    if "error" in result:
        if result["error"] == "not_food":
            await update.message.reply_text(
                "🤔 That doesn't look like food. Please send a photo of your meal."
            )
        else:
            await update.message.reply_text(
                f"⚠️ Analysis failed: {result.get('message', 'Unknown error')}. "
                "Try again or describe your meal in text."
            )
        return

    result["image_file_id"] = photo.file_id
    context.user_data[PENDING_KEY] = result

    await update.message.reply_text(
        format_analysis(result) + "\n\nIs this correct?",
        parse_mode="Markdown",
        reply_markup=meal_confirmation_keyboard(),
    )


# ---------------------------------------------------------------------------
# Text handler (free-text meal description)
# ---------------------------------------------------------------------------

async def handle_text_meal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _require_user(update):
        return

    await update.message.reply_chat_action(ChatAction.TYPING)

    ai_client = context.bot_data["openai_client"]
    result = await analyse_food_text(ai_client, update.message.text)

    if "error" in result:
        await update.message.reply_text(
            f"⚠️ Could not analyse that: {result.get('message', 'Unknown error')}."
        )
        return

    result["image_file_id"] = None
    context.user_data[PENDING_KEY] = result

    await update.message.reply_text(
        format_analysis(result) + "\n\nIs this correct?",
        parse_mode="Markdown",
        reply_markup=meal_confirmation_keyboard(),
    )


# ---------------------------------------------------------------------------
# Callback query handlers (Confirm / Edit / Cancel)
# ---------------------------------------------------------------------------

async def confirm_meal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    pending = context.user_data.get(PENDING_KEY)
    if not pending:
        await query.edit_message_text("Session expired. Please send your meal again.")
        return ConversationHandler.END

    user_id = update.effective_user.id
    add_meal(
        user_id=user_id,
        description=pending["description"],
        calories=pending["calories"],
        protein_g=pending["protein"],
        carbs_g=pending["carbs"],
        fat_g=pending["fat"],
        image_file_id=pending.get("image_file_id"),
    )
    context.user_data.pop(PENDING_KEY, None)

    totals = get_today_totals(user_id)
    user = get_user(user_id)

    await query.edit_message_text(
        f"✅ *Meal logged!*\n\n{format_status(totals, user)}",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def edit_meal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    pending = context.user_data.get(PENDING_KEY, {})
    await query.edit_message_text(
        f"Current values:\n{format_analysis(pending)}\n\n"
        "Send the corrected values in this format:\n"
        "`calories protein carbs fat`\n"
        "e.g. `450 35 40 12`",
        parse_mode="Markdown",
    )
    return AWAITING_EDIT


async def receive_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    parts = update.message.text.strip().split()
    if len(parts) != 4 or not all(p.lstrip("-").isdigit() for p in parts):
        await update.message.reply_text(
            "Please provide exactly 4 integers: `calories protein carbs fat`",
            parse_mode="Markdown",
        )
        return AWAITING_EDIT

    calories, protein, carbs, fat = (int(p) for p in parts)
    pending = context.user_data.get(PENDING_KEY, {})
    pending.update({"calories": calories, "protein": protein, "carbs": carbs, "fat": fat})
    context.user_data[PENDING_KEY] = pending

    await update.message.reply_text(
        format_analysis(pending) + "\n\nIs this correct?",
        parse_mode="Markdown",
        reply_markup=meal_confirmation_keyboard(),
    )
    return ConversationHandler.END  # back to waiting for callback


async def cancel_meal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data.pop(PENDING_KEY, None)
    await query.edit_message_text("❌ Meal discarded.")
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Handler factory
# ---------------------------------------------------------------------------

def build_meal_handler() -> ConversationHandler:
    """
    Wraps the edit sub-flow in a ConversationHandler so we can capture the
    corrected values; photo/text entry points are registered as standalone
    handlers in main.py because they must also work outside this conversation.
    """
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(edit_meal, pattern="^meal_edit$"),
        ],
        states={
            AWAITING_EDIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edit)
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_meal, pattern="^meal_cancel$"),
        ],
        name="meal_edit",
        persistent=False,
    )
